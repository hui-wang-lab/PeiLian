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
我希望  一份 yaml 配置文件就能生成至少 5 种行为差异可观测的客户画像，
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

- **Persona yaml schema**（`personas/*.yaml`）：隐藏关切、性格参数、坚持度、难度参数、对话开场
- **Persona 工厂**：`load_personas_from_yaml(path) -> list[Persona]`，从 yaml 生成 frozen dataclass
- **难度档分级**：简单（persistence 0.2-0.4）/ 中等（0.5-0.7）/ 困难（0.8-1.0），通过 yaml 字段或加载参数控制
- **CustomerState v1**：记录已披露字段、当轮允许回答字段、隐藏关切状态（未触发/已触发/暗示/表达）、信任度与耐心值
- **生成前状态摘要注入**：把 CustomerState 转成面向 LLM 的简短约束注入 system prompt
- **生成后状态更新**：根据代理人提问与客户回复更新已披露字段、隐藏关切触发/表达进度
- **新增样本 persona set**：至少 5 份 yaml，覆盖不同年龄/收入/坚持度/隐藏关切组合
- **CLI demo**：`python scripts/demo_p4.py` 加载 yaml persona set，选择 persona + 难度档，启动陪练对话
- **测试**：Persona 工厂加载与校验 / CustomerState 状态迁移 / prompt 含状态摘要 / 未修改 P3 judge 模块

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
│   ├── persona_factory.py             # 新增：yaml → Persona dataclass 工厂
│   ├── customer_state.py              # 新增：CustomerState dataclass + 状态迁移逻辑
│   ├── state_summary.py               # 新增：CustomerState → LLM 可读摘要
│   ├── dialogue.py                    # 修改：接入 CustomerState 摘要注入 + 生成后状态更新
│   └── prompts.py                     # 修改：模板增加 {state_summary} 占位符
├── scripts/
│   └── demo_p4.py                     # 新增：加载 yaml，选择 persona + 难度，启动陪练
└── tests/
    ├── test_persona_factory.py         # 新增：yaml 加载 / schema 校验 / 5 种 persona 生成
    ├── test_customer_state.py          # 新增：状态迁移 / 进度释放 / 边界条件
    ├── test_state_summary.py           # 新增：摘要含不允许回答的约束 / 已披露字段引用
    └── test_dialogue_state_injection.py # 新增：mock LLM，验证 system prompt 含状态摘要
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
| 1 | `personas/*.yaml`（5 份）| 新增 | 客户画像 yaml 配置文件 |
| 2 | `src/peilian/persona_factory.py` | 新增 | yaml 加载 → Persona dataclass；schema 校验 |
| 3 | `src/peilian/customer_state.py` | 新增 | CustomerState dataclass + `update_state()` 迁移函数 |
| 4 | `src/peilian/state_summary.py` | 新增 | CustomerState → prompt 摘要文本 |
| 5 | `src/peilian/dialogue.py` | 修改 | 注入 state_summary 到 system prompt；生成后调用 `update_state()` |
| 6 | `src/peilian/prompts.py` | 修改 | template 加 `{state_summary}` 占位 |
| 7 | `scripts/demo_p4.py` | 新增 | 加载 yaml → 选 persona + 难度 → 对话 |
| 8 | `tests/test_persona_factory.py` | 新增 | 工厂加载 / schema 校验 / 5 种 persona |
| 9 | `tests/test_customer_state.py` | 新增 | 状态迁移 / 进度释放边界 |
| 10 | `tests/test_state_summary.py` | 新增 | 摘要含关键约束 |
| 11 | `tests/test_dialogue_state_injection.py` | 新增 | mock LLM 验证 prompt 含摘要 |
| 12 | `README.md` | 修改 | 加 P4 demo 命令 + personas/ 说明 |

