from fastapi import FastAPI ,  Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.user_model import Credits

CHARGES = {
    "compare_text": {
        "description": "Compare plain job description text with CV text",
        "price": 3
    },
    "compare_files": {
        "description": "Compare uploaded CV file(s) with job description file",
        "price": 5
    },
    "get_text_reasoning": {
        "description": "Explain score and provide improvement suggestions",
        "price": 5
    },
    "get_file_reasoning": {
        "description": "Provide reasoning and improvement tips from files",
        "price": 8
    },
    "generate_cv": {
        "description": "CV generation",
        "price": 30
    }
}

#Dependecy to get DB session
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

#Dependecy to check if user has enough units
def check_user_units(user_id: int , required_units: int = 1, db: Session = Depends(get_db)):

    credit_record = db.query(Credits).filter(Credits.user_id == user_id).first()

    if not credit_record or credit_record.amount < required_units:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Insufficient units to perform this action"
        )
    
    # subtracting the units in the database before processing
    credit_record.amount -= required_units
    db.commit()

    return True # condition passed
