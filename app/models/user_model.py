from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base
from pydantic import BaseModel, EmailStr
from typing import List, Optional

# =============================
# ✅ SQLAlchemy MODELS
# =============================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # hashed password
    name = Column(String)
   
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

    # optional: relationship to match history
    match_history = relationship("MatchHistory", back_populates="user")


class MatchHistory(Base):
    __tablename__ = "match_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    user = relationship("User", back_populates="match_history")
    results = relationship("MatchResult", back_populates="history", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"
    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("match_history.id", ondelete="CASCADE"))
    file_name = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    matched_content = Column(Text)

    history = relationship("MatchHistory", back_populates="results")


# =============================
# ✅ Pydantic SCHEMAS
# =============================

# Login model class
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# User creation input
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

# ------------------------------
# Match history/result schemas
# ------------------------------

class MatchResultSchema(BaseModel):
    file_name: str
    score: float
    matched_content: Optional[str] = None

    class Config:
        orm_mode = True

class MatchHistorySchema(BaseModel):
    id: int
    job_description: str
    created_at: datetime
    results: List[MatchResultSchema] = []

    class Config:
        orm_mode = True
