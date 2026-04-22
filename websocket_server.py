#!/usr/bin/env python3
"""
WebSocket server for Chroma Simple Server
Provides real-time updates and bidirectional communication
"""

import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Any, Set, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types"""
    SEARCH = "search"
    INDEX = "index"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    STATS = "stats"
    PING = "ping"
    GPUINFO = "gpuinfo"
    
    # Response types
    SEARCH_RESULTS = "search_results"
    INDEX_PROGRESS = "index_progress"
    INDEX_COMPLETE = "index_complete"
    STATS_UPDATE = "stats_update"
    GPU_INFO = "gpu_info"
    PONG = "pong"
    ERROR = "error"
    
    # Event types
    SERVER_STATS = "server_stats"
    GPU_STATUS = "gpu_status"
    CONNECTION_INFO = "connection_info"

@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: str
    id: str = ""
    data: Dict[str, Any] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if not self.timestamp:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "id": self.id,
            "data": self.data,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(
            type=data.get("type", ""),
            id=data.get("id", ""),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", 0.0)
        )

@dataclass
class Subscription:
    """Client subscription"""
    client_id: str
    event_types: Set[str]
    created_at: float

class WebSocketServer:
    """WebSocket server for real-time communication"""
    
    def __init__(self, chroma_server, port: int = 8766):
        self.chroma_server = chroma_server
        self.port = port
        self.clients: Dict[str, Any] = {}  # client_id -> websocket
        self.subscriptions: Dict[str, Subscription] = {}  # client_id -> subscription
        self.running = False
        self.server_task = None
        self.event_loop = None
        self.stats_interval = 30.0  # seconds
        self.stats_task = None
        
    async def handle_client(self, websocket: Any, path: str) -> None:
        """
        Handle a WebSocket client connection.
        
        Args:
            websocket: The WebSocket connection object.
            path (str): The requested path.
        """
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        
        try:
            # Send connection info
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.CONNECTION_INFO.value,
                data={
                    "client_id": client_id,
                    "server_version": "1.1.0",
                    "features": ["search", "index", "stats", "gpuinfo", "subscribe"]
                }
            ))
            
            logger.info(f"WebSocket client connected: {client_id}")
            
            # Handle messages from client
            async for message in websocket:
                try:
                    await self.handle_message(client_id, message)
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self.send_error(websocket, str(e))
                    
        except Exception as e:
            logger.error(f"WebSocket connection error for {client_id}: {e}")
        finally:
            # Clean up
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.subscriptions:
                del self.subscriptions[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def handle_message(self, client_id: str, message: str) -> None:
        """
        Handle an incoming WebSocket message.
        
        Args:
            client_id (str): The ID of the client sending the message.
            message (str): The raw JSON message string.
        """
        try:
            ws_message = WebSocketMessage.from_json(message)
            logger.debug(f"Received message from {client_id}: {ws_message.type}")
            
            # Get client websocket
            websocket = self.clients.get(client_id)
            if not websocket:
                return
            
            # Handle message based on type
            handler_name = f"handle_{ws_message.type}"
            handler = getattr(self, handler_name, None)
            
            if handler:
                await handler(client_id, websocket, ws_message)
            else:
                await self.send_error(websocket, f"Unknown message type: {ws_message.type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {client_id}: {e}")
            websocket = self.clients.get(client_id)
            if websocket:
                await self.send_error(websocket, f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            websocket = self.clients.get(client_id)
            if websocket:
                await self.send_error(websocket, str(e))
    
    async def handle_search(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle a search request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        query = message.data.get("query", "")
        n_results = message.data.get("n_results", 5)
        
        if not query:
            await self.send_error(websocket, "Search query is required")
            return
        
        # Perform search (in thread pool to avoid blocking)
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None, 
                self.chroma_server.semantic_search, 
                query, n_results
            )
            
            # Send results
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.SEARCH_RESULTS.value,
                id=message.id,
                data={
                    "results": results,
                    "query": query,
                    "n_results": n_results
                }
            ))
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await self.send_error(websocket, f"Search failed: {str(e)}")
    
    async def handle_index(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle an index request with progress updates.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        file_patterns = message.data.get("file_patterns", ["**/*.java", "**/*.py", "**/*.js", "**/*.ts"])
        
        # Start indexing in background thread
        def index_with_progress():
            try:
                # This would need to be modified to provide progress updates
                count = self.chroma_server.index_codebase(file_patterns)
                return count
            except Exception as e:
                logger.error(f"Indexing error: {e}")
                raise
        
        loop = asyncio.get_event_loop()
        try:
            # For now, just do the indexing and send completion
            count = await loop.run_in_executor(None, index_with_progress)
            
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.INDEX_COMPLETE.value,
                id=message.id,
                data={
                    "count": count,
                    "total": self.chroma_server.collection.count() if self.chroma_server.collection else 0,
                    "file_patterns": file_patterns
                }
            ))
            
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            await self.send_error(websocket, f"Indexing failed: {str(e)}")
    
    async def handle_subscribe(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle a subscription request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        event_types = set(message.data.get("event_types", []))
        
        if not event_types:
            await self.send_error(websocket, "No event types specified")
            return
        
        # Create or update subscription
        self.subscriptions[client_id] = Subscription(
            client_id=client_id,
            event_types=event_types,
            created_at=time.time()
        )
        
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.PONG.value,  # Use pong as acknowledgment
            id=message.id,
            data={
                "subscribed_to": list(event_types),
                "client_id": client_id
            }
        ))
        
        logger.info(f"Client {client_id} subscribed to: {event_types}")
    
    async def handle_unsubscribe(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle an unsubscribe request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.PONG.value,
            id=message.id,
            data={"unsubscribed": True, "client_id": client_id}
        ))
        
        logger.info(f"Client {client_id} unsubscribed")
    
    async def handle_stats(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle a stats request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        try:
            stats = self.chroma_server.get_stats()
            
            # Add WebSocket stats
            stats.update({
                "websocket_clients": len(self.clients),
                "websocket_subscriptions": len(self.subscriptions),
                "server_uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
            })
            
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.STATS_UPDATE.value,
                id=message.id,
                data=stats
            ))
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await self.send_error(websocket, f"Failed to get stats: {str(e)}")
    
    async def handle_ping(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle a ping request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.PONG.value,
            id=message.id,
            data={"timestamp": time.time()}
        ))
    
    async def handle_gpuinfo(self, client_id: str, websocket: Any, message: WebSocketMessage) -> None:
        """
        Handle a GPU info request.
        
        Args:
            client_id (str): The client ID.
            websocket: The WebSocket connection.
            message (WebSocketMessage): The parsed message object.
        """
        try:
            import torch
            
            gpu_info = {
                "enabled": self.chroma_server.gpu_config.enabled if self.chroma_server.gpu_config else False,
                "device": getattr(self.chroma_server, 'device', 'cpu'),
                "torch_info": {
                    "version": torch.__version__,
                    "cuda_available": torch.cuda.is_available(),
                    "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
                    "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
                }
            }
            
            if self.chroma_server.gpu_config:
                gpu_info.update({
                    "batch_size": self.chroma_server.gpu_config.batch_size,
                    "use_mixed_precision": self.chroma_server.gpu_config.use_mixed_precision,
                    "cache_size": self.chroma_server.gpu_config.cache_size
                })
            
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.GPU_INFO.value,
                id=message.id,
                data=gpu_info
            ))
            
        except ImportError:
            await self.send_error(websocket, "PyTorch not available")
        except Exception as e:
            logger.error(f"GPU info error: {e}")
            await self.send_error(websocket, f"Failed to get GPU info: {str(e)}")
    
    async def send_message(self, websocket: Any, message: WebSocketMessage) -> None:
        """
        Send a message to a WebSocket client.
        
        Args:
            websocket: The WebSocket connection.
            message (WebSocketMessage): The message object to send.
        """
        try:
            await websocket.send(message.to_json())
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def send_error(self, websocket: Any, error_message: str) -> None:
        """
        Send an error message to a client.
        
        Args:
            websocket: The WebSocket connection.
            error_message (str): The error string to send.
        """
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.ERROR.value,
            data={"message": error_message}
        ))
    
    async def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all subscribed clients.
        
        Args:
            event_type (str): The type of event.
            data (Dict[str, Any]): The event data.
        """
        message = WebSocketMessage(
            type=event_type,
            data=data
        )
        
        for client_id, subscription in self.subscriptions.items():
            if event_type in subscription.event_types:
                websocket = self.clients.get(client_id)
                if websocket:
                    try:
                        await self.send_message(websocket, message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to {client_id}: {e}")
    
    async def periodic_stats(self) -> None:
        """Send periodic stats updates to subscribed clients."""
        while self.running:
            try:
                await asyncio.sleep(self.stats_interval)
                
                if MessageType.SERVER_STATS.value in self.get_subscribed_events():
                    stats = self.chroma_server.get_stats()
                    stats.update({
                        "websocket_clients": len(self.clients),
                        "timestamp": time.time()
                    })
                    
                    await self.broadcast_event(
                        MessageType.SERVER_STATS.value,
                        stats
                    )
                    
            except Exception as e:
                logger.error(f"Periodic stats error: {e}")
    
    def get_subscribed_events(self) -> Set[str]:
        """Get all event types that clients are subscribed to"""
        events = set()
        for subscription in self.subscriptions.values():
            events.update(subscription.event_types)
        return events
    
    async def start(self) -> None:
        """Start the WebSocket server."""
        try:
            import websockets
            
            self.start_time = time.time()
            self.running = True
            
            # Start periodic stats task
            self.stats_task = asyncio.create_task(self.periodic_stats())
            
            # Start WebSocket server
            server = await websockets.serve(
                self.handle_client,
                "localhost",
                self.port
            )
            
            logger.info(f"WebSocket server started on port {self.port}")
            
            # Keep server running
            await server.wait_closed()
            
        except ImportError:
            logger.error("websockets library not installed. Install with: pip install websockets")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
        finally:
            self.running = False
            if self.stats_task:
                self.stats_task.cancel()
    
    def start_in_thread(self) -> None:
        """Start the WebSocket server in a separate thread."""
        def run_server():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            self.event_loop.run_until_complete(self.start())
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"WebSocket server thread started")
    
    def stop(self) -> None:
        """Stop the WebSocket server."""
        self.running = False
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        logger.info("WebSocket server stopped")

