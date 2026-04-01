import os
import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash-lite")

file_path = "backend/answer_sheets/MID_PAPER_1.pdf"

doc = fitz.open(file_path)
page = doc.load_page(1)  # load the SECOND page

pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # render at high resolution
img_bytes = pix.tobytes("png")

prompt = """
You are an expert Document Analyst. Please carefully examine the visual layout of this handwritten answer sheet and answer the following questions:

1. **Margins & Borders**: Are there lines drawn for margins (left, right, top, bottom)? Are there any borders around the page? 
2. **Question Numbering Placement**: Exactly where in the page structure are the question numbers written? (e.g., inside the left margin, centered, outside a specific border box?)
3. **Numbering Format**: How do the question numbers visually look? (Are they boxed, circled, underlined? Do they follow a specific format like "1(a)" or "Q1"?)
4. **General Text Layout**: Does the student start answers directly next to the question number, or on the next line? Are answers visually separated by lines or whitespace?

I need this information to write a highly precise regular expression and OCR extraction prompt. Please be extremely detailed and describe exactly what you visually see.
"""

response = model.generate_content([
    prompt, 
    {"mime_type": "image/png", "data": img_bytes}
])

with open("backend/analysis_result.txt", "w", encoding="utf-8") as f:
    f.write(response.text)
