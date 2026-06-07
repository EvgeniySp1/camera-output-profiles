"""3D View sidebar UI for Camera Output Profiles."""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.types import Panel

from . import operators, render_manager, utils, validation


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
    if not scene.camera_output_validation_timestamp:
        row.label(text="Validation: Not validated", icon="INFO")
    elif critical:
        row.alert = True
        row.label(text=f"Validation: {summary}", icon="ERROR")
    elif warnings:
        row.label(text=f"Validation: {summary}", icon="ERROR")
    else:
        row.label(text=f"Validation: {summary}", icon="CHECKMARK")


def _draw_wrapped_path(layout, path: Path | str, *, width: int = 48) -> None:
    text = str(path)
    for index in range(0, len(text), width):
        layout.label(text=text[index : index + width])


def _selected_camera(context: bpy.types.Context) -> bpy.types.Object | None:
    return operators.active_or_selected_camera(context)


class CAMERAOUTPUT_PT_main(Panel):
    bl_idname = "CAMERAOUTPUT_PT_main"
    bl_label = "Camera Output Profiles"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cam Output"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene
        cameras = validation.iter_scene_cameras(scene)
        enabled_count = sum(
            1 for camera in cameras if camera.camera_output_profile.enabled
        )
        selected_camera = _selected_camera(context)

        layout.label(text="Camera Output Profiles v0.1.1", icon="CAMERA_DATA")
        layout.label(text=f"Cameras: {len(cameras)} | Enabled: {enabled_count}")

        explanation = layout.box()
        explanation.label(text="Camera profiles are separate from Blender's")
        explanation.label(text="global Output settings. Presets edit only the")
        explanation.label(text="selected camera profile. Add-on renders apply")
        explanation.label(text="it temporarily; use Apply Profile to Scene Output")
        explanation.label(text="to sync Blender's Format panel.")

        self._draw_output_section(layout, scene, selected_camera)
        self._draw_global_controls(layout, scene)
        self._draw_render_behavior(layout, scene)
        self._draw_presets(layout, selected_camera)

        if selected_camera is not None:
            self._draw_selected_profile(layout, scene, selected_camera)
        else:
            box = layout.box()
            box.label(text="Selected Camera Profile: None", icon="INFO")
            box.label(text="Select a camera to edit or render its profile.")

        self._draw_camera_list(layout, cameras)

    def _draw_output_section(
        self,
        layout,
        scene: bpy.types.Scene,
        selected_camera: bpy.types.Object | None,
    ) -> None:
        output = layout.box()
        output.label(text="Output")
        output.label(text="Base Output Folder:")
        output.prop(scene.render, "filepath", text="")

        try:
            base_path = utils.resolve_output_base(scene.render.filepath, bpy.path.abspath)
            _draw_wrapped_path(output, base_path)
        except ValueError as exc:
            row = output.row()
            row.alert = True
            row.label(text=str(exc), icon="ERROR")

        row = output.row(align=True)
        row.operator(
            "camera_output.choose_base_output_folder",
            text="Choose Base Output Folder",
        )
        row.operator(
            "camera_output.open_output_folder",
            text="Open Base Output Folder",
        )

        output.separator()
        output.label(
            text=(
                f"Scene Output: {scene.render.resolution_x} x "
                f"{scene.render.resolution_y} @ "
                f"{scene.render.resolution_percentage}% | "
                f"{scene.render.image_settings.file_format}"
            )
        )

        if selected_camera is not None:
            output.label(
                text=(
                    "Default Subfolder: "
                    f"{selected_camera.camera_output_profile.output_subfolder or '(none)'}"
                )
            )

    def _draw_global_controls(self, layout, scene: bpy.types.Scene) -> None:
        controls = layout.box()
        controls.label(text="Global Controls")
        controls.operator(
            "camera_output.add_profiles",
            text="Add / Refresh Camera Profiles",
        )
        row = controls.row(align=True)
        row.operator("camera_output.enable_all", text="Enable All Profiles")
        row.operator("camera_output.disable_all", text="Disable All Profiles")
        controls.operator(
            "camera_output.validate_profiles",
            text="Validate Profiles",
        )
        render_row = controls.row()
        render_row.scale_y = 1.25
        render_row.operator(
            "camera_output.render_enabled",
            text="Render All Enabled Profiles",
            icon="RENDER_STILL",
        )
        _draw_validation_status(controls, scene)

    def _draw_render_behavior(self, layout, scene: bpy.types.Scene) -> None:
        behavior = layout.box()
        behavior.label(text="Render Behavior")
        behavior.prop(scene, "camera_output_show_render_window")
        behavior.prop(scene, "camera_output_open_folder_after_render")
        behavior.prop(scene, "camera_output_restore_scene_output")

    def _draw_presets(
        self,
        layout,
        selected_camera: bpy.types.Object | None,
    ) -> None:
        presets = layout.box()
        presets.label(text="Presets for Selected Camera")
        grid = presets.grid_flow(
            row_major=True,
            columns=2,
            even_columns=True,
            align=True,
        )
        grid.enabled = selected_camera is not None
        for identifier, (label, _, _) in operators.PRESETS.items():
            op = grid.operator("camera_output.apply_preset", text=label)
            op.preset = identifier
        presets.label(text="Presets edit the camera profile only.")
        presets.label(text="Use Apply Profile to Scene Output to sync")
        presets.label(text="Blender's Format panel.")

    def _draw_selected_profile(
        self,
        layout,
        scene: bpy.types.Scene,
        camera: bpy.types.Object,
    ) -> None:
        profile = camera.camera_output_profile
        box = layout.box()
        box.label(text=f"Selected Camera Profile: {camera.name}", icon="CAMERA_DATA")
        box.prop(profile, "enabled", text="Enabled")

        resolution = box.row(align=True)
        resolution.prop(profile, "width", text="Width")
        resolution.prop(profile, "height", text="Height")
        box.label(
            text=f"Aspect Ratio: {utils.aspect_ratio_label(profile.width, profile.height)}"
        )

        format_row = box.row(align=True)
        format_row.prop(profile, "file_format", text="File Format")
        format_row.prop(profile, "color_mode", text="Color Mode")
        if profile.file_format in {"JPEG", "WEBP"}:
            box.prop(profile, "quality", text="Quality")

        box.prop(profile, "transparent_background", text="Transparent Background")

        box.label(text="Output Subfolder:")
        box.prop(profile, "output_subfolder", text="")
        box.label(text="Optional folder inside the Base Output Folder.")
        box.label(text="Leave empty to save directly in the base folder.")

        box.label(text="Filename Template:")
        box.prop(profile, "filename_template", text="")
        box.label(
            text="Tokens: {camera}, {scene}, {width}, {height}, {frame}, {format}, {date}"
        )

        frame_row = box.row(align=True)
        frame_row.prop(profile, "use_current_frame", text="Use Current Frame")
        if not profile.use_current_frame:
            frame_row.prop(profile, "frame", text="Frame")

        box.separator()
        box.label(text="Final Render Path:")
        try:
            final_path = render_manager.output_path_for_profile(scene, camera)
            _draw_wrapped_path(box, final_path)
        except (ValueError, utils.TemplateError) as exc:
            row = box.row()
            row.alert = True
            row.label(text=str(exc), icon="ERROR")

        render_row = box.row()
        render_row.scale_y = 1.3
        render_op = render_row.operator(
            "camera_output.render_profile",
            text="Render This Profile",
            icon="RENDER_STILL",
        )
        render_op.camera_name = camera.name

        apply_op = box.operator(
            "camera_output.apply_profile_to_scene",
            text="Apply Profile to Scene Output",
        )
        apply_op.camera_name = camera.name

        open_op = box.operator(
            "camera_output.open_final_output_folder",
            text="Open Final Output Folder",
        )
        open_op.camera_name = camera.name

    def _draw_camera_list(self, layout, cameras: list[bpy.types.Object]) -> None:
        layout.label(text=f"Camera List ({len(cameras)})", icon="OUTLINER_OB_CAMERA")
        if not cameras:
            layout.label(text="No cameras in scene.", icon="INFO")
            return

        for camera in cameras:
            profile = camera.camera_output_profile
            box = layout.box()
            header = box.row(align=True)
            header.prop(profile, "enabled", text="")
            header.label(text=camera.name, icon="CAMERA_DATA")

            details = box.row(align=True)
            details.label(text=f"{profile.width} x {profile.height}")
            details.label(
                text=utils.aspect_ratio_label(profile.width, profile.height)
            )
            details.label(text=profile.file_format)

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
            if index >= 12:
                break
            label = item.message
            if item.camera_name:
                label = f"{item.camera_name}: {label}"
            layout.label(text=label, icon=_validation_icon(item.severity))

        if len(results) > 12:
            layout.label(text=f"{len(results) - 12} more messages...", icon="INFO")


CLASSES = (
    CAMERAOUTPUT_PT_main,
    CAMERAOUTPUT_PT_validation_results,
)
