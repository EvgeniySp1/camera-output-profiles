"""Blender operators for Camera Output Profiles."""

from datetime import datetime
from pathlib import Path
import webbrowser

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from . import render_manager, utils, validation


PRESETS = {
    "FHD_16_9": ("FHD 16:9", 1920, 1080),
    "UHD_16_9": ("4K 16:9", 3840, 2160),
    "SQUARE": ("Square", 2048, 2048),
    "PORTRAIT_4_5": ("Portrait 4:5", 2160, 2700),
    "VERTICAL_9_16": ("Vertical 9:16", 1080, 1920),
    "THUMBNAIL_16_9": ("Thumbnail 16:9", 1280, 720),
}

PRESET_ITEMS = tuple(
    (identifier, label, f"Set resolution to {width} x {height}")
    for identifier, (label, width, height) in PRESETS.items()
)


def _active_or_selected_camera(context: bpy.types.Context) -> bpy.types.Object | None:
    active = context.object
    if active is not None and getattr(active, "type", None) == "CAMERA":
        return active
    for obj in context.selected_objects:
        if getattr(obj, "type", None) == "CAMERA":
            return obj
    return None


def _camera_by_name(scene: bpy.types.Scene, camera_name: str) -> bpy.types.Object | None:
    camera = scene.objects.get(camera_name)
    if camera is not None and getattr(camera, "type", None) == "CAMERA":
        return camera
    return None


def _initialize_camera_profile(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    force_frame: bool = False,
) -> None:
    profile = camera.camera_output_profile
    if force_frame or not profile.initialized:
        profile.frame = scene.frame_current
    profile.initialized = True


class CAMERAOUTPUT_OT_add_profiles(Operator):
    bl_idname = "camera_output.add_profiles"
    bl_label = "Add Profiles for All Cameras"
    bl_description = "Initialize output profiles for every camera in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        cameras = validation.iter_scene_cameras(scene)
        if not cameras:
            self.report({"WARNING"}, "No cameras found in this scene.")
            return {"CANCELLED"}

        for camera in cameras:
            _initialize_camera_profile(scene, camera)

        self.report({"INFO"}, f"Profiles ready for {len(cameras)} cameras.")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_enable_all(Operator):
    bl_idname = "camera_output.enable_all"
    bl_label = "Enable All"
    bl_description = "Enable all camera output profiles"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        cameras = validation.iter_scene_cameras(context.scene)
        for camera in cameras:
            _initialize_camera_profile(context.scene, camera)
            camera.camera_output_profile.enabled = True
        self.report({"INFO"}, f"Enabled {len(cameras)} camera profiles.")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_disable_all(Operator):
    bl_idname = "camera_output.disable_all"
    bl_label = "Disable All"
    bl_description = "Disable all camera output profiles"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        cameras = validation.iter_scene_cameras(context.scene)
        for camera in cameras:
            _initialize_camera_profile(context.scene, camera)
            camera.camera_output_profile.enabled = False
        self.report({"INFO"}, f"Disabled {len(cameras)} camera profiles.")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_validate_profiles(Operator):
    bl_idname = "camera_output.validate_profiles"
    bl_label = "Validate Profiles"
    bl_description = "Validate enabled camera output profiles"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        result = validation.validate_scene(context.scene, store=True)
        if result.has_critical:
            self.report({"ERROR"}, result.summary())
        elif result.warning_count:
            self.report({"WARNING"}, result.summary())
        else:
            self.report({"INFO"}, result.summary())
        return {"FINISHED"}


