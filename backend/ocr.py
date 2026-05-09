import os
import re
import time
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash-lite")


def upload_file_to_gemini(file_path: str) -> genai.types.File:
    """Upload a file to Gemini Files API and wait until it's ready."""
    print(f"Uploading file: {file_path}")

    mime_type = "application/pdf" if file_path.lower().endswith(".pdf") else _get_image_mime(file_path)

    uploaded = genai.upload_file(path=file_path, mime_type=mime_type)

    # Wait for file to be processed
    while uploaded.state.name == "PROCESSING":
        print("  ⏳ Waiting for file to be ready...")
        time.sleep(3)
        uploaded = genai.get_file(uploaded.name)

    if uploaded.state.name == "FAILED":
        raise Exception(f"File upload failed: {uploaded.name}")

    print(f"File ready: {uploaded.uri}")
    return uploaded


def _get_image_mime(file_path: str) -> str:
    ext = file_path.lower().rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "bmp": "image/bmp", "tiff": "image/tiff",
    }.get(ext, "image/png")


def extract_handwritten_text(file_path: str) -> dict:
    """
    Extract all text from a question paper PDF/image.
    Returns a dictionary mapping question numbers to their text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    uploaded = upload_file_to_gemini(file_path)

    prompt = """You are an expert OCR assistant.
This document may be a question paper from ANY subject — engineering, science, mathematics, arts, etc.

Your task:
1. Extract ALL questions from this document EXACTLY as written.
2. Group the text by question number (e.g., Q1, Q2, Q3).
3. Preserve sub-parts (a, b, c), marks allocation, and formatting.
4. Keep all printed AND handwritten text.
5. If text is unclear, write [unclear].
6. Do NOT summarize, skip, or paraphrase anything.

TABLES and DIAGRAMS:
- For any tables or grids, reproduce them fully in markdown table format.
- For any diagrams, figures, graphs, or illustrations, write [DIAGRAM: <description of what is shown>].

Return ONLY a valid JSON object. No markdown, no code fences, no explanation.

