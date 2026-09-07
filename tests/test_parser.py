from decimal import Decimal

import pytest

from app.parser import parse_query


@pytest.mark.parametrize(
    ("text", "asset_key", "amount"),
    [
        ("یورو", "eur", Decimal("1")),
        ("۱۰ یورو", "eur", Decimal("10")),
        ("یک یورو", "eur", Decimal("1")),
        ("10 euro", "eur", Decimal("10")),
        ("25 USD", "usd", Decimal("25")),
        ("ده دلار", "usd", Decimal("10")),
        ("دلار کانادا", "cad", Decimal("1")),
        ("۵ دلار کانادا", "cad", Decimal("5")),
        ("1.5 پوند", "gbp", Decimal("1.5")),
        ("۱۰ گرم طلا", "gold18", Decimal("10")),
        ("طلای ۲۴ عیار", "gold24", Decimal("1")),
        ("۲ سکه امامی", "emami", Decimal("2")),
        ("ربع سکه", "quartercoin", Decimal("1")),
    ],
)
def test_parse_query(text: str, asset_key: str, amount: Decimal) -> None:
    parsed = parse_query(text)
    assert parsed is not None
    assert parsed.asset.key == asset_key
    assert parsed.amount == amount


def test_unknown_query_returns_none() -> None:
    assert parse_query("سلام خوبی؟") is None


def test_zero_amount_is_rejected() -> None:
    assert parse_query("0 یورو") is None
