import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.facebook_lead_service import FacebookLeadService

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def facebook_lead_polling_loop() -> None:
    """
    Periodically imports leads from Facebook Lead Ads into local DB.
    Safe to run continuously; dedup is handled by Lead.external_id unique constraint.
    """
    if not settings.FACEBOOK_PAGE_ID:
        logger.info("Facebook polling disabled: FACEBOOK_PAGE_ID not set.")
        return
    if not settings.FACEBOOK_ACCESS_TOKEN:
        logger.info("Facebook polling disabled: FACEBOOK_ACCESS_TOKEN not set.")
        return

    interval = max(int(settings.FACEBOOK_POLL_INTERVAL_SECONDS), 10)
    lookback = max(int(settings.FACEBOOK_POLL_LOOKBACK_SECONDS), 60)
    limit = max(int(settings.FACEBOOK_IMPORT_LIMIT_PER_FORM), 1)

    logger.info(
        "Facebook polling enabled. page_id=%s interval=%ss lookback=%ss limit=%s",
        settings.FACEBOOK_PAGE_ID,
        interval,
        lookback,
        limit,
    )

    while True:
        since = _utc_now() - timedelta(seconds=lookback)
        db = SessionLocal()
        try:
            result = await FacebookLeadService.import_leads(
                db,
                form_id=str(settings.FACEBOOK_PAGE_ID),
                since=since,
                limit=limit,
            )
            logger.info(
                "Facebook import done. fetched=%s created=%s skipped=%s errors=%s",
                result.get("fetched"),
                result.get("created"),
                result.get("skipped"),
                len(result.get("errors") or []),
            )
        except Exception:
            logger.exception("Facebook import failed")
        finally:
            db.close()

        await asyncio.sleep(interval)

