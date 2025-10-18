# src/ingest.py
import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import json


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

def pdf_to_text(path):
    txt = []
    reader = PdfReader(path)
    for p in reader.pages:
        page_text = p.extract_text() or ""
        if page_text:
            txt.append(page_text)
    return "\n".join(txt)

def ingest_folder(folder='data', chunk_size=800, chunk_overlap=200):
    docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    for p in Path(folder).rglob('*.*'):  # recursive search
        if p.suffix.lower() == '.pdf':
            text = pdf_to_text(p)
        else:
            try:
                text = p.read_text(encoding='utf-8')
            except Exception as e:
                print(f"[ERROR] Cannot read {p}: {e}")
                continue

        if not text.strip():
            print(f"[WARN] Empty text from {p}")
            continue

        chunks = splitter.split_text(text)
        for i, c in enumerate(chunks):
            docs.append({
                'doc_id': p.name,
                'chunk_id': f"{p.name}_{i}",
                'file_type': p.suffix.lower().replace('.', ''),
                'source': "external" if "external_pdfs" in str(p.parent) else "internal",
                'text': c
            })

    print(f"Ingested {len(docs)} chunks from {folder}")
    return docs


if __name__ == "__main__":
    docs = ingest_folder(DATA_DIR)
    output_file = DATA_DIR / "chunks_preview.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(docs[:5], f, indent=2, ensure_ascii=False)
    print(f"Ingested {len(docs)} chunks. Sample saved to {output_file}")

