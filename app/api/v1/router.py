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


@api_router.get("/webhook")
async def verify_webhook(mode: str, verify_token: str, challenge: str):
    if verify_token == VERIFY_TOKEN:
        return int(challenge)
    return "Verification failed"


@api_router.post("/webhook")
async def receive_lead(request: Request):
    data = await request.json()

    lead_id = data["entry"][0]["changes"][0]["value"]["leadgen_id"]

    # Lead ma'lumotini olish
    url = f"https://graph.facebook.com/v18.0/{lead_id}"
    params = {"access_token": PAGE_ACCESS_TOKEN}

    response = requests.get(url, params=params)
    lead_data = response.json()

    print(lead_data)

    # Bu yerda DB ga yozasiz

    return {"status": "ok"}
