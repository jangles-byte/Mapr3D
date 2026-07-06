"""FastAPI application entry point."""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

load_dotenv()

app = FastAPI(title="Mapr3D", version="0.1.0",
              description="Local map-to-STL 3D studio backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": "Mapr3D backend", "docs": "/docs", "health": "/api/health"}
