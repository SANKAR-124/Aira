"""
Video Controller — Stage 8
============================
Handles POST /videos/upload:
  1. Validates & saves the uploaded file to temp_videos/.
  2. Creates a `videos` DB row with status 'pending'.
  3. Fires run_pipeline() as a FastAPI BackgroundTask so the HTTP response
     is returned to the caller immediately while processing runs async.
"""

import logging
import os
import shutil

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.ai.pipeline import run_pipeline
from app.db.session import get_db
from app.models.video import videos
from app.schemas.video_schema import VideoUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["Videos"])

# Directory where uploaded video files are saved before processing.
TEMP_VIDEO_DIR = "temp_videos"


def _ensure_temp_dir() -> None:
    """Create temp_videos/ if it doesn't already exist."""
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=202,
    summary="Upload a crowd video for AI analysis",
    description=(
        "Accepts a video file, saves it to `temp_videos/`, creates a DB record "
        "with status **pending**, and immediately starts the AI pipeline in the "
        "background. Returns 202 Accepted with the new video record."
    ),
)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file to analyse (mp4, avi, etc.)"),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    POST /videos/upload
    -------------------
    • Saves uploaded file  → temp_videos/<original_filename>
    • Creates videos row   → status = 'pending'
    • Enqueues pipeline    → BackgroundTasks (non-blocking)
    • Returns 202          → VideoUploadResponse
    """
    _ensure_temp_dir()

    # ---- 1. Persist the file -------------------------------------------------
    safe_filename = os.path.basename(file.filename or "upload.mp4")
    save_path = os.path.join(TEMP_VIDEO_DIR, safe_filename)

    # If a file with the same name already exists, make the name unique.
    base, ext = os.path.splitext(safe_filename)
    counter = 1
    while os.path.exists(save_path):
        save_path = os.path.join(TEMP_VIDEO_DIR, f"{base}_{counter}{ext}")
        counter += 1

    try:
        with open(save_path, "wb") as out_file:
            shutil.copyfileobj(file.file, out_file)
    except OSError as exc:
        logger.exception("Failed to save uploaded file: %s", save_path)
        raise HTTPException(status_code=500, detail=f"Could not save file: {exc}") from exc
    finally:
        await file.close()

    logger.info("Saved uploaded video → %s", save_path)

    # ---- 2. Create DB row with status 'pending' ------------------------------
    video_row = videos(
        original_filename=safe_filename,
        processed_status="pending",
    )
    db.add(video_row)
    db.commit()
    db.refresh(video_row)

    logger.info("Created videos row id=%d  filename=%s", video_row.id, safe_filename)

    # ---- 3. Fire the AI pipeline as a background task -----------------------
    # run_pipeline() opens its own DB sessions internally, so we pass only
    # the file path and the DB primary key — no session objects are shared
    # across thread boundaries.
    abs_save_path = os.path.abspath(save_path)
    background_tasks.add_task(run_pipeline, abs_save_path, video_row.id)

    logger.info("Background pipeline queued for video_id=%d", video_row.id)

    # ---- 4. Return 202 immediately -------------------------------------------
    return VideoUploadResponse.model_validate(video_row)
