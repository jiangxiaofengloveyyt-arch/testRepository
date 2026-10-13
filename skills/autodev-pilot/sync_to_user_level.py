#!/usr/bin/env python3
"""Install the shared WorkBuddy dispatcher for repository-local autodev-pilot.

Every repository keeps its authoritative Skill at
`.agents/skills/autodev-pilot/`. The user-level entry must stay generic so
contract, warehouse, and future modules do not overwrite one another.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
USER_SKILL = Path.home() / ".workbuddy" / "skills" / "autodev-pilot" / "SKILL.md"

DISPATCHER = """---
name: autodev-pilot
description: 仓库级 AI 自动开发 Skill 的公共入口。必须从当前代码工作区读取 .agents/skills/autodev-pilot/SKILL.md；本文件不承载领域规则。
agent_created: true
---

# 仓库级 autodev-pilot 公共入口

先确定当前任务的代码工作区根目录；只读取该仓库的
`.agents/skills/autodev-pilot/SKILL.md` 作为权威规则，并继续按其中的
`config/`、`references/`、`templates/` 执行。

不要把其他仓库的业务覆盖、路径配置或 JIRA 工作流带入当前仓库。找不到该
文件时停止并请求提供正确的工作区；不要回退到用户级目录中的旧副本。
"""


def main() -> int:
    if not (SKILL_DIR / "SKILL.md").is_file():
        print(f"ERROR: 仓库内 SKILL.md 不存在: {SKILL_DIR / 'SKILL.md'}")
        return 1
    USER_SKILL.parent.mkdir(parents=True, exist_ok=True)
    temporary = USER_SKILL.with_suffix(".tmp")
    temporary.write_text(DISPATCHER, encoding="utf-8", newline="\n")
    os.replace(temporary, USER_SKILL)
    print(f"synchronized shared dispatcher: {USER_SKILL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
