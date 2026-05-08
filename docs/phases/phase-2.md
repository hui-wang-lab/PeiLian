# Phase 2 — 状态观察器 + 规则评估

> 状态：计划阶段（待用户审阅本 spec）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-1.md`](phase-1.md) ✅

---

## P2 目标

把对话**评估能力**作为第一条独立纵切跑通：**给定一段对话历史（真实或样本），用规则层产出一份评估报告**，覆盖两件事——

1. **必问点覆盖率**：代理人在 KYC 阶段是否覆盖了关键问题类别（家庭 / 职业 / 收入 / 已有保障 / 未来规划 / 健康）
2. **合规红线扫描**：代理人发言中是否触碰了违禁话术（保证收益 / 与存款或国债误导对比 / 隐瞒免责条款 / 隐瞒或代填健康告知 / 承诺核保或理赔 / 混淆保险与理财）

**架构铁律（来自 [CLAUDE.md §2.2](../../CLAUDE.md)）**：

> 状态观察器**绝不**参与生成客户回复，**不**调度对话分支。

P2 的代码必须从架构上**物理隔离**：观察器只**消费** `Dialogue.messages`，不改写、不注入、不 hook 进对话流。

> 不变量来自 [CLAUDE.md §2.2 / §3 / §6 术语表](../../CLAUDE.md)。所有设计点都要回到这三处自检。

---

## 用户故事

### 业务侧
```
作为一名陪练系统的开发者 / 培训主管，
我希望  在代理人完成一段陪练对话后，
能够  立即看到一份基于规则的评估报告，
报告内  必问点覆盖情况一目了然（哪些问到了，哪些漏了），
       合规红线一旦命中能精确定位到第几轮、原话是什么、命中了哪条规则，
以便  在没有 LLM judge 介入前，先用规则层把"是不是问全了"和"有没有违规"两件硬性事实兜住。
```

### 测试侧
```
作为开发者，
我希望  在没有 LLM key 的环境下也能验证评估器的正确性，
能够  把一段假对话喂给评估器，断言它正确识别出"漏问 X / 命中违规 Y"，
以便  规则层的回归测试能完全脱离 LLM，跑得快、跑得稳。
```

---

## 纵切范围

- **规则数据**：必问点关键词词库 + 合规红线词库（写死在 `rules.py`，不引入 yaml/json，那是后续阶段）
- **观察器主入口**：`evaluate(messages: list[dict]) -> EvaluationReport`
- **评估报告**：`EvaluationReport` dataclass + 一段文本渲染函数
- **样本对话**：1 份精心构造的样本对话，**同时**覆盖"漏问 + 命中违规"两类问题，给 demo 和测试共用
- **CLI demo**：`python scripts/demo_p2.py` 打印样本对话的评估报告
- **测试**：rules 词库一致性 + observer 评估正确性 + report 渲染包含关键标识

---

## 建议目录结构（增量）

只列出 P2 新增/修改的部分：

```
PeiLian/
├── src/peilian/
│   ├── rules.py                   # 新增：必问点词库 + 合规红线词库（含正则）
│   ├── observer.py                # 新增：evaluate() 主入口 + 内部辅助
│   ├── report.py                  # 新增：EvaluationReport dataclass + render_report()
│   └── conversations.py           # 新增：SAMPLE_CONVERSATION_P2（demo + tests 共用）
├── scripts/
│   └── demo_p2.py                 # 新增：加载样本对话 → 跑 evaluate → 打印报告
└── tests/
    ├── test_rules.py              # 新增：词库非空性、类别覆盖
    ├── test_observer.py           # 新增：给定 messages 期望必问点结果 / 红线结果
    └── test_report.py             # 新增：dataclass 字段 + 渲染包含关键标识
