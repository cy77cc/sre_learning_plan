# Day 138: Alertmanager 告警

> 📅 日期：2026-05-03
> 📖 学习主题：Alertmanager 路由、分组、抑制、静默、通知渠道、高可用、告警模板、最佳实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 134 (Prometheus 基础), Day 135 (PromQL 查询语言)

---

## 🎯 学习目标

- 理解 Alertmanager 的架构和工作原理
- 掌握告警路由的配置方式
- 理解告警分组、抑制和静默机制
- 能够配置多种通知渠道
- 了解 Alertmanager 高可用配置
- 掌握告警模板的编写

---

## 📖 核心知识点

### 1. Alertmanager 架构

#### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Alertmanager 架构                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐                                               │
│  │  Prometheus      │                                               │
│  │  Server          │                                               │
│  │                  │                                               │
│  │  告警规则        │                                               │
│  │  触发告警        │                                               │
│  └────────┬─────────┘                                               │
│           │                                                         │
│           │ 发送告警                                                │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Alertmanager                               │  │
│  │                                                              │  │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │  │
│  │   │   路由       │  │   分组       │  │   抑制       │     │  │
│  │   │  (Route)     │  │  (Group)     │  │  (Inhibit)   │     │  │
│  │   └──────────────┘  └──────────────┘  └──────────────┘     │  │
│  │                                                              │  │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │  │
│  │   │   静默       │  │   去重       │  │   模板       │     │  │
│  │   │  (Silence)   │  │  (Dedup)     │  │  (Template)  │     │  │
│  │   └──────────────┘  └──────────────┘  └──────────────┘     │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              │ 通知                                 │
│                              ▼                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Slack      │  │   Email      │  │  PagerDuty   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Webhook    │  │   DingTalk   │  │  企业微信    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 告警生命周期

```
告警生命周期：

  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  告警    │────▶│  路由    │────▶│  分组    │────▶│  通知    │
  │  触发    │     │  匹配    │     │  聚合    │     │  发送    │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘
       │                 │                 │                 │
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  抑制    │     │  静默    │     │  去重    │     │  解析    │
  │  检查    │     │  检查    │     │  检查    │     │  恢复    │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘

  状态转换：
  inactive → pending → firing → resolved

  inactive：告警条件不满足
  pending：告警条件满足，但未持续 for 时间
  firing：告警条件持续满足，触发通知
  resolved：告警条件不再满足，发送恢复通知
```

### 2. 告警路由

#### 2.1 路由配置

```yaml
# alertmanager.yml
global:
  # 全局配置
  resolve_timeout: 5m
  smtp_from: 'alertmanager@example.com'
  smtp_smarthost: 'smtp.example.com:587'
  smtp_auth_username: 'alertmanager@example.com'
  smtp_auth_password: 'password'
  smtp_require_tls: true

# 路由配置
route:
  # 默认接收者
  receiver: 'default-slack'

  # 分组标签
  group_by: ['alertname', 'job', 'namespace']

  # 分组等待时间
  group_wait: 30s

  # 分组间隔
  group_interval: 5m

  # 重复间隔
  repeat_interval: 4h

  # 子路由
  routes:
    # 严重告警
    - matchers:
        - severity = critical
      receiver: 'pagerduty-critical'
      group_wait: 10s
      repeat_interval: 1h
      continue: false

    # 警告
    - matchers:
        - severity = warning
      receiver: 'slack-warnings'
      group_wait: 30s
      repeat_interval: 4h

    # 特定服务
    - matchers:
        - job = payment-service
      receiver: 'payment-team-slack'
      group_by: ['alertname', 'instance']
      group_wait: 10s
      repeat_interval: 30m

    # 特定命名空间
    - matchers:
        - namespace = production
      receiver: 'production-slack'
      group_by: ['alertname', 'pod']
```

#### 2.2 路由匹配

```yaml
# 路由匹配示例
route:
  routes:
    # 精确匹配
    - matchers:
        - severity = critical
      receiver: 'critical-slack'

    # 正则匹配
    - matchers:
        - job =~ ".*-service"
      receiver: 'service-slack'

    # 不等于匹配
    - matchers:
        - severity != info
      receiver: 'non-info-slack'

    # 多条件匹配
    - matchers:
        - severity = critical
        - namespace = production
      receiver: 'prod-critical-slack'

    # 或条件匹配
    - matchers:
        - severity =~ "critical|warning"
      receiver: 'important-slack'

    # 否定匹配
    - matchers:
        - severity !~ "info|debug"
      receiver: 'important-slack'
```

