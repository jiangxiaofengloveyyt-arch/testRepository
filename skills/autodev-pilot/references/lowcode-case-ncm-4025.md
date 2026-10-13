# 案例：NCM-4025 应收拆分方式列显示为空（判红 → 人工授权 → 转绿全链路）

## 工单与时间线

- 工单：【泽信uat走查】应收拆分方式列表列显示为空（labels=AI自动开发）。
- 2026-09-21：**判红**（RED 评论 #843274）。判据：交付物 = 配置 DML 修复脚本 → 硬边界②（迁移脚本类）；验证需生产写 → 硬边界①；本地无 DB 无有效红灯。
  完整判红报告：自动化工作区 `.ai-auto-fix/evidence/NCM-4025/red-report.md`。
- 2026-09-22 人工两轮反馈：① 定位口径改主键 `JE_CORE_RESOURCECOLUMN_ID`；② 「单子上是1008版本，落到 sql/v2/20261008_system.sql，达梦先不处理」= 设计授权落盘 → **判红转绿**。
- 转绿交付：`sql/v2/20261008_system.sql` 末尾追加（+19 行）→ commit + push + PR #41 → DONE / PR-READY / STATUS-NOTE（customfield_10022 预计开发完成为空 → 不代填，状态留「开发已回复」交人工）。

## 根因链路（8 环）

1. 列表「应收拆分方式」列显示为空（泽信 UAT 走查）。
2. 列配置 TACTICS.keyRefer.value 绑 itemCode【实测 `sql/v2/20260205_system.sql:6842`，MLcGAZDvjdLlaDUm-receivablesType】。
3. 字典 1020350516 初始化时 itemCode 传空串【实测 `sql/01_Update_Contract_history_20260306.sql:405-407`】。
4. 渲染时行数据（存 itemValue 值）↔ 字典项 itemCode（空）匹配落空 → 显示空。
5. 对照列（绑 itemValue，`:4210`/`:5028`/`:12835`）正常 → 反向用例成立【实测】。
6. 月度脚本把错配反复分发到各环境；20260924/20261008 已自愈、20261022 无该配置 ⇒ 只有中间版本存量环境需修复【实测盘点】。
7. 同类错配不止本列（`mVF1EB722djlJDyk-receivablesType` `:14594` 等，v2/v2-dm 成对）→ 按人工口径本轮只修工单所指列【实测】。
8. 库归属 = 系统库（ns_core_resourcecolumn 仅 `00_Create_System_Contract.sql` 257 处）→ 脚本落 `*_system.sql`【实测】。

## 修复 SQL（最终定稿 = 人工主键口径）

```sql
update ns_core_resourcecolumn
   set RESOURCECOLUMN_TACTICS = replace(RESOURCECOLUMN_TACTICS, '"value":"itemCode"', '"value":"itemValue"')
 where JE_CORE_RESOURCECOLUMN_ID = 'MLcGAZDvjdLlaDUm-receivablesType'
   and RESOURCECOLUMN_TACTICS like '%"value":"itemCode"%';
```

## 无 DB 环境验证策略【实测】

sqlite3 内存库模拟 `ns_core_resourcecolumn` 三行数据（目标错配行 / 同字典已正确行 / 其他主键行），5 断言：
修正生效 / 已正确行零改动 / 其他主键行零改动 / 幂等重跑 0 行 / JSON 结构不变。
脚本：自动化工作区 `.ai-auto-fix/evidence/NCM-4025/verify_fix_sql.py` → ALL PASS。
JIRA / PR 如实标注「未在任何数据库执行」+ 附执行后自检 select（预期剩余错配 0 行）。

## 沉淀经验（可复用结论）

1. 「低开列表字典列显示为空」⇒ 先看 TACTICS.keyRefer.value，再查字典 itemCode 是否空串 —— 两步全仓只读即可闭环定性。
2. 判红评论 = 设计授权载体：把完整可执行脚本放进判红评论与 evidence，人工一句「落到 XX 脚本」即转绿，下轮按原文落盘走 PR。
3. 定位口径宁窄勿宽：主键 > 列编码 like；宽条件可能误伤同字典其他列（本案人工即把宽条件改成了主键）。
4. 转绿后所有口径以人工最新反馈为准；DONE / PR 正文要显式写清最终口径与「达梦暂不处理」类范围限定，避免读者被判红评论里的旧口径误导。
5. 月度脚本自愈判断是影响面盘点的关键一步——先看最新月脚本有没有同一配置，再决定存量修复范围。
