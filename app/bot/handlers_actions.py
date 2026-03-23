from __future__ import annotations

from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container
from app.bot.keyboards import vacancy_card_keyboard
from app.bot.text_chunks import chunk_text
from app.services.explainability import build_explainability


async def perform_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or update.effective_user is None:
        return
    user_id = int(update.effective_user.id)
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await msg.reply_text("Сначала нажми /start или «Новое интервью».")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await msg.reply_text("Сначала ответь на все вопросы интервью — просто сообщениями в чат.")
        return
    profile = container.profile_service.from_answers(user_id, answers)
    await msg.reply_text("Генерируем резюме…")
    resume = container.llm_service.generate_resume(profile.to_text())
    container.artifact_repo.save_artifact(
        user_id=user_id,
        session_id=session.session_id,
        artifact_type="resume",
        content=resume,
    )
    for part in chunk_text(resume):
        await msg.reply_text(part)


async def perform_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or update.effective_user is None:
        return
    user_id = int(update.effective_user.id)
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await msg.reply_text("Сначала нажми /start или «Новое интервью».")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await msg.reply_text("Сначала пройди интервью — отвечай на вопросы сообщениями в чат.")
        return

    profile = container.profile_service.from_answers(user_id, answers)
    status_msg = await msg.reply_text("Считаем подборку по базе вакансий…")
    vacancies = container.vacancy_service.load_vacancies()
    index = container.matching_service.build_index(vacancies)
    recs = container.matching_service.recommend(profile, index, top_k=5)
    by_id = {v.id: v for v in vacancies}

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
        v = by_id.get(rec.vacancy_id)
        if not v:
            continue
        exp = build_explainability(profile, v)
        reasons = "\n".join(f"• {r}" for r in exp["reasons"])
        desc = (v.description or "").replace("\n", " ").strip()
        preview = desc[:400] + ("…" if len(desc) > 400 else "")
        salary = ""
        if v.salary_from or v.salary_to:
            salary = f"💰 от {v.salary_from or '—'} до {v.salary_to or '—'} ₽\n"
        body = (
            f"{i}. {escape(v.title)} — {escape(v.company)}\n"
            f"📍 {escape(v.location or '—')} · совпадение {round(rec.score, 3)}\n"
            f"{salary}"
            f"{reasons}\n\n"
            f"Описание: {escape(preview or '—')}\n"
            f"🔗 <a href=\"{escape(v.url, quote=True)}\">Открыть вакансию</a>"
        )
        await msg.reply_text(
            body,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=vacancy_card_keyboard(v.id, v.url),
        )


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await perform_resume(update, context)


async def handle_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await perform_match(update, context)
