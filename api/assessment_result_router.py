"""
assessment_result_router.py — API endpoint for detailed tutor feedback.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents import Runner, trace

from generate_questions import SESSION, get_lesson_session, save_feedback
from assessment_result import tutor_feedback_agent

router = APIRouter(prefix="/lessons", tags=["Assessment Result"])


class FeedbackRequest(BaseModel):
    question_number: int = Field(..., ge=1, le=5, description="Question number (1–5)")
    user_answer: str = Field(..., min_length=1, description="The student's answer")
    grading_result: str = Field(..., min_length=1, description="The verdict from the grading step")


@router.post("/{lesson_number}/feedback")
async def get_detailed_feedback(lesson_number: int, body: FeedbackRequest):
    """Get detailed tutor feedback after an answer has been graded."""
    try:
        lesson_data = get_lesson_session(lesson_number)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Questions for Lesson {lesson_number} have not been generated yet. "
                   f"Call POST /lessons/{lesson_number}/generate first.",
        )

    idx = body.question_number - 1
    question = lesson_data["questions"][idx]
    reference = lesson_data["reference_answers"][idx]

    tutor_input = (
        f"Question: {question}\n"
        f"Reference answer: {reference}\n"
        f"Student's answer: {body.user_answer}\n"
        f"Grader verdict: {body.grading_result}"
    )

    with trace(f"lesson_{lesson_number}_q{body.question_number}_api_feedback"):
        result = await Runner.run(tutor_feedback_agent, tutor_input)

    tutor_feedback = result.final_output

    # Persist to SQLite
    save_feedback(lesson_number, body.question_number, question, body.user_answer, tutor_feedback)

    return {
        "lesson_number": lesson_number,
        "question_number": body.question_number,
        "question": question,
        "tutor_feedback": tutor_feedback,
    }
