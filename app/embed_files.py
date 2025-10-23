import os
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from app.compare_advert_with_customer_cv import extract_uploaded_cv
from fastapi import UploadFile, File, Depends , HTTPException , Form
from app.models.user_model import UserCVUpload , UserCVChunk
from app.database.database import get_db
from sqlalchemy.orm import Session
import numpy as np
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

import hashlib

# Configurations
INPUT_FOLDER = "cv_documents" # folder containing your CVs
VECTOR_DB_PATH = "cv_vectorstore" # path to save the vector store
SUPPORTED_EXTENSIONS = ['.pdf' , '.docx', '.txt' , '.doc']

HR_CVS = "hr_users_cvs"

os.makedirs(VECTOR_DB_PATH, exist_ok=True)  # Ensure the output directory exists
os.makedirs(INPUT_FOLDER,exist_ok=True)  # Ensure the input directory exists
os.makedirs(HR_CVS,exist_ok=True)


#EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2" #HuggingFace model for embeddings
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def load_and_process_documents(folder_path):
    """ Load and process all documents in a folder. """
    documents = []
    failed_files = []

    #Iterate through all files in the folder
    for file_path in Path(folder_path).rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                print(f"Processing file: {file_path.name}")

                # Load based on file type
                if file_path.suffix.lower() == '.pdf':
                    loader = PyPDFLoader(str(file_path))
                elif file_path.suffix.lower() == '.docx':
                    loader = Docx2txtLoader(str(file_path))
                elif file_path.suffix.lower() == '.doc':
                    # Handle .doc files using unstructured
                    loader = UnstructuredFileLoader(str(file_path))
                else:  # .txt
                    loader = TextLoader(str(file_path))
                
                # Load the document and add/metadata
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    doc.metadata.update({
                        "source_file": str(file_path),
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                        "file_hash": hashlib.md5(file_path.read_bytes()).hexdigest(),
                    })
                documents.extend(loaded_docs)

            except Exception as e:
                print(f"Failed to load {file_path.name}: {e}")
                failed_files.append(file_path.name)
                continue

    print(f"\n Processed { len(documents)} documents from {len(list(Path(folder_path).rglob('*')))} files.")        
    print(f"Failed to load {len(failed_files)} files: {', '.join(failed_files)}")
    return documents , failed_files

#chunk the documents
def chunk_documents(documents):
    """ Split documents into smaller chunks. """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200 , length_function=len)
    chunks = text_splitter.split_documents(documents)
    print(f"Chunked into {len(chunks)} total chunks.")
    return chunks

# generate embeddings
def generate_embeddings(chunks):
    """ Generate embeddings for the document chunks. and vector store """
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # create unique IDS for each chunk
    for chunk in chunks:
        content = chunk.page_content,
        metadata = str(chunk.metadata)
        unique_id = hashlib.sha256(f"{content}{metadata}".encode()).hexdigest()[:16]
        chunk.metadata["chunk_id"] = unique_id

    #create vector store
    vector_store = FAISS.from_documents(chunks,embeddings)
    return vector_store

def embed_folder(folder_path , output_path):
    """ Main function to process the folder and create a vector store. """
    
    # Step 1 : Load and process documents
    raw_documents , failed = load_and_process_documents(folder_path)

    #Step 2 : Split documents into chunks
    chunks = chunk_documents(raw_documents)

    #Step 3 : Generate embeddings
    vector_store = generate_embeddings(chunks)

    #Step 4 : Save vector store
    vector_store.save_local(output_path)
    print(f"Vector store saved at {output_path}")

    return {
        "total_documents": len(raw_documents),
        "total_chunks": len(chunks),
        "failed_files": failed,
        "vector_db_path": output_path
    }

import re

#upload and embed cvs
def clean_extracted_text(text: str) -> str:
    """Clean and normalize extracted text"""
    if not text:
        return ""
    
    # Remove excessive whitespace but preserve paragraph structure
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double newline
    text = re.sub(r'[ \t]+', ' ', text)      # Multiple spaces to single
    text = text.strip()
    
    return text

def is_meaningful_text(text: str, min_meaningful_words=20) -> bool:
    """Check if extracted text has meaningful content"""
    if not text or len(text.strip()) < 100:
        return False
    
    # Count words (rough estimate)
    words = text.split()
    if len(words) < min_meaningful_words:
        return False
    
    # Check if text contains meaningful patterns (not just headers/fragments)
    meaningful_patterns = [
        'experience', 'skills', 'education', 'work', 'project',
        'developed', 'managed', 'created', 'responsible', 'achieved'
    ]
    
    text_lower = text.lower()
    meaningful_count = sum(1 for pattern in meaningful_patterns if pattern in text_lower)
    
    return meaningful_count >= 2

