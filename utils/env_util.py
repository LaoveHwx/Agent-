import os
from dotenv import load_dotenv
load_dotenv()

model_name = os.getenv("MODEL_NAME")
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")

embeddings_model_name = os.getenv("EMBEDDINGS_MODEL_NAME")

secret_key = os.getenv("SECRET_KEY")
algorithm = os.getenv("ALGORITHM")

ps_dsn = os.getenv("PS_DSN")
connection_string = os.getenv("CONNECTION_STRING")
connectioned_string = os.getenv("CONNECTIONED_STRING")

app_env = os.getenv("APP_ENV")
redis_url = os.getenv("REDIS_URL")
redis_db = os.getenv("REDIS_DB", "2")
memory_ttl_seconds = os.getenv("MEMORY_TTL_SECONDS", "604800")
memory_max_messages = os.getenv("MEMORY_MAX_MESSAGES", "20")
sql_query_timeout = os.getenv("SQL_QUERY_TIMEOUT")
sql_max_rows = os.getenv("SQL_MAX_ROWS")

# 后续可考虑优化：
# 1. 把环境变量封装成 Settings 对象，避免业务代码到处 import 零散变量。
# 2. 对 SQL_QUERY_TIMEOUT、SQL_MAX_ROWS 这类数字配置做 int 转换和非法值校验。
# 3. 对 PS_DSN、API_KEY、SECRET_KEY 这类关键配置做启动期必填检查，提前暴露配置问题。
# 4. 兼容 PS_DSN / CONNECTION_STRING 的优先级选择，避免数据库连接变量命名不统一。
# 5. Redis Memory 默认使用 REDIS_DB=2，避免占用你已经在使用的 DB 1。
