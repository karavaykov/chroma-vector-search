#!/usr/bin/env python3
"""
Metadata Service for Chroma Vector Search
Manages metadata and statistics
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

import chromadb
from chromadb.config import Settings
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
redis_client = redis.Redis(host='redis', port=6379, db=2)

# Pydantic models for API
class CollectionStats(BaseModel):
    collection_name: str
    total_documents: int
    total_files: int
    languages: Dict[str, int]
    object_types: Dict[str, int]
    file_extensions: Dict[str, int]
    indexed_at: Optional[datetime]
    last_updated: Optional[datetime]
    average_chunk_size: float
    metadata_fields: List[str]

class FileInfo(BaseModel):
    file_path: str
    language: str
    chunk_count: int
    total_lines: int
    indexed_at: datetime
    object_type: Optional[str] = None
    object_name: Optional[str] = None

class UpdateMetadataRequest(BaseModel):
    chunk_id: str
    metadata: Dict[str, Any]

class MetadataService:
    """Service for managing metadata and statistics"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
    
    def initialize(self, collection_name: str = "codebase_vectors"):
        """Initialize ChromaDB connection"""
        try:
            chroma_path = Path(".chroma_db").resolve()
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Metadata service initialized with collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize metadata service: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str = "codebase_vectors") -> CollectionStats:
        """Get comprehensive statistics about a collection"""
        cache_key = f"stats:{collection_name}"
        cached_stats = redis_client.get(cache_key)
        if cached_stats:
            return CollectionStats(**json.loads(cached_stats))
        
        if not self.collection or self.collection.name != collection_name:
            if not self.initialize(collection_name):
                raise HTTPException(status_code=500, detail="Failed to initialize metadata service")
        
        try:
            # Get all metadata
            results = self.collection.get(include=["metadatas"])
            metadatas = results["metadatas"]
            
            if not metadatas:
                return CollectionStats(
                    collection_name=collection_name,
                    total_documents=0,
                    total_files=0,
                    languages={},
                    object_types={},
                    file_extensions={},
                    average_chunk_size=0,
                    metadata_fields=[]
                )
            
            # Calculate statistics
            languages = Counter()
            object_types = Counter()
            file_extensions = Counter()
            file_paths = set()
            total_lines = 0
            metadata_fields = set()
            
            for metadata in metadatas:
                # Language statistics
                lang = metadata.get("language", "unknown")
                languages[lang] += 1
                
                # Object type statistics (for 1C/BSL)
                obj_type = metadata.get("object_type", "")
                if obj_type:
                    object_types[obj_type] += 1
                
                # File statistics
                file_path = metadata.get("file_path", "")
                if file_path:
                    file_paths.add(file_path)
                    # Extract file extension
                    if "." in file_path:
                        ext = file_path.split(".")[-1].lower()
                        file_extensions[ext] += 1
                
                # Line count
                line_start = metadata.get("line_start", 0)
                line_end = metadata.get("line_end", 0)
                if line_end > line_start:
                    total_lines += (line_end - line_start + 1)
                
                # Collect metadata fields
                metadata_fields.update(metadata.keys())
            
            # Calculate averages
            total_documents = len(metadatas)
            total_files = len(file_paths)
            average_chunk_size = total_lines / total_documents if total_documents > 0 else 0
            
            # Get collection metadata for timestamps
            collection_info = self.collection.metadata or {}
            indexed_at = collection_info.get("created_at")
            last_updated = collection_info.get("updated_at")
            
            stats = CollectionStats(
                collection_name=collection_name,
                total_documents=total_documents,
                total_files=total_files,
                languages=dict(languages),
                object_types=dict(object_types),
                file_extensions=dict(file_extensions),
                indexed_at=datetime.fromisoformat(indexed_at) if indexed_at else None,
                last_updated=datetime.fromisoformat(last_updated) if last_updated else None,
                average_chunk_size=average_chunk_size,
                metadata_fields=list(metadata_fields)
            )
            
            # Cache for 5 minutes
            redis_client.setex(cache_key, 300, json.dumps(stats.dict()))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_files(self, collection_name: str = "codebase_vectors") -> List[FileInfo]:
        """List all indexed files with their metadata"""
        cache_key = f"files:{collection_name}"
        cached_files = redis_client.get(cache_key)
        if cached_files:
            return [FileInfo(**f) for f in json.loads(cached_files)]
        
        if not self.collection or self.collection.name != collection_name:
            if not self.initialize(collection_name):
                raise HTTPException(status_code=500, detail="Failed to initialize metadata service")
        
        try:
            # Get all metadata grouped by file
            results = self.collection.get(include=["metadatas"])
            metadatas = results["metadatas"]
            
            # Group by file path
            files_dict = {}
            for metadata in metadatas:
                file_path = metadata.get("file_path", "")
                if not file_path:
                    continue
                
                if file_path not in files_dict:
                    files_dict[file_path] = {
                        "file_path": file_path,
                        "language": metadata.get("language", "unknown"),
                        "chunk_count": 0,
                        "total_lines": 0,
                        "object_type": metadata.get("object_type"),
                        "object_name": metadata.get("object_name"),
                        "indexed_at": metadata.get("indexed_at", datetime.now().isoformat())
                    }
                
                files_dict[file_path]["chunk_count"] += 1
                
                # Calculate total lines
                line_start = metadata.get("line_start", 0)
                line_end = metadata.get("line_end", 0)
                if line_end > line_start:
                    files_dict[file_path]["total_lines"] += (line_end - line_start + 1)
            
            # Convert to FileInfo objects
            files = []
            for file_data in files_dict.values():
                files.append(FileInfo(
                    file_path=file_data["file_path"],
                    language=file_data["language"],
                    chunk_count=file_data["chunk_count"],
                    total_lines=file_data["total_lines"],
                    indexed_at=datetime.fromisoformat(file_data["indexed_at"]) if isinstance(file_data["indexed_at"], str) else datetime.now(),
                    object_type=file_data["object_type"],
                    object_name=file_data["object_name"]
                ))
            
            # Sort by file path
            files.sort(key=lambda x: x.file_path)
            
            # Cache for 5 minutes
            redis_client.setex(cache_key, 300, json.dumps([f.dict() for f in files]))
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_metadata(self, request: UpdateMetadataRequest) -> Dict[str, Any]:
        """Update metadata for a specific chunk"""
        try:
            # Get current metadata
            results = self.collection.get(
                ids=[request.chunk_id],
                include=["metadatas"]
            )
            
            if not results["metadatas"]:
                raise HTTPException(status_code=404, detail="Chunk not found")
            
            current_metadata = results["metadatas"][0]
            
            # Update metadata
            updated_metadata = {**current_metadata, **request.metadata}
            updated_metadata["updated_at"] = datetime.now().isoformat()
            
            # Update in Chroma
            self.collection.update(
                ids=[request.chunk_id],
                metadatas=[updated_metadata]
            )
            
            # Invalidate caches
            self._invalidate_caches()
            
            return {
                "chunk_id": request.chunk_id,
                "updated_metadata": updated_metadata,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_metadata_schema(self, collection_name: str = "codebase_vectors") -> Dict[str, Any]:
        """Get metadata schema for a collection"""
        cache_key = f"schema:{collection_name}"
        cached_schema = redis_client.get(cache_key)
        if cached_schema:
            return json.loads(cached_schema)
        
        if not self.collection or self.collection.name != collection_name:
            if not self.initialize(collection_name):
                raise HTTPException(status_code=500, detail="Failed to initialize metadata service")
        
        try:
            # Get sample metadata to infer schema
            results = self.collection.get(limit=100, include=["metadatas"])
            metadatas = results["metadatas"]
            
            if not metadatas:
                return {"fields": [], "types": {}}
            
            # Analyze metadata fields
            field_types = {}
            field_values = {}
            
            for metadata in metadatas:
                for key, value in metadata.items():
                    if key not in field_values:
                        field_values[key] = []
                    field_values[key].append(value)
            
            # Infer types
            for key, values in field_values.items():
                # Check if all values are of the same type
                types = set(type(v).__name__ for v in values if v is not None)
                if len(types) == 1:
                    field_types[key] = list(types)[0]
                elif len(types) > 1:
                    field_types[key] = "mixed"
                else:
                    field_types[key] = "unknown"
            
            schema = {
                "collection_name": collection_name,
                "total_fields": len(field_types),
                "fields": list(field_types.keys()),
                "field_types": field_types,
                "sample_size": len(metadatas)
            }
            
            # Cache for 10 minutes
            redis_client.setex(cache_key, 600, json.dumps(schema))
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get metadata schema: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _invalidate_caches(self):
        """Invalidate all metadata caches"""
        try:
            # Delete all cache keys starting with stats:, files:, schema:
            for pattern in ["stats:*", "files:*", "schema:*"]:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to invalidate caches: {e}")

# FastAPI app
app = FastAPI(
    title="Metadata Service",
    description="Service for managing metadata and statistics",
    version="1.0.0"
)

metadata_service = MetadataService()

@app.get("/metadata/stats", response_model=CollectionStats)
async def get_stats(collection_name: str = "codebase_vectors"):
    """Get collection statistics"""
    return metadata_service.get_collection_stats(collection_name)

@app.get("/metadata/files", response_model=List[FileInfo])
async def list_files(collection_name: str = "codebase_vectors"):
    """List indexed files"""
    return metadata_service.list_files(collection_name)

@app.post("/metadata/update")
async def update_metadata(request: UpdateMetadataRequest):
    """Update chunk metadata"""
    return metadata_service.update_metadata(request)

@app.get("/metadata/schema")
async def get_schema(collection_name: str = "codebase_vectors"):
    """Get metadata schema"""
    return metadata_service.get_metadata_schema(collection_name)

@app.get("/metadata/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "metadata",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)