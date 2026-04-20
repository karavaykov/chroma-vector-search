#!/usr/bin/env python3
"""
Test script for Chroma Vector Search microservices
"""

import json
import time
import httpx
from typing import Dict, Any

class MicroservicesTester:
    """Test microservices functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
    
    def test_health(self) -> bool:
        """Test health endpoint"""
        print("Testing health endpoint...")
        try:
            response = self.client.get(f"{self.base_url}/api/v1/health")
            if response.status_code == 200:
                data = response.json()
                print(f"  Status: {data.get('status')}")
                print(f"  Services: {json.dumps(data.get('services'), indent=4)}")
                return data.get("status") == "healthy"
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def test_collections(self) -> bool:
        """Test collections endpoint"""
        print("\nTesting collections endpoint...")
        try:
            response = self.client.get(f"{self.base_url}/api/v1/collections")
            if response.status_code == 200:
                data = response.json()
                collections = data.get("collections", [])
                print(f"  Found {len(collections)} collections")
                for col in collections:
                    print(f"    - {col['name']}: {col['count']} documents")
                return True
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def test_search(self) -> bool:
        """Test search endpoint"""
        print("\nTesting search endpoint...")
        try:
            payload = {
                "query": "test search functionality",
                "n_results": 2,
                "collection_name": "codebase_vectors"
            }
            response = self.client.post(
                f"{self.base_url}/api/v1/search",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"  Found {len(results)} results")
                print(f"  Processing time: {data.get('processing_time_ms', 0):.2f}ms")
                return True
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def test_stats(self) -> bool:
        """Test stats endpoint"""
        print("\nTesting stats endpoint...")
        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/stats?collection_name=codebase_vectors"
            )
            if response.status_code == 200:
                data = response.json()
                print(f"  Collection: {data.get('collection_name')}")
                print(f"  Documents: {data.get('total_documents', 0)}")
                print(f"  Files: {data.get('total_files', 0)}")
                return True
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def test_files(self) -> bool:
        """Test files endpoint"""
        print("\nTesting files endpoint...")
        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/files?collection_name=codebase_vectors"
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"  Found {len(data)} files")
                    if data:
                        print(f"  First file: {data[0]['file_path']}")
                    return True
                else:
                    print(f"  Unexpected response format: {type(data)}")
                    return False
            else:
                print(f"  Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def test_direct_services(self) -> bool:
        """Test direct service endpoints"""
        print("\nTesting direct service endpoints...")
        
        services = {
            "indexing": "http://localhost:8001/health",
            "search": "http://localhost:8002/health",
            "metadata": "http://localhost:8003/metadata/health"
        }
        
        all_healthy = True
        for service_name, url in services.items():
            try:
                response = self.client.get(url, timeout=5.0)
                if response.status_code == 200:
                    print(f"  ✅ {service_name}: healthy")
                else:
                    print(f"  ❌ {service_name}: {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"  ❌ {service_name}: {e}")
                all_healthy = False
        
        return all_healthy
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("=" * 60)
        print("Chroma Vector Search Microservices Test")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health),
            ("Direct Services", self.test_direct_services),
            ("Collections", self.test_collections),
            ("Search", self.test_search),
            ("Stats", self.test_stats),
            ("Files", self.test_files),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            try:
                success = test_func()
                results.append((test_name, success))
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  Result: {status}")
            except Exception as e:
                print(f"  Exception: {e}")
                results.append((test_name, False))
                print(f"  Result: ❌ FAIL")
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary:")
        print("=" * 60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Microservices are working correctly.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check service logs.")
        
        return passed == total
    
    def close(self):
        """Close HTTP client"""
        self.client.close()

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Chroma Vector Search microservices")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", 
                       help="API Gateway base URL")
    parser.add_argument("--wait", type=int, default=0,
                       help="Wait N seconds before starting tests")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for services to start...")
        time.sleep(args.wait)
    
    tester = MicroservicesTester(args.base_url)
    
    try:
        success = tester.run_all_tests()
        exit(0 if success else 1)
    finally:
        tester.close()

if __name__ == "__main__":
    main()