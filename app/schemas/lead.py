from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    name: str
    phone: str
    note: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadOut(LeadBase):
    id: int
    status: str
    notes: list["LeadNoteOut"]
    created_at: datetime


class LeadNoteBase(BaseModel):
    text: str


class LeadNoteCreate(LeadNoteBase): ...


class LeadNoteOut(LeadNoteBase):
    id: int
    created_at: datetime


class DashboardItem(BaseModel):
    count: int
    leads: list[LeadOut] = []


class DashboradOut(BaseModel):
    new: DashboardItem
    contacted: DashboardItem
    negotiation: DashboardItem
    closed: DashboardItem


DashboradOut.model_rebuild()
