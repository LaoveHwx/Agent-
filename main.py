"""
总装配文件
    1.创建 FastAPI
    2.挂路由
    3.可能还有：初始化数据库...
    最后：前端CORS配置
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


from api_router.agent_router import agent_router
from api_router.evaluation_router import evaluation_router
from api_router.health_router import health_router
from api_router.memory_router import memory_router
from api_router.planner_router import planner_router
from api_router.rag_router import rag_router
from api_router.tool_router import tool_router
from utils.logger import request_log_middleware, setup_logger

logger = setup_logger(__name__)
app = FastAPI(title="Enterprise Data Agent API")

app.middleware("http")(request_log_middleware)
app.include_router(health_router)
app.include_router(agent_router, prefix="/v1")
app.include_router(planner_router, prefix="/v1")
app.include_router(rag_router, prefix="/v1")
app.include_router(tool_router, prefix="/v1")
app.include_router(memory_router, prefix="/v1")
app.include_router(evaluation_router, prefix="/v1")

# 允许跨域配置
# allow_origins: 允许请求源跨域访问，http://localhost:8080等等，"*"表示允许所有请求源
# allow_headers：允许请求头信息跨域访问，如：Content-Type、Authorization等
# allow_methods：允许请求方式跨域访问，如：get、post、put、delete、options等
# allow_credentials：是否允许请求携带认证信息
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True
)
