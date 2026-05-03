# Day 88: Docker 监控与日志

> 📅 日期：2026-05-03
> 📖 学习主题：容器监控体系（cAdvisor + Prometheus + Grafana）、日志驱动与集中日志管理
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 80-85 Docker 基础、Day 86 Docker 安全

---

## 🎯 学习目标

- 理解容器监控的三大支柱（指标、日志、追踪）
- 掌握 cAdvisor + Prometheus + Grafana 容器监控体系
- 能够配置和切换 Docker 日志驱动
- 实现 ELK/EFK 集中日志管理
- 掌握资源告警配置方法

---

## 📖 核心知识点

### 1. 容器监控体系架构

#### 1.1 可观测性三大支柱

```
┌─────────────────────────────────────────────────────────────┐
│              容器可观测性三大支柱                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │   指标       │  │   日志       │  │   追踪       │    │
│   │  (Metrics)   │  │   (Logs)     │  │  (Traces)    │    │
│   ├──────────────┤  ├──────────────┤  ├──────────────┤    │
│   │ 数值型时间序列│  │ 事件描述文本 │  │ 请求链路路径 │    │
│   │              │  │              │  │              │    │
│   │ CPU 使用率   │  │ 错误信息     │  │ 请求耗时     │    │
│   │ 内存使用量   │  │ 访问日志     │  │ 服务间调用   │    │
│   │ 网络 I/O     │  │ 调试信息     │  │ 性能瓶颈     │    │
│   │ 磁盘 I/O     │  │ 审计日志     │  │ 依赖关系     │    │
│   │              │  │              │  │              │    │
│   │ Prometheus   │  │ ELK/Loki    │  │ Jaeger/      │    │
│   │ + Grafana    │  │ + Kibana    │  │ Zipkin       │    │
│   └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│   三者关系：互为补充，共同构成完整的可观测性                   │
│   - Metrics：发现问题（"CPU 飙高了"）                       │
│   - Logs：定位原因（"OOM 导致进程崩溃"）                    │
│   - Traces：追踪链路（"数据库查询耗时 5s"）                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 容器监控架构设计

```
┌─────────────────────────────────────────────────────────────┐
│              生产环境容器监控架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│   │ Docker  │  │ Docker  │  │ Docker  │                   │
│   │ Host 1  │  │ Host 2  │  │ Host 3  │                   │
│   └────┬────┘  └────┬────┘  └────┬────┘                   │
│        │            │            │                          │
│        └────────┬───┴────────────┘                          │
│                 ▼                                           │
│   ┌────────────────────────────────────────────────────┐   │
│   │                  cAdvisor                          │   │
│   │          (容器指标采集，每个节点)                   │   │
│   └─────────────────────┬──────────────────────────────┘   │
│                         │ /metrics                          │
│                         ▼                                   │
│   ┌────────────────────────────────────────────────────┐   │
│   │                  Prometheus                         │   │
│   │            (指标存储 + 查询 + 告警)                 │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│   │   │  TSDB    │  │ PromQL   │  │ Alerting │       │   │
│   │   │ (存储)   │  │ (查询)   │  │ (告警)   │       │   │
│   │   └──────────┘  └──────────┘  └──────────┘       │   │
│   └─────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│           ┌─────────────┼─────────────┐                    │
│           ▼             ▼             ▼                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│   │ Grafana  │  │Alertmanager│ │   API    │               │
│   │(可视化)  │  │ (告警路由) │ │ (查询)   │               │
│   └──────────┘  └──────────┘  └──────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. cAdvisor 容器监控

#### 2.1 cAdvisor 简介

cAdvisor（Container Advisor）是 Google 开源的容器监控工具，自动采集容器的 CPU、内存、网络和磁盘使用数据。

```bash
# 运行 cAdvisor（快速启动）
docker run -d \
  --name cadvisor \
  --restart unless-stopped \
  -p 8080:8080 \
  -v /:/rootfs:ro \
  -v /var/run:/var/run:ro \
  -v /sys:/sys:ro \
  -v /var/lib/docker/:/var/lib/docker:ro \
  -v /dev/disk/:/dev/disk:ro \
  --privileged \
  --device=/dev/kmsg \
  gcr.io/cadvisor/cadvisor:v0.47.2

# 访问 Web UI
# http://localhost:8080

# 查看 Prometheus 指标端点
curl http://localhost:8080/metrics | head -50
```

#### 2.2 cAdvisor 指标详解

```
┌─────────────────────────────────────────────────────────────┐
│                cAdvisor 核心指标                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   CPU 指标                                                  │
│   ├── container_cpu_usage_seconds_total    CPU 累计使用时间 │
│   ├── container_cpu_system_seconds_total   内核态 CPU 时间  │
│   ├── container_cpu_user_seconds_total     用户态 CPU 时间  │
│   ├── container_cpu_cfs_throttled_seconds_total 被限流时间  │
│   └── container_cpu_cfs_periods_total      CFS 调度周期    │
│                                                             │
│   内存指标                                                  │
│   ├── container_memory_usage_bytes        内存使用量        │
│   ├── container_memory_working_set_bytes  工作集内存        │
│   ├── container_memory_rss                常驻内存          │
│   ├── container_memory_cache              缓存内存          │
│   └── container_memory_swap               交换分区使用      │
│                                                             │
│   网络指标                                                  │
│   ├── container_network_receive_bytes_total  接收字节数     │
│   ├── container_network_transmit_bytes_total 发送字节数     │
│   ├── container_network_receive_packets_total 接收包数      │
│   ├── container_network_transmit_packets_total 发送包数     │
│   ├── container_network_receive_errors_total  接收错误      │
│   └── container_network_transmit_errors_total 发送错误     │
│                                                             │
│   磁盘指标                                                  │
│   ├── container_fs_usage_bytes            文件系统使用量    │
│   ├── container_fs_limit_bytes            文件系统限制      │
│   ├── container_fs_reads_total            读取次数          │
│   ├── container_fs_writes_total           写入次数          │
│   └── container_fs_io_time_seconds_total  I/O 等待时间     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3 cAdvisor 生产配置

```yaml
# docker-compose.cadvisor.yml
version: '3.8'

