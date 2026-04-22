"""
generate_questions.py — Quiz Question Generator Agent

Uses FileSearchTool against lesson-specific vector stores to generate
5 study questions (with reference answers) grounded in each lesson document.

Pattern reference: 4_AgenticPatterns/tools/hostedtools.ipynb (FileSearchTool)
"""

import json
import re

from agents import Agent, Runner, trace, FileSearchTool

from read_document import (
    MODEL,
    QUESTIONS_PER_LESSON,
    get_vector_store_id,
    _get_connection,
)

# ---------------------------------------------------------------------------
# In-memory session cache (backed by SQLite)
# ---------------------------------------------------------------------------
SESSION: dict[int, dict] = {}


def _load_session_from_db(lesson_number: int) -> dict | None:
    """Load questions for a lesson from SQLite into SESSION cache."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT question, reference_answer, question_number "
        "FROM questions WHERE lesson_number = ? ORDER BY question_number",
        (lesson_number,),
    ).fetchall()
    conn.close()
    if not rows:
        return None
    data = {
        "questions": [row["question"] for row in rows],
        "reference_answers": [row["reference_answer"] for row in rows],
    }
    SESSION[lesson_number] = data
    return data


def _save_questions_to_db(lesson_number: int, questions: list[str], reference_answers: list[str]):
    """Persist generated questions and reference answers to SQLite."""
    conn = _get_connection()
    conn.execute("DELETE FROM questions WHERE lesson_number = ?", (lesson_number,))
    for i, (q, a) in enumerate(zip(questions, reference_answers), start=1):
        conn.execute(
            "INSERT INTO questions (lesson_number, question_number, question, reference_answer) "
            "VALUES (?, ?, ?, ?)",
            (lesson_number, i, q, a),
        )
    conn.commit()
    conn.close()


def save_assessment(lesson_number: int, question_number: int, question: str, user_answer: str, grading_result: str):
    """Store a grading result in the database."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO assessments (lesson_number, question_number, question, user_answer, grading_result) "
        "VALUES (?, ?, ?, ?, ?)",
        (lesson_number, question_number, question, user_answer, grading_result),
    )
    conn.commit()
    conn.close()


