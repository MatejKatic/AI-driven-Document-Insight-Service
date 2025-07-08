from pathlib import Path
from app.pdf_extractor import PDFExtractor
import time

def test_extraction():
    """Test PDF extraction methods"""

    extractor = PDFExtractor()
    

    test_dir = Path("test_docs")
    pdf_files = list(test_dir.glob("*.pdf"))
    image_files = list(test_dir.glob("*.png")) + list(test_dir.glob("*.jpg"))
    
    if not pdf_files and not image_files:
        print("❌ No test files found in test_docs/")
        return
    
    print("🔍 Testing Text Extraction Methods\n")
    print("=" * 60)
    
    if pdf_files:
        print("\n📄 Testing PDF files:")
        print("-" * 40)
        
        for pdf_file in pdf_files[:3]:  # Test first 3 PDFs
            print(f"\n📑 File: {pdf_file.name}")
            
            start_time = time.time()
            result = extractor.extract_text(str(pdf_file))
            extraction_time = time.time() - start_time
            
            if result["success"]:
                print(f"✅ Method: {result['method']}")
                print(f"⏱️  Time: {extraction_time:.2f}s")
                print(f"📊 Text length: {len(result['text'])} characters")
                print(f"📝 Preview: {result['text'][:200]}...")
                if result.get('page_count'):
                    print(f"📄 Pages: {result['page_count']}")
            else:
                print(f"❌ Failed: {result['error']}")
    
    if image_files:
        print("\n\n🖼️  Testing Image files:")
        print("-" * 40)
        
        for image_file in image_files[:2]:  # Test first 2 images
            print(f"\n🎨 File: {image_file.name}")
            
            start_time = time.time()
            result = extractor.extract_text(str(image_file))
            extraction_time = time.time() - start_time
            
            if result["success"]:
                print(f"✅ Method: {result['method']}")
                print(f"⏱️  Time: {extraction_time:.2f}s")
                print(f"📊 Text length: {len(result['text'])} characters")
                print(f"📝 Text: {result['text'][:200]}...")
            else:
                print(f"❌ Failed: {result['error']}")
    
    print("\n" + "=" * 60)
    print("✅ Text extraction test completed!")

if __name__ == "__main__":
    test_extraction()