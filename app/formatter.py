from __future__ import annotations

import html
from decimal import ROUND_HALF_UP, Decimal

from .catalog import AssetSpec
from .market_api import MarketQuote


def format_quote(asset: AssetSpec, amount: Decimal, quote: MarketQuote) -> str:
    amount_label = format_amount(amount)
    current_total = quote.current * amount

    lines = [
        f"{asset.emoji} <b>{html.escape(amount_label)} {html.escape(asset.fa_name)}</b>",
        "",
        f"💰 نرخ هر {html.escape(asset.unit_fa)}: <b>{format_toman(quote.current)} تومان</b>",
    ]

    if amount != Decimal("1"):
        lines.append(
            f"🧮 ارزش {html.escape(amount_label)} {html.escape(asset.unit_fa)}: "
            f"<b>{format_toman(current_total)} تومان</b>"
        )

    lines.append("")

    if quote.high is not None:
        lines.append(f"📈 بالاترین روز: <b>{format_toman(quote.high)} تومان</b>")
    if quote.low is not None:
        lines.append(f"📉 پایین‌ترین روز: <b>{format_toman(quote.low)} تومان</b>")
    if quote.open is not None:
        lines.append(f"🔓 قیمت بازشدن: {format_toman(quote.open)} تومان")

    change_line = _format_change(quote)
    if change_line:
        lines.append(change_line)

    if quote.updated_at:
        lines.extend(["", f"🕒 بروزرسانی: {html.escape(str(quote.updated_at))}"])

    lines.extend(
        [
            "",
            "<i>قیمت‌ها بر اساس داده بازار آزاد منبع API هستند.</i>",
        ]
    )
    return "\n".join(lines)


def format_toman(value: Decimal) -> str:
    rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(rounded):,}"


def format_amount(value: Decimal) -> str:
    if value == value.to_integral():
        return f"{int(value):,}"
    normalized = value.normalize()
    return format(normalized, "f")


def _format_change(quote: MarketQuote) -> str | None:
    if quote.change is None and quote.change_percent is None:
        return None

    change = quote.change
    percent = quote.change_percent

    positive = False
    negative = False
    if change is not None:
        positive = change > 0
        negative = change < 0
    elif percent is not None:
        positive = percent > 0
        negative = percent < 0

    icon = "🔺" if positive else "🔻" if negative else "➖"
    parts: list[str] = []

    if change is not None:
        sign = "+" if change > 0 else ""
        parts.append(f"{sign}{format_toman(change)} تومان")

    if percent is not None:
        sign = "+" if percent > 0 else ""
        parts.append(f"{sign}{format_percent(percent)}٪")

    return f"{icon} تغییر روزانه: <b>{' | '.join(parts)}</b>"


def format_percent(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):f}".rstrip("0").rstrip(".")
