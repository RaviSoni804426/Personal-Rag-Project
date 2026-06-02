import React from "react";
import { AnalyticsResponse } from "../services/api";

interface AnalyticsDashboardProps {
  analytics: AnalyticsResponse | null;
  loading: boolean;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ analytics, loading }) => {
  if (loading) {
    return (
      <div className="p-6 bg-slate-950 text-slate-100 min-h-full flex flex-col justify-center items-center space-y-3.5">
        <div className="w-8 h-8 rounded-full border-4 border-slate-800 border-t-indigo-500 animate-spin"></div>
        <p className="text-xs text-slate-400 font-semibold animate-pulse">Loading system observability parameters...</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-6 bg-slate-950 text-slate-100 min-h-full flex justify-center items-center">
        <p className="text-xs text-slate-500">Analytics logging records missing. Run queries in Chat Console first.</p>
      </div>
    );
  }

  // Pure SVG gauge calculation
  const getStrokeDash = (percentage: number, circumference: number) => {
    return (percentage / 100) * circumference;
  };

  const getMetricColor = (val: number) => {
    if (val >= 0.8) return "text-emerald-400";
    if (val >= 0.5) return "text-amber-400";
    return "text-rose-400";
  };

  const circumference = 2 * Math.PI * 34; // Radius is 34

  return (
    <div className="p-6 bg-slate-950 text-slate-100 min-h-full space-y-6 overflow-y-auto">
      {/* Header */}
      <header className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold text-slate-100">System Observability Dashboard</h2>
        <p className="text-xs text-slate-400">Monitor RAG pipeline latencies, token parameters, and automated generation evaluations</p>
      </header>

      {/* Grid Cards Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Queries */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-indigo-500 to-purple-500 opacity-30 group-hover:opacity-100 transition duration-300"></div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Queries</span>
          <span className="text-2xl font-extrabold text-slate-100 mt-2 block font-mono">
            {analytics.total_queries}
          </span>
          <span className="text-[9px] text-indigo-400 font-medium block mt-1">Live requests registered</span>
        </div>

        {/* Query Latency */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-purple-500 to-pink-500 opacity-30 group-hover:opacity-100 transition duration-300"></div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Avg Latency</span>
          <span className="text-2xl font-extrabold text-slate-100 mt-2 block font-mono">
            {analytics.avg_latency_ms ? `${Math.round(analytics.avg_latency_ms)}ms` : "0ms"}
          </span>
          <span className="text-[9px] text-purple-400 font-medium block mt-1">Reranking & API synthesis</span>
        </div>

        {/* Tokens Consumption */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-pink-500 to-rose-500 opacity-30 group-hover:opacity-100 transition duration-300"></div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Tokens Used</span>
          <span className="text-2xl font-extrabold text-slate-100 mt-2 block font-mono">
            {analytics.token_usage_total ? analytics.token_usage_total.toLocaleString() : "0"}
          </span>
          <span className="text-[9px] text-pink-400 font-medium block mt-1">Estimated context density</span>
        </div>

        {/* Knowledge Base Size */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 h-1 w-full bg-gradient-to-r from-emerald-500 to-teal-500 opacity-30 group-hover:opacity-100 transition duration-300"></div>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Database Index</span>
          <span className="text-2xl font-extrabold text-slate-100 mt-2 block font-mono">
            {analytics.docs_indexed_count} <span className="text-xs text-slate-500 font-normal">files</span>
          </span>
          <span className="text-[9px] text-emerald-400 font-medium block mt-1">
            Containing {analytics.chunks_indexed_count} vectorized chunks
          </span>
        </div>
      </div>

      {/* RAG Verification Evaluation Meters Section */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg shadow-slate-950/50">
        <h3 className="font-bold text-sm text-slate-200 mb-6">Autonomous RAG Validation Grades</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Faithfulness Gauge */}
          <div className="flex flex-col items-center p-4 bg-slate-950/30 rounded-xl border border-slate-800/40 text-center">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">LLM Faithfulness</span>
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="48" cy="48" r="34" className="stroke-slate-800" strokeWidth="6" fill="transparent" />
                <circle
                  cx="48"
                  cy="48"
                  r="34"
                  className="stroke-indigo-500 transition-all duration-500"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference - getStrokeDash((analytics.avg_faithfulness || 0.85) * 100, circumference)}
                />
              </svg>
              <div className="absolute text-center">
                <span className={`text-lg font-extrabold font-mono ${getMetricColor(analytics.avg_faithfulness)}`}>
                  {Math.round((analytics.avg_faithfulness || 0) * 100)}%
                </span>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mt-4 max-w-[200px]">
              Verifies if LLM answers are strictly grounded, preventing hallucinations.
            </p>
          </div>

          {/* Context Precision Gauge */}
          <div className="flex flex-col items-center p-4 bg-slate-950/30 rounded-xl border border-slate-800/40 text-center">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Context Precision</span>
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="48" cy="48" r="34" className="stroke-slate-800" strokeWidth="6" fill="transparent" />
                <circle
                  cx="48"
                  cy="48"
                  r="34"
                  className="stroke-purple-500 transition-all duration-500"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference - getStrokeDash((analytics.avg_context_precision || 0.85) * 100, circumference)}
                />
              </svg>
              <div className="absolute text-center">
                <span className={`text-lg font-extrabold font-mono ${getMetricColor(analytics.avg_context_precision)}`}>
                  {Math.round((analytics.avg_context_precision || 0) * 100)}%
                </span>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mt-4 max-w-[200px]">
              Assesses the relevancy density of vector blocks retrieved.
            </p>
          </div>

          {/* Answer Relevance Gauge */}
          <div className="flex flex-col items-center p-4 bg-slate-950/30 rounded-xl border border-slate-800/40 text-center">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Answer Relevance</span>
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="48" cy="48" r="34" className="stroke-slate-800" strokeWidth="6" fill="transparent" />
                <circle
                  cx="48"
                  cy="48"
                  r="34"
                  className="stroke-pink-500 transition-all duration-500"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference - getStrokeDash((analytics.avg_answer_relevance || 0.85) * 100, circumference)}
                />
              </svg>
              <div className="absolute text-center">
                <span className={`text-lg font-extrabold font-mono ${getMetricColor(analytics.avg_answer_relevance)}`}>
                  {Math.round((analytics.avg_answer_relevance || 0) * 100)}%
                </span>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mt-4 max-w-[200px]">
              Measures how cleanly the generated synthesis addresses the query context.
            </p>
          </div>

        </div>
      </section>

      {/* Query Log Diagnostic Registry */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg shadow-slate-950/50">
        <h3 className="font-bold text-sm text-slate-200 mb-4">Recent Query Diagnostics</h3>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                <th className="pb-3 pl-2">User Query</th>
                <th className="pb-3">Latency</th>
                <th className="pb-3">Faithfulness</th>
                <th className="pb-3">Est. Tokens</th>
                <th className="pb-3 pr-2 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {analytics.recent_history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-slate-500">
                    No query registers found. Initialize chat logs to view logs.
                  </td>
                </tr>
              ) : (
                analytics.recent_history.map((log, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/10 text-slate-300">
                    <td className="py-3.5 pl-2 font-medium truncate max-w-[260px]" title={log.query}>
                      {log.query}
                    </td>
                    <td className="py-3.5 font-mono text-slate-400">{Math.round(log.latency_ms)}ms</td>
                    <td className="py-3.5">
                      <span className={`font-semibold font-mono ${getMetricColor(log.faithfulness)}`}>
                        {Math.round(log.faithfulness * 100)}%
                      </span>
                    </td>
                    <td className="py-3.5 font-mono text-slate-400">{log.token_usage}</td>
                    <td className="py-3.5 pr-2 text-right text-slate-500 font-mono">{log.timestamp}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

    </div>
  );
};
