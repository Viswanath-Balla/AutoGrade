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

import os
import google.generativeai as genai
from dotenv import load_dotenv
import fitz  # PyMuPDF
# import base64
# import mimetypes

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash-lite")


def get_mime_type(file_path: str) -> str:
    """Detect correct mime type from file extension."""
    ext = file_path.lower().split(".")[-1]
    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
    }
    return mime_map.get(ext, "image/png")


def extract_from_image_bytes(image_bytes: bytes, mime_type: str, context: str = "") -> str:
    """Send image bytes to Gemini and extract text."""
    prompt = (
        "You are an expert OCR assistant. Your task:\n"
        "1. Extract ALL handwritten and printed text from this image EXACTLY as written.\n"
        "2. Preserve question numbers, bullet points, and formatting.\n"
        "3. If text is unclear, make your best guess and mark it with [unclear].\n"
        "4. Do NOT summarize, skip, or paraphrase anything.\n"
        "5. Maintain the original structure and line breaks.\n"
        f"{context}"
    )

    response = model.generate_content(
        [
            prompt,
            {
                "mime_type": mime_type,
                "data": image_bytes
            }
        ]
    )
    return response.text.strip()


def extract_handwritten_text(file_path: str) -> str:
    """
    Extract handwritten/printed text from PDF or image using Gemini Vision.
    - PDFs: each page is converted to a high-res image, labeled with page number
    - Images: directly sent to Gemini with correct mime type
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    full_text = ""

    try:
        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            total_pages = len(doc)
            print(f"📄 Processing PDF with {total_pages} page(s)...")

            for page_num, page in enumerate(doc, start=1):
                print(f"  → Extracting page {page_num}/{total_pages}...")

                # High-res render (300 DPI for handwriting accuracy)
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")

                try:
                    page_text = extract_from_image_bytes(
                        image_bytes=img_bytes,
                        mime_type="image/png",
                        context=f"This is page {page_num} of {total_pages} of a scanned document."
                    )

                    # Label each page clearly
                    full_text += f"--- PAGE {page_num} ---\n{page_text}\n\n"

                except Exception as page_err:
                    full_text += f"--- PAGE {page_num} ---\n[ERROR extracting this page: {page_err}]\n\n"

            doc.close()

        else:
            # Single image file
            mime_type = get_mime_type(file_path)
            print(f"🖼️ Processing image ({mime_type})...")

            with open(file_path, "rb") as f:
                image_bytes = f.read()

            full_text = extract_from_image_bytes(
                image_bytes=image_bytes,
                mime_type=mime_type
            )

    except Exception as e:
        raise Exception(f"OCR Extraction Failed: {str(e)}")

    return full_text


# ---- Quick test ----
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr.py <path_to_file>")
    else:
        result = extract_handwritten_text(sys.argv[1])
        print("\n===== EXTRACTED TEXT =====\n")
        print(result)
