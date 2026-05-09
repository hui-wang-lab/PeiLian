"""手动验证 P3 LLM judge 稳定性。

该脚本会多次调用真实 LLM，故不进入 pytest / CI。
"""

from __future__ import annotations

import argparse
import statistics
import sys


def _ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P3 judge repeatedly.")
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="真实 LLM judge 运行次数，默认 5。",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.runs < 1:
        print("[错误] --runs 必须 >= 1")
        return 1

    from peilian.config import load_settings
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import build_judge_result

    settings = load_settings()
    if not settings.has_llm_credentials:
        print("[错误] 未检测到 OPENAI_API_KEY。")
        print(
            "       请将 .env.example 拷贝为 .env，"
            "填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL 后重试。"
        )
        return 1

    print("[PeiLian P3 — judge 稳定性检查]")
    print(f"样本对话：SAMPLE_CONVERSATION_P3；runs={args.runs}")
    print()

    dimension_scores: dict[str, list[int]] = {}
    premature_counts: list[int] = []
    inconsistency_counts: list[int] = []

    for idx in range(args.runs):
        print(f"运行 {idx + 1}/{args.runs} ...")
        try:
            result = build_judge_result(SAMPLE_CONVERSATION_P3)
        except Exception as e:
            print(f"[P3 judge 调用失败：{type(e).__name__}: {e}]")
            print("请检查 OPENAI_MODEL / OPENAI_BASE_URL 是否支持 chat completions 与 response_format=json_object。")
            return 1

        for score in result.agent_report.scores:
            dimension_scores.setdefault(score.dimension, []).append(score.score)
        premature_counts.append(len(result.customer_report.premature_disclosure_issues))
        inconsistency_counts.append(len(result.customer_report.inconsistency_issues))

    print()
    print("代理人评分波动：")
    for dimension, values in dimension_scores.items():
        mean = statistics.fmean(values)
        variance = statistics.pvariance(values) if len(values) > 1 else 0.0
        spread = max(values) - min(values)
        print(
            f"  {dimension}: values={values}, mean={mean:.2f}, "
            f"max-min={spread}, variance={variance:.3f}"
        )

    print()
    print("客户 issue 数量波动：")
    for label, values in (
        ("premature_disclosure", premature_counts),
        ("inconsistency", inconsistency_counts),
    ):
        spread = max(values) - min(values)
        variance = statistics.pvariance(values) if len(values) > 1 else 0.0
        print(f"  {label}: values={values}, max-min={spread}, variance={variance:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
