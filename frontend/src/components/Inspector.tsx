import { useStudio } from "../state/store";

export default function Inspector() {
  const objects = useStudio((s) => s.objects);
  const selectedId = useStudio((s) => s.selectedId);
  const setHeightScale = useStudio((s) => s.setHeightScale);
  const toggle = useStudio((s) => s.toggleVisible);
  const remove = useStudio((s) => s.remove);
  const obj = objects.find((o) => o.id === selectedId) ?? null;

  if (!obj) {
    return (
      <div className="panel">
        <div className="panel-h">Inspector</div>
        <div className="muted small">Click an object to inspect and refine it.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-h">Inspector</div>
      <div className="kv">
        <span>Name</span>
        <b className="wrap">{obj.name}</b>
      </div>
      <div className="kv">
        <span>Type</span>
        <b>{obj.type}</b>
      </div>

      {obj.type === "terrain" && (
        <>
          <div className="kv">
            <span>Source</span>
            <b className="wrap">{obj.meta.source}</b>
          </div>
          <div className="kv">
            <span>Quality</span>
            <b>{obj.meta.quality}</b>
          </div>
          <div className="kv">
            <span>Relief</span>
            <b>{Math.round(obj.meta.zRange?.[1] ?? 0)} m</b>
          </div>
        </>
      )}

      {obj.type === "building" && (
        <>
          <div className="kv">
            <span>Height</span>
            <b>{Math.round(obj.meta.height)} m</b>
          </div>
          <div className="kv">
            <span>Footprint</span>
            <b>{Math.round(obj.meta.area)} m²</b>
          </div>
          <label className="field">
            <span>Height scale ×{obj.heightScale.toFixed(1)}</span>
            <input
              type="range"
              min={0.2}
              max={3}
              step={0.1}
              value={obj.heightScale}
              onChange={(e) => setHeightScale(obj.id, parseFloat(e.target.value))}
            />
          </label>
        </>
      )}

      <div className="row-btns">
        <button className="btn small" onClick={() => toggle(obj.id)}>
          {obj.visible ? "Hide" : "Show"}
        </button>
        <button className="btn small danger" onClick={() => remove(obj.id)}>
          Delete
        </button>
      </div>
    </div>
  );
}