```

> **不动 `dialogue.py` / `demo_p1.py`**：观察器与对话引擎物理隔离，evaluator 单独消费 `dialogue.messages`。`dialogue.py` 中 P1 留下的 3 行 P2 hook 注释**保留不动**——P2 用事后批处理就够，实时打点 hook 留给 P3+ 真正需要时再激活。

> **为什么把规则、观察器、报告拆三个文件？**
> 这是后续阶段的接口边界：P3 LLM-as-Judge 会复用 `EvaluationReport` 形态做叠加打分；P5 RAG 可能会扩展规则集（新增条款引用合规校验）；P4 persona 工厂出多 persona 后，必问点清单可能要按 persona 类型分组。在 P2 把边界划清楚，后续不用大改。

> **为什么 `conversations.py` 放在 `src/peilian/` 而不是 `tests/fixtures/`**：demo 和 tests 都要共用同一份样本对话；放进 src 子模块能保证两边 import 路径稳定，不需要 demo 通过 sys.path 注入访问 tests 目录。命名前缀 `SAMPLE_CONVERSATION_P2` 暗示其阶段性，未来可加 `_P3` `_P4` 等版本。

---

## 计划创建/修改的文件

| # | 文件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `src/peilian/rules.py` | 新增 | `MANDATORY_QUESTION_RULES` (必问点 6 类) + `COMPLIANCE_RULES` (红线 6 类) |
| 2 | `src/peilian/report.py` | 新增 | `EvaluationReport` dataclass + `render_report()` |
| 3 | `src/peilian/observer.py` | 新增 | `evaluate(messages) -> EvaluationReport` |
| 4 | `src/peilian/conversations.py` | 新增 | `SAMPLE_CONVERSATION_P2` (一段同时含漏问与违规的样本对话) |
| 5 | `scripts/demo_p2.py` | 新增 | 加载样本 → evaluate → 打印 report；UTF-8 stdout 重配 |
| 6 | `tests/test_rules.py` | 新增 | 词库非空性、类别完整性 |
| 7 | `tests/test_observer.py` | 新增 | 必问点命中/漏问、红线触发位置 |
| 8 | `tests/test_report.py` | 新增 | dataclass 字段、渲染含关键标识 |
| 9 | `README.md` | 修改 | 加 P2 demo 命令一节 |

> **明确不做**：
> - 不创建 `src/peilian/judge.py`（P3 LLM-as-Judge）
> - 不修改 `dialogue.py`（不引入实时 hook）
> - 不修改 `demo_p1.py`（不在 P1 demo 中嵌入评估输出）
> - 不引入 `jieba`/`pkuseg` 等中文分词库
> - 不引入 yaml/json 配置加载（规则写死在 Python 字面量）

---

## Demo 命令

```powershell
# 跑 P2 评估 demo（无需 OPENAI_API_KEY）
python scripts/demo_p2.py

# 跑测试（含 P2 新增）
pytest
```

预期 demo 输出形如：

```
[PeiLian P2 — 规则评估 demo]
样本对话：SAMPLE_CONVERSATION_P2（同时包含漏问与违规，用于演示评估能力）

═══════════════════════════════════════
评估报告
═══════════════════════════════════════

【必问点覆盖率】4 / 6  (66.7%)
  ✓ 已覆盖：family_structure, occupation, existing_coverage, health_status
  ✗ 漏问：  income, future_planning

【合规红线扫描】发现 1 处违规
  ⚠ 第 5 轮 [代理人]
     原话：…这款产品保证收益 4.5%，比存款利息高得多…
     命中规则：
       - 保证收益（关键词「保证收益」）
       - 与存款误导对比（关键词「比存款」）

