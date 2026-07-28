# 企业级 AI Agent 系统开发执行计划

## 项目名称

企业智能数据分析 Agent 系统

# 一、项目目标

开发一个企业级 Data Agent，实现：

用户自然语言输入：

> 分析2026年第一季度销售下降原因

系统自动完成：

1.  理解业务问题
2.  查询企业数据库
3.  检索业务知识
4.  自动生成 SQL
5.  执行数据分析
6.  输出可解释报告

------------------------------------------------------------------------

# 二、技术栈与开发环境

## 开发工具

### IDE

PyCharm

### AI辅助开发

CCGUI，codex

------------------------------------------------------------------------

## 后端技术

Python 3.11

核心框架：

-   FastAPI
-   LangChain
-   LangGraph

## 数据层

业务数据库：

PostgreSQL

向量检索：

PostgreSQL + pgvector

缓存：

Redis

模型：

-   Qwen系列模型
-   OpenAI API

工程：

-   Git
-   Docker

------------------------------------------------------------------------

# 三、整体开发周期

总周期：

10周

开发路线：

    环境搭建

    ↓

    项目工程化

    ↓

    PostgreSQL业务数据库

    ↓

    单Agent执行

    ↓

    RAG知识库

    ↓

    Agent Teams

    ↓

    Memory状态管理

    ↓

    评测体系

    ↓

    Docker部署

------------------------------------------------------------------------

# 阶段0：开发环境准备（第1天）

## 创建环境

``` bash
conda create -n data-agent python=3.11

conda activate data-agent
```

安装：

``` bash
pip install langgraph
pip install langchain
pip install fastapi
pip install uvicorn
pip install psycopg2
pip install pgvector
pip install redis
```

验收：

PyCharm可以正常运行Python项目。

------------------------------------------------------------------------

# 阶段1：项目基础工程搭建（第1周）

## 目标

建立企业级项目结构。

目录：

    data-agent

    ├── app
    │
    ├── agents
    │   ├── planner.py
    │   ├── sql_agent.py
    │   └── rag_agent.py
    │
    ├── tools
    │   ├── postgres_tool.py
    │   └── search_tool.py
    │
    ├── rag
    │   ├── embedding.py
    │   └── retriever.py
    │
    ├── memory
    │   └── redis_memory.py
    │
    ├── evaluation
    │
    ├── database
    │
    └── main.py

完成：

-   FastAPI服务
-   配置管理
-   日志系统
-   Git版本管理

验收：

启动服务：

    uvicorn main:app

返回：

    Agent API running

------------------------------------------------------------------------

# 阶段1.5：认证鉴权规划（后续需要时实现）

## 目标

为企业级 API 增加登录认证和 JWT Token 机制。

当前阶段只纳入计划，不立即实现，避免过早影响 Agent 主链路开发。

## 规划能力

### 登录接口

接口：

    POST /v1/auth/login

输入：

    username
    password

输出：

    access_token
    token_type
    expires_in

### JWT生成

基于：

    SECRET_KEY
    ALGORITHM

生成：

    access_token

Token Payload建议包含：

    sub
    user_id
    role
    exp

### JWT验证

封装：

    get_current_user()

用于保护后续接口：

    /v1/agent/analyze
    /v1/tools/sql/query
    /v1/rag/search

### 防御机制

-   密码不得明文保存
-   JWT必须设置过期时间
-   SECRET_KEY不得提交到Git
-   登录失败不暴露具体原因
-   需要统一认证异常响应

## 建议目录

    api_router/auth_router.py
    schemas/auth.py
    services/auth_service.py
    utils/security.py

## 验收

用户登录成功后获取Token。

携带：

    Authorization: Bearer <token>

可以访问受保护接口。

未携带或Token无效时返回：

    401 Unauthorized

------------------------------------------------------------------------

# 阶段2：PostgreSQL业务数据库建设（第2周）

## 目标

模拟企业真实数据环境。

设计业务表：

## 用户表

user

## 产品表

product

## 订单表

order

## 销售表

sales

示例：

``` sql
sales

id

product_id

date

amount

region
```

生成：

百万级测试数据。

实现：

PostgreSQL查询工具。

输入：

    查询需求

输出：

    SQL结果

验收：

用户：

> 查询本月销售额最高产品

Agent：

自动生成SQL并返回结果。

------------------------------------------------------------------------

# 阶段3：单Agent任务执行（第3周）

## 目标

实现基础Agent能力。

架构：

    用户

    ↓

    Planner Agent

    ↓

    Tool调用

    ↓

    结果总结

实现：

## Prompt管理

目录：

    prompts/

    system_prompt.yaml

    sql_prompt.yaml

支持：

-   Prompt模板
-   参数注入
-   版本管理

------------------------------------------------------------------------

## Tool开发

第一个Tool：

PostgreSQL Query Tool

功能：

    query_database(sql)

流程：

用户问题

↓

Agent生成SQL

↓

调用数据库

↓

返回结果

↓

总结回答

