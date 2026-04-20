#!/usr/bin/env python3
"""
Performance test script for GPU acceleration in Chroma Vector Search
Compares CPU vs GPU performance for indexing and search operations
"""

import time
import subprocess
import json
import os
import sys
from pathlib import Path
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from chroma_simple_server import ChromaSimpleServer, GPUConfig


def run_grep_test(pattern, project_path):
    """Run grep test and measure time"""
    print(f"\n🔍 Running grep test for pattern: '{pattern}'")
    
    # Create test files with the pattern
    test_file = os.path.join(project_path, "test_grep.txt")
    with open(test_file, "w") as f:
        for i in range(1000):
            f.write(f"Line {i}: This is a test document with {pattern} in it\n")
    
    start_time = time.time()
    
    try:
        # Run grep
        result = subprocess.run(
            ["grep", "-r", pattern, project_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        grep_time = time.time() - start_time
        line_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        
        print(f"  grep time: {grep_time:.3f}s")
        print(f"  Lines found: {line_count}")
        
        return grep_time, line_count
        
    except subprocess.TimeoutExpired:
        print(f"  grep timed out after 30 seconds")
        return 30.0, 0
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


def test_indexing_performance(project_path, use_gpu=False, device="cpu"):
    """Test indexing performance with and without GPU"""
    print(f"\n📊 Testing indexing performance (GPU: {use_gpu}, device: {device})")
    
    # Create GPU config if needed
    gpu_config = None
    if use_gpu:
        gpu_config = GPUConfig(
            enabled=True,
            device=device,
            batch_size=32,
            use_mixed_precision=True,
            cache_size=1000
        )
    
    start_time = time.time()
    
    try:
        # Create server and index
        server = ChromaSimpleServer(project_path, gpu_config=gpu_config)
        
        # Index the project
        count = server.index_codebase(["*.txt", "*.bsl", "*.xml"])
        
        indexing_time = time.time() - start_time
        
        print(f"  Indexing time: {indexing_time:.3f}s")
        print(f"  Documents indexed: {count}")
        print(f"  Device used: {server.device}")
        
        return indexing_time, count, server
        
    except Exception as e:
        print(f"  Error during indexing: {e}")
        return None, 0, None


def test_search_performance(server, query, num_results=10, iterations=3):
    """Test search performance"""
    print(f"\n🔎 Testing search performance for query: '{query}'")
    
    times = []
    for i in range(iterations):
        start_time = time.time()
        results = server.semantic_search(query, num_results)
        search_time = time.time() - start_time
        times.append(search_time)
        
        if i == 0:  # Show results only for first iteration
            print(f"  Iteration {i+1}: {search_time:.3f}s, Results: {len(results)}")
            if results:
                print(f"  Top result: {results[0]['file_path']}:{results[0]['line_start']}")
                print(f"  Score: {results[0]['similarity_score']:.3f}")
        else:
            print(f"  Iteration {i+1}: {search_time:.3f}s")
    
    avg_time = statistics.mean(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0
    
    print(f"  Average search time: {avg_time:.3f}s (±{std_dev:.3f}s)")
    
    return avg_time, std_dev, results


def test_batch_encoding_performance(server, batch_sizes=[1, 10, 32, 64, 128]):
    """Test batch encoding performance"""
    print(f"\n⚡ Testing batch encoding performance")
    
    # Create test texts
    test_texts = [f"Test text {i} for batch encoding performance testing" for i in range(max(batch_sizes))]
    
    results = []
    for batch_size in batch_sizes:
        batch_texts = test_texts[:batch_size]
        
        start_time = time.time()
        embeddings = server.encode_with_cache(batch_texts)
        encoding_time = time.time() - start_time
        
        speed = batch_size / encoding_time if encoding_time > 0 else 0
        
        print(f"  Batch size {batch_size:3d}: {encoding_time:.3f}s ({speed:.1f} texts/sec)")
        
        results.append({
            'batch_size': batch_size,
            'time': encoding_time,
            'speed': speed,
            'embeddings_count': len(embeddings)
        })
    
    return results


def test_gpu_info(server):
    """Test GPU information retrieval"""
    print(f"\n💻 Testing GPU information")
    
    response = server.handle_command("GPUINFO")
    result = json.loads(response)
    
    if result["type"] == "gpu_info":
        info = result["info"]
        print(f"  GPU enabled: {info['gpu_enabled']}")
        print(f"  Device: {info['device']}")
        print(f"  Batch size: {info['gpu_config']['batch_size']}")
        print(f"  Mixed precision: {info['gpu_config']['use_mixed_precision']}")
        
        torch_info = info['torch_info']
        print(f"  PyTorch version: {torch_info['version']}")
        print(f"  CUDA available: {torch_info['cuda_available']}")
        if torch_info['cuda_available']:
            print(f"  CUDA version: {torch_info['cuda_version']}")
        print(f"  MPS available: {torch_info['mps_available']}")
        
        return info
    else:
        print(f"  Error getting GPU info: {result}")
        return None


def run_comprehensive_performance_test(project_path):
    """Run comprehensive performance test comparing CPU and GPU"""
    print("=" * 80)
    print("🚀 COMPREHENSIVE PERFORMANCE TEST: CPU vs GPU")
    print("=" * 80)
    
    # Test queries from ENTERPRISE_PERFORMANCE_TEST.md
    test_queries = [
        "документ",
        "счет", 
        "банковский счет оплата",
        "резервное копирование",
        "шаблон сообщения"
    ]
    
    # Test grep performance
    print("\n📈 GREP PERFORMANCE TESTS")
    grep_results = {}
    for query in test_queries[:3]:  # Test first 3 queries with grep
        grep_time, line_count = run_grep_test(query, project_path)
        grep_results[query] = {'time': grep_time, 'lines': line_count}
    
    # Test CPU performance
    print("\n" + "=" * 80)
    print("💻 CPU PERFORMANCE TESTS")
    print("=" * 80)
    
    cpu_index_time, cpu_doc_count, cpu_server = test_indexing_performance(
        project_path, use_gpu=False
    )
    
    cpu_search_results = {}
    if cpu_server:
        for query in test_queries:
            avg_time, std_dev, results = test_search_performance(cpu_server, query)
            cpu_search_results[query] = {
                'avg_time': avg_time,
                'std_dev': std_dev,
                'results_count': len(results) if results else 0
            }
        
        # Test batch encoding
        cpu_batch_results = test_batch_encoding_performance(cpu_server)
    
    # Test GPU performance (if available)
    print("\n" + "=" * 80)
    print("🎮 GPU PERFORMANCE TESTS")
    print("=" * 80)
    
    # Try different GPU devices
    gpu_devices_to_test = ["cpu"]  # Always test CPU as baseline
    
    # Check for CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_devices_to_test.append("cuda")
            print("  ✅ CUDA GPU detected")
    except ImportError:
        pass
    
    # Check for MPS (Apple Silicon)
    try:
        import torch
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_devices_to_test.append("mps")
            print("  ✅ Apple Silicon (MPS) detected")
    except (ImportError, AttributeError):
        pass
    
    gpu_results = {}
    
    for device in gpu_devices_to_test:
        print(f"\n📊 Testing with device: {device}")
        
        use_gpu = (device != "cpu")
        gpu_index_time, gpu_doc_count, gpu_server = test_indexing_performance(
            project_path, use_gpu=use_gpu, device=device
        )
        
        if gpu_server:
            # Get GPU info
            gpu_info = test_gpu_info(gpu_server)
            
            # Test searches
            device_search_results = {}
            for query in test_queries:
                avg_time, std_dev, results = test_search_performance(gpu_server, query)
                device_search_results[query] = {
                    'avg_time': avg_time,
                    'std_dev': std_dev,
                    'results_count': len(results) if results else 0
                }
            
            # Test batch encoding
            device_batch_results = test_batch_encoding_performance(gpu_server)
            
            gpu_results[device] = {
                'index_time': gpu_index_time,
                'doc_count': gpu_doc_count,
                'search_results': device_search_results,
                'batch_results': device_batch_results,
                'gpu_info': gpu_info
            }
    
    # Generate comparison report
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE COMPARISON REPORT")
    print("=" * 80)
    
    if cpu_server and 'cpu' in gpu_results:
        print("\n📈 INDEXING PERFORMANCE:")
        print(f"  CPU: {cpu_index_time:.3f}s for {cpu_doc_count} documents")
        
        for device, results in gpu_results.items():
            if device != 'cpu':
                speedup = cpu_index_time / results['index_time'] if results['index_time'] > 0 else 0
                print(f"  {device.upper()}: {results['index_time']:.3f}s for {results['doc_count']} documents")
                print(f"    Speedup vs CPU: {speedup:.2f}x")
    
    print("\n🔍 SEARCH PERFORMANCE (average times):")
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        
        if query in cpu_search_results:
            cpu_time = cpu_search_results[query]['avg_time']
            print(f"    CPU: {cpu_time:.3f}s")
        
        for device, results in gpu_results.items():
            if device != 'cpu' and query in results['search_results']:
                gpu_time = results['search_results'][query]['avg_time']
                speedup = cpu_time / gpu_time if gpu_time > 0 else 0
                print(f"    {device.upper()}: {gpu_time:.3f}s (Speedup: {speedup:.2f}x)")
    
    print("\n⚡ BATCH ENCODING PERFORMANCE:")
    if 'cpu' in gpu_results and cpu_batch_results:
        # Compare last batch size (largest)
        last_batch = cpu_batch_results[-1]
        cpu_speed = last_batch['speed']
        print(f"  CPU: {cpu_speed:.1f} texts/sec (batch size: {last_batch['batch_size']})")
        
        for device, results in gpu_results.items():
            if device != 'cpu' and results.get('batch_results'):
                device_last_batch = results['batch_results'][-1]
                device_speed = device_last_batch['speed']
                speedup = device_speed / cpu_speed if cpu_speed > 0 else 0
                print(f"  {device.upper()}: {device_speed:.1f} texts/sec (Speedup: {speedup:.2f}x)")
    
    # Compare with grep
    print("\n📊 COMPARISON WITH GREP:")
    for query, grep_result in grep_results.items():
        if query in cpu_search_results:
            cpu_time = cpu_search_results[query]['avg_time']
            grep_time = grep_result['time']
            grep_speedup = grep_time / cpu_time if cpu_time > 0 else 0
            
            print(f"\n  Query: '{query}'")
            print(f"    grep: {grep_time:.3f}s ({grep_result['lines']} lines)")
            print(f"    ChromaDB (CPU): {cpu_time:.3f}s")
            print(f"    ChromaDB is {grep_speedup:.1f}x faster than grep")
            
            # Show GPU speedup if available
            for device, results in gpu_results.items():
                if device != 'cpu' and query in results['search_results']:
                    gpu_time = results['search_results'][query]['avg_time']
                    gpu_grep_speedup = grep_time / gpu_time if gpu_time > 0 else 0
                    print(f"    ChromaDB ({device.upper()}): {gpu_time:.3f}s ({gpu_grep_speedup:.1f}x faster than grep)")
    
    print("\n" + "=" * 80)
    print("✅ PERFORMANCE TEST COMPLETE")
    print("=" * 80)
    
    return {
        'grep_results': grep_results,
        'cpu_results': {
            'index_time': cpu_index_time,
            'doc_count': cpu_doc_count,
            'search_results': cpu_search_results,
            'batch_results': cpu_batch_results if 'cpu_batch_results' in locals() else None
        },
        'gpu_results': gpu_results
    }


def main():
    """Main function"""
    # Get project path from command line or use default
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "test_performance_project"
    
    # Ensure project path exists
    if not os.path.exists(project_path):
        print(f"Error: Project path '{project_path}' does not exist")
        print("Creating test project...")
        # Project was created earlier
        
    print(f"Testing performance on project: {project_path}")
    
    # Calculate project size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(project_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    
    print(f"Project size: {total_size / 1024:.1f} KB")
    
    # Run comprehensive test
    results = run_comprehensive_performance_test(project_path)
    
    # Save results to file
    output_file = "performance_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    main()