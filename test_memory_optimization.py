#!/usr/bin/env python3
"""
Test script for memory optimization in Chroma vector search
"""

import os
import sys
import time
import tracemalloc
from chroma_simple_server import ChromaSimpleServer

def get_memory_usage():
    """Get current memory usage in MB using resource module"""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB to MB
    except ImportError:
        # Fallback for Windows
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

def test_memory_optimization():
    """Test memory optimization features"""
    print("Testing memory optimization for Chroma vector search")
    print("=" * 60)
    
    # Start memory tracking
    tracemalloc.start()
    start_memory = get_memory_usage()
    
    # Initialize server
    print(f"Initial memory usage: {start_memory:.2f} MB")
    server = ChromaSimpleServer(project_root="..")
    
    # Test indexing with streaming
    print("\nTesting streaming indexing...")
    start_time = time.time()
    
    try:
        # Index with limited file patterns for 1С
        count = server.index_codebase(
            file_patterns=["**/*.xml", "**/*.bsl", "**/*.os"],
            max_file_size_mb=5
        )
        
        end_time = time.time()
        end_memory = get_memory_usage()
        
        print(f"Indexed {count} chunks in {end_time - start_time:.2f} seconds")
        print(f"Memory usage after indexing: {end_memory:.2f} MB")
        print(f"Memory increase: {end_memory - start_memory:.2f} MB")
        
        # Test search
        print("\nTesting semantic search...")
        search_start = time.time()
        results = server.semantic_search("обработка документа", n_results=3)
        search_end = time.time()
        
        print(f"Search completed in {search_end - search_start:.2f} seconds")
        print(f"Found {len(results)} results")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  File: {result['file_path']}")
            print(f"  Lines: {result['line_start']}-{result['line_end']}")
            print(f"  Score: {result['similarity_score']:.3f}")
            print(f"  Preview: {result['content'][:100]}...")
        
        # Get stats
        stats = server.get_stats()
        print(f"\nCollection stats: {stats['document_count']} documents")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    # Show memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("\nTop memory allocations:")
    for stat in top_stats[:10]:
        print(f"{stat.size / 1024:.1f} KB: {stat.traceback.format()[-1]}")
    
    tracemalloc.stop()
    
    return True

if __name__ == "__main__":
    test_memory_optimization()