import { useMemo } from "react";
import * as THREE from "three";
import { useStudio } from "../state/store";
import type { SceneObject } from "../types";

type Stop = [number, [number, number, number]];
const TERRAIN_RAMP: Stop[] = [
  [0.0, [0.16, 0.3, 0.2]],
  [0.35, [0.42, 0.47, 0.28]],
  [0.7, [0.55, 0.44, 0.31]],
  [1.0, [0.93, 0.93, 0.9]],
];

function rampColor(stops: Stop[], t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t));
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [t0, c0] = stops[i - 1];
      const [t1, c1] = stops[i];
      const f = (t - t0) / (t1 - t0 || 1);
      return [
        c0[0] + (c1[0] - c0[0]) * f,
        c0[1] + (c1[1] - c0[1]) * f,
        c0[2] + (c1[2] - c0[2]) * f,
      ];
    }
  }
  return stops[stops.length - 1][1];
}

function terrainColors(pos: Float32Array, zMax: number): THREE.BufferAttribute {
  const n = pos.length / 3;
  const col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const c = rampColor(TERRAIN_RAMP, pos[i * 3 + 2] / (zMax || 1));
    col[i * 3] = c[0];
    col[i * 3 + 1] = c[1];
    col[i * 3 + 2] = c[2];
  }
  return new THREE.BufferAttribute(col, 3);
}

export default function SceneMesh({ obj, zMax }: { obj: SceneObject; zMax: number }) {
  const selectedId = useStudio((s) => s.selectedId);
  const select = useStudio((s) => s.select);
  const selected = selectedId === obj.id;

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(obj.positions, 3));
    g.setIndex(new THREE.BufferAttribute(obj.indices, 1));
    g.computeVertexNormals();
    if (obj.type === "terrain") {
      g.setAttribute("color", terrainColors(obj.positions, zMax));
    }
    return g;
  }, [obj.positions, obj.indices, obj.type, zMax]);

  const baseZ = useMemo(() => {
    if (obj.type !== "building") return 0;
    let m = Infinity;
    for (let i = 2; i < obj.positions.length; i += 3) m = Math.min(m, obj.positions[i]);
    return Number.isFinite(m) ? m : 0;
  }, [obj.positions, obj.type]);

  if (!obj.visible) return null;
  const hs = obj.type === "building" ? obj.heightScale : 1;

  return (
    <mesh
      geometry={geometry}
      scale={[1, 1, hs]}
      position={[0, 0, baseZ * (1 - hs)]}
      onClick={(e) => {
        e.stopPropagation();
        select(obj.id);
      }}
    >
      {obj.type === "terrain" ? (
        <meshStandardMaterial vertexColors flatShading roughness={0.96} />
      ) : (
        <meshStandardMaterial
          color={selected ? "#f0997b" : "#8fb3d9"}
          emissive={selected ? "#d85a30" : "#000000"}
          emissiveIntensity={selected ? 0.55 : 0}
          roughness={0.6}
          metalness={0.05}
        />
      )}
    </mesh>
  );
}
