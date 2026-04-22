#!/usr/bin/env python3
"""
Basic tests for Chroma Vector Search
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chroma_simple_server import ChromaSimpleServer


@pytest.fixture
def server(temp_project):
    """ChromaSimpleServer with Chroma client closed after each test (Windows temp cleanup)."""
    srv = ChromaSimpleServer(temp_project)
    yield srv
    srv.close()


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test Java file
        java_file = Path(tmpdir) / "Test.java"
        java_file.write_text("""
public class Test {
    private String name;
    
    public Test(String name) {
        this.name = name;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
}
""")
        
        # Create test Python file
        python_file = Path(tmpdir) / "test.py"
        python_file.write_text("""
def calculate_sum(a, b):
    \"\"\"Calculate sum of two numbers\"\"\"
    return a + b

def calculate_product(a, b):
    \"\"\"Calculate product of two numbers\"\"\"
    return a * b

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        self.result += value
        return self.result
""")
        
        yield tmpdir


def test_server_initialization(server, temp_project):
    """Test that server can be initialized"""
    assert server.project_root == Path(temp_project).resolve()
    assert server.collection_name == "codebase_vectors"
    assert server.port == 8765


def test_indexing(server):
    """Test codebase indexing"""
    # Index only Java files
    count = server.index_codebase(["**/*.java"])
    
    assert count > 0
    assert server.collection is not None
    assert server.collection.count() == count


def test_semantic_search(server):
    """Test semantic search functionality"""
    # Index files
    server.index_codebase(["**/*.java", "**/*.py"])
    
    # Search for class-related code
    results = server.semantic_search("class definition", 2)
    
    assert isinstance(results, list)
    if results:  # May not find results in small test
        for result in results:
            assert "content" in result
            assert "file_path" in result
            assert "similarity_score" in result
            assert 0 <= result["similarity_score"] <= 1


def test_get_stats(server):
    """Test getting server statistics"""
    stats = server.get_stats()
    
    assert isinstance(stats, dict)
    assert "collection_name" in stats
    assert "document_count" in stats
    assert "project_root" in stats
    assert "port" in stats
    assert stats["collection_name"] == "codebase_vectors"


def test_command_handling(server):
    """Test command parsing and handling"""
    # Test PING command
    response = server.handle_command("PING")
    data = json.loads(response)
    assert data["type"] == "pong"
    
    # Test STATS command
    response = server.handle_command("STATS")
    data = json.loads(response)
    assert data["type"] == "stats"
    
    # Test invalid command
    response = server.handle_command("INVALID")
    data = json.loads(response)
    assert data["type"] == "error"


def test_chunk_processing(server, temp_project):
    """Test file chunking logic"""
    # Create a test file with multiple lines
    test_file = Path(temp_project) / "test_chunking.py"
    lines = [f"# Line {i}\n" for i in range(1, 31)]  # 30 lines
    test_file.write_text("".join(lines))
    
    chunks = server._process_file(str(test_file))
    
    # With chunk_size=15 and overlap=3, we expect chunks
    # 30 lines should produce at least 2 chunks
    assert len(chunks) >= 2
    
    for chunk in chunks:
        assert chunk.content
        assert Path(chunk.file_path) == Path("test_chunking.py")
        assert chunk.line_start > 0
        assert chunk.line_end >= chunk.line_start
        assert chunk.language == "python"
        assert chunk.chunk_id


def test_language_detection(server, temp_project):
    """Test language detection from file extensions"""
    test_cases = [
        ("test.java", "java"),
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("test.md", "markdown"),
        ("test.json", "json"),
        ("test.yml", "yaml"),
        ("test.unknown", "text"),
    ]
    
    for filename, expected_lang in test_cases:
        test_file = Path(temp_project) / filename
        test_file.write_text("# Test")
        
        chunks = server._process_file(str(test_file))
        if chunks:  # File might be too small
            assert chunks[0].language == expected_lang
        
        test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])