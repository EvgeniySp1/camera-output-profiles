import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_fake_bpy():
    bpy = types.ModuleType("bpy")
    bpy_props = types.ModuleType("bpy.props")
    bpy_types = types.ModuleType("bpy.types")

    def property_factory(property_name):
        def create_property(*args, **kwargs):
            return ("BLENDER_PROPERTY", property_name, args, kwargs)

        return create_property

    for name in (
        "BoolProperty",
        "CollectionProperty",
        "EnumProperty",
        "IntProperty",
        "PointerProperty",
        "StringProperty",
    ):
        setattr(bpy_props, name, property_factory(name))

    class PropertyGroup:
        pass

    class Operator:
        pass

    class Panel:
        pass

    class Object:
        pass

    class Scene:
        pass

    class Context:
        pass

    bpy_types.PropertyGroup = PropertyGroup
    bpy_types.Operator = Operator
    bpy_types.Panel = Panel
    bpy_types.Object = Object
    bpy_types.Scene = Scene
    bpy_types.Context = Context

    bpy.props = bpy_props
    bpy.types = bpy_types
    bpy.data = types.SimpleNamespace(scenes=[])
    bpy.path = types.SimpleNamespace(abspath=lambda value: value)
    bpy.app = types.SimpleNamespace(version_string="Fake Blender")
    bpy.ops = types.SimpleNamespace()
    bpy.utils = types.SimpleNamespace(
        register_class=lambda cls: None,
        unregister_class=lambda cls: None,
    )

    sys.modules["bpy"] = bpy
    sys.modules["bpy.props"] = bpy_props
    sys.modules["bpy.types"] = bpy_types
    return bpy


class BlenderImportSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_path = list(sys.path)
        sys.path.insert(0, str(ROOT))
        cls.bpy = install_fake_bpy()
        cls.addon = importlib.import_module("camera_output_profiles")

    @classmethod
    def tearDownClass(cls):
        sys.path[:] = cls.original_path
        for module_name in list(sys.modules):
            if module_name == "bpy" or module_name.startswith("bpy."):
                sys.modules.pop(module_name, None)
            if module_name == "camera_output_profiles" or module_name.startswith(
                "camera_output_profiles."
            ):
                sys.modules.pop(module_name, None)

    def test_blender_property_annotations_are_evaluated(self):
        profile_class = self.addon.properties.CameraOutputProfile
        enabled_property = profile_class.__annotations__["enabled"]
        self.assertIsInstance(enabled_property, tuple)
        self.assertEqual(enabled_property[:2], ("BLENDER_PROPERTY", "BoolProperty"))

        operator_class = self.addon.operators.CAMERAOUTPUT_OT_render_profile
        camera_name_property = operator_class.__annotations__["camera_name"]
        self.assertIsInstance(camera_name_property, tuple)
        self.assertEqual(
            camera_name_property[:2],
            ("BLENDER_PROPERTY", "StringProperty"),
        )

    def test_register_and_unregister_complete_with_fake_bpy(self):
        self.addon.register()
        self.assertTrue(hasattr(self.bpy.types.Object, "camera_output_profile"))
        self.assertTrue(
            hasattr(self.bpy.types.Scene, "camera_output_validation_results")
        )
        self.addon.unregister()
        self.assertFalse(hasattr(self.bpy.types.Object, "camera_output_profile"))

    def test_validation_detects_duplicate_final_output_paths(self):
        class ObjectCollection(list):
            def get(self, name):
                return next((item for item in self if item.name == name), None)

        class ValidationCollection(list):
            def add(self):
                item = types.SimpleNamespace(
                    severity="INFO",
                    message="",
                    camera_name="",
                )
                self.append(item)
                return item

        def profile():
            return types.SimpleNamespace(
                enabled=True,
                width=1920,
                height=1080,
                filename_template="same_name",
                file_format="PNG",
                color_mode="RGBA",
                use_current_frame=True,
                frame=1,
                output_subfolder="camera_profiles",
            )

        cameras = ObjectCollection(
            [
                types.SimpleNamespace(
                    name="Camera_A",
                    type="CAMERA",
                    data=object(),
                    camera_output_profile=profile(),
                ),
                types.SimpleNamespace(
                    name="Camera_B",
                    type="CAMERA",
                    data=object(),
                    camera_output_profile=profile(),
                ),
            ]
        )
        enum_items = [
            types.SimpleNamespace(identifier="PNG"),
            types.SimpleNamespace(identifier="JPEG"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            scene = types.SimpleNamespace(
                name="Scene",
                objects=cameras,
                frame_current=1,
                frame_start=1,
                frame_end=250,
                render=types.SimpleNamespace(
                    filepath=temp_dir,
                    image_settings=types.SimpleNamespace(
                        bl_rna=types.SimpleNamespace(
                            properties={
                                "file_format": types.SimpleNamespace(
                                    enum_items=enum_items
                                )
                            }
                        )
                    ),
                ),
                camera_output_validation_results=ValidationCollection(),
                camera_output_validation_summary="",
                camera_output_validation_critical_count=0,
                camera_output_validation_warning_count=0,
                camera_output_validation_info_count=0,
                camera_output_validation_timestamp="",
            )
            result = self.addon.operators.validation.validate_scene(scene)

        self.assertTrue(result.has_critical)
        self.assertTrue(
            any("Duplicate output filename" in item.message for item in result.messages)
        )

    def test_render_profile_restores_scene_settings(self):
        image_settings = types.SimpleNamespace(
            file_format="PNG",
            color_mode="RGBA",
            quality=75,
        )
        render = types.SimpleNamespace(
            resolution_x=640,
            resolution_y=480,
            resolution_percentage=50,
            filepath="//original",
            use_file_extension=True,
            image_settings=image_settings,
            film_transparent=False,
        )
        original_camera = types.SimpleNamespace(name="Original")
        profile = types.SimpleNamespace(
            enabled=True,
            width=1080,
            height=1920,
            file_format="JPEG",
            color_mode="RGBA",
            quality=90,
            transparent_background=True,
            output_subfolder="camera_profiles",
            filename_template="{camera}_{frame}",
            use_current_frame=False,
            frame=12,
        )
        camera = types.SimpleNamespace(
            name="Camera_Vertical",
            type="CAMERA",
            data=object(),
            camera_output_profile=profile,
        )
        scene = types.SimpleNamespace(
            name="Scene",
            camera=original_camera,
            render=render,
            frame_current=3,
        )

        def frame_set(value):
            scene.frame_current = value

        scene.frame_set = frame_set

        with tempfile.TemporaryDirectory() as temp_dir:
            render.filepath = temp_dir
            original_filepath = render.filepath
            self.bpy.path.abspath = lambda value: value

            def fake_render(**kwargs):
                Path(scene.render.filepath).write_text("render", encoding="utf-8")
                return {"FINISHED"}

            self.bpy.ops.render = types.SimpleNamespace(render=fake_render)
            output_path = self.addon.render_manager.render_profile(scene, camera)

            self.assertTrue(output_path.exists())

        self.assertIs(scene.camera, original_camera)
        self.assertEqual(render.resolution_x, 640)
        self.assertEqual(render.resolution_y, 480)
        self.assertEqual(render.resolution_percentage, 50)
        self.assertEqual(render.filepath, original_filepath)
        self.assertTrue(render.use_file_extension)
        self.assertEqual(image_settings.file_format, "PNG")
        self.assertEqual(image_settings.color_mode, "RGBA")
        self.assertEqual(image_settings.quality, 75)
        self.assertFalse(render.film_transparent)
        self.assertEqual(scene.frame_current, 3)


if __name__ == "__main__":
    unittest.main()
