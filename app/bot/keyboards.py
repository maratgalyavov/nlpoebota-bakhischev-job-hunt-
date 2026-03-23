from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# Тексты кнопок reply-клавиатуры (должны совпадать с проверкой в handle_free_text)
BTN_RESUME = "📄 Резюме"
BTN_MATCH = "🔍 Подбор вакансий"
BTN_HELP = "❓ Помощь"
BTN_NEW_INTERVIEW = "🔄 Новое интервью"


def main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_RESUME), KeyboardButton(BTN_MATCH)],
            [KeyboardButton(BTN_HELP), KeyboardButton(BTN_NEW_INTERVIEW)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выбери действие или напиши ответ на вопрос…",
    )


def vacancy_card_keyboard(vacancy_id: str, url: str) -> InlineKeyboardMarkup:
    """callback_data ≤ 64 байта: префикс + id (hh — обычно короткий числовой)."""
    row_actions = [
        InlineKeyboardButton("📝 Письмо", callback_data=f"l:{vacancy_id}"),
        InlineKeyboardButton("📊 Skill gaps", callback_data=f"g:{vacancy_id}"),
    ]
    row_feedback = [
        InlineKeyboardButton("👍 Релевантно", callback_data=f"p:{vacancy_id}"),
        InlineKeyboardButton("👎 Не подошло", callback_data=f"n:{vacancy_id}"),
    ]
    row_link = [InlineKeyboardButton("🔗 Открыть вакансию", url=url)]
    return InlineKeyboardMarkup([row_actions, row_feedback, row_link])
