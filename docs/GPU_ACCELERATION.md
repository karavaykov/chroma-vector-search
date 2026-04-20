# GPU Acceleration Guide

This guide explains how to use GPU acceleration for faster embedding generation in Chroma Vector Search.

## Overview

GPU acceleration can significantly speed up the process of generating embeddings for code search. The implementation supports:

- **NVIDIA GPUs** with CUDA
- **Apple Silicon** (M1/M2/M3) with MPS
- **CPU fallback** when GPU is not available

## Installation

### Basic Installation (CPU only)

```bash
pip install -r requirements.txt
```

### Installation with GPU Support

#### For NVIDIA GPUs (CUDA):

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install project with GPU dependencies
pip install -e ".[gpu]"
```

#### For Apple Silicon (MPS):

```bash
# PyTorch for Apple Silicon
pip install torch torchvision torchaudio

# Install project with GPU dependencies
pip install -e ".[gpu]"
```

#### Using requirements file:

```bash
pip install -r requirements-gpu.txt
```

## Usage

### Command Line Interface

#### Enable GPU acceleration:

```bash
# Basic GPU acceleration (auto-detect device)
python chroma_simple_server.py --server --gpu

# Specify GPU device
python chroma_simple_server.py --server --gpu --gpu-device cuda

# Custom batch size and mixed precision
python chroma_simple_server.py --server --gpu --gpu-batch-size 64 --gpu-mixed-precision

# Index with GPU acceleration
python chroma_simple_server.py --index --gpu
```

#### Available GPU options:

- `--gpu`: Enable GPU acceleration
- `--gpu-device`: Device to use (`auto`, `cuda`, `cpu`, `mps`)
- `--gpu-batch-size`: Batch size for GPU processing (default: 32)
- `--gpu-mixed-precision`: Enable mixed precision (float16)
- `--gpu-cache-size`: Cache size for embeddings (default: 1000)

### Programmatic Usage

```python
from chroma_simple_server import ChromaSimpleServer, GPUConfig

# Create GPU configuration
gpu_config = GPUConfig(
    enabled=True,
    device="auto",  # auto-detect best device
    batch_size=32,
    use_mixed_precision=True,
    cache_size=1000
)

# Create server with GPU acceleration
server = ChromaSimpleServer(
    project_root=".",
    gpu_config=gpu_config
)

# Use server as normal
results = server.semantic_search("database connection", 5)
```

### TCP Server Commands

When running as a TCP server, you can check GPU information:

```bash
# Get GPU information
echo "GPUINFO" | nc localhost 8765

# Example response:
{
  "type": "gpu_info",
  "info": {
    "gpu_enabled": true,
    "device": "cuda",
    "gpu_config": {
      "batch_size": 32,
      "use_mixed_precision": true,
      "cache_size": 1000
    },
    "torch_info": {
      "version": "2.0.0",
      "cuda_available": true,
      "cuda_version": "11.8",
      "mps_available": false
    }
  }
}
```

## Performance Optimization

### Batch Size Tuning

The optimal batch size depends on your GPU memory:

- **Small GPUs (4-8GB VRAM)**: 16-32
- **Medium GPUs (8-12GB VRAM)**: 32-64
- **Large GPUs (12+ GB VRAM)**: 64-128

Test different batch sizes:

```bash
python chroma_simple_server.py --server --gpu --gpu-batch-size 16
python chroma_simple_server.py --server --gpu --gpu-batch-size 32
python chroma_simple_server.py --server --gpu --gpu-batch-size 64
```

### Mixed Precision

Mixed precision (float16) can provide 2-3x speedup on compatible GPUs:

```bash
python chroma_simple_server.py --server --gpu --gpu-mixed-precision
```

**Note**: Not all operations support float16, and MPS (Apple Silicon) has limited float16 support.

### Caching

Embeddings are cached to avoid recomputation:

```bash
# Increase cache size for large codebases
python chroma_simple_server.py --server --gpu --gpu-cache-size 5000
```

## Device Detection

The system automatically detects available devices:

1. **CUDA** (NVIDIA GPUs) - if `torch.cuda.is_available()` returns True
2. **MPS** (Apple Silicon) - if `torch.backends.mps.is_available()` returns True
3. **CPU** - fallback if no GPU is available

You can check device availability:

```python
import torch

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda if torch.cuda.is_available() else 'N/A'}")
print(f"MPS available: {hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()}")
```

## Expected Performance Gains

### For NVIDIA GPUs (CUDA):

| Scenario | CPU Time | GPU Time | Speedup |
|----------|----------|----------|---------|
| Single query | ~50ms | ~20ms | 2.5x |
| Batch (32 texts) | ~1600ms | ~100ms | 16x |
| Indexing (1000 files) | ~300s | ~30s | 10x |

### For Apple Silicon (MPS):

| Scenario | CPU Time | GPU Time | Speedup |
|----------|----------|----------|---------|
| Single query | ~50ms | ~30ms | 1.7x |
| Batch (32 texts) | ~1600ms | ~200ms | 8x |
| Indexing (1000 files) | ~300s | ~60s | 5x |

## Troubleshooting

### Common Issues

#### 1. "CUDA not available" error

**Solution**: Install PyTorch with CUDA support:

```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 2. Out of memory errors

