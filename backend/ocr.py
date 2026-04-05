import os
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

    # Strip markdown fences if Gemini adds them
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

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

    prompt = """You are an expert OCR assistant analyzing a student's handwritten answer sheet.
This answer sheet may be from ANY subject — engineering, science, mathematics, arts, etc.

Your task:
1. Extract each answer written by the student.
2. Group answers by their question number (e.g., Q1, Q2, Q3).
3. If an answer spans multiple pages, combine it into ONE complete answer.
4. Preserve sub-parts (a, b, c) within each question.
5. Extract EXACT handwritten text — do NOT summarize or paraphrase.
6. If text is unclear, write [unclear].

IMPORTANT — Handle diagrams and tables inside the answer text:

TABLES (very important — read carefully):
- If the student has drawn a table (a grid with rows and columns) for ANY subject:
  - You MUST reproduce the ENTIRE table — every row, every column, every cell value.
  - Do NOT stop after the header row.
  - Do NOT skip rows or truncate the table.
  - Use markdown table format inline at the exact position the table appears.
  - Every row the student wrote must appear as a separate row in the markdown table.
  - This applies to ALL types of tables: comparison tables, truth tables, data tables,
    frequency tables, periodic tables, schedule tables, any kind of grid the student drew.
  - Example of a COMPLETE table (all rows must be included):
    | Feature    | Option A              | Option B              |
    |------------|-----------------------|-----------------------|
    | Row 1      | value                 | value                 |
    | Row 2      | value                 | value                 |
    | Row 3      | value                 | value                 |

DIAGRAMS:
- If the student has drawn ANY kind of diagram, figure, or visual for ANY subject:
  - Do NOT skip it.
  - Insert it inline at the exact position it appears in the answer.
  - Format: [DIAGRAM: <detailed description>]
  - The description MUST include:
    * Type of diagram — examples by subject:
        - CS/IT: flowchart, ER diagram, UML diagram, network topology, architecture diagram, state machine
        - Electronics/ECE: circuit diagram, logic gate diagram, waveform, block diagram
        - Mechanical: free body diagram, stress-strain graph, machine part sketch
        - Civil: structural diagram, load diagram, cross-section sketch
        - Physics: ray diagram, force diagram, wave diagram, experimental setup
        - Chemistry: molecular structure, reaction mechanism, apparatus diagram, graph
        - Maths: graph/plot, geometric figure, Venn diagram, number line
        - Biology: cell diagram, organ diagram, life cycle diagram, food chain
        - Any other subject: describe what you see accurately
    * ALL labels, values, units, and text written inside or near the diagram
    * ALL shapes used and what they represent
    * Direction of arrows, connections, or flow
    * Any equations, variables, or numbers written on or near the diagram
  - Be as detailed as possible so a grader can evaluate the diagram from your description alone.

Return ONLY a valid JSON object. No markdown, no code fences, no explanation.

Format — values must be plain strings (NOT nested objects):
{
  "Q1": "full answer text for Q1, with complete tables and [DIAGRAM: ...] inline",
  "Q2": "full answer text for Q2...",
  "Q3": "answer text...\n\n[DIAGRAM: detailed description of whatever diagram the student drew...]\n\nMore text if any."
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

    # Strip markdown fences if Gemini adds them
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)

        # Safety net: if Gemini still returns nested objects despite instructions,
        # flatten them into a plain string so the rest of your app is unaffected
        for qnum, content in parsed.items():
            if isinstance(content, dict):
                parts = []
                if content.get("text"):
                    parts.append(content["text"])
                for i, table in enumerate(content.get("tables", []), start=1):
                    parts.append(f"\n[TABLE {i}]\n{table}")
                for i, diagram in enumerate(content.get("diagrams", []), start=1):
                    parts.append(f"\n[DIAGRAM {i}: {diagram}]")
                parsed[qnum] = "\n".join(parts).strip()

        return parsed

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