# Text Extraction Methods

## PyMuPDF (Primary Method)
- **Purpose**: Extract text from regular PDFs
- **Speed**: Very fast (< 1 second for most PDFs)
- **Quality**: Excellent for PDFs with embedded text
- **Use case**: 90% of typical PDFs (reports, contracts, invoices)

## EasyOCR (Fallback Method)
- **Purpose**: Extract text from scanned PDFs and images
- **Speed**: Slower (5-30 seconds depending on pages)
- **Quality**: Good accuracy for printed text
- **Use case**: 
  - Scanned documents
  - Image files (PNG, JPG, etc.)
  - PDFs where PyMuPDF extracts no text

## Extraction Flow

```
PDF/Image File
    ↓
Is it a PDF?
    ├─ Yes → Try PyMuPDF
    │         ├─ Success → Return text
    │         └─ No text → Try EasyOCR
    └─ No → Use EasyOCR directly
```

## Performance Tips

1. **First run of EasyOCR is slow** - it downloads models (~64MB)
2. **Subsequent runs are faster** - models are cached
3. **PyMuPDF handles most cases** - OCR is rarely needed

## Testing Your Documents

Run the test script to see which method works for your files:
```bash
python test_extraction_methods.py
```