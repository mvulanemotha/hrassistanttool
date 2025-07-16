from fpdf import FPDF
import os

output_dir = "cv_documents"
os.makedirs(output_dir, exist_ok=True)

cv_samples = [
    {
        "name": "Software Engineer",
        "content": """John Doe
Email: john.doe@example.com
Phone: +1 555 123 4567

SUMMARY
Software engineer with 5 years of experience in developing scalable web applications and backend systems.
Proficient in Python, Django, and cloud technologies.

EXPERIENCE
Software Engineer - TechCorp
Jan 2020 - Present
- Developed REST APIs in Django.
- Deployed services on AWS.

EDUCATION
BSc Computer Science
University of Technology"""
    },
    {
        "name": "Data Analyst",
        "content": """Jane Smith
Email: jane.smith@example.com
Phone: +1 555 987 6543

SUMMARY
Data analyst with expertise in SQL, Python, and Tableau. Skilled in data visualization and predictive modeling.

EXPERIENCE
Data Analyst - Insight Analytics
Mar 2019 - Present
- Designed dashboards in Tableau.
- Built predictive models using scikit-learn.

EDUCATION
BSc Statistics
University of Data"""
    },
    # Add more CVs here...
]

def sanitize_text(text: str) -> str:
    # Replace problematic characters with ASCII equivalents
    return (text.replace("–", "-")
                .replace("—", "-")
                .replace("’", "'")
                .replace("“", '"')
                .replace("”", '"'))

def create_pdf(file_path: str, text: str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in sanitize_text(text).split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(file_path)

# Generate PDFs
pdf_files = []
for cv in cv_samples:
    filename = f"{cv['name'].replace(' ', '_')}.pdf"
    file_path = os.path.join(output_dir, filename)
    create_pdf(file_path, cv["content"])
    pdf_files.append(file_path)

print("✅ PDFs created:")
for f in pdf_files:
    print(f)
