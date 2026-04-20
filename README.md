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
- **Multi-language Support**: Java, Python, JavaScript, TypeScript, and more
- **Simple TCP Protocol**: Works with Python 3.9+
- **OpenCode Integration**: Custom tools for all agents
- **Persistent Storage**: Index survives server restarts
- **Fast Queries**: ~1 second response time

## 🏗️ Architecture

```
┌─────────────┐    TCP (8765)    ┌─────────────┐    Vector Search    ┌─────────────┐
│   OpenCode  │ ◄──────────────► │   Chroma    │ ◄────────────────► │   ChromaDB  │
│   Agent     │   JSON over TCP  │   Server    │   Embeddings       │   Storage   │
└─────────────┘                  └─────────────┘                    └─────────────┘
       │                               │                                    │
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
- Handles indexing and search requests
- Python 3.9+ compatible

### 2. **Chroma Client** (`chroma_client.py`)
- Command-line interface for testing
- Can be used independently of OpenCode

### 3. **OpenCode Configuration** (`opencode_chroma_simple.jsonc`)
- Custom tools definition for OpenCode
- Integration with Scout, Smith, and Architect agents

### 4. **Utility Scripts**
- `start_chroma_mcp.sh` - Launch script
- `install_chroma.sh` - Dependency installer

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
| Markdown | `.md` | Documentation |
| JSON/YAML | `.json`, `.yml`, `.yaml` | Config files |

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

### In OpenCode Prompts

```bash
# Semantic search for database code
@scout Find database connection code using chroma_semantic_search

# Search for UI patterns
@scout How are Swing buttons implemented? Use semantic search

# Find architectural patterns
@architect Plan feature based on existing patterns found via chroma_semantic_search
```

### Command Line

```bash
# Test server
python chroma_client.py --ping

# Search for code
python chroma_client.py --search "authentication system" --results 5

# Get statistics
python chroma_client.py --stats

# Re-index codebase
python chroma_client.py --index --patterns "**/*.java,**/*.py"
```

## 📈 Performance

| Operation | Time | Memory | Storage |
|-----------|------|--------|---------|
| Initial Indexing | ~2-3 sec per 100 files | ~50 MB | ~5 MB per 1000 chunks |
| Search Query | ~1 sec | ~10 MB | - |
| Server Runtime | - | ~100 MB | - |

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