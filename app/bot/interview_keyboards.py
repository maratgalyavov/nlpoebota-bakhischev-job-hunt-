from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- callback_data: префикс iv: (interview), лимит 64 байта ---

SKILL_CODES: dict[str, str] = {
    "py": "Python",
    "cpp": "C++",
    "sql": "SQL",
    "xls": "Excel",
}

EDUCATION_CODES: dict[str, str] = {
    "so": "Среднее общее образование",
    "spo": "Среднее профессиональное образование",
    "nvo": "Неполное высшее образование",
    "bak": "Бакалавриат",
    "spec": "Специалитет",
    "mag": "Магистратура",
    "asp": "Аспирантура",
    "doc": "Докторантура",
}

FORMAT_CODES: dict[str, str] = {
    "remote": "Удалённая работа (remote)",
    "office": "Офис",
    "hybrid": "Гибрид (офис + remote)",
}

EMPLOYMENT_CODES: dict[str, str] = {
    "full": "Полная занятость",
    "part": "Частичная занятость",
}


def skills_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    def lbl(code: str) -> str:
        name = SKILL_CODES[code]
        emoji = {"py": "🐍", "cpp": "⚙️", "sql": "🗄", "xls": "📊"}[code]
        mark = "✅ " if code in selected else ""
        return f"{mark}{emoji} {name}"

    row1 = [
        InlineKeyboardButton(lbl("py"), callback_data="iv:sk:t:py"),
        InlineKeyboardButton(lbl("cpp"), callback_data="iv:sk:t:cpp"),
    ]
    row2 = [
        InlineKeyboardButton(lbl("sql"), callback_data="iv:sk:t:sql"),
        InlineKeyboardButton(lbl("xls"), callback_data="iv:sk:t:xls"),
    ]
    row3 = [
        InlineKeyboardButton("✔️ Готово", callback_data="iv:sk:done"),
    ]
    return InlineKeyboardMarkup([row1, row2, row3])


def education_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for code, full in EDUCATION_CODES.items():
        label = f"🎓 {full}"
        rows.append([InlineKeyboardButton(label, callback_data=f"iv:ed:{code}")])
    return InlineKeyboardMarkup(rows)


def format_work_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏠 Remote", callback_data="iv:fmt:remote"),
                InlineKeyboardButton("🏢 Офис", callback_data="iv:fmt:office"),
            ],
            [InlineKeyboardButton("🔀 Гибрид", callback_data="iv:fmt:hybrid")],
        ]
    )


def employment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏱ Полная", callback_data="iv:emp:full"),
                InlineKeyboardButton("🕐 Частичная", callback_data="iv:emp:part"),
            ]
        ]
    )


def skills_question_caption(base_question: str) -> str:
    return (
        f"🛠 <b>{base_question}</b>\n\n"
        "Нажми на навыки, которыми владеешь (можно несколько), затем "
        "<b>«Готово»</b>.\n"
        "✏️ В чат можно дописать другие инструменты — они добавятся к выбору."
    )


def education_question_caption(base_question: str) -> str:
    return f"🎓 <b>{base_question}</b>\n\nВыбери уровень образования:"


def format_question_caption(base_question: str) -> str:
    return f"🏢 <b>{base_question}</b>\n\nВыбери удобный формат:"


def employment_question_caption(base_question: str) -> str:
    return f"⏱ <b>{base_question}</b>\n\nЧто тебе ближе?"
