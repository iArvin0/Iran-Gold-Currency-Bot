from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import Settings
from .handlers import handle_text, help_command, start
from .logging_config import configure_logging
from .market_api import MarketAPI

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "شروع بات"),
            BotCommand("help", "راهنما"),
        ]
    )


async def post_shutdown(application: Application) -> None:
    api: MarketAPI | None = application.bot_data.get("market_api")
    if api:
        await api.close()


async def error_handler(update: object, context) -> None:
    del update
    logger.error("Telegram update error", exc_info=context.error)


def main() -> None:
    settings = Settings.from_env()
    configure_logging(
        settings.log_dir,
        settings.log_level,
        bot_token=settings.bot_token,
        api_key=settings.oanor_api_key,
    )

    logger.info("Starting Iran Gold & Currency Bot")

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["settings"] = settings
    application.bot_data["market_api"] = MarketAPI(settings)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)

    application.run_polling(drop_pending_updates=True)
