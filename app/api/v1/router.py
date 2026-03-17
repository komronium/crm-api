from fastapi import APIRouter, Request

from app.api.v1.endpoints import auth, lead, operators, profile
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(operators.router)
api_router.include_router(profile.router)
api_router.include_router(lead.router)


@api_router.get("/webhook")
def verify(
    hub_mode: str = None, hub_challenge: str = None, hub_verify_token: str = None
):
    expected = (
        settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN.get_secret_value()
        if settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN
        else None
    )
    if expected and hub_verify_token == expected:
        return int(hub_challenge)
    return "Invalid token"


@api_router.post("/webhook")
async def receive(request: Request):
    data = await request.json()
    # TODO: handle facebook webhook events (leadgen, messaging, etc.)
    return {"status": "ok", "received": bool(data)}
