# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoGrade is an AI-powered automated answer sheet evaluation system built for JNTU (Jawaharlal Nehru Technological University). Teachers upload question papers; the system uses Gemini to extract questions, generate model answers, and store embeddings in Pinecone. Students upload handwritten answer sheets; the system OCRs them, computes cosine similarity against model answers, and returns per-question marks.

## Running the Project

```bash
# Activate virtual environment (Windows)
myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (from the project root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Access at `http://localhost:8000`. No separate build step is needed — Jinja2 templates are served directly.

## Environment Configuration

A `.env` file is required with:
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_SSL_CA` — TiDB Cloud (MySQL-compatible)
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` — JWT auth
- `GEMINI_API_KEY` — Google Generative AI (Gemini 2.5 Flash Lite)
- `PINECONE_API_KEY`, `PINECONE_INDEX` — Pinecone vector DB

## Architecture

### Core Pipeline

**Question Paper Ingestion** (triggered on upload, runs as a FastAPI background task):
1. `ocr.py` — Gemini Vision extracts text from PDF/image into structured JSON `{Q1: text, Q2: text, ...}`
2. `gemini_service.py` — `structure_questions()` normalises Q&A, `extract_marks()` parses mark allocations via regex, `generate_model_answers()` produces comprehensive answers (temperature=0.2)
3. `vector_store.py` — Embeds model answers using `sentence-transformers/all-MiniLM-L6-v2` (384-dim) and upserts to Pinecone namespaced by `qp_id`

**Evaluation** (triggered on answer sheet upload):
1. `ocr.py` — Extracts student handwritten answers per question number
2. `vector_store.py` — Embeds student answer, fetches model answer embedding from Pinecone, computes cosine similarity
3. `awarded_marks = cosine_similarity × max_marks` per question; aggregated into total score

### Key Files

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app, all routes, background task orchestration |
| `backend/ocr.py` | Gemini Vision OCR — extracts text from question papers and answer sheets |
| `backend/gemini_service.py` | Structures questions, generates model answers via Gemini API |
| `backend/vector_store.py` | Pinecone upsert/query, cosine similarity scoring |
| `backend/models.py` | SQLAlchemy ORM: `User`, `QuestionPaper`, `AnswerSheet`, `EvaluationResult` |
| `backend/db.py` | TiDB Cloud connection via PyMySQL |
| `backend/security.py` | Argon2 password hashing, JWT creation/verification |
| `backend/dependencies.py` | FastAPI dependency for authenticated routes (reads JWT from cookie) |
| `backend/schemas.py` | Pydantic request/response models |
| `backend/templates/` | Jinja2 HTML templates (home, register, login, dashboard, evaluate) |

### Routes

- `GET /` — Home
- `POST /register`, `POST /login`, `GET /logout`
- `GET /dashboard` — Lists uploaded question papers
- `POST /upload-question-paper` — Saves file, creates DB record, triggers background processing
- `GET /progress/{filename}` — Poll processing status
- `GET /evaluate` — Question paper selection page
- `POST /evaluate` — Upload answer sheet, run evaluation, return JSON results

### Auth Flow

JWT tokens are stored in HTTP-only cookies. The `dependencies.py` `get_current_user` dependency is applied to all protected routes. Tokens expire after 120 minutes (configurable via env).

### File Storage

- `backend/question_papers/` — Uploaded question paper files
- `backend/answer_sheets/` — Uploaded answer sheet files  
- `backend/uploads/` — Temporary files during processing
