from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadNote
from app.schemas.lead import LeadCreate, LeadNoteCreate, LeadUpdate


class LeadService:
    @staticmethod
    async def get_all_leads(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        today = datetime.now(timezone.utc).date()
        if date_from is None:
            date_from = today - timedelta(days=6)
        if date_to is None:
            date_to = today

        dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

        all_leads = (
            db.query(Lead)
            .filter(Lead.created_at >= dt_from, Lead.created_at <= dt_to)
            .order_by(Lead.created_at.desc())
            .all()
        )

        dashboard_data = {
            "new": {"count": 0, "leads": []},
            "contacted": {"count": 0, "leads": []},
            "negotiation": {"count": 0, "leads": []},
            "closed": {"count": 0, "leads": []},
            "low_quality": {"count": 0, "leads": []},
        }

        for lead in all_leads:
            status_key = (
                lead.status.value if hasattr(lead.status, "value") else lead.status
            )

            if status_key in dashboard_data:
                dashboard_data[status_key]["leads"].append(lead)
                dashboard_data[status_key]["count"] += 1

        return dashboard_data

    @staticmethod
    async def create_lead(db: Session, lead_data: LeadCreate):
        db_lead = Lead(name=lead_data.name, phone=lead_data.phone, source="manual")
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        if lead_data.note:
            await LeadService.create_note(
                db, db_lead.id, LeadNoteCreate(text=lead_data.note)
            )
        return db_lead

    @staticmethod
    async def update_lead_status(db: Session, lead_id: int, status: str):
        db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if db_lead:
            db_lead.status = status
            db.commit()
            db.refresh(db_lead)
        return db_lead

    @staticmethod
    async def update_lead(db: Session, lead_id: int, payload: LeadUpdate) -> Lead:
        db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not db_lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with id={lead_id} not found",
            )

        if payload.name is None and payload.phone is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nothing to update",
            )

        if payload.name is not None:
            db_lead.name = payload.name
        if payload.phone is not None:
            db_lead.phone = payload.phone

        db.commit()
        db.refresh(db_lead)
        return db_lead

    @staticmethod
    async def delete_lead(db: Session, lead_id: int):
        db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if db_lead:
            db.delete(db_lead)
            db.commit()
            return True
        return False

    @staticmethod
    async def create_note(db: Session, lead_id: int, request: LeadNoteCreate):
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with id={lead_id} not found",
            )

        db_note = LeadNote(lead_id=lead_id, text=request.text)
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        return db_note

    @staticmethod
    async def delete_note(db: Session, note_id):
        db_note = db.query(LeadNote).filter(LeadNote.id == note_id).first()
        if db_note:
            db.delete(db_note)
            db.commit()
            return True
        return False

    @staticmethod
    async def get_stats(db: Session):
        total = db.query(func.count(Lead.id)).scalar() or 0

        status_rows = (
            db.query(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
            .all()
        )
        by_status = {str(k): int(v) for k, v in status_rows if k}

        def series(days: int) -> list[dict]:
            now = datetime.now(timezone.utc)
            start = (now - timedelta(days=days - 1)).date()
            end = now.date()

            rows = (
                db.query(func.date(Lead.created_at).label("d"), func.count(Lead.id))
                .filter(Lead.created_at >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
                .group_by(func.date(Lead.created_at))
                .order_by(func.date(Lead.created_at))
                .all()
            )
            by_day = {r[0]: int(r[1]) for r in rows if r[0]}

            out: list[dict] = []
            cur = start
            while cur <= end:
                out.append({"date": cur.isoformat(), "count": by_day.get(cur, 0)})
                cur = cur + timedelta(days=1)
            return out

        def month_series(months: int) -> list[dict]:
            now = datetime.now(timezone.utc)
            first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start = (first_of_this_month - timedelta(days=months * 31)).replace(day=1)

            # Group by YYYY-MM in DB
            rows = (
                db.query(
                    func.to_char(Lead.created_at, "YYYY-MM").label("m"),
                    func.count(Lead.id),
                )
                .filter(Lead.created_at >= start)
                .group_by(func.to_char(Lead.created_at, "YYYY-MM"))
                .order_by(func.to_char(Lead.created_at, "YYYY-MM"))
                .all()
            )
            by_month = {str(r[0]): int(r[1]) for r in rows if r[0]}

            out: list[dict] = []
            cur = first_of_this_month
            keys: list[str] = []
            for _ in range(months):
                keys.append(cur.strftime("%Y-%m"))
                # go back one month safely
                prev = (cur - timedelta(days=1)).replace(day=1)
                cur = prev
            keys = list(reversed(keys))
            for k in keys:
                out.append({"month": k, "count": by_month.get(k, 0)})
            return out

        return {
            "total": int(total),
            "by_status": by_status,
            "last_7_days": series(7),
            "last_30_days": series(30),
            "last_12_months": month_series(12),
        }