═══════════════════════════════════════
```

预期 pytest 输出（含 P0/P1 已有 + P2 新增）：

```
tests\test_persona.py .......                   [..]
tests\test_prompts.py ........                  [..]
tests\test_rules.py .....                       [..]
tests\test_observer.py ......                   [..]
tests\test_report.py ...                        [..]
======= XX passed in 0.YY s =======
```

---

## 验收 Checklist

**结构 / 文件**
- [ ] 上述 9 个新增/修改文件全部到位
- [ ] **未**修改 `dialogue.py`、`demo_p1.py`、`prompts.py`、`persona.py`、`scenario.py`
- [ ] **未**创建 P3+ 物料（judge / RAG / web 等）

**规则数据**
- [ ] `MANDATORY_QUESTION_RULES` 含 6 个类别：family_structure / occupation / income / existing_coverage / future_planning / health_status
- [ ] `COMPLIANCE_RULES` 含 6 类：保证收益 / 存款误导对比 / 隐瞒免责 / 隐瞒或代填健告 / 承诺核保理赔 / 混淆保险与理财
- [ ] 所有规则有非空关键词列表；至少 2 类含正则补充（保证收益、混淆保险与理财）

**观察器**
- [ ] `evaluate(messages)` 只读 `messages`，不修改
- [ ] 只扫描 `role == "user"`（代理人发言）做必问点和红线判断
- [ ] 多次调用同一份 messages 结果稳定（纯函数，无副作用）
- [ ] **架构隔离自检**：`observer.py` 不 import `Dialogue` 或 `OpenAI`；`dialogue.py` 不 import `observer`

**报告**
- [ ] `EvaluationReport` 是 frozen dataclass，至少含：必问点覆盖列表 / 漏问列表 / 红线命中条目列表
- [ ] 红线命中条目至少含：轮次索引、原话片段、命中规则类别、命中关键词
- [ ] `render_report()` 输出包含「必问点覆盖率」「合规红线扫描」两个段落标题
- [ ] 输出在 Windows 控制台正常显示（UTF-8 stdout 重配）

**Demo**
- [ ] `python scripts/demo_p2.py` 在无 LLM key 环境下可直接运行
- [ ] 输出能同时演示「漏问」与「违规」两类问题（即样本对话有意涵盖两者）

**Tests**
- [ ] `pytest` 全绿；测试不依赖真实 LLM key
- [ ] `test_rules.py` 覆盖：必问点 6 类、红线 6 类、各类别 keywords 非空
- [ ] `test_observer.py` 覆盖：完美对话→无漏问无违规；故意漏问 1 类→正确识别；故意触发 1 条红线→精确定位轮次
- [ ] `test_report.py` 覆盖：dataclass 实例化、render 含「必问点覆盖率」「合规红线扫描」标题、含命中规则名

**Git**
- [ ] 至少一个 commit，message 第一行含 `Phase 2`
- [ ] 工作区干净

---

## 不在 P2 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| 销售漏斗阶段识别（开场/挖需/讲解/异议/促成的自动归类）| P3 或更后期 |
| LLM-as-Judge 评估、共情度/逻辑结构等模型层评分 | P3 |
| 评估报告嵌入 P1 demo（结束陪练后自动出报告）| 可选放到 P3 起步阶段 |
| Persona 工厂、配置化必问点（按 persona 类型分组）| P4 |
| 产品条款 RAG 校验（条款引用准确性）| P5 |
| Web UI / 雷达图可视化 | P6 |
| 错题本 / 弱项画像 / 自适应难度 | P7 |
| 实时 hook（在 `dialogue.send_user` 前后打点）| 留待真有需求 |
| 规则的 yaml/json 配置加载 | P4 一并做（与 persona 工厂同节奏）|
| 中文分词库（jieba 等）| 全程审慎，目前都不需要 |
| 修改 `CLAUDE.md` | 本阶段无需改动宪法 |
| 创建 `phase-3.md` 或任何 P3 物料 | P2 完成后由用户显式启动 P3 |

---

## 技术设计要点

### §1. 必问点规则（写死草稿，待用户审阅）

`src/peilian/rules.py` 暴露 `MANDATORY_QUESTION_RULES`，结构为 `dict[str, tuple[str, ...]]`，键为类别 id，值为关键词元组。**任意关键词在代理人发言中出现，即视为该类别已问**：

| 类别 id | 中文标签 | 触发关键词（任一命中即覆盖） |
|---|---|---|
| `family_structure` | 家庭结构 | 「几口人」「几个孩子」「家里有」「父母」「太太」「丈夫」「妻子」「老婆」「老公」「孩子多大」「家庭情况」 |
| `occupation` | 职业行业 | 「工作」「职业」「行业」「单位」「公司是做」「您是做什么的」 |
| `income` | 收入水平 | 「收入」「年收入」「月薪」「年薪」「家庭年收入」「赚」 |
| `existing_coverage` | 已有保障 | 「保险」「保单」「保障」「医疗险」「重疾」「意外险」「团险」「公司团」 |
| `future_planning` | 未来规划 | 「规划」「打算」「未来」「以后」「养老」「退休」「孩子教育」「子女教育」 |
| `health_status` | 健康情况 | 「身体」「健康」「体检」「手术」「住院」「家族病史」「慢病」 |

**风险**：关键词覆盖不全可能漏认（代理人用很侧面的话问）；"工作"「您今天怎么过来」这种泛泛话也可能假阳性。**P2 接受**这两种偏差——规则层只兜底，矫正交给 P3 LLM judge。

**P2 必问点的范围边界（已确认）**：

- **`income` 仅作为「支付能力 / 现金流」的最小代理变量**：是否被问到一次"收入/年收入/月薪"层面就视为已覆盖。**不**展开成更细颗粒度的 FNA 子项。
- **资产负债 / 现金流结构 / 预算区间**等更细粒度 FNA 项**暂不独立成类**——这些进 P2 会让规则结构过重，且依赖具体 persona 类型，留给 P4 persona 工厂阶段再考虑。
- **「保险态度 / 抗拒度」属销售过程观察项，不进 P2 必问点**——这是客户行为画像，不是代理人需要 KYC 询问的事项。
- **FORM / FNA 在 P2 只做概念映射**：6 个类别可以理解为 FORM/FNA 的最小投影（Family→family_structure；Occupation→occupation；Money→income + future_planning；Recreation→暂略；FNA 已有保障对照→existing_coverage；FNA 健康对照→health_status）。**不改变规则结构**，不在 P2 文档中再做 FORM/FNA 完整建模。

> 一句话：P2 不做完整 FNA 问卷，只跑规则层最小闭环。完整 FNA 建模如有需要，进 P4 persona 工厂或更后期。

### §2. 合规红线规则（写死草稿，待用户审阅）

`src/peilian/rules.py` 暴露 `COMPLIANCE_RULES`，结构为 `tuple[ComplianceRule, ...]`：

```
ComplianceRule(frozen):
  rule_id: str
  label: str
  keywords: tuple[str, ...]
  patterns: tuple[str, ...]    # 正则字符串（可空）
