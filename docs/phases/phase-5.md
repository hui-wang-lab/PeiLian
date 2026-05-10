# Phase 5 — Web UI + 报告

> 状态：计划阶段（已评审修订，待用户审阅本次修订后进入实现）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-4.md`](phase-4.md) ✅

---

## P5 目标

**把陪练从 CLI 搬进浏览器**——代理人打开网页选 persona、打字对话、结束后看到可视化报告（雷达图 + 逐句标注 + 合规扫描）。后端 API 与前端 UI 纵切交付，首次产出可演示的可视化交付物。

---

## 用户故事

### 业务侧
```
作为一名代理人，
我希望  在浏览器里完成一次陪练，而不是在终端里敲命令行，
以便  我能更自然地专注于对话本身，不被技术门槛分心。
```

```
作为一名培训主管，
我希望  陪练结束后能看到一张直观的雷达图和逐句标注，
以便  快速定位代理人弱项，而不需要阅读纯文本评估报告。
```

### 开发侧
```
作为开发者，
我希望  后端 API 与前端 UI 清晰分离，
以便  未来替换前端框架或接入移动端时不需要重写后端逻辑。
```

---

## 框架选型讨论

### 后端：FastAPI

| 候选 | 优势 | 劣势 | 结论 |
|---|---|---|---|
| **FastAPI** ✅ | 自动生成 OpenAPI 文档；类型注解与 Pydantic 模型天然适配现有 dataclass；同步路由可自然包住现有 `Dialogue.send_user()`；未来接入 async / streaming 空间充足；社区活跃 | 多一个 `uvicorn` 依赖 | **推荐** |
| Flask | 成熟稳定 | 同步阻塞模型，对话场景需额外处理长连接；无自动 OpenAPI 文档 | 逊于 FastAPI |
| Django | 全功能 | 重型框架，ORM / template / admin 全家桶与本项目无关；违背 CLAUDE.md 依赖审慎原则 | 排除 |

**选择 FastAPI 的核心理由**：

1. **与现有 Python 栈零摩擦**：`Dialogue` / `Persona` / `JudgeResult` 全部是 frozen dataclass，可由 FastAPI / Pydantic 序列化；本阶段用独立 Pydantic v2 模型镜像 P0–P4 dataclass（详见 §3 与文件清单第 8 项），避免 `frozenset`（如 `match_mandatory_categories` 返回值）/ 嵌套 `tuple[Issue, ...]` 等类型在 OpenAPI schema 上的边界差异，并为未来字段调整提供契约缓冲
2. **兼容现有同步对话引擎**：P4 的 `Dialogue.send_user()` 当前是同步 OpenAI client 调用；P5 路由优先用普通 `def` handler 交给 FastAPI 线程池执行，避免在 `async def` 中直接阻塞 event loop
3. **自动 OpenAPI 文档**：前端开发者（或未来移动端）可以直接看 `/docs` 对接，不需要额外维护 API 文档
4. **演进空间清晰**：若后续要做打字机效果或更强实时体验，可在不重写业务 API 的前提下追加 SSE / WebSocket

### 前端：轻量 HTML/JS + ECharts

| 候选 | 优势 | 劣势 | 结论 |
|---|---|---|---|
| **轻量 HTML/JS + ECharts** ✅ | 零 Node.js 依赖；FastAPI 静态文件托管；ECharts 雷达图开箱即用；vendor 自托管无需构建步骤；完全符合 CLAUDE.md 依赖审慎原则 | 交互复杂度较高时手写 JS 成本上升；无热更新 / 组件化 | **推荐** |
| Streamlit | 纯 Python 开发最快；内置 chat 组件 | 重型依赖（~150 个子依赖）；前后端耦合无法分离；自定义 UI 受限；Chat 交互模型与真实陪练场景有差距（全页刷新机制）；违背依赖审慎原则 | 排除 |
| Next.js / React | 组件化、生态丰富、专业前端体验 | 引入 Node.js 构建链；TypeScript / JSX 增加技术栈复杂度；部署需要两套服务 | P5 不推荐；若 P7+ 需要专业前端体验再迁移 |
| Gradio | ML demo 快速原型 | 与 Streamlit 类似的前后端耦合问题；定制化能力弱 | 排除 |

**选择轻量 HTML/JS 的核心理由**：

1. **依赖审慎**：不需要 `npm install`、不需要构建步骤、不需要 Node.js 运行时。前端以静态文件形式由 FastAPI 托管，`python -m peilian.server` 一条命令启动全部服务
2. **ECharts 是雷达图最佳选择**：五维雷达图（专业度 / 共情度 / 逻辑结构 / 异议处理 + 合规分）是中文业务场景的标准可视化，ECharts 的雷达图配置比 Chart.js / D3.js 简洁得多；本阶段以 vendor 自托管方式引入（详见 §5），不依赖外网 CDN
3. **向后演进路径清晰**：若 P7+ 需要更复杂的前端交互（错题本、历史趋势图、管理员后台），可无缝迁移到 React / Next.js，后端 API 不需要改动

### 依赖清单与审慎论证

| 依赖 | 用途 | 为什么不能自己写 30 行替代 |
|---|---|---|
| `fastapi` | HTTP API 框架 | 自己写 async HTTP server 远超 30 行且不安全 |
| `uvicorn` | ASGI 服务器 | 生产级 ASGI server 无法 30 行替代 |
| `pydantic` | request/response schema | `fastapi>=0.110` 默认携带 Pydantic v2，本项目显式 `pydantic>=2` 以锁定 schema 行为，避免实现期被传递依赖回退到 v1 |

**测试说明**：`fastapi` 自带的测试客户端能力随依赖链安装，不在 `pyproject.toml` 中单独列依赖。

**不引入的依赖**：`sse-starlette` / `streamlit` / `gradio` / `next.js` / `react` / `webpack` / `vite` ——SSE 不进入 P5 硬验收；其余方案均不满足"不能自己写 30 行替代"测试，或引入了与项目 Python 栈不匹配的技术生态。

---

## 纵切范围

- **后端 API**（`src/peilian/server/`）：
  - 会话管理：创建陪练会话（选 persona + 难度）、获取会话状态
  - 对话接口：发送代理人消息、返回客户完整回复（同步响应）
  - 评估接口：结束对话后调用 P2 evaluate + P3 judge，返回结构化 `JudgeResult`
  - 报告接口：返回 JSON 格式的完整评估报告（含 `JudgeResult`、原始消息、逐句标注，前端消费）
  - 静态文件托管：前端 HTML/JS/CSS 由 FastAPI serve
- **前端 UI**（`src/peilian/server/static/`）：
  - 首页：选择 persona + 难度档 → 创建会话
  - 对话页：聊天气泡式交互，支持 /quit 结束对话
  - 报告页：
    - 五维雷达图（ECharts）：专业度 / 共情度 / 逻辑结构 / 异议处理 + 合规分
    - 逐句标注：每条代理人发言标注命中的 KYC 类别与合规红线
    - 合规扫描结果：违规条目高亮展示
- **测试**：API 端点测试（mock LLM）；前端功能不写自动化测试（人工验收）

---

## 建议目录结构（增量）

```
PeiLian/
├── src/peilian/
│   ├── server/                         # 新增：Web 服务
│   │   ├── __init__.py
│   │   ├── app.py                      # FastAPI app 工厂 + 静态文件挂载 + 生命周期（不挂 CORS）
│   │   ├── __main__.py                 # 支持 python -m peilian.server，argparse 暴露 --host/--port/--reload
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── session.py              # 会话 CRUD：创建 / 获取 / 删除
│   │   │   ├── chat.py                 # 对话：发送消息（同步响应，持 session lock）
│   │   │   ├── report.py               # 报告：获取 ReportResponse（持 session lock + 缓存）
│   │   │   └── personas.py             # GET /api/personas（yaml.safe_load 直读，不污染注册表）
│   │   ├── schemas.py                  # Pydantic v2 模型 + 各模型 from_dataclass classmethod
│   │   ├── static/                     # 前端静态文件
│   │   │   ├── index.html              # 首页：选 persona + 难度
│   │   │   ├── chat.html               # 对话页
│   │   │   ├── report.html             # 报告页
│   │   │   ├── css/
│   │   │   │   └── style.css
│   │   │   ├── js/
│   │   │   │   ├── chat.js             # 对话交互逻辑
│   │   │   │   └── report.js           # 报告页：ECharts 雷达图 + 逐句标注渲染
│   │   │   └── vendor/
│   │   │       └── echarts.min.js      # vendor 自托管，实现阶段下载入仓（约 1MB）
│   │   └── session_store.py            # 内存会话存储（含 per-session lock + cached_report + status）
│   ├── dialogue.py                     # 不修改（P4 产物，直接消费）
│   ├── judge.py                        # 不修改（P3 产物，直接消费）
│   └── ...
├── pyproject.toml                      # 修改：dependencies 增加 fastapi / uvicorn / pydantic>=2
└── tests/
    └── test_server.py                  # 新增：API 端点测试（mock LLM）+ e2e 集成测试
