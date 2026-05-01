import json
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lead import Lead


def _graph_base_url() -> str:
    version = settings.FACEBOOK_GRAPH_VERSION
    return f"https://graph.facebook.com/{version}"


NAME_FIELDS = {"full_name", "name", "ismingiz?", "ismingiz"}
PHONE_FIELDS = {
    "номер_телефона",
    "номер телефона",
    "phone_number",
    "phone",
    "mobile_phone",
    "phone_number_uz",
    "telefon_raqamingiz?",
    "telefon_raqamingiz",
}


def _extract_field(field_data: list[dict], *names: str) -> str | None:
    wanted = {n.lower() for n in names}
    for item in field_data or []:
        name = (item.get("name") or "").lower()
        if name in wanted:
            values = item.get("values") or []
            if values:
                return str(values[0])
    return None


def _humanize(text: str) -> str:
    if not text:
        return text
    cleaned = text.replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def _extract_form_qa(field_data: list[dict]) -> list[dict]:
    """
    Returns a list of {"question": str, "answer": str} extracted from the
    Facebook lead's field_data, excluding the name/phone fields used for the
    Lead's main columns.
    """
    skip = {n.lower() for n in NAME_FIELDS | PHONE_FIELDS}
    qa: list[dict] = []
    for item in field_data or []:
        raw_name = (item.get("name") or "").strip()
        if not raw_name or raw_name.lower() in skip:
            continue
        values = item.get("values") or []
        answer = ", ".join(_humanize(str(v)) for v in values) if values else ""
        qa.append({"question": _humanize(raw_name), "answer": answer})
    return qa


class FacebookLeadService:
    @staticmethod
    async def list_page_forms(*, page_id: str) -> list[dict]:
        if not settings.FACEBOOK_ACCESS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FACEBOOK_ACCESS_TOKEN is not configured",
            )
        access_token = settings.FACEBOOK_ACCESS_TOKEN.get_secret_value()
        url = f"{_graph_base_url()}/{page_id}/leadgen_forms"
        params = {
            "access_token": access_token,
            "fields": "id,name,status,created_time",
            "limit": 100,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Facebook Graph error: {resp.status_code} {resp.text}",
            )

        payload = resp.json()
        return payload.get("data") or []

    @staticmethod
    async def import_leads(
        db: Session,
        *,
        form_id: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> dict:
        form_id = form_id or settings.FACEBOOK_LEADGEN_FORM_ID
        if not form_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FACEBOOK_LEADGEN_FORM_ID is not configured",
            )

        if not settings.FACEBOOK_ACCESS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FACEBOOK_ACCESS_TOKEN is not configured",
            )
        access_token = settings.FACEBOOK_ACCESS_TOKEN.get_secret_value()
        params = {
            "access_token": access_token,
            "fields": "id,created_time,field_data",
            "limit": limit,
        }
        if since is not None:
            # Graph expects unix timestamp
            params["since"] = int(since.timestamp())

        url = f"{_graph_base_url()}/{form_id}/leads"

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Facebook Graph error: {resp.status_code} {resp.text}",
            )

        payload = resp.json()
        data = payload.get("data") or []

        created = 0
        skipped = 0
        errors: list[dict] = []

        for item in data:
            lead_id = item.get("id")
            if not lead_id:
                skipped += 1
                continue

            exists = db.query(Lead).filter(Lead.external_id == str(lead_id)).first()
            if exists:
                skipped += 1
                continue

            field_data = item.get("field_data") or []
            name = _extract_field(field_data, *NAME_FIELDS)
            phone = _extract_field(field_data, *PHONE_FIELDS)

            if not name or not phone:
                errors.append(
                    {
                        "external_id": str(lead_id),
                        "reason": "missing_name_or_phone",
                    }
                )
                continue

            form_data = _extract_form_qa(field_data)

            db_lead = Lead(
                name=name,
                phone=phone,
                status="new",
                source="facebook",
                external_id=str(lead_id),
                raw_payload=json.dumps(item, ensure_ascii=False),
                form_data=form_data or None,
            )
            db.add(db_lead)
            created += 1

        db.commit()

        return {
            "fetched": len(data),
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "paging": payload.get("paging"),
        }

    @staticmethod
    async def import_leads_by_page(
        db: Session,
        *,
        page_id: str,
        since: datetime | None = None,
        limit_per_form: int = 50,
    ) -> dict:
        forms = await FacebookLeadService.list_page_forms(page_id=page_id)

        total = {"forms": len(forms), "fetched": 0, "created": 0, "skipped": 0, "errors": []}
        per_form: list[dict] = []

        for form in forms:
            form_id = form.get("id")
            if not form_id:
                continue
            result = await FacebookLeadService.import_leads(
                db, form_id=str(form_id), since=since, limit=limit_per_form
            )
            per_form.append(
                {
                    "form_id": str(form_id),
                    "name": form.get("name"),
                    "status": form.get("status"),
                    **{k: result.get(k) for k in ["fetched", "created", "skipped", "errors"]},
                }
            )
            total["fetched"] += int(result.get("fetched", 0))
            total["created"] += int(result.get("created", 0))
            total["skipped"] += int(result.get("skipped", 0))
            total["errors"].extend(result.get("errors") or [])

        return {"total": total, "forms": per_form}

