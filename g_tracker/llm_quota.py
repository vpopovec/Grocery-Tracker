"""Daily LLM scan quotas to cap paid API usage (Gemini, OpenRouter, etc.)."""

from datetime import date

from flask import current_app
from sqlalchemy import func, select

from g_tracker import db
from g_tracker.models import LlmDailyUsage


class QuotaExceeded(Exception):
    """Raised when per-user or global daily scan limits are reached."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _today() -> date:
    return date.today()


def _user_daily_limit() -> int:
    return int(current_app.config.get('LLM_SCANS_PER_USER_PER_DAY', 10))


def _global_daily_limit() -> int:
    return int(current_app.config.get('LLM_SCANS_GLOBAL_PER_DAY', 50))


def get_user_scan_count(person_id: int, usage_date: date | None = None) -> int:
    usage_date = usage_date or _today()
    row = db.session.execute(
        select(LlmDailyUsage.scan_count).where(
            LlmDailyUsage.person_id == person_id,
            LlmDailyUsage.usage_date == usage_date,
        )
    ).scalar()
    return int(row or 0)


def get_global_scan_count(usage_date: date | None = None) -> int:
    usage_date = usage_date or _today()
    total = db.session.execute(
        select(func.coalesce(func.sum(LlmDailyUsage.scan_count), 0)).where(
            LlmDailyUsage.usage_date == usage_date,
        )
    ).scalar()
    return int(total or 0)


def check_scan_allowed(person_id: int) -> None:
    """Raise QuotaExceeded if another LLM scan would exceed configured limits."""
    user_limit = _user_daily_limit()
    user_count = get_user_scan_count(person_id)
    if user_count >= user_limit:
        raise QuotaExceeded(
            f'Daily scan limit reached ({user_limit} per day). Try again tomorrow.'
        )

    global_limit = _global_daily_limit()
    global_count = get_global_scan_count()
    if global_count >= global_limit:
        raise QuotaExceeded(
            'The app has reached its daily scan limit. Try again tomorrow.'
        )


def record_scan_attempt(person_id: int) -> int:
    """
    Reserve one scan against daily quotas. Call before invoking the LLM API.
    Returns the user's scan count for today after incrementing.
    """
    usage_date = _today()
    row = db.session.execute(
        select(LlmDailyUsage).where(
            LlmDailyUsage.person_id == person_id,
            LlmDailyUsage.usage_date == usage_date,
        )
    ).scalar_one_or_none()

    if row is None:
        row = LlmDailyUsage(
            person_id=person_id,
            usage_date=usage_date,
            scan_count=1,
        )
        db.session.add(row)
    else:
        row.scan_count += 1

    db.session.commit()
    return row.scan_count


def quota_status(person_id: int) -> dict:
    """Counts for UI or logging."""
    user_limit = _user_daily_limit()
    user_count = get_user_scan_count(person_id)
    global_limit = _global_daily_limit()
    global_count = get_global_scan_count()
    return {
        'user_count': user_count,
        'user_limit': user_limit,
        'user_remaining': max(0, user_limit - user_count),
        'global_count': global_count,
        'global_limit': global_limit,
        'global_remaining': max(0, global_limit - global_count),
    }
