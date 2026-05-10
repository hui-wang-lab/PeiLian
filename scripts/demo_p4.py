#!/usr/bin/env python3
"""P4 Demo — Persona 工厂 + CustomerState 交互式陪练。

用法：
  python scripts/demo_p4.py                          # 交互式选择 persona + 难度
  python scripts/demo_p4.py --persona price_sensitive_midcareer --difficulty hard
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from peilian.config import load_settings
from peilian.customer_state import CustomerState
from peilian.dialogue import Dialogue
from peilian.persona_factory import get_persona_meta, load_persona_from_yaml
from peilian.scenario import SAMPLE_SCENARIO


def _list_personas(personas_dir: str) -> list[tuple[str, str]]:
    """列出可用的 persona，返回 [(文件名, 核心特征描述)]。

    清单展示用 yaml.safe_load 单独读取一次，目的是不触发工厂的注册副作用
    （未来若用户只想看清单不进入对话，避免污染注册表）。真正进入对话后，
    persona + meta 一律走 load_persona_from_yaml + get_persona_meta。
    """
    import yaml

    result = []
    for yaml_file in sorted(Path(personas_dir).glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        name = data.get("name", yaml_file.stem)
        occupation = data.get("occupation", "")
        age = data.get("age", "")
        desc = f"{name}（{age}岁，{occupation}）"
        result.append((yaml_file.stem, desc))
    return result


def _print_state_log(history: list[CustomerState]) -> None:
    """打印每轮 CustomerState 变化日志。"""
    print("\n" + "=" * 50)
    print("CustomerState 变化日志")
    print("=" * 50)
    for i, state in enumerate(history, 1):
        print(f"\n--- 第 {i} 轮 ---")
        print(f"  已披露字段: {state.disclosed_fields or '（无）'}")
        print(f"  信任度: {state.trust:.2f}")
        print(f"  耐心值: {state.patience:.2f}")
        concerns = []
        for key, stage in sorted(state.hidden_concern_stage):
            if stage != "untouched":
                concerns.append(f"{key}={stage}")
        if concerns:
            print(f"  隐藏关切: {', '.join(concerns)}")
        else:
            print(f"  隐藏关切: 全部未触发")


def main() -> None:
    parser = argparse.ArgumentParser(description="P4 Demo: Persona 工厂 + CustomerState")
    parser.add_argument("--persona", type=str, help="指定 persona 文件名（不含 .yaml）")
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        default="medium",
        help="难度档（默认 medium）",
    )
    args = parser.parse_args()

    personas_dir = str(_PROJECT_ROOT / "personas")

    # 加载 persona
    if args.persona:
        yaml_path = Path(personas_dir) / f"{args.persona}.yaml"
        if not yaml_path.exists():
            print(f"错误: 找不到 persona 文件 {yaml_path}")
            sys.exit(1)
    else:
        # 交互式选择
        available = _list_personas(personas_dir)
        print("\n=== PeiLian P4 Demo: Persona 工厂 + CustomerState ===\n")
        print("可用的 persona 清单：")
        for i, (stem, desc) in enumerate(available, 1):
            print(f"  {i}. {stem}: {desc}")

        while True:
            try:
                choice = input("\n请选择 persona 序号（或输入文件名）: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(available):
                        stem = available[idx][0]
                        break
                else:
                    stem = choice
                    if any(s == stem for s, _ in available):
                        break
                print("无效选择，请重试。")
            except EOFError:
                sys.exit(0)

        yaml_path = Path(personas_dir) / f"{stem}.yaml"

    persona = load_persona_from_yaml(str(yaml_path), difficulty=args.difficulty)
    meta = get_persona_meta(persona)

    print(f"\n已选择: {persona.name}（难度: {args.difficulty}）")
    print(f"坚持度: {persona.persistence:.2f}, 表达直接度: {persona.expressiveness:.2f}")
    print(f"隐藏关切: {', '.join(hc['label'] for hc in meta.hidden_concerns)}")

    # 加载配置
    settings = load_settings()
    if not settings.has_llm_credentials:
        print("\n错误: 未检测到 OPENAI_API_KEY。")
        print("请在项目根目录创建 .env 文件并配置：")
        print("  OPENAI_API_KEY=sk-...")
        print("  OPENAI_BASE_URL=https://api.openai.com/v1  # 可选")
        sys.exit(1)

    # 创建 Dialogue
    dialogue = Dialogue(persona, SAMPLE_SCENARIO, settings, persona_meta=meta)
    state_history: list[CustomerState] = []

    print("\n开始对话（输入 /quit 退出，/reset 重置对话）：")
    print("-" * 50)

    try:
        while True:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            if user_input == "/quit":
                break
            if user_input == "/reset":
                dialogue.reset()
                state_history.clear()
                print("\n[对话已重置]")
                continue

            response = dialogue.send_user(user_input)
            print(f"\n{persona.name}: {response}")

            # 记录 state
            if dialogue.customer_state is not None:
                state_history.append(dialogue.customer_state)

    except (KeyboardInterrupt, EOFError):
        pass

    # 打印 state 变化日志
    if state_history:
        _print_state_log(state_history)
    else:
        print("\n（未进行对话）")

    print("\n感谢使用 P4 Demo！")


if __name__ == "__main__":
    main()
