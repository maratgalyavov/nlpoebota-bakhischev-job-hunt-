from app.domain.interview_fsm import InterviewFSM
from app.domain.models import INTERVIEW_QUESTIONS_RU


def test_interview_fsm_start_and_complete() -> None:
    fsm = InterviewFSM()
    transition = fsm.start()
    assert transition.next_question_index == 0
    assert transition.ask_question == INTERVIEW_QUESTIONS_RU[0]

    for idx in range(len(INTERVIEW_QUESTIONS_RU) - 1):
        transition = fsm.answer(idx)
        assert transition.completed is False

    final = fsm.answer(len(INTERVIEW_QUESTIONS_RU) - 1)
    assert final.completed is True
    assert final.next_stage == InterviewFSM.REVIEW_STAGE

