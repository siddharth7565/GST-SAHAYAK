export interface RetrievedChunk {
  chunk_id: string;
  document_id: number;
  document: string;
  title?: string | null;
  document_type?: string | null;
  source_url?: string | null;
  issuing_authority?: string | null;
  publication_date?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  financial_year?: string | null;
  page: number;
  text: string;
  similarity_score: number;
  vector_score?: number | null;
  keyword_score?: number | null;
  hybrid_score?: number | null;
  retrieval_method?: 'hybrid' | 'vector_only' | 'keyword_only' | string;
}

export interface VerificationComponentDetails {
  evidence_component: number;
  agreement_component: number;
  model_coverage_component: number;
}

export interface VerificationSignal {
  verification_score: number;
  verification_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNVERIFIED';
  verification_status: 'strongly_supported' | 'moderately_supported' | 'limited_support' | 'unverified' | string;
  explanation: string;
  components: VerificationComponentDetails;
}

export interface RAGResponse {
  query: string;
  answer: string;
  retrieved_count: number;
  evidence_status: 'strong' | 'weak' | 'insufficient' | string;
  best_score: number;
  verification?: VerificationSignal | null;
  retrieved_chunks: RetrievedChunk[];
}

export interface ModelAnswerResult {
  provider: 'gemini' | 'mistral' | 'grok' | 'ollama' | string;
  model: string;
  success: boolean;
  answer?: string | null;
  error?: string | null;
  response_time?: number | null;
}

export interface ComparisonResult {
  overall_status: 'agreement' | 'partial_agreement' | 'disagreement' | 'insufficient_models' | string;
  successful_provider_count: number;
  failed_provider_count: number;
  pairwise_similarity: Record<string, number>;
  shared_legal_references: string[];
  conflicting_references: string[];
}

export interface MultiModelResponse {
  query: string;
  evidence_status: 'strong' | 'weak' | 'insufficient' | string;
  best_score: number;
  retrieved_count: number;
  model_results: ModelAnswerResult[];
  comparison: ComparisonResult;
  verification?: VerificationSignal | null;
  retrieved_chunks: RetrievedChunk[];
}

export interface HealthCheckResponse {
  status: 'ok' | string;
  message: string;
}

export interface TestBackendResponse {
  message: string;
}

export interface StoredDocumentSummary {
  id: number;
  filename: string;
  sha256_hash: string;
  title?: string | null;
  document_type: string;
  source_url?: string | null;
  issuing_authority?: string | null;
  publication_date?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  financial_year?: string | null;
  document_version?: string | null;
  description?: string | null;
  is_authoritative: boolean;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  mode: 'single' | 'multi';
  financialYear?: string | null;
  asOfDate?: string | null;
  verificationLevel?: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNVERIFIED' | string;
  verificationScore?: number | null;
  ragResult?: RAGResponse | null;
  verifyResult?: MultiModelResponse | null;
}

export interface SavedQueryItem {
  id: string;
  query: string;
  savedAt: string;
  category?: string;
  notes?: string;
  mode: 'single' | 'multi';
  financialYear?: string | null;
  asOfDate?: string | null;
}

export type PipelineStage = 'IDLE' | 'RETRIEVING' | 'GENERATING' | 'COMPARING' | 'VERIFYING' | 'COMPLETE';