### 3. 告警分组

#### 3.1 分组机制

```
告警分组机制：

  ┌──────────────────────────────────────────────────────────────┐
  │                    告警分组示例                                │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  原始告警：                                                  │
  │  ├── Alert 1: {alertname="HighCPU", job="api", instance="1"} │
  │  ├── Alert 2: {alertname="HighCPU", job="api", instance="2"} │
  │  ├── Alert 3: {alertname="HighCPU", job="web", instance="1"} │
  │  └── Alert 4: {alertname="HighMem", job="api", instance="1"} │
  │                                                              │
  │  group_by: ['alertname', 'job']                              │
  │                                                              │
  │  分组结果：                                                  │
  │  ├── Group 1: {alertname="HighCPU", job="api"}               │
  │  │   ├── Alert 1                                             │
  │  │   └── Alert 2                                             │
  │  │                                                           │
  │  ├── Group 2: {alertname="HighCPU", job="web"}               │
  │  │   └── Alert 3                                             │
  │  │                                                           │
  │  └── Group 3: {alertname="HighMem", job="api"}               │
  │      └── Alert 4                                             │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  分组参数：
  ├── group_by：分组标签
  ├── group_wait：首次告警等待时间（收集同一组的告警）
  ├── group_interval：同一组内告警的间隔
  └── repeat_interval：重复发送同一告警的间隔
```

#### 3.2 分组配置

```yaml
# 分组配置示例
route:
  # 全局分组
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # 严重告警分组（更短的间隔）
    - matchers:
        - severity = critical
      receiver: 'pagerduty'
      group_by: ['alertname']
      group_wait: 10s
      group_interval: 1m
      repeat_interval: 30m

    # 服务告警分组
    - matchers:
        - job =~ ".*-service"
      receiver: 'service-slack'
      group_by: ['alertname', 'job', 'instance']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

    # 节点告警分组
    - matchers:
        - job = node
      receiver: 'infra-slack'
      group_by: ['alertname', 'instance']
      group_wait: 1m
      group_interval: 10m
      repeat_interval: 4h
```

### 4. 告警抑制

#### 4.1 抑制机制

```
告警抑制机制：

  ┌──────────────────────────────────────────────────────────────┐
  │                    告警抑制示例                                │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  场景：节点宕机时，抑制该节点上的所有告警                    │
  │                                                              │
  │  源告警（source）：                                          │
  │  {alertname="NodeDown", instance="node1"}                    │
  │                                                              │
  │  目标告警（target）：                                        │
  │  ├── {alertname="HighCPU", instance="node1"}    → 被抑制    │
  │  ├── {alertname="HighMem", instance="node1"}    → 被抑制    │
  │  ├── {alertname="HighDisk", instance="node1"}   → 被抑制    │
  │  ├── {alertname="HighCPU", instance="node2"}    → 不抑制    │
  │  └── {alertname="NodeDown", instance="node2"}   → 不抑制    │
  │                                                              │
  │  抑制规则：                                                  │
  │  当 NodeDown 告警触发时，抑制同一 instance 的其他告警        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 4.2 抑制配置

```yaml
# 抑制配置
inhibit_rules:
  # 节点宕机时，抑制该节点的所有告警
  - source_matchers:
      - alertname = NodeDown
    target_matchers:
      - instance = {{ $labels.instance }}
    equal: ['instance']

  # 严重告警触发时，抑制同一服务的警告
  - source_matchers:
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['alertname', 'job']

  # 网络故障时，抑制依赖网络的服务告警
  - source_matchers:
      - alertname = NetworkDown
    target_matchers:
      - job =~ ".*-service"
    equal: ['namespace']

  # 数据库故障时，抑制依赖数据库的服务告警
  - source_matchers:
      - alertname = DatabaseDown
    target_matchers:
      - job =~ ".*-service"
    equal: ['namespace']
```

### 5. 告警静默

#### 5.1 静默机制

```
告警静默机制：

  ┌──────────────────────────────────────────────────────────────┐
  │                    告警静默示例                                │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  场景：计划维护窗口期间静默告警                              │
  │                                                              │
  │  静默规则：                                                  │
  │  ├── 时间范围：2026-05-03 02:00 - 04:00                     │
  │  ├── 匹配条件：namespace=production                         │
  │  └── 创建者：sre-team                                       │
  │                                                              │
  │  效果：                                                      │
  │  ├── 02:00 前：正常发送告警                                 │
  │  ├── 02:00-04:00：静默，不发送告警                          │
  │  └── 04:00 后：恢复正常发送                                 │
  │                                                              │
  │  静默 vs 抑制：                                              │
  │  ├── 静默：基于时间范围，手动创建                            │
  │  └── 抑制：基于告警关联，自动触发                            │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 5.2 静默配置

