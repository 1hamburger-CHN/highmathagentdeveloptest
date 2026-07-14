"""Extract text from HIT Complex Analysis PDF textbook."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not found, trying pdfplumber...")
    try:
        import pdfplumber
        HAS_PDFPLUMBER = True
        HAS_PYPDF = False
    except ImportError:
        print("No PDF library available. Install PyPDF2 or pdfplumber.")
        sys.exit(1)
else:
    HAS_PYPDF = True
    HAS_PDFPLUMBER = False

PDF_PATH = os.path.join(os.path.dirname(__file__), '..', 'HIT教材 复变函数与积分变换同步学习(2).pdf')

def extract_with_pypdf(path):
    reader = PyPDF2.PdfReader(path)
    print(f"Total pages: {len(reader.pages)}")
    for i in range(min(10, len(reader.pages))):
        text = reader.pages[i].extract_text()
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print(f"{'='*60}")
        if text:
            print(text[:2000])
        else:
            print("[No text extracted]")

def extract_with_pdfplumber(path):
    with pdfplumber.open(path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        for i in range(min(10, len(pdf.pages))):
            text = pdf.pages[i].extract_text()
            print(f"\n{'='*60}")
            print(f"PAGE {i+1}")
            print(f"{'='*60}")
            if text:
                print(text[:2000])
            else:
                print("[No text extracted]")

if __name__ == '__main__':
    if HAS_PYPDF:
        extract_with_pypdf(PDF_PATH)
    else:
        extract_with_pdfplumber(PDF_PATH)
