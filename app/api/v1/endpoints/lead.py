from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.schemas.lead import (
    DashboradOut,
    LeadStatsOut,
    LeadCreate,
    LeadUpdate,
    LeadNoteCreate,
    LeadNoteOut,
    LeadOut,
)
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"], dependencies=[])


@router.get(
    "/",
    response_model=DashboradOut,
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Unauthorized"}},
)
async def list_users(
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> DashboradOut:
    return await LeadService.get_all_leads(db, date_from=date_from, date_to=date_to)


@router.get("/stats", response_model=LeadStatsOut)
async def lead_stats(db: Session = Depends(get_db)) -> LeadStatsOut:
    data = await LeadService.get_stats(db)
    return LeadStatsOut(**data)


@router.post(
    "/",
    response_model=LeadOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid credentials"},
        401: {"description": "Unauthorized"},
    },
)
async def create_operator(lead: LeadCreate, db: Session = Depends(get_db)) -> LeadOut:
    return await LeadService.create_lead(db, lead)


@router.patch(
    "/{lead_id}",
    response_model=LeadOut,
)
async def update_lead(
    lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)
) -> LeadOut:
    return await LeadService.update_lead(db, lead_id, payload)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> Response:
    ok = await LeadService.delete_lead(db, lead_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with id={lead_id} not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post("/{lead_id}/notes/", response_model=LeadNoteOut)
async def create_note(
    lead_id: int, request: LeadNoteCreate, db: Session = Depends(get_db)
) -> LeadNoteOut:
    return await LeadService.create_note(db, lead_id, request)


@router.delete("/notes/{note_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int, db: Session = Depends(get_db)):
    await LeadService.delete_note(db, note_id)
