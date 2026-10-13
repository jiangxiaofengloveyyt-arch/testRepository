# 低开代码与 SQL 脚本生成器（Generator）

本文档记录 `newsee-generator` 的生成接口、模板上下文、版本脚本和安全用法。它描述“预览/生成脚本”的只读与交付边界，不授权 AI 直接执行生成 SQL。

## 1. 生成接口

| 能力 | 接口 | 参数 | 返回/产物 |
| --- | --- | --- | --- |
| 单表单代码下载 | `GET /generator/generatorByFuncinfoId` | `funcinfoId`、可选 `dictFlag` | zip 下载；`dictFlag` 默认 `1` |
| 单表单代码预览 | `GET /generator/previewCode` | `funcinfoId`、可选 `dictFlag` | `Map<文件名, 内容>` |
| 模块/应用批量代码下载 | `GET /generator/generatorBatchCode` | `funcId`、可选 `dictFlag` | zip 下载 |
| 菜单 SQL 预览 | `GET /generator/previewMenuScript` | `menuId`、`type`、`ver` | `Map<文件名, SQL>` |
| 无代码表单 SQL 预览 | `GET /generator/previewNoCode` | `funcId` | `00_Create.sql`、`01_Update_System.sql` 等 SQL 内容 |

【实测】接口定义见 `newsee-generator/src/main/java/com/newsee/generator/controller/GeneratorController.java:24-77`。

建议顺序：先 `previewMenuScript`/`previewNoCode`，保存响应和输入参数，人工审 SQL 后才考虑下载 zip；`generatorByFuncinfoId` 和 `generatorBatchCode` 属于产物生成，不是数据库执行。

## 2. 菜单版本 `ver`

菜单脚本接口的 `type` 用于区分普通菜单与应用菜单，`ver` 用于选择菜单版本。服务会查询各版本的 `ns_core_menu`、`ns_core_module_menu`、`ns_core_module`，组装 `MenuVersionData` 并按版本排序，再交给 `menu_script.sql` 模板渲染。

【实测】版本组装见 `GeneratorServiceImpl.java:286-395`；模型字段见 `GeneratorCodeBaseConfig.java` 的 `menuVersions` 与 `MenuVersionData.java`。

模板已经包含按版本分支的逻辑：根据 `mv.ver`/`page.menuVersions` 设置 `@script_menu_ver`，并在 `ns_core_module`、`ns_core_menu` 等写入时带 `ver` 和 `not exists` 幂等条件；模板入口为 `src/main/resources/template/menu/menu_script.sql`。

生成或改造版本脚本时必须确认：

- `ns_menu_version` 的当前版本由目标环境维护，脚本不能擅自初始化或切换它；
- 目标环境是否已存在 `ver` 列和兼容字段；缺字段的升级脚本属于数据库变更，转人工；
- 每个版本的模块、根菜单、模块菜单关联和页面菜单是否齐全；
- `not exists` 条件是否同时包含业务主键、租户组织和 `ver`，避免跨版本串数据。

## 3. FreeMarker 模板和输出规则

生成器读取 `src/main/resources/template`，以 `GeneratorCodeBaseConfig` 构建 `templateModel` 和 `filePathModel`，通过 `GeneratorEngine` 扫描模板并渲染。模板文件名本身也可能包含 `${className}`、`${subpackage_dir}` 等字面占位符；不要直接调用 FreeMarker 的变量路径替换去猜文件名。

【实测】模板根目录和模型装配见 `GeneratorServiceImpl.java:542-600`、`:628-702`；引擎入口和占位符处理见 `GeneratorEngine.java:35-147`、`:407-529`。

关键约定：

- `.ftl`/`.vm` 等扩展会被移除后写入产物；输出默认 UTF-8；
- 输出文件已存在时，若文件包含 `generator-insert-location`，引擎会把模板片段插入标记位置；否则受 `gg.isOverride()` 控制，默认不覆盖；
- 模板中可用 `gg` 控制 `setIgnoreOutput`、`setOverride`、`generateFile` 等行为；这些能力会产生文件写入，必须在隔离输出目录验证；
- 生成器为了批量代码可能使用线程池和临时目录，失败时需要收集日志、清理临时产物并核对 zip 内容，不以 HTTP 200 alone 判断成功。

## 4. 低开脚本生成的标准工作流

1. 从页面/工单确认 `funcinfoId`、`funcId`/`menuId`、`type`、`ver`、表单模式和目标数据库；缺任何一个关键定位值时转黄。
2. 先调用 NLCPD `checkCode` 核对表单、菜单、模块、字典和物理表编码；再只读调用 Generator 预览接口。
3. 保存原始 JSON/请求参数、预览响应、文件名清单和 SQL 摘要到 evidence；对 SQL 做语法、租户、版本、幂等和库归属审查。
4. 只在隔离目录下载 zip 或保存 SQL 文件；不覆盖目标业务仓库的已有二开文件。
5. 人工确认后，再由人工在正确环境执行脚本；执行前备份、事务/回滚策略、执行后自检和版本水位线必须齐全。
6. 生成器模板发生变更时，至少用一份代表性菜单/表单做真实预览，并检查 zip 顶层 `code/`、包名、Mapper 路径、SQL 文件名和 `generator-insert-location` 合并效果。

## 5. 失败诊断

- `previewNoCode` 报模板变量缺失（例如 `subTablesName`）时，先检查 `GeneratorModelUtils` 的模型完整性和当前表单模式，不要在模板里盲目加默认空列表掩盖数据缺口。
- SQL 文件名出现 URL 编码或字面 `${className}` 时，区分 HTTP 下载名、FreeMarker 文件查找和输出路径处理三层问题。
- 生成 zip 成功但内容缺文件时，检查 `GeneratorEngine` 的 includes/excludes、`@条件表达式`、模板扩展名和 `gg.setIgnoreOutput`。
- 版本脚本缺少某一版本数据时，先查 Generator 查询结果与 `MenuVersionData`，再查目标环境是否已初始化版本列；不能用手工复制 SQL 代替源数据核验。

## 6. 交付证据

至少记录：接口和参数（不含凭据）、源 `funcinfo/menu/ver`、生成器版本/commit、模板目录或 hash、预览响应摘要、产物文件清单、SQL 语法/幂等/租户检查、人工执行人、执行后自检和未覆盖版本。生成器只负责产出，不证明脚本已经在任何环境成功执行。
