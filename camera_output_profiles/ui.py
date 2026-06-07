"""3D View sidebar UI for Camera Output Profiles."""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.types import Panel

from . import operators, utils, validation


def _validation_icon(severity: str) -> str:
    return {
        "CRITICAL": "ERROR",
        "WARNING": "ERROR",
        "INFO": "INFO",
    }.get(severity, "INFO")


def _draw_validation_status(layout, scene: bpy.types.Scene) -> None:
    critical = scene.camera_output_validation_critical_count
    warnings = scene.camera_output_validation_warning_count
    summary = scene.camera_output_validation_summary

    row = layout.row()
    if critical:
        row.alert = True
        row.label(text=f"Validation: {summary}", icon="ERROR")
    elif warnings:
        row.label(text=f"Validation: {summary}", icon="ERROR")
    else:
        row.label(text=f"Validation: {summary}", icon="CHECKMARK")


def _draw_output_folder(layout, scene: bpy.types.Scene) -> None:
    try:
        base_path = utils.resolve_output_base(scene.render.filepath, bpy.path.abspath)
        text = utils.compact_path(Path(base_path))
        layout.label(text=f"Output: {text}", icon="FILE_FOLDER")
    except ValueError:
        row = layout.row()
        row.alert = True
        row.label(text="Output path is empty", icon="ERROR")


class CAMERAOUTPUT_PT_main(Panel):
    bl_idname = "CAMERAOUTPUT_PT_main"
    bl_label = "Camera Output Profiles"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene

        layout.label(text="Camera Output Profiles", icon="CAMERA_DATA")
        _draw_output_folder(layout, scene)
        _draw_validation_status(layout, scene)

        controls = layout.box()
        controls.label(text="Global Controls")
        row = controls.row(align=True)
        row.operator("camera_output.add_profiles", text="Add Profiles for All Cameras")
        row = controls.row(align=True)
        row.operator("camera_output.enable_all", text="Enable All")
        row.operator("camera_output.disable_all", text="Disable All")
        row = controls.row(align=True)
        row.operator("camera_output.validate_profiles", text="Validate Profiles")
        row.operator("camera_output.open_output_folder", text="Open Output Folder")
        render_row = controls.row()
        render_row.scale_y = 1.2
        render_row.operator(
            "camera_output.render_enabled",
            text="Render Enabled Profiles",
            icon="RENDER_STILL",
        )

        presets = layout.box()
        presets.label(text="Presets for Selected Camera")
        grid = presets.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        for identifier, (label, _, _) in operators.PRESETS.items():
            op = grid.operator("camera_output.apply_preset", text=label)
            op.preset = identifier

        cameras = validation.iter_scene_cameras(scene)
        layout.label(text=f"Cameras ({len(cameras)})", icon="OUTLINER_OB_CAMERA")
        if not cameras:
            layout.label(text="No cameras in scene.", icon="INFO")
            return

        for camera in cameras:
            self._draw_camera_profile(layout, camera)

    def _draw_camera_profile(self, layout, camera: bpy.types.Object) -> None:
        profile = camera.camera_output_profile
        box = layout.box()

        header = box.row(align=True)
        header.prop(profile, "enabled", text="")
        header.label(text=camera.name, icon="CAMERA_DATA")
        select_op = header.operator("camera_output.select_camera", text="", icon="RESTRICT_SELECT_OFF")
        select_op.camera_name = camera.name
        render_op = header.operator("camera_output.render_profile", text="", icon="RENDER_STILL")
        render_op.camera_name = camera.name

        resolution = box.row(align=True)
        resolution.prop(profile, "width", text="W")
        resolution.prop(profile, "height", text="H")
        resolution.label(
            text=f"Aspect: {utils.aspect_ratio_label(profile.width, profile.height)}"
        )

        file_row = box.row(align=True)
        file_row.prop(profile, "file_format", text="")
        file_row.prop(profile, "color_mode", text="")
        if profile.file_format in {"JPEG", "WEBP"}:
            file_row.prop(profile, "quality", text="Quality")

        box.prop(profile, "filename_template", text="Filename")
        box.prop(profile, "output_subfolder", text="Subfolder")

        options = box.row(align=True)
        options.prop(profile, "transparent_background", text="Transparent")
        options.prop(profile, "use_current_frame", text="Current Frame")
        if not profile.use_current_frame:
            options.prop(profile, "frame", text="Frame")


class CAMERAOUTPUT_PT_validation_results(Panel):
    bl_idname = "CAMERAOUTPUT_PT_validation_results"
    bl_label = "Validation Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        results = context.scene.camera_output_validation_results
        if not results:
            layout.label(text="No validation run yet.", icon="INFO")
            return

        for index, item in enumerate(results):
            if index >= 8:
                break
            label = item.message
            if item.camera_name:
                label = f"{item.camera_name}: {label}"
            layout.label(text=label, icon=_validation_icon(item.severity))

        if len(results) > 8:
            layout.label(text=f"{len(results) - 8} more messages...", icon="INFO")


CLASSES = (
    CAMERAOUTPUT_PT_main,
    CAMERAOUTPUT_PT_validation_results,
)
