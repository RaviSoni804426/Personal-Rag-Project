import React, { useState, useRef, useEffect } from "react";
import { apiService, ChatResponse, ChatSource, DocumentResponse } from "../services/api";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: Date;
  latency_ms?: number;
  token_usage?: number;
  confidence?: number;
  sources?: ChatSource[];
  eval_scores?: {
    faithfulness: number;
    context_precision: number;
    answer_relevance: number;
  };
}

interface ChatInterfaceProps {
  documents: DocumentResponse[];
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ documents }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "initial",
      sender: "assistant",
      text: "Hello! I am your Enterprise Document Intelligence Assistant. Ask me any question grounded in your uploaded documents, and I'll synthesize answers with precise source citations.",
      timestamp: new Date(),
    },
  ]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [activeSource, setActiveSource] = useState<ChatSource | null>(null);
  const [retrievalK, setRetrievalK] = useState(5);
  
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage: Message = {
      id: Math.random().toString(),
      sender: "user",
      text: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      // Execute retrieval-synthesis request
      const response = await apiService.sendQuery(
        userMessage.text,
        "default",
        selectedDocId || undefined,
        retrievalK
      );

      const assistantMessage: Message = {
        id: Math.random().toString(),
        sender: "assistant",
        text: response.answer,
        timestamp: new Date(),
        latency_ms: response.latency_ms,
        token_usage: response.token_usage,
        confidence: response.confidence,
        sources: response.sources,
        eval_scores: response.eval_scores,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: Message = {
        id: Math.random().toString(),
        sender: "assistant",
        text: `Error: ${err.message || "Something went wrong. Please confirm backend status."}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-emerald-400 bg-emerald-950/40 border-emerald-500/25";
    if (score >= 0.5) return "text-amber-400 bg-amber-950/40 border-amber-500/25";
    return "text-rose-400 bg-rose-950/40 border-rose-500/25";
  };

  return (
    <div className="flex flex-col h-full bg-transparent text-slate-100 relative">
      {/* Upper Control Bar */}
      <header className="bg-slate-900 border-b border-slate-850 px-6 py-4 flex items-center justify-between shadow-sm">
        <div>
          <h2 className="text-sm font-bold text-slate-100">Conversational Query Console</h2>
          <p className="text-[11px] text-slate-500">Ask questions grounded in the indexed knowledge base</p>
        </div>
        
        {/* Dynamic Context Settings */}
        <div className="flex items-center space-x-3.5">
          <div className="flex flex-col">
            <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider mb-1">
              Document Context Filter
            </label>
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-600 transition cursor-pointer"
            >
              <option value="">Query All Scope Documents</option>
              {documents.filter(d => d.status === "indexed").map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-[9px] text-slate-500 font-bold uppercase tracking-wider mb-1">
              Context Depth (K Chunks)
            </label>
            <input
              type="number"
              min="1"
              max="15"
              value={retrievalK}
              onChange={(e) => setRetrievalK(parseInt(e.target.value) || 5)}
              className="w-20 bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-600 transition"
            />
          </div>
        </div>
      </header>

      {/* Messaging Stream Grid */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
          >
            {/* Bubble */}
            <div
              className={`max-w-[70%] rounded-2xl px-5 py-3 text-sm shadow-sm transition-all duration-200 ${
                msg.sender === "user"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-slate-900 border border-slate-850 text-slate-200 rounded-bl-none"
              }`}
            >
              <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>

              {/* Citations block for assistant answers */}
              {msg.sender === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3.5 border-t border-slate-800">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2">
                    Verified Source Citations ({msg.sources.length})
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <button
                        key={src.chunk_id}
                        onClick={() => setActiveSource(src)}
                        className="flex items-center space-x-1.5 text-[10px] font-medium bg-slate-800 hover:bg-slate-700 border border-slate-700/60 hover:border-slate-500 text-indigo-300 hover:text-indigo-200 rounded-md px-2.5 py-1 transition duration-200 active:scale-95"
                      >
                        <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        <span className="truncate max-w-[130px]">{src.filename}</span>
                        <span className="text-[9px] text-slate-400 bg-slate-900 px-1 py-0.5 rounded font-mono">
                          {Math.round(src.score * 100)}%
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Diagnostic Metrics Underlay */}
            {msg.sender === "assistant" && (msg.latency_ms || msg.confidence) && (
              <div className="flex items-center space-x-3 mt-2 text-[10px] text-slate-500 px-2">
                {msg.latency_ms && (
                  <span>Latency: <strong className="text-slate-400">{Math.round(msg.latency_ms)}ms</strong></span>
                )}
                {msg.token_usage && (
                  <span>Tokens: <strong className="text-slate-400">{msg.token_usage}</strong></span>
                )}
                {msg.confidence !== undefined && (
                  <span className="flex items-center space-x-1">
                    <span>Trust Rating:</span>
                    <strong className={`px-1.5 py-0.5 rounded font-semibold ${msg.confidence >= 0.8 ? "text-emerald-400 bg-emerald-950/40" : "text-amber-400 bg-amber-950/40"}`}>
                      {Math.round(msg.confidence * 100)}%
                    </strong>
                  </span>
                )}
                
                {/* RAG Verification evaluation stats */}
                {msg.eval_scores && (
                  <div className="flex items-center space-x-2 border-l border-slate-800 pl-3">
                    <span className="text-slate-600">Evals:</span>
                    <span className="flex items-center space-x-0.5" title="Faithfulness">
                      <span>F:</span>
                      <strong className={msg.eval_scores.faithfulness >= 0.8 ? "text-emerald-400" : "text-amber-400"}>
                        {Math.round(msg.eval_scores.faithfulness * 100)}%
                      </strong>
                    </span>
                    <span className="flex items-center space-x-0.5" title="Answer Relevance">
                      <span>R:</span>
                      <strong className={msg.eval_scores.answer_relevance >= 0.8 ? "text-emerald-400" : "text-amber-400"}>
                        {Math.round(msg.eval_scores.answer_relevance * 100)}%
                      </strong>
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Messaging Stream Loading indicator */}
        {loading && (
          <div className="flex flex-col items-start">
            <div className="bg-slate-900 border border-slate-800 text-slate-400 rounded-2xl rounded-bl-none px-6 py-4 flex items-center space-x-3.5 max-w-[40%] animate-pulse">
              <div className="flex space-x-1">
                <div className="w-2.5 h-2.5 bg-indigo-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce delay-200"></div>
                <div className="w-2.5 h-2.5 bg-pink-500 rounded-full animate-bounce delay-300"></div>
              </div>
              <span className="text-xs text-slate-400 font-medium">Retrieving vectors & synthesizing...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Message Container */}
      <footer className="p-6 bg-slate-900/60 border-t border-slate-850">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            placeholder={
              documents.length === 0
                ? "Upload document indices in Document Manager first..."
                : "Ask any document query..."
            }
            className="w-full bg-slate-950 text-slate-200 rounded-xl px-5 py-4 border border-slate-850 outline-none focus:border-indigo-600 transition duration-150 pr-16 text-sm shadow-sm"
          />
          <button
            type="submit"
            disabled={loading || !query.trim() || documents.length === 0}
            className="absolute right-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg p-2.5 transition active:scale-95 disabled:opacity-30 disabled:pointer-events-none shadow"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </form>
      </footer>

      {/* Slide-over Right Citation Panel Modal */}
      {activeSource && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-end transition duration-350">
          <div className="w-[480px] h-full bg-slate-900 border-l border-slate-800 p-6 flex flex-col justify-between shadow-2xl">
            {/* Header */}
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-850">
                <h3 className="font-bold text-sm text-slate-100">Verification Source Details</h3>
                <button
                  onClick={() => setActiveSource(null)}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-slate-200 transition"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Document Meta */}
              <div className="mt-5 space-y-3.5">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Document Name</span>
                  <p className="text-xs text-slate-200 font-medium truncate bg-slate-950 px-3 py-2 rounded-lg mt-1 border border-slate-800/60">
                    {activeSource.filename}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3.5">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Relevance score</span>
                    <span className={`flex items-center justify-center rounded-lg border font-mono text-xs font-semibold py-1.5 mt-1 ${getScoreColor(activeSource.score)}`}>
                      {Math.round(activeSource.score * 100)}% Match
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Retrieval method</span>
                    <span className="flex items-center justify-center rounded-lg bg-indigo-950/40 border border-indigo-500/25 text-indigo-400 text-xs font-semibold py-1.5 mt-1 capitalize">
                      {activeSource.sources.join(" + ")}
                    </span>
                  </div>
                </div>

                <div className="mt-4">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Retrieved Text Content</span>
                  <div className="mt-1 bg-slate-950 p-4 rounded-xl border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-normal whitespace-pre-wrap max-h-[350px] overflow-y-auto shadow-inner">
                    {activeSource.text_content}
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={() => setActiveSource(null)}
                className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition active:scale-95"
              >
                Close Inspect Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
