from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
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
    qp_name = Column(String, nullable=False)          # actual filename on disk
    qp_display_name = Column(String, nullable=True)   # user-chosen label shown in UI
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

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    result_id    = Column(Integer, primary_key=True, index=True)
    paper_id     = Column(Integer, ForeignKey("question_papers.qp_id"), nullable=False)
    sheet_id     = Column(Integer, ForeignKey("answer_sheets.sheet_id"), nullable=False)  # ← link to AnswerSheet
    total_score  = Column(Float, nullable=False)
    max_score    = Column(Float, nullable=False)
    breakdown    = Column(Text, nullable=False)   # JSON — {q_num: marks_awarded}
    feedback     = Column(Text, nullable=True)    # JSON — {q_num: feedback text}
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    
    question_paper = relationship("QuestionPaper", backref="results")
    answer_sheet   = relationship("AnswerSheet", backref="results")