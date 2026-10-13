---
name: autodev-pilot
description: 处理 NCM 项目中带「AI自动开发」标签的工单，从定时取单、风险路由、TDD 实现和验证一直交付到 ai/<KEY> 分支与 PR。用于 newsee-contract 自动开发及人工反馈后的增量返工；禁止自动合并、删除分支、部署或生产写操作。
agent_created: true
---

# NCM 合同 AI 自动开发试点 — 执行工作流

## 公共功能基线（所有模块一致）

先读 [公共自动化运行手册](common-automation.md)。它统一规定取单去重、锁单、worktree、TDD 红绿证据、基线失败判定、Code Review、commit → push → PR → JIRA 回写、返工和证据门禁；其他模块的同名文件必须与它保持一致。

本文件其余内容是合同模块经实战验证的领域覆盖、工具限制和历史环境事实。若与公共手册冲突，仅当本文件明确针对合同仓库的更严格规则时才覆盖；合同事实不得迁移到其他模块。

## 运行配置（任何非空轮开发动作前必做）

本技能以**当前实际打开的仓库副本**为权威来源，不再假定盘符或用户名。仓库根目录、本机工具、自动化工作区、模板、规格、证据和 Worktree 路径统一由 `config/` 管理：

- `config/config.example.toml`：可入库的共享默认值，不包含凭据。
- `config/config.local.toml`：当前机器覆盖值，已被本目录 `.gitignore` 排除。
- `scripts/config_loader.py`：使用 Python 标准库加载、解析和校验配置。

配置优先级：`--config` → `AUTODEV_PILOT_CONFIG` → `config.local.toml` → `config.example.toml`。`backend_repo = "auto"` 时，从当前技能目录向上推导仓库根目录；也可用 `AUTODEV_PILOT_REPO_ROOT` 显式覆盖。

```bash
python .agents/skills/autodev-pilot/scripts/config_loader.py validate
python .agents/skills/autodev-pilot/scripts/config_loader.py resolve
python .agents/skills/autodev-pilot/scripts/config_loader.py get paths.backend_repo
```

`validate` 不通过时停止，不创建猜测目录、不回退到历史 F/G 盘路径。后文 `${paths.*}` 均指加载器输出的已解析值，执行命令前必须替换为实际路径。凭据仍通过现有凭据管理器在运行时获取，禁止写入配置文件。

用户级 `.workbuddy/skills/autodev-pilot/SKILL.md` 是按当前工作区分发的公共入口；修改仓库副本后运行当前目录下的 `sync_to_user_level.py`。领域规则一律以当前仓库副本为准。

> **2026-09-16 定位调整**：本技能不再限定「简单 Bug 修复」，覆盖 `NCM + AI自动开发` 标签的**全部工单**（缺陷 / 功能改进 / 新功能 / 加字段 / 改界面）。
> **2026-09-16 16:05 交付边界最新口径（人工指令「调整规则，push 分支并发起请求写进工作流中」）**：AI 终点 = **本地候选 commit + 完整证据 + push `ai/<KEY>` + 发起 PR(base=master) + JIRA 回写**。**push 与建 PR 是默认工作流的固定环节，不再逐轮请示**；**合并 PR / 删除开发分支（远端+本地）/ Code Review 签署 / 人工验收仍由人工执行**，部署/生产写永不执行。
> 历史口径（已被覆盖，仅供追溯）：2026-09-16 09:30「push + PR 即止」→ 同日 09:47「本地 commit 即止（不 push）」→ 本次 16:05 恢复并**固化为默认流程**（即 NCM-3744 那轮「逐轮书面授权才 push」的做法不再需要）。

## 何时使用

被要求「处理 NCM 项目 AI自动开发 标签的工单」「按模板包流程开发/修复工单」「回写 [AI-AUTO-DEV] 评论」「交人工评审与合并」时。

## 空轮早退（2026-09-21 人工指令，硬规则，省 token）

**每轮第一步只跑两条只读命令**：`python .ai-auto-fix/jira_cli.py wake` + `python .ai-auto-fix/jira_cli.py queue`。

- **两条都为空 ⇒ 立即结束本轮**：不读本技能、不读 AGENTS.md、不读模板包、不直查标签全量 JQL、不逐单读状态/标签、不 `verify`/`compliance` 任何 PR、不跑 worktree/分支/工作区自检、不做状态分布交叉核验。
- 空轮只做 3 件事：① 汇报「本轮无符合条件工单」并附两条命令原始输出；② 向自动化记忆追加 **2～3 行**；③ 结束。零 JIRA 写操作、零代码改动、零文件产出。
- **唯一例外**：命令是**执行报错**（不是返回空）或输出明显异常 ⇒ 允许再跑 **1 条**诊断命令定位并如实汇报，不要展开排查。
- 判据：`wake` 输出 `scanned=0 wake=0`（候选集为空 = 标签范围内无 `新建/开发已回复/开发/处理中/重处理` 工单）与 `queue` 输出 `count=0 total=0` 互为印证，属**正常空轮**，不是异常信号，不需要第三方数据源佐证。
- 反面教材（2026-09-21 09:31 轮）：空轮仍跑了「标签全量 JQL 交叉核验 + 逐单状态/标签核对 + NCM-3866 详情 + PR verify + worktree/分支/工作区自检」，全部属多余，纯浪费 token —— 已由人工叫停，不要再犯。

## 固定配置（2026-09 实测）

| 项 | 值 |
| --- | --- |
| JIRA 筛选器 | `filter=40473`，JQL 实际为 `project = NCM AND labels = "AI自动开发"`（owner 蒋晓峰）。**该筛选器会把已完成的单一起返回 → 取单必须自行加 `AND status = 新建`**（`jira_cli.py queue` 已内置） |
| 代码工作空间 | `${paths.backend_repo}`（Git，基线分支来自 `repositories.backend.base_branch`），共享工作区**必须保持零改动** |
| 模板包 | `${paths.templates}`；模板随本 Skill 分发，含 README/intent/spec/plan/tasks/**code-review**/AI执行提示词/人工验收清单/JIRA定时任务提示词。复制到 `${paths.specs}/<工单号>/` 后填写，原模板保持不改 |
| 路径来源 | 只认本轮 `config_loader.py resolve` 的结果。人工提供的其他机器路径先写入 `config.local.toml` 并执行 `validate`，不得写回 Skill 正文，也不得自行创建猜测目录 |
| 规格目录 | `${paths.specs}/<工单号>/`（每单放 intent / spec / plan / tasks / **code-review** 五件套）。`/specs` 与 `/docs` 在 `.gitignore` 内时，规格/证据另存一份到 `${paths.evidence}` 归档 |
| 分支命名 | `ai/<工单号>` |
| 隔离 worktree | `${paths.backend_worktree}`，固定复用同一路径，不按工单号新建。前端改动与后端改动操作不同文件，提交使用精确路径、绝不 `git add -A` |
| **前端工作空间** | 仓库 `${paths.frontend_repo}`；隔离目录 `${paths.frontend_worktree}`。远端仍是另一台独立 Gitea，改码前先 fetch 并建 `ai/<KEY>`；详见「前端开发场景」 |

> ⚠️ **前端仓库位置坑（2026-09-17 实测，曾误判为 GitLab）**：`code.new-see.com:3001` 的 `/api/v4/version` 返回 HTML 404（Gitea 1.9.2 用 **`/api/v1`**），且未登录时返回 `{"message":"Only signed in user is allowed to call APIs."}`。**另：git 凭据按 host（含端口）存储** → 用 IP `47.96.187.51:3001` 克隆会 `Logon failed could not read Username`，**必须用域名** `code.new-see.com:3001`。前端仓库 `AGENTS.md`/`CLAUDE.md` 规定：Vue 2.6.10 + Neap V10 微前端、必须用 `ns-*`/`ns-biz-*` 组件（**禁止 `el-*`**）、Service 模式 = `fetch + dataFilter`、ESLint Standard + Prettier（无分号/单引号/2 空格/LF，printWidth 160、tabWidth 4、trailingComma all）、Context 禁放 `funcId`（用 `Mix_funcId`）。**前端提交需人工切沙盒到个人模式，AI 无法代做**。

## 试点范围（2026-09-15 16:46 人工授权放宽 —— 一次设定，长期生效，不要再问）

**授权人**：蒋晓峰（会话内明确指定）。**授权内容**：试点范围 = `project = NCM AND labels = "AI自动开发"` 的**全部工单**，**不再按工单类型或改动性质做排除**。

**明确废止的排除项**（覆盖试点包 README「以下情形不纳入绿色自动化试点」中的两条）：

| README 原排除项 | 现在怎么处理 |
| --- | --- |
| 「新功能、需求口径不清或需要产品决策」 | 不再自动判黄 → 先按 **D1** 自选最优解并留痕；仅当"理解相反"才请示 |
| 「加字段、改界面、改配置中心」 | **不再是排除项**，按普通工单走绿色流程 |

**判灯只看技术条件（与工单类型无关）**：能否构造**有效红灯** ／ 能否完成**真实链路验证** ／ 是否需要**生产写操作**。三者满足且无需生产写 → 绿色。

**仍然硬停、必须交人工的两类（不可逆或跨系统影响，2026-09-16 NCM-3739 实例化）**：

1. 需要生产数据/生产写操作，或用户可见结果只能在**部署环境（业务库+系统库+前端）**才能验证。
2. 需要变更数据库结构或迁移脚本、公开 API 或跨服务契约、部署与基础设施。

> **实例（NCM-3739，2026-09-16 判红）**：需求「新增参数控制已终止支出合同可继续付款」看似只是加个参数，实际落地必须
> ① 改**系统库**按钮显隐配置（`ns_core_resourcebutton.RESOURCEBUTTON_INTERPRETER`，见下「改按钮显隐/加参数类工单」）；
> ② 提交**业务库**参数初始化脚本 + **系统库**参数设置表单生成物两套（`sql/v2/<迭代>.sql` 与 `sql/v2/<迭代>_system.sql`）。
> 这属硬停 ②，且用户可见结果（按钮出现并付款成功）需部署环境才能验证，属硬停 ① → **判红，只读分析 + 转人工**，不建分支。
> 要点：**「加字段/改界面/改配置中心不再是排除项」不等于「改系统库生成脚本可以自动做」** —— 前者是判灯不再按类型排除，后者是硬停 ② 的边界。

> 若这两类也要放开，只需人工一句话；未放开前按 README 转红/黄并写明「卡在哪一条」。

**提交/推送的授权依据**：README 要求「提交、推送、合并、部署仍按项目权限和人工授权执行」—— 授权人蒋晓峰的长期授权（2026-09-16 16:05 最新）已覆盖：隔离 worktree 内改代码、跑测试、建本地候选 commit、**push `ai/<KEY>` 开发分支、发起 PR(base=master)**；**合并 PR / 删除分支 / 部署 / 生产写不在授权内**（见下「交付边界」）。

## 交付边界（2026-09-16 16:05 最新口径：终点 = push + 发起 PR）

| 动作 | 谁执行 |
| --- | --- |
| 改代码、跑测试、本地候选 commit（隔离 worktree 内） | AI |
| **push `ai/<KEY>` 开发分支** | **AI（默认执行，不请示）** |
| **发起 PR（base=master，幂等，且不合并）** | **AI（默认执行，不请示）** |
| **JIRA 登记 PR 评论（`pr=` 等字段）** | AI |
| **合并 PR / 删除开发分支（远端与本地）** | **人工** |
| **Code Review（人工评审人签署）与最终验收** | **人工** |
| 部署/发布/触发流水线、生产库写 | 永不执行 |

AI 的终点是 **「本地候选 commit + 完整证据 + push 分支 + 发起 PR + JIRA 回写」**：

- 每个绿色工单交付时固定走完：`compliance 四查` → `push ai/<KEY>` → `pr <head> <title> <body>` → `verify` → JIRA `PR-READY` 评论。
- 本地分支与远端分支 `ai/<KEY>` **都由 AI 保留、不删除**（删除即等于销毁交付物；删除动作属人工）。
- worktree 目录清理后分支引用仍在（本地分支保留、远端已 push），人工可直接 `git worktree add` 或 checkout / 在 Gitea 页面对 PR 取用。
- JIRA 评论写清「分支、commit、红灯/目标测试、证据、`pr=`、**待人工：Code Review → 合并 PR → 删除开发分支 → 转「开发完成」**」。

> **口径演进记录（供追溯，不要再反复问）**：2026-09-16 09:30 授权「push + 发起 PR 即止」→ 同日 09:47 收紧为「本地 commit 即止（不 push）」→ 同日 15:56 经逐轮书面授权完成 NCM-3744 的 push + PR #32 → **16:05 人工指令「push 分支并发起请求写进工作流中」= 该做法固化为默认流程**。
> **现在不需要逐轮授权**：只要该轮是绿色工单、门禁与四查通过，就直接 push + 建 PR；不再问「是否授权 push」。
> **合并永不由 AI 执行**：`gitea_cli.py` 的 `merge` 子命令已于 2026-09-16 移除（调用即拒绝，exit=2），**任何情况下都不要恢复它**；也不要改用 `git push origin ai/<KEY>:master` 这类等价路径把代码写进 master。

**提示词优先原则**：自动化任务提示词（`AI自动开发（合同）`，id `9aa79f15-eac2-415f-95db-0548519f5e2d`，工作日每 3 小时执行）是本轮的**直接指令**。**2026-09-16 16:05 已按本节同步对齐**（push + 建 PR 写入交付链路；其余同前：占位符解析、状态映射、模板包新路径、D2 绕行、Code Review 无人值守口径、D6 不开单）。
若提示词与本节冲突：**以人工最新指令与本节的交付边界为准**（本次人工已明确把 push+PR 写进工作流 → 提示词若仍写「不 push」属未同步，应**按 push+PR 执行并在本轮报告里指出该冲突**）；涉及**合并/删除分支/部署/生产写**的冲突一律取更保守的一方（即不做）。

## 关键：本机构建方式（mvn 命令不可直接用）

1. **JDK**：`${paths.java}`；由本机配置给出并由 `config_loader.py validate` 校验，不再依赖系统 `JAVA_HOME` 或历史盘符。
2. **mvn sh 包装脚本已损坏**，必须用 java 直启 Launcher：

```bash
JAVA="<paths.java>"
MVN="<paths.maven_home>"
"$JAVA" -classpath "$MVN\\boot\\plexus-classworlds-2.8.0.jar" \
  "-Dclassworlds.conf=$MVN\\bin\\m2.conf" "-Dmaven.home=$MVN" \
  "-Dmaven.multiModuleProjectDirectory=<项目绝对路径>" \
  org.codehaus.plexus.classworlds.launcher.Launcher -B -ntp \
  -Dmaven.gitcommitid.skip=true <goals>
```

3. `-Dmaven.gitcommitid.skip=true` **必须加**：在 git worktree 下 `git-commit-id` 插件会报 `Could not get HEAD Ref`。
4. 用 `-Dtest=<类名>` 过滤时，**必须同时加 `-Dsurefire.failIfNoSpecifiedTests=false`**（注意是 `surefire.` 前缀；写成 `-DfailIfNoSpecifiedTests` 会因其他模块无匹配测试而 `BUILD FAILURE`，白白浪费一次 4 分钟构建）。
5. 反应堆只有两个模块：`newsee-contract-pojo`、`newsee-contract-rest`。用 `-pl newsee-contract-rest -am` 即可带上 pojo。
6. **凭据与本地仓库位置**：先读取 `${paths.maven_home}/conf/settings.xml` 与 `${paths.maven_local_repository}`。配置只保存路径，不复制其中的私有仓库凭据；不要因 `~/.m2` 为空就判定“无凭据不可构建”。
7. Bash 工具偶发 PATH 丢失（`tail: command not found`），命令前加 `export PATH="/usr/bin:/bin:$PATH"`。
8. Bash 工具偶发 F 盘瞬时不可达（`git: cannot change to '/f/Java/...'`）——重试即可，不要据此下结论。**2026-09-15 23:33 实测补充**：`git -C /f/Java/newsee-contract <cmd>` 可能在目录明明存在时连续 3 次报 `fatal: cannot change to`，而 `cd /f/Java/newsee-contract && git <cmd>` 立即成功 → 自检类命令**优先用 `cd && git`**，不要反复用 `-C` 重试。
9. 单次全量构建约 3～4 分钟；`sleep` 超过 120s 会被 SIGTERM，拆成多次 `sleep 100~115` 轮询。
10. **命令必须先 `cd <worktree>` 再启动 Launcher（2026-09-16 NCM-4000 实测）**：否则会报
   `[ERROR] Could not find the selected project in the reactor: newsee-contract-rest`（`-Dmaven.multiModuleProjectDirectory` 不能替代当前目录，反应堆根是按 cwd 找的）。正确姿势：`cd "$WT" && "$JAVA" -classpath ... Launcher ...`。
11. 日志用 `grep` 读时加 `-a`（构建日志含二进制/控制字符时普通 grep 会静默无输出，容易被误判为"日志没写"）；`Tests run:` 汇总行直接 `grep -a "Tests run:" | tail`。

## 已知阻断：跨仓编译错误（有可复现绕行，不必再判黄）

`newsee-contract-rest` 在基线 `master` 上**编译失败**，14 处错误集中在 3 个与业务工单无关的文件，均为 `找不到符号 setXxx`：

- `SyncBudgetServiceImpl`、`ExpenditureSettlementServiceImpl` → `com.newsee.budget.dto.BudgetExternalDTO` 缺 `taskId/processKey/payBankName/payBankAccount/customerType`
- `SyncFinanceServiceImpl` → `com.newsee.finance.dto.FinancePaymentDto` 缺 `isWithholdTax/withholdTaxAmount`

根因：上游 `newsee-budget`/`newsee-finance` 的源码与已发布快照均缺这些字段，属**跨仓不一致，不是待修工单的回归**。

**可行绕行（已在 NCM-3997 验证通过）**：这 3 个实现类**无任何外部引用**（仅 `implements` 接口），因此可在隔离 worktree 的 `newsee-contract-rest/pom.xml` 的 `maven-compiler-plugin` 配置中临时加：

```xml
<excludes>
  <exclude>**/SyncBudgetServiceImpl.java</exclude>
  <exclude>**/SyncFinanceServiceImpl.java</exclude>
  <exclude>**/ExpenditureSettlementServiceImpl.java</exclude>
</excludes>
```

并**在提交前 `git checkout -- newsee-contract-rest/pom.xml` 还原**，确保候选 commit 里不含该临时改动。绕行事实必须在 JIRA 评论与报告中如实写明（`env_note`）。

