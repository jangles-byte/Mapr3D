export interface Bounds {
  extentM: number;
  xRange: [number, number];
  yRange: [number, number];
  zMax: number;
}

export interface RawObject {
  id: string;
  type: string;
  name: string;
  positions: number[];
  indices: number[];
  vertexCount: number;
  meta: Record<string, any>;
}

export interface BuildResponse {
  sceneId: string;
  objects: RawObject[];
  dem: { source: string; quality: string; zoom: number };
  bounds: Bounds;
  buildingCount: number;
  suggestedScaleMM: number;
  notes: string[];
}

export interface Transform {
  tx: number;
  ty: number;
  tz: number;
  scale: number;
  rotZ: number;
}

export interface SceneObject {
  id: string;
  type: string;
  name: string;
  positions: Float32Array;
  indices: Uint32Array;
  meta: Record<string, any>;
  visible: boolean;
  heightScale: number;
  transform?: Transform;
}

export type BBox = [number, number, number, number]; // [w, s, e, n]

export interface ExportParams {
  scaleMM: number;
  baseThicknessMM: number;
  zExaggeration: number;
  includeBuildings: boolean;
  demSource: "auto" | "opentopography" | "synthetic";
  union: boolean;
  resolution: number; // terrain heightfield grid detail (max dimension)
}
