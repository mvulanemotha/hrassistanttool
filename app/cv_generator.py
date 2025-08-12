import io
import os
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
from docx2pdf import convert

# --- Load environment variables ---
load_dotenv()

# Get Groq API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ Missing GROQ_API_KEY in .env file")

# Create OpenAI client for Groq API
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# --- Helper functions ---

def extract_text_from_docx(docx_bytes: bytes) -> str:
    """
    Extract plain text from a DOCX file.
    """
    doc = Document(io.BytesIO(docx_bytes))
    return "\n".join(
        [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    )


def generate_cv_with_llm(user_cv_text: str, template_text: str) -> str:
    """
    Ask the LLM to rewrite CV using template style.
    """
    prompt = f"""
    You are a professional CV writer. Rewrite the user's CV using the style, tone,
    and structure of the template CV. Preserve all relevant achievements, skills,
    and experiences from the user CV.

    --- TEMPLATE CV ---
    {template_text}

    --- USER CV ---
    {user_cv_text}

    Now produce the rewritten CV content in plain text.
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Groq model
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def create_docx_from_text(template_bytes: bytes, generated_text: str) -> bytes:
    """
    Insert generated text into a new DOCX while preserving basic template style.
    """
    template_doc = Document(io.BytesIO(template_bytes))
    new_doc = Document()

    for para in template_doc.paragraphs:
        if para.style.name.startswith("Heading"):
            new_doc.add_paragraph(para.text, style=para.style)
        else:
            # Insert generated CV text after headings
            new_doc.add_paragraph(generated_text)
            break

    output_stream = io.BytesIO()
    new_doc.save(output_stream)
    return output_stream.getvalue()



def convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "temp.docx")
        pdf_path = os.path.join(tmpdir , "temp.pdf")

        with open(docx_path , "wb") as f:
            f.write(docx_bytes)

        convert(docx_path , pdf_path) #requires Ms Word Installed

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    return pdf_bytes