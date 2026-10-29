from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LeadStatus = Literal[
    "new", "callback", "low_quality", "thinking", "next_month", "intro_lesson", "sale"
]


def _clean(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    phone: str = Field(..., min_length=3, max_length=32)

    _strip = field_validator("name", "phone", mode="before")(_clean)


class LeadFormField(BaseModel):
    question: str
    answer: str


class LeadCreate(LeadBase):
    note: str | None = Field(default=None, max_length=512)


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    phone: str | None = Field(default=None, min_length=3, max_length=32)

    _strip = field_validator("name", "phone", mode="before")(_clean)


class LeadOut(LeadBase):
    id: int
    status: str
    notes: list["LeadNoteOut"]
    form_data: list[LeadFormField] | None = None
    created_at: datetime


class LeadNoteBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=512)

    _strip = field_validator("text", mode="before")(_clean)


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
