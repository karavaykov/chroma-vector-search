# Contributing to Chroma Vector Search

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## 🎯 Development Philosophy

- **Keep it simple**: Python 3.9 compatibility is key
- **Semantic search first**: Focus on meaning-based code discovery
- **OpenCode integration**: Seamless experience for OpenCode users
- **Documentation**: Clear examples and guides

## 📋 Contribution Guidelines

### 1. Reporting Issues

When reporting issues, please include:

- **Description**: Clear explanation of the issue
- **Steps to reproduce**: Specific steps to trigger the issue
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: Python version, OS, dependencies
- **Logs**: Relevant error messages or logs

### 2. Feature Requests

For feature requests:

- **Use case**: Describe the problem you're solving
- **Proposed solution**: How the feature should work
- **Alternatives considered**: Other approaches you considered
- **Impact**: Who benefits and how

### 3. Pull Requests

#### Before submitting:
- [ ] Tests pass: `pytest tests/`
- [ ] Code formatted: `black .`
- [ ] Linting passes: `flake8 .`
- [ ] Type checking: `mypy .`
- [ ] Documentation updated
- [ ] No breaking changes

#### PR Template:
```markdown
## Description
Brief description of changes

## Related Issues
Fixes #(issue)

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added tests
- [ ] Updated tests
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings
```

## 🛠️ Development Setup

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/chroma-vector-search.git
cd chroma-vector-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install in development mode
pip install -e .
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_server.py -v

# Run with coverage
pytest --cov=. tests/

# Type checking
mypy .
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Sort imports
isort .
```

## 🏗️ Project Structure

```
chroma-vector-search/
├── chroma_simple_server.py   # Main server implementation
├── chroma_client.py          # Client for testing/CLI
├── opencode_chroma_simple.jsonc  # OpenCode configuration
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── tests/                    # Test suite
│   ├── test_server.py
│   ├── test_client.py
│   └── test_integration.py
├── examples/                 # Usage examples
│   ├── example_usage.py
│   └── sample_queries.txt
├── docs/                     # Documentation
│   ├── api.md
│   ├── deployment.md
│   └── troubleshooting.md
└── scripts/                  # Utility scripts
    ├── benchmark.py
    └── profile.py
```

## 🔧 Adding Language Support

To add support for a new programming language:

1. **Update language map** in `chroma_simple_server.py`:
```python
language_map['.vue'] = 'vue'
language_map['.dart'] = 'dart'
```

2. **Add test files** in `tests/test_languages/`

3. **Update documentation** in `README.md`

4. **Add example queries** in `examples/sample_queries.txt`

## 🧪 Writing Tests

### Test Structure

```python
def test_semantic_search():
    """Test semantic search functionality"""
    # Arrange
    server = ChromaSimpleServer()
    server.index_codebase(["**/*.java"])
    
    # Act
    results = server.semantic_search("database connection", 3)
    
    # Assert
    assert len(results) == 3
    assert all('similarity_score' in r for r in results)
    assert all(r['similarity_score'] > 0 for r in results)
```

### Test Categories

- **Unit tests**: Individual functions and classes
- **Integration tests**: Server-client communication
- **Performance tests**: Indexing and search speed
- **Regression tests**: Bug fixes

## 📚 Documentation

### Updating Documentation

1. **README.md**: Main project documentation
2. **API docs**: Code comments and docstrings
3. **Examples**: Practical usage examples
4. **Troubleshooting**: Common issues and solutions

### Documentation Standards

- Use Markdown format
- Include code examples
- Link to related resources
- Keep language simple and clear
- Update when code changes

## 🚀 Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Checklist

- [ ] Update version in `setup.py`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create GitHub release
- [ ] Tag release commit
- [ ] Announce release

## 🤝 Community

### Communication

- **Issues**: Bug reports and feature requests
- **Discussions**: Questions and ideas
- **Pull Requests**: Code contributions

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## 🎖️ Recognition

Contributors will be recognized in:

- **README.md** contributors section
- **Release notes**
- **Project documentation**

## ❓ Getting Help

- Check existing documentation
- Search existing issues
- Ask in discussions
- Contact maintainers

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Chroma Vector Search! 🚀