def is_good_chunk(chunk: str) -> bool:
    """Check if a chunk is meaningful enough to keep"""
    chunk = chunk.strip()
    
    # Too short
    if len(chunk) < 50:
        return False
        
    # Just a single word or name
    if len(chunk.split()) <= 3:
        return False
        
    # Mostly special characters or numbers
    if re.match(r'^[\W\d_]+$', chunk.replace(' ', '')):
        return False
        
    # Common meaningless patterns
    meaningless_patterns = [
        r'^\s*[•\-*]\s*\w{1,3}\s*$',  # Single bullet with short text
        r'^\s*\w+\s+/\s+\w+\s*$',     # Single "word / word" pattern
        r'^\s*\d{4}\s*[-–]\s*\d{4}\s*$',  # Just date range
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, chunk, re.IGNORECASE):
            return False
            
    return True

async def fallback_extraction(file_bytes: bytes, filename: str) -> str:
    """Fallback extraction for problematic files"""
    try:
        print("🔄 Trying fallback PDF extraction...")
        
        # For PDFs, try PyPDF2 as fallback
        if filename.lower().endswith('.pdf'):
            try:
                import PyPDF2
                from io import BytesIO
                
                pdf_file = BytesIO(file_bytes)
                reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if len(text.strip()) > 100:
                    print(f"✅ PyPDF2 fallback successful: {len(text)} chars")
                    return text
            except Exception as pdf_error:
                print(f"❌ PyPDF2 fallback failed: {pdf_error}")
                
        # For all files, try simple text decoding as last resort
        try:
            text = file_bytes.decode('utf-8', errors='ignore')
            if len(text.strip()) > 100:
                print(f"✅ Text decoding fallback successful: {len(text)} chars")
                return text
        except Exception as decode_error:
            print(f"❌ Text decoding failed: {decode_error}")
            
        return ""
    except Exception as e:
        print(f"❌ Fallback extraction error: {e}")
        return ""

# =============================
# IMPROVED CV UPLOAD & EMBEDDING
# =============================

async def uploaded_cv_embed(
    files: list[UploadFile] = File(...),
    user_id: str = File(...),
    job_title: str = File(...),
    db: Session = Depends(get_db)
):
    try:
        saved_files = []
        processed_cvs = []
        failed_cvs = []

        for file in files:
            print(f"\n=== Processing {file.filename} ===")
            
            # ✅ Check file size
            content = await file.read()
            if len(content) == 0:
                error_msg = f"Empty file: {file.filename}"
                print(f"❌ {error_msg}")
                failed_cvs.append({"file": file.filename, "error": error_msg})
                continue

            # Save file
            file_path = os.path.join(HR_CVS, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file.filename)

            # Extract text with enhanced validation
            try:
                text = await extract_uploaded_cv(content, file.filename)
                text = clean_extracted_text(text)
                
                # If primary extraction failed, try fallback
                if not text or len(text.strip()) < 100:
                    print("🔄 Primary extraction failed, trying fallback...")
                    text = await fallback_extraction(content, file.filename)
                    text = clean_extracted_text(text)
                    
            except Exception as e:
                print(f"❌ Extraction failed: {e}")
                try:
                    text = await fallback_extraction(content, file.filename)
                    text = clean_extracted_text(text)
                except Exception as fallback_error:
                    print(f"❌ Fallback also failed: {fallback_error}")
                    failed_cvs.append({"file": file.filename, "error": f"Extraction failed: {e}"})
                    continue

            # ✅ Validate extraction quality
            if not text or len(text.strip()) < 100:
                error_msg = f"Insufficient text extracted ({len(text) if text else 0} chars)"
                print(f"❌ {error_msg}")
                failed_cvs.append({"file": file.filename, "error": error_msg})
                continue
                
            if not is_meaningful_text(text):
                error_msg = "Text extracted but lacks meaningful content"
                print(f"❌ {error_msg}")
                failed_cvs.append({"file": file.filename, "error": error_msg})
                continue

            print(f"✅ Text extraction successful: {len(text)} characters")
            print(f"📝 Sample: {text[:200]}...")

            # ✅ DIRECT WHOLE-CV EMBEDDING (NO CHUNKS)
            print("🎯 Using DIRECT WHOLE-CV embedding (no chunks)")
            
            try:
                # Embed the entire CV text
                embedding = embedding_model.embed_documents([text])[0]
                embedding = np.array(embedding)
                embedding = normalize(embedding.reshape(1, -1))[0]
                
                # Save CV record with the full embedding
                cv_record = UserCVUpload(
                    user_id=user_id,
                    job_title=job_title,
                    file_name=file.filename,
                    cv_embeddings=embedding.tolist()  # Full CV embedding
                )
                db.add(cv_record)
                db.commit()
                
                print(f"✅ Direct embedding successful for {file.filename}")
                print(f"📊 Embedding dimensions: {len(embedding)}")
                print(f"📄 Text length: {len(text)} characters")
                
                # ✅ NO CHUNKS CREATED - we skip UserCVChunk entirely
                
                processed_cvs.append(file.filename)
                
            except Exception as embedding_error:
                print(f"❌ Embedding failed: {embedding_error}")
                failed_cvs.append({"file": file.filename, "error": f"Embedding failed: {embedding_error}"})
                continue

        return {
            "message": f"Processed {len(processed_cvs)}/{len(files)} CVs successfully (FULL CV EMBEDDING - NO CHUNKS)",
            "saved_files": saved_files,
            "processed_cvs": processed_cvs,
            "failed_cvs": failed_cvs,
            "embedding_type": "full_cv_no_chunks"
        }

    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
