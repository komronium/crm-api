import hmac

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from app.api.v1.endpoints import auth, lead, operators, profile
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(operators.router)
api_router.include_router(profile.router)
api_router.include_router(lead.router)


@api_router.get("/webhook")
def verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    expected = (
        settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN.get_secret_value()
        if settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN
        else None
    )
    if (
        expected
        and hub_mode == "subscribe"
        and hub_challenge is not None
        and hub_verify_token
        and hmac.compare_digest(hub_verify_token, expected)
    ):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


@api_router.post("/webhook")
async def receive(request: Request):
    data = await request.json()
    # TODO: handle facebook webhook events (leadgen, messaging, etc.)
    return {"status": "ok", "received": bool(data)}
