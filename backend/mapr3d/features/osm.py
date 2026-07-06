"""OpenStreetMap building footprints via the Overpass API."""

from __future__ import annotations

import httpx

# Overpass is frequently rate-limited/busy; try mirrors in order.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
UA = {"User-Agent": "Mapr3D/0.1 (local 3D studio)"}


def _overpass_query(query: str, timeout: float) -> dict:
    last_exc: Exception | None = None
    with httpx.Client(timeout=timeout, headers=UA) as client:
        for url in OVERPASS_URLS:
            try:
                r = client.post(url, data={"data": query})
                r.raise_for_status()
                return r.json()
            except Exception as ex:  # rate limit / timeout / mirror down
                last_exc = ex
                continue
    raise last_exc if last_exc else RuntimeError("no Overpass endpoint responded")


def fetch_buildings(w: float, s: float, e: float, n: float,
                    timeout: float = 45.0) -> list[dict]:
    """Return building footprints as ``[{id, rings, tags}]`` in lon/lat.

    ``rings`` is a list of outer rings (a way has one; a multipolygon may have
    several). Raises if every Overpass mirror fails.
    """
    query = (
        "[out:json][timeout:40];"
        "("
        f'way["building"]({s},{w},{n},{e});'
        f'relation["building"]["type"="multipolygon"]({s},{w},{n},{e});'
        ");"
        "out geom;"
    )
    data = _overpass_query(query, timeout)

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
    """A human label for a footprint, avoiding raw tag values like "yes"."""
    if tags.get("name"):
        return tags["name"]
    hn, street = tags.get("addr:housenumber"), tags.get("addr:street")
    if hn and street:
        return f"{hn} {street}"
    btype = tags.get("building", "")
    if btype and btype not in ("yes", "true", "1"):
        return btype.replace("_", " ").capitalize()
    if hn:
        return f"No. {hn}"
    num = fallback_id.split("/")[-1]
    return f"Building {num[-4:]}" if num.isdigit() else "Building"
