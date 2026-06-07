# Camera Output Profiles

Open-source Blender add-on for per-camera render resolution, aspect ratio, file naming, and output profiles.

Blender stores render output settings at scene level. Camera Output Profiles adds a profile to each camera so one scene can produce widescreen, square, portrait, vertical, and custom still images without repeatedly editing global render settings.

## Features

- Per-camera width, height, format, color mode, quality, transparency, frame, subfolder, and filename template
- PNG and JPEG output, plus WebP when supported by the installed Blender build
- FHD, 4K, square, portrait, vertical, and thumbnail resolution presets
- Validation for invalid profiles, tokens, frames, formats, and duplicate output filenames
- One-click batch rendering for all enabled camera profiles
- Automatic restoration of the original scene camera and render settings
- Markdown render report written to `CAMERA_OUTPUT_PROFILES_REPORT.md`
- Blender 4.2 LTS+ target, with Blender 5.x support where APIs remain compatible

## Installation

1. Download the repository ZIP.
2. In Blender, open **Edit -> Preferences -> Add-ons -> Install** (or **Install from Disk**).
3. Select the ZIP containing the `camera_output_profiles` folder, or select the add-on folder.
4. Enable **Camera Output Profiles**.

For a release ZIP, the archive should contain the `camera_output_profiles/` package at its root.

## Quick Start

1. Open a scene with multiple cameras.
2. Open the 3D Viewport N-panel and select **Cam Output**.
3. Click **Add Profiles for All Cameras**.
4. Select a camera and apply a resolution preset, or enter a custom size.
5. Set the scene render output path.
6. Click **Render Enabled Profiles**.

The add-on treats `Scene > Output > Output Path` as the base output folder. Each profile adds its sanitized subfolder, filename, and image extension.

## Filename Tokens

| Token | Value |
| --- | --- |
| `{camera}` | Camera object name |
| `{width}` | Profile width |
| `{height}` | Profile height |
| `{frame}` | Rendered frame |
| `{format}` | Lowercase file format |
| `{date}` | Current date as `YYYY-MM-DD` |
| `{scene}` | Scene name |

Example:

```text
{scene}_{camera}_{width}x{height}_{frame:04d}_{format}
```

Invalid filesystem characters and path separators are replaced. Empty names receive a safe fallback, repeated whitespace is collapsed, and `.` / `..` traversal segments are removed from subfolders.

## Validation

Validation reports Critical, Warning, and Info messages in the panel. Critical errors block batch rendering; warnings do not.

Checks include:

- Missing cameras or output path
- Invalid width or height
- Empty or malformed filename templates
- Unsupported tokens and image formats
- Duplicate final output filenames
- Invalid camera objects
- Custom frames outside the scene frame range

## Limitations

- v0.1.0 renders still images only.
- Animation profile support is planned.
- Render engine and sample overrides are planned.
- WebP is available only when the current Blender build exposes `WEBP` as an image format.
- Blender UI/render integration must be tested inside Blender; standard Python tests cannot execute `bpy`.

## Manual Test Checklist

1. Create three cameras: `Camera_Front`, `Camera_Square`, and `Camera_Vertical`.
2. Set `Camera_Front` to 1920x1080 PNG.
3. Set `Camera_Square` to 2048x2048 PNG.
4. Set `Camera_Vertical` to 1080x1920 JPEG.
5. Enable all profiles and render them.
6. Confirm all files use the expected names, dimensions, formats, and folders.
7. Confirm the original scene camera, resolution, output path, image format, transparency setting, and current frame are restored.
8. Give two profiles the same final filename and confirm validation blocks batch rendering.
9. Empty one filename template and confirm validation reports a critical error.
10. Confirm `CAMERA_OUTPUT_PROFILES_REPORT.md` lists outputs, skipped cameras, and warnings.

## Screenshots

Screenshots will be added after Blender 4.2/5.x UI verification. See `docs/screenshots/`.

## Development Status

Early open-source MVP. The code is organized by properties, UI, operators, validation, rendering, and pure utility helpers.

Run the standard-library tests:

```bash
python -m unittest discover -s tests -v
```

Run the end-to-end Blender test:

```bash
blender --background --factory-startup --python tests/blender_integration_test.py
```

## Contributing

Issues and pull requests are welcome. Keep changes compatible with Blender 4.2 LTS+, avoid external runtime dependencies, and include reproducible Blender test steps for UI or render changes.

See [User Guide](docs/USER_GUIDE.md), [Roadmap](docs/ROADMAP.md), and [Changelog](CHANGELOG.md).

## License

MIT License. See [LICENSE](LICENSE).
