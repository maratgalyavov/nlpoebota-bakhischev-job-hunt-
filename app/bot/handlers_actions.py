from __future__ import annotations

from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.backend_client import BackendClientError, generate_resume, match_vacancies
from app.bot.keyboards import vacancy_card_keyboard
from app.bot.text_chunks import chunk_text


async def perform_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or update.effective_user is None:
        return
    user_id = int(update.effective_user.id)
    await msg.reply_text("Генерируем резюме…")
    try:
        resume = await generate_resume(user_id)
    except BackendClientError as exc:
        await msg.reply_text(exc.user_message)
        return
    for part in chunk_text(resume):
        await msg.reply_text(part)


async def perform_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or update.effective_user is None:
        return
    user_id = int(update.effective_user.id)
    status_msg = await msg.reply_text("Считаем подборку по базе вакансий…")
    try:
        recs = await match_vacancies(user_id, top_k=5)
    except BackendClientError as exc:
        try:
            await status_msg.delete()
        except Exception:
            pass
        await msg.reply_text(exc.user_message)
        return

    try:
        await status_msg.delete()
    except Exception:
        pass

    if not recs:
        await msg.reply_text(
            "Пока нет уверенных совпадений. Попробуй «Новое интервью» и уточни роль, стек или город.",
        )
        return

    await msg.reply_text("Топ вакансий — под каждой карточкой кнопки: письмо, skill gaps, отзыв 👍/👎, ссылка.")
    for i, rec in enumerate(recs, start=1):
        reasons = "\n".join(f"• {r}" for r in rec.explainability.get("reasons", []))
        preview = rec.description_preview
        salary = ""
        if rec.salary_from or rec.salary_to:
            salary = f"💰 от {rec.salary_from or '—'} до {rec.salary_to or '—'} ₽\n"
        body = (
            f"{i}. {escape(rec.title)} — {escape(rec.company)}\n"
            f"📍 {escape(rec.location or '—')} · совпадение {round(rec.score, 3)}\n"
            f"{salary}"
            f"{reasons}\n\n"
            f"Описание: {escape(preview or '—')}\n"
            f"🔗 <a href=\"{escape(rec.url, quote=True)}\">Открыть вакансию</a>"
        )
        await msg.reply_text(
            body,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=vacancy_card_keyboard(rec.vacancy_id, rec.url),
        )


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await perform_resume(update, context)


async def handle_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await perform_match(update, context)
