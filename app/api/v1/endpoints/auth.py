from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import LoginRequest, Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1", tags=["Authentication"])


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid credentials"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal Server Error"},
    },
)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> Token:
    return await AuthService.login(db, request)
