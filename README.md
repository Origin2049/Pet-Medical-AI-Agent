# Pet-Medical-AI-Agent

基于 LangGraph 构建的 **毛球医生（FluffDoc）**—— 一位 AI 宠物家庭医生。项目采用 LangChain + LangGraph 智能体架构，提供专业的宠物健康咨询服务，支持本地运行与 HTTP 服务部署。

## 项目定位

Pet-Medical-AI-Agent 是一个面向宠物主人的 AI 健康顾问应用，能够：

- 采集宠物基本信息（品种、年龄、性别、症状等）
- 基于知识库分析常见宠物健康问题
- 提供分级建议：居家观察 / 预约就诊 / 紧急就医
- 对中毒、窒息、大量出血等紧急情况即时引导急诊
- 通过滑动窗口对话管理维持多轮交互上下文

> **免责声明**：所有建议仅供参考，不替代专业兽医诊断。

## 项目架构

项目基于 **LangGraph Agent** 模式构建，核心流程如下：

```
用户请求 → FastAPI HTTP Server / 本地运行
              │
              ▼
       GraphService（主调度器）
              │
              ▼
    Agent Builder (agents/agent.py)
              │
        ┌─────┴─────┐
        │   LLM 模型  │  ← doubao-seed-2-0-lite
        │  系统提示词  │  ← 毛球医生角色设定
        └─────┬─────┘
              │
    ┌─────────┴─────────┐
    │   Checkpoint 存储  │  ← PostgresSaver / MemorySaver
    │   (memory_saver)   │
    └───────────────────┘
```

### 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| `agents` | `src/agents/agent.py` | Agent 构建工厂：加载 LLM 配置、组装系统提示词、绑定工具、接入 Checkpointer |
| `graphs` | `src/graphs/` | 留空扩展目录，用于未来多节点工作流定义 |
| `storage` | `src/storage/` | 数据持久层：PostgreSQL 数据库连接、会话 Checkpoint 存储、OR 模型定义 |
| `tools` | `src/tools/` | 工具集合目录，可扩展自定义工具（如知识库检索） |
| `main` | `src/main.py` | 主入口：FastAPI 服务生命周期、全部 HTTP 端点、本地运行模式 |

### storage 子模块

| 子模块 | 路径 | 说明 |
|--------|------|------|
| `database` | `src/storage/database/db.py` | PostgreSQL 连接池管理，支持自动重试（最多 20 秒），从 `PGDATABASE_URL` 环境变量或 Coze 平台密钥中心获取连接串 |
| `memory` | `src/storage/memory/memory_saver.py` | 会话记忆管理器：优先使用 `AsyncPostgresSaver`（持久化），数据库不可用时自动退化为 `MemorySaver`（内存缓存，不跨重启） |
| `shared` | `src/storage/database/shared/model.py` | SQLAlchemy ORM 基类定义 |

## 环境要求与依赖

