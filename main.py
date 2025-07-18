from fastapi import FastAPI , UploadFile, File , Query , Depends ,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List , Dict, Any
from fastapi.responses import JSONResponse
from pydantic import BaseModel , EmailStr
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from datetime import datetime

from app.embed_files import embed_folder , INPUT_FOLDER ,VECTOR_DB_PATH
from app.compare_cvs import compare_with_job_description # importing the function
from app.database.database import SessionLocal
from app.models.user_model import User , UserLogin , UserCreate , MatchHistory , MatchResult , MatchHistorySchema ,MatchResultSchema
from app.utils.auth import create_access_token


app = FastAPI(
    title="HR AI Assistant API",
    description="Upload CVs, embed them, and compare against job description",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # ✅ allow all origins
    allow_credentials=True,
    allow_methods=["*"],       # ✅ allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],       # ✅ allow all headers
) 

#password hashing
pwd_context = CryptContext(schemes=["bcrypt"] , deprecated="auto")

#Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()    


# create a login end point
@app.post("/hrassistantai/login" , status_code=200)
def login(user: UserLogin, db:Session = Depends(get_db)):   
    print("🚀 Login endpoint CALLED!", flush=True)
    db_user = db.query(User).filter(User.email == user.email).first()
    print(f"User Details: {db_user}", flush=True)
    if not db_user:
        #raise HTTPException(status_code=400 , detail="User not found")
        return { "status_code" : 400 , "message" : "User not found" }

    # verify password
    if not pwd_context.verify(user.password , db_user.password):
        #raise HTTPException(status_code=400 , detail="Invalid email or password")
        return { "status_code" : 400 , "message" : "User not found" }
  
    # create jwt token
    access_token = create_access_token(data={"sub": db_user.email})
    return { "access_token" : access_token , "status_code" : 200 , "user_id": db_user.id } 

# create a new user
@app.post("/hrassistantai/newuser")
def create_user(user:UserCreate , db:Session= Depends(get_db)):
    """ 
    create a new user
    """
    # check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        #raise HTTPException(status_code=400, detail="Email already registered")
        return { "status_code" : 400 , "message" : "Email already registered" }
    # Hash the password
    hashed_password = pwd_context.hash(user.password)

    #Create new user object
    db_user = User(email=user.email, password=hashed_password , name=user.name)

    # Add to DB and commit
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
 
    return { "id":db_user.id , "email": db_user.email , "name": db_user.name , "status_code" : 201 }


@app.post("/hrassistantai/upload_cv_embed")
#call function to upload files
async def upload_cv_embed(files: list[UploadFile] = File(...)):
    """
    Upload CV files and create a vector store for comparison.
    """
    # Create upload folder if it doesn't exist
    os.makedirs(INPUT_FOLDER, exist_ok=True)

    saved = []
    # Save uploaded files
    for file in files:
        path = os.path.join(INPUT_FOLDER, file.filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        saved.append(file.filename)

    #print the saved files
    print(f"Files saved: {', '.join(saved)}") 

    # Embed the folder and create vector store
    result = embed_folder(INPUT_FOLDER, VECTOR_DB_PATH)
    
    return {
        "message": "CVs processed successfully.",
        "summary": result,
        "saved_files": saved
    }

@app.get("/hrassistantai/compare_job_description")
#call function to compare job description with stored CVs
def compare_job_description_endpoint(job_description: str):
    """
    Compare a job description with stored CVs and return the best matches.
    Pass the job description as a query paramenter or request body.
    """
  
    # call your existsing logic to compare job description with stored CVs
    results = compare_with_job_description(job_description)

    #convert the results (Document object) into serializable data
    output = []
    for file_name , (doc ,score) in results.items():
        output.append({
            "file_name": file_name,
            "Score": float(score),
            "Matched_content" : doc.page_content[:500]
        })

    return JSONResponse(content={"matches" : output})


@app.post("/hrassistantai/save_matches")
def save_matches_history(user_id:int , job_description: str , matches: List , db: Session = Depends(get_db)):
    history = MatchHistory(user_id=user_id , job_description=job_description , created_at=datetime.utcnow())
    db.add(history)
    db.commit()
    db.refresh(history)

    for m in matches:
        result = MatchResult(
            history_id = history.id,
            file_name=m["file_name"],
            score=m["score"],
            matched_content=m.get("Matched_content","")
        )
        db.add(result)
    db.commit()

    return { "status": "ok", "history_id": history.id }
 

@app.get("/hrassistantai/match_history/{user_id}" , response_model=List[MatchHistorySchema])
def get_match_history(user_id:int , db:Session = Depends(get_db)):
    history_records = (
        db.query(MatchHistory).
        filter(MatchHistory.user_id == user_id)
        .all()
    )

    return history_records
