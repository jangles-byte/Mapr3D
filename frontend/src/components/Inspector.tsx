import { useStudio } from "../state/store";

export default function Inspector() {
  const objects = useStudio((s) => s.objects);
  const selectedId = useStudio((s) => s.selectedId);
  const setHeightScale = useStudio((s) => s.setHeightScale);
  const setTransform = useStudio((s) => s.setTransform);
  const bounds = useStudio((s) => s.bounds);
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

      {obj.type === "imported" && obj.transform && bounds && (
        <>
          <div className="kv">
            <span>Triangles</span>
            <b>{(obj.meta.triangles ?? 0).toLocaleString()}</b>
          </div>
          <label className="field">
            <span>Scale · {Math.round(obj.transform.scale)} m</span>
            <input
              type="range"
              min={Math.round(bounds.extentM * 0.02)}
              max={Math.round(bounds.extentM * 1.2)}
              step={1}
              value={obj.transform.scale}
              onChange={(e) => setTransform(obj.id, { scale: +e.target.value })}
            />
          </label>
          <label className="field">
            <span>Rotation · {Math.round((obj.transform.rotZ * 180) / Math.PI)}°</span>
            <input
              type="range"
              min={0}
              max={Math.PI * 2}
              step={0.02}
              value={obj.transform.rotZ}
              onChange={(e) => setTransform(obj.id, { rotZ: +e.target.value })}
            />
          </label>
          <label className="field">
            <span>Move east–west</span>
            <input
              type="range"
              min={bounds.xRange[0]}
              max={bounds.xRange[1]}
              step={1}
              value={obj.transform.tx}
              onChange={(e) => setTransform(obj.id, { tx: +e.target.value })}
            />
          </label>
          <label className="field">
            <span>Move north–south</span>
            <input
              type="range"
              min={bounds.yRange[0]}
              max={bounds.yRange[1]}
              step={1}
              value={obj.transform.ty}
              onChange={(e) => setTransform(obj.id, { ty: +e.target.value })}
            />
          </label>
          <label className="field">
            <span>Height · {Math.round(obj.transform.tz)} m</span>
            <input
              type="range"
              min={-Math.round(bounds.zMax)}
              max={Math.round(bounds.zMax * 3 + 100)}
              step={1}
              value={obj.transform.tz}
              onChange={(e) => setTransform(obj.id, { tz: +e.target.value })}
            />
          </label>
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
