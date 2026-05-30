import argparse
import os
from rag_app.groq_client import embed_texts
from rag_app import storage
from dotenv import load_dotenv

load_dotenv()

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True, help="Directory with text files to ingest")
    p.add_argument("--db", default=os.getenv("DB_PATH", "./data/memories.db"))
    args = p.parse_args()

    storage.init_db(args.db)

    files = []
    for root, _, filenames in os.walk(args.dir):
        for fn in filenames:
            if fn.lower().endswith((".txt", ".md")):
                files.append(os.path.join(root, fn))

    if not files:
        print("No text files found in directory")
        return

    texts = [read_text_file(f) for f in files]
    embeddings = embed_texts(texts)

    for f, t, e in zip(files, texts, embeddings):
        storage.add_document(args.db, t, {"source": f}, e)
        print(f"Indexed {f}")

if __name__ == '__main__':
    main()