```json
// 通过 API 创建静默
{
  "matchers": [
    {
      "name": "namespace",
      "value": "production",
      "isRegex": false,
      "isEqual": true
    },
    {
      "name": "severity",
      "value": "warning",
      "isRegex": false,
      "isEqual": true
    }
  ],
  "startsAt": "2026-05-03T02:00:00Z",
  "endsAt": "2026-05-03T04:00:00Z",
  "createdBy": "sre-team",
  "comment": "计划维护窗口 - 数据库升级",
  "status": {
    "state": "active"
  }
}
```

```bash
# 通过 API 创建静默
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "namespace", "value": "production", "isRegex": false}
    ],
    "startsAt": "2026-05-03T02:00:00Z",
    "endsAt": "2026-05-03T04:00:00Z",
    "createdBy": "sre-team",
    "comment": "计划维护窗口"
  }'

# 查看所有静默
curl http://alertmanager:9093/api/v2/silences

# 删除静默
curl -X DELETE http://alertmanager:9093/api/v2/silence/{silence-id}
```

### 6. 通知渠道

#### 6.1 Slack 通知

```yaml
# Slack 接收者配置
receivers:
  - name: 'slack-sre'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
        channel: '#sre-alerts'
        send_resolved: true
        title: '{{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
        username: 'Alertmanager'
        icon_emoji: ':bell:'
```

#### 6.2 Email 通知

```yaml
# Email 接收者配置
receivers:
  - name: 'email-sre'
    email_configs:
      - to: 'sre-team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'password'
        require_tls: true
        send_resolved: true
        headers:
          Subject: '{{ template "email.subject" . }}'
        html: '{{ template "email.html" . }}'
```

#### 6.3 Webhook 通知

```yaml
# Webhook 接收者配置
receivers:
  - name: 'webhook-ops'
    webhook_configs:
      - url: 'http://webhook-ops:8080/alerts'
        send_resolved: true
        http_config:
          basic_auth:
            username: 'webhook-user'
            password: 'webhook-password'
```

#### 6.4 企业微信通知

```yaml
# 企业微信接收者配置
receivers:
  - name: 'wechat-sre'
    wechat_configs:
      - corp_id: 'ww1234567890'
        api_secret: 'secret'
        agent_id: '1000002'
        to_user: '@all'
        to_party: 'sre-team'
        send_resolved: true
        message: '{{ template "wechat.message" . }}'
```

#### 6.5 钉钉通知

```yaml
# 钉钉需要使用 webhook 转发
receivers:
  - name: 'dingtalk-sre'
    webhook_configs:
      - url: 'http://dingtalk-webhook:8060/dingtalk/ops/send'
        send_resolved: true
        http_config:
          bearer_token: 'dingtalk-token'
```

#### 6.6 PagerDuty 通知

```yaml
# PagerDuty 接收者配置
receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'pagerduty-service-key'
        send_resolved: true
        description: '{{ template "pagerduty.description" . }}'
        severity: '{{ if eq .Status "firing" }}critical{{ else }}info{{ end }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'
```

### 7. 告警模板

#### 7.1 模板语法

```
Alertmanager 模板语法：

  ┌──────────────────────────────────────────────────────────────┐
  │                    Go 模板语法                                │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  变量：                                                      │
  │  ├── .Status        - 告警状态（firing/resolved）            │
  │  ├── .Alerts        - 告警列表                               │
  │  ├── .Alert         - 单个告警                               │
  │  ├── .Labels        - 标签                                   │
  │  ├── .Annotations   - 注解                                   │
  │  ├── .StartsAt      - 开始时间                               │
  │  ├── .EndsAt        - 结束时间                               │
  │  ├── .GeneratorURL  - 告警来源 URL                           │
  │  └── .Firing        - 触发中的告警                           │
  │                                                              │
  │  函数：                                                      │
  │  ├── {{ .Labels.alertname }}  - 获取标签值                   │
  │  ├── {{ .Annotations.summary }} - 获取注解值                 │
  │  ├── {{ len .Alerts }}        - 告警数量                     │
  │  ├── {{ range .Alerts }}      - 遍历告警                     │
  │  ├── {{ if eq .Status "firing" }} - 条件判断                 │
  │  └── {{ template "name" . }}  - 调用模板                     │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 7.2 通用模板

```yaml
# alertmanager.yml 中定义模板
templates:
  - '/etc/alertmanager/templates/*.tmpl'

