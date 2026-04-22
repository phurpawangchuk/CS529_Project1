"""
main.py — FastAPI application for the Lesson Quiz Assessment System.

Mounts all routers and serves the API.

Usage:
    cd Project1
    uvicorn api.main:app --reload

Swagger docs: http://127.0.0.1:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.read_document_router import router as read_document_router
from api.generate_questions_router import router as generate_questions_router
from api.quiz_assessment_router import router as quiz_assessment_router
from api.assessment_result_router import router as assessment_result_router
from api.settings_router import router as settings_router
from api.upload_router import router as upload_router
from api.auth_otp_router import router as auth_otp_router
from api.send_email_router import router as send_email_router

app = FastAPI(
    title="Lesson Quiz Assessment API",
    description=(
        "REST API for the Lesson Quiz Assessment System. "
        "Generates quiz questions from lesson documents, grades student answers, "
        "and provides detailed tutor feedback. Supports 5 lessons with 5 questions each."
    ),
    version="1.0.0",
)

# CORS — allow localhost for dev; in production the frontend is served from the
# same origin so CORS is not needed, but we keep "http://localhost:3000" for local dev.
allowed_origins = ["http://localhost:3000"]
if os.getenv("SPACE_ID"):  # Running on Hugging Face Spaces
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(read_document_router)
app.include_router(generate_questions_router)
app.include_router(quiz_assessment_router)
app.include_router(assessment_result_router)
app.include_router(settings_router)
app.include_router(upload_router)
app.include_router(auth_otp_router)
app.include_router(send_email_router)


# --------------- Serve React static build (production) ---------------
STATIC_DIR = Path(__file__).resolve().parent.parent / "ui" / "build"

if STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount("/static", StaticFiles(directory=STATIC_DIR / "static"), name="static")

    @app.get("/", tags=["UI"])
    def serve_root():
        """Serve the React app."""
        return FileResponse(STATIC_DIR / "index.html")

    # NOTE: Do NOT add a catch-all /{path} route here — it would shadow
    # all API routes (/settings, /upload, etc.).  The React SPA only needs
    # "/" since it handles routing client-side via hash/state.
else:
    @app.get("/", tags=["Health"])
    def health_check():
        """API health check."""
        return {"status": "ok", "service": "Lesson Quiz Assessment API"}
