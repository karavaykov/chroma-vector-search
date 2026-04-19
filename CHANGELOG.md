# Changelog

All notable changes to Chroma Vector Search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation
- Python 3.9 compatibility layer
- TCP server protocol for OpenCode integration
- Multi-language code indexing support
- Semantic search with Sentence Transformers
- OpenCode custom tools configuration
- Comprehensive documentation and examples

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- MCP dependency (requires Python 3.10+)
- Binary index files from repository

### Fixed
- N/A (initial release)

### Security
- N/A (initial release)

## [0.1.0] - 2025-04-19

### Added
- **Core Features**:
  - ChromaDB vector database integration
  - Semantic code search using all-MiniLM-L6-v2
  - TCP server on port 8765 for Python 3.9 compatibility
  - Multi-language support (Java, Python, JavaScript, TypeScript, etc.)
  - Code chunking with configurable size and overlap
  
- **OpenCode Integration**:
  - Custom tools for semantic search
  - Integration with Scout, Smith, and Architect agents
  - Example configuration files
  - Usage examples and prompts
  
- **Developer Tools**:
  - Command-line client for testing
  - Start/stop scripts
  - Dependency installation script
  - Performance benchmarking
  
- **Documentation**:
  - Comprehensive README with examples
  - API documentation
  - Contribution guidelines
  - Troubleshooting guide
  - Example usage scripts

### Technical Details:
- **Server**: `chroma_simple_server.py` - TCP server with JSON protocol
- **Client**: `chroma_client.py` - Command-line interface
- **Configuration**: `opencode_chroma_simple.jsonc` - OpenCode integration
- **Dependencies**: ChromaDB, Sentence Transformers, NumPy, Pandas
- **Compatibility**: Python 3.9+, macOS/Linux/Windows

### Performance:
- **Indexing**: ~2-3 seconds per 100 files
- **Search**: ~1 second per query
- **Memory**: ~50 MB for embedding model
- **Storage**: ~5 MB per 1000 code chunks

### Supported Languages:
- Java (.java)
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Go (.go), Rust (.rs), C/C++ (.c, .cpp, .h)
- C# (.cs), PHP (.php), Ruby (.rb)
- Swift (.swift), Kotlin (.kt), Scala (.scala)
- Markdown (.md), JSON (.json), YAML (.yml, .yaml)

## Key Features in v0.1.0:

1. **Semantic Search**: Find code by meaning, not just keywords
2. **Python 3.9 Compatible**: Works with default macOS Python
3. **Simple Integration**: TCP protocol instead of complex MCP
4. **Persistent Storage**: Index survives server restarts
5. **OpenCode Ready**: Pre-configured for immediate use
6. **Multi-language**: Support for 15+ programming languages
7. **Configurable**: Adjustable chunk size and overlap
8. **Lightweight**: Minimal dependencies and memory footprint

## Upgrade Notes:
- This is the initial release
- No migration needed from previous versions
- Compatible with OpenCode v1.0+
- Requires Python 3.9 or later

## Known Limitations:
- No real-time indexing (requires manual re-index)
- Single-file JSON storage (no sharding)
- Basic error handling
- No authentication/authorization

## Roadmap for Next Release:
- Real-time file watching and indexing
- Improved error handling and recovery
- Additional embedding model options
- Web interface for search results
- Docker containerization
- Performance optimizations

---

*Changelog format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)*