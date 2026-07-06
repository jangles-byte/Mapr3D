# Mapr3D

A local **3D studio that pulls from maps**. Pick any place on Earth, load it into an
editable 3D scene where *anything is printable*, select and refine individual objects
(terrain, buildings, water, imported meshes), then export a watertight STL for printing.

Not a one-shot terrain mesher — a scene editor. Objects stay discrete and editable; the
printable solid is a *compile step* at export time.

## Why it's built this way

- **Detail comes from data, not software.** The whole system is a data-sourcing pipeline
  with a studio UI on top. The data layer picks the best available source per region.
- **Keep objects separate.** The scene is a graph of discrete meshes. They are only
  boolean-unioned into one solid at export. That is what makes "pull a structure out and
  refine it" possible.
- **Runs locally, no keys required.** Elevation comes from keyless global terrain tiles
  (AWS Terrain Tiles); buildings from OpenStreetMap. Optional high-res sources
  (OpenTopography USGS 1 m lidar) plug in with an API key.

## Architecture

```
frontend/   Vite + React + react-three-fiber studio, MapLibre region picker
backend/    FastAPI: DEM resolver, OSM features, meshing, STL export
```

Pipeline: pick region -> fetch best-available DEM + OSM -> build scene graph ->
edit / refine -> boolean-union + base -> export STL.

## Data sources (best per region)

| Region      | Source                                  | Resolution | Key |
|-------------|-----------------------------------------|-----------|-----|
| Global      | AWS Terrain Tiles (Terrarium)           | ~ tile zoom (blended 3DEP/SRTM) | no |
| US high-res | OpenTopography USGS 3DEP 1 m            | 1 m       | yes |
| Global DEM  | OpenTopography SRTM / Copernicus        | 30 m      | yes |
| Buildings   | OpenStreetMap (Overpass API)            | footprints + heights | no |

## Quickstart

Easiest on macOS: **double-click `Mapr3D.command`** in Finder. It opens Terminal,
installs dependencies on first run, and starts both servers.

Or from a terminal:

```bash
./run.sh
```

Then open http://localhost:5173. Press Ctrl+C to stop.

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node.js. Ports are
configurable via `MAPR3D_BACKEND_PORT` / `MAPR3D_FRONTEND_PORT`.

<details>
<summary>Run the servers manually instead</summary>

```bash
# backend
cd backend && uv sync && uv run uvicorn mapr3d.main:app --reload --port 8000
# frontend (separate terminal)
cd frontend && npm install && npm run dev
```

</details>

## Status

Early build. See the pipeline stages in `backend/mapr3d/` and the studio in
`frontend/src/`.

## Roadmap

- [x] Repo scaffold
- [x] DEM resolver (keyless terrain tiles + synthetic fallback)
- [x] Terrain -> watertight solid
- [x] Map region picker + 3D studio viewport
- [x] OSM buildings as selectable objects
- [x] Editing: hide / delete / height scale
- [x] STL export (watertight, scaled, base + vertical exaggeration)
- [x] High-res lidar channel with graceful fallback (OpenTopography key)
- [x] Boolean-union single-manifold export toggle
- [x] Terrain detail (resolution) control
- [x] Detailed basemaps (OSM streets + Esri satellite)
- [x] Mesh-import injector — drop OBJ/STL/PLY/GLB meshes (3D Tiles /
      photogrammetry / Gaussian-splat exports) onto the terrain, place and
      scale them, export welded in
- [ ] Direct Google 3D Tiles fetch by region (auto-import, no manual export)
- [ ] Terrain refine ops (flatten a selected patch)
