"""Create dummy test documents for the AI Document Insight Service"""

import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

def create_all_test_documents():
    """Create all test documents - both PDFs and images"""
    
    test_dir = Path("test_docs")
    test_dir.mkdir(exist_ok=True)
    
    print("📄 Creating test documents for AI Document Insight Service...")
    print("=" * 60)
    
    print("\n📑 Creating PDF documents...")
    create_test_pdfs(test_dir)
    
    print("\n🖼️ Creating image documents for OCR testing...")
    create_test_images(test_dir)
    
    print("\n" + "=" * 60)
    print("✅ All test documents created successfully!")
    print(f"📁 Location: {test_dir.absolute()}")
    print(f"📊 Total files created: {len(list(test_dir.glob('*')))}")
    print("\nDocument types created:")
    print("  - PDF files: Business reports, contracts, technical specs")
    print("  - Image files: Receipts, invoices, business cards, notes")
    print("  - Formats: PDF, PNG, JPG (testing both text extraction and OCR)")

def create_test_pdfs(test_dir):
    """Create sample PDF documents for testing"""
    
    documents = [
        {
            "filename": "company_report_2024.pdf",
            "title": "Annual Company Report 2024",
            "content": """
ANNUAL COMPANY REPORT 2024

Executive Summary:
Our company achieved remarkable growth in 2024, with revenue increasing by 25% year-over-year. 
Key highlights include successful product launches, market expansion, and improved operational efficiency.

Financial Performance:
- Revenue: $10.5 million (up from $8.4 million in 2023)
- Net Profit: $2.1 million
- Operating Margin: 20%
- Customer Base: 15,000 active customers

Strategic Initiatives:
1. Digital Transformation: Implemented new CRM system
2. Market Expansion: Entered 3 new geographic markets
3. Product Innovation: Launched 5 new products
4. Sustainability: Reduced carbon footprint by 15%

Future Outlook:
We anticipate continued growth in 2025 with projected revenue of $13 million.
Key focus areas include AI integration, customer experience enhancement, and strategic partnerships.
            """
        },
        {
            "filename": "technical_specification.pdf",
            "title": "Technical Specification Document",
            "content": """
TECHNICAL SPECIFICATION - AI DOCUMENT PROCESSOR

1. System Overview:
The AI Document Processor is a cloud-based solution for intelligent document analysis.
It uses advanced machine learning algorithms to extract, classify, and analyze text data.

2. Architecture:
- Frontend: React-based web application
- Backend: FastAPI microservices
- ML Engine: Transformer-based models
- Database: PostgreSQL with vector storage
- Cache: Redis for performance optimization

3. Key Features:
- Multi-format support (PDF, DOCX, images)
- Real-time text extraction
- Natural language question answering
- Entity recognition and classification
- Sentiment analysis
- Multi-language support

4. Performance Requirements:
- Processing speed: < 5 seconds per document
- Accuracy: > 95% for text extraction
- Concurrent users: 1000+
- Uptime: 99.9% SLA

5. Security:
- End-to-end encryption
- GDPR compliant
- SOC 2 certified
- Regular security audits
            """
        },
        {
            "filename": "contract_sample.pdf",
            "title": "Service Agreement Contract",
            "content": """
SERVICE AGREEMENT CONTRACT

This Agreement is entered into as of January 1, 2024, between:
Client: ABC Corporation ("Client")
Service Provider: XYZ Solutions Ltd. ("Provider")

1. SERVICES
Provider agrees to deliver the following services:
- Software development and maintenance
- Technical support (24/7)
- Monthly performance reports
- Security updates and patches

2. PAYMENT TERMS
- Monthly fee: $5,000
- Payment due: Net 30 days
- Late payment penalty: 1.5% per month

3. TERM AND TERMINATION
- Initial term: 12 months
- Auto-renewal: Yes, unless 30-day notice
- Early termination: 90-day notice required

4. CONFIDENTIALITY
Both parties agree to maintain strict confidentiality of all proprietary information.

5. LIABILITY
Provider's liability limited to monthly service fees. No consequential damages.

6. GOVERNING LAW
This agreement governed by the laws of Delaware, USA.
            """
        }
    ]
    
    for doc in documents:
        pdf_path = test_dir / doc["filename"]
        
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        
        title_rect = fitz.Rect(72, 72, 540, 120)
        page.insert_textbox(
            title_rect,
            doc["title"],
            fontsize=16,
            fontname="Helvetica-Bold",
            align=1  # Center
        )
        
        content_rect = fitz.Rect(72, 140, 540, 720)
        page.insert_textbox(
            content_rect,
            doc["content"],
            fontsize=11,
            fontname="Helvetica"
        )
        
        pdf_doc.save(str(pdf_path))
        pdf_doc.close()
        
        print(f"  ✅ Created: {doc['filename']}")

