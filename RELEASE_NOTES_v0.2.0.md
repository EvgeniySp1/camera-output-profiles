# Camera Output Profiles v0.2.0

## What is Camera Output Profiles?

An open-source Blender add-on for per-camera output profiles and compact camera workflow tools.

## What's new in v0.2.0

- Visible single-profile rendering with completion/cancel restoration
- Camera view and lens presets
- Perspective and orthographic framing
- Target Empty and Track To tools
- Camera duplication with profile copying
- Product and social camera set creation
- Compact preset and camera-tool panels

## Important change: batch rendering temporarily disabled

Batch rendering is temporarily disabled in v0.2.0 while a visible render queue is being redesigned.

## Visible render mode

The add-on prefers Blender's invoked render workflow and keeps profile settings applied until a completion or cancellation handler runs. A synchronous fallback is used when invocation is unavailable.

## Camera placement tools

Place cameras around selected, active, saved, scene-center, or visible targets. Frame selected objects, collections, or all visible objects.

## Tracking target tools

Create a target Empty, aim once, add/update the add-on Track To constraint, or remove only add-on-owned tracking.

## Camera set creation

Create Product Basic, Product Full, or Social Pack camera sets with initialized output profiles and optional shared tracking.

## Installation

Download the release ZIP, install it through Blender **Edit -> Preferences -> Add-ons -> Install from Disk**, and enable **Camera Output Profiles**.

## Known limitations

- Still images only
- No multi-camera render queue in v0.2.0
- WebP depends on the Blender build
- Blender 5.1.2 manual verification follows the checklist in `docs/TESTING.md`

## Roadmap

v0.3.0 targets a visible sequential render queue with progress, cancel, retry, reports, and contact sheets.

## Testing notes

Automated Python tests and the repository's available Blender background integration test are run before release. Blender 5.1.2 is not claimed unless manually executed.
