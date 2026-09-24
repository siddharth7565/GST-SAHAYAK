import {
  HealthCheckResponse,
  TestBackendResponse,
  RAGResponse,
  MultiModelResponse,
  StoredDocumentSummary
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

export async function checkHealth(): Promise<HealthCheckResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function testBackend(): Promise<TestBackendResponse> {
  const response = await fetch(`${API_BASE_URL}/api/test`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function sendChatMessage(message: string): Promise<{ answer: string }> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function sendRAGQuery(
  query: string,
  top_k: number = 5,
  financialYear: string | null = null,
  asOfDate: string | null = null
): Promise<RAGResponse> {
  const payload = {
    query,
    top_k,
    financial_year: financialYear || null,
    as_of_date: asOfDate || null,
  };

  const response = await fetch(`${API_BASE_URL}/api/rag/answer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `RAG query failed with status ${response.status}`);
  }

  return await response.json();
}

export async function sendMultiModelVerification(
  query: string,
  top_k: number = 5,
  financialYear: string | null = null,
  asOfDate: string | null = null,
  providers: string[] = ["gemini", "mistral", "grok", "ollama"]
): Promise<MultiModelResponse> {
  const payload = {
    query,
    top_k,
    financial_year: financialYear || null,
    as_of_date: asOfDate || null,
    providers,
  };

  const response = await fetch(`${API_BASE_URL}/api/rag/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Multi-model verification failed with status ${response.status}`);
  }

  return await response.json();
}

export async function getStoredDocuments(): Promise<StoredDocumentSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/documents`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch documents: ${response.status}`);
  }
  return await response.json();
}
