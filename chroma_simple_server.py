#!/usr/bin/env python3
"""
Simple Chroma Server for OpenCode - Works with Python 3.9
Provides vector search capabilities without MCP dependencies
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import hashlib
import socket
import threading
import time
import pickle
from functools import lru_cache

# Chroma imports
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# WebSocket support
try:
    from websocket_server import WebSocketServer
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("WebSocket support not available. Install with: pip install websockets")

# Hybrid search support
try:
    from keyword_search import KeywordSearchIndex, HybridSearchOptimizer
    from search_fuser import SearchResultFuser, SearchQualityEvaluator
    HYBRID_SEARCH_AVAILABLE = True
except ImportError as e:
    HYBRID_SEARCH_AVAILABLE = False
    logger.warning(f"Hybrid search support not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EnterpriseMetadata:
    """Enterprise metadata for 1C/BSL code"""
    object_type: str = ""  # Procedure, Function, Module, etc.
    object_name: str = ""  # Name of the procedure/function
    module_type: str = ""  # CommonModule, Document, Catalog, etc.
    subsystem: str = ""    # Subsystem name
    author: str = ""       # Author information
    created_date: str = "" # Creation date
    modified_date: str = "" # Last modification date
    version: str = ""      # Version information
    description: str = ""  # Description/comment
    parameters: List[str] = None  # Function/procedure parameters
    return_type: str = ""  # Return type for functions
    export: bool = False   # Is exported
    deprecated: bool = False # Is deprecated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Chroma metadata"""
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
    enterprise_metadata: EnterpriseMetadata = None

@dataclass
class GPUConfig:
    """Configuration for GPU acceleration"""
    enabled: bool = False
    device: str = "auto"  # "auto", "cuda", "cpu", "mps"
    batch_size: int = 32
    use_mixed_precision: bool = True
    cache_size: int = 1000
    
    def __post_init__(self):
        """Validate configuration"""
        if self.device not in ["auto", "cuda", "cpu", "mps"]:
            raise ValueError(f"Invalid device: {self.device}. Must be one of: auto, cuda, cpu, mps")
        
        if self.batch_size < 1:
            raise ValueError(f"Batch size must be positive: {self.batch_size}")
        
        if self.cache_size < 0:
            raise ValueError(f"Cache size must be non-negative: {self.cache_size}")

