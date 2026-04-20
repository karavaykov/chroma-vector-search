#!/usr/bin/env python3
"""
Indexing Service for Chroma Vector Search
Handles codebase indexing and embedding generation
"""

import os
import sys
import json
import logging
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection for job tracking
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Pydantic models for API
class IndexRequest(BaseModel):
    project_root: str = Field(default=".", description="Project root directory")
    file_patterns: List[str] = Field(
        default=["**/*.java", "**/*.py", "**/*.js", "**/*.ts", "**/*.bsl", "**/*.os"],
        description="File patterns to index"
    )
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    collection_name: str = Field(default="codebase_vectors", description="Chroma collection name")
    batch_size: int = Field(default=1000, description="Batch size for processing")

class IndexResponse(BaseModel):
    job_id: str
    status: str
    message: str
    timestamp: datetime

class IndexStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float  # 0.0 to 1.0
    total_files: int
    processed_files: int
    total_chunks: int
    processed_chunks: int
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

# Reuse existing dataclasses from chroma_simple_server.py
@dataclass
class EnterpriseMetadata:
    """Enterprise metadata for 1C/BSL code"""
    object_type: str = ""
    object_name: str = ""
    module_type: str = ""
    subsystem: str = ""
    author: str = ""
    created_date: str = ""
    modified_date: str = ""
    version: str = ""
    description: str = ""
    parameters: List[str] = None
    return_type: str = ""
    export: bool = False
    deprecated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_name": self.object_name,
            "module_type": self.module_type,
            "subsystem": self.subsystem,
            "author": self.author,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "version": self.version,
            "description": self.description,
            "parameters": json.dumps(self.parameters) if self.parameters else "",
            "return_type": self.return_type,
            "export": str(self.export),
            "deprecated": str(self.deprecated)
        }

