"""
Analytics Pydantic schemas — Stage 9
======================================
Lightweight response models that map directly to the DB columns in
`videos` and `analytics_events` tables.  All models use
`model_config = {"from_attributes": True}` so SQLAlchemy ORM objects
can be passed directly to `model_validate()`.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Video schemas
# ---------------------------------------------------------------------------

class VideoResponse(BaseModel):
    """One row from the `videos` table — returned by GET /videos."""
    id: int
    original_filename: str
    processed_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analytics-event schemas
# ---------------------------------------------------------------------------

class AnalyticsEventResponse(BaseModel):
    """
    One row from the `analytics_events` table.
    Returned by GET /videos/{video_id}/events and GET /alerts/high-risk.
    """
    id: int
    video_id: int
    frame_number: int
    timestamp_sec: Optional[float] = None
    headcount: Optional[int] = None
    motion_speed: Optional[float] = None
    risk_score: Optional[int] = None
    risk_level: str
    alert_image_url: Optional[str] = None

    model_config = {"from_attributes": True}
