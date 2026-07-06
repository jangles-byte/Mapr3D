"""OpenStreetMap building footprints via the Overpass API."""

from __future__ import annotations

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "Mapr3D/0.1 (local 3D studio)"}


def fetch_buildings(w: float, s: float, e: float, n: float,
                    timeout: float = 45.0) -> list[dict]:
    """Return building footprints as ``[{id, rings, tags}]`` in lon/lat.

    ``rings`` is a list of outer rings (a way has one; a multipolygon may have
    several). Raises on network failure so the caller can decide to continue
    without buildings.
    """
    query = (
        "[out:json][timeout:40];"
        "("
        f'way["building"]({s},{w},{n},{e});'
        f'relation["building"]["type"="multipolygon"]({s},{w},{n},{e});'
        ");"
        "out geom;"
    )
    with httpx.Client(timeout=timeout, headers=UA) as client:
        r = client.post(OVERPASS_URL, data={"data": query})
        r.raise_for_status()
        data = r.json()

    out: list[dict] = []
    for el in data.get("elements", []):
        rings: list[list[tuple[float, float]]] = []
        if el.get("type") == "way" and el.get("geometry"):
            rings = [[(p["lon"], p["lat"]) for p in el["geometry"]]]
        elif el.get("type") == "relation":
            for m in el.get("members", []):
                if m.get("role") == "outer" and m.get("geometry"):
                    rings.append([(p["lon"], p["lat"]) for p in m["geometry"]])
        rings = [r_ for r_ in rings if len(r_) >= 3]
        if not rings:
            continue
        out.append({
            "id": f"{el['type']}/{el['id']}",
            "rings": rings,
            "tags": el.get("tags", {}),
        })
    return out


def building_height(tags: dict, default: float = 6.0) -> float:
    """Best-effort height in meters from OSM tags."""
    raw = tags.get("height") or tags.get("building:height")
    if raw:
        try:
            return float(str(raw).replace("m", "").split()[0])
        except (ValueError, IndexError):
            pass
    levels = tags.get("building:levels")
    if levels:
        try:
            return max(1.0, float(levels)) * 3.2
        except ValueError:
            pass
    return default


def building_name(tags: dict, fallback_id: str) -> str:
    return tags.get("name") or tags.get("building") or fallback_id.split("/")[-1]
