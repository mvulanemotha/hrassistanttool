from pydantic import BaseModel
from langchain_community.embeddings import HuggingFaceEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from fastapi.responses import JSONResponse
from fastapi import UploadFile , File , HTTPException
from docx import Document
from io import BytesIO
import fitz
from pathlib import Path
import tempfile
import subprocess
import os
import io
from dotenv import load_dotenv
from openai import OpenAI
from fastapi.concurrency import run_in_threadpool
import pytesseract
from PIL import Image


load_dotenv()

#EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL = "intfloat/e5-base-v2"

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".doc", ".jpg", ".jpeg", ".png"]


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env file")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


embedder = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device":"cpu"},
    encode_kwargs={"normalize_embeddings":True}
)


# ==== Request Schema ====
class CompareRequest(BaseModel):
    job_description: str
    cv_text:str


# --- Compare endpoint
def compare_texts(payload:CompareRequest):
    job_desc = payload.job_description
    cv_text = payload.cv_text

    # generate embeddings
    job_embed = embedder.embed_query(job_desc)
    cv_embed = embedder.embed_query(cv_text)

    # compute cosine similarity
    similarity = cosine_similarity(
        np.array(job_embed).reshape(1,-1),
        np.array(cv_embed).reshape(1,-1)
    )[0][0]

    return {
        "score" : round(float(similarity), 4),
        "interpretation" : "1.0 = perfect match, 0 = no match"
    }

# extract
def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from an image (PNG, JPG, etc) using Tesseract OCR
    """

    image  = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image)

    return text.strip()

# extract text
def extract_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")

def extract_docx(file_bytes: bytes) -> str:
    bio = BytesIO(file_bytes)
    doc = Document(bio)
    return "\n".join(para.text for para in doc.paragraphs)

def extract_doc(file_bytes: bytes) -> str:
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # Convert using LibreOffice CLI to .txt in same temp dir
    output_dir = tempfile.gettempdir()
    try:
        subprocess.run([
            "soffice",
            "--headless",
            "--convert-to", "txt:Text",
            "--outdir", output_dir,
            tmp_path
        ], check=True)

        txt_file = Path(output_dir) / (Path(tmp_path).stem + ".txt")
        with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Failed to convert .doc file")
    finally:
        os.remove(tmp_path)
        if txt_file.exists():
            os.remove(txt_file)

    return text

async def extract_uploaded_text(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

    file_bytes = await file.read()

    try:
        if ext == ".pdf":
            text = extract_pdf(file_bytes)
        elif ext == ".docx":
            text = extract_docx(file_bytes)
        elif ext == ".txt":
            text = extract_txt(file_bytes)
        elif ext == ".doc":
            text = extract_doc(file_bytes)
        elif ext in [".jpg" , ".jpeg" , ".png"]:
            text = extract_text_from_image(file_bytes)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return text

# compare text files
async def compare_documents(job_description_file:UploadFile, cv_file: UploadFile):
    try:
        # Extract text
        job_description_text = await extract_uploaded_text(job_description_file)
        cv_text = await extract_uploaded_text(cv_file)

        #Embed
        job_embed = embedder.embed_query(job_description_text)
        cv_embed = embedder.embed_query(cv_text)

        # compute similarity
        similarity = cosine_similarity(
            np.array(job_embed).reshape(1, -1),
            np.array(cv_embed).reshape(1 , -1) 
        )[0][0]

        return {
            "score" : round(float(similarity) , 4),
            "interpretation" : "1.0 = perfect match, 0 = no match"
        }

    except Exception as e:
        return JSONResponse(status_code=500 , content={"error" : str(e)})



#explain low cv score
async def explain_low_score(job_description_file: UploadFile = File(...),
                            cv_file: UploadFile = File(...)):
    try:
        # Extract text (async)
        job_text = await extract_uploaded_text(job_description_file)
        cv_text = await extract_uploaded_text(cv_file)

        # Compute embeddings & similarity (sync, quick enough)
        job_embed = embedder.embed_query(job_text)
        cv_embed = embedder.embed_query(cv_text)
        similarity = cosine_similarity(
            np.array(job_embed).reshape(1, -1),
            np.array(cv_embed).reshape(1, -1)
        )[0][0]

        # Compose prompt
        prompt = f"""
        The similarity score between the job description and CV is {similarity*100:.2f}%.
        A low score means the CV does not align well with the job description.

        === Job Description ===
        {job_text}

        === CV ===
        {cv_text}

        Your task:
        - Be precise and structured.
        - Do not use bold text, asterisks, or Markdown formatting in your response.
        - First explain briefly why the score is low (biggest mismatches).
        - Then list exactly which skills, experiences, or keywords are missing from the CV.
        - Finally, give actionable suggestions for improving the CV so it aligns with this job.

        Format your response exactly as:

        Explanation:
        - (1–3 short bullet points on why the CV scored low)

        Missing Skills/Keywords:
        - (bullet list, only the most important missing items)

        Suggestions for Improvement:
        - (bullet list of concrete edits or additions to the CV)

        Keep the answer concise, clear, and easy for the user to follow.
        """


        # Run synchronous client call in threadpool
        def sync_openai_call():
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=350,
                temperature=0.5,
            )

        response = await run_in_threadpool(sync_openai_call)
        explanation = response.choices[0].message.content.strip()

        return {
            "similarity_score": round(float(similarity), 4),
            "explanation": explanation
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


#explain low cv score
async def explain_low_score_in_text(job_text, cv_text):
    try:
        # Compute embeddings & similarity
        job_embed = embedder.embed_query(job_text)
        cv_embed = embedder.embed_query(cv_text)
        similarity = cosine_similarity(
            np.array(job_embed).reshape(1, -1),
            np.array(cv_embed).reshape(1, -1)
        )[0][0]

        # Refined prompt
        prompt = f"""
            The similarity score between the job description and CV is {similarity*100:.2f}%.
            A low score means the CV does not align well with the job description.

            === Job Description ===
            {job_text}

            === CV ===
            {cv_text}

            Your task:
            - Be precise and structured.
            - First explain briefly why the score is low (biggest mismatches).
            - Then list exactly which skills, experiences, or keywords are missing from the CV.
            - Finally, give actionable suggestions for improving the CV so it aligns with this job.

            Format your response as:

            Explanation:
            - (1–3 short bullet points on why the CV scored low)

            Missing Skills/Keywords:
            - (bullet list, only the most important missing items)

            Suggestions for Improvement:
            - (bullet list of concrete edits or additions to the CV)

            Keep the answer concise, clear, and easy for the user to follow.
            """


        # Run synchronous client call in threadpool
        def sync_openai_call():
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.5,
            )

        response = await run_in_threadpool(sync_openai_call)
        explanation = response.choices[0].message.content.strip()

        return {
            "similarity_score": round(float(similarity), 4),
            "explanation": explanation
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
