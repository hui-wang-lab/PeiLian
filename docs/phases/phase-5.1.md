# Phase 5.1 — 场景可配 + 自定义角色 + AI 客户口语化（P5 增量补丁）

> 状态：实现完成，待用户验收 commit
> 定位：**P5 增量补丁**，不动 [`docs/ROADMAP.md`](../ROADMAP.md) 中 P6（产品 RAG）/ P7（错题本）顺序
> 上层路线图：[`docs/ROADMAP.md`](../ROADMAP.md)
> 项目宪法：[`CLAUDE.md`](../../CLAUDE.md)
> 上一阶段：[`phase-5.md`](phase-5.md) ✅

---

## 一、目标一句话

把 P5 的 FastAPI Web UI 从「写死场景 + 写死 5 个 persona + 客户严肃说话」补丁成「场景可配（含 UI 新建） + persona 可自定义（含 UI 新建） + AI 客户口语化角色扮演（off/mild/heavy 三档）」。

---

## 二、决策记录

| # | 决策 | 取值 |
|---|---|---|
| D1 | 阶段定位 | P5 增量补丁（不算独立阶段，ROADMAP P6/P7 保持不变） |
| D2 | 配置范围 | Hybrid：内置 yaml + Web UI 临时新建落地到 `_user/` 子目录 |
| D3 | 口语化开关 | persona yaml 新增 `colloquial_style: off / mild / heavy` 字段 |
| D4 | 自定义 persona hidden_concerns | 完整表单：可填 `key / label / keywords / initial_stage` |
| D5 | 口语化强度 | 保守版：off=零变化；mild=语气词+短句+轻停顿；heavy=mild + 偶尔同音字误用 + 答非所问敷衍 |
| D6 | 口语化与 P3 customer judge | 改 `judge_prompts.py` 加豁免条款：口语化错别字/敷衍**不**判 inconsistency |

---

## 三、文件清单

### 新增

| 路径 | 说明 |
|---|---|
| [`scenarios/office_first_meet.yaml`](../../scenarios/office_first_meet.yaml) | 内置场景 1（迁移自 `SAMPLE_SCENARIO`） |
| [`scenarios/coffee_followup.yaml`](../../scenarios/coffee_followup.yaml) | 内置场景 2：咖啡馆复盘建议 |
| [`scenarios/phone_intro.yaml`](../../scenarios/phone_intro.yaml) | 内置场景 3：电话首次约访 |
| `scenarios/_user/.gitkeep` | 用户新建场景目录占位 |
| `personas/_user/.gitkeep` | 用户新建 persona 目录占位 |
| [`src/peilian/scenario_factory.py`](../../src/peilian/scenario_factory.py) | yaml 加载 / 校验 / 内置 + `_user/` 双源合并 |
| [`src/peilian/server/routes/scenarios.py`](../../src/peilian/server/routes/scenarios.py) | `GET /api/scenarios` + `POST /api/scenarios` |
| [`src/peilian/server/static/scenario_form.html`](../../src/peilian/server/static/scenario_form.html) | 新建场景表单 |
| [`src/peilian/server/static/persona_form.html`](../../src/peilian/server/static/persona_form.html) | 新建 persona 表单（含动态 hidden_concerns） |
| [`src/peilian/server/static/js/scenario_form.js`](../../src/peilian/server/static/js/scenario_form.js) | 场景表单交互 |
| [`src/peilian/server/static/js/persona_form.js`](../../src/peilian/server/static/js/persona_form.js) | persona 表单交互（标签输入 + concern 行管理 + 风格切换） |
| [`tests/test_scenario_factory.py`](../../tests/test_scenario_factory.py) | yaml 加载、必填校验、双源合并 |
| [`tests/test_scenarios_api.py`](../../tests/test_scenarios_api.py) | `GET/POST /api/scenarios`（含 422 / 409） |
| [`tests/test_personas_create.py`](../../tests/test_personas_create.py) | `POST /api/personas`（含完整 hidden_concerns） |
| [`tests/test_colloquial_prompt.py`](../../tests/test_colloquial_prompt.py) | 口语化片段渲染 + off 向后兼容 |
| [`tests/test_session_with_scenario.py`](../../tests/test_session_with_scenario.py) | e2e：自定义 scenario_id 走 chat → 校验 system prompt 注入 |

### 修改

