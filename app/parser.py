from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .catalog import ASSETS, AssetSpec

PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

NOISE_WORDS = {
    "قیمت",
    "قیمتش",
    "نرخ",
    "نرخش",
    "چنده",
    "چند",
    "است",
    "هست",
    "بده",
    "بگو",
    "لطفا",
    "لطفاً",
    "میشه",
    "میشود",
    "می‌شود",
    "تومان",
    "تومن",
    "price",
    "rate",
    "please",
    "how",
    "much",
    "is",
    "of",
}

PERSIAN_SIMPLE = {
    "صفر": 0,
    "یک": 1,
    "یه": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "پنج": 5,
    "شش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,
    "ده": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "شانزده": 16,
    "هفده": 17,
    "هجده": 18,
    "نوزده": 19,
    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
    "صد": 100,
    "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
    "ششصد": 600,
    "هفتصد": 700,
    "هشتصد": 800,
    "نهصد": 900,
}

ENGLISH_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    asset: AssetSpec
    amount: Decimal


def normalize_text(value: str) -> str:
    value = value.translate(PERSIAN_DIGITS)
    value = value.replace("ي", "ی").replace("ك", "ک")
    value = value.replace("\u200c", " ")
    value = value.replace("٫", ".").replace("٬", "").replace(",", "")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s.\-]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def parse_query(text: str) -> ParsedQuery | None:
    normalized = normalize_text(text)
    asset = _find_asset(normalized)
    if asset is None:
        return None

    remaining = f" {normalized} "
    for alias in sorted(
        {normalize_text(alias) for alias in asset.aliases},
        key=len,
        reverse=True,
    ):
        remaining = remaining.replace(f" {alias} ", " ")

    tokens = [
        token
        for token in re.sub(r"\s+", " ", remaining).strip().split()
        if token not in NOISE_WORDS and token not in {"واحد", "unit"}
    ]

    amount = _parse_amount(tokens)
    if amount is None:
        amount = Decimal("1")

    if amount <= 0:
        return None

    return ParsedQuery(asset=asset, amount=amount)


def _find_asset(text: str) -> AssetSpec | None:
    padded = f" {text} "
    choices: list[tuple[int, AssetSpec]] = []

    for asset in ASSETS:
        for alias in asset.aliases:
            normalized_alias = normalize_text(alias)
            if f" {normalized_alias} " in padded:
                choices.append((len(normalized_alias), asset))

    if not choices:
        return None

    choices.sort(key=lambda item: item[0], reverse=True)
    return choices[0][1]


def _parse_amount(tokens: list[str]) -> Decimal | None:
    if not tokens:
        return None

    for token in tokens:
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            try:
                return Decimal(token)
            except InvalidOperation:
                return None

    persian_value = _parse_word_number(tokens, PERSIAN_SIMPLE, {"هزار": 1000, "میلیون": 1_000_000})
    if persian_value is not None:
        return Decimal(persian_value)

    english_value = _parse_word_number(
        tokens,
        ENGLISH_NUMBERS,
        {"thousand": 1000, "million": 1_000_000},
    )
    if english_value is not None:
        return Decimal(english_value)

    return None


def _parse_word_number(
    tokens: list[str],
    values: dict[str, int],
    scales: dict[str, int],
) -> int | None:
    if not any(token in values or token in scales for token in tokens):
        return None

    total = 0
    current = 0
    found = False

    for token in tokens:
        if token in {"و", "and"}:
            continue

        if token in scales:
            scale = scales[token]
            current = current or 1
            total += current * scale
            current = 0
            found = True
            continue

        value = values.get(token)
        if value is None:
            continue

        found = True
        if value == 100 and token == "hundred":
            current = (current or 1) * 100
        else:
            current += value

    return total + current if found else None
