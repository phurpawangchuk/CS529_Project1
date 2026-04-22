"""
quiz_assessment.py — Answer Grading Function Tool

Exposes a @function_tool that compares a user's answer against the stored
reference answer and returns a CORRECT/INCORRECT verdict with short feedback.

Pattern reference: 4_AgenticPatterns/tools/functionastool.ipynb (@function_tool)
"""

from agents import function_tool

from read_document import client, MODEL, QUESTIONS_PER_LESSON
from generate_questions import SESSION, get_lesson_session

# ---------------------------------------------------------------------------
# Prompt constants for the grader LLM call
# ---------------------------------------------------------------------------
ANSWER_GRADER_SYSTEM_PROMPT = (
    "You are a precise quiz grader. Compare the student's answer to the "
    "reference answer. Accept answers that convey the same meaning even if "
    "the wording differs.\n\n"
    "Reply in exactly this format:\n"
    "  VERDICT: CORRECT   (or VERDICT: INCORRECT)\n"
    "  FEEDBACK: One or two sentences explaining why."
)

ANSWER_GRADER_USER_TEMPLATE = (
    "Question: {question}\n\n"
    "Reference answer: {reference}\n\n"
    "Student's answer: {user_answer}"
)


# ---------------------------------------------------------------------------
# Function tool — grade a single answer
# ---------------------------------------------------------------------------
@function_tool
def assess_answer(lesson_number: int, question_number: int, user_answer: str) -> str:
    """
    Grade the user's answer for a specific lesson and question.

    Args:
        lesson_number:  Which lesson (1–5).
        question_number: Which question within the lesson (1–5).
        user_answer:     The student's answer text.

    Returns:
        A short verdict (CORRECT / INCORRECT) with one-line feedback.
    """
    try:
        lesson_data = get_lesson_session(int(lesson_number))
    except ValueError:
        return (
            f"Error: Questions for Lesson {lesson_number} have not been generated yet. "
            "Please generate them first."
        )

    idx = int(question_number) - 1
    if idx < 0 or idx >= QUESTIONS_PER_LESSON:
        return f"Error: question_number must be between 1 and {QUESTIONS_PER_LESSON}."

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
                    user_answer=user_answer,
                ),
            },
        ],
    )
    return response.choices[0].message.content or ""
