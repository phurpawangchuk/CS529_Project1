"""
settings_router.py — API endpoints for application settings.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

import read_document

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    model: Optional[str] = Field(None, description="Model name to use")
    questions_per_lesson: Optional[int] = Field(None, ge=1, le=20, description="Number of questions per lesson")


@router.get("/")
def get_settings():
    """Return current application settings."""
    docs = read_document.get_all_lesson_documents()
    lessons = []
    for num, doc in docs.items():
        lessons.append({
            "lesson_number": num,
            "configured": True,
            "vector_store_id": doc["vector_store_id"],
            "filename": doc["filename"],
        })

    return {
        "model": read_document.MODEL,
        "questions_per_lesson": read_document.QUESTIONS_PER_LESSON,
        "total_lessons": read_document.TOTAL_LESSONS,
        "lessons": lessons,
    }


@router.put("/")
def update_settings(body: SettingsUpdate):
    """Update application settings."""
    if body.model is not None:
        read_document.MODEL = body.model

    if body.questions_per_lesson is not None:
        read_document.QUESTIONS_PER_LESSON = body.questions_per_lesson

    return get_settings()
