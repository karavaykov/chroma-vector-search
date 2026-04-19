#!/usr/bin/env python3
"""
Setup script for Chroma Vector Search for OpenCode
"""

from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="chroma-vector-search",
    version="0.1.0",
    author="Chroma Vector Search Team",
    author_email="your-email@example.com",
    description="Semantic code search integration for OpenCode using ChromaDB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/chroma-vector-search",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "chroma-search-server=chroma_simple_server:main",
            "chroma-search-client=chroma_client:main",
        ],
    },
    include_package_data=True,
    keywords="opencode, chroma, vector-search, semantic-search, code-search",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/chroma-vector-search/issues",
        "Source": "https://github.com/yourusername/chroma-vector-search",
        "Documentation": "https://github.com/yourusername/chroma-vector-search#readme",
    },
)