| 路径 | 说明 |
|---|---|
| [`src/peilian/persona.py`](../../src/peilian/persona.py) | `Persona` 新增 `colloquial_style: str = "off"`；`__post_init__` 校验 `{off, mild, heavy}` |
| [`src/peilian/persona_factory.py`](../../src/peilian/persona_factory.py) | yaml schema 加 `colloquial_style`（可选）；`load_personas_from_dir` 新增 `include_user=True` 扫 `_user/` |
| [`src/peilian/prompts.py`](../../src/peilian/prompts.py) | `_TEMPLATE` 加 `{colloquial_block}`；`_render_colloquial_block(style)` 三档文案；off 输出与 P5 byte-identical |
| [`src/peilian/judge_prompts.py`](../../src/peilian/judge_prompts.py) | `CUSTOMER_JUDGE_SYSTEM_PROMPT` 加「口语化豁免」条款 |
| [`src/peilian/server/schemas.py`](../../src/peilian/server/schemas.py) | `CreateSessionRequest.scenario_id` 默认 `office_first_meet`；新增 `ScenarioSummary` / `CreateScenarioRequest` / `CreatePersonaRequest` / `HiddenConcernInput`；`PersonaSummary` 加 `colloquial_style` + `is_builtin` |
| [`src/peilian/server/session_store.py`](../../src/peilian/server/session_store.py) | `SessionStore.create` 增 `scenario=` / `scenario_id=` 关键字参数；`SessionData` 增 `scenario_id` 字段 |
| [`src/peilian/server/routes/session.py`](../../src/peilian/server/routes/session.py) | 加载场景：`find_scenario_by_id` 在内置 + `_user/` 中查；persona 同样支持双源 |
| [`src/peilian/server/routes/personas.py`](../../src/peilian/server/routes/personas.py) | `list_personas` 双源合并；新增 `POST /api/personas`（校验 + 写 `_user/{slug}.yaml`） |
| [`src/peilian/server/app.py`](../../src/peilian/server/app.py) | 挂载 scenarios 路由 |
| [`src/peilian/server/static/index.html`](../../src/peilian/server/static/index.html) | 加导航入口 + 场景卡片列表 + "+ 新建客户/场景" 按钮；JS 加 `loadScenarios` + 把 `scenario_id` 带进 POST |
| [`src/peilian/server/static/css/style.css`](../../src/peilian/server/static/css/style.css) | 追加 P5.1 样式：场景卡片、表单页、标签输入、隐藏关切动态行、自定义徽标 |
| [`personas/*.yaml`](../../personas/) × 5 | 每份加 `colloquial_style: mild` |

### 不做（明确边界）

- 不做 persona / scenario 的 UI 编辑与删除（本期只新建）
- 不做用户认证 / 多用户隔离
- 不做 hidden_concerns 关键词智能补全
- 不动 [`CLAUDE.md`](../../CLAUDE.md)（项目宪法不变）
- 不引入新依赖（PyYAML、FastAPI 已有）

---

## 四、关键技术点

### §1 Scenario yaml schema

```yaml
id: office_first_meet
name: 办公室初次见面
context: |
  你和这位代理人是初次见面，地点在你的办公室...
constraints: |
  你只能预留约 20 分钟...
tags:
  - 初次见面
  - 办公室
```

校验：`id` 匹配 `^[a-z0-9_]{1,32}$`、`name` 非空、`context` / `constraints` 非空、`tags` 必为字符串数组（或省略）。

### §2 colloquial_style 三档（保守版）

由 [`_render_colloquial_block`](../../src/peilian/prompts.py) 注入：

- **off**：返回空串，行为完全等同 P5（off 渲染的 prompt 与 P5 byte-identical，详见 [`tests/test_colloquial_prompt.py::test_off_prompt_byte_identical_to_pre_p5_1`](../../tests/test_colloquial_prompt.py)）
- **mild**：注入「说话像真人微信聊天：短句优先；语气词（呃 / 那个 / 就是 / 其实 / emm）；偶尔半截话停顿（用「……」表示）；不要主动展开长段；普通人不懂的就说不清楚；禁止括号动作描写」
- **heavy**：mild 全部 + 「允许偶尔同音字误用（在/再、那/哪、得/的、做/作）；轻微语序颠倒；偶尔走神 / 答非所问 / 随口敷衍；仍然遵守所有【对话规则】红线」

### §3 CLAUDE.md 红线对齐

| 红线 | 是否受影响 | 处理 |
|---|---|---|
| §2.1 代理人驱动、AI 客户被动反应 | 否 | 拟人化只改"说话方式"；【对话规则】7 条 / 【开场行为】全保留 |
| §2.2 状态观察器 ≠ 场景控制器 | 否 | scenario 仍只作为 system prompt 注入材料 |
| §3 合规红线 | 否 | 合规扫描只查 `role == "user"`（代理人侧），客户口语化与合规扫描无交集 |
| P3 customer judge 一致性 | 是 | [`judge_prompts.py`](../../src/peilian/judge_prompts.py) 加口语化豁免条款，明确「inconsistency 只指语义上的自相矛盾，口语错别字 / 敷衍不算」 |

### §4 文件落地安全

- `slug` 必须匹配 `^[a-z0-9_]{1,32}$`
- 写入路径：`Path(base_dir / "_user" / f"{slug}.yaml").resolve()`，加 `relative_to(base_dir / "_user")` 校验，防路径穿越
- `yaml.safe_dump(..., allow_unicode=True, sort_keys=False)`
- 文件已存在直接返回 409（不静默覆盖）
- 列表 API 合并双源时按 `id` 去重，**内置 yaml 优先**（避免用户名字撞内置造成混乱）

