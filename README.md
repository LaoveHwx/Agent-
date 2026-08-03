# 企业智能数据分析 Agent 系统

这是一个面向企业数据分析场景的 AI Agent 项目。用户输入自然语言问题后，系统可以进行任务规划、业务知识检索、SQL 查询、数据分析，并输出可解释的回答。

详细开发路线见：[企业级AI_Agent系统开发执行计划.md](企业级AI_Agent系统开发执行计划.md)。

## 项目功能

- Agent 编排：基于 LangGraph 编排 Planner、SQL Agent、RAG Agent、Analyst Agent。
- Text2SQL：根据用户问题生成并执行 PostgreSQL 查询。
- RAG 知识库：支持文档上传、文本切分、Embedding、pgvector 检索。
- Memory：基于 Redis 保存会话上下文、Agent 状态和工具结果。
- 流式输出：`/v1/agent/stream` 支持 NDJSON 事件流，便于前端展示执行过程。
- Evaluation：提供 SQL、RAG、Agent 基础回归评测入口。
- MCP 工具：预留 MCP 图表工具接入能力。

## 环境安装

建议新建干净的 Conda 虚拟环境，Python 使用 3.11。`env_name` 可以替换成自己的环境名。

```bash
conda create -n env_name python=3.11 -y
conda activate env_name
```

升级基础打包工具：

```bash
python -m pip install -U pip setuptools wheel
```

安装项目依赖：

```bash
pip install "fastapi[standard-no-fastapi-cloud-cli]" uvicorn python-dotenv
pip install langchain langchain-openai langchain-ollama langgraph langgraph-checkpoint-redis
pip install "psycopg[binary]" psycopg_pool redis python-multipart
pip install langchain-mcp-adapters
pip install fastmcp
pip install pgvector pandas
```

说明：

- 当前代码使用 `psycopg` 连接 PostgreSQL，因此安装 `psycopg[binary]`。
- `python-multipart` 用于支持 RAG 文件上传接口。
- `langgraph-checkpoint-redis` 用于 Redis 会话检查点。
- `fastmcp`、`langchain-mcp-adapters` 用于 MCP 工具接入。

## 外部服务

运行完整功能前，需要准备：

- PostgreSQL：业务数据表和 RAG 向量表。
- pgvector：PostgreSQL 向量检索扩展。
- Redis：会话记忆和状态保存。
- Qwen/OpenAI-compatible Chat Model：大模型接口。
- Ollama Embeddings：可选，用于本地 Embedding。

## 环境变量

项目从 `.env` 读取配置。示例：

```env
MODEL_NAME=your_model_name
API_KEY=your_api_key
BASE_URL=your_model_base_url
EMBEDDINGS_MODEL_NAME=your_embedding_model_name

PS_DSN=postgresql://user:password@localhost:5432/database

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

SQL_QUERY_TIMEOUT=10
SQL_MAX_ROWS=200
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=10
POSTGRES_POOL_TIMEOUT=10
POSTGRES_POOL_MAX_LIFETIME=3600

OLLAMA_BASE_URL=http://127.0.0.1:11434
RAG_EMBEDDING_DIM=1024
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120
```

## 启动项目

在项目根目录执行：

```bash
uvicorn main:app --reload
```

启动后访问：

```text
API:  http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
```

## 常用接口

健康检查：

```text
GET /health
```

初始化 demo 业务数据：

```text
POST /v1/tools/sql/demo-data
```

查看业务表结构：

```text
GET /v1/tools/sql/schema
```

初始化 RAG 表：

```text
POST /v1/rag/init
```

上传知识库文件：

```text
POST /v1/rag/upload
```

检索知识库：

```text
POST /v1/rag/search
```

Agent 问答：

```text
POST /v1/agent/analyze
```

Agent 流式问答：

```text
POST /v1/agent/stream
```

运行评测：

```text
POST /v1/evaluation/run
```

## 测试顺序

1. 创建并激活 Python 3.11 虚拟环境。
2. 安装依赖。
3. 配置 `.env`。
4. 启动 PostgreSQL、pgvector 和 Redis。
5. 执行 `uvicorn main:app --reload` 启动后端。
6. 调用 `/v1/tools/sql/demo-data` 初始化 demo 数据。
7. 调用 `/v1/rag/init` 初始化知识库表。
8. 上传业务文档到 `/v1/rag/upload`。
9. 使用 `/v1/agent/analyze` 或 `/v1/agent/stream` 提问。

使用：开启本地
-cd 到前端所在文件夹
-npm run build 启动
-python.exe -m http.server 8088 --directory dist  挂载
启动http://localhost:8088
 or
http://localhost:8088/#/
## 示例问题

```text
查询销售额最高的产品
为什么华东地区销售下降？
把刚才的销售结果画成柱状图
```
