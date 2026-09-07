from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .errors import UserFacingError
from .formatter import format_quote
from .market_api import MarketAPI
from .parser import parse_query

logger = logging.getLogger(__name__)

START_TEXT = """\
💰 <b>بات قیمت ارز، طلا و سکه</b>

اسم ارز یا دارایی را بفرست؛ اگر تعداد ننویسی، قیمت یک واحد نمایش داده می‌شود.

<b>نمونه‌ها:</b>
<code>یورو</code>
<code>۱۰ یورو</code>
<code>یک یورو</code>
<code>25 USD</code>
<code>دلار کانادا</code>
<code>۱۰ گرم طلا</code>
<code>طلای ۲۴ عیار</code>
<code>سکه امامی</code>
<code>۲ نیم سکه</code>

قیمت‌ها فقط به <b>تومان</b> نمایش داده می‌شوند.
برای دیدن دارایی‌های پشتیبانی‌شده /help را بزن.
"""

HELP_TEXT = """\
📚 <b>راهنما</b>

<b>ارزها:</b>
💵 دلار آمریکا — USD
💶 یورو — EUR
💷 پوند انگلیس — GBP
🇦🇪 درهم امارات — AED
🇹🇷 لیر ترکیه — TRY
🇨🇦 دلار کانادا — CAD
🇦🇺 دلار استرالیا — AUD
🇨🇭 فرانک سوئیس — CHF
🇨🇳 یوان چین — CNY
🇷🇺 روبل روسیه — RUB
🇮🇶 دینار عراق — IQD
🇸🇦 ریال عربستان — SAR
🇯🇵 ین ژاپن — JPY

<b>طلا:</b>
🥇 طلای ۱۸ عیار
🥇 طلای ۲۴ عیار
⚖️ مثقال طلا
🌍 اونس جهانی طلا

<b>سکه:</b>
🪙 سکه امامی
🪙 سکه بهار آزادی
🪙 نیم سکه
🪙 ربع سکه
🪙 سکه گرمی

<b>ورودی‌های قابل فهم:</b>
<code>یورو</code>
<code>۱۰ یورو</code>
<code>10 euro</code>
<code>EUR</code>
<code>یک دلار</code>
<code>ده دلار</code>
<code>5 گرم طلا</code>

خروجی شامل نرخ فعلی، بالاترین/پایین‌ترین روز، تغییر روزانه و زمان بروزرسانی است؛
هرجا منبع API آن فیلد را ارائه کند.

<b>دستورات:</b>
/start
/help
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            START_TEXT,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(
            HELP_TEXT,
            parse_mode=ParseMode.HTML,
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not message.text or not user:
        return

    parsed = parse_query(message.text)
    if parsed is None:
        await message.reply_text(
            "❌ متوجه نشدم.\n\n"
            "مثلاً بنویس:\n"
            "<code>یورو</code>\n"
            "<code>۱۰ دلار</code>\n"
            "<code>طلای ۱۸ عیار</code>\n"
            "<code>سکه امامی</code>\n\n"
            "برای لیست کامل /help را بزن.",
            parse_mode=ParseMode.HTML,
        )
        return

    api: MarketAPI = context.application.bot_data["market_api"]

    logger.info(
        "Market query | user_id=%s | asset=%s | amount=%s",
        user.id,
        parsed.asset.key,
        parsed.amount,
    )

    status = await message.reply_text("⏳ در حال دریافت آخرین نرخ…")

    try:
        quote = await api.get_quote(parsed.asset)
        text = format_quote(parsed.asset, parsed.amount, quote)
        await status.edit_text(text, parse_mode=ParseMode.HTML)

    except UserFacingError as exc:
        logger.info(
            "User-facing market error | asset=%s | error=%s",
            parsed.asset.key,
            exc,
        )
        await status.edit_text(
            f"❌ <b>دریافت قیمت ناموفق بود</b>\n\n{exc}",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("Unhandled market query failure | asset=%s", parsed.asset.key)
        await status.edit_text(
            "❌ <b>خطای غیرمنتظره</b>\n\n"
            "مشکلی رخ داد. فایل log را برای جزئیات بررسی کنید.",
            parse_mode=ParseMode.HTML,
        )
