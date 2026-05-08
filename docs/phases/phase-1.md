# Phase 1 — 单 persona 单场景

> 状态：计划阶段（待用户审阅本 spec）
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-0.md`](phase-0.md) ✅

---

## P1 目标

把第一条业务纵切跑通：**1 个写死的客户画像 + 1 个固定寿险销售场景，CLI 中代理人可与 AI 客户进行多轮文本对话，且 AI 客户严格遵守「代理人驱动，客户被动反应」原则**。

本阶段**不做**评估、RAG、Web UI；本阶段重点是把"对话能跑通且符合架构原则"这一件事做扎实，为后续阶段铺好接口与文件结构。

> 不变量来自 [CLAUDE.md §2.1 / §2.2 / §3](../../CLAUDE.md)。本 spec 中所有设计点都要回到这三条上自检。

---

## 用户故事

```
作为一名寿险代理人，
我希望  打开终端运行一行命令，
就能  与一个写死的虚拟客户「王先生」开始一轮文本陪练对话，
体验到  客户基于自身画像和我们的历史对话给出真实反应，
观察到  客户不会主动报家底、不会主动问条款、不会主动催价格，
能够  随时通过 /quit 退出，或 /reset 重新开始，
以便  在没有评估系统的情况下，先肉眼验证陪练对话的真实感与架构原则的落地。
```

---

## 纵切范围

- **写死的 Persona**：1 个 Python 字面量定义的客户画像样本（不引入 yaml/json 加载，那是 P4）
- **写死的 Scenario**：1 个固定场景对象，作为 system prompt 的一部分注入
- **System Prompt 模板**：通过函数渲染，把 persona + scenario 拼成一段约束 LLM 行为的提示词
- **最小对话引擎**：维护 `messages` 列表，每轮调用一次 LLM，不流式、不异步
- **CLI Demo**：标准输入循环 + `/quit` `/reset` 命令
- **pytest 引入**：作为 dev optional 依赖；测试覆盖 persona 与 prompt 渲染层（**不**测真实 LLM）

---

## 建议目录结构（增量）

只列出 P1 新增/修改的部分：

```
PeiLian/
├── pyproject.toml                  # 修改：加 [project.optional-dependencies] dev = ["pytest>=8"]
├── README.md                       # 修改：加 P1 demo 命令
├── src/peilian/
│   ├── persona.py                  # 新增：Persona dataclass + SAMPLE_PERSONA 常量
│   ├── scenario.py                 # 新增：Scenario dataclass + SAMPLE_SCENARIO 常量
│   ├── prompts.py                  # 新增：customer system prompt 模板与渲染
│   └── dialogue.py                 # 新增：多轮对话引擎
├── scripts/
│   └── demo_p1.py                  # 新增：CLI 陪练 demo
└── tests/
    ├── __init__.py                 # 新增
    ├── test_persona.py             # 新增：persona 字段与边界
    └── test_prompts.py             # 新增：被动反应约束渲染断言
```

> **为什么把 persona / scenario / prompts / dialogue 拆四个文件？**
> 这是后续阶段的接口边界：P2 状态观察器要 hook 进 dialogue，P4 persona 工厂会替换 persona.py 中的硬编码常量为生成器，P5 RAG 会被 prompts.py 引用。在 P1 把边界划清楚，后续不用大改。

---

## 计划创建/修改的文件

| # | 文件 | 类型 | 说明 |
|---|---|---|---|
| 1 | `src/peilian/persona.py` | 新增 | `Persona` dataclass + `SAMPLE_PERSONA` 常量 |
| 2 | `src/peilian/scenario.py` | 新增 | `Scenario` dataclass + `SAMPLE_SCENARIO` 常量 |
| 3 | `src/peilian/prompts.py` | 新增 | `render_customer_system_prompt(persona, scenario) -> str` |
| 4 | `src/peilian/dialogue.py` | 新增 | `Dialogue` 类，封装 messages + `send_user(text) -> str` |
| 5 | `scripts/demo_p1.py` | 新增 | CLI 主循环 + `/quit` `/reset` |
| 6 | `tests/__init__.py` | 新增 | 空文件 |
| 7 | `tests/test_persona.py` | 新增 | persona 实例化与字段范围 |
| 8 | `tests/test_prompts.py` | 新增 | 渲染输出包含被动反应核心约束 |
| 9 | `pyproject.toml` | 修改 | 添加 `[project.optional-dependencies] dev = ["pytest>=8"]` |
| 10 | `README.md` | 修改 | 加 P1 demo 命令一节 |

> **明确不做**：不创建 `src/peilian/observer.py`（P2）、不创建 `rag/` 目录（P5）、不创建 `web/` 或 `server.py`（P6）。

---

## Demo 命令

```powershell
# 1. 安装（含 dev 依赖）
pip install -e ".[dev]"

