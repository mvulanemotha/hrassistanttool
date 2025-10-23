from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime ,Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.database.database import Base
from pydantic import BaseModel, EmailStr, constr, field_validator
from typing import List, Optional
from pgvector.sqlalchemy import Vector

# =============================
# ✅ SQLAlchemy MODELS
# =============================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)  # hashed password
    name = Column(String, nullable=False)
    user = Column(String, nullable=False)
    country = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    uploaded_cvs = relationship("UserCVUpload", back_populates="user", cascade="all, delete-orphan")
    credits = relationship("Credits", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transactions", back_populates="user")
    match_history = relationship("MatchHistory", back_populates="user")
    processed_cvs = relationship("CVProcessed", back_populates="user", cascade="all, delete-orphan")
    cvs_to_process = relationship("CVToProcess", back_populates="user", cascade="all, delete-orphan")
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    referrals = relationship("Referals", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

class Referals(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referral_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="referrals")
    referral_links = relationship("ReferralLink", back_populates="referral", cascade="all, delete-orphan")


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(Integer, ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False)
    referred_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    referral = relationship("Referals", back_populates="referral_links")
    referred_user = relationship("User")  # Optional: add back_populates if needed


class Credits(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credits")


class Transactions(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reference_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")


class MatchHistory(Base):
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_description = Column(Text, nullable=False)
    job_title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="match_history")
    results = relationship("MatchResult", back_populates="history", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("match_history.id", ondelete="CASCADE"))
    file_name = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    matched_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = relationship("MatchHistory", back_populates="results")


class UserCVUpload(Base):
    __tablename__ = "user_cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_title = Column(String, nullable=False)
    file_name = Column(String , nullable=False)
    cv_embeddings = Column(Vector(768))  # full CV-level embedding (optional)
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="uploaded_cvs")
    uploaded_chunks = relationship("UserCVChunk", back_populates="cv_upload", cascade="all, delete")
    
class UserCVChunk(Base):
    __tablename__ = "user_cv_chunks"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("user_cvs.id", ondelete="CASCADE"))
    chunk_text = Column(String, nullable=False)
    embedding = Column(Vector(768))  # 384-dimensional vector from the MiniLM model
    chunk_id = Column(String, nullable=False)  # unique ID for traceability
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    cv_upload = relationship("UserCVUpload", back_populates="uploaded_chunks")


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))

    user = relationship("User", back_populates="otps")


class CVToProcess(Base):
    __tablename__ = "cv_to_process"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_cv = Column(Integer, nullable=False)
    user_cv = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cvs_to_process")
    processed_cvs = relationship("CVProcessed", back_populates="cv_to_process", cascade="all, delete-orphan")


class CVProcessed(Base):
    __tablename__ = "cv_processed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_to_process_id = Column(Integer, ForeignKey("cv_to_process.id", ondelete="CASCADE"), nullable=False)
    processed_cv = Column(String, nullable=False)
    downloaded = Column(Boolean, default=False)
    #email_sent = Column(Boolean ,default=False)
   
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="processed_cvs")
    cv_to_process = relationship("CVToProcess", back_populates="processed_cvs")


# ------------------------------
# User-related Schemas
# ------------------------------

class UserInfoSchema(BaseModel):
    id: int
    email: EmailStr
    name: str
    user: str
    country: str
    contact: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    user: str
    country: str
    contact: str
    referral_code: str

    @field_validator('contact')
    def validate_contact(cls, v):
        import re
        pattern = r"^\+\d{1,4}\d{6,14}$"
        if not re.match(pattern, v):
            raise ValueError("Contact must be in the format: +<country code><number>")
        return v


# ------------------------------
# CV Processing Schemas
# ------------------------------

class CVProcessSchema(BaseModel):
    id: int
    user_id: int
    user_cv: str
    status: str
    template_cv: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    user: Optional[UserInfoSchema]  # Nested user schema

    class Config:
        from_attributes = True


# ------------------------------
# Match History / Result Schemas
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
    job_title: str
    created_at: datetime
    results: List[MatchResultSchema] = []

    class Config:
        from_attributes = True


class SaveMatchesRequest(BaseModel):
    user_id: int
    jobDescription: str  # match frontend key
    job_title: str
    matchedCandidates: List[MatchResultSchema]


class UserCVSchema(BaseModel):
    id: int
    user_id: int
    job_title: str
    file_name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# ------------------------------
# Credit / Payment Schemas
# ------------------------------

class CreditSchema(BaseModel):
    id: int
    user_id: int
    amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class AddCreditRequest(BaseModel):
    user_id: int
    amount: int


class RequestToPay(BaseModel):
    amount: float
    msisdn: str
    user_id: int


# ------------------------------
# Miscellaneous Requests
# ------------------------------

class LowScoreRequest(BaseModel):
    job_description: str
    cv_text: str
    required_units: int
    user_id: int


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    password: str


class ResetPasswordRequest(BaseModel):
    user_id: int
    otp: str
    password: str
