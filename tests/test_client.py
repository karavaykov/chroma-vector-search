#!/usr/bin/env python3
"""
Client tests for Chroma Vector Search
"""

import pytest
import socket
import json
import time
import threading
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chroma_client import send_command


class MockServer:
    """Mock server for testing client"""
    
    def __init__(self, port=8765):
        self.port = port
        self.server_socket = None
        self.running = False
        self.thread = None
    
    def start(self):
        """Start mock server in background thread"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        
        self.running = True
        
        def server_loop():
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    self.handle_client(client_socket)
                except socket.timeout:
                    continue
                except Exception:
                    break
        
        self.thread = threading.Thread(target=server_loop, daemon=True)
        self.thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
    
    def handle_client(self, client_socket):
        """Handle client connection"""
        try:
            data = client_socket.recv(4096).decode('utf-8').strip()
            
            if data == "PING":
                response = json.dumps({
                    "type": "pong",
                    "status": "alive",
                    "timestamp": time.time()
                })
            elif data.startswith("SEARCH|"):
                response = json.dumps({
                    "type": "search_results",
                    "results": [
                        {
                            "rank": 1,
                            "content": "Test content 1",
                            "file_path": "test1.java",
                            "line_start": 1,
                            "line_end": 10,
                            "language": "java",
                            "similarity_score": 0.85,
                            "chunk_id": "test1"
                        },
                        {
                            "rank": 2,
                            "content": "Test content 2",
                            "file_path": "test2.py",
                            "line_start": 5,
                            "line_end": 15,
                            "language": "python",
                            "similarity_score": 0.75,
                            "chunk_id": "test2"
                        }
                    ]
                })
            elif data == "STATS":
                response = json.dumps({
                    "type": "stats",
                    "stats": {
                        "collection_name": "test_collection",
                        "document_count": 100,
                        "project_root": "/test/project",
                        "port": self.port
                    }
                })
            else:
                response = json.dumps({
                    "type": "error",
                    "message": f"Unknown command: {data}"
                })
            
            client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            error_response = json.dumps({
                "type": "error",
                "message": str(e)
            })
            client_socket.send(error_response.encode('utf-8'))
        finally:
            client_socket.close()
    
    def stop(self):
        """Stop mock server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.thread:
            self.thread.join(timeout=2)


@pytest.fixture
def mock_server():
    """Create a mock server for testing"""
    server = MockServer(port=8766)  # Use different port to avoid conflicts
    server.start()
    yield server
    server.stop()


def test_send_command_ping(mock_server):
    """Test sending PING command"""
    result = send_command(8766, "PING")
    
    assert isinstance(result, dict)
    assert result["type"] == "pong"
    assert result["status"] == "alive"
    assert "timestamp" in result


def test_send_command_search(mock_server):
    """Test sending SEARCH command"""
    result = send_command(8766, "SEARCH|test query|3")
    
    assert isinstance(result, dict)
    assert result["type"] == "search_results"
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 2
    
    # Check first result
    first_result = result["results"][0]
    assert first_result["rank"] == 1
    assert first_result["content"] == "Test content 1"
    assert first_result["file_path"] == "test1.java"
    assert first_result["similarity_score"] == 0.85


def test_send_command_stats(mock_server):
    """Test sending STATS command"""
    result = send_command(8766, "STATS")
    
    assert isinstance(result, dict)
    assert result["type"] == "stats"
    assert "stats" in result
    
    stats = result["stats"]
    assert stats["collection_name"] == "test_collection"
    assert stats["document_count"] == 100
    assert stats["project_root"] == "/test/project"
    assert stats["port"] == 8766


def test_send_command_error(mock_server):
    """Test sending invalid command"""
    result = send_command(8766, "INVALID_COMMAND")
    
    assert isinstance(result, dict)
    assert result["type"] == "error"
    assert "message" in result
    assert "Unknown command" in result["message"]


def test_send_command_server_not_running():
    """Test sending command when server is not running"""
    # Use a port that's unlikely to be in use
    result = send_command(9999, "PING")
    
    assert isinstance(result, dict)
    assert result["type"] == "error"
    assert "Server not running" in result["message"] or "Connection refused" in result["message"]


def test_send_command_timeout():
    """Test command timeout"""
    # Create a socket that accepts but doesn't respond
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_socket.bind(('localhost', 8767))
    test_socket.listen(1)
    
    def accept_and_hang():
        conn, addr = test_socket.accept()
        # Don't respond, just hang
        time.sleep(2)
        conn.close()
    
    import threading
    thread = threading.Thread(target=accept_and_hang, daemon=True)
    thread.start()
    
    time.sleep(0.1)  # Let server start
    
    # This should timeout
    result = send_command(8767, "PING")
    
    assert isinstance(result, dict)
    assert result["type"] == "error"
    
    test_socket.close()


def test_command_parsing():
    """Test command string parsing logic"""
    # This tests the internal logic of the server's handle_command method
    # We'll import and test the server directly
    from chroma_simple_server import ChromaSimpleServer
    
    # Create a minimal server instance
    server = ChromaSimpleServer(".")
    try:
        # Test PING command
        response = server.handle_command("PING")
        data = json.loads(response)
        assert data["type"] == "pong"
        
        # Test STATS command
        response = server.handle_command("STATS")
        data = json.loads(response)
        assert data["type"] == "stats"
        
        # Test SEARCH command with parameters
        response = server.handle_command("SEARCH|test query|5")
        data = json.loads(response)
        # This might return error if no index, but should parse correctly
        assert "type" in data
        
        # Test invalid command
        response = server.handle_command("INVALID|param")
        data = json.loads(response)
        assert data["type"] == "error"
    finally:
        server.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])