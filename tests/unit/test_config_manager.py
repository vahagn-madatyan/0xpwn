"""Unit tests for oxpwn.config — model, YAML persistence, env-override resolution."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
import yaml

from oxpwn.config import ConfigManager, OxpwnConfig
from oxpwn.config.manager import resolve_config


# ---------------------------------------------------------------------------
# OxpwnConfig model
# ---------------------------------------------------------------------------


class TestOxpwnConfig:
    """OxpwnConfig Pydantic model behaviour."""

    def test_defaults(self):
        cfg = OxpwnConfig()
        assert cfg.model is None
        assert cfg.api_key is None
        assert cfg.base_url is None
        assert cfg.schema_version == 1

    def test_construction_with_values(self):
        cfg = OxpwnConfig(
            model="ollama/llama3.1",
            api_key="sk-test-key",
            base_url="http://localhost:11434",
        )
        assert cfg.model == "ollama/llama3.1"
        assert cfg.api_key == "sk-test-key"
        assert cfg.base_url == "http://localhost:11434"

    def test_extra_fields_ignored(self):
        """Forward-compat: unknown fields don't crash the model."""
        cfg = OxpwnConfig.model_validate(
            {
                "model": "gemini/gemini-2.5-flash",
                "api_key": "sk-123",
                "future_field": "should be ignored",
                "another_extra": 42,
            }
        )
        assert cfg.model == "gemini/gemini-2.5-flash"
        assert not hasattr(cfg, "future_field")

    def test_schema_version_preserved(self):
        cfg = OxpwnConfig(schema_version=2)
        assert cfg.schema_version == 2

    def test_model_dump_roundtrip(self):
        cfg = OxpwnConfig(model="test/model", api_key=None, base_url=None)
        data = cfg.model_dump()
        restored = OxpwnConfig.model_validate(data)
        assert restored == cfg


# ---------------------------------------------------------------------------
# ConfigManager — path resolution
# ---------------------------------------------------------------------------


