# WebSocket API Documentation

## Overview
The Chroma Simple Server now includes WebSocket support for real-time bidirectional communication. This enables:
- Real-time search results
- Progress updates during indexing
- Server statistics streaming
- Event subscriptions
- Lower latency compared to HTTP requests

## Quick Start

### Starting the Server with WebSocket Support
```bash
# Start server with WebSocket (default port 8766)
python chroma_simple_server.py --server --websocket-port 8766

# Start server without WebSocket
python chroma_simple_server.py --server --no-websocket
```

### Connecting to WebSocket
```javascript
// JavaScript example
const ws = new WebSocket('ws://localhost:8766');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

// Send a ping message
ws.send(JSON.stringify({
    type: 'ping',
    id: 'test_001',
    data: {}
}));
```

## Message Format

All WebSocket messages use JSON format:

```json
{
  "type": "message_type",
  "id": "unique_request_id",
  "data": {
    // Message-specific data
  },
  "timestamp": 1734739200.123
}
```

## Message Types

### Client Requests

| Type | Description | Data Fields |
|------|-------------|-------------|
| `ping` | Health check | None |
| `search` | Semantic search | `query`, `n_results` (default: 5) |
| `stats` | Server statistics | None |
| `gpuinfo` | GPU information | None |
| `subscribe` | Subscribe to events | `event_types` (array) |
| `unsubscribe` | Unsubscribe from events | None |

### Server Responses

| Type | Description | Data Fields |
|------|-------------|-------------|
| `pong` | Response to ping | `timestamp` |
| `search_results` | Search results | `results`, `query`, `n_results` |
| `stats_update` | Server statistics | Various server stats |
| `gpu_info` | GPU information | GPU configuration and status |
| `error` | Error message | `message` |
| `connection_info` | Connection established | `client_id`, `server_version`, `features` |

### Server Events (Broadcast)

| Type | Description | Data Fields |
|------|-------------|-------------|
| `server_stats` | Periodic stats | Server statistics |
| `index_progress` | Indexing progress | `current`, `total`, `file`, `percentage` |
| `index_complete` | Indexing complete | `count`, `total`, `file_patterns` |

## API Examples

### 1. Basic Connection
```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://localhost:8766') as ws:
        # Receive connection info
        message = await ws.recv()
        data = json.loads(message)
        print(f"Connected as client: {data['data']['client_id']}")
```

### 2. Search Request
```python
search_msg = {
    "type": "search",
    "id": "search_001",
    "data": {
        "query": "database connection",
        "n_results": 5
    }
}

await ws.send(json.dumps(search_msg))
response = await ws.recv()
results = json.loads(response)
```

### 3. Subscribe to Events
```python
subscribe_msg = {
    "type": "subscribe",
    "id": "sub_001",
    "data": {
        "event_types": ["server_stats", "index_progress"]
    }
}

await ws.send(json.dumps(subscribe_msg))
```

### 4. Get GPU Information
```python
gpu_msg = {
    "type": "gpuinfo",
    "id": "gpu_001",
    "data": {}
}

await ws.send(json.dumps(gpu_msg))
```

## Event Subscription

### Available Events
- `server_stats`: Periodic server statistics (every 30 seconds)
- `index_progress`: Progress updates during indexing
- `index_complete`: Notification when indexing completes

### Subscription Example
```javascript
// Subscribe to server stats
ws.send(JSON.stringify({
    type: 'subscribe',
    id: 'sub_001',
    data: {
        event_types: ['server_stats']
    }
}));

// Handle incoming events
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'server_stats') {
        console.log('Server stats:', data.data);
    }
};
```

## Error Handling

### Error Response Format
```json
{
  "type": "error",
  "id": "request_id",
  "data": {
    "message": "Error description"
  },
  "timestamp": 1734739200.123
}
```

### Common Errors
- `Invalid JSON`: Malformed message
- `Unknown message type`: Unsupported message type
- `Search query is required`: Missing query in search request
- `No event types specified`: Empty subscription request

## Performance Considerations

