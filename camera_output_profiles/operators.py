"""Blender operators for Camera Output Profiles."""

from datetime import datetime
from pathlib import Path
import webbrowser

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator

from . import render_manager, utils, validation


DEFAULT_FILENAME_TEMPLATE = "{camera}_{width}x{height}_{frame}"
LEGACY_FILENAME_TEMPLATE = "{camera}*{width}x{height}*{frame}"

PRESETS = {
    "FHD_16_9": ("FHD 16:9", 1920, 1080),
    "UHD_16_9": ("4K 16:9", 3840, 2160),
    "SQUARE": ("Square", 2048, 2048),
    "PORTRAIT_4_5": ("Portrait 4:5", 2160, 2700),
    "VERTICAL_9_16": ("Vertical 9:16", 1080, 1920),
    "THUMBNAIL_16_9": ("Thumbnail 16:9", 1280, 720),
}

PRESET_ITEMS = tuple(
    (identifier, label, f"Set the camera profile to {width} x {height}")
    for identifier, (label, width, height) in PRESETS.items()
)


def active_or_selected_camera(context: bpy.types.Context) -> bpy.types.Object | None:
    active = getattr(context, "object", None)
    if active is not None and getattr(active, "type", None) == "CAMERA":
        return active
    for obj in getattr(context, "selected_objects", ()):
        if getattr(obj, "type", None) == "CAMERA":
            return obj
    scene_camera = getattr(getattr(context, "scene", None), "camera", None)
    if scene_camera is not None and getattr(scene_camera, "type", None) == "CAMERA":
        return scene_camera
    return None


def _camera_by_name(scene: bpy.types.Scene, camera_name: str) -> bpy.types.Object | None:
    camera = scene.objects.get(camera_name)
    if camera is not None and getattr(camera, "type", None) == "CAMERA":
        return camera
    return None


def _resolve_camera(
    context: bpy.types.Context,
    camera_name: str = "",
) -> bpy.types.Object | None:
    if camera_name:
        return _camera_by_name(context.scene, camera_name)
    return active_or_selected_camera(context)


def _initialize_camera_profile(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    *,
    force_frame: bool = False,
) -> None:
    profile = camera.camera_output_profile
    if force_frame or not profile.initialized:
        profile.frame = scene.frame_current
    if profile.filename_template == LEGACY_FILENAME_TEMPLATE:
        profile.filename_template = DEFAULT_FILENAME_TEMPLATE
    profile.initialized = True


def _set_status(context: bpy.types.Context, message: str | None) -> None:
    workspace = getattr(context, "workspace", None)
    if workspace is None:
        return
    try:
        workspace.status_text_set(message)
    except Exception:
        pass


