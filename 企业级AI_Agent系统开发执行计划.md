# 企业级 AI Agent 系统技术栈扩展计划

当前项目已经具备：

- FastAPI 后端服务
- LangChain / LangGraph Agent 编排
- SQL Agent / RAG Agent / Analyst Agent
- PostgreSQL 业务数据查询
- pgvector 向量检索
- Redis 会话记忆
- 基础 Evaluation 回归评测
- `/v1/agent/stream` 流式输出接口
- MCP 图表工具接入雏形

因此后续重点不是重新搭建项目，而是在现有基础上补齐 JD 强调的工程化 AI Agent 能力。

## 一、JD 技术要求归纳

两个 JD 对技术栈的核心要求可以归纳为：

- AI 应用开发：RAG、Agent、工作流自动化、Text2SQL。
- LLM 框架：LangChain、Transformers、主流大模型 API。
- Prompt Engineering：Prompt 设计、调优、版本管理、效果验证。
- RAG 技术链路：文档解析、chunk 切分、Embedding、向量检索、Rerank、混合检索。
- 评测优化：生成质量、召回准确率、响应延迟、成本、稳定性。
- 后端工程：Python、FastAPI、数据库、接口封装、服务联调。
- 数据处理：正则、Pandas、PostgreSQL、Elasticsearch、FAISS、MongoDB 等。
- 全栈能力：了解 React / Vue，能完成基础前端展示。
- 工程化能力：测试、日志、问题排查、Docker、文档沉淀。

## 二、当前项目技术栈缺口

| 方向 | 当前已有 | 主要缺口 |
| --- | --- | --- |
| Agent 编排 | LangGraph 多节点工作流 | 缺少更清晰的节点耗时、工具调用、错误追踪 |
| Prompt | Prompt 写在代码中 | 缺少 Prompt 文件化、版本管理、A/B 测试 |
| RAG | pgvector 向量检索 | 缺少混合检索、Rerank、召回评测、引用校验 |
| Text2SQL | PostgreSQL 查询工具、业务表限制 | 缺少 SQL 安全校验、错误自修复、SQL 质量评测 |
| Evaluation | SQL/RAG/Agent 基础回归 | 缺少延迟、成本、召回、失败原因分类 |
| Memory | Redis 会话记忆 | 缺少用户隔离、长期记忆写入策略 |
| 前端 | 后端已提供 stream 接口 | 缺少 React/Vue 页面展示 Agent 执行过程 |
| 工程化 | FastAPI、日志、Git | 缺少 Docker Compose、测试命令、依赖文件、CI |
| 数据处理 | PostgreSQL、pgvector | 缺少 Pandas 处理样例、ES/FAISS/MongoDB 调研或对比 |

## 三、技术栈扩展计划

| 优先级 | 扩展方向 | 建议加入的技术栈 | 当前项目落点 | JD 对应能力 | 验收标准 |
| --- | --- | --- | --- | --- | --- |
| P0 | Prompt 管理 | YAML / JSON Prompt 模板、版本号、Prompt Loader | 新建 `prompts/`，抽离 Planner、SQL、RAG、Analyst、Final Prompt | Prompt Engineering、LLM 应用开发 | 修改 Prompt 不需要改 Agent 代码 |
| P0 | RAG 增强 | pgvector + BM25/全文检索 + Rerank 接口 | 扩展 `rag/retriever.py` 和 RAG 评测集 | 文档解析、Embedding、向量检索、Rerank | RAG 结果返回来源、score、命中情况 |
| P0 | Evaluation 升级 | JSONL 测试集、指标统计、失败分类、延迟统计 | 扩展 `evaluation/runner.py` | 效果评测、原因分析、方案验证 | 输出 SQL/RAG/Agent 分项指标 |
| P0 | Text2SQL 安全 | SQL Parser / 白名单校验 / 只读限制 / 超时限制 / psycopg_pool 连接池 | 强化 `tools/postgres_tool.py` 和 `utils/postgres_pool.py` | Text2SQL、数据库、安全稳定性 | 危险 SQL 被拒绝，错误可追踪，数据库连接可复用 |
| P1 | Agent 可观测性 | trace_id、节点耗时、工具耗时、错误摘要 | 扩展 `graph/center_graph.py` 和日志中间件 | 问题排查、上线支持、稳定性 | 单次请求可追踪完整 Agent 链路 |
| P1 | 前端展示 | React 或 Vue、NDJSON 流式消费 | 新建 `frontend/`，接入 `/v1/agent/stream` | 全栈开发、系统集成 | 页面展示步骤、工具调用、最终回答 |
| P1 | 数据处理增强 | Pandas、正则清洗、CSV/JSON 数据处理 | 扩展 RAG 上传解析和评测数据分析 | 数据处理、大规模文本处理 | 能处理结构化/半结构化业务文件 |
| P1 | 工程化部署 | requirements.txt、Docker Compose、pytest、ruff | 补齐依赖、启动、测试和部署脚本 | Linux 后端、工程交付 | 新环境可按文档稳定启动 |
| P2 | 检索方案对比 | FAISS / Elasticsearch | 做小规模方案验证，不强制替换 pgvector | 技术调研、方案验证 | 输出对比结论和适用场景 |
| P2 | 长期存储扩展 | MongoDB | 用于长期记忆或非结构化业务文档元数据 | 数据库、多源数据管理 | 明确是否适合当前项目 |
| P2 | 模型能力扩展 | Transformers、Fine-tuning 方案 | 先做方案文档，不直接改主链路 | LLM 原理、微调经验 | 明确何时微调、何时优先 RAG/Prompt |

