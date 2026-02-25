from pydantic import BaseModel, Field, model_validator

from app.schemas.user import UserOut


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)
    confirm_password: str = Field(..., min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_passwords(cls, values):
        cur = values.current_password
        new = values.new_password
        conf = values.confirm_password

        if new != conf:
            raise ValueError("Yangi parol va tasdiqlash bir xil bo'lishi kerak.")
        if cur == new:
            raise ValueError("Yangi parol joriy parol bilan bir xil bo'lmasligi kerak.")
        return values