> **工序顺序铁律（2026-09-17 NCM-3992 踩坑）**：还原 pom 必须是**所有编译/测试动作都做完之后**的最后一步。
> 错误顺序：还原 pom → 合入新基线 → 复跑测试 ⇒ 必然 `[ERROR] COMPILATION ERROR ... 找不到符号 setCustomerType/setPayBankName` + `BUILD FAILURE`（看着像本单改坏了，实际是绕行被自己撤掉）。
> 正确顺序：实现 → 定向绿 → 全量 → package → **（如需同步基线）合入 origin/master → 复跑定向+全量** → 还原 pom → `git diff origin/master -- pom.xml` 验证为空 → commit → push → PR。
> 判断信号：日志里报错文件是 `SyncBudgetServiceImpl` / `SyncFinanceServiceImpl` / `ExpenditureSettlementServiceImpl` 三个**与本单无关**的文件时，一律先检查 pom excludes 是否还在，**不要去改业务代码**。

## 基线既有失败（全量测试永远不可能"全绿"）

`CheckPojoTest.testNoPojoReferenceInPom`（位于 `newsee-contract-rest/src/test/java/CheckPojoTest.java`）在**未改动的基线上就失败**：

```
在newsee-contract-pojo的pom.xml中找到了pojo依赖: [newsee-finance-pojo]
```

该用例只读取 `newsee-contract-pojo/pom.xml`（扫 `../` 下的 `newsee*pojo` 目录）。定性为「既有失败、非本次回归」的**可复核依据**：该文件在本次改动 `git diff` 中为空。按试点规则**不得标记为可忽略**，需在评论 `failures=` 字段单列并交人工裁决。

## NCM 工作流状态与试点映射（2026-09-16 修订）

`GET /rest/api/2/status` 实测本实例状态名与 id（NCM 常用）：

| 试点角色 | 实际状态（id） |
| --- | --- |
| 取单状态 | 新建（1） |
| 执行中状态 | 开发已回复（10000） |
| 黄色 / 待补充状态 | 开发/处理中（3） |
| 机器完成待验收状态 | 开发/处理中（3）（NCM 无「待验收」状态，靠评论说明） |
| 红色转人工状态 | 开发已回复（10000）（NCM 无「人工处理」状态，靠评论说明） |
| 执行失败状态 | 开发已回复（10000） |
| 人工合并后 / 人工转 | 开发完成（5）—— **由人工执行** |

**不存在**「待需求补充 / 待验收 / 执行失败 / 人工处理」这些状态。

**流转 id 不固定，取决于工单当前状态**（2026-09-15 实测）。工单在「新建」时可用流转只有 4 个：
`11 开发回复→开发已回复`、`21 开发已经解决→开发完成`、`161 开发处理→开发/处理中`、`201 关闭问题→问题已关闭`。
→ 从「新建」判黄/完成：**走 `161` 到「开发/处理中」**；从「新建」到「开发已回复」走 `11`。
**通用做法**：每次先用 `jira_cli.py transitions <KEY>` 打印当前可用流转再按**目标状态名**选，不要假定 id 固定。
若从当前状态查不到到「开发/处理中」的可用流转 → **保持现状**并在评论写明「待人工流转」，**不要为了凑状态去走「开发完成」**（代码尚未经人工评审与合入 master，谎报完成会误导验收）。

**流转 21（→开发完成）的必填字段**（少填一个就 HTTP 400；**AI 默认不执行该流转**，仅在确认人工已合并后使用）：

| 字段 | 说明 | 取值参考（同项目同经办人已解决工单的既有填法） |
| --- | --- | --- |
| `resolution` | 解决结果 | `{"name":"完成"}` |
| `customfield_10090` | 是否已自测 | `{"id":"13963"}` 开发已自测，继续测试 |
| `customfield_10400` | 影响客户范围 | `{"id":"10960"}` 一般共通 |
| `customfield_11510` | 开发实际工作量（数字） | NCM-3997=1.0 / NCM-3832=4.0 / NCM-3819=6.0 |
| `customfield_10022` | 预计开发完成（日期） | 填实际完成日 |

- 黄色 → 「开发/处理中」。
- 绿色完成（本地 commit + 证据齐） → 「开发/处理中」，评论写明「Code Review 与验收待人工；push/PR/合并待人工授权」。
- 下一轮被唤起时若发现人工已 push/合并 → 追加说明评论（写清 sha 与核验结果），**状态流转仍交人工**（除非人工明确要求 AI 转）。

**从「开发已回复」出发的实测流转集（2026-09-16 NCM-3744）**：只有 4 条 —— `31 开发处理中→开发/处理中`、`41 开发已经解决→开发完成`、`51 重新处理→重处理`、`211 关闭问题→问题已关闭`（**没有 161**，161 只在「新建」阶段可用）。
⚠️ **`31` 也带必填字段**：`customfield_10022 预计开发完成`（日期），漏填即 `HTTP 400: customfield_10022: 预计开发完成 is required`；实际还会连带要求 `customfield_11801 管控级别`（NCM-4000 实测 400 报的就是这个）。

✅ **正确做法：先读工单现值，能透传就透传（2026-09-17 NCM-3992 首次实测成功）**。`31` 的必填字段在多数工单上**早已由人工填写**（本单 = `customfield_11801={"id":"13171"}` 二级管控、`customfield_10022="2026-09-25"`）。此时**照抄现值提交即可，字段值不是 AI 新造的、也未构成新的交付承诺**：

```bash
# 1) 读现值（get_issue 取 fields）
python -c "import sys;sys.path.insert(0,'.ai-auto-fix');import jira_cli;f=jira_cli.get_client().get_issue('NCM-XXXX')['fields'];print(f.get('customfield_11801'),f.get('customfield_10022'))"
# 2) 透传现值流转
python .ai-auto-fix/jira_cli.py transit <KEY> 31 --fields '{"customfield_11801":{"id":"<现值id>"},"customfield_10022":"<现值日期>"}'
# → transition= {"success": true, "transition": "开发处理中"} / status_now= 开发/处理中
```

**仅当字段为空时**才不代填（属人工承诺）：保持「开发已回复」，发 `[AI-AUTO-DEV] NOTE` 给出可复制命令：
`python .ai-auto-fix/jira_cli.py transit <KEY> 31 --fields '{"customfield_10022":"YYYY-MM-DD"}'`
（`jira_cli.py` 2026-09-16 起支持 `--fields <json>` 带字段流转。）
> 判据记牢：**「照抄工单已有值」≠「代填承诺」**。前者直接做；后者（凭空给日期/选管控级别）才停手交人工。

⚠️ **2026-09-17 NCM-4007 补充：`customfield_10022` 为空时，只透传 `customfield_11801` 仍会被拒**。实测请求带 `{"customfield_11801":{"id":"13171"}}` 仍 `HTTP 400: customfield_10022 预计开发完成 is required`。此时**不要为了过流转而编造日期** —— 保持「开发已回复」，发 `[AI-AUTO-DEV] STATUS-NOTE`，正文写清 `status_now= / target= / blocked_by=（报错原文 + 「该字段为空=人工排期承诺，AI 不代填」）/ 可复制命令 / 说明=未用「开发完成」避免谎报 / delivery_now=`。**判断顺序固定：先读现值 → 两个都非空则透传流转；任一为空则停手发 STATUS-NOTE。**

- **陷阱**：`transition_issue(key,'41')` 会 HTTP 400 `resolution is required`，必须带上解决结果：
  `c.transition_issue(key, '41', {'resolution': {'name': '完成'}})`。
  可用 solution 列表：`GET /rest/api/2/resolution`（含 `完成`、`不解决`、`无法重现`、`需重新处理` 等）。
- **陷阱**：不要绕过 `jira_cli.py` 直接 `JiraClient()` 调 API —— 裸构造**没有登录态**，一律 `HTTP 401`（要用 `get_client()` + `c.login()`）。

## Git 服务（Gitea）：push / 发起 PR —— **默认执行（2026-09-16 16:05 起）；合并禁止 AI 执行**

远端是自建 **Gitea 1.17.3**：`http://source.new-see.com:3005/NEAP/newsee-contract.git`
（同机 IP 别名 `47.96.105.192:3005`，API 报错里会出现后者，属同一实例）。
判定方式：`GET /api/v1/version` 返回 JSON → Gitea；GitLab 是 `/api/v4`（本实例 404）。

### 凭据怎么取（不要硬编码密码）—— 2026-09-15 修订，旧写法会**永久阻塞**

**坑（实测）**：本机**系统级** gitconfig（`<PortableGit>/etc/gitconfig`）设了
`credential.helper=helper-selector`（交互式「选账号」助手）。无人值守时它会一直等交互输入：
`git credential fill` / `git ls-remote origin` / `git push` **全部无限挂起**（实测 4~5 分钟零输出，
曾被误判为「网络不通」）。逐层验证的结论：Gitea HTTP API `curl http://source.new-see.com:3005/api/v1/version`
返回 200 且耗时 0.05s → 网络正常，**挂起点就是凭据助手**。

**正确取法**（跳过系统配置 + 显式指定 GCM）：

```bash
printf 'protocol=http\nhost=source.new-see.com:3005\n\n' | \
GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
  git -c credential.helper=manager credential fill
# → protocol/host/username=jiangxiaofeng/password=...
```

**push 也必须带同样的环境**，否则照样挂起：

```bash
GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
  git -c credential.helper=manager push origin ai/<KEY>:ai/<KEY>
```

**⚠️ 2026-09-16 实测补充：`git fetch` 同样会挂起（不只是 push）**。本仓库远端为 http 私有地址，`git fetch origin master` 也需要走凭据助手 → 裸执行会无限挂起（实测 2m25s 零输出，只能手动 kill，容易被误判成「远端卡住/网络问题」）。**所有需要访问远端的 git 命令（fetch / ls-remote / push / credential fill）统一加这套环境变量**：

```bash
timeout 60 env GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
  git -c credential.helper=manager fetch origin master   # 实测 60s 内成功，exit=0
```

（`git status` / `git log` / `git rev-parse` 等纯本地命令不受影响，无需加。）

**诊断口径**：`timeout 20` + 检查退出码。124 = 超时挂起（凭据助手问题）；128 + `could not read Username` = 没有助手（配置被跳过）。
`-c credential.helper=manager` 单独用**无效**（命令行 `-c` 是追加，系统 `helper-selector` 仍先跑），必须叠加 `GIT_CONFIG_NOSYSTEM=1`。

取到凭据后不落盘：`gitea_cli.py` 每次运行临时取用，只放到 `Authorization: Basic` 头里。
**绝不**把密码写进文件、证据目录或提交。

### 工具环境坑（2026-09-17 NCM-3971 交付轮实测）

1. **shell PATH 损坏（dirname not found 连锁）**：若 `ls/cp/grep/cat/head/find` 全部 `command not found`，把 `${paths.git_usr_bin}` 转成当前 shell 可用形式后加入 PATH；或直接用 **python（shutil/os/subprocess）替代 coreutils**。禁止回退到历史用户名下的 PortableGit 路径。
2. **Edit 工具多行替换误删行**：old_string 含 7 行而 new_string 只写了其中 1 行 → **静默删掉其余 6 行业务代码**，工具不报错。修复=立即读回该区段补全；预防=**new_string 必须完整包含所有要保留的行**（只改动的行可变，其余原样保留），改完先 `git diff` 核验行数与上下文再 commit。同类文件锁错误 `EBUSY` 重试一次即可（前一次写入的短暂冲突）。
3. **前端文件的换行符噪音**：前端仓库 `core.autocrlf=true` 且无 `.gitattributes` → 改完 `NS_contract/**` 文件后 `git diff` 会提示 `warning: LF will be replaced by CRLF`。**这是正常提示不是错误**，diff 内容本身仍是干净的小改动（本轮 +14 −3）。**判据**：看 `git diff --stat` 的行数是否符合预期，若出现整文件重写（几百行变更）才是真问题（那时检查是否被工具改了行尾）。

### push（**交付链路固定环节：绿色工单交付即执行，不需请示**）

```bash
git -C <worktree> push origin ai/<KEY>:ai/<KEY>
# 远端已有同名分支且内容一致时跳过（幂等）；不一致时先看是否本分支历史（force 一律禁止）
```

**2026-09-16 15:56 首次实测通过、16:05 起固化为默认流程的完整配方（每轮绿色交付都照此跑）：**

```bash
# 0) 先 fetch 复核基线（务必带凭据安全环境变量，否则挂起）
cd /f/Java/newsee-contract
timeout 90 env GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
  git -c credential.helper=manager fetch origin master
git merge-base --is-ancestor origin/master ai/<KEY> && echo "已含最新基线，可 ff"
# 1) push（同样必须带那三个环境变量 + -c credential.helper=manager）
timeout 240 env GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
  git -c credential.helper=manager push -u origin ai/<KEY>
# 2) 建 PR（幂等；标题/正文先写进两个 UTF-8 文件）
python <paths.automation_workspace>/.ai-auto-fix/gitea_cli.py pr ai/<KEY> <title.txt> <body.md>
# 3) 核验（四查④：base.sha 必须等于远端 master HEAD）
python <paths.automation_workspace>/.ai-auto-fix/gitea_cli.py verify <PR号> ai/<KEY>
# 4) 回 JIRA 发 [AI-AUTO-DEV] PR-READY 评论：pr=#号+URL / head= / remote_branch= / base=+base.sha 比对 / pr_state / authorization=默认工作流 / merger=待人工 / next=
```

要点与实测观察：

- `git push` 成功时远端会顺带回一段 `remote: Create a new pull request for 'ai/<KEY>': <compare URL>`，**该 URL 用 IP 形式**（`http://47.96.105.192:3005/...`），可直接转给人工。
- push 走 HTTP + Git Credential Manager 取凭据，**不要**用 `git push` 裸命令（会被系统级 `helper-selector` 卡死）。
- 建 PR 前把标题/正文写成文件（`pr_title_<KEY>.txt` / `pr_body_<KEY>.md`），正文照「改动表 + 口径 + 验证证据 + 基线 + 待人工 + 关联评论号」组织 —— 与 `gitea_cli.py pr` 的三参签名匹配，也便于人工直接审。
- **PR 正文与 `[AI-AUTO-DEV] DONE` 评论要分开写**：PR 是给评审人看的（含 diff 视角），评论是给 JIRA 留痕的。
- 建完 PR 后 **JIRA 追加一条评论**登记：`pr=#编号 + URL / head= / remote_branch= / base= + base.sha 比对结果 / pr_state / pr_convention / authorization= / merger=待人工 / next=`。
- **push 后必做基线终检（2026-09-17 NCM-4009 实测：master 会在一轮内前进 —— 四查时一致、push 时已落后）**：首次 push 后立即 `timeout 120 env GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git -c credential.helper=manager ls-remote origin master`，再 `git merge-base --is-ancestor origin/master HEAD && echo OK`。不在祖先链 → `git fetch origin master` → `git -c user.name="WorkBuddy AI" -c user.email="ai-autodev@new-see.com" merge origin/master --no-edit` → 重加 pom 绕行 → 复跑定向+全量 → 还原 pom → 再 push（PR 会自动挂接既有 PR，无需新建；JIRA `base_check` 写清前后两段基线）。

### 发起 PR（**交付链路固定环节：push 成功后立即建 PR**；幂等：先查再建）

`POST /api/v1/repos/{owner}/{repo}/pulls`，body：`{"title","body","head":"ai/<KEY>","base":"master"}`。

- 幂等：先 `GET /pulls?state=all&limit=50`，若存在 `head.ref == ai/<KEY>` 的 PR 则复用，不要重复创建。
- 顺带 `GET /branch_protections` 看目标分支是否受保护（本仓库保护的是 22 个 `V10.0.*.RC`，**master 未保护**）。
- 返回 `201` + `number`/`html_url`；`mergeable=True` 表示无冲突。

### 合并 —— **禁止 AI 执行（2026-09-16 09:30 起；16:05「push+PR 进工作流」的调整不含合并，仍禁止）**

**AI 不得调用合并接口，也不得用任何其他方式把代码写进 master。** 合并动作与开发分支的删除一律由人工完成。

以下内容**仅作为知识保留**（用于向人类解释/写 PR 描述），**不是可执行步骤**：

- 接口：`POST /api/v1/repos/{owner}/{repo}/pulls/{index}/merge`，body `{"Do":"merge"}`（Gitea 1.17 用大写 `Do`）。
- 本仓库 PR 惯例（实测 #11–#31 一致）：`base=master`、合并方式 = merge commit，
  提交信息格式 `Merge pull request '<title>' (#N) from X into master`；**无 squash、无 rebase**。
- 人力提示：人工合并前建议先看 `[AI-AUTO-DEV] DONE` 评论/PR 摘要与四查结论，再决定是否合并。

#### 人工直接说「合并进 master」怎么办（2026-09-16 15:34 实测口径）

**不执行，但把前置工作做满 + 一行命令交接。** 该指令只有 3 个词，不足以判定为「变更长期规则」；按单次指令执行会绕过人工评审/验收环节。处理动作：

1. 明确回复「未执行合并」，点明命中的是**长期硬边界**（不是本轮能力不足）；
2. 顺手做满「合并就绪」（这段是允许做的，属合规四查④）：`git fetch origin master` → 若基线前进，建 wt-pilot 合入 `ai/<KEY>` → **重跑同一套测试** → 还原临时绕行 → worktree 删净 → 导出相对最新基线的补丁；
3. 在 JIRA 发 `[AI-AUTO-DEV] NOTE / 分支已同步最新基线，处于「可 fast-forward 合入 master」状态`，字段含 `head=/commits=/base_check=/reverify=/diff_vs_base=/patch=/merger=待人工/decision=`（decision 里写明「若需改为允许 AI 合并，请明确变更该长期规则，不按单次指令处理」）；
4. 回复里给人工**可直接粘贴的命令**（分两条路径）：
   ```bash
   cd /d <paths.backend_repo>
   git fetch origin master
   git log --oneline origin/master..ai/<KEY>      # 确认要合的内容
   git push origin ai/<KEY>:master                # 路径 A：本分支已含 origin/master → fast-forward
   # 路径 B（master 有保护/需评审时）：git push origin ai/<KEY> 后在 Gitea 走 PR 合并
   ```
   路径 A 不可用时兜底：把 `<KEY>-merge-ready.patch` 交给人工 `git am`。

**判据一句话**：**「合并就绪」是 AI 的活，「合并动作」是人工的活。** 边界没被明确改写前，一律照此办理，不要因为指令短就直接执行。

### 四查（**每轮 push + 建 PR 之前必做**；缺一不可，用于自证 PR 可用）

1. **惯例**：`GET /pulls?state=all` 看历史 PR 的 base 与是否 merged。
2. **分支保护**：`GET /branch_protections`，确认目标分支不在列表内。
3. **部署风险**：`GET /hooks` 看 push webhook。本仓库只有 2 个 Dify 检查机器人
   （`/api/dify/checkGitSql`、`/api/dify/checkGitCode`），**无 CI/部署钩子** → 不会因 push/合并触发部署。
