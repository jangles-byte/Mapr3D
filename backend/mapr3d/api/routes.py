"""API endpoints: build a scene, export an STL."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Response

from .. import __version__
from ..mesh import scene as scene_mod
from ..models import BuildRequest, ExportRequest

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/config")
def config() -> dict:
    """Report backend capabilities so the UI can adapt (e.g. lidar availability)."""
    return {"openTopographyKey": bool(os.environ.get("OPENTOPOGRAPHY_API_KEY"))}


@router.post("/scene/build")
def build_scene(req: BuildRequest) -> dict:
    try:
        return scene_mod.build_scene(
            req.bbox, req.includeBuildings, req.demSource,
            req.maxBuildings, req.resolution,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:  # noqa: BLE001 - surface a clean 500
        raise HTTPException(status_code=500, detail=f"scene build failed: {ex}")


@router.post("/scene/export")
def export_scene(req: ExportRequest) -> Response:
    try:
        data = scene_mod.export_stl(
            req.sceneId, req.includedIds, req.scaleMM, req.baseThicknessMM,
            req.zExaggeration, req.edits, req.union,
        )
    except KeyError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"export failed: {ex}")
    return Response(
        content=data,
        media_type="model/stl",
        headers={
            "Content-Disposition": f'attachment; filename="mapr3d_{req.sceneId}.stl"'
        },
    )