async def match_job_advert(
    user_id:str,
    job_title:str,
    job_description: str,
    top_k: int = 10,
    min_score: float = 0.3,
    db: Session = Depends(get_db)
):
    """
    Match job description against stored FULL CV embeddings (no chunks)
    """
    try:
        print(f"🔍 Matching job against FULL CV embeddings...")
        
        # Embed the job description
        job_embedding = embedding_model.embed_query(job_description)
        job_embedding = np.array(job_embedding).reshape(1, -1)
        job_embedding = normalize(job_embedding)[0]

        # Get only CVs that have embeddings (full CV embeddings)
        cv_records = db.query(UserCVUpload).filter(
            UserCVUpload.cv_embeddings.isnot(None) , UserCVUpload.job_title == job_title , UserCVUpload.user_id == user_id
        ).all()

        if not cv_records:
            return {"message": "No CV embeddings found in database", "matches": []}

        print(f"📊 Comparing with {len(cv_records)} FULL CV embeddings")

        # Calculate similarities
        matches = []
        for cv in cv_records:
            cv_embedding = np.array(cv.cv_embeddings).reshape(1, -1)
            similarity = cosine_similarity(job_embedding.reshape(1, -1), cv_embedding)[0][0]
            
            if similarity >= min_score:
                matches.append({
                    "cv_id": cv.id,
                    "file_name": cv.file_name,
                    "job_title": cv.job_title,
                    "user_id": cv.user_id,
                    "similarity_score": round(float(similarity), 4),
                    "match_percentage": f"{similarity * 100:.1f}%",
                    "uploaded_at": cv.uploaded_at.isoformat() if cv.uploaded_at else None,
                    "embedding_type": "full_cv"  # Indicate this is full CV matching
                })

        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top K matches
        top_matches = matches[:top_k]

        print(f"✅ Found {len(top_matches)} matches using FULL CV embeddings")

        return {
            "total_cvs_searched": len(cv_records),
            "matches_found": len(matches),
            "matching_method": "full_cv_embeddings",
            "job_description_preview": job_description[:200] + "..." if len(job_description) > 200 else job_description,
            "top_matches": top_matches
        }

    except Exception as e:
        print(f"❌ Matching failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Job matching failed: {str(e)}")

async def search_cvs_by_keywords(
    keywords: str,
    db: Session = Depends(get_db)
):
    """
    Search CVs by keywords in content
    """
    try:
        # Search in chunk texts for more granular results
        chunks = db.query(UserCVChunk).filter(
            UserCVChunk.chunk_text.ilike(f"%{keywords}%")
        ).all()

        # Group by CV to avoid duplicates
        cv_matches = {}
        for chunk in chunks:
            cv = db.query(UserCVUpload).filter(UserCVUpload.id == chunk.cv_id).first()
            if cv and cv.id not in cv_matches:
                cv_matches[cv.id] = {
                    "cv_id": cv.id,
                    "file_name": cv.file_name,
                    "job_title": cv.job_title,
                    "user_id": cv.user_id,
                    "matching_chunks": []
                }
            
            if cv:
                cv_matches[cv.id]["matching_chunks"].append({
                    "chunk_preview": chunk.chunk_text[:300] + "..." if len(chunk.chunk_text) > 300 else chunk.chunk_text,
                    "chunk_id": chunk.chunk_id
                })

        results = list(cv_matches.values())

        return {
            "search_keywords": keywords,
            "cv_matches_found": len(results),
            "total_chunks_matched": len(chunks),
            "results": results
        }

    except Exception as e:
        print(f"❌ Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    embed_folder(INPUT_FOLDER, VECTOR_DB_PATH)