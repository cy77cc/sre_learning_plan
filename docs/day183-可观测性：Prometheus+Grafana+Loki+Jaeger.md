# Day 183: 可观测性栈部署 — Prometheus + Grafana + Loki + Jaeger

> 📅 日期：2026-05-06
> 📖 学习主题：完整可观测性栈部署、自定义指标、告警规则、仪表盘、日志收集、链路追踪
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 130-140 (Prometheus/Grafana), Day 182 (微服务部署)

---

## 🎯 学习目标

完成 Day 183 的学习后，你应该能够：

1. 使用 Helm 部署完整的可观测性栈
2. 配置 Prometheus 自定义指标和告警规则
3. 创建 Grafana Dashboard 并配置数据源联动
4. 部署 Loki + Promtail 实现日志收集
5. 部署 Jaeger + OpenTelemetry Collector 实现链路追踪
6. 验证 Metrics -> Logs -> Traces 三支柱联动排查流程

---

## 📖 核心知识点

### 1. 可观测性架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Grafana (Dashboard)                     │   │
│  │    Metrics ←──→ Logs ←──→ Traces (三支柱联动)             │   │
│  └────────┬──────────────┬──────────────┬──────────────────┘   │
│           │              │              │                       │
│  ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐               │
│  │  Prometheus    │ │  Loki   │ │   Jaeger    │               │
│  │  (Metrics)     │ │ (Logs)  │ │  (Traces)   │               │
│  └────────┬───────┘ └────┬────┘ └──────┬──────┘               │
│           │              │              │                       │
│  ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐               │
│  │ AlertManager   │ │Promtail │ │  OTel Coll. │               │
│  │ (Alerting)     │ │(Agents) │ │ (Collectors)│               │
│  └────────────────┘ └─────────┘ └─────────────┘               │
│                                                                 │
│  数据流:                                                        │
│  App → /metrics → Prometheus → AlertManager → Slack/PagerDuty  │
│  App → stdout → Promtail → Loki → Grafana Logs                 │
│  App → OTLP → OTel Collector → Jaeger → Grafana Traces         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Helm Values 配置

#### 2.1 Prometheus (kube-prometheus-stack)

