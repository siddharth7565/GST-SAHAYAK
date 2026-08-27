import math
from typing import List, Optional
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Service layer for generating text embeddings using local SentenceTransformers model.
    Loads model once and reuses instance across requests.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        """Lazy load and reuse the SentenceTransformer model instance."""
        if self._model is None:
            # Download/load model once on first request
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def get_dimension(self) -> int:
        """Returns the embedding vector dimension of the loaded model."""
        model = self._get_model()
        if hasattr(model, "get_embedding_dimension"):
            return model.get_embedding_dimension()
        return model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> List[float]:
        """Generates a numerical embedding vector for a single text string."""
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")
        model = self._get_model()
        vector = model.encode(text.strip(), convert_to_numpy=True)
        return vector.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates numerical embedding vectors for a batch of text strings."""
        if not texts:
            return []
        cleaned_texts = [t.strip() for t in texts if t and t.strip()]
        if not cleaned_texts:
            raise ValueError("All provided texts for embedding are empty.")
        model = self._get_model()
        vectors = model.encode(cleaned_texts, convert_to_numpy=True)
        return vectors.tolist()

    def compute_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculates cosine similarity between two numerical vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return round(dot_product / (norm1 * norm2), 4)

    def evaluate_similarity(self, text1: str, text2: str) -> float:
        """Generates embeddings for two text inputs and calculates their cosine similarity."""
        v1 = self.embed_text(text1)
        v2 = self.embed_text(text2)
        return self.compute_cosine_similarity(v1, v2)


# Global singleton instance
embedding_service = EmbeddingService()