def _open_folder(operator: Operator, folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        operator.report({"ERROR"}, f"Could not create output folder: {exc}")
        return False

    try:
        result = bpy.ops.wm.path_open(filepath=str(folder))
        if "FINISHED" in result:
            return True
    except Exception:
        pass

    try:
        opened = bool(webbrowser.open(folder.as_uri()))
        if not opened:
            operator.report({"ERROR"}, f"Could not open output folder: {folder}")
        return opened
    except Exception as exc:
        operator.report({"ERROR"}, f"Could not open output folder: {exc}")
        return False


class CAMERAOUTPUT_OT_add_profiles(Operator):
    bl_idname = "camera_output.add_profiles"
    bl_label = "Add / Refresh Camera Profiles"
    bl_description = "Initialize profiles and refresh legacy defaults for all cameras"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        cameras = validation.iter_scene_cameras(scene)
        if not cameras:
            self.report({"WARNING"}, "No cameras found in this scene.")
            return {"CANCELLED"}

        for camera in cameras:
            _initialize_camera_profile(scene, camera)

        self.report({"INFO"}, f"Added or refreshed {len(cameras)} camera profiles.")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_enable_all(Operator):
    bl_idname = "camera_output.enable_all"
    bl_label = "Enable All Profiles"
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
    bl_label = "Disable All Profiles"
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
        result = validation.validate_scene(
            context.scene,
            store=True,
            selected_camera=active_or_selected_camera(context),
        )
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
    bl_description = "Change only the active camera profile; Scene Output stays unchanged"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(name="Preset", items=PRESET_ITEMS)

    def execute(self, context: bpy.types.Context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}

        _, width, height = PRESETS[self.preset]
        profile = camera.camera_output_profile
        _initialize_camera_profile(context.scene, camera)
        profile.width = width
        profile.height = height
        self.report(
            {"INFO"},
            (
                f"Applied {width}x{height} preset to {camera.name} profile. "
                "Scene Output unchanged."
            ),
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_select_camera(Operator):
    bl_idname = "camera_output.select_camera"
    bl_label = "Select"
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


class CAMERAOUTPUT_OT_apply_profile_to_scene(Operator):
    bl_idname = "camera_output.apply_profile_to_scene"
    bl_label = "Apply Profile to Scene Output"
    bl_description = "Copy the selected camera profile into Blender's Output settings"
    bl_options = {"REGISTER", "UNDO"}

    camera_name: StringProperty(name="Camera", default="")

    def execute(self, context: bpy.types.Context):
        camera = _resolve_camera(context, self.camera_name)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}

        profile = camera.camera_output_profile
        try:
            render_manager.apply_profile_to_scene_output(context.scene, profile)
        except Exception as exc:
            self.report(
                {"ERROR"},
                f"Could not apply {camera.name} profile to Scene Output: {exc}",
            )
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            (
                f"Applied {camera.name} profile to Scene Output: "
                f"{profile.width}x{profile.height} {profile.file_format}"
            ),
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_choose_base_output_folder(Operator):
    bl_idname = "camera_output.choose_base_output_folder"
    bl_label = "Choose Base Output Folder"
    bl_description = "Choose the base folder used by all camera profiles"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(name="Base Output Folder", subtype="DIR_PATH")
    filter_folder: BoolProperty(default=True, options={"HIDDEN"})

    def invoke(self, context: bpy.types.Context, event):
        try:
            self.directory = str(
                utils.resolve_output_base(
                    context.scene.render.filepath,
                    bpy.path.abspath,
                )
            )
        except ValueError:
            self.directory = bpy.path.abspath("//")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context):
        if not self.directory.strip():
            self.report({"ERROR"}, "Choose a valid Base Output Folder.")
            return {"CANCELLED"}
        context.scene.render.filepath = self.directory
        self.report({"INFO"}, f"Base Output Folder: {self.directory}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_open_output_folder(Operator):
    bl_idname = "camera_output.open_output_folder"
    bl_label = "Open Base Output Folder"
    bl_description = "Open the Base Output Folder"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        try:
            base_path = utils.resolve_output_base(
                context.scene.render.filepath,
                bpy.path.abspath,
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"} if _open_folder(self, base_path) else {"CANCELLED"}


class CAMERAOUTPUT_OT_open_final_output_folder(Operator):
    bl_idname = "camera_output.open_final_output_folder"
    bl_label = "Open Final Output Folder"
    bl_description = "Open the folder for the selected camera's final render path"
    bl_options = {"REGISTER"}

    camera_name: StringProperty(name="Camera", default="")

    def execute(self, context: bpy.types.Context):
        camera = _resolve_camera(context, self.camera_name)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        try:
            output_path = render_manager.output_path_for_profile(context.scene, camera)
        except (ValueError, utils.TemplateError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return (
            {"FINISHED"}
            if _open_folder(self, output_path.parent)
            else {"CANCELLED"}
        )


class CAMERAOUTPUT_OT_render_profile(Operator):
    bl_idname = "camera_output.render_profile"
    bl_label = "Render This Profile"
    bl_description = "Render one still using this camera profile"
    bl_options = {"REGISTER"}

    camera_name: StringProperty(name="Camera", default="")

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        camera = _resolve_camera(context, self.camera_name)
        if camera is None:
            self.report({"ERROR"}, "Camera not found.")
            return {"CANCELLED"}

        result = validation.validate_scene(
            scene,
            cameras=[camera],
            include_disabled=True,
            store=True,
            selected_camera=camera,
        )
        if result.has_critical:
            self.report({"ERROR"}, f"Render cancelled: {result.summary()}")
            return {"CANCELLED"}

        now = datetime.now()
        try:
            output_path = render_manager.output_path_for_profile(
                scene,
                camera,
                now=now,
            )
        except (ValueError, utils.TemplateError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        profile = camera.camera_output_profile
        message = (
            f"Rendering {camera.name} at {profile.width}x{profile.height} "
            f"to {output_path}"
        )
        print(f"[Camera Output Profiles] {message}")
        self.report({"INFO"}, message)
        _set_status(context, message)

        try:
            rendered_path = render_manager.render_profile(
                scene,
                camera,
                now=now,
                restore_scene_output=scene.camera_output_restore_scene_output,
                show_render_window=scene.camera_output_show_render_window,
            )
        except render_manager.RenderProfileError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        finally:
            _set_status(context, None)

        if scene.camera_output_open_folder_after_render:
            _open_folder(self, rendered_path.parent)

        self.report(
            {"INFO"},
            f"Rendered {camera.name} profile: {rendered_path}",
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_render_enabled(Operator):
    bl_idname = "camera_output.render_enabled"
    bl_label = "Render All Enabled Profiles"
    bl_description = "Validate and render every enabled camera output profile"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        now = datetime.now()
        selected_camera = active_or_selected_camera(context)
        validation_result = validation.validate_scene(
            scene,
            store=True,
            now=now,
            selected_camera=selected_camera,
        )
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

        try:
            base_path = utils.resolve_output_base(
                scene.render.filepath,
                bpy.path.abspath,
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        batch_result = render_manager.BatchRenderResult()
        for camera in all_cameras:
            if not camera.camera_output_profile.enabled:
                batch_result.skipped.append(
                    render_manager.SkippedProfile(camera.name, "Profile disabled")
                )

        total = len(enabled_cameras)
        for index, camera in enumerate(enabled_cameras, start=1):
            profile = camera.camera_output_profile
            progress = (
                f"Rendering {index}/{total}: {camera.name} "
                f"{profile.width}x{profile.height}"
            )
            print(f"[Camera Output Profiles] {progress}")
            self.report({"INFO"}, progress)
            _set_status(context, progress)
            try:
                output_path = render_manager.render_profile(
                    scene,
                    camera,
                    now=now,
                    base_path=base_path,
                    restore_scene_output=scene.camera_output_restore_scene_output,
                    show_render_window=False,
                )
                batch_result.rendered.append(
                    render_manager.RenderedProfile(
                        camera.name,
                        output_path,
                        profile.width,
                        profile.height,
                        profile.file_format,
                    )
                )
            except render_manager.RenderProfileError as exc:
                message = str(exc)
                batch_result.skipped.append(
                    render_manager.SkippedProfile(camera.name, message)
                )
                batch_result.errors.append(message)
                self.report({"WARNING"}, message)

        _set_status(context, None)

        try:
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

        if not batch_result.rendered:
            print(
                "[Camera Output Profiles] Batch failed: "
                f"0 rendered, {len(batch_result.skipped)} skipped."
            )
            self.report({"ERROR"}, "All enabled camera profile renders failed.")
            return {"CANCELLED"}

        if scene.camera_output_show_render_window:
            render_manager.show_render_result()
        if scene.camera_output_open_folder_after_render:
            _open_folder(self, base_path)

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
            (
                f"Rendered {len(batch_result.rendered)} profiles. "
                f"Report: {report_label}"
            ),
        )
        return {"FINISHED"}


CLASSES = (
    CAMERAOUTPUT_OT_add_profiles,
    CAMERAOUTPUT_OT_enable_all,
    CAMERAOUTPUT_OT_disable_all,
    CAMERAOUTPUT_OT_validate_profiles,
    CAMERAOUTPUT_OT_apply_preset,
    CAMERAOUTPUT_OT_select_camera,
    CAMERAOUTPUT_OT_apply_profile_to_scene,
    CAMERAOUTPUT_OT_choose_base_output_folder,
    CAMERAOUTPUT_OT_open_output_folder,
    CAMERAOUTPUT_OT_open_final_output_folder,
    CAMERAOUTPUT_OT_render_profile,
    CAMERAOUTPUT_OT_render_enabled,
)
