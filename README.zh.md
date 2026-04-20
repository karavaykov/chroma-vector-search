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
pytest tests/

# 测试单个模块
pytest tests/test_basic.py
pytest tests/test_client.py
```

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