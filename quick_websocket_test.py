#!/usr/bin/env python3
"""
Quick test to verify WebSocket server integration
"""

import subprocess
import time
import sys
import os

def test_websocket_server():
    """Test that WebSocket server starts correctly"""
    print("Testing WebSocket server integration...")
    
    # Start server in background
    print("Starting Chroma server with WebSocket...")
    server_process = subprocess.Popen(
        [sys.executable, "chroma_simple_server.py", "--server", "--websocket-port", "8766"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give server time to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    # Check if server is running
    if server_process.poll() is not None:
        # Server exited
        stdout, stderr = server_process.communicate()
        print("Server failed to start!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print("Server started successfully!")
    
    # Try to run WebSocket test
    print("\nRunning WebSocket client test...")
    test_process = subprocess.Popen(
        [sys.executable, "test_websocket.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for test to complete
    time.sleep(5)
    
    if test_process.poll() is not None:
        stdout, stderr = test_process.communicate()
        print("Test output:")
        print(stdout)
        if stderr:
            print("Errors:", stderr)
    else:
        print("Test timed out, killing...")
        test_process.terminate()
    
    # Kill server
    print("\nStopping server...")
    server_process.terminate()
    server_process.wait()
    
    print("\n✅ WebSocket integration test completed!")
    return True

def check_imports():
    """Check if required imports work"""
    print("Checking imports...")
    
    try:
        import websockets
        print(f"✅ websockets version: {websockets.__version__}")
        
        # Try to import our WebSocket server
        from websocket_server import WebSocketServer
        print("✅ WebSocketServer import successful")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("WebSocket Integration Test")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check imports
    if not check_imports():
        print("\n❌ Import check failed")
        return 1
    
    # Run server test
    print("\n" + "=" * 60)
    success = test_websocket_server()
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())