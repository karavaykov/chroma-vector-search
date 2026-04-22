# Chroma Vector Search for OpenCode

[English](README.md) | [Русский](README.ru.md) | [中文](README.zh.md)

为 OpenCode 设计的语义代码搜索工具 - TCP 替代 MCP（兼容 Python 3.9+）

## 📋 概述

Chroma Vector Search 是一个语义代码搜索工具，通过简单的 TCP 协议与 OpenCode 集成。与需要 Python ≥3.10 的官方 MCP（模型上下文协议）不同，我们的服务器可以在 Python 3.9+ 上运行，使其与标准的 macOS 系统兼容。

## ✨ 特性

- **兼容 Python 3.9+** - 可在标准 macOS 系统上运行
- **端口 8765 的 TCP 服务器** - 简单的文本协议
- **语义代码搜索** - 使用 ChromaDB 和 Sentence Transformers
- **与 OpenCode 集成** - 通过自定义工具配置
- **完整文档** - API、部署、使用示例
- **测试和 CI/CD** - 通过 GitHub Actions 自动测试
- **GPU 加速** - 支持 CUDA 和 MPS 用于快速嵌入生成（2.6x-14.7x 加速）
- **高级搜索 (v1.1.0)** - 对已索引文本的正则搜索、命中周围的上下文行、流式结果（WebSocket 与 REST SSE）

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/karavaykov/chroma-vector-search.git
cd chroma-vector-search

# 安装依赖
pip install -r requirements.txt
```

### 启动服务器

```bash
# 启动 TCP 服务器
python chroma_simple_server.py

# 或使用脚本
./start_chroma_mcp.sh
```

### 与 OpenCode 集成

添加到 OpenCode 配置 (`~/.opencode/config.json`):

```json
{
  "tools": [
    {
      "type": "custom",
      "config": "./opencode_chroma_simple.jsonc"
    }
  ]
}
```

## 📖 使用方法

### 代码索引

```bash
# 索引代码目录
python chroma_client.py index /path/to/your/code
```

### 代码搜索

```bash
# 语义搜索
python chroma_client.py search "错误处理函数"
```

### OpenCode 提示词示例

```
查找所有与用户认证相关的函数
显示支付处理的实现
查找数据库操作相关的类
```

## 🌐 Web 界面 (v1.1.0 新功能)

Chroma Vector Search 现在包含一个内置的 Web UI，以便于交互。

### 启动 Web UI
Web UI 由 API Gateway 微服务自动提供：
```bash
# 启动微服务（包括 API Gateway）
./start_microservices.sh

# 打开浏览器并访问：
# http://localhost:8000/
```

### 功能特点
- **搜索：** 直接从浏览器执行语义搜索、关键字搜索或混合搜索。
- **混合控制：** 使用滑块调整语义与关键字的权重。
- **索引：** 触发代码库索引，并通过 WebSocket 实时查看进度。
- **语法高亮：** 代码结果显示正确的语法高亮。
- **元数据徽章：** 直接在结果中查看 1C/BSL 企业元数据（作者、模块类型、函数调用）。

### 高级搜索 (v1.1.0)
- **正则搜索：** 在关键字索引的内存文档上按模式匹配（请先完成代码库索引以填充关键字索引）。
- **命中上下文：** 对语义、关键字、混合与正则搜索使用 `context_lines` 或 `context_before` / `context_after`（单体 `chroma_simple_server.py` 与 WebSocket API）。
- **流式输出：** 在 Web UI 中启用流式；WebSocket 在 `search` 消息中设置 `stream: true`，处理 `search_result_chunk` 与结束的 `search_complete`。微服务场景下，API Gateway 的 `POST /api/v1/search/stream`（SSE）转发到 Search Service。

## 🌐 WebSocket API (v1.1.0 新功能)

支持 WebSocket 的实时双向通信：

### WebSocket 特性
- **实时搜索结果**：即时响应流
- **按条流式结果 (v1.1.0)：** 当 `data.stream` 为 true 时，服务器发送 `search_result_chunk` 并以 `search_complete` 结束（除了一次性 `search_results`）。
- **进度更新**：实时索引进度
- **事件订阅**：订阅服务器事件
- **双向通信**：服务器可以推送更新
- **低延迟**：与 HTTP/TCP 请求相比

### WebSocket 快速入门
```bash
# 启动带有 WebSocket 的服务器（默认端口 8766）
python chroma_simple_server.py --server --websocket-port 8766

