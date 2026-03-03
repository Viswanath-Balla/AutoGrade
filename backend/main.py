import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi import UploadFile, File
from typing import List
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select
from db import engine, Base, get_db
from security import hash_password
from models import User, QuestionPaper, AnswerSheet
from schemas import UserCreate, UserLogin
from fastapi import HTTPException, Depends
from security import verify_password, create_access_token
from dependencies import get_current_user
from ocr import extract_handwritten_text 
from fastapi import Form, File, UploadFile, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import shutil
import os
from PIL import Image
# import pytesseract
import fitz  # PyMuPDF
from models import QuestionPaper
from db import get_db
app = FastAPI()

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

from fastapi import Response, status
from fastapi.responses import RedirectResponse

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
    ques_names = os.listdir(QUES_PATH)
    # print(ques_names)
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
    request: Request,
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

    return {"message": "Uploaded successfully"}

from fastapi import Form
from gemini_service import (
    structure_answers,
    structure_questions,
    evaluate_answers
)
from ocr import extract_handwritten_text
from pypdf import PdfReader

def extract_pdf_text(path: str):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# main.py

from ocr import extract_handwritten_text  # your ocr.py file from before

def extract_text(file_path):
    """
    Drop-in replacement for the old Tesseract extract_text().
    Now uses Gemini Vision for far better handwriting accuracy.
    """
    return extract_handwritten_text(file_path)

@app.post("/evaluate")
async def evaluate(
    paper_id: int = Form(...),
    answerSheet: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        print("Received paper_id:", paper_id)
        print("Uploaded file:", answerSheet.filename)

        question_paper = db.query(QuestionPaper).filter(
            QuestionPaper.qp_id == paper_id
        ).first()

        if not question_paper:
            return JSONResponse(
                status_code=404,
                content={"detail": "Question paper not found"}
            )

        print("Question paper path:", question_paper.qp_path)

        qp_text = extract_text(question_paper.qp_path)

        answer_path = os.path.join(UPLOAD_FOLDER, answerSheet.filename)

        with open(answer_path, "wb") as buffer:
            shutil.copyfileobj(answerSheet.file, buffer)

        ans_text = extract_text(answer_path)

        print("\n===== QUESTION PAPER TEXT =====\n", qp_text)
        print("\n===== ANSWER SHEET TEXT =====\n", ans_text)

        return {
            "question_paper_text": qp_text,
            "answer_sheet_text": ans_text
        }

    except Exception as e:
        print("ERROR:", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )