"""
环境变量集中读取：load_dotenv 后暴露全局配置。

统一管理 LLM、嵌入、数据库、Redis、CORS 等配置项，业务代码 import 即用；
数字类配置由各使用方按需做 int 转换与校验。
"""
import os
from dotenv import load_dotenv
load_dotenv()

model_name = os.getenv("MODEL_NAME")
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_max_tokens = os.getenv("MODEL_MAX_TOKENS", "4096")

model_name2 = os.getenv("MODEL_NAME2")
api_key2 = os.getenv("API_KEY2")
base_url2 = os.getenv("BASE_URL2")

embeddings_model_name = os.getenv("EMBEDDINGS_MODEL_NAME")

secret_key = os.getenv("SECRET_KEY")
algorithm = os.getenv("ALGORITHM")

ps_dsn = os.getenv("PS_DSN")
<<<<<<< HEAD
connection_string = os.getenv("CONNECTION_STRING")
connectioned_string = os.getenv("CONNECTIONED_STRING")

app_env = os.getenv("APP_ENV")
redis_url = os.getenv("REDIS_URL")
redis_host = os.getenv("REDIS_HOST", "192.168.233.129")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")
redis_password = os.getenv("REDIS_PASSWORD") or None
memory_ttl_seconds = os.getenv("MEMORY_TTL_SECONDS", "604800")
memory_max_messages = os.getenv("MEMORY_MAX_MESSAGES", "20")
sql_query_timeout = os.getenv("SQL_QUERY_TIMEOUT")
sql_max_rows = os.getenv("SQL_MAX_ROWS")
postgres_pool_min_size = os.getenv("POSTGRES_POOL_MIN_SIZE", "1")
postgres_pool_max_size = os.getenv("POSTGRES_POOL_MAX_SIZE", "10")
postgres_pool_timeout = os.getenv("POSTGRES_POOL_TIMEOUT", "10")
postgres_pool_max_lifetime = os.getenv("POSTGRES_POOL_MAX_LIFETIME", "3600")

# 前端跨域白名单：逗号分隔。换端口时改 .env 的 CORS_ORIGINS 即可，无需改代码。
# 注意：allow_credentials=True 时不能用 "*"，必须显式列出 origin。
_default_cors_origins = ["http://localhost:8080", "http://localhost:8088"]
cors_origins = [
    origin.strip()
    for origin in (os.getenv("CORS_ORIGINS") or "").split(",")
    if origin.strip()
] or _default_cors_origins

# 后续可考虑优化：
# 1. 把环境变量封装成 Settings 对象，避免业务代码到处 import 零散变量。
# 2. 对 SQL_QUERY_TIMEOUT、SQL_MAX_ROWS 这类数字配置做 int 转换和非法值校验。
# 3. 对 PS_DSN、API_KEY、SECRET_KEY 这类关键配置做启动期必填检查，提前暴露配置问题。
# 4. 兼容 PS_DSN / CONNECTION_STRING 的优先级选择，避免数据库连接变量命名不统一。
# 5. Redis 推荐使用 REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_PASSWORD 显式构建客户端。
=======

app_env = os.getenv("APP_ENV")
redis_url = os.getenv("REDIS_URL")
redis_host = os.getenv("REDIS_HOST", "192.168.233.129")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")
redis_password = os.getenv("REDIS_PASSWORD") or None
memory_ttl_seconds = os.getenv("MEMORY_TTL_SECONDS", "604800")
memory_max_messages = os.getenv("MEMORY_MAX_MESSAGES", "20")
sql_query_timeout = os.getenv("SQL_QUERY_TIMEOUT")
sql_max_rows = os.getenv("SQL_MAX_ROWS")
postgres_pool_min_size = os.getenv("POSTGRES_POOL_MIN_SIZE", "1")
postgres_pool_max_size = os.getenv("POSTGRES_POOL_MAX_SIZE", "10")
postgres_pool_timeout = os.getenv("POSTGRES_POOL_TIMEOUT", "10")
postgres_pool_max_lifetime = os.getenv("POSTGRES_POOL_MAX_LIFETIME", "3600")

# 前端跨域白名单：逗号分隔。换端口时改 .env 的 CORS_ORIGINS 即可，无需改代码。
# 注意：allow_credentials=True 时不能用 "*"，必须显式列出 origin。
_default_cors_origins = ["http://localhost:8080", "http://localhost:8088"]
cors_origins = [
    origin.strip()
    for origin in (os.getenv("CORS_ORIGINS") or "").split(",")
    if origin.strip()
] or _default_cors_origins

# 后续可考虑优化：
# 1. 把环境变量封装成 Settings 对象，避免业务代码到处 import 零散变量。
# 2. 对 SQL_QUERY_TIMEOUT、SQL_MAX_ROWS 这类数字配置做 int 转换和非法值校验。
# 3. 对 PS_DSN、API_KEY、SECRET_KEY 这类关键配置做启动期必填检查，提前暴露配置问题。
# 4. 兼容 PS_DSN / CONNECTION_STRING 的优先级选择，避免数据库连接变量命名不统一。
# 5. Redis 推荐使用 REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_PASSWORD 显式构建客户端。
>>>>>>> dev-v2
