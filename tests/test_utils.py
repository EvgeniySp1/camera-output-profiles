import importlib.util
from pathlib import Path
import unittest


UTILS_PATH = (
    Path(__file__).resolve().parents[1]
    / "camera_output_profiles"
    / "utils.py"
)


def load_utils():
    spec = importlib.util.spec_from_file_location("camera_output_profiles_utils", UTILS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class UtilsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.utils = load_utils()

    def test_sanitize_filename_replaces_invalid_characters_and_spaces(self):
        result = self.utils.sanitize_filename('  Front:  Camera/Shot*  ')
        self.assertEqual(result, "Front_ Camera_Shot_")

    def test_sanitize_filename_uses_fallback_for_empty_name(self):
        self.assertEqual(self.utils.sanitize_filename(" .. "), "camera_output")

    def test_sanitize_subfolder_removes_traversal_segments(self):
        result = self.utils.sanitize_subfolder("../renders/../../social:shots")
        self.assertEqual(result, Path("renders") / "social_shots")

    def test_template_rejects_unknown_tokens(self):
        with self.assertRaises(self.utils.TemplateError):
            self.utils.render_filename_template(
                "{camera}_{unknown}",
                {
                    "camera": "Camera",
                    "width": 1920,
                    "height": 1080,
                    "frame": 1,
                    "format": "png",
                    "date": "2026-06-07",
                    "scene": "Scene",
                },
            )

    def test_template_rejects_malformed_braces(self):
        with self.assertRaises(self.utils.TemplateError):
            self.utils.extract_template_tokens("{camera")

    def test_template_supports_all_documented_tokens(self):
        values = {
            "camera": "Camera Front",
            "width": 1920,
            "height": 1080,
            "frame": 7,
            "format": "png",
            "date": "2026-06-07",
            "scene": "Product Scene",
        }
        result = self.utils.render_filename_template(
            "{scene}_{camera}_{width}x{height}_{frame:04d}_{format}_{date}",
            values,
        )
        self.assertEqual(
            result,
            "Product Scene_Camera Front_1920x1080_0007_png_2026-06-07",
        )

    def test_aspect_ratio_labels_common_profiles(self):
        cases = {
            (1920, 1080): "16:9",
            (2048, 2048): "1:1",
            (2160, 2700): "4:5",
            (1080, 1920): "9:16",
            (1234, 777): "Custom",
        }
        for resolution, expected in cases.items():
            with self.subTest(resolution=resolution):
                self.assertEqual(
                    self.utils.aspect_ratio_label(*resolution),
                    expected,
                )

    def test_build_output_path_uses_sanitized_template_and_extension(self):
        result = self.utils.build_output_path(
            Path("C:/renders"),
            "../camera_profiles",
            "{camera}*{width}x{height}*{frame}",
            {
                "camera": "Front/Camera",
                "width": 1920,
                "height": 1080,
                "frame": 1,
                "format": "png",
                "date": "2026-06-07",
                "scene": "Scene",
            },
            "PNG",
        )
        self.assertEqual(
            result,
            Path("C:/renders/camera_profiles/Front_Camera_1920x1080_1.png"),
        )


if __name__ == "__main__":
    unittest.main()
