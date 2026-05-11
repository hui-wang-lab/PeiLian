"""P4 Persona 工厂测试：yaml 加载 / schema 校验 / 难度缩放 / meta 回查。"""

import os
import tempfile
from pathlib import Path

import pytest

from peilian.persona_factory import (
    PersonaMeta,
    adjust_difficulty_values,
    get_persona_meta,
    load_persona_from_yaml,
    load_personas_from_dir,
)

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PERSONAS_DIR = _PROJECT_ROOT / "personas"


def test_load_single_yaml_returns_valid_persona():
    """单文件 yaml 加载 → 有效 Persona 实例。"""
    yaml_path = _PERSONAS_DIR / "price_sensitive_midcareer.yaml"
    persona = load_persona_from_yaml(str(yaml_path))
    assert persona.name == "张先生"
    assert persona.age == 35
    assert persona.persistence == pytest.approx(0.7)
    assert persona.expressiveness == pytest.approx(0.5)
    assert len(persona.hidden_concerns) == 2


def test_load_all_five_personas_from_dir():
    """目录加载 → 5 份全部成功，每份 hidden_concerns ≥ 2 条。"""
    personas = load_personas_from_dir(str(_PERSONAS_DIR))
    assert len(personas) == 5
    for p in personas:
        assert len(p.hidden_concerns) >= 2
        meta = get_persona_meta(p)
        assert isinstance(meta, PersonaMeta)
        assert len(meta.hidden_concerns) >= 2
        for hc in meta.hidden_concerns:
            assert "key" in hc
            assert "label" in hc
            assert "keywords" in hc
            assert "initial_stage" in hc


def test_load_personas_include_user_is_explicit(tmp_path: Path):
    """默认仅加载内置目录；Web 需要 _user 时显式 include_user=True。"""
    sample = """
name: "测试客户"
age: 30
occupation: "测试"
family: "已婚"
income_level: "中等"
existing_coverage: ["社保"]
pain_points: ["忙"]
hidden_concerns:
  - key: test_concern
    label: "测试关切"
    keywords: ["test"]
    initial_stage: untouched
persistence: 0.5
expressiveness: 0.5
initial_mood: "正常"
"""
    (tmp_path / "builtin.yaml").write_text(sample, encoding="utf-8")
    (tmp_path / "_user").mkdir()
    (tmp_path / "_user" / "custom.yaml").write_text(
        sample.replace("测试客户", "自定义客户"),
        encoding="utf-8",
    )

    assert len(load_personas_from_dir(str(tmp_path))) == 1
    assert len(load_personas_from_dir(str(tmp_path), include_user=True)) == 2


def _write_temp_yaml(content):
    """写入临时文件并返回路径（调用方负责删除）。"""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    try:
        f.write(content)
        f.close()  # Windows 上必须先关闭
        return f.name
    except:
        f.close()
        raise


def test_yaml_missing_required_field_raises_keyerror():
    """缺必填字段 → KeyError。"""
    bad_yaml = """
name: "测试"
age: 30
occupation: "IT"
family: "已婚"
income_level: "中产"
existing_coverage:
  - "社保"
pain_points:
  - "忙"
hidden_concerns:
  - key: test
    label: "测试"
    keywords: ["test"]
    initial_stage: untouched
persistence: 0.5
"""
    # 故意缺 expressiveness 和 initial_mood
    path = _write_temp_yaml(bad_yaml)
    try:
        with pytest.raises(KeyError):
            load_persona_from_yaml(path)
    finally:
        os.unlink(path)


def test_yaml_invalid_hidden_concern_key_raises_valueerror():
    """hidden_concerns key 不符合命名规则 → ValueError。"""
    bad_yaml = """
name: "测试"
age: 30
occupation: "IT"
family: "已婚"
income_level: "中产"
existing_coverage: ["社保"]
pain_points: ["忙"]
hidden_concerns:
  - key: InvalidKey
    label: "测试"
    keywords: ["test"]
    initial_stage: untouched
persistence: 0.5
expressiveness: 0.5
initial_mood: "正常"
"""
    path = _write_temp_yaml(bad_yaml)
    try:
        with pytest.raises(ValueError):
            load_persona_from_yaml(path)
    finally:
        os.unlink(path)


def test_yaml_empty_keywords_raises_valueerror():
    """hidden_concerns keywords 为空 → ValueError。"""
    bad_yaml = """
name: "测试"
age: 30
occupation: "IT"
family: "已婚"
income_level: "中产"
existing_coverage: ["社保"]
pain_points: ["忙"]
hidden_concerns:
  - key: test_concern
    label: "测试"
    keywords: []
    initial_stage: untouched
persistence: 0.5
expressiveness: 0.5
initial_mood: "正常"
"""
    path = _write_temp_yaml(bad_yaml)
    try:
        with pytest.raises(ValueError):
            load_persona_from_yaml(path)
    finally:
        os.unlink(path)


