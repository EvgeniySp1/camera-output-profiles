"""Compact Blender UI panels for Camera Output Profiles."""

from __future__ import annotations

import bpy
from bpy.types import Panel

from . import camera_tools, operators, render_manager, utils, validation


ADDON_VERSION_LABEL = "Camera Output Profiles v0.2.0"
TOKEN_HELP = "Tokens: {camera}, {scene}, {width}, {height}, {frame}, {format}, {date}"


def _selected_camera(context):
    return operators.active_or_selected_camera(context)


def _validation_icon(severity: str) -> str:
    return {"CRITICAL": "ERROR", "WARNING": "ERROR", "INFO": "INFO"}.get(
        severity, "INFO"
    )


def _draw_validation_status(layout, scene) -> None:
    row = layout.row()
    if not scene.camera_output_validation_timestamp:
        row.label(text="Validation: Not validated", icon="INFO")
    elif scene.camera_output_validation_critical_count:
        row.alert = True
        row.label(text=f"Validation: {scene.camera_output_validation_summary}", icon="ERROR")
    elif scene.camera_output_validation_warning_count:
        row.label(text=f"Validation: {scene.camera_output_validation_summary}", icon="ERROR")
    else:
        row.label(text=f"Validation: {scene.camera_output_validation_summary}", icon="CHECKMARK")


def _draw_validation_messages(layout, scene, limit: int = 12) -> None:
    if not scene.camera_output_validation_results:
        layout.label(text="No validation run yet.", icon="INFO")
        return
    for index, item in enumerate(scene.camera_output_validation_results):
        if index >= limit:
            layout.label(text="More messages available in validation data.", icon="INFO")
            break
        prefix = f"{item.camera_name}: " if item.camera_name else ""
        layout.label(text=f"{prefix}{item.message}", icon=_validation_icon(item.severity))


def _draw_compact_final_path(layout, scene, camera) -> None:
    layout.label(text="Final Render Path:")
    try:
        compact = utils.compact_path(
            render_manager.output_path_for_profile(scene, camera),
            max_length=76,
        )
        layout.label(text=compact)
    except (ValueError, utils.TemplateError) as exc:
        row = layout.row()
        row.alert = True
        row.label(text=str(exc), icon="ERROR")


def _draw_profile_actions(layout, camera, *, prominent: bool = False) -> None:
    row = layout.row()
    row.enabled = not render_manager.is_render_job_active()
    row.scale_y = 1.25 if prominent else 1.0
    operator = row.operator(
        "camera_output.render_profile",
        text="Render This Profile",
        icon="RENDER_STILL",
    )
    operator.camera_name = camera.name
    operator = layout.operator(
        "camera_output.apply_profile_to_scene",
        text="Apply Profile to Scene Output",
    )
    operator.camera_name = camera.name


def _draw_profile_fields(layout, profile) -> None:
    layout.prop(profile, "enabled", text="Enabled")
    row = layout.row(align=True)
    row.prop(profile, "width", text="Width")
    row.prop(profile, "height", text="Height")
    layout.label(text=f"Aspect Ratio: {utils.aspect_ratio_label(profile.width, profile.height)}")
    row = layout.row(align=True)
    row.prop(profile, "file_format", text="File Format")
    row.prop(profile, "color_mode", text="Color Mode")
    if profile.file_format in {"JPEG", "WEBP"}:
        layout.prop(profile, "quality", text="Quality")
    layout.prop(profile, "transparent_background", text="Transparent Background")
    layout.prop(profile, "output_subfolder", text="Output Subfolder")
    layout.prop(profile, "filename_template", text="Filename Template")
    row = layout.row(align=True)
    row.prop(profile, "use_current_frame", text="Use Current Frame")
    if not profile.use_current_frame:
        row.prop(profile, "frame", text="Frame")


class CAMERAOUTPUT_PT_main(Panel):
    bl_idname = "CAMERAOUTPUT_PT_main"
    bl_label = "Camera Output Profiles"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        camera = _selected_camera(context)
        layout.label(text=ADDON_VERSION_LABEL, icon="CAMERA_DATA")
        if camera is None:
            layout.label(text="Selected Camera: None", icon="INFO")
        else:
            profile = camera.camera_output_profile
            layout.label(text=f"Selected Camera: {camera.name}", icon="CAMERA_DATA")
            layout.label(
                text=(
                    f"Profile: {profile.width} x {profile.height} | "
                    f"{utils.aspect_ratio_label(profile.width, profile.height)} | "
                    f"{profile.file_format}"
                )
            )
            _draw_compact_final_path(layout, scene, camera)
            _draw_profile_actions(layout, camera, prominent=True)
        layout.operator("camera_output.validate_profiles", text="Validate Profiles")


