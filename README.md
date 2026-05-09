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

## P2 Demo — 规则层评估（必问点覆盖率 + 合规红线扫描）

```powershell
# 1. 跑评估 demo（无需 OPENAI_API_KEY，纯本地规则层）
python scripts/demo_p2.py

# 2. 跑测试（含 P2 新增）
pytest
```

`demo_p2.py` 会加载 `SAMPLE_CONVERSATION_P2`（一段同时含漏问与违规的样本对话）跑评估，输出形如：

```
【必问点覆盖率】4 / 6  (66.7%)
  ✓ 已覆盖：family_structure (家庭结构), occupation (职业行业), ...
  ✗ 漏问：  income (收入水平), future_planning (未来规划)

【合规红线扫描】发现 1 处违规
  ⚠ 第 3 轮 [代理人]
     原话：…保证收益 4.5%，比存款利…
     命中规则：
       - 保证收益（关键词「保证收益」）
       - 与存款/国债误导对比（关键词「比存款」）
```

要在 P1 陪练结束后手动评估自己的真实对话历史，可以：

```python
from peilian.observer import evaluate
from peilian.report import render_report

report = evaluate(dialogue.messages)  # dialogue 是 P1 demo 里的 Dialogue 实例
print(render_report(report))
```

> 状态观察器与对话引擎**物理隔离**：`observer.evaluate()` 只消费 `messages`，不会影响客户回复或推进对话分支（详见 [`CLAUDE.md`](CLAUDE.md) §2.2）。

---

## P3 Demo — LLM-as-Judge 评估

```powershell
# 1. 确保 .env 已配置 OPENAI_API_KEY（P3 不支持 --skip-llm）

# 2. 跑综合评估 demo：P2 规则层 + P3 代理人评分 + P3 客户诊断
python scripts/demo_p3.py

# 3. 手动验证 judge 稳定性（会调用真实 LLM，不进 pytest）
python scripts/check_stability_p3.py
python scripts/check_stability_p3.py --runs 10

# 4. 跑测试（P3 测试全部使用 mock client，不烧 LLM 额度）
pytest
```

`demo_p3.py` 固定加载 `SAMPLE_CONVERSATION_P3`，这段样本故意包含 AI 客户越界泄露与前后矛盾，用于演示 customer judge 的诊断能力。P3 judge 仍然是纯诊断层：不修改 `dialogue.py`，不接入生成链路，不调度对话分支。

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

🚩 **P3 — LLM-as-Judge 评估**（详见 [`docs/phases/phase-3.md`](docs/phases/phase-3.md)）

阶段切换由用户显式确认；不会自动推进到下一阶段。
