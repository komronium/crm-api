from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    name: str
    phone: str
    note: str | None = None


class LeadOut(LeadBase):
    id: int
    status: str
    created_at: datetime


class DashboardItem(BaseModel):
    count: int
    leads: list[LeadOut] = []


class DashboradOut(BaseModel):
    new: DashboardItem
    contacted: DashboardItem
    negotiation: DashboardItem
    closed: DashboardItem
