"""DEM data providers.

Primary keyless source is AWS Terrain Tiles (Terrarium encoding), which blends
USGS 3DEP, SRTM and others so it returns the best available data per location.
A synthetic fractal source is the offline fallback so the app always runs.
"""

from __future__ import annotations

import io
import math
import os

import httpx
import numpy as np
from PIL import Image

from .geo import TILE, lonlat_to_pixel, pick_zoom

TERRARIUM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"
USGS_3DEP_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)
UA = {"User-Agent": "Mapr3D/0.1 (local 3D studio)"}


def in_usa(w: float, s: float, e: float, n: float) -> bool:
    """Rough bounds for USGS 3DEP coverage (CONUS + AK + HI + territories)."""
    cx, cy = (w + e) / 2.0, (s + n) / 2.0
    return -170.0 <= cx <= -64.0 and 15.0 <= cy <= 72.0


def fetch_usgs_3dep(w: float, s: float, e: float, n: float,
                    max_dim: int = 400, timeout: float = 40.0
                    ) -> tuple[np.ndarray, int]:
    """Keyless USGS 3DEP bare-earth elevation (down to 1 m in the US).

    Uses the National Map ImageServer, which returns a float32 GeoTIFF for the
    bbox. Rows are north -> south. Raises if the area has no 3DEP coverage.
    """
    import tifffile  # local import: only needed for this source

    lat0 = (s + n) / 2.0
    aspect = ((e - w) * math.cos(math.radians(lat0))) / max(n - s, 1e-9)
    if aspect >= 1.0:
        width, height = max_dim, max(2, int(round(max_dim / aspect)))
    else:
        width, height = max(2, int(round(max_dim * aspect))), max_dim

    params = {
        "bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326,
        "size": f"{width},{height}", "format": "tiff", "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }
    with httpx.Client(timeout=timeout, headers=UA) as client:
        r = client.get(USGS_3DEP_URL, params=params)
        r.raise_for_status()
        if "image" not in r.headers.get("content-type", ""):
            raise ValueError("3DEP returned no image (out of coverage)")
        arr = np.asarray(tifffile.imread(io.BytesIO(r.content)), dtype=np.float64)

    if arr.ndim != 2:
        arr = arr.reshape(height, width)
    arr = np.where(arr < -1e5, np.nan, arr)  # NoData sentinel
    if np.isnan(arr).mean() > 0.6:
        raise ValueError("3DEP has no coverage for this area")
    if np.isnan(arr).any():
        arr = np.where(np.isnan(arr), np.nanmin(arr), arr)
    return arr, 0  # already at requested grid; row 0 = north


def _decode_terrarium(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB")).astype(np.float64)
    return (a[..., 0] * 256.0 + a[..., 1] + a[..., 2] / 256.0) - 32768.0


def _resize(arr: np.ndarray, max_dim: int) -> np.ndarray:
    h, w = arr.shape
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        nh = max(2, int(round(h * scale)))
        nw = max(2, int(round(w * scale)))
        im = Image.fromarray(arr.astype(np.float32), mode="F").resize(
            (nw, nh), Image.BILINEAR
        )
        return np.asarray(im, dtype=np.float64)
    return arr


def fetch_terrain_tiles(w: float, s: float, e: float, n: float,
                        max_dim: int = 220, timeout: float = 30.0
                        ) -> tuple[np.ndarray, int]:
    """Fetch, mosaic and decode Terrarium tiles covering the bbox.

    Returns ``(heights, zoom)`` with rows ordered north -> south.
    """
    z = pick_zoom(w, s, e, n)
    x0f, y0f = lonlat_to_pixel(w, n, z)  # north-west corner
    x1f, y1f = lonlat_to_pixel(e, s, z)  # south-east corner
    tx0, tx1 = math.floor(x0f / TILE), math.floor(x1f / TILE)
    ty0, ty1 = math.floor(y0f / TILE), math.floor(y1f / TILE)
    ncols, nrows = tx1 - tx0 + 1, ty1 - ty0 + 1
    mosaic = np.zeros((nrows * TILE, ncols * TILE), dtype=np.float64)

    with httpx.Client(timeout=timeout, headers=UA) as client:
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                r = client.get(TERRARIUM_URL.format(z=z, x=tx, y=ty))
                r.raise_for_status()
                dec = _decode_terrarium(Image.open(io.BytesIO(r.content)))
                ry, rx = (ty - ty0) * TILE, (tx - tx0) * TILE
                mosaic[ry:ry + TILE, rx:rx + TILE] = dec

    cx0, cx1 = int(round(x0f - tx0 * TILE)), int(round(x1f - tx0 * TILE))
    cy0, cy1 = int(round(y0f - ty0 * TILE)), int(round(y1f - ty0 * TILE))
    crop = mosaic[cy0:cy1, cx0:cx1]
    if crop.size == 0 or min(crop.shape) < 2:
        raise ValueError("empty DEM crop for bbox")
    return _resize(crop, max_dim), z


def fetch_opentopography(w: float, s: float, e: float, n: float,
                         demtype: str = "USGS1m", max_dim: int = 400,
                         timeout: float = 60.0) -> tuple[np.ndarray, int]:
    """High-res DEM via OpenTopography (needs OPENTOPOGRAPHY_API_KEY).

    Requests ESRI ASCII grid so no GDAL/rasterio is needed to parse it.
    """
    key = os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not key:
        raise RuntimeError("OPENTOPOGRAPHY_API_KEY not set")
    params = {
        "demtype": demtype, "south": s, "north": n, "west": w, "east": e,
        "outputFormat": "AAIGrid", "API_Key": key,
    }
    with httpx.Client(timeout=timeout, headers=UA) as client:
        r = client.get(OPENTOPO_URL, params=params)
        r.raise_for_status()
        text = r.text
    H = _parse_aaigrid(text)
    return _resize(H, max_dim), 0


def _parse_aaigrid(text: str) -> np.ndarray:
    header: dict[str, float] = {}
    rows: list[list[float]] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0].lower()
        if key in ("ncols", "nrows", "xllcorner", "yllcorner", "cellsize",
                   "nodata_value"):
            header[key] = float(parts[1])
        else:
            rows.append([float(v) for v in parts])
    H = np.array(rows, dtype=np.float64)
    nodata = header.get("nodata_value")
    if nodata is not None:
        H[H == nodata] = np.nan
        if np.isnan(H).any():
            H = np.where(np.isnan(H), np.nanmin(H), H)
    return H  # AAIGrid rows are already north -> south


def synthetic_terrain(w: float, s: float, e: float, n: float,
                      max_dim: int = 200) -> tuple[np.ndarray, int]:
    """Deterministic fractal heightfield used when the network is unavailable."""
    seed = int(abs(w * 1000) + abs(n * 1000) + abs(e * 100) + abs(s * 100)) % (2 ** 31)
    rng = np.random.default_rng(seed)
    size = max_dim
    h = np.zeros((size, size), dtype=np.float64)
    freq, amp = 2, 1.0
    for _ in range(6):
        g = rng.standard_normal((freq + 1, freq + 1)).astype(np.float32)
        im = np.asarray(
            Image.fromarray(g, mode="F").resize((size, size), Image.BICUBIC)
        )
        h += im * amp
        freq *= 2
        amp *= 0.5
    h -= h.min()
    if h.max() > 0:
        h = h / h.max() * 320.0
    return h, 0