def save_feedback(lesson_number: int, question_number: int, question: str, user_answer: str, tutor_feedback: str):
    """Store tutor feedback in the database."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO feedback (lesson_number, question_number, question, user_answer, tutor_feedback) "
        "VALUES (?, ?, ?, ?, ?)",
        (lesson_number, question_number, question, user_answer, tutor_feedback),
    )
    conn.commit()
    conn.close()


def get_assessment_history(lesson_number: int) -> list[dict]:
    """Retrieve all assessment records for a lesson, including the question text."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT a.question_number, "
        "  CASE WHEN a.question != '' THEN a.question ELSE COALESCE(q.question, '') END AS question, "
        "  a.user_answer, a.grading_result, a.created_at "
        "FROM assessments a "
        "LEFT JOIN questions q ON a.lesson_number = q.lesson_number AND a.question_number = q.question_number "
        "WHERE a.lesson_number = ? ORDER BY a.created_at",
        (lesson_number,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_feedback_history(lesson_number: int) -> list[dict]:
    """Retrieve all feedback records for a lesson."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT question_number, question, user_answer, tutor_feedback, created_at "
        "FROM feedback WHERE lesson_number = ? ORDER BY created_at",
        (lesson_number,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Prompt & instruction constants
# ---------------------------------------------------------------------------
QUESTION_GENERATOR_INSTRUCTIONS = (
    "You are an expert quiz creator. Your job is to generate study questions "
    "from the uploaded lesson materials using the file search tool. "
    "Rules:\n"
    "  - Only use facts found via the file search tool; never invent information.\n"
    "  - Cover different sections or key concepts from the lesson.\n"
    "  - Return a single JSON object with exactly two keys:\n"
    '      "questions"          — array of 5 question strings\n'
    '      "reference_answers"  — array of 5 concise ideal-answer strings\n'
    "  - Number questions implicitly by array index (1..5).\n"
    "  - Output raw JSON only — no markdown fences, no extra text."
)

QUESTION_TYPE_PROMPTS = {
    "short_qa": "Generate short answer questions that require brief written responses.",
    "mcq": (
        "Generate multiple-choice questions. Each question string must include the question "
        "followed by four options labeled A), B), C), D). "
        "The reference answer should be the correct option letter and its text."
    ),
    "fill_blank": (
        "Generate fill-in-the-blank questions. Each question should contain a blank "
        "indicated by '______' where the student must supply the missing word or phrase. "
        "The reference answer should be the correct word or phrase for the blank."
    ),
    "mixed": (
        "Generate a mix of question types: include some multiple-choice (with options A, B, C, D), "
        "some short answer questions, and some fill-in-the-blank questions (using '______' for blanks). "
        "Vary the types across the questions. "
        "For MCQ questions, the reference answer should be the correct option letter and text. "
        "For fill-in-the-blank, the reference answer should be the missing word or phrase."
    ),
}

GENERATE_QUIZ_PROMPT = (
    "Generate exactly {n} distinct questions that test understanding of this lesson. "
    "{question_type_instruction} "
    "Cover different sections or concepts when possible. "
    "Return only the JSON object as specified in your instructions."
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def extract_json_object(text: str) -> dict:
    """Extract the first JSON object from model output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in model output.")
    return json.loads(match.group(0))


# ---------------------------------------------------------------------------
# Build a quiz-generator agent for a specific lesson
# ---------------------------------------------------------------------------
def build_question_generator_agent(lesson_number: int) -> Agent:
    """Create a quiz generator agent wired to the lesson's vector store."""
    vector_store_id = get_vector_store_id(lesson_number)
    return Agent(
        name=f"lesson_{lesson_number}_question_generator",
        instructions=QUESTION_GENERATOR_INSTRUCTIONS,
        model=MODEL,
        tools=[
            FileSearchTool(vector_store_ids=[vector_store_id]),
        ],
    )


# ---------------------------------------------------------------------------
# Generate questions for a lesson
# ---------------------------------------------------------------------------
async def generate_lesson_questions(lesson_number: int, question_type: str = "short_qa") -> dict:
    """
    Generate 5 questions + reference answers for the given lesson.

    Returns dict with keys 'questions' and 'reference_answers'.
    Also stores the result in SESSION[lesson_number].
    """
    agent = build_question_generator_agent(lesson_number)
    type_instruction = QUESTION_TYPE_PROMPTS.get(question_type, QUESTION_TYPE_PROMPTS["short_qa"])
    prompt = GENERATE_QUIZ_PROMPT.format(n=QUESTIONS_PER_LESSON, question_type_instruction=type_instruction)

    with trace(f"lesson_{lesson_number}_quiz_generation"):
        result = await Runner.run(agent, prompt)

    data = extract_json_object(result.final_output)
    questions = data.get("questions", [])
    references = data.get("reference_answers", [])

    if len(questions) != QUESTIONS_PER_LESSON or len(references) != QUESTIONS_PER_LESSON:
        raise ValueError(
            f"Expected {QUESTIONS_PER_LESSON} questions and references; "
            f"got {len(questions)} / {len(references)}"
        )

    SESSION[lesson_number] = {
        "questions": questions,
        "reference_answers": references,
    }

    # Persist to SQLite
    _save_questions_to_db(lesson_number, questions, references)

    return data


def get_lesson_session(lesson_number: int) -> dict:
    """Retrieve stored questions/answers for a lesson. Checks cache then DB."""
    if lesson_number not in SESSION:
        # Try loading from SQLite
        data = _load_session_from_db(lesson_number)
        if data is None:
            raise ValueError(
                f"Questions for Lesson {lesson_number} have not been generated yet. "
                "Run generate_lesson_questions() first."
            )
    return SESSION[lesson_number]
