#!/usr/bin/env python3
"""
Chroma REST Client for OpenCode integration
Communicates with Chroma microservices via REST API
"""

import json
import sys
import argparse
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

class ChromaRESTClient:
    """Client for Chroma REST API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
    
    def search(self, query: str, n_results: int = 5, collection_name: str = "codebase_vectors", 
               filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Perform semantic search"""
        try:
            payload = {
                "query": query,
                "n_results": n_results,
                "collection_name": collection_name
            }
            if filters:
                payload["filters"] = filters
            
            response = self.client.post(f"{self.base_url}/api/v1/search", json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def index(self, project_root: str = ".", file_patterns: Optional[list] = None, 
              max_file_size_mb: int = 10, collection_name: str = "codebase_vectors") -> Dict[str, Any]:
        """Index the codebase"""
        try:
            payload = {
                "project_root": project_root,
                "max_file_size_mb": max_file_size_mb,
                "collection_name": collection_name
            }
            if file_patterns:
                payload["file_patterns"] = file_patterns
            
            response = self.client.post(f"{self.base_url}/api/v1/index", json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def get_index_status(self, job_id: str) -> Dict[str, Any]:
        """Get indexing job status"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/index/status/{job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def get_stats(self, collection_name: str = "codebase_vectors") -> Dict[str, Any]:
        """Get server statistics"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/stats?collection_name={collection_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def list_files(self, collection_name: str = "codebase_vectors") -> Dict[str, Any]:
        """List indexed files"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/files?collection_name={collection_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def list_collections(self) -> Dict[str, Any]:
        """List available collections"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/collections")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def search_similar(self, chunk_id: str, n_results: int = 5) -> Dict[str, Any]:
        """Find similar chunks"""
        try:
            payload = {
                "chunk_id": chunk_id,
                "n_results": n_results
            }
            response = self.client.post(f"{self.base_url}/api/v1/search/similar", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            response = self.client.get(f"{self.base_url}/api/v1/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"type": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    def close(self):
        """Close HTTP client"""
        self.client.close()

def print_search_results(result: Dict[str, Any]):
    """Print search results in readable format"""
    if result.get("type") == "error":
        print(f"Error: {result.get('message', 'Unknown error')}")
        return
    
    query = result.get("query", "")
    results = result.get("results", [])
    total = result.get("total_results", 0)
    processing_time = result.get("processing_time_ms", 0)
    
    print(f"\nFound {total} results for '{query}' ({processing_time:.2f}ms):\n")
    
    for item in results:
        print(f"Rank {item['rank']} (Score: {item['similarity_score']:.3f})")
        print(f"File: {item['file_path']}:{item['line_start']}-{item['line_end']}")
        print(f"Language: {item['language']}")
        print(f"Content:\n{item['content'][:200]}...\n")
        print("-" * 80)

def print_index_result(result: Dict[str, Any]):
    """Print indexing result"""
    if result.get("type") == "error":
        print(f"Error: {result.get('message', 'Unknown error')}")
        return
    
    job_id = result.get("job_id", "")
    status = result.get("status", "")
    message = result.get("message", "")
    
    print(f"Indexing job started:")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {status}")
    print(f"  Message: {message}")
    print(f"\nCheck status with: --index-status {job_id}")

def print_index_status(result: Dict[str, Any]):
    """Print indexing status"""
    if isinstance(result, dict) and result.get("type") == "error":
        print(f"Error: {result.get('message', 'Unknown error')}")
        return
    
    job_id = result.get("job_id", "")
    status = result.get("status", "")
    progress = result.get("progress", 0.0) * 100
    total_files = result.get("total_files", 0)
    processed_files = result.get("processed_files", 0)
    total_chunks = result.get("total_chunks", 0)
    processed_chunks = result.get("processed_chunks", 0)
    
    print(f"Indexing Job: {job_id}")
    print(f"Status: {status}")
    print(f"Progress: {progress:.1f}%")
    print(f"Files: {processed_files}/{total_files}")
    print(f"Chunks: {processed_chunks}/{total_chunks}")
    
    if result.get("error_message"):
        print(f"Error: {result['error_message']}")

def print_stats(result: Dict[str, Any]):
    """Print statistics"""
    if isinstance(result, dict) and result.get("type") == "error":
        print(f"Error: {result.get('message', 'Unknown error')}")
        return
    
    stats = result if isinstance(result, dict) else {}
    
    print(f"Collection: {stats.get('collection_name', 'N/A')}")
    print(f"Total documents: {stats.get('total_documents', 0)}")
    print(f"Total files: {stats.get('total_files', 0)}")
    print(f"Average chunk size: {stats.get('average_chunk_size', 0):.1f} lines")
    
    if stats.get('languages'):
        print("\nLanguages:")
        for lang, count in stats['languages'].items():
            print(f"  {lang}: {count}")
    
    if stats.get('indexed_at'):
        indexed_at = datetime.fromisoformat(stats['indexed_at'].replace('Z', '+00:00'))
        print(f"\nIndexed at: {indexed_at.strftime('%Y-%m-%d %H:%M:%S')}")

def print_health(result: Dict[str, Any]):
    """Print health check results"""
    if isinstance(result, dict) and result.get("type") == "error":
        print(f"Error: {result.get('message', 'Unknown error')}")
        return
    
    status = result.get("status", "")
    services = result.get("services", {})
    timestamp = result.get("timestamp", "")
    
    print(f"Overall Status: {status.upper()}")
    print(f"Timestamp: {timestamp}")
    print("\nServices:")
    
    for service, service_status in services.items():
        status_icon = "✅" if service_status == "healthy" else "❌"
        print(f"  {status_icon} {service}: {service_status}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chroma REST Client for OpenCode")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="API Gateway base URL")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--results", type=int, default=5, help="Number of results")
    parser.add_argument("--collection", type=str, default="codebase_vectors", help="Collection name")
    parser.add_argument("--index", action="store_true", help="Index codebase")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    parser.add_argument("--patterns", type=str, help="File patterns for indexing (comma separated)")
    parser.add_argument("--max-size", type=int, default=10, help="Maximum file size in MB")
    parser.add_argument("--index-status", type=str, help="Get indexing job status")
    parser.add_argument("--stats", action="store_true", help="Get server statistics")
    parser.add_argument("--files", action="store_true", help="List indexed files")
    parser.add_argument("--collections", action="store_true", help="List available collections")
    parser.add_argument("--similar", type=str, help="Find similar chunks (chunk ID)")
    parser.add_argument("--similar-results", type=int, default=5, help="Number of similar results")
    parser.add_argument("--health", action="store_true", help="Check API health")
    
    args = parser.parse_args()
    
    client = ChromaRESTClient(args.base_url)
    
    try:
        if args.search:
            result = client.search(args.search, args.results, args.collection)
            print_search_results(result)
        
        elif args.index:
            file_patterns = args.patterns.split(",") if args.patterns else None
            result = client.index(args.project_root, file_patterns, args.max_size, args.collection)
            print_index_result(result)
        
        elif args.index_status:
            result = client.get_index_status(args.index_status)
            print_index_status(result)
        
        elif args.stats:
            result = client.get_stats(args.collection)
            print_stats(result)
        
        elif args.files:
            result = client.list_files(args.collection)
            if isinstance(result, list):
                print(f"Found {len(result)} files:")
                for file_info in result[:20]:  # Show first 20 files
                    print(f"  {file_info['file_path']} ({file_info['language']}, {file_info['chunk_count']} chunks)")
                if len(result) > 20:
                    print(f"  ... and {len(result) - 20} more files")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
        
        elif args.collections:
            result = client.list_collections()
            if isinstance(result, dict) and "collections" in result:
                collections = result["collections"]
                print(f"Found {len(collections)} collections:")
                for col in collections:
                    print(f"  {col['name']}: {col['count']} documents")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
        
        elif args.similar:
            result = client.search_similar(args.similar, args.similar_results)
            print_search_results(result)
        
        elif args.health:
            result = client.health_check()
            print_health(result)
        
        else:
            # Show help
            print("Chroma REST Client for OpenCode")
            print(f"Base URL: {args.base_url}")
            print("\nUsage:")
            print("  --search QUERY           Search for code")
            print("  --results N              Number of results (default: 5)")
            print("  --collection NAME        Collection name (default: codebase_vectors)")
            print("  --index                  Index codebase")
            print("  --project-root PATH      Project root directory (default: .)")
            print("  --patterns PAT           File patterns (e.g., '**/*.java,**/*.py')")
            print("  --max-size MB            Maximum file size in MB (default: 10)")
            print("  --index-status JOB_ID    Get indexing job status")
            print("  --stats                  Get server statistics")
            print("  --files                  List indexed files")
            print("  --collections            List available collections")
            print("  --similar CHUNK_ID       Find similar chunks")
            print("  --similar-results N      Number of similar results (default: 5)")
            print("  --health                 Check API health")
            print("  --base-url URL           API Gateway base URL (default: http://localhost:8000)")
            print("\nExamples:")
            print(f"  {sys.argv[0]} --search 'database connection' --results 3")
            print(f"  {sys.argv[0]} --index --project-root /path/to/project --patterns '**/*.java,**/*.md'")
            print(f"  {sys.argv[0]} --index-status abc123-456-def")
            print(f"  {sys.argv[0]} --stats")
            print(f"  {sys.argv[0]} --health")
    
    finally:
        client.close()

if __name__ == "__main__":
    main()