class CAMERAOUTPUT_PT_presets(Panel):
    bl_idname = "CAMERAOUTPUT_PT_presets"
    bl_label = "Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        self.layout.label(text="Open a preset group below.")


class CAMERAOUTPUT_PT_output_presets(Panel):
    bl_idname = "CAMERAOUTPUT_PT_output_presets"
    bl_label = "Output Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_presets"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        grid = self.layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        grid.enabled = _selected_camera(context) is not None
        for identifier, (label, _, _) in operators.PRESETS.items():
            operator = grid.operator("camera_output.apply_preset", text=label)
            operator.preset = identifier


class CAMERAOUTPUT_PT_view_presets(Panel):
    bl_idname = "CAMERAOUTPUT_PT_view_presets"
    bl_label = "View Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_presets"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        grid = self.layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        grid.enabled = _selected_camera(context) is not None
        for identifier, (label, _) in camera_tools.VIEW_PRESETS.items():
            operator = grid.operator("camera_output.apply_view_preset", text=label)
            operator.preset = identifier


class CAMERAOUTPUT_PT_lens_presets(Panel):
    bl_idname = "CAMERAOUTPUT_PT_lens_presets"
    bl_label = "Lens Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_presets"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        grid = self.layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        grid.enabled = _selected_camera(context) is not None
        for identifier, (label, _, _) in camera_tools.LENS_PRESETS.items():
            operator = grid.operator("camera_output.apply_lens_preset", text=label)
            operator.preset = identifier


class CAMERAOUTPUT_PT_camera_tools(Panel):
    bl_idname = "CAMERAOUTPUT_PT_camera_tools"
    bl_label = "Camera Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        enabled = _selected_camera(context) is not None
        layout.prop(scene, "camera_output_target_mode", text="Target")
        row = layout.row(align=True)
        row.prop(scene, "camera_output_distance_multiplier", text="Distance")
        row.prop(scene, "camera_output_height_offset", text="Height")
        layout.prop(scene, "camera_output_margin", text="Margin")

        box = layout.box()
        box.label(text="Frame / Fit")
        row = box.row(align=True)
        row.enabled = enabled
        for target, label in (
            ("SELECTED", "Frame Selected Object"),
            ("COLLECTION", "Active Collection"),
            ("VISIBLE", "All Visible"),
        ):
            operator = row.operator("camera_output.frame_target", text=label)
            operator.target = target

        box = layout.box()
        box.label(text="Target / Tracking")
        row = box.row(align=True)
        row.enabled = enabled
        row.operator("camera_output.create_target_empty", text="Create Target Empty")
        row.operator("camera_output.aim_at_target", text="Aim Camera at Target")
        row = box.row(align=True)
        row.enabled = enabled
        row.operator("camera_output.add_tracking", text="Add Track To Target")
        row.operator("camera_output.remove_tracking", text="Remove Camera Tracking")

        box = layout.box()
        box.label(text="Duplicate")
        box.prop(scene, "camera_output_copy_tracking", text="Copy Tracking")
        row = box.row()
        row.enabled = enabled
        row.operator("camera_output.duplicate_camera_profile", text="Duplicate Camera + Profile")

        box = layout.box()
        box.label(text="Create Camera Set")
        box.prop(scene, "camera_output_camera_set_type", text="Type")
        box.prop(scene, "camera_output_camera_set_add_tracking", text="Add Tracking")
        box.operator("camera_output.create_camera_set", text="Create Camera Set")


class CAMERAOUTPUT_PT_camera_list(Panel):
    bl_idname = "CAMERAOUTPUT_PT_camera_list"
    bl_label = "Camera List"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        cameras = validation.iter_scene_cameras(context.scene)
        layout.operator("camera_output.add_profiles", text="Add / Refresh Camera Profiles")
        row = layout.row(align=True)
        row.operator("camera_output.enable_all", text="Enable All Profiles")
        row.operator("camera_output.disable_all", text="Disable All Profiles")
        for camera in cameras:
            profile = camera.camera_output_profile
            box = layout.box()
            row = box.row(align=True)
            row.prop(profile, "enabled", text="")
            row.label(text=camera.name, icon="CAMERA_DATA")
            box.label(text=f"{profile.width} x {profile.height} | {profile.file_format}")
            row = box.row(align=True)
            operator = row.operator("camera_output.select_camera", text="Select")
            operator.camera_name = camera.name
            operator = row.operator("camera_output.render_profile", text="Render")
            operator.camera_name = camera.name


