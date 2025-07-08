"""Create dummy test documents for the AI Document Insight Service"""

import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

def create_test_pdfs():
    """Create sample PDF documents for testing"""
    
    test_dir = Path("test_docs")
    test_dir.mkdir(exist_ok=True)
    
    print("📄 Creating test documents...")
    
    # Sample content for different document types
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

Signed:
Client Representative: ________________
Provider Representative: ________________
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
        
        print(f"✅ Created: {doc['filename']}")
    
    create_scanned_document(test_dir / "scanned_invoice.png")
    
    print("\n✅ Test documents created successfully!")
    print(f"📁 Location: {test_dir.absolute()}")

def create_scanned_document(output_path):
    """Create a fake 'scanned' document image for OCR testing"""
    
    img = Image.new('RGB', (600, 800), color='white')
    draw = ImageDraw.Draw(img)
    
    for _ in range(1000):
        x = random.randint(0, 600)
        y = random.randint(0, 800)
        gray = random.randint(240, 255)
        draw.point((x, y), fill=(gray, gray, gray))
    
    y_position = 50
    
    draw.text((200, y_position), "INVOICE #2024-001", fill='black')
    y_position += 50
    
    invoice_content = [
        "Date: January 15, 2024",
        "Bill To: Sample Customer Inc.",
        "",
        "Description              Quantity    Price",
        "----------------------------------------",
        "Consulting Services         10h      $150/h",
        "Software License            1        $500",
        "Technical Support           5h       $100/h",
        "",
        "Subtotal: $2,500",
        "Tax (10%): $250",
        "TOTAL: $2,750",
        "",
        "Payment Due: February 15, 2024"
    ]
    
    for line in invoice_content:
        draw.text((50, y_position), line, fill='black')
        y_position += 30
    
    img.save(output_path)
    print(f"✅ Created: scanned_invoice.png (for OCR testing)")

if __name__ == "__main__":
    create_test_pdfs()