```yaml
# infrastructure/helm/prometheus/values.yaml
# kube-prometheus-stack Helm Chart Values

# ============================================================
# Prometheus 配置
# ============================================================
prometheus:
  prometheusSpec:
    retention: 15d
    retentionSize: "10GB"

    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: "2"
        memory: 4Gi

    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi

    # 监控所有 ServiceMonitor
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    ruleSelectorNilUsesHelmValues: false

    # 附加抓取配置
    additionalScrapeConfigs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__
          - source_labels: [__meta_kubernetes_namespace]
            action: replace
            target_label: kubernetes_namespace
          - source_labels: [__meta_kubernetes_pod_name]
            action: replace
            target_label: kubernetes_pod_name

# ============================================================
# AlertManager 配置
# ============================================================
alertmanager:
  alertmanagerSpec:
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 256Mi

  config:
    global:
      resolve_timeout: 5m
      slack_api_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

    route:
      group_by: ['alertname', 'namespace', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'slack-notifications'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty-critical'
          continue: true
        - match:
            severity: warning
          receiver: 'slack-warnings'

    receivers:
      - name: 'slack-notifications'
        slack_configs:
          - channel: '#sre-alerts'
            send_resolved: true
            title: '{{ .GroupLabels.alertname }}'
            text: >-
              {{ range .Alerts }}
              *Alert:* {{ .Annotations.summary }}
              *Description:* {{ .Annotations.description }}
              *Severity:* {{ .Labels.severity }}
              *Namespace:* {{ .Labels.namespace }}
              {{ end }}

      - name: 'slack-warnings'
        slack_configs:
          - channel: '#sre-warnings'
            send_resolved: true
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

      - name: 'pagerduty-critical'
        pagerduty_configs:
          - service_key: 'YOUR-PAGERDuty-KEY'
            severity: '{{ .GroupLabels.severity }}'

    inhibit_rules:
      - source_match:
          severity: 'critical'
        target_match:
          severity: 'warning'
        equal: ['alertname', 'namespace']

# ============================================================
# Grafana 配置
# ============================================================
grafana:
  enabled: true
  adminPassword: "admin123"

  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

  persistence:
    enabled: true
    size: 10Gi

  # 数据源配置
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
        - name: Prometheus
          type: prometheus
          url: http://prometheus-kube-prometheus-prometheus:9090
          access: proxy
          isDefault: true
          editable: false

        - name: Loki
          type: loki
          url: http://loki:3100
          access: proxy
          editable: false
          jsonData:
            maxLines: 1000

        - name: Jaeger
          type: jaeger
          url: http://jaeger-query:16686
          access: proxy
          editable: false

  # Dashboard 配置
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
        - name: 'default'
          orgId: 1
          folder: ''
          type: file
          disableDeletion: false
          editable: true
          options:
            path: /var/lib/grafana/dashboards/default

  dashboards:
    default:
      # Node Exporter Dashboard
      node-exporter:
        gnetId: 1860
        revision: 33
        datasource: Prometheus

      # Kubernetes Cluster Dashboard
      kubernetes-cluster:
        gnetId: 7249
        revision: 1
        datasource: Prometheus

      # Nginx Ingress Dashboard
      nginx-ingress:
        gnetId: 9614
        revision: 1
        datasource: Prometheus

  # Grafana 插件
  plugins:
    - grafana-piechart-panel
    - grafana-clock-panel

# ============================================================
# Node Exporter
# ============================================================
nodeExporter:
  enabled: true

# ============================================================
# Kube State Metrics
# ============================================================
kubeStateMetrics:
  enabled: true

# ============================================================
# 自定义告警规则
# ============================================================
additionalPrometheusRulesMap:
  pod-alerts:
    groups:
      - name: pod-alerts
        rules:
          - alert: PodCrashLooping
            expr: rate(kube_pod_container_status_restarts_total[15m]) * 60 * 5 > 0
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
              description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} has been restarting more than 5 times in 15 minutes"

          - alert: PodNotReady
            expr: kube_pod_status_ready{condition="true"} == 0
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready"
              description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} has been in a non-ready state for more than 5 minutes"

          - alert: PodMemoryUsageHigh
            expr: |
              sum by (namespace, pod) (container_memory_working_set_bytes{container!=""})
              / sum by (namespace, pod) (kube_pod_container_resource_limits{resource="memory"})
              > 0.9
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} memory usage is high"
              description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} memory usage is above 90%"

          - alert: PodCPUUsageHigh
            expr: |
              sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))
              / sum by (namespace, pod) (kube_pod_container_resource_limits{resource="cpu"})
              > 0.9
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} CPU usage is high"
              description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} CPU usage is above 90%"

  application-alerts:
    groups:
      - name: application-alerts
        rules:
          - alert: HighErrorRate
            expr: |
              sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[5m]))
              / sum by (namespace, service) (rate(http_requests_total[5m]))
              > 0.05
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "High error rate on {{ $labels.service }}"
              description: "Service {{ $labels.namespace }}/{{ $labels.service }} has error rate above 5% ({{ $value }})"

          - alert: HighLatency
            expr: |
              histogram_quantile(0.95, sum by (namespace, service, le) (rate(http_request_duration_seconds_bucket[5m]))) > 0.5
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High latency on {{ $labels.service }}"
              description: "Service {{ $labels.namespace }}/{{ $labels.service }} P95 latency is above 500ms ({{ $value }}s)"

          - alert: ServiceDown
            expr: up == 0
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: "Service {{ $labels.instance }} is down"
              description: "Service {{ $labels.instance }} has been down for more than 1 minute"

  node-alerts:
    groups:
      - name: node-alerts
        rules:
          - alert: NodeHighCPU
            expr: |
              100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
            for: 10m
            labels:
              severity: warning
            annotations:
              summary: "Node {{ $labels.instance }} high CPU usage"
              description: "Node {{ $labels.instance }} CPU usage is above 80% ({{ $value }}%)"

          - alert: NodeHighMemory
            expr: |
              (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 85
            for: 10m
            labels:
              severity: warning
            annotations:
              summary: "Node {{ $labels.instance }} high memory usage"
              description: "Node {{ $labels.instance }} memory usage is above 85% ({{ $value }}%)"

          - alert: NodeDiskSpaceLow
            expr: |
              (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 > 85
            for: 10m
            labels:
              severity: warning
            annotations:
              summary: "Node {{ $labels.instance }} low disk space"
              description: "Node {{ $labels.instance }} disk usage is above 85% ({{ $value }}%)"
```

