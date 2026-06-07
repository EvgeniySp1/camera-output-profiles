# Camera Output Profiles v0.1.1

**DRAFT - NOT RELEASED**

## What changed

This maintenance release redesigns the N-panel and makes the separation between per-camera profiles and Blender's global Scene Output explicit.

## UX improvements

- Added version, camera count, and enabled profile count
- Added a compact profile-vs-scene explanation
- Added editable Base Output Folder controls
- Added complete Final Render Path preview
- Replaced important icon-only actions with text buttons
- Added selected-camera profile editor and large Render This Profile action
- Added visible render behavior settings
- Added progress reports for batch rendering

## Workflow improvements

- Added Apply Profile to Scene Output
- Added Open Final Output Folder
- Changed the default template to `{camera}_{width}x{height}_{frame}`
- Added strict path traversal validation
- Added overwrite, empty-subfolder, and Scene Output mismatch warnings
- Expanded Markdown batch reports with resolution, format, base folder, and full paths

## Testing status

- Automated Python tests are required before commit.
- Blender background integration is tested where a compatible local Blender is available.
- Blender 5.1.2 manual testing is still required.

## Release status

Do not publish this version until the checklist in `docs/TESTING.md` passes in Blender 5.1.2.
