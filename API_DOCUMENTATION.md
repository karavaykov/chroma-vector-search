# Chroma Vector Search - API Documentation

## Overview

Chroma Vector Search provides a RESTful API for semantic search in codebases. The API is organized around microservices with a single entry point through the API Gateway.

**Base URL:** `http://localhost:8000/api/v1`

## Authentication

Currently, the API does not require authentication for local development. For production deployments, configure API keys or JWT tokens in the `.env` file.

## Rate Limiting

- Default: 60 requests per minute per IP address
- Configurable via `RATE_LIMIT_PER_MINUTE` environment variable
- Exceeding limits returns HTTP 429 Too Many Requests

## Endpoints

### Health Check

#### GET `/health`

Check the health status of all services.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api-gateway": "healthy",
    "indexing": "healthy",
    "search": "healthy",
    "metadata": "healthy"
  },
  "timestamp": "2026-04-20T22:30:45.123456"
}
```

### Search

#### POST `/search`

Perform semantic search on indexed code.

**Request Body:**
```json
{
  "query": "database connection",
  "n_results": 5,
  "collection_name": "codebase_vectors",
  "filters": {
    "language": "python",
    "file_path": {"$contains": "src/"}
  },
  "where_document": {
    "$contains": "def"
  }
}
```

**Parameters:**
- `query` (required): Search query text
- `n_results` (optional, default=5): Number of results to return
- `collection_name` (optional, default="codebase_vectors"): Collection to search
- `filters` (optional): Metadata filters (ChromaDB syntax)
- `where_document` (optional): Document content filters

**Response:**
```json
{
  "query": "database connection",
  "results": [
    {
      "rank": 1,
      "similarity_score": 0.892,
      "content": "def connect_to_database():\n    conn = psycopg2.connect(...)",
      "file_path": "src/database.py",
      "line_start": 45,
      "line_end": 50,
      "language": "python",
      "chunk_id": "database.py_45_50",
      "metadata": {
        "object_type": "Function",
        "object_name": "connect_to_database",
        "author": "developer@example.com"
      }
    }
  ],
  "total_results": 1,
  "collection_name": "codebase_vectors",
  "processing_time_ms": 124.5
}
```

### Indexing

#### POST `/index`

Start indexing a codebase.

**Request Body:**
```json
{
  "project_root": "/path/to/project",
  "file_patterns": ["**/*.py", "**/*.java", "**/*.js"],
  "max_file_size_mb": 10,
  "collection_name": "codebase_vectors",
  "batch_size": 1000
}
```

**Parameters:**
- `project_root` (optional, default="."): Root directory to index
- `file_patterns` (optional, default=["**/*.java", "**/*.py", "**/*.js", "**/*.ts", "**/*.bsl", "**/*.os"]): Glob patterns for files to index
- `max_file_size_mb` (optional, default=10): Maximum file size in MB
- `collection_name` (optional, default="codebase_vectors"): Collection name
- `batch_size` (optional, default=1000): Batch size for processing

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Indexing job started",
  "timestamp": "2026-04-20T22:30:45.123456"
}
```

#### GET `/index/status/{job_id}`

Get the status of an indexing job.

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": 0.65,
  "total_files": 1000,
  "processed_files": 650,
  "total_chunks": 5000,
  "processed_chunks": 3250,
  "start_time": "2026-04-20T22:30:45.123456",
  "end_time": null,
  "error_message": null
}
```

**Status values:** `pending`, `running`, `completed`, `failed`

### Statistics

#### GET `/stats`

Get collection statistics.

**Query Parameters:**
- `collection_name` (optional, default="codebase_vectors"): Collection name

**Response:**
```json
{
  "collection_name": "codebase_vectors",
  "total_documents": 12500,
  "total_files": 2500,
  "languages": {
    "python": 8000,
    "java": 3000,
    "javascript": 1000,
    "typescript": 500
  },
  "object_types": {
    "Function": 6000,
    "Class": 3000,
    "Procedure": 2000,
    "Module": 1500
  },
  "file_extensions": {
    "py": 8000,
    "java": 3000,
    "js": 1000,
    "ts": 500
  },
  "indexed_at": "2026-04-20T21:45:30.123456",
  "last_updated": "2026-04-20T22:30:45.123456",
  "average_chunk_size": 42.5,
  "metadata_fields": ["object_type", "object_name", "author", "created_date"]
}
```

### Files

#### GET `/files`

List all indexed files.

**Query Parameters:**
- `collection_name` (optional, default="codebase_vectors"): Collection name

**Response:**
```json
[
  {
    "file_path": "src/database.py",
    "language": "python",
    "chunk_count": 15,
    "total_lines": 250,
    "indexed_at": "2026-04-20T22:30:45.123456",
    "object_type": "Module",
    "object_name": "database"
  }
]
```

### Collections

#### GET `/collections`

List available collections.

**Response:**
```json
{
  "collections": [
    {
      "name": "codebase_vectors",
      "count": 12500
    },
    {
      "name": "test_enterprise",
      "count": 100
    }
  ]
}
```

### Similar Search

#### POST `/search/similar`

Find similar code chunks.

**Request Body:**
```json
{
  "chunk_id": "database.py_45_50",
  "n_results": 5
}
```

**Parameters:**
- `chunk_id` (required): ID of the chunk to find similar items for
- `n_results` (optional, default=5): Number of similar results

**Response:** Same format as `/search` endpoint

## Direct Service Endpoints

Each microservice also exposes its own API:

### Indexing Service
- **URL:** `http://localhost:8001`
- **Health:** `GET /health`
- **Index:** `POST /index`
- **Status:** `GET /index/status/{job_id}`
- **Delete:** `DELETE /index/{collection_name}`

