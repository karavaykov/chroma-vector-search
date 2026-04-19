# Chroma Vector Search API Documentation

## Overview

Chroma Vector Search provides semantic code search capabilities through a simple TCP-based API. This document describes the server API, client usage, and integration patterns.

## Server API

### TCP Protocol

The server listens on port 8765 (configurable) and accepts simple text commands:

```
COMMAND|parameter1|parameter2|...
```

Responses are JSON-encoded strings.

### Commands

#### `PING`
Check if server is alive.

**Request:**
```
PING
```

**Response:**
```json
{
  "type": "pong",
  "status": "alive",
  "timestamp": 1745092800.123456
}
```

#### `SEARCH|query|n_results`
Perform semantic search.

**Parameters:**
- `query`: Natural language search query
- `n_results`: Number of results to return (default: 5)

**Request:**
```
SEARCH|database connection|3
```

**Response:**
```json
{
  "type": "search_results",
  "results": [
    {
      "rank": 1,
      "content": "public class Database { ... }",
      "file_path": "src/Database.java",
      "line_start": 10,
      "line_end": 25,
      "language": "java",
      "similarity_score": 0.85,
      "chunk_id": "abc123"
    }
  ]
}
```

#### `INDEX|file_patterns`
Index the codebase.

**Parameters:**
- `file_patterns`: Comma-separated file patterns (optional)

**Request:**
```
INDEX|**/*.java,**/*.py
```

**Response:**
```json
{
  "type": "index_result",
  "count": 150,
  "total": 150
}
```

#### `STATS`
Get server statistics.

**Request:**
```
STATS
```

**Response:**
```json
{
  "type": "stats",
  "stats": {
    "collection_name": "codebase_vectors",
    "document_count": 150,
    "project_root": "/path/to/project",
    "port": 8765
  }
}
```

## Python API

### Server Class

```python
from chroma_simple_server import ChromaSimpleServer

# Initialize server
server = ChromaSimpleServer(
    project_root=".",  # Project directory
    port=8765          # Server port
)

# Index codebase
count = server.index_codebase([
    "**/*.java",
    "**/*.py",
    "**/*.js"
])

# Perform search
results = server.semantic_search(
    query="authentication system",
    n_results=5
)

# Get statistics
stats = server.get_stats()

# Handle command (for custom integrations)
response = server.handle_command("SEARCH|database|3")
```

### Client Class

```python
from chroma_client import send_command

# Send commands to server
result = send_command(
    port=8765,
    command="SEARCH|database connection|3"
)

# Helper functions
from chroma_client import search, index_codebase, get_stats, ping

# Search
results = search(8765, "database connection", 3)

# Index
index_codebase(8765, "**/*.java,**/*.py")

# Get stats
stats = get_stats(8765)

# Ping
ping(8765)
```

## Configuration

### Server Configuration

```python
# Default configuration in chroma_simple_server.py
CHUNK_SIZE = 15      # Lines per code chunk
OVERLAP = 3          # Overlapping lines between chunks
PORT = 8765          # Server port
MODEL = 'all-MiniLM-L6-v2'  # Embedding model
COLLECTION_NAME = 'codebase_vectors'
```

### Language Support

The server automatically detects languages from file extensions:

```python
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
```

## Error Handling

### Error Responses

All error responses follow this format:

```json
{
  "type": "error",
  "message": "Error description"
}
```

### Common Errors

1. **Server not running**
   ```json
   {"type": "error", "message": "Server not running"}
   ```

2. **Invalid command**
   ```json
   {"type": "error", "message": "Unknown command: INVALID"}
   ```

3. **Missing parameters**
   ```json
   {"type": "error", "message": "Missing query for SEARCH"}
   ```

4. **Indexing errors**
   ```json
   {"type": "error", "message": "Failed to process file: ..."}
   ```

## Performance Considerations

### Indexing Performance