**Solution**: Reduce batch size:

```bash
python chroma_simple_server.py --server --gpu --gpu-batch-size 16
```

#### 3. MPS not available on Apple Silicon

**Solution**: Ensure you have the latest PyTorch:

```bash
pip install --upgrade torch torchvision torchaudio
```

#### 4. Mixed precision errors

**Solution**: Disable mixed precision:

```bash
python chroma_simple_server.py --server --gpu
# (without --gpu-mixed-precision flag)
```

### Debugging

Enable debug logging to see GPU operations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check GPU memory usage:

```python
import torch
if torch.cuda.is_available():
    print(f"GPU Memory allocated: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
    print(f"GPU Memory cached: {torch.cuda.memory_reserved() / 1024**2:.2f} MB")
```

## Advanced Configuration

### Custom Model

To use a different embedding model with GPU:

```python
from sentence_transformers import SentenceTransformer
import torch

# Load model
model = SentenceTransformer('all-mpnet-base-v2')

# Move to GPU
if torch.cuda.is_available():
    model = model.to('cuda')
    model.half()  # Enable mixed precision
```

### Multiple GPUs

For multi-GPU systems:

```python
import torch
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Use DataParallel for multiple GPUs
if torch.cuda.device_count() > 1:
    model = torch.nn.DataParallel(model)
    model = model.to('cuda')
```

## Monitoring

### Performance Metrics

Monitor GPU usage during operation:

```bash
# NVIDIA GPUs
nvidia-smi

# Apple Silicon
sudo powermetrics --samplers smc
```

### Logging

GPU operations are logged at INFO level:

```
2024-01-01 12:00:00 - __main__ - INFO - CUDA GPU detected, using CUDA
2024-01-01 12:00:01 - __main__ - INFO - Model moved to cuda
2024-01-01 12:00:01 - __main__ - INFO - Mixed precision (float16) enabled
2024-01-01 12:00:01 - __main__ - INFO - Model warmed up successfully
2024-01-01 12:00:02 - __main__ - DEBUG - Processing GPU batch 1/3 (size: 32)
```

## Best Practices

1. **Warm up the model** - First inference is slower due to compilation
2. **Use appropriate batch size** - Balance memory usage and throughput
3. **Enable caching** - Avoid recomputing embeddings for duplicate texts
4. **Monitor memory usage** - Adjust batch size based on available VRAM
5. **Test on your hardware** - Performance varies by GPU model

## Limitations

1. **VRAM requirements** - Model requires ~1-2GB VRAM
2. **CUDA version compatibility** - Must match PyTorch and driver versions
3. **MPS limitations** - Some operations not optimized for Apple Silicon
4. **Float16 precision** - May affect embedding quality slightly

## Future Improvements

Planned enhancements for GPU acceleration:

1. **TensorRT optimization** - Further speedup for NVIDIA GPUs
2. **ONNX Runtime** - Cross-platform acceleration
3. **Quantization** - Reduce memory usage with int8
4. **Dynamic batching** - Automatic batch size adjustment
5. **GPU memory pooling** - Better memory management

## Support

For issues with GPU acceleration:

1. Check the [PyTorch installation guide](https://pytorch.org/get-started/locally/)
2. Verify CUDA/MPS availability
3. Check system requirements
4. Open an issue on GitHub with:
   - GPU model and driver version
   - PyTorch version
   - Error message and logs