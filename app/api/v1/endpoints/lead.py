from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.lead import DashboradOut, LeadOut
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"], dependencies=[])


@router.get(
    "/",
    response_model=DashboradOut,
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Unauthorized"}},
)
async def list_users(db: Session = Depends(get_db)) -> DashboradOut:
    return await LeadService.get_all_leads(db)


@router.patch("/{lead_id}/status", response_model=LeadOut)
async def update_status(
    lead_id: int,
    status: str,  # Yoki Enum ishlatsangiz yanada xavfsizroq bo'ladi
    db: Session = Depends(get_db),
):
    """
    Lead statusini yangilash uchun endpoint.
    """
    updated_lead = await LeadService.update_lead_status(
        db=db, lead_id=lead_id, status=status
    )

    if not updated_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID si {lead_id} bo'lgan lead topilmadi",
        )

    return updated_lead