```

| rule_id | 标签 | keywords | patterns（regex）|
|---|---|---|---|
| `guarantee_return` | 保证收益 | 「保证收益」「稳赚不赔」「零风险」「肯定不亏」「保本保息」 | `保证.{0,3}收益`、`保本.{0,3}息` |
| `mislead_vs_deposit` | 与存款/国债误导对比 | 「比存款」「比银行」「跟存款一样」「比国债」「跟定期一样」 | `比.{0,3}存款`、`比.{0,3}国债` |
| `hide_exclusion` | 隐瞒免责条款 | 「不用看免责」「免责不重要」「免责条款没事」「不会拒赔」 | — |
| `hide_health_disclosure` | 隐瞒 / 代填健康告知 | 「健告随便填」「不用如实告知」「告知不重要」「不报也行」「不告知没事」「我帮您填」「这项填否」「这个不用写」「病史不用写」「我来处理健告」 | — |
| `promise_underwriting` | 承诺核保 / 理赔 | 「核保肯定过」「肯定能买」「理赔包过」「保证赔付」「百分百赔」 | — |
| `misrepresent_as_financial_product` | 混淆保险与理财 | 「就是理财」「当理财买」「和理财一样」「主要看收益」 | `保险.{0,6}理财`、`当.{0,3}理财.{0,3}买`、`保险.{0,6}理财.{0,6}产品` |

**P2 暂不加入的红线类别**（保留在风险/范围说明中显式排除）：

- **「夸大特定病种保障」**：依赖具体产品条款（不同产品对甲状腺/原位癌/轻症等覆盖各异），规则层硬卡容易误伤。留待 P5 RAG 接入条款知识库后做条款引用准确性校验。
- **「误导犹豫期 / 退保规则」**：同样依赖具体产品条款细节；语义层判断容易与 P3 LLM judge 重叠。留待 P5 / P3 协同时考虑。

**P2 词库扩张策略**：只放最高频、高精度的核心词；不做大而全的同义词穷举。**假阴性由 P3 LLM judge 兜底**——这是 P2 与后续阶段的明确分工。

**风险**：关键词假阳性（如代理人转述客户自己的话「您说的『稳赚不赔』确实不存在」会被命中）。**P2 接受**——P3 LLM judge 会做语义层矫正。

### §3. `EvaluationReport` 形态

```
EvaluationReport(frozen):
  total_categories: int                 # 必问点总类数（= 6）
  covered_categories: tuple[str, ...]   # 已覆盖的类别 id（按 rules 中顺序）
  missed_categories: tuple[str, ...]    # 漏问的类别 id
  compliance_hits: tuple[ComplianceHit, ...]