### Search Service
- **URL:** `http://localhost:8002`
- **Health:** `GET /health`
- **Search:** `POST /search`
- **Similar:** `POST /search/similar`
- **Metadata Search:** `GET /search/metadata`
- **Collections:** `GET /collections`

### Metadata Service
- **URL:** `http://localhost:8003`
- **Health:** `GET /metadata/health`
- **Stats:** `GET /metadata/stats`
- **Files:** `GET /metadata/files`
- **Update:** `POST /metadata/update`
- **Schema:** `GET /metadata/schema`

## Error Handling

### Error Response Format
```json
{
  "detail": "Error message description",
  "status": 400,
  "title": "Bad Request",
  "type": "about:blank"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created
- `202 Accepted`: Request accepted for processing
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Examples

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

def search_code(query, n_results=5):
    response = requests.post(
        f"{BASE_URL}/search",
        json={
            "query": query,
            "n_results": n_results
        }
    )
    response.raise_for_status()
    return response.json()

def index_codebase(project_root, file_patterns=None):
    if file_patterns is None:
        file_patterns = ["**/*.py", "**/*.java"]
    
    response = requests.post(
        f"{BASE_URL}/index",
        json={
            "project_root": project_root,
            "file_patterns": file_patterns
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
results = search_code("database connection")
print(f"Found {len(results['results'])} results")

job = index_codebase("/path/to/project")
print(f"Indexing job started: {job['job_id']}")
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication middleware", "n_results": 3}'

# Index codebase
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"project_root": "/home/user/project", "file_patterns": ["**/*.py"]}'

# Check indexing status
curl http://localhost:8000/api/v1/index/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Get statistics
curl http://localhost:8000/api/v1/stats
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = 'http://localhost:8000/api/v1';

interface SearchResult {
  rank: number;
  similarity_score: number;
  content: string;
  file_path: string;
  line_start: number;
  line_end: number;
  language: string;
}

async function searchCode(query: string, nResults = 5): Promise<SearchResult[]> {
  const response = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, n_results: nResults })
  });
  
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.results;
}

// Usage
const results = await searchCode('error handling');
console.log(`Found ${results.length} results`);
```

## WebSocket Support (Future)

Planned WebSocket endpoints for real-time updates:

- `/ws/indexing/progress` - Real-time indexing progress
- `/ws/search/stream` - Streaming search results
- `/ws/notifications` - System notifications

## API Versioning

The API uses URL versioning:
- Current version: `v1`
- Future versions: `v2`, `v3`, etc.

To ensure compatibility, always specify the version in the URL.

## Monitoring and Metrics

The API exposes Prometheus metrics at:
- `GET /metrics` on each service

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration histogram
- `chroma_search_requests_total` - Search request count
- `chroma_indexing_jobs_total` - Indexing job count
- `chroma_cache_hits_total` - Cache hit count
- `container_memory_usage_bytes` - Memory usage
- `container_cpu_usage_seconds_total` - CPU usage

## Best Practices

1. **Use appropriate timeouts:** Set reasonable timeouts for API calls
2. **Handle errors gracefully:** Implement retry logic for transient errors
3. **Cache responses:** Cache search results when appropriate
4. **Monitor rate limits:** Respect rate limits and implement backoff
5. **Use filters:** Use metadata filters to narrow search results
6. **Batch operations:** Use batch endpoints when available
7. **Validate inputs:** Validate request parameters before sending

## Support

For API issues or questions:
1. Check the [GitHub Issues](https://github.com/karavaykov/chroma-vector-search/issues)
2. Review the [API Documentation](https://github.com/karavaykov/chroma-vector-search/blob/main/API_DOCUMENTATION.md)
3. Join [GitHub Discussions](https://github.com/karavaykov/chroma-vector-search/discussions)