class CAMERAOUTPUT_PT_help(Panel):
    bl_idname = "CAMERAOUTPUT_PT_help"
    bl_label = "Help"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Profiles stay separate from Scene Output.")
        layout.label(text="View tools use Target Mode and Margin.")
        layout.label(text="Create a Target Empty before adding tracking.")
        layout.label(text=TOKEN_HELP)
        layout.label(text="Batch rendering is disabled in v0.2.0.")


class CAMERAOUTPUT_PT_validation_errors(Panel):
    bl_idname = "CAMERAOUTPUT_PT_validation_errors"
    bl_label = "Validation Errors"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"
    bl_parent_id = "CAMERAOUTPUT_PT_main"

    @classmethod
    def poll(cls, context):
        return context.scene.camera_output_validation_critical_count > 0

    def draw(self, context):
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
    def poll(cls, context):
        return context.scene.camera_output_validation_critical_count == 0

    def draw(self, context):
        _draw_validation_messages(self.layout, context.scene)


class CAMERAOUTPUT_PT_camera_profile(Panel):
    bl_idname = "CAMERAOUTPUT_PT_camera_profile"
    bl_label = "Camera Output Profile"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return getattr(getattr(context, "object", None), "type", None) == "CAMERA"

    def draw(self, context):
        camera = context.object
        layout = self.layout
        profile = camera.camera_output_profile
        _draw_profile_fields(layout, profile)
        tracking = layout.box()
        tracking.label(text="Tracking Target")
        tracking.prop(profile, "tracking_target", text="")
        constraint = camera.constraints.get(camera_tools.TRACK_CONSTRAINT_NAME)
        tracking.label(text=f"Tracking: {'Active' if constraint else 'Inactive'}")
        if camera.data.type == "ORTHO":
            tracking.label(text=f"Lens: Orthographic ({camera.data.ortho_scale:g})")
        else:
            tracking.label(text=f"Lens: {camera.data.lens:g} mm")
        _draw_compact_final_path(layout, context.scene, camera)
        _draw_profile_actions(layout, camera)


class CAMERAOUTPUT_PT_scene_settings(Panel):
    bl_idname = "CAMERAOUTPUT_PT_scene_settings"
    bl_label = "Camera Output Profiles Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Base Output Folder")
        layout.prop(scene.render, "filepath", text="")
        row = layout.row(align=True)
        row.operator("camera_output.choose_base_output_folder", text="Choose Base Output Folder")
        row.operator("camera_output.open_output_folder", text="Open Base Output Folder")
        layout.prop(scene, "camera_output_default_subfolder", text="Default Output Subfolder")
        layout.prop(scene, "camera_output_show_render_window")
        layout.prop(scene, "camera_output_open_folder_after_render")
        layout.prop(scene, "camera_output_restore_scene_output")
        layout.prop(scene, "camera_output_write_report", text="Write Markdown Report")
        workflow = layout.box()
        workflow.label(text="Camera Workflow Defaults")
        workflow.prop(scene, "camera_output_target_mode")
        workflow.prop(scene, "camera_output_distance_multiplier")
        workflow.prop(scene, "camera_output_height_offset")
        workflow.prop(scene, "camera_output_margin")
        workflow.prop(scene, "camera_output_camera_set_type")
        workflow.prop(scene, "camera_output_camera_set_add_tracking")
        validation_box = layout.box()
        validation_box.label(text="Validation Status")
        _draw_validation_status(validation_box, scene)
        validation_box.operator("camera_output.validate_profiles", text="Validate Profiles")


CLASSES = (
    CAMERAOUTPUT_PT_main,
    CAMERAOUTPUT_PT_presets,
    CAMERAOUTPUT_PT_output_presets,
    CAMERAOUTPUT_PT_view_presets,
    CAMERAOUTPUT_PT_lens_presets,
    CAMERAOUTPUT_PT_camera_tools,
    CAMERAOUTPUT_PT_camera_list,
    CAMERAOUTPUT_PT_help,
    CAMERAOUTPUT_PT_validation_errors,
    CAMERAOUTPUT_PT_validation_results,
    CAMERAOUTPUT_PT_camera_profile,
    CAMERAOUTPUT_PT_scene_settings,
)
