---
name: jira-connector
description: Connect to JIRA Server with multiple authentication methods. Use when querying JIRA issues, creating tickets, analyzing project data, or when user mentions JIRA, issue tracking, tickets, sprints, or backlog management.
---

# JIRA Connector

连接 JIRA Server 9.10.2+ 进行工单操作。

## 快速开始

```python
import sys
sys.path.append('C:\\Users\\PC\\.workbuddy\\skills\\jira-connector')
from jira_client import get_client

client = get_client()
client.login()

# 测试连接
server_info = client.test_connection()
print(f"Connected to JIRA {server_info['version']}")
```

**环境变量（推荐 PAT 方式）：**
| 变量 | 说明 |
|------|------|
| `JIRA_BASE_URL` | JIRA服务器地址，如 `http://bug.new-see.com:8088` |
| `JIRA_TOKEN` | Personal Access Token |

## 常用操作

| 操作 | 方法 | 示例 |
|------|------|------|
| 获取工单 | `client.get_issue('ITOPS-123')` | 获取工单详情 |
| 搜索工单 | `client.search(jql)` | JQL查询 |
| 添加评论 | `client.add_comment('ITOPS-123', '内容')` | 添加评论 |
| 更新字段 | `client.update_issue('ITOPS-123', {'字段': '值'})` | 更新自定义字段 |
| 状态流转 | `client.transition_issue('ITOPS-123', '11')` | 变更状态 |

### 获取工单信息

```python
issue = client.get_issue('ITOPS-123')
summary = issue['fields']['summary']
status = issue['fields']['status']['name']
reporter = issue['fields']['reporter']['displayName']
assignee = issue['fields'].get('assignee', {}).get('displayName', 'Unassigned')
comments = issue['fields'].get('comment', {}).get('comments', [])
```

### 添加评论

```python
client.add_comment('ITOPS-123', '[AI-2026-03-20 17:00]\n**问题分析**：xxx')
```

### 更新自定义字段

```python
# 日期字段
client.update_issue('ITOPS-123', {'customfield_10022': '2026-03-25'})

# 选项字段（必须用ID格式）
client.update_issue('ITOPS-123', {'customfield_12400': {'id': '15261'}})
```

### 状态流转

```python
# 直接按状态名流转
client.transition_issue('ITOPS-123', '开始进行')

# 按状态ID流转
client.transition_issue('ITOPS-123', '11')
```

### 搜索工单

```python
# 简单查询
results = client.search('project = ITOPS AND status = "创建工单"')

# 分页查询
all_issues = client.search_all('project = ITOPS ORDER BY created DESC')
```

## 自定义字段参考

| 字段名 | Field ID | 类型 | 示例值 |
|--------|----------|------|--------|
| 预计开发完成 | customfield_10022 | 日期 | '2026-03-25' |
| 开发实际工作量 | customfield_11510 | 数字 | 2 |
| 解决方案 | customfield_13403 | 文本 | '已修复' |
| 评价 | customfield_12400 | 选项 | {'id': '15261'} |
| 客户名称 | customfield_10000 | 选项 | {'id': '13163'} |

## 状态流转必填字段

| 从状态 | 到状态 | 转移ID | 必填字段 |
|--------|--------|--------|----------|
| 创建工单 | 正在处理 | 11 | customfield_10022 |
| 正在处理 | 结果确认 | 191 | resolution |
| 结果确认 | 已关闭 | 171 | 无 |

**重要**：状态流转前必须先设置必填字段。

## 响应规范

处理工单后，必须在回复中包含 JIRA 链接：

```
工单：ITOPS-12345
链接：http://bug.new-see.com:8088/browse/ITOPS-12345
```

## 依赖

其他技能通过以下方式调用：

```python
import sys
sys.path.append('C:\\Users\\PC\\.workbuddy\\skills\\jira-connector')
from jira_client import get_client

client = get_client()
```

## 版本信息

当前版本：v1.2

详细变更记录见 `CHANGELOG.md`
