from __future__ import annotations


def build_resume_prompt(profile_text: str) -> str:
    return (
        "Ты карьерный AI-помощник. Составь структурированное резюме на русском языке. "
        "Не придумывай факты, используй только данные пользователя. "
        "Разделы: Заголовок, О себе, Опыт, Навыки, Образование, Дополнительно.\n\n"
        f"Профиль пользователя:\n{profile_text}"
    )


def build_cover_letter_prompt(profile_text: str, vacancy_text: str) -> str:
    return (
        "Составь сопроводительное письмо на русском языке (150-200 слов), деловой тон. "
        "Не добавляй вымышленных достижений.\n\n"
        f"Профиль:\n{profile_text}\n\n"
        f"Вакансия:\n{vacancy_text}"
    )


def build_skill_gaps_prompt(profile_text: str, vacancy_text: str) -> str:
    return (
        "Сравни профиль кандидата и требования вакансии. "
        "Верни список недостающих навыков, приоритет (высокий/средний/низкий), "
        "и короткую рекомендацию как прокачать.\n\n"
        f"Профиль:\n{profile_text}\n\n"
        f"Вакансия:\n{vacancy_text}"
    )

