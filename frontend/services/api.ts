export interface DocumentResponse {
  id: string;
  filename: string;
  file_size: number;
  chunk_strategy: string;
  chunks_count: number;
  status: string;
  created_at: string;
}

export interface ChatSource {
  chunk_id: string;
  text_content: string;
  score: number;
  filename: string;
  sources: string[];
}

export interface ChatEvaluation {
  faithfulness: number;
  context_precision: number;
  answer_relevance: number;
}

export interface ChatResponse {
  answer: string;
  confidence: number;
  latency_ms: number;
  token_usage: number;
  sources: ChatSource[];
  eval_scores: ChatEvaluation;
}

export interface AnalyticsResponse {
  total_queries: number;
  avg_latency_ms: number;
  avg_confidence: number;
  avg_faithfulness: number;
  avg_context_precision: number;
  avg_answer_relevance: number;
  token_usage_total: number;
  docs_indexed_count: number;
  chunks_indexed_count: number;
  recent_history: Array<{
    query: string;
    latency_ms: number;
    token_usage: number;
    faithfulness: number;
    timestamp: string;
  }>;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const apiService = {
  async uploadFile(
    file: File,
    chunkStrategy = "recursive",
    chunkSize = 1000,
    chunkOverlap = 200
  ): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("chunk_strategy", chunkStrategy);
    formData.append("chunk_size", chunkSize.toString());
    formData.append("chunk_overlap", chunkOverlap.toString());

    const response = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to upload and index document.");
    }

    return response.json();
  },

  async listDocuments(): Promise<DocumentResponse[]> {
    const response = await fetch(`${BASE_URL}/documents`);
    if (!response.ok) {
      throw new Error("Failed to load documents list.");
    }
    return response.json();
  },

  async deleteDocument(id: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/documents/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete document.");
    }
  },

  async sendQuery(
    query: string,
    sessionId = "default",
    documentId?: string,
    k = 5
  ): Promise<ChatResponse> {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        session_id: sessionId,
        document_id: documentId || null,
        k,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to process chat query.");
    }

    return response.json();
  },

  async getAnalytics(): Promise<AnalyticsResponse> {
    const response = await fetch(`${BASE_URL}/analytics`);
    if (!response.ok) {
      throw new Error("Failed to fetch analytics metrics.");
    }
    return response.json();
  },

  async resetSystem(): Promise<void> {
    const response = await fetch(`${BASE_URL}/system/reset`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error("Failed to execute system purge reset.");
    }
  },
};
