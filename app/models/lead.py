import enum

from sqlalchemy import Column, Enum, String, Text

from app.db.base import Base


class StatusType(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    NEGOTIATION = "negotiation"
    CLOSED = "closed"

    def __str__(self):
        return self.value


class Lead(Base):
    name = Column(String(length=128), nullable=False)
    phone = Column(String(length=32), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(String(length=32), default="new", nullable=False)
