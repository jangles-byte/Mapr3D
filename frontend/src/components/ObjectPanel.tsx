import { useRef } from "react";
import { useStudio } from "../state/store";
import type { SceneObject } from "../types";

export default function ObjectPanel() {
  const objects = useStudio((s) => s.objects);
  const selectedId = useStudio((s) => s.selectedId);
  const sceneId = useStudio((s) => s.sceneId);
  const select = useStudio((s) => s.select);
  const toggle = useStudio((s) => s.toggleVisible);
  const remove = useStudio((s) => s.remove);
  const importMeshFile = useStudio((s) => s.importMeshFile);
  const fileRef = useRef<HTMLInputElement>(null);

  const terrain = objects.filter((o) => o.type === "terrain");
  const buildings = objects.filter((o) => o.type === "building");
  const imported = objects.filter((o) => o.type === "imported");
  const setAll = (vis: boolean) =>
    buildings.forEach((b) => b.visible !== vis && toggle(b.id));

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) importMeshFile(f);
    e.target.value = "";
  };

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

      {imported.length > 0 && (
        <>
          <div className="sub-h">
            <span>Imported</span>
            <span className="count">{imported.length}</span>
          </div>
          {imported.map(Row)}
        </>
      )}

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

      <input
        ref={fileRef}
        type="file"
        accept=".obj,.stl,.ply,.glb,.gltf,.off"
        style={{ display: "none" }}
        onChange={onFile}
      />
      <button
        className="btn small import-btn"
        disabled={!sceneId}
        title={
          sceneId
            ? "Add a high-detail mesh (3D Tiles, photogrammetry, splat)"
            : "Build a scene first"
        }
        onClick={() => fileRef.current?.click()}
      >
        + Import mesh…
      </button>
    </div>
  );
}