------------------------------------------------------------------------

# 阶段4：RAG知识库建设（第4-5周）

## 目标

解决企业业务知识问题。

知识来源：

-   产品文档
-   财务规则
-   指标定义
-   数据字典

流程：

    文档

    ↓

    文本切分

    ↓

    Embedding

    ↓

    pgvector

    ↓

    Retriever

    ↓

    LLM回答

数据库：

PostgreSQL

新增：

    documents

    embedding vector

    metadata

优化：

第一版：

向量搜索

第二版：

混合检索：

    Vector Search

    +

    BM25

验收：

用户：

> GMV是什么意思？

Agent：

返回定义，并提供来源。

------------------------------------------------------------------------

# 阶段5：Agent Teams开发（第6-7周）

## 目标

实现多Agent协作。

架构：

                  Coordinator

                        |

    --------------------------------

    |              |              |

    SQL Agent   RAG Agent   Analyst Agent

## Agent职责

### Coordinator Agent

负责：

-   任务拆解
-   Agent调度
-   结果汇总

### SQL Agent

负责：

-   数据查询
-   SQL生成

### RAG Agent

负责：

-   知识检索

### Analyst Agent

负责：

-   数据分析
-   结论生成

使用：

LangGraph

当前实现方法调整：

-   模型调用统一使用 LangChain `ChatOpenAI`
-   SQL Agent / RAG Agent / Analyst Agent 使用 `create_agent` 或 LCEL
-   SQL、RAG、长期记忆能力统一封装为 LangChain tools
-   LangGraph 图只编译一次，运行时复用 compiled graph
-   不再保留“无 LLM 降级运行”路径，Agent 必须依赖大模型

状态：

``` python
state={

question:

sql:

result:

analysis:

}
```

验收：

复杂问题：

> 为什么华东地区销售下降？

系统自动：

查询销售

↓

查询产品

↓

检索业务规则

↓

生成分析

------------------------------------------------------------------------

# 阶段6：Memory和状态管理（第8周）

## Redis实现

当前实现方法调整：

短期记忆：

    RedisSaver + thread_id=session_id

用于保存当前会话上下文，让同一聊天框内上一句和下一句可以关联。

Redis客户端构建方式：

``` python
redis_client = Redis(
    host="192.168.233.129",
    port=6379,
    db=0,
    password=None,
)
```

长期记忆：

    用户个性化记忆
    公司主要情况记忆

以 LangChain tools 形式提供给 Agent 调用。

保存：

    conversation

    agent_state

    tool_result

实现：

-   多轮对话
-   状态恢复
-   中断继续

案例：

用户：

第一次：

分析销售

第二次：

继续分析华南地区

Agent保持上下文。

------------------------------------------------------------------------

# 阶段7：Agent评测体系（第9周）

建立100条测试集。

分类：

-   简单查询
-   多表分析
-   知识问答
-   复杂推理

指标：

## SQL指标

-   SQL生成成功率
-   执行成功率

## Agent指标

-   任务完成率
-   Tool调用成功率

## RAG指标

-   Recall
-   引用准确率

## 系统指标

-   响应时间
-   Token成本

增加：

-   Prompt A/B测试
-   模型A/B测试
-   回归测试

当前优先级调整：

-   保留小规模回归测试集，用于验证 SQL / RAG / Agent 主链路
-   暂不扩展到 100 条测试集
-   优先保证 Agent/Graph/Memory/Stream 接口稳定

------------------------------------------------------------------------

# 阶段8：工程化部署（第10周）

当前优先级调整：

本阶段暂不推进。

当前项目重点先放在：

    Agent正确回复
    LangGraph编排稳定
    Redis短期/长期记忆
    前端流式输出接口

Docker部署：

    docker-compose


    ├── Agent服务

    ├── PostgreSQL

    ├── Redis

部署：

    FastAPI

    ↓

    Nginx

    ↓

    Docker

------------------------------------------------------------------------

# 最终项目成果

代码仓库：

    data-agent

包含：

-   单Agent系统
-   RAG知识库
-   PostgreSQL数据分析
-   Tool Calling
-   Agent Teams
-   Memory
-   Evaluation

------------------------------------------------------------------------

# JD匹配关系 

  JD要求         实现
  -------------- ---------------------
  AI Agent开发   LangGraph Agent系统
  Prompt编排     Prompt管理模块
  Tool定义调用   PostgreSQL Tool
  RAG优化        pgvector+混合检索
  Agent Teams    Coordinator架构
  上下文管理     Redis Memory
  评测体系       Evaluation系统
  工程规范       Docker+Git
登录功能的密码要存加密哈希。
------------------------------------------------------------------------

# 项目定位

企业Agent：

    用户需求

    ↓

    任务理解

    ↓

    任务规划

    ↓

    知识检索

    ↓

    工具调用

    ↓

    数据处理

    ↓

    结果验证

    ↓

    生成业务结论

    ↓

    评测优化

目标：

达到企业 Agent 工程师岗位作品要求。
