#!/usr/bin/env python3
"""
Search Service for Chroma Vector Search
Handles semantic search queries
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection for caching
redis_client = redis.Redis(host='redis', port=6379, db=1)

# Pydantic models for API
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    n_results: int = Field(default=5, description="Number of results to return")
    collection_name: str = Field(default="codebase_vectors", description="Chroma collection name")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")
    where_document: Optional[Dict[str, Any]] = Field(default=None, description="Document filters")

class SearchResult(BaseModel):
    rank: int
    similarity_score: float
    content: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    chunk_id: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    collection_name: str
    processing_time_ms: float

class SimilarRequest(BaseModel):
    chunk_id: str = Field(..., description="Chunk ID to find similar items")
    n_results: int = Field(default=5, description="Number of similar results")

class SearchService:
    """Service for semantic search"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.model_cache = {}
    
    def initialize(self, collection_name: str = "codebase_vectors"):
        """Initialize ChromaDB and embedding model"""
        try:
            # Initialize ChromaDB
            chroma_path = Path(".chroma_db").resolve()
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get collection
            self.collection = self.chroma_client.get_collection(collection_name)
            
            # Initialize embedding model with caching
            model_name = "all-MiniLM-L6-v2"
            if model_name not in self.model_cache:
                self.embedding_model = SentenceTransformer(model_name)
                self.model_cache[model_name] = self.embedding_model
            else:
                self.embedding_model = self.model_cache[model_name]
                
            logger.info(f"Search service initialized with collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize search service: {e}")
            return False
    
    def encode_query(self, query: str) -> List[float]:
        """Encode search query"""
        return self.embedding_model.encode(query).tolist()
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """Perform semantic search"""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = f"search:{hash(json.dumps(request.dict()))}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for query: {request.query}")
            result_data = json.loads(cached_result)
            result_data["cached"] = True
            return SearchResponse(**result_data)
        
        # Initialize if needed
        if not self.collection or self.collection.name != request.collection_name:
            if not self.initialize(request.collection_name):
                raise HTTPException(status_code=500, detail="Failed to initialize search service")
        
        try:
            # Encode query
            query_embedding = self.encode_query(request.query)
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=request.n_results,
                where=request.filters,
                where_document=request.where_document,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
                ):
                    # Convert distance to similarity score (1 - normalized distance)
                    similarity_score = 1.0 - (distance / 2.0)  # Simple normalization
                    
                    result = SearchResult(
                        rank=i + 1,
                        similarity_score=similarity_score,
                        content=doc,
                        file_path=metadata.get("file_path", ""),
                        line_start=metadata.get("line_start", 0),
                        line_end=metadata.get("line_end", 0),
                        language=metadata.get("language", "unknown"),
                        chunk_id=metadata.get("chunk_id", ""),
                        metadata=metadata
                    )
                    search_results.append(result)
            
            # Calculate processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create response
            response = SearchResponse(
                query=request.query,
                results=search_results,
                total_results=len(search_results),
                collection_name=request.collection_name,
                processing_time_ms=processing_time_ms
            )
            
            # Cache result (5 minutes TTL)
            redis_client.setex(cache_key, 300, json.dumps(response.dict()))
            
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def search_similar(self, request: SimilarRequest) -> SearchResponse:
        """Find similar chunks to a given chunk"""
        start_time = datetime.now()
        
        try:
            # Get the chunk by ID
            chunk_result = self.collection.get(
                ids=[request.chunk_id],
                include=["embeddings", "documents", "metadatas"]
            )
            
            if not chunk_result["embeddings"]:
                raise HTTPException(status_code=404, detail="Chunk not found")
            
            # Use the chunk's embedding to find similar items
            results = self.collection.query(
                query_embeddings=chunk_result["embeddings"],
                n_results=request.n_results + 1,  # +1 to exclude the original
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results (skip the first one which is the original)
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
                ):
                    # Skip the original chunk
                    if metadata.get("chunk_id") == request.chunk_id:
                        continue
                    
                    similarity_score = 1.0 - (distance / 2.0)
                    
                    result = SearchResult(
                        rank=len(search_results) + 1,
                        similarity_score=similarity_score,
                        content=doc,
                        file_path=metadata.get("file_path", ""),
                        line_start=metadata.get("line_start", 0),
                        line_end=metadata.get("line_end", 0),
                        language=metadata.get("language", "unknown"),
                        chunk_id=metadata.get("chunk_id", ""),
                        metadata=metadata
                    )
                    search_results.append(result)
                    
                    if len(search_results) >= request.n_results:
                        break
            
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return SearchResponse(
                query=f"Similar to chunk {request.chunk_id}",
                results=search_results,
                total_results=len(search_results),
                collection_name=self.collection.name,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Similar search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def search_by_metadata(self, filters: Dict[str, Any], n_results: int = 10) -> SearchResponse:
        """Search by metadata filters"""
        start_time = datetime.now()
        
        try:
            results = self.collection.get(
                where=filters,
                limit=n_results,
                include=["documents", "metadatas"]
            )
            
            search_results = []
            for i, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
                result = SearchResult(
                    rank=i + 1,
                    similarity_score=1.0,  # No similarity score for metadata search
                    content=doc,
                    file_path=metadata.get("file_path", ""),
                    line_start=metadata.get("line_start", 0),
                    line_end=metadata.get("line_end", 0),
                    language=metadata.get("language", "unknown"),
                    chunk_id=metadata.get("chunk_id", ""),
                    metadata=metadata
                )
                search_results.append(result)
            
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return SearchResponse(
                query=f"Metadata search: {filters}",
                results=search_results,
                total_results=len(search_results),
                collection_name=self.collection.name,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI app
app = FastAPI(
    title="Search Service",
    description="Service for semantic search in codebases",
    version="1.0.0"
)

search_service = SearchService()

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform semantic search"""
    return search_service.search(request)

@app.post("/search/similar", response_model=SearchResponse)
async def search_similar(request: SimilarRequest):
    """Find similar chunks"""
    return search_service.search_similar(request)

@app.get("/search/metadata")
async def search_by_metadata(
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    object_type: Optional[str] = None,
    n_results: int = 10
):
    """Search by metadata"""
    filters = {}
    if language:
        filters["language"] = language
    if file_path:
        filters["file_path"] = {"$contains": file_path}
    if object_type:
        filters["object_type"] = object_type
    
    return search_service.search_by_metadata(filters, n_results)

@app.get("/collections")
async def list_collections():
    """List available collections"""
    try:
        if not search_service.chroma_client:
            search_service.initialize()
        
        collections = search_service.chroma_client.list_collections()
        return {
            "collections": [{"name": col.name, "count": col.count()} for col in collections]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "search",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)