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




import os
import json
import mimetypes
import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON from Gemini response."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def _save_temp_json(file_path: str, data: dict) -> str:
    """Save extracted data as a temp JSON file next to the original file."""
    json_path = os.path.splitext(file_path)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved temp JSON: {json_path}")
    return json_path


def delete_temp_json(file_path: str):
    """Delete the temp JSON file after scoring is done."""
    json_path = os.path.splitext(file_path)[0] + ".json"
    if os.path.exists(json_path):
        os.remove(json_path)
        print(f"Deleted temp JSON: {json_path}")


def _upload_file(file_path: str):
    """Upload a file to Gemini Files API and return the file object."""
    print(f"Uploading {file_path} to Gemini...")
    mime_type, _ = mimetypes.guess_type(file_path)
    uploaded = genai.upload_file(
        path=file_path,
        mime_type=mime_type or "application/octet-stream"
    )
    print(f"Uploaded: {uploaded.name}")
    return uploaded


def _send_image_inline(file_path: str):
    """For image files, send inline instead of uploading."""
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, "rb") as f:
        image_bytes = f.read()
    return {"mime_type": mime_type or "image/png", "data": image_bytes}


def extract_questions_from_qp(file_path: str) -> dict:
    """
    Extracts all questions from a question paper in a single API call.
    Supports PDF and images. Uses cache if JSON already exists.
    """
    # ── Cache check ────────────────────────────────────────────────────
    json_path = os.path.splitext(file_path)[0] + ".json"
    if os.path.exists(json_path):
        print(f"Loading cached questions from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    prompt = """
    You are an expert OCR engine and exam question paper parser.
    Extract ALL questions from this question paper in a single pass.

    Rules:
    - Identify every question number (e.g., Q1, 1., 2a, 2(b), etc.)
    - Extract full question text exactly as written — do NOT paraphrase
    - Extract marks if mentioned (e.g., [5 marks], (10)) — set null if not found
    - Treat each sub-part (2a, 2b) as a separate entry
    - Process ALL pages before responding

    Return ONLY valid JSON, no explanation outside it:
    {
        "questions": [
            {
                "question_number": "1",
                "question_text": "full question text exactly as written",
                "marks": 5
            },
            {
                "question_number": "2a",
                "question_text": "...",
                "marks": null
            }
        ]
    }
    """

    try:
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type == "application/pdf":
            uploaded_file = _upload_file(file_path)
            contents = [prompt, uploaded_file]
        else:
            contents = [prompt, _send_image_inline(file_path)]

        response = model.generate_content(
            contents=contents,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                max_output_tokens=8192
            )
        )

        parsed = _parse_json_response(response.text)
        _save_temp_json(file_path, parsed)

        print("\n===== EXTRACTED QUESTIONS =====")
        print(json.dumps(parsed, indent=2))
        print("================================\n")

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Raw response:\n{response.text}")
        return {"error": "Failed to parse JSON", "raw": response.text}

    except Exception as e:
        print(f"Question extraction failed: {e}")
        return {"error": str(e)}


def extract_answers_from_pdf(file_path: str) -> dict:
    json_path = os.path.splitext(file_path)[0] + ".json"
    if os.path.exists(json_path):
        print(f"Loading cached answers from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    prompt = """
    You are an expert OCR engine and exam answer sheet parser.
    Extract ALL handwritten and printed text from this answer sheet in a single pass.

    CRITICAL RULES — MUST FOLLOW:
    - Process EVERY SINGLE PAGE before responding — do not stop early
    - For each question, include the COMPLETE answer text — never truncate or summarize
    - If an answer continues across multiple pages, merge all of it under the same question number
    - Preserve the student's exact wording — do NOT paraphrase or shorten anything
    - Identify question numbers written by the student (e.g., Q1, 1., 2a, 2(b), Q.1 etc.)
    - Treat sub-parts (2a, 2b) as separate entries
    - Group any unidentifiable text under "unknown"
    - Do NOT add ellipsis (...) or cut off any answer mid-sentence

    Return ONLY valid JSON, no explanation outside it:
    {
        "answers": [
            {
                "question_number": "1",
                "answer_text": "complete full answer text exactly as written, no truncation"
            },
            {
                "question_number": "2a",
                "answer_text": "complete full answer text exactly as written, no truncation"
            },
            {
                "question_number": "unknown",
                "answer_text": "any text that could not be mapped to a question number"
            }
        ]
    }
    """

    try:
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type == "application/pdf":
            uploaded_file = _upload_file(file_path)
            contents = [prompt, uploaded_file]
        else:
            contents = [prompt, _send_image_inline(file_path)]

        response = model.generate_content(
            contents=contents,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                max_output_tokens=8192  # increase output limit
            )
        )

        # Handle case where response was cut off mid-JSON
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        # Attempt to fix truncated JSON by closing it
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            print("JSON truncated, attempting repair...")
            # Close any open answer_text and array/object
            if not raw.endswith("}"):
                raw = raw.rstrip(",\n ")
                # Close the last answer_text if open
                if '"answer_text": "' in raw.split("}")[-1]:
                    raw += '"}'
                raw += "\n]}"
            try:
                parsed = json.loads(raw)
                print("JSON repaired successfully")
            except json.JSONDecodeError as e:
                print(f"JSON repair failed: {e}")
                return {"error": "Response was truncated and could not be repaired", "raw": response.text}

        _save_temp_json(file_path, parsed)

        print("\n===== EXTRACTED ANSWERS =====")
        print(json.dumps(parsed, indent=2))
        print("=============================\n")

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Raw response:\n{response.text}")
        return {"error": "Failed to parse JSON", "raw": response.text}

    except Exception as e:
        print(f"Answer extraction failed: {e}")
        return {"error": str(e)}


# ── Quick test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ocr.py <qp|ans> <path_to_file>")
    elif sys.argv[1] == "qp":
        print(extract_questions_from_qp(sys.argv[2]))
    elif sys.argv[1] == "ans":
        print(extract_answers_from_pdf(sys.argv[2]))