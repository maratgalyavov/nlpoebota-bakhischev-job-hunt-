from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.backend_client import (
    BackendClientError,
    BackendNotFoundError,
    answer_interview,
    get_interview_state,
)
from app.bot.interview_keyboards import (
    education_keyboard,
    education_question_caption,
    employment_keyboard,
    employment_question_caption,
    format_question_caption,
    format_work_keyboard,
    skills_keyboard,
    skills_question_caption,
)
from app.bot.keyboards import main_menu_reply_keyboard
from app.domain.models import INTERVIEW_QUESTIONS_RU

# Индексы вопросов с inline-кнопками
IX_SKILLS = 1
IX_EDUCATION = 2
IX_FORMAT = 7
IX_EMPLOYMENT = 8


def _user_data_map(context: ContextTypes.DEFAULT_TYPE) -> dict:
    user_data = context.user_data
    if user_data is None:
        return {}
    return user_data


def _reset_skill_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = _user_data_map(context)
    user_data.pop("iv_skills", None)
    user_data.pop("skill_extra", None)


async def send_next_question_prompt(
    chat,
    context: ContextTypes.DEFAULT_TYPE,
    next_q_idx: int,
    question_plain: str | None,
) -> None:
    """Отправляет следующий вопрос: с inline-клавиатурой или обычным текстом."""
    text = question_plain or (
        INTERVIEW_QUESTIONS_RU[next_q_idx] if next_q_idx < len(INTERVIEW_QUESTIONS_RU) else ""
    )

    if next_q_idx == IX_SKILLS:
        _reset_skill_draft(context)
        user_data = _user_data_map(context)
        user_data["iv_skills"] = set()
        user_data["skill_extra"] = ""
        await chat.send_message(
            skills_question_caption(text),
            reply_markup=skills_keyboard(set()),
            parse_mode="HTML",
        )
        return

    if next_q_idx == IX_EDUCATION:
        await chat.send_message(
            education_question_caption(text),
            reply_markup=education_keyboard(),
            parse_mode="HTML",
        )
        return

    if next_q_idx == IX_FORMAT:
        await chat.send_message(
            format_question_caption(text),
            reply_markup=format_work_keyboard(),
            parse_mode="HTML",
        )
        return

    if next_q_idx == IX_EMPLOYMENT:
        await chat.send_message(
            employment_question_caption(text),
            reply_markup=employment_keyboard(),
            parse_mode="HTML",
        )
        return

    await chat.send_message(f"💬 {text}")


async def persist_answer_and_show_next(
    user_id: int,
    q_idx: int,
    answer_text: str,
    chat,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Сохраняет ответ на вопрос q_idx и показывает следующий шаг.
    Возвращает True, если интервью завершено.
    """
    try:
        state = await get_interview_state(user_id)
    except BackendNotFoundError:
        await chat.send_message("Сессия не найдена. Нажми /start или «Новое интервью».")
        return False
    except BackendClientError as exc:
        await chat.send_message(exc.user_message)
        return False

    if state.completed:
        return False
    if state.question_index != q_idx:
        return False

    try:
        next_state = await answer_interview(user_id=user_id, answer_text=answer_text)
    except BackendNotFoundError:
        await chat.send_message("Сессия не найдена. Нажми /start или «Новое интервью».")
        return False
    except BackendClientError as exc:
        await chat.send_message(exc.user_message)
        return False

    if q_idx == IX_SKILLS:
        _reset_skill_draft(context)

    if next_state.completed:
        await chat.send_message(
            "🎉 Спасибо! Интервью завершено.\n\n"
            "Дальше — кнопками внизу: резюме, подбор вакансий, письмо и skill gaps под каждой карточкой.",
            reply_markup=main_menu_reply_keyboard(),
        )
        return True

    await send_next_question_prompt(
        chat,
        context,
        next_state.question_index,
        next_state.next_question,
    )
    return False


async def submit_interview_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    answer_text: str,
) -> None:
    if update.effective_user is None:
        return
    msg = update.effective_message
    if msg is None:
        return
    user_id = int(update.effective_user.id)
    answer_text = answer_text.strip()
    if not answer_text:
        await msg.reply_text("Напиши ответ одним сообщением или используй: /a <твой ответ>")
        return

    try:
        state = await get_interview_state(user_id)
    except BackendNotFoundError:
        await msg.reply_text("Сессия не найдена. Нажми /start или «Новое интервью».")
        return
    except BackendClientError as exc:
        await msg.reply_text(exc.user_message)
        return
    if state.completed:
        await msg.reply_text("Интервью уже завершено. Используй кнопки меню ниже или команды /resume и /match.")
        return

    q_idx = state.question_index

    # Вопрос про навыки: если уже есть выбор кнопками или доп. текст — дописываем; иначе весь текст = ответ
    user_data = _user_data_map(context)
    if q_idx == IX_SKILLS and user_data.get("iv_skills") is not None:
        skills = user_data.get("iv_skills") or set()
        extra_prev = (user_data.get("skill_extra") or "").strip()
        if len(skills) == 0 and not extra_prev:
            pass
        else:
            if extra_prev:
                user_data["skill_extra"] = f"{extra_prev}, {answer_text}"
            else:
                user_data["skill_extra"] = answer_text
            await msg.reply_text(
                "✅ Добавил к ответу. Нажми «✔️ Готово» на кнопках под вопросом или допиши ещё текстом.",
            )
            return

    await persist_answer_and_show_next(user_id, q_idx, answer_text, msg.chat, context)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    answer_text = " ".join(context.args).strip() if context.args else ""
    if not answer_text:
        await update.message.reply_text(
            "Используй: /a <твой ответ> или просто напиши ответ обычным сообщением.",
        )
        return
    await submit_interview_answer(update, context, answer_text)
