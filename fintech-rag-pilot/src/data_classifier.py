# src/data_classifier.py
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------
# Load environment key
# ---------------------
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    raise EnvironmentError("❌ OPENAI_API_KEY not found in environment or .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------
# Rule-based detection patterns
# ---------------------
SENSITIVE_KEYWORDS = [
    r"\bcredit card\b", r"\bcard number\b", r"\bcvv\b", r"\bcvc\b",
    r"\bpan\b", r"\bpancard\b", r"\baadhaar\b", r"\baadhar\b",
    r"\bssn\b", r"\bpassport\b", r"\bbank account\b",
    r"\baccount number\b", r"\bpin\b", r"\batm\b", r"\bupi\b",
]

CARD_RE = re.compile(r"(?:\d{4}[-\s]?){3}\d{4}")   # 4-4-4-4 format
DIGIT_SEQ_RE = re.compile(r"\b\d{12,19}\b")         # 12–19 digit continuous numbers

BUSINESS_KEYWORDS = [
    r"\binvoice\b", r"\bloan\b", r"\bbalance\b", r"\baccount summary\b",
    r"\bpayment\b", r"\btransaction\b", r"\bsalary\b", r"\bpayslip\b",
    r"\bprofit\b", r"\brevenue\b", r"\bclient\b", r"\bemployee\b",
    r"\bconfidential\b", r"\binternal\b", r"\bstatement\b"
]

PUBLIC_KEYWORDS = [
    r"\bRBI\b", r"\bpolicy\b", r"\bguideline\b", r"\bannouncement\b",
    r"\bpublic\b", r"\bpress release\b", r"\bFAQ\b", r"\bterms and conditions\b"
]

# ---------------------
# Rule-based shortcut classifier
# ---------------------
def rule_based_label(query: str):
    q = query.lower()

    # 1) Sensitive RED
    for patt in SENSITIVE_KEYWORDS:
        if re.search(patt, q):
            return {"label": "RED", "confidence": 1.0, "reason": f"Matched sensitive keyword '{patt}'"}

    if CARD_RE.search(query) or DIGIT_SEQ_RE.search(re.sub(r"[\s-]", "", query)):
        return {"label": "RED", "confidence": 0.99, "reason": "Detected credit-card-like digit sequence"}

    # 2) Business / Internal (YELLOW)
    for patt in BUSINESS_KEYWORDS:
        if re.search(patt, q):
            return {"label": "YELLOW", "confidence": 0.8, "reason": f"Matched business-related keyword '{patt}'"}

    # 3) Public / Safe (GREEN)
    for patt in PUBLIC_KEYWORDS:
        if re.search(patt, q):
            return {"label": "GREEN", "confidence": 0.9, "reason": f"Matched public keyword '{patt}'"}

    # Default if nothing triggered
    return None

# ---------------------
# LLM classification fallback
# ---------------------
def llm_classify(query: str, model="gpt-3.5-turbo"):
    prompt = f"""
You are a data classification assistant. Classify the following query into one of three categories:

- RED → Sensitive personal or financial data (PAN, card, CVV, Aadhaar, passport, account number, etc.)
- YELLOW → Internal, confidential, or business-sensitive (employee, financial report, internal communication, non-public company info)
- GREEN → Public, non-sensitive, safe for general release.

Return JSON like:
{{ "label": "RED"|"YELLOW"|"GREEN", "confidence": 0–1, "reason": "short justification" }}

Query: "{query}"
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a deterministic, rule-following text classifier."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=150
    )

    text = resp.choices[0].message.content.strip()

    # Try extracting valid JSON
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            return {"label": "YELLOW", "confidence": 0.5, "reason": "Could not parse model JSON"}
    else:
        return {"label": "YELLOW", "confidence": 0.5, "reason": "No valid JSON returned"}

# ---------------------
# Unified classification entrypoint
# ---------------------
def classify_query(query: str):
    rule = rule_based_label(query)
    if rule:
        return rule

    result = llm_classify(query)
    label = result.get("label", "YELLOW")
    confidence = float(result.get("confidence", 0.5))
    reason = result.get("reason", "")
    confidence = max(0.0, min(1.0, confidence))
    return {"label": label, "confidence": confidence, "reason": reason}

# ---------------------
# Quick CLI test
# ---------------------
if __name__ == "__main__":
    print("🔍 Data Classification Self-Test\n")
    while True:
        q = input("Enter query (or 'exit'): ").strip()
        if q.lower() == "exit":
            break
        out = classify_query(q)
        print(json.dumps(out, indent=2))
        print()
