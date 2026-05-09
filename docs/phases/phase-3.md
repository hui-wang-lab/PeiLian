# Phase 3 — LLM-as-Judge 评估

> 状态：计划阶段（待用户审阅本 spec）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-2.md`](phase-2.md) ✅

---

## P3 目标

把对话**评估能力**从规则层延伸到模型层：**用 LLM 对一段对话同时给出两份独立报告**——

1. **`AgentJudgeReport`**：评代理人（4 个维度的 1–5 分打分 + 简短理由）
2. **`CustomerJudgeReport`**：评 AI 客户自身（识别越界泄露与前后矛盾，输出 issue list）

P3 与 P2 的最终产物在 demo / 渲染层合并为一份「综合报告」，但中间层完全解耦：

- **judge 只消费 `messages`，不依赖 `EvaluationReport`**（与 P2 数据流隔离，便于独立演化）
- **拼装层**：`build_judge_result(messages) -> JudgeResult` 内部顺序执行 `evaluate()` + `judge_agent()` + `judge_customer()`，把 3 份产物装进同一个 `JudgeResult`

**架构铁律继承自 [CLAUDE.md §2.2](../../CLAUDE.md)**：

> 状态观察器（含 P3 judge）**绝不**参与生成客户回复，**不**调度对话分支。

P3 是**纯诊断**：

- 不修改 `dialogue.py`、不接 hook、不改 `prompts.py`
- 即使 judge 指出「AI 客户在第 N 轮越界泄露了 hidden_concerns」，**P3 也不修复**——修复路径在 P4 引入 `CustomerState` 时才落地

---

## 用户故事

### 业务侧
```
作为一名陪练系统的开发者 / 培训主管，
我希望  在规则层评估之外再拿到一份模型层的诊断报告，
能够  看到代理人 4 个维度的细颗粒度评分（话术专业度 / 共情度 /
        逻辑结构 / 异议处理质量），并附一句话评语；
能够  看到 AI 客户自身有没有"演得不真"——典型的：
        - 在没被问到时主动报家庭/收入/已有保单/隐藏关切（越界泄露）
        - 同一字段在不同轮自相矛盾（一致性问题）
以便  在 P5 RAG 之前，先用 LLM 兜住规则层兜不住的语义判断；
      同时为 P4 的 CustomerState 设计提供「客户当前演技哪里崩」的可量化输入。
```

### 测试侧
```
作为开发者，
我希望  CI / 本地 pytest 不烧任何真实 LLM 额度，
能够  用 mock 的 judge response 测 schema、parsing、渲染、合并逻辑；
也希望  有独立脚本在我手动想验证模型稳定性时跑真实 LLM N 次拿方差；
以便  开发态测试快、稳、零成本，模型稳定性验证留给人工触发。
```

---

## 纵切范围

- **代理人评分 rubric**：4 个维度的 1–5 分量纲 + 每维度子准则文本（写死在 `judge_prompts.py`）
- **客户诊断 rubric**：越界泄露 + 一致性两类，issue list 输出（不打总分）
- **judge 入口**：`judge_agent(messages) -> AgentJudgeReport`、`judge_customer(messages) -> CustomerJudgeReport`
- **JudgeResult 合并**：`build_judge_result(messages) -> JudgeResult`（内部顺序执行 P2 evaluate 与 P3 judge_*，统一渲染；P3 不做并发）
- **样本对话**：新增 `SAMPLE_CONVERSATION_P3`（专门含 AI 客户越界 + 一致性问题，给 demo 与测试用）
- **CLI demo**：`python scripts/demo_p3.py` 强制需 LLM key，跑 `SAMPLE_CONVERSATION_P3` 输出综合报告
- **稳定性脚本**：`scripts/check_stability_p3.py` 对同一段对话跑 N 次 judge，输出每维度方差 + max-min（不进 pytest）
- **测试**：mock LLM client 测 parsing / schema / 渲染 / 合并；不调真实 LLM

---

## 建议目录结构（增量）

只列出 P3 新增/修改的部分：

```
PeiLian/
├── src/peilian/
│   ├── judge_prompts.py           # 新增：代理人 rubric + 客户诊断 rubric + 两份 system prompt
│   ├── judge.py                   # 新增：dataclass (AgentJudgeReport / CustomerJudgeReport /
│   │                              #         DimensionScore / Issue / JudgeResult)
│   │                              #       + judge_agent / judge_customer / build_judge_result
│   │                              #       + parse_* + render_judge_result
│   └── conversations.py           # 修改：追加 SAMPLE_CONVERSATION_P3（不动 SAMPLE_CONVERSATION_P2）
├── scripts/
│   ├── demo_p3.py                 # 新增：跑 build_judge_result 并打印综合报告
│   └── check_stability_p3.py      # 新增：N 次跑 judge，输出方差 / max-min；不进 pytest
└── tests/
    ├── test_judge_prompts.py      # 新增：rubric / system prompt 渲染含关键约束
    ├── test_judge_parse.py        # 新增：fake judge response → 正确 parse 成 dataclass
    ├── test_judge.py              # 新增：mock LLM client，端到端 judge_agent / judge_customer / build_judge_result
    └── test_judge_render.py       # 新增：render_judge_result 含三段标题与关键标识