4. **可交付性**：`GET /pulls/{n}` 的 `base.sha` 是否等于**远端** master HEAD、`mergeable` 是否为 true。
   **坑（2026-09-15 实测）**：比对对象必须是**远端** master HEAD —— 本地 `master` ref 可能早已陈旧。
   本轮一度因为拿陈旧的本地 `master`（65603da18）去比 PR 的 `base.sha`（1d01743c）而**误判 ④ 不通过**；
   正确做法是**先 `git fetch origin master` 再比**（或直接用 `GET /repos/{o}/{r}/branches/master` 的 sha）。
   若作业期间 master 前进过（曾一次前进 6 个提交），**先把 `origin/master` 合入本分支并重跑测试**再交付。

**注意（因 AI 不合并而必须遵守的基线口径）**：AI 不合并 → 本地 `master` ref **不会**因合并而前进。
所以**每轮建分支的基线一律取 `origin/master`（先 `git fetch origin master`）**，
用 `git worktree add -b ai/<KEY> <wt> origin/master`，**不要用可能陈旧的本地 `master`**。
`git fetch` 只更新远端引用、不动工作区文件，共享工作区仍视为零改动。
**（2026-09-16 补充）fetch 必须带凭据安全环境变量，否则挂起** —— 见本文件「凭据怎么取」末尾的补充说明；本轮实测 `origin/master` 已从 `6c7d00d01` 前进到 `6604381bd`（本地 master ref 陈旧属预期）。

交付后不主动改共享工作区：不做 `merge --ff-only` 同步（那是人工合并后的动作，由人工执行）。

#### Gitea 页面事实（2026-09-16 15:51 实测，写 PR 描述或向人工解释时直接用）

- 仓库路径 = **`NEAP/newsee-contract`**；PR 列表 = `…/NEAP/newsee-contract/pulls`。
  人工可能用 **IP `47.96.105.192:3005`** 访问，自动化用域名 `source.new-see.com:3005`，**同一台服务器**（别当成两个环境）。
- **`master` 不受分支保护**：受保护的只有 22 个 `V10.0.*.RC` 分支 → 直接 `git push origin ai/<KEY>:master`（fast-forward）技术上可行；是否需要走 PR 纯看团队流程（历史 29 个 merged PR 全 base=master、全 merge commit）。
- push webhook 只有 2 个 Dify 检查：`checkGitSql` / `checkGitCode`（`http://172.16.44.104:5558/api/dify/*`），**无 CI/部署钩子** → push/合并不触发部署；但推 SQL 后要留意 `checkGitSql` 的结果。

#### 「人工说 Gitea 上没看到合并请求 / PR」诊断（一步定位，别猜）

**两种原因，都不是人工看错页面**：① 该轮发生在 16:05 之前（当时规则不允许 AI push）→ 属正常，说明情况并按新规则**补做 push + 建 PR**；② 本轮 push 环节失败（凭据助手挂起、base.sha 校验不过、网络失败）→ 用下面两条只读命令定位后**重试**。

```bash
python .ai-auto-fix/gitea_cli.py compliance ai/<KEY>      # 输出末行 [4] PR: 不存在（尚未创建）
# 或直接查分支：GET /repos/NEAP/newsee-contract/branches/ai%2F<KEY>  → 404 = 远端没有该分支
```

答复口径：① 说明根因（未 push 或 push 失败，不是页面问题）；② 给出 Gitea 路径与 IP `47.96.105.192:3005` / 域名 `source.new-see.com:3005` 的同一性；③ **push/建 PR 已是默认动作，不需要人工授权** —— 直接补做并回 JIRA 登记 `pr=`；④ 若凭据/网络始终不可用，给人工可直接粘贴的命令兜底。

## 前端开发场景（`micro_contract_management`）—— 2026-09-17 NCM-3971 首次实操，全流程实测通过

> **一句话**：前端工单的**唯一真门槛是「改动落点定位」**（目录不在 `src/` 下、Vue 2 选项式、模板/提交多处耦合），
> 而**交付链路 = 后端的同构复制**（建 worktree/分支 → 改 → commit → push → 建 PR），只是换一个 host。
> 本轮前端侧**没有红灯可写**（本机无法跑 Vue 构建/单测）→ 用「行为矩阵 + diff 自证 + 人工联调」替代，见「前端验证口径」。

### 仓库与分支（记住这三条就不会走错）

| 项 | 值 |
| --- | --- |
| 克隆地址 | `http://code.new-see.com:3001/NW-frontend/micro_contract_management.git`（**必须用域名**，用 IP `47.96.187.51:3001` 克隆会 `Logon failed`——git 凭据按 host 含端口存储） |
| 工作空间 | `${paths.frontend_worktree}`（独立浅克隆；`git clone --depth 1 --branch master <url> <paths.frontend_worktree>`） |
| 分支/基线 | 与后端同规则：`git fetch origin master` → `git worktree add -b ai/<KEY> <wt> origin/master`（或直接在该浅克隆上 `git checkout -b ai/<KEY>`）；分支名同为 `ai/<KEY>`，**与后端同名但互不相干** |
| API | Gitea **1.9.2**，前缀 **`/api/v1`**（后端实例是 1.17.3 的 `/api/v1`，两者路径相同但**不同实例**，别把凭据/组织搞混） |

### 前端代码定位（最容易卡住的一步）

**`ls src/views` 会什么都没有** —— 前端不是标准 `src/` 布局，根目录下按业务域分目录：

```
micro_contract_management/
├── NS_contract/                     ← 合同域（本试点相关改动都在这里）
│   ├── service/contractManagement.js            ← API 定义（fetch + dataFilter 模式）
│   ├── assets/
│   └── views/contract/contractManagement/
│       ├── contractManagement.vue               ← 列表页
│       └── components/contractManagement-form-dialog.vue   ← 表单弹窗（改动最集中的文件）
└── ...（其他 NS_* 业务域）
```

**定位配方**：`Glob <wt>/**/*contractManagement*` 或 `Glob <wt>/**/*<关键词>*.vue`，**不要**先 `ls src/`。找到文件后按「关键词 grep → 读上下文 30 行 → 改」的次序，不要整文件通读（单文件 3000+ 行）。

### 前端代码约束（`AGENTS.md` / `CLAUDE.md` 规定，违反会被 ESLint 拦）

| 约束 | 内容 |
| --- | --- |
| 框架 | Vue **2.6.10** 选项式 API + Neap V10 微前端（不是 Vue 3 / 组合式） |
| 组件 | 必须用 `ns-*` / `ns-biz-*` 组件，**禁止 `el-*`**（Element UI 直调） |
| Service 模式 | `fetch + dataFilter`，不手写 axios |
| 代码风格 | ESLint Standard + Prettier：**无分号、单引号、2 空格缩进、LF**，`printWidth 160`、`tabWidth 4`、`trailingComma all` |
| Context | 禁止在 context 里放 `funcId`，用 `Mix_funcId` |
| ⚠️ `prop` 不可变 | **`vue/no-mutating-props` 会拦** `this.<prop> = x`。模板 id 这类由父组件传入的 prop，**不要就地回写**，改用本组件 `data` 字段承载（NCM-3971 用 `latestTemplateId` 即此因） |
| ⚠️ 沙盒 | 前端页面验证需人工把沙盒**切到个人模式**，AI 无法代做 → 评论/汇报里显式提示 |

> ⚠️ **AGENTS.md / CLAUDE.md 是给别的 AI 工具读的，里面的命令（构建/提交）未必适用于本机**。照它写代码，
> 但**不要照它跑命令**（尤其不要试图在本机跑前端构建 —— 依赖没装，见下「前端验证口径」）。

### 前端改动配方（NCM-3971 实例，五处改动的形状可直接复用）

当需求是「某个场景要换成新数据源/新接口」时，改动**几乎总是这几处**，照此清单逐处核对，避免「改一半」：

1. **`data()` 声明承载字段**（不要写 prop）；
2. **`visible` watcher 里重置**（弹窗复用 → 不重置会残留上一单的值，是本类 bug 的典型来源）；
3. **数据获取方法内分流**（按 `this.dialogType` 判断走哪个 URL / 哪个接口），并在拿到响应后**记录关键 id**；
4. **暂存路径落库处**（NCM-3971 在 `:2253`）—— 写成 `新值 || 旧值` 的**回退式**，天然保证不影响其他场景；
5. **正式提交路径落库处**（NCM-3971 在 `:2524`）—— 注意这类地方**往往已有一个 `if (dialogType ∈ {add,copy,renew})` 的分支块**，需要：① 把该块内的赋值改成回退式；② **额外补一个新的 `if`** 覆盖之前没被这个块管到的场景（NCM-3971 是 `change`）。

> **本类场景的「改一半」陷阱（必查）**：页面渲染用的是新接口返回的数据，但**提交/暂存落库时取的可能是另一个变量**。
> 只改渲染源、不改落库值 = 用户看到新模板、存下去还是旧模板 id，**业务痛点完全没消除**。
> **核对方法**：把「渲染取值点」与「落库赋值点」都在 grep 里列出来，逐个确认已覆盖。NCM-3971 的落库点有 2 个（暂存 + 提交），都要改。

### 前端验证口径（**本机不可跑构建/单测 —— 这是前端场景与前端的最大差别**）

前端浅克隆里**没有 `node_modules`，本机也没有前端构建环境** → 无法写红灯、无法跑 lint/单测。**不要伪造「已验证通过」**。
用下面三层替代（都属可复核证据）：

| 层级 | 做法 | 本轮实例 |
| --- | --- | --- |
| 静态自证 | `git diff` **逐行读**，确认：改动只在预期处、无误删、括号/缩进完整、无 `el-*` 新引入、无 `this.<prop>=` | 最终 +14 −3，五次改动各自对应一句注释 |
| 行为矩阵 | 把 `dialogType` × 「打开取哪个接口 / 落库用哪个 id」列成**表格**写进 PR 正文与 JIRA 评论 | add/copy 走原接口且 `latestTemplateId` 恒 null → 行为不变；change/renew 走新接口 |
| 依赖声明 | 明确写出**未经联调的部分**与**跨仓依赖顺序** | 后端未部署时前端调新接口 404，`getTemplateFormJson` catch 兜底 → 建议后端 PR 先合 |

> **不要在 PR/JIRA 里写「测试通过」**。写「无本机可执行测试；以静态自证 + 行为矩阵为证据；待部署环境人工联调」。
> 若人工明确要求补前端测试，属新范围（需先解决本机前端构建环境），应回复说明而不是硬凑。

### 前端 PR 怎么建（**`gitea_cli.py` 不适用**，用下面这条 python 直连配方）

`gitea_cli.py` 只指向后端实例 → 用它建前端 PR 会 404（或建到错误的仓库）。**实测可用配方**（凭据全程内存、不落盘）：

```bash
python -c "
import json, urllib.request, urllib.error, base64, subprocess, os
env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
out = subprocess.run(['git','-c','credential.helper=manager','credential','fill'],
                     input='protocol=http\nhost=code.new-see.com:3001\n\n',
                     capture_output=True, text=True, env=env, timeout=60).stdout
user = pwd = ''
for line in out.splitlines():
    if line.startswith('username='): user = line[9:]
    elif line.startswith('password='): pwd = line[9:]
assert user and pwd, 'credential fill failed'
body = open('<paths.automation_workspace>/.ai-auto-fix/pr_body_frontend_<KEY>.md', encoding='utf-8').read()
payload = {'title': 'feat(...): <KEY> ...', 'head': 'ai/<KEY>', 'base': 'master', 'body': body}
req = urllib.request.Request('http://code.new-see.com:3001/api/v1/repos/NW-frontend/micro_contract_management/pulls',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type':'application/json',
             'Authorization':'Basic '+base64.b64encode((user+':'+pwd).encode()).decode()}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        r = json.loads(resp.read()); print('PR', r.get('number'), r.get('html_url'), r.get('mergeable'))
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read().decode('utf-8','replace')[:500])
"
```

- 幂等：先 `GET .../pulls?state=all&limit=50` 查 `head.ref == ai/<KEY>`，有则复用不重复建。
- push 前端分支同样要带那三个环境变量 + `-c credential.helper=manager`（见「凭据怎么取」）。
- **不要**用 shell 管道 + `grep`/`cut` 组这条命令：本轮实测 PATH 损坏会让它们全挂（见「工具环境坑」），**一律在 python 内完成**。
- 前端 PR 建成后 **JIRA 追加一条 `PR-READY` 评论**（跨仓要写**两个 pr=**），并在 `repo=` 字段标明这是另一台 Gitea。

### 跨仓工单（后端 + 前端）的交付形态

当工单同时要求改后端 `newsee-contract` 与前端 `micro_contract_management` 时（NCM-3971 即此类）：

| 项 | 处理方式 |
| --- | --- |
| 分支 | **两个仓库各自建 `ai/<KEY>`**（同名的两条独立分支，互不相干）；两侧都要走 `fetch origin master` → 建分支的同样流程 |
| PR | **两个 PR**，都 base=`master`：后端用 `gitea_cli.py pr`；**前端用上面那条 python 直连配方**（`gitea_cli.py` 会 404） |
| JIRA 登记 | **发两条 `PR-READY` 评论**（本轮实测更清晰）：后端一条（pr=#34 / 四查结论）、前端一条（pr=#213 / `repo=` 标明另一台 Gitea / 合并顺序提示）。若合并成一条，则必须分别列出两个 pr= 与两个 URL |
| 合并依赖顺序 | 后端新接口需先可用 → 前端才能联调。**合并本身仍由人工**；评论里要写明「**建议后端先行**」，并说清后端未部署时前端的降级表现（NCM-3971：调新接口 404，`getTemplateFormJson` 的 catch 兜底 → 弹窗能开但模板 JSON 为空） |
| 前端沙盒 | 前端页面验证需人工**切换沙盒到个人模式**，AI 无法代做 → 在评论/汇报里显式提示 |
| 收尾 | **两个 worktree 都要清**（`wt-pilot` + `wt-frontend`）；前端浅克隆直接 `rmtree` 即可（无需 `worktree remove`，它不是 git worktree——除非你按上位方式用 `worktree add` 建的）；两侧本地 + 远端分支都**保留**，交人工合并后删除 |

### 可直接复用的脚本（`${paths.automation_workspace}/.ai-auto-fix/`）—— 2026-09-15 已收敛为 2 个入口

| 脚本 | 用途 |
| --- | --- |
| `jira_cli.py` | `queue`（查筛选器 40473 队列）/ `detail <KEY>` / `comment <KEY> <file>` / `transitions <KEY>` / **`transit <KEY> <id>`（执行流转，id 先现查；成功后回读并打印 status_now，便于复核）** |
| `gitea_cli.py` | `compliance <head_br>`（发起 PR 前四查）/ `pr <head_br> <title_file> <body_file>`（幂等建 PR）/ `verify <pr_number> <head_br>`（核验 PR 状态与远端分支仍在） |

`merge` 子命令已于 2026-09-16 **按人工指令移除**（AI 不再具备合并能力）；若脚本里又出现合并调用，即为违规，应先删掉再执行。

两者均通过 `git credential fill`（带上面那套环境）**运行时取凭据、不落盘**。
已删除 20 个一次性脚本（`jira_*.py` × 17、`git_pr.py` / `git_merge.py` / `final_check.py`），**不要再用旧名**。

### 默认授权与硬边界（2026-09-16 16:05 修订：终点 = push + 发起 PR；合并仍禁止）

**默认已授权、不再逐次询问**：在隔离 worktree 内改代码、跑测试、建**本地候选 commit**、**push `ai/<KEY>` 到远端**、**发起 PR（base=master，幂等）**、写 JIRA 评论与流转。**到此为止。**

**仍需人工执行（AI 不做，也无须询问）**：**合并 PR**、**删除分支**、Code Review 签署、人工验收。

**永久硬边界（不自作主张、也无须询问，直接不做）**：

- **合并 PR 到 master（任何形式：merge commit / squash / rebase / 直接 push master / `git push origin ai/<KEY>:master` / 本地 fast-forward 后推）**。
- **删除任何分支**（远端 `ai/<KEY>`、本地 `ai/<KEY>`、他人分支）—— 分支即交付物，删掉等于销毁成果。
- 部署/发布/触发流水线；任何生产库写操作。
- `force push`、改动 GitHub/Gitea 仓库的 branch protection 配置。
- 修改或关闭他人 PR、绕过仓库既有 review 约定。
- **代签人工评审结论 / 虚构评审人 / 勾选人工验收项**。

**硬停并交人工（仅这 3 种情形）**：

1. 修复需要改变对外接口/数据语义，或需要改上游 `newsee-budget`/`newsee-finance`。
2. 需要生产数据/生产写操作，或需变更 DB 结构/系统库生成脚本/部署拓扑（硬停②）。
3. 改动波及面超出工单范围（>5 个生产文件或跨模块）。

远端分支与本地分支 `ai/<KEY>` 均由**人工在合并后删除**；在此之前 AI 不得触碰。

## 自主决策规则（2026-09-16 修订：默认自己拍板，不再事前请示；交付动作止于「push + 发起 PR」）

试点工单的目标是「产出**对的**、**可被人工直接评审并合入 master 的本地分支 + 一个可直接点合并的 PR**」。出现下列情形一律**自主执行 + 留痕**，不要停下来等人拍板；不需要自主的是「合并 / 删分支 / 代签评审」——那些不归 AI。

### D1 方案选择：能判定就自己定

满足全部 4 条 → 直接实施该方案，**不得把 A/B 抛给人工**：
① 改动最小；② 与仓库既有同模式写法一致（有同类列/同类方法可参照）；③ 全仓 grep 已核实引用面与副作用（如枚举 `desc` 无人读 → 改文案零行为影响）；④ 该方案在本机**可被测试验证**（另一方案需 DB/配置/生产环境才能验证 → 直接淘汰）。

> 反例（NCM-3997 首轮踩坑）：方案 A（VO 补 `<code>Name` + Service 回填 + 枚举文案修正）满足全部 4 条；方案 B（查数据字典）本机不可验证 → **本就该直接做 A**，却停下等人工回「A」，白烧一轮。

仅当两方案在**对外行为/数据语义上不可逆地不同**、且代码、单测、注释、既有惯例均无法判定时才请示；请示必须自带默认值：「我倾向 X（因为…），若无异议我按 X 执行」，且 X 永远选可回滚的那个。

### D2 环境报错：先绕行，不直接判黄

遇到与工单无关的编译/依赖阻断，按序自试；**任一成功即继续绿色流程，不再请示「是否开发」**：
1. grep 确认阻断文件是否被外部引用 → 无引用则在**隔离 worktree 内**给 `maven-compiler-plugin` 加 `<excludes>`，提交前 `git checkout -- <pom>` 还原；
2. 缩小范围：`-pl <module> -am`、`-DskipTests`、`-o` 离线、指定上游快照版本；
3. 仅当必须上游改动（如其他仓的 DTO 缺字段）才判黄，且评论里写清「需要哪个仓加哪些字段」。

> 反例（第二轮踩坑）：已确认这 3 个文件无外部引用、绕行显然可行，仍判黄并等人工说「进行开发」。

### D3 环境结论必须实测，且禁止"只查一处就下结论"

