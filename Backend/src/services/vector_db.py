import json
import logging
import numpy as np
import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PayloadSchemaType
)
from ..config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"
VECTOR_DIM = 3072  # gemini-embedding-001


class VectorDB:
    """
    Qdrant Cloud vector database for semantic search.
    Drop-in replacement for old SQLite-based VectorDB.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize Qdrant Cloud connection.
        
        Args:
            db_path: Ignored (kept for interface compatibility). 
                     Connection is configured via settings/env.
        """
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self._ensure_collection()
        logger.info(f"VectorDB connected to Qdrant Cloud: {settings.QDRANT_URL}")
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for filtered search
            for field in ["document_id", "subject", "topic", "difficulty"]:
                self.client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            logger.info(f"Created Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_DIM})")
        else:
            logger.info(f"Qdrant collection '{COLLECTION_NAME}' already exists")
    
    def add_document(self, doc_id: str, source_file: str, 
                    metadata: Dict = None) -> bool:
        """
        Register a document (metadata only, stored as payload on chunks).
        Kept for interface compatibility — actual storage happens in add_chunks.
        """
        self._doc_metadata_cache = getattr(self, '_doc_metadata_cache', {})
        self._doc_metadata_cache[doc_id] = {
            'source_file': source_file,
            **(metadata or {})
        }
        logger.debug(f"Document '{doc_id}' metadata registered")
        return True
    
    def add_chunks(self, document_id: str, chunks: List[Dict], 
                   embeddings: np.ndarray) -> int:
        """
        Upsert chunks with embeddings into Qdrant.
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError(f"Chunks ({len(chunks)}) != embeddings ({len(embeddings)})")
            
            doc_meta = getattr(self, '_doc_metadata_cache', {}).get(document_id, {})
            
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                point_id = str(uuid.uuid4())
                payload = {
                    "document_id": document_id,
                    "chunk_index": chunk['chunk_index'],
                    "content": chunk['content'],
                    "token_count": chunk.get('token_count'),
                    "subject": doc_meta.get('subject'),
                    "topic": doc_meta.get('topic'),
                    "difficulty": doc_meta.get('difficulty'),
                    "source_file": doc_meta.get('source_file', 'unknown'),
                    "language": doc_meta.get('language', 'kk'),
                    "chunk_metadata": chunk.get('metadata', {}),
                }
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload,
                ))
            
            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(points), batch_size):
                self.client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points[i:i + batch_size],
                )
            
            logger.info(f"Upserted {len(points)} chunks for document '{document_id}'")
            return len(points)
            
        except Exception as e:
            logger.error(f"Error adding chunks for '{document_id}': {e}")
            return 0
    
    def search(self, query_embedding: np.ndarray, 
               top_k: int = 5,
               filters: Dict = None,
               min_similarity: float = 0.0) -> List[Dict]:
        """
        Search for most similar chunks via Qdrant Cloud.
        Cosine similarity is computed server-side.
        """
        try:
            filters = filters or {}
            
            # Build Qdrant filter
            must_conditions = []
            for key in ['subject', 'topic', 'difficulty', 'document_id']:
                if key in filters:
                    must_conditions.append(
                        FieldCondition(field=key, match=MatchValue(value=filters[key]))
                    )
            
            qdrant_filter = Filter(must=must_conditions) if must_conditions else None
            
            hits = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding.tolist(),
                query_filter=qdrant_filter,
                limit=top_k,
                score_threshold=min_similarity if min_similarity > 0 else None,
            )
            
            results = []
            for hit in hits:
                p = hit.payload
                results.append({
                    'chunk_id': hit.id,
                    'document_id': p.get('document_id'),
                    'chunk_index': p.get('chunk_index'),
                    'content': p.get('content'),
                    'token_count': p.get('token_count'),
                    'metadata': p.get('chunk_metadata', {}),
                    'subject': p.get('subject'),
                    'topic': p.get('topic'),
                    'difficulty': p.get('difficulty'),
                    'source_file': p.get('source_file'),
                    'similarity': hit.score,
                })
            
            logger.info(f"Qdrant search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
    def get_document_stats(self, doc_id: str) -> Optional[Dict]:
        """Get statistics for a specific document."""
        try:
            hits = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(must=[
                    FieldCondition(field="document_id", match=MatchValue(value=doc_id))
                ]),
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )[0]
            
            if not hits:
                return None
            
            token_counts = [h.payload.get('token_count', 0) or 0 for h in hits]
            first = hits[0].payload
            
            return {
                'id': doc_id,
                'source_file': first.get('source_file'),
                'subject': first.get('subject'),
                'topic': first.get('topic'),
                'difficulty': first.get('difficulty'),
                'language': first.get('language'),
                'chunk_count': len(hits),
                'avg_chunk_tokens': sum(token_counts) / max(len(token_counts), 1),
            }
        except Exception as e:
            logger.error(f"Error getting stats for '{doc_id}': {e}")
            return None
    
    def get_database_stats(self) -> Dict:
        """Get overall database statistics."""
        try:
            collection_info = self.client.get_collection(COLLECTION_NAME)
            total_chunks = collection_info.points_count or 0
            
            # Get a sample to count unique documents and subjects
            all_points = []
            offset = None
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=1000,
                    offset=offset,
                    with_payload=["document_id", "subject", "token_count"],
                    with_vectors=False,
                )
                all_points.extend(points)
                if next_offset is None:
                    break
                offset = next_offset
            
            doc_ids = set()
            subjects = {}
            total_tokens = 0
            token_counts = []
            
            for p in all_points:
                payload = p.payload
                doc_ids.add(payload.get('document_id'))
                subj = payload.get('subject')
                if subj:
                    subjects[subj] = subjects.get(subj, 0) + 1
                tc = payload.get('token_count') or 0
                total_tokens += tc
                token_counts.append(tc)
            
            return {
                'total_documents': len(doc_ids),
                'total_chunks': total_chunks,
                'avg_chunk_size': sum(token_counts) / max(len(token_counts), 1),
                'total_tokens': total_tokens,
                'subjects_distribution': subjects,
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks belonging to a document."""
        try:
            self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[
                    FieldCondition(field="document_id", match=MatchValue(value=doc_id))
                ]),
            )
            logger.info(f"Document '{doc_id}' deleted from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error deleting document '{doc_id}': {e}")
            return False
    
    def clear_database(self) -> bool:
        """Delete the collection and recreate it."""
        try:
            self.client.delete_collection(collection_name=COLLECTION_NAME)
            self._ensure_collection()
            logger.info("Qdrant collection cleared and recreated")
            return True
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False