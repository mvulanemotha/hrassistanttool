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
    password = Column(String , nullable=False)  # hashed password
    name = Column(String , nullable=False)
    user = Column(String , nullable=False)
    country = Column(String , nullable=False)
    created_at = Column(DateTime , default=datetime.utcnow)
   
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

    # optional: relationship to match history
    match_history = relationship("MatchHistory", back_populates="user")
    uploaded_cvs = relationship("UserCVUpload", back_populates="user", cascade="all, delete-orphan")
    credits = relationship("Credits", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transactions" , back_populates="user")  

class Credits(Base):
    __tablename__ = "credits"

    id = Column(Integer , primary_key=True , index=True)
    user_id = Column(Integer , ForeignKey("users.id") , nullable=False)
    amount = Column(Float , nullable=False)
    created_at = Column(DateTime , default=datetime.utcnow)

    #relationship to user
    user = relationship("User" , back_populates="credits")

class Transactions(Base):
    __tablename__ = "transactions"

    id = Column(Integer , primary_key=True , index=True)
    user_id = Column(Integer,ForeignKey("users.id") , nullable=False)
    reference_id = Column(String , nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Integer, default=0 , nullable=False)
    created_at = Column(DateTime , default=datetime.utcnow ,nullable=False)

    #Relationshsip
    user = relationship("User" , back_populates="transactions")
    


class MatchHistory(Base):
    __tablename__ = "match_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_description = Column(Text, nullable=False)
    job_title = Column(String, nullable=False)  # ✅ Add this line

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

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

    created_at = Column(DateTime , default=datetime.utcnow)
    updated_at = Column(DateTime , default=datetime.utcnow)

    history = relationship("MatchHistory", back_populates="results")

class UserCVUpload(Base):
    __tablename__ = "user_cvs"

    id = Column(Integer , primary_key=True , index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete = "CASCADE"))
    file_name = Column(String, nullable=False)
    job_title = Column(String , nullable=False)

    created_at = Column(DateTime , default=datetime.utcnow)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    #optional: relationship to User
    user = relationship("User", back_populates="uploaded_cvs")

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
    user: str

# ------------------------------
# Match history/result schemas
# ------------------------------

class MatchResultSchema(BaseModel):
    file_name: str
    score: float
    matched_content: Optional[str] = None

    class Config:
        from_attributes = True

class MatchHistorySchema(BaseModel):
    id: int
    user_id: int
    job_description: str
    job_title: str  # ✅ Add this line
    created_at: datetime
    results: List[MatchResultSchema] = []

    class Config:
        from_attributes = True


class SaveMatchesRequest(BaseModel):
    user_id: int
    jobDescription: str # match frontend key
    job_title: str  # ✅ Add this line
    matchedCandidates: List[MatchResultSchema]

class UserCVSchema(BaseModel):

    id : int
    user_id : int
    job_title : str
    file_name : str
    created_at : datetime

    model_config = {
        "from_attributes": True
    }


class CreditSchema(BaseModel):
    id:int
    user_id:int
    amount: float
    created_at: datetime

    class Config:
        form_attributes = True


class AddCreditRequest(BaseModel):
    user_id:int
    amount: int


class RequestToPay(BaseModel):
    amount: float
    msisdn: str
    user_id: int