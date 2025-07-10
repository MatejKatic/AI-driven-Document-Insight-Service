"""Check if all required dependencies are installed correctly"""

import sys

def check_dependency(package_name, import_name=None):
    """Check if a package is installed and can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name} - Installed")
        return True
    except ImportError:
        print(f"❌ {package_name} - NOT installed")
        return False

def main():
    print("Checking AI Document Insight Service Dependencies")
    print("=" * 50)
    
    # Core dependencies
    core_dependencies = [
        ("FastAPI", "fastapi"),
        ("Uvicorn", "uvicorn"),
        ("Python-Multipart", "multipart"),
        ("Python-Dotenv", "dotenv"),
        ("Pydantic", "pydantic"),
        ("HTTPX", "httpx"),
    ]
    
    # PDF & OCR dependencies
    pdf_dependencies = [
        ("PyMuPDF", "fitz"),
        ("Pillow", "PIL"),
        ("EasyOCR", "easyocr"),
        ("OpenCV", "cv2"),
    ]
    
    # ML & Data dependencies
    ml_dependencies = [
        ("NumPy", "numpy"),
        ("Scikit-learn", "sklearn"),
        ("Pandas", "pandas"),
    ]
    
    # UI & Visualization dependencies
    ui_dependencies = [
        ("Gradio", "gradio"),
        ("Plotly", "plotly"),
    ]
    
    # Performance & Optional dependencies
    other_dependencies = [
        ("PSUtil", "psutil"),
        ("Redis", "redis"),
    ]
    
    all_installed = True
    
    print("\n📦 Core Dependencies:")
    for package, import_name in core_dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n📄 PDF & OCR Dependencies:")
    for package, import_name in pdf_dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n🤖 ML & Data Dependencies:")
    for package, import_name in ml_dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n🎨 UI & Visualization Dependencies:")
    for package, import_name in ui_dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n⚡ Performance & Optional Dependencies:")
    for package, import_name in other_dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n" + "=" * 50)
    
    if all_installed:
        print("✅ All dependencies are installed!")
        print("\nNext steps:")
        print("1. Create a .env file with your DEEPSEEK_API_KEY")
        print("2. Add test PDFs to test_docs/ folder")
        print("3. Run: python run.py (for API)")
        print("4. Run: python run_gradio.py (for UI)")
        print("   OR")
        print("   Run: python run_all.py (for both)")
    else:
        print("❌ Some dependencies are missing!")
        print("\nInstall missing packages:")
        print("pip install -r requirements.txt")
    
    # Check for .env file
    print("\n" + "=" * 50)
    print("Checking configuration:")
    
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        if os.getenv("DEEPSEEK_API_KEY"):
            print("✅ DEEPSEEK_API_KEY found in .env")
        else:
            print("❌ DEEPSEEK_API_KEY not found - add it to .env file")
            print("   Copy .env.example to .env and add your key")
    except:
        print("❌ Could not check .env file")
    
    # Check for test documents
    print("\n" + "=" * 50)
    print("Checking test documents:")
    
    from pathlib import Path
    test_dir = Path("test_docs")
    if test_dir.exists():
        pdf_count = len(list(test_dir.glob("*.pdf")))
        img_count = len(list(test_dir.glob("*.png")) + list(test_dir.glob("*.jpg")))
        
        if pdf_count > 0 or img_count > 0:
            print(f"✅ Found {pdf_count} PDFs and {img_count} images in test_docs/")
        else:
            print("⚠️  No test documents found in test_docs/")
            print("   Run: python create_test_docs.py")
    else:
        print("❌ test_docs/ folder not found")
        print("   Create it and add PDFs or run: python create_test_docs.py")
    
    # Check if API is running
    print("\n" + "=" * 50)
    print("Checking API status:")
    
    try:
        import httpx
        import asyncio
        
        async def check_api():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8000/", timeout=2.0)
                    if response.status_code == 200:
                        print("✅ API server is running on http://localhost:8000")
                        return True
            except:
                pass
            print("❌ API server is not running")
            print("   Run: python run.py")
            return False
        
        asyncio.run(check_api())
    except:
        print("❌ Could not check API status")

if __name__ == "__main__":
    main()