# 2. 跑陪练对话
python scripts/demo_p1.py

# 3. 跑测试
pytest
```

预期 demo 输出形如：

```
[PeiLian P1 — 单 persona 单场景陪练]

客户称呼：王先生
会面场景：办公室初次约访
时间约束：对方只预留约 20 分钟
任务提示：你是一名寿险代理人，请主动开始对话——挖需、讲解、应对异议、促成均由你推进。

操作：直接输入消息开始对话；/quit 退出；/reset 重置

代理人 > 您好王先生，我是友邦的张顾问。今天耽误您 20 分钟，先冒昧问下，您是因为什么愿意约这次见面？
客户   > 张顾问您好。同事最近买了份重疾险，我有点好奇，所以想听您讲讲。

代理人 > /quit
[陪练已结束]
```

> **CLI 开场不泄露家庭结构、已有保单、收入档、hidden_concerns 等需代理人问出来的信息**。这些信息都只存在 system prompt 里，等代理人发问后客户才会逐步显露——这是 P1 「被动反应」原则在交互层的直接体现。

预期 pytest 输出：

```
tests/test_persona.py ...      [ 60%]
tests/test_prompts.py ..       [100%]
3 passed in 0.05s
```

---

## 验收 Checklist

**结构 / 文件**
- [ ] 上述 10 个新增/修改文件全部到位
- [ ] `pyproject.toml` 仅在 `[project.optional-dependencies] dev` 中加 `pytest`，主依赖未变
- [ ] **未**创建 P2/P4/P5/P6 相关代码文件

**Persona / Prompt**
- [ ] `Persona` dataclass 是 `frozen=True`，字段类型清晰
- [ ] `SAMPLE_PERSONA` 在模块加载时即可实例化，无外部依赖
- [ ] `render_customer_system_prompt()` 输出包含 persona 关键字段（name / age / family）
- [ ] 渲染输出**显式包含**至少 4 条被动反应硬规则（见「技术设计要点 §3」）

**对话引擎**
- [ ] `Dialogue` 类初始化时把 system prompt 写入 `messages[0]`
- [ ] 每次 `send_user(text)` 后 `messages` 长度 +2（user + assistant）
- [ ] LLM 调用错误时给出明确异常或错误消息，不静默失败

**CLI Demo**
- [ ] `python scripts/demo_p1.py` 在配好 `.env` 后能进入交互循环
- [ ] `/quit` 退出，`/reset` 清空对话历史并重新打印开场说明
- [ ] 无 `OPENAI_API_KEY` 时给出明确错误并指引去 `.env` 配置（**不支持** `--skip-llm`，理由见技术设计 §6）
- [ ] Windows 控制台中文与符号正常显示（沿用 P0 的 stdout UTF-8 重配套路）

**被动反应人工验收（最关键，肉眼判断）**
- [ ] 代理人不主动问家庭结构 → 客户不主动报家底
- [ ] 代理人不主动讲保费 → 客户不主动提价格
- [ ] 代理人不主动讲条款 → 客户不主动追问条款细节
- [ ] 代理人长时间寒暄不进正题 → 客户表现出耐心耗尽（这是允许的自然反应）
- [ ] 客户**绝不**主动 say goodbye 结束对话；只有用户 `/quit` 才能结束

**Tests**
- [ ] `pytest` 在干净环境绿；测试不依赖真实 LLM key
- [ ] `test_persona.py` 覆盖：实例化、`persistence` ∈ [0,1]、`expressiveness` ∈ [0,1]
- [ ] `test_prompts.py` 覆盖：渲染非空、含 persona 关键字段、含被动反应核心关键词（如「不主动」「代理人不问」）

**Git**
- [ ] 至少一个 commit，message 第一行含 `Phase 1`
- [ ] 工作区干净

---

## 不在 P1 范围内（显式排除）

| ❌ 不做 | 何时做 |
|---|---|
| 状态观察器、销售漏斗阶段识别 | P2 |
| 必问点覆盖率计算、合规红线规则扫描 | P2 |
| LLM-as-Judge 评估、rubric | P3 |
| 多 persona / 配置文件加载 / 难度档 | P4 |
| RAG / 知识库 / 向量库 | P5 |
| Web UI / API server | P6 |
| 错题本 / 自适应难度 | P7 |
| 流式输出 / 异步 / function calling | 暂不引入 |
| 上下文裁剪 / token 计数 / 摘要压缩 | 暂不需要（单场景对话不会爆 context） |
| Mock LLM 或集成测试 | P1 不做，避免增加复杂度（见技术设计 §5） |
| Lint / formatter / pre-commit | 维持 P0 决定，暂不引入 |
| 引入 langchain / llamaindex 等框架 | 全程审慎，本阶段都不需要 |
| 修改 `CLAUDE.md` | 本阶段无需改动宪法 |
| 创建 `phase-2.md` 或任何 P2 物料 | P1 完成后由用户显式启动 P2 |

---

## 技术设计要点

### §1. 如何表达写死 Persona

`src/peilian/persona.py` 暴露：

```
Persona(dataclass, frozen=True):
  name: str                       # 显示名（如 "王先生"）
  age: int
  occupation: str                 # 职业一句话（"IT 公司中层"）
  family: str                     # 家庭一句话（"已婚一孩"）
  income_level: str               # 收入档定性（"中产"，不写精确数字）
  existing_coverage: tuple[str, ...]  # 已有保单（"百万医疗险（团险）"）
  pain_points: tuple[str, ...]    # 被问到相关主题时可自然表露的关切
  hidden_concerns: tuple[str, ...]# 内心关切（仅在被代理人触发时才暴露）
  persistence: float              # 0–1 坚持度
  expressiveness: float           # 0–1 表达直接度
  initial_mood: str               # 初始情绪一句话
