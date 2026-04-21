#!/usr/bin/env python3
"""
Integration tests for hybrid search functionality
"""

import unittest
import tempfile
import os
import sys
import time
from pathlib import Path
import threading

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chroma_simple_server import ChromaSimpleServer, GPUConfig


class TestHybridSearchIntegration(unittest.TestCase):
    """Integration tests for hybrid search"""
    
    def setUp(self):
        """Set up test server with temporary directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
        self.project_root = Path(self.temp_dir)
        
        # Create test files
        self._create_test_files()
        
        # Initialize server without GPU for testing
        gpu_config = GPUConfig(enabled=False)
        self.server = ChromaSimpleServer(
            project_root=str(self.project_root),
            port=8767,  # Use different port to avoid conflicts
            gpu_config=gpu_config,
            websocket_port=8768
        )
    
    def _create_test_files(self):
        """Create test files for indexing"""
        # Python file
        python_content = '''
def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    return a + b

def calculate_product(x, y):
    """Calculate product of two numbers"""
    return x * y

class Calculator:
    """Simple calculator class"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, a, b):
        """Add two numbers"""
        self.result = a + b
        return self.result
'''
        
        # Java file
        java_content = '''
public class Calculator {
    private int result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public int add(int a, int b) {
        this.result = a + b;
        return this.result;
    }
    
    public int multiply(int x, int y) {
        return x * y;
    }
}
'''
        
        # Markdown file
        markdown_content = '''
# Calculator Documentation

This document describes the calculator functionality.

## Functions

- `calculate_sum`: Adds two numbers
- `calculate_product`: Multiplies two numbers

## Classes

