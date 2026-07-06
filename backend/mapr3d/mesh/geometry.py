"""Low-level geometry builders returning (vertices, faces) numpy arrays.

Everything is unit-agnostic: callers scale coordinates before/after. Terrain
surfaces are single-sided (for fast preview); terrain solids and building
prisms are closed manifolds (for printing).
"""

from __future__ import annotations

import numpy as np
import shapely.geometry as sg
import trimesh


def terrain_surface(gx: np.ndarray, gy: np.ndarray, H: np.ndarray
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Top surface only. ``H`` indexed [row=y, col=x]."""
    ny, nx = H.shape
    X, Y = np.meshgrid(gx, gy)
    V = np.column_stack([X.ravel(), Y.ravel(), H.ravel()]).astype(np.float64)
    idx = np.arange(nx * ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel()
    b = idx[:-1, 1:].ravel()
    c = idx[1:, 1:].ravel()
    d = idx[1:, :-1].ravel()
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    return V, F.astype(np.int64)


def terrain_solid(gx: np.ndarray, gy: np.ndarray, H: np.ndarray,
                  base: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Closed watertight solid: draped top, flat bottom at ``-base``, walls."""
    ny, nx = H.shape
    X, Y = np.meshgrid(gx, gy)
    top = np.column_stack([X.ravel(), Y.ravel(), H.ravel()])
    bz = -abs(base)
    bot = np.column_stack([X.ravel(), Y.ravel(), np.full(nx * ny, bz)])
    V = np.vstack([top, bot]).astype(np.float64)
    N = nx * ny
    top_idx = np.arange(N).reshape(ny, nx)
    bot_idx = top_idx + N

    def grid_faces(idx: np.ndarray, flip: bool) -> np.ndarray:
        a = idx[:-1, :-1].ravel()
        b = idx[:-1, 1:].ravel()
        c = idx[1:, 1:].ravel()
        d = idx[1:, :-1].ravel()
        if flip:
            return np.vstack([np.column_stack([a, c, b]),
                              np.column_stack([a, d, c])])
        return np.vstack([np.column_stack([a, b, c]),
                          np.column_stack([a, c, d])])

    faces = [grid_faces(top_idx, flip=False), grid_faces(bot_idx, flip=True)]

    def wall(top_line: np.ndarray, bot_line: np.ndarray, flip: bool) -> np.ndarray:
        t0, t1 = top_line[:-1], top_line[1:]
        b0, b1 = bot_line[:-1], bot_line[1:]
        if flip:
            return np.vstack([np.column_stack([t0, b1, b0]),
                              np.column_stack([t0, t1, b1])])
        return np.vstack([np.column_stack([t0, b0, b1]),
                          np.column_stack([t0, b1, t1])])

    faces.append(wall(top_idx[0, :], bot_idx[0, :], flip=True))    # south
    faces.append(wall(top_idx[-1, :], bot_idx[-1, :], flip=False))  # north
    faces.append(wall(top_idx[:, 0], bot_idx[:, 0], flip=False))    # west
    faces.append(wall(top_idx[:, -1], bot_idx[:, -1], flip=True))   # east

    F = np.vstack(faces).astype(np.int64)
    return V, F


def polygon_from_ring(ring: list[tuple[float, float]]) -> sg.Polygon | None:
    """Validated shapely polygon from a local-meters ring, or None if degenerate."""
    if len(ring) < 3:
        return None
    poly = sg.Polygon(ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    if poly.area < 1.0:  # skip sub-1 m^2 slivers
        return None
    return poly


def building_prism(poly: sg.Polygon, base_z: float, height: float
                   ) -> tuple[np.ndarray, np.ndarray] | None:
    """Extruded watertight prism sitting from ``base_z`` up by ``height``."""
    try:
        mesh = trimesh.creation.extrude_polygon(poly, height=max(0.5, height))
    except Exception:
        return None
    mesh.apply_translation([0.0, 0.0, base_z])
    return np.asarray(mesh.vertices, dtype=np.float64), \
        np.asarray(mesh.faces, dtype=np.int64)