services:
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.47.2
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg:/dev/kmsg
    command:
      - --port=8080
      - --housekeeping_interval=10s
      - --disable_metrics=accelerator,udp,tcp,advtcp,process,sched,hugetlb
      - --docker_only=true
      - --store_container_labels=false
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

---

### 3. Prometheus 容器监控

#### 3.1 Prometheus 架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Prometheus 架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│   │ cAdvisor    │    │ Node        │    │ App         │   │
│   │ :8080       │    │ Exporter    │    │ Metrics     │   │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘   │
│          │ Pull             │ Pull             │ Pull      │
│          └──────────────────┼──────────────────┘           │
│                             ▼                               │
│                   ┌─────────────────┐                      │
│                   │   Prometheus    │                      │
│                   │   Server        │                      │
│                   │                 │                      │
│                   │ ┌─────────────┐ │                      │
│                   │ │  Retrieval  │ │ ← 拉取指标          │
│                   │ └─────────────┘ │                      │
│                   │ ┌─────────────┐ │                      │
│                   │ │    TSDB     │ │ ← 时序存储          │
│                   │ └─────────────┘ │                      │
│                   │ ┌─────────────┐ │                      │
│                   │ │  PromQL     │ │ ← 查询语言          │
│                   │ └─────────────┘ │                      │
│                   │ ┌─────────────┐ │                      │
│                   │ │ Rule Eval   │ │ ← 告警规则          │
│                   │ └─────────────┘ │                      │
│                   └────────┬────────┘                      │
│                            │                                │
│              ┌─────────────┼─────────────┐                 │
│              ▼             ▼             ▼                 │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│   │  Grafana     │ │ Alertmanager │ │  API Client  │     │
│   │  (可视化)    │ │ (告警路由)   │ │ (查询接口)   │     │
│   └──────────────┘ └──────────────┘ └──────────────┘     │
│                                                             │
│   特点：                                                     │
│   - Pull 模型：主动拉取指标                                 │
│   - 时序数据库：高效存储时间序列数据                         │
│   - PromQL：强大的查询和聚合语言                             │
│   - 服务发现：自动发现监控目标                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s      # 全局采集间隔
  evaluation_interval: 15s   # 规则评估间隔
  scrape_timeout: 10s        # 采集超时

# 告警规则文件
rule_files:
  - "rules/*.yml"

# 告警管理器
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# 采集目标配置
scrape_configs:
  # 采集 Prometheus 自身指标
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 采集 cAdvisor 容器指标
  - job_name: 'cadvisor'
    scrape_interval: 10s
    static_configs:
      - targets: ['cadvisor:8080']
    # 只采集以 "container_" 开头的指标
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'container_(cpu|memory|network|fs)_.*'
        action: keep

  # 使用 Docker 服务发现（自动发现容器）
  - job_name: 'docker'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 30s
    relabel_configs:
      # 只采集带有 prometheus.scrape 标签的容器
      - source_labels: [__meta_docker_container_label_prometheus_scrape]
        regex: 'true'
        action: keep
      # 使用容器名作为实例标签
      - source_labels: [__meta_docker_container_name]
        regex: '/(.*)'
        target_label: container
      # 使用容器标签
      - source_labels: [__meta_docker_container_label_app]
        target_label: app
      # 获取容器端口
      - source_labels: [__meta_docker_container_network_ip]
        target_label: __address__
        regex: '(.*)'
        replacement: '${1}:8080'

  # 采集 Node Exporter（宿主机指标）
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

#### 3.3 完整的监控栈部署

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  # Prometheus - 指标存储与查询
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./rules:/etc/prometheus/rules:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=30d
      - --storage.tsdb.retention.size=10GB
      - --web.enable-lifecycle
      - --web.enable-admin-api
    networks:
      - monitoring

  # Grafana - 可视化
  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=securepassword
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://grafana.example.com
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    depends_on:
      - prometheus
    networks:
      - monitoring

  # cAdvisor - 容器指标采集
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.47.2
    container_name: cadvisor
    restart: unless-stopped
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
      - /dev/kmsg:/dev/kmsg
    command:
      - --port=8080
      - --docker_only=true
    networks:
      - monitoring

  # Node Exporter - 宿主机指标
  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - --path.procfs=/host/proc
      - --path.sysfs=/host/sys
      - --path.rootfs=/rootfs
      - --collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)
    networks:
      - monitoring

  # Alertmanager - 告警路由
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:
  alertmanager-data:

networks:
  monitoring:
    driver: bridge
```

#### 3.4 容器监控常用 PromQL 查询

```promql
# ========== CPU 相关 ==========

# 容器 CPU 使用率（百分比）
100 * rate(container_cpu_usage_seconds_total{container!=""}[5m]) / on(instance) group_left() machine_cpu_cores