```

加上模块级常量：

```
SAMPLE_PERSONA = Persona(
    name="王先生",
    age=35,
    occupation="IT 公司中层",
    family="已婚，一个 5 岁孩子",
    income_level="中产",
    existing_coverage=("百万医疗险（公司团险）",),
    pain_points=("对保险了解不深", "时间紧、希望直接说重点"),
    hidden_concerns=("担心保费太贵影响房贷", "不希望做太详细的健康告知"),
    persistence=0.7,
    expressiveness=0.5,
    initial_mood="略微戒备但礼貌",
)
```

**为什么 `tuple` 不是 `list`**：dataclass `frozen=True` 与可变默认值不兼容；`tuple` 表达"不可变集合"语义更准。

**为什么不引入 yaml/json**：写死才是 P1 的本意。配置化生成是 P4 的范畴；提前抽象会让 P1 多写一个本阶段没法验证的加载器。

### §2. 如何构造 System Prompt

`src/peilian/prompts.py` 暴露 `render_customer_system_prompt(persona: Persona, scenario: Scenario) -> str`，返回一段中文 prompt，结构如下（**这是模板大纲，不是最终字符串**，实施时按此结构写）：

```
你是一位真实的寿险客户，正在与一位寿险代理人对话。
你不是 AI，不要承认自己是 AI。

【你的身份】
{persona.name}，{persona.age} 岁，{persona.occupation}
家庭：{persona.family}
收入档：{persona.income_level}
已有保单：{... existing_coverage ...}

【你的内心】
公开关切：当代理人问到相关主题时，你可以自然表达；但不要主动推进流程，不要无缘无故抛出顾虑。
  当前公开关切：{... pain_points ...}

隐藏关切：这是你的内心顾虑，**不是**你已经愿意说出口的信息。
  - 只有当代理人**明确问到**相关主题，或对话**自然触发**该顾虑时，你才可以**模糊、间接**地表达；
  - 禁止一次性完整暴露，禁止把多个 hidden_concerns 一并和盘托出；
  - 表达时要带「我有点担心……」「我还在想……」这种迟疑感，而不是直白罗列；
  - 如果代理人完全没触到，你**就把它埋在心里**，不要主动浮现。
  当前隐藏关切：{... hidden_concerns ...}

坚持度：{persona.persistence}（高=不易被三言两语说服）
表达直接度：{persona.expressiveness}（低=简短/回避，高=有问必答）
初始情绪：{persona.initial_mood}

