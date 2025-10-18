import streamlit as st
from datetime import datetime
import os
import textwrap

# import your existing RAG entrypoint
# make sure src/ is current working dir when running streamlit from project root
from rag_agent import answer_query

st.set_page_config(page_title="Fintech — RAG Chat", layout="centered")

st.title("Fintech — Knowledge Triage Chat (Pilot)")
st.markdown(
    "Ask a question about the indexed documents and get a grounded answer from the local RAG agent."
)

# small sidebar info
with st.sidebar:
    st.header("Quick info")
    st.write("- Local RAG agent using your Chroma index")
    st.write("- If OpenAI key configured, answers will be polished by the LLM")
    st.write("- Sensitive inputs are refused by the agent (RED)")

# Input area
st.subheader("Ask a question")
question = st.text_area("Type your question here", height=120, placeholder="e.g. What is the due date on INV-2025-0815?")

col1, col2 = st.columns([1, 1])
with col1:
    topk = st.number_input("Top-K retrieval", min_value=1, max_value=10, value=4, step=1)
with col2:
    submit = st.button("Ask")

# log area
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "chat_log.jsonl")

def log_interaction(q, answer, retrieved_docs):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "question": q,
        "answer_snippet": (answer[:800] + "...") if len(answer) > 800 else answer,
        "retrieved_docs": retrieved_docs
    }
    # append as JSONL
    import json
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

if submit and question.strip():
    with st.spinner("Thinking... (retrieving + generating)"):
        try:
            resp = answer_query(question.strip(), k=int(topk))
        except Exception as e:
            st.error("Agent call failed: " + str(e))
            resp = None

    if resp is None:
        st.warning("No response from the agent.")
    else:
        # If your answer_query returns "I could not call a generator..." or similar, just display raw
        st.subheader("Answer")
        st.markdown(textwrap.fill(resp, width=120))

        # Try to extract retrieved docs list if agent appends '[Retrieved docs: ...]'
        docs_list = []
        if isinstance(resp, str) and "[Retrieved docs:" in resp:
            # simple parse: last bracketed part
            try:
                tail = resp.split("[Retrieved docs:")[-1].strip()
                tail = tail.rstrip("]").strip()
                docs_list = [d.strip() for d in tail.split(",") if d.strip()]
            except Exception:
                docs_list = []

        if docs_list:
            st.subheader("Retrieved documents")
            for d in docs_list:
                st.write("- " + d)

        # show button to reveal raw evidence (fallback will show evidence text in response if no LLM)
        if st.checkbox("Show raw retrieved evidence (if present in response)"):
            st.subheader("Raw retrieved evidence (excerpt)")
            # we already show full resp; but display again in code block for readability
            st.code(resp, language="text")

        # log interaction (non-sensitive logging)
        try:
            log_interaction(question.strip(), resp, docs_list)
        except Exception:
            pass

# small footer: show last few logs
st.markdown("---")
st.subheader("Recent queries (local log)")
try:
    import json
    if os.path.exists(LOG_FILE):
        lines = open(LOG_FILE, "r", encoding="utf-8").read().strip().splitlines()[-6:]
        for ln in reversed(lines):
            try:
                j = json.loads(ln)
                st.write(f"- `{j['timestamp']}`  —  {j['question'][:120]} → {j['answer_snippet'][:200]}")
            except Exception:
                st.write("- " + ln[:200])
    else:
        st.write("No queries yet.")
except Exception as e:
    st.write("Log read failed:", e)
