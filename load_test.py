#!/usr/bin/env python3
"""
Load testing for Chroma Vector Search
Simulates high traffic and measures performance
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import argparse
import sys

@dataclass
class LoadTestResult:
    """Load test result"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    details: Dict[str, Any]

class LoadTester:
    """Load tester for Chroma Vector Search"""
    
    def __init__(self, base_url: str, concurrent_workers: int = 10):
        self.base_url = base_url.rstrip("/")
        self.concurrent_workers = concurrent_workers
        self.results: List[LoadTestResult] = []
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, 
                          method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make a single HTTP request"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                async with session.get(url, timeout=30) as response:
                    status = response.status
                    text = await response.text()
            elif method == "POST":
                async with session.post(url, json=data, timeout=30) as response:
                    status = response.status
                    text = await response.text()
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            latency_ms = (time.time() - start_time) * 1000
            
            if 200 <= status < 300:
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "status_code": status,
                    "response": text[:500]  # Truncate for logging
                }
            else:
                return {
                    "success": False,
                    "latency_ms": latency_ms,
                    "status_code": status,
                    "error": f"HTTP {status}: {text[:200]}"
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "latency_ms": (time.time() - start_time) * 1000,
                "status_code": 0,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": (time.time() - start_time) * 1000,
                "status_code": 0,
                "error": str(e)
            }
    
    async def run_concurrent_requests(self, endpoint: str, num_requests: int,
                                     method: str = "GET", data: Dict = None) -> LoadTestResult:
        """Run concurrent requests"""
        print(f"  Running {num_requests} concurrent requests to {endpoint}...")
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_workers)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for i in range(num_requests):
                task = self.make_request(session, endpoint, method, data)
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
        
        # Process results
        successful = [r for r in responses if r["success"]]
        failed = [r for r in responses if not r["success"]]
        latencies = [r["latency_ms"] for r in successful]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            p50_index = int(len(latencies_sorted) * 0.5)
            p95_index = int(len(latencies_sorted) * 0.95)
            p99_index = int(len(latencies_sorted) * 0.99)
            
            p50 = latencies_sorted[p50_index] if p50_index < len(latencies_sorted) else 0
            p95 = latencies_sorted[p95_index] if p95_index < len(latencies_sorted) else 0
            p99 = latencies_sorted[p99_index] if p99_index < len(latencies_sorted) else 0
        else:
            p50 = p95 = p99 = 0
        
        result = LoadTestResult(
            test_name=f"Concurrent {endpoint}",
            total_requests=num_requests,
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_seconds=total_duration,
            requests_per_second=num_requests / total_duration if total_duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=len(failed) / num_requests if num_requests > 0 else 0,
            details={
                "endpoint": endpoint,
                "method": method,
                "sample_errors": [f["error"] for f in failed[:3]] if failed else [],
                "sample_responses": [s["response"] for s in successful[:2]] if successful else []
            }
        )
        
        self.results.append(result)
        return result
    
    async def run_sustained_load(self, endpoint: str, duration_seconds: int,
                                requests_per_second: int, method: str = "GET", 
                                data: Dict = None) -> LoadTestResult:
        """Run sustained load for a duration"""
        print(f"  Running sustained load ({requests_per_second} req/sec for {duration_seconds}s) to {endpoint}...")
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_workers)
        timeout = aiohttp.ClientTimeout(total=300)
        
        responses = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            request_count = 0
            
            while time.time() < end_time:
                batch_start = time.time()
                batch_tasks = []
                
                # Create batch of requests for this second
                for _ in range(requests_per_second):
                    if time.time() >= end_time:
                        break
                    
                    task = self.make_request(session, endpoint, method, data)
                    batch_tasks.append(task)
                    request_count += 1
                
                # Execute batch
                batch_responses = await asyncio.gather(*batch_tasks)
                responses.extend(batch_responses)
                
                # Sleep to maintain rate
                batch_duration = time.time() - batch_start
                if batch_duration < 1.0:
                    await asyncio.sleep(1.0 - batch_duration)
        
        total_duration = time.time() - start_time
        
        # Process results
        successful = [r for r in responses if r["success"]]
        failed = [r for r in responses if not r["success"]]
        latencies = [r["latency_ms"] for r in successful]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            p50_index = int(len(latencies_sorted) * 0.5)
            p95_index = int(len(latencies_sorted) * 0.95)
            p99_index = int(len(latencies_sorted) * 0.99)
            
            p50 = latencies_sorted[p50_index] if p50_index < len(latencies_sorted) else 0
            p95 = latencies_sorted[p95_index] if p95_index < len(latencies_sorted) else 0
            p99 = latencies_sorted[p99_index] if p99_index < len(latencies_sorted) else 0
        else:
            p50 = p95 = p99 = 0
        
        result = LoadTestResult(
            test_name=f"Sustained {endpoint}",
            total_requests=len(responses),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_seconds=total_duration,
            requests_per_second=len(responses) / total_duration if total_duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=len(failed) / len(responses) if responses else 0,
            details={
                "endpoint": endpoint,
                "method": method,
                "target_rps": requests_per_second,
                "actual_rps": len(responses) / total_duration if total_duration > 0 else 0,
                "sample_errors": [f["error"] for f in failed[:3]] if failed else []
            }
        )
        
        self.results.append(result)
        return result
    
    async def run_search_load_test(self, queries: List[str], num_requests: int) -> LoadTestResult:
        """Run load test with search queries"""
        print(f"  Running search load test with {len(queries)} queries, {num_requests} total requests...")
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_workers)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for i in range(num_requests):
                query = queries[i % len(queries)]
                data = {
                    "query": query,
                    "n_results": 3,
                    "collection_name": "codebase_vectors"
                }
                task = self.make_request(session, "/api/v1/search", "POST", data)
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
        
        # Process results
        successful = [r for r in responses if r["success"]]
        failed = [r for r in responses if not r["success"]]
        latencies = [r["latency_ms"] for r in successful]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            p50_index = int(len(latencies_sorted) * 0.5)
            p95_index = int(len(latencies_sorted) * 0.95)
            p99_index = int(len(latencies_sorted) * 0.99)
            
            p50 = latencies_sorted[p50_index] if p50_index < len(latencies_sorted) else 0
            p95 = latencies_sorted[p95_index] if p95_index < len(latencies_sorted) else 0
            p99 = latencies_sorted[p99_index] if p99_index < len(latencies_sorted) else 0
        else:
            p50 = p95 = p99 = 0
        
        result = LoadTestResult(
            test_name="Search Load Test",
            total_requests=num_requests,
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_seconds=total_duration,
            requests_per_second=num_requests / total_duration if total_duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=len(failed) / num_requests if num_requests > 0 else 0,
            details={
                "endpoint": "/api/v1/search",
                "method": "POST",
                "unique_queries": len(queries),
                "sample_errors": [f["error"] for f in failed[:3]] if failed else [],
                "queries_used": queries
            }
        )
        
        self.results.append(result)
        return result
    
    def print_result(self, result: LoadTestResult):
        """Print test result"""
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")
        print(f"{'='*60}")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful: {result.successful_requests}")
        print(f"Failed: {result.failed_requests}")
        print(f"Error Rate: {result.error_rate*100:.2f}%")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        print(f"Requests/sec: {result.requests_per_second:.2f}")
        print(f"\nLatency Statistics:")
        print(f"  Average: {result.avg_latency_ms:.2f}ms")
        print(f"  Minimum: {result.min_latency_ms:.2f}ms")
        print(f"  Maximum: {result.max_latency_ms:.2f}ms")
        print(f"  P50: {result.p50_latency_ms:.2f}ms")
        print(f"  P95: {result.p95_latency_ms:.2f}ms")
        print(f"  P99: {result.p99_latency_ms:.2f}ms")
        
        if result.details.get("sample_errors"):
            print(f"\nSample Errors:")
            for error in result.details["sample_errors"][:3]:
                print(f"  - {error}")
    
    def generate_report(self):
        """Generate load test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "concurrent_workers": self.concurrent_workers,
            "results": []
        }
        
        for result in self.results:
            report["results"].append({
                "test_name": result.test_name,
                "total_requests": result.total_requests,
                "successful_requests": result.successful_requests,
                "failed_requests": result.failed_requests,
                "total_duration_seconds": result.total_duration_seconds,
                "requests_per_second": result.requests_per_second,
                "avg_latency_ms": result.avg_latency_ms,
                "min_latency_ms": result.min_latency_ms,
                "max_latency_ms": result.max_latency_ms,
                "p50_latency_ms": result.p50_latency_ms,
                "p95_latency_ms": result.p95_latency_ms,
                "p99_latency_ms": result.p99_latency_ms,
                "error_rate": result.error_rate,
                "details": result.details
            })
        
        # Calculate overall statistics
        if self.results:
            report["overall"] = {
                "total_tests": len(self.results),
                "total_requests": sum(r.total_requests for r in self.results),
                "total_successful": sum(r.successful_requests for r in self.results),
                "total_failed": sum(r.failed_requests for r in self.results),
                "overall_error_rate": sum(r.failed_requests for r in self.results) / 
                                     sum(r.total_requests for r in self.results) 
                                     if sum(r.total_requests for r in self.results) > 0 else 0,
                "avg_requests_per_second": statistics.mean(r.requests_per_second for r in self.results),
                "avg_latency_ms": statistics.mean(r.avg_latency_ms for r in self.results),
                "max_latency_ms": max(r.max_latency_ms for r in self.results)
            }
        
        # Save report
        report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📊 Load test report saved to: {report_file}")
        
        # Print summary
        if self.results and "overall" in report:
            print(f"\n📈 Overall Summary:")
            print(f"  Total Tests: {report['overall']['total_tests']}")
            print(f"  Total Requests: {report['overall']['total_requests']}")
            print(f"  Success Rate: {(1 - report['overall']['overall_error_rate'])*100:.2f}%")
            print(f"  Avg Requests/sec: {report['overall']['avg_requests_per_second']:.2f}")
            print(f"  Avg Latency: {report['overall']['avg_latency_ms']:.2f}ms")
            print(f"  Max Latency: {report['overall']['max_latency_ms']:.2f}ms")
    
    async def run_all_tests(self):
        """Run all load tests"""
        print("=" * 60)
        print("Chroma Vector Search - Load Testing")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Concurrent Workers: {self.concurrent_workers}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Test queries
        search_queries = [
            "database connection",
            "error handling",
            "authentication",
            "logging configuration",
            "api endpoint",
            "data validation",
            "file upload",
            "email sending",
            "caching strategy",
            "performance optimization"
        ]
        
        # Run tests
        tests = [
            ("Health Check - 100 concurrent", 
             lambda: self.run_concurrent_requests("/api/v1/health", 100)),
            
            ("Search - 50 concurrent", 
             lambda: self.run_concurrent_requests("/api/v1/search", 50, "POST", 
                                                 {"query": "test", "n_results": 3})),
            
            ("Search Load - 200 requests", 
             lambda: self.run_search_load_test(search_queries, 200)),
            
            ("Sustained Load - 10 RPS for 30s", 
             lambda: self.run_sustained_load("/api/v1/health", 30, 10)),
            
            ("Sustained Search - 5 RPS for 60s", 
             lambda: self.run_sustained_load("/api/v1/search", 60, 5, "POST",
                                            {"query": "performance", "n_results": 2})),
        ]
        
        for test_name, test_func in tests:
            print(f"\n▶️  Running: {test_name}")
            result = await test_func()
            self.print_result(result)
        
        # Generate report
        self.generate_report()
        
        # Check if tests passed (error rate < 5%)
        overall_error_rate = sum(r.failed_requests for r in self.results) / \
                            sum(r.total_requests for r in self.results) \
                            if sum(r.total_requests for r in self.results) > 0 else 0
        
        print("\n" + "=" * 60)
        print("LOAD TEST COMPLETE")
        print("=" * 60)
        print(f"Overall Error Rate: {overall_error_rate*100:.2f}%")
        print(f"Status: {'✅ PASS' if overall_error_rate < 0.05 else '❌ FAIL'}")
        print("=" * 60)
        
        return overall_error_rate < 0.05

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Load testing for Chroma Vector Search")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000",
                       help="API Gateway base URL")
    parser.add_argument("--workers", type=int, default=10,
                       help="Number of concurrent workers")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick load test (fewer requests)")
    
    args = parser.parse_args()
    
    tester = LoadTester(args.base_url, args.workers)
    
    if args.quick:
        # Modify for quick test
        tester.concurrent_workers = 5
        # Run simplified tests
        print("Running quick load test...")
        # Just run health check and one search test
        await tester.run_concurrent_requests("/api/v1/health", 20)
        await tester.run_concurrent_requests("/api/v1/search", 10, "POST",
                                           {"query": "test", "n_results": 2})
        tester.generate_report()
    else:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())