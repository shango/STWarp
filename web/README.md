# STWarp Web

FastAPI wrapper around `stmesh.core` — upload two STMap EXRs, download a
zip of AE Mesh Warp `.ffx` presets.

## Run locally

From the repo root:

```bash
pip install -r web/requirements.txt
uvicorn web.app.main:app --reload --port 8000
```

Open <http://localhost:8000>.

Or via Docker:

```bash
docker build -f web/Dockerfile -t stwarp-web .
docker run --rm -p 8000:8000 stwarp-web
```

## Deploy to Railway

`railway.toml` at the repo root points Railway at `web/Dockerfile`.
Push the branch/commit to GitHub; Railway rebuilds automatically.

- Build context: repo root (so `stmesh/` is importable inside the image).
- Health check: `GET /healthz`.
- Port: Railway injects `$PORT`; the container honours it.
