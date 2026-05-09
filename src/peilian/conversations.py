"""P2 样本对话：demo 与 tests 共用。

来源：docs/phases/phase-2.md §5
- 单份样本同时覆盖「漏问」与「违规」两类问题
- 故意漏问：income（收入）、future_planning（未来规划）
- 故意触发：guarantee_return + mislead_vs_deposit
  （同一句话命中两条规则，验证 observer 多命中能力）
- 客户应答（role=assistant）严格被动反应，不主动报家庭/收入信息
  （CLAUDE.md §2.1）；这些应答不参与评估，只是为了让样本读起来像真对话
"""

from __future__ import annotations


SAMPLE_CONVERSATION_P2: list[dict[str, str]] = [
    # 0：system 占位（demo 不依赖具体 prompt 内容）
    {"role": "system", "content": ""},

    # 1：代理人 — 命中 family_structure（「几口人」「几个孩子」）
    {
        "role": "user",
        "content": "您好王先生，先了解下您家里几口人，有几个孩子？",
    },
    # 2：客户 — 被动应答
    {"role": "assistant", "content": "三口人，太太和一个孩子。"},

    # 3：代理人 — 命中 occupation（「您是做什么的」「行业」）
    {
        "role": "user",
        "content": "您是做什么的？方便了解下行业吗？",
    },
    # 4：客户 — 被动应答
    {"role": "assistant", "content": "IT 行业。"},

    # 5：代理人 — 命中 existing_coverage（「保险」），同时触发 2 条红线
    #     - guarantee_return（「保证收益」+ pattern）
    #     - mislead_vs_deposit（「比存款」）
    {
        "role": "user",
        "content": (
            "那您之前买过什么保险吗？我推荐这款产品保证收益 4.5%，"
            "比存款利息高得多。"
        ),
    },
    # 6：客户 — 被动应答（追问收益是否属实，但不直接说违规话）
    {
        "role": "assistant",
        "content": "公司有团险吧。这个收益是真的吗？",
    },

    # 7：代理人 — 命中 health_status（「身体」「手术」）
    {
        "role": "user",
        "content": "您身体怎么样，做过手术吗？",
    },
    # 8：客户 — 被动应答
    {"role": "assistant", "content": "还行。"},
]


SAMPLE_CONVERSATION_P3: list[dict[str, str]] = [
    # 0：system 占位（demo 不依赖具体 prompt 内容）
    {"role": "system", "content": ""},

    # 1：代理人 — 开场较空泛，尚未问家庭结构
    {"role": "user", "content": "您好张先生，今天我们简单聊聊。"},
    # 2：客户 — 故意越界：未问家庭即报家庭结构；同时给后续一致性埋点
    {
        "role": "assistant",
        "content": "你好，我家里 5 口人，太太是医生，在协和，还有两个孩子和岳母。",
    },

    # 3：代理人 — 命中 occupation
    {"role": "user", "content": "那您工作呢？"},
    # 4：客户 — 故意越界：职业被问到可答，但价格敏感尚未触发
    {"role": "assistant", "content": "我做 IT 的。其实我最担心的就是这款贵不贵。"},

    # 5：代理人 — 异议处理较模板化
    {
        "role": "user",
        "content": "这款其实定价很合理，您看每天也就一杯咖啡的钱。",
    },
    # 6：客户 — 故意一致性问题：太太职业前后不一致
    {"role": "assistant", "content": "嗯。对了我太太在律所做合伙人，工作蛮忙。"},

    # 7：代理人 — 命中 health_status
    {"role": "user", "content": "您身体怎么样？"},
    # 8：客户 — 正常被动回答
    {"role": "assistant", "content": "还行，没什么大问题。"},
]
