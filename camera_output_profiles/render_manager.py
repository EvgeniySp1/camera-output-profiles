"""Render execution and report generation for camera output profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import webbrowser

import bpy

from . import utils
from .validation import ValidationResult


REPORT_FILENAME = "CAMERA_OUTPUT_PROFILES_REPORT.md"
_ACTIVE_RENDER_JOB = None


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
    width: int
    height: int
    file_format: str


@dataclass(slots=True)
class SkippedProfile:
    camera_name: str
    reason: str


@dataclass(slots=True)
class BatchRenderResult:
    rendered: list[RenderedProfile] = field(default_factory=list)
    skipped: list[SkippedProfile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    report_path: Path | None = None


@dataclass(slots=True)
class RenderSession:
    scene: Any
    camera_name: str
    snapshot: SceneRenderSnapshot
    output_path: Path
    restore_scene_output: bool
    open_folder_after_render: bool
    write_report: bool
    show_render_window: bool
    fallback_used: bool = False


@dataclass(slots=True)
class RenderStartResult:
    output_path: Path
    fallback_used: bool
    operator_result: set[str]


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


def _restore_non_profile_settings(
    scene: bpy.types.Scene,
    snapshot: SceneRenderSnapshot,
) -> list[str]:
    """Restore camera, frame and base path while keeping profile format settings."""
    render = scene.render
    errors: list[str] = []
    restore_steps = (
        ("scene.camera", lambda: setattr(scene, "camera", snapshot.camera)),
        ("filepath", lambda: setattr(render, "filepath", snapshot.filepath)),
        ("frame", lambda: scene.frame_set(snapshot.frame_current)),
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


def apply_profile_to_scene_output(scene: bpy.types.Scene, profile) -> None:
    """Copy a camera profile into Blender's global Scene Output settings."""
    scene.render.resolution_x = int(profile.width)
    scene.render.resolution_y = int(profile.height)
    scene.render.resolution_percentage = 100
    _apply_image_settings(scene, profile)
    if hasattr(scene.render, "film_transparent"):
        scene.render.film_transparent = bool(profile.transparent_background)


def show_render_result() -> bool:
    """Show Blender's Render Result when running with a user interface."""
    if getattr(bpy.app, "background", False):
        return False
    try:
        result = bpy.ops.render.view_show("INVOKE_DEFAULT")
        return "FINISHED" in result or "RUNNING_MODAL" in result
    except Exception as exc:
        print(f"[Camera Output Profiles] Could not show Render Result: {exc}")
        return False


def output_path_for_profile(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    now: datetime | None = None,
    base_path: Path | None = None,
) -> Path:
    profile = camera.camera_output_profile
    frame = int(scene.frame_current if profile.use_current_frame else profile.frame)
    if base_path is None:
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
    base_path: Path | None = None,
    restore_scene_output: bool = True,
    show_render_window: bool = False,
) -> Path:
    """Render one still image and optionally restore scene settings afterwards."""
    if getattr(camera, "type", None) != "CAMERA" or camera.data is None:
        raise RenderProfileError(f"{camera.name} is not a valid camera.")

    profile = camera.camera_output_profile
    try:
        output_path = output_path_for_profile(
            scene,
            camera,
            now=now,
            base_path=base_path,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, utils.TemplateError) as exc:
        raise RenderProfileError(
            f"Could not prepare output for {camera.name}: {exc}"
        ) from exc

    snapshot = capture_scene_settings(scene)
    render_error: Exception | None = None

    try:
        scene.camera = camera
        apply_profile_to_scene_output(scene, profile)
        scene.render.filepath = str(output_path)
        if hasattr(scene.render, "use_file_extension"):
            scene.render.use_file_extension = False
        if not profile.use_current_frame:
            scene.frame_set(int(profile.frame))

        operator_result = bpy.ops.render.render(write_still=True, scene=scene.name)
        if "FINISHED" not in operator_result:
            raise RuntimeError(f"Blender render operator returned {operator_result}")
    except Exception as exc:
        render_error = exc
    finally:
        restore_errors = []
        if render_error is not None or restore_scene_output:
            restore_errors = _restore_scene_settings(scene, snapshot)
        else:
            restore_errors = _restore_non_profile_settings(scene, snapshot)

    if render_error is not None:
        raise RenderProfileError(f"Render failed for {camera.name}: {render_error}") from render_error
    if restore_errors:
        raise RenderProfileError(
            f"Rendered {camera.name}, but restoring scene settings reported errors."
        )

    print(f"[Camera Output Profiles] Rendered {camera.name}: {output_path}")
    if show_render_window:
        show_render_result()
    return output_path