def test_websocket_client():
    """Test WebSocket client (for development)"""
    import asyncio
    import websockets
    import json
    
    async def test():
        uri = "ws://localhost:8766"
        async with websockets.connect(uri) as websocket:
            # Receive connection info
            message = await websocket.recv()
            print(f"Connected: {message}")
            
            # Send ping
            ping_msg = {
                "type": "ping",
                "id": "test_123",
                "data": {}
            }
            await websocket.send(json.dumps(ping_msg))
            
            # Receive pong
            response = await websocket.recv()
            print(f"Pong: {response}")
            
            # Send search
            search_msg = {
                "type": "search",
                "id": "search_123",
                "data": {
                    "query": "test",
                    "n_results": 3
                }
            }
            await websocket.send(json.dumps(search_msg))
            
            # Receive search results
            response = await websocket.recv()
            print(f"Search results: {response}")
    
    asyncio.run(test())

if __name__ == "__main__":
    # Test the WebSocket server
    logging.basicConfig(level=logging.INFO)
    
    # Create a mock chroma server for testing
    class MockChromaServer:
        def semantic_search(self, query, n_results):
            return [{"rank": 1, "content": "test", "score": 0.9}]
        
        def index_codebase(self, patterns):
            return 10
        
        def get_stats(self):
            return {"documents": 100, "status": "running"}
        
        @property
        def collection(self):
            class MockCollection:
                def count(self):
                    return 100
            return MockCollection()
        
        gpu_config = None
    
    server = WebSocketServer(MockChromaServer(), port=8766)
    print("Starting test WebSocket server...")
    server.start_in_thread()
    
    # Keep running
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped")