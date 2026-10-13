# 合同领域覆盖入口

本仓库的多轮实战运行手册完整保存在 [contract-runbook-history.md](contract-runbook-history.md)，内容未删减；[contract-runbook-index.md](contract-runbook-index.md) 标出了已抽取的公共主题与必须保留的合同个性。合同、动态字段、合同调整/终止、SQL、前端、NCM 唤醒、构建阻断或已知缺陷配方相关任务，必须按任务类型读取该手册中的对应章节。

低开专题知识在公共入口 [common-domain.md](common-domain.md)、[README.md](README.md) 及其 `lowcode-*.md` 文件中。低开结构和排查方法可以跨模块复用；其中 NCM-4025、合同路径和数据值是历史案例，迁移到其他模块前必须重新核验。

当历史手册记载的是合同专属环境、JIRA 字段、远端、构建绕行或业务配方时，仅对本合同仓库生效。取单、TDD、Code Review、PR 与证据等公共行为以 `common-automation.md` 和 `common-operational-notes.md` 为准；冲突时采用更严格规则。