```

> **不动 P2 物料**：`rules.py` / `report.py` / `observer.py` 一行不改。`conversations.py` 只**追加** `SAMPLE_CONVERSATION_P3`，不改 `SAMPLE_CONVERSATION_P2`。
>
> **不动 P1 物料**：`dialogue.py` / `prompts.py` / `persona.py` / `scenario.py` 全部保持不变。判 AI 客户越界泄露的修复路径在 P4。

> **为什么 judge_prompts.py 与 judge.py 拆两文件**：rubric 文本是 prompt 工程产物，会反复改；judge.py 是接口与 parsing 逻辑，相对稳定。拆开避免改 prompt 时污染到接口侧的 git history。与 P1 的 `prompts.py` / `dialogue.py` 拆分同理。

> **为什么不拆 judge_models.py**：P3 的 dataclass 总共 5 个，且全部围绕 judge_*() 的输入输出，强耦合。单独成文件会切断"看接口就知道返回啥"的就近性。如果 P5+ judge schema 暴涨，再拆。

---

## 计划创建/修改的文件

| # | 文件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `src/peilian/judge_prompts.py` | 新增 | 代理人 rubric (4 维度) + 客户诊断 rubric (2 类) + 两份 judge system prompt |
| 2 | `src/peilian/judge.py` | 新增 | 5 个 frozen dataclass + judge_agent / judge_customer / build_judge_result + parse 帮助 + render_judge_result |
| 3 | `src/peilian/conversations.py` | 修改 | 追加 `SAMPLE_CONVERSATION_P3`（保留 P2 sample 不动）|
| 4 | `scripts/demo_p3.py` | 新增 | 加载 P3 sample → build_judge_result → 打印综合报告；强制 LLM key |
| 5 | `scripts/check_stability_p3.py` | 新增 | 对 P3 sample 跑 N 次 judge，输出每维度方差 / max-min；不进 pytest |
| 6 | `tests/test_judge_prompts.py` | 新增 | 两份 system prompt 渲染含关键约束（4 维度名 / 越界 / 一致性等关键字）|
| 7 | `tests/test_judge_parse.py` | 新增 | fake judge JSON → 正确 parse；非法 JSON / 缺字段时给出可定位的错误 |
| 8 | `tests/test_judge.py` | 新增 | mock LLM client，端到端 judge_agent / judge_customer / build_judge_result（含与 P2 evaluate 合并）|
| 9 | `tests/test_judge_render.py` | 新增 | render_judge_result 含「评估报告」「代理人评分」「AI 客户行为诊断」三段标题与关键标识 |
| 10 | `README.md` | 修改 | 加 P3 demo 命令一节 + 稳定性脚本说明 |

> **明确不做**：
> - 不创建 `src/peilian/customer_state.py`（P4 的 CustomerState）
> - 不修改 `dialogue.py` / `prompts.py` / `persona.py` / `scenario.py`
> - 不改 P2 物料（rules / report / observer）
> - 不引入 `langchain` / `pydantic` 等新依赖（dataclass + 手写 JSON parse 够用）
> - 不做 LLM judge 自动重试 / 多模型集成 / 投票打分
> - 不在 demo_p1.py 里嵌入 judge 调用（保持 P1 demo 纯净，与 phase-2 同节奏）

---

## Demo 命令

```powershell
# 跑 P3 综合评估 demo（需 OPENAI_API_KEY；同时输出 P2 规则层 + P3 模型层）
python scripts/demo_p3.py

# 跑测试（pytest 不烧 LLM 额度，全部走 mock）
pytest

# 手动验证模型评分稳定性（默认 5 次，写到 stdout；烧 LLM 额度）
python scripts/check_stability_p3.py
python scripts/check_stability_p3.py --runs 10
```

预期 demo 输出形如：

```
[PeiLian P3 — LLM-as-Judge 评估 demo]
样本对话：SAMPLE_CONVERSATION_P3（含 AI 客户越界 + 一致性问题，
                                  专门用于演示 customer judge 能力）

═══════════════════════════════════════
综合评估报告
═══════════════════════════════════════

【一、规则层评估（P2）】
  必问点覆盖率：2 / 6  (33.3%)
    ✓ 已覆盖：occupation (职业行业), health_status (健康情况)
    ✗ 漏问：  family_structure (家庭结构), income (收入水平), existing_coverage (已有保障), future_planning (未来规划)
  合规红线扫描：未发现违规

【二、代理人评分（P3）】
  ★★★☆☆  3/5  话术专业度    用词得体但偶有过度技术化
  ★★★★☆  4/5  共情度        多次回应客户情绪，开场寒暄到位
  ★★☆☆☆  2/5  逻辑结构      KYC 未做完即跳到产品讲解
  ★★★☆☆  3/5  异议处理      识别到价格异议但回应较模板化
  综合评语：节奏需调整；建议在转入产品讲解前补齐收入与已有保障问询。

