# LLM API Toolbox v1.5.0

一个本地运行的网页大模型接口工作台，通过统一后端调用 Mock、OpenAI、Anthropic 和 OpenAI-Compatible（预置 DeepSeek）Provider。

## 当前能力

- 中文单页对话界面、多轮上下文、流式与非流式回答。
- Provider/模型选择、system prompt、temperature、最大输出 token。
- 停止生成、清空、复制、token 用量和统一错误提示。
- 无任何密钥时可使用 Mock 完整运行。
- OpenAI Responses API、Anthropic Messages API 和 DeepSeek 兼容接口适配。
- Provider 密钥仅由后端读取。
- 顶部 Provider/模型选择框保持常驻，并提供“管理模型”入口，可在已有对话中随时调整配置。
- “管理模型”支持逐行增加/删除模型，并可使用尚未保存的 API Key、Base URL 和选定模型测试连接。
- 生成设置提供“允许联网搜索”开关；开启后会先检索公开网页结果，再交给当前模型回答。
- 弹窗配置仅保存在后端内存，后端重启自动清除；API 不会返回密钥内容。
- 本机 SQLite 会话历史：自动保存、恢复、搜索、重命名、删除和时间分组。
- ChatGPT/Claude 风格的浅色工作区，历史栏和消息区分别独立滚动。
- 前后端版本自动检测；旧后端会显示明确提示，不再表现为按钮无响应。
- OpenAPI 文档、离线 Adapter 契约测试、API/SSE 集成测试。

## 环境要求

本地运行：

- Python 3.12
- Node.js 22 或更高 LTS 版本
- npm 10+

容器运行：

- Docker Desktop 4+
- Docker Compose v2

## 从旧版本升级

不要同时混用新版前端和旧版后端，否则接口配置会显示版本不匹配。Windows 本地升级步骤：

1. 在旧版前端和后端终端分别按 `Ctrl+C`。
2. 解压 V1.5.0；如需保留永久密钥，在自己电脑上把旧版 `.env` 复制到新版根目录。
3. 在新版目录启动后端：

```powershell
cd backend
py -3.12 -m pip install -e .
py -3.12 -m uvicorn app.main:app --reload --port 8000
```

4. 新开一个 PowerShell，在新版目录启动前端：

```powershell
cd frontend
npm install
npm run dev
```

5. 访问 <http://localhost:8000/api/v1/meta>，应看到版本 `1.5.0`；随后打开 <http://localhost:3000>。

## 零密钥启动：本地命令

### 1. 准备配置

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS/Linux：

```bash
cp .env.example .env
```

所有 API key 保持为空即可。

### 2. 启动后端

Windows PowerShell：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

macOS/Linux：

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

打开 <http://localhost:8000/docs> 可查看接口文档。

### 3. 启动前端

在新的终端中：

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:3000>，默认选择 Mock Provider。

## 零密钥启动：Docker

首先复制 `.env.example` 为 `.env`，然后运行：

```bash
docker compose up --build
```

访问 <http://localhost:3000>。停止并移除容器：

```bash
docker compose down
```

Compose 默认只把 3000 和 8000 端口绑定到 `127.0.0.1`，局域网中的其他设备无法直接访问配置接口。

## 配置真实 Provider

### 方式一：在网页中配置（临时、推荐用于首次验证）

1. 启动前后端并打开 <http://localhost:3000>。
2. 点击左侧入口或顶部模型选择框旁的“管理模型”。
3. 选择 OpenAI、Anthropic 或 DeepSeek。
4. 粘贴 API Key；官方接口通常无需修改 Base URL。
5. 使用单选按钮指定一个模型，点击“测试连接”验证当前表单。
6. 测试成功后点击“保存配置”。如果当前模型仍存在，已有对话会继续使用它。

网页填写的密钥只发送到本机 FastAPI 并保存在进程内存中，不存入浏览器，也不会通过查询接口返回。关闭或重启后端后需要重新填写。

“测试连接”使用窗口中尚未保存的配置，执行一次最小非流式请求；它不会保存配置、创建会话或写入聊天记录，但这仍是一次真实模型调用，可能产生少量 API 费用。

## 实验性联网搜索

