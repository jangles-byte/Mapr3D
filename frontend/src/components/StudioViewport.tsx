import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, GizmoHelper, GizmoViewport, Grid } from "@react-three/drei";
import { useStudio } from "../state/store";
import SceneMesh from "./SceneMesh";

function hint(status: string, error: string | null): string {
  if (status === "loading") return "Building scene — fetching elevation and buildings…";
  if (status === "error") return error ?? "Something went wrong.";
  return "Select a region on the map, then Build to pull it into 3D.";
}

export default function StudioViewport() {
  const objects = useStudio((s) => s.objects);
  const bounds = useStudio((s) => s.bounds);
  const status = useStudio((s) => s.status);
  const error = useStudio((s) => s.error);
  const select = useStudio((s) => s.select);

  const center = useMemo<[number, number]>(() => {
    if (!bounds) return [0, 0];
    return [
      (bounds.xRange[0] + bounds.xRange[1]) / 2,
      (bounds.yRange[0] + bounds.yRange[1]) / 2,
    ];
  }, [bounds]);

  const dist = bounds ? Math.max(bounds.extentM, 200) : 1500;

  return (
    <div className="viewport">
      <Canvas
        camera={{
          position: [dist * 0.55, dist * 0.7, dist * 0.65],
          near: 1,
          far: dist * 30,
          fov: 45,
        }}
        onPointerMissed={() => select(null)}
      >
        <color attach="background" args={["#0f1216"]} />
        <hemisphereLight intensity={0.75} groundColor={"#181c22"} />
        <directionalLight
          position={[dist, dist * 2, dist * 1.4]}
          intensity={1.4}
        />
        <group rotation={[-Math.PI / 2, 0, 0]}>
          <group position={[-center[0], -center[1], 0]}>
            {objects.map((o) => (
              <SceneMesh key={o.id} obj={o} zMax={bounds?.zMax ?? 1} />
            ))}
          </group>
        </group>
        <Grid
          args={[dist * 4, dist * 4]}
          cellSize={dist / 10}
          sectionSize={dist / 2}
          infiniteGrid
          fadeDistance={dist * 6}
          cellColor="#2a2f37"
          sectionColor="#3a4049"
          position={[0, -1, 0]}
        />
        <OrbitControls makeDefault target={[0, 0, 0]} maxDistance={dist * 10} />
        <GizmoHelper alignment="bottom-right" margin={[64, 64]}>
          <GizmoViewport labelColor="white" axisHeadScale={1} />
        </GizmoHelper>
      </Canvas>
      {status !== "ready" && (
        <div className={`viewport-hint ${status === "error" ? "is-error" : ""}`}>
          {hint(status, error)}
        </div>
      )}
    </div>
  );
}
