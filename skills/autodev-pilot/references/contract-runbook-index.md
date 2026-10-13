# 合同运行手册拆分索引

`contract-runbook-history.md` 是合同项目多轮实战手册的完整归档，保留 100% 原文，供追溯历史决策和合同专属配方。为避免其他模块复制 NCM/合同事实，当前执行时按下面的边界读取。

## 已提取到公共规则

以下内容的跨模块部分已归入公共文件，后续以公共文件为执行基线：

| 历史手册主题 | 公共承载 | 仍需回到模块资料确认的内容 |
| --- | --- | --- |
| 空轮早退、取单、锁单、红黄绿 | `common-automation.md` | 当前模块 JIRA 项目、过滤器、状态和锁实现 |
| TDD、真实红灯、夹具陷阱、基线失败 | `common-automation.md`、`common-operational-notes.md` | 当前模块真实入口、DTO、数据库和测试命令 |
| 唤醒、变更水位线、事件去重、自激防护 | `common-operational-notes.md` | NCM 的字段/状态/过滤器和实测记录仍只在本合同历史中有效 |
| 证据、脱敏、Code Review、安全边界 | `common-automation.md`、`common-operational-notes.md` | 当前模块的人工验收和额外门禁 |
| Git、分支、commit、push、PR、JIRA 回写 | `common-automation.md` | 当前仓库远端、基线分支和权限配置 |
| 环境阻断与返工接管 | `common-operational-notes.md` | 当前机器工具链、构建绕行和既有失败 |

## 保留为合同个性

以下主题不得抽到公共规则，也不得直接迁移到仓储或其他模块：

- NCM 工作流状态映射、NCM 项目/过滤器/标签/字段和 NCM 唤醒实测记录；
- Gitea 合同远端、合同仓库分支和合同前后端仓间关系；
- 合同前端 `micro_contract_management` 的代码地图、按钮/参数配方和跨仓 DTO 规则；
- 合同模板、变更/续签、收款计划、久其、动态字段 `dynamicMap`、合同调整/减免、终止删除应收等业务配方；
- 合同 SQL 表、存储过程、迁移脚本、已知缺陷先例和本机合同环境绕行；
- 低开资料中的 NCM-4025 案例数据。低开平台的通用排查方法已放入公共 `README.md` 与 `lowcode-*.md`，但案例事实仍须按当前模块重新验证。

## 执行顺序

1. 先读公共 `common-automation.md` 与需要的 `common-operational-notes.md`。
2. 涉及低开时读 `common-domain.md`、`README.md` 和对应 `lowcode-*.md`。
3. 再按工单类型读取本索引标记的合同专属章节；对 `contract-runbook-history.md` 中的公共旧描述，以公共文件为准。
4. 若公共规则与合同专属规则冲突，采用更严格规则，并在证据中记录冲突和采用原因。
