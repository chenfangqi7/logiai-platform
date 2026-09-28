# LogiAI Platform

LogiAI 是现有 TMS / WMS / ERP 之上的物流 AI 能力层。MVP 提供数据接入、统一运单、异常规则、模型分析、运营仪表盘、租户隔离和知识库。项目采用 Vue 3 前端、FastAPI 模块化单体、PostgreSQL/pgvector 与 Redis。

## 快速启动

需要 Docker Desktop 或 Docker Engine 与 Docker Compose。

```sh
cp .env.example .env
docker compose up -d --build
```

在 `.env` 中至少修改 `JWT_SECRET` 与 `DEV_ADMIN_PASSWORD`。首次启动会执行 Alembic 迁移，并在开发环境创建 1 个租户、1 个管理员、1,200 票运单、50 辆车、30 名司机、10 条线路、6,000 条轨迹和 50 条以上异常。种子重复运行不会重复创建演示运单。

| 服务 | 地址 |
| --- | --- |
| 前端 | <http://localhost:5173> |
| API / 文档 | <http://localhost:8001> / <http://localhost:8001/docs> |
| 健康检查 | <http://localhost:8001/health> |

本机已有服务占用 8000，因此默认把容器的 8000 端口映射到宿主机 8001。PostgreSQL 对外默认映射到 5433。可在 `.env` 设置 `SERVER_PORT` 与 `POSTGRES_PORT` 更改宿主机端口。浏览器页面使用 Vite 代理连接容器内的后端。

默认开发租户代码为 `demo`，用户名为 `admin`，密码取自 `.env` 的 `DEV_ADMIN_PASSWORD`。未提供 `.env` 时的开发默认密码是 `change-this-development-password`，仅适合本机体验。更改已有种子管理员的密码不会自动覆盖数据库中的密码。

## 演示链路

1. 登录后进入“数据接入”并新建 REST 连接器。表单已预填开发环境的模拟 TMS 接口 `http://server:8000/demo/tms/shipments`。
2. 在连接器详情中测试连接、获取样例，然后打开“字段映射”。样例字段会自动建议目标字段；确认 `waybillNo → shipment_no`，保存映射。
3. 返回连接器详情点击“同步数据”。25 条模拟运单会导入统一模型，保存原始来源 JSON，并自动运行五类异常规则。
4. 在“运单中心”搜索 `MOCK`，查看轨迹、关联异常和原始数据。在“异常中心”查看分析、建议并解决异常。
5. 在“仪表盘”查看统计、趋势和线路排行。打开“AI 助手”询问“帮我分析今天的异常运输情况。”回答只使用当前租户的数据工具。
6. 在“知识库”添加 SOP 文本或上传 TXT/PDF/DOCX/XLSX 文件；相关问题会检索当前租户的知识片段。

也可在仓库根目录运行 `apps/server/.venv/Scripts/python.exe scripts/smoke.py`（Windows）或相应虚拟环境 Python，执行上述 API 链路的 HTTP 冒烟检查。脚本读取 `SMOKE_BASE_URL` 与 `DEV_ADMIN_PASSWORD` 环境变量。

## 可选模型配置

不配置 LLM 时，助手和仪表盘给出有明确来源的规则统计回答；异常详情显示“规则分析”。要启用模型分析，设置 `LLM_API_KEY`、`LLM_MODEL`，以及可选的 `LLM_BASE_URL`（默认 OpenAI 兼容 Chat Completions URL）。新导入异常会在请求完成后由进程内后台任务调用模型；异常详情也可手动点击“更新分析”。

`LLM_INPUT_COST_PER_MILLION` 和 `LLM_OUTPUT_COST_PER_MILLION` 用于按返回的 token 用量估算成本。聊天消息和 `ai_usage` 表记录提供者、模型、token 与成本；费率为 0 时成本值只是未配置费率的占位值。仪表盘模型摘要缓存 5 分钟到 Redis。

知识库使用 pgvector 存储 1,536 维向量。离线默认嵌入算法为确定性字符 n-gram 哈希，适合演示关键词邻近检索，不等同于生产语义嵌入。

## API 与安全边界

所有 API 以 `/api/v1` 开头。登录接口为 `POST /auth/login`，请求体含 `tenant_code`、`username`、`password`；受保护接口使用 Bearer JWT。主要模块位于 `/connectors`、`/shipments`、`/exceptions`、`/ai`、`/dashboard`、`/knowledge`。Webhook 使用 `/webhooks/{connector_id}` 与 `X-Webhook-Secret`，无需用户 JWT。

连接器、映射、运单、轨迹、异常、会话、消息及知识查询均限定 `tenant_id`。AI 工具只能调用服务层，不接收 SQL。连接器密钥不会在 API 响应中返回。REST 连接器校验 URL、拒绝重定向并限制响应大小；开发环境允许模拟服务地址。上传文件限制为 5 MB，导入上限 5,000 行。

## 本地开发与验证

需要 Python 3.12+、Node.js 22+。可先运行 `docker compose up -d postgres redis`。在 `apps/server` 创建虚拟环境，安装 `pip install -e '.[test]'`，把 `.env.example` 复制到 `apps/server/.env`，将数据库地址改为 `localhost:5433`、Redis 主机名改为 `localhost`，然后运行：

```sh
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8001
pytest
```

在 `apps/web` 运行 `npm ci`、`npm run dev` 和 `npm run build`。本地 Vite 代理默认连接 8000；若后端监听 8001，设置 `VITE_API_PROXY_TARGET=http://localhost:8001`。Docker 配置可用 `docker compose config --quiet` 检查。

## 当前限制

- 开发 Compose 暴露数据库和 Redis 端口；生产环境需要独立的网络、密钥管理、HTTPS、审计、登录限流和令牌撤销策略。
- 模型异常分析的进程内后台任务不会在进程故障后自动重试；生产可替换为持久队列。没有模型密钥时不会产生模型生成内容。
- 知识库离线向量适合演示，复杂语义检索需要真实嵌入提供者及重建索引。
- 文件导入支持 JSON、CSV、XLSX；知识库支持 TXT、PDF、DOCX、XLSX。扫描版 PDF 不执行 OCR。当前权限结构只有 `admin`/`member` 角色字段，没有完整用户管理和细粒度 RBAC。
