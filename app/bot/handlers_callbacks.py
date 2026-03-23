from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container
from app.bot.text_chunks import chunk_text


def _target_chat(update: Update):
    query = update.callback_query
    if query and query.message:
        return query.message.chat
    return update.effective_chat


async def handle_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    try:
        prefix, vacancy_id = query.data.split(":", 1)
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    await query.answer()
    user_id = int(query.from_user.id)

    if prefix == "l":
        await _send_cover_letter(update, user_id, vacancy_id)
    elif prefix == "g":
        await _send_skill_gaps(update, user_id, vacancy_id)
    elif prefix == "p":
        await _record_feedback(update, user_id, vacancy_id, True)
    elif prefix == "n":
        await _record_feedback(update, user_id, vacancy_id, False)


async def _send_cover_letter(update: Update, user_id: int, vacancy_id: str) -> None:
    chat = _target_chat(update)
    if chat is None:
        return
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await chat.send_message("Сначала нажми /start.")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await chat.send_message("Сначала пройди интервью.")
        return
    vac = container.vacancy_service.get_vacancy(vacancy_id)
    if vac is None:
        await chat.send_message("Вакансия не найдена (возможно, снята с публикации).")
        return
    profile = container.profile_service.from_answers(user_id, answers)
    profile_text = profile.to_text()
    vacancy_text = f"{vac.title}. {vac.company}. {vac.description}"
    await chat.send_message("Пишем сопроводительное письмо…")
    cover = container.llm_service.generate_cover_letter(profile_text, vacancy_text)
    container.artifact_repo.save_artifact(
        user_id=user_id,
        session_id=session.session_id,
        artifact_type="cover_letter",
        content=cover,
        meta_json=f'{{"vacancy_id":"{vac.id}"}}',
    )
    for part in chunk_text(cover):
        await chat.send_message(part)


async def _send_skill_gaps(update: Update, user_id: int, vacancy_id: str) -> None:
    chat = _target_chat(update)
    if chat is None:
        return
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await chat.send_message("Сначала нажми /start.")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await chat.send_message("Сначала пройди интервью.")
        return
    vac = container.vacancy_service.get_vacancy(vacancy_id)
    if vac is None:
        await chat.send_message("Вакансия не найдена.")
        return
    profile = container.profile_service.from_answers(user_id, answers)
    profile_text = profile.to_text()
    vacancy_text = f"{vac.title}. {vac.company}. {vac.description}"
    await chat.send_message("Считаем пробелы в навыках…")
    gaps = container.llm_service.generate_skill_gaps(profile_text, vacancy_text)
    container.artifact_repo.save_artifact(
        user_id=user_id,
        session_id=session.session_id,
        artifact_type="skill_gaps",
        content=gaps,
        meta_json=f'{{"vacancy_id":"{vac.id}"}}',
    )
    for part in chunk_text(gaps):
        await chat.send_message(part)


async def _record_feedback(update: Update, user_id: int, vacancy_id: str, positive: bool) -> None:
    chat = _target_chat(update)
    if chat is None:
        return
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await chat.send_message("Сначала нажми /start.")
        return
    container.feedback_repo.add_feedback(
        user_id=user_id,
        session_id=session.session_id,
        item_type="vacancy_match",
        item_id=vacancy_id,
        is_positive=positive,
        comment=None,
    )
    await chat.send_message("Спасибо за отклик — это поможет улучшить подборку.")
