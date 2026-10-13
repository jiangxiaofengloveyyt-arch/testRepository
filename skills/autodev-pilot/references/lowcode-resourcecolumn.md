# 低开列配置（ns_core_resourcecolumn.RESOURCECOLUMN_TACTICS）

## 表与库归属【实测】

- 列配置表 `ns_core_resourcecolumn` **只在系统库**：`sql/00_Create_System_Contract.sql` 中 257 处 vs 业务库 0 处。
- ⇒ 修复脚本落 `sql/v2/YYYYMMDD_system.sql` + `sql/v2-dm/YYYYMMDD_system.sql`（成对；人工可指示只落一边，如 NCM-4025 达梦暂不处理）。
- 主键：`JE_CORE_RESOURCECOLUMN_ID = '<funcinfoId>-<列编码>'`（2026-09-22 人工定稿的定位口径，**优先于列编码 like 宽条件**）。

## TACTICS 结构

`RESOURCECOLUMN_TACTICS` 为紧凑 JSON（无空格），关键键：

```
{"dataUrl":"...classCode=<字典分类码>","keyRefer":{"label":"itemName","value":"itemValue"},"source":"/resultData"}
```

- `keyRefer.value` 决定渲染时用字典项的哪个键与行数据匹配：
  绑 `itemValue` = 正确；绑 `itemCode`（而 itemCode 为空串）⇒ 匹配落空 → **列显示为空**。
- ⚠️ **形态坑**【实测】：system 脚本**源文件**里 TACTICS 值以转义形态出现（`keyRefer\\":{\\"label\\":...`），且同脚本内不同行形态不同（有的行外层裸 JSON、有的行嵌在 @变量转义 JSON 里）。脚本字面量形态 ≠ 数据库实存形态（取决于 sql_mode 反斜杠转义）。
  ⇒ 修复脚本以人工指定口径为准（无反斜杠形态 replace），**执行后必跑自检**；若 replace 命中 0 行 ⇒ 实存形态带转义，换 `\\"value\\":\\"itemCode\\"` 形态重试。

## 修复 SQL 两模式

### 模式 A：replace（keyRefer 错绑，其余配置不动）— NCM-4025 定稿【主键口径，人工 2026-09-22 指定】

```sql
update ns_core_resourcecolumn
   set RESOURCECOLUMN_TACTICS = replace(RESOURCECOLUMN_TACTICS, '"value":"itemCode"', '"value":"itemValue"')
 where JE_CORE_RESOURCECOLUMN_ID = 'MLcGAZDvjdLlaDUm-receivablesType'
   and RESOURCECOLUMN_TACTICS like '%"value":"itemCode"%';
```

要点：主键定位（禁用「列编码 + 字典码 like」宽条件）；like 收窄保证已正确行 / 其他主键行零改动；幂等（重跑 0 行）。

### 模式 B：整值覆盖（静态枚举列，值域稳定）— 同表人工先例【实测】

【实测】`sql/v2/20260205_system.sql:10308-10309`；v2-dm 同款 `sql/v2-dm/20260205_system.sql:13692-13694`：

```sql
update ns_core_resourcecolumn set RESOURCECOLUMN_TACTICS = '[{"label":"待审核","value":"0"},...]'
 where RESOURCECOLUMN_NAME_EN = 'checkStatus'
   and JE_CORE_RESOURCECOLUMN_ID = 'contractManagementUnion-hGtmwpM5ervhtokC-checkStatus';
```

适用：字典不需要走数据接口的静态枚举；覆盖后彻底脱离字典依赖。**动态字典列用模式 A**。

## 月度 system 脚本机制【实测盘点】

- 月度 `*_system.sql` = 设计器导出的**配置全量重发**：人工在环境上修过配置后，下月重导出即「自愈」；但旧脚本仍会把错配重新写进新环境。
- `classCode=1020350516`（应收拆分方式）错配分布（【引用】NCM-4025 判红报告盘点，证据目录 `.ai-auto-fix/evidence/NCM-4025/red-report.md`）：
  - 20260205(x3) / 20260423(x2) / 20260507 / 20260521 / 20260604 / 20260618(x1) / 20260702(x2)，v2 与 v2-dm 成对；
  - 20260924 / 20261008 已绑 itemValue（设计器侧自愈）；20261022 无该字典配置（无反向覆盖）；
  - ⇒ 只有 20260702~20260924 之间的中间版本存量环境需要修复脚本。
- 判影响面必答三问：错配从哪个脚本引入？最新月脚本是否已自愈？修复脚本插入位置是否幂等无害（模式 A 任意位置均可）。
- 盘点方法（锚点法，勿用大正则）：`grep -n 'classCode=<code>' sql/v2/*_system.sql sql/v2-dm/*_system.sql` → 逐命中行看后 ~250 字符内的 keyRefer.value（用 python 窗口扫描；正则遇多层 `\\\"` 转义极易翻车，锚点 + 窗口最稳）。
