from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    name: str
    phone: str


class LeadFormField(BaseModel):
    question: str
    answer: str


class LeadCreate(LeadBase):
    note: str | None = None


class LeadUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None


class LeadOut(LeadBase):
    id: int
    status: str
    notes: list["LeadNoteOut"]
    form_data: list[LeadFormField] | None = None
    created_at: datetime


class LeadNoteBase(BaseModel):
    text: str


class LeadNoteCreate(LeadNoteBase): ...


class LeadNoteOut(LeadNoteBase):
    id: int
    created_at: datetime


class LeadChartPoint(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class LeadStatsOut(BaseModel):
    total: int
    by_status: dict[str, int]
    last_7_days: list[LeadChartPoint]
    last_30_days: list[LeadChartPoint]
    last_12_months: list[dict]


class DashboardItem(BaseModel):
    count: int
    leads: list[LeadOut] = []


class DashboradOut(BaseModel):
    new: DashboardItem
    callback: DashboardItem
    low_quality: DashboardItem
    thinking: DashboardItem
    next_month: DashboardItem
    intro_lesson: DashboardItem
    sale: DashboardItem


DashboradOut.model_rebuild()
