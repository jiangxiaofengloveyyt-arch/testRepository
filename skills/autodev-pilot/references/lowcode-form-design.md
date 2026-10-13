# 低开表单设计配置（funcinfoId / formJson / 页面归属定位）

## funcinfoId：串起列配置与表单的钥匙

- 列配置主键 = `<funcinfoId>-<列编码>`（如 `MLcGAZDvjdLlaDUm-receivablesType`）。
- 表单字段 id = `<funcinfoId>-<modelKey>`（如 `MLcGAZDvjdLlaDUm-contractNo`）。
- ⇒ 拿到错配 funcinfoId，去 system 脚本的**表单 JSON**（`set @new_form_data='{...}'` 语句）里 grep，即可定位页面归属。
  【实测】`sql/v2/20260205_system.sql:6501`，`MLcGAZDvjdLlaDUm` →：

| 键 | 值 | 含义 |
| --- | --- | --- |
| databaseName | formdesign-contract-center | 所属微服务库 |
| menuName | 应收款管理 | 菜单名 |
| tableName | bcrm_receivables | 业务表 |
| formCode | contractReceivable | 表单编码 |

- 边界【实测】：纯列表页片段可能不含这些键 → 报告如实写「页面归属待确认」；修复条件（主键定位）不依赖页面归属。

## keyRefer 的两种挂点

- **列**（列表渲染）：`TACTICS.keyRefer.value` = 行数据 ↔ 字典项的匹配键（详见 lowcode-resourcecolumn.md）。
- **表单字段**（提交写入）：formOptions/keyRefer 决定下拉提交哪个键的值。**行数据存的是 itemValue**（表单端绑 itemValue 提交）⇒ 列配置也应绑 itemValue【实测对照 + 推断】。
- 三态对照【实测 `sql/v2/20260205_system.sql`】：
  - 正确（itemValue）：`:4210`（3s1UDt2SQAdWatcP）/ `:5028` / `:12835`；
  - 错配（itemCode）：`:6842`（MLcGAZDvjdLlaDUm）/ `:14594`（mVF1EB722djlJDyk）。

## 排查路径（全仓只读闭环，无需 DB）

1. 从工单现象定位列：菜单/页面名 → grep system 脚本 `menuName` 或列编码。
2. funcinfoId → 表单 JSON 定位页面归属（databaseName / menuName / tableName / formCode）。
3. `TACTICS.dataUrl` 里的 classCode → 按 lowcode-dictionary.md 查字典项 itemCode 是否为空串。
4. keyRefer.value 错绑 ⇒ 修复 SQL（lowcode-resourcecolumn.md 模式 A）。