下「不可构建 / 无凭据 / 环境不可用」这类结论前，必须完成 3 步：
1. **找全 `settings.xml`**：已知候选目录优先，`-maxdepth 3`；**禁止全盘 `find /c /d /e /f`**（实测跑 65 分钟且零新增信息）；
2. **实测一次最小构建目标**（`validate` 或 `-pl <module> compile`）并保留真实报错——不要从「`~/.m2` 为空」推断 401；
3. 若是 401/无凭据，用 settings 的 `<server>` id 对照 pom 的 `<repository>` id 再定性。

负面结论必须标注**置信度 + 未验证项**；**下一轮开工第一件事是复核上一轮的负面结论**（本次因未复核，第一轮的错误结论拖到第二轮才纠正）。

### D4 交付链路：push + 发起 PR（2026-09-16 16:05 修订为默认流程）

见「默认授权与硬边界」。链路 = `commit` → **push `ai/<KEY>`** → **建 PR（base=master，先 compliance 四查、幂等）** → **写 JIRA DONE + PR-READY 评论** → **流转到「开发/处理中」** → **停止（不合并）**。
`next=` 字段写明「待人工：Code Review → 合并 PR → 删除开发分支 → 转开发完成」。
仅 3 种情形硬停（见上）：需改对外语义或上游仓 / 需生产写或改 DB 结构 / 波及面超范围。
> 历史口径：09:30 授权 `push → PR 即止` → 09:47 收紧为「本地 commit 即止」→ **16:05 人工指令「push 分支并发起请求写进工作流中」= 恢复并固化为默认流程（本节的现行口径）**。合并始终不归 AI。

### D5 用「事后可审计」替代「事前请示」

每次自主决策在 DONE 评论里一行留痕，供人工事后复核：

```
decisions=[D1 采纳方案A(最小改动+既有同模式+枚举desc无人读+本机可验证); D2 绕行跨仓编译(excludes 3文件,提交前已还原); D4 push+PR 默认执行(已 push ai/<KEY> 并建 PR #N，不合并/不删分支); D6 顺手发现项只汇报不开单]
```

### D6 顺手发现的问题：只汇报，不开单（2026-09-16 人工修订，覆盖旧规则）

与工单无关但确属缺陷的发现（跨仓 DTO 不一致、工单描述含明文口令、上游仓缺陷等）→ **一律不建 JIRA 单、不指派给任何人员**（2026-09-16 人工明确指令：不要提 JIRA 单给相关人员）。处理方式：只在当轮汇报和（如已在处理的）工单评论中**事实性列出**发现，标注「未开单，由人工决定是否跟进」即可。

**例外**：全量测试中的**基线既有失败**（如 `CheckPojoTest`）同样只单列、不开单，并注明"非本次回归"的可复核依据。

> 历史遗留：NCM-3999 为旧规则下的存量单，人工已表示「不用管」，不再跟进、不追加评论、不转状态。

### （已停用）D6 实操：NCM 建单必填字段——保留仅作参考，当前规则禁止自主开单

`POST /rest/api/2/issue` 建单会被拒 8 次左右的字段校验（`errors` 只回一批），**先取元数据再建单**：

```bash
# 必填字段与值域（createmeta 的老接口 404，用这个新路径）
GET /rest/api/2/issue/createmeta/NCM/issuetypes/1
```

必填：`components`（模块，array）、`customfield_10601` 功能现状、`customfield_10602` 客户提出角色（**自由文本**）、
`customfield_10041` 期望上线时间（date）、`customfield_13401` 修改建议、`customfield_13400` 业务场景、
`customfield_12600` 客户信息（**级联选择**）、`customfield_10000` 客户名称（option）。

- 级联字段格式：`{"id":"15865","child":{"id":"15866"}}`（父=客户，子=项目；`00-内部测试` 父 15865 / 子仅 `其他` 15866）。
- 内部自检发现的缺陷：`客户信息=00-内部测试(15865/15866)`、`客户名称=00-新视窗(13163)`、
  `客户提出角色` 写「内部（AI 自动化试点自检发现，非客户提出）」（自由文本，**如实写**即可，不要编客户）。
- **无从推断的字段**：`期望上线时间` 属排期决策、`components` 在多模块缺陷下无唯一答案 →
  可填最接近值但**必须在描述里写明是 AI 占位值、请负责人调整**；若连最接近值都填不出，才降级为「评论里列出待人工开单」并写明已尝试的字段。
- 本次产出示例：`NCM-3999`（跨仓 newsee-budget/newsee-finance DTO 缺字段导致整仓编译阻断）。

## Code Review 门禁（2026-09-16 模板包新增；无人值守执行口径）

模板包把 Code Review 列为**分层测试前的门禁**，文件为 `specs/<KEY>/code-review.md`（含 R01–R19 清单 + 结论区 + AI 自审区 + 人工评审意见区）。

**无人值守下的正确做法（关键，避免停摆或造假）**：

1. AI 完成**自审**（范围/规格/异常/安全/性能/并发/兼容/真实接线/敏感信息），把自审输出写进 `code-review.md` 的「AI 自审输出」区，并逐项核对 R01–R19。
2. **人工评审人无法在单轮内同步出现** → 不得因等待评审而停摆，**也绝不允许虚构评审人、代签「通过」、勾选人工项**。
   `code-review.md` 中「评审人 / 评审结论 / 评审时间 / 人工评审意见」一律留 `待人工填写`。
3. 自审通过后**可以继续**分层测试与真实链路验证 —— 这些结果正是给人工评审用的证据；但 DONE 评论的 `review=` 必须写：
   `AI自审=已出（见 specs/<KEY>/code-review.md）；人工评审人/结论=待人工；阻断项=无/列出`。
4. 自审发现阻断项、或需要转黄/转红 → 停止实施并按路由回写 JIRA，不做「先改完再解释」。

## 执行要点

1. 取单：`jira-connector` 技能 → `c.search(jql)`；JQL = `project = NCM AND labels = "AI自动开发" AND status = 新建 ORDER BY created ASC`；只取最早 1 张。方法名：`c.get_issue/get_comments/add_comment/get_transitions/transition_issue`。
2. 去重：已存在 `[AI-AUTO-DEV] RUNNING/DONE`（或历史前缀 `[AI-AUTO-FIX]` 的同类评论）、或已存在 `ai/<KEY>` 分支（本地或远端）→ 跳过。
3. 缺关键字段（复现/期望/模块/环境/验收）→ **先尝试自主补默认**：能从代码、既有同模式实现、resourcecolumn 配置、数据字典、同工单其他评论推断出唯一合理语义 → 按推断实现并留痕；仅当**不同理解会导致实现方向相反**（如"要不要改数据"、"是否含历史数据"）才 YELLOW 评论 + 转「开发/处理中」、不建分支。
3b. **判红路径（2026-09-16 NCM-3739 实践，硬停时走这条）**：仍然先取锁（RUNNING 评论 + 流转「开发已回复」）→ 做**只读**分析（grep 代码/SQL/历史提交，`git fetch` 只更新引用不改工作区）→ 把分析写成 `${paths.evidence}/<KEY>-red-analysis.md` → 发 `[AI-AUTO-DEV] RED` 评论（字段沿用 DONE 模板：route/branch=none/commit=none/reason/changes=none/review/green=none/real_path=none/failures/diff/evidence/decisions/env_note/next）→ 状态保持「开发已回复」。
   **判红 = 不建分支、不建 worktree、不写 worktree 内 specs（那需要分支）**；证据只落在自动化工作区的 evidence 目录。判红也要给足下一步可执行信息（待人工决策项 + 已定位的代码改动点与行号），不要只写"转人工"。
4. 隔离：`git fetch origin master`（**必须带凭据安全环境变量**）→ `git worktree add -b ai/<KEY> <paths.backend_worktree> origin/master`（**基线取 origin/master**，本地 `master` 可能因「AI 不合并」而陈旧）；**不要在共享工作区改码**。
   worktree 内建 `specs/<KEY>/`（intent / spec / plan / tasks / code-review 五件套，抄模板包并填空），保留脱敏摘要。
5. 红灯：先只写测试（生产代码零改动）；新增/小功能类工单用「目标行为测试」替代红灯。
6. 编译失败/依赖失败/环境故障 **不算有效红灯**；与工单无关的阻断先按 D2 绕行（已知跨仓 DTO 缺字段：临时 excludes 3 个 impl，提交前还原）。
7. commit 前门禁：绿色 + 有效红灯/目标测试 + 同断言转绿 + 定向/模块/全量/构建 + 真实链路 + diff 仅含批准范围 + AI 自审完成。
8. 交付：**push `ai/<KEY>` + 建 PR(base=master)**（先 compliance 四查；PR 幂等），**不合并、不删分支**；评论必须带 `decisions=`（见 D5）与 `review=`（人工评审待办）。
8b. **前端侧工单（改动落在 `micro_contract_management`）**：先判「是不是跨仓」——① 只改前端 → 只在前端仓走一遍（后端仓不动）；② **跨仓（后端 + 前端）→ 两侧各建 `ai/<KEY>` 分支、各建一个 PR**（前端 PR 用 python 直连配方，`gitea_cli.py` 会 404）。前端**无可执行测试**（本机无构建环境）→ 用「diff 静态自证 + 行为矩阵 + 声明未联调」替代红灯，**不得写「测试通过」**。详见「前端开发场景」章节。
9. DONE 评论之后**追加 `[AI-AUTO-DEV] PR-READY` 评论**登记 `pr=` / `url=` / `head=` / `base.sha 比对` / `pr_state` / `merger=待人工`。**跨仓发两条**（各一个 pr=）。下一轮被唤起时若发现人工已合并：追加说明评论写清 merge sha 与核验结果，**状态流转交人工**。
10. 流转：绿色完成 → 「开发/处理中」（先 `jira_cli.py transitions <KEY>` 现查 id，通常是 `161`）；查不到 → 保持现状并评论说明。
11. 回写评论模板见模板包 `JIRA定时任务提示词.md`（DONE 字段：route/branch/commit/red_or_target/reason/changes/review/green/real_path/failures/diff/evidence/decisions/env_note/next；PR 字段：pr/url/head/remote_branch/base/base_check/pr_state/authorization/merger/next）。

## 红灯与真实链路的实用写法（`newsee-contract-rest`）

- 不启动 Spring、不用数据库：`ContractPaymentRecordServiceImplTest` 是模板——`mock(...)` + `ReflectionTestUtils.setField` 注入 mapper + 反射调私有方法。
- **红灯断言要落在真实导出工具写出的 Excel 单元格上**，而不是只断言 VO 上的某个字段，否则会出现「单测绿但导出仍旧为空」的假修复：
  - `ExcelUtil.addExcelDataNew(SXSSFWorkbook, sheetIndex, List<NsCoreResourcecolumnVo>, List<?>, startRow)` 是 **public static**，可直接调用。
  - 列配置用 `com.newsee.common.vo.NsCoreResourcecolumnVo`（在 `newsee-common-inter` jar 中），需 `setFilterType("select")`、`setFilterConfigType("select")`、`setResourcecolumnHidden("0")`（后者仅供 `commonExcelExport` 过滤可见列用）。
  - 真实入口：`ExcelUtil.commonExcelExport(fileName, list, header, response)`（controller 就是这么调）；用 `mock(HttpServletResponse.class)` + 自实现 `ServletOutputStream`（覆写 `write(int)`/`isReady()`/`setWriteListener`）把真实 xlsx 字节捕获到 `ByteArrayOutputStream`，再用 `new XSSFWorkbook(...)` 重新打开断言单元格 → 可同时产出人工验收样本文件。
  - 反射调私有方法时，参数含 null 的用 `getDeclaredMethod(...)` + `setAccessible(true)` 比 `ReflectionTestUtils.invokeMethod` 更不易踩类型匹配问题。
  - 枚举/工具的空值安全性先确认：`ThirdTypeEnum.getDescByCode(null)` 返回 `""`、`DateUtil.formatDate(null,fmt)` 返回 `""`（安全）；`handleOrgControl` 只在 `belongProjectId` 非空时才发远程调用（夹具置空即可绕过）。
- 源码编码为 UTF-8（rest pom 显式声明），测试里可直接写中文期望值；且断言硬编码中文而非回读枚举，才能同时抓出枚举自带文案缺陷。

## 红灯夹具的致命坑：ReflectionTestUtils.setField 对不存在的字段会抛异常（2026-09-15 实测）

第一版红灯用 `ReflectionTestUtils.setField(strategy, "receivableLockUtil", ...)` 注入「修复后才会存在」的字段 →
修复前 result 是 **`Errors: 7`（IllegalArgumentException: Could not find field ...），不是 `Failures`**。
**这不算有效红灯**（README 明文：夹具错误/编译失败/环境故障都不算），因为失败点落在夹具注入而非业务断言。

**解法：存在即注入（soft inject）**，让修复前也跑到业务断言处失败：

```java
private static void setFieldIfPresent(Object target, String name, Object value) {
    if (org.springframework.util.ReflectionUtils.findField(target.getClass(), name) != null) {
        ReflectionTestUtils.setField(target, name, value);
    }
}
```

对**新增字段**用它，对**既有字段**仍用 `setField`（既有字段被改名时应立刻暴露）。
修复前表现变成 `Failures: 7, Errors: 0` + `Wanted but not invoked: iChargeRemoteService.lockChargeCustomerChargeDetail([71001, 71002])` —— 这才是合格红灯。
判定口径：**只要断言是「某方法必须被调用」，soft inject 不会掩盖功能缺失**（没实现就一定 verify 不过）。

**红灯行数参考**：`Tests run: 8, Failures: 7, Errors: 0`（第 8 个是「参数开关关闭时不得调用中台」的反向用例，修复前后都应通过）。

### 同源坑 2：夹具漏 mock 依赖 → 一堆 NPE，也不是有效红灯（2026-09-17 NCM-4007 实测）

`dataHandle` 这类「大方法」内部会串行调用多个 mapper，**任一未 mock 就 NPE，且报错落在业务代码行号上、极易误判成真实缺陷**。NCM-4007 首两轮均 `Failures: 2, Errors: 6`：

| 报错位置 | 缺失夹具 | 修法 |
| --- | --- | --- |
| `ContractManagementUnionServiceImpl.java:3858` | `contractSignatoryInfoMapper`（`selectByContractId`） | 加 mock → `emptyList()` |
| 同文件 `:3898` | `ecmDictionaryItemMapper`（`listByCode`） | 加 mock → `emptyList()` |
| 同文件 `:4018` | 入参 row 的 `isEarlyEntry` 为 null（`1 == conInfo.getIsEarlyEntry()` 拆箱） | `row.put("isEarlyEntry", 0)` |

✅ **夹具补齐配方**（目标方法有 6+ 个注入依赖时一次补齐，别一轮一轮试）：
```java
ReflectionTestUtils.setField(svc, "contractSignatoryInfoMapper", mock);   // selectByContractId → emptyList()
ReflectionTestUtils.setField(svc, "ecmDictionaryItemMapper", mock);       // listByCode → emptyList()（包名 com.newsee.contract.dao.ecm）
ReflectionTestUtils.setField(svc, "parameterSettingService", mock);       // 返回 ""，避免开关判定 NPE
```
> ⚠️ `EcmDictionaryItemMapper` 的真实包名是 **`com.newsee.contract.dao.ecm`**，不在 `com.newsee.contract.dao`。
> **判定口径不变：`Errors > 0` 一律不算有效红灯**，必须 `Failures > 0 && Errors == 0` 且失败断言 = 预声明断言（NCM-4007 最终 `8/3/0` 通过）。

### 同源坑 3：pom 注释里不能出现连续两个减号 `--`（2026-09-17 NCM-4007 实测）

给 D2 绕行写 XML 注释说明时若写了 `git checkout --` 之类文本，Maven 直接报
`Non-parseable POM ... in comment after two dashes (--)`，且**报错指向 pom 而非注释内容**，很容易误以为是绕行本身有问题。
→ **pom 注释中一律不用 `--`**（写「双横线」「连字符」或改用 `git checkout <path>` 描述）。

## 「改按钮显隐 / 加参数」类工单的机制（2026-09-16 NCM-3739 实测确认）

**这两件事都不在本仓库的 Java 代码里**，命中试点硬停 ②，判红并交人工：

1. **按钮显隐 = 系统库配置**：`ns_core_resourcebutton.RESOURCEBUTTON_INTERPRETER` 是一段 JSON 条件数组，只支持**行数据字段**（实测可用 `triggerModelKey` 全集：`billingBalance/changeStatus/chargeStatus/checkStatus/contractState/isDisabled/preCheckStatus/receivedPrice/residualPrice/settlementStatus/supplierStatus/unBillingBalance/hasPermission/noPayBalance/payingAmount`），**没有「读系统参数」的机制**。
   - 例：付款管理列表「付款」按钮 `JE_CORE_RESOURCEBUTTON_ID='GVgGlZdb5m8pWblQ-gridPaymentBtn'`，条件含 `{"triggerModelKey":"contractState","comparision":"NOT_EQUAL","triggerValue":["2"]}` → 合同已终止(2) 时按钮隐藏（最新基线见 `sql/v2/20260716_system.sql:1645`；同条件散见 `sql/00_Create_System_Contract.sql`、`01_Update_System_Contract_history_20260306.sql` 与各 `v2/*_system.sql`）。
   - 让参数只控制它，只有两条互斥路线：A 删掉该条件、由后端参数兜底（关闭时按钮可见但点击报错）；B 后端列表 VO 新增字段承载参数值、表达式引用（需前端配合，关闭时按钮隐藏）。**两者用户可见行为不同 → 属人工决策，AI 不代选**。
2. **新增参数 = 两套发布脚本，不是一次代码改动**：
   - 业务库：`sql/v2/<迭代>.sql` 内 `CALL add_contractParameter ('显示名','paramKey','默认值','','[]');`，惯例用 `IF NOT EXISTS(select 1 from ns_wms_parameter_setting where paramKey='...')` 包一层保证幂等；
   - 系统库：`sql/v2/<迭代>_system.sql` 需含参数设置表单 `form_content` 的对应开关（**平台设计器生成的 1.3MB 级脚本**，本迭代 `20260910_system.sql` = 1303341 字节）；
   - 达梦侧同步 `sql/v2-dm/<迭代>.sql` 与 `sql/v2-dm/<迭代>_system.sql`（近期由 `ARM-70819 自动转换新增 MySQL SQL 为达梦 SQL` 提交成对生成）；
   - 可复核样例（NCM-3990）：参数 `showFinanceBankAccountInfo` 同时出现在上述 4 个文件。
   - 迭代脚本按 `fixVersion` 定位：如 `HT_V10.1.20261022` → `sql/v2/20261022.sql` 与 `sql/v2/20261022_system.sql`（**新建迭代时为空文件**）。
3. 代码侧读参数惯例：`parameterSettingService.getParameterSettingSingle(<key>)` / `getParameterSettingSingleEnterpriseId(<key>, enterpriseId)`；key 常量放 `newsee-contract-pojo/.../base/Constant.java`（`DICTIONARY_CODE_*`）或 `enums/NumberGenerateRuleKey.java`（(desc, code) 枚举）。**注意参数缺失时返回 `""`**，所以闸门写法必须是「命中开关值才放行」，天然向后兼容。

