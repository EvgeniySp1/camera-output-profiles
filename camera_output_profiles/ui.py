"""Blender UI panels for Camera Output Profiles."""

from __future__ import annotations

import bpy
from bpy.types import Panel

from . import operators, render_manager, utils, validation


ADDON_VERSION_LABEL = "Camera Output Profiles v0.1.2-unreleased"
TOKEN_HELP = (
    "Tokens: {camera}, {scene}, {width}, {height}, "
    "{frame}, {format}, {date}"
)


def _validation_icon(severity: str) -> str:
    return {
        "CRITICAL": "ERROR",
        "WARNING": "ERROR",
        "INFO": "INFO",
    }.get(severity, "INFO")


def _selected_camera(context: bpy.types.Context) -> bpy.types.Object | None:
    return operators.active_or_selected_camera(context)


def _draw_validation_status(layout, scene: bpy.types.Scene) -> None:
    row = layout.row()
    if not scene.camera_output_validation_timestamp:
        row.label(text="Validation: Not validated", icon="INFO")
    elif scene.camera_output_validation_critical_count:
        row.alert = True
        row.label(
            text=f"Validation: {scene.camera_output_validation_summary}",
            icon="ERROR",
        )
    elif scene.camera_output_validation_warning_count:
        row.label(
            text=f"Validation: {scene.camera_output_validation_summary}",
            icon="ERROR",
        )
    else:
        row.label(
            text=f"Validation: {scene.camera_output_validation_summary}",
            icon="CHECKMARK",
        )


def _draw_validation_messages(layout, scene: bpy.types.Scene, limit: int = 12) -> None:
    results = scene.camera_output_validation_results
    if not results:
        layout.label(text="No validation run yet.", icon="INFO")
        return

    for index, item in enumerate(results):
        if index >= limit:
            break
        label = item.message
        if item.camera_name:
            label = f"{item.camera_name}: {label}"
        layout.label(text=label, icon=_validation_icon(item.severity))

    if len(results) > limit:
        layout.label(text=f"{len(results) - limit} more messages...", icon="INFO")


def _draw_compact_final_path(
    layout,
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
) -> None:
    layout.label(text="Final Render Path:")
    try:
        final_path = render_manager.output_path_for_profile(scene, camera)
        compact = utils.compact_path(final_path, max_length=88)
        midpoint = min(44, len(compact))
        layout.label(text=compact[:midpoint])
        if len(compact) > midpoint:
            layout.label(text=compact[midpoint:])
    except (ValueError, utils.TemplateError) as exc:
        row = layout.row()
        row.alert = True
        row.label(text=str(exc), icon="ERROR")


def _draw_profile_actions(
    layout,
    camera: bpy.types.Object,
    *,
    prominent: bool = False,
) -> None:
    render_row = layout.row()
    if prominent:
        render_row.scale_y = 1.25
    render_op = render_row.operator(
        "camera_output.render_profile",
        text="Render This Profile",
        icon="RENDER_STILL",
    )
    render_op.camera_name = camera.name

    apply_op = layout.operator(
        "camera_output.apply_profile_to_scene",
        text="Apply Profile to Scene Output",
    )
    apply_op.camera_name = camera.name


def _draw_profile_fields(layout, profile) -> None:
    layout.prop(profile, "enabled", text="Enabled")

    resolution = layout.row(align=True)
    resolution.prop(profile, "width", text="Width")
    resolution.prop(profile, "height", text="Height")
    layout.label(
        text=f"Aspect Ratio: {utils.aspect_ratio_label(profile.width, profile.height)}"
    )

    format_row = layout.row(align=True)
    format_row.prop(profile, "file_format", text="File Format")
    format_row.prop(profile, "color_mode", text="Color Mode")
    if profile.file_format in {"JPEG", "WEBP"}:
        layout.prop(profile, "quality", text="Quality")

    layout.prop(
        profile,
        "transparent_background",
        text="Transparent Background",
    )
    layout.prop(profile, "output_subfolder", text="Output Subfolder")
    layout.prop(profile, "filename_template", text="Filename Template")

    frame_row = layout.row(align=True)
    frame_row.prop(profile, "use_current_frame", text="Use Current Frame")
    if not profile.use_current_frame:
        frame_row.prop(profile, "frame", text="Frame")


def _draw_presets(layout, enabled: bool) -> None:
    layout.label(text="Presets")
    grid = layout.grid_flow(
        row_major=True,
        columns=2,
        even_columns=True,
        align=True,
    )
    grid.enabled = enabled
    for identifier, (label, _, _) in operators.PRESETS.items():
        op = grid.operator("camera_output.apply_preset", text=label)
        op.preset = identifier


class CAMERAOUTPUT_PT_main(Panel):
    bl_idname = "CAMERAOUTPUT_PT_main"
    bl_label = "Camera Output Profiles"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene
        camera = _selected_camera(context)

        layout.label(text=ADDON_VERSION_LABEL, icon="CAMERA_DATA")

        if camera is None:
            layout.label(text="Selected Camera: None", icon="INFO")
            layout.label(text="Select a camera to use profile actions.")
        else:
            profile = camera.camera_output_profile
            layout.label(text=f"Selected Camera: {camera.name}", icon="CAMERA_DATA")
            enabled_label = "Enabled" if profile.enabled else "Disabled"
            layout.label(
                text=(
                    f"Profile: {profile.width} x {profile.height} | "
                    f"{utils.aspect_ratio_label(profile.width, profile.height)} | "
                    f"{profile.file_format} | {enabled_label}"
                )
            )
            _draw_compact_final_path(layout, scene, camera)
            _draw_profile_actions(layout, camera, prominent=True)

        presets = layout.box()
        _draw_presets(presets, camera is not None)

        batch_row = layout.row()
        batch_row.scale_y = 1.15
        batch_row.operator(
            "camera_output.render_enabled",
            text="Render All Enabled Profiles",
            icon="RENDER_STILL",
        )
        layout.operator(
            "camera_output.validate_profiles",
            text="Validate Profiles",
        )


