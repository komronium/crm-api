import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.facebook_lead_service import FacebookLeadService

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 1800


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_token_error(exc: Exception) -> bool:
    detail = str(getattr(exc, "detail", exc))
    return '"code":190' in detail or "Error validating access token" in detail


async def import_once(since: datetime, limit: int) -> dict:
    """One import round. FACEBOOK_LEADGEN_FORM_ID wins; when it is empty the value of FACEBOOK_PAGE_ID is used
    as the form id (this is how the live deployment has always been configured)."""
    form_id = settings.FACEBOOK_LEADGEN_FORM_ID or str(settings.FACEBOOK_PAGE_ID)
    db = SessionLocal()
    try:
        return await FacebookLeadService.import_leads(db, form_id=form_id, since=since, limit=limit)
    finally:
        db.close()


async def facebook_lead_polling_loop() -> None:
    """
    Periodically imports leads from Facebook Lead Ads into local DB.
    Dedup is handled by Lead.external_id. A failing round backs off (up to 30 minutes) and logs one line,
    instead of a full traceback every minute.
    """
    if not settings.FACEBOOK_PAGE_ID and not settings.FACEBOOK_LEADGEN_FORM_ID:
        logger.info("Facebook polling disabled: no FACEBOOK_PAGE_ID or FACEBOOK_LEADGEN_FORM_ID.")
        return
    if not settings.FACEBOOK_ACCESS_TOKEN:
        logger.info("Facebook polling disabled: FACEBOOK_ACCESS_TOKEN not set.")
        return

    interval = max(int(settings.FACEBOOK_POLL_INTERVAL_SECONDS), 10)
    lookback = max(int(settings.FACEBOOK_POLL_LOOKBACK_SECONDS), 60)
    limit = max(int(settings.FACEBOOK_IMPORT_LIMIT_PER_FORM), 1)

    logger.info(
        "Facebook polling enabled. page_id=%s form_id=%s interval=%ss lookback=%ss limit=%s",
        settings.FACEBOOK_PAGE_ID, settings.FACEBOOK_LEADGEN_FORM_ID, interval, lookback, limit,
    )

    failures = 0
    while True:
        try:
            result = await import_once(_utc_now() - timedelta(seconds=lookback), limit)
            if failures:
                logger.info("Facebook import works again after %s failed rounds.", failures)
            failures = 0
            logger.info(
                "Facebook import done. fetched=%s created=%s skipped=%s errors=%s",
                result.get("fetched"), result.get("created"), result.get("skipped"),
                len(result.get("errors") or []),
            )
            delay = interval
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failures += 1
            if _is_token_error(exc):
                logger.error(
                    "Facebook access token is expired or invalid: create a new FACEBOOK_ACCESS_TOKEN "
                    "(a system-user token does not expire). Retrying in %ss.", MAX_BACKOFF_SECONDS,
                )
                delay = MAX_BACKOFF_SECONDS
            else:
                logger.warning("Facebook import failed (%s in a row): %s", failures, str(exc)[:300])
                delay = min(interval * (2 ** min(failures, 6)), MAX_BACKOFF_SECONDS)

        await asyncio.sleep(delay)