Format — values must be plain strings (NOT nested objects):
{
  "General Instructions": "Any instructions at the top...",
  "Q1": "full text for Q1...",
  "Q2": "full text for Q2..."
}
"""

    response = model.generate_content([prompt, uploaded])

    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    if not response.text:
        raise ValueError("Gemini returned an empty response for the question paper. It may have been blocked by safety filters.")
    raw = response.text.strip()
    print("\n===== RAW GEMINI RESPONSE (question paper) =====\n", raw)

    # Extract outermost {...} — handles markdown fences and any preamble
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print("JSON parse failed for question paper:", e)
        return {"raw": raw}


def extract_answers_by_question(file_path: str) -> dict:
    """
    Extract student answers grouped by question number.

    Returns the SAME shape as the original code:
        { "Q1": "plain string answer", "Q2": "plain string answer", ... }

    Diagrams are described inline as [DIAGRAM: ...] within the string.
    Tables are reproduced inline in markdown format within the string.
    This means your frontend and grader need NO changes at all.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    uploaded = upload_file_to_gemini(file_path)

    prompt = """You are an expert OCR assistant analyzing a JNTU student's handwritten answer booklet.

EXAM CONTEXT:
- This is a JNTU university exam. The question paper has 6 questions.
- The student is required to answer ANY 4 out of 6 questions.
- Each question is worth 5 marks. Maximum total = 20 marks.

════════════════════════════════════════
STEP 1 — COVER PAGE METADATA EXTRACTION
════════════════════════════════════════
The cover page has printed labels with handwritten values filled in by the student.
Extract each field exactly as described below. If a field is not visible or unreadable, use "".

H.T. No. (Hall Ticket Number):
- It is printed in a row of exactly 10 individual boxes. The student writes one character per box.
- Characters can be digits (0-9) OR letters (A-Z).
- Example boxes might contain: 2 3 0 1 1 M 2 2 0 6  → extract as "23011M2206"
- IMPORTANT: join ALL 10 characters together with NO spaces whatsoever.
- Store as "roll_number".

NAME OF THE EXAMINATION:
- The full exam name written by the student (e.g., "B.Tech II Year II Semester").
- Store as "exam_name".

SUBJECT:
- The subject name including any code in brackets (e.g., "Data-Base Management Systems [DBMS]").
- Store as "subject".

BRANCH/SPECIALIZATION:
- Branch, specialization, year, and semester info (e.g., "CSE-SE [IDDMP] [2nd Year 2nd Semester]").
- Store as "class_name".

DATE OF EXAM:
- The date written by the student (e.g., "22/04/2026").
- Store as "date_of_exam".

════════════════════════════════════════
STEP 2 — ANSWER EXTRACTION
════════════════════════════════════════
CRITICAL — QUESTION NUMBER DETECTION:
Students write question numbers in many formats. You MUST recognize ALL of these as question numbers:
  "1."  "1)"  "Q1"  "Q.1"  "Q 1"  "Question 1"  "Ans 1"  "1"  "(1)"
Always output the key as "Q1", "Q2", "Q3", "Q4", "Q5", or "Q6" — nothing else.
════════════════════════════════════════════════════════════════════════════════
IMPORTANT NOTE: Be especially very very careful distinguishing handwritten '4' from '6' — they look similar.

RULES:
1. Only include questions where the student has actually written an answer. Valid question numbers are Q1 through Q6 only.
2. If an answer spans multiple pages, combine it into ONE complete string.
3. Preserve sub-parts (a, b, c) within each question's answer text.
4. Extract EXACT handwritten text — do NOT summarize or paraphrase.
5. If text is unclear, write [unclear].
6. Do NOT output a question key if no answer body is written under it (even if the number is visible).
7. Do NOT invent or guess question numbers — only output numbers you can clearly see written by the student.
8. Ignore any printed question paper text; extract ONLY the student's handwritten answers.
9. Scan the ENTIRE document from first page to last page and extract ALL question numbers the student has written — do not stop early or skip any question.

TABLES — reproduce EVERY table fully in markdown format (all rows, all columns, never truncate).

DIAGRAMS — insert inline: [DIAGRAM: <type, all labels, arrows, values, connections — enough detail for a grader to evaluate it without seeing the image>]

════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════
Return ONLY a valid JSON object. No markdown fences, no explanation, no preamble.
All values must be plain strings (never nested objects or arrays).
Keys for answers MUST be exactly "Q1", "Q2", "Q3", "Q4", "Q5", or "Q6".

{
  "roll_number": "23011M2206",
  "exam_name": "B.Tech II Year II Semester",
  "subject": "Data-Base Management Systems [DBMS]",
  "class_name": "CSE-SE [IDDMP] [2nd Year 2nd Semester]",
  "date_of_exam": "22/04/2026",
  "Q1": "full answer text...",
  "Q3": "full answer text...",
  "Q4": "full answer text...",
  "Q6": "full answer text..."
}
"""

    response = model.generate_content([prompt, uploaded])

    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    if not response.text:
        raise ValueError("Gemini returned an empty response for the answer sheet. It may have been blocked by safety filters.")
    raw = response.text.strip()
    print("\n===== RAW GEMINI RESPONSE (answer sheet) =====\n", raw)

    # Extract outermost {...} — handles markdown fences and any preamble
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    try:
        parsed = json.loads(raw)

        # Safety net: flatten any nested objects Gemini returns despite instructions
        for qnum, content in list(parsed.items()):
            if isinstance(content, dict):
                parts = []
                if content.get("text"):
                    parts.append(content["text"])
                for i, table in enumerate(content.get("tables", []), start=1):
                    parts.append(f"\n[TABLE {i}]\n{table}")
                for i, diagram in enumerate(content.get("diagrams", []), start=1):
                    parts.append(f"\n[DIAGRAM {i}: {diagram}]")
                parsed[qnum] = "\n".join(parts).strip()

        # Normalise question number keys to "Q1"…"Q6" regardless of how Gemini wrote them
        METADATA_KEYS = {"roll_number", "exam_name", "subject", "class_name", "date_of_exam", "raw"}
        normalised = {}
        for key, value in parsed.items():
            if key in METADATA_KEYS:
                normalised[key] = value
                continue
            # Match any format: "1", "1.", "Q1", "Q.1", "Q 1", "Question 1", "Ans 1", "(1)" etc.
            m = re.search(r'\b([1-6])\b', key)
            if m:
                normalised[f"Q{m.group(1)}"] = value
            else:
                normalised[key] = value  # keep unknown keys as-is

        return normalised

    except json.JSONDecodeError as e:
        print("JSON parse failed:", e)
        return {"raw": raw}


# ---- Quick test ----
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr.py <path_to_file>")
    else:
        result = extract_answers_by_question(sys.argv[1])
        print("\n===== EXTRACTED ANSWERS =====\n")
        for q, ans in result.items():
            print(f"\n--- {q} ---\n{ans}")