class TestConfigManagerPaths:
    """ConfigManager.get_config_path() XDG + env resolution."""

    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("OXPWN_CONFIG", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        mgr = ConfigManager()
        expected = Path.home() / ".config" / "oxpwn" / "config.yaml"
        assert mgr.get_config_path() == expected

    def test_xdg_config_home(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OXPWN_CONFIG", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        mgr = ConfigManager()
        assert mgr.get_config_path() == tmp_path / "xdg" / "oxpwn" / "config.yaml"

    def test_oxpwn_config_env_overrides_all(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom" / "my-config.yaml"
        monkeypatch.setenv("OXPWN_CONFIG", str(custom))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        mgr = ConfigManager()
        assert mgr.get_config_path() == custom


# ---------------------------------------------------------------------------
# ConfigManager — load / save / delete / exists
# ---------------------------------------------------------------------------


class TestConfigManagerPersistence:
    """YAML round-trip, atomic writes, delete, exists."""

    @pytest.fixture(autouse=True)
    def _isolate_config(self, monkeypatch, tmp_path):
        """Point config at a temp directory for every test."""
        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()
        self.config_file = self.config_dir / "config.yaml"
        monkeypatch.setenv("OXPWN_CONFIG", str(self.config_file))

    def test_load_missing_file_returns_defaults(self):
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg == OxpwnConfig()

    def test_save_then_load_roundtrip(self):
        mgr = ConfigManager()
        original = OxpwnConfig(
            model="ollama/llama3.1",
            api_key="sk-secret",
            base_url="http://localhost:11434",
        )
        mgr.save(original)
        loaded = mgr.load()
        assert loaded == original

    def test_roundtrip_preserves_none_values(self):
        mgr = ConfigManager()
        original = OxpwnConfig(model="test/model", api_key=None, base_url=None)
        mgr.save(original)
        loaded = mgr.load()
        assert loaded.api_key is None
        assert loaded.base_url is None

    def test_save_creates_parent_dirs(self, monkeypatch, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "config.yaml"
        monkeypatch.setenv("OXPWN_CONFIG", str(deep_path))
        mgr = ConfigManager()
        mgr.save(OxpwnConfig(model="test"))
        assert deep_path.exists()

    def test_atomic_write_permissions(self):
        mgr = ConfigManager()
        mgr.save(OxpwnConfig(model="test"))
        mode = stat.S_IMODE(self.config_file.stat().st_mode)
        assert mode == 0o600

    def test_no_tmp_file_left_behind(self):
        mgr = ConfigManager()
        mgr.save(OxpwnConfig(model="test"))
        tmp_file = self.config_file.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_exists_false_when_missing(self):
        mgr = ConfigManager()
        assert mgr.exists() is False

    def test_exists_true_after_save(self):
        mgr = ConfigManager()
        mgr.save(OxpwnConfig())
        assert mgr.exists() is True

    def test_delete_removes_config(self):
        mgr = ConfigManager()
        mgr.save(OxpwnConfig(model="test"))
        assert mgr.exists() is True
        mgr.delete()
        assert mgr.exists() is False

    def test_delete_noop_when_missing(self):
        mgr = ConfigManager()
        mgr.delete()  # should not raise

    def test_load_with_extra_fields_in_yaml(self):
        """Config written by a newer version with unknown keys loads cleanly."""
        data = {
            "model": "gemini/gemini-2.5-flash",
            "api_key": "sk-future",
            "base_url": None,
            "schema_version": 2,
            "new_feature_flag": True,
            "nested": {"deep": "value"},
        }
        self.config_file.write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg.model == "gemini/gemini-2.5-flash"
        assert cfg.schema_version == 2

    def test_load_corrupt_yaml_returns_defaults(self):
        self.config_file.write_text("{{invalid yaml: [", encoding="utf-8")
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg == OxpwnConfig()

    def test_load_yaml_scalar_returns_defaults(self):
        """A YAML file containing just a string/number should not crash."""
        self.config_file.write_text("just a string\n", encoding="utf-8")
        mgr = ConfigManager()
        cfg = mgr.load()
        assert cfg == OxpwnConfig()


# ---------------------------------------------------------------------------
# resolve_config — precedence: CLI > env > YAML
# ---------------------------------------------------------------------------


class TestResolveConfig:
    """resolve_config() merges sources with correct precedence."""

    def test_yaml_only(self):
        yaml_cfg = OxpwnConfig(
            model="ollama/llama3.1", api_key="yaml-key", base_url="http://yaml"
        )
        result = resolve_config(env={}, yaml_config=yaml_cfg)
        assert result["model"] == "ollama/llama3.1"
        assert result["api_key"] == "yaml-key"
        assert result["base_url"] == "http://yaml"

    def test_env_beats_yaml(self):
        yaml_cfg = OxpwnConfig(model="yaml-model", api_key="yaml-key")
        result = resolve_config(
            env={"OXPWN_MODEL": "env-model", "OXPWN_API_KEY": "env-key"},
            yaml_config=yaml_cfg,
        )
        assert result["model"] == "env-model"
        assert result["api_key"] == "env-key"

    def test_cli_beats_env_beats_yaml(self):
        yaml_cfg = OxpwnConfig(model="yaml", api_key="yaml-key", base_url="yaml-url")
        result = resolve_config(
            cli_model="cli-model",
            cli_api_key="cli-key",
            cli_base_url="cli-url",
            env={
                "OXPWN_MODEL": "env-model",
                "OXPWN_API_KEY": "env-key",
                "OXPWN_LLM_BASE_URL": "env-url",
            },
            yaml_config=yaml_cfg,
        )
        assert result["model"] == "cli-model"
        assert result["api_key"] == "cli-key"
        assert result["base_url"] == "cli-url"

    def test_partial_override(self):
        """CLI overrides model, env overrides api_key, YAML provides base_url."""
        yaml_cfg = OxpwnConfig(
            model="yaml-model", api_key="yaml-key", base_url="yaml-url"
        )
        result = resolve_config(
            cli_model="cli-model",
            env={"OXPWN_API_KEY": "env-key"},
            yaml_config=yaml_cfg,
        )
        assert result["model"] == "cli-model"
        assert result["api_key"] == "env-key"
        assert result["base_url"] == "yaml-url"

    def test_all_none_when_nothing_provided(self):
        result = resolve_config(env={}, yaml_config=OxpwnConfig())
        assert result["model"] is None
        assert result["api_key"] is None
        assert result["base_url"] is None

    def test_env_defaults_to_os_environ(self, monkeypatch):
        monkeypatch.setenv("OXPWN_MODEL", "from-real-env")
        monkeypatch.delenv("OXPWN_API_KEY", raising=False)
        monkeypatch.delenv("OXPWN_LLM_BASE_URL", raising=False)
        result = resolve_config(yaml_config=OxpwnConfig())
        assert result["model"] == "from-real-env"
