import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useStudio } from "../state/store";
import type { BBox } from "../types";

const STYLE = "https://demotiles.maplibre.org/style.json";

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
  const [drawing, setDrawing] = useState(false);
  const setBbox = useStudio((s) => s.setBbox);
  const bbox = useStudio((s) => s.bbox);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [-122.4194, 37.7749],
      zoom: 13,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-left");

    map.on("load", () => {
      map.addSource("sel", { type: "geojson", data: emptyFC() });
      map.addLayer({
        id: "sel-fill",
        type: "fill",
        source: "sel",
        paint: { "fill-color": "#f0997b", "fill-opacity": 0.22 },
      });
      map.addLayer({
        id: "sel-line",
        type: "line",
        source: "sel",
        paint: { "line-color": "#d85a30", "line-width": 2 },
      });
    });

    const setBox = (data: GeoJSON.Feature | null) => {
      const src = map.getSource("sel") as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(data ? { type: "FeatureCollection", features: [data] } : emptyFC());
    };

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

  const startDraw = () => {
    drawingRef.current = true;
    setDrawing(true);
    const map = mapRef.current;
    if (map) map.getCanvas().style.cursor = "crosshair";
  };

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map" />
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
