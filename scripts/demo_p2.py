"""PeiLian P2 — 规则评估 demo。

设计原则（来自 docs/phases/phase-2.md）：
- 不依赖 OPENAI_API_KEY（评估器纯本地，规则层不调 LLM）
- 写死使用 SAMPLE_CONVERSATION_P2，不参数化（Q10）
- Windows 控制台 UTF-8 输出（与 demo_p0/demo_p1 同节奏）
- 演示「漏问 + 违规」两类问题：漏 income / future_planning；
  命中 guarantee_return + mislead_vs_deposit
"""

from __future__ import annotations

import sys


def _ensure_utf8_stdout() -> None:
    # Windows 默认控制台是 GBK，无法打印 ✓ / ✗ / ⚠ / ═ 等符号；切到 UTF-8。
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


_HEADER = (
    "[PeiLian P2 — 规则评估 demo]\n"
    "样本对话：SAMPLE_CONVERSATION_P2"
    "（同时包含漏问与违规，用于演示评估能力）\n"
)


def main() -> int:
    _ensure_utf8_stdout()

    from peilian.conversations import SAMPLE_CONVERSATION_P2
    from peilian.observer import evaluate
    from peilian.report import render_report

    print(_HEADER)
    report = evaluate(SAMPLE_CONVERSATION_P2)
    print(render_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
