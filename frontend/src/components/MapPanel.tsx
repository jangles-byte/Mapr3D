import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useStudio } from "../state/store";
import type { BBox } from "../types";

type Basemap = "streets" | "satellite";

// Keyless, detailed raster basemaps (unlike MapLibre's demo style, which is
// just country polygons). Streets shows towns/roads/labels; satellite shows
// the actual buildings and terrain you're about to model.
const STYLES: Record<Basemap, maplibregl.StyleSpecification> = {
  streets: {
    version: 8,
    sources: {
      base: {
        type: "raster",
        tiles: [
          "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [{ id: "base", type: "raster", source: "base" }],
  },
  satellite: {
    version: 8,
    sources: {
      base: {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "Esri, Maxar, Earthstar Geographics",
      },
    },
    layers: [{ id: "base", type: "raster", source: "base" }],
  },
};

function emptyFC(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function boxFeature(a: maplibregl.LngLat, b: maplibregl.LngLat): GeoJSON.Feature {
  const w = Math.min(a.lng, b.lng),
    e = Math.max(a.lng, b.lng);
  const s = Math.min(a.lat, b.lat),
    n = Math.max(a.lat, b.lat);
  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    },
  };
}

function normBox(a: maplibregl.LngLat, b: maplibregl.LngLat): BBox {
  return [
    Math.min(a.lng, b.lng),
    Math.min(a.lat, b.lat),
    Math.max(a.lng, b.lng),
    Math.max(a.lat, b.lat),
  ];
}

export default function MapPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const drawingRef = useRef(false);
  const startRef = useRef<maplibregl.LngLat | null>(null);
  const boxRef = useRef<GeoJSON.Feature | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [basemap, setBasemap] = useState<Basemap>("streets");
  const setBbox = useStudio((s) => s.setBbox);
  const bbox = useStudio((s) => s.bbox);

  // Add / re-add the selection source + layers (setStyle wipes them).
  const addSelLayers = (map: maplibregl.Map) => {
    if (map.getSource("sel")) return;
    map.addSource("sel", {
      type: "geojson",
      data: boxRef.current
        ? { type: "FeatureCollection", features: [boxRef.current] }
        : emptyFC(),
    });
    map.addLayer({
      id: "sel-fill",
      type: "fill",
      source: "sel",
      paint: { "fill-color": "#f0997b", "fill-opacity": 0.25 },
    });
    map.addLayer({
      id: "sel-line",
      type: "line",
      source: "sel",
      paint: { "line-color": "#d85a30", "line-width": 2 },
    });
  };

  const setBox = (data: GeoJSON.Feature | null) => {
    boxRef.current = data;
    const map = mapRef.current;
    const src = map?.getSource("sel") as maplibregl.GeoJSONSource | undefined;
    if (src) {
      src.setData(
        data ? { type: "FeatureCollection", features: [data] } : emptyFC()
      );
    }
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLES.streets,
      center: [-122.4194, 37.7749],
      zoom: 14,
      maxZoom: 19,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-left");

    map.on("load", () => addSelLayers(map));
    // After a basemap swap the style reloads; re-add our selection layers.
    map.on("styledata", () => addSelLayers(map));

    map.on("mousedown", (e) => {
      if (!drawingRef.current) return;
      startRef.current = e.lngLat;
      map.dragPan.disable();
    });
    map.on("mousemove", (e) => {
      if (!drawingRef.current || !startRef.current) return;
      setBox(boxFeature(startRef.current, e.lngLat));
    });
    map.on("mouseup", (e) => {
      if (!drawingRef.current || !startRef.current) return;
      setBox(boxFeature(startRef.current, e.lngLat));
      setBbox(normBox(startRef.current, e.lngLat));
      startRef.current = null;
      drawingRef.current = false;
      setDrawing(false);
      map.dragPan.enable();
      map.getCanvas().style.cursor = "";
    });

    return () => map.remove();
  }, [setBbox]);

  const switchBasemap = (next: Basemap) => {
    setBasemap(next);
    mapRef.current?.setStyle(STYLES[next]);
  };

  const startDraw = () => {
    drawingRef.current = true;
    setDrawing(true);
    const map = mapRef.current;
    if (map) map.getCanvas().style.cursor = "crosshair";
  };

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map" />
      <div className="map-top">
        <div className="seg">
          <button
            className={basemap === "streets" ? "seg-btn on" : "seg-btn"}
            onClick={() => switchBasemap("streets")}
          >
            Streets
          </button>
          <button
            className={basemap === "satellite" ? "seg-btn on" : "seg-btn"}
            onClick={() => switchBasemap("satellite")}
          >
            Satellite
          </button>
        </div>
      </div>
      <div className="map-tools">
        <button className={drawing ? "btn btn-accent" : "btn"} onClick={startDraw}>
          {drawing ? "Drag a box on the map…" : "Select region"}
        </button>
        {bbox && !drawing && (
          <span className="map-bbox">
            {bbox[1].toFixed(3)}, {bbox[0].toFixed(3)} →{" "}
            {bbox[3].toFixed(3)}, {bbox[2].toFixed(3)}
          </span>
        )}
      </div>
    </div>
  );
}
