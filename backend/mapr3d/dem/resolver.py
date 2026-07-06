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

    H, zoom, source = _resolve_heights(w, s, e, n, prefer, max_dim)

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


def _resolve_heights(w: float, s: float, e: float, n: float,
                     prefer: str, max_dim: int) -> tuple[np.ndarray, int, str]:
    """Try sources in priority order, always falling back to something usable.

    opentopography: USGS 1 m lidar -> Copernicus 30 m -> keyless tiles -> synthetic.
    auto:           keyless tiles -> synthetic.
    """
    if prefer == "synthetic":
        H, z = sources.synthetic_terrain(w, s, e, n, max_dim=min(max_dim, 200))
        return H, z, "synthetic (requested)"

    if prefer == "opentopography":
        for demtype, label, md in (
            ("USGS1m", "OpenTopography USGS 3DEP 1 m lidar", max(max_dim, 400)),
            ("COP30", "OpenTopography Copernicus 30 m", max_dim),
        ):
            try:
                H, z = sources.fetch_opentopography(w, s, e, n, demtype=demtype,
                                                    max_dim=md)
                return H, z, label
            except Exception:
                continue  # no key, no coverage, or network -> try the next

    try:
        H, z = sources.fetch_terrain_tiles(w, s, e, n, max_dim=max_dim)
        note = "AWS Terrain Tiles (Terrarium)"
        if prefer == "opentopography":
            note += " — lidar unavailable (no key or no coverage)"
        return H, z, note
    except Exception as ex:
        H, z = sources.synthetic_terrain(w, s, e, n, max_dim=min(max_dim, 200))
        return H, z, f"synthetic (fallback: {type(ex).__name__})"


def _quality_label(lat: float, zoom: int, source: str) -> str:
    s = source.lower()

    def zoom_tier() -> str:
        res = ground_resolution(lat, zoom)
        tier = "high" if res <= 5 else "medium" if res <= 20 else "low"
        return f"{tier} (~{res:.0f} m/pixel, zoom {zoom})"

    if "synthetic" in s:
        return "no real elevation data"
    # Check the actual data source before the "lidar unavailable" note text.
    if "terrarium" in s or "terrain tiles" in s:
        return zoom_tier() if zoom > 0 else "medium (terrain tiles)"
    if "3dep" in s or "1 m lidar" in s:
        return "high (~1 m lidar)"
    if "30 m" in s:
        return "low (~30 m)"
    return zoom_tier() if zoom > 0 else "unknown"
