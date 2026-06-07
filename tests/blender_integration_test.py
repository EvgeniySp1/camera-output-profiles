"""Run with Blender in background mode to verify v0.2.0 end to end."""

from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import camera_output_profiles
from camera_output_profiles import camera_tools, render_manager


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def add_camera(name: str, location=(6.0, -6.0, 4.0)):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    camera_tools.safe_look_at(camera, Vector((0.0, 0.0, 0.0)))
    return camera


def select_objects(*objects, active=None) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[-1]


def configure_profile(camera, width=320, height=180) -> None:
    profile = camera.camera_output_profile
    profile.initialized = True
    profile.enabled = True
    profile.width = width
    profile.height = height
    profile.file_format = "PNG"
    profile.color_mode = "RGBA"
    profile.quality = 90
    profile.transparent_background = False
    profile.output_subfolder = "camera_profiles"
    profile.filename_template = "{camera}_{width}x{height}_{frame}"
    profile.use_current_frame = True


def image_size(path: Path) -> tuple[int, int]:
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        return tuple(image.size)
    finally:
        bpy.data.images.remove(image)


def main() -> None:
    camera_output_profiles.register()
    clear_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"

    bpy.ops.mesh.primitive_cube_add(size=2.0)
    cube = bpy.context.object
    cube.name = "Product"
    camera = add_camera("Camera")
    configure_profile(camera)
    scene.camera = camera

    select_objects(cube, camera, active=camera)
    original_resolution = (
        camera.camera_output_profile.width,
        camera.camera_output_profile.height,
    )
    original_location = camera.location.copy()
    result = bpy.ops.camera_output.apply_view_preset(
        preset="THREE_QUARTER_FRONT"
    )
    assert result == {"FINISHED"}, result
    assert (camera.location - original_location).length > 0.1
    assert (
        camera.camera_output_profile.width,
        camera.camera_output_profile.height,
    ) == original_resolution

    result = bpy.ops.camera_output.frame_target(target="SELECTED")
    assert result == {"FINISHED"}, result

    result = bpy.ops.camera_output.create_target_empty()
    assert result == {"FINISHED"}, result
    target = camera.camera_output_profile.tracking_target
    assert target is not None
    assert target.parent is cube

    result = bpy.ops.camera_output.add_tracking()
    assert result == {"FINISHED"}, result
    constraint = camera.constraints.get(camera_tools.TRACK_CONSTRAINT_NAME)
    assert constraint is not None
    assert constraint.target is target

    result = bpy.ops.camera_output.apply_lens_preset(preset="LENS_70")
    assert result == {"FINISHED"}, result
    assert camera.data.type == "PERSP"
    assert camera.data.lens == 70.0
    assert (
        camera.camera_output_profile.width,
        camera.camera_output_profile.height,
    ) == original_resolution

    scene.camera_output_copy_tracking = False
    result = bpy.ops.camera_output.duplicate_camera_profile()
    assert result == {"FINISHED"}, result
    duplicate = bpy.context.object
    assert duplicate is not camera
    assert duplicate.data is not camera.data
    assert duplicate.camera_output_profile.width == camera.camera_output_profile.width
    assert duplicate.camera_output_profile.height == camera.camera_output_profile.height
    assert duplicate.constraints.get(camera_tools.TRACK_CONSTRAINT_NAME) is None

    select_objects(cube, active=cube)
    scene.camera_output_camera_set_type = "PRODUCT_BASIC"
    scene.camera_output_camera_set_add_tracking = True
    existing_camera_names = {obj.name for obj in scene.objects if obj.type == "CAMERA"}
    result = bpy.ops.camera_output.create_camera_set()
    assert result == {"FINISHED"}, result
    new_cameras = [
        obj
        for obj in scene.objects
        if obj.type == "CAMERA" and obj.name not in existing_camera_names
    ]
    assert len(new_cameras) == 4, [obj.name for obj in new_cameras]
    assert all(item.camera_output_profile.initialized for item in new_cameras)
    assert all(
        item.constraints.get(camera_tools.TRACK_CONSTRAINT_NAME) is not None
        for item in new_cameras
    )

    with tempfile.TemporaryDirectory(prefix="camera-output-profiles-v020-") as temp_dir:
        select_objects(camera, active=camera)
        scene.camera = duplicate
        scene.render.filepath = temp_dir
        scene.render.resolution_x = 640
        scene.render.resolution_y = 480
        scene.render.resolution_percentage = 50
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.quality = 80
        scene.render.film_transparent = False
        scene.frame_set(3)
        scene.camera_output_restore_scene_output = True
        scene.camera_output_write_report = True
        scene.camera_output_show_render_window = False

        original = render_manager.capture_scene_settings(scene)
        output_path = render_manager.output_path_for_profile(scene, camera)
        result = bpy.ops.camera_output.render_profile(camera_name=camera.name)
        assert result == {"FINISHED"}, result
        assert not render_manager.is_render_job_active()
        assert output_path.exists(), output_path
        assert image_size(output_path) == (320, 180)
        assert render_manager.capture_scene_settings(scene) == original
        assert (output_path.parent / render_manager.REPORT_FILENAME).exists()

        batch_result = bpy.ops.camera_output.render_enabled()
        assert batch_result == {"CANCELLED"}, batch_result

    result = bpy.ops.camera_output.remove_tracking()
    assert result == {"FINISHED"}, result
    assert camera.constraints.get(camera_tools.TRACK_CONSTRAINT_NAME) is None

    camera_output_profiles.unregister()
    print("BLENDER_INTEGRATION_TEST_OK")


if __name__ == "__main__":
    main()
