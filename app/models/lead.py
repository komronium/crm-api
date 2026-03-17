from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Lead(Base):
    name = Column(String(length=128), nullable=False)
    phone = Column(String(length=32), nullable=False)
    note = Column(Text, nullable=True)
    # Keep as String to avoid DB enum/type coupling across environments.
    status = Column(String(length=32), nullable=False, default="new")

    # Optional external linking (e.g. Facebook Lead Ads lead id)
    source = Column(String(length=32), nullable=False, default="manual")
    external_id = Column(String(length=128), nullable=True, unique=True, index=True)
    raw_payload = Column(Text, nullable=True)

    notes = relationship(
        "LeadNote", back_populates="lead", cascade="all, delete-orphan"
    )


class LeadNote(Base):
    text = Column(String(length=512), nullable=False)

    lead_id = Column(ForeignKey("lead.id"), nullable=False)
    lead = relationship("Lead", back_populates="notes")
