from fastapi import FastAPI , UploadFile, File , Query
import os
from typing import List , Dict, Any
from fastapi.responses import JSONResponse

from embed_files import embed_folder , INPUT_FOLDER ,VECTOR_DB_PATH
from compare_cvs import compare_with_job_description # importing the function

app = FastAPI(
    title="HR AI Assistant API",
    description="Upload CVs, embed them, and compare against job description",
    version="1.0.0"
)

@app.post("/upload_cv_embed")
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

@app.get("/compare_job_description")
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
 