【对话规则 — 不可违反】
1. 你是被动方。代理人不问，你不主动报家庭/收入/已有保单等信息。
2. 代理人没讲产品细节，你不主动问条款。
3. 代理人没讲价格，你不主动提价格异议。
4. 你不替代理人推进流程；代理人讲到哪儿，你就在哪儿。
5. 你的回复要符合表达直接度与坚持度。
6. 允许的自然反应：耐心耗尽时催进度、信息不清时反问、被打动时态度软化。
   但这必须是「真人客户在同样情境下也会出现」的反应。
7. 你不主动结束对话。

【场景】
{scenario.context}
{scenario.constraints}

【风格】
说人话，简短自然，不必每句都礼貌客套。可以表现迟疑、思考、戒备。
```

**关键设计选择**：

- 用**中文 prompt**：客户角色就是中文母语者，prompt 与回复语种一致更自然
- 把规则**编号 + 强语气**：LLM 对编号列表与"不可违反"等措辞响应更稳
- 把 `hidden_concerns` 显式列在 prompt 中告诉 LLM "**不**主动暴露"——这是明知风险但故意为之，因为 P1 不引入"运行时隐藏"机制；依赖 LLM 自律。如果发现 LLM 频繁泄露，再看是否把 hidden_concerns 移出 system prompt 单独传或在 P2 加观察器拦截
- 不在 prompt 中嵌入产品条款细节——条款相关内容是 P5 RAG 的范畴，P1 让客户回避此类细节即可

### §3. 如何约束 AI 客户「被动反应」

三道防线，层层递进：

| 防线 | 实现 | 期望覆盖 |
|---|---|---|
| 1. Prompt 硬规则 | system prompt §2 中编号 1–7 条对话规则 + 「你的内心」中针对 `pain_points` / `hidden_concerns` 的分级约束（公开关切被问才表达；隐藏关切只能被明确触发后模糊间接表达，禁止一次性完整暴露）| 80% 场景 |
| 2. Persona 字段语义约束 | `expressiveness` 低 → 客户简短；`persistence` 高 → 不易松口；`hidden_concerns` 在 prompt 中以「内心顾虑、迟疑表达、禁止和盘托出」三段约束包装 | 增强 LLM 对规则的具象化理解 |
| 3. Tests 渲染层断言 | `test_prompts.py` 断言渲染输出包含「不主动」「代理人不问」「禁止一次性完整暴露」等关键字 | 防止重构时规则被无意删除 |

**P1 不做的两条更严的防线**（留给后续）：
- 运行时检测客户违反规则（属于 P2 状态观察器）
- LLM judge 对客户回复打分（属于 P3）

**风险与缓解**：LLM 仍可能偶发主动报信息。P1 阶段以"人工肉眼观察 + 规则反复打磨"为主，不引入自动化检测。如果偏离严重到无法接受，启动 P2 时优先把"被动反应监控"做进观察器。

### §4. 如何做最小多轮对话

`src/peilian/dialogue.py` 暴露 `Dialogue` 类：

```
Dialogue:
  __init__(persona, scenario, settings):
    self.client = OpenAI(api_key=..., base_url=...)
    self.model = settings.model
    self.system_prompt = render_customer_system_prompt(persona, scenario)
    self.messages = [{"role": "system", "content": self.system_prompt}]

  send_user(text: str) -> str:
    self.messages.append({"role": "user", "content": text})
    resp = self.client.chat.completions.create(
        model=self.model,
        messages=self.messages,
        temperature=0.7,
    )
    answer = resp.choices[0].message.content or ""
    self.messages.append({"role": "assistant", "content": answer})
    return answer

  reset() -> None:
    self.messages = [{"role": "system", "content": self.system_prompt}]
