# 公共领域参考入口

本文件列出可跨仓库复用的领域与运行参考。模块 `references/domain.md` 只负责本模块的路由；不要把合同或仓储的路径、JIRA 字段、远端地址和业务配方写入这里。

## 公共运行规则

- [common-automation.md](common-automation.md)：取单、锁单、红黄绿路由、TDD、worktree、基线失败、Code Review、commit → push → PR → JIRA 回写、返工和证据门禁。
- [common-operational-notes.md](common-operational-notes.md)：从多轮实战手册抽取的跨模块运行细则，包括真实红灯、唤醒去重、环境诊断、交付证据和安全边界。

## 公共低开知识

以下低开资料可以供任何采用相同低开平台约定的模块复用。文档中的具体工单号是历史案例，不代表模块归属；读取后仍须回到当前模块的代码地图、配置和数据库核验。

- [README.md](README.md)：低开资料索引和证据编写约定。
- [lowcode-modeling-api.md](lowcode-modeling-api.md)：NLCPD 一次性建模 API、JSON 资源顺序、查重、字典口径、补偿回滚和在线代码执行边界。
- [lowcode-generator.md](lowcode-generator.md)：Generator 预览/下载接口、菜单 `ver`、FreeMarker 模板、增量合并和脚本生成证据。
- [lowcode-dictionary.md](lowcode-dictionary.md)：数据字典、`add_ecmDictionaryItem` 参数顺序和接口核验。
- [lowcode-resourcecolumn.md](lowcode-resourcecolumn.md)：列配置、`keyRefer`、修复 SQL 与幂等性。
- [lowcode-form-design.md](lowcode-form-design.md)：表单设计、`funcinfoId`、`formJson` 和挂点定位。
- [lowcode-case-ncm-4025.md](lowcode-case-ncm-4025.md)：NCM-4025 全链路案例；仅作为历史样例，不能替代目标模块验证。

公共资料的结论必须保留 `file:line` 证据；无法核验时标明【推断】并给出验证路径。模块专属事实放回各自的 `domain.md` 或模块历史手册。