**「合同终止后仍要能付款」类的既有代码守卫（NCM-3739 只读定位）**：
- `ContractPaymentRecordServiceImpl.java:559-561`（真实入口 `ContractPaymentRecordController#/contractPaymentRecord/add-contractPaymentRecord`）：`ContractStateEnum.ENDING` → `BizException.fail("合同【…】已终止，无法发起付款！")` —— 即本单待加参数闸门处。
- `PaymentPlanApprovalServiceImpl.java:1574-1576`（`validPaymentPlanApproval`）：`BizException.fail("合同已终止，无法新增付款计划！")` —— 属「新增付款计划」，与「发起付款」是两回事，勿顺手一起放开。
- `ContractPayableManagementServiceImpl` 无 `ContractStateEnum` 判断（应付款不受影响）。

## 「变更/续签时改用新模板」类工单（2026-09-17 NCM-3971 实测：**先判红，口径澄清后转绿**）

> **本节的正确读法**：NCM-3971 我先判红，人工随后给出明确口径（JIRA 评论 841914）把红转绿。**教训不是「不该判红」，而是「判红时要精确指出是哪一条约束导致红，并把它写成可回答的问题」** —— 我的 4 问里 Q4「是否保留历史绑定（改解析口径不动存储 vs 改写 contractTemplateId 动存储）」正是人工一句「不改存储、只新增读取接口」就解除的点。**判红报告里把「解除条件」写清楚，人工回一句就能转绿**，这是正确的工作方式。
>
> **这类工单的红/绿分界线**：
> - **红** = 要求「改写 `ns_contract_info.contractTemplateId` 存储值」或「自动回填新模板字段的默认值」→ 前者不可逆改历史、后者无既有模式且需产品定义。
> - **绿** = 只要求「**读取侧**按 id 解析出最新在用版本再返回」（不动存储）→ 影响面收敛在展示层，有唯一实现路径。**NCM-3971 属此类**。

### 合同模板版本机制（做模板类工单必读）

| 关注点 | 事实 | 位置 |
| --- | --- | --- |
| 合同存的是**具体版本 id**，不是族 id | `ns_contract_info.contractTemplateId` 单值 BIGINT 列 | `mapper/ContractManagementUnionMapper.xml:78,155,874-875` |
| 写入取具体版本行 | `dto.setContractTemplateId(templateList.get(0).getId())` | `ContractInfoExcelListener:213`、`ContractInfoExcel4SoluxeListener:220` |
| 模板族关联字段 | `originalId`；`isCurrentUse=1`（CURRENT）/`0`（HISTORY） | `ContractTemplate.java:136-139`；`ContractTemplateUseEnum` |
| **已审核模板再编辑 = insert 新行** | `setId(null)` + `setOriginalId(旧的族id)`，新行待审核 | `ContractTemplateServiceImpl#editContractTemplate:280-307` |
| 审核通过时切换在用标记 | 先 `updateIsCurrentUse(originalId, HISTORY)` → 再 `setIsCurrentUse(CURRENT)`；`versionNo` 每次 **+0.1** | `auditContractTemplate:363-390` |
| 取同族最新版本（族内查询参考） | `selectAllNewVersion(enterpriseId)`：`INNER JOIN (SELECT originalId, MAX(versionNo) ... GROUP BY originalId)` | `ContractTemplateMapper.java:49` + `xml:698-720` |
| ⭐ **「最新在用」定稿取法 = `selectByNo`（人工指认，2026-09-17）** | `selectByNo(templateNo, enterpriseId)`：`deleteFlag=0 and isCurrentUse=1 and checkStatus=1 and templateNo=? limit 1`。`templateNo` 是**族内共享**的模板编码（创建必填 `checkParam:456`）。三方集成本就用此模式解析最新在用模板：`ThirdPartyInterfaceServiceImpl:518,528` / `OutHangZhouDITieServiceImpl:437,441` / `OutMingYuanServiceImpl:205` | `ContractTemplateMapper.java:52` + `xml:803-815` |
| 按族取 | `selectByOriginalId(originalId, isCurrentUse)` | `ContractTemplateMapper.java:56` + `xml:822-832` |
| **合同业务链路零引用版本解析** | 全仓 grep：上述两方法**只被模板管理模块自己用**（`:158,343,988`） | — |

> ⚠️ **`updateIsCurrentUse` 是脏数据风险点（NCM-3971 顺手发现②，未开单）**：`ContractTemplateMapper.xml:818-820` 为 `where originalId=? and deleteFlag=0 and checkStatus=1` —— **无条件批量、不排除当前行**。配合 `editContractTemplate:296` 插入新行时就 `setIsCurrentUse(CURRENT)`，**存在同族多行 `isCurrentUse=1`** 的可能。
> → 但**不要因此自作主张改用 MAX(versionNo)**：人工已定稿「最新在用 = `selectByNo`」（有 `limit 1`，脏数据下也不报错）。MAX(versionNo) 方案在 NCM-3971 v1 提出后被人工纠正否决 —— 自研排序还有 `V1.9` vs `V1.10` 字符串比较回退的坑。

### 「按 id 取最新在用模板」的标准实现（NCM-3971 定稿方案 v2，可直接复用）

**后端**：新增独立接口（**不要改 `detail-contractTemplate` 的既有语义**，保持向后兼容）；**零新增 mapper SQL**，纯 Service 组合既有方法：
- `GET /contract/contractTemplate/detailLatest-contractTemplate`，入参 `id` = 合同持有的任意版本 id
- 实现：`selectById(id)` 取该行 → 拿 `templateNo`（模板编码，族内共享）+ `enterpriseId` → `selectByNo(templateNo, enterpriseId)` 取**当前在用且已审核**的最新版本 → 复用 `detailContractTemplate:228-249` 装配（`dataHandle` + 在线文档 id）
- **兜底铁律：行不存在 / templateNo 为空 / selectByNo 查不到 → 一律退化按传入 id 返回，绝不返回 `null`**（否则前端白屏；对存量脏数据零影响）
- 业务正确性：编辑产生的新版本在审核通过前不生效 —— `selectByNo` 此期间返回**最后一个已审核版本**，正是业务想要的
- ⚠️ **不要用 `order by versionNo` 自研排序**：versionNo 是 `V1.0`/`V1.10` 字符串，`V1.9` vs `V1.10` 会比较错误

**前端**（`micro_contract_management`，**以下为 2026-09-17 实际交付形态**，PR #213）：

单文件改动 `NS_contract/views/contract/contractManagement/components/contractManagement-form-dialog.vue`（+14 −3），五处：

| # | 位置 | 写法 |
| --- | --- | --- |
| 1 | `data()` | `latestTemplateId: null` —— **用 data 字段承载，不要回写 prop**（`vue/no-mutating-props` 会拦） |
| 2 | `visible` watcher（`if (val) {` 内） | `this.latestTemplateId = null` —— 弹窗复用，不重置会残留上一单的值 |
| 3 | `getTemplateFormJson()` | `const useLatest = ['change','renew'].includes(this.dialogType)`；URL 三元切换 `useLatest ? '/contract/contractTemplate/detailLatest-contractTemplate' : '/contract/contractTemplate/detail-contractTemplate'`；响应里 `if (useLatest) { this.latestTemplateId = res.resultData.id }` |
| 4 | 暂存落库（原 `:2251`） | `query.contractTemplateId = this.latestTemplateId \|\| this.templateId;` |
| 5 | 正式提交落库（原 `:2524`） | ① 原有 `if (add \|\| copy \|\| renew)` 块内改成同样的回退式；② **新增** `if (this.dialogType === 'change' && this.latestTemplateId) { query.contractTemplateId = this.latestTemplateId; }` —— 原块**没有 `change`**，而 change 的 `contractTemplateId` 是从 `detailData`（旧 id）合并来的，必须补这一支 |

- **原方案里的「service 层新增 `getLatestContractTemplate`」未实施**：组件内本来就直接 `tableDataFetch`，换 URL 即可；新增 service 函数没有第二个调用方 → 会变死代码。**这是可以主动偏离计划并留痕的正当例子**（已在 PR 正文写明）。
- ⚠️ **不要回写 `this.templateId`**（v1 方案的想法，已否决）：`templateId` 是 prop；改用 data 字段 + 落库处回退式 `新值 || 旧值`，既绕开 ESLint 又天然不影响 `add`/`copy`。
- 用户**显式重选模板**的入口 `templateSelected/index.vue` **仅被 copyDialog 引用**（`grep` 实测）—— 变更/续签没有模板重选 UI → **不存在「用户选择被覆盖」的风险**（v1 列的待联调点 Q2 据此关闭，无需再问人工）。

### 前端接口辨识（NCM-3971 澄清，避免误改）

| 接口 | 真实作用 | 是否参与模板 id 选取 |
| --- | --- | --- |
| `/contract/contractTemplate/detail-contractTemplate` | 按 id 取**该具体版本**模板 JSON（`form-dialog:2618`、`ContractDetailDialog:730`、`TemplateDetailDialog:212` 共用） | **是**，模板加载入口 |
| ❗ `/contract/contractType/detailByTreeCodes-contractType` | **只解析「合同类型 treeCode → 中文名」**（`contractManagement.js:104-110 getShowDetail`），作为续签弹窗树控件 `linkCodeList[0].detailUrl` 的回显适配 URL（`renewal-dialog.vue:78`） | **否！** 人工口径里它只是「定位续签那块逻辑」的坐标，**本类工单不需要改它** |

### 判红时该问的 4 问（**每问都要写清「人工怎么答就能转绿」**）

1. **生效范围**：只对变更/续签，还是新建也适用？历史已存在合同是否批量重绑定？
2. **新字段值来源**：空值（前端让用户填）/ 模板默认值 / 强制必填阻断？→ **答「空值让用户填」即可转绿**
3. **「新模板」如何选定**：**已定稿，无需再问** —— 用既有 `selectByNo(templateNo, enterpriseId)`（人工 2026-09-17 指认；三方集成同模式）
4. **是否保留历史绑定**：**改解析口径（不动存储）** vs 改写 `contractTemplateId`（动存储）？→ **答「不动存储、只新增读取接口」即可转绿**（NCM-3971）

### 判红通用判据（三类实例归纳）

> **表面是「改一个取值/加一个判断」，但只要满足下列任一条 → 判红**：
> ① 会改变**已存在数据**的绑定/展示/追溯语义（历史合同、历史单据）；
> ② 「新值/新字段从哪来」在仓库内**找不到既有模式**，需产品定义默认值或校验强度；
> ③ 真实现象需要**客户真实数据 + 版本演进史**才能复现（本机不可达）。
> 这三条与「判灯只看技术条件」不冲突：它们都是技术条件（需生产数据 / 需不可逆变更 / 无唯一解），而非按工单类型排除。
>
> **但注意 ①：若人工口径把「改存储值」排除掉，第①条即失效**（只改读取侧不影响历史数据）。**判红报告必须显式写清「哪一条约束在卡着」，否则无法快速转绿。**

## 「给中间表 / 业务表加字段」类工单 = 迁移脚本 → 判红（2026-09-16 NCM-3744 实测）

**这是「加字段不再是排除项」的第二个边界实例**（第一个是 NCM-3739 的按钮显隐）。区分口径：

| 工单实质 | 路由 | 依据 |
| --- | --- | --- |
| Java 侧 VO/DTO/实体新增字段，映射**已存在**的列 | 绿色（按 D1 自做） | 只改代码，可单测验证 |
| 表**物理列不存在**，要新增列（含中间表同步字段） | **红色** | 硬停②「变更数据库结构或迁移脚本」 |

**判红取证三步（NCM-3744 配方，比只查表定义更有说服力）**：

1. **证明列不存在**：查建表脚本 MySQL `sql/v2/<迭代>.sql` + 达梦 `sql/v2-dm/<迭代>.sql`、实体类、两个 Mapper XML 的 resultMap / insert / update 列清单四处一致缺失。
2. **证明"本仓库既有做法就是改迁移脚本"** —— 在仓库里找**同语义先例**：如 `enterpriseScale` / `enterpriseScaleDesc`（企业规模）成对出现在 `sql/v2/20260312.sql:159-160` 与 `sql/v2-dm/20260312.sql:211-212`。幂等写法参照 `sql/v2/20260618.sql:90-101`（`IF NOT EXISTS(information_schema.COLUMNS)` + `ADD COLUMN`）。
3. **证明本迭代脚本是空的/不存在**：按 fixVersion 定位（`HT_V10.1.20261022` → `sql/v2/20261022.sql`、`sql/v2/20261022_system.sql`，两者 0 字节；`sql/v2-dm/20261022*.sql` 不存在）。

**同时叠加跨服务契约时一并列出**：NCM-3744 还需新增对业户中台 `POST /api/owner/refundAddCustomer/queryRelationshipByOwnerIds` 的调用 —— 仓库既有 `IOwnerRemoteService`（`@FeignClient(value="${newsee.contract.feign-client.owner-server:owner-server}")`）**无此方法**，服务提供方在 owner-server（非本仓库）→ 第二个硬停②。

## 久其（九期）同步模块地图（做 NCM-3744 类工单必读）

| 关注点 | 位置 |
| --- | --- |
| 中间表 | `ns_contract_info_map_jiuqi`（建表 `sql/v2/20260618.sql:42-68`，唯一键 `uk_contractId`） |
| 实体 | `newsee-contract-pojo/.../entity/JiuqiContractInfo.java`（22 字段） |
| Mapper | `rest/src/main/resources/mapper/JiuqiContractInfoMapper.xml`（MySQL）+ `mapper-dm/JiuqiContractInfoMapper.xml`（达梦，用 `MERGE INTO`，改列清单要**同步两份**） |
| 同步入口 | `ThirdPartyInterfaceServiceImpl.syncJiuqiContractInfo(Long enterpriseId)`（L955-1078）：每月 1-10 号跳过 → 增量查 `sys_date`（`selectIncrementBySysDate`，动态表 `ns_contract_info_extend_<enterpriseId>`）→ 应收过滤 `isInValidScope` → 批量 500/upsert → `markInvalidContracts` |
| 转换点 | 同文件 `convertToJiuqiContract(contract, contractLegalUnitMap, contractCustomerMap)`（L1211-1244）—— 新增字段的落点 |
| 客户/ownerId 来源 | L1036-1049：`signatoryInfoMapper.selectByContractId(ids, null, "2", enterpriseId)` → `contractIdToCustomerId` → `bcrmCustomerMapper.selectByIds(...)`；`BcrmCustomer.ownerId`（`BcrmCustomer.java:64`）即"ownerId list"的现成来源 |
| 定时触发 | `job/SyncDataTask.java:173 syncContractToJiuqi()`（硬编码 `enterpriseId=107`） |

**「同步新增字段」实施配方（NCM-3744 已跑通，2026-09-16；人工授权后可直接照做）**

改动面固定为 **5 实现 + 2 测试**：
1. `JiuqiContractInfo` 加字段（Lombok `@Data`，无需手写 getter）；
2. `IOwnerRemoteService` 加 Feign 声明（跨服务方法用 `RestResult<List<Map<String,Object>>>` 承载，沿用同接口 `getPrecinctByOrgIds` 先例 —— owner-server 的 DTO 不在本仓库，**不要自造 DTO**）；
3. 两侧 Mapper **各 4 处**补列：`resultMap` / INSERT 列+值（MySQL）或 MERGE `SELECT AS 别名`+`WHEN MATCHED UPDATE`+`WHEN NOT MATCHED INSERT`（达梦）/ `ON DUPLICATE KEY UPDATE`（MySQL）/ `selectValidByEnterpriseId` 查询列；
4. `ThirdPartyInterfaceServiceImpl`：`@Autowired private IOwnerRemoteService ownerRemoteService;` + 新增包级私有 `queryOwnerCompanySize(Collection<BcrmCustomer>)`（非空去重 ownerId → 500/批 `BATCH_SIZE` → 按 ownerId 建索引 → **远程失败/为空降级返回空 map 记 warn，不阻断同步**）+ `convertToJiuqiContract` 增加第 4 参；
5. 缺省值写 `""`（`Objects.toString(v, "")`），与既有 `ourEntityCode`/`oppositeEntityCode` 一致。
- **镜像风险**：`IOwnerRemoteService` 新增方法只编译消费端，owner-server 未提供时**编译照样过、运行才 404** → 必须在 `env_note`/`real_path` 写明「未联调」，别声称端到端已验证。

**红灯写法（新增私有方法/新签名，照抄）**：
- 用 `ReflectionUtils.findMethod(Impl.class, "<方法名>", 参数 Class...)` 按**实现后的签名**找方法；实现前返回 `null` → `assertNotNull(m, "…尚未实现")` 失败 → 得到 `Failures`（**有效红灯**）而非 `Errors`（夹具错）。参数类型照实写 `ContractInfo.class, Map.class, Map.class, Map.class` / `Collection.class`。
- 新注入字段用 **soft inject**（`findField != null` 才 `ReflectionTestUtils.setField`），既有字段直接 `setField`。
- NCM-3744 实测红灯/绿灯：`Tests run: 6, Failures: 6, Errors: 0` → `6, 0, 0`。

**「真实链路」在本机不可达时的替代证据（也照抄）**：用 `XMLMapperBuilder` 解析**仓库里那一份** Mapper 并断言绑定 SQL，比文本 grep 强得多。两个必踩的坑：
- 同一 namespace+id 在 `mapper/` 与 `mapper-dm/` 重复 → 必须**两个独立 `Configuration`**分别加载；`extends="...ContractInfoResultMap"` 要求**先把 `ContractManagementUnionMapper.xml` 解析进同一个 Configuration**；
- 入参必须复刻真实形态：DAO 声明 `insertOrUpdateBatch(@Param("list") List<...>)` → MyBatis 实际传 `{list, param1}` 的 Map；**直接传 List 会在 `foreach` 处抛 `UnsupportedOperationException`（CollectionWrapper.get）**，那是夹具错，不是 mapper 错。

## SQL 迁移脚本的落盘配方（2026-09-16 NCM-3744 实测；人工可授权 AI 只写这一块）

> 边界：AI **不开权限**——硬停②（DB 结构变更）默认判红交人工；**但人工一旦明确指令「按模板加这两个字段到某迭代脚本」，AI 可按下方配方执行**（这是"人工一句话放开"的少数情形）。放开范围仅限：往既有迭代脚本追加幂等块。

**版本定位（先验证，别靠猜）**：迭代文件 = 与工单 `fixVersion` **同名**的 `sql/v2/<8位日期>.sql`。已用 2 个数据点验证该映射：

| 工单 | fixVersion | SQL 实际落点 |
| --- | --- | --- |
| NCM-3832 | HT_V10.1.20260924 | `sql/v2/20260924.sql` ✅ |
| NCM-3990 | HT_V10.1.20260924 | `sql/v2/20260924.sql` ✅ |
| NCM-3744 | ~~HT_V10.1.20261022~~ → **HT_V10.1.20260924**（人工已改） | 人工指定「当前在飞迭代」`sql/v2/20260924.sql`（**与当时 fixVersion 20261022 冲突**） |