# CPU 被限流的时间比例
rate(container_cpu_cfs_throttled_seconds_total[5m]) / rate(container_cpu_cfs_periods_total[5m]) * 100

# CPU 使用率 Top 10 容器
topk(10, 100 * rate(container_cpu_usage_seconds_total{container!=""}[5m]) / on(instance) group_left() machine_cpu_cores)

# ========== 内存相关 ==========

# 容器内存使用量（MB）
container_memory_usage_bytes{container!=""} / 1024 / 1024

# 容器内存使用率（百分比）
100 * container_memory_usage_bytes{container!=""} / container_spec_memory_limit_bytes

# 内存工作集使用率（用于 OOM 判断）
100 * container_memory_working_set_bytes{container!=""} / container_spec_memory_limit_bytes

# 接近内存限制的容器（>80%）
100 * container_memory_working_set_bytes{container!=""} / container_spec_memory_limit_bytes > 80

# 容器内存 Top 10
topk(10, container_memory_usage_bytes{container!=""} / 1024 / 1024)

# ========== 网络相关 ==========

# 容器网络接收速率（bytes/s）
rate(container_network_receive_bytes_total{interface="eth0"}[5m])

# 容器网络发送速率（bytes/s）
rate(container_network_transmit_bytes_total{interface="eth0"}[5m])

# 网络错误率
rate(container_network_receive_errors_total[5m]) + rate(container_network_transmit_errors_total[5m])

# ========== 磁盘相关 ==========

# 容器文件系统使用量
container_fs_usage_bytes{container!=""} / 1024 / 1024 / 1024

# 容器磁盘读取速率
rate(container_fs_reads_bytes_total[5m])

# 容器磁盘写入速率
rate(container_fs_writes_bytes_total[5m])

# ========== 综合告警规则 ==========

# 容器重启次数（5 分钟内 > 3 次）
increase(container_last_seen{name!=""}[5m]) > 3

# 容器 OOM Killed
container_oom_events_total > 0
```

#### 3.5 告警规则配置

```yaml
# rules/container-alerts.yml
groups:
  - name: container_alerts
    rules:
      # 容器 CPU 使用率过高
      - alert: ContainerHighCPUUsage
        expr: |
          100 * rate(container_cpu_usage_seconds_total{container!=""}[5m]) / on(instance) group_left() machine_cpu_cores > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} CPU 使用率过高"
          description: "容器 {{ $labels.container }} CPU 使用率达到 {{ $value | printf \"%.1f\" }}%，持续 5 分钟。"

      # 容器内存使用率过高
      - alert: ContainerHighMemoryUsage
        expr: |
          100 * container_memory_working_set_bytes{container!=""} / container_spec_memory_limit_bytes > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} 内存使用率过高"
          description: "容器 {{ $labels.container }} 内存使用率达到 {{ $value | printf \"%.1f\" }}%。"

      # 容器接近 OOM
      - alert: ContainerNearOOM
        expr: |
          100 * container_memory_working_set_bytes{container!=""} / container_spec_memory_limit_bytes > 95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "容器 {{ $labels.container }} 接近 OOM"
          description: "容器 {{ $labels.container }} 内存使用率达到 {{ $value | printf \"%.1f\" }}%，可能即将 OOM Kill。"

      # 容器被 OOM Kill
      - alert: ContainerOOMKilled
        expr: |
          increase(container_oom_events_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "容器 {{ $labels.container }} 被 OOM Kill"
          description: "容器 {{ $labels.container }} 在过去 5 分钟内被 OOM Kill。"

      # 容器 CPU 被限流
      - alert: ContainerCPUThrottled
        expr: |
          rate(container_cpu_cfs_throttled_seconds_total[5m]) / rate(container_cpu_cfs_periods_total[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} CPU 被严重限流"
          description: "容器 {{ $labels.container }} CPU 限流比例达到 {{ $value | printf \"%.1f\" }}%。"

      # 容器重启频繁
      - alert: ContainerRestarting
        expr: |
          increase(container_last_seen{name!=""}[15m]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} 频繁重启"
          description: "容器 {{ $labels.container }} 在过去 15 分钟内重启超过 3 次。"

      # 容器网络错误
      - alert: ContainerNetworkErrors
        expr: |
          rate(container_network_receive_errors_total[5m]) + rate(container_network_transmit_errors_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} 网络错误"
          description: "容器 {{ $labels.container }} 检测到网络错误。"

      # 容器文件系统使用率过高
      - alert: ContainerHighDiskUsage
        expr: |
          100 * container_fs_usage_bytes{container!=""} / container_fs_limit_bytes > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.container }} 磁盘使用率过高"
          description: "容器 {{ $labels.container }} 磁盘使用率达到 {{ $value | printf \"%.1f\" }}%。"
```

#### 3.6 Alertmanager 配置

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alertmanager@example.com'
  smtp_auth_password: 'password'

# 告警路由
route:
  # 默认接收者
  receiver: 'default-receiver'
  # 分组策略
  group_by: ['alertname', 'container']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  # 子路由
  routes:
    # critical 告警发送到 PagerDuty
    - match:
        severity: critical
      receiver: 'critical-receiver'
      repeat_interval: 1h
    # warning 告警发送到 Slack
    - match:
        severity: warning
      receiver: 'slack-receiver'
      repeat_interval: 4h

# 接收者配置
receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'oncall@example.com'
        send_resolved: true

  - name: 'critical-receiver'
    pagerduty_configs:
      - service_key: '<pagerduty-key>'
    email_configs:
      - to: 'oncall@example.com'
        send_resolved: true

  - name: 'slack-receiver'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true

# 抑制规则
inhibit_rules:
  # 如果有 critical 告警，抑制同名 warning 告警
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'container']
```

