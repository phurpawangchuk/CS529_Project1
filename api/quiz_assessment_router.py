"""
quiz_assessment_router.py — API endpoint to grade a student's answer.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from read_document import client, MODEL, QUESTIONS_PER_LESSON
from generate_questions import SESSION, get_lesson_session, save_assessment
from quiz_assessment import ANSWER_GRADER_SYSTEM_PROMPT, ANSWER_GRADER_USER_TEMPLATE

router = APIRouter(prefix="/lessons", tags=["Quiz Assessment"])


class AssessAnswerRequest(BaseModel):
    question_number: int = Field(..., ge=1, le=5, description="Question number (1–5)")
    user_answer: str = Field(..., min_length=1, description="The student's answer")


@router.post("/{lesson_number}/assess")
def assess_answer(lesson_number: int, body: AssessAnswerRequest):
    """Grade the student's answer against the stored reference answer."""
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

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ANSWER_GRADER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": ANSWER_GRADER_USER_TEMPLATE.format(
                    question=question,
                    reference=reference,
                    user_answer=body.user_answer,
                ),
            },
        ],
    )
    grading_result = response.choices[0].message.content or ""

    # Persist to SQLite
    save_assessment(lesson_number, body.question_number, question, body.user_answer, grading_result)

    return {
        "lesson_number": lesson_number,
        "question_number": body.question_number,
        "question": question,
        "user_answer": body.user_answer,
        "grading_result": grading_result,
    }
