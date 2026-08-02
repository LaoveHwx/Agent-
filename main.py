"""
总装配文件
    1.创建 FastAPI
    2.挂路由
    3.可能还有：初始化数据库...
    最后：前端CORS配置
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


from api_router.agent_router import agent_router
from api_router.health_router import health_router
from api_router.memory_router import memory_router
from api_router.planner_router import planner_router
from api_router.rag_router import rag_router
from api_router.tool_router import tool_router
from utils.env_util import cors_origins
from utils.logger import request_log_middleware, setup_logger
from utils.postgres_pool import close_postgres_pool

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用关闭时释放 PostgreSQL 连接池。"""
    try:
        yield
    finally:
        close_postgres_pool()


app = FastAPI(title="Enterprise Data Agent API", lifespan=lifespan)
# 日志中间件
app.middleware("http")(request_log_middleware)
app.include_router(health_router)
app.include_router(agent_router, prefix="/v1")
app.include_router(planner_router, prefix="/v1")
app.include_router(rag_router, prefix="/v1")
app.include_router(tool_router, prefix="/v1")
app.include_router(memory_router, prefix="/v1")
# evaluation 评测套件（默认不挂载）：跑 sql/rag/agent 三类用例，
# 验证 SQL 能查到数据、RAG 能检到正确来源、Agent 路由+回答是否跑通。
# 需要时取消下面两行注释即可
# from api_router.evaluation_router import evaluation_router
# app.include_router(evaluation_router, prefix="/v1")

# 允许跨域配置
# allow_origins: 允许请求源跨域访问，来源见 utils.env_util.cors_origins（可由 .env 的 CORS_ORIGINS 覆盖）
# allow_headers：允许请求头信息跨域访问，如：Content-Type、Authorization等
# allow_methods：允许请求方式跨域访问，如：get、post、put、delete、options等
# allow_credentials：是否允许请求携带认证信息
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True
)
