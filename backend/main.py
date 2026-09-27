import logging

from fastapi import FastAPI

from app.routes.video_route import video_router
from app.routes.analytics_route import analytics_router

# ---------------------------------------------------------------------------
# Logging — shows pipeline progress in the terminal during development.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RCMP — Real-time Crowd Monitoring Platform",
    description=(
        "AI-powered backend for crowd density estimation, motion tracking, "
        "and risk scoring. Upload a video and receive per-frame analytics."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(video_router)
app.include_router(analytics_router)


# ---------------------------------------------------------------------------
# Health-check endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def home():
    return {"message": "Welcome to RCMP Backend"}


@app.get("/health", tags=["Health"])
def health():
    return {"message": "api healthy"}