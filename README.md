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