class CAMERAOUTPUT_OT_apply_preset(Operator):
    bl_idname = "camera_output.apply_preset"
    bl_label = "Apply Resolution Preset"
    bl_description = "Apply a common output resolution to the active or selected camera"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(name="Preset", items=PRESET_ITEMS)

    def execute(self, context: bpy.types.Context):
        camera = _active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}

        _, width, height = PRESETS[self.preset]
        profile = camera.camera_output_profile
        _initialize_camera_profile(context.scene, camera)
        profile.width = width
        profile.height = height
        self.report({"INFO"}, f"Applied {width}x{height} to {camera.name}.")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_select_camera(Operator):
    bl_idname = "camera_output.select_camera"
    bl_label = "Select Camera"
    bl_description = "Select this camera in the scene"
    bl_options = {"REGISTER"}

    camera_name: StringProperty(name="Camera")

    def execute(self, context: bpy.types.Context):
        camera = _camera_by_name(context.scene, self.camera_name)
        if camera is None:
            self.report({"ERROR"}, "Camera not found.")
            return {"CANCELLED"}

        for obj in context.selected_objects:
            obj.select_set(False)
        try:
            camera.select_set(True)
            context.view_layer.objects.active = camera
        except RuntimeError as exc:
            self.report({"WARNING"}, f"Camera found but could not be selected: {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}


class CAMERAOUTPUT_OT_render_profile(Operator):
    bl_idname = "camera_output.render_profile"
    bl_label = "Render This Profile"
    bl_description = "Render this camera output profile only"
    bl_options = {"REGISTER"}

    camera_name: StringProperty(name="Camera")

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        camera = _camera_by_name(scene, self.camera_name)
        if camera is None:
            self.report({"ERROR"}, "Camera not found.")
            return {"CANCELLED"}

        result = validation.validate_scene(
            scene,
            cameras=[camera],
            include_disabled=True,
            store=True,
        )
        if result.has_critical:
            self.report({"ERROR"}, result.summary())
            return {"CANCELLED"}

        try:
            output_path = render_manager.render_profile(scene, camera)
        except render_manager.RenderProfileError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Rendered {camera.name}: {output_path.name}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_render_enabled(Operator):
    bl_idname = "camera_output.render_enabled"
    bl_label = "Render Enabled Profiles"
    bl_description = "Validate and render every enabled camera output profile"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        now = datetime.now()
        validation_result = validation.validate_scene(scene, store=True, now=now)
        if validation_result.has_critical:
            self.report({"ERROR"}, f"Render cancelled: {validation_result.summary()}")
            return {"CANCELLED"}

        all_cameras = validation.iter_scene_cameras(scene)
        enabled_cameras = [
            camera for camera in all_cameras if camera.camera_output_profile.enabled
        ]
        if not enabled_cameras:
            self.report({"WARNING"}, "No enabled camera profiles to render.")
            return {"CANCELLED"}

        batch_result = render_manager.BatchRenderResult()
        for camera in all_cameras:
            if not camera.camera_output_profile.enabled:
                batch_result.skipped.append(
                    render_manager.SkippedProfile(camera.name, "Profile disabled")
                )

        for camera in enabled_cameras:
            try:
                output_path = render_manager.render_profile(scene, camera, now=now)
                batch_result.rendered.append(
                    render_manager.RenderedProfile(camera.name, output_path)
                )
            except render_manager.RenderProfileError as exc:
                message = str(exc)
                batch_result.skipped.append(
                    render_manager.SkippedProfile(camera.name, message)
                )
                self.report({"WARNING"}, message)

        try:
            base_path = utils.resolve_output_base(scene.render.filepath, bpy.path.abspath)
            base_path.mkdir(parents=True, exist_ok=True)
            batch_result.report_path = render_manager.write_markdown_report(
                scene,
                batch_result,
                validation_result,
                base_path=base_path,
            )
        except OSError as exc:
            batch_result.warnings.append(f"Could not write Markdown report: {exc}")
            self.report({"WARNING"}, f"Could not write Markdown report: {exc}")
        except ValueError as exc:
            batch_result.warnings.append(str(exc))
            self.report({"WARNING"}, str(exc))

        if not batch_result.rendered:
            print(
                "[Camera Output Profiles] Batch failed: "
                f"0 rendered, {len(batch_result.skipped)} skipped."
            )
            self.report({"ERROR"}, "All enabled camera profile renders failed.")
            return {"CANCELLED"}

        print(
            "[Camera Output Profiles] Batch complete: "
            f"{len(batch_result.rendered)} rendered, "
            f"{len(batch_result.skipped)} skipped."
        )
        report_label = (
            batch_result.report_path.name
            if batch_result.report_path is not None
            else "report unavailable"
        )
        self.report(
            {"INFO"},
            f"Rendered {len(batch_result.rendered)} profiles. Report: {report_label}",
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_open_output_folder(Operator):
    bl_idname = "camera_output.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the active scene output folder"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        try:
            base_path = utils.resolve_output_base(
                context.scene.render.filepath,
                bpy.path.abspath,
            )
            base_path.mkdir(parents=True, exist_ok=True)
        except (ValueError, OSError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        try:
            bpy.ops.wm.path_open(filepath=str(base_path))
        except Exception:
            try:
                webbrowser.open(Path(base_path).as_uri())
            except Exception as exc:
                self.report({"ERROR"}, f"Could not open output folder: {exc}")
                return {"CANCELLED"}

        return {"FINISHED"}


CLASSES = (
    CAMERAOUTPUT_OT_add_profiles,
    CAMERAOUTPUT_OT_enable_all,
    CAMERAOUTPUT_OT_disable_all,
    CAMERAOUTPUT_OT_validate_profiles,
    CAMERAOUTPUT_OT_apply_preset,
    CAMERAOUTPUT_OT_select_camera,
    CAMERAOUTPUT_OT_render_profile,
    CAMERAOUTPUT_OT_render_enabled,
    CAMERAOUTPUT_OT_open_output_folder,
)
