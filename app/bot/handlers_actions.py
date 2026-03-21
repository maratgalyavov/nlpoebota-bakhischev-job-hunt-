from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    user_id = int(update.effective_user.id)
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await update.message.reply_text("Сначала пройди /start")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await update.message.reply_text("Сначала ответь на вопросы интервью через /a")
        return
    profile = container.profile_service.from_answers(user_id, answers)
    resume = container.llm_service.generate_resume(profile.to_text())
    container.artifact_repo.save_artifact(
        user_id=user_id,
        session_id=session.session_id,
        artifact_type="resume",
        content=resume,
    )
    await update.message.reply_text(resume)


async def handle_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    user_id = int(update.effective_user.id)
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        await update.message.reply_text("Сначала пройди /start")
        return
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        await update.message.reply_text("Сначала ответь на вопросы интервью через /a")
        return

    profile = container.profile_service.from_answers(user_id, answers)
    vacancies = container.vacancy_service.load_vacancies()
    index = container.matching_service.build_index(vacancies)
    recs = container.matching_service.recommend(profile, index, top_k=5)
    by_id = {v.id: v for v in vacancies}

    if not recs:
        await update.message.reply_text("Пока нет точных совпадений. Попробуем расширить профиль.")
        return

    lines = ["Топ вакансий:"]
    for i, rec in enumerate(recs, start=1):
        v = by_id.get(rec.vacancy_id)
        if not v:
            continue
        lines.append(f"{i}. {v.title} — {v.company} ({round(rec.score, 3)})\n{v.url}")
    await update.message.reply_text("\n\n".join(lines))