class CAMERAOUTPUT_PT_camera_list(Panel):
    bl_idname = "CAMERAOUTPUT_PT_camera_list"
    bl_label = "Camera List"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        cameras = validation.iter_scene_cameras(context.scene)

        layout.operator(
            "camera_output.add_profiles",
            text="Add / Refresh Camera Profiles",
        )
        row = layout.row(align=True)
        row.operator("camera_output.enable_all", text="Enable All Profiles")
        row.operator("camera_output.disable_all", text="Disable All Profiles")

        if not cameras:
            layout.label(text="No cameras in scene.", icon="INFO")
            return

        for camera in cameras:
            profile = camera.camera_output_profile
            box = layout.box()
            header = box.row(align=True)
            header.prop(profile, "enabled", text="")
            header.label(text=camera.name, icon="CAMERA_DATA")
            box.label(
                text=(
                    f"{profile.width} x {profile.height} | "
                    f"{utils.aspect_ratio_label(profile.width, profile.height)} | "
                    f"{profile.file_format}"
                )
            )
            actions = box.row(align=True)
            select_op = actions.operator(
                "camera_output.select_camera",
                text="Select",
            )
            select_op.camera_name = camera.name
            render_op = actions.operator(
                "camera_output.render_profile",
                text="Render",
            )
            render_op.camera_name = camera.name


class CAMERAOUTPUT_PT_help(Panel):
    bl_idname = "CAMERAOUTPUT_PT_help"
    bl_label = "Help"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.label(text="Camera profiles are separate from Blender's")
        layout.label(text="global Scene Output settings.")
        layout.label(text="Presets edit only the selected camera profile.")
        layout.label(text="Rendering applies the profile temporarily.")
        layout.label(text="Use Apply Profile to Scene Output to sync")
        layout.label(text="Blender's Format panel manually.")
        layout.separator()
        layout.label(text=TOKEN_HELP)
        layout.label(text="Output Subfolder is relative to Base Output Folder.")


class CAMERAOUTPUT_PT_validation_errors(Panel):
    bl_idname = "CAMERAOUTPUT_PT_validation_errors"
    bl_label = "Validation Errors"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene.camera_output_validation_critical_count > 0

    def draw(self, context: bpy.types.Context) -> None:
        _draw_validation_messages(self.layout, context.scene)


class CAMERAOUTPUT_PT_validation_results(Panel):
    bl_idname = "CAMERAOUTPUT_PT_validation_results"
    bl_label = "Validation Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene.camera_output_validation_critical_count == 0

    def draw(self, context: bpy.types.Context) -> None:
        _draw_validation_messages(self.layout, context.scene)


class CAMERAOUTPUT_PT_camera_profile(Panel):
    bl_idname = "CAMERAOUTPUT_PT_camera_profile"
    bl_label = "Camera Output Profile"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = getattr(context, "object", None)
        return obj is not None and getattr(obj, "type", None) == "CAMERA"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        camera = context.object
        profile = camera.camera_output_profile

        _draw_profile_fields(layout, profile)
        layout.separator()
        _draw_compact_final_path(layout, context.scene, camera)
        _draw_profile_actions(layout, camera)


class CAMERAOUTPUT_PT_scene_settings(Panel):
    bl_idname = "CAMERAOUTPUT_PT_scene_settings"
    bl_label = "Camera Output Profiles Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene

        layout.label(text="Base Output Folder")
        layout.prop(scene.render, "filepath", text="")
        row = layout.row(align=True)
        row.operator(
            "camera_output.choose_base_output_folder",
            text="Choose Base Output Folder",
        )
        row.operator(
            "camera_output.open_output_folder",
            text="Open Base Output Folder",
        )

        layout.prop(
            scene,
            "camera_output_default_subfolder",
            text="Default Output Subfolder",
        )
        layout.separator()
        layout.prop(scene, "camera_output_show_render_window")
        layout.prop(scene, "camera_output_open_folder_after_render")
        layout.prop(scene, "camera_output_restore_scene_output")

        report_box = layout.box()
        report_box.label(text="Report Settings")
        report_box.prop(
            scene,
            "camera_output_write_report",
            text="Write Markdown Report",
        )
        report_box.label(text=render_manager.REPORT_FILENAME)

        validation_box = layout.box()
        validation_box.label(text="Validation Status")
        _draw_validation_status(validation_box, scene)
        validation_box.operator(
            "camera_output.validate_profiles",
            text="Validate Profiles",
        )


CLASSES = (
    CAMERAOUTPUT_PT_main,
    CAMERAOUTPUT_PT_camera_list,
    CAMERAOUTPUT_PT_help,
    CAMERAOUTPUT_PT_validation_errors,
    CAMERAOUTPUT_PT_validation_results,
    CAMERAOUTPUT_PT_camera_profile,
    CAMERAOUTPUT_PT_scene_settings,
)
