# 企业智能数据分析 Agent 系统

面向企业数据分析场景的 AI Agent 系统：用自然语言提问，系统自动完成任务规划、业务知识检索（RAG）、SQL 查询与数据分析，并输出可解释的回答。

## 系统架构

- **Agent 编排**：基于 LangGraph 编排 Planner、SQL Agent、RAG Agent、Analyst Agent 与 MCP 工具节点。
- **Text2SQL**：自然语言生成并执行 PostgreSQL 只读查询。
- **RAG 知识库**：文档上传、切分、Embedding、pgvector 向量检索。
- **Memory**：Redis 保存会话上下文与 Agent 状态。
- **流式输出**：`/v1/agent/stream` 返回 NDJSON 事件流，前端可实时展示执行步骤与打字机效果。
- **MCP 工具**：自建数值计算 server + 远程图表 server，失败自动降级不阻断回答。
- **Evaluation**：SQL / RAG / Agent 回归评测。

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

## 外部服务

运行前需要准备：

- **PostgreSQL**：业务数据表和 RAG 向量表
- **pgvector**：PostgreSQL 向量检索扩展
- **Redis**：会话记忆和状态保存
- **Qwen/OpenAI-compatible Chat Model**：大模型接口
- **Ollama Embeddings**：可选，本地 Embedding

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

## 启动步骤

```bash
# 1. 启动自建 MCP 数值计算服务（可选，失败不影响主流程）
python mcp_station/sever.py

# 2. 启动后端
uvicorn main:app --reload
```

启动后访问：

```text
API:  http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
```

## 常用接口

```text
GET  /health                     健康检查
POST /v1/tools/sql/demo-data     初始化演示业务数据
GET  /v1/tools/sql/schema        查看业务表结构
POST /v1/rag/init                初始化 RAG 知识库表
POST /v1/rag/upload              上传知识库文件
POST /v1/rag/search              检索知识库
POST /v1/agent/analyze           Agent 同步问答
POST /v1/agent/stream            Agent 流式问答（NDJSON）
POST /v1/evaluation/run          运行评测
```

## 前端使用

前端项目位于 `Agent_front`（Vue 2 + element-ui）：

```bash
cd Agent_front
npm run dev          # http://localhost:8080
```

登录账号由 `.env` 中的 `APP_USERNAME` / `APP_PASSWORD` 配置；后端会验证登录并签发有效期为 12 小时的访问令牌。Docker 使用说明见 `README.Docker.md`。

## 推荐使用顺序

1. 启动 PostgreSQL（含 pgvector）与 Redis。
2. 配置 `.env`。
3. `POST /v1/tools/sql/demo-data` 初始化演示数据。
4. `POST /v1/rag/init` 初始化知识库表，上传业务文档。
5. 启动前端，用自然语言提问。

## 示例问题

```text
查询销售额最高的产品
为什么华东地区销售下降？
把刚才的销售结果画成柱状图
```
