"""
Video Pydantic schema — Stage 8
================================
Response model returned from POST /videos/upload.
"""

from datetime import datetime
from pydantic import BaseModel


class VideoUploadResponse(BaseModel):
    """Minimal response returned immediately after a video is accepted."""
    id: int
    original_filename: str
    processed_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
