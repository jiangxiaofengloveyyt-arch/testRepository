# ITOPS 运维单字段速查表

## 单据类型

| 类型 | ID | 说明 |
|------|-----|------|
| 运维处理 | 11202 | 常规运维需求处理 |
| 数据调整 | 7 | 数据库数据修改 |
| 功能咨询 | 11203 | 功能使用咨询 |
| 系统缺陷 | 11204 | Bug修复 |
| 紧急发包 | 11401 | 紧急版本发布 |
| 工作量评估 | 11601 | 需求工作量评估 |

## 常用字段

### 基础字段

| 字段ID | 名称 | 类型 | 示例值 |
|--------|------|------|--------|
| summary | 摘要 | string | '问题描述' |
| description | 描述 | string | '详细描述' |
| assignee | 经办人 | user | {'name': 'yangzhidong'} |
| priority | 优先级 | option | {'id': '4'} |
| components | 模块 | array | [{'id': '15661'}] |

### 自定义字段

| 字段ID | 名称 | 类型 | 格式示例 |
|--------|------|------|----------|
| customfield_10000 | 客户名称 | option | {'id': '13163'} |
| customfield_12600 | 客户信息 | option-with-child | {'id': '15862', 'child': {'id': '15863'}} |
| customfield_10022 | 预计开发完成 | date | '2026-03-25' |
| customfield_11510 | 开发实际工作量 | number | 2 |
| customfield_13403 | 解决方案 | string | '已修复' |
| customfield_12400 | 评价 | option | {'id': '15261'} |
| customfield_13402 | 是否咨询 | option | {'id': '21680'} |
| customfield_13300 | 验证方式 | option | {'id': '21682'} |
| customfield_12000 | 需求是否评审通过 | option | {'id': '21680'} |

## 常用选项值

### 客户名称 (customfield_10000)

| 值 | ID |
|----|-----|
| 00-新视窗 | 13163 |

### 客户信息级联 (customfield_12600)

| Parent | Parent ID | Child | Child ID |
|--------|-----------|-------|----------|
| 00-新视窗 | 15862 | 其他 | 15863 |

### 评价 (customfield_12400)

| 值 | ID |
|----|-----|
| 非常满意 | 15261 |

### 是否咨询 (customfield_13402)

| 值 | ID |
|----|-----|
| 是 | 21679 |
| 否 | 21680 |

### 验证方式 (customfield_13300)

| 值 | ID |
|----|-----|
| 测试验证 | 21682 |

### 模块 (components)

| 值 | ID |
|----|-----|
| 其他 | 15661 |

## 状态流转

### 运维处理单据状态流

```
创建工单 → 正在进行 → 结果确认 → 完成
   ↓           ↓           ↓
 (创建)    (开始处理)   (提交完成)
```

### 状态转换ID

| 当前状态 | 目标状态 | 转换名称 | 转换ID | 必填字段 |
|----------|----------|----------|--------|----------|
| 创建工单 | 正在进行 | 开始进行 | 11 | 预计开发完成 |
| 正在进行 | 结果确认 | 提交完成 | 191 | 开发实际工作量, 解决方案 |
| 结果确认 | 完成 | 确认完成 | 171 | 评价 |
| 创建工单 | 已关闭 | Closed | 291 | - |
| 正在进行 | 已关闭 | Closed | 291 | - |
| 结果确认 | 正在处理 | 重处理 | 181 | - |

## 代码示例

### 创建运维单

```python
import sys
sys.path.append('e:/aicoding/skills/jira-connector')
from jira_client import get_client

client = get_client()
client.login()

new_issue = client.create_issue({
    "project": {"key": "ITOPS"},
    "issuetype": {"id": "11202"},
    "summary": "问题描述",
    "description": "详细描述",
    "assignee": {"name": "yangzhidong"},
    "components": [{"id": "15661"}],
    "customfield_10000": {"id": "13163"},
    "customfield_12600": {"id": "15862", "child": {"id": "15863"}},
    "customfield_13402": {"id": "21680"},
})

print(f"Created: {new_issue['key']}")
print(f"Link: http://bug.new-see.com:8088/browse/{new_issue['key']}")
```

### 状态变更（带必填字段）

```python
# 从"正在进行"转换到"结果确认"，同时设置必填字段
result = client.transition_issue(
    'ITOPS-123',
    '提交完成',
    fields={
        'customfield_11510': 2,  # 开发实际工作量
        'customfield_13403': '已修复'  # 解决方案
    }
)
print(f"Transitioned: {result}")
```

### 获取可用转换

```python
transitions = client.get_transitions('ITOPS-123')
for t in transitions:
    print(f"{t['id']}: {t['name']} -> {t['to']['name']}")
```

## 常见错误

### 1. 转换时缺少必填字段

**错误**: `HTTP 400 - customfield_11510: 开发实际工作量 is required`

**解决**: 在 transition_issue() 中传入 fields 参数

```python
client.transition_issue('ITOPS-123', '提交完成', fields={
    'customfield_11510': 2
})
```

### 2. Option字段格式错误

**错误**: HTTP 400 when setting option fields

**解决**: 使用 `{'id': 'xxx'}` 格式

```python
# 正确
{'customfield_12400': {'id': '15261'}}

# 错误
{'customfield_12400': '非常满意'}
{'customfield_12400': {'value': '非常满意'}}
```

### 3. 级联字段格式错误

**错误**: 客户信息字段设置失败

**解决**: 同时设置 parent 和 child

```python
{'customfield_12600': {'id': '15862', 'child': {'id': '15863'}}}
```

## 响应规范

创建或修改JIRA单后，必须在回复中包含链接：

```
## 运维单创建成功

| 字段 | 值 |
|------|------|
| 单号 | ITOPS-124854 |
| 摘要 | 测试AI创建操作运维单 |

访问链接: http://bug.new-see.com:8088/browse/ITOPS-124854
```
