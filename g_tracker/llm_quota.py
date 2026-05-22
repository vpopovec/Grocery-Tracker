"""Daily LLM usage quotas (OpenRouter receipt scans, Groq insight chat, etc.)."""

from datetime import date

from flask import current_app
from sqlalchemy import func, select

from g_tracker import db
from g_tracker.models import LlmDailyUsage

RECEIPT_SCAN = 'receipt_scan'
INSIGHT_CHAT = 'insight_chat'


class QuotaExceeded(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _today() -> date:
    return date.today()


def _limits(usage_kind: str) -> tuple[int, int]:
    if usage_kind == RECEIPT_SCAN:
        return (
            int(current_app.config.get('LLM_SCANS_PER_USER_PER_DAY', 10)),
            int(current_app.config.get('LLM_SCANS_GLOBAL_PER_DAY', 50)),
        )
    if usage_kind == INSIGHT_CHAT:
        return (
            int(current_app.config.get('INSIGHT_AI_PER_USER_PER_DAY', 20)),
            int(current_app.config.get('INSIGHT_AI_GLOBAL_PER_DAY', 100)),
        )
    raise ValueError(f'Unknown usage kind: {usage_kind}')


def get_user_usage_count(
    person_id: int,
    usage_kind: str,
    usage_date: date | None = None,
) -> int:
    usage_date = usage_date or _today()
    row = db.session.execute(
        select(LlmDailyUsage.usage_count).where(
            LlmDailyUsage.person_id == person_id,
            LlmDailyUsage.usage_date == usage_date,
            LlmDailyUsage.usage_kind == usage_kind,
        )
    ).scalar()
    return int(row or 0)


def get_global_usage_count(usage_kind: str, usage_date: date | None = None) -> int:
    usage_date = usage_date or _today()
    total = db.session.execute(
        select(func.coalesce(func.sum(LlmDailyUsage.usage_count), 0)).where(
            LlmDailyUsage.usage_date == usage_date,
            LlmDailyUsage.usage_kind == usage_kind,
        )
    ).scalar()
    return int(total or 0)


def check_usage_allowed(person_id: int, usage_kind: str) -> None:
    user_limit, global_limit = _limits(usage_kind)
    user_count = get_user_usage_count(person_id, usage_kind)
    if user_count >= user_limit:
        label = 'receipt scans' if usage_kind == RECEIPT_SCAN else 'AI questions'
        raise QuotaExceeded(
            f'Daily {label} limit reached ({user_limit} per day). Try again tomorrow.'
        )

    global_count = get_global_usage_count(usage_kind)
    if global_count >= global_limit:
        raise QuotaExceeded(
            'The app has reached its daily AI usage limit. Try again tomorrow.'
        )


def record_usage_attempt(person_id: int, usage_kind: str) -> int:
    usage_date = _today()
    row = db.session.execute(
        select(LlmDailyUsage).where(
            LlmDailyUsage.person_id == person_id,
            LlmDailyUsage.usage_date == usage_date,
            LlmDailyUsage.usage_kind == usage_kind,
        )
    ).scalar_one_or_none()

    if row is None:
        row = LlmDailyUsage(
            person_id=person_id,
            usage_date=usage_date,
            usage_kind=usage_kind,
            usage_count=1,
        )
        db.session.add(row)
    else:
        row.usage_count += 1

    db.session.commit()
    return row.usage_count


def quota_status(person_id: int, usage_kind: str) -> dict:
    user_limit, global_limit = _limits(usage_kind)
    user_count = get_user_usage_count(person_id, usage_kind)
    global_count = get_global_usage_count(usage_kind)
    return {
        'usage_kind': usage_kind,
        'user_count': user_count,
        'user_limit': user_limit,
        'user_remaining': max(0, user_limit - user_count),
        'global_count': global_count,
        'global_limit': global_limit,
        'global_remaining': max(0, global_limit - global_count),
    }