#### 3.7 Grafana Dashboard 配置

```json
{
  "dashboard": {
    "title": "Docker Container Monitoring",
    "panels": [
      {
        "title": "Container CPU Usage",
        "type": "timeseries",
        "targets": [
          {
            "expr": "100 * rate(container_cpu_usage_seconds_total{container!=\"\"}[5m]) / on(instance) group_left() machine_cpu_cores",
            "legendFormat": "{{ container }}"
          }
        ]
      },
      {
        "title": "Container Memory Usage (MB)",
        "type": "timeseries",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{container!=\"\"} / 1024 / 1024",
            "legendFormat": "{{ container }}"
          }
        ]
      },
      {
        "title": "Container Network I/O",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(container_network_receive_bytes_total{interface=\"eth0\"}[5m])",
            "legendFormat": "{{ container }} RX"
          },
          {
            "expr": "rate(container_network_transmit_bytes_total{interface=\"eth0\"}[5m])",
            "legendFormat": "{{ container }} TX"
          }
        ]
      },
      {
        "title": "Container Restarts",
        "type": "stat",
        "targets": [
          {
            "expr": "changes(container_last_seen{name!=\"\"}[1h])",
            "legendFormat": "{{ name }}"
          }
        ]
      }
    ]
  }
}
```

**推荐 Grafana Dashboard ID：**
- 893：Docker and System Monitoring
- 11600：Docker Container & Host Metrics
- 14282：cadvisor-exporter

```bash
# 导入 Dashboard
# 在 Grafana 中：+ -> Import -> 输入 ID 893 -> Load
```

---

### 4. Docker 日志驱动

#### 4.1 日志驱动概览

```
┌─────────────────────────────────────────────────────────────┐
│                Docker 日志驱动类型                            │
├──────────────┬──────────────┬───────────────────────────────┤
│ 驱动         │ 存储位置     │ 适用场景                      │
├──────────────┼──────────────┼───────────────────────────────┤
│ json-file    │ 本地文件     │ 默认，单机开发/测试           │
│ syslog       │ syslog 服务  │ 已有 syslog 基础设施          │
│ journald     │ systemd journal │ systemd 环境              │
│ fluentd      │ Fluentd      │ 集中日志收集                 │
│ awslogs      │ CloudWatch   │ AWS 环境                     │
│ gelf         │ Graylog      │ Graylog 环境                 │
│ splunk       │ Splunk       │ Splunk 环境                  │
│ etwlogs      │ ETW          │ Windows 环境                 │
│ none         │ 丢弃         │ 不需要日志的场景             │
└──────────────┴──────────────┴───────────────────────────────┘
```

#### 4.2 json-file 日志驱动

json-file 是默认日志驱动，将日志以 JSON 格式存储在宿主机文件中。

```bash
# 查看当前日志驱动
docker info --format '{{.LoggingDriver}}'
# json-file

# 配置 json-file 日志驱动（全局）
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true",
    "tag": "{{.Name}}/{{.ID}}"
  }
}
EOF
sudo systemctl restart docker

# 单容器配置
docker run -d \
  --log-driver json-file \
  --log-opt max-size=50m \
  --log-opt max-file=10 \
  --log-opt compress=true \
  --name myapp \
  nginx

# 查看容器日志文件位置
docker inspect --format='{{.LogPath}}' myapp
# /var/lib/docker/containers/<id>/<id>-json.log

# 查看日志内容
docker logs myapp
docker logs --tail 100 myapp
docker logs --since 2024-01-01T00:00:00 myapp
docker logs --until 2024-01-02T00:00:00 myapp
docker logs -f myapp  # 实时跟踪
```

**json-file 日志格式：**

```json
{
  "log": "2024-01-01 12:00:00 INFO  Starting application...\n",
  "stream": "stdout",
  "time": "2024-01-01T12:00:00.000000000Z"
}
```

#### 4.3 syslog 日志驱动

```bash
# 配置容器使用 syslog
docker run -d \
  --log-driver syslog \
  --log-opt syslog-address=udp://syslog-server:514 \
  --log-opt syslog-facility=local0 \
  --log-opt tag="myapp" \
  --name myapp \
  nginx

# 使用 TCP（更可靠）
docker run -d \
  --log-driver syslog \
  --log-opt syslog-address=tcp://syslog-server:514 \
  --log-opt syslog-tls=true \
  --log-opt syslog-tls-ca-cert=/etc/ssl/certs/ca-certificates.crt \
  --name myapp \
  nginx

# 宿主机 rsyslog 配置（/etc/rsyslog.d/docker.conf）
# 模板：按容器名分目录存储
# template(name="DockerLog" type="string"
#   string="/var/log/docker/%programname%.log")
#
# if $programname startswith 'docker-' then {
#   action(type="omfile" dynaFile="DockerLog")
#   stop
# }
```

#### 4.4 fluentd 日志驱动

