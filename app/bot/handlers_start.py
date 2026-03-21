from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    user_id = int(update.effective_user.id)
    username = update.effective_user.username

    container.user_repo.upsert_user(user_id=user_id, telegram_username=username)
    transition = container.fsm.start()
    state = container.session_repo.create_session(
        user_id=user_id,
        stage=transition.next_stage,
        question_index=transition.next_question_index,
    )
    context.user_data["session_id"] = state.session_id
    await update.message.reply_text(
        "Привет! Я AI-карьерный помощник. Я не гарантирую трудоустройство, "
        "но помогу с резюме, подбором вакансий и анализом skill gaps.\n\n"
        f"Первый вопрос:\n{transition.ask_question}"
    )

