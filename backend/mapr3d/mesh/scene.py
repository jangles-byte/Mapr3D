"""Scene assembly.

A scene is a structured, editable description (heightfield + building defs),
not baked meshes. Preview geometry and the export STL are both *generated* from
it, which is what lets the studio hide/delete/re-height individual objects and
still produce a clean solid on export.
"""

from __future__ import annotations

import io
import math
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np
import shapely.affinity as sa
import trimesh
from shapely.geometry import box as shapely_box

from ..dem.geo import sample_grid
from ..dem.resolver import DemResult, resolve_dem
from ..features import osm
from . import geometry as geo

SINK = 2.0            # meters buildings embed into terrain to stay connected
_MAX_SCENES = 12      # in-memory LRU cap
SCENES: "OrderedDict[str, Scene]" = OrderedDict()


@dataclass
class BuildingDef:
    id: str
    name: str
    poly: object            # shapely Polygon in local meters
    terr_z: float           # terrain top under the footprint (relative meters)
    height: float           # visual height in meters
    roof_shape: str         # "", "gabled", "hipped", "pyramidal", ...
    roof_h: float           # roof height in meters (0 = flat)
    tags: dict


@dataclass
class ImportedDef:
    """An external mesh (photogrammetry / 3D Tiles / splat) dropped into the scene.

    Vertices are stored normalized: centered on XY, base at z=0, max horizontal
    extent 1.0. The placement (position, uniform scale, z-rotation) lives in the
    editable transform so the studio can move/scale/rotate it.
    """
    id: str
    name: str
    vertices: np.ndarray    # [N,3] normalized unit mesh
    faces: np.ndarray       # [M,3]
    transform: dict         # {tx, ty, tz, scale, rotZ}


@dataclass
class Scene:
    id: str
    bbox: list[float]
    dem: DemResult
    buildings: list[BuildingDef] = field(default_factory=list)
    imported: list[ImportedDef] = field(default_factory=list)
    extent_m: float = 1.0


def _round(a: np.ndarray, nd: int = 2) -> list:
    return np.round(a, nd).astype(np.float64).ravel().tolist()


def _object_payload(oid: str, otype: str, name: str,
                    V: np.ndarray, F: np.ndarray, meta: dict) -> dict:
    return {
        "id": oid,
        "type": otype,
        "name": name,
        "positions": _round(V, 2),
        "indices": F.astype(np.int64).ravel().tolist(),
        "vertexCount": int(len(V)),
        "meta": meta,
    }


def build_scene(bbox: list[float], include_buildings: bool = True,
                dem_source: str = "auto", max_buildings: int = 1500,
                resolution: int = 220) -> dict:
    w, s, e, n = bbox
    dem = resolve_dem(w, s, e, n, prefer=dem_source, max_dim=resolution)
    sid = uuid.uuid4().hex[:12]

    extent_m = float(max(dem.grid_x[-1] - dem.grid_x[0],
                         dem.grid_y[-1] - dem.grid_y[0]))
    scene = Scene(id=sid, bbox=bbox, dem=dem, extent_m=max(extent_m, 1.0))

    objects: list[dict] = []

    V, F = geo.terrain_surface(dem.grid_x, dem.grid_y, dem.heights)
    objects.append(_object_payload(
        "terrain", "terrain", "Terrain", V, F,
        {"source": dem.source, "quality": dem.quality,
         "minElev": dem.min_elev, "zRange": [0.0, float(dem.heights.max())]},
    ))

    notes: list[str] = []
    if "synthetic" in dem.source:
        notes.append("No real elevation data here — using synthetic terrain.")

    if include_buildings:
        try:
            raw = osm.fetch_buildings(w, s, e, n)
        except Exception:
            raw = []
            notes.append("Buildings unavailable (OpenStreetMap timeout) — try Build again.")
        if len(raw) > max_buildings:
            notes.append(f"Showing first {max_buildings} of {len(raw)} buildings.")
        raw = raw[:max_buildings]
        terr_rect = shapely_box(float(dem.grid_x[0]), float(dem.grid_y[0]),
                                float(dem.grid_x[-1]), float(dem.grid_y[-1]))
        for b in raw:
            ring_ll = b["rings"][0]
            local = [dem.projector.to_local(lon, lat) for lon, lat in ring_ll]
            poly = geo.polygon_from_ring(local)
            if poly is None:
                continue
            # Clip to the terrain footprint so buildings never overhang the
            # plate (which would print as disconnected floating islands).
            poly = poly.intersection(terr_rect)
            if poly.is_empty or poly.area < 1.0:
                continue
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
            cx, cy = poly.centroid.x, poly.centroid.y
            terr_z = sample_grid(dem.grid_x, dem.grid_y, dem.heights, cx, cy)
            height = osm.building_height(b["tags"])
            shape, roof_h = osm.roof_info(b["tags"])
            if shape and shape != "flat" and roof_h is None:
                roof_h = geo.default_roof_height(poly)
            bd = BuildingDef(
                id=b["id"], name=osm.building_name(b["tags"], b["id"]),
                poly=poly, terr_z=terr_z, height=height,
                roof_shape=shape, roof_h=roof_h or 0.0, tags=b["tags"],
            )
            scene.buildings.append(bd)
            geom = geo.building_mesh(poly, terr_z - SINK, height + SINK,
                                     shape, (roof_h or None))
            if geom is None:
                continue
            bv, bf = geom
            objects.append(_object_payload(
                bd.id, "building", bd.name, bv, bf,
                {"height": height, "area": round(poly.area, 1),
                 "roof": shape or "flat"},
            ))

    _cache(scene)

    return {
        "sceneId": sid,
        "objects": objects,
        "dem": {"source": dem.source, "quality": dem.quality, "zoom": dem.zoom},
        "bounds": {
            "extentM": scene.extent_m,
            "xRange": [float(dem.grid_x[0]), float(dem.grid_x[-1])],
            "yRange": [float(dem.grid_y[0]), float(dem.grid_y[-1])],
            "zMax": float(dem.heights.max()),
        },
        "buildingCount": len(scene.buildings),
        "suggestedScaleMM": 180.0,
        "notes": notes,
    }


