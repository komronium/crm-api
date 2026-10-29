"""In-memory login throttle. The API runs as one process, so a dict is enough; a restart clears it."""
import time
from collections import defaultdict

from app.core.config import settings

_failures: dict[str, list[float]] = defaultdict(list)


def _recent(key: str) -> list[float]:
    cutoff = time.monotonic() - settings.LOGIN_LOCK_SECONDS
    _failures[key] = [t for t in _failures[key] if t > cutoff]
    return _failures[key]


def is_locked(key: str) -> bool:
    return len(_recent(key)) >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(key: str) -> None:
    _recent(key).append(time.monotonic())


def reset(key: str) -> None:
    _failures.pop(key, None)


def clear_all() -> None:
    _failures.clear()
