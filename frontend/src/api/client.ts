import type { BBox, BuildResponse } from "../types";

const API = "/api";

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getConfig(): Promise<{ openTopographyKey: boolean }> {
  return jsonOrThrow(await fetch(`${API}/config`));
}

export async function buildScene(args: {
  bbox: BBox;
  includeBuildings: boolean;
  demSource: string;
  resolution: number;
}): Promise<BuildResponse> {
  const res = await fetch(`${API}/scene/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bbox: args.bbox,
      includeBuildings: args.includeBuildings,
      demSource: args.demSource,
      resolution: args.resolution,
    }),
  });
  return jsonOrThrow(res);
}

export async function exportScene(args: {
  sceneId: string;
  includedIds: string[];
  scaleMM: number;
  baseThicknessMM: number;
  zExaggeration: number;
  edits: Record<string, { hidden?: boolean; heightScale?: number }>;
  union: boolean;
}): Promise<Blob> {
  const res = await fetch(`${API}/scene/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.blob();
}
