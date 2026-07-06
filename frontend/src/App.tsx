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
            disabled={status === "loading"}
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
