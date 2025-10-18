import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Send, FileText, ShieldCheck } from "lucide-react";

// Tailwind + shadcn style assumptions. This component expects a backend endpoint POST /api/ask
// Request body: { question: string, topk?: number }
// Response body: { answer: string, retrieved_docs?: string[] }

export default function RagChatUI() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // {id, role: 'user'|'assistant'|'system', text, docs?}
  const [loading, setLoading] = useState(false);
  const [topk, setTopk] = useState(4);
  const [showEvidence, setShowEvidence] = useState(false);
  const messagesRef = useRef(null);

  useEffect(() => {
    // scroll on new message
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, loading]);

  function pushMessage(msg) {
    setMessages((m) => [...m, { id: Date.now() + Math.random(), ...msg }]);
  }

  async function handleSend(e) {
    e?.preventDefault();
    const q = question.trim();
    if (!q) return;
    pushMessage({ role: "user", text: q });
    setQuestion("");
    setLoading(true);

    try {
      // POST to backend
      const resp = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, topk }),
      });

      if (!resp.ok) throw new Error(`Server ${resp.status}`);
      const data = await resp.json();

      // backend expected: { answer, retrieved_docs }
      pushMessage({ role: "assistant", text: data.answer || data.answer_text || "(no answer)", docs: data.retrieved_docs || [] });
    } catch (err) {
      pushMessage({ role: "assistant", text: `Error: ${err.message}` });
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([]);
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-indigo-50 p-6">
      <div className="mx-auto max-w-4xl shadow-2xl rounded-2xl overflow-hidden bg-white">
        {/* Header */}
        <header className="flex items-center justify-between gap-4 p-6 bg-gradient-to-r from-indigo-600 to-violet-600 text-white">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-white/20 w-12 h-12 flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Werize — Knowledge Triage</h1>
              <p className="text-sm opacity-85">Grounded answers from your indexed documents</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-sm text-white/90">Top-K</div>
            <select
              value={topk}
              onChange={(e) => setTopk(Number(e.target.value))}
              className="rounded-md bg-white/10 px-2 py-1 text-white">
              {[2,3,4,5,6].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <button onClick={clearChat} className="ml-3 inline-flex items-center gap-2 rounded-md bg-white/20 px-3 py-1 text-sm hover:bg-white/30">
              Clear
            </button>
          </div>
        </header>

        {/* Body */}
        <main className="grid grid-cols-3 gap-6 p-6">
          {/* Chat Column */}
          <div className="col-span-2 flex flex-col h-[60vh]">
            <div ref={messagesRef} className="flex-1 overflow-auto p-4 space-y-4 bg-slate-50 rounded-lg">
              <AnimatePresence initial={false} mode="popLayout">
                {messages.map((m) => (
                  <motion.div
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    key={m.id}
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[85%] p-4 rounded-2xl shadow-sm ${m.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white border'}`}>
                      <div className="text-sm whitespace-pre-wrap">{m.text}</div>
                      {m.docs && m.docs.length > 0 && (
                        <div className="mt-2 text-xs text-slate-500">
                          Sources: {m.docs.join(', ')}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && (
                <div className="flex justify-start">
                  <div className="animate-pulse bg-white border rounded-2xl p-3">Assistant is thinking...</div>
                </div>
              )}
            </div>

            <form onSubmit={handleSend} className="mt-4 flex gap-3">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask something about invoices, policies, loans..."
                className="flex-1 rounded-xl border px-4 py-3 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <button
                onClick={handleSend}
                disabled={loading || !question.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-white shadow hover:bg-indigo-700 disabled:opacity-50">
                <Send className="w-4 h-4" />
                <span>Send</span>
              </button>
            </form>

            <div className="mt-3 text-xs text-slate-500">Tip: sensitive inputs (credit cards, PAN, etc.) will be blocked by the agent.</div>
          </div>

          {/* Right Panel: Tools & Evidence */}
          <aside className="col-span-1 space-y-4">
            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <h3 className="font-semibold">Retrieved Documents</h3>
              <div className="mt-2 text-sm text-slate-600">
                After each answer the assistant will list the documents used as evidence here.
              </div>
            </div>

            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <h3 className="font-semibold">Quick Actions</h3>
              <div className="mt-3 flex flex-col gap-2">
                <button onClick={() => setShowEvidence((s) => !s)} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-slate-50">
                  <ShieldCheck className="w-4 h-4" />
                  Toggle Evidence View
                </button>

                <button onClick={() => window.location.reload()} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-slate-50">
                  <Search className="w-4 h-4" />
                  Refresh Index
                </button>
              </div>
            </div>

            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <h3 className="font-semibold">About</h3>
              <p className="text-sm text-slate-600 mt-2">Local pilot RAG agent. Data is stored locally in your Chroma index. For production, add authentication & audit.</p>
            </div>

          </aside>
        </main>

        <footer className="p-4 text-center text-xs text-slate-500">Built for Werize pilot • Keep sensitive data out of the chat</footer>
      </div>
    </div>
  );
}
