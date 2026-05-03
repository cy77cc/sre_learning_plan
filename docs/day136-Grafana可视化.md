# Day 136: Grafana 可视化

> 📅 日期：2026-05-03
> 📖 学习主题：Grafana 安装、数据源、仪表盘设计、变量、告警、Provisioning、最佳实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 134 (Prometheus 基础), Day 135 (PromQL 查询语言)

---

## 🎯 学习目标

- 掌握 Grafana 的安装和基本配置
- 理解 Grafana 数据源的配置方式
- 掌握仪表盘设计原则和常用面板类型
- 能够使用变量实现动态仪表盘
- 了解 Grafana Alerting 的配置方式
- 掌握 Provisioning 实现配置即代码

---

## 📖 核心知识点

### 1. Grafana 概述

#### 1.1 什么是 Grafana

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Grafana 可观测性平台                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Grafana 是开源的数据可视化和监控平台，支持多种数据源：              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Prometheus  │  │    Loki      │  │   Jaeger     │              │
│  │  指标数据    │  │  日志数据    │  │  链路追踪    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                        │
│         └─────────────────┼─────────────────┘                        │
│                           │                                          │
│                           ▼                                          │
│                  ┌──────────────────┐                                │
│                  │     Grafana      │                                │
│                  │                  │                                │
│                  │  - 仪表盘        │                                │
│                  │  - 面板          │                                │
│                  │  - 告警          │                                │
│                  │  - 变量          │                                │
│                  │  - 注释          │                                │
│                  │  - Provisioning  │                                │
│                  └──────────────────┘                                │
│                                                                     │
│  核心特性：                                                          │
│  ├── 多数据源支持（Prometheus、Loki、Elasticsearch 等）            │
│  ├── 丰富的可视化类型（图表、表格、仪表盘、地图等）                │
│  ├── 灵活的变量和模板系统                                          │
│  ├── 告警和通知集成                                                │
│  ├── 用户权限管理                                                  │
│  ├── Provisioning（配置即代码）                                    │
│  └── 插件生态系统                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 Grafana vs Kibana vs Datadog

```
┌─────────────┬─────────────────┬─────────────────┬─────────────────┐
│ 特性         │ Grafana         │ Kibana          │ Datadog         │
├─────────────┼─────────────────┼─────────────────┼─────────────────┤
│ 类型         │ 开源可视化      │ ES 可视化       │ SaaS 监控       │
│ 数据源       │ 多数据源        │ 仅 ES           │ 多数据源        │
│ 适用场景     │ 指标+日志+追踪 │ 日志分析        │ 全栈监控        │
│ 成本         │ 免费/企业版     │ 免费            │ 按主机收费      │
│ 扩展性       │ 插件丰富        │ ES 生态         │ 一站式          │
│ 部署方式     │ 自托管/云       │ 自托管          │ 仅 SaaS         │
└─────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 2. 安装与配置

#### 2.1 安装方式

```bash
# 1. Docker 安装（推荐开发环境）
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -v grafana_data:/var/lib/grafana \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana:11.0.0

# 2. Docker Compose
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  grafana:
    image: grafana/grafana:11.0.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./provisioning:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  grafana_data:
EOF

# 3. 包管理器安装（Ubuntu/Debian）
sudo apt-get install -y apt-transport-https software-properties-common
wget -q -O - https://apt.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install grafana

# 4. 包管理器安装（CentOS/RHEL）
sudo yum install -y https://dl.grafana.com/oss/release/grafana-11.0.0-1.x86_64.rpm

# 5. 二进制安装
wget https://dl.grafana.com/oss/release/grafana-11.0.0.linux-amd64.tar.gz
tar xvfz grafana-11.0.0.linux-amd64.tar.gz
cd grafana-11.0.0
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
sudo systemctl status grafana-server

# 访问
# 默认地址：http://localhost:3000
# 默认用户：admin
# 默认密码：admin
```

#### 2.2 核心配置

```ini
# /etc/grafana/grafana.ini

[server]
# HTTP 端口
http_port = 3000

# 域名
domain = grafana.example.com

# 根路径（如果使用反向代理）
root_url = %(protocol)s://%(domain)s:%(http_port)s/grafana/

[database]
# 数据库类型（sqlite3、mysql、postgres）
type = sqlite3

# MySQL 配置
# type = mysql
# host = 127.0.0.1:3306
# name = grafana
# user = grafana
# password = secret

