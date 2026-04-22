"""
upload_router.py — API endpoint to upload lesson documents to OpenAI vector stores.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

import read_document

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/")
async def upload_lesson_document(
    file: UploadFile = File(...),
    lesson_number: int = Form(...),
):
    """Upload a document for a lesson and create/update its OpenAI vector store."""
    if lesson_number < 1 or lesson_number > read_document.TOTAL_LESSONS:
        raise HTTPException(
            status_code=400,
            detail=f"Lesson number must be between 1 and {read_document.TOTAL_LESSONS}.",
        )

    allowed_types = [
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, TXT, DOCX.",
        )

    try:
        client = read_document.client

        # Upload file to OpenAI
        file_content = await file.read()
        uploaded_file = client.files.create(
            file=(file.filename, file_content),
            purpose="assistants",
        )

        # Create a new vector store for this lesson
        vector_store = client.vector_stores.create(
            name=f"Lesson {lesson_number} - {file.filename}",
        )

        # Add file to vector store
        client.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=uploaded_file.id,
        )

        # Persist to SQLite (survives server restarts)
        read_document.save_lesson_document(
            lesson_number, file.filename, vector_store.id, uploaded_file.id
        )

        return {
            "lesson_number": lesson_number,
            "filename": file.filename,
            "vector_store_id": vector_store.id,
            "file_id": uploaded_file.id,
            "status": "success",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/{lesson_number}")
def delete_lesson_document(lesson_number: int):
    """Delete a lesson document from SQLite and OpenAI storage."""
    doc = read_document.get_lesson_document(lesson_number)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"No document found for Lesson {lesson_number}.",
        )

    client = read_document.client

    # Delete vector store from OpenAI
    try:
        client.vector_stores.delete(doc["vector_store_id"])
    except Exception:
        pass  # Already deleted or not found on OpenAI

    # Delete file from OpenAI
    try:
        client.files.delete(doc["file_id"])
    except Exception:
        pass  # Already deleted or not found on OpenAI

    # Remove from SQLite
    read_document.delete_lesson_document(lesson_number)

    return {
        "lesson_number": lesson_number,
        "status": "deleted",
    }
