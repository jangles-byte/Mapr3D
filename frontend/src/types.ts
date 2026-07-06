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
}

export type BBox = [number, number, number, number]; // [w, s, e, n]

export interface ExportParams {
  scaleMM: number;
  baseThicknessMM: number;
  zExaggeration: number;
  includeBuildings: boolean;
  demSource: "auto" | "opentopography" | "synthetic";
  union: boolean;
}