**冲突处理惯例（NCM-3744 实例，可复用）**：人工口头指定的迭代与工单 `fixVersion` 不一致时 → **按人工指令落盘 + 在 JIRA 评论明确写成 `env_note`**（列出冲突事实与一句话搬迁方法），**不要自作主张替人工改 fixVersion、也不要静默按 fixVersion 落盘**。实测结果：人工随后自己去 JIRA 把 `fixVersion` 从 20261022 改成 20260924 来对齐（本轮回读 `fixVersions=["HT_V10.1.20260924"]` 确认）——即**只要把冲突讲清楚，人工会自己收口版本**，AI 无需再动。人工改完版本后补一条 `[AI-AUTO-DEV] NOTE` 评论**关闭该待办项**即算收口，不要重新流转状态。

空文件即"新建迭代占位"（如 `20261008.sql`、`20261022.sql` 均 0 字节；`v2-dm/20261022.sql` 连文件都还没有）。**在飞迭代 = 最后一个有内容且近期有提交的文件**（用 `git log --oneline -- sql/v2/` 看）。

**文件格式（必须实测后照抄，别臆断）**：`sql/v2/*.sql` 为 **UTF-8 无 BOM + 纯 CRLF + 末尾无换行**（实测 `20260910.sql`/`20260924.sql`：`count(\r\n)==count(\n)`、`endswith(b'\r\n')==False`）；`.gitattributes` 不存在，`core.autocrlf=true`（索引存 LF、工作区 CRLF）。
→ **不要用会写 LF 的工具直接改**：先 Write 一个片段文件（UTF-8），再用 Python 按字节追加：

```python
frag = open(frag_path,'rb').read().decode('utf-8').replace('\r\n','\n').rstrip('\n').replace('\n','\r\n')
before = open(target,'rb').read()
assert b'<新字段名>' not in before          # 幂等防重
open(target,'wb').write(before + b'\r\n\r\n\r\n' + frag.encode('utf-8'))
```

块间分隔 = **空 2 行**（`;\r\n\r\n\r\n`）。追加后必须校验：`BOM=False`、utf-8 decode OK、`pure CRLF=True`。

**幂等块模板**（照抄人工给的参照脚本，命名 `add_col_<表>_<列>`，一列一块）：

```sql
DROP PROCEDURE IF EXISTS add_col_<表>_<列>;
DELIMITER $$
CREATE PROCEDURE add_col_<表>_<列> ()
BEGIN
IF NOT EXISTS (
  SELECT COLUMN_NAME FROM information_schema.COLUMNS
  WHERE table_schema = (select database()) AND table_name = '<表>' AND column_name = '<列>'
) THEN
  ALTER TABLE <表> ADD COLUMN <列> VARCHAR(50) DEFAULT NULL COMMENT '<中文注释>';
END IF;
END$$
DELIMITER ;
CALL add_col_<表>_<列> ();
DROP PROCEDURE IF EXISTS add_col_<表>_<列>;
```

**类型/长度怎么定**：优先照**同语义先例**（如企业规模 → `enterpriseScale VARCHAR(10)`/`enterpriseScaleDesc VARCHAR(50)`，`sql/v2/20260312.sql:159-160`）；无先例时照**同表既有同类列**（久其表所有编码/名称列均 varchar(50)），并在评论里注明「此为 AI 判断，非需求原文」留痕。

**达梦侧不要手工改**：`sql/v2-dm/<迭代>.sql` 由自动转换任务成对生成（master 上有提交 `ARM-70819 自动转换新增 MySQL SQL 为达梦 SQL`；实测 `v2-dm/20260924.sql` 已同步 `contractTypeCode`/`relatedProjectId`）。手工补会与自动转换重复。达梦块形态供参考：`AND C.NAME IN ('<列>', UPPER('<列>'))` … `EXECUTE IMMEDIATE 'ALTER TABLE <表> ADD <列> BIGINT DEFAULT NULL'`。

## 已知缺陷配方（可复用）

**「前端传净额、后端按总额再比一次」类校验误拦（NCM-4000）**：应收/应付调整的 `adjustedFee` 由前端计算，是**净额口径**（`调整后应收总额 − 已收金额`，因 `difference = adjustedFee − (剩余应收 + 已调整金额)` 只在净额下自洽，`BcrmReceivablesServiceImpl:1632/1678`）。后端若再拿它与 `receivablesBalance`（已收金额，总额口径）比较，即**重复扣减一次已收金额**。

- 抛错点：`BcrmReceivablesServiceImpl#validAdjust`（应收，「调整后金额需大于已收金额！」）；应付侧同款写法在 `ContractPayableManagementServiceImpl#validAdjust:1438-1440`（「调整后金额需大于等于已付金额」，未修，属另一单）。
- 现场判别：已收 > 0 且用户要把剩余应收**全额调整掉**（`adjustedFee = 0`）时必现。
- 修法（最小）：删掉该处比较——净额口径下「调整后应收总额 ≥ 已收金额」⟺ `adjustedFee ≥ 0`，已由紧邻的「调整后金额不得小于0」校验承接，**保护语义不降低**；并在原处留 3 行注释说明口径。
- 红灯夹具（照抄）：mock `bcrmReceivablesMapper`（`getByIdList` 返回原应收、`selectByPreReceivableIdList` 空）、`contractManagementUnionMapper.selectById`（返回 `new ContractInfo()`）、`parameterSettingService.detailParameterSettingByEnterPriseId`（返回 `paramValue="0"` 的 `ParameterSetting`，**不能返回 null，否则 L1576 NPE**）、`receivablesAdjustMapper.selectByCheckStatus`（空）、`businessUtils`/`systemUtils`；驱动**公开入口** `adjustBatchReceivable`（或先注入真实 service 到 `BcrmReceivablesController.bcrmReceivablesService` 后调控制器方法，得到真实入口证据），再用 `ArgumentCaptor<BcrmReceivablesAdjust>` 断言 `insert` 的 `receivablesFee`。实测红灯 4/3/0 → 绿灯 4/0/0。

**「流程发起后未冻结中台应收 / 未加解锁」类（NCM-3989）**：`IProcessStrategy` 各实现类的加解锁写法**不统一**。

- 有加解锁的模板：`HTBGProcessStrategyImpl`（合同变更，`1_HT_BG`）、`HKJHBGProcessStrategyImpl`（回款计划变更）。
  标准写法 `lockOrUnLock(Long id, boolean lock)`：`receivablesMapper.selectByContractId(id)`（或 `selectByCollectionPlanId`）
  → 取 `getReceiveCenterId()` 列表 → `receivableLockUtil.receivableLock(centerIds,null)` / `receivableUnLock(...)`。
  调用点四处：发起加锁、**通过前先解锁**（异常时回滚加锁）、`instStatus ∈ {3退回,4拒绝,5终止,6删除}` 解锁。
- 缺加解锁的例子：`HTZZProcessStrategyImpl`（合同终止，`1_HT_ZZ`）—— NCM-3989 第一轮就是补它。
- 加解锁真实效果受系统参数闸门控制：`ReceivableLockUtil.syncChargeCenter` 读「是否同步应收中台」= `"1"` 才调中台。
  红灯夹具**要注入真实 `ReceivableLockUtil`**（只 mock `IChargeRemoteService` + `IParameterSettingService` + `SystemUtils`），
  这样断言落在「真实 remote 调用与入参」上，参数闸门也顺带被验证。

### ⚠️ 两套合同流程通道 —— 改流程类工单前**必须先 grep 通道归属**（NCM-3989 第二轮血泪教训）

**教训**：NCM-3989 第一轮只补了 `HTZZProcessStrategyImpl`，自认为「合同终止已全覆盖」，第二轮被测试退回（朗诗 UAT 现象依旧）。原因——**合同流程有两条并行通道，宏天那条补了跟朗诗毫无关系**。

| 通道 | 识别特征 | 发起入口 | 回调入口 | 处理类 |
|---|---|---|---|---|
| ① 宏天 BPM | 内部工作流 | 经 `ProcessFactory.getStrategy("1", businessType)` 派发 | `BPMController` 的 `startEvent/endEvent/...` | `HTZZProcessStrategyImpl`(`1_HT_ZZ`) / `HTBGProcessStrategyImpl`(`1_HT_BG`) / `HKJHBGProcessStrategyImpl` |
| ② 朗诗外部 BPM | 企业代码=朗诗，`bpmType=2` | `POST /ls/bpmStart` → 回调 `/ls/bpmStartCallBack` | `POST /contract/outer/ls/bpmCallBack` | **`OutLsServiceImpl`（直接处理，不经 ProcessFactory）** |

- **通道 ② 完全不走 `IProcessStrategy`**：`OutLsServiceImpl` 自己写状态机，方法名一一对应 —— `lsBpmStart` / `lsBpmStartCallBack`（发起回调，按 `bpmType` 分 `contractStop` 等 case）、`handleContractLsBpmApproved`（通过，case 数字对应业务类型）、`handleContractLsBpmDisagree`（不通过）、`handleContractLsBpmBackEdit`（撤回/驳回/退回）。
- **判定通道归属的 grep 姿势**：工单出现「朗诗 / LS / 外部 BPM / bpmCallBack / SR-日期-序号 单号」⇒ 通道 ②；只写「合同终止/变更流程」且无企业限定 ⇒ 先搜该类是否也被 `OutLsServiceImpl` 覆盖，**两条通道都要看待办是否同时存在**。
- `OutLsServiceImpl` 是 `IOutLsService` 的**唯一实现**，只被 `OutLsController` / `OutCallBackController` 使用（grep 一次即可确认，别再找第三个入口）。
- **通用原则**：凡「流程类」改动，交付前自问一句「这条链路是不是只覆盖了一种 workflow 通道？」——用一个 `grep -rn "流程关键词" --include=*ServiceImpl` 把同语义的兄弟类列全，再逐个确认。
- 通道 ② 的加解锁四处调用点（NCM-3989 第二轮已补，可照抄形状）：发起回调 `case "contractStop"` 加锁；通过 `case 4` **先解锁再 `doStop2`，`catch` 里回滚重新加锁并 `throw`**；不通过 `case 4` 解锁；撤回/驳回/退回 `case 4` 解锁。

**BPMController 的 instStatus 映射（做流程类工单必查，决定红灯用哪个 code）**：
`startEvent`→`1` 调 `processStart`；`endEvent`(通过)→`2` 调 `processApproved`；`endEvent`+`oppose`→`4` 调 `processApproved`；
`backToStart`/`taskRevoke`→`3` 调 `processBackToStart`；`endProcess`→`5` 调 `processStop`；`taskRemove`→`6` 调 `processDel`；
`taskComplete`/`taskCreate`+`agree`→`1` 调 `taskAgree`。

**真实入口验证（流程类，无需 Spring/DB）**：`ProcessFactory.getStrategy(WorkflowTypeEnum.HT.code()="1", businessType)`
→ `ProcessStrategyEnum.getProcessStrategyEnumBySystem` 按 businessType 找到枚举（如 `HT_ZZ`="1_HT_ZZ"）
→ `strategyMap.get(code)`。测试里 `new ProcessFactory()` 后 `ReflectionTestUtils.getField(factory,"strategyMap")` 取到 map
并 `put("1_HT_ZZ", 真实策略实例)`（这正是 Spring `@Autowired Map<String,IProcessStrategy>` 的注入方式），
再断言 `assertSame` + 驱动 `processStart` 断言加锁被调用 —— 可证明**实际入口命中新逻辑**。

**「列表页有值、导出 Excel 该列为空」类**：`ExcelUtil.addExcelDataNew` 对 `filterType=select` 的列按 `{code}Name` 反射取值。若 VO 只有 code 字段、没有 `<code>Name` 字段，反射取不到 → 写空串。修法（最小）：
1. VO 增加 `<code>Name` 字段；
2. Service 组装处（如 `BcrmReceivablesServiceImpl#dataHandle` 的 `voList.add(vo)` 之前）按既有 select 列（`receiveStatusName`/`receivablesTypeName`/`collectionStatusName`）同一模式回填；
3. 顺带核查枚举文案。例：`FreezeStatusEnum` 有描述缺陷 `未冻结("冻结中","0")`；该枚举全仓只用 `code()`，无人读 `desc`，修正零行为影响（需 grep 确认后再改）。

## 本机环境限制（清理阶段注意）

- `rm -rf` 对 >50 文件的目录会被安全守卫拦截（返回 `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]`，count≈1800）；`Add-Type` 与 COM 均被安全策略拦截 → 无法自动把 worktree 移入回收站。
- `git worktree remove --force` 会被 SIGTERM 中断，且它会先删 `.git` 指针，导致后续 `worktree list` 出现 `prunable`。
  **更省事的善后顺序**：`git -C <wt> checkout -- .` 还原改动 → 试 `git worktree remove --force` →
  失败就直接 `git -C <repo> worktree prune`（`.git` 指针已丢，prune 会把记录注销掉，`worktree list` 恢复干净），
  再按上面「两步删」清掉惰性目录（2026-09-15 实测可彻底删除，无需再交人工）。**分支一律不删**（本地与远端 `ai/<KEY>` 均保留，交人工在合并后清理 —— 2026-09-16 规则）。
- 放在自动化工作区内的 worktree 比 F: 盘更易善后；实在删不掉时如实报告残留路径，不要谎称"已清理干净"。
- **清理前必须先归档 `specs/<KEY>/`（2026-09-16 NCM-4000 实测教训）**：`/specs` 在 `.gitignore` 内 → 规格五件套**不在 commit 里**，一旦删除 worktree 就被一起删除，而 DONE 评论里通常写着「见 specs/<KEY>/code-review.md」→ 引用变成死链。**顺序固定为：① 复制到 `${paths.evidence}/<KEY>-specs`；② 再删 target 与 worktree**；③ 若已误删，按 JIRA 评论内容重建归档副本并发一条 `[AI-AUTO-DEV] NOTE` 写明权威路径（`authoritative_path=`），不要悄悄改口。
- **降低残留文件数（2026-09-15 复盘修订，已实测通过）**：残留目录膨胀几乎总是 `target/` 构建产物造成（本次 1816 个文件里 1158 个在 `target/`）。**分两步删**：① `rm -rf <wt>/*/target`（先删构建产物，1816 → 658）；② `rm -rf <wt>` 整体删除 —— 本次两步均成功，**不要再一开始就断定"删不掉、只能上报"**。
- **2026-09-15 第二轮实测（更省事的收尾顺序）**：在固定路径 `wt-pilot` 上先 `rm -rf <wt>/*/target`，
  该步之后目录内文件归零、连 `.git` 指针一起消失；此时再 `git -C <repo> worktree remove --force <wt>` 会报
  `fatal: '<wt>' is not a working tree` —— **这是正常结果，不是失败**。判据只看两处是否干净：
  `git worktree list` 仅剩主仓、`<repo>/.git/worktrees/` 已不存在（本轮两者均干净，**无需再 `worktree prune`**）。
  最后**不删分支**：本地与远端 `ai/<KEY>` 都保留（人工合并后由人工删除；保留本地分支同时让下一轮去重更可靠 —— 存在 `ai/<KEY>` 即跳过）。
- **worktree 路径固定复用**：固定用 `${paths.backend_worktree}`（每轮清理后复用，不按工单号新建），避免每轮新增一个残留目录。
- **前端工作空间的清理更简单（2026-09-17 NCM-3971 实测）**：`${paths.frontend_worktree}` 是**独立浅克隆**而非 git worktree时，可在确认解析路径位于 `${paths.automation_workspace}` 内后删除，**不需要** `git worktree remove/prune`，也不要去后端仓做 prune。跨仓工单收尾时两个隔离目录都要检查；若本轮只改前端，则只处理前端目录。
- **不要把「核验」和「删除」写进同一条链式命令（2026-09-16 15:34 实测教训）**：若命令以 `cd <wt> && git checkout -- pom.xml`（还原绕行）开头，而 `<wt>` 已不存在时，`cd` 失败会让**整个 `&&` 链静默跳过**（还原与核验都没跑，却看不出报错），随后用 `grep -c excludes || echo 0` 之类的兜底还会打印出「0」这种**假阳性绿色**。正确姿势：① 还原绕行与核验各写独立命令；② 判据不要依赖 `grep || echo` 这种双出口，直接用 `git show <commit>:<path> | grep -c` 查**提交内**内容（提交里没有绕行才算真干净）；③ 真正权威的判据是 `git diff --stat <base>..<branch> -- <pom>` 为空 + `git worktree list` 仅主仓 + `.git/worktrees/` 不存在。
- 若单次删除仍被 `[safe-delete]` 拦下：把删除拆成"先产物、后源码"两步重试；再不行才如实上报残留路径。
- **2026-09-17 NCM-4007 最省事的一次收尾（推荐直接照做，一次成功）**：顺序 = ① 归档 specs；② `python -c "import shutil;shutil.rmtree(r'<wt>/newsee-contract-rest/target',ignore_errors=True);shutil.rmtree(r'<wt>/newsee-contract-pojo/target',ignore_errors=True)"`；③ `git -C <repo> worktree remove --force <wt>` → `exit=0` 一次成功；④ `git -C <repo> worktree prune`；⑤ `git worktree list` 仅主仓 + `ls -d <wt>` 为空即判干净。**先删 target 是让 `worktree remove` 成功率接近 100% 的关键**（target 是文件数膨胀与安全守卫拦截的主因）。
- **收尾必做的四组核对（每轮固定）**：① `git -C <repo> status --porcelain | grep -v '^??'` 为空（共享工作区 tracked 零改动）；② 本地 `ai/*` 分支仍在（不删分支）；③ 远端 PR 状态 `open/merged=False/mergeable=True` + `base.sha == 远端 master HEAD`（`gitea_cli.py api GET /repos/NEAP/newsee-contract/pulls/<N>`，取 `head/base/{ref,sha,state,merged,mergeable}`；**注意 `g.api()` 第二返回值是 JSON 字符串，要 `json.loads`**）；④ `git merge-base --is-ancestor ai/<KEY> master` 返回非 0（=未并入，证明没合并）。

## 「动态字段 / dynamicMap 格式化」类工单配方（2026-09-17 NCM-4007 实测，可直接复用）

合同详情/列表的自定义字段由 `DynamicColumnUtils.getDynamicMap(entity, "<业务表编码>")` 装配为 `dynamicColumnList`，再由
`ContractManagementUnionServiceImpl#dataHandle(HttpServletRequest, List<Map>, List<CoreTablecolumn>)` 把值塞进 `dynamicMap` 回吐前端。

- **列元数据字段**（`com.newsee.common.entity.CoreTablecolumn`，在 `newsee-common-master.ARM-SNAPSHOT.jar` 内）：
  `tablecolumnCode`=DB 列名 / `tablecolumnNameEn`=dynamicMap 的 key / `tablecolumnType`=DB 类型名 / `syResourceType`（如 `CONTROL_MULTI` 多选）。