def is_render_job_active() -> bool:
    return _ACTIVE_RENDER_JOB is not None


def _handler_list(name: str):
    return getattr(getattr(bpy.app, "handlers", None), name, None)


def _register_render_handlers() -> None:
    for name, handler in (
        ("render_complete", _on_render_complete),
        ("render_cancel", _on_render_cancel),
    ):
        handlers = _handler_list(name)
        if handlers is not None and handler not in handlers:
            handlers.append(handler)


def _remove_render_handlers() -> None:
    for name, handler in (
        ("render_complete", _on_render_complete),
        ("render_cancel", _on_render_cancel),
    ):
        handlers = _handler_list(name)
        if handlers is not None:
            while handler in handlers:
                handlers.remove(handler)


def _set_workspace_status(message: str | None) -> None:
    workspace = getattr(getattr(bpy, "context", None), "workspace", None)
    if workspace is not None:
        try:
            workspace.status_text_set(message)
        except Exception:
            pass


def _open_output_folder(path: Path) -> None:
    try:
        result = bpy.ops.wm.path_open(filepath=str(path))
        if "FINISHED" in result:
            return
    except Exception:
        pass
    try:
        webbrowser.open(path.as_uri())
    except Exception as exc:
        print(f"[Camera Output Profiles] WARNING: Could not open output folder: {exc}")


def write_single_render_report(
    scene: bpy.types.Scene,
    camera_name: str,
    output_path: Path,
    *,
    cancelled: bool = False,
) -> Path:
    report_path = output_path.parent / REPORT_FILENAME
    lines = [
        "# Camera Output Profiles Report",
        "",
        f"- Scene: `{_markdown_text(scene.name)}`",
        f"- Date/time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- Blender version: `{bpy.app.version_string}`",
        f"- Rendered profiles: `{'0' if cancelled else '1'}`",
        f"- Status: `{'Cancelled' if cancelled else 'Completed'}`",
        "",
        "## Output Files",
        "",
        (
            f"- `{_markdown_text(camera_name)}` | "
            f"`{output_path}` | {'cancelled' if cancelled else 'rendered'}"
        ),
        "",
        "## Notes",
        "",
        "- Batch rendering is disabled in v0.2.0.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[Camera Output Profiles] Wrote report: {report_path}")
    return report_path


def _finish_render(cancelled: bool) -> None:
    global _ACTIVE_RENDER_JOB
    job = _ACTIVE_RENDER_JOB
    if job is None:
        _remove_render_handlers()
        return

    _ACTIVE_RENDER_JOB = None
    _remove_render_handlers()
    restore_errors: list[str] = []
    if getattr(job, "restore_scene_output", False):
        restore_errors = _restore_scene_settings(job.scene, job.snapshot)
    else:
        restore_errors = _restore_non_profile_settings(job.scene, job.snapshot)

    if cancelled:
        message = (
            f"Render cancelled for {job.camera_name}. "
            f"Planned output: {job.output_path}"
        )
        if job.write_report:
            try:
                job.output_path.parent.mkdir(parents=True, exist_ok=True)
                write_single_render_report(
                    job.scene,
                    job.camera_name,
                    job.output_path,
                    cancelled=True,
                )
            except OSError as exc:
                print(f"[Camera Output Profiles] WARNING: Could not write report: {exc}")
        if job.open_folder_after_render:
            _open_output_folder(job.output_path.parent)
    else:
        message = f"Rendered {job.camera_name} profile: {job.output_path}"
        if job.write_report:
            try:
                job.output_path.parent.mkdir(parents=True, exist_ok=True)
                write_single_render_report(job.scene, job.camera_name, job.output_path)
            except OSError as exc:
                print(f"[Camera Output Profiles] WARNING: Could not write report: {exc}")
        if job.open_folder_after_render:
            _open_output_folder(job.output_path.parent)
        if job.show_render_window and job.fallback_used:
            show_render_result()

    if restore_errors:
        message += " Scene restoration reported warnings."
    print(f"[Camera Output Profiles] {message}")
    _set_workspace_status(message)


def _on_render_complete(scene, *args) -> None:
    _finish_render(cancelled=False)


def _on_render_cancel(scene, *args) -> None:
    _finish_render(cancelled=True)


