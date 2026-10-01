"""Per-user custom shops on top of the taxonomy.SHOP_NAMES defaults."""

from __future__ import annotations

from sqlalchemy import select

from g_tracker import db
from g_tracker.models import PersonShop
from taxonomy import SHOP_NAMES

UNKNOWN = "Unknown"


def shop_key(name: str) -> str:
    """Case-insensitive identity key (collapsed whitespace)."""
    return " ".join(name.split()).casefold()


def clean_shop_name(raw: str) -> str:
    return " ".join((raw or "").split())


def get_custom_shop_names(person_id: int) -> list[str]:
    rows = db.session.execute(
        select(PersonShop.shop_name)
        .where(PersonShop.person_id == person_id)
        .order_by(PersonShop.shop_name)
    ).scalars().all()
    return list(rows)


def shops_for_prompt(person_id: int) -> list[str]:
    """Defaults + this user's customs, with Unknown last."""
    base = [s for s in SHOP_NAMES if s != UNKNOWN]
    seen = {shop_key(s) for s in base}
    customs: list[str] = []
    for name in get_custom_shop_names(person_id):
        key = shop_key(name)
        if key and key not in seen and key != shop_key(UNKNOWN):
            customs.append(name)
            seen.add(key)
    return base + customs + [UNKNOWN]


def resolve_shop_name(raw: str, known: list[str]) -> str | None:
    """Map user input to a canonical known name, or cleaned new name.

    Returns None for empty input or when the name is Unknown.
    """
    cleaned = clean_shop_name(raw)
    if not cleaned or shop_key(cleaned) == shop_key(UNKNOWN):
        return None
    key = shop_key(cleaned)
    for name in known:
        if shop_key(name) == key:
            return name
    return cleaned


def register_or_resolve_shop(person_id: int, raw_name: str) -> str | None:
    """Resolve name against defaults + customs; persist if it is a new custom.

    Does not create a person_shop row when the name matches a default.
    Returns the canonical shop_name to store on the receipt, or None if invalid.
    """
    defaults = [s for s in SHOP_NAMES if s != UNKNOWN]
    customs = get_custom_shop_names(person_id)
    resolved = resolve_shop_name(raw_name, defaults + customs)
    if resolved is None:
        return None

    default_keys = {shop_key(s) for s in defaults}
    custom_keys = {shop_key(s) for s in customs}
    key = shop_key(resolved)
    if key not in default_keys and key not in custom_keys:
        db.session.add(PersonShop(person_id=person_id, shop_name=resolved))
        db.session.commit()
    return resolved
