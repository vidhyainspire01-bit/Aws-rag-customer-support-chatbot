# src/rag_agent.py
import os
import textwrap
from dotenv import load_dotenv
from vectorstore import retrieve

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

def answer_query(question, k=4):
    """
    Main RAG entrypoint:
      1) retrieve top-k chunks,
      2) compose prompt with evidence,
      3) call LLM if available,
      4) fall back to safe listing if not.
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
            return f"{ans}\n\n[Retrieved docs: {docs_list}]"
        except Exception as e:
            # Log and return fallback evidence
            print("[WARN] OpenAI call failed:", e)
            return simple_fallback_answer(retrieved, question)
    else:
        return simple_fallback_answer(retrieved, question)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", type=str, required=True, help="Question to ask the RAG agent")
    parser.add_argument("-k", "--topk", type=int, default=4, help="Number of retrieved chunks to use")
    args = parser.parse_args()

    out = answer_query(args.question, k=args.topk)
    print("\n" + out + "\n")


















# src/rag_agent.py
import os
import re
import textwrap
from dotenv import load_dotenv
from vectorstore import retrieve

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
# Sensitive-input safety gate
# ---------------------------
def is_sensitive_query(query: str) -> bool:
    """
    Detects potentially sensitive inputs like credit card numbers, PAN/account numbers, CVV, etc.
    Returns True if the query appears to contain sensitive data or asks to handle it.
    """
    if not query:
        return False
    q = query.lower()

    # Keywords that indicate sensitive intent
    sensitive_keywords = [
        "credit card", "debit card", "card number", "cvv", "cvc",
        "pan number", "account number", "account no", "ifsc", "ssn",
        "passport", "aadhaar", "upi", "pin number", "atm pin", "bank account",
        "card expiry", "card details"
    ]
    if any(kw in q for kw in sensitive_keywords):
        return True

    # Detect 12-19 digit continuous sequences (common length for card numbers)
    if re.search(r"\b\d{12,19}\b", query.replace(" ", "")):
        return True

    # Detect patterns like 4-4-4-4 groups for card numbers with spaces/dashes
    if re.search(r"(?:\d{4}[-\s]?){3}\d{4}", query):
        return True

    # Detect CVV-like 3 or 4 digit sequences together with word 'cvv' or 'cvc'
    if re.search(r"(cvv|cvc)\D*\d{3,4}", q):
        return True

    return False

def sensitive_refusal_message():
    return (
        "⚠️ I’m sorry — I can’t process or store sensitive information such as credit/debit card numbers, "
        "CVV, PAN, bank account numbers, or PINs. For security and privacy, please contact your bank through "
        "their official secure channels or redact the sensitive information before asking."
    )
# ---------------------------
# End safety gate
# ---------------------------

def answer_query(question, k=4):
    """
    Main RAG entrypoint:
      1) safety-check the question,
      2) retrieve top-k chunks,
      3) compose prompt with evidence,
      4) call LLM if available,
      5) fall back to safe listing if not.
    """

    # 1) Safety gate: refuse to handle sensitive inputs
    if is_sensitive_query(question):
        return sensitive_refusal_message()

    # 2) Retrieval
    retrieved = retrieve(question, n_results=k)
    if not retrieved or len(retrieved) == 0:
        return "No documents found in the index."

    # 3) Compose evidence and prompt
    evidence_block = compose_evidence(retrieved)
    prompt = ANSWER_TEMPLATE.format(question=question, evidence=evidence_block)

    # 4) LLM call (if available)
    if USE_OPENAI and client is not None:
        try:
            ans = call_openai_chat(SYSTEM_PROMPT, prompt, max_tokens=512, temperature=0.0)
            docs_list = ", ".join([r.get("metadata", {}).get("doc_id", r.get("id")) for r in retrieved])
            return f"{ans}\n\n[Retrieved docs: {docs_list}]"
        except Exception as e:
            # Log and return fallback evidence
            print("[WARN] OpenAI call failed:", e)
            return simple_fallback_answer(retrieved, question)
    else:
        return simple_fallback_answer(retrieved, question)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", type=str, required=True, help="Question to ask the RAG agent")
    parser.add_argument("-k", "--topk", type=int, default=4, help="Number of retrieved chunks to use")
    args = parser.parse_args()

    out = answer_query(args.question, k=args.topk)
    print("\n" + out + "\n")
