"""
Utility functions for DataMind application.
"""

import os
import json
from typing import List, Optional
from pathlib import Path


def is_valid_file_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """Check if file has allowed extension."""
    if allowed_extensions is None:
        from datamind.config import settings
        allowed_extensions = settings.ALLOWED_EXTENSIONS
    
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def extract_text_from_file(filepath: str) -> Optional[str]:
    """
    Extract text from various file types.
    Supports: txt, md, pdf, docx, json, csv
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext in [".txt", ".md"]:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        
        elif ext == ".csv":
            import csv
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = [" | ".join(row) for row in reader]
                return "\n".join(rows)
        
        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                import io
                with open(filepath, "rb") as f:
                    reader = PdfReader(f)
                    text_parts = []
                    for page in reader.pages:
                        text_parts.append(page.extract_text() or "")
                    return "\n".join(text_parts)
            except ImportError:
                return None
        
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(filepath)
                text_parts = [p.text for p in doc.paragraphs]
                return "\n".join(text_parts)
            except ImportError:
                return None
        
        return None
    
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks


def get_file_size_mb(filepath: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
