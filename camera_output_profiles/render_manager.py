"""Render execution and report generation for camera output profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import bpy

from . import utils
from .validation import ValidationResult


REPORT_FILENAME = "CAMERA_OUTPUT_PROFILES_REPORT.md"


class RenderProfileError(RuntimeError):
    """Raised when one camera profile fails to render."""


@dataclass(slots=True)
class SceneRenderSnapshot:
    camera: Any
    resolution_x: int
    resolution_y: int
    resolution_percentage: int
    filepath: str
    use_file_extension: bool | None
    file_format: str
    color_mode: str
    quality: int | None
    film_transparent: bool | None
    frame_current: int


@dataclass(slots=True)
class RenderedProfile:
    camera_name: str
    output_path: Path


@dataclass(slots=True)
class SkippedProfile:
    camera_name: str
    reason: str


@dataclass(slots=True)
class BatchRenderResult:
    rendered: list[RenderedProfile] = field(default_factory=list)
    skipped: list[SkippedProfile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: Path | None = None


def capture_scene_settings(scene: bpy.types.Scene) -> SceneRenderSnapshot:
    render = scene.render
    image_settings = render.image_settings
    return SceneRenderSnapshot(
        camera=scene.camera,
        resolution_x=render.resolution_x,
        resolution_y=render.resolution_y,
        resolution_percentage=render.resolution_percentage,
        filepath=render.filepath,
        use_file_extension=(
            render.use_file_extension if hasattr(render, "use_file_extension") else None
        ),
        file_format=image_settings.file_format,
        color_mode=image_settings.color_mode,
        quality=image_settings.quality if hasattr(image_settings, "quality") else None,
        film_transparent=(
            render.film_transparent if hasattr(render, "film_transparent") else None
        ),
        frame_current=scene.frame_current,
    )


def _restore_scene_settings(
    scene: bpy.types.Scene,
    snapshot: SceneRenderSnapshot,
) -> list[str]:
    render = scene.render
    image_settings = render.image_settings
    errors: list[str] = []

    restore_steps = (
        ("scene.camera", lambda: setattr(scene, "camera", snapshot.camera)),
        ("resolution_x", lambda: setattr(render, "resolution_x", snapshot.resolution_x)),
        ("resolution_y", lambda: setattr(render, "resolution_y", snapshot.resolution_y)),
        (
            "resolution_percentage",
            lambda: setattr(
                render,
                "resolution_percentage",
                snapshot.resolution_percentage,
            ),
        ),
        ("filepath", lambda: setattr(render, "filepath", snapshot.filepath)),
        (
            "file_format",
            lambda: setattr(image_settings, "file_format", snapshot.file_format),
        ),
        (
            "color_mode",
            lambda: setattr(image_settings, "color_mode", snapshot.color_mode),
        ),
    )

    for label, restore in restore_steps:
        try:
            restore()
        except Exception as exc:
            errors.append(f"Could not restore {label}: {exc}")

    if snapshot.use_file_extension is not None and hasattr(render, "use_file_extension"):
        try:
            render.use_file_extension = snapshot.use_file_extension
        except Exception as exc:
            errors.append(f"Could not restore use_file_extension: {exc}")

    if snapshot.quality is not None and hasattr(image_settings, "quality"):
        try:
            image_settings.quality = snapshot.quality
        except Exception as exc:
            errors.append(f"Could not restore quality: {exc}")

    if snapshot.film_transparent is not None and hasattr(render, "film_transparent"):
        try:
            render.film_transparent = snapshot.film_transparent
        except Exception as exc:
            errors.append(f"Could not restore transparent film setting: {exc}")

    try:
        scene.frame_set(snapshot.frame_current)
    except Exception as exc:
        errors.append(f"Could not restore frame: {exc}")

    for error in errors:
        print(f"[Camera Output Profiles] WARNING: {error}")
    return errors


def _apply_image_settings(scene: bpy.types.Scene, profile) -> None:
    render = scene.render
    image_settings = render.image_settings
    image_settings.file_format = profile.file_format

    color_mode = profile.color_mode
    if profile.file_format == "JPEG" and color_mode == "RGBA":
        color_mode = "RGB"

    try:
        image_settings.color_mode = color_mode
    except Exception:
        image_settings.color_mode = "RGB"

    if profile.file_format in {"JPEG", "WEBP"} and hasattr(image_settings, "quality"):
        image_settings.quality = int(profile.quality)


def output_path_for_profile(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    now: datetime | None = None,
) -> Path:
    profile = camera.camera_output_profile
    frame = int(scene.frame_current if profile.use_current_frame else profile.frame)
    base_path = utils.resolve_output_base(scene.render.filepath, bpy.path.abspath)
    values = utils.build_template_values(
        camera_name=camera.name,
        scene_name=scene.name,
        width=profile.width,
        height=profile.height,
        frame=frame,
        file_format=profile.file_format,
        now=now,
    )
    return utils.build_output_path(
        base_path,
        profile.output_subfolder,
        profile.filename_template,
        values,
        profile.file_format,
    )


def render_profile(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    now: datetime | None = None,
) -> Path:
    """Render one still image and restore scene settings afterwards."""
    if getattr(camera, "type", None) != "CAMERA" or camera.data is None:
        raise RenderProfileError(f"{camera.name} is not a valid camera.")

    profile = camera.camera_output_profile
    try:
        output_path = output_path_for_profile(scene, camera, now=now)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, utils.TemplateError) as exc:
        raise RenderProfileError(
            f"Could not prepare output for {camera.name}: {exc}"
        ) from exc

    snapshot = capture_scene_settings(scene)
    render_error: Exception | None = None

    try:
        scene.camera = camera
        scene.render.resolution_x = int(profile.width)
        scene.render.resolution_y = int(profile.height)
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(output_path)
        if hasattr(scene.render, "use_file_extension"):
            scene.render.use_file_extension = False
        _apply_image_settings(scene, profile)
        if hasattr(scene.render, "film_transparent"):
            scene.render.film_transparent = bool(profile.transparent_background)
        if not profile.use_current_frame:
            scene.frame_set(int(profile.frame))

        operator_result = bpy.ops.render.render(write_still=True, scene=scene.name)
        if "FINISHED" not in operator_result:
            raise RuntimeError(f"Blender render operator returned {operator_result}")
    except Exception as exc:
        render_error = exc
    finally:
        restore_errors = _restore_scene_settings(scene, snapshot)

    if render_error is not None:
        raise RenderProfileError(f"Render failed for {camera.name}: {render_error}") from render_error
    if restore_errors:
        raise RenderProfileError(
            f"Rendered {camera.name}, but restoring scene settings reported errors."
        )

    print(f"[Camera Output Profiles] Rendered {camera.name}: {output_path}")
    return output_path


def _markdown_text(value: str) -> str:
    return value.replace("`", "'")


def write_markdown_report(
    scene: bpy.types.Scene,
    batch_result: BatchRenderResult,
    validation_result: ValidationResult,
    *,
    base_path: Path,
) -> Path:
    report_path = base_path / REPORT_FILENAME
    lines = [
        "# Camera Output Profiles Report",
        "",
        f"- Scene: `{_markdown_text(scene.name)}`",
        f"- Date/time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- Blender version: `{bpy.app.version_string}`",
        f"- Rendered profiles: `{len(batch_result.rendered)}`",
        "",
        "## Output Files",
        "",
    ]

    if batch_result.rendered:
        for rendered in batch_result.rendered:
            try:
                display_path = rendered.output_path.relative_to(base_path)
            except ValueError:
                display_path = rendered.output_path
            lines.append(f"- `{_markdown_text(rendered.camera_name)}`: `{display_path}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Skipped Cameras", ""])
    if batch_result.skipped:
        for skipped in batch_result.skipped:
            lines.append(
                f"- `{_markdown_text(skipped.camera_name)}`: {_markdown_text(skipped.reason)}"
            )
    else:
        lines.append("- None")

    warnings = validation_result.warning_messages() + batch_result.warnings
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- {_markdown_text(warning)}")
    else:
        lines.append("- None")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[Camera Output Profiles] Wrote report: {report_path}")
    return report_path
