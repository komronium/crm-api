from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Lead(Base):
    name = Column(String(length=128), nullable=False)
    phone = Column(String(length=32), nullable=False)
    status = Column(String(length=32), default="new", nullable=False)

    notes = relationship(
        "LeadNote", back_populates="lead", cascade="all, delete-orphan"
    )


class LeadNote(Base):
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(length=128), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead_id = Column(ForeignKey("lead.id"), nullable=False)
    lead = relationship("Lead", back_populates="notes")
