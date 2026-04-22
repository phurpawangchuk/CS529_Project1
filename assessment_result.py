"""
assessment_result.py — Tutor Feedback Agent (Agent-as-Tool)

Provides detailed, educational feedback after a quiz answer has been graded.
Exposed as a tool so the orchestrator can invoke it when the student wants
a deeper explanation, hint, or reinforcement.

Pattern reference: 4_AgenticPatterns/tools/agentsastools1.ipynb (Agent.as_tool)
"""

from agents import Agent

from read_document import MODEL

# ---------------------------------------------------------------------------
# Instruction for the tutor feedback agent
# ---------------------------------------------------------------------------
TUTOR_FEEDBACK_INSTRUCTIONS = (
    "You are a supportive and encouraging tutor. "
    "When given a quiz question, the reference answer, the student's answer, "
    "and the grader's verdict, you provide:\n"
    "  1. A clear explanation of the correct answer.\n"
    "  2. What the student got right (if anything).\n"
    "  3. Specific guidance on what to review or improve.\n"
    "Keep your response concise (3–5 sentences) and educational."
)

# ---------------------------------------------------------------------------
# Tutor agent
# ---------------------------------------------------------------------------
tutor_feedback_agent = Agent(
    name="tutor_feedback_agent",
    instructions=TUTOR_FEEDBACK_INSTRUCTIONS,
    model=MODEL,
)

# ---------------------------------------------------------------------------
# Expose as a tool for the orchestrator
# ---------------------------------------------------------------------------
tutor_feedback_tool = tutor_feedback_agent.as_tool(
    tool_name="provide_detailed_feedback",
    tool_description=(
        "Call this when the student requests a deeper explanation, hint, or "
        "study guidance after their quiz answer has been graded. "
        "Pass a single input string containing: the question, reference answer, "
        "student's answer, and the grader's verdict."
    ),
)