[security]
# 管理员用户
admin_user = admin

# 管理员密码
admin_password = admin

# 密码强度
min_password_length = 8

# 禁用注册
disable_gravatar = true

[auth]
# 匿名访问
disable_login_form = false

[auth.anonymous]
# 启用匿名访问
enabled = false

[users]
# 允许注册
allow_sign_up = false

# 默认角色
auto_assign_org = true
auto_assign_org_role = Viewer

[alerting]
# 启用告警
enabled = true

# 告警执行超时
execute_alerts = true

[unified_alerting]
# 统一告警（Grafana 8+）
enabled = true
```

#### 2.3 环境变量配置

```bash
# 使用环境变量覆盖配置
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SERVER_ROOT_URL=http://grafana.example.com \
  -e GF_SECURITY_ADMIN_USER=admin \
  -e GF_SECURITY_ADMIN_PASSWORD=secret \
  -e GF_DATABASE_TYPE=mysql \
  -e GF_DATABASE_HOST=mysql:3306 \
  -e GF_DATABASE_NAME=grafana \
  -e GF_DATABASE_USER=grafana \
  -e GF_DATABASE_PASSWORD=secret \
  grafana/grafana:11.0.0
```

### 3. 数据源配置

#### 3.1 Prometheus 数据源

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: "15s"
      queryTimeout: "60s"
      httpHeaderName1: "Authorization"
    secureJsonData:
      httpHeaderValue1: "Bearer ${PROMETHEUS_TOKEN}"
```

#### 3.2 Loki 数据源（日志）

```yaml
# provisioning/datasources/loki.yml
apiVersion: 1

datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
    jsonData:
      maxLines: 1000
      derivedFields:
        - datasourceUid: prometheus
          matcherRegex: "traceID=(\\w+)"
          name: TraceID
          url: "$${__value.raw}"
```

#### 3.3 多数据源配置

```yaml
# provisioning/datasources/all.yml
apiVersion: 1

datasources:
  # Prometheus - 生产环境
  - name: Prometheus-Prod
    type: prometheus
    access: proxy
    url: http://prometheus-prod:9090
    isDefault: true
    editable: true

  # Prometheus - 测试环境
  - name: Prometheus-Staging
    type: prometheus
    access: proxy
    url: http://prometheus-staging:9090
    editable: true

  # Loki - 日志
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true

  # Jaeger - 链路追踪
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: true
```

### 4. 仪表盘设计

#### 4.1 设计原则

```
┌─────────────────────────────────────────────────────────────────────┐
│                    仪表盘设计原则                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 分层设计（自上而下）                                            │
│     ├── 第一层：概览（Overview）                                    │
│     │   ├── 整体健康状态                                            │
│     │   ├── 关键 SLO 指标                                          │
│     │   └── 重要告警                                                │
│     │                                                               │
│     ├── 第二层：服务（Service）                                     │
│     │   ├── RED 方法指标（Rate, Errors, Duration）                 │
│     │   ├── 资源使用情况                                            │
│     │   └── 依赖服务状态                                            │
│     │                                                               │
│     └── 第三层：详情（Detail）                                      │
│         ├── 单个实例指标                                            │
│         ├── 日志和追踪                                              │
│         └── 配置和变更                                              │
│                                                                     │
│  2. 告诉故事（Tell a Story）                                       │
│     ├── 从左到右，从上到下                                          │
│     ├── 先展示问题，再展示原因                                      │
│     └── 关联指标放在相邻位置                                        │
│                                                                     │
│  3. 保持简洁                                                        │
│     ├── 每个面板一个明确目的                                        │
│     ├── 避免信息过载                                                │
│     └── 使用合适的图表类型                                          │
│                                                                     │
│  4. 使用变量                                                        │
│     ├── 服务名、环境、实例等使用变量                                │
│     ├── 支持动态切换                                                │
│     └── 提高仪表盘复用性                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 常用面板类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Grafana 面板类型                                   │
├──────────────┬──────────────────────────────────────────────────────┤
│ 面板类型      │ 适用场景                                            │
├──────────────┼──────────────────────────────────────────────────────┤
│ Time Series  │ 时间序列数据（默认，最常用）                        │
│ Stat         │ 单一数值（当前值、趋势指示）                        │
│ Gauge        │ 仪表盘（百分比、阈值指示）                          │
│ Bar Gauge    │ 条形仪表盘（多个指标对比）                          │
│ Table        │ 表格数据（多维度展示）                              │
│ Heatmap      │ 热力图（分布、密度）                                │
│ State        │ 状态时间线（告警状态、健康状态）                    │
│ Bar Chart    │ 柱状图（分类对比）                                  │
│ Pie Chart    │ 饼图（占比分析）                                    │
│ Logs         │ 日志面板（Loki 数据源）                             │
│ Node Graph   │ 拓扑图（服务依赖关系）                              │
│ Alert List   │ 告警列表（当前告警状态）                            │
│ Text         │ 文本面板（说明、文档）                              │
└──────────────┴──────────────────────────────────────────────────────┘
```