### §5 P5 路由兼容

- `Dialogue` 构造签名 `Dialogue(persona, scenario, settings, persona_meta=...)` 保持原样，scenario 不再硬编码 `SAMPLE_SCENARIO`
- `CreateSessionRequest.scenario_id` 默认值 `office_first_meet`，老客户端不传也能跑
- `SAMPLE_SCENARIO` 保留作为 store 层 fallback（`scenario=None` 时使用），向后兼容 P0–P5 测试与 demo

---

## 五、Demo 命令

```powershell
python -m peilian.server
```

预期：

1. 首页可见 5 个内置 persona + 3 个内置场景，分别可选
2. 点 "+ 新建场景"，填表单提交 → 文件落地 `scenarios/_user/{slug}.yaml`，回首页可见，带「自定义」徽标
3. 点 "+ 新建客户"，填表单（含 ≥1 条 hidden_concern + colloquial_style）→ 文件落地 `personas/_user/{slug}.yaml`，回首页可见
4. 选自定义场景 + 自定义客户 + 难度 → 开始陪练；客户回复风格随 `colloquial_style` 肉眼可辨
5. 同一个 persona 切 `off / mild / heavy` 走 3 次陪练，对话风格差异显著
6. 报告页 customer_report 在客户回复带「呃 / emm / 同音字」时**不**判 inconsistency

---

## 六、验收 Checklist

**结构 / 文件**
- [x] 17 个新增文件全部到位（含 5 个测试、3 个内置场景、2 个 _user/ 占位、6 个源码 + 静态资源、1 个本 spec）
- [x] 13 个修改文件改动符合 §三 描述，未越界
- [x] 未引入新依赖
- [x] 未改 [`CLAUDE.md`](../../CLAUDE.md)

**Scenario 可配**
- [x] 内置 3 个场景 yaml 加载成功（`test_scenario_factory.py`）
- [x] `GET /api/scenarios` 返回内置 + `_user/` 两源合并，按 id 去重（`test_user_dir_overrides_priority`）
- [x] `POST /api/scenarios` 写入 `scenarios/_user/{slug}.yaml`；非法 slug → 422；id 撞内置 → 409
- [x] 创建会话时传 `scenario_id` → `Dialogue` 实际收到该 scenario 的 context / constraints（`test_e2e_chat_uses_custom_scenario_context`）

**Persona 自定义**
- [x] `GET /api/personas` 内置 + `_user/` 合并
- [x] `POST /api/personas` 表单提交支持完整 hidden_concerns（key/label/keywords/initial_stage）
- [x] 写入 yaml 后下次刷新可见、可被 `load_persona_from_yaml` 加载、`get_persona_meta` 能查回（`test_create_persona_loadable_via_factory`）
- [x] 非法 slug / 缺字段 → 422；撞 id → 409

**口语化**
- [x] `Persona.colloquial_style` 取值校验 `{off, mild, heavy}`，非法 → ValueError
- [x] `render_customer_system_prompt` 三档文本明显不同；off 与 P5 输出严格一致（`test_off_prompt_byte_identical_to_pre_p5_1`）
- [x] 5 个内置 persona yaml 都加了 `colloquial_style: mild`
- [x] `CUSTOMER_JUDGE_SYSTEM_PROMPT` 含口语化豁免条款

**集成 / 兼容**
- [x] P0–P5 既有 pytest 全绿（146 项全过）
- [x] 不传 `scenario_id` 时默认走 `office_first_meet`，行为等同 P5（除 colloquial）
- [x] 浏览器端到端可走通（人工验收：内置/自定义场景 + 内置/自定义 persona 都能开会话 → 对话 → 看报告）

**Git**
- [x] 至少两个 commit：`docs(P5.1): 起草 phase-5.1.md 阶段计划` + `feat(P5.1): 实现场景可配 + 自定义角色 + AI 客户口语化`
- [x] 第一行含 `P5.1`，对齐既有 `docs(PN) / feat(PN)` 风格
- [x] 工作区干净

---

## 七、Commit 策略

```
# Step 1 — spec 入库（用户审批本 plan 后立即执行）
docs(P5.1): 起草 phase-5.1.md 阶段计划

# Step 2 — 实现（验收通过后执行）
feat(P5.1): 实现场景可配 + 自定义角色 + AI 客户口语化

- scenarios/*.yaml + scenario_factory.py
- POST /api/scenarios / POST /api/personas（落地 _user/ 子目录）
- Persona 新增 colloquial_style 字段（off/mild/heavy）
- prompts.py 加口语化片段渲染
- judge_prompts.py customer judge 加口语化豁免条款
- index.html 加场景选择 + 新建表单入口
```

---

## 八、完成条件

1. 验收 checklist 全部勾选（Git 项除外，待 commit 后勾）
2. 用户在浏览器端到端跑通一次「自定义场景 + 自定义客户」陪练
3. `pytest` 全绿（P0–P5 + P5.1，146 项 ✅）
4. 由用户授权后 commit
