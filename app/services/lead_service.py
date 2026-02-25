from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadNote
from app.schemas.lead import LeadNoteCreate


class LeadService:
    @staticmethod
    async def get_all_leads(db: Session):
        all_leads = db.query(Lead).all()

        dashboard_data = {
            "new": {"count": 0, "leads": []},
            "contacted": {"count": 0, "leads": []},
            "negotiation": {"count": 0, "leads": []},
            "closed": {"count": 0, "leads": []},
        }

        for lead in all_leads:
            # Statusni aniqlash (Enum bo'lsa .value, aks holda o'zi)
            status_key = (
                lead.status.value if hasattr(lead.status, "value") else lead.status
            )

            if status_key in dashboard_data:
                dashboard_data[status_key]["leads"].append(lead)
                dashboard_data[status_key]["count"] += 1

        return dashboard_data

    @staticmethod
    async def create_lead(db: Session, lead_data: dict):
        # LeadBase orqali kelgan ma'lumotlar uchun
        db_lead = Lead(name=lead_data.name, phone=lead_data.phone, note=lead_data.note)
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
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
