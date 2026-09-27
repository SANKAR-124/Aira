import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.video import videos
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
# App instance with Startup Event for cleanup
# ---------------------------------------------------------------------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    db: Session = SessionLocal()
    try:
        orphans = db.query(videos).filter(videos.processed_status == "processing").all()
        for v in orphans:
            logging.warning(f"Found orphaned video ID={v.id}. Marking as failed.")
            v.processed_status = "failed"
        if orphans:
            db.commit()
    except Exception as e:
        logging.error(f"Failed to cleanup orphaned videos: {e}")
    finally:
        db.close()
    
    yield
    # --- Shutdown ---
    pass

app = FastAPI(
    title="RCMP — Real-time Crowd Monitoring Platform",
    description=(
        "AI-powered backend for crowd density estimation, motion tracking, "
        "and risk scoring. Upload a video and receive per-frame analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (e.g. localhost:5173 for Vite)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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