class ChromaSimpleServer:
    """Simple server for Chroma vector search without MCP"""
    
    def __init__(self, project_root: str = ".", port: int = 8765, gpu_config: GPUConfig = None, websocket_port: int = 8766):
        self.project_root = Path(project_root).resolve()
        self.port = port
        self.websocket_port = websocket_port
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.websocket_server = None
        self.collection_name = "codebase_vectors"
        self.server_socket = None
        self.running = False
        self.device = "cpu"
        
        # GPU configuration
        self.gpu_config = gpu_config if gpu_config else GPUConfig()
        
        # Hybrid search configuration
        self.keyword_index = None
        self.search_fuser = None
        
        # Initialize Chroma
        self._init_chroma()
        
        # Initialize embedding model
        self._init_embedding_model()
        
        # Initialize keyword index if available
        self._init_keyword_index()
    
    def _init_chroma(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Use persistent storage in project directory
            chroma_path = self.project_root / ".chroma_db"
            chroma_path.mkdir(exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Create or get collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Chroma collection '{self.collection_name}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise
    
    def _init_embedding_model(self):
        """Initialize sentence transformer model for embeddings with caching"""
        try:
            if self.gpu_config.enabled:
                self._init_embedding_model_gpu()
            else:
                self._init_embedding_model_cpu()
            
            logger.info(f"Embedding model initialized (device: {self.device}, caching: enabled)")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _init_embedding_model_cpu(self):
        """Initialize model for CPU only"""
        # Use a lightweight model for code embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.device = "cpu"
        
        # Create cached version of encode method
        self._cached_encode = lru_cache(maxsize=self.gpu_config.cache_size)(self._encode_with_cache)
    
    def _init_embedding_model_gpu(self):
        """Initialize model with GPU support"""
        try:
            import torch
            
            # Determine device
            if self.gpu_config.device == "auto":
                if torch.cuda.is_available():
                    self.device = "cuda"
                    logger.info("CUDA GPU detected, using CUDA")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.device = "mps"
                    logger.info("Apple Silicon (MPS) detected, using MPS")
                else:
                    self.device = "cpu"
                    logger.warning("No GPU detected, falling back to CPU")
            else:
                self.device = self.gpu_config.device
            
            # Load model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Move to device
            if self.device != "cpu":
                self.embedding_model.to(self.device)
                logger.info(f"Model moved to {self.device}")
            
            # Enable mixed precision if requested and supported
            if (self.gpu_config.use_mixed_precision and 
                self.device != "cpu" and 
                self.device != "mps"):  # MPS doesn't fully support float16
                try:
                    self.embedding_model.half()
                    logger.info("Mixed precision (float16) enabled")
                except Exception as e:
                    logger.warning(f"Failed to enable mixed precision: {e}")
            
            # Create cached version of encode method
            self._cached_encode = lru_cache(maxsize=self.gpu_config.cache_size)(self._encode_with_cache)
            
            # Warm up model
            self._warm_up_model()
            
        except ImportError:
            logger.warning("PyTorch not installed for GPU support, falling back to CPU")
            self._init_embedding_model_cpu()
        except Exception as e:
            logger.error(f"Failed to initialize GPU model: {e}, falling back to CPU")
            self._init_embedding_model_cpu()
    
    def _warm_up_model(self):
        """Warm up the model with dummy data"""
        try:
            if self.device != "cpu":
                dummy_text = "Model warm up"
                self.embedding_model.encode([dummy_text])
                logger.info("Model warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warm up failed: {e}")
    
    def _init_keyword_index(self):
        """Initialize keyword search index"""
        if not HYBRID_SEARCH_AVAILABLE:
            logger.warning("Hybrid search modules not available. Keyword search will be disabled.")
            return
        
        try:
            self.keyword_index = KeywordSearchIndex()
            self.search_fuser = SearchResultFuser()
            
            # Try to load existing keyword index
            keyword_index_path = self.project_root / ".keyword_index.pkl"
            if keyword_index_path.exists():
                self.keyword_index.load(str(keyword_index_path))
                logger.info(f"Keyword index loaded from {keyword_index_path}, documents: {self.keyword_index.get_document_count()}")
            else:
                logger.info("No existing keyword index found. Will be built during indexing.")
                
        except Exception as e:
            logger.error(f"Failed to initialize keyword index: {e}")
            self.keyword_index = None
            self.search_fuser = None
    
    def _save_keyword_index(self):
        """Save keyword index to disk"""
        if self.keyword_index and HYBRID_SEARCH_AVAILABLE:
            try:
                keyword_index_path = self.project_root / ".keyword_index.pkl"
                self.keyword_index.save(str(keyword_index_path))
                logger.debug(f"Keyword index saved to {keyword_index_path}")
            except Exception as e:
                logger.error(f"Failed to save keyword index: {e}")
    
    def _encode_with_cache(self, text: str) -> List[float]:
        """Cached version of encode method"""
        if self.gpu_config.enabled and self.device != "cpu":
            return self._encode_single_gpu(text)
        else:
            return self.embedding_model.encode([text]).tolist()[0]
    
    def _encode_single_gpu(self, text: str) -> List[float]:
        """Encode single text on GPU"""
        import torch
        
        # Encode on GPU
        embedding = self.embedding_model.encode(
            [text],
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        # Move to CPU and convert to list
        if self.device != "cpu":
            embedding = embedding.cpu()
        
        return embedding.tolist()[0]
    
    def encode_with_cache(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts with caching for duplicates"""
        if self.gpu_config.enabled and self.device != "cpu" and len(texts) > 1:
            return self.encode_batch_gpu(texts)
        
        # Fall back to cached CPU encoding
        unique_texts = list(set(texts))
        text_to_embedding = {}
        
        # Encode unique texts
        for text in unique_texts:
            embedding = self._cached_encode(text)
            text_to_embedding[text] = embedding
        
        # Return embeddings in original order
        return [text_to_embedding[text] for text in texts]
    
    def encode_batch_gpu(self, texts: List[str]) -> List[List[float]]:
        """Encode batch of texts using GPU with optimization"""
        if not texts:
            return []
        
        # Split into batches
        batch_size = self.gpu_config.batch_size
        batches = [texts[i:i + batch_size] 
                  for i in range(0, len(texts), batch_size)]
        
        embeddings = []
        for i, batch in enumerate(batches):
            logger.debug(f"Processing GPU batch {i+1}/{len(batches)} (size: {len(batch)})")
            
            # Encode batch on GPU
            batch_embeddings = self.embedding_model.encode(
                batch,
                convert_to_tensor=True,
                show_progress_bar=False
            )
            
            # Move to CPU and convert to list
            if self.device != "cpu":
                batch_embeddings = batch_embeddings.cpu()
            
            embeddings.extend(batch_embeddings.tolist())
        
        return embeddings
    
    def _generate_chunk_id(self, file_path: str, line_start: int) -> str:
        """Generate unique ID for code chunk"""
        content = f"{file_path}:{line_start}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_1c_metadata(self, lines: List[str], start_line: int, end_line: int, file_path: str) -> EnterpriseMetadata:
        """Extract enterprise metadata from 1C/BSL code block"""
        metadata = EnterpriseMetadata()
        
        # Extract object type and name from first line
        if start_line < len(lines):
            first_line = lines[start_line].strip()
            first_lower = first_line.lower()
            
            if first_lower.startswith('процедура'):
                metadata.object_type = "Procedure"
                # Extract procedure name
                name_start = first_line.find('Процедура') + 9
                name_end = first_line.find('(', name_start) if '(' in first_line else len(first_line)
                metadata.object_name = first_line[name_start:name_end].strip()
                
            elif first_lower.startswith('функция'):
                metadata.object_type = "Function"
                # Extract function name
                name_start = first_line.find('Функция') + 7
                name_end = first_line.find('(', name_start) if '(' in first_line else len(first_line)
                metadata.object_name = first_line[name_start:name_end].strip()
                
            elif first_lower.startswith('procedure'):
                metadata.object_type = "Procedure"
                name_start = first_line.find('Procedure') + 9
                name_end = first_line.find('(', name_start) if '(' in first_line else len(first_line)
                metadata.object_name = first_line[name_start:name_end].strip()
                
            elif first_lower.startswith('function'):
                metadata.object_type = "Function"
                name_start = first_line.find('Function') + 8
                name_end = first_line.find('(', name_start) if '(' in first_line else len(first_line)
                metadata.object_name = first_line[name_start:name_end].strip()
        
        # Extract parameters from first line
        if '(' in first_line and ')' in first_line:
            params_start = first_line.find('(') + 1
            params_end = first_line.find(')', params_start)
            params_str = first_line[params_start:params_end].strip()
            if params_str:
                metadata.parameters = [p.strip() for p in params_str.split(',')]
        
        # Extract return type for functions
        if metadata.object_type == "Function" and 'возврат' in first_lower:
            return_start = first_lower.find('возврат')
            metadata.return_type = first_line[return_start + 7:].strip()
        
        # Check for export keyword (can be for both procedures and functions)
        if 'экспорт' in first_lower or 'export' in first_lower:
            metadata.export = True
        
        # Look for comments and metadata in preceding lines
        comment_lines = []
        for i in range(max(0, start_line - 10), start_line):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith('//'):
                # Remove '//' and any following whitespace
                comment = line[line.find('//') + 2:].strip()
                comment_lines.append(comment)
            elif stripped.startswith('#'):
                comment = line[line.find('#') + 1:].strip()
                comment_lines.append(comment)
        
        # Parse comments for metadata
        for comment in comment_lines:
            comment_lower = comment.lower()
            
            # Author
            if any(marker in comment_lower for marker in ['автор:', 'author:', 'разработчик:', 'developer:']):
                for marker in ['автор:', 'author:', 'разработчик:', 'developer:']:
                    if marker in comment_lower:
                        # Remove marker and any following colon/space
                        value = comment[comment.find(marker) + len(marker):].strip()
                        # Remove leading colon if present
                        if value.startswith(':'):
                            value = value[1:].strip()
                        metadata.author = value
                        break
            
            # Date
            elif any(marker in comment_lower for marker in ['дата:', 'date:', 'создано:', 'created:']):
                for marker in ['дата:', 'date:', 'создано:', 'created:']:
                    if marker in comment_lower:
                        value = comment[comment.find(marker) + len(marker):].strip()
                        if value.startswith(':'):
                            value = value[1:].strip()
                        metadata.created_date = value
                        break
            
            # Version
            elif any(marker in comment_lower for marker in ['версия:', 'version:', 'ver:']):
                for marker in ['версия:', 'version:', 'ver:']:
                    if marker in comment_lower:
                        value = comment[comment.find(marker) + len(marker):].strip()
                        if value.startswith(':'):
                            value = value[1:].strip()
                        metadata.version = value
                        break
            
            # Description (first non-metadata comment)
            elif not metadata.description and comment:
                metadata.description = comment
        
        # Determine module type from file path
        path_parts = Path(file_path).parts
        for part in path_parts:
            part_lower = part.lower()
            if 'commonmodule' in part_lower or 'общиймодуль' in part_lower:
                metadata.module_type = "CommonModule"
                break
            elif 'document' in part_lower or 'документ' in part_lower:
                metadata.module_type = "Document"
                break
            elif 'catalog' in part_lower or 'справочник' in part_lower:
                metadata.module_type = "Catalog"
                break
            elif 'report' in part_lower or 'отчет' in part_lower:
                metadata.module_type = "Report"
                break
            elif 'dataprocessor' in part_lower or 'обработка' in part_lower:
                metadata.module_type = "DataProcessor"
                break
        
        # Determine subsystem from file path
        for i, part in enumerate(path_parts):
            if 'subsystem' in part.lower() or 'подсистема' in part.lower():
                if i + 1 < len(path_parts):
                    metadata.subsystem = path_parts[i + 1]
                break
        
        return metadata
    
    def _process_1c_bsl_file(self, content: str, file_path: str) -> List[CodeChunk]:
        """Process 1C/BSL file with semantic chunking and enterprise metadata"""
        chunks = []
        
        # Split by procedures and functions for better semantic chunks
        lines = content.splitlines()
        
        # Find procedure/function boundaries
        procedure_start = -1
        current_procedure_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for procedure/function start
            if stripped.lower().startswith(('процедура', 'функция', 'procedure', 'function')):
                # Save previous procedure if exists
                if current_procedure_lines and procedure_start >= 0:
                    chunk_content = '\n'.join(current_procedure_lines).strip()
                    if len(chunk_content) >= 20:
                        # Extract metadata
                        metadata = self._extract_1c_metadata(
                            lines, procedure_start, 
                            procedure_start + len(current_procedure_lines) - 1,
                            file_path
                        )
                        
                        chunk = CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            line_start=procedure_start + 1,
                            line_end=procedure_start + len(current_procedure_lines),
                            language='1c_bsl',
                            chunk_id=self._generate_chunk_id(file_path, procedure_start + 1),
                            enterprise_metadata=metadata
                        )
                        chunks.append(chunk)
                
                # Start new procedure
                procedure_start = i
                current_procedure_lines = [line]
            elif current_procedure_lines:
                # Continue current procedure
                current_procedure_lines.append(line)
                
                # Check for end of procedure (КонецПроцедуры, КонецФункции, EndProcedure, EndFunction)
                if stripped.lower() in ('конецпроцедуры', 'конецфункции', 'endprocedure', 'endfunction'):
                    # Save completed procedure
                    chunk_content = '\n'.join(current_procedure_lines).strip()
                    if len(chunk_content) >= 20:
                        # Extract metadata
                        metadata = self._extract_1c_metadata(
                            lines, procedure_start,
                            procedure_start + len(current_procedure_lines) - 1,
                            file_path
                        )
                        
                        chunk = CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            line_start=procedure_start + 1,
                            line_end=procedure_start + len(current_procedure_lines),
                            language='1c_bsl',
                            chunk_id=self._generate_chunk_id(file_path, procedure_start + 1),
                            enterprise_metadata=metadata
                        )
                        chunks.append(chunk)
                    
                    # Reset for next procedure
                    procedure_start = -1
                    current_procedure_lines = []
        
        # Save last procedure if exists
        if current_procedure_lines and procedure_start >= 0:
            chunk_content = '\n'.join(current_procedure_lines).strip()
            if len(chunk_content) >= 20:
                # Extract metadata
                metadata = self._extract_1c_metadata(
                    lines, procedure_start,
                    procedure_start + len(current_procedure_lines) - 1,
                    file_path
                )
                
                chunk = CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    line_start=procedure_start + 1,
                    line_end=procedure_start + len(current_procedure_lines),
                    language='1c_bsl',
                    chunk_id=self._generate_chunk_id(file_path, procedure_start + 1),
                    enterprise_metadata=metadata
                )
                chunks.append(chunk)
        
        # If no procedures found, fall back to line-based chunking
        if not chunks:
            chunk_size = 15
            overlap = 3
            
            for i in range(0, len(lines), chunk_size - overlap):
                chunk_lines = lines[i:i + chunk_size]
                if not chunk_lines:
                    continue
                
                chunk_content = '\n'.join(chunk_lines).strip()
                if not chunk_content or len(chunk_content) < 20:
                    continue
                
                # Extract basic metadata for non-procedure chunks
                metadata = EnterpriseMetadata()
                metadata.object_type = "CodeBlock"
                metadata.module_type = self._detect_module_type_from_path(file_path)
                
                chunk = CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=i + len(chunk_lines),
                    language='1c_bsl',
                    chunk_id=self._generate_chunk_id(file_path, i + 1),
                    enterprise_metadata=metadata
                )
                chunks.append(chunk)
        
        return chunks
    
    def _detect_module_type_from_path(self, file_path: str) -> str:
        """Detect module type from file path"""
        path_parts = Path(file_path).parts
        for part in path_parts:
            part_lower = part.lower()
            if 'commonmodule' in part_lower or 'общиймодуль' in part_lower:
                return "CommonModule"
            elif 'document' in part_lower or 'документ' in part_lower:
                return "Document"
            elif 'catalog' in part_lower or 'справочник' in part_lower:
                return "Catalog"
            elif 'report' in part_lower or 'отчет' in part_lower:
                return "Report"
            elif 'dataprocessor' in part_lower or 'обработка' in part_lower:
                return "DataProcessor"
            elif 'informationregister' in part_lower or 'регистры' in part_lower:
                return "InformationRegister"
            elif 'accumulationregister' in part_lower or 'регистрынакопления' in part_lower:
                return "AccumulationRegister"
            elif 'accountingregister' in part_lower or 'регистрыбухгалтерии' in part_lower:
                return "AccountingRegister"
            elif 'calculationregister' in part_lower or 'регистрырасчета' in part_lower:
                return "CalculationRegister"
        return "Unknown"
    
    def _create_contextual_chunks(self, lines: List[str], file_path: str, base_metadata: EnterpriseMetadata) -> List[CodeChunk]:
        """Create contextual chunks for 1C/BSL code with surrounding context"""
        chunks = []
        chunk_size = 20  # Lines per chunk
        context_lines = 5  # Additional context lines
        
        for i in range(0, len(lines), chunk_size):
            # Calculate chunk boundaries with context
            chunk_start = max(0, i - context_lines)
            chunk_end = min(len(lines), i + chunk_size + context_lines)
            
            chunk_lines = lines[chunk_start:chunk_end]
            if not chunk_lines:
                continue
            
            chunk_content = '\n'.join(chunk_lines).strip()
            if not chunk_content or len(chunk_content) < 20:
                continue
            
            # Create metadata with context information
            metadata = EnterpriseMetadata(
                object_type=base_metadata.object_type,
                object_name=base_metadata.object_name,
                module_type=base_metadata.module_type,
                subsystem=base_metadata.subsystem,
                author=base_metadata.author,
                description=f"Contextual chunk: lines {chunk_start+1}-{chunk_end}",
                parameters=base_metadata.parameters,
                return_type=base_metadata.return_type,
                export=base_metadata.export,
                deprecated=base_metadata.deprecated
            )
            
            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                line_start=chunk_start + 1,
                line_end=chunk_end,
                language='1c_bsl',
                chunk_id=self._generate_chunk_id(file_path, chunk_start + 1),
                enterprise_metadata=metadata
            )
            chunks.append(chunk)
        
        return chunks
    
    def index_codebase(self, file_patterns: List[str] = None, max_file_size_mb: int = 10):
        """Index the codebase for vector search with streaming processing
        
        Args:
            file_patterns: List of file patterns to index
            max_file_size_mb: Maximum file size in MB to index (larger files will be skipped)
        """
        from glob import glob
        
        if file_patterns is None:
            file_patterns = ["**/*.java", "**/*.py", "**/*.js", "**/*.ts", "**/*.md", "**/*.txt", "**/*.bsl", "**/*.os", "**/*.xml"]
        
        batch_size = 1000
        current_batch = []
        total_files = 0
        total_indexed = 0
        
        def process_batch(batch_chunks):
            """Process a batch of chunks and add to Chroma and keyword index"""
            if not batch_chunks:
                return 0
            
            # Prepare batch data for Chroma
            batch_ids = [chunk.chunk_id for chunk in batch_chunks]
            batch_contents = [chunk.content for chunk in batch_chunks]
            batch_metadatas = []
            
            for chunk in batch_chunks:
                # Base metadata
                metadata = {
                    "file_path": chunk.file_path,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "language": chunk.language
                }
                
                # Add enterprise metadata if available
                if chunk.enterprise_metadata:
                    enterprise_dict = chunk.enterprise_metadata.to_dict()
                    metadata.update(enterprise_dict)
                
                batch_metadatas.append(metadata)
                
                # Add to keyword index if available
                if self.keyword_index and HYBRID_SEARCH_AVAILABLE:
                    try:
                        self.keyword_index.add_document(
                            chunk_id=chunk.chunk_id,
                            content=chunk.content,
                            metadata=metadata
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add chunk {chunk.chunk_id} to keyword index: {e}")
            
            # Generate embeddings for batch with caching
            batch_embeddings = self.encode_with_cache(batch_contents)
            
            # Add batch to collection
            self.collection.add(
                embeddings=batch_embeddings,
                documents=batch_contents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            return len(batch_chunks)
        
        for pattern in file_patterns:
            files = glob(str(self.project_root / pattern), recursive=True)
            for file_path in files:
                try:
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in Path(file_path).parts):
                        continue
                    
                    # Check file size
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb > max_file_size_mb:
                        logger.info(f"Skipping large file: {file_path} ({file_size_mb:.1f} MB > {max_file_size_mb} MB limit)")
                        continue
                    
                    # Process file and get chunks
                    file_chunks = self._process_file(file_path)
                    
                    # Add chunks to current batch
                    current_batch.extend(file_chunks)
                    
                    # Process batch if it reaches batch_size
                    if len(current_batch) >= batch_size:
                        batch_indexed = process_batch(current_batch)
                        total_indexed += batch_indexed
                        current_batch = []
                        logger.info(f"Indexed batch: {batch_indexed} chunks (total: {total_indexed})")
                    
                    total_files += 1
                    if total_files % 10 == 0:
                        logger.info(f"Processed {total_files} files...")
                        
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
        
        # Process remaining chunks in final batch
        if current_batch:
            batch_indexed = process_batch(current_batch)
            total_indexed += batch_indexed
            logger.info(f"Indexed final batch: {batch_indexed} chunks (total: {total_indexed})")
        
        if total_indexed == 0:
            logger.warning("No code chunks found to index")
        
        # Save keyword index if it was updated
        if self.keyword_index and HYBRID_SEARCH_AVAILABLE and total_indexed > 0:
            self._save_keyword_index()
            keyword_stats = self.keyword_index.get_stats()
            logger.info(f"Keyword index updated: {keyword_stats['total_documents']} documents, "
                       f"{keyword_stats['vocabulary_size']} unique words")
        
        logger.info(f"Total indexed {total_indexed} code chunks from {total_files} files")
        return total_indexed
    
    def _process_file(self, file_path: str) -> List[CodeChunk]:
        """Process a single file into code chunks"""
        path = Path(file_path)
        relative_path = path.relative_to(self.project_root)
        
        # Determine language from extension
        ext = path.suffix.lower()
        language_map = {
            '.java': 'java',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.xml': 'xml',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.properties': 'properties',
            '.bsl': '1c_bsl',
            '.os': '1c_bsl'
        }
        language = language_map.get(ext, 'text')
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            return []
        
        # Use specialized processing for 1C/BSL files
        if language == '1c_bsl':
            return self._process_1c_bsl_file(content, str(relative_path))
        
        # Default processing for other languages
        lines = content.splitlines()
        chunks = []
        chunk_size = 15  # lines per chunk
        overlap = 3      # overlapping lines
        
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            if not chunk_lines:
                continue
            
            chunk_content = '\n'.join(chunk_lines).strip()
            if not chunk_content or len(chunk_content) < 20:  # Skip very small chunks
                continue
            
            chunk = CodeChunk(
                content=chunk_content,
                file_path=str(relative_path),
                line_start=i + 1,
                line_end=i + len(chunk_lines),
                language=language,
                chunk_id=self._generate_chunk_id(str(relative_path), i + 1)
            )
            chunks.append(chunk)
        
        return chunks
    
    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search on indexed codebase"""
        if not self.embedding_model or not self.collection:
            raise RuntimeError("Server not properly initialized")
        
        # Generate query embedding with caching
        query_embedding = self._cached_encode(query)
        
        # Search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results['documents']:
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                formatted_results.append({
                    "rank": i + 1,
                    "content": doc,
                    "file_path": metadata["file_path"],
                    "line_start": metadata["line_start"],
                    "line_end": metadata["line_end"],
                    "language": metadata["language"],
                    "similarity_score": float(1 - distance),  # Convert distance to similarity
                    "chunk_id": results['ids'][0][i] if results['ids'] else f"result_{i}"
                })
        
        return formatted_results
    
    def keyword_search(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Perform keyword search on indexed codebase"""
        if not self.keyword_index or not HYBRID_SEARCH_AVAILABLE:
            logger.warning("Keyword search not available. Returning empty results.")
            return []
        
        try:
            # Perform keyword search
            keyword_results = self.keyword_index.search(query, n_results * 2)  # Get more results for deduplication
            
            # Format results
            formatted_results = []
            for i, result in enumerate(keyword_results):
                formatted_results.append({
                    "rank": i + 1,
                    "content": result.content,
                    "file_path": result.metadata.get("file_path", ""),
                    "line_start": result.metadata.get("line_start", 0),
                    "line_end": result.metadata.get("line_end", 0),
                    "language": result.metadata.get("language", "unknown"),
                    "similarity_score": float(result.score),
                    "chunk_id": result.chunk_id,
                    "search_type": "keyword"
                })
            
            logger.debug(f"Keyword search returned {len(formatted_results)} results")
            return formatted_results[:n_results]  # Return requested number of results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def hybrid_search(
        self, 
        query: str, 
        n_results: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        fusion_method: str = 'weighted',
        search_type: str = 'hybrid'
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword search"""
        
        # Determine which searches to perform based on search_type
        semantic_results = []
        keyword_results = []
        
        if search_type in ['semantic', 'hybrid']:
            try:
                semantic_results = self.semantic_search(query, n_results * 2)
                # Add search_type to semantic results
                for result in semantic_results:
                    result['search_type'] = 'semantic'
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")
        
        if search_type in ['keyword', 'hybrid'] and self.keyword_index and HYBRID_SEARCH_AVAILABLE:
            try:
                keyword_results = self.keyword_search(query, n_results * 2)
            except Exception as e:
                logger.warning(f"Keyword search failed: {e}")
        
        # If only one type of search was requested or available, return those results
        if search_type == 'semantic' or (search_type == 'hybrid' and not keyword_results):
            return semantic_results[:n_results]
        
        if search_type == 'keyword' or (search_type == 'hybrid' and not semantic_results):
            return keyword_results[:n_results]
        
        # Perform hybrid fusion
        try:
            # Update fuser weights
            if self.search_fuser:
                self.search_fuser.semantic_weight = semantic_weight
                self.search_fuser.keyword_weight = keyword_weight
            
            # Use hybrid search optimizer to suggest weights if not specified
            if semantic_weight == 0.7 and keyword_weight == 0.3:  # Default weights
                suggested_weights = HybridSearchOptimizer.suggest_weights(query)
                semantic_weight, keyword_weight = suggested_weights
                logger.debug(f"Using suggested weights: semantic={semantic_weight:.2f}, keyword={keyword_weight:.2f}")
            
            # Create fuser with specified weights
            fuser = SearchResultFuser(semantic_weight, keyword_weight)
            
            # Fuse results
            fused_results = fuser.fuse(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                n_results=n_results,
                fusion_method=fusion_method,
                deduplicate=True
            )
            
            # Add search_type to results
            for result in fused_results:
                result['search_type'] = 'hybrid'
                # Ensure similarity_score is float
                if 'similarity_score' in result:
                    result['similarity_score'] = float(result['similarity_score'])
            
            logger.info(f"Hybrid search: {len(semantic_results)} semantic + "
                       f"{len(keyword_results)} keyword → {len(fused_results)} fused results")
            
            return fused_results
            
        except Exception as e:
            logger.error(f"Hybrid search fusion failed: {e}")
            # Fallback: return semantic results
            return semantic_results[:n_results]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        count = self.collection.count() if self.collection else 0
        stats = {
            "collection_name": self.collection_name,
            "document_count": count,
            "project_root": str(self.project_root),
            "port": self.port,
            "hybrid_search_available": HYBRID_SEARCH_AVAILABLE
        }
        
        # Add GPU information if enabled
        if self.gpu_config.enabled:
            stats.update({
                "gpu_enabled": True,
                "gpu_device": self.device,
                "gpu_batch_size": self.gpu_config.batch_size,
                "gpu_mixed_precision": self.gpu_config.use_mixed_precision,
                "gpu_cache_size": self.gpu_config.cache_size
            })
        else:
            stats["gpu_enabled"] = False
        
        # Add keyword index information if available
        if self.keyword_index and HYBRID_SEARCH_AVAILABLE:
            keyword_stats = self.keyword_index.get_stats()
            stats.update({
                "keyword_index_available": True,
                "keyword_document_count": keyword_stats['total_documents'],
                "keyword_vocabulary_size": keyword_stats['vocabulary_size'],
                "keyword_avg_doc_length": keyword_stats['average_document_length']
            })
        else:
            stats["keyword_index_available"] = False
        
        return stats
    
    def handle_command(self, command: str) -> str:
        """Handle a command from client"""
        try:
            parts = command.strip().split("|", 1)
            cmd = parts[0].upper()
            
            if cmd == "SEARCH":
                if len(parts) > 1:
                    subparts = parts[1].split("|")
                    query = subparts[0]
                    n_results = int(subparts[1]) if len(subparts) > 1 else 5
                    results = self.semantic_search(query, n_results)
                    return json.dumps({
                        "type": "search_results",
                        "results": results
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "type": "error",
                        "message": "Missing query for SEARCH"
                    })
            
            elif cmd == "KEYWORD_SEARCH":
                if len(parts) > 1:
                    subparts = parts[1].split("|")
                    query = subparts[0]
                    n_results = int(subparts[1]) if len(subparts) > 1 else 10
                    results = self.keyword_search(query, n_results)
                    return json.dumps({
                        "type": "search_results",
                        "results": results
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "type": "error",
                        "message": "Missing query for KEYWORD_SEARCH"
                    })
            
            elif cmd == "HYBRID_SEARCH":
                if len(parts) > 1:
                    subparts = parts[1].split("|")
                    query = subparts[0]
                    n_results = int(subparts[1]) if len(subparts) > 1 else 10
                    semantic_weight = float(subparts[2]) if len(subparts) > 2 else 0.7
                    keyword_weight = float(subparts[3]) if len(subparts) > 3 else 0.3
                    fusion_method = subparts[4] if len(subparts) > 4 else 'weighted'
                    
                    results = self.hybrid_search(
                        query=query,
                        n_results=n_results,
                        semantic_weight=semantic_weight,
                        keyword_weight=keyword_weight,
                        fusion_method=fusion_method
                    )
                    return json.dumps({
                        "type": "search_results",
                        "results": results
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "type": "error",
                        "message": "Missing query for HYBRID_SEARCH"
                    })
            
            elif cmd == "INDEX":
                file_patterns = parts[1].split(",") if len(parts) > 1 else ["**/*.java", "**/*.py", "**/*.js", "**/*.ts"]
                count = self.index_codebase(file_patterns)
                return json.dumps({
                    "type": "index_result",
                    "count": count,
                    "total": self.collection.count() if self.collection else 0
                })
            
            elif cmd == "STATS":
                stats = self.get_stats()
                return json.dumps({
                    "type": "stats",
                    "stats": stats
                })
            
            elif cmd == "PING":
                return json.dumps({
                    "type": "pong",
                    "status": "alive",
                    "timestamp": time.time()
                })
            
            elif cmd == "GPUINFO":
                import torch
                gpu_info = {
                    "gpu_enabled": self.gpu_config.enabled,
                    "device": self.device,
                    "gpu_config": {
                        "batch_size": self.gpu_config.batch_size,
                        "use_mixed_precision": self.gpu_config.use_mixed_precision,
                        "cache_size": self.gpu_config.cache_size
                    },
                    "torch_info": {
                        "version": torch.__version__,
                        "cuda_available": torch.cuda.is_available(),
                        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
                        "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
                    }
                }
                return json.dumps({
                    "type": "gpu_info",
                    "info": gpu_info
                })
            
            else:
                return json.dumps({
                    "type": "error",
                    "message": f"Unknown command: {cmd}"
                })
                
        except Exception as e:
            return json.dumps({
                "type": "error",
                "message": str(e)
            })
    
    def start_server(self):
        """Start the TCP server and WebSocket server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Non-blocking with timeout
            
            self.running = True
            logger.info(f"Chroma server started on port {self.port}")
            
            # Start WebSocket server if available
            if WEBSOCKET_AVAILABLE and self.websocket_port:
                try:
                    self.websocket_server = WebSocketServer(self, self.websocket_port)
                    self.websocket_server.start_in_thread()
                    logger.info(f"WebSocket server started on port {self.websocket_port}")
                except Exception as e:
                    logger.error(f"Failed to start WebSocket server: {e}")
            
            def client_handler(client_socket):
                """Handle a client connection"""
                try:
                    # Receive command
                    data = client_socket.recv(4096).decode('utf-8').strip()
                    if data:
                        # Handle command
                        response = self.handle_command(data)
                        client_socket.send(response.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Client handler error: {e}")
                finally:
                    client_socket.close()
            
            # Main server loop
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.debug(f"Client connected: {addr}")
                    
                    # Handle client in a thread
                    thread = threading.Thread(target=client_handler, args=(client_socket,))
                    thread.daemon = True
                    thread.start()
                    
                except socket.timeout:
                    # Timeout, check if still running
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Server error: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        
        # Stop WebSocket server
        if self.websocket_server:
            self.websocket_server.stop()
            self.websocket_server = None
        
        # Stop TCP server
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        logger.info("Chroma server stopped")

def run_standalone(args):
    """Run in standalone mode (CLI)"""
    # Create GPU configuration if enabled
    gpu_config = None
    if args.gpu:
        gpu_config = GPUConfig(
            enabled=True,
            device=args.gpu_device,
            batch_size=args.gpu_batch_size,
            use_mixed_precision=args.gpu_mixed_precision,
            cache_size=args.gpu_cache_size
        )
        print(f"GPU acceleration enabled (device: {args.gpu_device})")
    
    # Determine WebSocket port
    websocket_port = None
    if hasattr(args, 'websocket_port') and args.websocket_port and not getattr(args, 'no_websocket', False):
        websocket_port = args.websocket_port
    
    server = ChromaSimpleServer(
        args.project_root, 
        gpu_config=gpu_config,
        websocket_port=websocket_port
    )
    
    if args.index:
        print("Indexing codebase...")
        count = server.index_codebase()
        print(f"Indexing complete. Added {count} documents. Total: {server.collection.count()}")
    
    elif args.search:
        print(f"Searching for: {args.search}")
        results = server.semantic_search(args.search, args.results)
        
        if results:
            print(f"\nFound {len(results)} results:\n")
            for result in results:
                print(f"Rank {result['rank']} (Score: {result['similarity_score']:.3f})")
                print(f"File: {result['file_path']}:{result['line_start']}-{result['line_end']}")
                print(f"Language: {result['language']}")
                print(f"Content:\n{result['content'][:300]}...\n")
                print("-" * 80)
        else:
            print("No results found.")
    
    elif args.stats:
        stats = server.get_stats()
        print(f"Chroma collection: {stats['collection_name']}")
        print(f"Document count: {stats['document_count']}")
        print(f"Project root: {stats['project_root']}")
    
    elif args.server:
        print(f"Starting Chroma server on port {args.port}...")
        print(f"Project: {args.project_root}")
        print(f"Collection: {server.collection_name}")
        print(f"Documents: {server.collection.count()}")
        
        # Show GPU info if enabled
        if args.gpu:
            print(f"GPU acceleration: ENABLED (device: {server.device})")
            print(f"GPU batch size: {args.gpu_batch_size}")
            print(f"GPU mixed precision: {'ENABLED' if args.gpu_mixed_precision else 'DISABLED'}")
            print(f"GPU cache size: {args.gpu_cache_size}")
        else:
            print(f"GPU acceleration: DISABLED")
        
        print("\nServer commands via TCP:")
        print("  SEARCH|query|n_results  - Semantic search")
        print("  INDEX|file_patterns     - Index codebase")
        print("  STATS                   - Get statistics")
        print("  PING                    - Check server status")
        print("  GPUINFO                 - Get GPU information")
        print("\nExample with netcat:")
        print(f"  echo 'SEARCH|database connection|5' | nc localhost {args.port}")
        print("")
        
        # Show WebSocket info if available
        if WEBSOCKET_AVAILABLE:
            websocket_port = args.websocket_port if hasattr(args, 'websocket_port') else 8766
            print(f"WebSocket server: ENABLED on port {websocket_port}")
            print("WebSocket API supports real-time updates and bidirectional communication")
            print("Connect with: ws://localhost:{websocket_port}")
            print("")
        else:
            print("WebSocket server: DISABLED (install: pip install websockets)")
            print("")
        
        server.start_server()
    
    else:
        # Show help
        print(f"Chroma Code Search Server")
        print(f"Project: {server.project_root}")
        print(f"Collection: {server.collection_name}")
        print(f"Documents: {server.collection.count() if server.collection else 0}")
        print("\nUsage:")
        print("  --index          Index the codebase")
        print("  --search QUERY   Search for code")
        print("  --results N      Number of results (default: 5)")
        print("  --stats          Show index statistics")
        print("  --server         Run as TCP server")
        print("  --port N         Server port (default: 8765)")
        print("  --project-root   Project root directory (default: .)")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chroma Code Search Server")
    parser.add_argument("--index", action="store_true", help="Index the codebase")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--results", type=int, default=5, help="Number of results")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--server", action="store_true", help="Run as TCP server")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    
    # GPU acceleration arguments
    parser.add_argument("--gpu", action="store_true", help="Enable GPU acceleration")
    parser.add_argument("--gpu-device", type=str, default="auto", 
                       choices=["auto", "cuda", "cpu", "mps"],
                       help="GPU device to use (auto, cuda, cpu, mps)")
    parser.add_argument("--gpu-batch-size", type=int, default=32,
                       help="Batch size for GPU processing")
    parser.add_argument("--gpu-mixed-precision", action="store_true",
                       help="Enable mixed precision (float16) for GPU")
    parser.add_argument("--gpu-cache-size", type=int, default=1000,
                       help="Cache size for embeddings")
    
    # WebSocket arguments
    parser.add_argument("--websocket-port", type=int, default=8766,
                       help="WebSocket server port (default: 8766)")
    parser.add_argument("--no-websocket", action="store_true",
                       help="Disable WebSocket server")
    
    args = parser.parse_args()
    
    # Disable WebSocket if requested
    if args.no_websocket:
        args.websocket_port = None
    
    run_standalone(args)

if __name__ == "__main__":
    main()