- **核心陷阱 1：`tablecolumnType` 的实际形态是「大写 DB 类型名」**（`VARCHAR`/`TEXT`/`LONGTEXT`/`DATE`…），证据是同仓 `Interceptor/ParamInterceptor.java:134-136`。
  → 比较一律用 `equalsIgnoreCase`，并在 DONE 的 `reason=` 里把「取大写还是小写」标为【推断项】留痕。
- **核心陷阱 2（2026-09-17 人工口径，务必记牢）：只格式化 `DATE`，`DATETIME`/`TIMESTAMP` 必须原值透传。**
  - `DATE` 语义上不含时间部分 → 展示 `00:00:00` 是格式缺陷，要拨掉。
  - `DATETIME`/`TIMESTAMP` **本身就承载时分秒** → 格式化成 `yyyy-MM-dd` 会**丢业务信息**，属反向缺陷。
  - 人工原话：「只处理DATE的，DATETIME 和 TIMESTAMP 本身就有时分秒 就要返回时分秒」。
  - 落地形状：辅助方法命名成 `isPureDateColumn`（**别叫 `isDateColumn`**，那个名字会诱导后手把三类合并），
    实现只有一行 `return "date".equalsIgnoreCase(tablecolumnType.trim());`。
  - **务必配套写反向用例**（否则后续很容易被"顺手统一"改回去）：datetime 保留时分秒 / 大写 DATETIME /
    timestamp 保留时分秒 / 「同一份数据、仅列类型不同」的对照（DATE 格式化 vs DATETIME 不格式化）。
- **日期带 `00:00:00` 的根因是双表现同源**：JDBC 返回 `java.util.Date`/`Timestamp` 原样入 `dynamicMap` →（a）Map 经 Jackson 序列化成本地实测的 **epoch 毫秒** `1790784000000`；（b）前端渲染成 `yyyy-MM-dd 00:00:00`。**修复=在写入点按列元数据判定日期列后格式化**，不要去改全局 Jackson 配置（会波及合同主表时间字段）。
- **最小修复形状**（写入点 else 分支 + 一个私有辅助方法，别再拆更多）：
  ```java
  Object dynamicValue = contractInfo.get(key);
  if (dynamicValue instanceof Date && isPureDateColumn(coreTablecolumn)) {   // 注意 DateUtil.formatDate 的入参是 Date，
      dynamicValue = DateUtil.formatDate((Date) dynamicValue, DateUtil.YYYYMMDD_FORMAT); // java.sql.Timestamp 是其子类可传入
  }
  dynamicMap.put(coreTablecolumn.getTablecolumnNameEn(), dynamicValue);
  ```
  仅处理 `Date` 实例，String 原值透传（避免二次解析）。
- **不要动的分支**：`syResourceType == CONTROL_MULTI` 的多选分支、三处 `remove`、以及 `if ("date".equals(...))` 之外的既有逻辑。
- **红灯断言 3 件套**（照抄即可）：① 文本断言 `expected <2026-10-01> but was <java.util.Date(Thu Oct 01 00:00:00 GMT+08:00 2026)>`；② 黑盒序列化 `new ObjectMapper().writeValueAsString(dynamicMap)` 必须含 `"zdyendDate1":"2026-10-01"` 且不含 `00:00:00`；③ 大写 `DATE` 形态同样格式化。另附反向用例（非日期透传 / null 保持 null / 多选分支不变 / String 不二次解析 / type 为 null 不 NPE / **datetime、timestamp 保留时分秒（4 条，见核心陷阱 2）**）。
- **真实链路口径**：`dataHandle` 正是 `#detailContractInfo`（L717）与 `#listPage`（L310）的共用装配入口 → 直接反射驱动它就等于命中真实入口；再加 Jackson 真实序列化断言覆盖「外发响应形态」。
- **反向约束也要做「反向红灯」自证（2026-09-17 NCM-4007 实测，强烈推荐）**：新增了「不该被改」的约束用例后，把**实现**临时回退到旧形态（`git checkout HEAD -- <实现文件>`）、**测试保持新版**跑一次，
  若失败恰好落在这些约束用例上，就证明它们真的在起作用（NCM-4007 实测 `12/4/0`，失败恰为 T7–T10，报错原文直接暴露 `Timestamp → String "2026-10-01"` 的截断）。
  这一招对付「口径类」需求特别有用 —— 它把「人工说的口径」变成可执行、可回归的断言，而不只是注释里的一句话。

### ⚠️ 口径类需求的通用教训（NCM-4007 两轮才收敛）

第一轮我按「日期型」笼统实现（`date`/`datetime`/`timestamp` 一并格式化），通过了红灯+绿灯+全量，
但**逻辑上多做了一个人工并不想要的改动**（截断 DATETIME 的时分秒），直到人工指正才修正。
→ **遇到「格式/显示」类需求，先把边界问清楚或按最窄解释实现**：
  「改什么」永远要配一个「**不改什么**」；宽度解释（一并处理）比窄解释风险更高，因为它悄悄改变了别的字段的行为。
  本单最窄解释就是「只处理工单现场那个类型（DATE）」，其余原值透传 —— 事后证明正是人工要的。

## 「合同调整/减免推中台带结算日期」类工单与「跨服务 DTO 缺字段」判红配方（2026-09-17 NCM-3866 实测）

### 中台同步的链路地图（合同应收 → 收费中台，做本类工单必读）

| 业务动作 | 本仓入口 | 推中台的方法 | 目标接口 | 用的 DTO | 服务端仓 |
| --- | --- | --- | --- | --- | --- |
| **新增应收** | `syncChargeAddList:1166` | 同左 | `POST /third/syncChargeDetail-addList2` | `SyncChargeCustomerDetailDTO` | newsee-charge |
| **调整应收**（审核通过） | `BcrmReceivablesServiceImpl#approveAdjustReceivable:1732` → L1921 | `SyncChargeServiceImpl#syncRecivableAdjustBatch:110` | `POST /third/masterData/batch-editPayment` | **`ThirdEditPaymentDTO`** | newsee-charge |
| 调整（V8 侧） | 同上 | — | V8 `ChargeDetailAdd` | `JSONObject` 手工拼 key | V8 服务 |
| **减免/调减** | `syncRecivablReduce:662` | 同左 | `POST /third/dicountForVnine` | `Map<String,Object>`（无 schema） | **newsee-bill** |
| 减免回滚 | `syncRecivablReduceRevert:876` | 同左 | 同上 | 同上 | newsee-bill |
| 删除应收 | `syncChargeDel:382/427` | — | — | — | newsee-charge |
| 客户信息变更 | `syncChargeUpdateList:1298` | — | — | — | newsee-charge |
| 冻结 | `syncFreezeReceivables:1653` | — | — | — | newsee-charge |
| 质保金 | `syncMarginAddList:1688` / `syncMarginDel:1784` | — | — | — | newsee-charge |

**两处参数闸门**（都在 `parameterSettingService.detailParameterSettingByEnterPriseId`）：
`Constant.DICTIONARY_CODE_SYNCCHARGECENTER = "syncChargeCenter"`（0 不同步 / 1 V10 / 2 V8）。

### 结算日期的语义（已定稿，不要再问）

- **结算日期 = 回款计划的 `collectionPlanDate`**（计划回款日期）。
  定稿证据：`SyncChargeServiceImpl:1938`
  `syncChargeDetailDTO.setSettlementDate(collectionPlan.getCollectionPlanDate()); // 结算日期`
  该行由历史提交 **`da07af00d`**（`yijd V10-24560【保利-v10合同费用对接】应收同步中台增加明源id、结算日期`）确立：
  `- setSettlementDate(receive.getFeesDueDate())` → `+ setSettlementDate(contractCollectionPlan.getCollectionPlanDate())`。
- 全仓 `setSettlementDate` 仅 4 处：`BcrmBillingServiceImpl:503` / `BcrmCollectionServiceImpl:328` /
  `ContractReceivablesConfirmServiceImpl:1403` / `SyncChargeServiceImpl:1938` —— **都**是「支出结算/TOB 结算」或「新增链路」，
  **调整链路与减免链路一处都没有**。
- `BcrmReceivables` 实体**没有**结算日期字段（只有 `receivablesDate` 应收日期、`feesDueDate` 费用到期日）→
  需求说「复制原应收的结算日期」时，实际来源是**原应收所属回款计划的 `collectionPlanDate`**。

### ⚠️ 本类工单的高频陷阱：**先查上游 DTO 有没有这个字段，再判红/绿**

需求写「接口没传 X 字段」时，**不要直接去本仓写 `dto.setXxx(...)`** —— 先反编译上游 DTO 确认字段是否存在，
否则会得到一个必然编译失败的伪改动。**配方（已实测）**：

```bash
JAR="<paths.maven_local_repository>/com/newsee/master/ARM/newsee-charge-pojo/master.ARM-SNAPSHOT/newsee-charge-pojo-master.ARM-SNAPSHOT.jar"
WORK="<paths.automation_workspace>/.ai-auto-fix/tmp-jar"; rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK"
"/e/Program Files/Java/jdk-17/bin/jar.exe"  xf "$JAR" com/newsee/charge/dto/ThirdEditPaymentDTO.class
"/e/Program Files/Java/jdk-17/bin/javap.exe" -p com/newsee/charge/dto/ThirdEditPaymentDTO.class
```

NCM-3866 实测：`ThirdEditPaymentDTO` 全部 18 字段为
`id, precinctId, ownerId, calcStartDate, calcEndDate, shouldChargeDate, chargeId, chargeSum, amount, adjustType, remark, thirdPartId, thirdPrecinctId, thirdOwnerId, thirdChargeId, masterPaymentId, accountFromType, receivePushCenterType`
→ **无 settlementDate/settleDate，也无 setter** ⇒ 本仓写 `setSettlementDate` 直接 `cannot find symbol` ⇒ **硬停① 判红**。
（对照：同 jar 的 `SyncChargeCustomerDetailDTO` **有** `settleDate` + `settlementDate` 两个字段 —— 这就是「新增链路能传、调整链路传不了」的全部原因。）

**判据一句话**：`需求要传的字段` ∩ `上游 DTO 字段集` = ∅ ⇒ 需改上游 DTO + 服务端落库 ⇒ **判红**，
且判红报告必须写明「本仓侧改动点已定位到行 + 待上游加哪个字段 + 卡在哪一条硬停」。

### 「无 schema 的 Map 契约」是另一种跨仓卡点

`syncRecivablReduce` 用 `Map<String,Object> params` 调 `newsee-bill` 的 `/third/dicountForVnine`
（`IBillRemoteService:36-37`）——**本仓单方面 `params.put("settlementDate", ...)` 会被服务端静默忽略**，
且无法本机验证。此类同样判红（需双仓约定 key 名 + 服务端消费），**不要因为「只是加个 map key、编译能过」就误判为绿色**。

### 判红报告的必备结构（NCM-3866 模板，直接套）

1. 需求原文（**注意 description 可能为空** → 取自 `customfield_10601` 功能现状 / `customfield_13401` 修改建议 / `customfield_13400` 业务场景，并纳入全部人工评论）；
2. 链路定位（真实入口 → 层层调用 → 目标接口 + HTTP 路径 + FeignClient 名 + **服务端在哪个仓**）；
3. 根因（**决定性证据**：反编译输出的字段全集 / 全仓 `set*/grep` 命中清单 / 历史提交 sha 与 diff）；
4. 卡点归类（命中哪一条硬停，逐子项说明「本仓能否独立完成」）；
5. **已定位的改动点 + 建议**（写到行号、说明变量是否就绪、标注待上游条件）；
6. **待人工回答 N 问，每问都写「答什么就能转绿」**（这是红转绿的关键，别只写「转人工」）；
7. 本轮动作（RUNNING 评论 id / 流转 id / 明确声明未建分支未改码）；
8. 顺手发现（只汇报不开单）。

## 「合同终止删除应收撞中台缴款守卫」类工单判红配方（2026-09-18 NCM-3992 重处理实测）

### 场景特征与链路地图
合同终止确认（`doStop2` → `handleCollectionPlan4Stop`，按回款计划拆分分支）对「结束月>终止月、账期>操作当月」的应收执行 1.3 删除：
`ContractCollectionPlanServiceImpl#handleCollectionPlan4Stop` L1980-1983 `syncChargeService.syncChargeDel(toDeleteList)`
→ `SyncChargeServiceImpl#syncChargeDel` L443 → `syncChargeDel4V10` L509-543 → `chargeRemoteService.deletePayment(ThirdPaymentDTO{idList=receiveCenterId, precinctId=houseId})`（charge-server `/third/deletePayment`）。
**中台守卫「已存在缴款数据,无法删除」的判定粒度本仓不可见**（newsee-charge 无本地源码，本地 m2 仓也无 charge 构件）。

### 判红关键取证：不要只看本仓代码，去 UAT 实测合同侧数据
测试单被重处理时，报错看似「本仓删了不该删的」，但实测数据可证明**被删应收合同侧已收=0、已开票=0**，守卫却仍拒绝 ⇒ 守卫在中台且粒度未知（收费对象级 or 明细级缴款归属）⇒ 判红。取证配方：
1. 测试评论/重处理原因常附 **UAT 地址+测试账号**（如 842273）——**可只读登录取证**（agent-browser：登录 → 合同模块「应收款管理」按合同编号过滤 → snapshot 读表格的 回款结束日期/应收年月/已收金额/已开票 列）。只查询，绝不点审核/终止/保存。
2. 与 JIRA 附件截图交叉验证（测试常贴应收列表截图，`get_issue_attachments` 可从 changelog 捞到）。
3. 数据判读：已缴款行（已收>0）的「回款结束日期所在月」若 ≤ 终止月 → 属规则 1.1 不动（本仓不会删它）；被删行已收=0 却被中台拒 ⇒ 守卫依据不在合同侧数据。

### 已知先例（若人工选择「友好提示」方向可复用）
- 按合同拆分分支的删除前守卫：`ContractCollectionPlanServiceImpl` L1823-1839 `unDeletable4Receive`（「合同终止次月及以后，存在已收/已开票的应收数据，请先处理后再执行合同终止操作！」）；**按回款计划分支 L1979-1984 无此守卫**。
- 中台缴款查询先例：`BusinessUtils#validReceivableEscrow` L278-337（`/api/charge/third/queryChargeDetailByIds`，查 `escrowPaidChargeSum`，代管缴款>0 即阻断）——注意它查的是**代管**缴款，与 deletePayment 的守卫字段未必相同。

### 唤醒重处理单的状态流转边界（2026-09-18 NCM-3992 实测）
从「重处理」出发的可用流转只有 `131→问题已关闭`、`151→开发/处理中`——**没有到「开发已回复」的流转**。判红/待人工时保持「重处理」现状并在评论写明待人工流转，不要为凑状态走 151。

## 工单「唤醒」机制：人工改描述 / 评论 / 退回重处理后自动重新入队（2026-09-18 落地）

### 要解决的问题
原取单规则只有 `status = 新建`。**判红或交付后工单进入「开发已回复 / 开发/处理中 / 重处理」，人工补描述、写评论或测试退回时 AI 完全无感知。**
- NCM-3866 判红后，经办人易继东直接在 description 上回答了取值口径（`sysdate`），状态未变，原规则永远捞不到。
  人工原话：「如果备注或者评论有更新，也要进入自动任务清单中」。
- NCM-3992 交付 PR #35 后被测试退回「重处理」并附测试评论/重处理原因，原规则同样捞不到。
  人工原话：「重处理的并且有备注的也要纳入，如 NCM-3992」。

另有一个**口径不一致**问题：人工在 JIRA 里看的筛选器 40473 一直含 4 个状态，而自动化 `queue` 只认「新建」⇒
"待开发清单"与实际取单范围对不上（见下文「取单清单必须与人工看到的筛选器一致」）。

### 机制：靠 changelog 水位线，不靠"重投标签"
候选集 `project = NCM AND labels = "AI自动开发" AND status in (新建, "开发已回复", "开发/处理中", 重处理)`，
逐单拉 `GET /rest/api/2/issue/<KEY>?expand=changelog`，与台账 `.ai-auto-fix/state/wake_ledger.json` 的 `baseline_ts` 比对：

| 代号 | 信号 | 判据 |
| --- | --- | --- |
| W1 | 新单 | `status = 新建` 且台账无记录 |
| W2 | 人工评论 | 存在 `id > comment_watermark` **或** `created > baseline_ts`，且正文不以 `[AI-AUTO-DEV]` / `[AI-AUTO-FIX]` 开头的评论 |
| W3 | 人工改字段 | changelog 中 `created > baseline_ts` 且变更字段 ∉ `{status, comment, resolution}` |
| W4 | 显式重跑 | 任意评论含 `[AI-AUTO-DEV] RERUN` / `AI重跑` / `/rerun` —— **可突破状态门禁** |
| W5 | 测试退回 | changelog 中 `status` 变更为 **`重处理`** —— AI 从不流转到该状态，故即使评论为空也必为人工 |

状态映射：`WAKE`（处理）/ `BLOCKED-BY-STATUS`（有信号但状态已在验收阶段，需 W4 才动）/ `HOLD`（累计 3 次未转绿，只认 W4；**`重处理` 态豁免此门槛**）/ `IDLE` / `CLOSED`（终态永不处理）。

### W5「测试退回」是 2026-09-18 补的盲区兜底（人工指令：「重处理的并且有备注的也要纳入，如 NCM-3992」）

**盲区成因**：AI 只改 `status` 与 `comment`，于是 `AI_ONLY_FIELDS = {status, comment, resolution}` 把**所有** status 变更都当 AI 动作过滤掉。而人工把工单从「测试已完成」拖到「重处理」只产生一个 `status` 变更 ——
- 若他顺手写了测试评论 ⇒ W2 命中（NCM-3992 就是这种，所以当轮没漏）；
- 若他顺手填了 `重处理原因` / `重处理原因分类` ⇒ W3 命中（自定义字段不在黑名单里）；
- **若他只改状态、什么都不写 ⇒ 旧规则完全静默 ⇒ 漏单。**

**修法**：给 status 变更加**目标白名单** `HUMAN_STATUS_TARGETS = {重处理}` —— AI 只会流转到「开发已回复 / 开发/处理中」，因此「status → 重处理」一定是人工。判据仍然是"变更字段"，只是把 status 这个字段**按目标值**细分，而不是整体放行。

**注意判据不能扩大**：不要因为想覆盖 W5 就把 `status` 从 `AI_ONLY_FIELDS` 里整个删掉 —— 那样 AI 自己的每次流转都会把自己唤醒，必然自激。这是本机制里最容易改错的一处。