def export_stl(sid: str, included_ids: list[str], scale_mm: float,
               base_mm: float, z_exag: float, edits: dict,
               do_union: bool = False) -> bytes:
    scene = get_scene(sid)
    if scene is None:
        raise KeyError("scene not found (rebuild the scene)")

    dem = scene.dem
    factor = scale_mm / scene.extent_m
    vfac = factor * z_exag
    included = set(included_ids) if included_ids else None

    meshes: list[trimesh.Trimesh] = []

    def wanted(oid: str) -> bool:
        if included is not None and oid not in included:
            return False
        return not edits.get(oid, {}).get("hidden", False)

    if wanted("terrain"):
        gx = dem.grid_x * factor
        gy = dem.grid_y * factor
        H = dem.heights * vfac
        V, F = geo.terrain_solid(gx, gy, H, base=base_mm)
        meshes.append(trimesh.Trimesh(vertices=V, faces=F, process=False))

    for b in scene.buildings:
        if not wanted(b.id):
            continue
        hscale = float(edits.get(b.id, {}).get("heightScale", 1.0))
        poly_s = sa.scale(b.poly, xfact=factor, yfact=factor, origin=(0, 0))
        base_z = (b.terr_z - SINK) * vfac
        height = (b.height * hscale + SINK) * vfac
        roof_h = (b.roof_h * vfac) if b.roof_h > 0 else None
        geom = geo.building_mesh(poly_s, base_z, height, b.roof_shape, roof_h)
        if geom is None:
            continue
        V, F = geom
        meshes.append(trimesh.Trimesh(vertices=V, faces=F, process=False))

    for imp in scene.imported:
        if not wanted(imp.id):
            continue
        tf = edits.get(imp.id, {}).get("transform", imp.transform)
        V = _apply_transform(imp.vertices, tf)
        V[:, 0] *= factor
        V[:, 1] *= factor
        V[:, 2] *= vfac
        meshes.append(trimesh.Trimesh(vertices=V, faces=imp.faces, process=False))

    if not meshes:
        raise ValueError("no objects selected for export")

    combined = None
    if do_union and len(meshes) > 1:
        try:
            # manifold3d requires each input to be a valid volume (watertight +
            # consistent winding), so repair before unioning.
            prepared = []
            for m in meshes:
                m.merge_vertices()
                trimesh.repair.fix_normals(m)
                prepared.append(m)
            combined = trimesh.boolean.union(prepared)
        except Exception:
            combined = None  # fall back to concatenated solids

    if combined is None:
        combined = trimesh.util.concatenate(meshes)

    combined.merge_vertices()
    trimesh.repair.fix_normals(combined)
    return combined.export(file_type="stl")


