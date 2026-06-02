"""
Utility functions for DataMind application.
"""

import os
import json
import re
from typing import List, Optional
from pathlib import Path

# Common English stopwords list to refine exact-keyword matching in Hybrid Search
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have",
    "havent", "having", "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him",
    "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt",
    "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some",
    "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there",
    "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom",
    "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve",
    "your", "yours", "yourself", "yourselves"
}


def is_valid_file_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """Check if file has allowed extension."""
    if allowed_extensions is None:
        from datamind.config import settings
        allowed_extensions = settings.ALLOWED_EXTENSIONS
    
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def clean_text_content(text: str) -> str:
    """Clean and normalize raw text extracted from files."""
    if not text:
        return ""
    # Normalize whitespace, strip control characters, and clean consecutive empty lines
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_text_from_file(filepath: str) -> Optional[str]:
    """
    Extract and clean text from various file types.
    Supports: txt, md, pdf, docx, json, csv
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext in [".txt", ".md"]:
            with open(filepath, "r", encoding="utf-8") as f:
                return clean_text_content(f.read())
        
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return clean_text_content(json.dumps(data, indent=2))
        
        elif ext == ".csv":
            import csv
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = [" | ".join(row) for row in reader]
                return clean_text_content("\n".join(rows))
        
        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                with open(filepath, "rb") as f:
                    reader = PdfReader(f)
                    text_parts = []
                    for page in reader.pages:
                        text_parts.append(page.extract_text() or "")
                    return clean_text_content("\n".join(text_parts))
            except ImportError:
                return None
        
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(filepath)
                text_parts = [p.text for p in doc.paragraphs]
                return clean_text_content("\n".join(text_parts))
            except ImportError:
                return None
        
        return None
    
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks strictly on sentence boundaries.
    Prevents sentences from being cut in half, maximizing semantic chunk quality.
    """
    # Clean text content first
    text = clean_text_content(text)
    if not text:
        return []
        
    # Split text on sentence endings (. ! ?) followed by whitespace
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_len = len(sentence)
        
        # If a single sentence exceeds the chunk_size, split it into character sliding windows
        if sentence_len > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            start = 0
            while start < sentence_len:
                end = min(start + chunk_size, sentence_len)
                chunks.append(sentence[start:end])
                start = end - overlap
                if start >= sentence_len:
                    break
            continue
            
        # Accumulate sentences if they fit under chunk_size
        if current_length + sentence_len + 1 <= chunk_size:
            current_chunk.append(sentence)
            current_length += sentence_len + 1
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # Form overlapping sentences for context continuity
            overlap_chunk = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) + 1 <= overlap:
                    overlap_chunk.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
                    
            current_chunk = overlap_chunk + [sentence]
            current_length = overlap_len + sentence_len + 1
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks


def get_file_size_mb(filepath: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
