# gemini_service.py

import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_flash = genai.GenerativeModel("gemini-1.5-flash")
model_pro = genai.GenerativeModel("gemini-1.5-pro")


def clean_json(response_text: str):
    """
    Cleans Gemini response and converts to JSON safely.
    """
    cleaned = re.sub(r"```json|```", "", response_text).strip()
    return json.loads(cleaned)


def structure_answers(answer_text: str):
    prompt = f"""
    Extract answers from the following student answer sheet.

    Map strictly by question number.

    Return ONLY valid JSON like:

    {{
        "1": "answer text",
        "2": "answer text"
    }}

    Answer Sheet:
    {answer_text}
    """

    response = model_flash.generate_content(prompt)
    return clean_json(response.text)


def structure_questions(question_text: str):
    prompt = f"""
    Extract questions from the following question paper.

    Map strictly by question number.

    Return ONLY valid JSON like:

    {{
        "1": "question text",
        "2": "question text"
    }}

    Question Paper:
    {question_text}
    """

    response = model_flash.generate_content(prompt)
    return clean_json(response.text)


def evaluate_answers(question_json, answer_json):
    prompt = f"""
    You are an expert exam evaluator.

    Questions:
    {question_json}

    Student Answers:
    {answer_json}

    Evaluate each answer based strictly on its corresponding question.

    Give:
    - marks out of 10
    - short feedback

    Return ONLY valid JSON:

    {{
        "1": {{
            "marks": 8,
            "feedback": "Good explanation"
        }}
    }}
    """

    response = model_pro.generate_content(prompt)
    return clean_json(response.text)