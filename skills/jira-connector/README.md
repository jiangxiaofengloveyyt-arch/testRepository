# JIRA Connector Skill
【重要】使用 jira-connector 技能前，请先设置环境变量

连接公司JIRA系统（双认证：nginx Basic Auth + JIRA Session）。

## 特点

- **安全**：用户名密码通过环境变量注入，不硬编码在代码中
- **双认证**：自动处理nginx层和JIRA层的双重认证
- **会话管理**：自动处理session过期重连
- **批量操作**：支持分页查询大数据集

## 快速开始

### 1. 设置环境变量

```powershell
# Windows PowerShell
$env:JIRA_BASE_URL="http://bug.new-see.com:8088"
$env:JIRA_NGINX_USER="你的nginx用户名"
$env:JIRA_NGINX_PASS="你的nginx密码"
$env:JIRA_USER="你的JIRA用户名"
$env:JIRA_PASS="你的JIRA密码"
```

### 2. 使用示例

```python
from jira_client import get_client

client = get_client()
issue = client.get_issue('AMS-5183')
print(issue['fields']['summary'])
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 技能主文档，包含完整API使用指南 |
| `jira_client.py` | 可复用的Python客户端类 |
| `examples.md` | 常见使用场景示例 |
| `README.md` | 本文件 |

## AMS项目常用字段参考

| 字段 | ID | 示例值 |
|------|-----|--------|
| 新需求 | 10604 | `{"id": "10604"}` |
| 207-物协易 | 15771 | `{"id": "15771"}` |
| 一般优先级 | 4 | `{"id": "4"}` |
| 00-新视窗 | 13163 | `{"id": "13163"}` |

## 注意事项

- 所有敏感信息通过环境变量传递，请勿硬编码
- 批量查询建议使用 `search_all()` 方法，内置分页和延迟
- 网络超时默认60秒，可根据需要调整
