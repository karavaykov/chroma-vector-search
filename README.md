# Chroma Vector Search for OpenCode

[English](README.md) | [Русский](README.ru.md) | [中文](README.zh.md)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5+-green.svg)](https://www.trychroma.com/)
[![OpenCode](https://img.shields.io/badge/OpenCode-Integration-orange.svg)](https://opencode.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Semantic code search integration for OpenCode using ChromaDB vector database. Enables natural language search across your codebase. TCP-based alternative to MCP (Python 3.9+ compatible).

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/chroma-vector-search.git
cd chroma-vector-search

# Install dependencies
pip install -r requirements.txt

# Index your codebase
python chroma_simple_server.py --index

# Start the server
python chroma_simple_server.py --server
```

### OpenCode Integration

```bash
# Copy configuration
cp opencode_chroma_simple.jsonc opencode.json

# Run OpenCode
opencode
```

## 📖 Features

- **Semantic Search**: Find code by meaning, not just keywords
- **Hybrid Search**: Combines semantic + keyword search for better accuracy
- **Multi-language Support**: Java, Python, JavaScript, TypeScript, and more
- **Enterprise 1C/BSL Support**: Specialized parser with metadata extraction
- **Simple TCP Protocol**: Works with Python 3.9+
- **WebSocket API**: Real-time updates and bidirectional communication
- **OpenCode Integration**: Custom tools for all agents
- **Persistent Storage**: Index survives server restarts
- **Fast Queries**: ~1 second response time
- **Memory Optimization**: Streaming batch processing for large codebases
- **Enterprise Metadata**: Author, version, dates, parameters for 1C code
- **GPU Acceleration**: CUDA and MPS support for faster embeddings (2.6x-14.7x speedup)
- **Advanced search (v1.1.0)**: Regex over indexed text, optional context lines around hits, and streaming results (WebSocket + REST SSE)

## 🏗️ Architecture

```
┌─────────────┐    TCP (8765)    ┌─────────────┐    Vector Search    ┌─────────────┐
│   OpenCode  │ ◄──────────────► │   Chroma    │ ◄────────────────► │   ChromaDB  │
│   Agent     │   JSON over TCP  │   Server    │   Embeddings       │   Storage   │
└─────────────┘                  └─────────────┘                    └─────────────┘
       │        WebSocket (8766)        │                                    │
       │ ◄───────────────────────────── │                                    │
       │ Custom Tools                  │ Sentence Transformers             │ .chroma_db/
       ▼                               ▼                                    ▼
┌─────────────┐              ┌──────────────────┐                 ┌──────────────────┐
│chroma_search│              │all-MiniLM-L6-v2  │                 │SQLite + HNSW     │
│chroma_index │              │Embedding Model   │                 │Vector Index      │
│chroma_stats │              └──────────────────┘                 └──────────────────┘
└─────────────┘
```

## 🛠️ Components

### 1. **Chroma Simple Server** (`chroma_simple_server.py`)
- TCP server on port 8765
- WebSocket server on port 8766 (real-time updates)
- Handles indexing and search requests
- Python 3.9+ compatible

### 2. **Chroma Client** (`chroma_client.py`)
- Command-line interface for testing
- Can be used independently of OpenCode

### 3. **Enterprise 1C/BSL Parser** (`chroma_simple_server.py`)
- Specialized parser for 1C Business Studio Language
- Semantic chunking by procedures and functions
- Enterprise metadata extraction (author, dates, versions)
- Contextual chunking with overlapping context

### 4. **Hybrid Search System** (`keyword_search.py`, `search_fuser.py`)
- **Keyword Search**: TF-IDF based full-text search with inverted index
- **Search Fusion**: Combines semantic and keyword results using RRF and Weighted Fusion
- **Adaptive Weights**: Automatically adjusts weights based on query complexity
- **Multi-level Caching**: LRU cache for embeddings and keyword index

### 5. **Memory Optimization System**
- Streaming batch processing for large codebases
- LRU caching for embedding models
- Selective indexing with file size limits
- Reduced memory footprint by 60-70%

### 6. **OpenCode Configuration** (`opencode_chroma_simple.jsonc`)
- Custom tools definition for OpenCode
- Integration with Scout, Smith, and Architect agents

### 7. **Utility Scripts**
- `start_chroma_mcp.sh` - Launch script
- `install_chroma.sh` - Dependency installer

### 8. **Web Interface** (`web_ui/`)
- Interactive UI for search and indexing
- Real-time WebSocket progress updates
- Hybrid search controls (semantic vs keyword weights)
- Syntax highlighting and metadata display

## 🗺️ Development Roadmap

Based on enterprise testing results, we have developed a 6-week roadmap for enterprise optimization:

**Key Goals:**
1. Memory optimization for >50k files
2. Enhanced 1C/BSL support for enterprise projects  
3. Microservices architecture with REST API
4. Docker containerization and monitoring

**Timeline:** 6 weeks | **Expected:** 5-10x performance improvement

[View Full Roadmap](DEVELOPMENT_ROADMAP.md) | [Enterprise Test Results](ENTERPRISE_PERFORMANCE_TEST.md)

## 📊 Supported Languages

| Language | Extensions | Notes |
|----------|------------|-------|
| Java | `.java` | Full support |
| Python | `.py` | Full support |
| JavaScript | `.js`, `.jsx` | Full support |
| TypeScript | `.ts`, `.tsx` | Full support |
| Go | `.go` | Basic support |
| Rust | `.rs` | Basic support |
| C/C++ | `.c`, `.cpp`, `.h` | Basic support |
| C# | `.cs` | Basic support |
| PHP | `.php` | Basic support |
| Ruby | `.rb` | Basic support |
| Swift | `.swift` | Basic support |
| Kotlin | `.kt` | Basic support |
| Scala | `.scala` | Basic support |
| 1C/BSL | `.bsl`, `.os` | **Enterprise support** with metadata |
| Markdown | `.md` | Documentation |
| JSON/YAML | `.json`, `.yml`, `.yaml` | Config files |
| XML | `.xml` | Configuration files |

## 🚀 Development Progress

### ✅ Phase 1: Memory Optimization (Completed)
- **Streaming batch processing** - Reduced memory usage by 60-70%
- **LRU caching** for embedding models (1000-entry cache)
- **Selective indexing** with file size limits
- **Commit:** `6cd7ba1` - Phase 1: Memory optimization and 1C/BSL support

### ✅ Phase 2: Enterprise 1C/BSL Support (Completed)
- **Specialized 1C/BSL parser** with semantic chunking
- **Enterprise metadata extraction** (author, dates, versions, parameters)
- **Contextual chunking** with overlapping context
- **Integration with Chroma** metadata storage
- **Comprehensive tests** for 1C parser functionality
- **Commit:** `8d0bf70` - Phase 2: Enterprise metadata and 1C/BSL support

### 🟡 Phase 3: Microservices Architecture (In Progress)
- **REST API** instead of TCP
- **Indexing Service** separate from Search Service
- **Docker containerization**
- **Target:** Completion by 26 May 2026

### 📅 Phase 4: Enterprise Readiness (Planned)
- **Monitoring** with Prometheus/Grafana
- **CI/CD pipeline**
- **API documentation**
- **Target release:** v1.0.0 by 7 June 2026

**See full roadmap:** [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)

## 🔧 Configuration

### Server Configuration

```python
# Default settings in chroma_simple_server.py
CHUNK_SIZE = 15      # Lines per code chunk
OVERLAP = 3          # Overlapping lines between chunks
PORT = 8765          # Server port
MODEL = 'all-MiniLM-L6-v2'  # Embedding model
```

### OpenCode Tools

```json
{
  "custom_tools": {
    "chroma_semantic_search": {
      "description": "Search codebase using semantic similarity",
      "command": ["python", "chroma_client.py", "--search", "{query}", "--results", "{n_results}", "--port", "8765"]
    }
  }
}
```

## 🎯 Usage Examples

### Hybrid Search Examples

```bash
# Semantic search (default) - for conceptual queries
python chroma_client.py --search "how to implement caching" --results 5

# Keyword search - for exact function/class names
python chroma_client.py --search "UserRepository" --search-type keyword --results 10

# Hybrid search with automatic weight adjustment
python chroma_client.py --search "create REST API endpoint" --search-type hybrid --results 8

# Hybrid search with custom weights
python chroma_client.py --search "calculateTotalPrice function" --search-type hybrid \
  --semantic-weight 0.3 --keyword-weight 0.7 --results 5

# Hybrid search with RRF fusion method
python chroma_client.py --search "database transaction handling" --search-type hybrid \
  --fusion-method rrf --results 5
```

### In OpenCode Prompts

```bash
# Semantic search for database code
@scout Find database connection code using chroma_semantic_search

# Keyword search for exact patterns
@smith Find UserRepository implementations using chroma_hybrid_search with keyword_weight=0.8

# Hybrid search for mixed queries
@architect Plan authentication system based on existing patterns using hybrid search
```

### Command Line

```bash
# Test server
python chroma_client.py --ping

# Search for code (semantic by default)
python chroma_client.py --search "authentication system" --results 5

# Get statistics including hybrid search info
python chroma_client.py --stats

# Re-index codebase (includes keyword index)
python chroma_client.py --index --patterns "**/*.java,**/*.py"
```

## 🌐 Web Interface (New in v1.1.0)

Chroma Vector Search now includes a built-in Web UI for easier interaction.

### Starting the Web UI
The Web UI is served automatically by the API Gateway microservice:
```bash
# Start the microservices (including API Gateway)
./start_microservices.sh

# Open your browser and navigate to:
# http://localhost:8000/
```

### Features
- **Search:** Perform Semantic, Keyword, or Hybrid searches directly from the browser.
- **Hybrid Controls:** Adjust semantic vs keyword weights using sliders.
- **Indexing:** Trigger codebase indexing and watch real-time progress via WebSocket.
- **Syntax Highlighting:** Code results are displayed with proper syntax highlighting.
- **Metadata Badges:** View 1C/BSL enterprise metadata (author, module type, calls) directly in the results.

### Advanced search (v1.1.0)
- **Regex search:** Pattern search over in-memory documents from the keyword index (index the codebase first so the keyword index is populated).
- **Context around hits:** Use `context_lines` (symmetric) or `context_before` / `context_after` on semantic, keyword, hybrid, and regex search (monolith `chroma_simple_server.py` and WebSocket API).
- **Streaming:** In the Web UI, enable streaming to receive hits progressively. WebSocket clients can set `stream: true` on `search` messages and handle `search_result_chunk` plus a final `search_complete`. With microservices, `POST /api/v1/search/stream` on the API Gateway proxies to the Search Service (Server-Sent Events).

## 🌐 WebSocket API (New in v1.1.0)

Real-time bidirectional communication with WebSocket support:

### WebSocket Features
- **Real-time search results**: Immediate response streaming
- **Chunked search streaming (v1.1.0):** When `data.stream` is true, the server emits `search_result_chunk` messages and ends with `search_complete` (in addition to one-shot `search_results`).
- **Progress updates**: Live indexing progress
- **Event subscriptions**: Subscribe to server events
- **Bidirectional communication**: Server can push updates
- **Lower latency**: Compared to HTTP/TCP requests

### Quick Start with WebSocket
```bash
# Start server with WebSocket (default port 8766)
python chroma_simple_server.py --server --websocket-port 8766

# Test WebSocket connection
python test_websocket.py

# Start without WebSocket
python chroma_simple_server.py --server --no-websocket
```

### WebSocket Client Example
```python
import asyncio
import websockets
import json

async def search_code():
    async with websockets.connect('ws://localhost:8766') as ws:
        # Send search request
        await ws.send(json.dumps({
            "type": "search",
            "id": "req_001",
            "data": {"query": "database", "n_results": 5}
        }))
        
        # Receive results
        response = await ws.recv()
        results = json.loads(response)
        print(f"Found {len(results['data']['results'])} results")
```

### Event Subscription
```javascript
// JavaScript WebSocket client
const ws = new WebSocket('ws://localhost:8766');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'search_results') {
        console.log('Search results:', data.data.results);
    } else if (data.type === 'server_stats') {
        console.log('Server update:', data.data);
    }
};

// Subscribe to server stats
ws.send(JSON.stringify({
    type: 'subscribe',
    data: {event_types: ['server_stats']}
}));
```

For complete API documentation, see [docs/WEBSOCKET_API.md](docs/WEBSOCKET_API.md).

## 🚀 GPU Acceleration (New in v1.1.0)

Accelerate embedding generation with GPU support for NVIDIA CUDA and Apple Silicon MPS:

### Installation with GPU Support

```bash
# For NVIDIA GPUs (CUDA) - 10-16x speedup
pip install -r requirements-gpu.txt

# For Apple Silicon (MPS) - 8-12x speedup
pip install torch torchvision torchaudio
pip install -r requirements.txt

# Or install with optional dependencies
pip install ".[gpu]"
```

### Usage Examples

```bash
# Enable GPU acceleration (auto-detect best device)
python chroma_simple_server.py --server --gpu

# Use specific GPU device
python chroma_simple_server.py --server --gpu --gpu-device cuda      # NVIDIA CUDA
python chroma_simple_server.py --server --gpu --gpu-device mps       # Apple Silicon
python chroma_simple_server.py --server --gpu --gpu-device cpu       # Force CPU

# Optimize for batch processing
python chroma_simple_server.py --server --gpu --gpu-batch-size 64 --gpu-mixed-precision

# Index with GPU acceleration
python chroma_simple_server.py --index --gpu --gpu-device auto
```

### Complete GPU Options

```bash
--gpu                    # Enable GPU acceleration
--gpu-device auto        # Device: auto, cuda, cpu, mps (default: auto)
--gpu-batch-size 32      # Batch size for GPU processing (default: 32)
--gpu-mixed-precision    # Enable mixed precision (float16)
--gpu-cache-size 1000    # Embedding cache size (default: 1000)
```

### Performance Gains (Tested on Apple M1)

| Operation | CPU Time | GPU Time (MPS) | Speedup |
|-----------|----------|----------------|---------|
| Search query | 4-39ms | 2-4ms | 2.6x-14.7x |
| Batch encoding (32 texts) | 204ms | 85ms | 2.4x |
| Batch encoding (64 texts) | 304ms | 24ms | 12.6x |
| Batch encoding (128 texts) | 601ms | 49ms | 12.3x |

**Expected performance on NVIDIA CUDA:** 10-16x speedup for batch processing

See [GPU Acceleration Guide](docs/GPU_ACCELERATION.md) for detailed instructions and [Performance Tests](ENTERPRISE_PERFORMANCE_TEST_WITH_GPU.md) for complete results.

## 📈 Performance

### CPU Mode (Baseline)
| Operation | Time | Memory | Storage |
|-----------|------|--------|---------|
| Initial Indexing | ~2-3 sec per 100 files | ~50 MB | ~5 MB per 1000 chunks |
| Search Query | ~1 sec | ~10 MB | - |
| Server Runtime | - | ~100 MB | - |
| Batch Encoding | ~210 texts/sec | ~100 MB | - |

### GPU Mode (Apple M1 MPS)
| Operation | Time | Speedup | GPU Memory |
|-----------|------|---------|------------|
| Search Query | 2-4ms | 2.6x-14.7x | ~1 GB |
| Batch Encoding | ~2,600 texts/sec | 12.3x | ~1-2 GB |
| Large Projects | 5-8x faster than grep | - | ~1-2 GB |

### GPU Mode (NVIDIA CUDA - Expected)
| Operation | Time | Speedup | GPU Memory |
|-----------|------|---------|------------|
| Search Query | ~20ms | 2.5x | ~1 GB |
| Batch Encoding | ~3,400 texts/sec | 16x | ~1-2 GB |
| Indexing | ~0.2-0.3 sec per 100 files | 10x | ~1-2 GB |

**See complete performance tests:** [ENTERPRISE_PERFORMANCE_TEST.md](ENTERPRISE_PERFORMANCE_TEST.md) | [GPU Acceleration Tests](ENTERPRISE_PERFORMANCE_TEST_WITH_GPU.md)

## 🔍 Search Examples

### High-Value Queries for Common Projects

```bash
# Database and persistence
"database connection pooling"
"SQL query execution"
"ORM entity mapping"

# API and services
"REST API endpoint"
"authentication middleware"
"JSON serialization"

# UI and frontend
"button click handler"
"form validation"
"data binding"

# Architecture
"dependency injection"
"service layer pattern"
"repository pattern"
```

## 🚢 Deployment

### Local Development

```bash
# Development setup
./start_chroma_mcp.sh

# Production-like setup
python chroma_simple_server.py --server --port 8765 > server.log 2>&1 &
```

### Docker (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8765

CMD ["python", "chroma_simple_server.py", "--server", "--port", "8765"]
```

## 🧪 Testing

```bash
# Full Python test suite (from repo root)
pytest tests/ -q

# 1C/BSL parser and chunking checks
python test_1c_parser.py
```

On Windows, tests call `ChromaSimpleServer.close()` so the embedded Chroma SQLite files are released before temporary directories are removed. If you embed `ChromaSimpleServer` in your own scripts, call `close()` when you are done with a persistent client.

## 🤝 Contributing

1. **Add Language Support**
   ```python
   # Add to language_map in chroma_simple_server.py
   language_map['.vue'] = 'vue'
   language_map['.dart'] = 'dart'
   ```

2. **Improve Chunking**
   ```python
   # Adjust chunk parameters
   CHUNK_SIZE = 20
   OVERLAP = 5
   ```

3. **Add New Tools**
   ```json
   {
     "chroma_find_similar": {
       "description": "Find code similar to given snippet"
     }
    }
    ```

## 🗺️ Roadmap Progress

### ✅ Version 1.1.0 - Completed
- **GPU Acceleration** - CUDA and MPS support for faster embeddings (2.6x-14.7x speedup)
- **Performance Optimization** - Batch processing and mixed precision
- **Enterprise 1C/BSL Support** - Specialized parser with metadata extraction
- **Memory Optimization** - Streaming processing for large codebases
- **WebSocket API** - Real-time indexing and search; optional per-hit streaming (`search_result_chunk` / `search_complete`)
- **Web UI** - Search, hybrid controls, indexing, syntax highlighting, 1C metadata badges, regex/context/streaming controls
- **Hybrid search** - Semantic + keyword with fusion (RRF / weighted)
- **Advanced search** - Regex over keyword-indexed text, configurable context lines, REST `POST /api/v1/search/stream` (SSE) via API Gateway

### 🔄 Version 1.2.0 - In Progress
- Enhanced authentication (JWT, API keys)
- Broader scale-out and integrations (see [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md))

### 📅 Future Plans
- Support for 1M+ files in collections
- GitHub/GitLab integration
- IDE plugins (VS Code, IntelliJ, PyCharm)
- Kubernetes operator and Helm charts

**See full roadmap:** [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md) | [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- [ChromaDB](https://www.trychroma.com/) for the vector database
- [Sentence Transformers](https://www.sbert.net/) for embedding models
- [OpenCode](https://opencode.ai/) for the AI coding agent platform

## 📚 Documentation

- [OpenCode Documentation](https://opencode.ai/docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers Documentation](https://www.sbert.net/docs/)

## 🐛 Troubleshooting

### Common Issues

1. **Server won't start**
   ```bash
   # Check port 8765
   lsof -i :8765
   
   # Check dependencies
   pip list | grep -E "chromadb|sentence-transformers"
   ```

2. **No search results**
   ```bash
   # Check index
   python chroma_client.py --stats
   
   # Re-index
   python chroma_simple_server.py --index
   ```

3. **OpenCode can't connect**
   ```bash
   # Test connection
   python chroma_client.py --ping
   
   # Check OpenCode config
   cat opencode.json | grep chroma
   ```

### Debug Mode

```bash
# Verbose logging
python chroma_simple_server.py --server --port 8765 --verbose

# Test with sample query
python chroma_client.py --search "test query" --debug
```

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/chroma-vector-search&type=Date)](https://star-history.com/#yourusername/chroma-vector-search&Date)

---

**Ready to supercharge your code search?** Install now and start finding code by meaning, not just keywords! 🚀