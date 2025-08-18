from fastapi import FastAPI , UploadFile, File ,Depends ,HTTPException, Query , BackgroundTasks , Form
from fastapi.middleware.cors import CORSMiddleware
import os
import io
from typing import List , Dict, Any
from fastapi.responses import JSONResponse , StreamingResponse
from pydantic import  ValidationError , BaseModel
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from datetime import datetime

from app.embed_files import embed_folder , INPUT_FOLDER ,VECTOR_DB_PATH
from app.compare_advert_with_customer_cv import compare_texts,compare_documents, CompareRequest , explain_low_score , explain_low_score_in_text
from app.compare_cvs import compare_with_job_description # importing the function
from app.database.database import SessionLocal
from app.models.user_model import Transactions , LowScoreRequest , RequestToPay, User, Credits , UserCVUpload , AddCreditRequest ,UserCVSchema, CreditSchema , UserLogin , UserCreate , MatchHistory , MatchResult , UserCVUpload , MatchHistorySchema, SaveMatchesRequest
from app.cv_generator import *
from app.services.payment import create_payment_intent

from app.utils.auth import create_access_token
from collections import defaultdict
import zipfile
from io import BytesIO
from pathlib import Path
import base64
from app.momopayment import request_to_pay, generate_uuid , update_transactions_credits_periodically 
from app.creditchargies import CHARGES , check_user_units
import asyncio



CV_STORAGE_DIR = Path("cv_documents")

