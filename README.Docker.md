# Docker 本地启动

在本目录运行。Docker Compose 会启动前端、FastAPI、Redis 和本地 MCP 服务。PostgreSQL 独立运行，由 `.env` 的 `APP_DATABASE_URL` 指定；Redis 数据保存在 Docker 命名卷中。

1. 复制 `.env.example` 为 `.env`，填写模型 API、独立 PostgreSQL、Ollama、共享登录和至少 32 字符的 `SECRET_KEY`。请勿提交真实 `.env`。
2. 运行 `docker compose up -d --build`。
3. 浏览器打开 `http://localhost:8080`；健康检查地址为 `http://localhost:8080/health`。
4. 查看日志：`docker compose logs -f backend`。停止服务：`docker compose down`。

前端通过同域 `/v1` 访问后端。Redis 仅在 Compose 内部网络开放，后端用 `redis` 作为主机名。PostgreSQL 不由本 Compose 启动，后端使用 `APP_DATABASE_URL` 连接现有数据库。

登录账号密码由 `.env` 配置，前端会向 `/v1/auth/login` 登录，后端会校验全部 `/v1` 业务接口。登录令牌 12 小时后过期。现有本机 `.env` 中已生成随机密码；可在本机用编辑器打开 `.env` 查看 `APP_PASSWORD`，不要把它发到公开聊天或提交到仓库。需要更换密码时，修改 `.env` 并重新创建后端容器。

在 `.env` 设置 `APP_DATABASE_URL=postgresql://用户:密码@数据库地址:5432/库名`。该地址必须能从后端容器访问，数据库需安装 pgvector。本机模拟生产时可连接 Docker 宿主机；正式生产可替换为云数据库内网地址。

首次使用业务演示数据与知识库时，需调用 `POST /v1/tools/sql/demo-data` 和 `POST /v1/rag/init`。RAG 嵌入依赖 `.env` 中的 `EMBEDDINGS_MODEL_NAME` 和 `OLLAMA_BASE_URL`。本项目的 Ollama 位于虚拟机外的物理主机，因此该地址应填写物理主机在 VMware 网络中的 IP，例如 `http://192.168.233.1:11434`。物理主机上的 Ollama 必须监听局域网地址，主机防火墙也必须允许虚拟机访问 TCP 11434。

本配置将网页绑定到本机 `127.0.0.1:8080`。要从其他联网设备临时访问，可在 Docker 服务启动后运行：

```bash
docker run -d --name agent-quick-tunnel --network host cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://localhost:8080
docker logs agent-quick-tunnel
```

日志中的 `https://...trycloudflare.com` 是临时公网地址。打开它即可看到前端，用 `.env` 中的共享账号密码登录；请求经同一地址的 `/v1` 转发到 FastAPI。虚拟机和 Docker 必须持续运行，隧道重启后地址可能改变。停止临时分享：`docker stop agent-quick-tunnel`；再次创建同名容器前须移除旧容器。临时隧道仅用于测试和演示，没有稳定地址或可用性保证。长期公开使用时，应配置正式域名与持久隧道，或把服务部署到一直在线的服务器。

`database/demo_business_seed.py` 是随项目提供的演示实例，默认创建产品、订单和地区事件表，并写入模拟数据。使用者可直接运行演示，也可修改其中的 `PRODUCTS`、`SALES_ORDERS`、`REGION_EVENTS` 和建表 SQL，把它换成自己的业务数据。若重写整个文件，应保留 `seed_demo_business_data()` 函数，并返回 `status`（字符串）、`tables`（表名列表）、`rows`（各表写入行数的字典），因为 `/v1/tools/sql/demo-data` 接口使用这个返回格式。真实企业数据和凭据不要提交到公开仓库。