#### 2.2 Loki

```yaml
# infrastructure/helm/loki/values.yaml

loki:
  auth_enabled: false

  commonConfig:
    replication_factor: 1

  storage:
    type: filesystem

  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h

  limits_config:
    retention_period: 168h  # 7 天
    max_query_series: 5000
    max_query_parallelism: 4

  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: "1"
      memory: 1Gi

  persistence:
    enabled: true
    size: 50Gi
    storageClassName: gp3

# ============================================================
# Promtail 配置
# ============================================================
promtail:
  enabled: true

  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push

    snippets:
      pipelineStages:
        - cri: {}
        - json:
            expressions:
              level: level
              msg: msg
              trace_id: trace_id
              span_id: span_id
        - labels:
            level:
            trace_id:
            span_id
        - metrics:
            total_lines:
              type: Counter
              description: "total number of log lines"
              config:
                match_all: true
            log_lines_with_trace:
              type: Counter
              description: "log lines with trace_id"
              config:
                source: trace_id
                value: ".*"
        - output:
            source: output

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

  tolerations:
    - effect: NoSchedule
      operator: Exists
```

#### 2.3 Jaeger

```yaml
# infrastructure/helm/jaeger/values.yaml

provisionDataStore:
  cassandra: false
  elasticsearch: false
  kafka: false

storage:
  type: badger

agent:
  enabled: true
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

collector:
  enabled: true
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

  service:
    type: ClusterIP
    grpc:
      port: 14250
    http:
      port: 14268
    otlp:
      grpc:
        name: otlp-grpc
        port: 4317
      http:
        name: otlp-http
        port: 4318

query:
  enabled: true
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

  service:
    type: ClusterIP
    port: 16686
```

### 3. OpenTelemetry Collector 配置

```yaml
# observability/jaeger/otel-collector.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  otel-collector-config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

      prometheus:
        config:
          scrape_configs:
            - job_name: 'otel-collector'
              scrape_interval: 10s
              static_configs:
                - targets: ['localhost:8888']

    processors:
      batch:
        timeout: 1s
        send_batch_size: 1024

      memory_limiter:
        check_interval: 1s
        limit_mib: 512
        spike_limit_mib: 128

      attributes:
        actions:
          - key: environment
            value: dev
            action: upsert

      resource:
        attributes:
          - key: service.namespace
            value: sre-capstone
            action: upsert

    exporters:
      logging:
        loglevel: info

      otlp/jaeger:
        endpoint: jaeger-collector:4317
        tls:
          insecure: true

      prometheus:
        endpoint: "0.0.0.0:8889"
        namespace: otel

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
      zpages:
        endpoint: 0.0.0.0:55679

    service:
      extensions: [health_check, zpages]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch, attributes, resource]
          exporters: [otlp/jaeger, logging]
        metrics:
          receivers: [otlp, prometheus]
          processors: [memory_limiter, batch]
          exporters: [prometheus]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.96.0
          args:
            - --config=/etc/otel-collector-config.yaml
          ports:
            - containerPort: 4317
              name: otlp-grpc
            - containerPort: 4318
              name: otlp-http
            - containerPort: 8889
              name: prometheus
            - containerPort: 13133
              name: health
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /
              port: 13133
          readinessProbe:
            httpGet:
              path: /
              port: 13133
          volumeMounts:
            - name: config
              mountPath: /etc/otel-collector-config.yaml
              subPath: otel-collector-config.yaml
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
    - name: prometheus
      port: 8889
      targetPort: 8889
```

