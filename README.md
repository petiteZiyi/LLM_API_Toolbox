# LLM API Toolbox v1.5.0

LLM API Toolbox 是一个本地运行的网页大模型接口工作台。它通过统一后端连接 Mock、OpenAI、Anthropic 和 DeepSeek 等模型服务，其中 DeepSeek 通过 OpenAI-Compatible 接口适配器接入。

项目提供多轮对话、流式输出、模型管理、会话历史和实验性联网搜索，并允许用户使用自己购买的 API Key。

## 当前能力

1. **统一模型调用**：在同一个网页中使用 Mock、OpenAI、Anthropic 和 DeepSeek，后端负责屏蔽不同厂商的接口差异。
2. **多轮对话**：支持连续上下文、流式与非流式回复、停止生成、清空对话、复制回答和 token 用量显示。
3. **模型与生成设置**：支持切换模型，并调整 system prompt、temperature 和最大输出 token。
4. **运行中管理模型**：对话开始前后均可打开“管理模型”，填写 API Key、Base URL 和模型名称，并逐行添加或删除模型。
5. **连接测试**：可使用尚未保存的 API Key、Base URL 和选定模型执行最小请求，区分认证、余额、限流、超时和上游错误。
6. **实验性联网搜索**：可在生成设置中开启联网搜索，先获取公开搜索摘要和来源 URL，再交给当前模型回答。
7. **会话历史**：使用本机 SQLite 自动保存消息和生成设置，支持恢复、搜索、重命名、删除和时间分组。
8. **本地密钥处理**：网页填写的 API Key 只保存在后端运行内存中，不写入浏览器或会话数据库；也可通过本机 `.env` 长期配置。
9. **零密钥运行**：没有任何真实 API Key 时仍可使用 Mock 完成界面、流式输出和会话功能验证。
10. **简洁网页界面**：采用浅色双栏工作区，历史栏与消息区域独立滚动，并可隐藏历史栏。
11. **兼容性检查**：前端会检查后端 API 兼容版本，并在服务未连接或版本不匹配时显示明确提示。
12. **开发与验收支持**：提供 OpenAPI 文档、离线 Adapter 契约测试、API/SSE 集成测试和前端单元测试。

## 项目结构

```text
LLM_API_Toolbox_v1.5.0/
├── backend/            # FastAPI 后端和 Provider Adapter
├── frontend/           # Next.js 网页前端
├── data/               # SQLite 会话数据库
├── start.sh            # Deepin/UOS 展示环境一键启动脚本
├── docker-compose.yml  # Docker Compose 配置
├── .env.example        # 环境变量示例
├── USER_GUIDE.md       # 用户使用手册
├── ARCHITECTURE.md     # 架构文档
└── ACCEPTANCE.md       # 验收清单
```

## 环境要求

### 本地运行

- Python 3.12
- Node.js 22 或更高 LTS 版本
- npm 10+

### 容器运行

- Docker Desktop 4+ 或 Linux Docker Engine
- Docker Compose v2

## 一键启动

项目根目录中的 `start.sh` 用于已完成环境准备的 Deepin/UOS 展示设备。它适合通过桌面图标双击启动，也可以由终端或桌面启动器调用。

脚本会自动完成以下操作：

1. 检查脚本中配置的项目目录是否存在。
2. 检查前端 3000 端口和后端 8000 端口是否已经运行。
3. 使用现有的 `backend/.venv` 启动 FastAPI 后端。
4. 使用现有的 `frontend/node_modules` 启动 Next.js 前端。
5. 在后台保持两个服务运行，最长等待 90 秒。
6. 服务就绪后自动打开 <http://localhost:3000>。
7. 如果服务已经运行，则只打开浏览器，不会重复启动。

### 使用前提

`start.sh` 不负责安装 Python、Node.js 或项目依赖。使用前需要确认：

- 脚本中的 `PROJECT_ROOT` 和 `PROJ` 与实际部署目录一致；
- `backend/.venv` 已创建并安装后端依赖；
- `frontend/node_modules` 已安装前端依赖；
- 系统提供 Bash、`ss`、`curl` 和 `xdg-open`；
- 3000 和 8000 端口未被其他程序占用。

脚本面向本机展示，前后端都监听 `127.0.0.1`，不会直接开放给局域网中的其他设备。

### 日志与问题排查

脚本会在其配置的项目根目录下创建 `logs` 目录：

```text
logs/
├── launcher.log
├── backend.log
└── frontend.log
```

- `launcher.log`：启动流程、目录检查和等待结果；
- `backend.log`：FastAPI 后端日志；
- `frontend.log`：Next.js 前端日志。

如果 90 秒后仍未自动打开网页，请先查看以上日志。完整的手动启动方式和故障排查步骤见 [USER_GUIDE.md](USER_GUIDE.md)。

## Docker 启动

在项目根目录复制环境变量示例：

```bash
cp .env.example .env
```

启动：

```bash
docker compose up --build
```

访问 <http://localhost:3000>。停止并移除容器：

```bash
docker compose down
```

Compose 默认只把 3000 和 8000 端口绑定到 `127.0.0.1`，局域网中的其他设备无法直接访问配置接口。

## 连接大模型 API

本项目将 OpenAI、Anthropic、DeepSeek 等提供模型 API 的服务统称为“模型服务（Provider）”。连接大模型 API，就是配置服务商、API Key、Base URL 和模型名称，让工具从 Mock 测试服务切换到真实模型。

