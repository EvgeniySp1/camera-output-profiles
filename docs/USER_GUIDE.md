# Camera Output Profiles User Guide

## Installation

1. Download the repository or release ZIP.
2. Open Blender 4.2 LTS or newer.
3. Open **Edit -> Preferences -> Add-ons**.
4. Choose **Install** or **Install from Disk**.
5. Select the ZIP containing the `camera_output_profiles` folder.
6. Enable **Camera Output Profiles**.

## Interface Overview

Open the 3D Viewport sidebar with `N`, then choose the **Cam Output** tab.

The main panel contains:

- Current scene output folder preview
- Last validation status
- Global profile controls
- Common resolution presets for the active or selected camera
- One compact card per scene camera
- Collapsible validation results

Each camera card includes enable state, select/render buttons, resolution, aspect label, image format, color mode, quality where relevant, filename template, subfolder, transparency, and frame controls.

## Profile Setup

1. Set `Scene > Output > Output Path` to a writable folder.
2. Click **Add Profiles for All Cameras**.
3. Select a camera.
4. Apply a preset or enter width and height manually.
5. Choose PNG, JPEG, or WebP when supported.
6. Set RGB/RGBA, quality, transparency, subfolder, and filename.
7. Leave **Current Frame** enabled or enter a specific still frame.

New profiles default to:

- 1920x1080
- PNG / RGBA
- Quality 90
- Opaque background
- `camera_profiles` subfolder
- `{camera}*{width}x{height}*{frame}` filename template

The asterisks in the default template are sanitized to underscores on disk.

## Filename Templates

Supported tokens:

- `{camera}`
- `{width}`
- `{height}`
- `{frame}`
- `{format}`
- `{date}`
- `{scene}`

Python-style format specifications are supported for valid tokens. For example, `{frame:04d}` produces `0001`.

Filenames are sanitized before rendering. Invalid filesystem characters become underscores, repeated whitespace is collapsed, and empty names use `camera_output`. Subfolder traversal segments such as `..` are removed.

## Rendering All Profiles

1. Click **Validate Profiles**.
2. Resolve every Critical message.
3. Leave warnings when they are acceptable.
4. Click **Render Enabled Profiles**.

The add-on renders enabled profiles sequentially. For every profile it temporarily changes the scene camera and output settings, renders one still, and restores the original settings.

After the batch, `CAMERA_OUTPUT_PROFILES_REPORT.md` is written to the scene output folder.

## Avoiding Duplicate Filenames

Use `{camera}` in the template when multiple profiles share a subfolder. Resolution, frame, date, or format tokens can further distinguish outputs.

Validation compares complete sanitized output paths, including extension. Duplicate final paths are Critical because a later render would overwrite an earlier file.

## Troubleshooting

### Output path is empty

Set `Scene > Output > Output Path` before validation or rendering.

### WebP is rejected

The installed Blender build does not expose WebP output. Select PNG or JPEG.

### JPEG transparency is missing

JPEG has no alpha channel. The add-on renders JPEG profiles as RGB and reports a warning.

### A custom frame reports a warning

The frame is outside the scene start/end range. Rendering is still allowed, but confirm that the frame is intentional.

### The output folder does not open

Use Blender's Output Properties to inspect the configured path. The add-on first uses Blender's cross-platform path opener and then a standard system fallback.

### Rendering fails

Open Blender's system console and review messages prefixed with `[Camera Output Profiles]`. Confirm that the output folder is writable and that the selected render engine can render the scene.

## Manual Verification

Use the checklist in the project README before publishing a release. UI interaction and actual `bpy.ops.render.render` execution must be tested inside Blender.