```bash
# 首先部署 Fluentd
docker run -d \
  --name fluentd \
  -p 24224:24224 \
  -p 24224:24224/udp \
  -v ./fluentd/conf:/fluentd/etc \
  fluent/fluentd:v1.16

# Fluentd 配置（fluent.conf）
# <source>
#   @type forward
#   port 24224
#   bind 0.0.0.0
# </source>
#
# <match docker.**>
#   @type file
#   path /fluentd/log/docker
#   append true
#   <buffer>
#     timekey 1h
#     timekey_use_utc true
#     flush_mode interval
#     flush_interval 10s
#   </buffer>
# </match>

# 容器使用 fluentd 日志驱动
docker run -d \
  --log-driver fluentd \
  --log-opt fluentd-address=localhost:24224 \
  --log-opt fluentd-async=true \
  --log-opt fluentd-retry-wait=1s \
  --log-opt fluentd-max-retries=30 \
  --log-opt tag="docker.{{.Name}}" \
  --name myapp \
  nginx

# docker-compose 中使用
# services:
#   web:
#     logging:
#       driver: fluentd
#       options:
#         fluentd-address: "localhost:24224"
#         fluentd-async: "true"
#         tag: "docker.web"
```

#### 4.5 日志驱动性能对比

```
┌─────────────────────────────────────────────────────────────┐
│              日志驱动性能与特性对比                           │
├──────────────┬──────────┬──────────┬──────────┬────────────┤
│ 驱动         │ 性能     │ 可靠性   │ 远程存储 │ 读取支持   │
├──────────────┼──────────┼──────────┼──────────┼────────────┤
│ json-file    │ 高       │ 高       │ 否       │ docker logs│
│ syslog       │ 中       │ 中       │ 是       │ 否         │
│ journald     │ 高       │ 高       │ 否       │ journalctl │
│ fluentd      │ 中       │ 高       │ 是       │ 否         │
│ awslogs      │ 中       │ 高       │ 是       │ 否         │
│ gelf         │ 中       │ 中       │ 是       │ 否         │
│ none         │ 最高     │ N/A      │ 否       │ 否         │
└──────────────┴──────────┴──────────┴──────────┴────────────┘

选择建议：
- 单机开发：json-file（默认，支持 docker logs）
- 生产环境：fluentd/syslog（集中收集）
- AWS 环境：awslogs（CloudWatch 集成）
- 不需要日志：none（最佳性能）
```

---

### 5. ELK/EFK 集中日志管理

#### 5.1 ELK 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    ELK 日志架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│   │ Docker  │  │ Docker  │  │ Docker  │                   │
│   │ Host 1  │  │ Host 2  │  │ Host 3  │                   │
│   └────┬────┘  └────┬────┘  └────┬────┘                   │
│        │            │            │                          │
│        ▼            ▼            ▼                          │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│   │Filebeat │  │Filebeat │  │Filebeat │                   │
│   │(采集)   │  │(采集)   │  │(采集)   │                   │
│   └────┬────┘  └────┬────┘  └────┬────┘                   │
│        │            │            │                          │
│        └────────────┼────────────┘                          │
│                     ▼                                       │
│   ┌────────────────────────────────────────────────────┐   │
│   │                 Logstash                            │   │
│   │              (解析 + 转换)                          │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│   │   │  Input   │→ │  Filter  │→ │  Output  │       │   │
│   │   │(Beats)   │  │(Grok等)  │  │(ES)      │       │   │
│   │   └──────────┘  └──────────┘  └──────────┘       │   │
│   └─────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│   ┌────────────────────────────────────────────────────┐   │
│   │              Elasticsearch                         │   │
│   │              (存储 + 索引 + 搜索)                  │   │
│   └─────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│   ┌────────────────────────────────────────────────────┐   │
│   │                 Kibana                              │   │
│   │              (可视化 + 分析)                        │   │
│   └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 EFK 栈部署

```yaml
# docker-compose.efk.yml
version: '3.8'

services:
  # Elasticsearch
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
      - bootstrap.memory_lock=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - elk

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    restart: unless-stopped
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - elk

  # Filebeat
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    container_name: filebeat
    restart: unless-stopped
    user: root
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - filebeat-data:/usr/share/filebeat/data
    depends_on:
      - elasticsearch
    networks:
      - elk

volumes:
  elasticsearch-data:
  filebeat-data:

networks:
  elk:
    driver: bridge
```

#### 5.3 Filebeat 配置

```yaml
# filebeat.yml
filebeat.inputs:
  # Docker 容器日志
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'
    processors:
      - add_docker_metadata:
          host: "unix:///var/run/docker.sock"

# 处理器：解析 Docker 日志 JSON
processors:
  - decode_json_fields:
      fields: ["message"]
      target: "json"
      overwrite_keys: true
      add_error_key: true
  - add_docker_metadata:
      host: "unix:///var/run/docker.sock"
  # 添加字段
  - add_fields:
      target: ''
      fields:
        environment: production

# 输出到 Elasticsearch
output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  indices:
    - index: "docker-%{+yyyy.MM.dd}"
  # 索引模板
  template.name: "docker"
  template.pattern: "docker-*"
  template.settings:
    index.number_of_shards: 1
    index.number_of_replicas: 0

# 或输出到 Logstash（更灵活的解析）
# output.logstash:
#   hosts: ["logstash:5044"]

# 设置
setup.kibana:
  host: "kibana:5601"

# 自动加载 Kibana dashboard
setup.dashboards.enabled: true

# 日志
logging.level: info
logging.to_stderr: true
```

#### 5.4 Grafana Loki 日志方案（轻量级替代）

