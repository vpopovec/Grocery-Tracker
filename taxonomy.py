"""Shared item taxonomy.

Lives at the repo root (stdlib only) so both processes can import it: the Flask
app (scan prompts, item editing) and the Streamlit financial tracker, which runs
out-of-process with its own inline dependency block.

Makro = široká skupina, mikro = podkategória (iba hodnoty z tohto zoznamu).
"""

HOUSEHOLD_EQUIPMENT_MACRO = "Domácnosť"
HOUSEHOLD_SUPPLIES_MACRO = "Drogéria a domáce potreby"

SLOVAK_TAXONOMY: dict[str, list[str]] = {
    "Čerstvé potraviny": [
        "Mliečne výrobky",
        "Pečivo a pekárenské výrobky",
        "Mäso a hydina",
        "Údeniny a salámy",
        "Ryby a morské plody",
        "Ovocie",
        "Zelenina",
        "Vajcia",
    ],
    "Trvanlivé potraviny": [
        "Cestoviny, ryža a obilniny",
        "Konzervované a pohotové jedlá",
        "Oleje, octy a dressingy",
        "Omáčky, dochucovadlá a koreniny",
        "Sladkosti a cukrovinky",
        "Snackové pochutiny a chipsy",
        "Cereálie a müsli",
        "Džemy, med a nátierky",
        "Prísady na pečenie",
        "Bezmäsité a rastlinné alternatívy",
    ],
    "Nápoje": [
        "Vody a minerálky",
        "Nealkoholické nápoje",
        "Šťavy a nektáry",
        "Káva",
        "Čaj",
        "Pivo",
        "Víno",
        "Liehoviny a destiláty",
    ],
    "Mrazené potraviny": [
        "Mrazená zelenina a ovocie",
        "Mrazené polotovary a jedlá",
        "Zmrzlina a mrazené dezerty",
    ],
    # Spotrebný tovar, ktorý sa minie (predtým sa tento makro volal "Domácnosť").
    HOUSEHOLD_SUPPLIES_MACRO: [
        "Čistiace prostriedky",
        "Papierové výrobky a utierky",
        "Sáčky, fólie a obaly",
        "Sviečky a zápalky",
    ],
    # Trvácne vybavenie domácnosti — investícia, nie spotreba.
    HOUSEHOLD_EQUIPMENT_MACRO: [
        "Nábytok",
        "Osvetlenie",
        "Kuchynské spotrebiče",
        "Veľké spotrebiče",
        "Riad a kuchynské potreby",
        "Bytový textil a doplnky",
        "Náradie a železiarstvo",
        "Záhrada a rastliny",
        "Elektronika a domáca technika",
    ],
    "Osobná hygiena a kozmetika": [
        "Starostlivosť o telo",
        "Starostlivosť o vlasy",
        "Ústna hygiena",
        "Kozmetika a parfuméria",
    ],
    "Zdravie a drogéria": [
        "Vitamíny a doplnky výživy",
        "Lieky bez predpisu (OTC)",
        "Hygienické potreby",
    ],
    "Pre zvieratá": [
        "Krmivo",
        "Pamlsky a doplnky pre zvieratá",
    ],
    "Ostatné": [
        "Nezaradené",
        "Textil a oblečenie",
        "Sezónne a darčekové",
    ],
}

# Micros that used to live under the old consumables meaning of "Domácnosť".
# Used by the one-off backfill in sqlite_db.ensure_household_taxonomy_rename.
LEGACY_HOUSEHOLD_SUPPLY_MICROS = tuple(SLOVAK_TAXONOMY[HOUSEHOLD_SUPPLIES_MACRO])

SHOP_NAMES = [
    "Lidl",
    "Kaufland",
    "Tesco",
    "Billa",
    "Coop Jednota",
    "Metro",
    "Yeme",
    "dm drogerie markt",
    "IKEA",
    "Jysk",
    "Möbelix",
    "Alza",
    "Datart",
    "OBI",
    "Hornbach",
    "Unknown",
]

DEFAULT_MACRO = "Ostatné"
DEFAULT_MICRO = "Nezaradené"


def macro_categories() -> list[str]:
    """All macro categories, in taxonomy order."""
    return list(SLOVAK_TAXONOMY)


def micro_categories(macro: str) -> list[str]:
    """Micro categories belonging to `macro`, or [] if the macro is unknown."""
    return list(SLOVAK_TAXONOMY.get(macro, []))


def is_valid_pair(macro: str, micro: str) -> bool:
    return micro in SLOVAK_TAXONOMY.get(macro, [])


def default_micro_for(macro: str) -> str:
    """First micro of `macro` — used when a macro changes without a matching micro."""
    micros = SLOVAK_TAXONOMY.get(macro)
    return micros[0] if micros else DEFAULT_MICRO