@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata"""
    content: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    chunk_id: str
    enterprise_metadata: Optional[EnterpriseMetadata] = None

class IndexingService:
    """Service for indexing codebases"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.model_cache = {}
        
    def initialize(self, collection_name: str = "codebase_vectors"):
        """Initialize ChromaDB and embedding model"""
        try:
            # Initialize ChromaDB with persistent storage
            chroma_path = Path(".chroma_db").resolve()
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Codebase vectors for semantic search"}
            )
            
            # Initialize embedding model with caching
            model_name = "all-MiniLM-L6-v2"
            if model_name not in self.model_cache:
                self.embedding_model = SentenceTransformer(model_name)
                self.model_cache[model_name] = self.embedding_model
            else:
                self.embedding_model = self.model_cache[model_name]
                
            logger.info(f"Indexing service initialized with collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize indexing service: {e}")
            return False
    
    def encode_with_cache(self, texts: List[str]) -> List[List[float]]:
        """Encode texts with caching"""
        return self.embedding_model.encode(texts).tolist()
    
    def _process_file(self, file_path: Path) -> List[CodeChunk]:
        """Process a single file into chunks"""
        # This is a simplified version - actual implementation would reuse logic from chroma_simple_server.py
        chunks = []
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Simple chunking by lines
            chunk_size = 50
            for i in range(0, len(lines), chunk_size):
                chunk_lines = lines[i:i + chunk_size]
                chunk_content = '\n'.join(chunk_lines)
                
                chunk = CodeChunk(
                    content=chunk_content,
                    file_path=str(file_path.relative_to(Path.cwd())),
                    line_start=i + 1,
                    line_end=i + len(chunk_lines),
                    language=self._detect_language(file_path),
                    chunk_id=f"{file_path.name}_{i}"
                )
                chunks.append(chunk)
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            
        return chunks
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext = file_path.suffix.lower()
        language_map = {
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.bsl': 'bsl',
            '.os': '1c',
            '.md': 'markdown',
            '.txt': 'text'
        }
        return language_map.get(ext, 'unknown')
    
    async def index_codebase(self, job_id: str, request: IndexRequest) -> Dict[str, Any]:
        """Index codebase asynchronously"""
        try:
            # Update job status
            self._update_job_status(job_id, "running", 0.0)
            
            # Initialize service
            if not self.initialize(request.collection_name):
                raise Exception("Failed to initialize indexing service")
            
            project_root = Path(request.project_root).resolve()
            if not project_root.exists():
                raise Exception(f"Project root does not exist: {project_root}")
            
            # Collect files
            all_files = []
            for pattern in request.file_patterns:
                files = list(project_root.rglob(pattern))
                all_files.extend(files)
            
            # Remove duplicates
            all_files = list(set(all_files))
            total_files = len(all_files)
            
            logger.info(f"Found {total_files} files to index")
            
            # Process files in batches
            chunks = []
            processed_files = 0
            
            for i, file_path in enumerate(all_files):
                # Check file size
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > request.max_file_size_mb:
                    logger.warning(f"Skipping large file: {file_path} ({file_size_mb:.2f} MB)")
                    continue
                
                # Process file
                file_chunks = self._process_file(file_path)
                chunks.extend(file_chunks)
                
                processed_files += 1
                
                # Update progress
                progress = processed_files / total_files
                self._update_job_status(
                    job_id, "running", progress,
                    total_files=total_files,
                    processed_files=processed_files,
                    total_chunks=len(chunks)
                )
                
                # Process batch if size reached
                if len(chunks) >= request.batch_size:
                    await self._process_batch(chunks)
                    chunks = []
            
            # Process remaining chunks
            if chunks:
                await self._process_batch(chunks)
            
            # Finalize
            total_documents = self.collection.count()
            self._update_job_status(
                job_id, "completed", 1.0,
                total_files=total_files,
                processed_files=processed_files,
                total_chunks=total_documents
            )
            
            return {
                "job_id": job_id,
                "status": "completed",
                "total_files": total_files,
                "processed_files": processed_files,
                "total_chunks": total_documents,
                "collection_name": request.collection_name
            }
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            self._update_job_status(job_id, "failed", 0.0, error_message=str(e))
            raise
    
    async def _process_batch(self, chunks: List[CodeChunk]):
        """Process a batch of chunks"""
        if not chunks:
            return
        
        try:
            # Prepare data for Chroma
            ids = []
            documents = []
            metadatas = []
            
            for chunk in chunks:
                chunk_id = f"{chunk.file_path}:{chunk.line_start}-{chunk.line_end}:{hash(chunk.content) & 0xffffffff}"
                ids.append(chunk_id)
                documents.append(chunk.content)
                
                metadata = {
                    "file_path": chunk.file_path,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "language": chunk.language,
                    "chunk_id": chunk.chunk_id
                }
                
                if chunk.enterprise_metadata:
                    metadata.update(chunk.enterprise_metadata.to_dict())
                
                metadatas.append(metadata)
            
            # Generate embeddings
            embeddings = self.encode_with_cache(documents)
            
            # Add to Chroma
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Processed batch of {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise
    
    def _update_job_status(self, job_id: str, status: str, progress: float, **kwargs):
        """Update job status in Redis"""
        try:
            status_data = {
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            redis_client.setex(f"indexing_job:{job_id}", 3600, json.dumps(status_data))
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from Redis"""
        try:
            data = redis_client.get(f"indexing_job:{job_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
        return None

# FastAPI app
app = FastAPI(
    title="Indexing Service",
    description="Service for indexing codebases into ChromaDB",
    version="1.0.0"
)

indexing_service = IndexingService()

@app.post("/index", response_model=IndexResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_indexing(request: IndexRequest, background_tasks: BackgroundTasks):
    """Start indexing job"""
    job_id = str(uuid.uuid4())
    
    # Store initial job status
    initial_status = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "start_time": datetime.now().isoformat(),
        "total_files": 0,
        "processed_files": 0,
        "total_chunks": 0
    }
    redis_client.setex(f"indexing_job:{job_id}", 3600, json.dumps(initial_status))
    
    # Start indexing in background
    background_tasks.add_task(indexing_service.index_codebase, job_id, request)
    
    return IndexResponse(
        job_id=job_id,
        status="pending",
        message="Indexing job started",
        timestamp=datetime.now()
    )

@app.get("/index/status/{job_id}", response_model=IndexStatus)
async def get_indexing_status(job_id: str):
    """Get indexing job status"""
    status_data = indexing_service.get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return IndexStatus(**status_data)

@app.delete("/index/{collection_name}")
async def delete_index(collection_name: str):
    """Delete collection"""
    try:
        if indexing_service.chroma_client:
            indexing_service.chroma_client.delete_collection(collection_name)
            return {"message": f"Collection '{collection_name}' deleted"}
        else:
            raise HTTPException(status_code=500, detail="Indexing service not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "indexing",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)