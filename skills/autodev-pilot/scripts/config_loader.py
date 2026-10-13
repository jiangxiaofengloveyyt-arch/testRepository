#!/usr/bin/env python3
"""Load and validate the shared autodev-pilot configuration layers.

The loader uses only the Python standard library. It never reads or prints
credentials. Shared defaults live in config.example.toml; tracked repository
identity lives in module.toml; machine-specific paths live in the ignored
config.local.toml or a file selected through AUTODEV_PILOT_CONFIG / --config.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = SKILL_DIR / "config" / "config.example.toml"
MODULE_CONFIG = SKILL_DIR / "config" / "module.toml"
LOCAL_CONFIG = SKILL_DIR / "config" / "config.local.toml"
ENV_CONFIG = "AUTODEV_PILOT_CONFIG"
ENV_REPO_ROOT = "AUTODEV_PILOT_REPO_ROOT"
ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(RuntimeError):
    pass


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"配置文件不存在: {path}")
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("version") != 1:
        raise ConfigError(f"不支持的配置版本: {data.get('version')!r} ({path})")
    return data


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _expand_env(value: str, field: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        resolved = os.environ.get(name)
        if resolved is None:
            raise ConfigError(f"{field} 依赖未设置的环境变量 {name}")
        return resolved

    return ENV_PATTERN.sub(replace, value)


def _path(value: str, base: Path, field: str) -> Path | None:
    if not value:
        return None
    expanded = _expand_env(value, field)
    candidate = Path(expanded).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve(strict=False)


def _resolve_command(value: str, field: str) -> str | None:
    if not value:
        return None
    expanded = _expand_env(value, field)
    candidate = Path(expanded).expanduser()
    if candidate.is_absolute() or candidate.parent != Path("."):
        return str(candidate.resolve(strict=False))
    return shutil.which(expanded) or expanded


def _discover_single(pattern: Path, field: str) -> Path:
    text = str(pattern)
    if not any(char in text for char in "*?["):
        return pattern
    matches = sorted(pattern.parent.glob(pattern.name))
    if len(matches) != 1:
        raise ConfigError(f"{field} 需要唯一匹配，当前匹配 {len(matches)} 个: {pattern}")
    return matches[0].resolve(strict=False)


def _select_override(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser().resolve(strict=False)
    from_env = os.environ.get(ENV_CONFIG)
    if from_env:
        return Path(from_env).expanduser().resolve(strict=False)
    if LOCAL_CONFIG.is_file():
        return LOCAL_CONFIG
    return None


def load_config(explicit: str | None = None) -> dict[str, Any]:
    config = _read_toml(EXAMPLE_CONFIG)
    config = _merge(config, _read_toml(MODULE_CONFIG))
    override = _select_override(explicit)
    if override:
        config = _merge(config, _read_toml(override))

    raw_paths = config.get("paths")
    if not isinstance(raw_paths, dict):
        raise ConfigError("缺少 [paths] 配置")

    repo_value = str(raw_paths.get("backend_repo", "auto"))
    if repo_value == "auto":
        repo_override = os.environ.get(ENV_REPO_ROOT)
        backend_repo = (
            Path(repo_override).expanduser().resolve(strict=False)
            if repo_override
            else SKILL_DIR.parents[2]
        )
    else:
        backend_repo = _path(repo_value, SKILL_DIR, "paths.backend_repo")
        if backend_repo is None:
            raise ConfigError("paths.backend_repo 不能为空")

    workspace = _path(
        str(raw_paths.get("automation_workspace", "")),
        SKILL_DIR,
        "paths.automation_workspace",
    )
    if workspace is None:
        raise ConfigError("paths.automation_workspace 不能为空")

    resolved_paths: dict[str, str | None] = {
        "backend_repo": str(backend_repo),
        "automation_workspace": str(workspace),
        "templates": str(
            _discover_single(
                _path(str(raw_paths.get("templates", "")), SKILL_DIR, "paths.templates")
                or SKILL_DIR,
                "paths.templates",
            )
        ),
        "specs": str(
            _path(str(raw_paths.get("specs", "specs")), backend_repo, "paths.specs")
        ),
        "backend_worktree": str(
            _path(
                str(raw_paths.get("backend_worktree", "wt-pilot")),
                workspace,
                "paths.backend_worktree",
            )
        ),
        "frontend_worktree": str(
            _path(
                str(raw_paths.get("frontend_worktree", "wt-frontend")),
                workspace,
                "paths.frontend_worktree",
            )
        ),
        "evidence": str(
            _path(str(raw_paths.get("evidence", ".ai-auto-fix/evidence")), workspace, "paths.evidence")
        ),
        "state": str(
            _path(str(raw_paths.get("state", ".ai-auto-fix/state")), workspace, "paths.state")
        ),
        "frontend_repo": (
            str(_path(str(raw_paths.get("frontend_repo", "")), backend_repo, "paths.frontend_repo"))
            if raw_paths.get("frontend_repo")
            else None
        ),
        "python": _resolve_command(str(raw_paths.get("python", "python")), "paths.python"),
        "java": _resolve_command(str(raw_paths.get("java", "")), "paths.java"),
        "maven_home": (
            str(_path(str(raw_paths.get("maven_home", "")), backend_repo, "paths.maven_home"))
            if raw_paths.get("maven_home")
            else None
        ),
        "maven_local_repository": (
            str(
                _path(
                    str(raw_paths.get("maven_local_repository", "")),
                    backend_repo,
                    "paths.maven_local_repository",
                )
            )
            if raw_paths.get("maven_local_repository")
            else None
        ),
        "git_usr_bin": (
            str(_path(str(raw_paths.get("git_usr_bin", "")), backend_repo, "paths.git_usr_bin"))
            if raw_paths.get("git_usr_bin")
            else None
        ),
    }

    config["paths"] = resolved_paths
    config["_meta"] = {
        "skill_dir": str(SKILL_DIR),
        "defaults": str(EXAMPLE_CONFIG),
        "module": str(MODULE_CONFIG),
        "override": str(override) if override else None,
    }
    return config


def _nested_get(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ConfigError(f"配置键不存在: {key}")
        current = current[part]
    return current


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def validate(config: dict[str, Any]) -> list[str]:
    paths = config["paths"]
    errors: list[str] = []

    module = config.get("module")
    if not isinstance(module, dict) or not str(module.get("id", "")).strip():
        errors.append("缺少 module.id")
    if not isinstance(module, dict) or not str(module.get("domain_reference", "")).strip():
        errors.append("缺少 module.domain_reference")
    elif not (SKILL_DIR / str(module["domain_reference"])).is_file():
        errors.append(f"module.domain_reference 不存在: {module['domain_reference']}")

    jira = config.get("jira")
    if not isinstance(jira, dict) or not str(jira.get("project", "")).strip():
        errors.append("缺少 jira.project")
    if isinstance(jira, dict) and not isinstance(jira.get("filter_id"), int):
        errors.append("jira.filter_id 必须为整数；未配置时填 0")
    if not isinstance(jira, dict) or not str(jira.get("required_label", "")).strip():
        errors.append("缺少 jira.required_label")

    backend = Path(paths["backend_repo"])
    workspace = Path(paths["automation_workspace"])
    templates = Path(paths["templates"])
    specs = Path(paths["specs"])

    if not backend.is_dir() or not (backend / ".git").exists():
        errors.append(f"backend_repo 不是 Git 仓库: {backend}")
    if not templates.is_dir():
        errors.append(f"templates 不存在: {templates}")
    if not specs.is_dir():
        errors.append(f"specs 不存在: {specs}")
    if not workspace.is_dir():
        errors.append(f"automation_workspace 不存在: {workspace}")

    for name in ("backend_worktree", "frontend_worktree", "evidence", "state"):
        candidate = Path(paths[name])
        if not _is_within(candidate, workspace):
            errors.append(f"{name} 必须位于 automation_workspace 内: {candidate}")

    frontend = paths.get("frontend_repo")
    if frontend and (not Path(frontend).is_dir() or not (Path(frontend) / ".git").exists()):
        errors.append(f"frontend_repo 不是 Git 仓库: {frontend}")

    for name in ("python", "java"):
        value = paths.get(name)
        if value and not Path(value).is_file() and not shutil.which(value):
            errors.append(f"{name} 不可执行或不存在: {value}")

    for name in ("maven_home", "maven_local_repository", "git_usr_bin"):
        value = paths.get(name)
        if value and not Path(value).is_dir():
            errors.append(f"{name} 不存在: {value}")

    return errors


def main() -> int:
    # Windows 控制台常为 GBK；模板目录可能含 U+200C，统一用 UTF-8 输出。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description="Resolve autodev-pilot configuration")
    parser.add_argument("--config", help="显式配置文件；优先于环境变量和 config.local.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("resolve", help="输出完整脱敏配置 JSON")
    get_parser = subparsers.add_parser("get", help="读取单个配置值")
    get_parser.add_argument("key", help="例如 paths.backend_repo")
    subparsers.add_parser("validate", help="检查路径和工具是否可用")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        if args.command == "resolve":
            print(json.dumps(config, ensure_ascii=False, indent=2))
            return 0
        if args.command == "get":
            value = _nested_get(config, args.key)
            if isinstance(value, (dict, list)):
                print(json.dumps(value, ensure_ascii=False))
            elif value is not None:
                print(value)
            return 0

        errors = validate(config)
        if errors:
            print("CONFIG INVALID")
            for error in errors:
                print(f"- {error}")
            return 2
        print("CONFIG OK")
        print(json.dumps(config["paths"], ensure_ascii=False, indent=2))
        return 0
    except (ConfigError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