```

---

## 计划创建/修改的文件

| # | 文件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `src/peilian/server/__init__.py` | 新增 | 包初始化 |
| 2 | `src/peilian/server/app.py` | 新增 | FastAPI app 工厂：创建 app、挂载路由、静态文件、生命周期；**不挂 CORS middleware**（详见 §1a） |
| 3 | `src/peilian/server/__main__.py` | 新增 | `python -m peilian.server` 入口；argparse 暴露 `--host`（默认 `127.0.0.1`）/ `--port`（默认 `8000`）/ `--reload`（默认关闭），启动 uvicorn |
| 4 | `src/peilian/server/routes/__init__.py` | 新增 | 路由包初始化 |
| 5 | `src/peilian/server/routes/session.py` | 新增 | `POST /api/sessions`（创建会话）、`GET /api/sessions/{id}`（获取状态）、`DELETE /api/sessions/{id}`（删除） |
| 6 | `src/peilian/server/routes/chat.py` | 新增 | `POST /api/sessions/{id}/chat`（发送消息返回客户完整回复，调用前持 `SessionData.lock`，成功后置 `cached_report=None`） |
| 7 | `src/peilian/server/routes/report.py` | 新增 | `GET /api/sessions/{id}/report`（持 `SessionData.lock`，缓存命中直接返回；首次生成调用 P2+P3 评估，返回 `ReportResponse`：`compliance_score` + `judge_result` + `messages` + `annotations`，并将 `status` 置为 `completed`） |
| 8 | `src/peilian/server/routes/personas.py` | 新增 | `GET /api/personas`：复用 demo_p4 的 `yaml.safe_load` 模式直读 `personas/*.yaml`，**不**调用 `load_personas_from_dir`，避免污染 `_META_BY_PERSONA` weakref 注册表 |
| 9 | `src/peilian/server/schemas.py` | 新增 | Pydantic v2 模型 + 各模型 `from_dataclass(...)` classmethod：`CreateSessionRequest` / `SessionResponse` / `ChatRequest` / `ChatResponse` / `MessageResponse` / `AnnotationResponse` / `PersonaSummary` / `ReportResponse`（含顶层 `compliance_score: int`） |
| 10 | `src/peilian/server/session_store.py` | 新增 | 内存会话存储：`SessionData`（含 `Dialogue` + `persona_meta` + `status` + `cached_report` + per-session `Lock`）+ `SessionStore`（dict + `RLock` 仅保护 dict 自身） |
| 11 | `src/peilian/server/static/index.html` | 新增 | 首页：persona 列表 + 难度选择 + 创建会话 |
| 12 | `src/peilian/server/static/chat.html` | 新增 | 对话页：聊天气泡 + 输入框 + "结束对话"按钮 + 发送 loading 指示 |
| 13 | `src/peilian/server/static/report.html` | 新增 | 报告页：雷达图 + 逐句标注 + 合规扫描 + AI 客户行为诊断区 |
| 14 | `src/peilian/server/static/css/style.css` | 新增 | 全局样式 |
| 15 | `src/peilian/server/static/js/chat.js` | 新增 | 对话交互：fetch API 发消息、渲染气泡、loading 指示 |
| 16 | `src/peilian/server/static/js/report.js` | 新增 | 报告渲染：ECharts 雷达图（按 `dimension` 字段查找 score）、逐句标注、合规高亮、customer_report 区 |
| 17 | `src/peilian/server/static/vendor/echarts.min.js` | 新增 | ECharts 5 vendor 自托管（约 1MB，**实现阶段下载入仓**，不引外网 CDN） |
| 18 | `pyproject.toml` | 修改 | dependencies 增加 `fastapi>=0.110` / `uvicorn[standard]>=0.27` / `pydantic>=2` |
| 19 | `tests/test_server.py` | 新增 | API 端点测试（TestClient + mock LLM）+ 至少 1 个 e2e 集成测试（创建会话 → 发 3 条消息 → 取报告 全链路） |
| 20 | `README.md` / `docs/ROADMAP.md` | 修改 | 加 P5 demo 命令 + Web UI 说明；同步当前阶段细节 |

> **明确不做**：
> - 不修改 P0-P4 任何现有模块（dialogue / judge / observer / persona_factory / customer_state / state_summary / prompts / rules / report）
> - 不做用户认证 / 登录（P5 单用户本地运行）
> - 不做数据库持久化（会话纯内存，服务重启即清空）
> - 不做 SSE / WebSocket 流式通信（P5 用同步响应；流式体验留后续优化）
> - 不做对话历史持久化（与 P7 错题本一起做）
> - 不做多用户并发隔离（P5 单进程单用户）
> - 不做移动端适配（首期桌面浏览器）
> - 不做 i18n（中文界面）

---

## Demo 命令

```powershell
# 启动 Web 服务（默认监听 127.0.0.1:8000，仅本机可访问）
python -m peilian.server

# 显式指定 host / port / 热重载（开发场景）
python -m peilian.server --host 127.0.0.1 --port 8000          # 等价默认
python -m peilian.server --host 0.0.0.0 --port 8080 --reload   # 开放外网 + 调试

# 浏览器打开 http://localhost:8000 即进入陪练首页

# API 文档自动生成
# http://localhost:8000/docs

# 跑测试（P5 测试 mock LLM，不烧额度）
pytest
```

`__main__.py` 用 stdlib `argparse` 暴露 `--host`（默认 `127.0.0.1`）、`--port`（默认 `8000`）、`--reload`（默认关闭）三个参数，**不**引入额外依赖。

预期 demo 行为：

1. 终端运行 `python -m peilian.server`，输出 `Uvicorn running on http://localhost:8000`
2. 浏览器打开 → 看到首页，列出 `personas/` 目录下的所有客户画像
3. 选择 persona + 难度档 → 点击"开始陪练" → 跳转对话页
4. 在对话页输入消息 → 客户回复出现在气泡中
5. 点击"结束对话" → 跳转报告页
6. 报告页显示：五维雷达图（按 `dimension` 字段查找 score）+ 逐句标注（每条代理人发言标注命中类别，含 `agent_turn_number`）+ 合规扫描结果（按违规轮次去重，与 CLI 文本报告口径一致）+ AI 客户行为诊断区
7. 刷新报告页（再次 GET `/api/sessions/{id}/report`）：缓存命中，**不**触发 LLM 调用

---

## 验收 Checklist

**结构 / 文件**
- [ ] 上述 20 个新增/修改文件全部到位
- [ ] **未**修改 P0-P4 任何现有模块（`dialogue.py` / `judge.py` / `observer.py` / `persona_factory.py` / `customer_state.py` / `state_summary.py` / `prompts.py` / `rules.py` / `report.py` / `config.py` / `persona.py` / `scenario.py` / `conversations.py` / `judge_prompts.py`）
- [ ] **未**修改 P0-P4 demo 脚本
- [ ] **未**创建 P6+ 物料（RAG、错题本等）
- [ ] `pyproject.toml` 新增依赖仅 `fastapi` / `uvicorn` / `pydantic>=2`（符合依赖审慎原则）

**后端 API**
- [ ] `POST /api/sessions` 接收 persona + difficulty，返回 `session_id`；内存创建 `Dialogue` 实例
- [ ] `GET /api/sessions/{id}` 返回会话状态（persona 信息 + 对话轮次 + `status`）
- [ ] `POST /api/sessions/{id}/chat` 接收代理人消息，返回客户回复文本；持有 `SessionData.lock`；成功后将 `cached_report` 置为 `None`
- [ ] `GET /api/sessions/{id}/report` 持有 `SessionData.lock`；首次调用 `build_judge_result` 并写缓存，将 `status` 置为 `completed`；返回 `ReportResponse`：顶层 `compliance_score` + `judge_result` + `messages` + `annotations`
- [ ] `compliance_score` 按违规轮次（去重 `(turn_index, agent_turn_number)`）计算，与 `render_judge_result` 文本口径一致（#1）
- [ ] `annotations` 覆盖每条代理人发言，包含 `turn_index`、`agent_turn_number`、命中的 KYC `categories`、对应 `compliance_hits`（#7）
- [ ] `GET /api/sessions/{id}/report` 第二次调用命中缓存，**不**再触发 LLM；chat 成功后缓存失效（#6）
- [ ] `GET /api/personas` 列表端点返回 `personas/` 下所有 yaml 元数据，且**不**污染 `_META_BY_PERSONA` weakref 注册表（#9）
- [ ] 同一 session 在 chat / report 调用 `Dialogue.send_user` / `build_judge_result` 前必须持有 `SessionData.lock`；并发请求 `messages` 不错位（#3）
- [ ] `app.py` **不**挂载 CORS middleware；`__main__.py` 默认监听 `127.0.0.1`，`--host 0.0.0.0` 才放开（#4 + #10）
- [ ] `DELETE /api/sessions/{id}` 清理会话内存
- [ ] 所有 API 返回正确 HTTP 状态码（200 / 201 / 404 / 422 / 500）
- [ ] 不存在的 session_id 返回 404
- [ ] `/docs` 自动生成的 OpenAPI 文档可正常访问
- [ ] 静态文件（HTML/JS/CSS）由 FastAPI 正确 serve
- [ ] LLM 调用失败时 API 返回 502 + 错误信息（不暴露内部堆栈）

**前端 UI**
- [ ] 首页：persona 列表通过 `GET /api/personas` 加载
- [ ] 首页：难度档三选一（简单/中等/困难）
- [ ] 对话页：聊天气泡式交互，代理人消息在右、客户消息在左
- [ ] 对话页：输入框 + 发送按钮 + "结束对话"按钮
- [ ] 对话页：LLM 响应延迟时有 loading 指示，发送按钮在请求中禁用
- [ ] 报告页：五维雷达图正确渲染（专业度 / 共情度 / 逻辑结构 / 异议处理 / 合规分）
- [ ] 报告页：ECharts radar 按 `dimension` 字段查找 score，**不**按数组索引；合规分直接读顶层 `compliance_score`（#5 附属）
- [ ] 报告页：ECharts 从 `/static/vendor/echarts.min.js` 加载，**不**引用任何外网 CDN（#5）
- [ ] 报告页：逐句标注——每条代理人发言旁标注命中的 KYC 类别
- [ ] 报告页：合规扫描结果——违规条目红色高亮，显示命中关键词与规则标签
- [ ] 报告页：含独立"AI 客户行为诊断"区，展示 `customer_report.premature_disclosure_issues` / `inconsistency_issues`（即使两类 issues 都为空也显示"未发现客户行为异常"）（#8）
- [ ] 页面间导航流畅（首页 → 对话 → 报告 → 新建会话）

**集成**
- [ ] 端到端跑通：浏览器完成一次陪练（选 persona → 对话 → 看报告）
- [ ] Web 与 CLI 消费同一套 `Dialogue` / `PersonaMeta` / `CustomerState` 链路；同 persona + 难度档下状态约束与被动反应规则一致
- [ ] 报告数据与 CLI `render_judge_result` 输出一致（同一份对话的评分相同）
- [ ] 合规红线在报告中正确高亮

**测试**
- [ ] `tests/test_server.py`：所有 API 端点测试通过（TestClient + mock LLM）
- [ ] `tests/test_server.py`：至少 1 个 e2e 集成测试，mock LLM 跑通"创建会话 → 发 3 条消息 → 取报告"全链路；校验 `compliance_score` / `annotations` / `customer_report` 完整且自洽（#12）
- [ ] `pytest` 全量测试（含 P0-P5）通过；P0-P4 测试不受影响

**Git**
- [ ] 至少两个 commit（spec 修订 + 实现物料），message 第一行含 `Phase 5` 或 `P5`，且符合既有 `docs(PN): ...` / `feat(PN): ...` 风格（对齐 P0–P4 先例）
- [ ] 工作区干净

---

## 不在 P5 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| 用户认证 / 登录 / 权限 | 产品化阶段 |
| 数据库持久化（会话/报告） | P7 错题本阶段 |
| WebSocket 实时推送 | 按需优化 |
| 对话历史导出（PDF/Excel） | P7+ |
| 移动端响应式适配 | 产品化阶段 |
| 管理员后台 / 培训主管看板 | 产品化阶段 |
| 产品条款 RAG | **P6** |
| 错题本 / 弱项画像 / 自适应难度 | **P7** |
| 多用户并发隔离 | 产品化阶段 |
| 修改 CLAUDE.md | 本阶段无需改动宪法 |
| 修改 P0-P4 业务模块 | P5 只消费 P0-P4 产物，不修改 |

---

## 技术设计要点

### §1. API 设计

```
# 会话管理
POST   /api/sessions                    → { session_id, persona, difficulty }
GET    /api/sessions/{id}               → { session_id, persona, turn_count, status }
DELETE /api/sessions/{id}               → 204

# 对话
POST   /api/sessions/{id}/chat          → { response, turn_count }

# 报告
GET    /api/sessions/{id}/report        → { judge_result, messages, annotations }

# 元数据（独立 routes/personas.py）
GET    /api/personas                    → [ { id, name, age, occupation, hidden_concerns_labels, ... } ]

# 静态文件
GET    /                                → index.html
GET    /chat?session={id}               → chat.html
GET    /report?session={id}             → report.html
```

**设计原则**：
- 无状态 API：每个请求携带 `session_id`，服务端用内存 dict 维护 `Dialogue` 实例
- RESTful 语义：资源用名词，动作用 HTTP method
- 错误格式统一：`{ "detail": "错误描述" }`，与 FastAPI 默认格式一致

**`/api/personas` 实现约束**：复用 [`scripts/demo_p4.py`](../../scripts/demo_p4.py) `_list_personas` 的 `yaml.safe_load` 模式，**不**调用 [`load_personas_from_dir`](../../src/peilian/persona_factory.py)——后者会把所有 persona 注册进 `_META_BY_PERSONA` weakref 注册表，列表接口高频调用会污染注册表（虽然 weakref 最终会回收，但服务进程内可能积累）。

### §1a. 安全基线

- **默认监听 `127.0.0.1:8000`**：`__main__.py` 默认 host 为 `127.0.0.1`，外网访问需用户显式 `--host 0.0.0.0`。强监管行业默认 0.0.0.0 是反向冒烟
- **不挂载 CORS middleware**：P5 前后端同源（FastAPI 自己 serve 静态文件），不需要 CORS；挂载 `CORSMiddleware(allow_origins=["*"])` 反而是把接口对任意 origin 开放，是明确的安全风险
- **错误响应不暴露内部堆栈**：LLM 调用失败时返回 502 + 简短描述，详细堆栈写日志

### §2. 会话存储

```python
# src/peilian/server/session_store.py
@dataclass
class SessionData:
    dialogue: Dialogue
    persona: Persona
    persona_meta: PersonaMeta
    difficulty: str
    created_at: datetime
    status: str = "active"            # "active" | "completed"
    cached_report: ReportResponse | None = None  # §3a 报告响应缓存
    lock: Lock = field(default_factory=Lock)     # per-session 锁，详见下文

class SessionStore:
    """内存会话存储。单进程单用户场景，不做分布式。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = RLock()  # 仅保护 dict 本身的 create / get / delete

    def create(self, persona: Persona, persona_meta: PersonaMeta,
               difficulty: str, settings: Settings) -> str:
        session_id = uuid4().hex[:8]
        dialogue = Dialogue(persona, SAMPLE_SCENARIO, settings, persona_meta=persona_meta)
        self._sessions[session_id] = SessionData(...)
        return session_id

    def get(self, session_id: str) -> SessionData | None: ...
    def delete(self, session_id: str) -> bool: ...
```

**关键约束**：
- 内存存储，服务重启清空——P5 不做持久化
- **两层锁**：
  - `SessionStore._lock`（`threading.RLock`）只保护 `_sessions` dict 自身的 create / get / delete，粒度小、持有时间短
  - `SessionData.lock`（`threading.Lock`）per-session，chat / report 路由在调用 `Dialogue.send_user` / `build_judge_result` 前必须 `with session_data.lock:`——`Dialogue.send_user` 内部要 append messages、调 OpenAI、再 append、再写回 `messages[0]`，整段不是线程安全的，浏览器端用户连点会让 `messages` 与 system prompt 错位
  - 顶层 RLock 不下放到业务路由，避免长持锁阻塞其他 session 的请求
- session_id 用 8 位 hex，P5 单用户场景碰撞概率可忽略
- **会话状态**：`SessionData.status` 在创建时为 `active`；`GET /api/sessions/{id}/report` 成功后置为 `completed`，便于未来 P7 错题本阶段做"已完成会话"持久化与清理。**P5 不实现 TTL 自动清理与多用户隔离**（统一留到 P7）

### §3. 报告数据结构

报告 API 返回的 JSON 以 P3 `JudgeResult` 为核心，并内嵌前端渲染逐句标注所需的 `messages` 与 `annotations`，以及后端预算好的 `compliance_score`：

```json
{
  "compliance_score": 4,
  "judge_result": {
    "evaluation_report": {
      "total_categories": 6,
      "covered_categories": ["family_structure", "occupation"],
      "missed_categories": ["income", "existing_coverage", "future_planning", "health_status"],
      "compliance_hits": [
        {
          "turn_index": 5,
          "agent_turn_number": 3,
          "excerpt": "…保证收益…",
          "rule_id": "guarantee_return",
          "rule_label": "保证收益",
          "matched_keyword": "保证收益"
        }
      ]
    },
    "agent_report": {
      "scores": [
        { "dimension": "professionalism", "label": "专业度", "score": 4, "reasoning": "…" },
        { "dimension": "empathy", "label": "共情度", "score": 3, "reasoning": "…" },
        { "dimension": "structure", "label": "逻辑结构", "score": 4, "reasoning": "…" },
        { "dimension": "objection_handling", "label": "异议处理", "score": 2, "reasoning": "…" }
      ],
      "overall_comment": "…"
    },
    "customer_report": {
      "premature_disclosure_issues": [],
      "inconsistency_issues": [],
      "overall_comment": "…"
    }
  },
  "messages": [
    { "turn_index": 1, "role": "user", "content": "您好，先了解下您家里几口人？" }
  ],
  "annotations": [
    {
      "turn_index": 1,
      "agent_turn_number": 1,
      "categories": ["family_structure"],
      "compliance_hits": []
    }
  ]
}
```

**雷达图五维映射**：

| 雷达轴 | 数据来源 | 满分 |
|---|---|---|
| 专业度 | `agent_report.scores[?].score where dimension == "professionalism"` | 5 |
| 共情度 | `agent_report.scores[?].score where dimension == "empathy"` | 5 |
| 逻辑结构 | `agent_report.scores[?].score where dimension == "structure"` | 5 |
| 异议处理 | `agent_report.scores[?].score where dimension == "objection_handling"` | 5 |
| 合规分 | 顶层 `compliance_score`，由后端按下文公式预算 | 5 |

**合规分计算（后端唯一权威口径）**：

```
violation_turns = {(h.turn_index, h.agent_turn_number) for h in compliance_hits}
compliance_score = max(0, 5 - len(violation_turns))
```

按"违规轮次"去重而非"hit 条目数"——同一条代理人发言同时命中"保证收益"和"零风险"两条规则时算 1 处违规、扣 1 分，与 P2 [`report.py::_render_compliance_section`](../../src/peilian/report.py) 与 [`judge.py::_render_p2_summary`](../../src/peilian/judge.py) 渲染的"X 处违规"口径一致。

**前端不要自己重算合规分**：直接读取 ReportResponse 顶层的 `compliance_score`，避免与文本报告对不上。

**customer_report 用途**：`judge_result.customer_report` 子树承载 P3 对 AI 客户自身的行为诊断（越界泄露 / 一致性问题），用于满足 [CLAUDE.md §3.1](../../CLAUDE.md) "评估端必须能识别 AI 自身的违规诱导"的诉求。前端**必须**在报告页设独立"AI 客户行为诊断"区渲染该子树（即使两类 issues 都为空也展示"未发现客户行为异常"），对齐 CLI 的 [`_render_customer_report`](../../src/peilian/judge.py)。该子树**不**纳入雷达图——AI 客户问题不计入代理人扣分。

### §3a. 报告响应缓存

`build_judge_result` 内部串行触发两次 LLM 调用（`judge_agent` + `judge_customer`），单次报告生成成本与延迟都高。为防止用户刷新报告页或浏览器 prefetch GET 反复烧额度，`SessionData.cached_report` 按以下规则缓存：

- **缓存 key**：`len(dialogue.messages)`（对话长度）
- **失效条件**：chat 路由成功调用 `Dialogue.send_user` 后，将 `cached_report` 置为 `None`（对话变化 → 缓存失效）
- **命中行为**：`GET /api/sessions/{id}/report` 在 `cached_report is not None` 且 `len(messages)` 未变化时直接返回缓存，**不**再触发任何 LLM 调用
- **首次生成**：缓存为空时调用 `build_judge_result`，结果写入 `cached_report` 后返回
- **状态副作用**：首次生成成功后将 `SessionData.status` 置为 `completed`（详见 §2）

实现成本约 10 行代码，但能避免 P5 验收期反复刷新报告页烧 LLM 额度。

### §4. 逐句标注

后端在 report 响应中内嵌 `annotations`，避免前端重复实现 P2 关键词匹配。生成逻辑：

1. 遍历 `messages` 中每条 `role == "user"` 的消息，同时维护一个递增的 `agent_turn_number`（从 1 起）
2. 调用 `match_mandatory_categories(text)` 得到命中的 KYC 类别集合
3. 扫描 `judge_result.evaluation_report.compliance_hits` 中 `turn_index` 匹配的违规条目
4. 返回 `{ turn_index, agent_turn_number, categories, compliance_hits }`，前端只负责渲染标签：`[家庭结构 ✓]` / `[⚠ 保证收益]`

**两种序号语义**（与 P2 / P3 保持一致，避免实现期混淆）：
- `turn_index`：在 `messages` 列表中的整体索引（**含 system，从 0 起**），与 `ComplianceHit.turn_index` 同口径，用于精确定位
- `agent_turn_number`：人类可读的"第 N 轮代理人发言"（**从 1 起**），与 `ComplianceHit.agent_turn_number` 同口径，前端展示用

### §5. 前端技术方案

**ECharts 雷达图（vendor 自托管）**：

```html
<script src="/static/vendor/echarts.min.js"></script>
```

实现阶段需把 `echarts.min.js`（约 1MB，echarts 5 LTS）一次性下载入 [`src/peilian/server/static/vendor/echarts.min.js`](../../src/peilian/server/static/vendor/echarts.min.js)，**纳入 git 仓库**，**不引入任何外网 CDN 依赖**。理由：
- 强监管行业 IT 环境通常禁止外部 CDN，离线/内网部署必须能跑
- jsdelivr 国内被墙、DNS 污染、版本号 breaking 升级都会让报告页直接白屏
- 一次性入库 1MB 文件，后续零运维成本；与"零 npm install / 零构建步骤"原则不冲突

**对话页交互**：
- fetch API 发送消息：`POST /api/sessions/{id}/chat`，body `{ "message": "..." }`
- 响应渲染为左侧气泡
- 输入框回车发送
- "结束对话"按钮触发报告页跳转
- 发送中显示 loading 指示，避免用户连点（前端层防御，后端 per-session lock 是兜底）

**报告页渲染**：
- 页面加载时 `GET /api/sessions/{id}/report` 拿 `ReportResponse`
- ECharts `radar` 类型渲染五维图：4 个维度通过 `agent_report.scores.find(s => s.dimension === "professionalism")` 等**按 `dimension` 字段查找** score（**不**按 `scores[i]` 数组索引），P3 维度顺序变化时不退化；第五维合规分直接读顶层 `compliance_score`
- 逐句标注：遍历 `messages` 与 `annotations`，前端展示用 `agent_turn_number`，定位用 `turn_index`，不在前端重复关键词匹配
- AI 客户行为诊断区：渲染 `judge_result.customer_report`（详见 §3 customer_report 用途）

**路由**：纯前端 hash 路由或 query string 参数（`?session=xxx`），不引入前端路由库。

### §6. 流式通信（不在 P5）

P5 对话接口只实现同步版本（`POST /chat` 返回完整回复），不引入 `sse-starlette`。后续若要追加流式体验，需先单独起草设计，避免与 P5 稳定验收耦合。

可选演进方向：

- `GET /api/sessions/{id}/chat/stream?...` + `EventSource`（浏览器原生 `EventSource` 只能发 GET）
- `POST /api/sessions/{id}/chat/stream` + fetch streaming（不用 `EventSource`）

**P5 验收不依赖流式通信**：同步版本即可通过验收。

### §7. 与 P0-P4 的关系

**P5 只消费 P0-P4 产物，不修改任何已有模块**：

| 消费方 | 被消费模块 | 接口 |
|---|---|---|
| `routes/session.py` | `persona_factory` | `load_persona_from_yaml` / `get_persona_meta`（创建会话时按 stem + difficulty 加载单个 persona） |
| `routes/session.py` | `config` | `load_settings` |
| `routes/personas.py` | `yaml`（标准库 PyYAML） | `yaml.safe_load`（直读 `personas/*.yaml`，**不**调用 `load_personas_from_dir`，避免污染 `_META_BY_PERSONA` 注册表） |
| `routes/chat.py` | `dialogue` | `Dialogue.send_user`（持 `SessionData.lock` 调用） |
| `routes/chat.py` | `session_store` | 持锁调用并失效 `cached_report` |
| `routes/report.py` | `judge` | `build_judge_result`（持 `SessionData.lock` 调用，缓存命中跳过） |
| `routes/report.py` | `observer` | `match_mandatory_categories`（生成 annotations 用） |
| `schemas.py` | `report` / `judge` / `persona_factory` | dataclass 字段结构用于 Pydantic v2 模型 + `from_dataclass` 转换 |

**零修改承诺**：`src/peilian/` 下除 `server/` 子包外，P5 不改动任何 `.py` 文件。

---

## 实施任务拆分（轻量 TDD 顺序）

| # | 任务 | 备注 |
|---|---|---|
| 1 | 修改 `pyproject.toml`：dependencies 增加 `fastapi>=0.110` / `uvicorn[standard]>=0.27` / `pydantic>=2` | — |
| 2 | 实现 `src/peilian/server/schemas.py`：Pydantic v2 模型 + 各模型 `from_dataclass` classmethod；`ReportResponse` 含顶层 `compliance_score: int` | 纯数据结构 |
| 3 | 实现 `src/peilian/server/session_store.py`：`SessionData`（含 `status` / `cached_report` / per-session `Lock`）+ `SessionStore`（dict + `RLock` 仅保护 dict） | 纯函数 + dict |
| 4 | 实现 `src/peilian/server/routes/personas.py`：`GET /api/personas`（`yaml.safe_load` 直读，**不**用 `load_personas_from_dir`） | 依赖 2 |
| 5 | 实现 `src/peilian/server/routes/session.py`：会话 CRUD（创建时 `load_persona_from_yaml` + `get_persona_meta`） | 依赖 2、3 |
| 6 | 实现 `src/peilian/server/routes/chat.py`：发送消息（`with session_data.lock:` 调用 `Dialogue.send_user`，成功后置 `cached_report = None`） | 依赖 2、3 |
| 7 | 实现 `src/peilian/server/routes/report.py`：评估报告（持 `session_data.lock`；缓存命中跳过 LLM；首次生成调用 `build_judge_result`，按 `(turn_index, agent_turn_number)` 去重算 `compliance_score`，写 `cached_report`，置 `status = "completed"`） | 依赖 2、3 |
| 8 | 实现 `src/peilian/server/app.py`：FastAPI app 工厂 + 路由挂载 + 静态文件（**不**挂 CORS middleware） | 依赖 4、5、6、7 |
| 9 | 实现 `src/peilian/server/__main__.py`：`argparse` 暴露 `--host`（默认 `127.0.0.1`）/ `--port`（默认 `8000`）/ `--reload`，启动 uvicorn | 依赖 8 |
| 10 | 跑 `pytest`：单端点测试 + e2e 集成测试（创建会话 → 发 3 条消息 → 取报告，校验 `compliance_score` / `annotations` / `customer_report`）通过（mock LLM） | TDD 绿灯 1 |
| 11 | 下载 ECharts 5 LTS 的 `echarts.min.js`（约 1MB）入 `src/peilian/server/static/vendor/` | vendor 自托管 |
| 12 | 实现前端 `index.html`：persona 选择 + 难度 + 创建会话（fetch `GET /api/personas`） | — |
| 13 | 实现前端 `chat.html` + `chat.js`：对话交互 + 发送中 loading + 按钮禁用 | — |
| 14 | 实现前端 `report.html` + `report.js`：ECharts radar（按 `dimension` 字段查找 score）+ 顶层 `compliance_score` + 逐句标注（用 `agent_turn_number`）+ 合规高亮 + 独立"AI 客户行为诊断"区 | 依赖 11 |
| 15 | 实现前端 `style.css`：全局样式 | — |
| 16 | 端到端人工验收：浏览器完整走通陪练 + 报告 | — |
| 17 | 修改 `README.md` / `docs/ROADMAP.md`：加 P5 demo 命令并同步当前阶段 | — |
| 18 | `pytest` 全量绿灯（P0-P5） | — |
| 19 | 用户审阅、勾选 checklist | — |
| 20 | 由用户授权 commit | — |

---

## 已确认决策

### Q1. 后端框架 → **FastAPI**

理由：自动 OpenAPI 文档、Pydantic 与现有 dataclass 零摩擦、同步路由可直接承接当前 `Dialogue.send_user()`，未来如需 async / streaming 也有演进空间。Flask 需要额外补 OpenAPI 与端点类型约束；Django 重型且无关功能过多。

### Q2. 前端方案 → **轻量 HTML/JS + ECharts（vendor 自托管）**

理由：零 Node.js 依赖、一条命令启动全部服务、ECharts 雷达图开箱即用、符合 CLAUDE.md 依赖审慎原则。Streamlit 前后端耦合且依赖过重；Next.js 引入 Node.js 构建链与项目 Python 栈不匹配。ECharts 引入方式见 Q11（vendor 自托管，不依赖外网 CDN）。

### Q3. 会话存储 → **内存 dict，不做持久化**

理由：P5 单用户本地运行场景，内存存储最简。持久化与 P7 错题本一起做。

### Q4. SSE vs 同步 → **P5 只做同步响应**

理由：当前 `Dialogue.send_user()` 是同步调用，同步 API 实现简单、验收稳定；SSE / WebSocket 作为后续增强体验，另起设计，不引入 P5 依赖与验收。

### Q5. 前端路由 → **query string 参数（?session=xxx）**

理由：不引入前端路由库。页面间通过 URL 参数传递 session_id，简单直接。

### Q6. 雷达图第五维（合规分）→ **5 - len(compliance_hits)，下限 0**

理由：合规是强监管行业的核心维度，必须出现在雷达图上。分数从 P2 `compliance_hits` 直接计算，不额外调 LLM。

### Q7. 逐句标注实现位置 → **后端计算，前端渲染**

理由：KYC 类别匹配逻辑在 `observer.py`（P2 已有），前端不应该重复实现关键词匹配。后端提供 annotations 数据，前端只做渲染。

### Q8. 合规分计算口径 → **按违规轮次去重，前端不重算**

理由：`compliance_hits` 是条目级，同一句话命中多条规则会膨胀计数。按 `(turn_index, agent_turn_number)` 去重得到"违规轮次数"再算分，与 P2 [`report.py::_render_compliance_section`](../../src/peilian/report.py) 的"X 处违规"口径一致。后端在 ReportResponse 顶层提供 `compliance_score: int`，前端**不重算**避免与文本报告对不上。

### Q9. DTO 层策略 → **独立 Pydantic v2 模型 + `from_dataclass` classmethod**

理由：P0–P4 dataclass 是 stdlib `frozen=True` 形态，含 `tuple[Issue, ...]` / `frozenset[str]` 等嵌套类型，FastAPI 直接挂 dataclass 到 `response_model` 在 Pydantic v2 下 schema 生成会有边界差异。独立 `schemas.py` 提供 `from_dataclass` 转换，既隔离契约破坏，又让 OpenAPI `/docs` schema 稳定。Pydantic 版本显式锁 `>=2`。

### Q10. 并发模型 → **两层锁：store RLock 保护 dict + per-session Lock 保护 dialogue 调用**

理由：`Dialogue.send_user` 内部 append messages → 调 OpenAI → append → 写回 `messages[0]`，整段非线程安全；浏览器端用户连点会让 `messages` 与 system prompt 错位。SessionStore 顶层 RLock 仅保护 dict 自身（粒度小），SessionData 携带自己的 Lock 让 chat / report 路由长持锁串行化同 session 的 dialogue 调用。

### Q11. ECharts 引入方式 → **vendor 自托管，echarts.min.js 入仓**

理由：强监管行业 IT 环境通常禁止外网 CDN，离线/内网部署必须能跑；jsdelivr 国内被墙、版本号 breaking 升级都会让报告页白屏。一次性入库约 1MB 文件，前端 `<script src="/static/vendor/echarts.min.js">`，与"零 npm install / 零构建步骤"原则不冲突。

### Q12. 报告响应缓存 → **SessionData.cached_report，按 `len(messages)` 失效**

理由：`build_judge_result` 每次都串行触发两次 LLM（judge_agent + judge_customer），用户刷新报告页或浏览器 prefetch GET 都会反复烧额度。缓存 key 用对话长度（chat 成功后置 None），命中直接返回；约 10 行代码避免 P5 验收期反复刷新报告页烧 LLM。

---

## Commit 策略

> 风格对齐 P0–P4 既有 commit 先例：`docs(PN): 起草/评审修订 phase-N.md 阶段计划` + `feat(PN): 实现 ...`（参考 `fc29d09 docs(P4): 评审修订 phase-4.md 阶段计划`）。

### Commit 1 — phase-5.md 首次入库（含评审修订内容；本次改稿审批后立即执行）

> 本 spec 在草稿阶段做过一轮评审修订（合规分口径、并发锁、ECharts vendor、报告缓存等 13 处定向修改），但未单独 commit 起草版。首次入库时合并为一个 commit，主题用"起草"，正文标注"含评审修订"，避免 git 历史中出现一条孤立的"评审修订"指向不存在的"起草"前置 commit。

```
docs(P5): 起草 phase-5.md 阶段计划（含评审修订）

P5 阶段计划首次入库，纳入草稿阶段的一轮评审修订成果：

- 合规分公式按违规轮次去重（去重 (turn_index, agent_turn_number)），与 P2 文本报告口径对齐；ReportResponse 顶层暴露 compliance_score
- DTO 策略明确：独立 Pydantic v2 模型 + from_dataclass，不直接挂 dataclass 到 response_model
- 并发模型：SessionStore RLock 保护 dict + SessionData per-session Lock 串行化 dialogue 调用
- 安全基线：app.py 不挂 CORS，__main__.py 默认 127.0.0.1，--host 0.0.0.0 显式放开
- ECharts vendor 自托管，static/vendor/echarts.min.js 入仓，不引外网 CDN
- 报告响应缓存（按 len(messages) 失效），避免刷新报告页反复烧 LLM
- annotations 增 agent_turn_number；customer_report 前端独立区渲染
- /api/personas 拆出独立路由，复用 demo_p4 的 yaml.safe_load 模式
- 文件清单 20 项，决策 Q1–Q12，验收 Checklist 覆盖结构/API/UI/集成/测试/Git
```

### Commit 2 — 实现完成（验收通过后执行）

```
feat(P5): 实现 Web UI + 可视化报告

- FastAPI 后端：会话管理 / 对话接口 / 报告接口 / personas 列表 / 静态文件托管
- 并发：SessionData per-session Lock + 报告响应缓存
- 前端：persona 选择 → 聊天对话 → 五维雷达图 + 逐句标注 + 合规高亮 + AI 客户行为诊断
- 依赖：fastapi / uvicorn / pydantic>=2
- ECharts vendor 自托管（static/vendor/echarts.min.js），无外网 CDN
```

---

## 完成条件

1. 验收 checklist 全部勾选
2. 用户在浏览器端到端跑通一次陪练（选 persona → 对话 → 看报告）
3. `pytest` 全绿（P0-P5 全部通过）
4. 由用户授权后 commit

---

## 进入 P6 的前置条件（仅作占位，不在 P5 内执行）

- P5 所有验收项通过
- 用户显式指示切换游标
- 启动 P6 时再起草 `phase-6.md`
