"""P4 Dialogue State Injection 测试：mock LLM 验证 system prompt 注入状态摘要。"""

from unittest.mock import MagicMock, patch

import pytest

from pathlib import Path

from peilian.customer_state import CustomerState
from peilian.dialogue import Dialogue
from peilian.persona import Persona
from peilian.persona_factory import get_persona_meta, load_persona_from_yaml
from peilian.scenario import SAMPLE_SCENARIO
from peilian.config import Settings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PERSONAS_DIR = _PROJECT_ROOT / "personas"


def _make_persona_and_meta(difficulty: str = "medium"):
    """从真实 yaml 加载 persona + meta（统一走工厂 + get_persona_meta）。"""
    yaml_path = _PERSONAS_DIR / "price_sensitive_midcareer.yaml"
    persona = load_persona_from_yaml(str(yaml_path), difficulty=difficulty)
    meta = get_persona_meta(persona)
    return persona, meta


def _mock_llm_response(text):
    """创建 mock LLM 响应。"""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_response.choices = [mock_choice]
    return mock_response


def test_first_send_user_system_prompt_has_state_summary():
    """mock LLM，首轮 send_user 时 messages[0] 含 state_summary 输出。"""
    persona, meta = _make_persona_and_meta()
    settings = Settings(api_key="fake", base_url=None, model="gpt-4o-mini")

    dialogue = Dialogue(persona, SAMPLE_SCENARIO, settings, persona_meta=meta)

    # mock LLM
    with patch.object(dialogue._client.chat.completions, "create") as mock_create:
        mock_create.return_value = _mock_llm_response("你好，有什么事？")
        dialogue.send_user("你好")

    # messages[0] 应含 state_summary 特征文本
    system_content = dialogue.messages[0]["content"]
    assert "【本轮对话状态】" in system_content
    assert "尚未被问到" in system_content


def test_multi_turn_system_prompt_reflects_updated_state():
    """多轮后 state_summary 反映状态（含已披露字段）。"""
    persona, meta = _make_persona_and_meta()
    settings = Settings(api_key="fake", base_url=None, model="gpt-4o-mini")

    dialogue = Dialogue(persona, SAMPLE_SCENARIO, settings, persona_meta=meta)

    responses = [
        "我们家里有三口人。",
        "我在互联网公司工作。",
    ]

    with patch.object(dialogue._client.chat.completions, "create") as mock_create:
        mock_create.side_effect = [_mock_llm_response(r) for r in responses]

        dialogue.send_user("您家里几口人？")
        dialogue.send_user("您做什么工作？")

    system_content = dialogue.messages[0]["content"]
    assert "family_structure" in dialogue.customer_state.disclosed_fields
    assert "occupation" in dialogue.customer_state.disclosed_fields
    # 应在已披露段落中体现，而不是仅出现在未披露清单。
    disclosed_line = next(
        line for line in system_content.splitlines() if line.startswith("已被问到并披露")
    )
    assert "家庭结构" in disclosed_line
    assert "职业行业" in disclosed_line


def test_backward_compat_persona_meta_none():
    """state_summary="" 时向后兼容。"""
    from peilian.persona import SAMPLE_PERSONA

    settings = Settings(api_key="fake", base_url=None, model="gpt-4o-mini")

    # 不传 persona_meta
    dialogue = Dialogue(SAMPLE_PERSONA, SAMPLE_SCENARIO, settings, persona_meta=None)

    assert dialogue.customer_state is None

    with patch.object(dialogue._client.chat.completions, "create") as mock_create:
        mock_create.return_value = _mock_llm_response("你好")
        dialogue.send_user("你好")

    system_content = dialogue.messages[0]["content"]
    # 不应含 P4 状态摘要特征字符串
    assert "【本轮对话状态】" not in system_content


def test_reset_resets_customer_state():
    """多轮后 reset → customer_state 回到初始。"""
    persona, meta = _make_persona_and_meta()
    settings = Settings(api_key="fake", base_url=None, model="gpt-4o-mini")

    dialogue = Dialogue(persona, SAMPLE_SCENARIO, settings, persona_meta=meta)

    with patch.object(dialogue._client.chat.completions, "create") as mock_create:
        mock_create.return_value = _mock_llm_response("我们家里有三口人。")
        dialogue.send_user("您家里几口人？")

    # 此时 state 已变化
    assert dialogue.customer_state.turn_count == 1
    assert "family_structure" in dialogue.customer_state.disclosed_fields

    # reset
    dialogue.reset()

    # 回到初始
    assert dialogue.customer_state.turn_count == 0
    assert dialogue.customer_state.disclosed_fields == frozenset()


def test_different_difficulty_reflected_in_prompt_values():
    """同一 persona 不同难度档 → system prompt 中 persistence/expressiveness 数值不同。"""
    persona_easy, meta_easy = _make_persona_and_meta(difficulty="easy")
    persona_hard, meta_hard = _make_persona_and_meta(difficulty="hard")

    # 不同难度下 get_persona_meta 不应串台
    assert meta_easy.difficulty == "easy"
    assert meta_hard.difficulty == "hard"

    settings = Settings(api_key="fake", base_url=None, model="gpt-4o-mini")

    dialogue_easy = Dialogue(persona_easy, SAMPLE_SCENARIO, settings, persona_meta=meta_easy)
    dialogue_hard = Dialogue(persona_hard, SAMPLE_SCENARIO, settings, persona_meta=meta_hard)

    # easy 的 persistence 低 (0.35)，hard 的 persistence 高 (0.91)
    easy_prompt = dialogue_easy.messages[0]["content"]
    hard_prompt = dialogue_hard.messages[0]["content"]

    assert easy_prompt != hard_prompt