#### 4.3 面板配置示例

```json
{
  "title": "HTTP Requests per Second",
  "type": "timeseries",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "sum(rate(http_requests_total{job=\"$service\"}[5m])) by (status)",
      "legendFormat": "{{status}}",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "reqps",
      "color": {
        "mode": "palette-classic"
      },
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10,
        "pointSize": 5,
        "showPoints": "auto"
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 1000 },
          { "color": "red", "value": 5000 }
        ]
      }
    }
  },
  "options": {
    "legend": {
      "displayMode": "table",
      "placement": "bottom",
      "calcs": ["last", "max", "mean"]
    },
    "tooltip": {
      "mode": "multi"
    }
  }
}
```

#### 4.4 RED 方法仪表盘

```json
{
  "title": "Service RED Dashboard",
  "panels": [
    {
      "title": "Request Rate",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"$service\"}[5m]))",
          "legendFormat": "QPS"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps",
          "thresholds": {
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 1000 },
              { "color": "red", "value": 5000 }
            ]
          }
        }
      }
    },
    {
      "title": "Error Rate",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"$service\", status=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=\"$service\"}[5m])) * 100",
          "legendFormat": "Error %"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "thresholds": {
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 1 },
              { "color": "red", "value": 5 }
            ]
          }
        }
      }
    },
    {
      "title": "P99 Latency",
      "type": "stat",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=\"$service\"}[5m])) by (le))",
          "legendFormat": "P99"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s",
          "thresholds": {
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 0.3 },
              { "color": "red", "value": 1 }
            ]
          }
        }
      }
    }
  ]
}
```

### 5. 变量（Variables）

#### 5.1 变量类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Grafana 变量类型                                   │
├──────────────┬──────────────────────────────────────────────────────┤
│ 变量类型      │ 说明                                                │
├──────────────┼──────────────────────────────────────────────────────┤
│ Query        │ 从数据源查询值（最常用）                            │
│ Custom       │ 自定义固定值列表                                    │
│ Text box     │ 文本输入框                                          │
│ Constant     │ 常量（隐藏）                                        │
│ Interval     │ 时间间隔（1m, 5m, 1h 等）                           │
│ Data source  │ 数据源选择                                          │
│ Ad hoc       │ 动态标签过滤                                        │
│ Snapshot     │ 快照变量                                            │
└──────────────┴──────────────────────────────────────────────────────┘
```

#### 5.2 变量配置

```json
{
  "templating": {
    "list": [
      {
        "name": "environment",
        "type": "custom",
        "label": "环境",
        "query": "production,staging,development",
        "current": {
          "text": "production",
          "value": "production"
        },
        "includeAll": false,
        "multi": false
      },
      {
        "name": "service",
        "type": "query",
        "label": "服务",
        "datasource": "Prometheus",
        "query": "label_values(http_requests_total{environment=\"$environment\"}, job)",
        "refresh": 2,
        "sort": 1,
        "includeAll": true,
        "allValue": ".*",
        "multi": false,
        "current": {
          "text": "All",
          "value": "$__all"
        }
      },
      {
        "name": "instance",
        "type": "query",
        "label": "实例",
        "datasource": "Prometheus",
        "query": "label_values(http_requests_total{environment=\"$environment\", job=\"$service\"}, instance)",
        "refresh": 2,
        "sort": 1,
        "includeAll": true,
        "allValue": ".*",
        "multi": true,
        "current": {
          "text": "All",
          "value": "$__all"
        }
      },
      {
        "name": "interval",
        "type": "interval",
        "label": "间隔",
        "query": "1m,5m,15m,30m,1h",
        "auto": true,
        "auto_min": "1m",
        "auto_count": 30,
        "current": {
          "text": "5m",
          "value": "5m"
        }
      },
      {
        "name": "quantile",
        "type": "custom",
        "label": "分位数",
        "query": "0.5,0.9,0.95,0.99",
        "current": {
          "text": "0.99",
          "value": "0.99"
        }
      }
    ]
  }
}
```

#### 5.3 变量查询函数

```promql
# label_values() - 获取标签值
label_values(http_requests_total, job)
label_values(http_requests_total{environment="production"}, job)
label_values(up{job="node"}, instance)

