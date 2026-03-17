# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import fitz  # PyMuPDF
# from PIL import Image
# import io

# load_dotenv()
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# # Use PRO model for handwriting
# model = genai.GenerativeModel("gemini-1.5-pro")


# def extract_handwritten_text(file_path: str) -> str:
#     """
#     Extract handwritten + printed text from image or PDF.
#     Labels PDF pages clearly.
#     """

#     try:
#         full_text = ""

#         prompt = """
#         This is an exam sheet containing handwritten and printed text.

#         Instructions:
#         - Extract ALL visible text.
#         - Preserve question numbers and formatting.
#         - Do NOT summarize.
#         - Do NOT correct grammar.
#         - If a word is unclear, write [unclear].
#         - Maintain line breaks.
#         """

#         # 🔥 Handle PDF
#         if file_path.lower().endswith(".pdf"):

#             doc = fitz.open(file_path)

#             for page_number, page in enumerate(doc, start=1):

#                 # High resolution improves handwriting detection
#                 pix = page.get_pixmap(dpi=300)

#                 img_bytes = pix.tobytes("png")

#                 response = model.generate_content(
#                     [
#                         prompt,
#                         {
#                             "mime_type": "image/png",
#                             "data": img_bytes
#                         }
#                     ]
#                 )

#                 page_text = response.text.strip()

#                 full_text += f"\n\n========== PAGE {page_number} ==========\n\n"
#                 full_text += page_text

#             doc.close()

#         # 🔥 Handle Image
#         else:
#             with open(file_path, "rb") as f:
#                 image_bytes = f.read()

#             response = model.generate_content(
#                 [
#                     prompt,
#                     {
#                         "mime_type": "image/png",
#                         "data": image_bytes
#                     }
#                 ]
#             )

#             full_text = response.text.strip()

#         return full_text

#     except Exception as e:
#         raise Exception(f"OCR Extraction Failed: {str(e)}")

# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import fitz  # PyMuPDF
# # import base64
# # import mimetypes

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# model = genai.GenerativeModel("gemini-2.5-flash-lite")


# def get_mime_type(file_path: str) -> str:
#     """Detect correct mime type from file extension."""
#     ext = file_path.lower().split(".")[-1]
#     mime_map = {
#         "jpg": "image/jpeg",
#         "jpeg": "image/jpeg",
#         "png": "image/png",
#         "webp": "image/webp",
#         "bmp": "image/bmp",
#         "tiff": "image/tiff",
#     }
#     return mime_map.get(ext, "image/png")


# def extract_from_image_bytes(image_bytes: bytes, mime_type: str, context: str = "") -> str:
#     """Send image bytes to Gemini and extract text."""
#     prompt = (
#         "You are an expert OCR assistant. Your task:\n"
#         "1. Extract ALL handwritten and printed text from this image EXACTLY as written.\n"
#         "2. Preserve question numbers, bullet points, and formatting.\n"
#         "3. If text is unclear, make your best guess and mark it with [unclear].\n"
#         "4. Do NOT summarize, skip, or paraphrase anything.\n"
#         "5. Maintain the original structure and line breaks.\n"
#         f"{context}"
#     )

#     response = model.generate_content(
#         [
#             prompt,
#             {
#                 "mime_type": mime_type,
#                 "data": image_bytes
#             }
#         ]
#     )
#     return response.text.strip()


# def extract_handwritten_text(file_path: str) -> str:
#     """
#     Extract handwritten/printed text from PDF or image using Gemini Vision.
#     - PDFs: each page is converted to a high-res image, labeled with page number
#     - Images: directly sent to Gemini with correct mime type
#     """

#     if not os.path.exists(file_path):
#         raise FileNotFoundError(f"File not found: {file_path}")

#     full_text = ""

#     try:
#         if file_path.lower().endswith(".pdf"):
#             doc = fitz.open(file_path)
#             total_pages = len(doc)
#             print(f"📄 Processing PDF with {total_pages} page(s)...")

#             for page_num, page in enumerate(doc, start=1):
#                 print(f"  → Extracting page {page_num}/{total_pages}...")

#                 # High-res render (300 DPI for handwriting accuracy)
#                 pix = page.get_pixmap(dpi=300)
#                 img_bytes = pix.tobytes("png")

#                 try:
#                     page_text = extract_from_image_bytes(
#                         image_bytes=img_bytes,
#                         mime_type="image/png",
#                         context=f"This is page {page_num} of {total_pages} of a scanned document."
#                     )

#                     # Label each page clearly
#                     full_text += f"--- PAGE {page_num} ---\n{page_text}\n\n"

#                 except Exception as page_err:
#                     full_text += f"--- PAGE {page_num} ---\n[ERROR extracting this page: {page_err}]\n\n"

#             doc.close()

#         else:
#             # Single image file
#             mime_type = get_mime_type(file_path)
#             print(f"🖼️ Processing image ({mime_type})...")

#             with open(file_path, "rb") as f:
#                 image_bytes = f.read()