def _apply_transform(V: np.ndarray, tf: dict) -> np.ndarray:
    """Scale (uniform) -> rotate about Z -> translate, in local meters."""
    s = float(tf.get("scale", 1.0))
    rz = float(tf.get("rotZ", 0.0))
    c, si = math.cos(rz), math.sin(rz)
    R = np.array([[c, -si, 0.0], [si, c, 0.0], [0.0, 0.0, 1.0]])
    out = (V * s) @ R.T
    out[:, 0] += float(tf.get("tx", 0.0))
    out[:, 1] += float(tf.get("ty", 0.0))
    out[:, 2] += float(tf.get("tz", 0.0))
    return out


IMPORT_TRIANGLE_BUDGET = 250_000  # keep preview + export responsive


def _load_trimesh(data: bytes, ext: str) -> trimesh.Trimesh:
    loaded = trimesh.load(io.BytesIO(data), file_type=ext, process=True)
    if isinstance(loaded, trimesh.Scene):
        geoms = [g for g in loaded.geometry.values()
                 if isinstance(g, trimesh.Trimesh)]
        if not geoms:
            raise ValueError("file contains no printable geometry")
        loaded = trimesh.util.concatenate(geoms)
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        raise ValueError("could not read a mesh from this file")
    return loaded


def _clean_mesh(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, int, int]:
    """Repair a possibly-messy imported mesh and cap its triangle count.

    Photogrammetry / splat meshes are often non-watertight and dense; merge
    duplicate vertices, drop degenerate faces, and decimate above the budget.
    Returns (mesh, original_triangles, final_triangles).
    """
    original = int(len(mesh.faces))
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()

    if len(mesh.faces) > IMPORT_TRIANGLE_BUDGET:
        try:
            mesh = mesh.simplify_quadric_decimation(
                face_count=IMPORT_TRIANGLE_BUDGET
            )
        except Exception:
            pass  # keep full-res if the decimator is unavailable

    if len(mesh.faces) == 0:
        raise ValueError("mesh had no valid faces after cleanup")
    return mesh, original, int(len(mesh.faces))


def import_mesh(sid: str, filename: str, data: bytes) -> dict:
    """Load an uploaded mesh, normalize it, and add it to the scene."""
    scene = get_scene(sid)
    if scene is None:
        raise KeyError("scene not found (rebuild the scene)")

    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    if ext not in ("obj", "stl", "ply", "glb", "gltf", "off"):
        raise ValueError(f"unsupported file type: .{ext}")

    mesh, tris_in, tris_out = _clean_mesh(_load_trimesh(data, ext))

    # Normalize: center on XY, base at z=0, max horizontal extent -> 1.0.
    V = np.asarray(mesh.vertices, dtype=np.float64)
    xmin, ymin, zmin = V.min(axis=0)
    xmax, ymax, _ = V.max(axis=0)
    V[:, 0] -= (xmin + xmax) / 2.0
    V[:, 1] -= (ymin + ymax) / 2.0
    V[:, 2] -= zmin
    span = max(xmax - xmin, ymax - ymin, 1e-6)
    V /= span

    # Default placement: terrain center, ~30% of the plate, sitting on terrain.
    cx = float((scene.dem.grid_x[0] + scene.dem.grid_x[-1]) / 2.0)
    cy = float((scene.dem.grid_y[0] + scene.dem.grid_y[-1]) / 2.0)
    tz = sample_grid(scene.dem.grid_x, scene.dem.grid_y, scene.dem.heights, cx, cy)
    transform = {"tx": cx, "ty": cy, "tz": float(tz),
                 "scale": round(0.3 * scene.extent_m, 2), "rotZ": 0.0}

    oid = f"import/{uuid.uuid4().hex[:8]}"
    name = filename.rsplit("/", 1)[-1]
    F = np.asarray(mesh.faces, dtype=np.int64)
    scene.imported.append(ImportedDef(oid, name, V, F, transform))

    meta = {"transform": transform, "triangles": tris_out}
    if tris_out < tris_in:
        meta["decimatedFrom"] = tris_in
    return _object_payload(oid, "imported", name, V, F, meta)


def _cache(scene: Scene) -> None:
    SCENES[scene.id] = scene
    SCENES.move_to_end(scene.id)
    while len(SCENES) > _MAX_SCENES:
        SCENES.popitem(last=False)


def get_scene(sid: str) -> Scene | None:
    scene = SCENES.get(sid)
    if scene is not None:
        SCENES.move_to_end(sid)
    return scene