# query_result() - 获取查询结果
query_result(sum(rate(http_requests_total[5m])) by (job))

# metric_names() - 获取指标名称
metric_names(http_.*)

# label_names() - 获取标签名称
label_names(http_requests_total)
```

#### 5.4 变量使用

```promql
# 在查询中使用变量
rate(http_requests_total{job="$service"}[$interval])

# 使用多选变量
rate(http_requests_total{job=~"$service"}[$interval])

# 使用变量进行过滤
rate(http_requests_total{job="$service", instance=~"$instance"}[$interval])

# 在面板标题中使用
"HTTP Requests - $service ($environment)"

# 在 Legend 中使用
"{{instance}} - {{status}}"
```

### 6. Grafana Alerting

#### 6.1 告警规则

```yaml
# provisioning/alerting/rules.yml
apiVersion: 1

groups:
  - orgId: 1
    name: Service Alerts
    folder: SRE
    interval: 1m
    rules:
      - uid: high-error-rate
        title: High Error Rate
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              expr: |
                sum(rate(http_requests_total{status=~"5.."}[5m]))
                /
                sum(rate(http_requests_total[5m]))
              instant: true
          - refId: B
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: __expr__
            model:
              type: threshold
              expression: A
              conditions:
                - evaluator:
                    type: gt
                    params: [0.05]
                  operator:
                    type: and
                  query:
                    params: [B]
                  reducer:
                    type: last
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
```

#### 6.2 联系点（Contact Points）

```yaml
# provisioning/alerting/contactpoints.yml
apiVersion: 1

contactPoints:
  - orgId: 1
    name: slack-sre
    receivers:
      - uid: slack-channel
        type: slack
        settings:
          url: https://hooks.slack.com/services/xxx/yyy/zzz
          recipient: "#sre-alerts"
          title: "{{ template \"default.title\" . }}"
          message: "{{ template \"default.message\" . }}"
        disableResolveMessage: false

  - orgId: 1
    name: email-sre
    receivers:
      - uid: email-sre-team
        type: email
        settings:
          addresses: sre-team@example.com
          singleEmail: false
        disableResolveMessage: false

  - orgId: 1
    name: pagerduty-sre
    receivers:
      - uid: pagerduty-critical
        type: pagerduty
        settings:
          integrationKey: ${PAGERDUTY_KEY}
          severity: critical
        disableResolveMessage: false
```

#### 6.3 通知策略（Notification Policies）

```yaml
# provisioning/alerting/policies.yml
apiVersion: 1

policies:
  - orgId: 1
    receiver: slack-sre
    group_by: ['alertname', 'job']
    group_wait: 30s
    group_interval: 5m
    repeat_interval: 4h
    routes:
      - receiver: pagerduty-sre
        matchers:
          - severity = critical
        group_wait: 10s
        repeat_interval: 1h
      - receiver: email-sre
        matchers:
          - severity = warning
        group_wait: 5m
        repeat_interval: 4h
```

### 7. Provisioning（配置即代码）

#### 7.1 目录结构

```
grafana/
├── provisioning/
│   ├── datasources/
│   │   ├── prometheus.yml
│   │   ├── loki.yml
│   │   └── jaeger.yml
│   ├── dashboards/
│   │   ├── dashboard.yml
│   │   └── dashboards/
│   │       ├── node-overview.json
│   │       ├── service-red.json
│   │       └── kubernetes-overview.json
│   ├── alerting/
│   │   ├── rules.yml
│   │   ├── contactpoints.yml
│   │   └── policies.yml
│   └── plugins/
│       └── plugins.yml
└── grafana.ini
```

#### 7.2 Dashboard Provisioning

```yaml
# provisioning/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: 'SRE'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/dashboards
      foldersFromFilesStructure: true