ComplianceHit(frozen):
  turn_index: int          # 在 messages 列表中的索引（含 system, 从 0 起）
  agent_turn_number: int   # 代理人第几轮发言（从 1 起）
  excerpt: str             # 命中片段（取关键词上下文 ±10 字符）
  rule_id: str
  rule_label: str
  matched_keyword: str
```

**为什么同时记录 `turn_index` 和 `agent_turn_number`**：前者用于精确定位回 messages 列表（开发态），后者用于人类可读的报告（"第 5 轮"）。

`render_report(report) -> str`：返回多段文本，符合 Demo 命令一节中的预期输出格式。

### §4. 观察器 API

```
def evaluate(messages: list[dict[str, Any]]) -> EvaluationReport:
    """对一段对话历史做规则层评估。

    只读 messages；不修改、不调 LLM、不接 dialogue.py。
    """
    ...
```

**实现要点**：
- 遍历 messages，过滤 `role == "user"` 的项（这是代理人发言）
- 对每条 user content：
  - 命中必问点关键词 → 把该类别加入 covered set
  - 命中红线关键词或正则 → 追加一条 ComplianceHit
- `missed = total - covered`，按规则定义顺序排列输出
- 纯函数：同一输入多次调用结果一致，不缓存、不持久化

**架构隔离自检**：`observer.py` 顶部 import 只允许 `peilian.rules` / `peilian.report`，**禁止**出现 `peilian.dialogue` / `openai`。

### §5. 样本对话 `SAMPLE_CONVERSATION_P2`

`src/peilian/conversations.py` 暴露一个 `list[dict[str, str]]` 常量，结构与 `Dialogue.messages` 一致（`{"role": ..., "content": ...}`）。

**设计目标**：单份样本同时演示"漏问"与"违规"两类问题。草稿构思（**最终内容在实施时定稿**）：

| 轮次 | 角色 | 内容（梗概）|
|---|---|---|
| 0 | system | (省略，可空字符串) |
| 1 | user (代理人) | 您好王先生，先了解下您家里几口人？（命中 family_structure） |
| 2 | assistant (客户) | 三口人，太太和一个孩子。 |
| 3 | user | 您是做哪行的？（命中 occupation） |
| 4 | assistant | IT 行业。 |
| 5 | user | 那您之前买过什么保险吗？（命中 existing_coverage）我推荐这款产品保证收益 4.5%，比存款利息高得多。（命中两条红线）|
| 6 | assistant | 公司有团险吧。这个收益是真的吗？ |
| 7 | user | 您身体怎么样，做过手术吗？（命中 health_status） |
| 8 | assistant | 还行。 |

故意**漏问**：`income`（收入）、`future_planning`（未来规划）。
故意**触发**：`guarantee_return`（保证收益）、`mislead_vs_deposit`（比存款）——一句话同时命中两条规则。

### §6. 测试设计

`test_rules.py`（约 5 条）：
- `MANDATORY_QUESTION_RULES` 含且仅含 6 个预期类别 id
- 每个类别 keywords 非空且长度 ≥ 3
- `COMPLIANCE_RULES` 含 6 个预期 rule_id（含 `misrepresent_as_financial_product`）
- 每个红线规则的 keywords 非空（patterns 可空）；至少 `guarantee_return` 与 `misrepresent_as_financial_product` 含 patterns
- 关键词在类别间不互相冲突（如 `保险` 不应同时出现在多个必问点类别中——可选断言）

`test_observer.py`（约 6 条）：
- **空 messages**：返回报告中 covered 为空，missed 为全部 6 类，compliance_hits 为空
- **完美对话**：人造 messages 6 类必问点全覆盖、无红线 → covered=6 / missed=0 / hits=0
- **漏问 1 类**：人造 messages 5 类问到 → missed 恰好为漏的那一类
- **触发 1 条红线**：人造 messages 含 1 句违规 → hits 长度=1，rule_id 正确
- **一句多命中**：人造 messages 含「保证收益 4.5%，比存款高」 → hits 长度=2，rule_id 分别为 guarantee_return / mislead_vs_deposit
- **样本对话端到端**：用 `SAMPLE_CONVERSATION_P2` 跑 evaluate，断言 `missed_categories == ("income", "future_planning")` 且 `len(compliance_hits) == 2`

`test_report.py`（约 3 条）：
- `EvaluationReport` 可实例化
- `render_report(empty_report)` 包含「必问点覆盖率」「合规红线扫描」字样
- `render_report(report_with_hits)` 包含 hit 的 rule_label

### §7. 与 P1 的关系

P1 已实现 `Dialogue.messages: list[dict[str, Any]]` 公开属性。P2 的 evaluator 直接消费这个属性（demo 时由 `SAMPLE_CONVERSATION_P2` 替代）。

**不**修改 `Dialogue` 类、**不**修改 `demo_p1.py`、**不**激活 `dialogue.py` 中的 hook 占位注释——这三处保持纯净。

如果未来希望"陪练结束自动跑评估并打印报告"，P3 起步阶段再统一考虑（可能在 demo 层做集成，而不是改 dialogue 类）。

### §8. P3 hook 预留：与 P1 Q6 同节奏

P3 是 LLM-as-Judge 评估，预计会消费 `EvaluationReport`（在规则层基础上做语义打分）或者直接消费 `messages`（独立打分通道）。

P2 阶段：**只允许在代码注释中写占位**（如 `# P3: LLM judge could augment this report later`），**不**预先定义 judge 接口、Protocol、回调列表等。

