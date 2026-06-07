# Testing Camera Output Profiles

## Automated Tests

```powershell
python -m unittest discover -s tests -v
```

```powershell
blender --background --factory-startup --python tests/blender_integration_test.py
```

## Blender 5.1.2 Manual Checklist

### Test 1: Single visible render

1. Open default scene.
2. Select Camera.
3. Set profile to 4K 16:9.
4. Click Render This Profile.

Expected: Blender shows F12-like progress where possible; output is 3840x2160; scene output restores when enabled.

### Test 2: Cancel render restore

1. Start visible render.
2. Cancel render.

Expected: scene settings restore; active render state clears; the next render can start.

### Test 3: View preset

1. Select Cube and Camera.
2. Apply 3/4 Front.

Expected: camera moves around and points at Cube; output profile is unchanged.

### Test 4: Frame selected

1. Select Cube and Camera.
2. Click Frame Selected Object.

Expected: Cube fits in the camera frame with margin.

### Test 5: Track target

1. Select Cube and Camera.
2. Create Target Empty.
3. Add Track To Target.
4. Move Cube.

Expected: target follows Cube and camera keeps looking at it.

### Test 6: Duplicate camera with profile

1. Set Camera profile to Square 2048x2048 PNG.
2. Duplicate Camera + Profile.

Expected: duplicate exists, profile is copied, duplicate is selected, original is unchanged.

### Test 7: Create Product Basic camera set

1. Select Cube.
2. Choose Product Basic.
3. Create Camera Set.

Expected: named cameras and profiles are created, point at target, and do not overwrite existing cameras.

### Test 8: Lens presets

1. Select Camera.
2. Apply 70mm Product.

Expected: lens is 70 mm and output resolution is unchanged.

### Test 9: Batch render removed

Expected: no visible Render All Enabled Profiles button; documentation states batch rendering is disabled for v0.2.0.
