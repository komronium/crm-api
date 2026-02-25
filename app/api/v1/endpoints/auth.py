from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import ChangePassword, LoginRequest, Token
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


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid password"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal Server Error"},
    },
)
async def change_password(
    request: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AuthService.change_password(db, current_user, request)