def test_yaml_persistence_out_of_range_raises():
    """persistence/expressiveness 越界 → ValueError。"""
    bad_yaml = """
name: "测试"
age: 30
occupation: "IT"
family: "已婚"
income_level: "中产"
existing_coverage: ["社保"]
pain_points: ["忙"]
hidden_concerns:
  - key: test_concern
    label: "测试"
    keywords: ["test"]
    initial_stage: untouched
persistence: 1.2
expressiveness: 0.5
initial_mood: "正常"
"""
    path = _write_temp_yaml(bad_yaml)
    try:
        with pytest.raises(ValueError):
            load_persona_from_yaml(path)
    finally:
        os.unlink(path)


def test_difficulty_scaling_easy_reduces_persistence():
    """难度档缩放：easy 将 persistence 0.7 → 0.35。"""
    p, e = adjust_difficulty_values(0.7, 0.5, "easy")
    assert p == pytest.approx(0.35)
    assert e == pytest.approx(0.65)  # 0.5 * 1.3

    p_m, e_m = adjust_difficulty_values(0.7, 0.5, "medium")
    assert p_m == pytest.approx(0.7)
    assert e_m == pytest.approx(0.5)

    p_h, e_h = adjust_difficulty_values(0.7, 0.5, "hard")
    assert p_h == pytest.approx(0.91)
    assert e_h == pytest.approx(0.35)  # 0.5 * 0.7


def test_difficulty_scaling_clip_at_boundary():
    """难度档越界处理：缩放后超出 [0,1] 时 clip。"""
    # persistence 0.9 * 1.3 = 1.17 → clip 到 1.0
    p_h, e_h = adjust_difficulty_values(0.9, 0.3, "hard")
    assert p_h == pytest.approx(1.0)
    assert e_h == pytest.approx(0.21)

    # expressiveness 0.9 * 1.3 = 1.17 → clip 到 1.0
    p_e, e_e = adjust_difficulty_values(0.3, 0.9, "easy")
    assert e_e == pytest.approx(1.0)


def test_difficulty_monotonicity():
    """难度档单调性：easy.persistence ≤ medium ≤ hard；expressiveness 反向。"""
    for yaml_file in _PERSONAS_DIR.glob("*.yaml"):
        p_easy, _ = adjust_difficulty_values(0.7, 0.5, "easy")
        p_med, _ = adjust_difficulty_values(0.7, 0.5, "medium")
        p_hard, _ = adjust_difficulty_values(0.7, 0.5, "hard")
        assert p_easy <= p_med <= p_hard

        _, e_easy = adjust_difficulty_values(0.5, 0.7, "easy")
        _, e_med = adjust_difficulty_values(0.5, 0.7, "medium")
        _, e_hard = adjust_difficulty_values(0.5, 0.7, "hard")
        assert e_easy >= e_med >= e_hard
        break  # 公式确定性，测一次即可


def test_persona_is_frozen_after_factory():
    """返回的 Persona 是 frozen。"""
    from dataclasses import FrozenInstanceError

    yaml_path = _PERSONAS_DIR / "price_sensitive_midcareer.yaml"
    persona = load_persona_from_yaml(str(yaml_path))
    with pytest.raises(FrozenInstanceError):
        persona.name = "李四"


def test_get_persona_meta_returns_structured_concerns():
    """get_persona_meta 能回查到结构化 hidden_concerns。"""
    yaml_path = _PERSONAS_DIR / "price_sensitive_midcareer.yaml"
    persona = load_persona_from_yaml(str(yaml_path))
    meta = get_persona_meta(persona)
    assert meta.source_path == str(yaml_path)
    assert meta.difficulty == "medium"
    concern_keys = [hc["key"] for hc in meta.hidden_concerns]
    assert "price_sensitive" in concern_keys
    assert "refuse_long_health_disclosure" in concern_keys


def test_get_persona_meta_distinguishes_same_persona_different_difficulty():
    """同一 yaml 加载多个难度后，meta 回查不能串到其他 difficulty。"""
    yaml_path = _PERSONAS_DIR / "price_sensitive_midcareer.yaml"

    persona_easy = load_persona_from_yaml(str(yaml_path), difficulty="easy")
    persona_hard = load_persona_from_yaml(str(yaml_path), difficulty="hard")

    assert get_persona_meta(persona_easy).difficulty == "easy"
    assert get_persona_meta(persona_hard).difficulty == "hard"