def cleanup_render_session(*, restore: bool = True) -> None:
    """Remove handlers and optionally restore a currently active add-on render."""
    global _ACTIVE_RENDER_JOB
    job = _ACTIVE_RENDER_JOB
    _ACTIVE_RENDER_JOB = None
    _remove_render_handlers()
    if restore and job is not None and hasattr(job, "scene") and hasattr(job, "snapshot"):
        _restore_scene_settings(job.scene, job.snapshot)
    _set_workspace_status(None)


def start_visible_render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    now: datetime | None = None,
) -> RenderStartResult:
    """Start one profile render and defer restoration to Blender render handlers."""
    global _ACTIVE_RENDER_JOB
    if is_render_job_active():
        raise RenderProfileError("Camera Output Profiles render is already running.")
    if getattr(camera, "type", None) != "CAMERA" or camera.data is None:
        raise RenderProfileError(f"{camera.name} is not a valid camera.")

    try:
        output_path = output_path_for_profile(scene, camera, now=now)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, utils.TemplateError) as exc:
        raise RenderProfileError(
            f"Could not prepare output for {camera.name}: {exc}"
        ) from exc

    snapshot = capture_scene_settings(scene)
    profile = camera.camera_output_profile
    scene.camera = camera
    apply_profile_to_scene_output(scene, profile)
    scene.render.filepath = str(output_path)
    if hasattr(scene.render, "use_file_extension"):
        scene.render.use_file_extension = False
    if not profile.use_current_frame:
        scene.frame_set(int(profile.frame))

    job = RenderSession(
        scene=scene,
        camera_name=camera.name,
        snapshot=snapshot,
        output_path=output_path,
        restore_scene_output=bool(scene.camera_output_restore_scene_output),
        open_folder_after_render=bool(scene.camera_output_open_folder_after_render),
        write_report=bool(scene.camera_output_write_report),
        show_render_window=bool(scene.camera_output_show_render_window),
    )
    _ACTIVE_RENDER_JOB = job
    _register_render_handlers()
    _set_workspace_status(f"Rendering {camera.name}: {output_path}")

    fallback_used = False
    try:
        result = bpy.ops.render.render(
            "INVOKE_DEFAULT",
            write_still=True,
            scene=scene.name,
        )
        if "CANCELLED" in result:
            raise RuntimeError(f"Visible render operator returned {result}")
    except Exception as visible_error:
        fallback_used = True
        job.fallback_used = True
        print(
            "[Camera Output Profiles] WARNING: "
            "Visible render invocation failed; used fallback render mode. "
            f"Reason: {visible_error}"
        )
        if _ACTIVE_RENDER_JOB is None:
            scene.camera = camera
            apply_profile_to_scene_output(scene, profile)
            scene.render.filepath = str(output_path)
            if hasattr(scene.render, "use_file_extension"):
                scene.render.use_file_extension = False
            if not profile.use_current_frame:
                scene.frame_set(int(profile.frame))
            _ACTIVE_RENDER_JOB = job
            _register_render_handlers()
        try:
            result = bpy.ops.render.render(write_still=True, scene=scene.name)
        except Exception as fallback_error:
            cleanup_render_session(restore=True)
            raise RenderProfileError(
                f"Render failed for {camera.name}: {fallback_error}"
            ) from fallback_error
        if "FINISHED" not in result:
            cleanup_render_session(restore=True)
            raise RenderProfileError(
                f"Blender render operator returned {result}"
            )

    if "FINISHED" in result and _ACTIVE_RENDER_JOB is job:
        _finish_render(cancelled=False)
    return RenderStartResult(output_path, fallback_used, set(result))


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
        f"- Base output folder: `{base_path}`",
        f"- Rendered profiles: `{len(batch_result.rendered)}`",
        "",
        "## Output Files",
        "",
    ]

    if batch_result.rendered:
        for rendered in batch_result.rendered:
            lines.append(
                "- "
                f"`{_markdown_text(rendered.camera_name)}` | "
                f"{rendered.width} x {rendered.height} | "
                f"{rendered.file_format} | "
                f"`{rendered.output_path}`"
            )
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

    lines.extend(["", "## Errors", ""])
    if batch_result.errors:
        for error in batch_result.errors:
            lines.append(f"- {_markdown_text(error)}")
    else:
        lines.append("- None")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[Camera Output Profiles] Wrote report: {report_path}")
    return report_path