## 四、推荐实施顺序

### 1. Prompt 管理（基础版已完成）

当前 Agent Prompt 已从代码中抽离到独立文件，并记录基础版本信息。后续可以继续补 Prompt A/B 测试和评测绑定。

已新增：

```text
prompts/
├── planner.json
├── sql_agent.json
├── rag_agent.json
├── analyst.json
├── mcp_visualization.json
└── final.json
```

已新增统一读取入口：

```text
utils/prompt_loader.py
```

### 2. 再做 Evaluation 升级

Prompt 和 RAG 优化必须依赖评测结果判断效果。当前评测只适合作基础回归，需要扩展指标。

建议新增指标：

- SQL 执行成功率
- SQL 结果非空率
- RAG 来源命中率
- RAG top_k 召回情况
- Agent 任务类型识别准确率
- 平均响应耗时
- 错误原因分类

### 3. 然后做 RAG 增强

当前 RAG 以 pgvector 向量检索为主，建议扩展为可对比的检索链路。

建议扩展：

- 向量检索：pgvector
- 关键词检索：PostgreSQL 全文检索或 BM25 方案
- 混合排序：vector score + keyword score
- Rerank：先预留接口，后续可接本地或 API Reranker
- 引用校验：最终回答必须保留来源信息

### 4. 补强 Text2SQL 安全

企业级 Text2SQL 不能只追求能查，还要保证安全边界。

当前已补充：

- 使用 `psycopg_pool` 增加 PostgreSQL 连接池。
- Text2SQL 查询和 RAG 入库/检索共用连接池。
- FastAPI 关闭时释放连接池。
- 连接池参数可通过 `.env` 配置：`POSTGRES_POOL_MIN_SIZE`、`POSTGRES_POOL_MAX_SIZE`、`POSTGRES_POOL_TIMEOUT`、`POSTGRES_POOL_MAX_LIFETIME`。

建议补强：

- 只允许 `SELECT`
- 禁止 `INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`TRUNCATE`
- 禁止访问 `information_schema`、`pg_catalog`、`rag_documents`、memory/checkpoint 表
- 限制最大返回行数
- 设置查询超时
- SQL 执行失败时返回可读错误

### 5. 最后补工程化和前端展示

为了匹配第二个 JD 的全栈和工程能力，需要补一个轻量前端和基本工程化文件。

建议新增：

- `frontend/`：React 或 Vue 页面
- `requirements.txt`：固定后端依赖
- `docker-compose.yml`：PostgreSQL + Redis + API
- `tests/`：核心服务测试
- `docs/`：Prompt、RAG、Evaluation、Text2SQL 安全说明

## 五、不建议当前优先投入的方向

以下方向 JD 中有提到或相关，但当前项目不建议立刻重投入：

- Torch / TensorFlow：当前项目是 LLM 应用工程，不是模型训练项目，暂不需要作为主技术栈。
- Fine-tuning：没有稳定业务数据和评测集前，不建议直接微调。
- Elasticsearch：可以做检索对比，但当前 pgvector + PostgreSQL 全文检索更符合项目复杂度。
- MongoDB：除非长期记忆或文档元数据规模扩大，否则不是当前必要项。
- 大规模评测集：先把小规模评测指标做完整，再扩展到 100 条以上。

## 六、最终目标

通过以上技术栈扩展，使当前项目从“能运行的 Agent Demo”升级为更符合 JD 的企业级 AI Agent 工程项目：

- 有 Agent 编排
- 有 RAG 检索增强
- 有 Text2SQL 安全边界
- 有 Prompt 调优体系
- 有 Evaluation 指标闭环
- 有 Redis Memory
- 有前端展示
- 有工程化部署和文档沉淀
