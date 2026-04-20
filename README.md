# STMesh

Standalone desktop app for building Adobe After Effects Mesh Warp `.ffx`
presets from 32-bit STMap EXR files.

Given a shot name, an export location, and a pair of STMap EXRs
(undistort and distort), STMesh writes:

```
<export_location>/
  <shot_name>_AE_mesh_warp_presets/
    <shot_name>_distort.ffx
    <shot_name>_undistort.ffx
```

Drop either preset onto an adjustment layer in After Effects to apply
or remove lens distortion.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer on `PATH` (only needed to build; the final
  `STMesh.exe` runs standalone)

## Windows build

The repo is developed on WSL/Linux and copied over to Windows for
builds. The expected location on the Windows side is:

```
C:\Users\shann\Documents\STMesh
```

Each time you sync a new commit, overwrite the source files in that
folder. The `.venv\`, `build\`, and `dist\` folders stay put between
builds and are reused to speed things up.

From that folder, run `build.bat`:

| Command           | What it does                                                 |
| ----------------- | ------------------------------------------------------------ |
| `build.bat`       | Build `dist\STMesh.exe`                                      |
| `build.bat run`   | Build, then launch the app                                   |
| `build.bat clean` | Wipe `build\`, `dist\`, and `__pycache__\` first, then build |
| `build.bat dev`   | Run from source without freezing (for quick iteration)       |

The first run creates `.venv` and installs PySide6, numpy, and
PyInstaller. Subsequent runs are much faster.

Final output: `C:\Users\shann\Documents\STMesh\dist\STMesh.exe`

## Running from source (any platform)

```
python -m venv .venv
. .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m stmesh
```

## Using the app

1. Enter a shot name. Letters, digits, underscore, dot, and hyphen
   only.
2. Pick an export location (the parent folder that will contain the
   new `<shot_name>_AE_mesh_warp_presets` folder).
3. Pick the two 32-bit STMap EXRs:
   - Undistort STMap: maps distorted pixels to their undistorted
     positions.
   - Distort STMap: re-applies lens distortion (a.k.a. redistort).
4. Optional: change the grid resolution. After Effects only supports
   7, 11, 13, and 19. Default is 11.
5. Click **Export presets**. Use **Open output folder** to reveal the
   result in Explorer.

## STMap EXR notes

- Supported compressions: none, ZIP (16 scanlines), and ZIPS
  (1 scanline). If you get an "Unsupported EXR compression" error,
  re-export with "Zip (16 scanlines)".
- Supported channel types: float32 and half.
- Only the R and G channels are read. R carries the horizontal sample
  coordinate; G carries the vertical one.
- Overscan is auto-detected by probing the STMap edges, so STMaps
  whose UVs extend beyond `[0, 1]` are handled correctly.

## Why the preset files are "crossed"

AE Mesh Warp is a forward warp: the image follows the mesh vertices
from their rest positions to their anchor positions. STMaps are
inverse warps: each pixel says "sample FROM here". To convert
correctly, the STMap used for each direction is the opposite of the
resulting preset:

- `<shot>_undistort.ffx` is built from the distort STMap
- `<shot>_distort.ffx` is built from the undistort STMap

The UI hides this inversion. Just feed it the STMaps labelled the way
your pipeline labels them and it will output presets with the names
you expect.

## Project layout

```
stmesh/
  core.py     STMap EXR reader, grid sampler, .ffx writer
  app.py      PySide6 UI (main window, workers, validation)
  theme.py    Qt stylesheet
main.py       PyInstaller entry point
STMesh.spec   PyInstaller build config
build.bat     Windows build script
```

## Credits

The EXR reader, grid sampler, and `.ffx` writer were originally part
of ExportGenie (`ExportGenie-REF.py` in this repo). STMesh factors
that logic out into a small standalone app.
