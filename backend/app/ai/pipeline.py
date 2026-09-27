"""
Master AI Pipeline — Stage 7b
==============================
Orchestrates the full per-video analysis loop:
  1. Mark video as 'processing' in the DB.
  2. Read frames from the video file.
  3. Run density estimation (CSRNet) and motion tracking (Farneback) on every
     consecutive frame pair.
  4. Run the risk engine to get a score + level.
  5. For high/severe frames: overlay a heatmap, upload to Cloudinary, and save
     the alert image URL.
  6. Persist every frame's analytics to the `analytics_events` table.
  7. On success: mark video 'completed' and delete the local file.
  8. On any exception: mark video 'failed' and leave the local file for debug.
"""

import logging
import os
import tempfile

import cv2
import numpy as np

from app.ai.density_estimator import process_frame
from app.ai.motion_tracker import calculate_optical_flow
from app.ai.risk_engine import calculate_risk
from app.db.session import SessionLocal
from app.models.analytics_event import analytics_events
from app.models.video import videos
from app.services.cloudinary_service import upload_image

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _set_video_status(video_id: int, status: str) -> None:
    """Open a fresh DB session, update the video row, and close it."""
    db = SessionLocal()
    try:
        video_row = db.query(videos).filter(videos.id == video_id).first()
        if video_row is None:
            logger.error("_set_video_status: no video row found for id=%s", video_id)
            return
        video_row.processed_status = status
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update video status to '%s' for id=%s", status, video_id)
    finally:
        db.close()


def _build_heatmap_overlay(frame: np.ndarray, density_map: np.ndarray) -> np.ndarray:
    """
    Overlay a colourised density heatmap on the original BGR frame.

    The density map is a 2-D float32 array (typically H/8 × W/8 from CSRNet).
    We resize it to match the frame, normalise to 0-255, apply COLORMAP_JET,
    and blend it with the original frame at 50 % opacity.
    """
    h, w = frame.shape[:2]

    # Resize density map to match frame dimensions.
    density_resized = cv2.resize(density_map, (w, h), interpolation=cv2.INTER_LINEAR)

    # Normalise to uint8 [0, 255].
    d_min, d_max = density_resized.min(), density_resized.max()
    if d_max > d_min:
        density_norm = ((density_resized - d_min) / (d_max - d_min) * 255).astype(np.uint8)
    else:
        density_norm = np.zeros((h, w), dtype=np.uint8)

    # Apply jet colour map.
    heatmap_bgr = cv2.applyColorMap(density_norm, cv2.COLORMAP_JET)

    # Blend 50/50 with the original frame.
    overlay = cv2.addWeighted(frame, 0.5, heatmap_bgr, 0.5, 0)
    return overlay


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_pipeline(video_path: str, video_id: int) -> None:
    """
    Analyse a video file and persist analytics events to the database.

    Args:
        video_path: Absolute path to the saved video file.
        video_id:   Primary key of the corresponding `videos` row.
    """
    # ------------------------------------------------------------------
    # Step 1 — Mark as processing immediately (before anything else).
    # ------------------------------------------------------------------
    _set_video_status(video_id, "processing")
    logger.info("Pipeline started for video_id=%s  path=%s", video_id, video_path)

    cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Step 2 — Open the video and read the very first frame.
    # ------------------------------------------------------------------
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        _set_video_status(video_id, "failed")
        logger.error("cv2.VideoCapture could not open: %s", video_path)
        return

    ret, prev_frame = cap.read()
    if not ret or prev_frame is None:
        cap.release()
        _set_video_status(video_id, "failed")
        logger.error("Could not read the first frame from: %s", video_path)
        return

    fps: float = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_number: int = 0  # 0-indexed; prev_frame is frame 0

    # ------------------------------------------------------------------
    # Step 3 — Frame-processing loop (wrapped in try/except per spec).
    # ------------------------------------------------------------------
    try:
        db = SessionLocal()
        try:
            while True:
                ret, curr_frame = cap.read()
                if not ret or curr_frame is None:
                    break  # End of video — normal exit.

                frame_number += 1
                timestamp_sec: float = frame_number / fps

                # ---- Density estimation (CSRNet) ----------------------
                headcount, density_map = process_frame(curr_frame)

                # ---- Motion tracking (Farneback optical flow) ----------
                motion_speed: float = calculate_optical_flow(prev_frame, curr_frame)

                # ---- Risk engine ---------------------------------------
                risk_score, risk_level = calculate_risk(headcount, motion_speed)

                # ---- Alert image for high/severe frames ----------------
                alert_image_url: str | None = None
                if risk_level in ("high", "severe"):
                    overlay = _build_heatmap_overlay(curr_frame, density_map)

                    # Save the overlay to a temp file, upload, then remove.
                    with tempfile.NamedTemporaryFile(
                        suffix=".jpg", delete=False
                    ) as tmp:
                        tmp_path = tmp.name

                    try:
                        cv2.imwrite(tmp_path, overlay)
                        alert_image_url = upload_image(tmp_path)
                    finally:
                        if os.path.isfile(tmp_path):
                            os.remove(tmp_path)

                # ---- Persist analytics event row -----------------------
                event = analytics_events(
                    video_id=video_id,
                    frame_number=frame_number,
                    timestamp_sec=round(timestamp_sec, 3),
                    headcount=headcount,
                    motion_speed=round(motion_speed, 4),
                    risk_score=risk_score,
                    risk_level=risk_level,
                    alert_image_url=alert_image_url,
                )
                db.add(event)
                db.commit()

                logger.debug(
                    "frame=%d  headcount=%d  speed=%.3f  risk=%s(%d)  url=%s",
                    frame_number, headcount, motion_speed, risk_level, risk_score,
                    alert_image_url or "—",
                )

                # Advance the sliding window.
                prev_frame = curr_frame

        finally:
            db.close()

    except Exception:
        # ---- On any exception: log, release cap, mark failed -----------
        logger.exception(
            "Pipeline failed for video_id=%s at frame %d", video_id, frame_number
        )
        if cap is not None:
            cap.release()
        _set_video_status(video_id, "failed")
        # Leave the local video file in place for debugging (spec requirement).
        return

    # ------------------------------------------------------------------
    # Step 4 — Success path: release, delete local file, mark completed.
    # ------------------------------------------------------------------
    cap.release()
    logger.info(
        "Pipeline completed for video_id=%s — processed %d frames.",
        video_id, frame_number,
    )

    try:
        os.remove(video_path)
        logger.info("Deleted local video file: %s", video_path)
    except OSError:
        logger.warning("Could not delete local video file: %s", video_path)

    _set_video_status(video_id, "completed")