- `Calculator`: Main calculator class with methods for arithmetic operations
'''
        
        # Write files
        (self.project_root / "test_calculator.py").write_text(python_content)
        (self.project_root / "Calculator.java").write_text(java_content)
        (self.project_root / "README.md").write_text(markdown_content)
    
    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_indexing_with_keyword_index(self):
        """Test that indexing creates both vector and keyword indices"""
        # Index files
        count = self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        self.assertGreater(count, 0)
        
        # Check stats
        stats = self.server.get_stats()
        self.assertGreater(stats['document_count'], 0)
        
        # Check if keyword index was created
        if stats.get('hybrid_search_available', False):
            self.assertTrue(stats.get('keyword_index_available', False))
            self.assertGreater(stats.get('keyword_document_count', 0), 0)
    
    def test_semantic_search(self):
        """Test semantic search functionality"""
        # First index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Perform semantic search
        results = self.server.semantic_search("calculate sum of numbers", n_results=3)
        
        self.assertGreater(len(results), 0)
        
        # Check result structure
        for result in results:
            self.assertIn('content', result)
            self.assertIn('file_path', result)
            self.assertIn('similarity_score', result)
            self.assertIn('chunk_id', result)
            self.assertGreater(result['similarity_score'], 0)
    
    def test_keyword_search(self):
        """Test keyword search functionality"""
        # First index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Check if keyword search is available
        stats = self.server.get_stats()
        if not stats.get('keyword_index_available', False):
            self.skipTest("Keyword search not available")
        
        # Perform keyword search
        results = self.server.keyword_search("Calculator class", n_results=3)
        
        self.assertGreater(len(results), 0)
        
        # Check result structure
        for result in results:
            self.assertIn('content', result)
            self.assertIn('file_path', result)
            self.assertIn('similarity_score', result)
            self.assertIn('chunk_id', result)
            self.assertIn('search_type', result)
            self.assertEqual(result['search_type'], 'keyword')
    
    def test_hybrid_search(self):
        """Test hybrid search functionality"""
        # First index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Check if hybrid search is available
        stats = self.server.get_stats()
        if not stats.get('hybrid_search_available', False):
            self.skipTest("Hybrid search not available")
        
        # Perform hybrid search with different weights
        test_cases = [
            (0.7, 0.3, 'weighted'),  # Default weights
            (0.5, 0.5, 'weighted'),  # Equal weights
            (0.3, 0.7, 'weighted'),  # Keyword-heavy
            (0.8, 0.2, 'rrf'),       # RRF fusion
        ]
        
        for semantic_weight, keyword_weight, fusion_method in test_cases:
            with self.subTest(weights=(semantic_weight, keyword_weight, fusion_method)):
                results = self.server.hybrid_search(
                    query="calculator function",
                    n_results=5,
                    semantic_weight=semantic_weight,
                    keyword_weight=keyword_weight,
                    fusion_method=fusion_method
                )
                
                self.assertGreater(len(results), 0)
                
                # Check result structure
                for result in results:
                    self.assertIn('content', result)
                    self.assertIn('similarity_score', result)
                    self.assertIn('chunk_id', result)
                    self.assertIn('search_type', result)
                    self.assertEqual(result['search_type'], 'hybrid')
                    # file_path might be in metadata for some results
                    if 'file_path' not in result:
                        self.assertIn('metadata', result)
    
    def test_search_type_parameter(self):
        """Test search_type parameter in hybrid_search"""
        # First index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Test semantic-only search
        semantic_results = self.server.hybrid_search(
            query="calculate",
            n_results=3,
            search_type='semantic'
        )
        
        self.assertGreater(len(semantic_results), 0)
        for result in semantic_results:
            self.assertEqual(result.get('search_type', 'semantic'), 'semantic')
        
        # Test keyword-only search (if available)
        stats = self.server.get_stats()
        if stats.get('keyword_index_available', False):
            keyword_results = self.server.hybrid_search(
                query="Calculator",
                n_results=3,
                search_type='keyword'
            )
            
            self.assertGreater(len(keyword_results), 0)
            for result in keyword_results:
                self.assertEqual(result.get('search_type', 'keyword'), 'keyword')
    
    def test_handle_command_hybrid(self):
        """Test handle_command method with hybrid search commands"""
        # First index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Test HYBRID_SEARCH command
        response = self.server.handle_command("HYBRID_SEARCH|calculator|3|0.7|0.3|weighted")
        self.assertIsInstance(response, str)
        
        # Parse JSON response
        import json
        result = json.loads(response)
        
        self.assertEqual(result['type'], 'search_results')
        self.assertIn('results', result)
    
    def test_stats_includes_hybrid_info(self):
        """Test that stats include hybrid search information"""
        stats = self.server.get_stats()
        
        # Check for hybrid search availability flag
        self.assertIn('hybrid_search_available', stats)
        
        # If hybrid search is available, check for keyword index info
        if stats['hybrid_search_available']:
            self.assertIn('keyword_index_available', stats)
            
            if stats['keyword_index_available']:
                self.assertIn('keyword_document_count', stats)
                self.assertIn('keyword_vocabulary_size', stats)
                self.assertIn('keyword_avg_doc_length', stats)
    
    def test_empty_keyword_index(self):
        """Test behavior with empty keyword index"""
        # First index to create keyword index
        self.server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        
        # Clear keyword index if it exists
        if self.server.keyword_index:
            self.server.keyword_index.clear()
        
        # Try keyword search
        results = self.server.keyword_search("test", n_results=5)
        self.assertEqual(len(results), 0)
        
        # Try hybrid search (should fall back to semantic)
        hybrid_results = self.server.hybrid_search(
            query="calculate",
            n_results=5,
            semantic_weight=0.5,
            keyword_weight=0.5
        )
        
        # Should still return semantic results
        self.assertGreater(len(hybrid_results), 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for hybrid search"""
    
    def test_search_performance(self):
        """Test that search performance is reasonable"""
        # Skip in CI environment
        import os
        if os.getenv('CI'):
            self.skipTest("Skipping performance test in CI")
        
        # Create test server
        temp_dir = tempfile.mkdtemp(prefix="chroma_perf_test_")
        project_root = Path(temp_dir)
        
        try:
            # Create a larger test file
            content = "\n".join([f"def function_{i}(): return {i}" for i in range(100)])
            (project_root / "large_file.py").write_text(content)
            
            server = ChromaSimpleServer(
                project_root=str(project_root),
                port=8769,
                gpu_config=GPUConfig(enabled=False)
            )
            
            # Index
            import time
            start_time = time.time()
            server.index_codebase(file_patterns=["**/*.py"], max_file_size_mb=1)
            index_time = time.time() - start_time
            
            # Performance check: indexing should take less than 10 seconds
            self.assertLess(index_time, 10.0, f"Indexing took {index_time:.2f} seconds")
            
            # Search performance
            test_queries = ["function", "return value", "def function_50"]
            
            for query in test_queries:
                start_time = time.time()
                
                # Test all search types
                if server.keyword_index:
                    keyword_results = server.keyword_search(query, n_results=10)
                    keyword_time = time.time() - start_time
                    
                    # Keyword search should be fast (< 0.1 seconds for small index)
                    self.assertLess(keyword_time, 0.1, 
                                   f"Keyword search for '{query}' took {keyword_time:.3f} seconds")
                
                start_time = time.time()
                semantic_results = server.semantic_search(query, n_results=10)
                semantic_time = time.time() - start_time
                
                # Semantic search should be reasonable (< 0.5 seconds)
                self.assertLess(semantic_time, 0.5,
                               f"Semantic search for '{query}' took {semantic_time:.3f} seconds")
                
                if server.keyword_index:
                    start_time = time.time()
                    hybrid_results = server.hybrid_search(
                        query=query,
                        n_results=10,
                        semantic_weight=0.5,
                        keyword_weight=0.5
                    )
                    hybrid_time = time.time() - start_time
                    
                    # Hybrid search should not be much slower than the slowest component
                    max_expected = max(semantic_time, keyword_time) * 1.5
                    self.assertLess(hybrid_time, max_expected,
                                   f"Hybrid search for '{query}' took {hybrid_time:.3f} seconds")
        
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()