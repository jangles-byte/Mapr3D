import { create } from "zustand";
import { buildScene, exportScene, getConfig, importMesh } from "../api/client";
import type { BBox, Bounds, ExportParams, SceneObject, Transform } from "../types";

type Status = "idle" | "loading" | "ready" | "error";

interface StudioState {
  bbox: BBox | null;
  sceneId: string | null;
  objects: SceneObject[];
  bounds: Bounds | null;
  dem: { source: string; quality: string; zoom: number } | null;
  buildingCount: number;
  selectedId: string | null;
  status: Status;
  error: string | null;
  notes: string[];
  exporting: boolean;
  importing: boolean;
  hasLidarKey: boolean;
  params: ExportParams;

  loadConfig: () => Promise<void>;
  setBbox: (b: BBox) => void;
  setParam: <K extends keyof ExportParams>(k: K, v: ExportParams[K]) => void;
  build: () => Promise<void>;
  select: (id: string | null) => void;
  toggleVisible: (id: string) => void;
  remove: (id: string) => void;
  setHeightScale: (id: string, v: number) => void;
  importMeshFile: (file: File) => Promise<void>;
  setTransform: (id: string, partial: Partial<Transform>) => void;
  exportStl: () => Promise<void>;
}

export const useStudio = create<StudioState>((set, get) => ({
  bbox: null,
  sceneId: null,
  objects: [],
  bounds: null,
  dem: null,
  buildingCount: 0,
  selectedId: null,
  status: "idle",
  error: null,
  notes: [],
  exporting: false,
  importing: false,
  hasLidarKey: false,
  params: {
    scaleMM: 180,
    baseThicknessMM: 3,
    zExaggeration: 1.5,
    includeBuildings: true,
    demSource: "auto",
    union: false,
    resolution: 220,
  },

  loadConfig: async () => {
    try {
      const c = await getConfig();
      set({ hasLidarKey: c.openTopographyKey });
    } catch {
      /* backend not up yet; ignore */
    }
  },

  setBbox: (b) => set({ bbox: b }),
  setParam: (k, v) =>
    set((s) => ({ params: { ...s.params, [k]: v } })),

  build: async () => {
    const { bbox, params } = get();
    if (!bbox) {
      set({ error: "Draw a region on the map first." });
      return;
    }
    set({ status: "loading", error: null, notes: [], selectedId: null });
    try {
      const res = await buildScene({
        bbox,
        includeBuildings: params.includeBuildings,
        demSource: params.demSource,
        resolution: params.resolution,
      });
      const objects: SceneObject[] = res.objects.map((o) => ({
        id: o.id,
        type: o.type,
        name: o.name,
        positions: new Float32Array(o.positions),
        indices: new Uint32Array(o.indices),
        meta: o.meta,
        visible: true,
        heightScale: 1,
      }));
      set({
        sceneId: res.sceneId,
        objects,
        bounds: res.bounds,
        dem: res.dem,
        buildingCount: res.buildingCount,
        notes: res.notes ?? [],
        status: "ready",
        params: { ...params, scaleMM: res.suggestedScaleMM || params.scaleMM },
      });
    } catch (e: any) {
      set({ status: "error", error: e.message ?? String(e) });
    }
  },

  select: (id) => set({ selectedId: id }),
  toggleVisible: (id) =>
    set((s) => ({
      objects: s.objects.map((o) =>
        o.id === id ? { ...o, visible: !o.visible } : o
      ),
    })),
  remove: (id) =>
    set((s) => ({
      objects: s.objects.filter((o) => o.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    })),
  setHeightScale: (id, v) =>
    set((s) => ({
      objects: s.objects.map((o) =>
        o.id === id ? { ...o, heightScale: v } : o
      ),
    })),

  importMeshFile: async (file) => {
    const { sceneId } = get();
    if (!sceneId) {
      set({ error: "Build a scene first, then import a mesh into it." });
      return;
    }
    set({ error: null, importing: true });
    try {
      const o = await importMesh(sceneId, file);
      const obj: SceneObject = {
        id: o.id,
        type: o.type,
        name: o.name,
        positions: new Float32Array(o.positions),
        indices: new Uint32Array(o.indices),
        meta: o.meta,
        visible: true,
        heightScale: 1,
        transform: o.meta.transform as Transform,
      };
      set((s) => ({ objects: [...s.objects, obj], selectedId: o.id }));
    } catch (e: any) {
      set({ error: e.message ?? String(e) });
    } finally {
      set({ importing: false });
    }
  },

  setTransform: (id, partial) =>
    set((s) => ({
      objects: s.objects.map((o) =>
        o.id === id && o.transform
          ? { ...o, transform: { ...o.transform, ...partial } }
          : o
      ),
    })),

  exportStl: async () => {
    const { sceneId, objects, params } = get();
    if (!sceneId) {
      set({ error: "Build a scene first." });
      return;
    }
    set({ exporting: true, error: null });
    try {
      const visible = objects.filter((o) => o.visible);
      const edits: Record<string, any> = {};
      for (const o of objects) {
        if (o.type === "building" && o.heightScale !== 1) {
          edits[o.id] = { heightScale: o.heightScale };
        }
        if (o.type === "imported" && o.transform) {
          edits[o.id] = { transform: o.transform };
        }
      }
      const blob = await exportScene({
        sceneId,
        includedIds: visible.map((o) => o.id),
        scaleMM: params.scaleMM,
        baseThicknessMM: params.baseThicknessMM,
        zExaggeration: params.zExaggeration,
        edits,
        union: params.union,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mapr3d_${sceneId}.stl`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      set({ error: e.message ?? String(e) });
    } finally {
      set({ exporting: false });
    }
  },
}));
