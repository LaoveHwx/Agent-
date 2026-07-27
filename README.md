# 企业智能数据分析 Agent 系统

企业级 AI Agent 项目，目标是构建一个面向企业数据分析场景的 Data Agent。系统通过自然语言理解业务问题，自动完成任务规划、业务知识检索、SQL 生成、数据库查询、数据分析，并输出可解释的业务报告。

本项目定位不是普通聊天机器人，而是一个具备工具调用、知识检索、状态管理和评测能力的企业 Agent 工程实践项目。

## 项目目标

用户输入类似：

```text
分析 2026 年第一季度销售下降原因
```

系统计划自动完成：

1. 理解业务问题
2. 拆解分析任务
3. 检索企业业务知识
4. 生成并执行 SQL
5. 分析数据库查询结果
6. 输出可解释的业务结论和报告

## 核心能力规划

- `Planner Agent`：理解用户需求，拆解任务，规划执行流程。
- `SQL Agent`：根据业务问题生成 SQL，并调用 PostgreSQL 查询工具。
- `RAG Agent`：检索产品文档、财务规则、指标定义、数据字典等企业知识。
- `Analyst Agent`：综合结构化数据和业务知识，生成分析结论。
- `Tool Calling`：封装 PostgreSQL 查询、搜索等外部工具。
- `Memory`：基于 Redis 保存对话、Agent 状态和工具结果，支持多轮上下文。
- `Evaluation`：建设测试集，评估 SQL、RAG、Agent 执行和系统性能。

## 技术栈

- Python 3.10
- FastAPI
- LangChain
- LangGraph
- PostgreSQL
- pgvector
- Redis
- Qwen 系列模型 / OpenAI API
- Docker / docker-compose

## 当前项目结构

```text
.
├── api_router/          # API 路由模块
├── graph/               # LangGraph / Agent 编排模块
├── utils/               # 通用工具
│   ├── env_util.py      # 环境变量读取
│   └── logger.py        # 日志工具
├── main.py              # FastAPI 应用入口
├── .env                 # 本地环境变量文件，已被 .gitignore 忽略
├── .gitignore
└── 企业级AI_Agent系统开发执行计划.md
```

> 当前仓库仍处于基础工程搭建阶段，部分计划模块尚未实现。

## 环境准备

创建并激活 Python 环境：

```bash
conda create -n data-agent python=3.10
conda activate data-agent
```

安装基础依赖：

```bash
pip install fastapi uvicorn python-dotenv
pip install langchain langgraph
pip install psycopg2 pgvector redis
```

## 环境变量

项目通过 `.env` 读取模型和数据库配置。示例：

```env
MODEL_NAME=your_model_name
API_KEY=your_api_key
BASE_URL=your_model_base_url
EMBEDDINGS_MODEL_NAME=your_embedding_model_name
PS_DSN=postgresql://user:password@localhost:5432/database
REDIS_URL=redis://:password@localhost:6379
REDIS_DB=2
SQL_QUERY_TIMEOUT=10
SQL_MAX_ROWS=200
```

字段说明：

- `MODEL_NAME`：模型名称
- `API_KEY`：模型服务 API Key
- `BASE_URL`：模型服务地址
- `PS_DSN`：PostgreSQL 连接字符串
- `REDIS_URL`：Redis 连接字符串，不建议在 URL 里写 `/1`
- `REDIS_DB`：Redis 数据库编号，默认 `2`，当前项目会拒绝使用已经占用的 DB `1`
- `EMBEDDINGS_MODEL_NAME`：Embedding 模型名称
- `SQL_QUERY_TIMEOUT`：SQL 查询超时时间，单位秒
- `SQL_MAX_ROWS`：SQL Tool 单次最大返回行数

RAG 可选配置：

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
RAG_EMBEDDING_DIM=1024
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120
```

当 `EMBEDDINGS_MODEL_NAME` 使用 Ollama 本地模型名，例如 `modelscope.cn/Embedding-GGUF/bge-large-zh-v1.5:latest` 或 `nomic-embed-text:latest` 时，系统会优先调用 Ollama Embeddings 接口。

## 启动服务

在项目根目录执行：

```bash
uvicorn main:app --reload
```

默认服务地址：

```text
http://127.0.0.1:8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 当前可用接口

健康检查：

```text
GET /health
```

Planner：

```text
GET  /v1/planner
POST /v1/planner/plan
```

SQL Tool：

```text
GET  /v1/tools/sql/schema
POST /v1/tools/sql/query
```

RAG：

```text
POST /v1/rag/init
POST /v1/rag/documents
POST /v1/rag/search
```

Agent Teams：

```text
GET  /v1/agent
POST /v1/agent/analyze
```

Memory：

```text
GET /v1/memory
GET /v1/memory/sessions/{session_id}
GET /v1/memory/tasks/{task_id}
```

`POST /v1/rag/init` 会在 PostgreSQL 中初始化 `pgvector` 扩展和 `rag_documents` 表。

`POST /v1/agent/analyze` 支持传入 `session_id`。如果不传，系统会自动生成。返回结果中会包含 `task_id` 和 `session_id`，后续可以用 Memory 接口查询会话记录和 Agent 状态。

## 当前开发状态

已完成：

- FastAPI 应用入口初步搭建
- CORS 配置
- 日志工具封装
- `.env` 环境变量读取
- 基础目录结构初始化

待完成：

- `planner_router`、`rag_router`、`tool_router` 路由模块实现和导入
- Planner / SQL / RAG / Analyst Agent 实现
- PostgreSQL 查询 Tool
- RAG 文档入库和 pgvector 检索
- Redis Memory
- Agent 评测体系
- Docker 部署配置

## 开发路线

1. 基础工程搭建：FastAPI、配置管理、日志系统、Git 管理。
2. PostgreSQL 业务数据库：设计用户、产品、订单、销售等业务表，构造测试数据。
3. 单 Agent 执行：实现 Prompt 管理、SQL 生成、Tool 调用和结果总结。
4. RAG 知识库：接入企业文档、指标定义和数据字典，支持向量检索和混合检索。
5. Agent Teams：基于 LangGraph 构建 Coordinator、SQL Agent、RAG Agent、Analyst Agent 协作流程。
6. Memory 状态管理：使用 Redis 保存 conversation、agent_state、tool_result。
7. 评测体系：建设测试集，评估 SQL 成功率、RAG Recall、任务完成率、响应时间和 Token 成本。
8. 工程化部署：使用 Docker Compose 编排 Agent 服务、PostgreSQL 和 Redis。

## 目标成果

最终项目将包含：

- 单 Agent 和多 Agent 协作系统
- PostgreSQL 企业数据分析能力
- RAG 企业知识库
- Tool Calling 工具调用框架
- Redis 上下文和状态管理
- Agent Evaluation 评测体系
- Docker 化部署方案

目标是达到企业 Agent 工程师岗位作品级要求。
