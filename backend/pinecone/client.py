from __future__ import annotations
from pinecone import Pinecone, FetchResponse
from typing import Iterable, List, Optional, Tuple, Any
from models.chunks import CourseChunk, ChunkMetadata


class PineconeClient:
    """
    This class centralizes configuration (api key + index name) and provides
    convenience helpers for batch upserting, namespace handling, and simple query/fetch
    operations.
    """

    def __init__(self,
        api_key: str,
        index_name: str,
        namespace: Optional[str] = None,
    ):
        self._pc = Pinecone(api_key=api_key)
        self._index = self._pc.Index(index_name)
        self.namespace = namespace

    def _effective_namespace(self,
        namespace: Optional[str]
    ) -> Optional[str]:
        """Set namespace within client."""
      
        return namespace if namespace is not None else self.namespace

    def create_record(self, 
        id: str, 
        embeddings: List[float], 
        metadata: ChunkMetadata
    ) -> Tuple[str, List[float], dict]:
        
        """Create the Pinecone Chunk in the correct format for upserts."""
        
        chunk = CourseChunk(id=id, values=embeddings, metadata=metadata)
        return chunk.to_pinecone_record()

    
    def upsert(self,
        records: Iterable[Tuple[str, List[float], dict]],
        namespace: Optional[str] = None,
        batch_size: int = 50,
    ) -> None:

        """Upsert records in batches."""

        ns = self._effective_namespace(namespace)
        batch: List[Tuple[str, List[float], dict]] = []

        for record in records:
            batch.append(record)
            if len(batch) >= batch_size:
                self._index.upsert(vectors=batch, namespace=ns)
                batch.clear()

        if batch:
            self._index.upsert(vectors=batch, namespace=ns)

    
    def fetch_by_id(self,
        ids: List[str],
        namespace: Optional[str] = None,
    ) -> FetchResponse:
        
        """Search the index with a specified ID."""

        ns = self._effective_namespace(namespace)
        return self._index.fetch(ids=ids, namespace=ns)

    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        include_metadata: bool = True,
    ) -> Any :
        
        """Search the index by semantic query."""

        ns = self._effective_namespace(namespace)
        return self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=ns,
            include_metadata=include_metadata,
        )
