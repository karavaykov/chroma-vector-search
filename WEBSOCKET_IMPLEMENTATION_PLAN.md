# WebSocket API Implementation Plan

## Overview
Add WebSocket support to the Chroma Simple Server for real-time updates and bidirectional communication.

## Current Architecture
- TCP socket server on port 8765
- Simple text-based protocol with pipe-separated commands
- Thread-per-connection model
- JSON responses

## WebSocket Design

### WebSocket Server
- Run on separate port (default: 8766) or same port with path-based routing
- Use `websockets` library (lightweight, async)
- Support both WebSocket and existing TCP protocol

### Message Format
```json
{
  "type": "command_type",
  "id": "request_id",
  "data": {...},
  "timestamp": "2025-01-01T00:00:00Z"
}
```

### Command Types
1. **search** - Semantic search with real-time progress
2. **index** - Index codebase with progress updates
3. **subscribe** - Subscribe to real-time events
4. **unsubscribe** - Unsubscribe from events
5. **stats** - Get server statistics
6. **ping** - Health check
7. **gpuinfo** - GPU information

### Real-time Events
1. **index_progress** - Indexing progress updates
2. **search_complete** - Search results
3. **server_stats** - Periodic server statistics
4. **gpu_status** - GPU utilization updates
5. **error** - Error notifications

## Implementation Steps

### Phase 1: Core WebSocket Server
1. Add `websockets` dependency to requirements
2. Create `WebSocketServer` class
3. Implement WebSocket message handling
4. Add command line option for WebSocket port

### Phase 2: Real-time Features
1. Implement progress tracking for indexing
2. Add subscription system for events
3. Implement periodic status updates
4. Add WebSocket-specific commands

### Phase 3: Integration
1. Update main server to support both TCP and WebSocket
2. Add configuration options
3. Update documentation
4. Add examples

## Technical Details

### Dependencies
```txt
websockets>=12.0
```

### Port Configuration
- TCP: 8765 (default)
- WebSocket: 8766 (default)
- Configurable via command line

### Concurrency Model
- Async/await for WebSocket connections
- Thread pool for CPU-intensive operations (embedding, indexing)
- Event loop for real-time notifications

## API Endpoints

### WebSocket Connection
```
ws://localhost:8766/ws
```

### Example Messages

**Search Request:**
```json
{
  "type": "search",
  "id": "req_123",
  "data": {
    "query": "database connection",
    "n_results": 5
  }
}
```

**Search Response:**
```json
{
  "type": "search_results",
  "id": "req_123",
  "data": {
    "results": [...],
    "query_time": 0.123
  }
}
```

**Index Progress:**
```json
{
  "type": "index_progress",
  "data": {
    "current": 50,
    "total": 100,
    "file": "src/main.py",
    "percentage": 50
  }
}
```

## Testing Strategy
1. Unit tests for WebSocket message parsing
2. Integration tests for real-time features
3. Performance tests with multiple connections
4. Compatibility tests with existing TCP clients

## Migration Path
1. Phase 1: Add WebSocket as optional feature
2. Phase 2: Make WebSocket default for new features
3. Phase 3: Deprecate TCP protocol (optional)