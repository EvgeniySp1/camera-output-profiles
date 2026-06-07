# Camera Workflow v0.2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release Camera Output Profiles v0.2.0 with visible single-camera rendering and compact camera workflow tools.

**Architecture:** Add a focused camera tools module and convert rendering to a handler-managed session. Keep existing profile/path helpers and split UI into collapsed child panels.

**Tech Stack:** Python standard library, Blender `bpy`, Blender `mathutils`, `unittest`.

---

### Task 1: Define v0.2.0 Contracts

**Files:** `tests/test_addon_contract.py`, `tests/test_blender_import_smoke.py`, `tests/blender_integration_test.py`

- [ ] Add failing tests for metadata, operators, hidden batch UI, render handlers, new properties, and release documentation.
- [ ] Run `python -m unittest discover -s tests -v` and confirm failures describe missing v0.2.0 behavior.

### Task 2: Implement Camera Workflow Services

**Files:** `camera_output_profiles/camera_tools.py`, `camera_output_profiles/properties.py`, `camera_output_profiles/operators.py`

- [ ] Add target, bounds, safe look-at, view, framing, target empty, tracking, duplication, camera set, and lens services.
- [ ] Add Blender operators and scene/profile properties for those services.
- [ ] Run standard-library tests.

### Task 3: Implement Visible Single Render Session

**Files:** `camera_output_profiles/render_manager.py`, `camera_output_profiles/operators.py`, `camera_output_profiles/__init__.py`

- [ ] Capture and apply scene settings, register unique completion/cancel handlers, invoke visible render, and add synchronous fallback.
- [ ] Restore settings, clear state/handlers, write the single-render report, and optionally open the output folder after completion.
- [ ] Disable the legacy batch operator and remove it from all UI.

### Task 4: Build Compact UI

**Files:** `camera_output_profiles/ui.py`

- [ ] Keep the main panel focused on camera summary, path, render, apply, and validation.
- [ ] Add collapsed Output/View/Lens Presets and Camera Tools panels.
- [ ] Add tracking/lens status to Camera Data and workflow defaults to Output Properties.

### Task 5: Documentation And Release

**Files:** `README.md`, `docs/USER_GUIDE.md`, `docs/TESTING.md`, `docs/ROADMAP.md`, `CHANGELOG.md`, `RELEASE_NOTES_v0.2.0.md`

- [ ] Document v0.2.0 behavior, batch disablement, workflows, limitations, and exact manual tests.
- [ ] Set metadata to `(0, 2, 0)`.

### Task 6: Verify And Publish

**Files:** all changed files

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run Blender 4.3 background integration.
- [ ] Build and inspect the installation ZIP.
- [ ] Commit as `Release v0.2.0 camera workflow tools`, fast-forward `main`, push, tag `v0.2.0`, and create the GitHub release from release notes.
