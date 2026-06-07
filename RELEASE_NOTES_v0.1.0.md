# Camera Output Profiles v0.1.0

## What is this?

Camera Output Profiles is an open-source Blender add-on for assigning still-image output settings to individual cameras. It is intended for scenes that need multiple aspect ratios, resolutions, filenames, or output folders.

## New features

- Per-camera resolution, format, color mode, quality, transparency, frame, subfolder, and filename template
- FHD, 4K, square, portrait, vertical, and thumbnail presets
- Batch rendering of all enabled profiles
- Safe restoration of original scene render settings
- Filename tokens and filesystem-safe sanitization
- Validation for duplicate paths, invalid templates, unsupported formats, and invalid frames
- Markdown batch report

## Installation

1. Download the v0.1.0 source ZIP.
2. Open Blender 4.2 LTS or newer.
3. Go to **Edit -> Preferences -> Add-ons -> Install** or **Install from Disk**.
4. Select the ZIP containing `camera_output_profiles/`.
5. Enable **Camera Output Profiles**.
6. Open **3D Viewport -> N-panel -> Cam Output**.

## Known limitations

- v0.1.0 renders still images only.
- Animation frame ranges are not supported.
- Render engine and sample overrides are not supported.
- WebP depends on support in the installed Blender build.
- The initial release has standard Python tests, but still requires manual Blender 4.2/5.x UI and render verification.

## Roadmap

The next milestones cover animation ranges, render engine overrides, progress UI, contact sheets, portable presets, variants, and a more capable render queue. See `docs/ROADMAP.md`.

## How to report issues

Open a GitHub issue with:

- Blender version and operating system
- Render engine
- Steps to reproduce
- Expected and actual result
- Blender console output
- A minimal `.blend` file when it can be shared
