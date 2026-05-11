"""P5.1 ScenarioFactory 测试：yaml 加载、schema 校验、双源合并。"""

from __future__ import annotations

from pathlib import Path

import pytest

from peilian.scenario_factory import (
    ID_PATTERN,
    find_scenario_by_id,
    list_scenarios,
    load_scenario_from_yaml,
)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCENARIOS_DIR = _PROJECT_ROOT / "scenarios"


def test_load_office_first_meet():
    scenario, meta = load_scenario_from_yaml(
        str(_SCENARIOS_DIR / "office_first_meet.yaml")
    )
    assert meta.id == "office_first_meet"
    assert "办公室" in scenario.context
    assert scenario.constraints.strip() != ""
    assert meta.is_builtin is True


def test_list_builtins():
    items = list_scenarios(_SCENARIOS_DIR)
    ids = {meta.id for _s, meta in items}
    assert {"office_first_meet", "coffee_followup", "phone_intro"}.issubset(ids)


def test_find_by_id_hit_and_miss():
    found = find_scenario_by_id("office_first_meet", base_dir=_SCENARIOS_DIR)
    assert found is not None
    missing = find_scenario_by_id("definitely_not_a_real_scene", base_dir=_SCENARIOS_DIR)
    assert missing is None


def test_id_pattern_accepts_valid_slugs():
    assert ID_PATTERN.match("a")
    assert ID_PATTERN.match("a1_b2")
    assert ID_PATTERN.match("o" * 32)


def test_id_pattern_rejects_invalid_slugs():
    assert ID_PATTERN.match("Aa") is None
    assert ID_PATTERN.match("中文") is None
    assert ID_PATTERN.match("a-b") is None
    assert ID_PATTERN.match("o" * 33) is None
    assert ID_PATTERN.match("") is None


def test_load_rejects_missing_required_field(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "id: bad\nname: 测试\ncontext: 略\n",
        encoding="utf-8",
    )
    with pytest.raises(KeyError):
        load_scenario_from_yaml(str(bad))


def test_load_rejects_invalid_id(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "id: Bad-Id\nname: 测试\ncontext: 略\nconstraints: 略\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_scenario_from_yaml(str(bad))


def test_user_dir_overrides_priority(tmp_path: Path):
    """内置 + _user/ 合并时按 id 去重，内置优先。"""
    base = tmp_path
    (base / "_user").mkdir()
    (base / "office_first_meet.yaml").write_text(
        "id: office_first_meet\nname: 内置版\ncontext: 内置情境\nconstraints: 内置约束\n",
        encoding="utf-8",
    )
    (base / "_user" / "office_first_meet.yaml").write_text(
        "id: office_first_meet\nname: 用户覆盖版\ncontext: 用户情境\nconstraints: 用户约束\n",
        encoding="utf-8",
    )
    items = list_scenarios(base)
    assert len(items) == 1
    _scenario, meta = items[0]
    assert meta.name == "内置版"
    assert meta.is_builtin is True
