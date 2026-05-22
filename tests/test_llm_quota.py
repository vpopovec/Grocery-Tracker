from datetime import date

import pytest

from g_tracker import create_app, db
from g_tracker.llm_quota import QuotaExceeded, check_scan_allowed, record_scan_attempt
from g_tracker.models import LlmDailyUsage, Person


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'LLM_SCANS_PER_USER_PER_DAY': 2,
        'LLM_SCANS_GLOBAL_PER_DAY': 3,
        'SCAN_RATE_LIMIT': '',
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_per_user_quota(app):
    with app.app_context():
        person = Person(username='u1', email='u1@x.com', name='U1')
        person.set_password('x')
        db.session.add(person)
        db.session.commit()
        pid = person.person_id

        check_scan_allowed(pid)
        record_scan_attempt(pid)
        check_scan_allowed(pid)
        record_scan_attempt(pid)

        with pytest.raises(QuotaExceeded):
            check_scan_allowed(pid)


def test_global_quota(app):
    with app.app_context():
        for i in range(3):
            p = Person(username=f'u{i}', email=f'u{i}@x.com', name=f'U{i}')
            p.set_password('x')
            db.session.add(p)
        db.session.commit()

        for i in range(3):
            pid = Person.query.filter_by(username=f'u{i}').first().person_id
            record_scan_attempt(pid)

        pid = Person.query.filter_by(username='u0').first().person_id
        with pytest.raises(QuotaExceeded):
            check_scan_allowed(pid)
