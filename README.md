# AutoGrade

Automates the tedious part of exam evaluation — reading handwritten and printed answer sheets, mapping them to the right question, and structuring everything for grading — so institutions can speed up paper evaluation at scale.

## Overview

AutoGrade is a FastAPI backend that ingests scanned question papers and student answer sheets (PDF or image), uses Google's Gemini Vision API to extract and structure their content into per-question JSON, and persists everything to a TiDB-backed relational schema behind JWT-authenticated user accounts.

## Features

- **JWT authentication** with Argon2 password hashing and httponly cookie-based sessions
- **Document extraction pipeline** — Gemini Vision parses handwritten and printed exam content, mapping text to question numbers in a single API call per document
- **Response caching** — extracted results are cached to disk so re-processing a document doesn't re-bill the API
- **Truncated-response repair** — automatically detects and repairs JSON output that gets cut off mid-response
- **TiDB-backed storage** via SQLAlchemy, with optional SSL connections
- **Server-rendered dashboard** (Jinja2) for uploading and managing question papers and answer sheets

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | FastAPI, Uvicorn |
| Database | TiDB (MySQL-compatible), SQLAlchemy ORM |
| Auth | JWT (python-jose), Argon2 (passlib) |
| AI / OCR | Google Gemini Vision API |
| Document handling | PyMuPDF, pypdf, Pillow |
| Templating | Jinja2 |

## Project Structure

    backend/
    ├── main.py           # FastAPI app, routes
    ├── models.py          # SQLAlchemy models (User, QuestionPaper, AnswerSheet)
    ├── schemas.py          # Pydantic request/response schemas
    ├── db.py              # Database engine and session setup
    ├── security.py         # Password hashing, JWT creation/verification
    ├── dependencies.py       # Auth dependency (get_current_user)
    ├── ocr.py             # Gemini-based extraction pipeline
    ├── gemini_service.py     # Scoring/evaluation logic
    └── templates/          # Jinja2 HTML templates

## Getting Started

### Prerequisites

- Python 3.10+
- A TiDB (or MySQL-compatible) database instance
- A Google Gemini API key

### Installation

    git clone https://github.com/Viswanath-Balla/AutoGrade.git
    cd AutoGrade
    pip install -r requirements.txt

### Environment Variables

Create a `.env` file in the project root:

    DB_HOST=your-tidb-host
    DB_PORT=4000
    DB_USER=your-db-user
    DB_PASSWORD=your-db-password
    DB_NAME=autograde
    DB_SSL_CA=path/to/ca-cert.pem   # optional

    GEMINI_API_KEY=your-gemini-api-key

    SECRET_KEY=your-jwt-secret
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60

### Running

    cd backend
    uvicorn main:app --reload

The app will be available at `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/register` | Register a new user |
| GET/POST | `/login` | Authenticate and receive a session cookie |
| GET | `/logout` | Clear the session |
| GET | `/dashboard` | User dashboard (auth required) |
| GET | `/evaluate` | View uploaded question papers |
| POST | `/upload-question-paper` | Upload a question paper (PDF/image) |
| POST | `/evaluate` | Upload an answer sheet and extract structured Q&A against a question paper |

## Roadmap

- [ ] Wire the scoring module (`gemini_service.evaluate_answers`) into the `/evaluate` endpoint to return per-question marks and feedback, not just extracted text
- [ ] Per-user file namespacing to avoid upload collisions
- [ ] Exportable grade reports
- [ ] Rate limiting on auth endpoints

## License

See [License](backend/License).
