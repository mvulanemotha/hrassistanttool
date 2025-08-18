import io
import os
import re
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
from docx2pdf import convert

# --- Load environment variables ---
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ Missing GROQ_API_KEY in .env file")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# --- Helper functions ---

def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract clean text from DOCX with section preservation"""
    doc = Document(io.BytesIO(docx_bytes))
    return "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

def generate_cv_with_llm(user_cv_text: str, template_text: str) -> str:
    """Generate formatted CV text with explicit Markdown instructions"""
    prompt = f"""
    Rewrite the user's CV using the style, tone, and structure of the template CV. 
    Preserve all content from the user CV while adopting the template's format.
    
    Important formatting rules:
    1. Use Markdown-style headers: **SECTION TITLE**
    2. Use hyphens for bullet points: - Item
    3. Keep contact info as plain text at top
    4. Maintain original achievements/metrics
    
    --- TEMPLATE EXAMPLE ---
    Caleb foster
    456 East 78th Ave | Denver, CO 87654 | 303.555.0113 | caleb@example.com
    
    **OBJECTIVE**
    Professional summary here...
    
    **EXPERIENCE**
    - Achievement 1
    - Achievement 2
    
    --- USER CV CONTENT ---
    {user_cv_text}
    
    --- TEMPLATE STYLE ---
    {template_text}
    
    Now produce the rewritten CV content:
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024
    )
    return response.choices[0].message.content

def create_docx_from_text(template_bytes: bytes, generated_text: str) -> bytes:
    """Convert generated Markdown-style text to formatted DOCX"""
    doc = Document(io.BytesIO(template_bytes))
    
    # Clear placeholder content but preserve styles
    for element in list(doc.element.body):
        doc.element.body.remove(element)
    
    # Process generated text
    sections = re.split(r"\n\s*\*\*", generated_text)  # Split by markdown headers
    
    # Process header (first section without **)
    header_content = sections[0].strip()
    if header_content:
        for line in header_content.split('\n'):
            if line.strip():
                p = doc.add_paragraph(line.strip())
                p.paragraph_format.space_after = Pt(0)
    
    # Process sections
    for section in sections[1:]:
        if '**' in section:
            title, content = section.split('**', 1)
            title = title.strip()
            content = content.strip()
            
            # Add section header
            if title:
                try:
                    header = doc.add_paragraph(title, style="Heading 1")
                except KeyError:
                    header = doc.add_paragraph(title)
                    header.runs[0].bold = True
                    header.runs[0].font.size = Pt(14)
            
            # Process content
            for item in content.split('\n'):
                item = item.strip()
                if not item:
                    continue
                    
                # Bullet points
                if item.startswith('-'):
                    p = doc.add_paragraph()
                    p.add_run('• ' + item[1:].strip())
                    
                    # Add custom bullet formatting
                    p.paragraph_format.left_indent = Pt(18)
                    p.paragraph_format.space_after = Pt(4)
                # Sub-headers
                elif item.endswith(':') and len(item) < 30:
                    try:
                        subhead = doc.add_paragraph(item, style="Heading 2")
                    except KeyError:
                        subhead = doc.add_paragraph(item)
                        subhead.runs[0].bold = True
                # Regular text
                else:
                    doc.add_paragraph(item)
    
    # Save to bytes
    output_stream = io.BytesIO()
    doc.save(output_stream)
    return output_stream.getvalue()

def convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    """Convert DOCX to PDF (requires MS Word)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "temp.docx")
        pdf_path = os.path.join(tmpdir, "temp.pdf")

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        convert(docx_path, pdf_path)

        with open(pdf_path, "rb") as f:
            return f.read()