#             full_text = extract_from_image_bytes(
#                 image_bytes=image_bytes,
#                 mime_type=mime_type
#             )

#     except Exception as e:
#         raise Exception(f"OCR Extraction Failed: {str(e)}")

#     return full_text


# # ---- Quick test ----
# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: python ocr.py <path_to_file>")
#     else:
#         result = extract_handwritten_text(sys.argv[1])
#         print("\n===== EXTRACTED TEXT =====\n")
#         print(result)


# new

# ocr.py

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
    print(f"⬆️ Uploading file: {file_path}")

    mime_type = "application/pdf" if file_path.lower().endswith(".pdf") else _get_image_mime(file_path)

    uploaded = genai.upload_file(path=file_path, mime_type=mime_type)

    # Wait for file to be processed
    while uploaded.state.name == "PROCESSING":
        print("  ⏳ Waiting for file to be ready...")
        time.sleep(3)
        uploaded = genai.get_file(uploaded.name)

    if uploaded.state.name == "FAILED":
        raise Exception(f"File upload failed: {uploaded.name}")

    print(f"  ✅ File ready: {uploaded.uri}")
    return uploaded


def _get_image_mime(file_path: str) -> str:
    ext = file_path.lower().rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "bmp": "image/bmp", "tiff": "image/tiff",
    }.get(ext, "image/png")


def extract_handwritten_text(file_path: str) -> str:
    """
    Upload entire PDF/image once to Gemini and extract all text.
    Returns raw extracted text (preserving structure).
    Used for QUESTION PAPERS.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    uploaded = upload_file_to_gemini(file_path)
    prompt = """You are an expert OCR assistant analyzing a student's handwritten answer sheet.

Extract each answer and group by question number. Follow these rules strictly:

━━━ TEXT ━━━
- Extract handwritten text EXACTLY as written — do NOT paraphrase or correct.
- Preserve sub-parts (a, b, c) within each question.
- If an answer spans multiple pages, combine into ONE complete answer.
- If text is unclear, write [unclear].

━━━ TABLES ━━━
- If a student has drawn or written a table, render it in Markdown format.
- Wrap each table like:
  [TABLE_START]
  | Col1 | Col2 |
  |------|------|
  | val  | val  |
  [TABLE_END]

━━━ DIAGRAMS ━━━
- If a student has drawn a diagram, describe it structurally inside:
  [DIAGRAM_START]
  Type: <Flowchart / Circuit / Block Diagram / Graph / Tree / Other>
  Components: <all labeled parts, nodes, symbols>
  Connections/Flow: <how they connect or relate>
  Labels: <all text labels or values in the diagram>
  Overall Meaning: <one-sentence summary of what it represents>
  [DIAGRAM_END]

━━━ OUTPUT FORMAT ━━━
Return ONLY a valid JSON object. Keys are question numbers (Q1, Q2, etc.).
Values are strings containing the full answer (text + embedded [TABLE_START]...[TABLE_END] and [DIAGRAM_START]...[DIAGRAM_END] blocks as needed).

Example:
{
  "Q1": "The process is as follows:\\n[DIAGRAM_START]\\nType: Flowchart\\nComponents: Start, Process A, Decision, End\\nConnections/Flow: Start -> Process A -> Decision -> End\\nLabels: Yes/No on decision\\nOverall Meaning: Represents a basic decision-making flow\\n[DIAGRAM_END]",
  "Q2": "The truth table is:\\n[TABLE_START]\\n| A | B | Output |\\n|---|---|--------|\\n| 0 | 0 | 0      |\\n[TABLE_END]",
  "Q3": "Newton's second law states force equals mass times acceleration."
}

- No markdown code fences, no extra explanation outside the JSON.
- Only raw JSON.
"""
    response = model.generate_content([prompt, uploaded])

    # Clean up uploaded file
    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    return response.text.strip()

def extract_answers_by_question(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    uploaded = upload_file_to_gemini(file_path)

    prompt = """You are an expert OCR assistant analyzing a student's handwritten answer sheet.

Your task:
1. Extract each answer written by the student.
2. Group answers by their question number (e.g., Q1, Q2, Q3).
3. If an answer spans multiple pages, combine it into ONE complete answer.
4. Preserve sub-parts (a, b, c) within each question.
5. Extract EXACT handwritten text — do NOT summarize or paraphrase.
6. If text is unclear, write [unclear].

Return ONLY a valid JSON object like:
{
  "Q1": "full answer for question 1...",
  "Q2": "full answer for question 2...",
  "Q3": "full answer for question 3..."
}

- No markdown, no code fences, no extra explanation.
- Only raw JSON.
"""

    response = model.generate_content([prompt, uploaded])

    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    # ✅ Print raw response for debugging
    raw = response.text.strip()
    print("\n===== RAW GEMINI RESPONSE (answer sheet) =====\n", raw)

    # Strip markdown fences if Gemini adds them
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print("⚠️ JSON parse failed:", e)
        return {"raw": raw}  # fallback: return as plain text