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
from app.models.analytics_event import analytics_events
from app.schemas.video_schema import VideoUploadResponse
from app.services.cloudinary_service import delete_image

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

def _background_delete_images(urls: list[str]) -> None:
    """Helper to delete multiple Cloudinary images in the background."""
    for url in urls:
        try:
            delete_image(url)
        except Exception as e:
            logger.error(f"Failed to delete Cloudinary image: {e}")

@router.delete(
    "/{video_id}",
    status_code=200,
    summary="Delete a video and all its data",
    description="Deletes the local video file, Cloudinary alert images, and all database records for this video."
)
def delete_video(video_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Fetch video
    video_row = db.query(videos).filter(videos.id == video_id).first()
    if not video_row:
        raise HTTPException(status_code=404, detail="Video not found")
        
    # 2. Delete Cloudinary images associated with this video (IN BACKGROUND)
    events_with_images = db.query(analytics_events).filter(
        analytics_events.video_id == video_id,
        analytics_events.alert_image_url.is_not(None)
    ).all()
    
    urls_to_delete = [event.alert_image_url for event in events_with_images]
    if urls_to_delete:
        background_tasks.add_task(_background_delete_images, urls_to_delete)
            
    # 3. Delete local video file if it exists
    save_path = os.path.join(TEMP_VIDEO_DIR, video_row.original_filename)
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
            logger.info(f"Deleted local video file: {save_path}")
        except Exception as e:
            logger.error(f"Failed to delete local video file: {e}")
            
    # 4. Delete from DB (analytics_events cascade automatically)
    db.delete(video_row)
    db.commit()
    
    return {"message": "Video and all associated data deleted successfully"}
