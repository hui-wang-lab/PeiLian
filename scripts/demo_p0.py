"""PeiLian Phase 0 健康检查 demo。

证明地基跑通：配置加载 + 包导入 + LLM 单轮往返。
传 --skip-llm 可跳过真实 LLM 调用，仅做地基验证。
"""

from __future__ import annotations

import argparse
import sys


def _ensure_utf8_stdout() -> None:
    # Windows 默认控制台是 GBK，无法打印 ✓ / ⏭ 等符号；切到 UTF-8。
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


def main() -> int:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="PeiLian Phase 0 健康检查")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="跳过真实 LLM 调用，只验证配置加载与包导入",
    )
    args = parser.parse_args()

    print("[PeiLian Phase 0 健康检查]")

    # [1/4] 配置加载
    from peilian.config import load_settings

    settings = load_settings()
    print("[1/4] ✓ 配置加载成功")
    print(f"        base_url = {settings.base_url or '<未配置>'}")
    print(f"        model    = {settings.model or '<未配置>'}")

    # [2/4] 包导入
    import peilian

    print(f"[2/4] ✓ 包导入成功 (peilian v{peilian.__version__})")

    # [3/4] / [4/4] 调 LLM 或跳过
    if args.skip_llm:
        print("[3/4] ⏭ 已跳过 LLM 调用 (--skip-llm)")
        print("[4/4] ⏭ 已跳过响应校验")
        print("\n✓ Phase 0 demo 通过（地基验证模式）")
        return 0

    if not settings.has_llm_credentials:
        print("[3/4] ✗ 缺少 OPENAI_API_KEY，无法调用 LLM")
        print("        提示：填好 .env 后重试，或加 --skip-llm 跑地基验证模式")
        return 1

    try:
        from openai import OpenAI
    except ImportError as e:
        print(f"[3/4] ✗ openai SDK 导入失败：{e}")
        return 1

    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    prompt = "用一句话证明你能正常对话。"
    print("[3/4] → 调用 LLM…")

    try:
        response = client.chat.completions.create(
            model=settings.model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
    except Exception as e:
        print(f"[3/4] ✗ LLM 调用失败：{type(e).__name__}: {e}")
        return 1

    answer = response.choices[0].message.content or "<空响应>"
    print("[4/4] ✓ 收到响应：\n")
    print(f"  Q: {prompt}")
    print(f"  A: {answer.strip()}")
    print("\n✓ Phase 0 demo 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
