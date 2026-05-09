"""PeiLian P3 — LLM-as-Judge 综合评估 demo。

设计原则（来自 docs/phases/phase-3.md）：
- 写死使用 SAMPLE_CONVERSATION_P3，不参数化
- 强制依赖 OPENAI_API_KEY，不支持 --skip-llm
- 输出 P2 规则层 + P3 代理人评分 + P3 客户行为诊断
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


_HEADER = (
    "[PeiLian P3 — LLM-as-Judge 评估 demo]\n"
    "样本对话：SAMPLE_CONVERSATION_P3"
    "（含 AI 客户越界 + 一致性问题，用于演示 customer judge 能力）\n"
)


def main() -> int:
    _ensure_utf8_stdout()

    from peilian.config import load_settings
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import build_judge_result, render_judge_result

    settings = load_settings()
    if not settings.has_llm_credentials:
        print("[错误] 未检测到 OPENAI_API_KEY。")
        print(
            "       请将 .env.example 拷贝为 .env，"
            "填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL 后重试。"
        )
        print("       说明：P3 demo 不支持 --skip-llm（judge 评估本身依赖真实 LLM）。")
        return 1

    print(_HEADER)
    try:
        result = build_judge_result(SAMPLE_CONVERSATION_P3)
    except Exception as e:
        print(f"[P3 judge 调用失败：{type(e).__name__}: {e}]")
        print("请检查 OPENAI_MODEL / OPENAI_BASE_URL 是否支持 chat completions 与 response_format=json_object。")
        return 1

    print(render_judge_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