### 4. 自定义 Grafana Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "SRE Capstone - Application Overview",
    "tags": ["sre-capstone", "application"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "title": "Request Rate (per service)",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "sum by (service) (rate(http_requests_total[5m]))",
            "legendFormat": "{{ service }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps",
            "custom": {
              "drawStyle": "line",
              "lineWidth": 2,
              "fillOpacity": 10
            }
          }
        },
        "options": {
          "tooltip": {"mode": "multi"},
          "legend": {"displayMode": "table", "placement": "right"}
        }
      },
      {
        "id": 2,
        "title": "Error Rate (per service)",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "sum by (service) (rate(http_requests_total{status=~\"5..\"}[5m])) / sum by (service) (rate(http_requests_total[5m])) * 100",
            "legendFormat": "{{ service }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 5}
              ]
            }
          }
        }
      },
      {
        "id": 3,
        "title": "P95 Latency (per service)",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))",
            "legendFormat": "{{ service }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 0.3},
                {"color": "red", "value": 0.5}
              ]
            }
          }
        }
      },
      {
        "id": 4,
        "title": "Active Connections",
        "type": "gauge",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [
          {
            "expr": "sum(active_connections)",
            "legendFormat": "Active Connections"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 1000,
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 500},
                {"color": "red", "value": 800}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Pod Status",
        "type": "stat",
        "datasource": "Prometheus",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 16},
        "targets": [
          {
            "expr": "count(kube_pod_status_phase{phase=\"Running\", namespace=\"sre-capstone\"})",
            "legendFormat": "Running"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "thresholds"},
            "thresholds": {
              "steps": [
                {"color": "red", "value": null},
                {"color": "green", "value": 1}
              ]
            }
          }
        }
      },
      {
        "id": 6,
        "title": "CPU Usage (per pod)",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 20},
        "targets": [
          {
            "expr": "sum by (pod) (rate(container_cpu_usage_seconds_total{namespace=\"sre-capstone\", container!=\"\"}[5m]))",
            "legendFormat": "{{ pod }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit"
          }
        }
      },
      {
        "id": 7,
        "title": "Memory Usage (per pod)",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 20},
        "targets": [
          {
            "expr": "sum by (pod) (container_memory_working_set_bytes{namespace=\"sre-capstone\", container!=\"\"}) / 1024 / 1024",
            "legendFormat": "{{ pod }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "decmbytes"
          }
        }
      }
    ]
  }
}
```

### 5. 三支柱联动配置

#### 5.1 Grafana 数据源联动

```yaml
# observability/grafana/provisioning/datasources.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus-kube-prometheus-prometheus:9090
    access: proxy
    isDefault: true
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
        - name: trace_id
          datasourceUid: jaeger

  - name: Loki
    type: loki
    url: http://loki:3100
    access: proxy
    jsonData:
      maxLines: 1000
      derivedFields:
        - datasourceUid: jaeger
          matcherRegex: "trace_id=(\\w+)"
          name: TraceID
          url: "$${__value.raw}"

  - name: Jaeger
    type: jaeger
    url: http://jaeger-query:16686
    access: proxy
    uid: jaeger
```

#### 5.2 联动排查流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    三支柱联动排查流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 指标异常发现 (Prometheus)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Grafana Dashboard 显示:                                 │   │
│  │  - Error Rate: 15% (正常 < 1%)                           │   │
│  │  - P95 Latency: 800ms (正常 < 200ms)                     │   │
│  │  - Pod Count: 3 (正常 2) → HPA 已触发扩容                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 2: 日志定位 (Loki)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  点击异常数据点 → Explore → Loki                          │   │
│  │  查询: {namespace="sre-capstone"} |= "error"             │   │
│  │  发现: "connection refused: database:5432"                │   │
│  │  日志中包含 trace_id: abc123                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 3: 链路追踪 (Jaeger)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  点击 trace_id → 跳转到 Jaeger                            │   │
│  │  查看完整请求链路:                                         │   │
│  │  - user-service → DB 查询 (耗时 500ms)                    │   │
│  │  - DB 连接超时                                            │   │
│  │  - 根因: RDS 连接池耗尽                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  Step 4: 修复并验证                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  - 增加连接池大小                                          │   │
│  │  - 部署修复版本                                            │   │
│  │  - 观察 Dashboard 恢复正常                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6. 部署脚本

```bash
#!/usr/bin/env bash
# scripts/deploy-observability.sh

set -euo pipefail

