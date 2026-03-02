import os
import google.generativeai as genai
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image
import io

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 🔥 Use PRO model for handwriting
model = genai.GenerativeModel("gemini-1.5-pro")


def extract_handwritten_text(file_path: str) -> str:
    """
    Extract handwritten text from PDF or image using Gemini Vision.
    Converts PDF pages to images before sending.
    """

    try:
        full_text = ""

        if file_path.lower().endswith(".pdf"):

            doc = fitz.open(file_path)

            for page in doc:
                pix = page.get_pixmap(dpi=300)  # high resolution
                img_bytes = pix.tobytes("png")

                response = model.generate_content(
                    [
                        "Extract all handwritten and printed text clearly from this image. "
                        "Preserve question numbers and formatting. "
                        "Do not summarize.",
                        {
                            "mime_type": "image/png",
                            "data": img_bytes
                        }
                    ]
                )

                full_text += response.text.strip() + "\n\n"

        else:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            response = model.generate_content(
                [
                    "Extract all handwritten and printed text clearly from this image. "
                    "Preserve question numbers and formatting. "
                    "Do not summarize.",
                    {
                        "mime_type": "image/png",
                        "data": image_bytes
                    }
                ]
            )

            full_text = response.text.strip()

        return full_text

    except Exception as e:
        raise Exception(f"OCR Extraction Failed: {str(e)}")