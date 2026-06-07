"""Validation for per-camera output profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
from typing import Iterable

import bpy

from . import utils


SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"


@dataclass(slots=True)
class ValidationMessage:
    severity: str
    message: str
    camera_name: str = ""


@dataclass(slots=True)
class ValidationResult:
    messages: list[ValidationMessage] = field(default_factory=list)
    output_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for item in self.messages if item.severity == SEVERITY_CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.messages if item.severity == SEVERITY_WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for item in self.messages if item.severity == SEVERITY_INFO)

    @property
    def has_critical(self) -> bool:
        return self.critical_count > 0

    def add(self, severity: str, message: str, camera_name: str = "") -> None:
        self.messages.append(ValidationMessage(severity, message, camera_name))

    def warning_messages(self) -> list[str]:
        warnings: list[str] = []
        for item in self.messages:
            if item.severity != SEVERITY_WARNING:
                continue
            prefix = f"{item.camera_name}: " if item.camera_name else ""
            warnings.append(f"{prefix}{item.message}")
        return warnings

    def summary(self) -> str:
        if self.critical_count:
            return (
                f"{self.critical_count} critical, "
                f"{self.warning_count} warnings, {self.info_count} info"
            )
        if self.warning_count:
            return f"OK with {self.warning_count} warnings"
        return "OK"


def iter_scene_cameras(scene: bpy.types.Scene) -> list[bpy.types.Object]:
    return sorted(
        (obj for obj in scene.objects if getattr(obj, "type", None) == "CAMERA"),
        key=lambda obj: obj.name.lower(),
    )


def supported_image_formats(scene: bpy.types.Scene) -> set[str]:
    try:
        enum_items = scene.render.image_settings.bl_rna.properties[
            "file_format"
        ].enum_items
        return {item.identifier for item in enum_items}
    except Exception:
        return {"PNG", "JPEG"}


def _normalize_duplicate_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _frame_for_profile(scene: bpy.types.Scene, profile) -> int:
    return int(scene.frame_current if profile.use_current_frame else profile.frame)


def _validate_camera_object(
    result: ValidationResult,
    camera: bpy.types.Object | None,
) -> bool:
    if camera is None:
        result.add(SEVERITY_CRITICAL, "Camera object is missing.")
        return False
    if getattr(camera, "type", None) != "CAMERA":
        result.add(SEVERITY_CRITICAL, "Object is not a camera.", camera.name)
        return False
    if getattr(camera, "data", None) is None:
        result.add(SEVERITY_CRITICAL, "Camera data is missing.", camera.name)
        return False
    return True


def _store_validation_result(
    scene: bpy.types.Scene,
    result: ValidationResult,
) -> None:
    collection = scene.camera_output_validation_results
    collection.clear()
    for message in result.messages:
        item = collection.add()
        item.severity = message.severity
        item.message = message.message
        item.camera_name = message.camera_name

    scene.camera_output_validation_critical_count = result.critical_count
    scene.camera_output_validation_warning_count = result.warning_count
    scene.camera_output_validation_info_count = result.info_count
    scene.camera_output_validation_summary = result.summary()
    scene.camera_output_validation_timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def validate_scene(
    scene: bpy.types.Scene,
    cameras: Iterable[bpy.types.Object] | None = None,
    *,
    include_disabled: bool = False,
    store: bool = True,
    now: datetime | None = None,
) -> ValidationResult:
    """Validate camera output profiles for the scene."""
    result = ValidationResult()
    all_scene_cameras = iter_scene_cameras(scene)
    selected_cameras = list(cameras) if cameras is not None else all_scene_cameras

    if cameras is None and not all_scene_cameras:
        result.add(SEVERITY_CRITICAL, "No cameras found in this scene.")

    base_path: Path | None = None
    try:
        base_path = utils.resolve_output_base(scene.render.filepath, bpy.path.abspath)
    except ValueError as exc:
        result.add(SEVERITY_CRITICAL, str(exc))

    supported_formats = supported_image_formats(scene)
    output_keys: dict[str, tuple[str, Path]] = {}
    enabled_count = 0

    for camera in selected_cameras:
        if not _validate_camera_object(result, camera):
            continue

        profile = camera.camera_output_profile
        should_validate_profile = include_disabled or profile.enabled
        if not should_validate_profile:
            continue

        if profile.enabled:
            enabled_count += 1

        if profile.width <= 0 or profile.height <= 0:
            result.add(
                SEVERITY_CRITICAL,
                "Enabled profile has invalid width or height.",
                camera.name,
            )
            continue

        if not profile.filename_template.strip():
            result.add(SEVERITY_CRITICAL, "Filename template is empty.", camera.name)
            continue

        try:
            utils.extract_template_tokens(profile.filename_template)
        except utils.TemplateError as exc:
            result.add(SEVERITY_CRITICAL, str(exc), camera.name)
            continue

        if profile.file_format not in utils.FILE_EXTENSIONS:
            result.add(
                SEVERITY_CRITICAL,
                f"Unsupported profile file format: {profile.file_format}",
                camera.name,
            )
            continue

        if profile.file_format not in supported_formats:
            result.add(
                SEVERITY_CRITICAL,
                f"File format {profile.file_format} is not supported by this Blender build.",
                camera.name,
            )
            continue

        frame = _frame_for_profile(scene, profile)
        if not profile.use_current_frame:
            if frame < scene.frame_start or frame > scene.frame_end:
                result.add(
                    SEVERITY_WARNING,
                    (
                        f"Frame {frame} is outside scene range "
                        f"{scene.frame_start}-{scene.frame_end}."
                    ),
                    camera.name,
                )

        if profile.file_format == "JPEG" and profile.color_mode == "RGBA":
            result.add(
                SEVERITY_WARNING,
                "JPEG does not store alpha; RGB will be used for this render.",
                camera.name,
            )

        if base_path is None:
            continue

        try:
            values = utils.build_template_values(
                camera_name=camera.name,
                scene_name=scene.name,
                width=profile.width,
                height=profile.height,
                frame=frame,
                file_format=profile.file_format,
                now=now,
            )
            output_path = utils.build_output_path(
                base_path,
                profile.output_subfolder,
                profile.filename_template,
                values,
                profile.file_format,
            )
        except (ValueError, utils.TemplateError) as exc:
            result.add(SEVERITY_CRITICAL, str(exc), camera.name)
            continue

        result.output_paths[camera.name] = output_path
        duplicate_key = _normalize_duplicate_key(output_path)
        if duplicate_key in output_keys:
            first_camera, first_path = output_keys[duplicate_key]
            result.add(
                SEVERITY_CRITICAL,
                f"Duplicate output filename also used by {first_camera}: {first_path}",
                camera.name,
            )
        else:
            output_keys[duplicate_key] = (camera.name, output_path)

    if cameras is None and all_scene_cameras and enabled_count == 0:
        result.add(SEVERITY_WARNING, "No enabled camera profiles found.")

    if not result.messages:
        result.add(SEVERITY_INFO, "All enabled camera profiles are valid.")

    if store:
        _store_validation_result(scene, result)
    return result
