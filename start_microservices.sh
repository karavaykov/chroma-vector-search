#!/bin/bash

# Start Chroma Vector Search Microservices
# Usage: ./start_microservices.sh [command]
# Commands: up, down, build, logs, status

set -e

COMMAND=${1:-up}

case $COMMAND in
    up)
        echo "Starting Chroma Vector Search microservices..."
        docker-compose up -d
        echo ""
        echo "Services:"
        echo "  API Gateway:      http://localhost:8000"
        echo "  Indexing Service: http://localhost:8001"
        echo "  Search Service:   http://localhost:8002"
        echo "  Metadata Service: http://localhost:8003"
        echo "  ChromaDB:         http://localhost:8004"
        echo "  Redis:            localhost:6379"
        echo "  PostgreSQL:       localhost:5432"
        echo ""
        echo "Check health: curl http://localhost:8000/api/v1/health"
        echo "Documentation: http://localhost:8000/api/docs"
        ;;
    
    down)
        echo "Stopping Chroma Vector Search microservices..."
        docker-compose down
        ;;
    
    build)
        echo "Building Docker images..."
        docker-compose build
        ;;
    
    logs)
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f $SERVICE
        fi
        ;;
    
    status)
        echo "Service status:"
        docker-compose ps
        echo ""
        echo "Health checks:"
        curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
        ;;
    
    restart)
        echo "Restarting services..."
        docker-compose restart
        ;;
    
    clean)
        echo "Cleaning up..."
        docker-compose down -v
        docker system prune -f
        ;;
    
    test)
        echo "Testing API endpoints..."
        
        # Test health endpoint
        echo "1. Testing health endpoint..."
        curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
        
        # Test collections endpoint
        echo -e "\n2. Testing collections endpoint..."
        curl -s http://localhost:8000/api/v1/collections | python3 -m json.tool
        
        # Test search endpoint
        echo -e "\n3. Testing search endpoint..."
        curl -s -X POST http://localhost:8000/api/v1/search \
            -H "Content-Type: application/json" \
            -d '{"query": "test search", "n_results": 2}' | python3 -m json.tool
        ;;
    
    *)
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  up        Start services"
        echo "  down      Stop services"
        echo "  build     Build Docker images"
        echo "  logs      View logs [service]"
        echo "  status    Check service status"
        echo "  restart   Restart services"
        echo "  clean     Stop and remove volumes"
        echo "  test      Test API endpoints"
        ;;
esac