NAMESPACE="observability"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== 创建命名空间 ==="
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# ============================================================
# 1. 部署 kube-prometheus-stack
# ============================================================
echo "=== 部署 Prometheus + Grafana + AlertManager ==="
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace "${NAMESPACE}" \
  --values "${PROJECT_ROOT}/infrastructure/helm/prometheus/values.yaml" \
  --wait \
  --timeout 10m

# ============================================================
# 2. 部署 Loki + Promtail
# ============================================================
echo "=== 部署 Loki + Promtail ==="
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install loki grafana/loki-stack \
  --namespace "${NAMESPACE}" \
  --values "${PROJECT_ROOT}/infrastructure/helm/loki/values.yaml" \
  --wait \
  --timeout 10m

# ============================================================
# 3. 部署 Jaeger
# ============================================================
echo "=== 部署 Jaeger ==="
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

helm upgrade --install jaeger jaegertracing/jaeger \
  --namespace "${NAMESPACE}" \
  --values "${PROJECT_ROOT}/infrastructure/helm/jaeger/values.yaml" \
  --wait \
  --timeout 10m

# ============================================================
# 4. 部署 OTel Collector
# ============================================================
echo "=== 部署 OpenTelemetry Collector ==="
kubectl apply -f "${PROJECT_ROOT}/observability/jaeger/otel-collector.yaml"

# ============================================================
# 5. 验证部署
# ============================================================
echo ""
echo "=== 验证部署状态 ==="
kubectl get pods -n "${NAMESPACE}"
echo ""
echo "=== 服务列表 ==="
kubectl get svc -n "${NAMESPACE}"

# ============================================================
# 6. 获取访问地址
# ============================================================
echo ""
echo "=== 访问地址 ==="

GRAFANA_LB=$(kubectl get svc -n "${NAMESPACE}" prometheus-grafana \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "使用 port-forward")
echo "Grafana: http://${GRAFANA_LB}:80 (admin/admin123)"

echo ""
echo "Port Forward 命令:"
echo "  kubectl port-forward svc/prometheus-grafana 3000:80 -n ${NAMESPACE}"
echo "  kubectl port-forward svc/jaeger-query 16686:16686 -n ${NAMESPACE}"
echo "  kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n ${NAMESPACE}"
```

---

## 💻 实战练习

### 练习 1：部署完整可观测性栈

**目标**：使用 Helm 部署 Prometheus + Grafana + Loki + Jaeger。

**步骤**：

```bash
# 1. 执行部署脚本
chmod +x scripts/deploy-observability.sh
./scripts/deploy-observability.sh

# 2. 验证所有组件
kubectl get pods -n observability

# 3. 验证 Prometheus targets
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n observability
# 访问 http://localhost:9090/targets 查看所有抓取目标

# 4. 验证 Grafana 数据源
kubectl port-forward svc/prometheus-grafana 3000:80 -n observability
# 访问 http://localhost:3000 → Configuration → Data Sources
```

**验证标准**：
- 所有 Pod 状态为 Running
- Prometheus targets 全部 UP
- Grafana 数据源连接正常
- Dashboard 正常显示数据

### 练习 2：验证告警规则

**目标**：触发告警规则并验证 AlertManager 通知。

**步骤**：

```bash
# 1. 查看告警规则
kubectl get prometheusrules -n observability

# 2. 模拟 Pod 崩溃
kubectl delete pod -n sre-capstone -l app.kubernetes.io/name=user-service

# 3. 观察告警触发
# 访问 Prometheus → Alerts 页面
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n observability

# 4. 查看 AlertManager 状态
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093:9093 -n observability
```

**验证标准**：
- 告警规则加载成功
- Pod 崩溃后告警触发
- AlertManager 收到告警

### 练习 3：三支柱联动排查

**目标**：模拟故障场景，完成 Metrics -> Logs -> Traces 的完整排查流程。

**步骤**：

```bash
# 1. 向应用发送测试请求
INGRESS_ADDR=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 发送带 trace 的请求
curl -H "Host: api.sre-capstone.com" \
     -H "traceparent: 00-$(openssl rand -hex 16)-$(openssl rand -hex 8)-01" \
     "http://${INGRESS_ADDR}/api/users"

