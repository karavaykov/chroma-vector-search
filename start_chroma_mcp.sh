#!/bin/bash
# Start Chroma Simple Server for OpenCode integration (Python 3.9 compatible)

echo "Starting Chroma Simple Server for OpenCode..."
echo "Project: $(pwd)"
echo "Python: $(python3 --version)"
echo ""

# Check if Python dependencies are installed
if ! python3 -c "import chromadb" 2>/dev/null; then
    echo "Installing ChromaDB dependencies..."
    pip3 install chromadb sentence-transformers
fi

# Check if codebase is indexed
if [ ! -d ".chroma_db" ] || [ ! -f ".chroma_db/chroma.sqlite3" ]; then
    echo "Codebase not indexed. Running initial index..."
    python3 chroma_simple_server.py --index
    echo ""
fi

# Show index stats
echo "Index Statistics:"
python3 chroma_simple_server.py --stats
echo ""

# Start server
echo "Starting Chroma server on port 8765 (press Ctrl+C to stop)..."
echo ""
echo "OpenCode Configuration:"
echo "1. Use config: cp opencode_chroma_simple.jsonc opencode.json"
echo "2. Or add custom tools to your existing opencode.json"
echo ""
echo "Test server with: python chroma_client.py --ping"
echo "Search example: python chroma_client.py --search 'database connection'"
echo ""

python3 chroma_simple_server.py --server --port 8765