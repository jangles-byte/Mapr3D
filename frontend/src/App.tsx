import { useEffect } from "react";
import MapPanel from "./components/MapPanel";
import StudioViewport from "./components/StudioViewport";
import ObjectPanel from "./components/ObjectPanel";
import Inspector from "./components/Inspector";
import Settings from "./components/Settings";
import { useStudio } from "./state/store";

export default function App() {
  const build = useStudio((s) => s.build);
  const exportStl = useStudio((s) => s.exportStl);
  const status = useStudio((s) => s.status);
  const exporting = useStudio((s) => s.exporting);
  const dem = useStudio((s) => s.dem);
  const error = useStudio((s) => s.error);
  const buildingCount = useStudio((s) => s.buildingCount);
  const hasScene = useStudio((s) => s.objects.length > 0);
  const bbox = useStudio((s) => s.bbox);
  const notes = useStudio((s) => s.notes);
  const loadConfig = useStudio((s) => s.loadConfig);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Mapr3D <span className="tag">map → STL studio</span>
        </div>
        <div className="top-actions">
          {dem && (
            <span className="badge" title={dem.source}>
              {dem.quality}
            </span>
          )}
          {hasScene && (
            <span className="muted small">{buildingCount} buildings</span>
          )}
          {error && <span className="err small">{error}</span>}
          <button
            className="btn btn-accent"
            onClick={build}
            disabled={status === "loading" || !bbox}
            title={bbox ? "" : "Select a region on the map first"}
          >
            {status === "loading" ? "Building…" : "Build 3D"}
          </button>
          <button
            className="btn"
            onClick={exportStl}
            disabled={!hasScene || exporting}
          >
            {exporting ? "Exporting…" : "Export STL"}
          </button>
        </div>
      </header>

      {notes.length > 0 && (
        <div className="notes-bar">
          {notes.map((n, i) => (
            <span key={i} className="note">
              {n}
            </span>
          ))}
        </div>
      )}

      <div className="body">
        <aside className="left">
          <MapPanel />
          <ObjectPanel />
        </aside>
        <main className="center">
          <StudioViewport />
        </main>
        <aside className="right">
          <Settings />
          <Inspector />
        </aside>
      </div>
    </div>
  );
}
