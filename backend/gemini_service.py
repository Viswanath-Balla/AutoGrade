# gemini_service.py

import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FLASH = "gemini-2.5-flash-lite"
PRO   = "gemini-2.5-flash-lite"   # use flash for both, pro quota is restrictive


def _call(model: str, prompt: str, temperature: float = 0.2) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature)
    )
    return response.text.strip()


def clean_json(response_text: str) -> dict:
    text = response_text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def structure_answers(answer_text: str) -> dict:
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
    return clean_json(_call(FLASH, prompt))


def structure_questions(question_text: str) -> dict:
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
    return clean_json(_call(FLASH, prompt))


def evaluate_answers(question_json, answer_json) -> dict:
    prompt = f"""
You are an expert exam evaluator.

Questions:
{question_json}

Student Answers:
{answer_json}

Evaluate each answer based strictly on its corresponding question.
Give marks out of 10 and short feedback.

Return ONLY valid JSON:
{{
    "1": {{
        "marks": 8,
        "feedback": "Good explanation"
    }}
}}
"""
    return clean_json(_call(PRO, prompt))


def extract_marks(question_text: str) -> int:
    patterns = [
        r'\[(\d+)\s*marks?\]',
        r'\((\d+)\s*marks?\)',
        r'M\[(\d+)\]',
        r'(\d+)\s*M\b',
        r'\bM(\d+)\b',
        r'\[M(\d+)\]',
    ]
    for pattern in patterns:
        match = re.search(pattern, question_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 5


def generate_model_answers(questions: dict) -> dict:
    filtered = {
        k: v for k, v in questions.items()
        if k not in ("General Instructions", "raw")
        and v and len(v.strip()) > 5
    }
    if not filtered:
        return {}

    questions_text = "\n\n".join(
        f"{q_num}: {q_text}"
        for q_num, q_text in filtered.items()
    )

    prompt = f"""You are an expert academic answer generator.
For each question below, generate a complete and accurate model answer.
Cover all key points a student needs to score full marks.
Be thorough but concise.
TABLES: Use column-value format:
  column_name: val1, val2, val3.
DIAGRAMS: Describe as [DIAGRAM: detailed description].

Questions:
{questions_text}

Return ONLY a valid JSON object. No markdown. No code fences. No explanation.
Keys must exactly match the question numbers given above.
Values must be plain strings.
{{
  "Q1": "complete model answer...",
  "Q2": "complete model answer..."
}}
"""
    raw = _call(PRO, prompt, temperature=0.2)
    print("\n===== RAW MODEL ANSWERS FROM GEMINI =====\n", raw[:500], "...")

    try:
        return clean_json(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️ Model answer JSON parse failed: {e}")
        return {}