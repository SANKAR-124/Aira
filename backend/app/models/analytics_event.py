from app.db.session import Base
from sqlalchemy import Column, Integer, Enum, VARCHAR, Float, ForeignKey
from sqlalchemy.orm import relationship

class analytics_events(Base):
    __tablename__ = "analytics_events"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp_sec = Column(Float)
    headcount = Column(Integer)
    motion_speed = Column(Float)
    risk_score = Column(Integer)
    risk_level = Column(Enum('low', 'moderate', 'high', 'severe'), nullable=False)
    alert_image_url = Column(VARCHAR(500), nullable=True)

    video = relationship("videos", back_populates="events")