【三、AI 客户行为诊断（P3）】
  越界泄露：发现 2 处
    ⚠ 第 1 轮 [客户]
       原话：…我家里 5 口人，太太和两个孩子，还有岳母…
       违反：代理人未问家庭结构，客户主动报家庭信息（hidden_concerns 类）
    ⚠ 第 3 轮 [客户]
       原话：…其实我最担心的就是这款贵不贵…
       违反：代理人未触发价格话题，客户主动暴露价格敏感（hidden_concerns 类）
  一致性问题：发现 1 处
    ⚠ 第 2 / 第 6 轮
       第 2 轮：…太太是医生，在协和…
       第 6 轮：…我太太在律所做合伙人…
       性质：太太职业前后矛盾

═══════════════════════════════════════
```

预期 pytest 输出（含 P0/P1/P2 已有 + P3 新增）：

```
tests\test_judge.py ......                      [..]
tests\test_judge_parse.py ......                [..]
tests\test_judge_prompts.py .....               [..]
tests\test_judge_render.py ....                 [..]
tests\test_observer.py ........                 [..]
tests\test_persona.py .......                   [..]
tests\test_prompts.py ........                  [..]
tests\test_report.py .....                      [..]
tests\test_rules.py .....                       [..]
======= XX passed in 0.YY s =======
```

---

## 验收 Checklist

**结构 / 文件**
- [ ] 上述 10 个新增/修改文件全部到位
- [ ] **未**修改 `dialogue.py` / `demo_p1.py` / `prompts.py` / `persona.py` / `scenario.py`
- [ ] **未**修改 P2 物料（rules / report / observer / demo_p2）
- [ ] **未**创建 P4+ 物料（customer_state / persona 工厂 / RAG / web 等）

**rubric 与 prompt**
- [ ] 代理人 rubric 含 4 维度：话术专业度 / 共情度 / 逻辑结构 / 异议处理质量
- [ ] 每维度有清晰的 1–5 分尺度文本（什么算 1 分、什么算 5 分）
- [ ] 客户诊断 rubric 含 2 类：越界泄露 / 一致性
- [ ] 越界泄露明确列出「未问即报」清单：家庭 / 收入 / 已有保障 / hidden_concerns
- [ ] judge system prompt 显式要求 LLM 输出 **JSON**，并给出 schema 范例（避免 free-form 文本难 parse）

**dataclass 与 API**
- [ ] `AgentJudgeReport` / `CustomerJudgeReport` / `DimensionScore` / `Issue` / `JudgeResult` 全部 frozen
- [ ] `judge_agent(messages)` / `judge_customer(messages)` 是入口；`build_judge_result(messages)` 在内部顺序执行 P2 evaluate + P3 judge_*
- [ ] judge 函数签名只接 `messages` 和可选的 `client`（便于注入 mock），**不接** EvaluationReport（与 Q2 决策一致）
- [ ] 所有 LLM 调用通过 `peilian.config.load_settings()` 获取配置；`client=None` 时由 `judge.py` 创建 OpenAI client

**测试**
- [ ] `pytest` 全绿；测试**不**调真实 LLM
- [ ] mock 客户端通过依赖注入或 `unittest.mock`，不需要新依赖
- [ ] `test_judge_parse.py` 覆盖：合法 JSON 完整 parse / 缺字段抛清晰错误 / 非法 JSON 抛清晰错误
- [ ] `test_judge.py` 覆盖：mock 返回固定 fake JSON → 端到端拿到正确 dataclass / build_judge_result 含 P2 + P3 三部分

**Demo / 稳定性脚本**
- [ ] `python scripts/demo_p3.py` 在无 LLM key 时报错并指引去 `.env`（与 demo_p1 同节奏）
- [ ] demo 输出三段标题：「规则层评估（P2）」「代理人评分（P3）」「AI 客户行为诊断（P3）」
- [ ] 输出在 Windows 控制台正常显示（UTF-8 stdout 重配）
- [ ] `python scripts/check_stability_p3.py` 默认跑 5 次，输出每维度的方差与 max-min；可用 `--runs N` 改次数
- [ ] 稳定性脚本**不**进 pytest（避免 CI 烧额度）

**Git**
- [ ] 至少两个 commit（spec 起草 + 实现物料），message 第一行含 `Phase 3` 或 `P3`
- [ ] 工作区干净

---

## 不在 P3 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| 修复 AI 客户越界泄露 / 一致性问题（改 dialogue / prompts）| **P4**（CustomerState 引入后才有"可说/不可说/已说"的状态可挂） |
| `CustomerState` 数据结构与生成前/后状态摘要 | **P4** |
| Persona 工厂、yaml 配置、难度档 | **P4** |
| 销售漏斗阶段自动识别（开场/挖需/讲解/异议/促成）| 留待真有需求 |
| 多 LLM 投票 / 多模型集成 | 留待真有需求；P3 只跑单模型 |
| Judge 自动重试 / 自动反馈循环 | 单次调用失败直接抛错给 demo 层 |
| 评估报告嵌入 P1 demo（结束陪练后自动出报告）| 可选放到 P4 起步阶段 |
| 产品条款 RAG 校验（条款引用准确性）| **P5** |
| Web UI / 雷达图可视化 | **P6** |
| 错题本 / 弱项画像 / 自适应难度 | **P7** |
| 修改 `CLAUDE.md` | 本阶段无需改动宪法 |
| 创建 `phase-4.md` 或任何 P4 物料 | P3 完成后由用户显式启动 P4 |

---

## 技术设计要点

### §1. 代理人评分 rubric（写死草稿，待用户审阅）

**量纲**：1–5 整数。选择整数而非小数 / 字母等级的理由：
- 整数最易稳定到 ±1（验收要求）
- 5 档够细但不至于让 LLM 在 4.3 / 4.5 之间纠结
- 渲染时可以用 ★★★☆☆ 直观显示

**4 个维度（与 ROADMAP 表述对齐）**：

| dimension | 中文标签 | 1 分（差） | 3 分（中等） | 5 分（优秀） |
|---|---|---|---|---|
| `professionalism` | 话术专业度 | 反复说错术语；过度技术化或过度口语化 | 术语基本准确，但偶有过度技术化或过度简化 | 术语准确、节奏得体、对客户认知水平有动态调整 |
| `empathy` | 共情度 | 完全无视客户情绪；只顾推自己的话 | 部分回应客户情绪，但偶有打断或忽略 | 多次主动回应客户情绪，使用恰当的回应模式（复述 / 共情 / 询问感受）|
| `structure` | 逻辑结构 | KYC / 讲解 / 异议 / 促成完全跳跃，无章法 | 大体按 KYC→讲解→异议→促成推进，但有局部跳跃或重复 | 节奏清晰；每步推进前有明确的过渡句与确认 |
| `objection_handling` | 异议处理 | 没识别出客户的异议或硬推 | 识别到异议但回应较模板化 | 准确识别异议类型（价格 / 信任 / 同业对比 / 拖延），回应切题且有差异化 |

**输出形态**：每维度 `(score, reasoning)`，外加一个 `overall_comment`（≤ 50 字）。

**为什么没有「合规」维度**：合规红线由 P2 规则层硬卡，模型层不重复打分（避免规则与 LLM 冲突时口径不一）。如 LLM 在评语中提及合规问题，那是 free-form 评语，不进结构化字段。

### §2. 客户诊断 rubric（写死草稿，待用户审阅）

**输出形态**：issue list（**不打总分**）。理由：
- 越界 / 一致性问题是**离散事件**，加总成分数会丢失定位信息
- 与代理人评分的连续打分逻辑分开，prompt 也更清晰
- 未来 P4 接 CustomerState 时，issue list 是可机器消费的输入

**两类 issue**：

#### 越界泄露 (`premature_disclosure`)

判定准则（写进 system prompt）：
- 对每条 `assistant` 消息中的每个受保护字段，判断截至该 assistant 回复前，代理人是否曾明确询问或自然触发过该字段。
- 如果该字段从未被问到 / 触发，客户主动报出，才算 `premature_disclosure`。
- 如果该字段已被问过 / 触发，后续自然引用不算越界；但如果后续泄露的是新的受保护字段或新的 `hidden_concerns`，仍可判为越界。
- 受保护字段（"未问即报算越界"）：
  - 家庭结构（人口数 / 配偶 / 孩子 / 父母）
  - 收入水平
  - 已有保障 / 已有保单
  - hidden_concerns（价格敏感 / 信任问题 / 与同业对比意向 / 拖延倾向 等）
- 受保护字段以外的客户主动延展（如对天气、时间的小寒暄）**不算越界**

输出 Issue 字段：
- `turn_index`：泄露发生在 `messages` 第几位（指向 assistant 消息）
- `agent_turn_number`：对应代理人发言序号（最近的上一个 user 消息）
- `excerpt`：泄露原话片段
- `violation_type`：固定为 `"premature_disclosure"`
- `protected_field`：被越界泄露的字段类（如 `"family_structure"` / `"hidden_concerns"`）
- `reasoning`：一句话解释为什么算越界

#### 一致性问题 (`inconsistency`)

判定准则：
- 同一字段在不同轮的客户回答自相矛盾
- P3 只判断对话内客户前后说法自相矛盾；不判断与外部 persona 对象的矛盾
- 若 system message 内显式包含 persona 信息，只能作为 `messages` 内可见信息参考；不得依赖 `peilian.persona` 或额外对象

输出 Issue 字段：
- `turn_index`：主要轮次（取较晚那一轮）
- `related_turn_indices`：相关轮次列表（含较早的那一轮）
- `excerpt`：矛盾片段（如 `"第 2 轮：太太是医生 / 第 6 轮：太太在律所"`）
- `violation_type`：固定为 `"inconsistency"`
- `field`：发生矛盾的字段类
- `reasoning`：一句话解释矛盾性质

### §3. dataclass 形态

```
DimensionScore(frozen):
  dimension: str            # "professionalism" / "empathy" / ...
  label: str                # 中文标签
  score: int                # 1–5
  reasoning: str            # 一句话理由

