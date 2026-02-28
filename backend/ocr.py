import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image
import mimetypes

load_dotenv()

def extract_handwritten_text(file_path: str):
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise Exception("API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    prompt = """
    You are a strict OCR engine.
    Extract ALL handwritten and printed text exactly as shown.
    Do NOT summarize.
    Preserve formatting.
    If no text is found, return: NO TEXT FOUND.
    """
    
    mime_type, _ = mimetypes.guess_type(file_path)
    
    try:
        # ✅ PDF HANDLING
        if mime_type == "application/pdf":
            # Upload file instead of inline
            uploaded_file = client.files.upload(file=file_path)
            
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[prompt, uploaded_file],
                config=types.GenerateContentConfig(
                    temperature=0
                )
            )
        
        # ✅ IMAGE HANDLING
        else:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type or "image/png"
            )
            
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    temperature=0
                )
            )
        
        extracted_text = response.text
        print(f"--- Extracted Text from {file_path} ---")
        print(extracted_text)
        print("-------------------------------------------")
        return extracted_text
    
    except Exception as e:
        error_msg = f"OCR failed: {str(e)}"
        print(error_msg)
        return error_msg