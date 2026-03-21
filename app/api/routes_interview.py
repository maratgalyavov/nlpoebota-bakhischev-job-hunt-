from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import container
from app.api.schemas import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewStartRequest,
    InterviewStartResponse,
)
from app.domain.models import INTERVIEW_QUESTIONS_RU, InterviewState

router = APIRouter(prefix="/v1/interview", tags=["interview"])


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(payload: InterviewStartRequest) -> InterviewStartResponse:
    container.user_repo.upsert_user(payload.user_id, payload.telegram_username)
    transition = container.fsm.start()
    state = container.session_repo.create_session(
        user_id=payload.user_id,
        stage=transition.next_stage,
        question_index=transition.next_question_index,
    )
    return InterviewStartResponse(
        session_id=state.session_id,
        stage=state.stage,
        question_index=state.question_index,
        question_text=transition.ask_question or INTERVIEW_QUESTIONS_RU[0],
    )


@router.post("/answer", response_model=InterviewAnswerResponse)
def answer_interview(payload: InterviewAnswerRequest) -> InterviewAnswerResponse:
    state = container.session_repo.get_last_session(payload.user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.completed:
        return InterviewAnswerResponse(
            session_id=state.session_id,
            stage=state.stage,
            question_index=state.question_index,
            completed=True,
            next_question=None,
        )

    q_idx = state.question_index
    container.answer_repo.add_answer(
        session_id=state.session_id,
        question_index=q_idx,
        question_text=INTERVIEW_QUESTIONS_RU[q_idx],
        answer_text=payload.answer_text,
    )
    transition = container.fsm.answer(q_idx)
    next_state = InterviewState(
        user_id=state.user_id,
        session_id=state.session_id,
        stage=transition.next_stage,
        question_index=transition.next_question_index,
        completed=transition.completed,
    )
    container.session_repo.update_session(next_state)
    return InterviewAnswerResponse(
        session_id=next_state.session_id,
        stage=next_state.stage,
        question_index=next_state.question_index,
        completed=next_state.completed,
        next_question=transition.ask_question,
    )


@router.get("/state/{user_id}", response_model=InterviewAnswerResponse)
def get_interview_state(user_id: int) -> InterviewAnswerResponse:
    state = container.session_repo.get_last_session(user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    next_question = None
    if not state.completed and 0 <= state.question_index < len(INTERVIEW_QUESTIONS_RU):
        next_question = INTERVIEW_QUESTIONS_RU[state.question_index]
    return InterviewAnswerResponse(
        session_id=state.session_id,
        stage=state.stage,
        question_index=state.question_index,
        completed=state.completed,
        next_question=next_question,
    )