AgentJudgeReport(frozen):
  scores: tuple[DimensionScore, ...]   # 4 项，按 rubric 顺序
  overall_comment: str                 # 综合评语，≤ 50 字
  raw_response: str                    # LLM 原始 JSON 文本（便于排查）

Issue(frozen):
  turn_index: int
  agent_turn_number: int               # 越界类有意义；一致性类传 0 或 -1
  related_turn_indices: tuple[int, ...]  # 一致性类用；越界类传空 tuple
  excerpt: str
  violation_type: str                  # "premature_disclosure" | "inconsistency"
  protected_field: str                 # 越界类：被泄露字段；一致性类：发生矛盾的字段
  reasoning: str

CustomerJudgeReport(frozen):
  premature_disclosure_issues: tuple[Issue, ...]
  inconsistency_issues: tuple[Issue, ...]
  overall_comment: str
  raw_response: str

JudgeResult(frozen):
  evaluation_report: EvaluationReport       # P2 规则层
  agent_report: AgentJudgeReport            # P3 代理人评分
  customer_report: CustomerJudgeReport      # P3 客户诊断
```

**为什么 raw_response 入字段**：调试期排查 LLM 输出格式问题；正式 demo 不展示。`render_judge_result()` 不打印 raw_response。

### §4. judge 模块 API

```
def judge_agent(
    messages: list[dict[str, Any]],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> AgentJudgeReport: ...

def judge_customer(
    messages: list[dict[str, Any]],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> CustomerJudgeReport: ...

def build_judge_result(
    messages: list[dict[str, Any]],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> JudgeResult:
    """顺序执行三件事：
    - peilian.observer.evaluate(messages)        → P2 规则层
    - judge_agent(messages, client=client, ...)  → P3 代理人评分
    - judge_customer(messages, ...)              → P3 客户诊断
    打包返回 JudgeResult。
    """

def render_judge_result(result: JudgeResult) -> str: ...
```

**实现要点**：
- `client=None` 时与现有 `dialogue.py` 一致：先 `settings = load_settings()`；若无 `settings.api_key`，抛出清晰错误并提示配置 `OPENAI_API_KEY` / `.env`；否则在 `judge.py` 内部创建 `OpenAI(api_key=settings.api_key, base_url=settings.base_url)`
- `model` 使用 `model or settings.model or "gpt-4o-mini"`
- LLM 调用 `temperature=0`，保留 `response_format={"type": "json_object"}`，并在 prompt 内写明 JSON schema
- 如果底层 OpenAI-compatible API 不支持 `response_format`，P3 不做自动降级或重试；demo 层允许抛出清晰错误，提示检查模型 / API 兼容性
- 每次调用前用 `messages[-N:]`（截到合理上下文）作为 prompt 中的对话引用，避免上下文爆炸；初版不截，整段塞进去
- parsing 失败抛 `JudgeParseError`（自定义异常，含 raw_response），demo 层兜底打印
- **不**做并发：`build_judge_result` 顺序跑 evaluate → judge_agent → judge_customer，单次 demo 至多 2 次 LLM 调用，串行可接受

**架构隔离**：`judge.py` 顶部 import 允许 `peilian.observer` / `peilian.report` / `peilian.judge_prompts` / `peilian.config` / `openai`；**禁止** import `peilian.dialogue` / `peilian.persona` / `peilian.scenario` / `peilian.prompts`（与 P2 observer 隔离规则保持一致）。

### §5. 样本对话 `SAMPLE_CONVERSATION_P3`

`src/peilian/conversations.py` 追加常量；P2 sample 一行不动。

**设计目标**：单份样本同时演示——

1. 代理人评分有可打分内容（KYC 跳跃 / 异议处理较模板化）
2. AI 客户**故意越界**（在代理人没问家庭时主动报家庭、没触发价格时主动说"我担心价格"）
3. AI 客户**故意前后矛盾**（如太太职业前后不一致）

草稿构思（**最终内容在实施时定稿**）：

| 轮次 | 角色 | 内容（梗概）| 评估意图 |
|---|---|---|---|
| 0 | system | (省略) | — |
| 1 | user | 您好张先生，今天聊聊。 | 代理人开场无营养（structure 减分材料） |
| 2 | assistant | 你好，我家里 5 口人，太太是医生在协和，两个孩子还有岳母。 | **越界**：未问即报家庭结构 |
| 3 | user | 那您工作呢？ | 命中 occupation |
| 4 | assistant | 我做 IT 的。其实我最担心的就是这款贵不贵。 | **越界**：未触发即暴露 hidden_concerns（价格敏感）|
| 5 | user | 这款其实定价很合理，您看每天就一杯咖啡的钱。 | 异议处理较模板化（objection_handling 中分材料）|
| 6 | assistant | 嗯。对了我太太在律所做合伙人，工作挺忙。 | **一致性问题**：第 2 轮说协和医生，第 6 轮说律所合伙人 |
| 7 | user | 您身体怎么样？ | 命中 health_status |
| 8 | assistant | 还行。 | 正常被动反应 |

**预期 evaluate 结果**：覆盖 occupation / health_status (2/6)；漏 family_structure / income / existing_coverage / future_planning；红线 0。

**预期 judge_customer 结果**：
- 越界泄露 issues：≥ 2 条（第 2 轮家庭、第 4 轮 hidden_concerns）
- 一致性 issues：≥ 1 条（第 2 / 第 6 轮太太职业）

**预期 judge_agent 结果**：4 维度都有可打分材料；不要求精确分数（LLM 评分本身有方差）。

### §6. LLM 调用与稳定性

**单次 judge 调用**：
- temperature=0
- `response_format={"type": "json_object"}` + prompt 内 JSON schema
- 如果底层 OpenAI-compatible API 不支持 `response_format`，P3 不做自动降级或重试；demo 层允许抛出清晰错误，提示检查模型 / API 兼容性
- 完整对话作为 user message 拼到 prompt 末尾，judge 角色 instruction 在 system

**稳定性脚本** `scripts/check_stability_p3.py`：
- 默认 5 次（`--runs N` 可改）
- 对 `SAMPLE_CONVERSATION_P3` 跑 N 次 `build_judge_result`
- 输出每个 `DimensionScore.dimension` 的：均值 / max-min / 简单方差
- 输出客户 issue 数量的 max-min（不要求每次完全一致）
- **不进 pytest**（CI 不烧 LLM 额度）

人工合格线：
- 每个 dimension 的 max-min ≤ 1（即所有运行都在最多差 1 分内）
- 客户 issue 数量 max-min ≤ 1（识别能力的稳定性）

不达标时由人工调 prompt（rubric 表述、范例、温度参数）。

### §7. 测试设计

**`test_judge_prompts.py`**（约 5 条）：
- 代理人 system prompt 含 4 个维度的中英文标签
- 代理人 system prompt 含「JSON」字样与 schema 关键字段名
- 代理人 system prompt 含 1–5 量纲说明
- 客户 system prompt 含「越界」「一致性」/「premature_disclosure」「inconsistency」
- 客户 system prompt 含受保护字段清单（家庭 / 收入 / 已有保障 / hidden_concerns）

**`test_judge_parse.py`**（约 6 条）：
- 合法 agent JSON → AgentJudgeReport，4 维度全 parse 出
- 合法 customer JSON → CustomerJudgeReport，越界 + 一致性 issues 全 parse 出
- 缺字段（如缺 reasoning）→ 抛 JudgeParseError，error message 含字段名
- 非法 JSON（截断字符串）→ 抛 JudgeParseError
- score 越界（如 score=7）→ 抛 JudgeParseError
- 维度名错误（如 `professionalisma`）→ 抛 JudgeParseError

**`test_judge.py`**（约 6 条）：
- mock client，judge_agent 端到端拿到 AgentJudgeReport
- mock client，judge_customer 端到端拿到 CustomerJudgeReport
- mock client + 真实 evaluate，build_judge_result 三段都对
- judge_agent 不修改入参 messages（纯函数性，不计 LLM 调用）
- mock LLM 抛 OpenAIError → judge 直接抛出，不吞
- import 隔离自检：judge 模块不 import `peilian.dialogue` / `peilian.persona` / `peilian.scenario` / `peilian.prompts`

**`test_judge_render.py`**（约 4 条）：
- render_judge_result 含「规则层评估（P2）」「代理人评分（P3）」「AI 客户行为诊断（P3）」三个段落标题
- render_judge_result 含 4 维度的中文标签
- render_judge_result 含 issue 的 protected_field 与 excerpt
- render_judge_result 在零 issue 时输出「未发现客户行为异常」字样

### §8. 与 P2 / P4 的关系

**与 P2**：
- judge.py import `peilian.observer.evaluate` 与 `peilian.report.EvaluationReport`，但 judge_agent / judge_customer 本身**不**消费 EvaluationReport（Q2 决策）
- `build_judge_result` 在 judge.py 内做合并，是 P2 与 P3 数据流唯一的会合点
- P2 物料一行不改

**与 P4**：
- P4 的 `CustomerState` 会消费 `CustomerJudgeReport`：把"客户在第 N 轮越界泄露了 family_structure"这类 issue 反向反馈到 prompt 层（"以后没问到家庭就别报"）
- 但 P3 **不**为 P4 预先定义 hook / Protocol / 回调；只允许在 judge.py / judge_prompts.py 顶部注释占位（如 `# P4: CustomerState may consume CustomerJudgeReport.premature_disclosure_issues`）
- 与 P2→P3 的"只允许注释占位"节奏一致

---

## 实施任务拆分（轻量 TDD 顺序，沿用 P1/P2 节奏）

| # | 任务 | 备注 |
|---|---|---|
| 1 | 起草 `tests/test_judge_prompts.py` + `test_judge_parse.py` + `test_judge.py` + `test_judge_render.py`（**先于实现**）| import 失败自然 fail |
| 2 | 跑 `pytest`，**确认全部失败**（缺少 judge / judge_prompts 模块）| TDD 红灯 |
| 3 | 实现 `src/peilian/judge_prompts.py`（rubric + 两份 system prompt）| — |
| 4 | 实现 `src/peilian/judge.py`（dataclass + parse + judge_*() + build_judge_result + render）| 依赖 judge_prompts、observer、report |
| 5 | 修改 `src/peilian/conversations.py` 追加 `SAMPLE_CONVERSATION_P3` | 不动 P2 sample |
| 6 | 跑 `pytest`，**确认全部通过** | TDD 绿灯 |
| 7 | 实现 `scripts/demo_p3.py`（强制 LLM key；加载 P3 sample → build_judge_result → 渲染）| — |
| 8 | 实现 `scripts/check_stability_p3.py`（N 次跑；输出方差 / max-min）| 不进 pytest |
| 9 | 修改 `README.md`：加 P3 demo 命令 + 稳定性脚本说明 | — |
| 10 | 用户人工配 LLM key 跑 `python scripts/demo_p3.py`，肉眼验证综合报告内容合理 | 见验收 checklist 「Demo / 稳定性脚本」 |
| 11 | （可选）用户人工跑 `python scripts/check_stability_p3.py`，确认稳定性达标 | 不达标则迭代 prompt |
| 12 | 用户审阅、勾选 checklist | — |
| 13 | 由用户授权 commit（**本阶段不自动 commit**）| 见「commit 策略」一节 |

---

## 已确认决策

以下决策已与用户对齐，实施时按此执行：

### Q1. judge 评分对象切分 → **两份独立 JudgeReport**

`AgentJudgeReport` 评代理人 4 维度 1–5 分；`CustomerJudgeReport` 评 AI 客户的越界泄露与一致性，输出 issue list 不打分。

理由：结构清晰、扩展灵活；P4 接 CustomerState 时只需替换 customer 部分。

### Q2. judge 与 P2 EvaluationReport 的数据流 → **混合：judge 消费 messages，report 拼装时合并**

`judge_agent` / `judge_customer` 只消费 `messages`，不依赖 `EvaluationReport`。`build_judge_result` 在内部顺序执行 `evaluate()` + `judge_agent()` + `judge_customer()`，把三份产物装进 `JudgeResult`。P3 不做并发。

理由：中间层完全解耦，P2 与 P3 各自演化；最终展示时统一为综合报告。

### Q3. 稳定性 ±1 验证形态 → **脚本化 + 真实 LLM**

新增 `scripts/check_stability_p3.py`，对 `SAMPLE_CONVERSATION_P3` 跑 N 次（默认 5）真实 judge，输出每维度方差 / max-min。**不进 pytest**——CI 不烧 LLM 额度。pytest 只用 mock client 测 schema / parsing / 渲染 / 合并。

### Q4. demo_p3.py LLM 依赖 → **强制依赖，不支持 --skip-llm**

无 LLM key 直接报错并指引去 `.env`。理由：judge 的核心价值是真实模型评分，假打分会误导验收。

### Q5. 评分量纲 → **1–5 整数**

代理人 4 维度统一 1–5 整数。理由：易稳定到 ±1；渲染可直观用 ★。

### Q6. 客户诊断输出形态 → **issue list，不打总分**

越界与一致性是离散事件，list 形式保留定位信息；与代理人评分逻辑分开，prompt 也更清晰。

### Q7. judge 文件结构 → **judge_prompts.py + judge.py 两文件**

prompt 文本与接口/parsing 分文件，沿用 P1 的 prompts.py / dialogue.py 拆分思路。dataclass 与 judge 接口同文件（强耦合，不再细拆）。

### Q8. 样本对话 → **新增 SAMPLE_CONVERSATION_P3，不复用 P2**

P2 sample 客户严格被动反应，无越界 / 矛盾，无法让 customer judge 出活。新增 P3 专属 sample，含故意越界与故意矛盾。P2 sample 一行不动。

### Q9. JSON output 约定 → **response_format=json_object + prompt 内 schema**

保留 `response_format={"type": "json_object"}`，prompt 里给出 JSON schema 范例，要求 LLM 严格按 schema 输出。parsing 失败抛 `JudgeParseError` 不重试。如果底层 OpenAI-compatible API 不支持 `response_format`，P3 不做自动降级或重试；demo 层允许抛出清晰错误，提示检查模型 / API 兼容性。

### Q10. P4 hook 预留 → **只允许注释占位，不设计接口**

与 phase-2.md Q8 节奏一致：可写 `# P4: CustomerState may consume ...` 注释，不预先定义 hook 函数签名 / Protocol / 回调列表。

### Q11. Commit 策略 → **两次 commit（沿用 P2 节奏）**

- Commit 1：phase-3.md 单独入库（本份 spec 经审批后立即执行），message: `docs(P3): 起草 phase-3.md 阶段计划`
- Commit 2：P3 实现物料一次性 commit（实现完成 + 人工验收通过 + pytest 全绿后），message: `feat(P3): 实现 LLM-as-Judge 评估`

### Q12. demo_p3.py 不参数化 → **写死使用 `SAMPLE_CONVERSATION_P3`**

不支持 CLI 参数加载其他 fixture。未来要做"批量评估多份历史对话"时再加。

---

## Commit 策略与建议 commit message（按 Q11：两次 commit）

### Commit 1 — phase-3.md 单独入库（本份 spec 经审批后立即执行）

```
docs(P3): 起草 phase-3.md 阶段计划

- LLM-as-Judge 评估 spec：两份独立 JudgeReport（代理人 4 维度 1-5 分 +
  AI 客户越界/一致性 issue list）
- 决策记录：judge 与 P2 数据流解耦 (judge 消费 messages, build_judge_result
  在内部合并 P2 evaluate + P3 judge_*); 1-5 整数量纲; 客户诊断不打总分;
  scripts/check_stability_p3.py 跑真实 LLM 取方差不进 pytest;
  demo_p3 强制依赖 OPENAI_API_KEY; judge_prompts.py + judge.py 两文件;
  新增 SAMPLE_CONVERSATION_P3 (不动 P2 sample); response_format=json_object;
  P4 hook 只允许注释占位; 两次 commit
- 实施任务采用轻量 TDD 顺序 (先写 mock 测试看红灯, 再实现看绿灯,
  人工跑稳定性脚本验证)
```

### Commit 2 — P3 实现物料（实现完成 + 人工验收通过 + pytest 全绿后执行）

```
feat(P3): 实现 LLM-as-Judge 评估

- 新增 src/peilian/judge_prompts.py: 代理人 4 维度 rubric (话术专业度/
  共情度/逻辑结构/异议处理) 含 1/3/5 分尺度文本 + 客户诊断 rubric (越界泄露
  + 一致性) + 两份 system prompt (强制 JSON 输出, 含 schema 范例)
- 新增 src/peilian/judge.py: 5 个 frozen dataclass (DimensionScore /
  AgentJudgeReport / Issue / CustomerJudgeReport / JudgeResult) +
  judge_agent / judge_customer / build_judge_result + parse 帮助 +
  render_judge_result (三段标题); JudgeParseError; 与 dialogue 物理隔离
  (不 import Dialogue / persona / scenario / prompts)
- 修改 src/peilian/conversations.py: 追加 SAMPLE_CONVERSATION_P3
  (含故意越界 + 故意矛盾, 给 customer judge 出活); P2 sample 一行不动
- 新增 scripts/demo_p3.py: 强制 LLM key, 加载 P3 sample → build_judge_result →
  打印综合报告 (P2 + 代理人评分 + 客户诊断)
- 新增 scripts/check_stability_p3.py: 默认 5 次跑真实 judge, 输出每维度
  方差 / max-min; 不进 pytest
- 新增 tests/test_judge_prompts.py / test_judge_parse.py / test_judge.py /
  test_judge_render.py: mock LLM client, 不调真实 LLM; 覆盖 prompt 关键约束 /
  parse 合法非法路径 / 端到端 mock judge / 渲染三段标题
- 更新 README.md: 加 P3 demo 命令 + 稳定性脚本说明

人工验证: SAMPLE_CONVERSATION_P3 综合报告输出符合预期
(P2 段 3/6 覆盖率 0 红线; 代理人段 4 维度有合理打分; 客户段识别 ≥2 越界 +
≥1 一致性问题); check_stability_p3.py 跑 5 次方差 ≤ 1
```

---

## 完成条件

1. 验收 checklist 全部勾选
2. 用户人工跑过 `python scripts/demo_p3.py`，确认综合报告内容符合预期
3. （可选）用户人工跑过 `python scripts/check_stability_p3.py`，确认每维度 max-min ≤ 1
4. `pytest` 全绿（mock 测试，不烧 LLM 额度）
5. 由用户授权后 commit

---

## 进入 P4 的前置条件（仅作占位，不在 P3 内执行）

- 本阶段所有验收项通过
- 用户显式指示切换游标
- 切换时由用户在 ROADMAP 把 P3 改为「✅ 已完成」并把游标移到 P4
- 启动 P4 时再起草 `phase-4.md`（**P3 内不创建该文件**）
- P4 起草时优先消费 P3 `CustomerJudgeReport.premature_disclosure_issues` 作为 CustomerState 设计的一手输入
