---
name: autodev-pilot
description: 在当前仓库按 JIRA 工单执行可审计的 AI 自动开发：风险路由、TDD、代码审查、commit、push、PR、JIRA 回写与人工验收；不用于合并、部署或生产写操作。
---

# Repository AI Autodev Pilot

本文件是所有仓库 `autodev-pilot` 的**完全一致公共入口**。它只定义共同的加载顺序和交付边界；业务规则、代码地图、环境事实和实战配方只存在于当前仓库的 `references/domain.md` 及其引用资料。不得将其他仓库的路径、JIRA 字段、远端地址或业务规则带入本轮。

## 运行配置

任何非只读动作前，在当前仓库根目录运行：

```powershell
python .agents/skills/autodev-pilot/scripts/config_loader.py validate
python .agents/skills/autodev-pilot/scripts/config_loader.py resolve
```

只使用解析输出中的 `${paths.*}`；预检失败则停止，不创建猜测目录、不改代码、不取单。共享默认值在 `config/config.example.toml`，仓库身份与 JIRA 差异在 `config/module.toml`；部署新电脑时先将 `config/config.local.example.toml` 复制为被忽略的 `config/config.local.toml`，再填写本机值。

新项目或新机器的人工/AI 配置清单见 [部署与配置说明](README.md)。

## 必读顺序

1. 当前仓库及目标目录最近的 `AGENTS.md`。
2. [公共自动化运行手册](references/common-automation.md)：取单、锁单、灯色、TDD、worktree、基线失败、评审、commit → push → PR → JIRA 回写、返工与证据的唯一公共基线。
3. [公共领域参考](references/common-domain.md)：当任务涉及低开平台或公共运行细则时，继续读取其中链接的资料。
4. [当前仓库领域覆盖](references/domain.md)：必须加载其路由到的业务规则、实际构建/测试入口、环境限制和专属经验。
5. `templates/README.md` 及本工单需要的 `intent.md`、`spec.md`、`plan.md`、`tasks.md`、`code-review.md`、人工验收清单和 JIRA 定时提示词。

将模板复制到 `${paths.specs}/<JIRA_KEY>/` 后再填写；原模板不改。

## 不可突破的交付边界

公共运行手册的绿色门禁通过后，标准终点是：候选 commit、push `ai/<JIRA_KEY>`、创建或更新以配置基线为目标的 PR，以及 JIRA 交付评论。远端/PR/JIRA 能力不可用时如实报告阻断，不得伪造成功。

无论何种业务，AI 都不得合并 PR、向基线直接推送、删除任务分支、部署、触发发布、操作生产/共享环境、写入凭据或绕过人工 Code Review/验收。领域覆盖可加严，不能放宽。

## 最小交付包

交付报告必须包括：JIRA Key、风险路由、实际修改文件、实际验证命令和结果、红绿/TDD 证据、Code Review 结论、commit/分支/PR/JIRA 回写结果、人工验收步骤、未执行项和剩余风险。
