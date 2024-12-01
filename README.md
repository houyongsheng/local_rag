# Local Offline RAG System

一个基于本地大语言模型的检索增强生成(RAG)系统,支持中英文文档的智能问答。本项目使用Ollama作为底层语言模型,无需依赖商业API。

A local Retrieval-Augmented Generation (RAG) system supporting intelligent Q&A for both Chinese and English documents. This project uses Ollama as the underlying language model, eliminating the need for commercial APIs.

## 特性 Features

- 🚀 基于本地LLM (Ollama),无需API密钥
- 💻 完全离线运行,无需联网
- 🔋 仅需CPU即可流畅运行,无需GPU
- 📚 支持中英文文档的智能问答
- 🔄 支持动态更新文档库
- 📝 提供文档总结功能
- 🌐 REST API接口,方便集成
- 💾 持久化向量存储
- 🧠 基于langchain和langgraph的对话管理
- 🖥️ 提供美观的Streamlit Web界面
- 💬 支持多会话管理和历史记录

## 系统要求 System Requirements

- 普通笔记本电脑即可运行 (Only a basic laptop is needed)
  - CPU: 任意现代处理器 (Any modern processor)
  - 内存: 建议8GB以上 (8GB+ RAM recommended)
  - 硬盘: 10GB可用空间 (10GB free disk space)
  - 无需GPU (No GPU required)
  - 无需联网 (No internet connection required after initial setup)

## 前置要求 Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/)
- 已安装以下模型（离线环境下将模型文件通过u盘拷贝到./ollama/models目录下）:
  - qwen2.5:3b（或其他模型）
  - bge-m3

## 安装 Installation

1. 克隆仓库 Clone the repository
```bash
git clone https://github.com/houyongsheng/local_rag.git
cd local_rag
```

2. 创建并激活虚拟环境 Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. 安装依赖 Install dependencies
```bash
pip install -r requirements.txt
```

## 使用方法 Usage

本项目提供两种使用方式：Web界面和API接口。

### 1. Web界面

启动Streamlit应用：
```bash
streamlit run app.py
```

功能特点：
- 美观的聊天界面
- 支持多会话管理
- 近期会话记录
- 一键获取文档总结
- 实时对话历史
- 支持更新文档库

### 2. API接口

启动FastAPI服务：
```bash
python rag.py
```

## API接口说明 API Endpoints

- POST `/chat`
  - 发送问题并获取回答 Send question and get answer
  - 请求体 Request body:
    ```json
    {
        "question": "你的问题",
        "thread_id": "会话ID(可选)"
    }
    ```

- POST `/update_docs`
  - 更新文档库 Update document database
  - 请求体 Request body:
    ```json
    {
        "docs_dir": "文档目录路径"
    }
    ```

- GET `/summary`
  - 获取文档总结 Get document summary

## 示例 Example

```python
import requests

# 发送问题
response = requests.post("http://localhost:8000/chat", 
    json={"question": "文档的主要内容是什么?"})
print(response.json())

# 更新文档
response = requests.post("http://localhost:8000/update_docs",
    json={"docs_dir": "/path/to/docs"})
print(response.json())
```

## 项目结构 Project Structure

```
local_rag/
├── app.py          # Streamlit Web界面
├── rag.py          # FastAPI后端服务
├── requirements.txt # 项目依赖
├── chroma_db/      # 向量数据库存储
└── test/           # 测试文档目录
```

## 贡献指南 Contributing

欢迎提交Pull Request或Issue!

## 开源协议 License

本项目采用 MIT 协议。
