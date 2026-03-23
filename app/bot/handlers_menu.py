from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container
from app.bot.handlers_actions import perform_match, perform_resume
from app.bot.handlers_interview import submit_interview_answer
from app.bot.handlers_start import run_start_interview
from app.bot.keyboards import BTN_HELP, BTN_MATCH, BTN_NEW_INTERVIEW, BTN_RESUME

HELP_TEXT = (
    "Как пользоваться ботом:\n\n"
    "1) /start или «Новое интервью» — короткое интервью (8 вопросов).\n"
    "2) На часть вопросов ответь кнопками (навыки, образование, формат, занятость), остальное — текстом.\n"
    "3) После завершения:\n"
    "   • «Резюме» — сгенерировать текст резюме.\n"
    "   • «Подбор вакансий» — топ-5 по базе вакансий проекта.\n"
    "4) Под каждой вакансией: сопроводительное письмо, skill gaps, 👍/👎, ссылка на вакансию.\n\n"
    "Команды: /resume, /match, /a <ответ>.\n\n"
    "Это AI-помощник: проверяй факты перед откликом."
)


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    user_id = int(update.effective_user.id)
    state = container.session_repo.get_last_session(user_id)

    if state and not state.completed:
        await submit_interview_answer(update, context, text)
        return

    if state and state.completed:
        if text == BTN_RESUME:
            await perform_resume(update, context)
        elif text == BTN_MATCH:
            await perform_match(update, context)
        elif text == BTN_HELP:
            await update.message.reply_text(HELP_TEXT)
        elif text == BTN_NEW_INTERVIEW:
            await run_start_interview(update, context)
        else:
            await update.message.reply_text(
                "Выбери действие кнопкой ниже или нажми «Помощь».\n"
                "Если хочешь начать заново — «Новое интервью».",
            )
        return

    await update.message.reply_text("Нажми /start, чтобы начать интервью.")
