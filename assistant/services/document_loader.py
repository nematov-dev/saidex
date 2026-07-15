"""Yuklangan fayldan (pdf/docx/txt) toza matn ajratib olish."""
from pathlib import Path
from pypdf import PdfReader
import docx


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == ".docx":
        d = docx.Document(file_path)
        return "\n".join(p.text for p in d.paragraphs)

    if ext in (".txt", ".md"):
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Qo'llab-quvvatlanmaydigan fayl turi: {ext}")
