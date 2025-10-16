from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
from pathlib import Path

# --- Helper to create a watermark
def create_watermark(text:str) -> PdfReader:
    packet = io.BytesIO()
    can = canvas.Canvas(packet,pagesize=A4)
    can.setFont("Helvetica-Bold" , 60)
    can.setFillGray(0.6,0.4)
    can.saveState()
    can.translate(300,500)
    can.rotate(45)
    can.drawCentredString(0,0, text)
    can.restoreState()
    can.save()

    packet.seek(0)

    return PdfReader(packet)


# --- Apply watermark to an existing PDF ---
def add_watermark_to_pdf(input_pdf_path:Path , watermark_text:str) -> io.BytesIO:
    watermark_pdf = create_watermark(watermark_text)
    input_pdf = PdfReader(str(input_pdf_path))
    output = PdfWriter()

    for page in input_pdf.pages:
        page.merge_page(watermark_pdf.pages[0])
        output.add_page(page)

    output_stream = io.BytesIO()
    output.write(output_stream)
    output_stream.seek(0)

    return output_stream
