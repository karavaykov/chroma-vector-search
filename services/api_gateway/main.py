#!/usr/bin/env python3
"""
API Gateway for Chroma Vector Search
Single entry point for all microservices
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection for rate limiting
redis_client = redis.Redis(host='redis', port=6379, db=3)

# Service URLs
SERVICE_URLS = {
    "indexing": "http://indexing-service:8001",
    "search": "http://search-service:8002",
    "metadata": "http://metadata-service:8003"
}

# Pydantic models for API
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    n_results: int = Field(default=5, description="Number of results")
    collection_name: str = Field(default="codebase_vectors", description="Collection name")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")

class IndexRequest(BaseModel):
    project_root: str = Field(default=".", description="Project root directory")
    file_patterns: list = Field(
        default=["**/*.java", "**/*.py", "**/*.js", "**/*.ts", "**/*.bsl", "**/*.os"],
        description="File patterns to index"
    )
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    collection_name: str = Field(default="codebase_vectors", description="Collection name")

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]
    timestamp: datetime

class APIGateway:
    """API Gateway for routing requests to microservices"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_rate_limit(self, client_ip: str, endpoint: str) -> bool:
        """Check if client has exceeded rate limit"""
        key = f"ratelimit:{client_ip}:{endpoint}"
        current = redis_client.incr(key)
        
        if current == 1:
            # Set expiration (60 requests per minute)
            redis_client.expire(key, 60)
        
        return current <= 60
    
    async def forward_to_service(self, service: str, endpoint: str, method: str = "GET", 
                               data: Optional[Dict] = None) -> Dict[str, Any]:
        """Forward request to a microservice"""
        url = f"{SERVICE_URLS[service]}/{endpoint}"
        
        try:
            if method == "GET":
                response = await self.client.get(url)
            elif method == "POST":
                response = await self.client.post(url, json=data)
            elif method == "DELETE":
                response = await self.client.delete(url)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Service error ({service}): {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Service connection error ({service}): {e}")
            raise HTTPException(status_code=503, detail=f"Service {service} unavailable")
    
    async def check_service_health(self, service: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        try:
            url = f"{SERVICE_URLS[service]}/health"
            response = await self.client.get(url, timeout=5.0)
            return {
                "service": service,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            logger.error(f"Health check failed for {service}: {e}")
            return {
                "service": service,
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()

# FastAPI app
app = FastAPI(
    title="Chroma Vector Search API Gateway",
    description="Single entry point for all microservices",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, restrict to specific hosts
)

async def get_gateway() -> Any:
    """Dependency for API Gateway"""
    gateway = APIGateway()
    try:
        yield gateway
    finally:
        await gateway.close()

async def rate_limit(request: Request, gateway: APIGateway = Depends(get_gateway)) -> None:
    """Dependency for rate limiting"""
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    
    if not await gateway.check_rate_limit(client_ip, endpoint):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )

@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    """Log all requests"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )
    
    return response

@app.post("/api/v1/search")
async def search(
    request: SearchRequest,
    gateway: APIGateway = Depends(get_gateway),
    _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    """Search endpoint"""
    return await gateway.forward_to_service(
        "search", "search", "POST", request.dict()
    )

@app.post("/api/v1/index")
async def index(
    request: IndexRequest,
    gateway: APIGateway = Depends(get_gateway),
    _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    """Index endpoint"""
    return await gateway.forward_to_service(
        "indexing", "index", "POST", request.dict()
    )

@app.get("/api/v1/index/status/{job_id}")
async def get_index_status(
    job_id: str,
    gateway: APIGateway = Depends(get_gateway)
) -> Dict[str, Any]:
    """Get indexing job status"""
    return await gateway.forward_to_service(
        "indexing", f"index/status/{job_id}", "GET"
    )

@app.get("/api/v1/stats")
async def get_stats(
    collection_name: str = "codebase_vectors",
    gateway: APIGateway = Depends(get_gateway)
) -> Dict[str, Any]:
    """Get collection statistics"""
    return await gateway.forward_to_service(
        "metadata", f"metadata/stats?collection_name={collection_name}", "GET"
    )

@app.get("/api/v1/files")
async def list_files(
    collection_name: str = "codebase_vectors",
    gateway: APIGateway = Depends(get_gateway)
) -> Dict[str, Any]:
    """List indexed files"""
    return await gateway.forward_to_service(
        "metadata", f"metadata/files?collection_name={collection_name}", "GET"
    )

@app.get("/api/v1/collections")
async def list_collections(gateway: APIGateway = Depends(get_gateway)) -> Dict[str, Any]:
    """List available collections"""
    return await gateway.forward_to_service("search", "collections", "GET")

@app.post("/api/v1/search/similar")
async def search_similar(
    chunk_id: str,
    n_results: int = 5,
    gateway: APIGateway = Depends(get_gateway),
    _: None = Depends(rate_limit)
) -> Dict[str, Any]:
    """Find similar chunks"""
    return await gateway.forward_to_service(
        "search", "search/similar", "POST", {"chunk_id": chunk_id, "n_results": n_results}
    )

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check(gateway: APIGateway = Depends(get_gateway)):
    """Health check endpoint"""
    services = {}
    
    # Check each service
    for service_name in SERVICE_URLS.keys():
        health = await gateway.check_service_health(service_name)
        services[service_name] = health["status"]
    
    # Determine overall status
    overall_status = "healthy" if all(status == "healthy" for status in services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        services=services,
        timestamp=datetime.now()
    )

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "service": "Chroma Vector Search API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "search": "POST /api/v1/search",
            "index": "POST /api/v1/index",
            "index_status": "GET /api/v1/index/status/{job_id}",
            "stats": "GET /api/v1/stats",
            "files": "GET /api/v1/files",
            "collections": "GET /api/v1/collections",
            "similar": "POST /api/v1/search/similar",
            "health": "GET /api/v1/health"
        },
        "documentation": {
            "swagger": "/api/docs",
            "redoc": "/api/redoc"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)