"""Blender operators for Camera Output Profiles."""

from datetime import datetime
from pathlib import Path
import webbrowser

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator

from . import camera_tools, render_manager, utils, validation


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

VIEW_PRESET_ITEMS = tuple(
    (identifier, label, f"Place the camera at the {label} view")
    for identifier, (label, _) in camera_tools.VIEW_PRESETS.items()
)

LENS_PRESET_ITEMS = tuple(
    (identifier, label, f"Apply {label} to the selected camera")
    for identifier, (label, _, _) in camera_tools.LENS_PRESETS.items()
)

FRAME_TARGET_ITEMS = (
    ("SELECTED", "Selected Object", "Frame selected non-camera objects"),
    ("COLLECTION", "Active Collection", "Frame the active collection"),
    ("VISIBLE", "All Visible", "Frame all visible non-camera objects"),
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
        profile.output_subfolder = scene.camera_output_default_subfolder
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
            target_objects=[
                obj
                for obj in context.selected_objects
                if getattr(obj, "type", None) != "CAMERA"
            ],
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
        if render_manager.is_render_job_active():
            self.report(
                {"ERROR"},
                "Camera Output Profiles render is already running.",
            )
            return {"CANCELLED"}
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
        message = f"Rendering {camera.name} at {profile.width}x{profile.height} to {output_path}"
        print(f"[Camera Output Profiles] {message}")
        _set_status(context, message)

        try:
            start_result = render_manager.start_visible_render(
                scene,
                camera,
                now=now,
            )
        except render_manager.RenderProfileError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if start_result.fallback_used:
            self.report(
                {"WARNING"},
                "Visible render invocation failed; used fallback render mode.",
            )
        elif "RUNNING_MODAL" in start_result.operator_result:
            self.report({"INFO"}, f"Started visible render: {start_result.output_path}")
        else:
            self.report({"INFO"}, f"Rendered {camera.name}: {start_result.output_path}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_apply_view_preset(Operator):
    bl_idname = "camera_output.apply_view_preset"
    bl_label = "Apply Camera View Preset"
    bl_description = "Place the selected camera around the configured target"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(name="View", items=VIEW_PRESET_ITEMS)

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        try:
            target = camera_tools.apply_view_preset(context, camera, self.preset)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        label = camera_tools.VIEW_PRESETS[self.preset][0]
        self.report(
            {"INFO"},
            f"Applied {label} view preset to {camera.name} around {target.label}",
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_frame_target(Operator):
    bl_idname = "camera_output.frame_target"
    bl_label = "Frame Target"
    bl_description = "Fit target objects into the selected camera frame"
    bl_options = {"REGISTER", "UNDO"}

    target: EnumProperty(name="Target", items=FRAME_TARGET_ITEMS, default="SELECTED")

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        if self.target == "COLLECTION":
            objects = [
                obj for obj in context.collection.all_objects
                if obj is not camera and getattr(obj, "type", None) != "CAMERA"
            ]
            label = "active collection"
        elif self.target == "VISIBLE":
            objects = [
                obj for obj in context.scene.objects
                if obj is not camera
                and getattr(obj, "type", None) != "CAMERA"
                and not getattr(obj, "hide_render", False)
            ]
            label = "all visible objects"
        else:
            objects = [
                obj for obj in context.selected_objects
                if obj is not camera and getattr(obj, "type", None) != "CAMERA"
            ]
            label = "selected object"
        try:
            camera_tools.frame_camera(context, camera, objects)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"Framed {label} in {camera.name} with {context.scene.camera_output_margin:g}% margin",
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_create_target_empty(Operator):
    bl_idname = "camera_output.create_target_empty"
    bl_label = "Create Target Empty"
    bl_description = "Create or update the selected camera's target Empty"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        try:
            empty, target = camera_tools.create_target_empty(context, camera)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Created target empty for {target.label}: {empty.name}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_aim_at_target(Operator):
    bl_idname = "camera_output.aim_at_target"
    bl_label = "Aim Camera at Target"
    bl_description = "Rotate the camera toward its saved target once"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        try:
            camera_tools.aim_at_saved_target(camera)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Aimed {camera.name} at target")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_add_tracking(Operator):
    bl_idname = "camera_output.add_tracking"
    bl_label = "Add Track To Target"
    bl_description = "Add or update the Camera Output Profiles Track To constraint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        try:
            camera_tools.add_tracking(camera)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Added Track To target for {camera.name}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_remove_tracking(Operator):
    bl_idname = "camera_output.remove_tracking"
    bl_label = "Remove Camera Tracking"
    bl_description = "Remove only the tracking constraint created by this add-on"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        if not camera_tools.remove_tracking(camera):
            self.report({"WARNING"}, f"No Camera Output Profiles tracking on {camera.name}")
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"Removed Camera Output Profiles tracking from {camera.name}",
        )
        return {"FINISHED"}


class CAMERAOUTPUT_OT_duplicate_camera_profile(Operator):
    bl_idname = "camera_output.duplicate_camera_profile"
    bl_label = "Duplicate Camera + Profile"
    bl_description = "Duplicate camera data and manually copy its output profile"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        duplicate = camera_tools.duplicate_camera(
            context,
            camera,
            copy_tracking=context.scene.camera_output_copy_tracking,
        )
        self.report({"INFO"}, f"Duplicated {camera.name} with output profile as {duplicate.name}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_create_camera_set(Operator):
    bl_idname = "camera_output.create_camera_set"
    bl_label = "Create Camera Set"
    bl_description = "Create a configured product or social camera set"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            cameras = camera_tools.create_camera_set(context)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Created {len(cameras)} cameras from camera set preset")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_apply_lens_preset(Operator):
    bl_idname = "camera_output.apply_lens_preset"
    bl_label = "Apply Lens Preset"
    bl_description = "Apply a focal length or orthographic preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(name="Lens", items=LENS_PRESET_ITEMS)

    def execute(self, context):
        camera = active_or_selected_camera(context)
        if camera is None:
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        label = camera_tools.apply_lens_preset(context, camera, self.preset)
        self.report({"INFO"}, f"Applied {label} lens preset to {camera.name}")
        return {"FINISHED"}


class CAMERAOUTPUT_OT_render_enabled(Operator):
    bl_idname = "camera_output.render_enabled"
    bl_label = "Deprecated Batch Render"
    bl_description = "Batch rendering is disabled while a visible queue is redesigned"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        self.report(
            {"WARNING"},
            "Batch rendering is temporarily disabled in v0.2.0.",
        )
        return {"CANCELLED"}


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
    CAMERAOUTPUT_OT_apply_view_preset,
    CAMERAOUTPUT_OT_frame_target,
    CAMERAOUTPUT_OT_create_target_empty,
    CAMERAOUTPUT_OT_aim_at_target,
    CAMERAOUTPUT_OT_add_tracking,
    CAMERAOUTPUT_OT_remove_tracking,
    CAMERAOUTPUT_OT_duplicate_camera_profile,
    CAMERAOUTPUT_OT_create_camera_set,
    CAMERAOUTPUT_OT_apply_lens_preset,
    CAMERAOUTPUT_OT_render_enabled,
)