```yaml
# docker-compose.loki.yml
version: '3.8'

services:
  # Loki - 日志聚合
  loki:
    image: grafana/loki:2.9.0
    container_name: loki
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/config.yml:ro
      - loki-data:/loki
    command: -config.file=/etc/loki/config.yml
    networks:
      - logging

  # Promtail - 日志采集
  promtail:
    image: grafana/promtail:2.9.0
    container_name: promtail
    restart: unless-stopped
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - logging

  # Grafana - 日志可视化
  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=securepassword
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - loki
    networks:
      - logging

volumes:
  loki-data:
  grafana-data:

networks:
  logging:
    driver: bridge
```

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker 容器日志
  - job_name: docker
    static_configs:
      - targets:
          - localhost
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*.log

    pipeline_stages:
      # 解析 Docker JSON 日志
      - docker: {}
      # 添加标签
      - labels:
          container_name:
          stream:
      # 正则提取字段
      - regex:
          expression: '^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<message>.*)$'
      - labels:
          level:
```

---

### 6. 资源告警最佳实践

#### 6.1 告警级别定义

```
┌─────────────────────────────────────────────────────────────┐
│                    告警级别定义                               │
├──────────┬───────────────────┬───────────────────────────────┤
│ 级别     │ 条件              │ 响应要求                      │
├──────────┼───────────────────┼───────────────────────────────┤
│ Critical │ 服务不可用        │ 5 分钟内响应，立即处理        │
│          │ OOM Kill          │                               │
│          │ 磁盘满            │                               │
├──────────┼───────────────────┼───────────────────────────────┤
│ Warning  │ CPU > 80%         │ 30 分钟内响应，排班处理       │
│          │ 内存 > 85%        │                               │
│          │ 频繁重启          │                               │
├──────────┼───────────────────┼───────────────────────────────┤
│ Info     │ 容器状态变化       │ 下一工作日检查               │
│          │ 配置变更          │                               │
└──────────┴───────────────────┴───────────────────────────────┘
```

#### 6.2 告警降噪策略

```yaml
# alertmanager.yml - 告警降噪配置

# 1. 分组：同一容器的告警合并
route:
  group_by: ['alertname', 'container']
  group_wait: 30s      # 等待 30s 收集同组告警
  group_interval: 5m   # 同组告警间隔
  repeat_interval: 4h  # 重复告警间隔

# 2. 抑制：critical 抑制 warning
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'container']

# 3. 静默：维护时间窗口
# 在 Alertmanager Web UI 中设置静默
# 例如：每周六 02:00-04:00 维护窗口

# 4. 路由：不同严重级别不同接收者
routes:
  - match:
      severity: critical
    receiver: pagerduty
    repeat_interval: 1h
  - match:
      severity: warning
    receiver: slack
    repeat_interval: 4h
```

---

## 💻 实战练习

### 练习 1：部署完整监控栈

**目标：** 部署 cAdvisor + Prometheus + Grafana 监控栈。

```bash
# 1. 创建项目目录
mkdir -p monitoring/{prometheus,grafana,alertmanager}
cd monitoring

# 2. 创建 Prometheus 配置
cat > prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
EOF

# 3. 创建告警规则
cat > prometheus/rules/container.yml << 'EOF'
groups:
  - name: containers
    rules:
      - alert: ContainerHighCPU
        expr: 100 * rate(container_cpu_usage_seconds_total{container!=""}[5m]) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} high CPU"
EOF

# 4. 创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:v2.48.0
    ports: ["9090:9090"]
    volumes:
      - ./prometheus:/etc/prometheus:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=7d
    networks: [monitoring]

  grafana:
    image: grafana/grafana:10.2.0
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin123
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on: [prometheus]
    networks: [monitoring]

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.47.2
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/kmsg:/dev/kmsg
    networks: [monitoring]

  node-exporter:
    image: prom/node-exporter:v1.7.0
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - --path.procfs=/host/proc
      - --path.sysfs=/host/sys
      - --path.rootfs=/rootfs
    networks: [monitoring]

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
EOF

# 5. 启动监控栈
docker compose up -d

# 6. 验证
docker compose ps
curl http://localhost:9090/-/healthy
curl http://localhost:8080/metrics | head -5

# 7. 访问 Grafana
# http://localhost:3000
# 用户名: admin, 密码: admin123
# 添加 Prometheus 数据源: http://prometheus:9090
# 导入 Dashboard ID: 893
```

### 练习 2：配置集中日志管理

**目标：** 使用 Loki + Promtail + Grafana 实现集中日志管理。

```bash
# 1. 创建项目目录
mkdir -p logging
cd logging

# 2. 创建 Loki 配置
cat > loki-config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 1h
  max_chunk_age: 1h

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h
EOF

# 3. 创建 Promtail 配置
cat > promtail-config.yml << 'EOF'
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    static_configs:
      - targets: [localhost]
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*.log
    pipeline_stages:
      - docker: {}
      - labels:
          container_name:
EOF

# 4. 创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]
    volumes:
      - ./loki-config.yml:/etc/loki/config.yml:ro
      - loki-data:/loki
    command: -config.file=/etc/loki/config.yml
    networks: [logging]

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on: [loki]
    networks: [logging]

  grafana:
    image: grafana/grafana:10.2.0
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin123
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on: [loki]
    networks: [logging]

volumes:
  loki-data:
  grafana-data:

networks:
  logging:
EOF

# 5. 启动
docker compose up -d

# 6. 在 Grafana 中添加 Loki 数据源
# http://localhost:3000 -> Configuration -> Data Sources
# URL: http://loki:3100

