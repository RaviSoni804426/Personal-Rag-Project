import os
import uuid
import json
import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.database.models import Document, DocumentChunk
from backend.ingestion.loaders import get_loader
from backend.chunking.strategies import perform_chunking
from backend.embeddings.provider import EmbeddingProvider
from backend.database.vector_store import ChromaVectorStore

class DocumentService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.embedding_provider = EmbeddingProvider()
        self.vector_store = ChromaVectorStore()

    def list_documents(self) -> List[Document]:
        return self.db.query(Document).order_by(Document.created_at.desc()).all()

    def get_document(self, document_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def delete_document(self, document_id: str) -> bool:
        doc = self.get_document(document_id)
        if not doc:
            return False
            
        try:
            # 1. Delete from vector store
            self.vector_store.delete_document(document_id)
            
            # 2. Delete from relational database (cascades chunks)
            self.db.delete(doc)
            self.db.commit()
            
            # 3. Try to delete physical file if local
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except Exception:
                    pass
            return True
        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")
            self.db.rollback()
            return False

    def ingest_document(
        self, 
        file_path: str, 
        chunk_strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Document:
        """
        Extracts, chunks, embeds, and indexes a local file.
        """
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        document_id = str(uuid.uuid4())
        
        # 1. Initialize pending database entry
        doc_entry = Document(
            id=document_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            chunk_strategy=chunk_strategy,
            status="processing"
        )
        self.db.add(doc_entry)
        self.db.commit()
        
        try:
            # 2. Parse text and metadata using specialized loaders
            loader = get_loader(file_path)
            raw_text, metadata = loader.load()
            
            # 3. Create splits via selected chunker
            # Provide embedding helper in case semantic chunking is requested
            emb_helper = lambda texts: self.embedding_provider.embed_texts(texts)
            chunks_data = perform_chunking(
                raw_text, 
                strategy=chunk_strategy, 
                embedding_fn=emb_helper,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if not chunks_data:
                raise ValueError("No text chunks generated from document.")
                
            # 4. Generate batch vector embeddings
            chunk_texts = [c["text"] for c in chunks_data]
            embeddings = self.embedding_provider.embed_texts(chunk_texts)
            
            # 5. Populate and write relational database records
            chunk_records = []
            chroma_chunks = []
            
            for idx, item in enumerate(chunks_data):
                chunk_id = f"{document_id}_ch_{idx}"
                text_content = item["text"]
                
                # Check character token count estimation
                token_est = len(text_content) // 4
                
                chunk_meta = item["metadata"]
                chunk_meta["filename"] = filename
                
                # Relational chunk entry
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=idx,
                    text_content=text_content,
                    token_count=token_est,
                    parent_chunk_id=item.get("parent_text"), # For parent-child hierarchy support
                    metadata_json=json.dumps(chunk_meta)
                )
                chunk_records.append(db_chunk)
                
                # Vector data mapped standard
                chroma_chunks.append({
                    "id": chunk_id,
                    "text_content": text_content,
                    "chunk_index": idx,
                    "parent_chunk_id": item.get("parent_text") or "",
                    "filename": filename
                })
                
            self.db.add_all(chunk_records)
            
            # 6. Bulk load vectors to ChromaDB persistent collection
            self.vector_store.add_chunks(document_id, chroma_chunks, embeddings)
            
            # 7. Update document completion status
            doc_entry.chunks_count = len(chunk_records)
            doc_entry.status = "indexed"
            doc_entry.metadata_json = json.dumps(metadata)
            self.db.commit()
            
            return doc_entry
            
        except Exception as e:
            print(f"Failed to ingest document {filename}: {e}")
            doc_entry.status = "failed"
            doc_entry.metadata_json = json.dumps({"error": str(e)})
            self.db.commit()
            raise e
