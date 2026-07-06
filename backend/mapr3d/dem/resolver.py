"""Best-available-per-region DEM resolver.

Given a bbox it selects a source, normalizes the result to a local-meters
heightfield with the base plane at z=0, and reports the data quality so the UI
can warn before someone commits a low-detail print.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import sources
from .geo import LocalProjector, ground_resolution


@dataclass
class DemResult:
    heights: np.ndarray   # [ny, nx], row 0 = south, col 0 = west, meters, min at 0
    grid_x: np.ndarray    # nx local meters, ascending west -> east
    grid_y: np.ndarray    # ny local meters, ascending south -> north
    min_elev: float       # true minimum elevation (subtracted from heights)
    source: str
    quality: str
    zoom: int
    projector: LocalProjector


def resolve_dem(w: float, s: float, e: float, n: float,
                prefer: str = "auto", max_dim: int = 220) -> DemResult:
    lon0, lat0 = (w + e) / 2.0, (s + n) / 2.0
    proj = LocalProjector(lon0, lat0)

    source = "synthetic"
    zoom = 0
    H: np.ndarray

    try:
        if prefer == "opentopography":
            H, zoom = sources.fetch_opentopography(w, s, e, n)
            source = "OpenTopography (USGS 1 m lidar)"
        elif prefer == "synthetic":
            raise RuntimeError("synthetic requested")
        else:
            H, zoom = sources.fetch_terrain_tiles(w, s, e, n, max_dim=max_dim)
            source = "AWS Terrain Tiles (Terrarium)"
    except Exception as ex:  # network / key / parse failure -> never blocks
        H, zoom = sources.synthetic_terrain(w, s, e, n, max_dim=min(max_dim, 200))
        source = f"synthetic (fallback: {type(ex).__name__})"

    H = np.flipud(np.ascontiguousarray(H))  # row 0 -> south
    ny, nx = H.shape

    x_w, _ = proj.to_local(w, lat0)
    x_e, _ = proj.to_local(e, lat0)
    _, y_s = proj.to_local(lon0, s)
    _, y_n = proj.to_local(lon0, n)
    grid_x = np.linspace(x_w, x_e, nx)
    grid_y = np.linspace(y_s, y_n, ny)

    min_elev = float(np.nanmin(H))
    H = H - min_elev  # base plane at 0

    quality = _quality_label(lat0, zoom, source)
    return DemResult(H, grid_x, grid_y, min_elev, source, quality, zoom, proj)


def _quality_label(lat: float, zoom: int, source: str) -> str:
    if zoom <= 0:
        return "no real elevation data" if source.startswith("synthetic") \
            else "high (lidar)"
    res = ground_resolution(lat, zoom)
    if res <= 5:
        tier = "high"
    elif res <= 20:
        tier = "medium"
    else:
        tier = "low"
    return f"{tier} (~{res:.0f} m/pixel, zoom {zoom})"
