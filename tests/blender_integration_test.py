"""Run with Blender in background mode to verify the add-on end to end."""

from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import camera_output_profiles
from camera_output_profiles import render_manager, validation


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def point_at(obj, target=(0.0, 0.0, 0.0)) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(name: str, location: tuple[float, float, float]):
    camera_data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    point_at(camera)
    return camera


def configure_profile(
    camera,
    *,
    width: int,
    height: int,
    file_format: str,
) -> None:
    profile = camera.camera_output_profile
    profile.initialized = True
    profile.enabled = True
    profile.width = width
    profile.height = height
    profile.file_format = file_format
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

    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
    bpy.ops.object.light_add(type="AREA", location=(4.0, -4.0, 6.0))
    light = bpy.context.object
    light.data.energy = 1000.0
    light.data.shape = "DISK"
    light.data.size = 5.0
    point_at(light)

    camera_front = add_camera("Camera_Front", (6.0, -6.0, 4.5))
    camera_square = add_camera("Camera_Square", (5.0, -5.0, 5.0))
    camera_vertical = add_camera("Camera_Vertical", (4.5, -4.5, 3.5))

    assert (
        camera_front.camera_output_profile.filename_template
        == "{camera}_{width}x{height}_{frame}"
    )
    assert scene.camera_output_show_render_window is True
    assert scene.camera_output_open_folder_after_render is False
    assert scene.camera_output_restore_scene_output is True

    configure_profile(
        camera_front,
        width=1920,
        height=1080,
        file_format="PNG",
    )
    configure_profile(
        camera_square,
        width=2048,
        height=2048,
        file_format="PNG",
    )
    configure_profile(
        camera_vertical,
        width=1080,
        height=1920,
        file_format="JPEG",
    )

    scene.camera = camera_front
    camera_front.select_set(True)
    bpy.context.view_layer.objects.active = camera_front
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    preset_result = bpy.ops.camera_output.apply_preset(preset="UHD_16_9")
    assert preset_result == {"FINISHED"}, preset_result
    assert camera_front.camera_output_profile.width == 3840
    assert camera_front.camera_output_profile.height == 2160
    assert scene.render.resolution_x == 1920
    assert scene.render.resolution_y == 1080

    apply_result = bpy.ops.camera_output.apply_profile_to_scene(
        camera_name=camera_front.name
    )
    assert apply_result == {"FINISHED"}, apply_result
    assert scene.render.resolution_x == 3840
    assert scene.render.resolution_y == 2160
    assert scene.render.resolution_percentage == 100

    camera_front.camera_output_profile.width = 1920
    camera_front.camera_output_profile.height = 1080

    with tempfile.TemporaryDirectory(prefix="camera-output-profiles-") as temp_dir:
        scene.render.filepath = temp_dir
        scene.camera = camera_front
        scene.render.resolution_x = 640
        scene.render.resolution_y = 480
        scene.render.resolution_percentage = 75
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.quality = 82
        scene.render.film_transparent = False
        scene.frame_set(5)

        original = render_manager.capture_scene_settings(scene)
        front_preview = render_manager.output_path_for_profile(scene, camera_front)
        assert front_preview == (
            Path(temp_dir)
            / "camera_profiles"
            / "Camera_Front_1920x1080_5.png"
        )
        operator_result = bpy.ops.camera_output.render_enabled()
        assert operator_result == {"FINISHED"}, operator_result

        expected = {
            Path(temp_dir)
            / "camera_profiles"
            / "Camera_Front_1920x1080_5.png": (1920, 1080),
            Path(temp_dir)
            / "camera_profiles"
            / "Camera_Square_2048x2048_5.png": (2048, 2048),
            Path(temp_dir)
            / "camera_profiles"
            / "Camera_Vertical_1080x1920_5.jpg": (1080, 1920),
        }
        for output_path, expected_size in expected.items():
            assert output_path.exists(), output_path
            assert image_size(output_path) == expected_size, output_path

        report_path = Path(temp_dir) / render_manager.REPORT_FILENAME
        assert report_path.exists(), report_path
        report_text = report_path.read_text(encoding="utf-8")
        assert "Camera_Front" in report_text
        assert "Camera_Square" in report_text
        assert "Camera_Vertical" in report_text
        assert "1920 x 1080" in report_text
        assert "2048 x 2048" in report_text
        assert "1080 x 1920" in report_text
        assert str(Path(temp_dir)) in report_text

        restored = render_manager.capture_scene_settings(scene)
        assert restored == original, (original, restored)

        camera_front.camera_output_profile.filename_template = "duplicate"
        camera_square.camera_output_profile.filename_template = "duplicate"
        duplicate_result = validation.validate_scene(scene)
        assert duplicate_result.has_critical
        assert any(
            "Duplicate output filename" in item.message
            for item in duplicate_result.messages
        )

        camera_square.camera_output_profile.filename_template = ""
        empty_result = validation.validate_scene(scene)
        assert empty_result.has_critical
        assert any(
            item.camera_name == "Camera_Square"
            and "Filename template is empty" in item.message
            for item in empty_result.messages
        )

        camera_square.camera_output_profile.filename_template = "../{camera}"
        traversal_result = validation.validate_scene(scene)
        assert traversal_result.has_critical
        assert any(
            "path separators or path traversal" in item.message
            for item in traversal_result.messages
        )

    camera_output_profiles.unregister()
    print("BLENDER_INTEGRATION_TEST_OK")


if __name__ == "__main__":
    main()
