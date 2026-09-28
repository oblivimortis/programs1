# AnythingLLM MCP Server

基于 Model Context Protocol(MCP,`2026-07-28` 版本,HTTP 传输)的 Python MCP Server,
把本机 AnythingLLM 的**单个工作区**暴露为 AI 工具,用于对工作区内容进行检索问答(RAG)。

- 传输协议:Streamable HTTP(`http://127.0.0.1:8000/mcp`),不用 stdio
- 工具:`ask_workspace(question)` —— 向配置的唯一工作区提问,返回 AnythingLLM 的回答
- 底层调用:AnythingLLM 的 `POST /api/v1/workspace/{slug}/chat`,`mode=query`

## 目录结构

```
.
├── server.py          # MCP Server 入口(单文件,MVP)
├── opencode.json      # opencode 项目级 MCP 配置
├── serve.py           # 上传网页的静态服务(8001,含文档正文预览代理)
├── uploader/
│   └── index.html     # 文档工作台网页(上传/预览/查阅/重嵌入/问答)
├── .env               # 本地配置(BASE_URL / API_KEY / WORKSPACE_SLUG)
├── .env.example       # 配置模板
├── requirements.txt   # Python 依赖
└── README.md
```

## 环境要求

- Windows + Python 3.13(可用 `py` 启动)
- 本机已运行 AnythingLLM(默认 `http://localhost:3001`)
- 已在 AnythingLLM「开发者 API」创建 API Key

## 初始化

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# 复制并填写配置(API Key、工作区 slug 可在 AnythingLLM 的 API 文档/工作区设置中获取)
Copy-Item .env.example .env
```

`.env` 内容:

```
ANYTHING_LLM_BASE_URL=http://localhost:3001
ANYTHING_LLM_API_KEY=你的开发API Key
ANYTHING_LLM_WORKSPACE_SLUG=工作区slug
```

> 工作区 slug 也可通过 API 获取:`curl http://localhost:3001/api/v1/workspaces -H "Authorization: Bearer <你的Key>"`

## 启动 / 停止

启动(前台,按 `Ctrl+C` 停止):

```powershell
.\.venv\Scripts\python server.py
```

停止:

- 前台运行时按 `Ctrl+C`;
- 或先查端口再结束进程:PowerShell 中执行
  `Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`;
- 修改 `server.py` 后需重启服务使其生效。

验证已启动:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

## 接入 opencode(项目级 MCP)

项目根目录已配置 `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "anythingllm": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/mcp",
      "enabled": true
    }
  }
}
```

- **前提**:MCP Server 必须先启动(见上),否则 opencode 连不上该工具。
- 修改配置后**重启 opencode**(或重新打开项目)才会加载 MCP Server。
- 查看 MCP 状态:`opencode mcp list`。
- 之后在对话中即可让 AI 使用 `anythingllm_ask_workspace` 工具。

## 协议说明(双兼容)

`server.py` 使用官方 `mcp` SDK 的 Streamable HTTP,对请求按 `MCP-Protocol-Version` 请求头自动路由:

- 带 `MCP-Protocol-Version: 2026-07-28` 的请求 → 无会话、无 `initialize` 的现代路径(`Mcp-Method`/`Mcp-Name` 头);
- 无该头 / 旧握手版本(`2024-11-05`~`2025-11-25` 等)的请求 → `initialize` + `Mcp-Session-Id` 会话路径(兼容旧客户端)。

## 手动验证

现代 `2026-07-28` 路径(`tools/list`,需带协议头):

```powershell
curl.exe -X POST http://127.0.0.1:8000/mcp `
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" `
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" `
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{}}}}"
```

`tools/call`(调用工具):

```powershell
curl.exe -X POST http://127.0.0.1:8000/mcp `
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/call" -H "Mcp-Name: ask_workspace" `
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" `
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"ask_workspace\",\"arguments\":{\"question\":\"你有哪些知识?\"},\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{}}}}"
```

## 文档工作台网页(uploader)

打开网页上传文件,把文件解析并**向量化嵌入**到 AnythingLLM 的第一个工作区(供 RAG 问答使用)。页面功能:

- **📂 添加文件**:选择文件夹后,左侧以**树状结构**展示目录,点击文件夹可展开/折叠,点击文件在中间**预览区**展示内容,并可「📤 上传并嵌入」;
- 中间上半部分为**文件预览区**,下半部分为**历史浏览区**(记录本次与上次预览过的文件,点击可再次打开,支持清空);
- **📚 查阅文件**:列出已上传文档(含"已嵌入/未嵌入"状态),点击条目可预览文档正文,并可 **🔄 重新嵌入**;
- **💬 知识问答**:基于工作区已嵌入内容直接 RAG 问答;
- 右侧**操作日志**记录上传/查阅/重嵌入等事件。

```powershell
# 启动服务(端口 8001)
.\.venv\Scripts\python serve.py

# 浏览器打开
start http://127.0.0.1:8001
```

页面会自动取第一个工作区,`POST /api/v1/document/upload`(multipart,`addToWorkspaces=首个工作区slug`,带 Bearer Key)。API Key 写在该文件顶部的 `KEY` 常量中,更换时同步修改。

同样适用 `Get-NetTCPConnection -LocalPort 8001 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` 停止。

## 常见问题

- **RAG 回答超时/无响应(日志报 `model requires more system memory`)**:机器空闲内存不足,模型(如 `qwen3.5:4b` 需 ~1.8 GiB)无法加载。关闭 QQ/Edge/Steam 等大内存程序后重试,或换更小的模型。
- **回答“没有相关知识”**:工作区暂无已嵌入文档,先在 AnythingLLM 中向该工作区上传并嵌入文档。
- **鉴权失败(403/401)**:检查 `.env` 中的 `ANYTHING_LLM_API_KEY`。
- **端口被占用**:8000 被其它程序占用时,修改 `server.py` 末尾的 `port` 并同步更新 `opencode.json` 的 `url`。