打开“生成设置”，启用“允许联网搜索”。之后每次发送问题时，后端会先尝试从 Bing RSS 获取公开搜索结果，失败时自动尝试 DuckDuckGo HTML，再把最多五条标题、摘要和 URL 作为不可信外部资料交给当前模型。因此同一个开关可用于 OpenAI、Anthropic 和 DeepSeek，不需要另外注册搜索 API Key。

当前实现只读取搜索结果的标题、摘要和来源地址，不会继续抓取任意网页正文。这样可以保持实现轻量，并减少 SSRF 和网页提示注入风险。它属于实验性能力：公开搜索入口可能因为地区网络、验证码或服务方页面调整而不可用。程序会显示“联网搜索暂时不可用”，不会在没有搜索结果时假装已经联网。

联网会增加响应时间，搜索摘要也会增加模型输入 token。开关会随会话保存在本机 SQLite 中；API Key 仍然不会写入数据库。

可在 `.env` 调整搜索行为：

```dotenv
WEB_SEARCH_TIMEOUT_SECONDS=8
WEB_SEARCH_MAX_RESULTS=5
```

## 会话历史

首次发送消息时会自动创建会话。用户消息、完整回复、停止生成后的部分回复和错误状态都会写入本机 SQLite 数据库。默认位置：

```text
data/llm_toolbox.db
```

会话可在左侧按时间查看、搜索、重新打开、重命名或删除。数据库不保存任何 API Key。旧版没有持久化功能，因此升级前已经关闭的页面会话无法恢复。

如需修改位置，可在 `.env` 中设置：

```dotenv
CONVERSATION_DB_PATH=../data/llm_toolbox.db
```

### 方式二：通过 `.env` 永久配置

在根目录 `.env` 中填写对应密钥：

```dotenv
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
```

如需兼容网关或代理地址，可配置：

```dotenv
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

重启后端后，`/api/v1/providers` 会把相应 Provider 标记为 `available`。密钥未配置时 Provider 仍会出现在界面，但不可发送请求。

模型列表也是配置项，可使用逗号分隔：

```dotenv
OPENAI_MODELS=gpt-5-mini
ANTHROPIC_MODELS=claude-sonnet-4-5
DEEPSEEK_MODELS=deepseek-flash,deepseek-v4-pro
```

模型名称和权限由账号及厂商当前配置决定。如在线请求提示模型不存在，请根据对应厂商控制台更新变量，无需修改代码。

## 运行测试

后端：

```bash
cd backend
pytest
```

前端单元测试、类型检查和构建：

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

首次运行浏览器 E2E 前安装 Chromium：

```bash
npx playwright install chromium
npm run test:e2e
```

E2E 使用浏览器路由模拟后端，不需要真实 Provider 或密钥。它只在需要执行浏览器自动化测试时安装 Chromium；正常使用本应用不需要额外安装浏览器。

## API 示例

非流式：

```bash
curl http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","model":"mock-echo-v1","messages":[{"role":"user","content":"你好"}],"parameters":{"temperature":0.7,"max_output_tokens":128}}'
```

流式：

```bash
curl -N http://localhost:8000/api/v1/chat/completions/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock","model":"mock-echo-v1","messages":[{"role":"user","content":"你好"}],"parameters":{"temperature":0.7,"max_output_tokens":128}}'
```

## 在线验证状态

- OpenAI/Anthropic Adapter 的请求、响应和流式转换通过离线契约测试后，可标记为 `implemented`。
- 只有使用对应厂商真实密钥完成 smoke test，才能标记为 `live-verified`。
- 当前无密钥时，在线测试状态应记录为 `NOT_RUN`，不代表失败。
- DeepSeek 调用成功只能验证 OpenAI-Compatible 通路，不能替代 OpenAI 在线验证。

## 安全说明

- 不要把 `.env`、密钥截图或带 Authorization header 的日志提交到仓库。
- 前端不会读取或接收 Provider API key。
- 配置写入接口仅面向 localhost 使用；网页配置不会持久化。
- 后端默认不记录 prompt 和 completion 正文。
- 当前版本仅面向本机使用。若部署到公网，必须增加身份认证、用户级限流、HTTPS 和更严格的审计。

## 项目文档

- [ARCHITECTURE.md](ARCHITECTURE.md)：架构、模块依赖和扩展方式。
- [ACCEPTANCE.md](ACCEPTANCE.md)：P0 验收清单与在线条件项。
