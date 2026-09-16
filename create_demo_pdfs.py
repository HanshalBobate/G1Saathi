import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf(path, title, date, lines):
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "SYNTHETIC DEMONSTRATION DATA")
    c.setFont("Helvetica", 14)
    c.drawString(50, 720, title)
    c.drawString(50, 700, f"Report Date: {date}")
    
    c.setFont("Helvetica", 12)
    y = 660
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
        
    c.save()

os.makedirs("data/demo_reports", exist_ok=True)

# CBC August
create_pdf("data/demo_reports/cbc_august.pdf", "Complete Blood Count (CBC)", "2026-08-01", [
    "Patient: Jane Doe (Synthetic)",
    "",
    "Hemoglobin: 10.5 g/dL (Reference Range: 12.0 - 16.0 g/dL)",
    "WBC: 6500 /uL (Reference Range: 4000 - 11000 /uL)",
    "Platelets: 220000 /uL (Reference Range: 150000 - 450000 /uL)"
])

# CBC September
create_pdf("data/demo_reports/cbc_september.pdf", "Complete Blood Count (CBC)", "2026-09-15", [
    "Patient: Jane Doe (Synthetic)",
    "",
    "Hemoglobin: 11.2 g/dL (Reference Range: 12.0 - 16.0 g/dL)",
    "WBC: 7200 /uL (Reference Range: 4000 - 11000 /uL)",
    "Platelets: 250000 /uL (Reference Range: 150000 - 450000 /uL)"
])

# Diabetes August
create_pdf("data/demo_reports/diabetes_august.pdf", "Metabolic Panel", "2026-08-01", [
    "Patient: John Smith (Synthetic)",
    "",
    "Fasting Blood Glucose: 135 mg/dL (Reference Range: 70 - 99 mg/dL)",
    "HbA1c: 7.2 % (Reference Range: < 5.7 %)"
])

# Diabetes September
create_pdf("data/demo_reports/diabetes_september.pdf", "Metabolic Panel", "2026-09-15", [
    "Patient: John Smith (Synthetic)",
    "",
    "Fasting Blood Glucose: 110 mg/dL (Reference Range: 70 - 99 mg/dL)",
    "HbA1c: 6.5 % (Reference Range: < 5.7 %)"
])
