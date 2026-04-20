#!/usr/bin/env python3
"""
Simple standalone WebSocket test
"""

import asyncio
import websockets
import json
import time

async def test_connection():
    """Test WebSocket connection"""
    uri = "ws://localhost:8766"
    
    print(f"Testing connection to {uri}...")
    
    try:
        # Try to connect with short timeout
        async with websockets.connect(uri, timeout=2) as websocket:
            print("✅ Connected successfully!")
            
            # Try to receive a message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1)
                data = json.loads(message)
                print(f"✅ Received message: {data.get('type')}")
                return True
            except asyncio.TimeoutError:
                print("⚠️  No message received (server might not be sending)")
                return True
                
    except ConnectionRefusedError:
        print("❌ Connection refused - server not running")
        return False
    except asyncio.TimeoutError:
        print("❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test"""
    print("=" * 60)
    print("Simple WebSocket Connection Test")
    print("=" * 60)
    
    print("\nMake sure the server is running with:")
    print("  python chroma_simple_server.py --server --websocket-port 8766")
    print("\nPress Enter when server is running...")
    input()
    
    # Run test
    success = asyncio.run(test_connection())
    
    if success:
        print("\n✅ WebSocket connection test passed!")
    else:
        print("\n❌ WebSocket connection test failed")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()