app = FastAPI(
    title="HR AI Assistant API",
    description="Upload CVs, embed them, and compare against job description",
    version="1.0.1"
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
    return { "access_token" : access_token , "status_code" : 200 , "user_id": db_user.id , "user": db_user.user , "name" : db_user.name , "email": db_user.email } 

# create a new user
@app.post("/hrassistantai/newuser")
def create_user(user:UserCreate , db:Session = Depends(get_db)):
    """ 
    create a new user
    """
    try:
        # check if user exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            #raise HTTPException(status_code=400, detail="Email already registered")
            return { "status_code" : 400 , "message" : "Email already registered" }
        # Hash the password
        hashed_password = pwd_context.hash(user.password)
        
        #Create new user object
        db_user = User(email=user.email, password=hashed_password , name=user.name , user=user.user , country=user.country , contact=user.contact )

        # Add to DB and commit
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        #assign credits to new user user
        initial_credits = Credits(
            user_id=db_user.id,
            amount=100,
            created_at=datetime.utcnow()
        )

        db.add(initial_credits)
        db.commit()
    
        return { "id":db_user.id , "email": db_user.email , "name": db_user.name , "status_code" : 201 , "user":db_user.user , "credits": initial_credits.amount }
    except ValidationError as e:
        # Handle Pydantic validation errors
        return {
            "status_code": 422,
            "message": "Validation error",
            "detail": e.errors()  # Provides specific validation error details
        }
    except Exception as e:
        # Handle other unexpected errors
        return {
            "status_code": 500,
            "message": "Internal server error",
            "detail": str(e)
        }

@app.post("/hrassistantai/upload_cv_embed")
#call function to upload files
async def upload_cv_embed(files: list[UploadFile] = File(...) , user_id:str = File(...) , job_title:str = File(...) , db: Session = Depends(get_db)):
    """
    Upload CV files and create a vector store for comparison.
    """
    print(files)

    # Create upload folder if it doesn't exist
    os.makedirs(INPUT_FOLDER, exist_ok=True)

    saved = []
    # Save uploaded files
    for file in files:
        path = os.path.join(INPUT_FOLDER, file.filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        saved.append(file.filename)

        cv_record = UserCVUpload(
            user_id = user_id,
            job_title = job_title,
            file_name = file.filename
        )
        db.add(cv_record)

    db.commit()

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
def compare_job_description_endpoint(job_description: str , allowed: bool = Depends(check_user_units)):
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


@app.post("/hrassistantai/save_matches" , response_model=MatchHistorySchema)
def save_matches_history(payload:SaveMatchesRequest, db: Session = Depends(get_db)):
    
    history = MatchHistory(user_id=payload.user_id , job_description=payload.jobDescription, job_title=payload.job_title, created_at=datetime.utcnow())
    db.add(history)
    db.commit()
    db.refresh(history)

    for m in payload.matchedCandidates:
        result = MatchResult(
            history_id=history.id,
            file_name=m.file_name,
            score=m.score,
            matched_content=m.matched_content or ""
        )
        db.add(result)
    db.commit()

    return history
 

@app.get("/hrassistantai/match_history")
def get_match_history(user_id:int , db:Session = Depends(get_db)):
    #return db.query(MatchHistory).all()
    history_records = (
        db.query(MatchHistory).
        filter(MatchHistory.user_id == user_id)
        .all()
    )

    #return history_records
    return [MatchHistorySchema.from_orm(history) for history in history_records] 


@app.get("/hrassistantai/user_cvs/")
def get_user_cvs(user_id:int ,db: Session = Depends(get_db)):
    user_cvs = db.query(UserCVUpload).filter(UserCVUpload.user_id == user_id).all()

    #group by job_title
    grouped: Dict[str , List[dict]] = defaultdict(list)

    for cv in user_cvs:
        cv_data = UserCVSchema.model_validate(cv).dict()
        cv_data["created_at"] = cv_data["created_at"].strftime("%Y-%m-%d %H:%M:%S") # Serialize datetime
        grouped[cv.job_title].append(cv_data)

    return JSONResponse(content=grouped)

#download matched documents
@app.get("/hrassistantai/download_matches")
def getMatched_cvs(match_id:int , db: Session = Depends(get_db)):
    #fetch match history and its results
    history = db.query(MatchHistory).filter(MatchHistory.id == match_id).first()

    if not history:
        return { "status_code": 400 , "message": "No job matches were found" }
    
    results = db.query(MatchResult).filter(MatchResult.history_id == match_id).all()
    
    if not results:
        return { "status_code": 400 , "message": "No matches were found" }

    # create ZIP stream
    zip_stream = BytesIO()
    with zipfile.ZipFile(zip_stream , mode="w" , compression=zipfile.ZIP_DEFLATED) as zipf:
        for result in results:
            file_path = CV_STORAGE_DIR / result.file_name
            if file_path.exists():
                # get original file extension
                ext = Path(result.file_name).suffix

                #build new name
                base_name = Path(result.file_name).stem # removes extension
                score_str = f"{result.score:.1f}".replace('.','.') # Optional: formart score
                new_file_name = f"{base_name}_score_{score_str}%{ext}"

                zipf.write(file_path, arcname=new_file_name)

    zip_stream.seek(0)


    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={"Content-Disposition" : f"attachment; filename=matches_{history.job_title.replace(' ', ' ')}.zip"}
    )

# compare text cv and job_description
@app.get("/hrassistantai/compare_text_cv_job_description")
def compare_cv_job_description_text(
    job_description: str = Query(...),
    cv_text: str = Query(...),
    user_id: int = Query(...),
    required_units: int = Query(...),
    allowed: bool = Depends(check_user_units)
):
    # You can still reuse your CompareRequest model internally if you want
    payload = CompareRequest(job_description=job_description, cv_text=cv_text)
    return compare_texts(payload)
    
# compare document cv and document advert
@app.post("/hrassistantai/compare_cv_advert_documents")
async def compare_advert_cv(job_description_file: UploadFile = File(...) , cv_file: UploadFile = File(...),
                            required_units: int = Form(...) , user_id : int = Form(...),
                            db: Session = Depends(get_db)
                             ):
    
    check_user_units(user_id,required_units , db)

    return await compare_documents(job_description_file , cv_file) 

#save user credits
@app.post("/hrassistantai/add_credits", response_model=CreditSchema)
def add_credit(data: AddCreditRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User Not Found")
    
    new_credit = Credits(
        user_id= data.user_id,
        amount= data.amount 
    )

    db.add(new_credit)
    db.commit()
    db.refresh(new_credit)


#get credits
@app.get("/hrassistantai/get_credits/{user_id}")
def get_user_credits(user_id:int ,db:Session = Depends(get_db)):
    return db.query(Credits).filter(Credits.user_id == user_id).order_by(Credits.created_at.desc()).all()


#create payment intent 
@app.get("/hrassistantai/create_payment_intent")
def create_intent(amount: float = Query(...,gt=0)):
    amount_in_cents = int(amount*100)
    return create_payment_intent(amount_in_cents)

# provide reasons low score api
@app.post("/hrassistantai/low_score_explanation")
async def generate_low_score_reason(job_description_file: UploadFile = File(...),  
                                    cv_file: UploadFile = File(...), 
                                    user_id: int = Form(...),
                                    required_units: int = Form(...),
                                    db: Session = Depends(get_db)):
    check_user_units(user_id,required_units,db)
    return await explain_low_score(job_description_file , cv_file)


#explain score not from file but from job descrption and cv text pasted
@app.post("/hrassistantai/explain_low_score_in_text")
async def low_score_reason(data: LowScoreRequest, db: Session = Depends(get_db) ):
    
    #Manually check units for this request
    check_user_units(
        user_id=data.user_id,
        required_units=data.required_units,
        db=db
    )
    return await explain_low_score_in_text(data.job_description , data.cv_text)


#request to pay
@app.post("/hrassistantai/request_to_pay")
def request_to_pay_to_add_credits(data: RequestToPay , db:Session = Depends(get_db)):

    uuid = generate_uuid()
    result = request_to_pay(data.amount , data.msisdn , uuid)
    
    #save transactions user_id
    transaction_data = Transactions(
        user_id = data.user_id,
        reference_id = uuid,
        amount = data.amount
    )

    db.add(transaction_data)
    db.commit()
    db.refresh(transaction_data)

    return result

#generate cv
@app.post("/hrassistantai/generate_cv")
async def generate_cv_with_llm_endpoint(
    user_cv: UploadFile = File(...),
    template_file: UploadFile = File(...),
    user_id: int = Form(...),
    required_units: int = Form(...),
    db: Session = Depends(get_db)
):
    

    # Read both files
    user_bytes = await user_cv.read()
    template_bytes = await template_file.read()

    if not user_bytes:
        raise HTTPException(400, "User CV file is empty")
    if not template_bytes:
        raise HTTPException(400, "Template CV file is empty")

    #check_user_units
    check_user_units(user_id , required_units , db)

    # Extract text
    user_text = extract_text_from_docx(user_bytes)
    template_text = extract_text_from_docx(template_bytes)

    if not user_text.strip():
        raise HTTPException(400, "User CV has no readable text")
    if not template_text.strip():
        raise HTTPException(400, "Template CV has no readable text")

    # Ask LLM to rewrite
    generated_text = generate_cv_with_llm(user_text, template_text)

    # Create DOCX from generated text
    generated_docx_bytes = create_docx_from_text(template_bytes, generated_text)

    # Create a PDF
    #generated_pdf_bytes = convert_docx_bytes_to_pdf_bytes(generated_docx_bytes)

    # Return files
    #return JSONResponse({
    #    "docx": base64.b64encode(generated_docx_bytes).decode()
    #    "pdf": base64.b64encode(generated_pdf_bytes).decode(),
    #})

      # Return files
    return JSONResponse({
        "docx": base64.b64encode(generated_docx_bytes).decode()
    })    

#get charge sheet
@app.get("/hrassistantai/chargies")
def get_chargies():
    return JSONResponse(content=CHARGES ,status_code=200)

#Runnning on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_transactions_credits_periodically())


class PassModel(BaseModel):
    password: str

# Update password
@app.put("/hrassistantai/changepass/{user_id}") 
def change_pass(user_id: int, password: PassModel , db:Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    try:
        if not user:
            raise HTTPException(status_code = 400 , detail="User not found")
        
        user.password = pwd_context.hash(password.password)

        db.commit()

        return JSONResponse(status_code=200 , content={ "message" : "Password changed succesfully"})

    except ValueError as e:
        raise HTTPException(status_code= 500, detail={str(e)}) 