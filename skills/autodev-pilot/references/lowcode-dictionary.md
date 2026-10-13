# 低开数据字典：两套模型不得混用

当前低开资料里存在两套字典实现，先按调用链判断，不要把字段名、接口或存储过程交叉套用：

| 模型 | 主要表/入口 | 适用场景 |
| --- | --- | --- |
| 平台 AI 建模字典 | `ns_core_dictionary`、`ns_core_dictionaryitem`、`ns_core_dictionarygroup`；`POST /aiModeling/generate` | 一次性生成 JSON、表单下拉和脚本前置建模 |
| 合同历史 ECM 字典 | `ns_ecm_dictionary_item`；`/contract/ecmDictionary/list-ecmDictionaryByClass` | 合同旧低开接口和已有 NCM 工单排查 |

平台 AI 建模字典的字段、查重、幂等和回滚口径见 [lowcode-modeling-api.md](lowcode-modeling-api.md)。本文件以下内容保留合同 ECM 的历史事实，不能用于替代平台字典协议。

## 合同历史 ECM 字典（ns_ecm_dictionary_item）

## 表与数据接口

- 字典项表：`ns_ecm_dictionary_item`，按 `dictionaryClassCode`（分类码）分组。
- 下拉数据接口：`GET /contract/ecmDictionary/list-ecmDictionaryByClass?classCode=<code>`，返回该分类全部字典项行。
  【实测】`newsee-contract-rest/src/main/java/com/newsee/contract/controller/ecm/EcmDictionaryItemController.java:73-77`
- 排查入口：查这个接口返回 or 直查表。**itemCode 为空串**是「列显示为空」类问题最常见的源头。

## 初始化存储过程：add_ecmDictionaryItem

签名（【实测】`sql/v2/20260205.sql:140-146`）：

```sql
CREATE PROCEDURE `add_ecmDictionaryItem`(
  in PPPP_dictionaryClassCode varchar(100),
  in PPPP_itemName varchar(100),  -- 名称，必填
  in PPPP_itemValue varchar(100), -- 值，必填
  in PPPP_itemCode varchar(100),  -- 编码，非必填
  in PPPP_orderIndex int)
```

⚠️ **参数序陷阱（NCM-4025 根因）**：**第 3 参 = itemValue（值）、第 4 参 = itemCode（编码）** —— itemValue 在前！
按「先编码后值」的直觉写调用就会把空串传给 itemCode。初始化先例（【实测】`sql/01_Update_Contract_history_20260306.sql:405-407`）：

```sql
call add_ecmDictionaryItem('1020350516','按月度','1','',1);   -- 第4参 itemCode 传了空串
call add_ecmDictionaryItem('1020350516','按工程进度','2','',2);
call add_ecmDictionaryItem('1020350516','按时点结算','3','',3);
```

排查命令：

```bash
grep -rn "add_ecmDictionaryItem('<classCode>'" sql/ | head
```

看第 4 参是否为空串。

## itemCode vs itemValue 语义

| 键 | 含义 | 注意 |
| --- | --- | --- |
| itemValue | 值 | **表单下拉提交、行数据存的就是它**【实测对照 + 推断，见 lowcode-form-design.md】 |
| itemCode | 编码 | 初始化常被传空串 ⇒ 若列配置 keyRefer.value 绑 itemCode，渲染匹配永远落空 → 列显示为空 |

**修复方向是改列配置绑 itemValue**（见 lowcode-resourcecolumn.md 修复 SQL 模式 A），而不是补 itemCode 数据——补数据不改变行数据实存值，且可能与表单提交语义冲突。
