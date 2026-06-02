"""
Personal RAG Assistant - Gradio Interface Bridge
Integrates the stunning and robust DataMind RAG services directly into the 
Hugging Face Spaces Gradio interface.
"""

import os
import sys
from typing import List
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

# Ensure current directory is in PYTHONPATH to resolve datamind modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load settings and services
from datamind.config import settings
from datamind.storage import VectorStore
from datamind.services import DocumentService
from datamind.utils import get_logger

load_dotenv()
logger = get_logger("gradio_bridge")

# Initialize central vector store and document service
settings.ensure_directories()
vector_store = VectorStore(settings.DB_PATH)
document_service = DocumentService(vector_store)


def ingest_files(files: List) -> str:
    """Ingest uploaded files, segment them, generate vectors, and store them."""
    if not files:
        return "No files provided."
    
    stored = []
    for f in files:
        # Handle different Gradio file representations (file objects or path strings)
        filepath = f if isinstance(f, str) else getattr(f, "name", None)
        if not filepath or not os.path.exists(filepath):
            continue
            
        try:
            filename = Path(filepath).name
            doc_id = document_service.ingest_file(filepath)
            stored.append(filename)
        except Exception as e:
            logger.error(f"Failed to ingest file {filepath} via Gradio: {e}")
            continue
            
    if stored:
        # Load stats for reporting
        try:
            stats = document_service.get_stats()
            total_docs = stats.get("total_documents", len(stored))
            total_chunks = stats.get("total_embeddings", 0)
            return f"✓ Indexed {len(stored)} document(s) successfully! Total documents in library: {total_docs} ({total_chunks} text segments vectorized)."
        except Exception:
            return f"✓ Indexed {len(stored)} document(s): {', '.join(stored)}"
            
    return "✗ Failed to extract or index text from uploaded files."


def answer(query: str, top_k: int = 5) -> str:
    """Perform hybrid vector-keyword search and synthesize response using Llama 3 / GPT."""
    if not query or not query.strip():
        return "Please enter a valid question."
        
    try:
        logger.info(f"Gradio bridge processing query: {query}")
        
        # Execute hybrid vector search and LLM synthesis
        result = document_service.get_answer(query, top_k=top_k)
        
        answer_text = result.get("answer")
        retrieved_segments = result.get("retrieved", [])
        
        if not answer_text:
            return "Could not generate answer. No LLM response available."
            
        # Format the response with clear, professional headers and citations
        formatted_response = answer_text + "\n\n"
        
        # Add citations section at the bottom for completeness
        if retrieved_segments:
            formatted_response += "\n---\n**📚 Citations & Source Contexts:**\n"
            for idx, segment in enumerate(retrieved_segments):
                score_pct = f"{segment.similarity_score * 100:.1f}"
                chunk_index = segment.metadata.get("chunk_index", 0)
                formatted_response += (
                    f"- **[{idx + 1}] {segment.filename}** (Segment {chunk_index} | Match Relevance: {score_pct}%)\n"
                    f"  *\"...{segment.excerpt.strip()}...\"*\n"
                )
                
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error generating answer in Gradio: {e}")
        return f"An error occurred while synthesizing your answer: {str(e)}"


# Define Gradio Theme & Interface
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="violet",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_950",
    block_background_fill="*neutral_900",
    block_label_text_color="*neutral_200",
    block_title_text_color="*neutral_100",
    body_text_color="*neutral_100",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_500",
    button_primary_text_color="white",
)

with gr.Blocks(theme=theme, title="DataMind Personal RAG Assistant") as demo:
    gr.HTML("""
        <div style="text-align: center; margin-bottom: 2rem; border-bottom: 1px solid #374151; padding-bottom: 1.5rem;">
            <h1 style="font-size: 2.25rem; font-weight: 800; color: white; margin-bottom: 0.5rem; font-family: sans-serif;">🧠 DataMind Personal RAG</h1>
            <p style="color: #9ca3af; font-size: 1.05rem;">Enterprise-grade semantic segment chunking and AI response synthesis platform.</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML("""
                <div style="background-color: #1f2937; padding: 1rem; border-radius: 8px; border: 1px solid #374151; margin-bottom: 1rem;">
                    <h3 style="color: white; font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">Step 1: Upload Documents</h3>
                    <p style="color: #9ca3af; font-size: 0.85rem;">Upload PDFs, Resumes, DOCX, or text files. The system will slice them into semantic overlaps and generate cached vector embeddings.</p>
                </div>
            """)
            files = gr.File(file_count="multiple", label="Upload files (pdf, docx, txt, md, json, csv)")
            ingest_btn = gr.Button("Ingest & Vectorize", variant="primary")
            status = gr.Textbox(label="Ingest status", placeholder="Status outputs will appear here...", interactive=False)
            
        with gr.Column(scale=2):
            gr.HTML("""
                <div style="background-color: #1f2937; padding: 1rem; border-radius: 8px; border: 1px solid #374151; margin-bottom: 1rem;">
                    <h3 style="color: white; font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">Step 2: Ask Your Knowledge Base</h3>
                    <p style="color: #9ca3af; font-size: 0.85rem;">Ask any questions. The system will retrieve dense relevant segments using hybrid semantic-keyword searches and synthesize answers using active LLMs.</p>
                </div>
            """)
            query = gr.Textbox(label="Your Question", placeholder="e.g., What is the professional experience of Ravi Kumar?", lines=2)
            
            with gr.Accordion("Advanced Vector settings", open=False):
                top_k = gr.Slider(minimum=1, maximum=15, step=1, value=5, label="top_k (Number of retrieved context segments)")
                
            ask_btn = gr.Button("Synthesize Answer", variant="primary")
            answer_box = gr.Markdown(label="Answer & Citations")

    # Wire event handlers
    ingest_btn.click(fn=ingest_files, inputs=[files], outputs=[status])
    ask_btn.click(fn=answer, inputs=[query, top_k], outputs=[answer_box])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))
