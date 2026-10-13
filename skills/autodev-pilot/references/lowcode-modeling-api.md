# 低开一次性建模 API（NLCPD）

本文档记录从 `newsee-nlcpd` 源码核验的低开元数据建模入口。它适用于“根据需求生成模块/菜单/表单/列/按钮/树/字典”的任务；只生成 SQL 脚本时，继续读取 [lowcode-generator.md](lowcode-generator.md)。

## 1. HTTP 入口

| 能力 | 接口 | 关键参数 | 用途 |
| --- | --- | --- | --- |
| 一次性建模落库 | `POST /aiModeling/generate` | `multipart/form-data` 字段 `file`，UTF-8 JSON | 按请求落库模块、菜单、表单、列、按钮、树和字典 |
| 编码查重 | `GET /aiModeling/checkCode?type=<type>&code=<code>` | `type`、`code` | 生成 JSON 前做幂等/冲突检查 |
| 下载 skill | `GET /aiModeling/downloadSkill?name=<name>` | 可选 skill 名称 | 获取服务端分发的建模 skill，不是业务脚本生成接口 |

【实测】入口和参数见 `newsee-nlcpd/newsee-nlcpd-rest/src/main/java/com/newsee/nlcpd/controller/AiModelingController.java:79-116`。

### 风险边界

- `/aiModeling/generate` 是真实数据库写操作，不是只读预览；自动化任务默认只能生成并审核 JSON，不能直接上传到生产或共享环境。
- 需求需要真实落库时至少转黄；涉及生产、跨租户、数据库结构或不可逆数据时转红并由人工执行。
- 生成前先保存 JSON、输入摘要、响应结果和脱敏证据；失败时不要盲目重试，先判断是否已经发生 DDL 或部分落库。

## 2. 请求 JSON 结构和依赖顺序

顶层数组字段由 `AiModelingRequestDTO` 定义：`modules`、`menus`、`forms`、`columns`、`buttons`、`trees`、`dictionarys`，见 `newsee-nlcpd/newsee-nlcpd-pojo/src/main/java/com/newsee/nlcpd/dto/AiModelingRequestDTO.java:27-45`。

每类资源通常支持 `op=create|update|merge`；各类定位键和字段不能凭标题猜测，必须按 DTO 注释、现有 service 和目标环境确认。表单至少需要 `formCode`、`formName`、`formMode`、`formContentStr` 等字段，见同文件 `:107-139`。

服务端固定按依赖顺序处理：

1. 字典和字典项；
2. 应用模块；
3. 菜单；
4. 表单（普通表单由 `addForm` 生成基础列和默认按钮）；
5. 列表列和查询条件；
6. 按钮；
7. 树及树表元数据。

【实测】`AiModelingServiceImpl.doGenerate` 位于 `newsee-nlcpd/newsee-nlcpd-rest/src/main/java/com/newsee/nlcpd/service/impl/AiModelingServiceImpl.java:218-261`。树表单存在特殊分支：当 `formCode` 与 `trees[].treeCode` 同名时，表单内容先暂存，树链路再补建物理表和元数据；不能按普通表单重复调用 `addForm`。

## 3. 幂等和查重

生成 JSON 前调用 `checkCode`，当前实现支持：

`funcinfoCode`、`menuMenusubname`、`menuCode`、`treeCode`、`moduleId`、`moduleName`、`dictionaryCode`、`tableName`。

【实测】实现见 `AiModelingServiceImpl.java:1771-1822`。重点规则：

- `menuMenusubname` 是全局菜单英文标题口径；重复时不要只换中文名。
- `dictionaryCode` 会连带平台级字典查重，必须使用功能域前缀避免静默复用别人的字典。
- `tableName` 是物理表名查重；必须确认数据库归属、租户字段和表前缀后再提交。
- `op=update/merge` 不应被失败补偿删除；只有本次明确 `create` 且落库成功的资源才登记为可补偿对象。

## 4. 字典引用口径

一次性建模使用的是平台字典模型：`ns_core_dictionary` + `ns_core_dictionaryitem`，字典分组为 `ns_core_dictionarygroup`。字典编码是平台共享资源，表单下拉通过 `formOptions.dataFrom='数据字典'` 引用。

【实测】DTO 注释见 `AiModelingRequestDTO.java:243-274`；服务落库与查重见 `AiModelingServiceImpl.java:275-337`、`:401-460`。

当前服务实现的注意点：

- `dictionaryCode` 必须先查重；不要把历史 `ns_ecm_dictionary_item` 的 `itemValue/itemCode` 参数顺序套到该模型。
- 服务日志和注释要求表单的 `dataDictionaryValue` 使用已解析的字典主键/jeId 口径，不能只凭字段名写编码；以目标版本 `AiModelingServiceImpl.java:306-323` 和实际 `CoreFormServiceImpl` 读取逻辑复核。
- 字典项的 `itemCode` 是实际存库的编码，`itemName` 是展示名称，服务按编码做 upsert；同一字典内编码应稳定。

## 5. 事务与补偿回滚

服务用 `TransactionTemplate` 包住主流程；但 `addForm` 会执行 `CREATE TABLE`/`ALTER TABLE`，MySQL DDL 会隐式提交，所以普通事务不能保证全量回滚。异常后服务按逆序执行补偿删除，涉及功能、菜单、表单、列、按钮、字典和物理表。

【实测】事务和原因说明见 `AiModelingServiceImpl.java:182-218`、`:1847-1955`。

因此 AI 只能：

1. 在受控环境先做查重和预览；
2. 记录请求中的全部 `create` 编码和目标表；
3. 失败时保留服务响应和补偿日志，不假设“事务已回滚”；
4. 由人工核对元数据、物理表、缓存和租户范围，再决定是否重试或手工清理。

## 6. 在线 Java 代码执行（独立高风险入口）

NLCPD 另有 `POST /code-execute/execute` 和 `GET /code-execute/dependencies`，见 `newsee-nlcpd/newsee-nlcpd-rest/src/main/java/com/newsee/nlcpd/controller/CodeExecuteController.java:30-44`。请求包含 `code`、`codeType`、`timeout`、可选 `databaseName`、`injectContext` 和参数；服务会解密、编译并在超时线程中运行。

源码虽然有危险模式拦截（命令执行、反射、网络、文件删除、DDL/DML 等）和默认 30000ms 超时，见 `CodeExecuteServiceImpl.java:30-105`、`:129-219`，但这不是完整沙箱，也不等同于 dry-run。代码执行可能访问数据库上下文、输出敏感信息或触发远程服务，因此：

- AI 不得把它当作低开脚本执行器，也不得用它验证生产数据；
- 本地诊断必须使用脱敏数据、最小权限、短超时和可审计参数；
- 任何真实 SQL、远程数据库或共享环境调用都转红，由人工在隔离环境执行；
- 记录安全校验结果、编译结果、stdout/stderr 摘要和超时情况，不能记录凭据。