> **明确不做**：
> - 不修改 `dialogue.py` 的对话引擎核心逻辑（只注入和更新状态）
> - 不修改 P3 judge / judge_prompts（P3→P4 数据流已解耦）
> - 不修改 `persona.py` 的现有 `Persona` dataclass 字段（维持 P1/P2/P3 兼容）
> - 不做对话内的多分支选择（不根据状态主动推进话题）
> - 不做持久化 CustomerState 到磁盘（暂存内存）
> - 不引入 `pyyaml` 之外的新依赖（如果项目还未有，用标准库 json 做替代方案）

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
- [ ] 上述 12 个新增/修改文件全部到位
- [ ] **未**修改 `persona.py`（Persona dataclass 字段）、`judge.py`、`judge_prompts.py`
- [ ] **未**修改 P1/P2/P3 demo 脚本
- [ ] **未**创建 P5+ 物料（RAG、web 等）

**Persona 工厂**
- [ ] 至少 5 份 yaml，每份生成有效 `Persona` 实例
- [ ] yaml 字段包括：name / age / occupation / family / income_level / existing_coverage / pain_points / hidden_concerns / persistence / expressiveness / initial_mood
- [ ] 工厂函数校验 persistence/expressiveness 在 [0,1] 范围内
- [ ] 难度档切换显著改变 persistence/expressiveness（简单 0.2-0.4 / 中等 0.5-0.7 / 困难 0.8-1.0，可覆盖 yaml 值）
- [ ] 同一份 yaml 用不同难度档生成，persistence/expressiveness 按档位调整

**CustomerState**
- [ ] `CustomerState` 为 frozen dataclass，包含：
  - `disclosed_fields: frozenset[str]` — 已披露字段
  - `hidden_concern_state: dict[str, str]` — 隐藏关切的当前阶段
  - `trust: float` — 信任度 0-1
  - `patience: float` — 耐心值 0-1
- [ ] `update_state()` 纯函数：`(CustomerState, agent_message, customer_response) -> CustomerState`（不调 LLM）
- [ ] 隐藏关切迁移路径：`untouched → triggered → hinted → expressed`（或等价中文标签）
- [ ] 已披露字段增量为幂等：同一字段多次披露不重复计数
- [ ] 未触发的隐藏关切不会出现在生成后摘要的"可表达"部分
- [ ] 面对泛泛提问（"想了解你家庭情况"），CustomerState 不将字段标记为"被问到"

**状态摘要注入**
- [ ] `state_summary()` 输出包含：
  - 当前不可主动披露的字段清单
  - 已披露字段（可自然引用）
  - 各隐藏关切当前阶段与允许的表达程度
  - 信任度 / 耐心值的行为提示
- [ ] 摘要文本注入到 `render_customer_system_prompt` 的 `{state_summary}` 占位
- [ ] mock LLM 测试验证 system prompt 中包含状态摘要关键约束

**Demo / 测试**
- [ ] `python scripts/demo_p4.py` 可交互跑通
- [ ] demo 在无 LLM key 时报错并引导配置 .env
- [ ] `pytest` P4 测试全绿（mock / 纯函数测试，不调 LLM）
- [ ] `pytest` 全量测试（含 P0-P3）P4 相关测试通过，P3 测试不受影响

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

每份 yaml 对应一个 `Persona` 实例。字段与现有 `Persona` dataclass 对齐：

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
  - "担心保费太贵影响房贷"
  - "不希望做太详细的健康告知"
persistence: 0.7
expressiveness: 0.5
initial_mood: "略微戒备但礼貌"
```

5 份 yaml 覆盖：

| 文件名 | 核心特征 | 差异化维度 |
|---|---|---|
| `price_sensitive_midcareer.yaml` | 价格敏感中年 | 中收入 / 价格敏感 / 拒绝长健康告知 |
| `trust_issue_sme_owner.yaml` | 信任问题小企业主 | 高收入 / 对保险行业不信任 / 同业对比 |
| `young_family_new_parent.yaml` | 年轻新父母 | 低预算 / 急需保障 / 拖延倾向 |
| `nearing_retirement.yaml` | 临近退休 | 高年龄 / 已有团险 / 对未来规划犹豫 |
| `high_net_worth_skeptic.yaml` | 高净值怀疑型 | 很高收入 / 坚持度极高 / 对保险价值质疑 |

---

### §2. Persona 工厂

```python
# src/peilian/persona_factory.py 伪代码接口