```

#### 7.3 完整 Provisioning 示例

```yaml
# docker-compose.yml
version: '3.8'

services:
  grafana:
    image: grafana/grafana:11.0.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./provisioning/datasources:/etc/grafana/provisioning/datasources
      - ./provisioning/dashboards:/etc/grafana/provisioning/dashboards
      - ./provisioning/alerting:/etc/grafana/provisioning/alerting
    restart: unless-stopped

volumes:
  grafana_data:
```

### 8. 最佳实践

#### 8.1 仪表盘命名规范

```
仪表盘命名规范：

  格式：[团队]-[服务]-[层级]-[视角]

  层级：
  ├── Overview  - 全局概览
  ├── Service   - 服务级别
  ├── Instance  - 实例级别
  └── Detail    - 详细信息

  视角：
  ├── RED       - Rate, Errors, Duration
  ├── USE       - Utilization, Saturation, Errors
  ├── SLO       - Service Level Objectives
  └── Capacity  - 容量规划

  示例：
  ├── platform-overview-RED
  ├── backend-user-service-RED
  ├── platform-node-USE
  ├── backend-user-service-SLO
  └── platform-node-capacity
```

#### 8.2 面板命名规范

```
面板命名规范：

  格式：[指标类型] - [聚合方式] - [时间范围]

  示例：
  ├── HTTP Requests - Rate - 5m
  ├── HTTP Errors - Rate - 5m
  ├── HTTP Latency - P99 - 5m
  ├── CPU Usage - Avg - 5m
  ├── Memory Usage - Current
  └── Disk Usage - Current

  Legend 格式：
  ├── {{instance}} - {{status}}
  ├── {{job}} - {{method}}
  └── {{instance}} - {{mountpoint}}
```

#### 8.3 性能优化

```
Grafana 性能优化：

  1. 使用 Recording Rules
     ├── 预计算复杂查询
     ├── 减少实时计算
     └── 提高 Dashboard 加载速度

  2. 合理设置时间范围
     ├── 默认时间范围：1h 或 6h
     ├── 避免过长的时间范围（>7d）
     └── 使用变量控制时间范围

  3. 限制面板数量
     ├── 每个 Dashboard 最多 20-30 个面板
     ├── 使用行（Row）组织面板
     └── 考虑使用 Dashboard 链接

  4. 优化查询
     ├── 使用 Recording Rules 替代复杂查询
     ├── 避免高基数聚合
     └── 使用 $__rate_interval 替代固定间隔

  5. 缓存配置
     ├── 启用查询缓存
     ├── 合理设置缓存时间
     └── 使用 CDN 缓存静态资源
```

### 9. 常用仪表盘

#### 9.1 Node Exporter 仪表盘

```
推荐 Dashboard ID：
├── 1860  - Node Exporter Full（最全面）
├── 11074 - Node Exporter（简洁版）
└── 13978 - Node Exporter（中文版）

关键面板：
├── CPU 使用率
├── 内存使用率
├── 磁盘使用率
├── 磁盘 IO
├── 网络流量
├── 系统负载
└── 系统运行时间
```

#### 9.2 应用 RED 仪表盘

```json
{
  "title": "Application RED Dashboard",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"$service\"}[$interval])) by (status)",
          "legendFormat": "{{status}}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"$service\", status=~\"5..\"}[$interval])) / sum(rate(http_requests_total{job=\"$service\"}[$interval]))",
          "legendFormat": "Error Rate"
        }
      ]
    },
    {
      "title": "Latency Distribution",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.5, sum(rate(http_request_duration_seconds_bucket{job=\"$service\"}[$interval])) by (le))",
          "legendFormat": "P50"
        },
        {
          "expr": "histogram_quantile(0.9, sum(rate(http_request_duration_seconds_bucket{job=\"$service\"}[$interval])) by (le))",
          "legendFormat": "P90"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=\"$service\"}[$interval])) by (le))",
          "legendFormat": "P99"
        }
      ]
    }
  ]
}
```

---

## 💻 实战练习

### 练习 1：安装 Grafana 并配置 Prometheus 数据源

**目标**：完成 Grafana 安装，配置 Prometheus 数据源

```bash
# 步骤 1：启动 Grafana
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana:11.0.0

# 步骤 2：访问 Grafana
# 打开 http://localhost:3000
# 用户名：admin，密码：admin

