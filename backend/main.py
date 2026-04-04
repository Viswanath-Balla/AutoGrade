import os
import traceback
import shutil
import time
from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import Response, status
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select
from db import engine, Base, get_db
from security import hash_password, verify_password, create_access_token
from models import User, QuestionPaper
from schemas import UserCreate, UserLogin
from dependencies import get_current_user
from ocr import extract_handwritten_text, extract_answers_by_question
from vector_store import upsert_model_answers, has_embeddings, get_similarity
from gemini_service import generate_model_answers, extract_marks, structure_questions
app = FastAPI()

progress_tracker = {}

@app.get("/progress/question-paper/{filename}")
def get_progress(filename: str):
    return progress_tracker.get(filename, {"status": "Not started", "progress": 0})

def process_question_paper_task(filename: str, file_path: str, qp_id: int):
    try:
        progress_tracker[filename] = {"status": "Extracting text from document...", "progress": 10}
        
        # 1. Extract text
        text = extract_handwritten_text(file_path)
        
        progress_tracker[filename] = {"status": "Structuring questions with Gemini...", "progress": 40}
        
        # 2. Structure questions
        questions = structure_questions(text)
        
        progress_tracker[filename] = {"status": "Generating model answers...", "progress": 70}
        
        # 3. Generate answers and extract marks
        model_answers = generate_model_answers(questions)
        marks_map = {q_num: extract_marks(q_text) for q_num, q_text in questions.items()}
        
        progress_tracker[filename] = {"status": "Saving embeddings to Vector DB...", "progress": 90}
        
        # 4. Upsert vectors
        upsert_model_answers(qp_id, model_answers, questions, marks_map)
        
        progress_tracker[filename] = {"status": "Completed successfully!", "progress": 100}
    except Exception as e:
        traceback.print_exc()
        progress_tracker[filename] = {"status": f"Error: {str(e)}", "progress": -1}

# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

templates = Jinja2Templates(directory="templates")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_path = os.path.join(BASE_DIR, "..", ".env")

load_dotenv(env_path)

QUES_PATH = "question_papers"
ANS_PATH = "answer_sheets"

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/register")
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    result = db.execute(
        select(User).where(User.email == user.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(
    response: Response,
    user: UserLogin,
    db: Session = Depends(get_db)
):

    result = db.execute(
        select(User).where(User.email == user.email)
    )

    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": db_user.email,
        "username": db_user.username,
        "id": db_user.id
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )

    return {"message": "Login successful"}

@app.get("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    # Redirect to login page
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/dashboard")
async def dashboard(
    request: Request,
    user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "username": user["username"]} 
    )

@app.get("/evaluate")
async def evaluate(
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch question papers for the logged-in user
    result = db.execute(
        select(QuestionPaper).where(QuestionPaper.user_id == user["id"])
    )
    question_papers = result.scalars().all()
    
    return templates.TemplateResponse(
        "evaluate.html",
        {"request": request, "question_papers": question_papers}
    )

@app.post("/upload-question-paper")
def upload_question_paper(
    background_tasks: BackgroundTasks,
    questionPaper: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    file_location = f"{QUES_PATH}/{questionPaper.filename}"
    with open(file_location, "wb") as buffer:
        buffer.write(questionPaper.file.read())

    result = db.execute(
        select(QuestionPaper).where(QuestionPaper.qp_name == questionPaper.filename)
    )
    existing_sheet = result.scalar_one_or_none()

    if existing_sheet:
        return {"message": "Question paper already exists"}

    new_qp = QuestionPaper(
        qp_name=questionPaper.filename,
        qp_path=file_location,
        user_id=user["id"]
    )

    db.add(new_qp)
    db.commit()
    db.refresh(new_qp)

    progress_tracker[questionPaper.filename] = {"status": "Starting processing...", "progress": 5}
    background_tasks.add_task(process_question_paper_task, questionPaper.filename, file_location, new_qp.qp_id)

    return {"message": "Upload started", "filename": questionPaper.filename}

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/evaluate")
async def evaluate(
    paper_id: int = Form(...),
    answerSheet: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        print("Received paper_id:", paper_id)
        print("Uploaded file:", answerSheet.filename)

        # --- Fetch question paper from DB ---
        question_paper = db.query(QuestionPaper).filter(
            QuestionPaper.qp_id == paper_id
        ).first()

        if not question_paper:
            return JSONResponse(
                status_code=404,
                content={"detail": "Question paper not found"}
            )

        # --- Check embeddings exist ---
        if not has_embeddings(paper_id):
            return JSONResponse(
                status_code=400,
                content={"detail": "Question paper has not been processed yet. Please wait for processing to complete before evaluating."}
            )

        # --- Save uploaded answer sheet ---
        # Give unique name to avoid filename collisions
        ext = os.path.splitext(answerSheet.filename)[1]
        unique_filename = f"ans_{paper_id}_{int(time.time())}{ext}"
        answer_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        with open(answer_path, "wb") as buffer:
            shutil.copyfileobj(answerSheet.file, buffer)

        print("Answer sheet saved to:", answer_path)

        # --- Extract answers grouped by question ---
        answers_by_question = extract_answers_by_question(answer_path)

        print("\n===== ANSWERS BY QUESTION =====\n", answers_by_question)

        # --- Evaluate each answer using Pinecone vector similarity ---
        results = []
        total_score = 0.0

        for question_number, student_answer in answers_by_question.items():
            if not student_answer or not isinstance(student_answer, str) or not student_answer.strip():
                print(f"⚠️  Skipping {question_number}: empty or null answer from OCR")
                results.append({
                    "question_number": question_number,
                    "student_answer": "",
                    "error": "No answer detected for this question",
                    "awarded_marks": 0
                })
                continue

            try:
                similarity_data = get_similarity(paper_id, question_number, student_answer)

                max_marks = similarity_data["max_marks"]
                cosine_sim = similarity_data["cosine_similarity"]
                awarded_marks = round(cosine_sim * max_marks, 2)
                total_score += awarded_marks

                results.append({
                    "question_number": question_number,
                    "question_text": similarity_data["question_text"],
                    "student_answer": student_answer,
                    "model_answer": similarity_data["model_answer"],
                    "cosine_similarity_pct": similarity_data["cosine_similarity_pct"],
                    "max_marks": max_marks,
                    "awarded_marks": awarded_marks
                })

            except Exception as e:
                print(f"⚠️  Skipping {question_number}: {e}")
                results.append({
                    "question_number": question_number,
                    "student_answer": student_answer,
                    "error": str(e),
                    "awarded_marks": 0
                })

        if total_score < 0:
            total_score = 0
        return {
            "total_score": round(total_score, 2),
            "results": results
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )



# /*
# 1. remove qp extraction from /evaluate
# 2. keep answer sheets exatraction from /evaluate.
# 3. convert the extracted answers into vector embeddings in /evaluate.
# 4. fetch vector embeddings for corresponding question paper from vector db.
# 5. compare extracted answers and fetched answers according to question number using cosine similarity and score each question.
# 6. at last display total score for all questions in same /evaluate route

# Doubts:
# 1. what does cosine similarity give as output.
# 2. Thresholds in scoring */