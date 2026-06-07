# Camera Output Profiles User Guide

## Installation

Install the release ZIP through **Edit -> Preferences -> Add-ons -> Install from Disk**, enable the add-on, then open **3D Viewport -> N-panel -> Cam Output**.

## Output Profiles

Each camera stores width, height, image format, color mode, quality, transparency, output subfolder, filename template, and frame choice. Output presets modify only this profile. Use **Apply Profile to Scene Output** when Blender's native Output panel must match it.

The final filename supports `{camera}`, `{scene}`, `{width}`, `{height}`, `{frame}`, `{format}`, and `{date}`.

## Visible Single Render

**Render This Profile** temporarily applies the profile and invokes Blender's visible render workflow where possible. Completion and cancellation handlers restore the original camera, resolution, percentage, path, format, color, quality, frame, and transparency when restoration is enabled.

If the UI context cannot start a visible render, the add-on reports `Visible render invocation failed; used fallback render mode.` and uses Blender's synchronous render operator.

Batch rendering is temporarily disabled in v0.2.0 while a visible render queue is being redesigned.

## View Presets

Choose Target Mode, Distance Multiplier, Height Offset, and Margin under **Camera Tools**. Then open **Presets -> View Presets** and select Front, Back, Left, Right, Top, Bottom, 3/4 Front, 3/4 Back, Isometric, Low Angle, or High Angle.

Selected Object falls back to the active object and then scene center when necessary. Top and bottom views use a stable fallback up vector.

## Frame And Fit

- **Frame Selected Object** uses selected non-camera objects.
- **Active Collection** uses objects in the active collection.
- **All Visible** uses visible non-camera objects.

Perspective cameras move along the current view direction using the limiting field of view. Orthographic cameras update `ortho_scale`. Target transforms and geometry are not changed.

## Target Tracking

1. Resolve the desired target with Target Mode.
2. Click **Create Target Empty**.
3. Click **Aim Camera at Target** for a one-time rotation.
4. Click **Add Track To Target** for persistent tracking.

For one object, the Empty is parented while preserving world transform. The add-on uses `TRACK_NEGATIVE_Z`, `UP_Y`, and the constraint name `COP_Track_To_Target`. **Remove Camera Tracking** removes only that constraint.

## Duplicate Camera With Profile

**Duplicate Camera + Profile** copies the object, camera data, transform, and every profile field. The duplicate becomes active. Enable **Copy Tracking** to retain the add-on target reference and tracking constraint.

## Camera Sets

Choose Product Basic, Product Full, or Social Pack, optionally enable tracking, then click **Create Camera Set**. New names are generated safely without overwriting existing cameras.

Social Pack creates 16:9 hero, 1:1 square, and 9:16 vertical profile resolutions. Product sets create common directional views around the target.

## Lens Presets

Open **Presets -> Lens Presets** for 24, 35, 50, 70, 85, 100 mm, or Orthographic Product. Lens changes never modify output resolution.

## Troubleshooting

**Render already running:** wait or cancel Blender's current render. The add-on clears its job on completion/cancel.

**Target missing:** recreate the Target Empty and add tracking again.

**Nothing to frame:** select a non-camera object or choose another framing source.

**4K profile but Output panel shows FullHD:** this is expected. Click **Apply Profile to Scene Output** only when manual synchronization is desired.

**Wrong path:** validate the Base Output Folder, Output Subfolder, and filename template shown under Final Render Path.
