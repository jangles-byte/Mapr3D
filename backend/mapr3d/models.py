"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BuildRequest(BaseModel):
    bbox: list[float] = Field(..., description="[west, south, east, north] degrees")
    includeBuildings: bool = True
    demSource: str = "auto"  # auto | opentopography | synthetic
    maxBuildings: int = 1500
    resolution: int = 220    # max heightfield grid dimension

    @field_validator("bbox")
    @classmethod
    def _valid_bbox(cls, v: list[float]) -> list[float]:
        if len(v) != 4:
            raise ValueError("bbox must be [west, south, east, north]")
        w, s, e, n = v
        if not (w < e and s < n):
            raise ValueError("require west < east and south < north")
        if (e - w) > 2.0 or (n - s) > 2.0:
            raise ValueError("bbox too large; select a smaller region")
        return v


class ExportRequest(BaseModel):
    sceneId: str
    includedIds: list[str] = Field(default_factory=list)
    scaleMM: float = 180.0            # longest horizontal edge of the model
    baseThicknessMM: float = 3.0
    zExaggeration: float = 1.5
    edits: dict[str, dict] = Field(default_factory=dict)  # id -> {heightScale}
    union: bool = False              # attempt single-manifold boolean union
