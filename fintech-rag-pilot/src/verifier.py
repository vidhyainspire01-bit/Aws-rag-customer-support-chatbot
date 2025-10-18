# src/verifier.py
import re
import os
import json
from dotenv import load_dotenv
from vectorstore import retrieve

load_dotenv()

# OpenAI setup (new v1 client)
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

def tokenize(text):
    return re.findall(r"\w+", (text or "").lower())

def overlap_score(answer, retrieved):
    """
    Fraction of answer tokens that appear in the retrieved evidence text.
    """
    ans_tokens = tokenize(answer)
    if not ans_tokens:
        return 0.0
    evidence_text = " ".join([r.get("text", "").lower() for r in retrieved])
    found = sum(1 for t in ans_tokens if t in evidence_text)
    return found / len(ans_tokens)

def openai_judge(answer, retrieved, max_evidence_chars=2000, max_chunks=6):
    """
    Use OpenAI (new client) to judge whether the ANSWER is supported by the EVIDENCE.
    Returns a dict with parsed decision if possible.
    """
    if not USE_OPENAI or client is None:
        return {"decision": "NO_LLM", "reason": "No OPENAI_API_KEY set or OpenAI client unavailable."}

    # Prepare truncated evidence (top-k chunks)
    evidence_parts = []
    for r in retrieved[:max_chunks]:
        docid = r.get("metadata", {}).get("doc_id", r.get("id"))
        txt = (r.get("text") or "")[:max_evidence_chars]
        evidence_parts.append(f"=== {docid} ===\n{txt}")
    evidence_block = "\n\n".join(evidence_parts)

    # Strict JSON judge prompt
    judge_prompt = f"""
You are a rigorous AI evaluator that reviews whether an AI assistant's answer
is grounded in the retrieved evidence.

You will be given:
1) QUESTION
2) RETRIEVED EVIDENCE
3) ANSWER

Task:
- Check if the ANSWER is fully supported by the RETRIEVED EVIDENCE.
- Rate how well-supported it is (0–100).
- Respond ONLY with strict JSON and NOTHING else, using keys:
  {{ "decision": "SUPPORTED" or "NOT_SUPPORTED", "score": integer 0-100, "reason": "one-sentence explanation" }}

QUESTION:
{""}

RETRIEVED EVIDENCE:
{evidence_block}

ANSWER:
{answer}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a precise fact-checker. Use ONLY the provided evidence."},
                {"role": "user", "content": judge_prompt}
            ],
            max_tokens=250,
            temperature=0.0,
        )

        # Extract text safely (new client returns object-like response)
        try:
            text = resp.choices[0].message.content.strip()
        except Exception:
            text = str(resp)

        # Try to extract JSON object from model output
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                # normalize keys
                return {
                    "decision": parsed.get("decision"),
                    "score": parsed.get("score"),
                    "reason": parsed.get("reason"),
                    "raw": text
                }
            except Exception:
                return {"decision_raw": text}
        else:
            return {"decision_raw": text}

    except Exception as e:
        return {"decision": "ERROR", "reason": str(e)}

def verify_answer(question, answer, k=4):
    retrieved = retrieve(question, n_results=k)
    score = overlap_score(answer, retrieved)
    judge = None
    if USE_OPENAI and client is not None:
        judge = openai_judge(answer, retrieved)
    return {
        "overlap_score": score,
        "num_retrieved": len(retrieved),
        "retrieved_docs": [r.get("metadata", {}).get("doc_id", r.get("id")) for r in retrieved],
        "llm_judge": judge
    }

# quick CLI test
if __name__ == "__main__":
    q = input("Question: ")
    from rag_agent import answer_query
    ans = answer_query(q, k=4)
    print("\nANSWER:\n", ans)
    v = verify_answer(q, ans, k=4)
    print("\nVERIFICATION:\n", json.dumps(v, indent=2))
