import { useState, useEffect } from 'react';
import { checkHealth, testBackend, sendRAGQuery, sendMultiModelVerification } from './api';
import './App.css';

function App() {
  // Part 1 States
  const [healthStatus, setHealthStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState(null);

  // Workflow Mode State
  const [mode, setMode] = useState('rag'); // 'rag' | 'verify'

  // RAG / Multi-Model States
  const [messageInput, setMessageInput] = useState('');
  const [selectedFY, setSelectedFY] = useState(''); // '' | '2024-25' | '2025-26' | '2026-27'
  const [asOfDateInput, setAsOfDateInput] = useState(''); // '' | 'YYYY-MM-DD'
  const [userPrompt, setUserPrompt] = useState('');
  const [ragResult, setRagResult] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [expandedChunks, setExpandedChunks] = useState({});

  // Check GET /health on mount
  useEffect(() => {
    handleCheckHealth();
  }, []);

  const handleCheckHealth = async () => {
    setHealthStatus('checking');
    try {
      const data = await checkHealth();
      if (data.status === 'ok') {
        setHealthStatus('connected');
      } else {
        setHealthStatus('disconnected');
      }
    } catch (err) {
      setHealthStatus('disconnected');
    }
  };

  const handleTestConnection = async () => {
    setTestLoading(true);
    setTestError(null);
    setTestResult(null);

    try {
      const data = await testBackend();
      setTestResult(data.message);
      setHealthStatus('connected');
    } catch (err) {
      setTestError(`Backend test failed: ${err.message}`);
      setHealthStatus('disconnected');
    } finally {
      setTestLoading(false);
    }
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    const prompt = messageInput.trim();
    if (!prompt || chatLoading) return;

    setChatLoading(true);
    setChatError(null);
    setRagResult(null);
    setVerifyResult(null);
    setUserPrompt(prompt);
    setExpandedChunks({});

    try {
      if (mode === 'verify') {
        const data = await sendMultiModelVerification(
          prompt,
          5,
          selectedFY || null,
          asOfDateInput || null,
          ['gemini', 'mistral', 'grok', 'ollama']
        );
        setVerifyResult(data);
      } else {
        const data = await sendRAGQuery(
          prompt,
          5,
          selectedFY || null,
          asOfDateInput || null
        );
        setRagResult(data);
      }
      setMessageInput('');
      setHealthStatus('connected');
    } catch (err) {
      setChatError(err.message || 'Failed to process request.');
    } finally {
      setChatLoading(false);
    }
  };

  const toggleChunkExpand = (chunkId) => {
    setExpandedChunks((prev) => ({
      ...prev,
      [chunkId]: !prev[chunkId],
    }));
  };

  return (
    <div className="container">
      {/* Header */}
      <h1 className="title">GST SAHAYAK</h1>
      <p className="subtitle">AI-Powered GST Legal Research & Verification System</p>

      {/* Backend Status Badge */}
      <div className={`status-badge ${healthStatus}`}>
        Backend Status:{' '}
        {healthStatus === 'checking' && 'Checking...'}
        {healthStatus === 'connected' && 'Connected'}
        {healthStatus === 'disconnected' && 'Not Connected'}
      </div>

      {/* Backend Test Section */}
      <div className="action-section">
        <button
          className="test-btn"
          onClick={handleTestConnection}
          disabled={testLoading}
        >
          {testLoading ? 'Testing...' : 'Test Backend Connection'}
        </button>
      </div>

      {testResult && (
        <div className="response-box test-result">
          <strong>Test Result:</strong> {testResult}
        </div>
      )}

      {testError && (
        <div className="response-box error">
          <strong>Test Error:</strong> {testError}
        </div>
      )}

      <hr className="divider" />

      {/* Mode Selector */}
      <div className="mode-toggle-bar">
        <button
          type="button"
          className={`mode-btn ${mode === 'rag' ? 'active' : ''}`}
          onClick={() => setMode('rag')}
        >
          ⚡ Standard Grounded RAG
        </button>
        <button
          type="button"
          className={`mode-btn ${mode === 'verify' ? 'active' : ''}`}
          onClick={() => setMode('verify')}
        >
          🛡️ Multi-Model Answer Verification
        </button>
      </div>

      {/* Main Chat / Verification Section */}
      <div className="chat-section">
        <h2 className="chat-title">
          {mode === 'verify'
            ? 'Verify Answer Across Multiple LLMs (Single Evidence Retrieval)'
            : 'Ask GST Law Question (Grounded RAG Search)'}
        </h2>

        {/* Temporal Context Controls */}
        <div className="temporal-filter-bar">
          <div className="filter-group">
            <label className="filter-label">Financial Year (Optional):</label>
            <select
              className="filter-select"
              value={selectedFY}
              onChange={(e) => setSelectedFY(e.target.value)}
              disabled={chatLoading}
            >
              <option value="">All FYs (Default)</option>
              <option value="2024-25">FY 2024-25</option>
              <option value="2025-26">FY 2025-26</option>
              <option value="2026-27">FY 2026-27</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">As-of Applicability Date (Optional):</label>
            <input
              type="date"
              className="filter-date"
              value={asOfDateInput}
              onChange={(e) => setAsOfDateInput(e.target.value)}
              disabled={chatLoading}
            />
          </div>
        </div>

        <form onSubmit={handleSendChat} className="chat-form">
          <input
            type="text"
            className="chat-input"
            placeholder={
              mode === 'verify'
                ? 'Ask a question to verify across Gemini, OpenAI & Claude...'
                : 'Ask a GST legal question...'
            }
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            disabled={chatLoading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={chatLoading || !messageInput.trim()}
          >
            {chatLoading ? 'Processing...' : mode === 'verify' ? 'Verify Answers' : 'Send'}
          </button>
        </form>

        {chatLoading && (
          <div className="response-box loading">
            <span className="spinner">⏳</span>{' '}
            {mode === 'verify'
              ? 'Retrieving single shared evidence & executing multi-model verification...'
              : 'Evaluating evidence quality in pgvector & generating grounded answer...'}
          </div>
        )}

        {/* Standard RAG Card Result */}
        {ragResult && (
          <div className="response-box chat-card">
            <div className="chat-prompt">Q: {userPrompt}</div>

            {(selectedFY || asOfDateInput) && (
              <div className="applied-temporal-badge">
                🗓️ Applied Filters:{' '}
                {selectedFY && <span>Financial Year: <strong>{selectedFY}</strong> </span>}
                {asOfDateInput && <span>As-of Date: <strong>{asOfDateInput}</strong></span>}
              </div>
            )}

            {/* Verification Signal Banner */}
            {ragResult.verification && renderVerificationSignal(ragResult.verification)}

            <div className="chat-answer-header"><strong>Answer:</strong></div>
            <div className="chat-answer">{ragResult.answer}</div>

            {/* Sources */}
            {renderSources(ragResult.retrieved_chunks, ragResult.retrieved_count, expandedChunks, toggleChunkExpand)}
          </div>
        )}

        {/* Multi-Model Verification Card Result */}
        {verifyResult && (
          <div className="response-box chat-card verify-card">
            <div className="chat-prompt">Q: {userPrompt}</div>

            {(selectedFY || asOfDateInput) && (
              <div className="applied-temporal-badge">
                🗓️ Applied Filters:{' '}
                {selectedFY && <span>Financial Year: <strong>{selectedFY}</strong> </span>}
                {asOfDateInput && <span>As-of Date: <strong>{asOfDateInput}</strong></span>}
              </div>
            )}

            {/* Verification Signal Banner */}
            {verifyResult.verification && renderVerificationSignal(verifyResult.verification)}

            {/* Shared Legal References */}
            {verifyResult.comparison && verifyResult.comparison.shared_legal_references.length > 0 && (
              <div className="shared-refs-box">
                <strong>📜 Shared Legal References Cited:</strong>{' '}
                {verifyResult.comparison.shared_legal_references.map((ref) => (
                  <span key={ref} className="ref-tag">{ref}</span>
                ))}
              </div>
            )}

            {/* Model Results List */}
            <div className="model-results-grid">
              {verifyResult.model_results.map((res) => (
                <div key={res.provider} className={`model-card ${res.success ? 'success' : 'failed'}`}>
                  <div className="model-header">
                    <span className="model-provider-title">
                      {res.provider.toUpperCase()} ({res.model})
                    </span>
                    <span className={`model-status-pill ${res.success ? 'ok' : 'err'}`}>
                      {res.success ? 'SUCCESS' : 'UNCONFIGURED / FAILED'}
                    </span>
                  </div>

                  {res.success ? (
                    <div className="model-answer-text">{res.answer}</div>
                  ) : (
                    <div className="model-error-text">⚠️ {res.error}</div>
                  )}
                </div>
              ))}
            </div>

            {/* Shared Sources */}
            {renderSources(verifyResult.retrieved_chunks, verifyResult.retrieved_count, expandedChunks, toggleChunkExpand)}
          </div>
        )}

        {chatError && (
          <div className="response-box error">
            <strong>Error:</strong> {chatError}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper to render Verification Signal Banner
function renderVerificationSignal(verif) {
  const level = verif.verification_level;
  const scorePercent = (verif.verification_score * 100).toFixed(1);

  return (
    <div className={`verification-signal-banner ${level}`}>
      <div className="verif-header">
        <span className="verif-level-badge">
          {level === 'HIGH' && '🟢 HIGH VERIFICATION'}
          {level === 'MEDIUM' && '🟡 MEDIUM VERIFICATION'}
          {level === 'LOW' && '🔴 LOW VERIFICATION'}
          {level === 'UNVERIFIED' && '⚪ UNVERIFIED'}
        </span>
        <span className="verif-score-badge">
          Verification Score: <strong>{scorePercent}%</strong>
        </span>
      </div>
      <div className="verif-explanation">
        💡 {verif.explanation}
      </div>
    </div>
  );
}

// Helper to render retrieved sources list
function renderSources(chunks, count, expandedChunks, toggleExpand) {
  return (
    <div className="sources-section">
      <h3 className="sources-title">
        📚 Single Shared Evidence Sources ({count || 0})
      </h3>

      {count === 0 ? (
        <div className="no-sources">
          No matching GST documents met the criteria. Zero LLM calls were made.
        </div>
      ) : (
        <div className="sources-list">
          {chunks.map((chunk, idx) => {
            const isExpanded = !!expandedChunks[chunk.chunk_id];
            const matchPercent = (chunk.similarity_score * 100).toFixed(1);

            return (
              <div key={chunk.chunk_id} className="source-card">
                <div className="source-header">
                  <span className="source-num">[{idx + 1}]</span>
                  <span className="source-doc-title">
                    {chunk.title || chunk.document}
                  </span>
                  <span className="similarity-badge">
                    {matchPercent}% Match
                  </span>
                </div>

                <div className="source-meta-row">
                  {chunk.retrieval_method && (
                    <span className={`meta-tag method ${chunk.retrieval_method}`}>
                      {chunk.retrieval_method === 'hybrid' && '⚡ Hybrid Match'}
                      {chunk.retrieval_method === 'vector_only' && '🧠 Vector Match'}
                      {chunk.retrieval_method === 'keyword_only' && '🔤 Keyword Match'}
                    </span>
                  )}
                  {chunk.document_type && <span className="meta-tag type">{chunk.document_type}</span>}
                  <span className="meta-tag page">Page {chunk.page}</span>
                  {chunk.financial_year && <span className="meta-tag fy">FY {chunk.financial_year}</span>}
                  {(chunk.effective_from || chunk.effective_to) && (
                    <span className="meta-tag effective">
                      Effective: {chunk.effective_from || 'Beginning'}
                      {chunk.effective_to ? ` to ${chunk.effective_to}` : ' Onwards'}
                    </span>
                  )}
                  {chunk.issuing_authority && <span className="meta-tag authority">{chunk.issuing_authority}</span>}
                </div>

                {chunk.source_url && (
                  <div className="source-url-wrapper">
                    <a href={chunk.source_url} target="_blank" rel="noopener noreferrer" className="source-url-link">
                      Official Source Document 🔗
                    </a>
                  </div>
                )}

                <div className="source-text-box">
                  <p className="source-text">
                    {isExpanded
                      ? chunk.text
                      : chunk.text.length > 180
                      ? chunk.text.slice(0, 180) + '...'
                      : chunk.text}
                  </p>
                  {chunk.text.length > 180 && (
                    <button type="button" className="expand-btn" onClick={() => toggleExpand(chunk.chunk_id)}>
                      {isExpanded ? 'Show Less' : 'Show Full Chunk Text'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default App;
