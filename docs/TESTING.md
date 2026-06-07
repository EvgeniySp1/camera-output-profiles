# Testing Camera Output Profiles

## Automated Tests

```powershell
python -m unittest discover -s tests -v
```

```powershell
blender --background --factory-startup --python tests/blender_integration_test.py
```

## Blender 5.1.2 Manual Checklist

### Test 1: Preset changes profile only

1. Open default Blender scene.
2. Select Camera.
3. Open N-panel > Cam Output.
4. Click `Add / Refresh Camera Profiles`.
5. Click `4K 16:9`.

Expected:

- selected camera profile shows 3840 x 2160
- camera list shows 3840 x 2160
- Blender native Output > Format may remain 1920 x 1080
- report says profile changed and Scene Output unchanged

### Test 2: Apply profile to Scene Output

1. With selected profile at 3840 x 2160, click `Apply Profile to Scene Output`.

Expected:

- Blender native Output > Format changes to 3840 x 2160
- resolution percentage becomes 100%

### Test 3: Final path clarity

1. Check selected camera section.

Expected:

- full final render path is visible
- path includes base output folder
- path includes output subfolder if not empty
- path includes filename generated from template

### Test 4: Render This Profile

1. Set profile to 3840 x 2160 PNG.
2. Confirm final path preview is visible.
3. Click `Render This Profile`.

Expected:

- render process is visible or clearly reported
- file is saved to the shown path
- output image is 3840 x 2160
- no FullHD image is produced from this profile

### Test 5: Render All Enabled Profiles

1. Add 3 cameras:
   - Camera_FHD: 1920 x 1080 PNG
   - Camera_4K: 3840 x 2160 PNG
   - Camera_Vertical: 1080 x 1920 JPEG
2. Click `Render All Enabled Profiles`.

Expected:

- progress is reported for each camera
- 3 files are created
- each file has its own correct resolution
- Markdown report is created
- no file overwrites another

### Test 6: Filename template

1. Set filename template to `{camera}_{width}x{height}_{frame}`.
2. Render selected profile.

Expected:

- output filename contains camera name, width, height and frame
- no asterisks
- no broken shortened tokens

### Test 7: Panel locations and compact N-panel

1. Open N-panel > Cam Output.
2. Confirm the main panel shows only selected-camera summary, final path, presets, render/apply actions, batch render, and validation.
3. Confirm Camera List and Help are collapsed by default.
4. Open Properties > Camera Data.
5. Open Properties > Output.

Expected:

- full profile fields appear under Camera Output Profile in Camera Data
- global settings appear under Camera Output Profiles Settings in Output Properties
- long explanations and filename token help are not permanently visible in the main N-panel
- validation results are collapsed unless critical errors exist
