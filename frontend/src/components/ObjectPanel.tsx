import { useStudio } from "../state/store";
import type { SceneObject } from "../types";

export default function ObjectPanel() {
  const objects = useStudio((s) => s.objects);
  const selectedId = useStudio((s) => s.selectedId);
  const select = useStudio((s) => s.select);
  const toggle = useStudio((s) => s.toggleVisible);
  const remove = useStudio((s) => s.remove);

  const terrain = objects.filter((o) => o.type === "terrain");
  const buildings = objects.filter((o) => o.type === "building");
  const setAll = (vis: boolean) =>
    buildings.forEach((b) => b.visible !== vis && toggle(b.id));

  const Row = (o: SceneObject) => (
    <div
      key={o.id}
      className={"obj-row" + (selectedId === o.id ? " sel" : "")}
      onClick={() => select(o.id)}
    >
      <button
        className="icon"
        title="Toggle visibility"
        onClick={(e) => {
          e.stopPropagation();
          toggle(o.id);
        }}
      >
        {o.visible ? "◉" : "○"}
      </button>
      <span className={"obj-name" + (o.visible ? "" : " off")}>{o.name}</span>
      <button
        className="icon"
        title="Delete"
        onClick={(e) => {
          e.stopPropagation();
          remove(o.id);
        }}
      >
        ✕
      </button>
    </div>
  );

  return (
    <div className="panel objects">
      <div className="panel-h">Scene</div>
      {objects.length === 0 && <div className="muted small">No objects yet.</div>}
      {terrain.map(Row)}
      {buildings.length > 0 && (
        <>
          <div className="sub-h">
            <span>Buildings</span>
            <span className="count">{buildings.length}</span>
            <span className="spacer" />
            <button className="link" onClick={() => setAll(true)}>
              show
            </button>
            <button className="link" onClick={() => setAll(false)}>
              hide
            </button>
          </div>
          <div className="obj-list">{buildings.map(Row)}</div>
        </>
      )}
    </div>
  );
}
