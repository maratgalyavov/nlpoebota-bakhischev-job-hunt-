from __future__ import annotations

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from app.bot.backend_client import BackendClientError, start_interview


def _user_data_map(context: ContextTypes.DEFAULT_TYPE) -> dict:
    user_data = context.user_data
    if user_data is None:
        return {}
    return user_data


async def run_start_interview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return
    msg = update.effective_message
    if msg is None:
        return
    user_id = int(update.effective_user.id)
    username = update.effective_user.username

    try:
        state = await start_interview(user_id=user_id, telegram_username=username)
    except BackendClientError as exc:
        await msg.reply_text(exc.user_message)
        return
    user_data = _user_data_map(context)
    user_data["session_id"] = state.session_id
    user_data.pop("iv_skills", None)
    user_data.pop("skill_extra", None)
    await msg.reply_text(
        "Привет! Я AI-карьерный помощник. Я не гарантирую трудоустройство, "
        "но помогу с резюме и подбором вакансий из базы. "
        "и анализом skill gaps.\n\n"
        "Отвечай на вопросы обычными сообщениями в чат (команда /a тоже работает).\n\n"
        f"Первый вопрос:\n{state.question_text}",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_start_interview(update, context)