### 在网页中临时配置

1. 启动应用并打开 <http://localhost:3000>。
2. 点击顶部模型选择框旁的齿轮和“管理模型”。
3. 选择 OpenAI、Anthropic 或 DeepSeek。
4. 填写 API Key，并检查 Base URL。
5. 添加模型名称，并选中一个模型进行“测试连接”。
6. 测试成功后点击“保存配置”。

测试连接会执行一次最小非流式请求，可能产生少量 API 费用，但不会创建会话或保存当前表单。

网页填写的密钥只发送到本机 FastAPI 并保存在后端运行内存中，不存入浏览器，也不会通过配置查询接口返回。关闭或重启后端后，需要重新填写。

### 常用官方接口

| 模型服务 | Base URL | 模型示例 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | 以账号控制台实际可用模型为准 |
| Anthropic | `https://api.anthropic.com` | 以账号控制台实际可用模型为准 |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat`、`deepseek-reasoner` |

DeepSeek 使用 OpenAI-Compatible 请求格式，但在本工具中应直接选择预置的 `DeepSeek` 模型服务。

### 通过 `.env` 长期配置

在项目根目录复制 `.env.example` 为 `.env`，填写对应密钥：

```dotenv
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
```

如需使用官方接口以外的兼容网关，可调整 Base URL：

```dotenv
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

模型列表使用英文逗号分隔：

```dotenv
OPENAI_MODELS=gpt-5-mini
ANTHROPIC_MODELS=claude-sonnet-4-5
DEEPSEEK_MODELS=deepseek-chat,deepseek-reasoner
```

模型名称和访问权限由账号及服务商当前配置决定。修改 `.env` 后需要重启后端。

## 实验性联网搜索

打开“生成设置”，启用“允许联网搜索”。之后每次发送问题时，后端会优先从 Bing RSS 获取公开搜索结果，失败时尝试 DuckDuckGo，再把最多五条标题、摘要和 URL 作为不可信外部资料交给当前模型。

该功能可用于 OpenAI、Anthropic 和 DeepSeek，不需要额外申请搜索 API Key。

当前实现只读取搜索结果的标题、摘要和来源地址，不会继续抓取网页正文。公开搜索入口可能因为地区网络、验证码或服务方页面调整而不可用。搜索失败时，程序会显示“联网搜索暂时不可用”，不会在没有搜索结果时假装已经联网。

联网搜索会增加响应时间和模型输入 token。可以在 `.env` 调整：

```dotenv
WEB_SEARCH_TIMEOUT_SECONDS=8
WEB_SEARCH_MAX_RESULTS=5
```

## 会话历史

首次发送消息时，系统会自动创建会话。用户消息、模型回复、停止生成后的部分回复和错误状态都会写入本机 SQLite 数据库。

默认位置：

```text
data/llm_toolbox.db
```

会话可在左侧按时间查看、搜索、重新打开、重命名或删除。数据库保存消息和生成设置，但不保存 API Key。

如需修改数据库位置，可在 `.env` 设置：

```dotenv
CONVERSATION_DB_PATH=../data/llm_toolbox.db
```

## 运行测试

后端：

```bash
cd backend
pytest
```

前端：

```bash
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

首次执行浏览器 E2E 前需要安装 Chromium：

```bash
npx playwright install chromium
npm run test:e2e
```

E2E 使用浏览器路由模拟后端，不需要真实模型服务或 API Key。正常使用本应用不需要安装 Playwright 浏览器组件。

## API 示例

后端启动后，可以访问 <http://localhost:8000/docs> 查看完整 OpenAPI 文档。

非流式请求：

```bash
curl http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","model":"mock-echo-v1","messages":[{"role":"user","content":"你好"}],"parameters":{"temperature":0.7,"max_output_tokens":128}}'
```

流式请求：

```bash
curl -N http://localhost:8000/api/v1/chat/completions/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","model":"mock-echo-v1","messages":[{"role":"user","content":"你好"}],"parameters":{"temperature":0.7,"max_output_tokens":128}}'
```

## 验证状态说明

- OpenAI 和 Anthropic Adapter 通过离线请求、响应与流式转换契约测试后，可标记为 `implemented`。
- 只有使用相应服务商的真实密钥完成 smoke test，才能标记为 `live-verified`。
- 没有真实密钥时，在线验证记录为 `NOT_RUN`，不代表功能失败。
- DeepSeek 调用成功只能验证 OpenAI-Compatible 通路，不能替代 OpenAI 在线验证。

## 安全说明

- 不要把 `.env`、API Key、密钥截图、数据库或带 Authorization header 的日志提交到 Git。
- 前端不会读取或接收模型服务 API Key。
- 网页配置保存在后端运行内存中，重启后端后清除。
- 后端默认不记录 prompt 和 completion 正文。
- 联网搜索会把当前问题发送到公开搜索服务。
- 当前版本面向本机使用；部署到公网前必须增加身份认证、用户级限流、HTTPS、权限隔离和安全审计。

## 项目文档

- [USER_GUIDE.md](USER_GUIDE.md)：安装、配置、使用、备份和故障排查。
- [ARCHITECTURE.md](ARCHITECTURE.md)：架构、模块依赖和扩展方式。
- [ACCEPTANCE.md](ACCEPTANCE.md)：P0 验收清单与验证状态。
