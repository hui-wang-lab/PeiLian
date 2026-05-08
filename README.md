# PeiLian

寿险代理人文本陪练系统：以 LLM 模拟客户，帮代理人在真实销售场景中练习 KYC、产品讲解、异议处理与促成。

> 本仓库以 **AI Coding 工作流实践**为元目标。详见 [`CLAUDE.md`](CLAUDE.md)（项目宪法）与 [`docs/ROADMAP.md`](docs/ROADMAP.md)（阶段路线图）。

---

## 三步跑通 Phase 0 Demo

```powershell
# 1. 安装（开发模式）
pip install -e .

# 2. 配置环境变量
copy .env.example .env
# 用编辑器打开 .env，填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL

# 3. 运行健康检查
python scripts/demo_p0.py
# 或在无 API key 环境下：
python scripts/demo_p0.py --skip-llm
```

预期输出形如：

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

---

## P1 Demo — 单 persona 单场景陪练

```powershell
# 1. 安装含 dev 依赖（首次或更新依赖时执行）
pip install -e ".[dev]"

# 2. 确保 .env 已配置 OPENAI_API_KEY（P1 不支持 --skip-llm）

# 3. 进入陪练对话
python scripts/demo_p1.py

# 4. 跑测试
pytest
```

陪练界面只展示客户称呼、会面场景、时间约束与代理人任务提示。家庭结构、收入、已有保单等信息都不会被预先暴露——必须由代理人在对话中**问出来**。客户严格遵守「代理人驱动、客户被动反应」原则（详见 [`CLAUDE.md`](CLAUDE.md) §2）。

CLI 内可用命令：

| 命令 | 作用 |
|---|---|
| `/quit` | 退出陪练 |
| `/reset` | 清空对话历史并重新开始 |

---

## 项目地图

| 文件 | 用途 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | 项目宪法：稳定原则、合规红线、术语表 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 阶段路线图 + 当前游标 |
| [`docs/phases/phase-N.md`](docs/phases/) | 每阶段的详细 spec |
| `src/peilian/` | 主代码包 |
| `scripts/demo_p*.py` | 各阶段的一行命令 demo |

---

## 当前阶段

🚩 **P0 — 项目初始化与开发工作流地基**（详见 [`docs/phases/phase-0.md`](docs/phases/phase-0.md)）

阶段切换由用户显式确认；不会自动推进到下一阶段。
