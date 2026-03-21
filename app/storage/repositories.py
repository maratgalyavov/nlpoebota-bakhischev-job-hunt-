from __future__ import annotations

from typing import Any, Optional

from app.domain.models import InterviewState
from app.storage.db import get_connection


class UserRepository:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def upsert_user(self, user_id: int, telegram_username: Optional[str] = None) -> None:
        with get_connection(self.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO users(user_id, telegram_username)
                VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET telegram_username=excluded.telegram_username
                """,
                (user_id, telegram_username),
            )
            connection.commit()


class SessionRepository:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def create_session(self, user_id: int, stage: str, question_index: int = 0) -> InterviewState:
        with get_connection(self.sqlite_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions(user_id, stage, question_index, completed)
                VALUES(?, ?, ?, 0)
                """,
                (user_id, stage, question_index),
            )
            session_id = cursor.lastrowid
            connection.commit()
        return InterviewState(
            user_id=user_id,
            session_id=int(session_id),
            stage=stage,
            question_index=question_index,
            completed=False,
        )

    def get_last_session(self, user_id: int) -> Optional[InterviewState]:
        with get_connection(self.sqlite_path) as connection:
            row = connection.execute(
                """
                SELECT session_id, user_id, stage, question_index, completed
                FROM sessions
                WHERE user_id = ?
                ORDER BY session_id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return InterviewState(
            user_id=int(row["user_id"]),
            session_id=int(row["session_id"]),
            stage=str(row["stage"]),
            question_index=int(row["question_index"]),
            completed=bool(row["completed"]),
        )

    def update_session(self, state: InterviewState) -> None:
        with get_connection(self.sqlite_path) as connection:
            connection.execute(
                """
                UPDATE sessions
                SET stage = ?, question_index = ?, completed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (state.stage, state.question_index, int(state.completed), state.session_id),
            )
            connection.commit()


class InterviewAnswerRepository:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def add_answer(
        self,
        session_id: int,
        question_index: int,
        question_text: str,
        answer_text: str,
    ) -> None:
        with get_connection(self.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO interview_answers(session_id, question_index, question_text, answer_text)
                VALUES(?, ?, ?, ?)
                """,
                (session_id, question_index, question_text, answer_text),
            )
            connection.commit()

    def list_answers(self, session_id: int) -> list[dict[str, Any]]:
        with get_connection(self.sqlite_path) as connection:
            rows = connection.execute(
                """
                SELECT question_index, question_text, answer_text
                FROM interview_answers
                WHERE session_id = ?
                ORDER BY question_index ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]


class ArtifactRepository:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def save_artifact(
        self,
        user_id: int,
        session_id: int,
        artifact_type: str,
        content: str,
        meta_json: Optional[str] = None,
    ) -> None:
        with get_connection(self.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO generated_artifacts(user_id, session_id, artifact_type, content, meta_json)
                VALUES(?, ?, ?, ?, ?)
                """,
                (user_id, session_id, artifact_type, content, meta_json),
            )
            connection.commit()


class FeedbackRepository:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def add_feedback(
        self,
        user_id: int,
        session_id: Optional[int],
        item_type: str,
        item_id: Optional[str],
        is_positive: bool,
        comment: Optional[str],
    ) -> None:
        with get_connection(self.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO feedback(user_id, session_id, item_type, item_id, is_positive, comment)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (user_id, session_id, item_type, item_id, int(is_positive), comment),
            )
            connection.commit()
