const API_BASE_URL = 'http://localhost:8000';

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function testBackend() {
  const response = await fetch(`${API_BASE_URL}/api/test`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

export async function sendChatMessage(message) {
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

export async function sendRAGQuery(query, top_k = 5, financialYear = null, asOfDate = null) {
  const payload = {
    query: query,
    top_k: top_k,
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

export async function sendMultiModelVerification(query, top_k = 5, financialYear = null, asOfDate = null, providers = ["gemini", "mistral", "grok", "ollama"]) {
  const payload = {
    query: query,
    top_k: top_k,
    financial_year: financialYear || null,
    as_of_date: asOfDate || null,
    providers: providers,
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
