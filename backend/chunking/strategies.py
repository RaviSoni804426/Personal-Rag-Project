import re
from typing import List, Dict, Any, Tuple, Callable

class RecursiveCharacterChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []
        
        chunks = []
        # Recursive text splitter logic
        def split_text(txt: str, separators: List[str]) -> List[str]:
            if len(txt) <= self.chunk_size:
                return [txt]
            
            if not separators:
                # Direct force splits if no delimiters remain
                return [txt[i:i + self.chunk_size] for i in range(0, len(txt), self.chunk_size - self.chunk_overlap)]
            
            separator = separators[0]
            splits = txt.split(separator)
            
            # Reconstruct splits with separators
            parts = []
            for i, split in enumerate(splits):
                if i < len(splits) - 1:
                    parts.append(split + separator)
                else:
                    parts.append(split)
            
            # Combine parts that fit within chunk_size
            merged = []
            current_chunk = ""
            
            for part in parts:
                if len(part) > self.chunk_size:
                    # If a single part exceeds chunk size, split it recursively using next level separators
                    if current_chunk:
                        merged.append(current_chunk)
                        current_chunk = ""
                    merged.extend(split_text(part, separators[1:]))
                elif len(current_chunk) + len(part) <= self.chunk_size:
                    current_chunk += part
                else:
                    if current_chunk:
                        merged.append(current_chunk)
                    # Initialize next chunk, keeping overlap text if possible
                    overlap_source = current_chunk[-self.chunk_overlap:] if len(current_chunk) >= self.chunk_overlap else current_chunk
                    current_chunk = overlap_source + part
            
            if current_chunk:
                merged.append(current_chunk)
                
            return merged

        raw_splits = split_text(text, self.separators)
        # Final clean filter to remove empty chunks
        return [c.strip() for c in raw_splits if c.strip()]


class ParentChildChunker:
    def __init__(self, parent_size: int = 1500, child_size: int = 400, overlap: int = 50):
        self.parent_chunker = RecursiveCharacterChunker(chunk_size=parent_size, chunk_overlap=overlap * 2)
        self.child_chunker = RecursiveCharacterChunker(chunk_size=child_size, chunk_overlap=overlap)

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Returns a list of dictionaries detailing parent-child chunk objects:
        [
          {
            "parent_index": int,
            "parent_text": str,
            "child_index": int,
            "child_text": str
          }
        ]
        """
        parent_chunks = self.parent_chunker.chunk(text)
        results = []
        child_global_index = 0
        
        for parent_idx, parent_text in enumerate(parent_chunks):
            child_chunks = self.child_chunker.chunk(parent_text)
            for child_idx, child_text in enumerate(child_chunks):
                results.append({
                    "parent_index": parent_idx,
                    "parent_text": parent_text,
                    "child_index": child_global_index,
                    "child_text": child_text
                })
                child_global_index += 1
                
        return results


class SemanticSimilarityChunker:
    def __init__(self, max_chunk_size: int = 1200, similarity_threshold: float = 0.65):
        self.max_chunk_size = max_chunk_size
        self.similarity_threshold = similarity_threshold

    def split_sentences(self, text: str) -> List[str]:
        # Basic split on sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk(self, text: str, embedding_fn: Callable[[List[str]], List[List[float]]]) -> List[str]:
        """
        Chunk text by splitting at points where sentence semantic embedding similarity drops.
        Falls back to recursive character chunking if embedding_fn is not operational.
        """
        sentences = self.split_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return sentences

        try:
            # Generate embeddings for all sentences
            embeddings = embedding_fn(sentences)
            
            # Calculate cosine similarities between adjacent sentences
            import numpy as np
            similarities = []
            for i in range(len(embeddings) - 1):
                vec1 = np.array(embeddings[i])
                vec2 = np.array(embeddings[i+1])
                
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                
                if norm1 == 0 or norm2 == 0:
                    similarity = 0.0
                else:
                    similarity = np.dot(vec1, vec2) / (norm1 * norm2)
                similarities.append(similarity)
            
            chunks = []
            current_chunk_sentences = [sentences[0]]
            current_len = len(sentences[0])
            
            for i, similarity in enumerate(similarities):
                next_sentence = sentences[i + 1]
                # Break rules: similarity drop or size limit exceeded
                if similarity < self.similarity_threshold or current_len + len(next_sentence) > self.max_chunk_size:
                    chunks.append(" ".join(current_chunk_sentences))
                    current_chunk_sentences = [next_sentence]
                    current_len = len(next_sentence)
                else:
                    current_chunk_sentences.append(next_sentence)
                    current_len += len(next_sentence) + 1  # Add space
                    
            if current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))
                
            return chunks
        except Exception:
            # High-robustness fallback: recursive chunking
            fallback = RecursiveCharacterChunker(chunk_size=self.max_chunk_size, chunk_overlap=150)
            return fallback.chunk(text)


def perform_chunking(
    text: str, 
    strategy: str = "recursive", 
    embedding_fn: Callable[[List[str]], List[List[float]]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Unified manager executing selected chunking configurations.
    Returns:
        List[Dict[str, Any]]: List of dictionary details:
        [
           {
              "chunk_index": int,
              "text": str,
              "parent_text": Optional[str],
              "metadata": Dict[str, Any]
           }
        ]
    """
    strategy = strategy.lower().strip()
    
    if strategy == "semantic" and embedding_fn is not None:
        chunker = SemanticSimilarityChunker(max_chunk_size=chunk_size)
        chunks = chunker.chunk(text, embedding_fn)
        return [
            {
                "chunk_index": idx,
                "text": chunk_text,
                "parent_text": None,
                "metadata": {"strategy": "semantic"}
            }
            for idx, chunk_text in enumerate(chunks)
        ]
        
    elif strategy == "parent-child":
        chunker = ParentChildChunker(parent_size=chunk_size * 2, child_size=chunk_size, overlap=chunk_overlap)
        relationships = chunker.chunk(text)
        return [
            {
                "chunk_index": item["child_index"],
                "text": item["child_text"],
                "parent_text": item["parent_text"],
                "metadata": {
                    "strategy": "parent-child",
                    "parent_index": item["parent_index"]
                }
            }
            for item in relationships
        ]
        
    else:  # "recursive" default
        chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk(text)
        return [
            {
                "chunk_index": idx,
                "text": chunk_text,
                "parent_text": None,
                "metadata": {"strategy": "recursive"}
            }
            for idx, chunk_text in enumerate(chunks)
        ]
