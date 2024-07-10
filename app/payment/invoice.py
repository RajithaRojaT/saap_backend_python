from reportlab.lib.pagesizes import letter
import os
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
import os
from reportlab.pdfgen import canvas


def create_invoice_pdf(file_path, invoice_data):
    c = canvas.Canvas(file_path, pagesize=letter)

    # Set up text properties
    c.setFont("Helvetica-Bold", 16)

    # Title
    c.drawCentredString(300, 750, "Invoice")
    # c.drawImage("images/sb-logo.png", 50, 720, width=100, height=50)  
    # Separator line
    c.line(50, 710, 550, 710)
    c.setFont("Helvetica", 12)
    # Invoice details
    y_position = 690
    for key, value in invoice_data.items():
        c.drawString(100, y_position, f"{key}: {value}")
        y_position -= 20  # Move to the next line

    # Footer
    # c.drawString(50, 50, "Thank you for your business.")

    c.save()