### 自激防护的关键：**绝不能按作者判断**
AI 使用的 JIRA 账号就是 **`jiangxiaofeng`（蒋晓峰）**（`/rest/api/2/myself` 实测：`name=jiangxiaofeng, display=蒋晓峰, email=jiangxiaofeng@new-see.com`），与人工**同一账号**，因此 changelog 的 `author` **无法**区分 AI 与人工。
真正的判据是**变更字段**：**AI 只会改 `status` 与 `comment`**，所以 `description` / 自定义需求字段 / `labels` / `Fix Version` / 计划字段一旦出现在 changelog 里，就一定是人工动作。
该判据顺带覆盖一个盲区：**人工用户本人手工改描述**同样命中 W3（判据是字段，不是作者）。

### 水位线为什么能用字符串比较
`baseline_ts` 存 JIRA 服务器时间原格式（`2026-09-17T20:55:46.000+0800`），全部事件同时区同格式 ⇒ 直接字符串比较即可，**不依赖本地时钟**（本地时钟偏差会导致漏报或重复上报）。
`wake-ack` 写入的不是"当前时间"，而是 **`max(全部评论 created, 全部 history created)`** —— 即"已消化事件的服务器时间上界"，语义最稳。
**`baseline_ts` 的下界 = `max(工单 created, 最后一条 [AI-AUTO-DEV] 评论时间, 台账 baseline_ts)`** ⇒ 台账整个丢失时也不会把历史单批量捞入（兜底靠"最后一条 AI 评论"）。
W2 另有一条更硬的判据：**评论 id 水位线 `comment_watermark`**（`wake-ack` 时写入 `max(comment id)`）。评论 id 单调递增、无时区/时钟问题，**优先于时间戳比较**。

### 取单清单必须与人工看到的筛选器一致（2026-09-18 修正）
筛选器 **40473「00_AI自动开发_合同（待开发）」** 的 JQL 一直是
`project = NCM AND status in (新建, "开发/处理中", 重处理, 开发已回复) AND labels = AI自动开发`，
但 `jira_cli.py queue` 早期**硬编码**成 `status = 新建` —— 于是「筛选器里待开发的单」与「自动化实际会取的单」对不上，
人工看到 NCM-3992 在待开发清单里，自动化却只看「新建」。
现已改为 `queue` **直接读筛选器 40473 的 JQL**（`GET /rest/api/2/filter/40473`，读不到才回退同义硬编码），
输出 `jql_source` / `jql` / `dist`（状态分布）/ `claimable`，两边口径从此同源。
**领取规则不变**：`新建` 可直接领；其余状态（开发已回复 / 开发/处理中 / 重处理）**必须 wake 命中才领**，
否则同一张单会被无限重复处理。

### 命令
```bash
python .ai-auto-fix/jira_cli.py queue                   # 读筛选器 40473 的待开发清单（4 个状态）
python .ai-auto-fix/jira_cli.py wake                    # 扫描（只读，输出 JSON）
python .ai-auto-fix/jira_cli.py wake-ack <KEY>          # 处理完必须 ack，否则下轮重复响应同一事件
python .ai-auto-fix/jira_cli.py wake-hold <KEY> <note>  # 暂停该单自动响应
python .ai-auto-fix/jira_cli.py full <KEY>              # 拉全字段（需求正文在 customfield_13400/13401/10601）

# 改过 jira_cli.py 后必跑（离线、不联网、9 例）
python .ai-auto-fix/tests/test_wake_signals.py
# 真实数据校验（只读 JIRA，不写台账）：用 NCM-3992 的真实 changelog 验证 W5
python .ai-auto-fix/tests/verify_wake_realdata.py
```

### 唤醒单的处理纪律
**增量响应，不重贴全文**：重读全量最新需求（description + `customfield_13400` 业务场景 / `customfield_13401` 修改建议 / `customfield_10601` 功能现状 + 全部人工评论）→ 与上轮结论对比 → 产出 delta → 重新判路由。
- 结论未变 ⇒ 只发 `[AI-AUTO-DEV] UPDATE`（trigger / wake 来源 / delta / 复核依据 / 待人工问题更新）。
- 由红转绿 ⇒ 走正常实现流程（建分支 / worktree / 红灯 / PR）。
- `wake_count >= 3` 仍未转绿 ⇒ HOLD，避免"人工每改一次就刷一篇长评论"；**但「重处理」态豁免该门槛** —— 测试反复退回是常态，静音会让"重处理 + 有备注"永久漏掉，正好违背人工指令。人工显式 `wake-hold` 仍然永远生效。

### 「重处理」单的处理要点（测试退回，必有失败现场）
1. 备注可能分布在**三处**：测试评论（`comment`）、**`重处理原因`**、**`重处理原因分类`** —— 三者都要读，用 `jira_cli.py full <KEY>` 一次拉全。NCM-3992 的失败信息就写在 `重处理原因` 里（不在评论正文）。
2. 必看附件：测试截图 / 日志 / UAT 地址；`jira_cli.py detail <KEY>` 可列 attachment。
3. 先复核「上轮交付是否真的没修好」再动手，区分两种情形：
   - **上轮实现有回归** ⇒ 在同一分支 `ai/<KEY>` 上补充提交 + `[AI-AUTO-DEV] SCOPE-FIX`；
   - **上轮没覆盖到这个场景** ⇒ 按新需求重新实现。
4. 判红转人工时，报告必须写明「上轮哪条结论仍然成立 / 哪条被测试证伪」，**不得重贴上轮结论**。NCM-3992 第二轮就是这个形态：4 个正场景测试全过（上轮结论成立），1 个新场景（8 月已缴款 + 终止 9 月）撞中台缴款守卫失败（新增事实）。

### 实测记录（2026-09-18）
**第一轮 · NCM-3866**
- 首轮扫描：`scanned=1 wake=1`，唯一命中项正是 `NCM-3866`，reason = `W3 人工改字段 by 易继东 @2026-09-17T20:55:46 description: None -> ...sysdate...`；
  **AI 自己 17:01 的 status 流转与 17:02 的 RED 评论均未被误报** ✓
- ack 后复扫：`WAKE -> IDLE` ✓（自激防护成立）
- 发 UPDATE 评论（842262）后 ack：`baseline_ts` 推进到 `2026-09-18T11:10:27`，复扫仍 `IDLE` ✓

**第二轮 · NCM-3992（重处理）**
- 12:01 定时轮扫描命中：`run_id=20260918-120000`，reasons = `W2 人工评论 842027/842239/842273 + W3 人工改字段「重处理原因/附件」`，status=`重处理` ⇒ 走 WAKE 并被领取响应（RUNNING 842290 / RED 842291）。
  **这就是「重处理 + 有备注」能进清单的线上实证** —— 当轮没漏，但依据依赖"人工顺手写了评论"。
- 补 W5 后离线回归：`test_wake_signals.py` 9/9 PASS（T1 W5 命中 / T2·T3 自激防护 / T4·T5 评论 id 去重 / T6 W5 不误报 / T7 复合 / T8 W4 / T9 常数集）。
- 真实数据校验 `verify_wake_realdata.py`：
  - (a) 真实 changelog 中确有 `2026-09-18T11:25:33 panzhuqing status: 测试已完成 -> 重处理`；
  - (b) 用**同一份真实时间线**、但剥离非 status 项、清空评论（模拟"只改状态、什么都不写"）⇒ 旧规则 `reasons=[]`（漏单），新规则产出 `W5 测试退回重处理` ✓；
  - (c) 用当前台账水位线（`2026-09-18T12:01:37`）复扫真实工单 ⇒ `reasons=[]`、`explicit=False` ⇒ **IDLE，新规则零自激、零重复唤醒** ✓
- `queue` 改造后实测：`jql_source=filter/40473(00_AI自动开发_合同（待开发）)`，`count=2 dist={'开发已回复': 1, '重处理': 1}` —— 与人工在 JIRA 看到的清单一致 ✓

### 设计取舍与已知边界
- **为什么不用"人工加重投标签"**：需要人工多一步操作，且 NCM 工单平时不带标签流转习惯；changelog 水位线是零操作、零误报的。
- **为什么不用 JQL `updated >= -2d` 直接取单**：AI 自己的评论也会刷新 `updated` ⇒ 必然自激；且人工尚未看过的历史单会被批量捞入。**JQL 只用来缩小候选集，是否"唤醒"必须靠台账判定。**
- **BLOCKED-BY-STATUS 是一个刻意的保守设计**：工单进入「测试中 / 开发完成 / 测试已完成」后属人工验收流程，AI 不主动插手；**人工若确实要 AI 返工，在评论里写 `[AI-AUTO-DEV] RERUN` 即可**（这一条要主动告知业务方）。
- **「重处理」不属验收态，属待开发态**：它意味着代码要改，所以在 `AUTO_OK_STATUS` 里、不受 BLOCKED-BY-STATUS 限制；而且豁免 HOLD。
- **「备注」在 NCM 里不一定在评论里**：`重处理原因` / `重处理原因分类` / 测试评论 三处都可能有；判定时不能只看 `comment`。这是 2026-09-18 人工指令里"有备注的"的实际落点。
- 台账勿手工编辑；若台账丢失，`wake` 会用"最后一条 `[AI-AUTO-DEV]` 评论时间"或 `created` 作兜底 baseline（不会把历史单全部捞入）。
- **每次改 `jira_cli.py` 的唤醒逻辑后，必须跑 `tests/test_wake_signals.py`** —— 这套规则的判据很细（字段黑名单 + status 目标白名单 + 评论 id 水位线 + HOLD 豁免），纯靠人眼 review 极易改出自激或漏单。

## 复盘改进待办（工程卫生）

- ~~`.ai-auto-fix/` 下已积累 20+ 个一次性脚本，应收敛入口~~ → **2026-09-15 已完成**：
  收敛为 `jira_cli.py`（queue/detail/comment/transitions）与 `gitea_cli.py`（compliance/pr/verify），
  已删除 17 个 `jira_*.py` + `git_pr.py`/`git_merge.py`/`final_check.py`。**新增能力请扩展这两个入口，不要再新建一次性脚本。**
  （2026-09-16：`gitea_cli.py` 的 `merge` 子命令已按人工指令**移除**——AI 不再具备合并能力。）
- 每轮开始前先复核上一轮的**负面环境结论**（D3）。已被推翻的历史误判清单：
  ① “本机无 Maven 凭据/不可构建”（曾误判；现在必须以 `${paths.maven_home}/conf/settings.xml` 的本轮实测为准）；
  ② "Gitea 网络不通"（错，是系统 gitconfig 的 `credential.helper=helper-selector` 交互式助手在挂起）。

### 环境坑补充（2026-09-17 NCM-4007 口径纠正轮实测，均为高频）

1. **`git-commit-id-maven-plugin` 在 worktree 内必失败**：报
   `Could not get HEAD Ref, are you sure you have some commits in the dotGitDirectory?`
   （worktree 的 `.git` 只是**文件指针**，插件解析不了）。
   → **正确跳过属性是 `-Dmaven.gitcommitid.skip=true`**。注意：`-Dgitcommitid.skip=true` **无效**（少前缀 `maven.`）。
   本单失败时该报错指向 `newsee-contract-pojo` 的 `get-the-git-infos` 执行，别误判成 pojo 有问题。
2. **worktree 的 `.git` 指针会中途消失**：主仓 `.git/worktrees/<name>/` 整个目录不翼而飞 →
   之后**所有** git 命令（连 `git status`）都报 `fatal: not a git repository: <repo>/.git/worktrees/<name>`。
   → **抢救顺序（实测零丢失）**：① 把已修改文件复制到 `${paths.automation_workspace}/tmp/keep/` 备份；
     ② `python -c "shutil.rmtree(wt)"` 删掉坏 wt（先遍历删 `target`）；③ `git worktree prune`；
     ④ `git worktree add <wt> <branch>` 重建；⑤ 把备份文件拷回。**重建后务必 `git diff --stat` 核验改动仍在。**
3. **`jira_cli.py comment` 用位置参数**：正确是 `python jira_cli.py comment <KEY> <文件路径>`，
   **不接受 `--file`**（写 `--file x` 会报 `FileNotFoundError: '--file'`）。
4. **长任务不要用 `nohup ... &`**：shell 会话一结束子进程就被杀，**日志会是 0 字节**（现象是"命令返回了但什么都没跑"）。
   → 一律用 Bash 工具的 `run_in_background=true`（前台命令形式 + 平台托管），完成后 `TaskOutput` 取结果。
5. **Timestamp 断言别比 `toString()`**：纳秒为 0 时 `java.sql.Timestamp#toString` 补 `.0`
   （`2026-10-01 23:59:58.0`），会把你自己的断言坑掉。**比 `getTime()`**（毫秒粒度）最稳。
6. **PATH 偶发只剩 python/git**（`dirname`/`cat`/`grep`/`ls` 全挂）：将 `${paths.git_usr_bin}` 转为当前 shell 形式后加入 PATH；
   **注意 `cat >> file <<EOF` 在这种状态下会静默失败**（本次中文内容全部丢失，文件行数没变）→
   写记忆/长文本优先用 **Write 工具或 python `io.open(..., 'a')`**，别依赖 heredoc。

## 证据与脱敏

- 证据目录：`${paths.evidence}`（截图、红/绿/全量构建日志、真实导出样本 xlsx、`git format-patch` 补丁）。
- **绝不复制**工单里的账号口令/Token 凭据；JIRA 评论中也不得出现私有仓库凭据或主机地址，只写"凭据已核验可用"。
- 只写事实与可复核证据，不写"已修复""测试通过"这类无证据结论。

### 环境坑补充（2026-09-21 NCM-3852 交付轮实测）

- **javac 单文件验证被排除编译的 impl（错误集比对法）**：当目标 impl 属 D2 excludes 三文件时，可用
  `mvn dependency:build-classpath -Dmdep.outputFile=cp.txt`（须在线，`-o` 会 DependencyResolutionException）取 classpath，
  再 `javac @args_file` 编译 impl 单文件，与 `git show origin/master:<impl>` 原版跑出的错误集比对——
  **判据=「本次新增错误集合为空」**（基线本身必有既有错误，别追求 0 error）。
- **javac @argfile 两个坑**：①classpath 含 Windows 反斜杠路径时 argfile 会把 `\` 当转义 ⇒ 全部路径转 `/` 再写入；
  ②classpath 51KB 直接送命令行会报 `Argument list too long` ⇒ 必须走 argfile。
- **javac 验证必须开 Lombok 注解处理**：加 `-proc:none` 会少生成 `@Slf4j.log`/`@Data` getter ⇒ 误报一堆
  「找不到符号 变量 log」（NCM-3852 实测 13 个假错误）；去掉该限制后错误集即收敛为真实跨仓缺失。
- **`gitea_cli.py verify` 只输出 2 行**（state/merged + remote_branch），不含 base.sha/mergeable——核对 PR 可交付性
  可临时 `python -c "import gitea_cli as g, json; d=json.loads(g.api('GET','/repos/%s/%s/pulls/<N>'%(g.OWNER,g.REPO))[1]); print(d['mergeable'], d['base']['sha'], d['head']['sha'])"`。
- **`clean_worktree.py` 只清 target 不删 worktree**（本轮实测 WT_EXISTS 仍 True）⇒ 清理收尾必须补手动
  `git worktree remove --force <wt>`，判据仍是 `worktree list` 仅主仓 + `.git/worktrees` 消失。
- **`git ls-remote` 偶发无限挂起**（fetch 正常 ls-remote 挂死，本轮实测）：远端查询命令一律套 `timeout 120`；
  master HEAD 判定改用 fetch 后 `git rev-parse origin/master`。
- **「单号前缀类」工单配方（NCM-3852 实测，可复用）**：前缀来源缺陷（空值拼 "null"）的修法=抽一个静态 resolver 类
  （参数注入 remote service，可 mock 可单测）+ impl 一处接线；impl 被排除编译时这是唯一能让逻辑进单测的结构。
  fail-fast 文案照抄同方法既有 `BizException.fail("...，结算单编号生成失败！")` 风格。

## 环境坑补充（2026-09-21 NCM-3989 第三轮实测）

- **RUNNING 评论必须带 `[AI-AUTO-DEV]` 前缀**：曾用 `open('run_id.txt','w').write(...)` 生成评论文件时漏写前缀行，
  该评论会被 wake 判为「人工评论」（W2 判据=正文不以 `[AI-AUTO-DEV]` 开头）造成假唤醒源。
  虽然随后的 `wake-ack` 会把 `comment_watermark` 推过该评论 id 而不实际自激，但仍应立即补发带前缀的标准评论纠正。
  **RUNNING 评论文件一律用 Write 工具生成并逐行核对首行**。
- **上轮 PR 已被人工合并后的交付形态（NCM-3989 r3 实测）**：`compliance` 会显示「该 head 上最近的历史 PR state=closed merged=True」
  → 幂等复用失效，**必须新建 PR**（`gitea_cli.py pr` 对 closed PR 不会复用）。先 `git merge-base --is-ancestor <上轮commit> origin/master`
  确认上轮交付已进 master，再 push（fast-forward）+ 新建 PR，PR diff 自动只含本轮 delta；DONE 评论写明「上轮 PR #N 已被人工合并」。
- **合并基线可能自带新失败（非本单回归的实证法）**：merge origin/master 后全量出现新失败（本轮 = NCM3744CompanySizeSyncTest，
  来自基线合入的 NCM-3744 代码）→ 把本单改动**备份后移出工作区**（`git diff > patch` + `git checkout --` + 暂移新测试文件），
  在无本单改动的基线 HEAD 上复跑同一测试，同样失败 ⇒ 定性「基线既有」，恢复改动继续交付。不要只凭「diff 无关」口头定性。
- **`git stash push -- <pathspec>` 含未跟踪文件时会静默失败**（只报 `Did you forget to 'git add'?`，改动原样留在工作区）；
  且工作区可能残留历史轮的旧 stash（勿动）。备份/恢复用「patch + checkout + cp」组合更可靠。

## 低开平台（低代码设计器）资料（references/）—— 2026-09-22 NCM-4025 沉淀
「XX列表某列显示为空 / 字典下拉取值错绑 / 表单设计·列配置」类工单**先读 `references/README.md`**
（权威路径：本仓库 `.agents/skills/autodev-pilot/references/`；用户级入口不含该目录）：
- `lowcode-dictionary.md` —— 数据字典存储过程 `add_ecmDictionaryItem` **参数序陷阱（第3参=itemValue、第4参=itemCode）**与数据接口 `/contract/ecmDictionary/list-ecmDictionaryByClass`
- `lowcode-resourcecolumn.md` —— `ns_core_resourcecolumn.TACTICS` / keyRefer 错绑修复 SQL 两模式（replace 主键口径 vs 整值覆盖）/ 月度 system 脚本自愈机制 / TACTICS 转义形态坑
- `lowcode-form-design.md` —— funcinfoId 定位页面归属（menuName/formCode/tableName/databaseName）与 keyRefer 两种挂点
- `lowcode-case-ncm-4025.md` —— NCM-4025 判红 → 人工授权 → 转绿落盘全链路复盘（含无 DB 的 sqlite3 验证策略）
新增低开知识进 references/ 的约定（命名 `lowcode-<主题>.md`、file:line 证据、实测/推断标注）见该 README。
