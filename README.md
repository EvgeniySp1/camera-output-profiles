# Camera Output Profiles

Open-source Blender add-on for per-camera render resolution, aspect ratio, file naming, and output profiles.

> Development version: v0.1.2, unreleased. Test locally before publishing.

## How It Works

Camera Output Profiles stores output settings per camera. Blender itself stores render resolution globally per scene, not per camera. Therefore presets update the selected camera profile, not Blender's global Output panel. When rendering through the add-on, the profile is applied temporarily. Use **Apply Profile to Scene Output** if you want Blender's Format panel to match the selected profile.

This separation is intentional:

- Presets edit only the selected camera profile.
- Blender's native **Output > Format** remains unchanged.
- Add-on rendering temporarily applies the profile.
- Original Scene Output settings are restored by default.
- Manual synchronization happens only through **Apply Profile to Scene Output**.

## Features

- Per-camera width, height, format, color mode, quality, transparency, frame, subfolder, and filename template
- PNG and JPEG output, plus WebP when supported by the installed Blender build
- FHD, 4K, square, portrait, vertical, and thumbnail presets
- Full **Final Render Path** preview for the selected camera
- Explicit **Render This Profile** and **Render All Enabled Profiles** actions
- Optional Render Result window and automatic output-folder opening
- Manual **Apply Profile to Scene Output** action
- Validation for paths, frames, formats, templates, duplicate outputs, and overwrite risk
- Automatic scene restoration through `try/finally`
- Markdown batch report at `CAMERA_OUTPUT_PROFILES_REPORT.md`
- Compact quick-workflow N-panel
- Full profile editing in Camera Data Properties
- Global settings in Output Properties

## Installation

1. Download or archive the local project.
2. Ensure the ZIP contains `camera_output_profiles/` at its root.
3. Open Blender.
4. Go to **Edit -> Preferences -> Add-ons -> Install from Disk**.
5. Select the ZIP.
6. Enable **Camera Output Profiles**.

For local testing, reinstall the ZIP after code changes or temporarily add the repository package to Blender's scripts/add-ons directory.

## Quick Start

1. Select a camera.
2. Open **N-panel > Cam Output**.
3. Expand **Camera List** and click **Add / Refresh Camera Profiles**.
4. Choose a preset, for example **4K 16:9**.
5. Check **Final Render Path**.
6. Click **Render This Profile**.
7. Find the output in the shown folder.

The 4K preset changes the selected camera profile to 3840 x 2160. Blender's native Scene Output may remain 1920 x 1080 until **Apply Profile to Scene Output** is clicked.

## UI Locations

- **3D Viewport > N-panel > Cam Output**: selected-camera summary, presets, final path, render/apply actions, batch render, validation, collapsed Camera List, and collapsed Help.
- **Properties > Camera Data > Camera Output Profile**: complete profile editor for the selected camera.
- **Properties > Output > Camera Output Profiles Settings**: Base Output Folder, default subfolder, render behavior, validation status, and Markdown report setting.

## Output Paths

The final path combines:

1. **Base Output Folder** from `scene.render.filepath`
2. Optional per-camera **Output Subfolder**
3. Expanded **Filename Template**
4. Image format extension

Example:

```text
C:\tmp\camera_profiles\Camera_3840x2160_0001.png
```

Leave **Output Subfolder** empty to save directly into the Base Output Folder.

## Filename Tokens

Default template:

```text
{camera}_{width}x{height}_{frame}
```

Supported tokens:

| Token | Value |
| --- | --- |
| `{camera}` | Camera object name |
| `{scene}` | Scene name |
| `{width}` | Profile width |
| `{height}` | Profile height |
| `{frame}` | Rendered frame |
| `{format}` | Lowercase image format |
| `{date}` | Current date as `YYYY-MM-DD` |

Invalid filesystem characters are sanitized. Path separators and traversal such as `../` are rejected.

## Render Behavior

- **Show Render Window**: shows Blender's Render Result after a single render, or after batch completion, when Blender runs with a UI.
- **Open Output Folder After Render**: opens the relevant output folder after success.
- **Restore Scene Output After Render**: restores the original resolution, format, quality, transparency, camera, frame, and output path. When disabled, profile format settings remain applied while the original camera, frame, and Base Output Folder are preserved.

## Validation

Critical errors block rendering:

- Missing cameras or invalid Base Output Folder
- Invalid dimensions
- Empty or malformed filename template
- Unsupported filename token
- Path traversal
- Unsupported image format
- Duplicate final output paths
- Custom frame outside the scene range

Warnings do not block rendering:

- Scene Output differs from the selected profile
- Empty Output Subfolder
- Existing file may be overwritten
- JPEG profile requests RGBA

## Limitations

- v0.1.2 still renders still images only.
- Animation frame-range profiles are planned.
- Render engine and sample overrides are planned.
- WebP depends on the installed Blender build.
- v0.1.2 must be manually verified in Blender 5.1.2 before release.

## Testing

Standard-library tests:

```powershell
python -m unittest discover -s tests -v
```

Available Blender integration test:

```powershell
blender --background --factory-startup --python tests/blender_integration_test.py
```

The integration scene uses:

- `Camera_Front`: 1920 x 1080 PNG
- `Camera_Square`: 2048 x 2048 PNG
- `Camera_Vertical`: 1080 x 1920 JPEG

See [docs/TESTING.md](docs/TESTING.md) for the exact Blender 5.1.2 manual checklist.

## Contributing

Issues and pull requests are welcome after local Blender verification. Keep runtime code limited to Python's standard library and Blender's `bpy` API.

## License

MIT License. See [LICENSE](LICENSE).
