from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.backend_client import (
    BackendClientError,
    add_feedback,
    generate_cover_letter,
    generate_skill_gaps,
)
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
    await chat.send_message("Пишем сопроводительное письмо…")
    try:
        cover = await generate_cover_letter(user_id, vacancy_id)
    except BackendClientError as exc:
        await chat.send_message(exc.user_message)
        return
    for part in chunk_text(cover):
        await chat.send_message(part)


async def _send_skill_gaps(update: Update, user_id: int, vacancy_id: str) -> None:
    chat = _target_chat(update)
    if chat is None:
        return
    await chat.send_message("Считаем пробелы в навыках…")
    try:
        gaps = await generate_skill_gaps(user_id, vacancy_id)
    except BackendClientError as exc:
        await chat.send_message(exc.user_message)
        return
    for part in chunk_text(gaps):
        await chat.send_message(part)


async def _record_feedback(update: Update, user_id: int, vacancy_id: str, positive: bool) -> None:
    chat = _target_chat(update)
    if chat is None:
        return
    try:
        await add_feedback(
            user_id=user_id,
            session_id=None,
            item_type="vacancy_match",
            item_id=vacancy_id,
            is_positive=positive,
            comment=None,
        )
    except BackendClientError as exc:
        await chat.send_message(exc.user_message)
        return
    await chat.send_message("Спасибо за отклик — это поможет улучшить подборку.")
