# test_pipeline.py

from gemini_service import structure_questions, generate_model_answers, extract_marks
from vector_store import upsert_model_answers, get_similarity

# ── Step 1: Paste a sample QP text here ───────────────────────────────
qp_text = """
1. Define photosynthesis and explain its stages. [5 marks]
2. What is the difference between mitosis and meiosis? [5 marks]
3. Explain Newton's second law of motion with an example. [5 marks]
"""

# ── Step 2: Extract questions ──────────────────────────────────────────
print("\n--- Extracting Questions ---")
questions = structure_questions(qp_text)
print(questions)

# ── Step 3: Build marks map ────────────────────────────────────────────
print("\n--- Extracting Marks ---")
marks_map = {
    q_num: extract_marks(q_text)
    for q_num, q_text in questions.items()
}
print(marks_map)

# ── Step 4: Generate model answers ────────────────────────────────────
print("\n--- Generating Model Answers ---")
model_answers = generate_model_answers(questions)
print(model_answers)

# ── Step 5: Store in Pinecone ──────────────────────────────────────────
print("\n--- Storing in Pinecone ---")
upsert_model_answers(
    qp_id=999,           # test QP ID
    model_answers=model_answers,
    questions=questions,
    marks_map=marks_map
)

# test_pipeline.py — replace the similarity test section

# ── Step 6: Test similarity with a student answer ──────────────────────
print("\n--- Testing Similarity ---")

# Use key from model_answers, not questions
test_question = list(model_answers.keys())[0]   # "Q1" not "1"
print(f"Testing with question key: {test_question}")

student_answer = "Photosynthesis is the process by which plants make food using sunlight."

result = get_similarity(
    qp_id=999,
    question_number=test_question,
    student_answer=student_answer
)
print(result)