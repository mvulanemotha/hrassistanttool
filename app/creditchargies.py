from fastapi import FastAPI ,  Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.user_model import Credits

CHARGES = {
    "compare_files": {
        "description": "Comparing your CV with a job advert.",
        "price": 2
    },
    "get_file_reasoning": {
        "description": "Provide reasoning and improvement tips.",
        "price": 3
    },
    "generate_cv": {
        "description": "CV generation.",
        "price": 70
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
        
        return False
        
    # subtracting the units in the database before processing
    credit_record.amount -= required_units
    db.commit()

    return True # condition passed
