"""
read_document.py — Document & Vector Store Configuration for Lesson Quiz System

Manages the connection to OpenAI vector stores where lesson documents are uploaded.
Each lesson maps to its own vector store ID so questions are grounded
in that specific lesson's content.

Vector store IDs are stored in SQLite (lesson_documents table),
populated dynamically when documents are uploaded via the UI.
"""

import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# OpenAI client & model
# ---------------------------------------------------------------------------
client = OpenAI()
MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# SQLite database setup (shared across modules)
# ---------------------------------------------------------------------------
# On HF Spaces the app directory may be read-only; use /tmp for the DB.
if os.getenv("SPACE_ID"):
    DB_PATH = "/tmp/quiz_sessions.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_sessions.db")


def _get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate_db():
    """Add question column to assessments and feedback tables if missing."""
    conn = _get_connection()
    for table in ("assessments", "feedback"):
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "question" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN question TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()


def _init_db():
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lesson_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_number INTEGER NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            vector_store_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_number INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question TEXT NOT NULL,
            reference_answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(lesson_number, question_number)
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_number INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question TEXT NOT NULL DEFAULT '',
            user_answer TEXT NOT NULL,
            grading_result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_number INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question TEXT NOT NULL DEFAULT '',
            user_answer TEXT NOT NULL,
            tutor_feedback TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


_init_db()
_migrate_db()

# ---------------------------------------------------------------------------
# Lesson document helpers (SQLite persistence for uploads)
# ---------------------------------------------------------------------------
def save_lesson_document(lesson_number: int, filename: str, vector_store_id: str, file_id: str):
    """Persist lesson document metadata to SQLite."""
    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO lesson_documents (lesson_number, filename, vector_store_id, file_id) "
        "VALUES (?, ?, ?, ?)",
        (lesson_number, filename, vector_store_id, file_id),
    )
    conn.commit()
    conn.close()


def get_all_lesson_documents() -> dict[int, dict]:
    """Load all lesson document records from SQLite."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT lesson_number, filename, vector_store_id, file_id, uploaded_at "
        "FROM lesson_documents ORDER BY lesson_number"
    ).fetchall()
    conn.close()
    return {row["lesson_number"]: dict(row) for row in rows}


def get_lesson_document(lesson_number: int) -> dict | None:
    """Load a single lesson document record from SQLite."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT lesson_number, filename, vector_store_id, file_id, uploaded_at "
        "FROM lesson_documents WHERE lesson_number = ?",
        (lesson_number,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_lesson_document(lesson_number: int):
    """Delete a lesson document record from SQLite."""
    conn = _get_connection()
    conn.execute("DELETE FROM lesson_documents WHERE lesson_number = ?", (lesson_number,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTAL_LESSONS = 5
QUESTIONS_PER_LESSON = 5


def get_vector_store_id(lesson_number: int) -> str:
    """Return the vector store ID for a given lesson from SQLite."""
    doc = get_lesson_document(lesson_number)
    if doc:
        return doc["vector_store_id"]

    raise ValueError(
        f"Vector Store ID for Lesson {lesson_number} is not configured. "
        f"Please upload a document for Lesson {lesson_number} first."
    )


def list_configured_lessons() -> list[int]:
    """Return lesson numbers that have been uploaded (from SQLite)."""
    docs = get_all_lesson_documents()
    return sorted(docs.keys())
