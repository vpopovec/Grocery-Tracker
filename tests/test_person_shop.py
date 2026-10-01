from config import Config
from g_tracker import create_app, db
from g_tracker.models import Person
from g_tracker.shops import (
    UNKNOWN,
    register_or_resolve_shop,
    resolve_shop_name,
    shop_key,
    shops_for_prompt,
)
from taxonomy import SHOP_NAMES
import pytest


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RATELIMIT_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    assert 'receipts.db' not in app.config['SQLALCHEMY_DATABASE_URI']
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


def test_shop_key_normalizes_case_and_space():
    assert shop_key('  Lidl  ') == shop_key('lidl')
    assert shop_key('Coop  Jednota') == shop_key('coop jednota')


def test_resolve_rejects_unknown_and_empty():
    known = [s for s in SHOP_NAMES if s != UNKNOWN]
    assert resolve_shop_name('', known) is None
    assert resolve_shop_name('Unknown', known) is None
    assert resolve_shop_name('lidl', known) == 'Lidl'
    assert resolve_shop_name('Biedronka', known) == 'Biedronka'


def test_register_custom_shop_and_prompt_injection(app):
    with app.app_context():
        pid = _add_user()
        assert 'Biedronka' not in shops_for_prompt(pid)

        name = register_or_resolve_shop(pid, '  biedronka ')
        assert name == 'biedronka'
        prompt_shops = shops_for_prompt(pid)
        assert 'biedronka' in prompt_shops
        assert prompt_shops[-1] == UNKNOWN

        # Case-insensitive dedupe: same custom, keep first spelling
        again = register_or_resolve_shop(pid, 'BIEDRONKA')
        assert again == 'biedronka'
        assert shops_for_prompt(pid).count('biedronka') == 1

        # Defaults are not duplicated into person_shop
        assert register_or_resolve_shop(pid, 'tesco') == 'Tesco'
        assert 'Tesco' in shops_for_prompt(pid)