```

**对话历史维护**：完整保留，不裁剪。P1 单场景对话很难突破 token 上限；裁剪/摘要留给上下文真出问题的那一阶段。

**温度**：`0.7`（默认体感自然）。`temperature=0` 会让客户机械化，不利于陪练；过高又难复现。

**异常处理**：捕获 `openai` 抛的异常，CLI 层打印 `[LLM 调用失败：xxx]` 并继续等待用户下一条输入（不让一次失败拖垮整个会话）。

**为什么是类不是函数**：未来 P2 状态观察器需要在 `send_user` 前后打点，类形态便于加 hook。

### §5. 是否引入 pytest，最小测试范围

**引入**。作为 `[project.optional-dependencies] dev` 加入 `pytest>=8`，由开发者 `pip install -e ".[dev]"` 启用。不进主依赖，免得部署/演示环境变重。

**最小测试范围**（全部不依赖真实 LLM）：

`tests/test_persona.py`：
- `SAMPLE_PERSONA` 能导入并实例化
- `0 <= SAMPLE_PERSONA.persistence <= 1`
- `0 <= SAMPLE_PERSONA.expressiveness <= 1`
- `existing_coverage` / `pain_points` / `hidden_concerns` 都是 `tuple`
- 实例化非法值（如 `persistence=2.0`）能在初始化或独立 `validate()` 中被检测（实施时决定是 dataclass `__post_init__` 还是单独函数）

`tests/test_prompts.py`：
- `render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)` 返回非空 str
- 输出包含 `SAMPLE_PERSONA.name`、`str(SAMPLE_PERSONA.age)`
- 输出包含被动反应核心关键词集（至少命中 3/4：「不主动」、「代理人不问」、「不替代理人推进」、「不主动结束对话」）
- 输出包含 `SAMPLE_SCENARIO.context` 中的关键标识词

**明确不做**：
- 不写 `dialogue.py` 的端到端 LLM 测试（成本高、不稳定）
- 不引入 `pytest-mock` 或自建 LLM mock（增加复杂度，收益低）
- 不写 CLI demo 的子进程测试

**理由**：P1 验收的核心证据是「人工跑 demo 观察客户被动反应」，这本就不是 unit test 能完整覆盖的。pytest 在 P1 的角色是**防止 prompt 渲染被无意改坏**，不是端到端验证。

### §6. 关于 `--skip-llm`：P1 **不**支持

P0 demo 是健康检查，跳过 LLM 仍能验证地基；P1 demo 是业务对话本身，跳过 LLM 等于没跑。**无 key 直接报错并指引** `.env` 配置，比加一个无意义的"假对话"模式更诚实。

如果开发者无 key 想看代码结构，让他们看 `pytest`：测试覆盖了 persona 与 prompt 层，完全无需 LLM。

---

## 实施任务拆分（轻量 TDD 顺序）

按「先写测试 → 看到失败 → 实现到测试通过 → 再做无法测的层」的轻量 TDD 节奏推进。这能强制 prompt 中被动反应约束的关键字不被遗漏，且不会引入 mock LLM 等重型测试基础设施。

| # | 任务 | 备注 |
|---|---|---|
| 1 | 修改 `pyproject.toml`：加 `[project.optional-dependencies] dev = ["pytest>=8"]` | — |
| 2 | `pip install -e ".[dev]"` 安装 dev 依赖 | — |
| 3 | 新增 `tests/__init__.py` + `tests/test_persona.py` + `tests/test_prompts.py`（**先于实现**）| 测试以 import 失败的方式自然 fail |
| 4 | 跑 `pytest`，**确认全部失败**（缺少 persona / prompts 模块）| 这是 TDD 的红灯 |
| 5 | 实现 `src/peilian/persona.py` + `src/peilian/scenario.py` + `src/peilian/prompts.py` | 实现到测试可以跑过为止，不超额 |
| 6 | 跑 `pytest`，**确认全部通过** | TDD 的绿灯 |
| 7 | 实现 `src/peilian/dialogue.py` + `scripts/demo_p1.py` | 这两层不进单测覆盖 |
| 8 | 修改 `README.md`：加 P1 demo 命令 | — |
| 9 | 用户人工跑 demo，肉眼验证被动反应（**最关键的验收**）| 见验收 checklist 「被动反应人工验收」 |
| 10 | 用户审阅、勾选 checklist | — |
| 11 | 由用户授权 commit（**本阶段不自动 commit**） | 见「commit 策略」一节 |

---

## 已确认决策

以下决策已与用户对齐，实施时按此执行：

### Q1. `SAMPLE_SCENARIO` 设定 → **方案 A**

- 35 岁王先生，已婚一孩，IT 公司中层，已有公司团险百万医疗
- 同事最近买了份重疾险，他想了解
- 办公室初次约访，给代理人 20 分钟
- 价格敏感、时间紧、不愿做详细健康告知

> 注意：这些信息**只进 system prompt**，不在 CLI 开场展示。CLI 只显示称呼/场景/时间/任务（见 Demo 命令一节）。

### Q2. `hidden_concerns` 进 system prompt → **方案 A，但加强约束**

`hidden_concerns` 写入 system prompt，但用三段强约束包装：

1. `hidden_concerns` 是内心顾虑，**不是**已经愿意说出口的信息；
2. 只有当代理人**明确问到相关主题**，或对话**自然触发**该顾虑时，才可以**模糊、间接**地表达；
3. **禁止一次性完整暴露** `hidden_concerns`；表达时要带「我有点担心……」「我还在想……」的迟疑感，不和盘托出。

具体约束文案体现在 §2 system prompt 模板的「你的内心」段、§3 三道防线表的第 1 行、`test_prompts.py` 的关键字断言三个位置，**三处必须保持一致**，缺一不可。

如果 demo 中仍频繁泄露，P2 再加观察器拦截。

### Q3. CLI 输入 → **单行**

每按 Enter 即发送。多轮对话天然就是短句节奏；多行模式留给后续按需引入。

### Q4. 客户开场白 → **客户不主动开场**

CLI 启动后只打印场景介绍，等待**代理人**先输入第一句；客户从此刻开始被动反应。这是 §2.1 在交互层的直接落地；CLI 提示语会显式告诉用户"请主动开始对话"。

### Q5. Commit 策略 → **两次 commit，分离文档与实现**

- **Commit 1（先）**：当本份 phase-1.md 经审批后，**单独**提交 phase-1.md。这一步把"阶段计划"作为独立可追溯的物料归档，便于事后审计 plan→impl 的对应关系。
- **Commit 2（后）**：P1 全部实现完成、人工验收通过、`pytest` 全绿后，**实现物料一次性**提交。

> 与 P0 一次性 commit 模式不同的地方：P1 spec 比 P0 重得多，先把 spec 落库再开工，能让"实施过程中是否偏离计划"这件事可被 git 历史回看。

### Q6. P2 hook 预留 → **只允许注释占位，不设计接口**

`dialogue.py` 中可写注释占位（如 `# P2: pre/post-message observer hooks would go here`），**不**预先定义 hook 函数签名、协议类、回调列表等任何接口形态。等 P2 真启动并有真实 caller 时再设计接口，避免空想式 API。

