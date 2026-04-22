#!/usr/bin/env python3
"""
Tests for GPU acceleration functionality in Chroma Vector Search
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chroma_simple_server import ChromaSimpleServer, GPUConfig


class TestGPUConfig(unittest.TestCase):
    """Test GPU configuration class"""
    
    def test_default_config(self):
        """Test default GPU configuration"""
        config = GPUConfig()
        self.assertFalse(config.enabled)
        self.assertEqual(config.device, "auto")
        self.assertEqual(config.batch_size, 32)
        self.assertTrue(config.use_mixed_precision)
        self.assertEqual(config.cache_size, 1000)
    
    def test_custom_config(self):
        """Test custom GPU configuration"""
        config = GPUConfig(
            enabled=True,
            device="cuda",
            batch_size=64,
            use_mixed_precision=False,
            cache_size=500
        )
        self.assertTrue(config.enabled)
        self.assertEqual(config.device, "cuda")
        self.assertEqual(config.batch_size, 64)
        self.assertFalse(config.use_mixed_precision)
        self.assertEqual(config.cache_size, 500)
    
    def test_invalid_device(self):
        """Test invalid device configuration"""
        with self.assertRaises(ValueError):
            GPUConfig(device="invalid_device")
    
    def test_invalid_batch_size(self):
        """Test invalid batch size"""
        with self.assertRaises(ValueError):
            GPUConfig(batch_size=0)
    
    def test_invalid_cache_size(self):
        """Test invalid cache size"""
        with self.assertRaises(ValueError):
            GPUConfig(cache_size=-1)


class TestGPUAcceleration(unittest.TestCase):
    """Test GPU acceleration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self._servers = []
        
        # Create a test Python file
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def hello_world():
    \"\"\"Prints hello world\"\"\"
    print("Hello, World!")

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
""")

    def _track_server(self, server):
        self._servers.append(server)
        return server

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        import gc
        for s in self._servers:
            s.close()
        self._servers.clear()
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_server_without_gpu(self):
        """Test server initialization without GPU"""
        server = self._track_server(ChromaSimpleServer(self.test_dir))
        self.assertIsNotNone(server.embedding_model)
        self.assertEqual(server.device, "cpu")
        self.assertFalse(server.gpu_config.enabled)
    
    def test_server_with_gpu_disabled(self):
        """Test server initialization with GPU disabled"""
        gpu_config = GPUConfig(enabled=False)
        server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
        self.assertIsNotNone(server.embedding_model)
        self.assertEqual(server.device, "cpu")
        self.assertFalse(server.gpu_config.enabled)
    
    def test_server_with_gpu_enabled(self):
        """Test server initialization with GPU enabled"""
        try:
            import torch
            gpu_config = GPUConfig(enabled=True, device="cpu")  # Force CPU for testing
            server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
            self.assertIsNotNone(server.embedding_model)
            self.assertTrue(server.gpu_config.enabled)
            
            # Test that device is set correctly
            self.assertEqual(server.device, "cpu")
            
        except ImportError:
            self.skipTest("PyTorch not installed")
    
    def test_encoding_without_gpu(self):
        """Test encoding without GPU acceleration"""
        server = self._track_server(ChromaSimpleServer(self.test_dir))
        
        # Test single text encoding
        text = "Test text for encoding"
        embedding = server._cached_encode(text)
        self.assertIsInstance(embedding, list)
        self.assertGreater(len(embedding), 0)
        
        # Test batch encoding
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = server.encode_with_cache(texts)
        self.assertEqual(len(embeddings), len(texts))
        for emb in embeddings:
            self.assertIsInstance(emb, list)
            self.assertGreater(len(emb), 0)
    
    def test_encoding_with_gpu(self):
        """Test encoding with GPU acceleration (forced to CPU for testing)"""
        try:
            import torch
            gpu_config = GPUConfig(enabled=True, device="cpu", batch_size=2)
            server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
            
            # Test single text encoding
            text = "Test text for GPU encoding"
            embedding = server._cached_encode(text)
            self.assertIsInstance(embedding, list)
            self.assertGreater(len(embedding), 0)
            
            # Test batch encoding with GPU
            texts = ["GPU Text 1", "GPU Text 2", "GPU Text 3", "GPU Text 4"]
            embeddings = server.encode_with_cache(texts)
            self.assertEqual(len(embeddings), len(texts))
            for emb in embeddings:
                self.assertIsInstance(emb, list)
                self.assertGreater(len(emb), 0)
            
            # Test batch GPU encoding directly
            gpu_embeddings = server.encode_batch_gpu(texts)
            self.assertEqual(len(gpu_embeddings), len(texts))
            
        except ImportError:
            self.skipTest("PyTorch not installed")
    
    def test_stats_with_gpu(self):
        """Test statistics include GPU information"""
        gpu_config = GPUConfig(enabled=True, device="cpu")
        server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
        
        stats = server.get_stats()
        self.assertIn("gpu_enabled", stats)
        self.assertTrue(stats["gpu_enabled"])
        self.assertIn("gpu_device", stats)
        self.assertEqual(stats["gpu_device"], "cpu")
        self.assertIn("gpu_batch_size", stats)
        self.assertIn("gpu_mixed_precision", stats)
        self.assertIn("gpu_cache_size", stats)
    
    def test_stats_without_gpu(self):
        """Test statistics without GPU"""
        server = self._track_server(ChromaSimpleServer(self.test_dir))
        
        stats = server.get_stats()
        self.assertIn("gpu_enabled", stats)
        self.assertFalse(stats["gpu_enabled"])
    
    def test_gpuinfo_command(self):
        """Test GPUINFO command"""
        gpu_config = GPUConfig(enabled=True, device="cpu")
        server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
        
        response = server.handle_command("GPUINFO")
        result = json.loads(response)
        
        self.assertEqual(result["type"], "gpu_info")
        self.assertIn("info", result)
        self.assertTrue(result["info"]["gpu_enabled"])
        self.assertEqual(result["info"]["device"], "cpu")
        self.assertIn("torch_info", result["info"])
    
    def test_indexing_with_gpu(self):
        """Test indexing with GPU acceleration"""
        try:
            import torch
            gpu_config = GPUConfig(enabled=True, device="cpu")
            server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
            
            # Index the test file
            count = server.index_codebase(["*.py"])
            self.assertGreater(count, 0)
            
            # Search to test embeddings
            results = server.semantic_search("hello world", 2)
            self.assertIsInstance(results, list)
            
        except ImportError:
            self.skipTest("PyTorch not installed")
    
    def test_mixed_precision_config(self):
        """Test mixed precision configuration"""
        try:
            import torch
            # Test with mixed precision enabled
            config1 = GPUConfig(enabled=True, device="cpu", use_mixed_precision=True)
            server1 = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=config1))
            
            # Test with mixed precision disabled
            config2 = GPUConfig(enabled=True, device="cpu", use_mixed_precision=False)
            server2 = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=config2))
            
            self.assertTrue(server1.gpu_config.use_mixed_precision)
            self.assertFalse(server2.gpu_config.use_mixed_precision)
            
        except ImportError:
            self.skipTest("PyTorch not installed")


class TestPerformanceComparison(unittest.TestCase):
    """Test performance comparison between CPU and GPU"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self._servers = []
        
        # Create multiple test files for performance testing
        for i in range(5):
            test_file = os.path.join(self.test_dir, f"test_{i}.py")
            with open(test_file, "w") as f:
                f.write(f'''
def function_{i}():
    """Test function {i}"""
    value = {i} * 10
    return value

class Class{i}:
    def __init__(self):
        self.id = {i}
    
    def process(self):
        return self.id * 100
''')

    def _track_server(self, server):
        self._servers.append(server)
        return server

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        import gc
        for s in self._servers:
            s.close()
        self._servers.clear()
        gc.collect()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_batch_encoding_performance(self):
        """Test batch encoding performance (qualitative test)"""
        try:
            import torch
            import time
            
            # Create texts for batch encoding
            texts = [f"Test text {i} for performance comparison" for i in range(50)]
            
            # Test with CPU
            cpu_config = GPUConfig(enabled=False)
            cpu_server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=cpu_config))
            
            cpu_start = time.time()
            cpu_embeddings = cpu_server.encode_with_cache(texts)
            cpu_time = time.time() - cpu_start
            cpu_server.close()
            self._servers.remove(cpu_server)
            
            # Test with GPU (forced to CPU for compatibility)
            gpu_config = GPUConfig(enabled=True, device="cpu", batch_size=16)
            gpu_server = self._track_server(ChromaSimpleServer(self.test_dir, gpu_config=gpu_config))
            
            gpu_start = time.time()
            gpu_embeddings = gpu_server.encode_with_cache(texts)
            gpu_time = time.time() - gpu_start
            
            # Verify embeddings are the same shape
            self.assertEqual(len(cpu_embeddings), len(gpu_embeddings))
            self.assertEqual(len(cpu_embeddings[0]), len(gpu_embeddings[0]))
            
            # Log performance comparison
            print(f"\nPerformance comparison for {len(texts)} texts:")
            print(f"  CPU time: {cpu_time:.3f} seconds")
            print(f"  GPU time: {gpu_time:.3f} seconds")
            print(f"  Speedup: {cpu_time/gpu_time:.2f}x")
            
        except ImportError:
            self.skipTest("PyTorch not installed")


if __name__ == "__main__":
    unittest.main()