from sqlalchemy.orm import relationship
from app.db.session import Base
from sqlalchemy import Column, Integer, Float, Enum, DateTime, VARCHAR, func

class videos(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(VARCHAR(255), nullable=False)
    processed_status = Column(Enum("pending", "processing", "completed", "failed"), default="pending")
    created_at = Column(DateTime(), nullable=False, default=func.now())

    events = relationship("analytics_events", back_populates="video", cascade="all, delete-orphan")