---

## 实施任务拆分（轻量 TDD 顺序，沿用 P1 节奏）

| # | 任务 | 备注 |
|---|---|---|
| 1 | 新增 `tests/test_rules.py` + `tests/test_observer.py` + `tests/test_report.py`（**先于实现**）| import 失败自然 fail |
| 2 | 跑 `pytest`，**确认全部失败**（缺少 rules / observer / report 模块）| TDD 红灯 |
| 3 | 实现 `src/peilian/rules.py`（必问点 + 红线词库，含 ComplianceRule dataclass）| — |
| 4 | 实现 `src/peilian/report.py`（EvaluationReport / ComplianceHit dataclass + render）| 依赖 rules.py |
| 5 | 实现 `src/peilian/observer.py`（evaluate 主入口）| 依赖 rules.py、report.py |
| 6 | 实现 `src/peilian/conversations.py`（SAMPLE_CONVERSATION_P2）| 用于 demo 与 test 端到端用例 |
| 7 | 跑 `pytest`，**确认全部通过** | TDD 绿灯 |
| 8 | 实现 `scripts/demo_p2.py`（加载样本 → evaluate → 打印 report）| — |
| 9 | 修改 `README.md`：加 P2 demo 命令 | — |
| 10 | 用户人工跑 `python scripts/demo_p2.py`，肉眼验证报告内容合理 | 见验收 checklist 「Demo」 |
| 11 | 用户审阅、勾选 checklist | — |
| 12 | 由用户授权 commit（**本阶段不自动 commit**）| 见「commit 策略」一节 |

