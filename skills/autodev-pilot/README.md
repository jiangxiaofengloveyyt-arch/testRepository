# autodev-pilot 部署与配置说明

本技能包用于把 JIRA 来源的简单开发任务交给 WorkBuddy/AI 按统一流程执行。Bug 修复只是其中一种任务类型；边界行为、校验提示、兼容性修正和已冻结规格内的小范围调整也可以使用。

本 README 面向两类人：

- **人工/管理员**：把技能包迁移到新项目或新机器时，负责填写项目身份、JIRA 工作流、本机路径和权限。
- **AI/WorkBuddy**：每轮执行前负责读取配置、验证环境、发现缺失项并停止在安全边界内；不得猜测配置。

## 一、配置分层

配置按“公共默认值 → 项目身份 → 本机覆盖”合并，后层覆盖前层：

| 文件 | 是否提交 | 修改人 | 放什么 |
| --- | --- | --- | --- |
| `config/config.example.toml` | 是 | 技能维护者 | 所有仓库共用的配置骨架、默认路径名、风险安全开关 |
| `config/module.toml` | 是 | 项目维护者 | 模块 ID、显示名、JIRA Project/过滤器/标签/状态、模块级工作流差异 |
| `config/config.local.example.toml` | 是 | 技能维护者 | 新机器需要填写的本机配置模板 |
| `config/config.local.toml` | 否，必须加入 Git 忽略 | 机器管理员 | 后端/前端仓库路径、自动化工作区、JDK/Maven/Python、证据目录等本机值 |

不要把密码、Token、Cookie、连接串或真实客户数据写进任何示例和跟踪文件。JIRA/代码托管凭据使用 WorkBuddy 连接器或机器凭据管理器提供。

## 二、迁移到其他项目时人工必须修改

### 1. 复制技能包和确认仓库

将整个 `.agents/skills/autodev-pilot/` 复制到目标 Git 仓库，保留公共的 `SKILL.md`、`references/common-*`、`templates/` 和 `scripts/`。不要为新项目复制出另一份 JIRA 定时提示词；提示词应保持公共版本。

确认目标项目的后端仓库是 Git 仓库，并决定是否配置前端仓库。`paths.backend_repo = "auto"` 只适用于 Skill 位于目标后端仓库内；Skill 放在独立目录时必须填写绝对路径或环境变量。

### 2. 修改 `config/module.toml`

至少填写以下项目个性：

```toml
[module]
id = "<小写模块标识>"
display_name = "<模块名称>"
domain_reference = "references/domain.md"

[jira]
project = "<JIRA Project Key>"
filter_id = 0                 # 没有固定过滤器时填 0
required_label = "AI自动开发"
issue_types = []              # 空数组表示不按 Issue Type 限制

[jira.workflow]
candidate_statuses = ["<进入 AI 队列的状态>"]
running_status = "<AI 执行中状态>"
yellow_status = "<待补充/黄灯状态>"
ready_status = "<AI 待验收状态>"
red_status = "<转人工/红灯状态>"
failed_status = "<执行失败状态>"
```

状态名称必须使用目标 JIRA 的真实显示值，不能使用示例值。没有确认状态时保持为空，AI 会停止取单并报告配置阻断。

如果项目不是 `master` 基线或远端不是 `origin`，在公共配置或模块配置中覆盖：

```toml
[repositories.backend]
base_branch = "<实际基线分支>"
branch_prefix = "ai/"
remote = "origin"
```

### 3. 修改 `references/domain.md`

这里放不能抽象成 TOML 的模块知识：

- 后端、前端代码地图和模块边界；
- 实际测试、构建、静态检查和真实链路入口；
- 模块专属红黄灯风险，例如金额、库存、合同、权限、租户隔离或消息；
- 人工验收重点、已知基线失败和特殊回退方式；
- 业务配方、SQL/接口约束和领域专属历史。

不要把这些规则硬编码到公共 `JIRA定时任务提示词.md` 中。

## 三、迁移到新机器时人工必须修改

1. 将 `config/config.local.example.toml` 复制为同目录的 `config/config.local.toml`。不要改文件名，后者必须被 Git 忽略。
2. 填写机器实际值：

```toml
[paths]
backend_repo = "<后端仓库绝对路径>"
frontend_repo = "<前端仓库绝对路径；无前端则留空>"
automation_workspace = "<已存在且专用于自动化的工作区>"
python = "<python 或绝对路径>"
java = "<java 绝对路径；不需要则留空>"
maven_home = "<Maven 目录；不需要则留空>"
maven_local_repository = "<Maven 本地仓库；不需要则留空>"
git_usr_bin = "<Git usr/bin 目录；不需要则留空>"
```

3. 确认 `automation_workspace` 已存在，并允许 AI 在其中创建配置中的 `backend_worktree`、`frontend_worktree`、`evidence` 和 `state` 子路径。工作区不要放人工未提交修改。
4. 确认 WorkBuddy 已授权 JIRA 查询/评论/状态回写，以及代码托管的 push/PR 能力。授权不包含合并、部署或生产写入。

如果使用环境变量覆盖，可以设置：

- `AUTODEV_PILOT_CONFIG`：指定另一份本机 TOML；
- `AUTODEV_PILOT_REPO_ROOT`：在 `backend_repo = "auto"` 时指定仓库根目录。

## 四、AI 每次执行前必须做

在目标仓库根目录运行：

```powershell
python .agents/skills/autodev-pilot/scripts/config_loader.py validate
python .agents/skills/autodev-pilot/scripts/config_loader.py resolve
```

Windows 没有 `python` 命令时，可使用目标机已配置的 Python 启动方式，例如 `py -3`。AI 必须：

1. 先读取 `resolve` 的脱敏 JSON，不使用记忆中的路径、Project、状态或分支；
2. 检查 `module.id`、`jira.project`、`jira.workflow.*`、后端仓库、自动化工作区和工具路径；
3. 配置或路径缺失时停止，不取单、不创建 worktree、不改代码；
4. 读取 `SKILL.md`、`references/common-automation.md`、`references/domain.md`，涉及低开或公共运行细则时再读相应公共参考；
5. 只在配置值和 JIRA 实际响应一致时执行后续流程。

`validate` 通过只代表路径和工具可用，不代表工单适合自动化；入口风险仍需按公共规则和模块 `domain.md` 判定。

## 五、部署后的验收顺序

人工第一次部署新项目/新机器时，按以下顺序验收：

1. `config.local.toml` 未被 Git 跟踪，且没有凭据明文；
2. `config_loader.py validate` 通过；
3. `resolve` 输出的路径、JIRA Project、状态和基线分支与实际一致；
4. 空轮查询不会创建 worktree 或修改文件；
5. 一张可安全回滚的简单工单能正确进入绿色、黄色或红色路由；
6. 绿色任务能留下红灯/绿灯、Code Review、真实链路和人工验收证据；
7. push/PR/JIRA 回写失败时会如实停在失败状态；
8. AI 不会合并 PR、删除分支、部署或操作生产/共享环境。

## 六、哪些文件通常不应修改

- `SKILL.md`：公共入口，除非所有模块的加载顺序或安全边界都要变化；
- `templates/JIRA定时任务提示词.md`：公共流程，两边应保持一致；
- `references/common-automation.md`、`references/common-operational-notes.md`：公共运行规则，不能加入单一模块事实；
- `config/config.example.toml`：公共配置骨架，不写机器路径和项目私有值。

如果新项目确实需要更严格的业务规则，优先修改它自己的 `module.toml`、`config.local.toml` 或 `references/domain.md`，并在交付证据中说明原因。
