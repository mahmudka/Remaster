"""
PDF book parser using pypdf (pure Python, ARM64 compatible).
Splits text into ~2000-char chunks for RAG.
"""
import re
import pypdf


CHUNK_SIZE = 2000


def parse_pdf(file_path: str) -> list[str]:
    """Extract text chunks from a PDF book."""
    reader = pypdf.PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text() or ""
        full_text += text + "\n"

    return _split_chunks(full_text)


def _split_chunks(text: str) -> list[str]:
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            # Break at sentence boundary
            boundary = text.rfind(". ", start, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if len(c) > 100]
