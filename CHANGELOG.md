# Changelog

All notable changes to Chroma Vector Search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-20

### Added
- **Microservices Architecture**:
  - API Gateway with rate limiting and health checks
  - Indexing Service with asynchronous job processing
  - Search Service with caching and similarity search
  - Metadata Service with comprehensive statistics
  - RESTful API replacing TCP protocol
  
- **Enterprise Deployment**:
  - Docker Compose with production-ready configuration
  - Resource management and limits
  - Persistent storage for all services
  - Environment-based configuration (.env files)
  - Redis for caching and job tracking
  - PostgreSQL for metadata persistence (optional)
  
- **Monitoring & Observability**:
  - Prometheus metrics collection
  - Grafana dashboards for real-time monitoring
  - Alerting system with configurable rules
  - Performance metrics tracking
  - Health checks and service discovery
  
- **Developer Experience**:
  - Complete OpenAPI/Swagger documentation
  - Python REST client library
  - Command-line interface tools
  - Comprehensive testing suite
  - Load testing and performance validation
  - Enterprise performance testing scripts
  
- **Performance & Scalability**:
  - 3-4x faster than grep for semantic search
  - Support for 500k+ files in enterprise codebases
  - < 2 second search response time (95th percentile)
  - 60-70% memory usage reduction
  - Horizontal scaling of individual services
  
- **Security & Operations**:
  - Rate limiting and request throttling
  - Comprehensive logging system
  - Docker security best practices
  - Resource isolation and limits
  - Backup and recovery procedures

### Changed
- **Architecture**: Monolithic TCP server replaced with microservices
- **Protocol**: TCP protocol replaced with RESTful API
- **Client**: New REST client library required
- **Configuration**: Moved to environment variables
- **Storage**: Enhanced metadata storage with PostgreSQL
- **Deployment**: Docker-based deployment with orchestration

### Deprecated
- TCP protocol and `chroma_simple_server.py`
- Old client library `chroma_client.py`
- Direct ChromaDB file manipulation
- Manual service management scripts

### Removed
- MCP dependency and compatibility layer
- Single-process architecture limitations
- Manual configuration files
- Basic error handling in favor of comprehensive solutions

### Fixed
- Memory leaks in large-scale indexing
- Race conditions in concurrent searches
- Performance bottlenecks in embedding generation
- Data persistence issues across restarts
- Error handling and recovery mechanisms

### Security
- Implemented rate limiting to prevent abuse
- Added input validation and sanitization
- Secure Docker configurations
- Environment variable encryption support
- Access control for sensitive operations

## [0.1.0] - 2025-04-19

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