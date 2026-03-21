from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container
from app.domain.models import INTERVIEW_QUESTIONS_RU, InterviewState


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    user_id = int(update.effective_user.id)
    answer_text = " ".join(context.args).strip() if context.args else ""
    if not answer_text:
        await update.message.reply_text("Используй команду: /a <твой ответ>")
        return

    state = container.session_repo.get_last_session(user_id)
    if state is None:
        await update.message.reply_text("Сессия не найдена. Нажми /start")
        return
    if state.completed:
        await update.message.reply_text("Интервью уже завершено. Используй /resume или /match")
        return

    q_idx = state.question_index
    container.answer_repo.add_answer(
        session_id=state.session_id,
        question_index=q_idx,
        question_text=INTERVIEW_QUESTIONS_RU[q_idx],
        answer_text=answer_text,
    )
    transition = container.fsm.answer(q_idx)
    next_state = InterviewState(
        user_id=user_id,
        session_id=state.session_id,
        stage=transition.next_stage,
        question_index=transition.next_question_index,
        completed=transition.completed,
    )
    container.session_repo.update_session(next_state)
    if transition.completed:
        await update.message.reply_text(
            "Спасибо! Интервью завершено. Теперь доступно: /resume и /match"
        )
        return
    await update.message.reply_text(transition.ask_question or "Продолжаем интервью")

