from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from app.bot.handlers_actions import handle_match, handle_resume
from app.bot.handlers_interview import handle_answer
from app.bot.handlers_start import handle_start
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_telegram_app() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for bot runtime")
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("resume", handle_resume))
    app.add_handler(CommandHandler("match", handle_match))
    app.add_handler(CommandHandler("a", handle_answer))
    return app


def run_bot() -> None:
    logger.info("Starting Telegram bot")
    app = build_telegram_app()
    app.run_polling()


if __name__ == "__main__":
    run_bot()

