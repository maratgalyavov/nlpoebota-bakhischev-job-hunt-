from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.api.deps import container
from app.bot.handlers_interview import (
    IX_EDUCATION,
    IX_EMPLOYMENT,
    IX_FORMAT,
    IX_SKILLS,
    persist_answer_and_show_next,
)
from app.bot.interview_keyboards import (
    EDUCATION_CODES,
    EMPLOYMENT_CODES,
    FORMAT_CODES,
    SKILL_CODES,
    skills_keyboard,
)

logger = logging.getLogger(__name__)


def _user_data_map(context: ContextTypes.DEFAULT_TYPE) -> dict:
    user_data = context.user_data
    if user_data is None:
        return {}
    return user_data


async def handle_interview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data or not query.from_user:
        return
    if not query.data.startswith("iv:"):
        return

    user_id = int(query.from_user.id)
    parts = query.data.split(":")
    # iv:sk:t:py | iv:sk:done | iv:ed:bak | iv:fmt:remote | iv:emp:full

    state = container.session_repo.get_last_session(user_id)
    if state is None or state.completed:
        await query.answer("Сессия не найдена или интервью уже завершено.", show_alert=True)
        return

    chat = query.message.chat if query.message else None
    if chat is None:
        await query.answer()
        return

    # --- навыки ---
    if len(parts) >= 3 and parts[1] == "sk":
        if state.question_index != IX_SKILLS:
            await query.answer("Этот вопрос уже не актуален.", show_alert=True)
            return

        if parts[2] == "t" and len(parts) >= 4:
            code = parts[3]
            if code not in SKILL_CODES:
                await query.answer()
                return
            user_data = _user_data_map(context)
            sel = user_data.setdefault("iv_skills", set())
            if code in sel:
                sel.remove(code)
            else:
                sel.add(code)
            await query.answer()
            if query.message:
                try:
                    await query.message.edit_reply_markup(reply_markup=skills_keyboard(sel))
                except Exception as exc:
                    logger.debug("edit_reply_markup: %s", exc)
            return

        if parts[2] == "done":
            user_data = _user_data_map(context)
            sel = user_data.get("iv_skills") or set()
            extra = (user_data.get("skill_extra") or "").strip()
            labels = [SKILL_CODES[c] for c in sorted(sel, key=lambda x: SKILL_CODES[x])]
            if extra:
                labels.append(extra)
            if not labels:
                await query.answer("Выбери навыки кнопками или напиши список в чат.", show_alert=True)
                return
            answer_text = ", ".join(labels)
            await query.answer("Сохранено ✓")
            await persist_answer_and_show_next(user_id, IX_SKILLS, answer_text, chat, context)
            return

    # --- образование ---
    if len(parts) >= 3 and parts[1] == "ed":
        if state.question_index != IX_EDUCATION:
            await query.answer("Этот вопрос уже не актуален.", show_alert=True)
            return
        code = parts[2]
        if code not in EDUCATION_CODES:
            await query.answer()
            return
        answer_text = EDUCATION_CODES[code]
        await query.answer()
        await persist_answer_and_show_next(user_id, IX_EDUCATION, answer_text, chat, context)
        return

    # --- формат работы ---
    if len(parts) >= 3 and parts[1] == "fmt":
        if state.question_index != IX_FORMAT:
            await query.answer("Этот вопрос уже не актуален.", show_alert=True)
            return
        code = parts[2]
        if code not in FORMAT_CODES:
            await query.answer()
            return
        answer_text = FORMAT_CODES[code]
        await query.answer()
        await persist_answer_and_show_next(user_id, IX_FORMAT, answer_text, chat, context)
        return

    # --- занятость ---
    if len(parts) >= 3 and parts[1] == "emp":
        if state.question_index != IX_EMPLOYMENT:
            await query.answer("Этот вопрос уже не актуален.", show_alert=True)
            return
        code = parts[2]
        if code not in EMPLOYMENT_CODES:
            await query.answer()
            return
        answer_text = EMPLOYMENT_CODES[code]
        await query.answer()
        await persist_answer_and_show_next(user_id, IX_EMPLOYMENT, answer_text, chat, context)
        return

    await query.answer()