# 7. 生成测试日志
docker run --rm alpine sh -c "for i in $(seq 1 100); do echo \"Log entry $i\"; sleep 0.1; done"

# 8. 在 Grafana Explore 中查询日志
# {job="docker"} |= "Log entry"
# {container_name="myapp"} | json | level="error"
```

### 练习 3：容器资源告警配置

**目标：** 配置容器资源告警并发送到 Slack。

```bash
# 1. 创建告警规则
cat > rules/container-alerts.yml << 'EOF'
groups:
  - name: container_alerts
    rules:
      - alert: ContainerCPUHigh
        expr: |
          100 * rate(container_cpu_usage_seconds_total{container!=""}[5m]) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} CPU > 80%"
          description: "CPU usage is {{ $value | printf \"%.1f\" }}%"

      - alert: ContainerMemoryHigh
        expr: |
          100 * container_memory_working_set_bytes{container!=""} / container_spec_memory_limit_bytes > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} Memory > 85%"

      - alert: ContainerOOMKilled
        expr: increase(container_oom_events_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.container }} was OOM Killed"

      - alert: ContainerRestarting
        expr: |
          changes(container_last_seen{name!=""}[15m]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} restarting frequently"
EOF

# 2. 创建 Alertmanager 配置（Slack 通知）
cat > alertmanager/alertmanager.yml << 'EOF'
global:
  resolve_timeout: 5m

route:
  receiver: 'slack'
  group_by: ['alertname', 'container']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 1h

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
        send_resolved: true

  - name: 'pagerduty'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#critical-alerts'
        send_resolved: true
EOF

# 3. 添加 Alertmanager 到监控栈
# 在 docker-compose.yml 中添加 alertmanager 服务

# 4. 验证告警规则
# 访问 Prometheus: http://localhost:9090/alerts
# 检查规则是否加载成功

# 5. 测试告警
# 创建一个高 CPU 消耗的容器
docker run --rm --name stress alpine sh -c "while true; do :; done"
# 等待 5 分钟后，告警应触发

# 6. 验证告警通知
# 检查 Slack 频道是否收到告警消息
# 访问 Alertmanager: http://localhost:9093 查看告警状态
```

---

## 🎯 面试题精选

### 1. 容器监控的三大支柱是什么？

**参考答案：**

容器监控的三大支柱是 Metrics（指标）、Logs（日志）和 Traces（追踪）：

- **Metrics**：数值型时间序列数据，用于发现问题。工具：Prometheus + Grafana
- **Logs**：事件描述文本，用于定位原因。工具：ELK/Loki
- **Traces**：请求链路路径，用于追踪性能瓶颈。工具：Jaeger/Zipkin

三者互为补充：Metrics 发现 CPU 飙高，Logs 定位是哪个请求导致，Traces 追踪该请求经过了哪些服务。

### 2. cAdvisor 采集哪些容器指标？

**参考答案：**

cAdvisor 采集四类容器指标：
- **CPU**：`container_cpu_usage_seconds_total`、`container_cpu_cfs_throttled_seconds_total`
- **内存**：`container_memory_usage_bytes`、`container_memory_working_set_bytes`
- **网络**：`container_network_receive_bytes_total`、`container_network_transmit_bytes_total`
- **磁盘**：`container_fs_usage_bytes`、`container_fs_reads_bytes_total`

其中 `container_memory_working_set_bytes` 是 OOM Kill 的判断依据，`rate(container_cpu_usage_seconds_total[5m])` 是 CPU 使用率计算的基础。

### 3. Prometheus 的 Pull 模型有什么优势？

**参考答案：**

Pull 模型（Prometheus 主动拉取）vs Push 模型（应用主动推送）：

| 特性 | Pull | Push |
|------|------|------|
| 目标发现 | 天然支持服务发现 | 需要应用知道 Push 地址 |
| 健康检查 | 无响应即为目标不可用 | 需要额外机制 |
| 数据控制 | Prometheus 控制采集频率 | 应用可能推送过多数据 |
| 调试 | 直接 curl 目标端点 | 不方便调试 |
| 批处理任务 | 需要 Pushgateway | 天然支持 |

Pull 模型更适合长期运行的服务（如 Web 服务），Push 模型适合短生命周期任务（如 cron job）。

### 4. Docker 日志驱动 json-file 和 fluentd 各有什么优缺点？

**参考答案：**

| 特性 | json-file | fluentd |
|------|-----------|---------|
| `docker logs` 支持 | 支持 | 不支持 |
| 远程存储 | 不支持 | 支持 |
| 日志解析 | 无 | 强大的 filter 插件 |
| 性能 | 高（本地 I/O） | 中（网络 I/O） |
| 可靠性 | 高 | 高（支持缓冲） |
| 适用场景 | 单机/开发 | 生产/集中收集 |

生产环境推荐 fluentd 或 syslog 驱动配合集中日志系统，开发环境用 json-file 方便 `docker logs` 调试。

### 5. PromQL 中如何计算容器 CPU 使用率？

**参考答案：**

```promql
# 容器 CPU 使用率（百分比）
100 * rate(container_cpu_usage_seconds_total{container!=""}[5m])
  / on(instance) group_left()
  machine_cpu_cores
