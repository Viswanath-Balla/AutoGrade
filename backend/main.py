import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from security import hash_password
from models import User
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

@app.post("/login")
async def login_user(
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
    "username": db_user.username
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/dashboard")
async def dashboard(
    request: Request,
    user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "username": user["username"]} 
    )