# 步骤 3：添加 Prometheus 数据源
# Configuration -> Data Sources -> Add data source
# Type: Prometheus
# URL: http://prometheus:9090
# Save & Test

# 步骤 4：导入 Node Exporter 仪表盘
# Dashboards -> Import
# Dashboard ID: 1860
# Load
```

### 练习 2：创建带变量的自定义仪表盘

**目标**：创建一个带变量的 RED 方法仪表盘

```json
{
  "dashboard": {
    "title": "Service RED Dashboard",
    "templating": {
      "list": [
        {
          "name": "service",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(http_requests_total, job)",
          "refresh": 2,
          "includeAll": true
        }
      ]
    },
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{job=~\"$service\"}[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{job=~\"$service\", status=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=~\"$service\"}[5m])) * 100"
          }
        ]
      },
      {
        "title": "P99 Latency",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=~\"$service\"}[5m])) by (le))"
          }
        ]
      }
    ]
  }
}
```

### 练习 3：配置 Provisioning

**目标**：使用 Provisioning 自动化 Grafana 配置

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
```

```yaml
# provisioning/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: 'SRE'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards/dashboards
```

---

## 🎯 面试题精选

### 1. Grafana 的核心特性是什么？

**参考答案**：

Grafana 的核心特性包括：
1. 多数据源支持（Prometheus、Loki、Elasticsearch、MySQL 等）
2. 丰富的可视化类型（时间序列、统计、表格、热力图等）
3. 灵活的变量和模板系统
4. 告警和通知集成
5. 用户权限管理
6. Provisioning（配置即代码）
7. 插件生态系统

### 2. 如何设计一个好的监控仪表盘？

**参考答案**：

好的仪表盘设计应该：
1. **分层设计**：概览 → 服务 → 详情
2. **告诉故事**：从左到右，从上到下，先展示问题再展示原因
3. **保持简洁**：每个面板一个明确目的，避免信息过载
4. **使用变量**：提高复用性，支持动态切换
5. **遵循命名规范**：统一的命名方式
6. **关联指标**：相关指标放在相邻位置

### 3. Grafana 的变量有哪些类型？各适用于什么场景？

**参考答案**：

- **Query**：从数据源查询值，最常用，如获取服务列表
- **Custom**：自定义固定值列表，如环境选择
- **Text box**：文本输入框，如搜索关键词
- **Interval**：时间间隔，如 1m、5m、1h
- **Data source**：数据源选择
- **Ad hoc**：动态标签过滤

### 4. 什么是 Provisioning？有什么优势？

**参考答案**：

Provisioning 是 Grafana 的配置即代码功能，通过 YAML 文件定义数据源、仪表盘、告警等配置。

优势：
1. 版本控制：配置可以纳入 Git 管理
2. 自动化：通过 CI/CD 自动部署
3. 一致性：确保环境配置一致
4. 可审计：配置变更有记录
5. 可恢复：可以快速恢复配置

### 5. RED 方法和 USE 方法有什么区别？

**参考答案**：

- **RED 方法**（Rate, Errors, Duration）：用于面向请求的服务
  - Rate：每秒请求数
  - Errors：错误率
  - Duration：请求延迟

- **USE 方法**（Utilization, Saturation, Errors）：用于基础设施资源
  - Utilization：资源使用率
  - Saturation：资源饱和度
  - Errors：资源错误

选择依据：面向请求的服务用 RED，基础设施资源用 USE。

---

## 📚 深入阅读

1. **Grafana 官方文档** - https://grafana.com/docs/
2. **Grafana 仪表盘设计** - https://grafana.com/docs/grafana/latest/dashboards/
3. **Grafana Provisioning** - https://grafana.com/docs/grafana/latest/administration/provisioning/
4. **Grafana Alerting** - https://grafana.com/docs/grafana/latest/alerting/
5. **Grafana 社区仪表盘** - https://grafana.com/grafana/dashboards/

---

## ✅ 自检清单

- [ ] 能够安装和配置 Grafana
- [ ] 能够配置 Prometheus 数据源
- [ ] 理解仪表盘设计原则
- [ ] 能够创建带变量的仪表盘
- [ ] 了解常用面板类型和适用场景
- [ ] 能够配置 Grafana Alerting
- [ ] 掌握 Provisioning 的使用
- [ ] 理解 RED 方法和 USE 方法
- [ ] 能够导入和自定义社区仪表盘
- [ ] 了解性能优化技巧
