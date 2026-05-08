# Phase 0 — 项目初始化与开发工作流地基

> 状态：进行中（待用户验收）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)

---

## 目标

搭好可持续开发的项目骨架与上下文文档体系，并用一个**业务中性**的最小 demo 证明地基跑得通。本阶段不涉及任何业务逻辑。

元目标：让下一次任意会话从零启动时，Claude Code 能通过自动加载的 CLAUDE.md + 显式读取 ROADMAP.md，立即知道项目目标、当前阶段、本阶段做什么、什么不能碰。

---

## 任务清单

| # | 任务 | 文件 |
|---|---|---|
| 1 | 写 .gitignore | `.gitignore` |
| 2 | 写 .env.example | `.env.example` |
| 3 | 写 pyproject.toml | `pyproject.toml` |
| 4 | 创建 peilian 包 | `src/peilian/__init__.py` |
| 5 | 写 config 加载模块 | `src/peilian/config.py` |
| 6 | 写 demo 脚本（含 `--skip-llm`）| `scripts/demo_p0.py` |
| 7 | 写 CLAUDE.md 项目宪法 | `CLAUDE.md` |
| 8 | 写 ROADMAP.md | `docs/ROADMAP.md` |
| 9 | 写 phase-0.md（本文件）| `docs/phases/phase-0.md` |
| 10 | 完善 README | `README.md` |
| 11 | 用户人工运行 demo 验证 | — |
| 12 | 提交首个 commit | git |

---

## Demo 命令

`demo_p0.py` 支持 `--skip-llm` 标志，用于无 API key 环境下也能验证地基（仍执行配置加载 + 包导入两步健康检查，仅跳过真实 LLM 调用）。

```powershell
# 1. 安装（开发模式）
pip install -e .

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL

# 3a. 完整健康检查（需有可用 API key）
python scripts/demo_p0.py

# 3b. 跳过真实 LLM 调用（无 key 环境）
python scripts/demo_p0.py --skip-llm
```

预期完整版输出：

```
[PeiLian Phase 0 健康检查]
[1/4] ✓ 配置加载成功
        base_url = https://xxx
        model    = gpt-4o-mini
[2/4] ✓ 包导入成功 (peilian v0.0.1)
[3/4] → 调用 LLM…
[4/4] ✓ 收到响应：

  Q: 用一句话证明你能正常对话。
  A: 收到，已成功响应。

✓ Phase 0 demo 通过
```

预期 `--skip-llm` 输出：

```
[PeiLian Phase 0 健康检查]
[1/4] ✓ 配置加载成功
        base_url = <未配置>
        model    = <未配置>
[2/4] ✓ 包导入成功 (peilian v0.0.1)
[3/4] ⏭ 已跳过 LLM 调用 (--skip-llm)
[4/4] ⏭ 已跳过响应校验

✓ Phase 0 demo 通过（地基验证模式）
```

---

## 验收 Checklist

**结构 / 文件**
- [ ] 目录结构符合 plan 设计
- [ ] `.gitignore` 覆盖 `.env`、`.venv`、`__pycache__`、`.idea/`、`*.egg-info`
- [ ] `.env.example` 含三个必要环境变量，无真实密钥
- [ ] `pyproject.toml` 依赖仅 `openai` + `python-dotenv`

**文档**
- [ ] `CLAUDE.md` 含：项目目标、两条核心架构原则、合规红线、技术栈基线、工作流约定、术语表、Claude Code 入口指引
- [ ] `CLAUDE.md` 不含任何 schema/字段/具体 API 形态
- [ ] `docs/ROADMAP.md` 顶部有「当前游标：P0」醒目标识，含 P0–P7 总览
- [ ] `docs/phases/phase-0.md` 含目标 / 任务清单 / Demo / 验收清单 / 不做项
- [ ] `README.md` 三步内能让一个新克隆者跑通 demo

**可执行性**
- [ ] `pip install -e .` 成功
- [ ] `python scripts/demo_p0.py --skip-llm` 跑通前两步并显式提示已跳过 LLM
- [ ] `python scripts/demo_p0.py` 在配好 `.env` 后能拿到真实响应（如本会话无 key 则用 `--skip-llm` 替代）
- [ ] `.env` 在 `git status` 中不出现
- [ ] `.idea/` 不会被纳入版本管理

**Git**
- [ ] 至少一个 commit，message 第一行含 `Phase 0`
- [ ] 工作区干净

---

## 不在 Phase 0 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| persona 数据结构 / 字段 | P1 |
| 对话状态机 / 多轮记忆 | P1 |
| 评估逻辑（规则层、LLM judge）| P2 / P3 |
| RAG / 知识库 / 向量库 | P5 |
| Web UI / API server | P6 |
| 单元测试框架（pytest 等） | P1 |
| Lint / formatter / pre-commit | 暂不 |
| CI / GitHub Actions | 暂不 |
| logging / 监控 | 后续按需 |
| langchain / llamaindex 等重型框架 | 全程审慎，目前都不需要 |
| **创建 phase-1.md 或任何 P1 物料** | **P0 完成后由用户显式启动 P1** |

---

## 完成条件

1. 上述验收 checklist 全部勾选
2. 用户人工跑过 `pip install -e .` 与 `python scripts/demo_p0.py [--skip-llm]`
3. 提交 commit

---

## 进入 P1 的前置条件

- 本阶段所有验收项通过
- **用户显式指示切换游标**到 P1
- 用户切换游标时：在 ROADMAP.md 把 P0 改为「✅ 已完成」并把当前游标移到 P1
- 启动 P1 时先用 Plan 模式起草 phase-1.md（**Phase 0 内不创建该文件**）
