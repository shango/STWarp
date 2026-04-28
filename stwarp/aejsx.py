"""After Effects JSX generator for STWarp.

Builds a .jsx that recreates the canonical compositing setup used in
Export Genie:

- Inner work comp at the undistort STMap's resolution. Contains the
  undistort + redistort Mesh Warp adjustment layers (both disabled by
  default) and a guide-layer placeholder for the undistorted plate.
- Outer comp at the redistort STMap's resolution. Contains the work
  comp scaled to fit with the redistort preset applied, and a
  guide-layer placeholder for the raw (distorted) plate.

Real footage isn't shipped with the export; the JSX uses
``app.project.importPlaceholder`` for both plates so the user can swap
in their actual sequences after running the script.
"""

from __future__ import annotations

import os


DEFAULT_DURATION_SECONDS = 1.0
DEFAULT_FPS = 24.0


def _esc(s: str) -> str:
    """Escape a string for a JSX single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def write_ae_jsx(
    jsx_path: str,
    shot_name: str,
    undistort_dims: tuple[int, int],
    distort_dims: tuple[int, int],
    undistort_ffx: str,
    distort_ffx: str,
    fps: float = DEFAULT_FPS,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
) -> None:
    """Write the AE JSX setup file.

    Args:
        jsx_path: Output .jsx path.
        shot_name: Shot label used as the comp / layer name prefix.
        undistort_dims: (w, h) of the undistort STMap. Sets the inner
            (UD / work) comp size and the UD plate placeholder size.
        distort_dims: (w, h) of the redistort STMap. Sets the outer
            (raw plate) comp size and the raw plate placeholder size.
        undistort_ffx: Basename of the undistort .ffx (sits next to the JSX).
        distort_ffx: Basename of the redistort .ffx.
        fps: Comp frame rate.
        duration_seconds: Comp duration, in seconds.
    """
    und_w, und_h = undistort_dims
    raw_w, raw_h = distort_dims
    if und_w <= 0 or und_h <= 0 or raw_w <= 0 or raw_h <= 0:
        raise ValueError("STMap dimensions must be positive integers.")

    duration = float(duration_seconds)
    fps_val = float(fps)

    shot_js = _esc(shot_name)
    work_comp_name = f"{shot_js}_UD_{und_w}x{und_h}"
    outer_comp_name = f"{shot_js}_{raw_w}x{raw_h}"
    ud_plate_name = f"{shot_js}_UD_{und_w}x{und_h}"
    raw_plate_name = f"{shot_js}_{raw_w}x{raw_h}"

    und_ffx_js = _esc(os.path.basename(undistort_ffx).replace("\\", "/"))
    dist_ffx_js = _esc(os.path.basename(distort_ffx).replace("\\", "/"))

    # Scale the inner comp up (or down) to the outer comp size so that
    # the redistorted output covers the raw plate exactly.
    scale_x = round(raw_w / float(und_w) * 100.0, 4)
    scale_y = round(raw_h / float(und_h) * 100.0, 4)

    L: list[str] = []
    L.append(f"// STWarp AE setup -- {shot_js}")
    L.append(f"// Inner work comp: {und_w}x{und_h} (undistorted plate)")
    L.append(f"// Outer comp:      {raw_w}x{raw_h} (raw / re-distorted plate)")
    L.append("// Plates are placeholders -- relink to real footage in AE.")
    L.append("")
    L.append("app.activate();")
    L.append("")
    L.append("function findMeshWarp(layer) {")
    L.append("    var fx = layer.property('ADBE Effect Parade');")
    L.append("    for (var i = 1; i <= fx.numProperties; i++) {")
    L.append("        var p = fx.property(i);")
    L.append("        if (p.matchName === 'ADBE MESH WARP') return p;")
    L.append("    }")
    L.append("    return null;")
    L.append("}")
    L.append("")
    L.append("function deselectAll(items) {")
    L.append("    for (var i = 1; i <= items.length; i++) {")
    L.append("        var it = items[i];")
    L.append("        if (it instanceof FolderItem) deselectAll(it.items);")
    L.append("        it.selected = false;")
    L.append("    }")
    L.append("}")
    L.append("")
    L.append("function STWarpSetup() {")
    L.append("app.exitAfterLaunchAndEval = false;")
    L.append("app.beginUndoGroup('STWarp Setup');")
    L.append("")
    L.append("var compsFolder  = app.project.items.addFolder('_Comps');")
    L.append("var platesFolder = app.project.items.addFolder('Plates');")
    L.append("")
    L.append("var _scriptDir = (new File($.fileName)).parent;")
    L.append("")
    L.append(
        f"var undFfx = new File(_scriptDir.fsName + '/' + '{und_ffx_js}');")
    L.append(
        "if (!undFfx.exists) undFfx = File.openDialog("
        f"'Locate {und_ffx_js}', '*.ffx', false);")
    L.append(
        f"var distFfx = new File(_scriptDir.fsName + '/' + '{dist_ffx_js}');")
    L.append(
        "if (!distFfx.exists) distFfx = File.openDialog("
        f"'Locate {dist_ffx_js}', '*.ffx', false);")
    L.append("")

    # --- Inner / work comp at the undistort STMap resolution ---
    L.append("// --- Inner work comp (undistorted plate resolution) ---")
    L.append(
        f"var workComp = app.project.items.addComp('{work_comp_name}', "
        f"{und_w}, {und_h}, 1.0, {duration}, {fps_val});")
    L.append("workComp.parentFolder = compsFolder;")
    L.append("")

    # Undistort adjustment layer (uses <shot>_undistort.ffx, built from
    # the redistort STMap). Disabled by default to match the reference.
    L.append(
        "var undAdj = workComp.layers.addSolid([0,0,0], 'undistort', "
        f"workComp.width, workComp.height, 1.0, {duration});")
    L.append("undAdj.adjustmentLayer = true;")
    L.append("undAdj.moveToBeginning();")
    L.append("if (undFfx) {")
    L.append("    undAdj.applyPreset(undFfx);")
    L.append("    var undFx = findMeshWarp(undAdj);")
    L.append("    if (undFx) undFx.name = 'undistort';")
    L.append("}")
    L.append("undAdj.enabled = false;")
    L.append("")

    # Redistort adjustment layer (uses <shot>_distort.ffx, built from
    # the undistort STMap).
    L.append(
        "var redAdj = workComp.layers.addSolid([0,0,0], 'redistort', "
        f"workComp.width, workComp.height, 1.0, {duration});")
    L.append("redAdj.adjustmentLayer = true;")
    L.append("redAdj.moveToBeginning();")
    L.append("if (distFfx) {")
    L.append("    redAdj.applyPreset(distFfx);")
    L.append("    var redFx = findMeshWarp(redAdj);")
    L.append("    if (redFx) redFx.name = 'redistort';")
    L.append("}")
    L.append("redAdj.enabled = false;")
    L.append("")

    # Undistorted plate placeholder (bottom of the inner comp).
    L.append(
        f"var udFootage = app.project.importPlaceholder('{ud_plate_name}', "
        f"{und_w}, {und_h}, {fps_val}, {duration});")
    L.append("udFootage.parentFolder = platesFolder;")
    L.append(f"var udLayer = workComp.layers.add(udFootage, {duration});")
    L.append("udLayer.startTime = 0;")
    L.append("udLayer.moveToEnd();")
    L.append("udLayer.guideLayer = true;")
    L.append("")

    # --- Outer comp at the redistort STMap resolution ---
    L.append("// --- Outer comp (raw / re-distorted plate resolution) ---")
    L.append(
        f"var outerComp = app.project.items.addComp('{outer_comp_name}', "
        f"{raw_w}, {raw_h}, 1.0, {duration}, {fps_val});")
    L.append("outerComp.parentFolder = compsFolder;")
    L.append("")

    # Raw plate placeholder, added first so it ends up on the bottom
    # after we layer the work comp on top.
    L.append(
        f"var rawFootage = app.project.importPlaceholder('{raw_plate_name}', "
        f"{raw_w}, {raw_h}, {fps_val}, {duration});")
    L.append("rawFootage.parentFolder = platesFolder;")
    L.append(f"var rawLayer = outerComp.layers.add(rawFootage, {duration});")
    L.append("rawLayer.startTime = 0;")
    L.append("rawLayer.guideLayer = true;")
    L.append("")

    # Work comp on top, scaled to fit, with redistort preset applied.
    L.append(f"var workLayer = outerComp.layers.add(workComp, {duration});")
    L.append("workLayer.startTime = 0;")
    L.append("workLayer.moveToBeginning();")
    L.append(
        "workLayer.property('Transform').property('Scale')"
        f".setValue([{scale_x}, {scale_y}]);")
    L.append("if (distFfx) {")
    L.append("    workLayer.applyPreset(distFfx);")
    L.append("    var wFx = findMeshWarp(workLayer);")
    L.append("    if (wFx) wFx.name = 'redistort';")
    L.append("}")
    L.append("")

    L.append("deselectAll(app.project.items);")
    L.append("outerComp.selected = true;")
    L.append("outerComp.openInViewer();")
    L.append("")
    L.append("app.endUndoGroup();")
    L.append("alert('STWarp setup complete.');")
    L.append("}")
    L.append("")
    L.append("STWarpSetup();")
    L.append("")

    with open(jsx_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
