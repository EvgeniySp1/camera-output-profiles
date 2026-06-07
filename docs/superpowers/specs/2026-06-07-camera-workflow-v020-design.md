# Camera Output Profiles v0.2.0 Design

## Architecture

Keep output profiles as per-camera `PropertyGroup` data. Add `camera_tools.py` for target resolution, camera placement, framing, tracking, duplication, camera sets, and lens presets. Keep operators thin and expose those services through Blender operators.

Single-profile rendering becomes an explicit render session in `render_manager.py`. It captures scene state, applies the profile, registers `render_complete` and `render_cancel` handlers, invokes Blender's visible render operator, then restores state and removes handlers only after completion or cancellation. One add-on render session may be active at a time.

## UI

The N-panel remains compact. The main panel shows selected camera/profile/path and one render action. Output, view, and lens controls live in collapsed child panels under Presets. Camera placement, framing, tracking, duplication, and camera-set controls live under a collapsed Camera Tools panel. Camera List, Validation, and Help remain collapsed unless validation contains critical errors.

Full profile fields remain in Camera Data Properties. Global render and workflow defaults remain in Output Properties.

## Compatibility And Safety

Target Blender 4.2 LTS and newer API-compatible versions. Use `bpy`, `mathutils`, and Python standard library only. Never modify target geometry. Only remove the add-on-owned tracking constraint. Preserve render settings through a complete scene snapshot and clean handlers during add-on unregister.

## Testing

Standard-library tests verify metadata, registration, UI contracts, render-session cleanup, and documentation. A Blender background integration test verifies camera placement, framing, tracking, duplication, camera sets, lens presets, single rendering, output size, report generation, and scene restoration. Blender 5.1.2 remains a documented manual checklist unless run in this environment.
