from decimal import Decimal

from app.catalog import ASSET_BY_KEY
from app.market_api import find_quote, find_symbol, first_quote, quote_from_record


def test_currency_quote_from_toman_fields() -> None:
    payload = {
        "data": [
            {
                "symbol": "USD",
                "name": "US Dollar",
                "close_toman": 123_000,
                "open_toman": 120_000,
                "high_toman": 125_000,
                "low_toman": 119_000,
                "change_toman": 3_000,
                "change_percent": 2.5,
                "date": "2026-09-08",
            },
            {
                "symbol": "EUR",
                "name": "Euro",
                "close_toman": 145_000,
                "high_toman": 147_000,
                "low_toman": 143_000,
            },
        ]
    }

    quote = find_quote(payload, ASSET_BY_KEY["eur"])
    assert quote is not None
    assert quote.symbol == "EUR"
    assert quote.current == Decimal("145000")
    assert quote.high == Decimal("147000")
    assert quote.low == Decimal("143000")


def test_rial_fields_are_converted_to_toman() -> None:
    record = {
        "symbol": "USD",
        "price_rial": 1_230_000,
        "high_rial": 1_250_000,
        "low_rial": 1_190_000,
    }
    quote = quote_from_record(record)
    assert quote is not None
    assert quote.current == Decimal("123000")
    assert quote.high == Decimal("125000")
    assert quote.low == Decimal("119000")


def test_nested_toman_fields() -> None:
    record = {
        "symbol": "USD",
        "price": {"toman": "123,000"},
        "high": {"toman": "125,000"},
        "low": {"toman": "119,000"},
    }
    quote = quote_from_record(record)
    assert quote is not None
    assert quote.current == Decimal("123000")
    assert quote.high == Decimal("125000")


def test_find_gold_by_name_and_path() -> None:
    payload = {
        "gold": {
            "geram18": {
                "name": "طلای 18 عیار",
                "price_toman": 9_500_000,
                "high_toman": 9_600_000,
                "low_toman": 9_400_000,
            }
        }
    }
    quote = find_quote(payload, ASSET_BY_KEY["gold18"])
    assert quote is not None
    assert quote.current == Decimal("9500000")


def test_find_gold_symbol() -> None:
    payload = {
        "symbols": [
            {"symbol": "GERAM18", "name": "طلای 18 عیار"},
            {"symbol": "EMAMI", "name": "سکه امامی"},
        ]
    }
    assert find_symbol(payload, ASSET_BY_KEY["gold18"]) == "GERAM18"
    assert find_symbol(payload, ASSET_BY_KEY["emami"]) == "EMAMI"


def test_find_symbol_from_flat_list() -> None:
    payload = {"symbols": ["USD", "GERAM18", "EMAMI"]}
    assert find_symbol(payload, ASSET_BY_KEY["gold18"]) == "GERAM18"


def test_first_quote_from_wrapped_dedicated_response() -> None:
    payload = {"data": {"price_toman": 123_000, "high_toman": 125_000}}
    quote = first_quote(payload, symbol_hint="USD")
    assert quote is not None
    assert quote.symbol == "USD"
    assert quote.current == Decimal("123000")
