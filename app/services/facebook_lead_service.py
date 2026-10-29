import json
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lead import Lead


MAX_PAGES = 5


def _graph_base_url() -> str:
    version = settings.FACEBOOK_GRAPH_VERSION
    return f"https://graph.facebook.com/{version}"


# Priority-ordered: the primary fields used for Lead.name / Lead.phone columns.
# Earlier entries are preferred when extracting the main value.
NAME_FIELDS = ("full_name", "name", "ismingiz?", "ismingiz")
PHONE_FIELDS = (
    "phone",
    "phone_number",
    "mobile_phone",
    "phone_number_uz",
    "номер_телефона",
    "номер телефона",
    "telefon_raqamingiz?",
    "telefon_raqamingiz",
)

# Only the canonical fields are excluded from form_data Q&A; the localized
# ismingiz?/telefon_raqamingiz fields are kept so they appear alongside the
# rest of the form responses.
FORM_DATA_SKIP = {"full_name", "name", "phone", "phone_number", "mobile_phone",
                  "phone_number_uz", "номер_телефона", "номер телефона"}


def _extract_field(field_data: list[dict], *names: str) -> str | None:
    by_name = {(item.get("name") or "").lower(): item for item in field_data or []}
    for n in names:
        item = by_name.get(n.lower())
        if not item:
            continue
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
    Facebook lead's field_data, excluding the canonical name/phone fields
    that populate the Lead's main columns.
    """
    qa: list[dict] = []
    for item in field_data or []:
        raw_name = (item.get("name") or "").strip()
        if not raw_name or raw_name.lower() in FORM_DATA_SKIP:
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

        created = 0
        skipped = 0
        fetched = 0
        errors: list[dict] = []
        paging = None

        async with httpx.AsyncClient(timeout=20) as client:
            # Follow "next" pages (up to MAX_PAGES), otherwise a burst larger than `limit` loses leads.
            for _ in range(MAX_PAGES):
                resp = await client.get(url, params=params)
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Facebook Graph error: {resp.status_code} {resp.text}",
                    )
                payload = resp.json()
                data = payload.get("data") or []
                paging = payload.get("paging")
                fetched += len(data)

                for item in data:
                    result = FacebookLeadService._store_lead(db, item)
                    if result == "created":
                        created += 1
                    elif result == "skipped":
                        skipped += 1
                    else:
                        errors.append(result)

                next_url = (paging or {}).get("next")
                if not next_url or not data:
                    break
                url, params = next_url, None

        return {
            "fetched": fetched,
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "paging": paging,
        }

    @staticmethod
    def _store_lead(db: Session, item: dict):
        """Save one Graph lead. Returns "created", "skipped" or an error dict. One bad lead never loses the others."""
        lead_id = item.get("id")
        if not lead_id:
            return "skipped"
        if db.query(Lead).filter(Lead.external_id == str(lead_id)).first():
            return "skipped"

        field_data = item.get("field_data") or []
        name = _extract_field(field_data, *NAME_FIELDS)
        phone = _extract_field(field_data, *PHONE_FIELDS)
        if not name or not phone:
            return {"external_id": str(lead_id), "reason": "missing_name_or_phone"}

        db_lead = Lead(
            name=name[:128],
            phone=phone[:32],
            status="new",
            source="facebook",
            external_id=str(lead_id),
            raw_payload=json.dumps(item, ensure_ascii=False),
            form_data=_extract_form_qa(field_data) or None,
        )
        db.add(db_lead)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return "skipped"
        return "created"

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

