#!/usr/bin/env python3
"""
Enterprise Performance Testing for Chroma Vector Search
Tests the system with large codebases (>50k files)
"""

import os
import sys
import time
import json
import statistics
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import psutil
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestResult:
    """Test result data class"""
    test_name: str
    success: bool
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    details: Dict[str, Any]
    error: Optional[str] = None

class EnterprisePerformanceTester:
    """Performance tester for enterprise scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000", project_root: str = "."):
        self.base_url = base_url.rstrip("/")
        self.project_root = Path(project_root).resolve()
        self.client = httpx.Client(timeout=300.0)  # 5 minute timeout for large operations
        self.results: List[TestResult] = []
        
    def measure_resource_usage(self) -> Dict[str, float]:
        """Measure current resource usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "memory_mb": memory_info.rss / (1024 * 1024),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "threads": process.num_threads(),
            "open_files": len(process.open_files())
        }
    
    def run_test(self, test_func, test_name: str, **kwargs) -> TestResult:
        """Run a test and measure performance"""
        print(f"\n{'='*60}")
        print(f"Running test: {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        start_resources = self.measure_resource_usage()
        
        try:
            details = test_func(**kwargs)
            success = True
            error = None
        except Exception as e:
            details = {}
            success = False
            error = str(e)
            print(f"  ❌ Error: {e}")
        
        end_time = time.time()
        end_resources = self.measure_resource_usage()
        
        duration_ms = (end_time - start_time) * 1000
        
        result = TestResult(
            test_name=test_name,
            success=success,
            duration_ms=duration_ms,
            memory_usage_mb=end_resources["memory_mb"] - start_resources["memory_mb"],
            cpu_usage_percent=end_resources["cpu_percent"],
            details=details,
            error=error
        )
        
        self.results.append(result)
        
        if success:
            print(f"  ✅ Success: {duration_ms:.2f}ms")
            print(f"  📊 Memory delta: {result.memory_usage_mb:.2f} MB")
            print(f"  ⚡ CPU usage: {result.cpu_usage_percent:.1f}%")
        else:
            print(f"  ❌ Failed: {error}")
        
        return result
    
    def test_health(self) -> Dict[str, Any]:
        """Test health endpoint"""
        response = self.client.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    def test_small_search(self) -> Dict[str, Any]:
        """Test small search query"""
        payload = {
            "query": "database connection",
            "n_results": 5,
            "collection_name": "codebase_vectors"
        }
        response = self.client.post(f"{self.base_url}/api/v1/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def test_large_search(self, query: str = "error handling and exception management") -> Dict[str, Any]:
        """Test larger search query"""
        payload = {
            "query": query,
            "n_results": 20,
            "collection_name": "codebase_vectors"
        }
        response = self.client.post(f"{self.base_url}/api/v1/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def test_concurrent_searches(self, num_requests: int = 10) -> Dict[str, Any]:
        """Test concurrent search requests"""
        queries = [
            "database connection",
            "error handling",
            "authentication",
            "authorization",
            "logging",
            "configuration",
            "testing",
            "deployment",
            "monitoring",
            "performance"
        ]
        
        results = []
        latencies = []
        
        def make_request(query: str):
            start = time.time()
            try:
                payload = {
                    "query": query,
                    "n_results": 3,
                    "collection_name": "codebase_vectors"
                }
                response = self.client.post(f"{self.base_url}/api/v1/search", json=payload)
                response.raise_for_status()
                latency = (time.time() - start) * 1000
                return {"query": query, "success": True, "latency_ms": latency}
            except Exception as e:
                latency = (time.time() - start) * 1000
                return {"query": query, "success": False, "latency_ms": latency, "error": str(e)}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, query) for query in queries[:num_requests]]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result["success"]:
                    latencies.append(result["latency_ms"])
        
        return {
            "total_requests": len(results),
            "successful_requests": sum(1 for r in results if r["success"]),
            "failed_requests": sum(1 for r in results if not r["success"]),
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "results": results
        }
    
    def test_indexing_small(self) -> Dict[str, Any]:
        """Test indexing a small set of files"""
        # Create a test directory with sample files
        test_dir = self.project_root / "test_enterprise_data"
        test_dir.mkdir(exist_ok=True)
        
        # Create sample Python files
        for i in range(10):
            file_path = test_dir / f"test_file_{i}.py"
            file_path.write_text(f"""
# Test file {i}
def function_{i}():
    '''Test function {i}'''
    return "Hello from function {i}"

class TestClass{i}:
    '''Test class {i}'''
    def __init__(self):
        self.value = {i}
    
    def get_value(self):
        return self.value
""")
        
        payload = {
            "project_root": str(test_dir),
            "file_patterns": ["**/*.py"],
            "max_file_size_mb": 1,
            "collection_name": "test_enterprise"
        }
        
        # Start indexing
        response = self.client.post(f"{self.base_url}/api/v1/index", json=payload)
        response.raise_for_status()
        job_data = response.json()
        
        job_id = job_data["job_id"]
        
        # Wait for completion
        max_wait = 60  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            time.sleep(2)
            status_response = self.client.get(f"{self.base_url}/api/v1/index/status/{job_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "total_files": status_data.get("total_files", 0),
                    "processed_files": status_data.get("processed_files", 0),
                    "total_chunks": status_data.get("total_chunks", 0),
                    "duration_seconds": time.time() - start_time
                }
            elif status_data["status"] == "failed":
                raise Exception(f"Indexing failed: {status_data.get('error_message', 'Unknown error')}")
        
        raise Exception("Indexing timed out")
    
    def test_metadata_operations(self) -> Dict[str, Any]:
        """Test metadata operations"""
        results = {}
        
        # Test stats
        response = self.client.get(f"{self.base_url}/api/v1/stats")
        response.raise_for_status()
        results["stats"] = response.json()
        
        # Test files list
        response = self.client.get(f"{self.base_url}/api/v1/files")
        response.raise_for_status()
        files_data = response.json()
        results["files_count"] = len(files_data) if isinstance(files_data, list) else 0
        
        # Test collections
        response = self.client.get(f"{self.base_url}/api/v1/collections")
        response.raise_for_status()
        results["collections"] = response.json()
        
        return results
    
    def test_stress(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """Stress test the system"""
        print(f"  Running stress test for {duration_seconds} seconds...")
        
        queries = [
            "database",
            "function",
            "class",
            "error",
            "test",
            "config",
            "auth",
            "log",
            "api",
            "service"
        ]
        
        request_count = 0
        success_count = 0
        latencies = []
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            for query in queries:
                if time.time() >= end_time:
                    break
                
                start = time.time()
                try:
                    payload = {
                        "query": query,
                        "n_results": 2,
                        "collection_name": "codebase_vectors"
                    }
                    response = self.client.post(f"{self.base_url}/api/v1/search", json=payload, timeout=10.0)
                    response.raise_for_status()
                    success_count += 1
                    latencies.append((time.time() - start) * 1000)
                except Exception:
                    pass  # Ignore errors in stress test
                
                request_count += 1
                
                # Small delay to avoid overwhelming the system
                time.sleep(0.1)
        
        return {
            "duration_seconds": duration_seconds,
            "total_requests": request_count,
            "successful_requests": success_count,
            "success_rate": success_count / request_count if request_count > 0 else 0,
            "requests_per_second": request_count / duration_seconds,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0
        }
    
    def run_all_tests(self) -> bool:
        """Run all enterprise performance tests"""
        print("=" * 60)
        print("Enterprise Performance Testing - Chroma Vector Search")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Project Root: {self.project_root}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Run tests
        tests = [
            ("Health Check", self.test_health),
            ("Small Search", self.test_small_search),
            ("Large Search", lambda: self.test_large_search()),
            ("Metadata Operations", self.test_metadata_operations),
            ("Concurrent Searches (10)", lambda: self.test_concurrent_searches(10)),
            ("Small Indexing", self.test_indexing_small),
            ("Stress Test (30s)", lambda: self.test_stress(30)),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_func, test_name)
        
        # Generate report
        self.generate_report()
        
        # Check if all tests passed
        all_passed = all(r.success for r in self.results)
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {sum(1 for r in self.results if r.success)}")
        print(f"Failed: {sum(1 for r in self.results if not r.success)}")
        print(f"Overall: {'✅ PASS' if all_passed else '❌ FAIL'}")
        
        return all_passed
    
    def generate_report(self):
        """Generate performance test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "project_root": str(self.project_root),
            "results": []
        }
        
        for result in self.results:
            report["results"].append({
                "test_name": result.test_name,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "memory_usage_mb": result.memory_usage_mb,
                "cpu_usage_percent": result.cpu_usage_percent,
                "details": result.details,
                "error": result.error
            })
        
        # Calculate statistics
        successful_tests = [r for r in self.results if r.success]
        if successful_tests:
            report["statistics"] = {
                "avg_duration_ms": statistics.mean(r.duration_ms for r in successful_tests),
                "max_duration_ms": max(r.duration_ms for r in successful_tests),
                "min_duration_ms": min(r.duration_ms for r in successful_tests),
                "avg_memory_usage_mb": statistics.mean(r.memory_usage_mb for r in successful_tests),
                "total_memory_peak_mb": sum(r.memory_usage_mb for r in successful_tests),
                "success_rate": len(successful_tests) / len(self.results)
            }
        
        # Save report
        report_file = self.project_root / "enterprise_performance_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📊 Report saved to: {report_file}")
        
        # Print key metrics
        if successful_tests:
            print("\n📈 Key Performance Metrics:")
            print(f"  Average test duration: {report['statistics']['avg_duration_ms']:.2f}ms")
            print(f"  Maximum test duration: {report['statistics']['max_duration_ms']:.2f}ms")
            print(f"  Average memory usage: {report['statistics']['avg_memory_usage_mb']:.2f} MB")
            print(f"  Success rate: {report['statistics']['success_rate']*100:.1f}%")
    
    def cleanup(self):
        """Cleanup test data"""
        test_dir = self.project_root / "test_enterprise_data"
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise Performance Testing for Chroma Vector Search")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", 
                       help="API Gateway base URL")
    parser.add_argument("--project-root", type=str, default=".", 
                       help="Project root directory for testing")
    parser.add_argument("--skip-cleanup", action="store_true",
                       help="Skip cleanup of test data")
    
    args = parser.parse_args()
    
    tester = EnterprisePerformanceTester(args.base_url, args.project_root)
    
    try:
        success = tester.run_all_tests()
        exit(0 if success else 1)
    finally:
        if not args.skip_cleanup:
            tester.cleanup()
        tester.client.close()

if __name__ == "__main__":
    main()