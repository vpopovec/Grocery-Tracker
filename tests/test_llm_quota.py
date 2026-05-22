from datetime import date

import pytest

from g_tracker import create_app, db
from g_tracker.llm_quota import (
    INSIGHT_CHAT,
    RECEIPT_SCAN,
    QuotaExceeded,
    check_usage_allowed,
    record_usage_attempt,
)
from g_tracker.models import Person


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'LLM_SCANS_PER_USER_PER_DAY': 2,
        'LLM_SCANS_GLOBAL_PER_DAY': 3,
        'INSIGHT_AI_PER_USER_PER_DAY': 5,
        'INSIGHT_AI_GLOBAL_PER_DAY': 10,
        'SCAN_RATE_LIMIT': '',
        'ASK_AI_RATE_LIMIT': '',
        'RATELIMIT_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _add_user(username='u1'):
    person = Person(username=username, email=f'{username}@x.com', name=username)
    person.set_password('x')
    db.session.add(person)
    db.session.commit()
    return person.person_id


def test_receipt_scan_per_user_quota(app):
    with app.app_context():
        pid = _add_user()
        check_usage_allowed(pid, RECEIPT_SCAN)
        record_usage_attempt(pid, RECEIPT_SCAN)
        check_usage_allowed(pid, RECEIPT_SCAN)
        record_usage_attempt(pid, RECEIPT_SCAN)
        with pytest.raises(QuotaExceeded):
            check_usage_allowed(pid, RECEIPT_SCAN)


def test_receipt_scan_global_quota(app):
    with app.app_context():
        pids = []
        for i in range(3):
            pid = _add_user(f'u{i}')
            record_usage_attempt(pid, RECEIPT_SCAN)
            pids.append(pid)
        with pytest.raises(QuotaExceeded):
            check_usage_allowed(pids[0], RECEIPT_SCAN)


def test_insight_chat_separate_from_receipt(app):
    with app.app_context():
        pid = _add_user()
        record_usage_attempt(pid, RECEIPT_SCAN)
        record_usage_attempt(pid, RECEIPT_SCAN)
        with pytest.raises(QuotaExceeded):
            check_usage_allowed(pid, RECEIPT_SCAN)
        check_usage_allowed(pid, INSIGHT_CHAT)