- **Chunk size**: Larger chunks = fewer embeddings but less precise
- **Overlap**: Prevents missing code at chunk boundaries
- **File patterns**: Limit to relevant file types for faster indexing

### Search Performance

- **Embedding model**: `all-MiniLM-L6-v2` is fast and accurate
- **Result count**: Limit `n_results` to needed amount
- **Query length**: Longer queries may be more accurate

### Memory Usage

- **Model**: ~50 MB for embedding model
- **Index**: ~5 MB per 1000 code chunks
- **Server**: ~100 MB total runtime

## Integration Examples

### OpenCode Integration

```json
{
  "custom_tools": {
    "chroma_semantic_search": {
      "description": "Search codebase using semantic similarity",
      "command": ["python", "chroma_client.py", "--search", "{query}", "--results", "{n_results}", "--port", "8765"],
      "parameters": {
        "query": {"type": "string", "description": "Search query"},
        "n_results": {"type": "integer", "description": "Results count", "default": 5}
      }
    }
  }
}
```

### Custom Integration

```python
import socket
import json

def chroma_search(query, n_results=5, port=8765):
    """Custom integration function"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(('localhost', port))
    
    command = f"SEARCH|{query}|{n_results}"
    sock.send(command.encode('utf-8'))
    
    response = sock.recv(65536).decode('utf-8')
    sock.close()
    
    return json.loads(response)
```

### Web Integration

```python
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    n_results = request.args.get('n', 5, type=int)
    
    # Call Chroma client
    result = subprocess.run(
        ['python', 'chroma_client.py', '--search', query, '--results', str(n_results)],
        capture_output=True,
        text=True
    )
    
    return jsonify(json.loads(result.stdout))
```

## Advanced Usage

### Custom Embedding Models

```python
from sentence_transformers import SentenceTransformer

# Use different model
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Or custom model
class CustomChromaServer(ChromaSimpleServer):
    def _init_embedding_model(self):
        self.embedding_model = SentenceTransformer('your/custom/model')
```

### Multiple Collections

```python
# Create multiple collections for different purposes
server1 = ChromaSimpleServer(project_root="./src", collection_name="source_code")
server2 = ChromaSimpleServer(project_root="./docs", collection_name="documentation")

# Search in specific collection
source_results = server1.semantic_search("function definition")
doc_results = server2.semantic_search("API documentation")
```

### Real-time Indexing

```python
import watchdog.observers
import watchdog.events

class CodeChangeHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, server):
        self.server = server
    
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Re-index changed file
            self.server.index_codebase([event.src_path])

# Watch for file changes
observer = watchdog.observers.Observer()
handler = CodeChangeHandler(server)
observer.schedule(handler, path='.', recursive=True)
observer.start()
```

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check port 8765 is available
   - Verify Python dependencies are installed
   - Check project directory exists

2. **No search results**
   - Ensure codebase is indexed
   - Check file patterns include your files
   - Try different search queries

3. **Slow performance**
   - Reduce chunk size for faster indexing
   - Limit file patterns to relevant files
   - Use faster embedding model

4. **Memory issues**
   - Reduce chunk size
   - Index fewer files at once
   - Use smaller embedding model

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or run server with verbose output
server = ChromaSimpleServer(project_root=".")
server.index_codebase(verbose=True)
```

## API Stability

### Stable Endpoints
- `PING` - Server health check
- `SEARCH` - Semantic search
- `STATS` - Server statistics

### Experimental Endpoints
- `INDEX` - Indexing (may change)
- Custom commands (subject to change)

### Versioning
API version is included in server responses:
```json
{
  "type": "pong",
  "version": "0.1.0",
  "status": "alive"
}
```

## Security Considerations

### Network Security
- Server binds to `localhost` by default
- No authentication implemented
- Use firewall rules for production

### Data Security
- Index files stored locally
- No data sent to external services
- Embeddings generated locally

### Recommendations
1. Run server behind reverse proxy
2. Add authentication for production
3. Regular security updates
4. Monitor server logs