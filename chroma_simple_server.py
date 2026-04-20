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

# Chroma imports
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata"""
    content: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    chunk_id: str

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
        """Initialize sentence transformer model for embeddings"""
        try:
            # Use a lightweight model for code embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _generate_chunk_id(self, file_path: str, line_start: int) -> str:
        """Generate unique ID for code chunk"""
        content = f"{file_path}:{line_start}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def index_codebase(self, file_patterns: List[str] = None):
        """Index the codebase for vector search"""
        from glob import glob
        
        if file_patterns is None:
            file_patterns = ["**/*.java", "**/*.py", "**/*.js", "**/*.ts", "**/*.md", "**/*.txt"]
        
        chunks = []
        total_files = 0
        
        for pattern in file_patterns:
            files = glob(str(self.project_root / pattern), recursive=True)
            for file_path in files:
                try:
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in Path(file_path).parts):
                        continue
                    
                    file_chunks = self._process_file(file_path)
                    chunks.extend(file_chunks)
                    total_files += 1
                    if total_files % 10 == 0:
                        logger.info(f"Processed {total_files} files...")
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
        
        if not chunks:
            logger.warning("No code chunks found to index")
            return 0
        
        # Process in batches to avoid size limits
        batch_size = 1000
        total_indexed = 0
        
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            batch_chunks = chunks[i:batch_end]
            
            # Prepare batch data for Chroma
            batch_ids = [chunk.chunk_id for chunk in batch_chunks]
            batch_contents = [chunk.content for chunk in batch_chunks]
            batch_metadatas = [{
                "file_path": chunk.file_path,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "language": chunk.language
            } for chunk in batch_chunks]
            
            # Generate embeddings for batch
            batch_embeddings = self.embedding_model.encode(batch_contents).tolist()
            
            # Add batch to collection
            self.collection.add(
                embeddings=batch_embeddings,
                documents=batch_contents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            total_indexed += len(batch_chunks)
            logger.info(f"Indexed batch {i//batch_size + 1}: {len(batch_chunks)} chunks (total: {total_indexed})")
        
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
            '.properties': 'properties'
        }
        language = language_map.get(ext, 'text')
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Skip binary files
            return []
        
        chunks = []
        chunk_size = 15  # lines per chunk
        overlap = 3      # overlapping lines
        
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            if not chunk_lines:
                continue
            
            content = ''.join(chunk_lines).strip()
            if not content or len(content) < 20:  # Skip very small chunks
                continue
            
            chunk = CodeChunk(
                content=content,
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
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
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