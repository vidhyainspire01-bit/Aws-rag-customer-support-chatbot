# src/rag_agent.py
import os
import re
import textwrap
import json
import hashlib
from dotenv import load_dotenv
from vectorstore import retrieve
from datetime import datetime

# classifier must be implemented in src/data_classifier.py
# it should export: classify_query(query: str) -> {"label":..., "confidence":..., "reason":...}
from data_classifier import classify_query

load_dotenv()

# Read OpenAI key from environment (DO NOT hardcode keys)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
USE_OPENAI = bool(OPENAI_API_KEY)
client = None

if USE_OPENAI:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print("[WARN] Failed to create OpenAI client:", e)
        USE_OPENAI = False
        client = None

SYSTEM_PROMPT = (
    "You are a domain-expert assistant. Use ONLY the provided evidence chunks to answer the user's question. "
    "Cite which document the answer came from where appropriate. "
    "If the answer is not present in the evidence, say: \"I don't have enough information in the knowledge base to answer that.\""
)

ANSWER_TEMPLATE = """
Question:
{question}

Retrieved Evidence:
{evidence}

Answer:
"""

def compose_evidence(retrieved):
    parts = []
    for r in retrieved:
        meta = r.get("metadata", {}) or {}
        doc_id = meta.get("doc_id", r.get("id"))
        parts.append(f"=== {doc_id} ===\n{r.get('text','').strip()}\n")
    return "\n".join(parts)

def call_openai_chat(system_prompt, user_prompt, max_tokens=512, temperature=0.0):
    """
    Use OpenAI v1 client to create a chat completion.
    Raises exceptions up to caller to handle.
    """
    if client is None:
        raise RuntimeError("OpenAI client not available")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # new client API
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )

    # extract content
    try:
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback to string if shape differs
        return str(resp)

def simple_fallback_answer(retrieved, question):
    evidence = compose_evidence(retrieved)
    excerpt = evidence[:4000]  # keep it reasonably short
    return (
        "I could not call a generator (no OpenAI key or API failed); here are the top retrieved evidence chunks:\n\n"
        f"{excerpt}\n\n"
        "If you want a polished answer, set the OPENAI_API_KEY environment variable and re-run."
    )

# ---------------------------
# Human review / logging helper
# ---------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
HUMAN_REVIEW_LOG = os.path.join(LOG_DIR, "human_review.log")

def _hash_query(query: str) -> str:
    """Return a SHA256 hex digest of the query (used for redacted logging)."""
    h = hashlib.sha256()
    h.update(query.encode("utf-8"))
    return h.hexdigest()

def create_human_review_ticket(query: str, label: str, meta: dict):
    """
    Minimal human-review stub:
    - Writes a redacted entry to logs/human_review.log
    - Does NOT store raw user query (only the hash + metadata).
    """
    try:
        entry = {
            "time": datetime.utcnow().isoformat() + "Z",
            "query_hash": _hash_query(query),
            "label": label,
            "confidence": meta.get("confidence"),
            "reason": meta.get("reason")
        }
        with open(HUMAN_REVIEW_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        # placeholder for real escalation (e.g., send to Slack, create ticket, etc.)
        print(f"[INFO] Human review ticket created (query_hash={entry['query_hash']})")
    except Exception as e:
        print("[WARN] Failed to create human review ticket:", e)

# ---------------------------
# Routing helpers
# ---------------------------
def handle_rag_pipeline(question, k=4, internal_only=False):
    """
    Run retrieval + optional LLM generation.
    If internal_only=True, you should route to an internal collection only.
    Current retrieve() implementation uses the default collection; if you have
    separate collections implement selection inside vectorstore.retrieve.
    """
    retrieved = retrieve(question, n_results=k)
    if not retrieved or len(retrieved) == 0:
        return "No documents found in the index."

    evidence_block = compose_evidence(retrieved)
    prompt = ANSWER_TEMPLATE.format(question=question, evidence=evidence_block)

    if USE_OPENAI and client is not None:
        try:
            ans = call_openai_chat(SYSTEM_PROMPT, prompt, max_tokens=512, temperature=0.0)
            docs_list = ", ".join([r.get("metadata", {}).get("doc_id", r.get("id")) for r in retrieved])
            tag = "[INTERNAL]" if internal_only else "[PUBLIC]"
            return f"{ans}\n\n{tag} [Retrieved docs: {docs_list}]"
        except Exception as e:
            print("[WARN] OpenAI call failed:", e)
            return simple_fallback_answer(retrieved, question)
    else:
        fallback = simple_fallback_answer(retrieved, question)
        if internal_only:
            return fallback + "\n\n[INTERNAL DATA]"
        return fallback

def answer_query_normal(question, k=4):
    """Default public RAG path"""
    return handle_rag_pipeline(question, k=k, internal_only=False)

def private_rag_answer(question, k=4):
    """
    Internal-only RAG path. Right now it calls the same retrieve() function.
    If you want strict separation, implement separate vectorstore collections and
    update vectorstore.retrieve to accept a 'collection' parameter.
    """
    return handle_rag_pipeline(question, k=k, internal_only=True)

# ---------------------------
# Main entrypoint with classifier injection
# ---------------------------
def answer_query(question, k=4):
    """
    Main RAG entrypoint:
      1) classify the query by data sensitivity (RED / YELLOW / GREEN),
      2) route accordingly,
      3) retrieve and generate answers for allowed categories.
    """

    # Run classifier first
    try:
        meta = classify_query(question)
    except Exception as e:
        print("[WARN] classify_query failed, defaulting to YELLOW:", e)
        meta = {"label": "YELLOW", "confidence": 0.5, "reason": "classifier error"}

    label = meta.get("label", "YELLOW")
    conf = float(meta.get("confidence", 0.0))
    reason = meta.get("reason", "")

    print(f"[INFO] Query classified as {label} (confidence={conf:.2f}) — {reason}")

    # Handle RED: refuse
    if label == "RED":
        # conservative refusal for RED data
        return (
            "🔴 This query appears to contain sensitive or personal financial data. "
            "For your security, I cannot process or store such information. "
            "Please contact authorized support through a secure channel."
        )

    # Handle YELLOW: internal / business-sensitive
    if label == "YELLOW":
        # create human review ticket if confidence is low
        if conf < 0.6:
            try:
                create_human_review_ticket(question, label, meta)
            except Exception as e:
                print("[WARN] Failed to schedule human review:", e)
        # route to internal RAG pipeline (implementation note above)
        resp = private_rag_answer(question, k=k)
        return resp + f"\n\n[⚠️ INTERNAL DATA — label: {label}, confidence={conf:.2f}]"

    # Handle GREEN: public
    resp = answer_query_normal(question, k=k)
    return resp + f"\n\n[🟢 PUBLIC DATA — label: {label}, confidence={conf:.2f}]"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", type=str, required=True, help="Question to ask the RAG agent")
    parser.add_argument("-k", "--topk", type=int, default=4, help="Number of retrieved chunks to use")
    args = parser.parse_args()

    out = answer_query(args.question, k=args.topk)
    print("\n" + out + "\n")
