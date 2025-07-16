import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# === CONFIGURATIONS ===
VECTOR_DB_PATH = "cv_vectorstore"  # Path to your FAISS vector store
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 20  # retrieve top 20 chunks before grouping

# === Load the vector store ===
def load_vectorstore():
    """Load the vector store from the specified path."""
    print(f"[INFO] Loading vector store from: {VECTOR_DB_PATH}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = FAISS.load_local(
        VECTOR_DB_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("[INFO] Vector store loaded successfully.")
    return vectorstore

# === Compare job description with stored CVs ===
def compare_with_job_description(job_description: str):
    vectorstore = load_vectorstore()

    print("[INFO] Searching for similar CVs to the job description...")
    results_with_scores = vectorstore.similarity_search_with_score(job_description, k=TOP_K)

    if not results_with_scores:
        print("[INFO] No similar CVs found.")
        return []

    # Group by file_name and keep only best (lowest score) per file
    best_by_file = {}
    for doc, score in results_with_scores:
        file_name = doc.metadata.get("file_name", "Unknown")
        if file_name not in best_by_file or score < best_by_file[file_name][1]:
            best_by_file[file_name] = (doc, score)

    print("\n=== TOP MATCHES (Best per CV) ===\n")
    for i, (file_name, (doc, score)) in enumerate(best_by_file.items(), start=1):
        print(f"Match #{i}")
        print(f"File: {file_name}")
        print(f"Score (lower is more similar): {score:.4f}")
        print("Matched Text:\n", doc.page_content[:500], "...\n")
        print("-" * 60)

    print(f"[INFO] Found {len(best_by_file)} matching CV(s).")
    return best_by_file

# === Main run ===
if __name__ == "__main__":
    print("Paste the job description below (press Enter when done):")
    print("(Type your job description. When finished, type 'END' on a new line.)")
    job_desc_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        job_desc_lines.append(line)

    job_description_text = "\n".join(job_desc_lines).strip()
    if job_description_text:
        compare_with_job_description(job_description_text)
    else:
        print("[ERROR] No job description provided.")