---

## Commit 策略与建议 commit message（按 Q5：两次 commit）

### Commit 1 — phase-1.md 单独入库（本份 spec 经审批后立即执行）

```
docs(P1): 起草 phase-1.md 阶段计划

- 单 persona 单场景的端到端最小陪练 spec
- 决策记录: SAMPLE_SCENARIO=A; hidden_concerns 进 prompt 但加强不泄露约束;
  CLI 单行输入; 客户不主动开场; 两次 commit; 不预设 P2 hook 接口
- 实施任务采用轻量 TDD 顺序 (先写测试, 看红灯, 再实现, 看绿灯)
```

### Commit 2 — P1 实现物料（实现完成 + 人工验收通过 + pytest 全绿后执行）

```
feat(P1): 单 persona 单场景的最小文本陪练

- 新增 src/peilian/persona.py: Persona dataclass + SAMPLE_PERSONA
  (35 岁价格敏感型客户, 含 pain_points / hidden_concerns / 坚持度)
- 新增 src/peilian/scenario.py: Scenario dataclass + SAMPLE_SCENARIO
- 新增 src/peilian/prompts.py: render_customer_system_prompt(),
  含 7 条「被动反应」硬约束规则 + hidden_concerns 三段不泄露约束
- 新增 src/peilian/dialogue.py: 最小多轮对话引擎 (Dialogue 类,
  messages 维护 + LLM 调用, 不流式不异步; 仅注释占位 P2 observer hook)
- 新增 scripts/demo_p1.py: CLI 陪练 demo, 单行输入, 客户不主动开场,
  开场只展示称呼/场景/时间/任务, 不泄露需被代理人问出的信息;
  支持 /quit /reset
- 引入 pytest (作为 [project.optional-dependencies] dev),
  新增 tests/test_persona.py / tests/test_prompts.py,
  覆盖 persona 字段范围与 system prompt 中被动反应约束的渲染
- 更新 README.md 加 P1 demo 命令

人工验证: 客户严格遵守 CLAUDE.md §2.1 被动反应原则 (checklist 全部勾选)
```

---

## 完成条件

1. 验收 checklist 全部勾选
2. 用户人工跑过 `python scripts/demo_p1.py` 并完成被动反应人工验收
3. `pytest` 全绿
4. 由用户授权后 commit

---

## 进入 P2 的前置条件（仅作占位，不在 P1 内执行）

- 本阶段所有验收项通过
- 用户显式指示切换游标
- 切换时由用户在 ROADMAP 把 P1 改为「✅ 已完成」并把游标移到 P2
- 启动 P2 时再起草 `phase-2.md`（**P1 内不创建该文件**）
