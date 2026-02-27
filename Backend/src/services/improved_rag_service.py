"""
Improved RAG Service with chunking and semantic search.
Uses Google text-embedding-004 via EmbeddingService (cloud-based).
"""

import logging
from typing import List, Dict
import numpy as np
from dataclasses import dataclass
from .document_loader import DocumentLoader, Document
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    doc_id: str
    chunk_index: int
    metadata: Dict
    embedding: np.ndarray = None


class ImprovedRAGService:
    """Enhanced RAG with chunking and semantic search via Google Embeddings."""
    
    def __init__(
        self, 
        document_loader: DocumentLoader, 
        chunk_size: int = 300,
        chunk_overlap: int = 50
    ):
        self.document_loader = document_loader
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[Chunk] = []
        self.chunk_embeddings = None
        
        # Use the centralized cloud EmbeddingService
        try:
            self.embedding_service = EmbeddingService()
            logger.info(f"Using EmbeddingService: {self.embedding_service.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize EmbeddingService: {e}")
            self.embedding_service = None
        
        self._initialize_with_chunking()
    
    def _split_text_into_chunks(self, text: str, metadata: Dict, doc_id: str) -> List[Chunk]:
        """Split text into overlapping chunks."""
        chunks = []
        text_length = len(text)
        
        if text_length <= self.chunk_size:
            chunks.append(Chunk(
                text=text,
                doc_id=doc_id,
                chunk_index=0,
                metadata=metadata
            ))
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < text_length:
            end = start + self.chunk_size
            
            if end < text_length:
                for marker in ['. ', '! ', '? ', '.\n', '\n']:
                    last_marker = text.rfind(marker, start, end)
                    if last_marker != -1:
                        end = last_marker + len(marker)
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(Chunk(
                    text=chunk_text,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    metadata=metadata
                ))
                chunk_index += 1
            
            start = end - self.chunk_overlap
            if start >= text_length:
                break
        
        return chunks
    
    def _initialize_with_chunking(self):
        """Load documents, split into chunks, and create embeddings."""
        try:
            documents = self.document_loader.load_documents()
            
            if not documents:
                logger.warning("No documents loaded for RAG")
                return
            
            logger.info(f"Processing {len(documents)} documents with chunking...")
            
            all_chunks = []
            for doc in documents:
                doc_chunks = self._split_text_into_chunks(
                    text=doc.content,
                    metadata=doc.metadata,
                    doc_id=doc.id
                )
                all_chunks.extend(doc_chunks)
            
            self.chunks = all_chunks
            logger.info(f"Created {len(self.chunks)} chunks from {len(documents)} documents")
            
            if self.embedding_service and self.chunks:
                chunk_texts = []
                for chunk in self.chunks:
                    enriched_text = chunk.text
                    if 'subject' in chunk.metadata:
                        enriched_text = f"Пән: {chunk.metadata['subject']}. {enriched_text}"
                    if 'topic' in chunk.metadata:
                        enriched_text = f"{enriched_text} Тақырып: {chunk.metadata['topic']}"
                    chunk_texts.append(enriched_text)
                
                logger.info(f"Creating embeddings for {len(chunk_texts)} chunks via Google API...")
                
                # EmbeddingService.encode() handles batching internally
                self.chunk_embeddings = self.embedding_service.encode(
                    chunk_texts,
                    batch_size=100,
                )
                logger.info(f"Created embeddings: {self.chunk_embeddings.shape}")
            
        except Exception as e:
            logger.error(f"Error initializing documents with chunking: {e}", exc_info=True)
            self.chunks = []
            self.chunk_embeddings = None
    
    def retrieve_relevant_documents(
        self, 
        query: str, 
        top_k: int = 3, 
        similarity_threshold: float = 0.3
    ) -> str:
        """
        Retrieve relevant chunks using semantic similarity.
        """
        if not self.chunks or self.chunk_embeddings is None:
            logger.warning("No chunks or embeddings available")
            return ""
        
        try:
            query_embedding = self.embedding_service.encode(query)[0]
            
            similarities = self.embedding_service.batch_similarity(
                query_embedding, self.chunk_embeddings
            )
            
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            relevant_chunks = []
            seen_docs = set()
            
            for idx in top_indices:
                similarity = similarities[idx]
                
                if similarity >= similarity_threshold:
                    chunk = self.chunks[idx]
                    relevant_chunks.append((chunk, similarity))
                    seen_docs.add(chunk.doc_id)
            
            if not relevant_chunks:
                logger.info(f"No relevant chunks found for query: {query[:50]}...")
                return ""
            
            context_parts = []
            for i, (chunk, similarity) in enumerate(relevant_chunks, 1):
                context_parts.append(
                    f"--- Дереккөз {i} (релевантность: {similarity:.2f}) ---\n"
                    f"ID: {chunk.doc_id} [chunk {chunk.chunk_index}]\n"
                    f"Пән: {chunk.metadata.get('subject', 'Белгісіз')}\n"
                    f"Тақырып: {chunk.metadata.get('topic', 'Белгісіз')}\n"
                    f"Мазмұн:\n{chunk.text}\n"
                )
            
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for query: {query[:50]}...")
            return "\n" + "="*70 + "\n" + "\n".join(context_parts)
        
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return ""
    
    def add_document(self, document: Document):
        """Add a new document, chunk it, and update embeddings."""
        try:
            new_chunks = self._split_text_into_chunks(
                text=document.content,
                metadata=document.metadata,
                doc_id=document.id
            )
            
            self.chunks.extend(new_chunks)
            
            chunk_texts = []
            for chunk in new_chunks:
                enriched_text = chunk.text
                if 'subject' in chunk.metadata:
                    enriched_text = f"Пән: {chunk.metadata['subject']}. {enriched_text}"
                if 'topic' in chunk.metadata:
                    enriched_text = f"{enriched_text} Тақырып: {chunk.metadata['topic']}"
                chunk_texts.append(enriched_text)
            
            new_embeddings = self.embedding_service.encode(chunk_texts)
            
            if self.chunk_embeddings is None:
                self.chunk_embeddings = new_embeddings
            else:
                self.chunk_embeddings = np.vstack([self.chunk_embeddings, new_embeddings])
            
            logger.info(f"Added document {document.id} as {len(new_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
    
    def get_stats(self) -> dict:
        """Get RAG system statistics."""
        subjects = {}
        for chunk in self.chunks:
            subj = chunk.metadata.get('subject', 'Unknown')
            subjects[subj] = subjects.get(subj, 0) + 1
        
        return {
            "total_chunks": len(self.chunks),
            "total_documents": len(set(c.doc_id for c in self.chunks)),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embeddings_shape": self.chunk_embeddings.shape if self.chunk_embeddings is not None else None,
            "embedding_model": self.embedding_service.model_name if self.embedding_service else None,
            "subjects": subjects,
        }