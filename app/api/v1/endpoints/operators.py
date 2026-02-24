from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(
    prefix="/api/v1/operators",
    tags=["Operators"],
    dependencies=[Depends(get_admin_user)],
)


@router.get(
    "/",
    response_model=List[UserOut],
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Unauthorized"}},
)
async def list_operators(db: Session = Depends(get_db)) -> List[User]:
    return await UserService.get_all_operators(db)


@router.post(
    "/",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid credentials"},
        401: {"description": "Unauthorized"},
    },
)
async def create_operator(user: UserCreate, db: Session = Depends(get_db)) -> User:
    return await UserService.create_user(user, db)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"description": "Unauthorized"}, 404: {"description": "Not found"}},
)
async def delete_oprator(user_id: int, db: Session = Depends(get_db)):
    await UserService.delete_user(db, user_id)
