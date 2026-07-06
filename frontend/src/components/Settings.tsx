import { useStudio } from "../state/store";

export default function Settings() {
  const p = useStudio((s) => s.params);
  const setParam = useStudio((s) => s.setParam);
  const bounds = useStudio((s) => s.bounds);
  const hasLidarKey = useStudio((s) => s.hasLidarKey);

  const mPerMm = bounds ? bounds.extentM / p.scaleMM : null;

  return (
    <div className="panel">
      <div className="panel-h">Print settings</div>

      <label className="field">
        <span>Model size (longest edge) · {p.scaleMM} mm</span>
        <input
          type="range"
          min={40}
          max={300}
          step={5}
          value={p.scaleMM}
          onChange={(e) => setParam("scaleMM", +e.target.value)}
        />
      </label>

      <label className="field">
        <span>Base thickness · {p.baseThicknessMM} mm</span>
        <input
          type="range"
          min={0}
          max={12}
          step={0.5}
          value={p.baseThicknessMM}
          onChange={(e) => setParam("baseThicknessMM", +e.target.value)}
        />
      </label>

      <label className="field">
        <span>Vertical exaggeration · ×{p.zExaggeration.toFixed(1)}</span>
        <input
          type="range"
          min={1}
          max={4}
          step={0.1}
          value={p.zExaggeration}
          onChange={(e) => setParam("zExaggeration", +e.target.value)}
        />
      </label>

      {mPerMm !== null && (
        <div className="readout">
          1 mm ≈ {mPerMm.toFixed(1)} m · smallest printable feature ≈{" "}
          {(0.4 * mPerMm).toFixed(1)} m
        </div>
      )}

      <label className="check">
        <input
          type="checkbox"
          checked={p.includeBuildings}
          onChange={(e) => setParam("includeBuildings", e.target.checked)}
        />
        Include buildings (OpenStreetMap)
      </label>

      <label className="field">
        <span>Elevation source</span>
        <select
          value={p.demSource}
          onChange={(e) => setParam("demSource", e.target.value as any)}
        >
          <option value="auto">Auto — best available</option>
          <option value="opentopography">OpenTopography lidar (needs key)</option>
          <option value="synthetic">Synthetic — offline demo</option>
        </select>
      </label>

      {p.demSource === "opentopography" && (
        <div className={hasLidarKey ? "readout" : "readout warn"}>
          {hasLidarKey
            ? "US regions get 1 m 3DEP lidar; elsewhere Copernicus 30 m."
            : "No OpenTopography key set — add OPENTOPOGRAPHY_API_KEY to backend/.env for 1 m lidar. Falls back to terrain tiles until then."}
        </div>
      )}
    </div>
  );
}
