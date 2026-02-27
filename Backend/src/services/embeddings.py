import logging
import numpy as np
from google import genai
from typing import List, Union
import threading
from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating text embeddings using Google's text-embedding-004.
    Cloud-based, no local model needed.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = "gemini-embedding-001"):
        if not hasattr(self, 'genai_client'):
            self.model_name = model_name
            self.embedding_dim = 3072
            self.genai_client = genai.Client(api_key=settings.LLM_API_KEY)
            logger.info(f"EmbeddingService initialized: {self.model_name} (dim={self.embedding_dim})")
    
    def encode(self, texts: Union[str, List[str]], 
               batch_size: int = 100,
               show_progress: bool = False,
               normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for text(s) via Google Gemini API.
        
        Returns:
            numpy array of embeddings, shape (n_texts, embedding_dim)
        """
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                response = self.genai_client.models.embed_content(
                    model=self.model_name,
                    contents=batch_texts
                )
                batch_embeddings = [emb.values for emb in response.embeddings]
                all_embeddings.extend(batch_embeddings)
            
            embeddings = np.array(all_embeddings, dtype=np.float32)
            
            if normalize:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1e-10
                embeddings = embeddings / norms
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        try:
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
            return float(np.dot(embedding1, embedding2))
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def batch_similarity(self, query_embedding: np.ndarray, 
                        chunk_embeddings: np.ndarray) -> np.ndarray:
        """Compute similarity between one query and multiple chunks."""
        try:
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
            chunk_embeddings_norm = chunk_embeddings / chunk_norms
            return np.dot(chunk_embeddings_norm, query_norm)
        except Exception as e:
            logger.error(f"Error in batch similarity: {e}")
            return np.zeros(len(chunk_embeddings))
            
    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "device": "Google Cloud API",
        }
    
    def unload_model(self):
        """Cloud API — nothing to unload."""
        logger.info("Cloud embedding model is stateless; nothing to unload.")


def encode_text(text: str) -> np.ndarray:
    """Quick function to encode single text."""
    service = EmbeddingService()
    return service.encode(text)[0]