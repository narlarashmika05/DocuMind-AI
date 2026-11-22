"""Read-only access to evaluation results produced by the scripts in evaluation/.

Experiments run offline from the command line (they take minutes and load several
models); the dashboard only displays their saved results.
"""

import json
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.v1.deps import CurrentUser
from app.core.config import settings

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _run_dir(name: str):
    if not SAFE_NAME.match(name):  # no path traversal through run or file names
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    path = settings.EVALUATION_RESULTS_DIR / name
    if not (path / "results.json").is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return path


@router.get("/runs")
def list_runs(current_user: CurrentUser) -> list[dict]:
    runs = []
    if settings.EVALUATION_RESULTS_DIR.is_dir():
        for path in settings.EVALUATION_RESULTS_DIR.glob("*/results.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            runs.append({"name": data["name"], "kind": data["kind"], "created": data["created"]})
    return sorted(runs, key=lambda r: r["created"], reverse=True)


@router.get("/runs/{name}")
def get_run(name: str, current_user: CurrentUser) -> dict:
    return json.loads((_run_dir(name) / "results.json").read_text(encoding="utf-8"))


@router.get("/runs/{name}/charts/{filename}")
def get_chart(name: str, filename: str, current_user: CurrentUser) -> FileResponse:
    path = _run_dir(name) / "charts" / filename
    if not SAFE_NAME.match(filename) or not filename.endswith(".png") or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chart not found")
    return FileResponse(path, media_type="image/png")
