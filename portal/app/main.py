import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.search import aggregated_search, health_check

app = FastAPI(title="Artifact Portal", version="1.0.0")

WEB_DIR = Path("/app/web")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="web index file is missing")
    return FileResponse(index_path)


@app.get("/api/health")
async def api_health() -> dict:
    checks = await health_check()
    return {"status": checks}


@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query("all", pattern="^(all|docker|npm|pypi|extension)$"),
) -> dict:
    return await aggregated_search(q, type)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("PORTAL_BIND", "0.0.0.0")
    port = int(os.getenv("PORTAL_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)

