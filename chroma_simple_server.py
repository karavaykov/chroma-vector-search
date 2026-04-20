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

class ChromaSimpleServer:
    """Simple server for Chroma vector search without MCP"""
    
    def __init__(self, project_root: str = ".", port: int = 8765):
        self.project_root = Path(project_root).resolve()
        self.port = port
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.collection_name = "codebase_vectors"
        self.server_socket = None
        self.running = False
        
        # Initialize Chroma
        self._init_chroma()
        
        # Initialize embedding model
        self._init_embedding_model()
    
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
            # Use a lightweight model for code embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create cached version of encode method
            self._cached_encode = lru_cache(maxsize=1000)(self._encode_with_cache)
            
            logger.info("Embedding model initialized with caching")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _encode_with_cache(self, text: str) -> List[float]:
        """Cached version of encode method"""
        return self.embedding_model.encode([text]).tolist()[0]
    
    def encode_with_cache(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts with caching for duplicates"""
        unique_texts = list(set(texts))
        text_to_embedding = {}
        
        # Encode unique texts
        for text in unique_texts:
            embedding = self._cached_encode(text)
            text_to_embedding[text] = embedding
        
        # Return embeddings in original order
        return [text_to_embedding[text] for text in texts]
    
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
            """Process a batch of chunks and add to Chroma"""
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed codebase"""
        count = self.collection.count() if self.collection else 0
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "project_root": str(self.project_root),
            "port": self.port
        }
    
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
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Non-blocking with timeout
            
            self.running = True
            logger.info(f"Chroma server started on port {self.port}")
            
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
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        logger.info("Chroma server stopped")

def run_standalone(args):
    """Run in standalone mode (CLI)"""
    server = ChromaSimpleServer(args.project_root)
    
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
        print("\nServer commands via TCP:")
        print("  SEARCH|query|n_results  - Semantic search")
        print("  INDEX|file_patterns     - Index codebase")
        print("  STATS                   - Get statistics")
        print("  PING                    - Check server status")
        print("\nExample with netcat:")
        print(f"  echo 'SEARCH|database connection|5' | nc localhost {args.port}")
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
    
    args = parser.parse_args()
    run_standalone(args)

if __name__ == "__main__":
    main()