import os
import re
from pathlib import Path

from langchain.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import hashlib

# Configurations
INPUT_FOLDER = "cv_documents" # folder containing your CVs
VECTOR_DB_PATH = "cv_vectorstore" # path to save the vector store
SUPPORTED_EXTENSIONS = ['.pdf' , '.docx', '.txt' , '.doc']

os.makedirs(VECTOR_DB_PATH, exist_ok=True)  # Ensure the output directory exists
os.makedirs(INPUT_FOLDER,exist_ok=True)  # Ensure the input directory exists

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2" # HuggingFace model for embeddings


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


# Run the embedding process
if __name__ == "__main__":
    result = embed_folder(INPUT_FOLDER, VECTOR_DB_PATH)
    print("\nEmbedding Summary")
    print(f"- Processed documents: {result['total_documents']}")
    print(f"- Created chunks: {result['total_chunks']}")
    print(f"- Failed files: {len(result['failed_files'])}")
    print(f"- Vector DB location: {result['vector_db_path']}")