### Connection Limits
- Default: No hard limit (system-dependent)
- Recommended: < 1000 concurrent connections

### Message Size
- Maximum message size: 16KB (configurable)
- Large search results may be split into multiple messages

### Reconnection
- Automatic reconnection not implemented
- Implement exponential backoff in client

## Client Libraries

### Python
```python
import websockets
import json

class ChromaWebSocketClient:
    def __init__(self, uri='ws://localhost:8766'):
        self.uri = uri
        self.ws = None
    
    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        # Get connection info
        message = await self.ws.recv()
        return json.loads(message)
    
    async def search(self, query, n_results=5):
        msg = {
            "type": "search",
            "id": f"search_{int(time.time())}",
            "data": {"query": query, "n_results": n_results}
        }
        await self.ws.send(json.dumps(msg))
        response = await self.ws.recv()
        return json.loads(response)
```

### JavaScript
```javascript
class ChromaWebSocketClient {
    constructor(url = 'ws://localhost:8766') {
        this.url = url;
        this.ws = null;
        this.callbacks = new Map();
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const callback = this.callbacks.get(data.id);
            if (callback) {
                callback(data);
                this.callbacks.delete(data.id);
            }
        };
        
        return new Promise((resolve) => {
            this.ws.onopen = () => resolve();
        });
    }
    
    search(query, nResults = 5) {
        const id = `search_${Date.now()}`;
        const msg = {
            type: 'search',
            id,
            data: { query, n_results: nResults }
        };
        
        return new Promise((resolve) => {
            this.callbacks.set(id, resolve);
            this.ws.send(JSON.stringify(msg));
        });
    }
}
```

## Testing

### Test Script
```bash
# Run the test client
python test_websocket.py

# Test with custom URI
python test_websocket.py ws://localhost:8766
```

### Manual Testing with wscat
```bash
# Install wscat
npm install -g wscat

# Connect and test
wscat -c ws://localhost:8766
> {"type": "ping", "id": "test", "data": {}}
< {"type": "pong", "id": "test", "data": {...}}
```

## Migration from TCP Protocol

### TCP Protocol (Legacy)
```bash
echo "SEARCH|database connection|5" | nc localhost 8765
```

### WebSocket Protocol (Recommended)
```javascript
// More features, real-time updates, bidirectional
ws.send(JSON.stringify({
    type: 'search',
    data: {query: 'database connection', n_results: 5}
}));
```

## Configuration

### Command Line Options
```bash
# WebSocket port (default: 8766)
--websocket-port 8766

# Disable WebSocket
--no-websocket

# TCP port (default: 8765)
--port 8765
```

### Server Configuration
- WebSocket server starts automatically when `--server` is used
- Both TCP and WebSocket servers can run simultaneously
- WebSocket requires `websockets` Python package

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Check if server is running: `python chroma_simple_server.py --server`
   - Verify port: Default is 8766 for WebSocket

2. **ModuleNotFoundError: No module named 'websockets'**
   ```bash
   pip install websockets
   ```

3. **Slow response times**
   - Check GPU configuration
   - Monitor server resources
   - Consider batch size optimization

4. **WebSocket connection drops**
   - Implement ping/pong in client
   - Add reconnection logic
   - Check network stability

### Logging
Enable debug logging for troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

### Current Implementation
- Localhost only binding
- No authentication
- No encryption (WebSocket over ws://)

### Production Recommendations
1. Use wss:// (WebSocket Secure)
2. Implement authentication
3. Add rate limiting
4. Use reverse proxy (nginx, Apache)
5. Enable CORS if needed

### Example nginx Configuration
```nginx
location /ws/ {
    proxy_pass http://localhost:8766;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host $host;
}
```

## Future Enhancements

### Planned Features
1. **Authentication**: JWT tokens, API keys
2. **Compression**: Message compression for large results
3. **Binary protocol**: Protobuf for better performance
4. **Cluster support**: Multiple server instances
5. **Metrics**: Prometheus metrics endpoint

### Community Contributions
- Client libraries for other languages
- UI components for real-time search
- Integration with popular IDEs
- Plugin system for custom events