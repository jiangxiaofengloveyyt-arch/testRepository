# 低代码平台（低开）工单知识库 — 公共 references/

## 这是什么

适用于采用相同 formdesign 低代码设计器约定的模块。入口工单特征：「XX 列表某列显示为空」「字典下拉取值错绑」「表单设计/列配置类」。2026-09 起的 NCM-4025 是首个全链路历史案例，后续知识按主题分文件承接；案例中的项目编号、路径和数据仍需在目标模块重新核验。

## 文件索引

| 文件 | 主题 |
| --- | --- |
| [common-automation.md](common-automation.md) | 所有模块共用的自动开发运行手册；非低开工单也必须先读 |
| [common-operational-notes.md](common-operational-notes.md) | 从多轮实战手册抽取的真实红灯、唤醒去重、环境诊断、证据和安全边界 |
| [lowcode-modeling-api.md](lowcode-modeling-api.md) | NLCPD 一次性建模 API、JSON 结构、查重、依赖顺序、补偿回滚和在线代码执行边界 |
| [lowcode-generator.md](lowcode-generator.md) | Generator 预览/下载接口、菜单版本、FreeMarker 模板、增量合并和脚本交付流程 |
| [lowcode-dictionary.md](lowcode-dictionary.md) | 数据字典（ns_ecm_dictionary_item）：存储过程 `add_ecmDictionaryItem` 参数序陷阱、数据接口 |
| [lowcode-resourcecolumn.md](lowcode-resourcecolumn.md) | 列配置（ns_core_resourcecolumn.TACTICS）：keyRefer 错绑、修复 SQL 两模式、月度 system 脚本机制、主键定位口径 |
| [lowcode-form-design.md](lowcode-form-design.md) | 表单设计配置：funcinfoId 定位页面归属、formJson 结构、keyRefer 挂点 |
| [lowcode-case-ncm-4025.md](lowcode-case-ncm-4025.md) | NCM-4025 完整案例复盘：判红 → 人工授权 → 转绿落盘全链路 |

## 扩展约定（后续新增知识时遵守）

1. 新文件命名 `lowcode-<主题>.md`，写完**必须**加进上面的索引表，并同步到其他采用同一低开约定的模块技能包。
2. 所有结论必须带 `file:line` 形式的仓内证据；无法核验的明确标【推断】并写清验证路径。
3. 证据分级标注：【实测】= 本仓/本环境亲自验证过；【引用】= 来自人工反馈或历史工单结论（可信但本轮未复核）。
4. 涉及 SQL 修复脚本的：写明库归属（系统库 / 业务库）、幂等性、执行后自检语句。
5. 不在 SKILL.md 里堆细节——SKILL.md 只保留一段入口指引，细节全部落本目录。

## 权威路径说明（重要）

本目录位于当前仓库 `${paths.backend_repo}/.agents/skills/autodev-pilot/references/`，随仓库分发；实际路径以 `config_loader.py resolve` 为准。它是公共资料的仓库内副本，不能替代当前模块的 `domain.md`。
用户级 `~/.workbuddy/skills/autodev-pilot/SKILL.md` 是公共入口，不复制本目录。
处理低开工单时一律读取仓库权威副本；改本目录无需同步正文，但修改权威路径后应重新运行 `sync_to_user_level.py` 刷新重定向。
