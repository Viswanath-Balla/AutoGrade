from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from db import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuestionPaper(Base):
    __tablename__ = "question_papers"

    qp_id = Column(Integer, primary_key=True, index=True)
    qp_name = Column(String, nullable=False)
    qp_path = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class AnswerSheet(Base):
    __tablename__ = "answer_sheets"

    sheet_id = Column(Integer, primary_key=True, index=True)
    sheet_name = Column(String, nullable=False, unique=True)
    sheet_path = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)