# 通用模板示例
# /etc/alertmanager/templates/common.tmpl

{{ define "common.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "common.text" }}
{{ range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Status:* {{ .Status }}
*Severity:* {{ .Labels.severity }}
*Job:* {{ .Labels.job }}
*Instance:* {{ .Labels.instance }}
*Description:* {{ .Annotations.description }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}
{{ if .EndsAt }}*Ended:* {{ .EndsAt.Format "2006-01-02 15:04:05" }}{{ end }}
*Details:*
{{ range .Labels.SortedPairs }}  - {{ .Name }}: {{ .Value }}
{{ end }}
---
{{ end }}
{{ end }}
```

#### 7.3 Slack 模板

```yaml
# Slack 模板
{{ define "slack.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "slack.text" }}
{{ range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Status:* {{ .Status | toUpper }}
*Severity:* {{ .Labels.severity | toUpper }}
*Job:* {{ .Labels.job }}
*Instance:* {{ .Labels.instance }}
*Description:* {{ .Annotations.description }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}
*Details:*
{{ range .Labels.SortedPairs }}  • {{ .Name }}: {{ .Value }}
{{ end }}
{{ end }}
{{ end }}
```

#### 7.4 Email 模板

```yaml
# Email 模板
{{ define "email.subject" }}
[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }} - {{ .GroupLabels.job }}
{{ end }}

{{ define "email.html" }}
<html>
<body>
<h2>Alert Notification</h2>
<table border="1" cellpadding="5" cellspacing="0">
  <tr>
    <th>Status</th>
    <th>Alert Name</th>
    <th>Severity</th>
    <th>Job</th>
    <th>Instance</th>
    <th>Description</th>
    <th>Started</th>
  </tr>
  {{ range .Alerts }}
  <tr>
    <td>{{ .Status | toUpper }}</td>
    <td>{{ .Labels.alertname }}</td>
    <td>{{ .Labels.severity | toUpper }}</td>
    <td>{{ .Labels.job }}</td>
    <td>{{ .Labels.instance }}</td>
    <td>{{ .Annotations.description }}</td>
    <td>{{ .StartsAt.Format "2006-01-02 15:04:05" }}</td>
  </tr>
  {{ end }}
</table>
<p>Total Alerts: {{ .Alerts | len }}</p>
</body>
</html>
{{ end }}
```

### 8. 高可用配置

#### 8.1 集群模式

```
Alertmanager 集群模式：

  ┌──────────────────────────────────────────────────────────────┐
  │                    Alertmanager 集群                          │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │   │ Alertmanager │  │ Alertmanager │  │ Alertmanager │     │
  │   │    实例 1    │  │    实例 2    │  │    实例 3    │     │
  │   │              │  │              │  │              │     │
  │   │  :9093       │  │  :9093       │  │  :9093       │     │
  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
  │          │                 │                 │               │
  │          └─────────────────┼─────────────────┘               │
  │                            │                                 │
  │                     Gossip 协议                              │
  │                     告警去重                                 │
  │                     状态同步                                 │
  │                                                              │
  │  Prometheus 配置：                                           │
  │  alerting:                                                   │
  │    alertmanagers:                                            │
  │      - static_configs:                                       │
  │          - targets:                                           │
  │            - alertmanager-1:9093                             │
  │            - alertmanager-2:9093                             │
  │            - alertmanager-3:9093                             │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 8.2 高可用配置

```yaml
# Alertmanager 高可用配置
# alertmanager.yml
global:
  resolve_timeout: 5m

# 集群配置
cluster:
  listen-address: "0.0.0.0:9094"
  peers:
    - alertmanager-1:9094
    - alertmanager-2:9094
    - alertmanager-3:9094
  settle_timeout: 15s

route:
  receiver: 'default-slack'
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default-slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
        channel: '#alerts'
```

```bash
# Docker Compose 高可用部署
version: '3.8'

services:
  alertmanager-1:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager-1
    ports:
      - "9093:9093"
      - "9094:9094"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--cluster.listen-address=0.0.0.0:9094'
      - '--cluster.peer=alertmanager-2:9094'
      - '--cluster.peer=alertmanager-3:9094'

  alertmanager-2:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager-2
    ports:
      - "9095:9093"
      - "9096:9094"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--cluster.listen-address=0.0.0.0:9094'
      - '--cluster.peer=alertmanager-1:9094'
      - '--cluster.peer=alertmanager-3:9094'

  alertmanager-3:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager-3
    ports:
      - "9097:9093"
      - "9098:9094"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--cluster.listen-address=0.0.0.0:9094'
      - '--cluster.peer=alertmanager-1:9094'
      - '--cluster.peer=alertmanager-2:9094'
```

### 9. 告警最佳实践

#### 9.1 告警分级

```
告警分级最佳实践：

  ┌──────────────────────────────────────────────────────────────┐
  │                    告警分级                                    │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  P0 - 致命（Critical）                                       │
  │  ├── 服务完全不可用                                          │
  │  ├── 数据丢失风险                                            │
  │  ├── 安全漏洞                                                │
  │  ├── 响应时间：5 分钟                                        │
  │  └── 通知方式：电话 + 短信 + 即时通讯                        │
  │                                                              │
  │  P1 - 严重（High）                                           │
  │  ├── 服务部分不可用                                          │
  │  ├── 性能严重下降                                            │
  │  ├── 错误率超过阈值                                          │
  │  ├── 响应时间：15 分钟                                       │
  │  └── 通知方式：短信 + 即时通讯                               │
  │                                                              │
  │  P2 - 一般（Medium）                                         │
  │  ├── 服务性能下降                                            │
  │  ├── 资源使用率过高                                          │
  │  ├── 非核心功能异常                                          │
  │  ├── 响应时间：1 小时                                        │
  │  └── 通知方式：即时通讯                                      │
  │                                                              │
  │  P3 - 低（Low）                                              │
  │  ├── 潜在风险                                                │
  │  ├── 信息性告警                                              │
  │  ├── 响应时间：24 小时                                       │
  │  └── 通知方式：邮件                                          │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 9.2 告警质量

```
告警质量检查清单：

  ✅ 告警应该是可操作的
     ├── 收到告警后，值班人员应该知道该做什么
     └── 如果不知道该做什么，这个告警可能不需要

  ✅ 告警应该是准确的
     ├── 避免误报（false positive）
     ├── 避免漏报（false negative）
     └── 使用合适的阈值和持续时间

  ✅ 告警应该是及时的
     ├── 问题发生后尽快通知
     ├── 避免通知延迟
     └── 使用合适的 group_wait

  ✅ 告警应该是分级的
     ├── 严重告警立即通知
     ├── 一般告警延迟通知
     └── 信息告警批量通知

  ✅ 告警应该是可维护的
     ├── 定期审查告警规则
     ├── 删除无用告警
     └── 更新过时告警
```

#### 9.3 常见问题

```
常见告警问题及解决方案：

  1. 告警风暴
     ├── 问题：大量告警同时触发
     ├── 原因：级联故障、配置错误
     └── 解决：分组、抑制、静默

  2. 误报
     ├── 问题：告警触发但无实际问题
     ├── 原因：阈值设置不当、瞬时波动
     └── 解决：调整阈值、增加 for 时间

  3. 漏报
     ├── 问题：问题发生但未触发告警
     ├── 原因：告警规则缺失、阈值过高
     └── 解决：完善告警规则、降低阈值

  4. 通知疲劳
     ├── 问题：告警太多，值班人员麻木
     ├── 原因：告警质量低、重复告警
     └── 解决：提高告警质量、减少重复

  5. 告警延迟
     ├── 问题：问题发生很久才收到告警
     ├── 原因：group_wait 过长、通知延迟
     └── 解决：优化分组配置、使用即时通讯
```

---

## 💻 实战练习

### 练习 1：配置 Alertmanager

**目标**：完成 Alertmanager 基本配置

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default-slack'
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity = critical
      receiver: 'pagerduty'
      group_wait: 10s
      repeat_interval: 1h
    - matchers:
        - severity = warning
      receiver: 'slack-warnings'

receivers:
  - name: 'default-slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
        channel: '#alerts'
        send_resolved: true

  - name: 'slack-warnings'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
        channel: '#warnings'
        send_resolved: true

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'pagerduty-key'
        send_resolved: true
```

### 练习 2：配置告警模板

**目标**：创建自定义告警模板

```yaml
# /etc/alertmanager/templates/custom.tmpl
{{ define "custom.title" }}
[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "custom.text" }}
{{ range .Alerts }}
Alert: {{ .Labels.alertname }}
Status: {{ .Status | toUpper }}
Severity: {{ .Labels.severity | toUpper }}
Job: {{ .Labels.job }}
Instance: {{ .Labels.instance }}
Description: {{ .Annotations.description }}
Started: {{ .StartsAt.Format "2006-01-02 15:04:05" }}
{{ end }}
{{ end }}
```

### 练习 3：配置告警抑制

**目标**：配置告警抑制规则

```yaml
# alertmanager.yml
inhibit_rules:
  # 节点宕机时，抑制该节点的所有告警
  - source_matchers:
      - alertname = NodeDown
    target_matchers:
      - instance = {{ $labels.instance }}
    equal: ['instance']

  # 严重告警触发时，抑制同一服务的警告
  - source_matchers:
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['alertname', 'job']
```

---

## 🎯 面试题精选

### 1. Alertmanager 的核心功能是什么？

**参考答案**：

Alertmanager 的核心功能：
1. **路由**：根据标签将告警路由到不同的接收者
2. **分组**：将相似告警聚合在一起，减少通知数量
3. **抑制**：当高优先级告警触发时，抑制低优先级告警
4. **静默**：在特定时间范围内静默告警
5. **去重**：避免重复发送相同告警
6. **通知**：支持多种通知渠道（Slack、Email、PagerDuty 等）

### 2. 告警分组的 group_wait、group_interval、repeat_interval 有什么区别？

**参考答案**：

- **group_wait**：首次告警触发后等待的时间，用于收集同一组的其他告警
- **group_interval**：同一组内，两个告警之间的最小间隔
- **repeat_interval**：同一告警重复发送的间隔

示例：
- group_wait: 30s（等待 30 秒收集同组告警）
- group_interval: 5m（同组告警间隔至少 5 分钟）
- repeat_interval: 4h（同一告警每 4 小时重复一次）

### 3. 什么是告警抑制？如何配置？

**参考答案**：

告警抑制是指当某个告警触发时，自动抑制相关告警。

常见场景：
- 节点宕机时，抑制该节点上的所有告警
- 严重告警触发时，抑制同一服务的警告

配置方式：
```yaml
inhibit_rules:
  - source_matchers:
      - alertname = NodeDown
    target_matchers:
      - severity = warning
    equal: ['instance']
```

### 4. 如何实现 Alertmanager 高可用？

**参考答案**：

Alertmanager 高可用通过集群模式实现：
1. 部署多个 Alertmanager 实例（通常 3 个）
2. 配置 Gossip 协议进行状态同步
3. Prometheus 发送告警到所有实例
4. 实例之间自动去重

配置要点：
- cluster.listen-address：集群监听地址
- cluster.peer：集群成员地址
- settle_timeout：集群稳定等待时间

### 5. 告警模板有哪些常用变量？

**参考答案**：

常用变量：
- `.Status`：告警状态（firing/resolved）
- `.Alerts`：告警列表
- `.Labels`：标签
- `.Annotations`：注解
- `.StartsAt`：开始时间
- `.EndsAt`：结束时间
- `.GroupLabels`：分组标签

常用函数：
- `{{ .Labels.alertname }}`：获取标签值
- `{{ len .Alerts }}`：告警数量
- `{{ range .Alerts }}`：遍历告警
- `{{ if eq .Status "firing" }}`：条件判断

---

## 📚 深入阅读

1. **Alertmanager 官方文档** - https://prometheus.io/docs/alerting/latest/alertmanager/
2. **Alertmanager 配置** - https://prometheus.io/docs/alerting/latest/configuration/
3. **Alertmanager 模板** - https://prometheus.io/docs/alerting/latest/notifications/
4. **Alertmanager API** - https://prometheus.io/docs/alerting/latest/clients/

---

## ✅ 自检清单

- [ ] 理解 Alertmanager 的架构和工作原理
- [ ] 掌握告警路由的配置方式
- [ ] 理解告警分组、抑制和静默机制
- [ ] 能够配置多种通知渠道
- [ ] 了解 Alertmanager 高可用配置
- [ ] 掌握告警模板的编写
- [ ] 理解告警最佳实践
- [ ] 能够解决常见告警问题
