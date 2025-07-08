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
    
    dependencies = [
        ("FastAPI", "fastapi"),
        ("Uvicorn", "uvicorn"),
        ("PyMuPDF", "fitz"),
        ("EasyOCR", "easyocr"),
        ("Pillow", "PIL"),
        ("NumPy", "numpy"),
        ("OpenCV", "cv2"),
        ("HTTPX", "httpx"),
        ("python-dotenv", "dotenv"),
        ("Pydantic", "pydantic"),
        ("AIOFiles", "aiofiles"),
    ]
    
    all_installed = True
    
    for package, import_name in dependencies:
        if not check_dependency(package, import_name):
            all_installed = False
    
    print("\n" + "=" * 50)
    
    if all_installed:
        print("✅ All dependencies are installed!")
        print("\nNext steps:")
        print("1. Create a .env file with your DEEPSEEK_API_KEY")
        print("2. Add test PDFs to test_docs/ folder")
        print("3. Run: python run.py")
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
    except:
        print("❌ Could not check .env file")

if __name__ == "__main__":
    main()