#!/usr/bin/env python3
"""
Example usage of Chroma Vector Search for OpenCode
"""

import json
import subprocess
import sys
import time

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def example_1_basic_search():
    """Example 1: Basic semantic search"""
    print("=" * 60)
    print("Example 1: Basic Semantic Search")
    print("=" * 60)
    
    # Start server (in background)
    print("Starting Chroma server...")
    server_proc = subprocess.Popen(
        ["python", "chroma_simple_server.py", "--server", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Search examples
    queries = [
        "database connection",
        "user authentication",
        "Swing UI button",
        "JSON serialization",
        "error handling"
    ]
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        stdout, stderr, code = run_command(
            f"python chroma_client.py --search '{query}' --results 2 --port 8765"
        )
        
        if code == 0:
            print(f"Found results for '{query}'")
        else:
            print(f"Error: {stderr}")
    
    # Stop server
    server_proc.terminate()
    server_proc.wait()
    print("\nServer stopped.")

def example_2_indexing():
    """Example 2: Indexing different file types"""
    print("\n" + "=" * 60)
    print("Example 2: Indexing Codebase")
    print("=" * 60)
    
    # Index Java files only
    print("Indexing Java files...")
    stdout, stderr, code = run_command(
        "python chroma_simple_server.py --index --project-root ."
    )
    
    if code == 0:
        print("Indexing successful!")
    else:
        print(f"Error: {stderr}")
    
    # Get statistics
    print("\nGetting index statistics...")
    stdout, stderr, code = run_command(
        "python chroma_simple_server.py --stats"
    )
    
    if code == 0:
        print(stdout)

def example_3_opencode_integration():
    """Example 3: OpenCode integration examples"""
    print("\n" + "=" * 60)
    print("Example 3: OpenCode Integration Prompts")
    print("=" * 60)
    
    prompts = [
        # Scout agent examples
        "@scout How is database connection handled? Use chroma_semantic_search",
        "@scout Find all authentication-related code using semantic search",
        "@scout What Swing UI patterns are used? Search with chroma_semantic_search",
        
        # Smith agent examples  
        "@smith Before implementing new feature, search for similar patterns with chroma_semantic_search",
        
        # Architect agent examples
        "@architect Plan new feature based on existing patterns found via chroma_semantic_search",
    ]
    
    print("Example OpenCode prompts:\n")
    for i, prompt in enumerate(prompts, 1):
        print(f"{i}. {prompt}")
    
    print("\nCustom tool usage in OpenCode config:")
    print("""
{
  "custom_tools": {
    "chroma_semantic_search": {
      "description": "Search codebase using semantic similarity",
      "command": ["python", "chroma_client.py", "--search", "{query}", "--results", "{n_results}", "--port", "8765"]
    }
  }
}
""")

def example_4_advanced_queries():
    """Example 4: Advanced search queries"""
    print("\n" + "=" * 60)
    print("Example 4: Advanced Search Queries")
    print("=" * 60)
    
    advanced_queries = [
        # Architectural patterns
        "repository pattern implementation",
        "service layer architecture",
        "dependency injection setup",
        
        # Design patterns
        "singleton pattern usage",
        "factory method pattern",
        "observer pattern implementation",
        
        # Code quality
        "error handling best practices",
        "logging configuration",
        "configuration management",
        
        # Specific technologies
        "SQLite database operations",
        "JSON serialization with Gson",
        "Swing event handling",
    ]
    
    print("Advanced semantic search queries:\n")
    for i, query in enumerate(advanced_queries, 1):
        print(f"{i}. {query}")

def example_5_workflow():
    """Example 5: Complete development workflow"""
    print("\n" + "=" * 60)
    print("Example 5: Complete Development Workflow")
    print("=" * 60)
    
    workflow = """
1. RESEARCH PHASE
   ```
   @scout How are fiscal receipts implemented? Use chroma_semantic_search
   @scout Find database transaction patterns with semantic search
   ```

2. PLANNING PHASE
   ```
   @architect Plan receipt export feature based on found patterns
   @architect Design database schema changes using existing patterns
   ```

3. IMPLEMENTATION PHASE
   ```
   @smith Implement export feature using similar patterns found
   @smith Add new database tables following existing conventions
   ```

4. REVIEW PHASE
   ```
   @warden Review implementation against architectural patterns
   @warden Check for consistency with existing codebase
   ```
"""
    print(workflow)

def main():
    """Main example runner"""
    print("Chroma Vector Search for OpenCode - Examples")
    print("=" * 60)
    
    examples = [
        example_1_basic_search,
        example_2_indexing,
        example_3_opencode_integration,
        example_4_advanced_queries,
        example_5_workflow,
    ]
    
    for example in examples:
        try:
            example()
            input("\nPress Enter to continue to next example...")
        except KeyboardInterrupt:
            print("\n\nExamples interrupted.")
            break
        except Exception as e:
            print(f"\nError in example: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Index your codebase: python chroma_simple_server.py --index")
    print("3. Start server: python chroma_simple_server.py --server")
    print("4. Configure OpenCode: cp opencode_chroma_simple.jsonc opencode.json")
    print("5. Run OpenCode: opencode")
    print("\nHappy coding! 🚀")

if __name__ == "__main__":
    main()