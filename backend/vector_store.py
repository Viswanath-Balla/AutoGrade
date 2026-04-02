# vector_store.py

import os
import numpy as np
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ── MiniLM embedder — loaded once, cached for entire server session ────
embedder = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384
print("✅ MiniLM loaded")

# ── Pinecone client ────────────────────────────────────────────────────
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = os.getenv("PINECONE_INDEX", "autograde")
index = pc.Index(INDEX_NAME)
print("✅ Pinecone connected")


# ── Core utility ───────────────────────────────────────────────────────

def embed_text(text: str) -> list:
    """Convert text to 384-dim normalized embedding vector."""
    return embedder.encode(text, normalize_embeddings=True).tolist()


def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ── Write ──────────────────────────────────────────────────────────────

def upsert_model_answers(
    qp_id: int,
    model_answers: dict,
    questions: dict,
    marks_map: dict
):
    """
    Embed each model answer and store in Pinecone.

    Args:
        qp_id         : Question paper ID — used as namespace
        model_answers : { "Q1": "model answer text", ... }
        questions     : { "Q1": "question text", ... }
        marks_map     : { "Q1": 5, "Q2": 10, ... }
    """
    vectors = []

    for q_num, answer_text in model_answers.items():
        if not answer_text or not answer_text.strip():
            print(f"⚠️  Skipping {q_num} — empty model answer")
            continue

        embedding = embed_text(answer_text)

        vectors.append({
            "id": q_num,
            "values": embedding,
            "metadata": {
                "question_number": q_num,
                "model_answer": answer_text[:10000],
                "question_text": questions.get(q_num, "")[:500],
                "max_marks": marks_map.get(q_num, 5)
            }
        })

    if vectors:
        index.upsert(vectors=vectors, namespace=str(qp_id))
        print(f"✅ Upserted {len(vectors)} vectors for QP {qp_id}")
    else:
        print("⚠️  No vectors to upsert")


# ── Read ───────────────────────────────────────────────────────────────

def fetch_model_answers(qp_id: int, question_numbers: list) -> dict:
    """
    Fetch stored embeddings + metadata from Pinecone.

    Returns:
    {
        "Q1": {
            "embedding": [...],
            "model_answer": "...",
            "question_text": "...",
            "max_marks": 5
        },
        ...
    }
    """
    result = index.fetch(ids=question_numbers, namespace=str(qp_id))
    output = {}

    for q_num, vector_data in result.vectors.items():
        output[q_num] = {
            "embedding": vector_data.values,
            "model_answer": vector_data.metadata.get("model_answer", ""),
            "question_text": vector_data.metadata.get("question_text", ""),
            "max_marks": vector_data.metadata.get("max_marks", 5)
        }

    return output


def get_similarity(
    qp_id: int,
    question_number: str,
    student_answer: str
) -> dict:
    """
    Main function called during evaluation.
    Embeds student answer, fetches model answer from Pinecone,
    computes and returns cosine similarity + metadata.

    Returns:
    {
        "cosine_similarity": 0.87,
        "cosine_similarity_pct": 87.0,
        "model_answer": "...",
        "question_text": "...",
        "max_marks": 10
    }
    """
    # Fetch model answer from Pinecone
    fetched = fetch_model_answers(qp_id, [question_number])

    if question_number not in fetched:
        raise ValueError(
            f"No model answer found for '{question_number}' in QP {qp_id}. "
            f"Make sure the QP was uploaded and processed correctly."
        )

    model_data = fetched[question_number]

    # Embed student answer
    student_embedding = embed_text(student_answer)

    # Compute similarity
    similarity = cosine_similarity(student_embedding, model_data["embedding"])

    return {
        "cosine_similarity": similarity,
        "cosine_similarity_pct": round(similarity * 100, 2),
        "model_answer": model_data["model_answer"],
        "question_text": model_data["question_text"],
        "max_marks": model_data["max_marks"]
    }


# ── Delete ─────────────────────────────────────────────────────────────

def delete_qp_vectors(qp_id: int):
    """Delete all vectors for a question paper (called when QP is deleted)."""
    index.delete(delete_all=True, namespace=str(qp_id))
    print(f"🗑️  Deleted all vectors for QP {qp_id}")

# Checking if it has embeddings
def has_embeddings(qp_id: int) -> bool:
    """Returns True if vectors already exist in Pinecone for this QP."""
    stats = index.describe_index_stats()
    namespaces = stats.namespaces
    ns_key = str(qp_id)
    return ns_key in namespaces and namespaces[ns_key].vector_count > 0
