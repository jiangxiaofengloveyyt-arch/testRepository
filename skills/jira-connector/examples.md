# JIRA Connector Examples

## Example 1: Query Single Issue

```python
from jira_client import get_client

client = get_client()
issue = client.get_issue('AMS-5183')
print(f"Title: {issue['fields']['summary']}")
print(f"Status: {issue['fields']['status']['name']}")
```

## Example 2: Search Issues

```python
from jira_client import get_client

client = get_client()

# Search recent 新需求 in 物协易 module
jql = 'project=AMS AND issuetype=新需求 AND component="207-物协易" ORDER BY created DESC'
results = client.search(jql, fields=['summary', 'status', 'priority'], max_results=10)

for issue in results['issues']:
    print(f"{issue['key']}: {issue['fields']['summary']}")
```

## Example 3: Create Issue with Standard Format

```python
from jira_client import get_client

client = get_client()

fields = {
    "project": {"key": "AMS"},
    "issuetype": {"id": "10604"},  # 新需求
    "summary": "【物协易】新功能需求",
    "description": "客户名称:00-新视窗\n\n业务场景:xxx\n\n功能现状:xxx\n\n修改建议:xxx\n\n客户信息:00-新视窗",
    "priority": {"id": "4"},  # 一般
    "components": [{"id": "15771"}],  # 207-物协易
    "customfield_10000": {"id": "13163"},  # 客户名称
    "customfield_13400": "业务场景详细描述",
    "customfield_10601": "当前功能现状描述",
    "customfield_13401": "修改建议详细内容",
    "customfield_10602": "智慧运营事业部",
    "customfield_10041": "2025-12-31",
    "customfield_12600": {"value": "00-新视窗", "child": {"value": "其他"}}
}

result = client.create_issue(fields)
print(f"Created: {result['key']}")
```

## Example 4: Batch Export Data

```python
from jira_client import get_client
import json

client = get_client()

# Export all 2025 ITOPS tickets
jql = 'project=ITOPS AND created >= "2025-01-01" AND created < "2026-01-01"'
issues = client.search_all(jql, fields=['summary', 'status', 'created', 'resolutiondate'])

with open('itops_2025.json', 'w', encoding='utf-8') as f:
    json.dump(issues, f, ensure_ascii=False, indent=2)

print(f"Exported {len(issues)} issues")
```

## Example 5: Analyze Project Statistics

```python
from jira_client import get_client
from collections import Counter

client = get_client()

# Get all resolved issues in a project
jql = 'project=AMS AND status=完成 AND created >= "2025-01-01"'
issues = client.search_all(jql, fields=['issuetype', 'priority', 'components'])

# Count by type
type_counts = Counter(i['fields']['issuetype']['name'] for i in issues)
print("By Type:", dict(type_counts))

# Count by priority
priority_counts = Counter(i['fields']['priority']['name'] for i in issues)
print("By Priority:", dict(priority_counts))
```