def create_test_images(test_dir):
    """Create various test images for OCR testing"""
    
    create_scanned_invoice(test_dir / "scanned_invoice.png")
    create_receipt_image(test_dir / "receipt_sample.jpg")
    create_business_card(test_dir / "business_card.png")
    create_meeting_notes(test_dir / "meeting_notes.png")

def create_scanned_invoice(output_path):
    """Create a fake 'scanned' invoice for OCR testing"""
    
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    for _ in range(1000):
        x = random.randint(0, 800)
        y = random.randint(0, 1000)
        gray = random.randint(240, 255)
        draw.point((x, y), fill=(gray, gray, gray))
    
    y = 100
    
    draw.text((300, y), "INVOICE #2024-001", fill='black')
    y += 80
    
    draw.text((50, y), "Tech Solutions Inc.", fill='black')
    y += 40
    draw.text((50, y), "123 Main Street, Suite 100", fill='black')
    y += 40
    draw.text((50, y), "San Francisco, CA 94105", fill='black')
    y += 80
    
    draw.text((50, y), "Date: January 15, 2024", fill='black')
    y += 40
    draw.text((50, y), "Bill To: Sample Customer Inc.", fill='black')
    y += 80
    
    draw.text((50, y), "Description", fill='black')
    draw.text((400, y), "Quantity", fill='black')
    draw.text((550, y), "Price", fill='black')
    draw.text((650, y), "Total", fill='black')
    y += 40
    
    draw.line([(50, y), (750, y)], fill='black', width=1)
    y += 20
    
    items = [
        ("Consulting Services", "10 hours", "$150/hr", "$1,500"),
        ("Software License", "1", "$500", "$500"),
        ("Technical Support", "5 hours", "$100/hr", "$500"),
    ]
    
    for item, qty, price, total in items:
        draw.text((50, y), item, fill='black')
        draw.text((400, y), qty, fill='black')
        draw.text((550, y), price, fill='black')
        draw.text((650, y), total, fill='black')
        y += 40
    
    y += 40
    draw.text((400, y), "TOTAL:", fill='black')
    draw.text((650, y), "$2,750", fill='black')
    
    img = img.rotate(0.5, fillcolor='white')  # Slight rotation
    img.save(output_path)
    print(f"  ✅ Created: {output_path.name}")

def create_receipt_image(output_path):
    """Create a receipt-style image"""
    img = Image.new('RGB', (400, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    for _ in range(500):
        x = random.randint(0, 400)
        y = random.randint(0, 600)
        gray = random.randint(245, 255)
        draw.point((x, y), fill=(gray, gray, gray))
    
    y = 30
    
    draw.text((120, y), "TECH STORE", fill='black')
    y += 30
    draw.text((80, y), "123 Tech Avenue", fill='black')
    y += 40
    
    draw.text((30, y), "Date: 2024-01-20  Time: 14:35", fill='black')
    y += 40
    
    items = [
        ("USB Cable", "$12.99"),
        ("Wireless Mouse", "$34.99"),
        ("HDMI Adapter", "$19.99"),
    ]
    
    for item, price in items:
        draw.text((30, y), item, fill='black')
        draw.text((280, y), price, fill='black')
        y += 30
    
    y += 20
    draw.text((30, y), "TOTAL:", fill='black')
    draw.text((280, y), "$67.97", fill='black')
    
    img.save(output_path, quality=95)
    print(f"  ✅ Created: {output_path.name}")

def create_business_card(output_path):
    """Create a business card image"""
    img = Image.new('RGB', (500, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    draw.text((50, 50), "John Smith", fill='black')
    draw.text((50, 90), "Senior Software Engineer", fill='black')
    draw.text((50, 130), "Tech Innovations Corp", fill='black')
    draw.text((50, 180), "Email: john.smith@techinnovations.com", fill='black')
    draw.text((50, 210), "Phone: +1 (555) 123-4567", fill='black')
    
    img.save(output_path)
    print(f"  ✅ Created: {output_path.name}")

def create_meeting_notes(output_path):
    """Create a meeting notes image"""
    img = Image.new('RGB', (600, 400), color=(255, 255, 240))
    draw = ImageDraw.Draw(img)
    
    for y in range(50, 400, 30):
        draw.line([(30, y), (570, y)], fill=(200, 200, 200))
    
    y = 60
    notes = [
        "Meeting Notes - Product Review",
        "Date: January 18, 2024",
        "",
        "Key Points:",
        "- Q4 revenue exceeded targets by 15%",
        "- Customer satisfaction: 4.2/5",
        "",
        "Action Items:",
        "1. Prepare Q1 roadmap",
        "2. Schedule feedback sessions"
    ]
    
    for note in notes:
        draw.text((40, y), note, fill='black')
        y += 25
    
    img.save(output_path)
    print(f"  ✅ Created: {output_path.name}")

if __name__ == "__main__":
    create_all_test_documents()