```

解释：
- `rate(container_cpu_usage_seconds_total[5m])`：5 分钟内的每秒 CPU 使用率（0-1 核）
- `machine_cpu_cores`：宿主机 CPU 核数
- `on(instance) group_left()`：按 instance 关联宿主机核数
- 乘以 100 转换为百分比

注意：`container_cpu_usage_seconds_total` 是累计值，必须用 `rate()` 计算变化率。

### 6. ELK 和 EFK 有什么区别？

**参考答案：**

- **ELK**：Elasticsearch + Logstash + Kibana。Logstash 负责日志解析和转换，功能强大但资源消耗大。
- **EFK**：Elasticsearch + Fluentd/Filebeat + Kibana。用 Fluentd 或 Filebeat 替代 Logstash。

| 特性 | Logstash | Fluentd | Filebeat |
|------|----------|---------|----------|
| 语言 | JRuby | Ruby/C | Go |
| 内存 | 大（200MB+） | 中（100MB+） | 小（30MB+） |
| 插件 | 丰富 | 丰富 | 有限 |
| 功能 | 解析+转换 | 解析+转换+输出 | 采集+发送 |
| 适用场景 | 复杂日志处理 | 通用 | 轻量采集 |

EFK 推荐 Filebeat 作为采集器（轻量），Logstash/Fluentd 做复杂解析。

### 7. 如何设计容器监控告警规则？

**参考答案：**

告警规则设计原则：

1. **四级告警**：
   - Critical：服务不可用（OOM Kill、容器崩溃）- 立即响应
   - Warning：资源紧张（CPU > 80%、内存 > 85%）- 30 分钟响应
   - Info：状态变化 - 下一工作日检查

2. **必须告警的指标**：
   - 容器 OOM Kill（`increase(container_oom_events_total) > 0`）
   - 容器频繁重启（`changes(container_last_seen[15m]) > 3`）
   - CPU 使用率持续高（`rate() > 80%` for 5m）
   - 内存接近限制（`working_set / limit > 95%`）

3. **告警降噪**：
   - 分组合并（group_by: alertname, container）
   - 抑制规则（critical 抑制 warning）
   - 维护窗口静默

### 8. Grafana Loki 和 ELK 有什么区别？

**参考答案：**

| 特性 | ELK | Loki |
|------|-----|------|
| 索引方式 | 全文索引 | 仅索引标签 |
| 存储成本 | 高（索引膨胀） | 低（仅标签索引） |
| 查询能力 | 强（Lucene） | 中（LogQL） |
| 资源消耗 | 高 | 低 |
| 与 Grafana 集成 | 需要插件 | 原生支持 |
| 适用场景 | 复杂日志分析 | 与 Prometheus 配合 |

Loki 的设计理念是 "like Prometheus, but for logs"，只索引标签不索引内容，大幅降低存储成本，适合与 Prometheus 监控栈配合使用。

### 9. 如何优化 Docker 容器的日志性能？

**参考答案：**

```bash
# 1. 设置日志轮转（防止磁盘撑满）
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3",
    "compress": "true"
  }
}
EOF

# 2. 对不需要日志的容器禁用日志
docker run --log-driver none myapp

# 3. 使用异步日志驱动
docker run --log-driver fluentd --log-opt fluentd-async=true myapp

# 4. 应用层面优化
# - 使用结构化日志（JSON 格式）
# - 避免过多 DEBUG 级别日志
# - 批量写入而非逐行写入

# 5. 监控日志磁盘使用
du -sh /var/lib/docker/containers/*/
docker system df
```

### 10. 如何在 Kubernetes 中实现容器监控？

**参考答案：**

Kubernetes 环境的容器监控通常使用：

1. **Prometheus Operator**：自动化部署和管理 Prometheus
   - ServiceMonitor：自动发现采集目标
   - PodMonitor：直接监控 Pod
   - PrometheusRule：管理告警规则

2. **kube-state-metrics**：Kubernetes 对象指标
   - Pod 状态、Deployment 副本数、PVC 状态等

3. **cAdvisor**：kubelet 内置，自动采集容器指标

4. **metrics-server**：资源指标 API（HPA 使用）

```yaml
# ServiceMonitor 示例
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
    - port: metrics
      interval: 15s
```

---

## 📚 深入阅读

### 官方文档
- [Docker Logging Documentation](https://docs.docker.com/config/containers/logging/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [cAdvisor GitHub](https://github.com/google/cadvisor)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)

### 工具资源
- [Prometheus Exporters](https://prometheus.io/docs/instrumenting/exporters/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [Filebeat Documentation](https://www.elastic.co/beats/filebeat)
- [Fluentd Documentation](https://www.fluentd.org/)

---

## ✅ 自检清单

### 监控体系
- [ ] 理解可观测性三大支柱（Metrics、Logs、Traces）
- [ ] 能够部署 cAdvisor + Prometheus + Grafana 监控栈
- [ ] 掌握 PromQL 常用查询（CPU、内存、网络、磁盘）
- [ ] 能够配置 Grafana Dashboard

### 日志管理
- [ ] 理解 Docker 各日志驱动的区别
- [ ] 能够配置 json-file 日志轮转
- [ ] 能够部署 EFK/ELK 或 Loki 集中日志系统
- [ ] 理解 Filebeat/Fluentd/Promtail 的配置

### 告警配置
- [ ] 能够编写 Prometheus 告警规则
- [ ] 能够配置 Alertmanager 告警路由
- [ ] 理解告警降噪策略（分组、抑制、静默）
- [ ] 能够集成 Slack/邮件通知

---

**下一阶段：** Day 89 将进行 Docker 阶段综合实战，包括 LAMP/LNMP 部署、微服务架构和安全扫描。
