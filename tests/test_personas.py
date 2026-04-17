"""Tests for personas module."""
from personas import AGENT_CONFIG, load_persona_spec, build_system_prompt


class TestAgentConfig:
    def test_has_all_agents(self):
        for key in ["practitioner", "redteam", "mentor", "clerk"]:
            assert key in AGENT_CONFIG

    def test_agent_has_required_fields(self):
        for key, cfg in AGENT_CONFIG.items():
            assert "name" in cfg, f"{key} missing name"
            assert "label" in cfg, f"{key} missing label"
            assert "emoji" in cfg, f"{key} missing emoji"
            assert "file" in cfg, f"{key} missing file"

    def test_names_korean(self):
        names = {cfg["name"] for cfg in AGENT_CONFIG.values()}
        assert "CFO" in names
        assert "CSO" in names
        assert "고문" in names
        assert "비서실장" in names


class TestLoadPersonaSpec:
    def test_loads_practitioner(self):
        spec = load_persona_spec("practitioner")
        assert len(spec) > 100

    def test_loads_all_agents(self):
        for key in AGENT_CONFIG:
            spec = load_persona_spec(key)
            assert isinstance(spec, str)
            assert len(spec) > 50


class TestBuildSystemPrompt:
    def test_contains_persona_spec(self):
        prompt = build_system_prompt("practitioner")
        assert "페르소나 명세서" in prompt

    def test_contains_boundary_rules(self):
        prompt = build_system_prompt("practitioner")
        assert "영역 경계" in prompt or "자기 영역만" in prompt

    def test_contains_korean_instruction(self):
        prompt = build_system_prompt("redteam")
        assert "한국어" in prompt