# 2. 在 Grafana 中查看指标
# 访问 Grafana → SRE Capstone Dashboard

# 3. 点击异常数据点 → 跳转到 Loki 查看日志

# 4. 从日志中找到 trace_id → 跳转到 Jaeger 查看链路

# 5. 验证三支柱联动完整流程
```

**验证标准**：
- 指标在 Prometheus 中可见
- 日志在 Loki 中可查询
- 链路在 Jaeger 中可追踪
- 三者通过 trace_id 关联

---

## 🎯 面试题精选

### 问题 1：可观测性的三支柱是什么？它们如何协同工作？

**参考答案**：

三支柱：
1. **Metrics (指标)**：数值型时间序列，用于监控趋势和告警
2. **Logs (日志)**：离散事件记录，用于调试和审计
3. **Traces (链路)**：请求在分布式系统中的完整路径

协同工作：
```
告警触发 (Metrics) → 查看相关日志 (Logs) → 追踪请求链路 (Traces) → 定位根因
```

### 问题 2：Prometheus 的数据模型是什么？

**参考答案**：

Prometheus 使用时间序列数据模型：
- 每个时间序列由指标名 + 标签唯一标识
- 数据格式：`metric_name{label1="value1", label2="value2"} timestamp value`
- 支持四种指标类型：Counter、Gauge、Histogram、Summary
- 使用 PromQL 查询语言

### 问题 3：Loki 与 ELK 相比有什么优势？

**参考答案**：

| 维度 | Loki | ELK |
|------|------|-----|
| 索引 | 仅索引标签 | 全文索引 |
| 存储 | 低成本 | 高成本 |
| 查询 | LogQL | KQL |
| 集成 | Grafana 原生 | 需要 Kibana |
| 资源消耗 | 低 | 高 |

Loki 优势：轻量级、低成本、与 Grafana 深度集成。

### 问题 4：OpenTelemetry 是什么？为什么需要它？

**参考答案**：

OpenTelemetry 是 CNCF 的可观测性标准项目：
- 提供统一的 SDK 收集 Metrics、Logs、Traces
- 支持多种语言和框架
- 厂商中立，可导出到任意后端
- 替代了 OpenTracing 和 OpenCensus

优势：标准化、厂商无关、生态丰富。

### 问题 5：如何设计有效的告警规则？

**参考答案**：

1. **基于 SLO 告警**：Error Budget 消耗告警
2. **症状告警**：高错误率、高延迟（而非原因告警）
3. **分级严重度**：Critical (页面)、Warning (消息)、Info (记录)
4. **避免告警疲劳**：合理设置阈值和 for 时间
5. **包含上下文**：告警消息包含摘要和描述

### 问题 6：Prometheus 的 recording rules 有什么用？

**参考答案**：

Recording rules 预计算常用 PromQL 表达式并保存为新的时间序列：
- 减少查询时的计算量
- 提高 Dashboard 加载速度
- 用于复杂的告警规则

```yaml
groups:
  - name: recording_rules
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
```

### 问题 7：如何监控 K8s 集群本身？

**参考答案**：

kube-prometheus-stack 自动监控：
- **kube-state-metrics**：K8s 对象状态
- **node-exporter**：节点指标
- **kubelet**：kubelet 指标
- **cadvisor**：容器指标

关键指标：
- Node CPU/Memory/Disk
- Pod 状态和重启次数
- Deployment 可用副本数
- PVC 使用率

---

## 📚 深入阅读

### 官方文档
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

### 推荐资源
- [Google SRE Book - Monitoring](https://sre.google/sre-book/practical-alerting/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

---

## ✅ 自检清单

- [ ] 能使用 Helm 部署完整可观测性栈
- [ ] 理解 Prometheus 数据模型和 PromQL
- [ ] 能配置自定义告警规则
- [ ] 能创建 Grafana Dashboard
- [ ] 理解 Loki 日志收集原理
- [ ] 理解 Jaeger 链路追踪原理
- [ ] 能配置三支柱联动
- [ ] 能完成 Metrics -> Logs -> Traces 排查流程
- [ ] 完成 3 个实战练习
- [ ] 能回答相关面试题

---

*由 SRE 学习计划自动生成 | 2026-05-03*
