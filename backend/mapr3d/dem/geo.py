"""Geographic helpers: slippy-map tile math and a local meters projection."""

from __future__ import annotations

import math

import numpy as np

TILE = 256
EARTH_CIRCUMFERENCE = 40075016.686  # meters at equator


def lonlat_to_pixel(lon: float, lat: float, z: int) -> tuple[float, float]:
    """Web Mercator global pixel coordinates at zoom ``z`` (256px tiles)."""
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n * TILE
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n * TILE
    return x, y


def pixel_to_lonlat(px: float, py: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = px / (n * TILE) * 360.0 - 180.0
    m = math.pi - 2.0 * math.pi * py / (n * TILE)
    lat = math.degrees(math.atan(math.sinh(m)))
    return lon, lat


def pick_zoom(w: float, s: float, e: float, n: float,
              max_tiles: int = 16, min_zoom: int = 1, max_zoom: int = 14) -> int:
    """Highest zoom whose tile count over the bbox stays under ``max_tiles``.

    Picking the highest affordable zoom is what gives "best available detail
    per region" for free.
    """
    for z in range(max_zoom, min_zoom - 1, -1):
        x0, y0 = lonlat_to_pixel(w, n, z)
        x1, y1 = lonlat_to_pixel(e, s, z)
        tx = math.floor(x1 / TILE) - math.floor(x0 / TILE) + 1
        ty = math.floor(y1 / TILE) - math.floor(y0 / TILE) + 1
        if tx * ty <= max_tiles:
            return z
    return min_zoom


def ground_resolution(lat: float, z: int) -> float:
    """Approximate meters-per-pixel of a web-mercator tile at ``lat``/``z``."""
    return EARTH_CIRCUMFERENCE * math.cos(math.radians(lat)) / (2 ** z * TILE)


class LocalProjector:
    """Equirectangular projection to local meters around a bbox center.

    Good enough for city-scale prints; avoids a full projection dependency.
    """

    def __init__(self, lon0: float, lat0: float):
        self.lon0 = lon0
        self.lat0 = lat0
        self.mlon = 111320.0 * math.cos(math.radians(lat0))
        self.mlat = 110574.0

    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.mlon, (lat - self.lat0) * self.mlat


def sample_grid(gx: np.ndarray, gy: np.ndarray, H: np.ndarray,
                x: float, y: float) -> float:
    """Bilinear sample of heightfield ``H`` (indexed [row=y, col=x])."""
    nx = len(gx)
    ny = len(gy)
    fx = float(np.interp(x, gx, np.arange(nx)))
    fy = float(np.interp(y, gy, np.arange(ny)))
    i0 = int(np.clip(math.floor(fx), 0, nx - 2))
    j0 = int(np.clip(math.floor(fy), 0, ny - 2))
    tx = fx - i0
    ty = fy - j0
    return float(
        H[j0, i0] * (1 - tx) * (1 - ty)
        + H[j0, i0 + 1] * tx * (1 - ty)
        + H[j0 + 1, i0] * (1 - tx) * ty
        + H[j0 + 1, i0 + 1] * tx * ty
    )
