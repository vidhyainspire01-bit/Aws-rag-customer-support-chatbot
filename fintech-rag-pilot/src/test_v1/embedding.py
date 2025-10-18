# src/embeddings.py
import sys
from pathlib import Path
import json
from datetime import datetime, timezone
import numpy as np
from sentence_transformers import SentenceTransformer

import chromadb

# === Config ===
MODEL_NAME = "all-MiniLM-L6-v2"
PERSIST_DIR = "chromadb_store"
COLLECTION_NAME = "werize_docs"
BATCH_SIZE = 128

# === Paths ===
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PERSIST_PATH = ROOT_DIR / PERSIST_DIR

def build_chroma(docs, persist_directory=PERSIST_PATH, model_name=MODEL_NAME):
    """Build and persist Chroma vector index using chromadb.PersistentClient (v1.2+)."""
    persist_directory.mkdir(parents=True, exist_ok=True)

    # Use PersistentClient so index is stored under persist_directory
    client = chromadb.PersistentClient(path=str(persist_directory))

    # Delete existing collection (dev-friendly) and create fresh
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"[Init] Collection '{COLLECTION_NAME}' ready at {persist_directory}")

    # Prepare encoder
    model = SentenceTransformer(model_name)

    texts = [d["text"] for d in docs]
    ids = [d["chunk_id"] for d in docs]
    metadatas = [
        {
            "doc_id": d.get("doc_id"),
            "file_type": d.get("file_type"),
            "source": d.get("source"),
        }
        for d in docs
    ]

    # Batch encode
    embeddings_batches = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        emb = model.encode(batch_texts, show_progress_bar=True, convert_to_numpy=True)
        embeddings_batches.append(emb)

    embeddings = np.vstack(embeddings_batches) if embeddings_batches else np.zeros((0, model.get_sentence_embedding_dimension()))

    # Add vectors
    collection.add(documents=texts, embeddings=embeddings.tolist(), ids=ids, metadatas=metadatas)

    # Persist to disk (PersistentClient persists automatically but call persist if available)
    try:
        client.persist()
    except Exception:
        pass

    print(f"✅ Indexed {len(ids)} chunks into Chroma (collection='{COLLECTION_NAME}') at {persist_directory}")

    # Save manifest
    meta = {
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "model_name": model_name,
        "num_vectors": len(ids),
        "collection": COLLECTION_NAME
    }
    with open(persist_directory / "index_manifest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[Manifest] Saved index metadata → {persist_directory / 'index_manifest.json'}")


if __name__ == "__main__":
    from ingest import ingest_folder

    docs = ingest_folder(str(DATA_DIR))
    if not docs:
        print("❌ No docs found to index. Make sure data/ contains your files and ingest runs correctly.")
        sys.exit(1)

    build_chroma(docs)
