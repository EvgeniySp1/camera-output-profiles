# Camera Output Profiles User Guide

## Installation

1. Create a ZIP with `camera_output_profiles/` at the archive root.
2. Open Blender **Edit -> Preferences -> Add-ons**.
3. Choose **Install from Disk**.
4. Select the ZIP and enable **Camera Output Profiles**.
5. Open **3D Viewport -> N-panel -> Cam Output**.

## Camera Profiles and Scene Output

Blender stores render output settings globally on the scene. Camera Output Profiles stores separate settings on each camera.

Selecting **4K 16:9** changes the selected camera profile to 3840 x 2160. Blender's native **Output > Format** may still show 1920 x 1080. This is expected.

When the add-on renders, it temporarily applies the selected profile. By default it restores the original Scene Output after rendering.

Use **Apply Profile to Scene Output** when you explicitly want Blender's Format panel to match the selected profile.

## Interface Overview

### N-panel > Cam Output

The compact workflow panel shows:

- Selected camera and profile summary
- Final Render Path
- Render This Profile and Apply Profile to Scene Output
- Resolution presets
- Render All Enabled Profiles and Validate Profiles
- Collapsed Camera List
- Collapsed Help and validation details

### Camera Data Properties

Open **Properties > Camera Data > Camera Output Profile** to edit all fields for the selected camera. The panel appears only when the active object is a camera.

### Output Properties

Open **Properties > Output > Camera Output Profiles Settings** for:

- Base Output Folder
- Default Output Subfolder for newly initialized profiles
- Render window, folder opening, and restoration settings
- Validation status
- Markdown report setting

## Base Output Folder

The **Base Output Folder** is `scene.render.filepath`.

Use:

- **Choose Base Output Folder** to select it through Blender's file browser.
- **Open Base Output Folder** to open it in the operating system.

The add-on treats this value as a folder, not a filename prefix.

These controls are located in **Output Properties > Camera Output Profiles Settings**.

## Output Subfolder

Each camera has an optional **Output Subfolder**.

Default:

```text
camera_profiles
```

For a Base Output Folder of `C:\tmp`, the default subfolder produces:

```text
C:\tmp\camera_profiles
```

Leave the field empty to save directly into `C:\tmp`.

Absolute subfolders and traversal such as `../` are rejected.

The global **Default Output Subfolder** is copied only into newly initialized profiles. It does not overwrite existing per-camera values.

## Final Render Path

The selected camera section always calculates and displays the complete **Final Render Path**.

It updates when camera, dimensions, format, template, subfolder, or frame changes.

Example:

```text
C:\tmp\camera_profiles\Camera_3840x2160_0001.png
```

Check this path before rendering.

## Filename Templates

Default:

```text
{camera}_{width}x{height}_{frame}
```

Tokens:

- `{camera}`
- `{scene}`
- `{width}`
- `{height}`
- `{frame}`
- `{format}`
- `{date}`

Python format specifications are supported, for example `{frame:04d}`.

Invalid filename characters are sanitized. Path separators, traversal, malformed braces, and unsupported tokens are critical validation errors.

## Render This Profile

**Render This Profile** renders only the selected camera.

Before rendering, Blender reports the camera, resolution, and full path. After rendering, it reports the saved file.

If **Show Render Window** is enabled, Blender opens the Render Result where the UI context allows it.

## Render All Enabled Profiles

**Render All Enabled Profiles** validates and renders enabled cameras in sequence.

Progress is reported for each camera:

```text
Rendering 1/3: Camera_FHD 1920x1080
Rendering 2/3: Camera_4K 3840x2160
Rendering 3/3: Camera_Vertical 1080x1920
```

The batch writes `CAMERA_OUTPUT_PROFILES_REPORT.md` to the Base Output Folder. It contains Blender version, scene, base folder, camera, resolution, format, full path, skipped profiles, warnings, and errors.

Disable **Write Markdown Report** in Output Properties when a batch report is not needed.

## Apply Profile to Scene Output

This manual action copies the selected profile into Blender's native Scene Output:

- Resolution X/Y
- Resolution percentage 100%
- File format
- Color mode where supported
- JPEG/WebP quality where supported
- Film transparency where supported

Presets never perform this synchronization automatically.

## Render Behavior

### Show Render Window

Default: enabled.

Shows Blender's Render Result after rendering where possible. Background/headless Blender cannot open a render window, so progress remains available in reports and console output.

### Open Output Folder After Render

Default: disabled.

Opens the final folder after a successful single render, or the Base Output Folder after a batch.

### Restore Scene Output After Render

Default: enabled.

Restores the original Scene Output settings after rendering.

When disabled, the last profile's resolution and format settings remain applied. The original camera, frame, Base Output Folder, and file-extension behavior are still restored.

## Validation

Critical messages block rendering. Warnings explain non-blocking conditions such as Scene Output differing from the profile, an empty subfolder, or overwrite risk.

Scene Output differing from the selected profile is normal. Use **Apply Profile to Scene Output** only when the Format panel must match.

## Troubleshooting

### Render saved under `C:\tmp\camera_profiles`

`C:\tmp` is the Base Output Folder and `camera_profiles` is the profile's Output Subfolder. Both are visible in the panel, along with the complete Final Render Path.

### 4K profile still shows FullHD in Output Properties

Presets edit the camera profile only. Click **Apply Profile to Scene Output** to copy 3840 x 2160 into Blender's Format panel.

### Render feels silent

Enable **Show Render Window** and watch Blender's status/report area. Batch progress also prints to the system console.

### File already exists

Validation reports overwrite risk. Change the filename template, camera name, subfolder, or frame token.
