"""STWarp web app: browser-based AE Mesh Warp preset builder."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import secrets
import shutil
import tempfile
import time
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from stwarp import __app_name__, __version__, core


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent.parent

# 150 MB per uploaded file — generous headroom for 4K+ 32-bit EXRs.
MAX_UPLOAD_BYTES = 150 * 1024 * 1024

SHOT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")

# Retention policy.
#   uploads/<token>/*.exr     — reaped 10 min after last write.
#   outputs/<token>/<shot>/*  — reaped 15 min after last write.
# The response zip is assembled in-memory from the outputs dir and
# streamed; it never lives on disk separately.
STORAGE_ROOT = Path(tempfile.gettempdir()) / "stwarp"
UPLOADS_DIR = STORAGE_ROOT / "uploads"
OUTPUTS_DIR = STORAGE_ROOT / "outputs"
UPLOADS_TTL_SECONDS = 10 * 60
OUTPUTS_TTL_SECONDS = 15 * 60
SWEEP_INTERVAL_SECONDS = 60

log = logging.getLogger("stwarp.web")


def _sweep_dir(root: Path, ttl_seconds: int) -> None:
    """Delete direct subdirs of `root` whose last write exceeds the TTL."""
    if not root.exists():
        return
    now = time.time()
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        try:
            age = now - entry.stat().st_mtime
        except FileNotFoundError:
            continue
        if age > ttl_seconds:
            shutil.rmtree(entry, ignore_errors=True)


def _sweep_all() -> None:
    _sweep_dir(UPLOADS_DIR, UPLOADS_TTL_SECONDS)
    _sweep_dir(OUTPUTS_DIR, OUTPUTS_TTL_SECONDS)


async def _sweep_loop() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            _sweep_all()
        except Exception:  # noqa: BLE001
            log.exception("storage sweep failed")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    _sweep_all()  # clean stragglers from prior container life
    task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=f"{__app_name__} Web", version=__version__, lifespan=_lifespan)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": __app_name__,
            "version": __version__,
            "grid_res": core.DEFAULT_GRID_RES,
        },
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "version": __version__}


@app.post("/export")
async def export(
    shot_name: str = Form(...),
    undistort: UploadFile = File(...),
    distort: UploadFile = File(...),
) -> StreamingResponse:
    # The signature guarantees exactly one undistort + one distort per
    # request; FastAPI drops any additional files posted to the same
    # field name.
    shot_name = shot_name.strip()
    if not SHOT_NAME_RE.match(shot_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Shot name may only contain letters, numbers, underscore, "
                "dot, and hyphen, and must start with a letter or number."
            ),
        )

    for label, upload in (("undistort", undistort), ("distort", distort)):
        name = (upload.filename or "").lower()
        if not name.endswith(".exr"):
            raise HTTPException(
                status_code=400,
                detail=f"The {label} STMap must be a .exr file.",
            )

    token = secrets.token_urlsafe(12)
    upload_dir = UPLOADS_DIR / token
    output_dir = OUTPUTS_DIR / token
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        undist_path = upload_dir / "undistort.exr"
        dist_path = upload_dir / "distort.exr"
        await _save_upload(undistort, undist_path)
        await _save_upload(distort, dist_path)

        try:
            result = core.export_presets(
                shot_name=shot_name,
                export_dir=str(output_dir),
                undistort_stmap=str(undist_path),
                distort_stmap=str(dist_path),
                grid_res=core.DEFAULT_GRID_RES,
            )
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500, detail=f"Export failed: {exc}") from exc

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            preset_dir = Path(result.output_dir)
            folder_name = preset_dir.name
            for ffx in result.ffx_paths:
                zf.write(ffx, arcname=f"{folder_name}/{os.path.basename(ffx)}")
        buf.seek(0)

        zip_name = f"{shot_name}_AE_mesh_warp_presets.zip"
        headers = {"Content-Disposition": f'attachment; filename="{zip_name}"'}
        return StreamingResponse(
            buf, media_type="application/zip", headers=headers)
    except HTTPException:
        # On failure, release both dirs immediately — retention only
        # applies to successful exports.
        shutil.rmtree(upload_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    """Stream an upload to disk, enforcing a per-file size cap."""
    total = 0
    with dest.open("wb") as fh:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"{upload.filename} exceeds the "
                        f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
                    ),
                )
            fh.write(chunk)
