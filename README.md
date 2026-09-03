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
