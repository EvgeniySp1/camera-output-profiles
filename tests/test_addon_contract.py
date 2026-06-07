import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "camera_output_profiles"


def assignment_value(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"Assignment {name!r} was not found")


class AddonContractTests(unittest.TestCase):
    def test_required_python_modules_exist_and_parse(self):
        module_names = {
            "__init__.py",
            "properties.py",
            "ui.py",
            "operators.py",
            "render_manager.py",
            "validation.py",
            "utils.py",
        }
        self.assertEqual(
            {path.name for path in PACKAGE.glob("*.py")},
            module_names,
        )
        for module_name in module_names:
            source = (PACKAGE / module_name).read_text(encoding="utf-8")
            ast.parse(source, filename=module_name)

    def test_bl_info_matches_release_metadata(self):
        module = ast.parse((PACKAGE / "__init__.py").read_text(encoding="utf-8"))
        bl_info = assignment_value(module, "bl_info")
        self.assertEqual(bl_info["name"], "Camera Output Profiles")
        self.assertEqual(bl_info["version"], (0, 1, 1))
        self.assertEqual(bl_info["blender"], (4, 2, 0))
        self.assertEqual(bl_info["category"], "Render")
        self.assertEqual(bl_info["location"], "View3D > Sidebar > Cam Output")

    def test_required_operator_ids_are_present(self):
        source = (PACKAGE / "operators.py").read_text(encoding="utf-8")
        required_ids = {
            "camera_output.add_profiles",
            "camera_output.enable_all",
            "camera_output.disable_all",
            "camera_output.validate_profiles",
            "camera_output.render_enabled",
            "camera_output.render_profile",
            "camera_output.apply_preset",
            "camera_output.select_camera",
            "camera_output.open_output_folder",
            "camera_output.choose_base_output_folder",
            "camera_output.open_final_output_folder",
            "camera_output.apply_profile_to_scene",
        }
        for operator_id in required_ids:
            with self.subTest(operator_id=operator_id):
                self.assertIn(f'"{operator_id}"', source)

    def test_panel_location_matches_requirements(self):
        source = (PACKAGE / "ui.py").read_text(encoding="utf-8")
        self.assertIn('bl_space_type = "VIEW_3D"', source)
        self.assertIn('bl_region_type = "UI"', source)
        self.assertIn('bl_category = "Cam Output"', source)
        self.assertIn('bl_label = "Camera Output Profiles"', source)
        for label in (
            "Camera Output Profiles v0.1.1",
            "Camera profiles are separate from Blender",
            "Base Output Folder",
            "Choose Base Output Folder",
            "Open Base Output Folder",
            "Render All Enabled Profiles",
            "Selected Camera Profile:",
            "Final Render Path",
            "Render This Profile",
            "Apply Profile to Scene Output",
            "Open Final Output Folder",
            "Output Subfolder",
            "Tokens: {camera}, {scene}, {width}, {height}, {frame}, {format}, {date}",
            "Select",
            "Render",
        ):
            with self.subTest(label=label):
                self.assertIn(label, source)

    def test_required_project_documentation_exists(self):
        required_files = {
            ROOT / "README.md",
            ROOT / "LICENSE",
            ROOT / "CHANGELOG.md",
            ROOT / "RELEASE_NOTES_v0.1.0.md",
            ROOT / "DRAFT_RELEASE_NOTES_v0.1.1.md",
            ROOT / "docs" / "USER_GUIDE.md",
            ROOT / "docs" / "TESTING.md",
            ROOT / "docs" / "ROADMAP.md",
            ROOT / "docs" / "screenshots" / ".gitkeep",
            ROOT / "examples" / ".gitkeep",
            ROOT / ".gitignore",
        }
        for path in required_files:
            with self.subTest(path=path):
                self.assertTrue(path.exists(), f"Missing required file: {path}")

    def test_readme_documents_tokens_limitations_and_manual_test(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for token in (
            "{camera}",
            "{width}",
            "{height}",
            "{frame}",
            "{format}",
            "{date}",
            "{scene}",
        ):
            with self.subTest(token=token):
                self.assertIn(token, readme)
        self.assertIn("still images only", readme)
        self.assertIn("Camera_Front", readme)
        self.assertIn("Camera_Square", readme)
        self.assertIn("Camera_Vertical", readme)
        self.assertIn("Apply Profile to Scene Output", readme)
        self.assertIn("Final Render Path", readme)

    def test_release_documents_match_version(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE_NOTES_v0.1.0.md").read_text(
            encoding="utf-8"
        )
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("0.1.0", changelog)
        self.assertIn("# Camera Output Profiles v0.1.0", release_notes)
        for version in ("v0.2.0", "v0.3.0", "v1.0.0"):
            self.assertIn(version, roadmap)

    def test_v011_documentation_is_unreleased(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        draft_notes = (ROOT / "DRAFT_RELEASE_NOTES_v0.1.1.md").read_text(
            encoding="utf-8"
        )
        testing = (ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
        self.assertIn("v0.1.1", changelog)
        self.assertIn("unreleased", changelog.lower())
        self.assertIn("DRAFT", draft_notes)
        self.assertIn("NOT RELEASED", draft_notes)
        self.assertIn("Blender 5.1.2", testing)
        self.assertIn("Preset changes profile only", testing)


if __name__ == "__main__":
    unittest.main()
