from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
import tempfile
import os
import yaml
import re
from typing import Dict, List, Optional
from rendercv import create_a_pdf_from_a_yaml_string

app = FastAPI()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

TEMPLATES = {
    "classic": "Traditional two-column layout with conservative styling",
    "moderncv": "Clean single-column design with modern typography",
    "fancy": "Decorative elements with creative sections",
    "engineering": "Technical layout with skills matrix"
}

class CVRequest(BaseModel):
    cv_text: str
    template: str = "moderncv"

def convert_to_yaml(user_cv_text: str) -> str:
    prompt = f"""
    Analyze the following CV information and convert it to RenderCV-compatible YAML.
    Follow these rules strictly:
    1. Use exact field names from the schema below
    2. Leave missing fields empty (use null or empty lists/strings)
    3. Maintain proper YAML syntax
    4. Include all required sections even if empty

    Required YAML structure:
    name: str
    label: str
    email: str
    phone: str
    website: str
    location: str
    social_networks:
      - network: str
        username: str
    education:
      - institution: str
        degree: str
        date: str
        gpa: float
        courses: List[str]
    sections:
      - category: str
        entries:
          - organization: str
            position: str
            date: str
            location: str
            highlights: List[str]

    Input CV Content:
    {user_cv_text}

    Output ONLY valid YAML without any additional text or explanations.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000
    )

    yaml_content = response.choices[0].message.content
    return sanitize_yaml(yaml_content)

def sanitize_yaml(raw_yaml: str) -> str:
    """Clean and validate YAML structure"""
    # Remove code block markers if present
    cleaned = re.sub(r"^```yaml|^```|\s*```$", "", raw_yaml, flags=re.MULTILINE)
    
    # Parse and validate YAML structure
    try:
        parsed = yaml.safe_load(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Invalid YAML structure: root should be a dictionary")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax: {str(e)}")

    # Ensure required fields exist
    required_fields = ["name", "sections"]
    for field in required_fields:
        if field not in parsed:
            parsed[field] = "" if field == "name" else []

    # Ensure sections have proper structure
    if "sections" not in parsed:
        parsed["sections"] = []
    elif isinstance(parsed["sections"], list):
        for section in parsed["sections"]:
            if "category" not in section:
                section["category"] = "Uncategorized"
            if "entries" not in section:
                section["entries"] = []

    # Convert back to YAML with consistent formatting
    return yaml.dump(
        parsed,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=80
    )


async def get_available_templates() -> Dict[str, str]:
    return TEMPLATES


async def generate_cv(request: CVRequest):
    if request.template not in TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template. Valid options: {list(TEMPLATES.keys())}"
        )
    
    try:
        yaml_content = convert_to_yaml(request.cv_text)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "cv.pdf")
            create_a_pdf_from_a_yaml_string(yaml_content, output_file_path=pdf_path)
            
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise HTTPException(status_code=500, detail="PDF generation failed")
                
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"cv_{request.template}.pdf"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))