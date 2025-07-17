#models.py
from sqlalchemy import Column, Integer , String
from app.database.database import Base
from pydantic import BaseModel, EmailStr

class User(Base):
    __tablename__ = "users"
    id = Column(Integer  ,primary_key=True , index=True)
    email = Column(String , unique=True, index=True)
    password = Column(String) # hashed password
    name = Column(String)

# login model class
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# pydantic schema for user input
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str