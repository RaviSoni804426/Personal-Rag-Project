import React, { useState } from "react";
import { apiService, DocumentResponse } from "../services/api";

interface DocumentManagerProps {
  documents: DocumentResponse[];
  onRefresh: () => void;
}

export const DocumentManager: React.FC<DocumentManagerProps> = ({ documents, onRefresh }) => {
  const [file, setFile] = useState<File | null>(null);
  const [strategy, setStrategy] = useState("recursive");
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setSuccess(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || uploading) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      await apiService.uploadFile(file, strategy, chunkSize, chunkOverlap);
      setSuccess(`Indexed successfully: ${file.name}`);
      setFile(null);
      // Reset input element
      const fileInput = document.getElementById("file-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to parse and upload file.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document and purge its vector chunks?")) return;
    try {
      await apiService.deleteDocument(id);
      onRefresh();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleSystemReset = async () => {
    if (!confirm("CRITICAL WARNING: This will permanently delete ALL indexed documents, database vectors, cache records, and physical uploads. Proceed?")) return;
    try {
      await apiService.resetSystem();
      onRefresh();
    } catch (err: any) {
      alert(`Purge failed: ${err.message}`);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="p-6 bg-transparent text-slate-100 min-h-full space-y-6">
      {/* Dashboard upper header */}
      <header className="flex justify-between items-center pb-4 border-b border-slate-900">
        <div>
          <h2 className="text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent">Enterprise Document Ingestion Manager</h2>
          <p className="text-xs text-slate-400">Load, parse, segment, and vector-index enterprise data directories</p>
        </div>
        
        <button
          onClick={handleSystemReset}
          className="bg-rose-950/40 hover:bg-rose-900 border border-rose-500/20 hover:border-rose-500 text-rose-400 hover:text-rose-200 text-xs font-semibold px-4 py-2 rounded-lg transition active:scale-95 shadow shadow-rose-950/20"
        >
          Factory Reset Index
        </button>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Upload Container Panel */}
        <section className="glass-panel rounded-2xl p-5 space-y-5 h-fit shadow-lg shadow-slate-950/40">
          <h3 className="font-bold text-sm text-slate-200">Index New Document</h3>
          
          <form onSubmit={handleUpload} className="space-y-4">
            {/* File Drag and Drop Box */}
            <div className="border-2 border-dashed border-slate-700/80 rounded-xl p-6 text-center hover:border-indigo-500 transition relative bg-slate-950/40">
              <input
                id="file-input"
                type="file"
                onChange={handleFileChange}
                disabled={uploading}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                accept=".pdf,.docx,.txt,.csv,.xlsx,.xls,.md,.html"
              />
              <svg className="w-8 h-8 text-slate-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-xs text-slate-300 font-semibold block">
                {file ? file.name : "Select or drag file"}
              </span>
              <span className="text-[10px] text-slate-500 mt-1 block">
                PDF, Word, CSV, Excel, MD, HTML (Max 50MB)
              </span>
            </div>

            {/* Ingestion Strategy Settings */}
            <div className="space-y-3.5 bg-slate-950/30 p-3.5 rounded-xl border border-slate-850/60">
              <div>
                <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">
                  Segmentation / Chunking Strategy
                </label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-slate-950/80 border border-slate-800 text-xs rounded-xl px-3 py-2.5 text-slate-200 outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-300 cursor-pointer"
                >
                  <option value="recursive">Recursive Character Splitting</option>
                  <option value="semantic">Semantic Similarity-Based</option>
                  <option value="parent-child">Parent-Child Leaf Hierarchies</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1 text-[10px] text-slate-500">
                  <span className="font-bold uppercase tracking-wider">Chunk Target Size</span>
                  <span className="font-mono text-indigo-400">{chunkSize} chars</span>
                </div>
                <input
                  type="range"
                  min="200"
                  max="3000"
                  step="100"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1 text-[10px] text-slate-500">
                  <span className="font-bold uppercase tracking-wider">Overlap Size</span>
                  <span className="font-mono text-indigo-400">{chunkOverlap} chars</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="800"
                  step="50"
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>
            </div>

            {/* Message alert slots */}
            {error && <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-500/20 px-3 py-2 rounded-lg">{error}</div>}
            {success && <div className="text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-500/20 px-3 py-2 rounded-lg">{success}</div>}

            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-xl text-xs font-bold transition active:scale-95 disabled:opacity-40 disabled:pointer-events-none glow-button shadow shadow-indigo-500/20"
            >
              {uploading ? "Ingesting & indexing..." : "Start Upload Ingestion"}
            </button>
          </form>
        </section>

        {/* Documents Indexed Grid List */}
        <section className="lg:col-span-2 glass-panel rounded-2xl p-5 shadow-lg shadow-slate-950/40">
          <h3 className="font-bold text-sm text-slate-200 mb-4">Currently Indexed Knowledge Bases ({documents.length})</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-3 pl-2">Filename</th>
                  <th className="pb-3">Strategy</th>
                  <th className="pb-3">Chunks Count</th>
                  <th className="pb-3">File Size</th>
                  <th className="pb-3">Ingest Status</th>
                  <th className="pb-3 pr-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-10 text-slate-500">
                      No documents indexed yet. Upload files above to initialize vector stores.
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/20 text-slate-300">
                      <td className="py-4 pl-2 font-medium truncate max-w-[200px]" title={doc.filename}>
                        {doc.filename}
                      </td>
                      <td className="py-4">
                        <span className="bg-indigo-950/50 border border-indigo-500/15 text-indigo-400 text-[10px] font-semibold px-2 py-0.5 rounded capitalize">
                          {doc.chunk_strategy}
                        </span>
                      </td>
                      <td className="py-4 font-mono font-semibold">{doc.chunks_count} chunks</td>
                      <td className="py-4 text-slate-400">{formatBytes(doc.file_size)}</td>
                      <td className="py-4">
                        <span
                          className={`inline-flex items-center space-x-1.5 text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                            doc.status === "indexed"
                              ? "bg-emerald-950/50 text-emerald-400 border border-emerald-500/15"
                              : doc.status === "failed"
                              ? "bg-rose-950/50 text-rose-400 border border-rose-500/15"
                              : "bg-amber-950/50 text-amber-400 border border-amber-500/15 animate-pulse"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </td>
                      <td className="py-4 pr-2 text-right">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded transition active:scale-90"
                          title="Purge Document Vectors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