# 测试 WebSocket 连接
python test_websocket.py
```

有关完整的 API 文档，请参阅 [docs/WEBSOCKET_API.md](docs/WEBSOCKET_API.md)。

## 🚀 GPU 加速（v1.1.0 新功能）

通过 NVIDIA CUDA 和 Apple Silicon MPS 的 GPU 支持加速嵌入生成：

### 安装 GPU 支持

```bash
# 适用于 NVIDIA GPU (CUDA) - 10-16x 加速
pip install -r requirements-gpu.txt

# 适用于 Apple Silicon (MPS) - 8-12x 加速
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

### 使用方法

```bash
# 启用 GPU 加速（自动检测最佳设备）
python chroma_simple_server.py --server --gpu

# 使用特定 GPU 设备
python chroma_simple_server.py --server --gpu --gpu-device cuda      # NVIDIA CUDA
python chroma_simple_server.py --server --gpu --gpu-device mps       # Apple Silicon
python chroma_simple_server.py --server --gpu --gpu-device cpu       # 强制使用 CPU

# 批量处理优化
python chroma_simple_server.py --server --gpu --gpu-batch-size 64 --gpu-mixed-precision
```

### 性能结果（在 Apple M1 上测试）

| 操作 | CPU 时间 | GPU 时间 (MPS) | 加速比 |
|------|----------|----------------|--------|
| 搜索查询 | 4-39毫秒 | 2-4毫秒 | 2.6x-14.7x |
| 批量处理 (64 文本) | 304毫秒 | 24毫秒 | 12.6x |
| 批量处理 (128 文本) | 601毫秒 | 49毫秒 | 12.3x |

**详细文档:** [GPU 加速指南](docs/GPU_ACCELERATION.md) | [性能测试](ENTERPRISE_PERFORMANCE_TEST_WITH_GPU.md)

## 🏗️ 架构

```
┌─────────────────┐    TCP (端口 8765)    ┌─────────────────┐
│    OpenCode     │ ◄───────────────────► │  Chroma 服务器  │
│   (客户端)      │                       │   (Python 3.9+) │
└─────────────────┘                       └─────────────────┘
         │                                         │
         ▼                                         ▼
┌─────────────────┐                       ┌─────────────────┐
│  自定义工具     │                       │    ChromaDB     │
│   配置          │                       │  + 嵌入模型     │
└─────────────────┘                       └─────────────────┘
```

## 📊 协议命令

服务器支持简单的文本协议：

```
SEARCH <查询>          # 语义搜索
INDEX <路径>           # 目录索引
STATS                  # 数据库统计
PING                   # 连接测试
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -q

# 1C/BSL 解析与分块
python test_1c_parser.py

# 测试单个模块
pytest tests/test_basic.py
pytest tests/test_client.py
```

在 Windows 上，测试会调用 `ChromaSimpleServer.close()`，以便在删除临时目录前释放 Chroma 的 SQLite 文件。若你在自己的脚本中使用该服务器，用完后也请调用 `close()`。

## 🤝 贡献

我们欢迎对项目的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 获取详细信息。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 📞 支持

- **问题反馈**: [GitHub Issues](https://github.com/karavaykov/chroma-vector-search/issues)
- **文档**: [docs/](docs/)
- **示例**: [examples/](examples/)

## 🙏 致谢

- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Sentence Transformers](https://www.sbert.net/) - 嵌入模型
- [OpenCode](https://opencode.ai/) - AI 开发平台

---

**注意**: 本项目是官方 MCP（模型上下文协议）的替代方案，专门设计为兼容 Python 3.9+，使其可供更广泛的用户使用。