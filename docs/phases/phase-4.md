# Phase 4 — Persona 工厂 + CustomerState

> 状态：计划阶段（待用户审阅本 spec）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-3.md`](phase-3.md) ✅
> 上一阶段产物可消费：`CustomerJudgeReport.premature_disclosure_issues`（AI 客户越界泄露的量化输入）

---

## P4 目标

**把客户"演得真"这件事做扎实**——从配置化生成多种客户画像，到运行时动态追踪客户状态，让 AI 客户在同一个陪练会话内：

1. **不遗忘已说过的话**（不会同一轮说已婚下一轮说单身）
2. **不主动暴露未触发信息**（代理人不问就不报；即使泛泛提问也只回答被点名的那一项）
3. **隐藏关切按节奏释放**（未触发→已触发→暗示→表达，不是一句话和盘托出）

**架构铁律继承自 [CLAUDE.md §2.1 / §2.2](../../CLAUDE.md)**：

> - 代理人驱动，AI 客户严格被动反应
> - CustomerState 只约束"可说/不可说/说到什么程度"，**不**按剧本强行推进话题
> - 状态观察器（含 P3 judge）**绝不**参与生成客户回复

P4 从"静态 persona → 注入 prompt 就完事"升级到"动态 persona → 状态追踪 → 逐步释放"。

---

## 用户故事

### 业务侧
```
作为一名陪练系统的开发者 / 培训主管，
我希望  一组 yaml 配置文件就能生成至少 5 种行为差异可观测的客户画像，
并且  能选择难度档（简单/中等/困难），让我观察不同坚持度与信息隐藏度下代理人的表现差异，
以便  快速覆盖不同客户类型的陪练场景，而不需要每次都手写 Python 字典。
```

```
作为一名陪练系统的使用者（代理人），
我希望  同一个客户在我问到不同轮次时，不会"失忆"——之前说过的信息能自然引用，
并且  没问到的事不会自己冒出来，
以便  陪练体验接近真实客户，训练价值高。
```

### 测试侧
```
作为开发者，
我希望  pytest 不烧 LLM 额度就能测 Persona 工厂的生成逻辑与 CustomerState 的状态迁移，
能够  用 mock 或纯函数测试覆盖状态正确性，
也希望  有 demo 脚本让我手动验证 5 种 persona 的对话行为差异。
```

---

## 纵切范围

- **Persona yaml schema**（`personas/*.yaml`）：基础属性、痛点、**结构化 hidden_concerns（key + label + keywords + initial_stage）**、性格参数、坚持度、对话开场
- **Persona 工厂**：`load_persona_from_yaml(path) -> Persona`、`load_personas_from_dir(dir) -> list[Persona]`，从 yaml 生成 frozen dataclass
- **难度档分级**：easy / medium / hard 三档，对 persistence / expressiveness 做**线性缩放 + clip 到 [0,1]**（具体公式见 §2）
- **CustomerState v1**：记录已披露字段（`disclosed_fields`）、本轮代理人点名了哪些字段（`asked_fields_this_turn`）、隐藏关切状态机（未触发/已触发/暗示/表达）、信任度与耐心值
- **生成前状态摘要注入**：把 CustomerState 转成面向 LLM 的**短约束文本（≤ 400 字）**，每轮重新渲染 system prompt
- **生成后状态更新**：根据代理人提问与客户回复，更新已披露字段、隐藏关切触发/表达进度、信任度、耐心值
- **新增样本 persona set**：至少 5 份 yaml，覆盖不同年龄 / 收入 / 坚持度 / 隐藏关切组合
- **CLI demo**：`python scripts/demo_p4.py` 加载 yaml persona set，选择 persona + 难度档，启动陪练对话；退出后打印每轮 CustomerState 变化日志
- **测试**：Persona 工厂加载与校验 / CustomerState 状态迁移 / state_summary 长度与措辞约束 / prompt 含状态摘要 / dialogue.reset 同步重置 state / 未修改 P3 judge 模块

---

## 建议目录结构（增量）

只列出 P4 新增/修改的部分：

```
PeiLian/
├── personas/                          # 新增：客户画像 yaml 集合
│   ├── price_sensitive_midcareer.yaml
│   ├── trust_issue_sme_owner.yaml
│   ├── young_family_new_parent.yaml
│   ├── nearing_retirement.yaml
│   └── high_net_worth_skeptic.yaml
├── src/peilian/
│   ├── persona_factory.py             # 新增：yaml → Persona dataclass 工厂 + 难度缩放
│   ├── customer_state.py              # 新增：CustomerState dataclass + 状态迁移逻辑（纯函数）
│   ├── state_summary.py               # 新增：CustomerState → LLM 可读摘要（≤ 400 字、被动语态）
│   ├── dialogue.py                    # 修改：每轮重渲 system prompt 注入 state_summary + 生成后调 update_state；reset 同步重置 state
│   ├── prompts.py                     # 修改：模板增加 {state_summary} 占位符（默认空串，向后兼容）
│   └── observer.py                    # 修改：提取 match_mandatory_categories()，evaluate 行为不变
├── scripts/
│   └── demo_p4.py                     # 新增：加载 yaml，选择 persona + 难度，启动陪练；退出后打印每轮 state 变化
├── pyproject.toml                     # 修改：dependencies 增加 pyyaml>=6
└── tests/
    ├── test_persona_factory.py         # 新增：yaml 加载 / schema 校验 / 5 种 persona / 难度缩放 + clip
    ├── test_customer_state.py          # 新增：状态迁移 / 进度释放 / 重复问幂等 / 边界条件
    ├── test_state_summary.py           # 新增：摘要长度 ≤ 400 / 被动措辞 / 含未披露字段清单 / 隐藏关切阶段
    ├── test_dialogue_state_injection.py # 新增：mock LLM 验证 system prompt 每轮重渲含最新 state_summary；reset 同步重置
    └── test_observer.py / test_rules.py # 修改：守护 P2 匹配函数提取前后行为一致
```

> **不动 P3 物料**：`judge.py` / `judge_prompts.py` 一行不改。
>
> **不动 P3 测试**：`test_judge*.py` 全部保留，不作修改。
>
> **不修改 `demo_p1.py` / `demo_p2.py` / `demo_p3.py`**：P4 只新增 `demo_p4.py`。

---

## 计划创建/修改的文件

| # | 文件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `personas/*.yaml`（5 份）| 新增 | 客户画像 yaml 配置文件，含结构化 hidden_concerns（key/label/keywords/initial_stage） |
| 2 | `src/peilian/persona_factory.py` | 新增 | yaml 加载 → Persona dataclass；schema 校验；难度档线性缩放 + clip |
| 3 | `src/peilian/customer_state.py` | 新增 | CustomerState frozen dataclass + `update_state()` 纯函数 |
| 4 | `src/peilian/state_summary.py` | 新增 | CustomerState → prompt 摘要文本（≤ 400 字、被动语态） |
| 5 | `src/peilian/dialogue.py` | 修改 | `_render_system_prompt()` 提取；每轮 `send_user` 前覆写 `messages[0]`；生成后调 `update_state()`；`reset()` 同步重置 |
| 6 | `src/peilian/prompts.py` | 修改 | `render_customer_system_prompt` 增加可选 `state_summary` 参数 + template 加 `{state_summary}` 占位 |
| 7 | `src/peilian/observer.py` | 修改 | 提取公开纯函数 `match_mandatory_categories(text)`；`evaluate()` 行为不变 |
| 8 | `pyproject.toml` | 修改 | dependencies 增加 `pyyaml>=6` |
| 9 | `scripts/demo_p4.py` | 新增 | 加载 yaml → 选 persona + 难度 → 对话；退出后打印每轮 state 变化 |
| 10 | `tests/test_persona_factory.py` | 新增 | 工厂加载 / schema 校验 / 5 种 persona / 难度缩放 + clip 边界 |
| 11 | `tests/test_customer_state.py` | 新增 | 状态迁移 / 进度释放 / 重复问幂等 / patience 衰减 |
| 12 | `tests/test_state_summary.py` | 新增 | 摘要长度 ≤ 400 / 被动语态 / 含未披露字段清单 / 含隐藏关切阶段 |
| 13 | `tests/test_dialogue_state_injection.py` | 新增 | mock LLM 验证 system prompt 每轮重渲含最新摘要；难度档差异反映在 prompt 数值；reset 同步重置 state |
| 14 | `tests/test_observer.py` / `tests/test_rules.py` | 修改 | 守护 `match_mandatory_categories()` 与 P2 既有覆盖率行为一致 |
| 15 | `README.md` | 修改 | 加 P4 demo 命令 + personas/ 说明 |

> **明确不做**：
> - 不改对话循环骨架（仍是 `send_user(text) → 调 LLM → 存 messages`）；只改 system prompt 渲染时机（一次性 → 每轮重渲）和 `send_user` 末尾追加一行 `update_state()`
> - 不在运行时消费 P3 `CustomerJudgeReport`（P3 仅作离线设计期参考，详见 §7）
> - 不修改 P3 judge / judge_prompts（P3→P4 数据流已解耦）
> - 不修改 `persona.py` 的现有 `Persona` dataclass 字段（维持 P1/P2/P3 兼容；hidden_concerns 仍是 `tuple[str, ...]`，结构化 key 由 `persona_factory.py` 内部维护额外索引）
> - 不做对话内的多分支选择（不根据状态主动推进话题）
> - 不做持久化 CustomerState 到磁盘（暂存内存）
> - 不引入 `pyyaml` 之外的新依赖

---

## Demo 命令

```powershell
# 加载 yaml persona set，启动陪练对话
python scripts/demo_p4.py

# 指定 persona 文件和难度
python scripts/demo_p4.py --persona price_sensitive_midcareer --difficulty hard

# 跑测试（P4 测试不调用真实 LLM）
pytest

# 交互内观察：同一客户不会遗忘已披露信息，隐藏关切按节奏释放
```

预期 demo 行为：

1. 程序列出可用的 persona 清单（`personas/` 目录下所有 yaml）
2. 用户选择 persona 和难度档（简单/中等/困难）
3. 进入多轮 CLi 对话；AI 客户按 `CustomerState` 约束逐步释放信息
4. `/quit` 退出；可在退出后查看本轮 CustomerState 摘要（已披露字段、隐藏关切状态）

---

## 验收 Checklist

**结构 / 文件**
- [ ] 上述 15 个新增/修改文件全部到位（含 `pyproject.toml` 加 `pyyaml>=6`）
- [ ] **未**修改 `persona.py`（Persona dataclass 字段）、`judge.py`、`judge_prompts.py`
- [ ] **未**修改 P1/P2/P3 demo 脚本
- [ ] **未**创建 P5+ 物料（RAG、web 等）
- [ ] `customer_state.py` / `dialogue.py` / `state_summary.py` 都**未** import `peilian.judge` 或 `peilian.judge_prompts`（运行时与 P3 解耦的物理校核）

**Persona 工厂**
- [ ] 至少 5 份 yaml，每份生成有效 `Persona` 实例
- [ ] yaml 字段包括：name / age / occupation / family / income_level / existing_coverage / pain_points / **hidden_concerns（结构化：key + label + keywords + initial_stage）** / persistence / expressiveness / initial_mood
- [ ] hidden_concerns key 校验：`[a-z][a-z0-9_]*`；同一 persona 内不重复
- [ ] hidden_concerns keywords 校验：每条至少 1 个非空关键词，用于状态机触发；keywords 不进入 `Persona.hidden_concerns` 文本展示
- [ ] 工厂函数校验 persistence/expressiveness 在 [0,1] 范围内
- [ ] 难度档单调性：同一 yaml 在 easy / medium / hard 三档下 persistence 单调不减、expressiveness 单调不增
- [ ] 难度档越界处理：缩放后超出 [0,1] 时 clip（如 0.9 × 1.3 → 1.0）
- [ ] `get_persona_meta(persona)` 能回查到结构化 hidden_concerns（key/label/keywords/initial_stage）

**CustomerState**
- [ ] `CustomerState` 为 frozen dataclass，包含：
  - `disclosed_fields: frozenset[str]` — 已披露字段
  - `asked_fields_this_turn: frozenset[str]` — 本轮代理人点名的字段
  - `hidden_concern_stage: frozenset[tuple[str, str]]` — 隐藏关切阶段（frozen 友好类型，**不用** dict）
  - `trust: float` — 信任度 0-1
  - `patience: float` — 耐心值 0-1
  - `turn_count: int`
- [ ] `CustomerState.initial(persona, persona_meta)` 公式：trust = clip(0.6 - 0.4 × persistence, 0.1, 0.9)；patience = 1.0；turn_count = 0
- [ ] `update_state()` 纯函数：不调 LLM；签名 `(state, agent_message, customer_response, *, persona, persona_meta) -> CustomerState`
- [ ] 隐藏关切迁移路径：`untouched → triggered → hinted → expressed`，**单轮最多推进一档**
- [ ] 已披露字段增量为幂等：同一字段多次披露不重复计数
- [ ] 客户主动报未问字段：`disclosed_fields` 不增加
- [ ] 面对泛泛提问（如"想了解你的情况"），`asked_fields_this_turn` 为空集；面对 P2 粗粒度命中但非具体点名的话术（如"想了解你的家庭情况"），P4 具体点名过滤可将其降级为未点名
- [ ] 合规红线词出现在 agent_message → trust -0.10

**状态摘要注入**
- [ ] `render_state_summary()` 输出 `len(text) ≤ 400` 字
- [ ] 摘要包含：
  - 当前未披露字段清单（被动语态："尚未被代理人问到"）
  - 已披露字段（可自然引用）
  - 各隐藏关切当前阶段与被动语态描述（"如代理人再次触及，可 …"）
  - 信任度 / 耐心值数值与内心状态描述（不指示行动）
- [ ] **措辞守护**：摘要文本不含禁用词（"可以披露"、"现在可以说"、"主动表达"、"主动说出来"等）
- [ ] 摘要文本注入到 `render_customer_system_prompt` 的 `{state_summary}` 占位
- [ ] `state_summary=""` 时 `render_customer_system_prompt` 行为与 P1/P2/P3 一致（向后兼容）

**dialogue 集成**
- [ ] 每次 `send_user` 调用前 `messages[0]` 被覆写为最新 system prompt
- [ ] `send_user` 末尾调用 `update_state` 推进 `self._customer_state`
- [ ] `Dialogue.reset()` 同时重置 `customer_state` 与 `messages[0]`
- [ ] `persona_meta=None` 时 P1/P2/P3 demo 行为完全一致（向后兼容）

**Demo / 测试**
- [ ] `python scripts/demo_p4.py` 可交互跑通；列出 `personas/` 下 yaml；支持 `--persona` / `--difficulty`
- [ ] demo 在无 LLM key 时报错并引导配置 .env
- [ ] demo 退出时打印每轮 `CustomerState` 变化日志（disclosed_fields 增量、hidden_concern_stage 迁移）
- [ ] **人工观察项**：跑同一份 persona 的 easy 与 hard 档，客户回答风格能感觉到差异（坚持度、信息隐藏度）
- [ ] **人工观察项**：跑 5 份 persona 的 medium 档，能感觉到 5 种不同的客户特征
- [ ] `pytest` P4 测试全绿（mock / 纯函数测试，不调 LLM）
- [ ] `pytest` 全量测试（含 P0-P3）通过；P3 测试不受影响

**Git**
- [ ] 至少两个 commit（spec 起草 + 实现物料），message 第一行含 `Phase 4` 或 `P4`
- [ ] 工作区干净

---

## 不在 P4 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| 产品条款 RAG 知识库 | **P5** |
| Web UI / 可视化报告 | **P6** |
| 错题本 / 弱项画像 / 自适应难度 | **P7** |
| 对话内多分支主动推进（CustomerState 只约束不调度）| 永远不会（架构铁律）|
| CustomerState 持久化到磁盘 | P7 错题本阶段 |
| 多人同时陪练 / 会话管理 | P6 Web UI 阶段 |
| 修改 `CLAUDE.md` | 本阶段无需改动宪法 |
| 修改 P3 judgement 流程 | P3 物料只读不写 |

---

## 技术设计要点

### §1. Persona yaml schema

每份 yaml 对应一个 `Persona` 实例。基础字段与现有 `Persona` dataclass 对齐；`hidden_concerns` **在 yaml 中是结构化对象**（含稳定 key 与触发 keywords），便于 CustomerState 跟踪状态机；`persona_factory.py` 在生成 frozen `Persona` 时把它**降维成 `tuple[str, ...]`**（保持 P1/P2/P3 dataclass 兼容），同时把 `(key, label, keywords, initial_stage, source_path, difficulty)` 索引另存到工厂内部映射，供 `customer_state.initial(persona, persona_meta)` 消费。

```yaml
# personas/price_sensitive_midcareer.yaml
name: "张先生"
age: 35
occupation: "IT 公司中层"
family: "已婚，一个 5 岁孩子"
income_level: "中产"
existing_coverage:
  - "百万医疗险（公司团险）"
pain_points:
  - "对保险了解不深"
  - "时间紧、希望直接说重点"
hidden_concerns:
  - key: price_sensitive
    label: "担心保费太贵影响房贷"
    keywords: ["价格", "保费", "预算", "房贷", "贵"]
    initial_stage: untouched
  - key: refuse_long_health_disclosure
    label: "不希望做太详细的健康告知"
    keywords: ["健康告知", "体检", "病史", "问太细"]
    initial_stage: untouched
persistence: 0.7
expressiveness: 0.5
initial_mood: "略微戒备但礼貌"
```

**字段约束**：
- `hidden_concerns[*].key`：`[a-z][a-z0-9_]*` 蛇形命名，5 份 yaml 全集内允许重名（同一类关切跨 persona 复用 key），单 persona 内 key 不重复
- `hidden_concerns[*].keywords`：非空字符串列表，用于 CustomerState 判断是否被触发；避免用整句 label 做脆弱子串匹配
- `hidden_concerns[*].initial_stage`：必须是 `untouched / triggered / hinted / expressed` 之一；P4 默认全部 `untouched`
- `persistence` / `expressiveness`：`[0.0, 1.0]` 浮点

5 份 yaml 覆盖（每份至少 2 条 hidden_concerns 草稿示例，最终内容实施时定稿）：

| 文件名 | 核心特征 | hidden_concerns 草稿（key） |
|---|---|---|
| `price_sensitive_midcareer.yaml` | 价格敏感中年 | `price_sensitive` / `refuse_long_health_disclosure` |
| `trust_issue_sme_owner.yaml` | 信任问题小企业主 | `distrust_industry` / `peer_comparison` |
| `young_family_new_parent.yaml` | 年轻新父母 | `low_budget` / `procrastination` |
| `nearing_retirement.yaml` | 临近退休 | `existing_coverage_overlap` / `future_plan_hesitation` |
| `high_net_worth_skeptic.yaml` | 高净值怀疑型 | `value_skepticism` / `high_persistence_objection` |

---

### §2. Persona 工厂

```python
# src/peilian/persona_factory.py 伪代码接口

def load_persona_from_yaml(path: str, *, difficulty: str = "medium") -> Persona:
    """从单个 yaml 文件加载 Persona，按难度档线性缩放 persistence/expressiveness 并 clip 到 [0,1]。"""

def load_personas_from_dir(dir_path: str = "personas", *, difficulty: str = "medium") -> list[Persona]:
    """加载目录下所有 yaml，按难度档统一缩放。"""

def get_persona_meta(persona: Persona) -> PersonaMeta:
    """取出工厂内部维护的额外索引（hidden_concerns 的 key/label/keywords/initial_stage 列表）。
    
    Persona dataclass 本身只存 hidden_concerns: tuple[str, ...]（label 列表，与 P1/P2/P3 兼容），
    结构化索引由工厂在 load 时建立。
    实现不得只按 persona.name 查回；应以 Persona 实例本身或 (source_path, difficulty, name)
    组成的稳定 key 防止同名 persona / 不同难度重复加载时互相覆盖。
    """

def adjust_difficulty_values(persistence: float, expressiveness: float, difficulty: str) -> tuple[float, float]:
    """纯函数：按档位缩放并 clip。"""
```

**难度档缩放规则（线性缩放 + clip）**：

| 难度 | persistence 缩放 | expressiveness 缩放 | 越界处理 | 行为特征 |
|---|---|---|---|---|
| easy | × 0.5 | × 1.3 | clip 到 [0,1] | 容易被说服，信息主动度略高 |
| medium | × 1.0（保持原值）| × 1.0（保持原值）| — | 标准行为 |
| hard | × 1.3 | × 0.7 | clip 到 [0,1] | 不易被说服，信息隐藏度更高 |

**关键约束（避免与早期"区间锚定"叙述冲突）**：
- 不强制"easy 必须落在 0.2-0.4"等区间；只保证**同一份 yaml 在 easy/medium/hard 三档的输出值单调有序**（easy.persistence ≤ medium.persistence ≤ hard.persistence；expressiveness 反向）
- clip 后若 easy/medium 出现相同值（极端边界），允许；测试只校核单调性而非严格区间
- 公式参数为经验值，可在 P7 自适应难度阶段进一步调优

**Persona dataclass 不修改**：`persona.py` 现有 `Persona` 字段保持不变。工厂产出的是同一个 frozen dataclass 实例。`hidden_concerns` 在 dataclass 中仍是 `tuple[str, ...]`（labels），结构化 key 索引由工厂内部维护。

---

### §3. CustomerState dataclass

**字段全集来源**：`MANDATORY_QUESTION_RULES.keys()`（P2 已定义的 6 类：`family_structure / occupation / income / existing_coverage / future_planning / health_status`）。这与 P2 关键词匹配的"全集"自动对齐，避免双源维护。

```python
@dataclass(frozen=True)
class CustomerState:
    # 已披露字段集合（key 来自 MANDATORY_QUESTION_RULES.keys()）
    disclosed_fields: frozenset[str]

    # 本轮代理人点名了哪些字段（每轮 update_state 重写一次）
    asked_fields_this_turn: frozenset[str]

    # 隐藏关切状态机：(concern_key, stage) 元组的 frozenset
    # stage ∈ {"untouched", "triggered", "hinted", "expressed"}
    # 用 frozenset[tuple[str, str]] 而非 dict，保持 frozen dataclass 真正不可变
    hidden_concern_stage: frozenset[tuple[str, str]]

    # 信任度 0.0-1.0（初始公式：clip(0.6 - 0.4 * persona.persistence, 0.1, 0.9)）
    # 直觉：persistence 越高 → 初始越戒备 → trust 越低
    trust: float

    # 耐心值 0.0-1.0（初始恒为 1.0；多轮无进展扣减）
    patience: float

    # 已经历对话轮次（每次 update_state +1）
    turn_count: int

    @classmethod
    def initial(cls, persona: Persona, persona_meta: PersonaMeta) -> "CustomerState":
        """从 persona + 工厂额外索引构造初始状态。"""
        ...

    def stage_of(self, concern_key: str) -> str:
        """便捷读取某 hidden_concern 的当前 stage；不存在返回 'untouched'。"""
        ...
```

**状态迁移函数（纯函数，不调 LLM）**：

```python
def update_state(
    state: CustomerState,
    agent_message: str,
    customer_response: str,
    *,
    persona: Persona,
    persona_meta: PersonaMeta,
) -> CustomerState:
    """根据代理人本轮发言 + 客户本轮回复，返回新的 CustomerState。

    规则（全部基于关键词匹配 / 子串包含，不调 LLM）：
    1. coarse_fields = match_mandatory_categories(agent_message)
       asked_fields_this_turn = filter_specific_asked_fields(agent_message, coarse_fields)
       （P2 粗粒度匹配只判断"覆盖过哪个 KYC 类别"；P4 还要过滤是否具体点名。
        泛泛提问如"想了解你的情况"不匹配任何关键词 → 空集；
        "想了解你的家庭情况"可被 P2 计入 family_structure 覆盖，但 P4 可过滤为未具体点名，
        让客户模糊回应或反问，而不是和盘托出。）
    2. disclosed_fields ∪= 客户回复中命中的字段 ∩ 已被问过的字段
       （即：客户主动报了未问的字段，state 不标记为 disclosed；这是合规设计：
        反馈到 prompt 时，未 disclosed 的字段会出现在"不应主动披露"清单里）
    3. hidden_concern_stage 迁移：对每条 hidden_concern，按 yaml keywords 在
       agent_message + customer_response 中的命中情况推进一档（最多推进一档/轮）：
       - untouched → triggered：agent_message 触及该关切关键词
       - triggered → hinted：customer_response 含模糊表达词（如"有点担心"、"还在想"）
       - hinted → expressed：customer_response 含明确表达词（如"我担心 ___"完整句）
    4. 信任度调整：
       - 代理人提问命中 ≥ 1 个 P2 必问点 → +0.02
       - 代理人发言出现 P2 合规红线词 → -0.10
       - 否则不变
       （不再用模糊的"问得专业"判定；规则化、可机械验证）
    5. 耐心值调整：
       - asked_fields_this_turn 为空 且 turn_count > 0 → -0.03
       - asked_fields_this_turn 非空 → +0.01
       - 同样 clip 到 [0, 1]
    6. turn_count += 1
    7. 重复问同一字段（已在 disclosed_fields 中）→ 第 2、3 条幂等不重复，
       但 patience 仍按第 5 条变化（避免代理人复读规避扣分）
    """
```

**关键设计决策**：

- Agent message 中的粗粒度字段命中判定**复用 P2 `_scan_mandatory` 核心**（不重复发明匹配器）：将 `peilian.observer._scan_mandatory` 提取为公开 `match_mandatory_categories(text) -> frozenset[str]`，并加 P2 测试守护
- P4 在粗粒度命中后再做 `filter_specific_asked_fields()`：把"家庭情况 / 保障情况 / 你的情况"这类宽泛话术与"几口人 / 有没有保单 / 收入多少"这类具体点名区分开，防止 P2 覆盖率词库直接变成客户披露许可
- 泛泛提问（如"想了解你的情况"）不匹配任何具体字段关键词，不算"点名"
- 信任度 / 耐心值的变化幅度是**经验值**，可在 P7 自适应难度阶段调
- hidden_concern 阶段推进**只看实际触发证据**（关键词命中），**不按轮次自动推进**——这是守住 CLAUDE.md §2.2 的关键

---

### §4. 状态摘要注入

`state_summary.py` 把 `CustomerState` 转成面向 LLM 的**短约束文本（≤ 400 字）**，所有"允许程度"措辞采用**被动语态**，避免 LLM 解读为"可以主动表达"：

```
def render_state_summary(
    state: CustomerState,
    persona: Persona,
    persona_meta: PersonaMeta,
) -> str:
    """生成注入到 system prompt 的文本片段。
    
    长度约束：函数返回的字符串 len() ≤ 400 字（含中英标点）。
    超长时截断"隐藏关切"列表（保留状态非 untouched 的项），并在末尾加省略提示。
    
    形如（示例）：
    【本轮对话状态】
    已被代理人问到并披露：职业、家庭结构
    尚未被代理人问到（不要主动提）：收入水平、已有保障、健康情况
    隐藏关切：
      - 价格敏感：已被触发并暗示过；如代理人再次触及，可保持模糊，不要完整说出来
      - 信任问题：尚未被触发；不要主动提及
    当前信任度：0.4（偏低，保持戒备语气）
    当前耐心值：0.95（充足）
    """
```

**措辞约束（写死在实现 + 测试守护）**：
- 描述未披露字段：用「**尚未被代理人问到（不要主动提）**」，禁止出现「可以披露」「现在可以说」等主动语态
- 描述 hidden_concern 阶段：用「**如代理人再次触及，可 …**」「**尚未被触发；不要主动提及**」，禁止「现在可以表达」「主动说出来」
- 信任度 / 耐心值：只描述客户**当前内心状态**，不指示行动（如「保持戒备语气」OK，「主动催进度」不 OK）

**注入点**：`render_customer_system_prompt(persona, scenario, *, state_summary: str = "")` 的 template 新增 `{state_summary}` 占位。

**向后兼容**：`state_summary=""` 时占位渲染为空字符串（或一行注释），与现有 P1/P2/P3 行为完全一致，不影响已有 demo。

---

### §5. dialogue.py 集成点

**现状基线（实读 `src/peilian/dialogue.py`）**：
- 当前没有 `_build_system_prompt()` / `_get_ai_response()` 方法
- system prompt 在 `__init__` 中**一次性渲染**为 `self._system_prompt` 并固化为 `self.messages[0]`
- 对话循环在 `send_user(text)` 一个方法里完成：append user → 调 LLM → append assistant
- `reset()` 把 `self.messages` 还原成单元素 `[{system}]`

**P4 集成方案（动态注入策略：每轮覆写 `messages[0]`）**：

二选一中确定采用 **A 案：每次 `send_user` 调用前覆写 `self.messages[0]`** 作为 system prompt 的最新版本。理由：

| 方案 | 优 | 劣 | 选择 |
|---|---|---|---|
| **A. 覆写 `messages[0]`** | 不污染 user/assistant 流；P3 judge 看到的对话流干净；不影响合规扫描 | 偏离"system prompt 一次性固化"假设；调试时需注意 messages[0] 会变 | ✅ 采用 |
| B. 末尾追加 system 消息 | system prompt 真静态 | 污染 messages 序列；P3 judge 与 P2 observer 都需感知"伪 system 提示"；额外维护成本高 | ❌ 弃用 |

**实施细节**：

```python
class Dialogue:
    def __init__(self, persona, scenario, settings, *, persona_meta=None):
        # ... 原有 client/model 初始化 ...
        self._persona = persona
        self._scenario = scenario
        self._persona_meta = persona_meta  # P4 新增；P1/P2/P3 调用方传 None 时降级到无 state_summary
        self._customer_state = (
            CustomerState.initial(persona, persona_meta) if persona_meta else None
        )
        self.messages = [{"role": "system", "content": self._render_system_prompt()}]

    def _render_system_prompt(self) -> str:
        """每轮调用前重新渲染。state_summary 为空时与 P1/P2/P3 行为一致。"""
        summary = ""
        if self._customer_state is not None:
            summary = render_state_summary(self._customer_state, self._persona, self._persona_meta)
        return render_customer_system_prompt(
            self._persona, self._scenario, state_summary=summary
        )

    def send_user(self, text: str) -> str:
        # P4: 每轮调用前刷新 system prompt（messages[0] 覆写）
        self.messages[0] = {"role": "system", "content": self._render_system_prompt()}
        self.messages.append({"role": "user", "content": text})
        response = self._client.chat.completions.create(...)
        answer = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": answer})
        # P4: 生成后状态更新
        if self._customer_state is not None:
            self._customer_state = update_state(
                self._customer_state, text, answer,
                persona=self._persona, persona_meta=self._persona_meta,
            )
        return answer

    def reset(self) -> None:
        # P4: 同步重置 customer_state，保持与新会话一致
        if self._persona_meta is not None:
            self._customer_state = CustomerState.initial(self._persona, self._persona_meta)
        self.messages = [{"role": "system", "content": self._render_system_prompt()}]

    @property
    def customer_state(self) -> CustomerState | None:
        return self._customer_state
```

**侵入度承诺修订**（替换原"最小侵入"措辞）：
- 对话循环**骨架不变**（仍是 user → LLM → assistant 三步走）
- system prompt 渲染时机由"一次性"改为"每轮"，这是**必要侵入**，不是 bug
- `persona_meta=None` 时 P1/P2/P3 行为完全一致（向后兼容守护：测试中保留 P1 demo 路径不传 `persona_meta`）

---

### §6. 测试设计

**`test_persona_factory.py`**（约 8 条）：
- 单文件 yaml 加载 → 有效 Persona
- 目录加载 → 5 份全部成功；每份 hidden_concerns 至少 2 条且 key 唯一
- persistence / expressiveness yaml 值越界（如 1.2）→ raise ValueError
- hidden_concerns 缺 key / keywords 字段 → raise KeyError；key 不符合命名规则或 keywords 为空 → raise ValueError
- 缺失必填字段 yaml → raise KeyError
- 难度档缩放：easy 将 persistence 0.7 → 0.35；hard 将 persistence 0.9 → clip(1.17, 0, 1) = 1.0
- 难度档单调性：对同一 yaml，easy.persistence ≤ medium.persistence ≤ hard.persistence；expressiveness 反向
- loader 返回的 Persona 是 frozen；`get_persona_meta(persona)` 能回查到结构化 hidden_concerns；同名 persona / 不同 difficulty 重复加载不会取错 meta

**`test_customer_state.py`**（约 8 条）：
- 初始状态：所有字段未披露；hidden_concern_stage 全部 untouched；trust = clip(0.6 - 0.4*persistence, 0.1, 0.9)；patience = 1.0
- 代理人点名 occupation 关键词 → asked_fields_this_turn = {"occupation"}；disclosed_fields 含 occupation
- P2 粗粒度命中但非具体点名的话术（如"想了解你的家庭情况"）→ P2 可计覆盖，P4 asked_fields_this_turn 可为空
- 客户主动报未问字段 → disclosed_fields **不增加**（被动反应原则的状态层验证）
- 隐藏关切迁移：untouched → triggered（agent 触及关键词）→ hinted（客户模糊词）→ expressed（客户完整表达）线性推进
- 隐藏关切单轮最多推进一档（防止一轮跳两档）
- 耐心值衰减：连续 3 轮 asked_fields 为空 → patience ≈ 1.0 - 3×0.03 = 0.91
- 同一字段重复问到（已 disclosed）→ disclosed_fields 幂等不重复；patience 仍按规则变化（不允许复读规避扣分）
- 合规红线词出现在 agent_message → trust -0.10

**`test_state_summary.py`**（约 6 条）：
- 摘要长度 `len(text) ≤ 400`
- 摘要含未披露字段清单（用 P2 中文标签）
- 摘要含每个 hidden_concern 的当前阶段与被动语态描述
- 摘要含信任度 / 耐心值数值
- 初始状态摘要不含任何"已披露"字段
- **措辞守护**：摘要不出现禁用词（"可以披露"、"现在可以说"、"主动表达"、"主动说出来"等关键词列表）

**`test_dialogue_state_injection.py`**（约 5 条）：
- mock LLM client，首轮 `send_user` 时 `messages[0]` 含 `render_state_summary` 输出（无已披露字段段落）
- 多轮 `send_user` 后 `messages[0]` 反映最新状态（含已披露字段）
- `persona_meta=None` 时向后兼容（P1 路径），`render_state_summary` 不被调用，messages[0] 与 P1 一致
- `dialogue.reset()` 后 `customer_state` 回到初始；`messages[0]` 同步重渲
- 同一 persona 不同难度档（easy / hard）→ system prompt 中 persistence / expressiveness 数值显著不同（人工眼见为实，行为差异由 LLM 反映；本测试只校核 prompt 层数值）

**P2 兼容测试补充**：
- `match_mandatory_categories(text)` 对既有 P2 关键词返回与 `_scan_mandatory` 等价的 category 集合
- `evaluate(messages)` 的 covered / missed / compliance 结果与提取前保持一致

---

### §7. 与 P2 / P3 的关系

**与 P2**：
- CustomerState 的字段匹配规则**复用 P2 关键词逻辑**：将 `peilian.observer._scan_mandatory(content, covered)` 的核心提取为新的公开纯函数 `match_mandatory_categories(text) -> frozenset[str]`，`_scan_mandatory` 内部调用它（保持 P2 行为不变，加 P2 测试守护新函数）
- `report.py` / `evaluate()` 不修改
- `evaluate()` 仍消费对话历史 messages，不受 CustomerState 动态注入影响（`messages[0]` 即使变化，`evaluate` 只扫 `role=user`）

**与 P3**：
- **运行时无数据流**：P4 `customer_state.py` / `dialogue.py` / `state_summary.py` 都**不 import** `peilian.judge` 或 `peilian.judge_prompts`；P3 的 `CustomerJudgeReport` 在 P4 运行时不被消费
- **离线设计期参考**：P3 `CustomerJudgeReport.premature_disclosure_issues` 是本阶段设计 CustomerState 状态机的一手输入——告诉我们 protected_field 全集（`family_structure / income / existing_coverage / hidden_concerns`）和"未问即报"的判定标准
- P4 的 CustomerState 会从源头减少越界泄露（约束 prompt 中的"可说/不可说"），从而让 P3 judge 的客户诊断报告越来越干净——**这个反馈循环是离线的**（人工跑 demo_p3 → 看 issue 列表 → 调 yaml / state_summary 措辞）
- **不修改** P3 的 `judge.py` / `judge_prompts.py`
- P3 judge 仍然只消费 messages，不依赖 CustomerState（架构解耦）

---

## 实施任务拆分（轻量 TDD 顺序）

| # | 任务 | 备注 |
|---|---|---|
| 1 | 修改 `pyproject.toml`：dependencies 增加 `pyyaml>=6`，重新 `pip install -e .` | — |
| 2 | 提取 P2 `_scan_mandatory` 核心为公开 `match_mandatory_categories(text)` 并补 P2 测试 | 仅**追加**导出 + 测试，P2 行为不变 |
| 3 | 起草 `tests/test_persona_factory.py` + `test_customer_state.py` + `test_state_summary.py`（**先于实现**）| import 失败自然 fail |
| 4 | 跑 `pytest` P4 相关测试，确认全部失败 | TDD 红灯 |
| 5 | 实现 5 份 `personas/*.yaml`（每份 hidden_concerns ≥ 2 条，含 key/label/keywords/initial_stage）| 覆盖不同客户类型 |
| 6 | 实现 `src/peilian/persona_factory.py`（yaml → Persona + PersonaMeta + 难度缩放 + clip）| 依赖 `pyyaml` |
| 7 | 实现 `src/peilian/customer_state.py`（CustomerState frozen dataclass + initial + update_state 纯函数）| 无外部依赖 |
| 8 | 实现 `src/peilian/state_summary.py`（CustomerState → 文本，含长度限制与被动措辞）| 无外部依赖 |
| 9 | 跑 `pytest` P4 测试（不含 dialogue 注入），确认通过 | TDD 绿灯 1 |
| 10 | 修改 `src/peilian/prompts.py`（`render_customer_system_prompt` 增加 `state_summary=""` 关键字参数 + template 加 `{state_summary}` 占位）| 向后兼容守护：现有 P1/P2/P3 测试不变更需通过 |
| 11 | 修改 `src/peilian/dialogue.py`（按 §5：`_render_system_prompt` / `send_user` 覆写 `messages[0]` / `update_state` / `reset` 同步重置）| 见 §5 详细伪码 |
| 12 | 实现 `tests/test_dialogue_state_injection.py` | mock LLM |
| 13 | 跑 `pytest`，确认全量绿灯（P0-P4）| TDD 绿灯 2 |
| 14 | 实现 `scripts/demo_p4.py` | 交互式 demo + 退出后打印 state 变化日志 |
| 15 | 修改 `README.md`：加 P4 demo 命令 + personas/ 说明 | — |
| 16 | 用户人工跑 `python scripts/demo_p4.py`，验证 5 种 persona 行为差异 + easy/hard 档差异 | — |
| 17 | 用户审阅、勾选 checklist | — |
| 18 | 由用户授权 commit | — |

---

## 已确认决策

### Q1. Persona 配置文件格式 → **YAML**

理由：人类可编辑，多层结构清晰，pyyaml 是 Python 生态标准依赖。如果项目希望避免新增依赖，可降级为 JSON（标准库），但 YAML 的注释能力和可读性更适合"配置化客户画像"这个场景。

### Q2. 难度档实现方式 → **工厂参数 + yaml 值缩放**

`load_persona_from_yaml(path, difficulty="medium")` 加载后按档位线性缩放 persistence / expressiveness。不引入独立的 `Difficulty` dataclass（最少新增类型）。

### Q3. CustomerState 中"字段是否被问到"的判断 → **P2 粗粒度匹配 + P4 具体点名过滤**

不重复发明 P2 已有的 KYC 类别识别逻辑：先用 `match_mandatory_categories(text)` 得到粗粒度类别覆盖，再由 P4 的 `filter_specific_asked_fields(text, coarse_fields)` 判断是否足够具体到可以允许客户回答。

示例：
- 「想了解你的情况」→ P2 不命中，P4 `asked_fields_this_turn = ∅`
- 「想了解你的家庭情况」→ P2 可计 `family_structure` 覆盖，但 P4 可过滤为未具体点名，客户应模糊回应或反问
- 「您家里几口人？」→ P2 命中且 P4 具体点名，客户可简短回答家庭结构这一项

### Q4. state_summary 注入 → **修改 prompts.py template + dialogue.py 透传**

在 `render_customer_system_prompt` 增加可选的 `state_summary` 参数，默认为空字符串（向后兼容 P1/P2/P3）。

### Q5. dialogue.py 修改范围 → **对话循环骨架不变，system prompt 改为每轮重渲**

实读现有 `Dialogue` 后确认没有 `_build_system_prompt()` / `_get_ai_response()` 方法。P4 修改方式按 §5 执行：

- 新增 `_render_system_prompt()` 私有方法，集中调用 `render_customer_system_prompt(..., state_summary=...)`
- 每次 `send_user(text)` 调 LLM 前覆写 `messages[0]` 为最新 system prompt
- LLM 返回并 append assistant 后调用 `update_state()`
- `reset()` 同步重置 `customer_state` 与 `messages[0]`

对话循环骨架仍保持 `append user → 调 LLM → append assistant → 更新状态`，但 system prompt 渲染时机从一次性改为每轮，这是 P4 为注入 CustomerState 的必要侵入。

### Q6. CustomerState 持久化 → **P4 不做**

只在内存中维护本轮 CustomerState。错题本/跨会话状态持久化留给 P7。

### Q7. pyyaml 依赖 → **新增（轻量、标准）**

项目当前无 yaml 依赖。pyyaml 是纯 Python 且体积小，符合 CLAUDE.md "每加一个依赖都要能说出为什么不能自己写 30 行替代"——手写 yaml parser 远超 30 行且不安全。

### Q8. Commit 策略 → **两次 commit（沿用 P1/P2/P3 节奏）**

- Commit 1：`docs/ROADMAP.md` 游标切换（本次）
- Commit 2：`docs(P4): 起草 phase-4.md 阶段计划`（本 spec 用户审批后）
- Commit 3：`feat(P4): 实现 Persona 工厂 + CustomerState`（实现完成 + 验收通过后）

### Q9. demo_p4.py 参数化 → **支持 --persona 和 --difficulty**

与 demo_p1.py 的简单启动方式不同，P4 demo 需要区分 persona 和难度。支持 CLI flag，未指定时交互式列出可用 persona 让用户选择。退出时打印每轮 CustomerState 变化日志，便于调试 update_state。

### Q10. dialogue.py 动态注入策略 → **每轮覆写 `messages[0]`**

A 案（覆写 messages[0]）vs B 案（追加 system 消息）二选一。采用 A：不污染 user/assistant 流，P3 judge 与 P2 observer 不需感知。代价是放弃"system prompt 一次性固化"假设；这一点在 §5 明示，并修正"最小侵入"措辞为"对话循环骨架不变 + system prompt 渲染时机由一次性改为每轮"。

### Q11. hidden_concerns 结构化 → **yaml 用对象（key + label + keywords + initial_stage），Persona dataclass 仍存 `tuple[str, ...]`**

避免修改 P1/P2/P3 已稳定的 `Persona.hidden_concerns: tuple[str, ...]` 字段。结构化索引由 `persona_factory.py` 内部维护，外部通过 `get_persona_meta(persona) -> PersonaMeta` 查回。CustomerState 用 key 跟踪状态机，用 keywords 判断触发证据，与 yaml 一一对应。

### Q12. CustomerState 字段全集来源 → **复用 P2 `MANDATORY_QUESTION_RULES.keys()`**

`disclosed_fields` / `asked_fields_this_turn` 的全集 = P2 已定义的 6 类必问点 key。避免双源维护；同时把 `peilian.observer._scan_mandatory` 的核心提取为公开纯函数 `match_mandatory_categories(text) -> frozenset[str]` 给 P4 复用。

### Q13. CustomerState 字段类型 → **frozen 友好（frozenset / tuple）**

`hidden_concern_stage` 用 `frozenset[tuple[str, str]]` 而非 `dict[str, str]`，与 `disclosed_fields: frozenset[str]` 风格一致；frozen dataclass 配可变 dict 是常见反模式（frozen 只阻止字段重新赋值，dict.update 仍能改内容），P4 一次到位。

### Q14. trust / patience 初始公式与调整规则 → **写死可机械验证**

- 初始：`trust = clip(0.6 - 0.4 × persistence, 0.1, 0.9)`；`patience = 1.0`
- 调整：trust 看 P2 必问点 / 合规红线命中（不再用模糊的"问得专业"）；patience 看 `asked_fields_this_turn` 是否为空
- 全部经验值，可在 P7 调；P4 只保证规则化、可测试

### Q15. state_summary 长度上限 → **≤ 400 字 + 截断 untouched 项**

控制 token 成本与 prompt 噪声；超长时截断"untouched"的隐藏关切（保留状态非 untouched 的项），并在末尾加省略提示。测试守护长度。

### Q16. state_summary 措辞 → **被动语态 + 禁用词清单**

避免 LLM 把"已暗示 → 可以模糊回应"解读为"我可以主动浮现"。所有"允许程度"措辞用被动语态；禁用词列表（"可以披露 / 现在可以说 / 主动表达 / 主动说出来"等）由测试守护。

---

## Commit 策略

### Commit 1 — ROADMAP 游标切换到 P4（当前，立即执行）

```
chore: 切换 ROADMAP 游标到 P4（Persona 工厂 + CustomerState）

- P3 标记为 ✅ 已完成（commit 9cf2916）
- 游标移到 P4
- README.md 当前阶段同步更新
```

### Commit 2 — phase-4.md 单独入库（本 spec 审批后立即执行）

```
docs(P4): 起草 phase-4.md 阶段计划

- Persona 工厂 + CustomerState spec：5 份 yaml 客户画像（结构化 hidden_concerns
  含 key/label/keywords/initial_stage）+ 难度档线性缩放+clip + CustomerState 状态追踪
  （frozenset 友好类型；trust=clip(0.6-0.4*persistence,0.1,0.9), patience=1.0）
  + 生成前状态摘要注入（≤400 字、被动语态、禁用词守护）+ 生成后状态更新
  （update_state 纯函数；信任度看 P2 必问点/红线命中，耐心值看 asked_fields_this_turn）
- 决策记录（Q1-Q16）：YAML 配置；难度线性缩放+clip；字段全集复用 P2 rules
  并提取公开 match_mandatory_categories；state_summary 注入 prompts template；
  dialogue.py 每轮覆写 messages[0]（动态注入策略 A 案）；hidden_concerns
  yaml 结构化但 Persona dataclass 不变；CustomerState frozen 友好类型；
  trust/patience 公式可机械验证；摘要长度上限+被动语态；CustomerState 不持久化；
  新增 pyyaml 依赖；P4 运行时不消费 P3 CustomerJudgeReport（仅离线设计参考）
- 实施任务采用轻量 TDD 顺序（先写 mock 测试看红灯，再实现看绿灯）
- 评审修订：dialogue 集成方案与现状对齐；hidden_concern key 标准化；
  难度缩放公式与区间锚定矛盾解除；trust/patience 初值/调整规则化；
  frozen dataclass 字段类型一致；摘要长度与措辞守护
```

---

## 完成条件

1. 验收 checklist 全部勾选
2. 用户人工跑过 `python scripts/demo_p4.py`，验证 5 种 persona 行为差异 + CustomerState 状态追踪
3. `pytest` 全绿（P0-P4 全部通过）
4. 由用户授权后 commit

---

## 进入 P5 的前置条件（仅作占位，不在 P4 内执行）

- P4 所有验收项通过
- 用户显式指示切换游标
- 启动 P5 时再起草 `phase-5.md`
