#!/bin/bash
# Install ChromaDB and dependencies for OpenCode vector search

echo "Installing ChromaDB and dependencies..."

# Install Python packages
pip3 install chromadb>=0.5.0
pip3 install sentence-transformers>=2.2.2
pip3 install openai>=1.0.0
pip3 install numpy>=1.24.0
pip3 install pandas>=2.0.0
pip3 install tqdm>=4.65.0
pip3 install python-dotenv>=1.0.0

# Install MCP server dependencies
pip3 install mcp>=0.1.0

echo "Installation complete!"
echo ""
echo "To use Chroma vector search in OpenCode:"
echo "1. First index your codebase:"
echo "   python chroma_mcp_server.py --index"
echo ""
echo "2. Then run OpenCode with the MCP server:"
echo "   opencode"
echo ""
echo "3. Use semantic search in prompts:"
echo "   'Find authentication code using chroma-code-search'"
echo "   'Search for database connection code with semantic search'"