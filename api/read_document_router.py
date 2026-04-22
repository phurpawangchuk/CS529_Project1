"""
read_document_router.py — API endpoints for lesson & vector store configuration.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException

from read_document import (
    TOTAL_LESSONS,
    QUESTIONS_PER_LESSON,
    get_vector_store_id,
    list_configured_lessons,
    get_all_lesson_documents,
)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/")
def get_all_lessons():
    """List all lessons and their configuration status."""
    docs = get_all_lesson_documents()
    lessons = []
    for num in range(1, TOTAL_LESSONS + 1):
        doc = docs.get(num)
        lessons.append({
            "lesson_number": num,
            "configured": doc is not None,
            "vector_store_id": doc["vector_store_id"] if doc else None,
            "filename": doc["filename"] if doc else None,
        })
    return {
        "total_lessons": TOTAL_LESSONS,
        "questions_per_lesson": QUESTIONS_PER_LESSON,
        "configured_lessons": list_configured_lessons(),
        "lessons": lessons,
    }


@router.get("/{lesson_number}")
def get_lesson(lesson_number: int):
    """Get configuration details for a specific lesson."""
    try:
        store_id = get_vector_store_id(lesson_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "lesson_number": lesson_number,
        "vector_store_id": store_id,
        "questions_per_lesson": QUESTIONS_PER_LESSON,
    }