---

## 已确认决策

以下决策已与用户对齐，实施时按此执行：

### Q1. 必问点 6 个类别 → **保持 6 类，加边界说明**

类别清单不变：`family_structure` / `occupation` / `income` / `existing_coverage` / `future_planning` / `health_status`。

**边界**（详见 §1 「P2 必问点的范围边界」）：
- `income` 仅作为「支付能力 / 现金流」的最小代理变量，**不**展开 FNA 子项
- 资产负债 / 现金流结构 / 预算区间等更细粒度 FNA **不独立成类**
- 「保险态度 / 抗拒度」属销售过程观察项，**不进** P2 必问点
- FORM / FNA 在 P2 只做概念映射，**不改变**规则结构

> 一句话：P2 不做完整 FNA 问卷，只跑规则层最小闭环。

### Q2. 合规红线 → **从 5 类调整为 6 类**

最终 6 类：

```
guarantee_return                  保证收益
mislead_vs_deposit                与存款/国债误导对比
hide_exclusion                    隐瞒免责条款
hide_health_disclosure            隐瞒 / 代填健康告知
promise_underwriting              承诺核保 / 理赔
misrepresent_as_financial_product 混淆保险与理财（新增）
```

**两处关键调整**：

1. `hide_health_disclosure` 的中文标签从「隐瞒健康告知」改为「**隐瞒 / 代填健康告知**」，关键词补充代填类高风险表达：「我帮您填」「这项填否」「这个不用写」「病史不用写」「我来处理健告」。
2. **新增** `misrepresent_as_financial_product`：keywords「就是理财」「当理财买」「和理财一样」「主要看收益」；patterns `保险.{0,6}理财`、`当.{0,3}理财.{0,3}买`、`保险.{0,6}理财.{0,6}产品`（去掉单独关键词「理财产品」改成 regex，避免误伤「这不是单纯的理财产品」这类合规表达）。

**P2 暂不加入**「夸大特定病种保障」「误导犹豫期 / 退保规则」两类——前者依赖产品条款，留 P5 RAG；后者语义层判断与 P3 LLM judge 重叠（详见 §2 footer）。

### Q3. 关键词词库的扩张策略 → **方案 A**

P2 只放最高频核心词；假阴性由 P3 LLM judge 兜底。**不做**大而全的同义词穷举或复杂正则。

### Q4. 评估器对客户发言扫描策略 → **只扫代理人**

只扫 `role == "user"`。客户发言中出现「能保证收益吗？」这类内容**不直接算违规**——真正要判断的是代理人如何回应，这个语义层判断留给 P3 LLM judge。

### Q5. 评估器 API 形态 → **纯函数**

```
evaluate(messages: list[dict]) -> EvaluationReport
```

无状态、纯函数。**不**设计 `Evaluator` 类，**不**做可注入自定义规则的接口。需要时再演化（YAGNI）。

### Q6. Fixture 位置 → **`src/peilian/conversations.py`**

导出 `SAMPLE_CONVERSATION_P2`，demo 与 tests 共用。

### Q7. 不改 `demo_p1.py` → **保持 P1 demo 纯净**

P2 只新增 `python scripts/demo_p2.py`。本份 spec 只规划 README 在 P2 完成时加一行手动调用提示（`from peilian.observer import evaluate; evaluate(dialogue.messages)`）；本次只修订 phase spec，**不实现**。

