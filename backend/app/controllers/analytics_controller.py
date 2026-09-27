"""
Analytics Controller — Stage 9
================================
Public read-only API that exposes crowd-monitoring data for dashboard
consumption.  No authentication required (per spec).

Endpoints:
  GET /videos                         — list all video records
  GET /videos/{video_id}/events       — full frame-by-frame timeline for one video
  GET /alerts/high-risk               — all events where risk_level is high or severe
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.analytics_event import analytics_events
from app.models.video import videos
from app.schemas.analytics_schema import AnalyticsEventResponse, VideoResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])


# ---------------------------------------------------------------------------
# GET /videos — list all video records
# ---------------------------------------------------------------------------

@router.get(
    "/videos",
    response_model=List[VideoResponse],
    summary="List all uploaded videos",
    description=(
        "Returns every row in the `videos` table ordered by most recent first, "
        "including the current processing status."
    ),
)
def list_videos(db: Session = Depends(get_db)) -> List[VideoResponse]:
    rows = db.query(videos).order_by(videos.id.desc()).all()
    return rows


# ---------------------------------------------------------------------------
# GET /videos/{video_id}/events — full analytics timeline for one video
# ---------------------------------------------------------------------------

@router.get(
    "/videos/{video_id}/events",
    response_model=List[AnalyticsEventResponse],
    summary="Get full analytics timeline for a video",
    description=(
        "Returns every `analytics_events` row for the given video, ordered "
        "chronologically by frame number.  Suitable for time-series graphing."
    ),
)
def get_video_events(
    video_id: int,
    db: Session = Depends(get_db),
) -> List[AnalyticsEventResponse]:
    # Verify the video exists first — return 404 if not.
    video_row = db.query(videos).filter(videos.id == video_id).first()
    if video_row is None:
        raise HTTPException(status_code=404, detail=f"Video with id={video_id} not found.")

    rows = (
        db.query(analytics_events)
        .filter(analytics_events.video_id == video_id)
        .order_by(analytics_events.frame_number.asc())
        .all()
    )
    return rows


# ---------------------------------------------------------------------------
# GET /alerts/high-risk — events where risk_level is high or severe
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/high-risk",
    response_model=List[AnalyticsEventResponse],
    summary="Get all high-risk / severe alert events",
    description=(
        "Returns all `analytics_events` rows where `risk_level` is **high** "
        "or **severe**, ordered by most recent first.  Used to populate the "
        "alert table on the dashboard."
    ),
)
def get_high_risk_alerts(db: Session = Depends(get_db)) -> List[AnalyticsEventResponse]:
    rows = (
        db.query(analytics_events)
        .filter(analytics_events.risk_level.in_(["high", "severe"]))
        .order_by(analytics_events.id.desc())
        .all()
    )
    return rows
