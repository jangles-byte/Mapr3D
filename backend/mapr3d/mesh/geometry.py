"""Low-level geometry builders returning (vertices, faces) numpy arrays.

Everything is unit-agnostic: callers scale coordinates before/after. Terrain
surfaces are single-sided (for fast preview); terrain solids and building
prisms are closed manifolds (for printing).
"""

from __future__ import annotations

import warnings

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


_FLAT = {"", "flat", "none"}
_GABLE = {"gabled", "gambrel", "saltbox", "half-hipped"}
_HIP = {"hipped", "mansard", "round"}
_PYRAMID = {"pyramidal", "dome", "cone", "onion"}


def _obb(poly: sg.Polygon) -> tuple[np.ndarray, float, float]:
    """Oriented bounding box corners with the long edge as C0->C1."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # degenerate footprints -> handled below
        rect = poly.minimum_rotated_rectangle
    pts = np.asarray(rect.exterior.coords)
    if len(pts) < 4:  # collinear / degenerate
        return np.zeros((4, 2)), 0.0, 0.0
    pts = pts[:4]
    e01 = float(np.linalg.norm(pts[1] - pts[0]))
    e12 = float(np.linalg.norm(pts[2] - pts[1]))
    if e01 >= e12:
        return pts, e01, e12
    return np.roll(pts, -1, axis=0), e12, e01  # rotate so C0->C1 is long


def default_roof_height(poly: sg.Polygon) -> float:
    """A sensible roof height (m) when the tags don't give one."""
    _, _, short_len = _obb(poly)
    return float(min(0.35 * short_len, 4.0))


def _roof_faces(shape: str, long_len: float, short_len: float) -> np.ndarray:
    """Roof faces referencing top-ring verts 4-7 and apex/ridge verts 8(-9)."""
    if shape in _PYRAMID:
        return np.array([[4, 5, 8], [5, 6, 8], [6, 7, 8], [7, 4, 8]],
                        dtype=np.int64)
    # gabled / hipped: ridge verts 8 (over T0-T3 mid) and 9 (over T1-T2 mid)
    return np.array([
        [4, 5, 9], [4, 9, 8],   # slope over T0-T1
        [7, 6, 9], [7, 9, 8],   # slope over T3-T2
        [4, 7, 8],              # end / hip A
        [5, 6, 9],              # end / hip B
    ], dtype=np.int64)


def _shaped_building(C: np.ndarray, base_z: float, wall_h: float,
                     roof_h: float, shape: str, long_len: float,
                     short_len: float) -> tuple[np.ndarray, np.ndarray]:
    """One watertight solid: OBB floor + walls + shaped roof (no inner caps)."""
    z_top = base_z + wall_h
    zr = z_top + roof_h
    B = [[C[i][0], C[i][1], base_z] for i in range(4)]      # 0-3 base
    T = [[C[i][0], C[i][1], z_top] for i in range(4)]       # 4-7 eaves
    V = B + T
    if shape in _PYRAMID:
        apex = C.mean(axis=0)
        V.append([apex[0], apex[1], zr])                    # 8
    else:
        long_dir = (C[1] - C[0]) / (np.linalg.norm(C[1] - C[0]) + 1e-9)
        inset = min(0.5 * short_len, 0.45 * long_len) if shape in _HIP else 0.0
        ra = (C[0] + C[3]) / 2.0 + long_dir * inset
        rb = (C[1] + C[2]) / 2.0 - long_dir * inset
        V.append([ra[0], ra[1], zr])                        # 8
        V.append([rb[0], rb[1], zr])                        # 9

    faces = [[0, 2, 1], [0, 3, 2]]                          # floor (downward)
    for i in range(4):                                       # walls
        a, b = i, (i + 1) % 4
        faces += [[a, b, b + 4], [a, b + 4, a + 4]]
    F = np.vstack([np.array(faces, dtype=np.int64),
                   _roof_faces(shape, long_len, short_len)])
    return np.asarray(V, dtype=np.float64), F


def building_mesh(poly: sg.Polygon, base_z: float, height: float,
                  roof_shape: str = "", roof_h: float | None = None
                  ) -> tuple[np.ndarray, np.ndarray] | None:
    """Extruded walls plus a shaped roof (Simple 3D Buildings subset).

    Shaped roofs are built as one watertight solid over the footprint's oriented
    bounding box, so they only apply when the footprint is nearly rectangular
    (where a gable/hip actually makes sense). Everything else stays a flat prism
    over the true footprint.
    """
    shape = (roof_shape or "").lower().strip()
    if shape not in (_GABLE | _HIP | _PYRAMID):
        return building_prism(poly, base_z, height)

    C, long_len, short_len = _obb(poly)
    obb_area = long_len * short_len
    if obb_area <= 0 or poly.area / obb_area < 0.85:
        return building_prism(poly, base_z, height)  # too irregular for a ridge

    if roof_h is None:
        roof_h = min(0.35 * short_len, 4.0)
    roof_h = max(0.0, min(roof_h, height * 0.85))
    if roof_h < 0.3:
        return building_prism(poly, base_z, height)

    return _shaped_building(C, base_z, height - roof_h, roof_h, shape,
                            long_len, short_len)