### Q8. P3 hook 预留 → **只允许注释占位，不设计接口**

`observer.py` / `report.py` 中可写注释占位（如 `# P3: LLM judge could augment this report later`），**不**预先定义 hook 函数签名、Protocol、回调列表等任何接口形态。

### Q9. Commit 策略 → **两次 commit**

- Commit 1：phase-2.md 单独入库（本份 spec 经审批后立即执行），message: `docs(P2): 起草 phase-2.md 阶段计划`
- Commit 2：P2 实现物料一次性 commit（实现完成 + 人工验收通过 + pytest 全绿后），message: `feat(P2): 实现规则层评估 + 状态观察器`

### Q10. `demo_p2.py` 不参数化 → **写死使用 `SAMPLE_CONVERSATION_P2`**

不支持 CLI 参数加载其他 fixture。未来要做"批量评估多份历史对话"时再加。

---

## Commit 策略与建议 commit message（按 Q9：两次 commit）

### Commit 1 — phase-2.md 单独入库（本份 spec 经审批后立即执行）

```
docs(P2): 起草 phase-2.md 阶段计划

- 状态观察器 + 规则评估的端到端最小评估能力 spec
- 决策记录: 必问点 6 类 (含 income 仅作支付能力代理变量的边界说明) /
  合规红线 6 类 (含新增 misrepresent_as_financial_product 与
  hide_health_disclosure 扩展为「隐瞒/代填健告」); evaluate 纯函数;
  样本对话放 src/peilian/conversations.py; 不改 dialogue/demo_p1;
  不预设 P3 接口; 评估只扫代理人发言; 两次 commit
- 实施任务采用轻量 TDD 顺序 (先写测试, 看红灯, 再实现, 看绿灯)
```

### Commit 2 — P2 实现物料（实现完成 + 人工验收通过 + pytest 全绿后执行）

```
feat(P2): 实现规则层评估 + 状态观察器

- 新增 src/peilian/rules.py: 必问点 6 类词库 (family/occupation/income/
  existing_coverage/future_planning/health_status) + 合规红线 6 类
  (保证收益/存款误导对比/隐瞒免责/隐瞒或代填健告/承诺核保理赔/
  混淆保险与理财), 含正则补充
- 新增 src/peilian/report.py: EvaluationReport + ComplianceHit frozen
  dataclass + render_report() 文本渲染
- 新增 src/peilian/observer.py: evaluate(messages) 纯函数主入口,
  只读 messages, 只扫 role==user; 与 dialogue 物理隔离 (不 import
  Dialogue / OpenAI)
- 新增 src/peilian/conversations.py: SAMPLE_CONVERSATION_P2 (一段
  同时含漏问与违规的样本对话, demo 与 tests 共用)
- 新增 scripts/demo_p2.py: 加载样本 → evaluate → 打印报告; 无 LLM 依赖
- 新增 tests/test_rules.py / test_observer.py / test_report.py,
  覆盖词库结构 / 必问点命中漏问 / 红线触发定位 / 报告渲染关键标识
- 更新 README.md 加 P2 demo 命令 + evaluator 手动调用提示

人工验证: 样本对话评估输出符合预期 (漏问 income/future_planning,
命中 guarantee_return + mislead_vs_deposit; 其余 4 类红线规则有
词库与测试覆盖, demo 不强求全部触发)
```

---

## 完成条件

1. 验收 checklist 全部勾选
2. 用户人工跑过 `python scripts/demo_p2.py`，确认报告内容符合预期
3. `pytest` 全绿
4. 由用户授权后 commit

---

## 进入 P3 的前置条件（仅作占位，不在 P2 内执行）

- 本阶段所有验收项通过
- 用户显式指示切换游标
- 切换时由用户在 ROADMAP 把 P2 改为「✅ 已完成」并把游标移到 P3
- 启动 P3 时再起草 `phase-3.md`（**P2 内不创建该文件**）