| 要求 | 说明 |
|------|------|
| Python | >= 3.12 |
| 包管理器 | [uv](https://github.com/astral-sh/uv) |
| 数据库 | PostgreSQL（可选，无数据库时退化为内存模式） |

### 核心依赖

- **LangChain 全家桶**：`langchain==1.0.3` / `langgraph==1.0.2` / `langchain-openai==1.0.1`
- **Web 框架**：`fastapi>=0.121` / `uvicorn>=0.38`
- **数据库**：`SQLAlchemy>=2.0` / `psycopg[binary]>=3.3` / `langgraph-checkpoint-postgres>=3.0`
- **文档处理**：`pypdf>=6.4` / `docx2python>=3.5` / `openpyxl>=3.1` / `python-pptx>=1.0`
- **Coze 平台集成**：`coze-coding-utils>=0.2.8` / `coze-workload-identity>=0.1.4`
- **其他**：`opencv-python>=4.12` / `pandas>=2.2` / `Pillow>=10.3` / `rich>=14`

完整依赖清单见 `pyproject.toml`。

## 安装与配置

### 1. 克隆项目

```bash
git clone <repo-url> && cd Pet-Medical-AI-Agent
```

### 2. 环境准备

设置工作空间路径：

```bash
export COZE_WORKSPACE_PATH=$(pwd)
```

### 3. 运行安装脚本

```bash
bash scripts/setup.sh
```

脚本会通过 `uv sync` 自动安装 `.venv` 中的所有依赖。若 `uv.lock` 已冻结则使用 `--frozen` 模式。生产部署模式下通过 `PIP_TARGET` 安装到指定目录。

### 4. 配置环境变量

本地开发时，运行 `load_env.sh` 从 Coze 平台拉取项目环境变量（包含 `PGDATABASE_URL`、`COZE_WORKLOAD_IDENTITY_API_KEY`、`COZE_INTEGRATION_MODEL_BASE_URL` 等）：

```bash
source scripts/load_env.sh
```

或手动设置关键环境变量：

```bash
export PGDATABASE_URL="postgresql://user:password@host:5432/dbname"
export COZE_WORKLOAD_IDENTITY_API_KEY="your-api-key"
export COZE_INTEGRATION_MODEL_BASE_URL="https://your-model-endpoint/v1"
```

### 5. Agent 配置

编辑 `config/agent_llm_config.json` 调整 Agent 行为：

```json
{
    "config": {
        "model": "doubao-seed-2-0-lite-260215",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_completion_tokens": 10000,
        "timeout": 600,
        "thinking": "disabled"
    },
    "sp": "...毛球医生系统提示词...",
    "tools": []
}
```

| 字段 | 说明 |
|------|------|
| `config.model` | LLM 模型名称 |
| `config.temperature` | 生成温度（0-1），越高越随机 |
| `config.timeout` | 请求超时（秒） |
| `config.thinking` | 思维链模式：`disabled` / `enabled` |
| `sp` | 系统提示词（System Prompt），定义毛球医生角色与行为 |
| `tools` | 绑定的工具列表（可扩展） |

## 运行方式

### HTTP 服务模式

启动 FastAPI HTTP 服务，提供完整的 REST API：

```bash
bash scripts/http_run.sh -p 5000
```

服务将在 `http://0.0.0.0:5000` 启动。可用端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/run` | POST | 同步执行 Agent，返回完整结果 |
| `/stream_run` | POST | SSE 流式执行，实时返回对话生成过程 |
| `/async_run` | POST | 异步任务提交，适用于长时间执行 |
| `/task/{task_id}` | GET | 查询异步任务状态与结果 |
| `/cancel/{run_id}` | POST | 取消正在执行的任务 |
| `/node_run/{node_id}` | POST | 单独运行工作流中的指定节点 |
| `/v1/chat/completions` | POST | OpenAI Chat Completions 兼容接口 |
| `/graph_parameter` | GET | 获取 Graph 输入/输出 Schema |
| `/health` | GET | 健康检查 |

### 本地运行模式

直接命令行运行，适合开发调试：

```bash
# 运行完整工作流
bash scripts/local_run.sh -m flow -i '{"text": "我的猫最近一直打喷嚏"}'

# 运行指定节点
bash scripts/local_run.sh -m node -n node_name -i '{"text": "测试"}'

# Agent 对话模式
bash scripts/local_run.sh -m agent
```

也可以直接用 Python 调用：

```bash
source .venv/bin/activate
python src/main.py -m flow -i '{"text": "你好"}'
python src/main.py -m http -p 5000
```

## 项目结构

```
Pet-Medical-AI-Agent/
├── .coze                          # Coze 平台配置文件
├── .gitignore                     # Git 忽略规则
├── pyproject.toml                 # 项目元数据与依赖声明
├── uv.lock                        # uv 锁定依赖版本
├── README.md                      # 本文件
│
├── config/
│   └── agent_llm_config.json      # Agent LLM 配置与系统提示词
│
├── scripts/
│   ├── setup.sh                   # 依赖安装脚本
│   ├── load_env.sh                # 环境变量加载入口
│   ├── load_env.py                # Coze 平台环境变量拉取
│   ├── http_run.sh                # HTTP 服务启动脚本
│   ├── local_run.sh               # 本地运行脚本
│   └── pack.sh                    # 依赖锁定打包脚本
│
└── src/
    ├── __init__.py
    ├── main.py                    # 主入口：FastAPI 服务 + 命令行解析
    │
    ├── agents/
    │   ├── __init__.py
    │   └── agent.py               # Agent 构建工厂（FluffDoc 毛球医生）
    │
    ├── graphs/
    │   └── __init__.py            # 工作流定义目录（预留扩展）
    │
    ├── tools/
    │   └── __init__.py            # 工具集合目录（预留扩展）
    │
    └── storage/
        ├── __init__.py
        ├── database/
        │   ├── __init__.py
        │   ├── db.py              # PostgreSQL 连接管理（带重试）
        │   └── shared/
        │       ├── __init__.py
        │       └── model.py       # SQLAlchemy ORM 基类
        └── memory/
            ├── __init__.py
            └── memory_saver.py    # Checkpoint 存储（Postgres/Memory 双模式）
```

## 关键设计

### 双模 Checkpoint 存储

会话记忆管理器 (`MemoryManager`) 实现了优雅降级策略：

1. 从环境变量获取 `PGDATABASE_URL` → 若成功，使用 `AsyncPostgresSaver`（持久化，生产环境推荐）
2. 若数据库不可用 → 自动退化为 `MemorySaver`（内存存储，进程重启后丢失）

此设计确保项目在无数据库的开发环境中也能开箱即用。

### 滑动窗口消息管理

Agent 使用滑动窗口策略保留最近 40 条消息（约 20 轮对话），通过自定义 `_windowed_messages` 函数实现，避免上下文窗口溢出。

### 多模式运行

`main.py` 支持四种运行模式：

- `http`：FastAPI HTTP 服务（生产/调试均可）
- `flow`：单次全工作流执行（同步）
- `node`：单节点调试执行
- `agent`：Agent 对话式交互

### OpenAI 兼容接口

`/v1/chat/completions` 端点提供与 OpenAI API 兼容的对话接口，可无缝集成到现有 OpenAI SDK 调用链路中。

## 扩展指南

### 添加新工具

在 `src/tools/` 下创建工具模块（如 `knowledge_search.py`），然后在 `config/agent_llm_config.json` 的 `tools` 数组中注册：

```json
"tools": ["tools.knowledge_search.search_pet_knowledge"]
```

### 升级为多节点工作流

在 `src/graphs/` 下定义 `StateGraph` 工作流，替换当前的单一 Agent 模式为多步工作流（如：信息采集 → 症状分析 → 风险评估 → 建议生成）。

### 扩展自定义模型

修改 `config/agent_llm_config.json` 中的 `model` 字段即可切换到其他兼容 OpenAI API 的模型。
