# src/llm_ping.py
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()  # loads .env in project root

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in environment. Put it in a .env file at project root:")
    print("OPENAI_API_KEY=sk-....")
    raise SystemExit(1)

# import new OpenAI client
try:
    from openai import OpenAI
except Exception as e:
    print("❌ openai package not found or failed to import:", e)
    print("-> Install with: pip install --upgrade openai")
    raise

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI client created")
except Exception as e:
    print("❌ Failed to create OpenAI client:", e)
    raise SystemExit(1)

# Short test question + evidence + judge prompt (minimal)
question = "What is the due date on invoice INV-2025-0815?"
evidence = "=== invoice_techsuppliers_20250815.txt ===\nInvoice No: INV-2025-0815\nDue Date: 2025-09-14\n"
answer = "The due date for invoice INV-2025-0815 is 2025-09-14."

judge_prompt = f"""
You are a rigorous AI evaluator that reviews whether an AI assistant's answer
is grounded in the retrieved evidence.

You will be given:
1) QUESTION
2) RETRIEVED EVIDENCE
3) ANSWER

Task:
- Check if the ANSWER is fully supported by the RETRIEVED EVIDENCE.
- Output ONLY strict JSON exactly with keys:
  {{ "decision": "SUPPORTED" or "NOT_SUPPORTED", "score": 0-100, "reason": "one-sentence" }}

QUESTION:
{question}

RETRIEVED EVIDENCE:
{evidence}

ANSWER:
{answer}

Respond ONLY in JSON, nothing else.
"""

# Call the chat completions API using the new client
try:
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a precise fact-checker."},
                  {"role": "user", "content": judge_prompt}],
        max_tokens=150,
        temperature=0.0
    )
except Exception as e:
    print("❌ OpenAI API call failed:", e)
    print("- Check network, key validity, and that the key has not been revoked.")
    raise SystemExit(1)

# Extract text safely
try:
    text = resp.choices[0].message.content.strip()
except Exception:
    text = str(resp)

print("\n=== MODEL RAW OUTPUT ===\n")
print(text)
print("\n=== PARSE ATTEMPT ===\n")

# Try to extract JSON blob
m = re.search(r"\{.*\}", text, re.DOTALL)
if m:
    try:
        parsed = json.loads(m.group(0))
        print("✅ Parsed JSON from model:")
        print(json.dumps(parsed, indent=2))
    except Exception as e:
        print("⚠️ Found JSON-like text but parsing failed:", e)
        print("Raw text:")
        print(text)
else:
    print("⚠️ No JSON object found in model output. Raw text below:")
    print(text)

# Final health summary
print("\n=== HEALTH SUMMARY ===")
print("OPENAI_API_KEY present:", bool(OPENAI_API_KEY))
print("Model response length:", len(text))
