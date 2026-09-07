from decimal import Decimal

from app.catalog import ASSET_BY_KEY
from app.formatter import format_quote, format_toman
from app.market_api import MarketQuote


def test_format_toman_rounds_and_separates() -> None:
    assert format_toman(Decimal("123456.7")) == "123,457"


def test_format_quote_for_multiple_euros() -> None:
    quote = MarketQuote(
        symbol="EUR",
        current=Decimal("150000"),
        high=Decimal("155000"),
        low=Decimal("148000"),
        change=Decimal("2500"),
        change_percent=Decimal("1.69"),
        updated_at="2026-09-08",
    )
    text = format_quote(ASSET_BY_KEY["eur"], Decimal("10"), quote)
    assert "1,500,000 تومان" in text
    assert "155,000 تومان" in text
    assert "+1.69٪" in text
