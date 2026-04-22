"""
quiz_chatbot.py — Interactive Lesson Quiz Chatbot (Orchestrator)

Main entry point that ties together all modules:
  - read_document.py    → document/vector store config
  - generate_questions.py → quiz generation agent (FileSearchTool)
  - quiz_assessment.py  → answer grading function tool (@function_tool)
  - assessment_result.py → tutor feedback agent (Agent.as_tool)

The chatbot walks the user through 5 lessons, each with 5 questions,
evaluates answers, and provides feedback interactively.

Usage:
    python quiz_chatbot.py
"""

import asyncio
import json

from agents import Agent, Runner, trace

from read_document import MODEL, TOTAL_LESSONS, QUESTIONS_PER_LESSON, list_configured_lessons
from generate_questions import generate_lesson_questions, get_lesson_session
from quiz_assessment import assess_answer
from assessment_result import tutor_feedback_tool

# ---------------------------------------------------------------------------
# Orchestrator agent — combines grading tool + tutor feedback tool
# ---------------------------------------------------------------------------
QUIZ_ORCHESTRATOR_INSTRUCTIONS = (
    "You are a friendly quiz chatbot that helps students test their understanding "
    "of lesson materials.\n\n"
    "Workflow:\n"
    "  1. Present questions one at a time from the current lesson.\n"
    "  2. After the student answers, use the assess_answer tool to grade it.\n"
    "     Pass: lesson_number, question_number, and the student's answer.\n"
    "  3. Share the verdict (CORRECT / INCORRECT) and short feedback.\n"
    "  4. If the student asks for more explanation, use the provide_detailed_feedback tool.\n"
    "  5. After all 5 questions, summarize the score (e.g., 3/5 correct).\n\n"
    "Be encouraging and concise. Guide the student through one question at a time."
)

quiz_orchestrator = Agent(
    name="lesson_quiz_orchestrator",
    instructions=QUIZ_ORCHESTRATOR_INSTRUCTIONS,
    model=MODEL,
    tools=[assess_answer, tutor_feedback_tool],
)


# ---------------------------------------------------------------------------
# Interactive chatbot loop
# ---------------------------------------------------------------------------
async def run_lesson_quiz(lesson_number: int) -> None:
    """Generate questions for a lesson and run an interactive Q&A loop."""
    print(f"\n{'='*60}")
    print(f"  Lesson {lesson_number} Quiz — Generating questions...")
    print(f"{'='*60}\n")

    quiz_data = await generate_lesson_questions(lesson_number)
    questions = quiz_data["questions"]

    # Display all questions up front
    print("Here are your 5 questions:\n")
    for i, q in enumerate(questions, 1):
        print(f"  Q{i}: {q}")
    print()

    # Interactive grading loop
    for i in range(1, QUESTIONS_PER_LESSON + 1):
        print(f"\n--- Question {i} ---")
        print(f"  {questions[i - 1]}")
        user_answer = input(f"\n  Your answer: ").strip()
        if not user_answer:
            print("  (Skipped)")
            continue

        prompt = (
            f"Lesson {lesson_number}, Question {i}. "
            f"The student's answer is: \"{user_answer}\". "
            f"Please grade it using the assess_answer tool."
        )

        with trace(f"lesson_{lesson_number}_q{i}_grading"):
            result = await Runner.run(quiz_orchestrator, prompt)
        print(f"\n  {result.final_output}")

        # Offer deeper feedback
        follow_up = input("\n  Want more explanation? (y/n): ").strip().lower()
        if follow_up == "y":
            session = get_lesson_session(lesson_number)
            detail_prompt = (
                f"The student wants a deeper explanation for Lesson {lesson_number}, "
                f"Question {i}.\n"
                f"Question: {session['questions'][i-1]}\n"
                f"Reference answer: {session['reference_answers'][i-1]}\n"
                f"Student's answer: {user_answer}\n"
                f"Please use the provide_detailed_feedback tool."
            )
            with trace(f"lesson_{lesson_number}_q{i}_feedback"):
                detail_result = await Runner.run(quiz_orchestrator, detail_prompt)
            print(f"\n  Tutor: {detail_result.final_output}")

    print(f"\n{'='*60}")
    print(f"  Lesson {lesson_number} Quiz Complete!")
    print(f"{'='*60}\n")


async def main():
    """Main entry point — run quizzes for all configured lessons."""
    configured = list_configured_lessons()

    if not configured:
        print("No lesson vector stores are configured yet.")
        print("Edit LESSON_VECTOR_STORES in read_document.py or set environment variables:")
        for i in range(1, TOTAL_LESSONS + 1):
            print(f"  LESSON_{i}_VECTOR_STORE_ID=vs_your_id_here")
        return

    print(f"\nConfigured lessons: {configured}")
    print(f"Each lesson has {QUESTIONS_PER_LESSON} questions.\n")

    for lesson_num in configured:
        run_quiz = input(f"Start Lesson {lesson_num} quiz? (y/n): ").strip().lower()
        if run_quiz == "y":
            await run_lesson_quiz(lesson_num)

    print("\nAll selected quizzes complete. Great job studying!")


if __name__ == "__main__":
    asyncio.run(main())