def load_persona_from_yaml(path: str, *, difficulty: str = "medium") -> Persona:
    """从单个 yaml 文件加载 Persona，按难度档调整 persistence/expressiveness。"""

def load_personas_from_dir(dir_path: str = "personas") -> list[Persona]:
    """加载目录下所有 yaml，默认难度 = medium。"""

def adjust_difficulty(persona: Persona, difficulty: str) -> Persona:
    """按档位缩放 persistence / expressiveness。"""
```

**难度档缩放规则**：

| 难度 | persistence 缩放 | expressiveness 缩放 | 行为特征 |
|---|---|---|---|
| easy | × 0.5（0.2-0.4 档）| × 1.3（更愿意回答）| 容易被说服，信息主动度略高 |
| medium | 保持 yaml 原值 | 保持 yaml 原值 | 标准行为 |
| hard | × 1.3（0.7-1.0 档）| × 0.7（更沉默寡言）| 不易被说服，信息隐藏度更高 |

**Persona dataclass 不修改**：`persona.py` 现有 `Persona` 字段保持不变。工厂产出的是同一个 frozen dataclass 实例。

---

### §3. CustomerState dataclass

```python
@dataclass(frozen=True)
class CustomerState:
    # 已披露字段集合（如 "family_structure", "occupation", "income"）
    disclosed_fields: frozenset[str]

    # 隐藏关切状态映射 {concern_key: stage}
    # stage ∈ {"untouched", "triggered", "hinted", "expressed"}
    hidden_concern_stage: dict[str, str]

    # 信任度 0.0-1.0（初始值由 persona.persistence 决定）
    trust: float

    # 耐心值 0.0-1.0（初始 1.0，多轮无进展扣减）
    patience: float

    # 本轮对话轮次（用于 patience 衰减）
    turn_count: int
```

**状态迁移函数**：

```python
def update_state(
    state: CustomerState,
    agent_message: str,
    customer_response: str,
    *,
    persona: Persona,
) -> CustomerState:
    """纯函数：根据代理人本轮发言 + 客户本轮回复，更新 CustomerState。

    规则：
    1. 识别代理人是否点名了某个受保护字段 → 标记为"被问过"
    2. 识别客户回复是否包含了某个新字段 → 如果被问过则标记 disclosed
    3. 识别客户回复是否表达了隐藏关切 → 更新对应 stage
    4. 信任度调整：代理人问得专业 +0.02；模板化回答 -0.01
    5. 耐心值调整：每轮无实质进展 -0.03；进展 +0.02
    6. turn_count +1
    """
```

**关键设计决策**：

- Agent message 中的字段命中判定复用 P2 `rules.py` 的关键词逻辑（不重复发明匹配器）
- 泛泛提问（如"想了解你的情况"）不匹配任何具体字段关键词，不算"点名"
- 信任度 / 耐心值的变化幅度是经验值，后续阶段可调

---

### §4. 状态摘要注入

`state_summary.py` 把 `CustomerState` 转成面向 LLM 的简短约束文本：

```
def render_state_summary(state: CustomerState, persona: Persona) -> str:
    """生成注入到 system prompt 的文本片段。
    
    形如：
    【本轮对话状态】
    你已向代理人披露：职业、家庭结构
    尚未披露：收入水平、已有保障、健康情况
    隐藏关切状态：
      - 价格敏感：已暗示 → 可以模糊回应，但不要完整暴露
      - 信任问题：未触发 → 完全不要提及
      - ...
    当前信任度：0.4（偏低，保持戒备）
    当前耐心值：0.95（充足）
    """
