# Camera Output Profiles

Camera Output Profiles is an open-source Blender add-on for per-camera output profiles, visible single-camera rendering, camera placement presets, target tracking and product camera set creation.

Version: **v0.2.0**

## Features

- Per-camera resolution, format, color, quality, transparency, frame, subfolder, and filename template
- Visible single-profile rendering with completion/cancel restoration handlers
- FHD, 4K, square, portrait, vertical, and thumbnail output presets
- Front, back, side, top, isometric, 3/4, low, and high camera views
- Perspective and orthographic object framing
- Target Empty creation and add-on-owned Track To constraints
- Camera duplication with reliable profile copying
- Product Basic, Product Full, and Social Pack camera sets
- 24, 35, 50, 70, 85, 100 mm and orthographic lens presets
- Compact N-panel, Camera Data profile panel, and Output Properties settings

Batch rendering is temporarily disabled in v0.2.0 while a visible render queue is being redesigned.

## Installation

1. Download the v0.2.0 ZIP from GitHub Releases.
2. Open Blender.
3. Go to **Edit -> Preferences -> Add-ons -> Install from Disk**.
4. Select the ZIP.
5. Enable **Camera Output Profiles**.
6. Open **3D Viewport -> N-panel -> Cam Output**.

## Quick Start

1. Select a product or object.
2. Add or refresh the camera profile from **Camera List**.
3. Choose an **Output Preset**.
4. Use a **View Preset** or **Frame Selected Object**.
5. Optionally choose **Create Target Empty**, then **Add Track To Target**.
6. Click **Render This Profile**.
7. Find the file at **Final Render Path**.

## Visible Render

The add-on applies the selected profile, starts Blender's visible render invocation where the UI context supports it, and restores scene output settings from `render_complete` or `render_cancel` handlers. If visible invocation is unavailable, it uses a synchronous fallback and reports that fallback.

Only one add-on render can run at a time. **Apply Profile to Scene Output** remains a separate manual action; resolution presets do not silently change Blender's global Output settings.

## Camera Workflow

**View Presets** place the selected camera around the configured target mode: Selected Object, Active Object, Camera Target Empty, Scene Center, or All Visible Objects.

**Camera Tools** can frame targets, create a parented target Empty, aim once, add/remove persistent tracking, duplicate a camera and profile, or create a complete camera set. Tracking uses one add-on-owned Track To constraint and does not remove user constraints.

## Output Paths

The final path combines Blender's Base Output Folder, the per-camera Output Subfolder, expanded filename template, and the correct extension.

Supported tokens:

- `{camera}`
- `{width}`
- `{height}`
- `{frame}`
- `{format}`
- `{date}`
- `{scene}`

Default template:

```text
{camera}_{width}x{height}_{frame}
```

Invalid filename characters are sanitized. Absolute subfolders, separators in templates, and traversal such as `../` are rejected.

## UI Locations

- **N-panel -> Cam Output**: summary, final path, render, presets, camera tools, validation, camera list, help
- **Camera Data Properties -> Camera Output Profile**: full profile, tracking target, lens status
- **Output Properties -> Camera Output Profiles Settings**: paths, render behavior, reports, workflow defaults

## Limitations

- v0.2.0 renders still images only.
- Batch rendering is temporarily disabled.
- Animation profiles and render engine/sample overrides are not implemented.
- WebP depends on the installed Blender build.
- Blender 5.1.2 requires the documented manual checklist; automated integration in this repository uses the available Blender installation.

## Testing

```powershell
python -m unittest discover -s tests -v
```

```powershell
blender --background --factory-startup --python tests/blender_integration_test.py
```

See [docs/TESTING.md](docs/TESTING.md).

## Contributing

Issues and pull requests are welcome. Runtime code must use only Python's standard library and Blender APIs.

## License

MIT License. See [LICENSE](LICENSE).
