"""Config model, YAML persistence, and env-override resolution for 0xpwn."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

_DEFAULT_CONFIG_DIR = ".config/oxpwn"
_CONFIG_FILENAME = "config.yaml"


class OxpwnConfig(BaseModel, extra="ignore"):
    """Persistent user configuration for 0xpwn.

    ``extra="ignore"`` ensures that config files written by a newer version
    (with additional fields) load without error in an older version,
    providing forward-compatibility / schema-migration safety.
    """

    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    schema_version: int = 1


class ConfigManager:
    """YAML-backed config persistence with XDG path resolution.

    Path precedence:
      1. ``OXPWN_CONFIG`` env var (explicit override)
      2. ``$XDG_CONFIG_HOME/oxpwn/config.yaml``
      3. ``~/.config/oxpwn/config.yaml`` (XDG default)
    """

    def get_config_path(self) -> Path:
        """Resolve the config file path following XDG conventions."""
        explicit = os.environ.get("OXPWN_CONFIG")
        if explicit:
            return Path(explicit)

        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home) / "oxpwn" / _CONFIG_FILENAME

        return Path.home() / _DEFAULT_CONFIG_DIR / _CONFIG_FILENAME

    def load(self) -> OxpwnConfig:
        """Load config from YAML, returning empty defaults if file is missing."""
        path = self.get_config_path()
        if not path.exists():
            logger.debug("config.loaded", path=str(path), source="defaults")
            return OxpwnConfig()

        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "config.load_error",
                path=str(path),
                error=str(exc),
            )
            return OxpwnConfig()

        if not isinstance(data, dict):
            logger.debug("config.loaded", path=str(path), source="defaults")
            return OxpwnConfig()

        config = OxpwnConfig.model_validate(data)
        logger.debug("config.loaded", path=str(path), source="file")
        return config

    def save(self, config: OxpwnConfig) -> Path:
        """Atomically write config to YAML with restrictive permissions.

        Writes to a ``.tmp`` sibling first, then uses ``os.replace`` for an
        atomic rename.  The resulting file has ``0o600`` permissions so that
        API keys are not world-readable.

        Returns the final config file path.
        """
        path = self.get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = path.with_suffix(".tmp")
        data = config.model_dump(mode="python")
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)

        tmp_path.write_text(yaml_str, encoding="utf-8")
        os.replace(tmp_path, path)
        os.chmod(path, 0o600)

        logger.debug("config.written", path=str(path))
        return path

    def delete(self) -> None:
        """Remove the config file if it exists."""
        path = self.get_config_path()
        if path.exists():
            path.unlink()
            logger.debug("config.deleted", path=str(path))

    def exists(self) -> bool:
        """Return ``True`` if the config file exists on disk."""
        return self.get_config_path().exists()


def resolve_config(
    *,
    cli_model: str | None = None,
    cli_api_key: str | None = None,
    cli_base_url: str | None = None,
    env: dict[str, str] | None = None,
    yaml_config: OxpwnConfig | None = None,
) -> dict[str, Any]:
    """Merge configuration sources with precedence: CLI > env > YAML.

    Parameters
    ----------
    cli_model, cli_api_key, cli_base_url:
        Values passed directly on the command line (highest priority).
    env:
        Environment variable mapping.  If *None*, reads from ``os.environ``.
    yaml_config:
        Parsed YAML config.  If *None*, uses an empty default.

    Returns
    -------
    dict with keys ``model``, ``api_key``, ``base_url`` — any may be *None*
    if no source provided a value.
    """
    if env is None:
        env = dict(os.environ)
    if yaml_config is None:
        yaml_config = OxpwnConfig()

    def _first(*values: str | None) -> str | None:
        for v in values:
            if v is not None:
                return v
        return None

    return {
        "model": _first(cli_model, env.get("OXPWN_MODEL"), yaml_config.model),
        "api_key": _first(cli_api_key, env.get("OXPWN_API_KEY"), yaml_config.api_key),
        "base_url": _first(cli_base_url, env.get("OXPWN_LLM_BASE_URL"), yaml_config.base_url),
    }