```

**注入点**：`render_customer_system_prompt(persona, scenario, state_summary="")` 的 template 新增 `{state_summary}` 占位。

**向后兼容**：`state_summary=""` 时与现有 P1/P2/P3 行为完全一致，不影响已有 demo。

---

### §5. dialogue.py 集成点

只修改两个位置，不动对话引擎核心循环：

1. **`_build_system_prompt()`** → 增加 `state_summary` 参数，透传给 `render_customer_system_prompt()`
2. **`_get_ai_response()`** 返回后 → 调用 `update_state()` 更新 `self.customer_state`

```
class Dialogue:
    def __init__(self, persona, scenario, ...):
        self.customer_state = CustomerState.initial(persona)
    
    def _build_system_prompt(self):
        summary = render_state_summary(self.customer_state, self.persona)
        return render_customer_system_prompt(self.persona, self.scenario, state_summary=summary)
    
    def step(self, user_message):
        response = self._get_ai_response(...)  # 现有逻辑
        self.customer_state = update_state(self.customer_state, user_message, response, persona=self.persona)
        return response
```

---

### §6. 测试设计

**`test_persona_factory.py`**（约 6 条）：
- 单文件 yaml 加载 → 有效 Persona
- 目录加载 → 5 份全部成功
- persistence / expressiveness 越界 yaml → raise ValueError
- 难度档缩放：easy 将 persistence 0.7 → 0.35
- 缺失必填字段 yaml → raise KeyError
- loader 返回的 Persona 是 frozen

**`test_customer_state.py`**（约 6 条）：
- 初始状态：所有字段未披露，所有隐藏关切 untouched
- 代理人点名 occupation → disclosed_fields 含 occupation
- 客户主动报未问字段 → disclosed_fields 不增加（只有被问过的才标记）
- 隐藏关切迁移：untouched → triggered → hinted → expressed 线性推进
- 耐心值衰减：连续 3 轮无进展 → patience 从 1.0 降到约 0.91
- 同一字段重复问到 → disclosed_fields 幂等不重复

**`test_state_summary.py`**（约 4 条）：
- 摘要含未披露字段清单
- 摘要含隐藏关切当前阶段与允许程度
- 摘要含信任度/耐心值提示
- 初始状态摘要不含任何已披露信息

**`test_dialogue_state_injection.py`**（约 3 条）：
- mock LLM client，验证 system prompt 含 state_summary 文本
- 多轮对话后 state_summary 反映本轮状态
- state_summary="" 时向后兼容（不抛错）

---

### §7. 与 P2 / P3 的关系

**与 P2**：
- CustomerState 的字段匹配规则复用 P2 `rules.py` 的 `MANDATORY_CATEGORIES` 关键词映射
- 不修改 `observer.py` / `evaluate()` / `report.py`
- `evaluate()` 消费的是对话历史 messages，不受 CustomerState 动态注入影响

**与 P3**：
- P3 `CustomerJudgeReport.premature_disclosure_issues` 是本阶段设计 CustomerState 的一手输入——它告诉了我们应该优先"堵"哪些越界泄露类型
- P4 的 CustomerState 会从根本上减少越界泄露（因为约束了"可说/不可说"），从而让 P3 judge 的客户诊断报告越来越干净
- **不修改** P3 的 `judge.py` / `judge_prompts.py`
- P3 judge 仍然只消费 messages，不依赖 CustomerState（架构解耦）

---

## 实施任务拆分（轻量 TDD 顺序）

| # | 任务 | 备注 |
|---|---|---|
| 1 | 起草 `tests/test_persona_factory.py` + `test_customer_state.py` + `test_state_summary.py`（**先于实现**）| import 失败自然 fail |
| 2 | 跑 `pytest` P4 相关测试，确认全部失败 | TDD 红灯 |
| 3 | 实现 5 份 `personas/*.yaml` | 覆盖不同客户类型 |
| 4 | 实现 `src/peilian/persona_factory.py`（yaml → Persona + 难度缩放）| 依赖 `pyyaml` 或等价方案 |
| 5 | 实现 `src/peilian/customer_state.py`（dataclass + update_state）| 无外部依赖 |
| 6 | 实现 `src/peilian/state_summary.py`（CustomerState → 文本）| 无外部依赖 |
| 7 | 跑 `pytest` P4 测试，确认通过 | TDD 绿灯 |
| 8 | 修改 `src/peilian/prompts.py`（template 加 {state_summary} 占位）| 向后兼容 |
| 9 | 修改 `src/peilian/dialogue.py`（注入 state_summary + 更新 state）| 最小侵入 |
| 10 | 实现 `tests/test_dialogue_state_injection.py` | mock LLM |
| 11 | 实现 `scripts/demo_p4.py` | 交互式 demo |
| 12 | 修改 `README.md`：加 P4 demo 命令 | — |
| 13 | 全量 pytest 通过（P0-P4）| — |
| 14 | 用户人工跑 `python scripts/demo_p4.py`，验证 5 种 persona 行为差异 | — |
| 15 | 用户审阅、勾选 checklist | — |
| 16 | 由用户授权 commit | — |

---

## 已确认决策

### Q1. Persona 配置文件格式 → **YAML**

理由：人类可编辑，多层结构清晰，pyyaml 是 Python 生态标准依赖。如果项目希望避免新增依赖，可降级为 JSON（标准库），但 YAML 的注释能力和可读性更适合"配置化客户画像"这个场景。

### Q2. 难度档实现方式 → **工厂参数 + yaml 值缩放**

`load_persona_from_yaml(path, difficulty="medium")` 加载后按档位线性缩放 persistence / expressiveness。不引入独立的 `Difficulty` dataclass（最少新增类型）。

### Q3. CustomerState 中"字段是否被问到"的判断 → **复用 P2 rules 关键词匹配**

不重复发明一套匹配器。代理人消息中含 family 关键词 → `family_structure` 被问到。泛泛词（"你的情况"）不匹配任何关键词 → 不算点名。

### Q4. state_summary 注入 → **修改 prompts.py template + dialogue.py 透传**

在 `render_customer_system_prompt` 增加可选的 `state_summary` 参数，默认为空字符串（向后兼容 P1/P2/P3）。

### Q5. dialogue.py 修改范围 → **只加两处，不动轮循环**

`_build_system_prompt()` 加 state_summary 注入；`_get_ai_response()` 返回后加 `update_state()`。对话循环的核心逻辑（收消息/调LLM/拼messages）不动。

### Q6. CustomerState 持久化 → **P4 不做**

只在内存中维护本轮 CustomerState。错题本/跨会话状态持久化留给 P7。

### Q7. pyyaml 依赖 → **新增（轻量、标准）**

项目当前无 yaml 依赖。pyyaml 是纯 Python 且体积小，符合 CLAUDE.md "每加一个依赖都要能说出为什么不能自己写 30 行替代"——手写 yaml parser 远超 30 行且不安全。

### Q8. Commit 策略 → **两次 commit（沿用 P1/P2/P3 节奏）**

- Commit 1：`docs/ROADMAP.md` 游标切换（本次）
- Commit 2：`docs(P4): 起草 phase-4.md 阶段计划`（本 spec 用户审批后）
- Commit 3：`feat(P4): 实现 Persona 工厂 + CustomerState`（实现完成 + 验收通过后）

### Q9. demo_p4.py 参数化 → **支持 --persona 和 --difficulty**

与 demo_p1.py 的简单启动方式不同，P4 demo 需要区分 persona 和难度。支持 CLI flag，未指定时交互式列出可用 persona 让用户选择。

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

- Persona 工厂 + CustomerState spec：
  5 份 yaml 客户画像 + 难度档分级 + CustomerState 状态追踪 +
  生成前状态摘要注入 + 生成后状态更新
- 决策记录：YAML 格式；难度通过参数缩放 persistence/expressiveness；
  字段匹配复用 P2 rules 关键词；state_summary 注入 prompts template；
  dialogue.py 最小侵入（加两处不动循环）；
  CustomerState 不持久化；新增 pyyaml 依赖
- 实施任务采用轻量 TDD 顺序（先写 mock 测试看红灯，再实现看绿灯）
- CustomerState 设计优先消费 P3 CustomerJudgeReport.premature_disclosure_issues
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
