#!/usr/bin/env python3
"""
Chroma Client for OpenCode integration
Communicates with ChromaSimpleServer via TCP
"""

import socket
import json
import sys
import argparse

def send_command(port: int = 8765, command: str = "PING") -> dict:
    """Send a command to Chroma server"""
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(('localhost', port))
        
        # Send command
        sock.send(command.encode('utf-8'))
        
        # Receive response
        response = sock.recv(65536).decode('utf-8')
        sock.close()
        
        # Parse JSON response
        return json.loads(response)
        
    except ConnectionRefusedError:
        return {"type": "error", "message": "Server not running"}
    except socket.timeout:
        return {"type": "error", "message": "Connection timeout"}
    except Exception as e:
        return {"type": "error", "message": str(e)}

def search(port: int, query: str, n_results: int = 5, search_type: str = "semantic",
            semantic_weight: float = 0.7, keyword_weight: float = 0.3, fusion_method: str = "weighted"):
    """Perform search (semantic, keyword, or hybrid)"""
    if search_type == "semantic":
        command = f"SEARCH|{query}|{n_results}"
    elif search_type == "keyword":
        command = f"KEYWORD_SEARCH|{query}|{n_results}"
    elif search_type == "hybrid":
        command = f"HYBRID_SEARCH|{query}|{n_results}|{semantic_weight}|{keyword_weight}|{fusion_method}"
    else:
        print(f"Error: Unknown search type '{search_type}'")
        return
    
    result = send_command(port, command)
    
    if result.get("type") == "search_results":
        results = result.get("results", [])
        if results:
            print(f"\nFound {len(results)} results for '{query}' ({search_type} search):\n")
            for item in results:
                search_type_display = item.get('search_type', search_type)
                print(f"Rank {item['rank']} (Score: {item['similarity_score']:.3f}, Type: {search_type_display})")
                print(f"File: {item['file_path']}:{item['line_start']}-{item['line_end']}")
                print(f"Language: {item['language']}")
                print(f"Content:\n{item['content'][:200]}...\n")
                print("-" * 80)
        else:
            print("No results found.")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}")

def index_codebase(port: int, file_patterns: str = None):
    """Index the codebase"""
    if file_patterns:
        command = f"INDEX|{file_patterns}"
    else:
        command = "INDEX"
    
    result = send_command(port, command)
    
    if result.get("type") == "index_result":
        print(f"Indexing complete. Added {result.get('count', 0)} documents.")
        print(f"Total documents: {result.get('total', 0)}")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}")

def get_stats(port: int):
    """Get server statistics"""
    result = send_command(port, "STATS")
    
    if result.get("type") == "stats":
        stats = result.get("stats", {})
        print(f"Chroma collection: {stats.get('collection_name')}")
        print(f"Document count: {stats.get('document_count')}")
        print(f"Project root: {stats.get('project_root')}")
        print(f"Server port: {stats.get('port')}")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}")

def ping(port: int):
    """Check if server is alive"""
    result = send_command(port, "PING")
    
    if result.get("type") == "pong":
        print(f"Server is alive (port: {port})")
        print(f"Status: {result.get('status')}")
    else:
        print(f"Server not responding: {result.get('message', 'Unknown error')}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chroma Client for OpenCode")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--results", type=int, default=5, help="Number of results")
    parser.add_argument("--search-type", type=str, default="semantic", 
                       choices=["semantic", "keyword", "hybrid"], help="Type of search")
    parser.add_argument("--semantic-weight", type=float, default=0.7, 
                       help="Weight for semantic search in hybrid mode (0.0-1.0)")
    parser.add_argument("--keyword-weight", type=float, default=0.3, 
                       help="Weight for keyword search in hybrid mode (0.0-1.0)")
    parser.add_argument("--fusion-method", type=str, default="weighted",
                       choices=["rrf", "weighted", "both"], help="Fusion method for hybrid search")
    parser.add_argument("--index", action="store_true", help="Index codebase")
    parser.add_argument("--patterns", type=str, help="File patterns for indexing (comma separated)")
    parser.add_argument("--stats", action="store_true", help="Get server statistics")
    parser.add_argument("--ping", action="store_true", help="Ping server")
    
    args = parser.parse_args()
    
    if args.search:
        search(args.port, args.search, args.results, args.search_type,
               args.semantic_weight, args.keyword_weight, args.fusion_method)
    elif args.index:
        index_codebase(args.port, args.patterns)
    elif args.stats:
        get_stats(args.port)
    elif args.ping:
        ping(args.port)
    else:
        # Show help
        print("Chroma Client for OpenCode")
        print(f"Default port: {args.port}")
        print("\nUsage:")
        print("  --search QUERY     Search for code")
        print("  --results N        Number of results (default: 5)")
        print("  --search-type TYPE Type of search: semantic, keyword, hybrid (default: semantic)")
        print("  --semantic-weight W Weight for semantic search in hybrid mode (default: 0.7)")
        print("  --keyword-weight W  Weight for keyword search in hybrid mode (default: 0.3)")
        print("  --fusion-method M  Fusion method: rrf, weighted, both (default: weighted)")
        print("  --index            Index codebase")
        print("  --patterns PAT     File patterns (e.g., '**/*.java,**/*.py')")
        print("  --stats            Get server statistics")
        print("  --ping             Ping server")
        print("  --port N           Server port (default: 8765)")
        print("\nExamples:")
        print(f"  {sys.argv[0]} --search 'database connection' --results 3")
        print(f"  {sys.argv[0]} --search 'function calculate' --search-type keyword --results 5")
        print(f"  {sys.argv[0]} --search 'API endpoint' --search-type hybrid --semantic-weight 0.6 --keyword-weight 0.4")
        print(f"  {sys.argv[0]} --index --patterns '**/*.java,**/*.md'")
        print(f"  {sys.argv[0]} --stats")

if __name__ == "__main__":
    main()