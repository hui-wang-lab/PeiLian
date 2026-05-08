"""PeiLian P1 — 单 persona 单场景 CLI 陪练 demo。

设计原则（来自 docs/phases/phase-1.md）：
- 客户不主动开场；CLI 启动后等待代理人先输入第一句
- CLI 开场只展示称呼/场景/时间/任务，不泄露家庭/职业/收入/已有保单/hidden_concerns
- 单行输入：每按 Enter 即发送
- /quit 退出；/reset 重置对话历史
- 无 OPENAI_API_KEY 时给出明确错误并指引去 .env 配置；不支持 --skip-llm
"""

from __future__ import annotations

import sys


def _ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


_OPENING = """[PeiLian P1 — 单 persona 单场景陪练]

客户称呼：王先生
会面场景：办公室初次约访
时间约束：对方只预留约 20 分钟
任务提示：你是一名寿险代理人，请主动开始对话——挖需、讲解、应对异议、促成均由你推进。

操作：直接输入消息开始对话；/quit 退出；/reset 重置
"""


def _print_opening() -> None:
    print(_OPENING)


def main() -> int:
    _ensure_utf8_stdout()

    from peilian.config import load_settings
    from peilian.dialogue import Dialogue
    from peilian.persona import SAMPLE_PERSONA
    from peilian.scenario import SAMPLE_SCENARIO

    settings = load_settings()
    if not settings.has_llm_credentials:
        print("[错误] 未检测到 OPENAI_API_KEY。")
        print(
            "       请将 .env.example 拷贝为 .env，"
            "填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL 后重试。"
        )
        print("       说明：P1 不支持 --skip-llm（陪练对话本身依赖 LLM）。")
        return 1

    try:
        dialogue = Dialogue(SAMPLE_PERSONA, SAMPLE_SCENARIO, settings)
    except Exception as e:
        print(f"[初始化失败] {type(e).__name__}: {e}")
        return 1

    _print_opening()

    while True:
        try:
            user_input = input("代理人 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("[陪练已结束]")
            return 0

        if not user_input:
            continue

        if user_input == "/quit":
            print("[陪练已结束]")
            return 0

        if user_input == "/reset":
            dialogue.reset()
            print("[对话已重置]\n")
            _print_opening()
            continue

        try:
            answer = dialogue.send_user(user_input)
        except Exception as e:
            print(f"[LLM 调用失败：{type(e).__name__}: {e}]")
            continue

        print(f"客户   > {answer}\n")


if __name__ == "__main__":
    sys.exit(main())
