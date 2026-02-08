import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi import UploadFile, File
from typing import List
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from security import hash_password
from models import User, QuestionPaper, AnswerSheet
from schemas import UserCreate, UserLogin
from fastapi import HTTPException, Depends
from security import verify_password, create_access_token
from dependencies import get_current_user

app = FastAPI()

templates = Jinja2Templates(directory="templates")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_path = os.path.join(BASE_DIR, "..", ".env")

load_dotenv(env_path)

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/register")
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):

    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create user
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "User registered successfully"
    }

@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

from fastapi import Response, status
from fastapi.responses import RedirectResponse

@app.post("/login")
async def login_user(
    response: Response,
    user: UserLogin,
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(User).where(User.email == user.email)
    )

    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": db_user.email,
        "username": db_user.username,
        "id": db_user.id
    }) 

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        # secure=True, # Uncomment for HTTPS
        samesite="lax"
    )

    return {
        "access_token": token, # Optional based on frontend needs, keeping for now
        "token_type": "bearer",
        "message": "Login successful"
    }

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
    db: AsyncSession = Depends(get_db)
):
    # Fetch question papers for the logged-in user
    result = await db.execute(
        select(QuestionPaper).where(QuestionPaper.user_id == user["id"])
    )
    question_papers = result.scalars().all()
    
    return templates.TemplateResponse(
        "evaluate.html",
        {"request": request, "question_papers": question_papers}
    )

@app.post("/upload-question-paper")
async def upload_question_paper(
    request: Request,
    questionPaper: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    message = "Question paper uploaded successfully"
    file_location = f"question_papers/{questionPaper.filename}"
    with open(file_location, "wb") as buffer:
        buffer.write(await questionPaper.read())
    
    #Handling duplicate sheets
    result = await db.execute(
        select(QuestionPaper).where(QuestionPaper.qp_name == questionPaper.filename)
    )
    existing_sheet = result.scalar_one_or_none()
    if existing_sheet:
        message=f"Question paper already exists"
    else:
        #upload qp path to db
        new_qp = QuestionPaper(
            qp_name=questionPaper.filename,
            qp_path=file_location,
            user_id=user["id"]
        )
        db.add(new_qp)
        await db.commit()
        await db.refresh(new_qp)

    return {"message": message}

@app.post("/evaluate")
async def evaluate(
    request: Request,
    answerSheet: List[UploadFile] = File(...),  # Change to List[UploadFile]
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    message = "Answer sheets uploaded successfully"

    for sheet in answerSheet:
        file_location = f"answer_sheets/{sheet.filename}"
        with open(file_location, "wb") as buffer:
            buffer.write(await sheet.read())

        #Handling duplicate sheets
        result = await db.execute(
            select(AnswerSheet).where(AnswerSheet.sheet_name == sheet.filename)
        )
        existing_sheet = result.scalar_one_or_none()
        if existing_sheet:
            message=f"Sheet {sheet.filename} already exists"
            break
        # Save each sheet to DB
        new_answer_sheet = AnswerSheet(
            sheet_name=sheet.filename,
            sheet_path=file_location,
            user_id=user["id"]
        )
        db.add(new_answer_sheet)
    
    await db.commit()
    return {"message": message}
