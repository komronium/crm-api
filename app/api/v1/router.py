import requests
from fastapi import APIRouter, Request

from app.api.v1.endpoints import auth, lead, operators, profile

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(operators.router)
api_router.include_router(profile.router)
api_router.include_router(lead.router)


VERIFY_TOKEN = "abc123"
PAGE_ACCESS_TOKEN = ""


VERIFY_TOKEN = "my_secure_token"


@api_router.get("/webhook")
def verify(
    hub_mode: str = None, hub_challenge: str = None, hub_verify_token: str = None
):
    if hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return "Invalid token"


@api_router.post("/webhook")
async def receive(request: Request):
    data = await request.json()
    print(data)  # Shu yerga comment + DM keladi
    return {"status": "ok"}
