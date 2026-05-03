# Day 141: Logstash / Fluentd 日志采集（Pipeline 架构、Input/Filter/Output、Fluentd 对比、Filebeat）

> 📅 日期：2026-05-06
> 📖 学习主题：Logstash Pipeline 架构、Fluentd 统一日志层、Filebeat 轻量采集、三者对比与选型
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 140 (Elasticsearch 基础), Day 13 (日志管理)

## 🎯 学习目标

- 深入理解 Logstash 的 Pipeline 架构和执行模型
- 掌握 Input、Filter、Output 插件的配置与使用
- 理解 Fluentd 的架构设计与路由机制
- 掌握 Filebeat 的部署配置与模块系统
- 能够根据场景选择合适的日志采集方案
- 能够设计生产级日志采集管道

---

## 📖 核心知识点

### 1. 日志采集架构概述

```
现代日志采集架构的演进：

第一代：rsyslog + 文件
  ├── 简单，但无解析能力
  └── 难以扩展

第二代：Logstash + Elasticsearch
  ├── 强大的解析能力
  └── 资源消耗大，不适合边缘采集

第三代：Filebeat + Logstash + Elasticsearch
  ├── 轻量采集 + 强大处理
  └── 成为行业标准

第四代：Fluentd / Fluent Bit
  ├── CNCF 毕业项目
  ├── K8s 生态标准
  └── 统一日志层

第五代：OpenTelemetry Collector
  ├── 统一采集 Metrics/Logs/Traces
  ├── 厂商中立
  └── 未来趋势

┌──────────────────────────────────────────────────────────────────┐
│                    日志采集架构选型                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  轻量采集层（部署在每台机器/容器）                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │  Filebeat   │  │ Fluent Bit │  │ Promtail   │                 │
│  │  (Elastic)  │  │ (CNCF)     │  │ (Grafana)  │                 │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘                 │
│         │               │               │                         │
│  重处理层（可选）                                                   │
│  ┌──────┴───────────────┴───────────────┴──────────────────┐     │
│  │              Logstash / Fluentd / OTel Collector          │     │
│  │         解析、富化、过滤、路由、多目标输出                    │     │
│  └──────┬───────────────┬───────────────┬──────────────────┘     │
│         │               │               │                         │
│  存储层                                                                │
│  ┌──────┴─────┐  ┌──────┴─────┐  ┌──────┴─────┐                 │
│  │    ES      │  │    Loki    │  │   S3/GCS   │                 │
│  └────────────┘  └────────────┘  └────────────┘                 │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 2. Logstash 深入

#### 2.1 Pipeline 执行模型

```
Logstash Pipeline 执行模型：

┌─────────────────────────────────────────────────────────────────┐
│                    Logstash Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Input 阶段（可多个并行）                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │  Beats   │ │  File   │ │  Kafka  │                           │
│  └────┬────┘ └────┬────┘ └────┬────┘                           │
│       │           │           │                                   │
│       └───────────┴───────────┘                                   │
│                   │                                                │
│                   ▼                                                │
│  ┌────────────────────────────────────────┐                      │
│  │           Input Queue                   │                      │
│  │  (In-Memory / Persistent)               │                      │
│  └──────────────────┬─────────────────────┘                      │
│                     │                                              │
│                     ▼                                              │
│  Filter 阶段（按顺序执行，可多线程）                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │  Grok   │→ │  Mutate │→ │  Date   │→ │ GeoIP  │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
│                     │                                              │
│                     ▼                                              │
│  ┌────────────────────────────────────────┐                      │
│  │           Filter Queue                  │                      │
│  └──────────────────┬─────────────────────┘                      │
│                     │                                              │
│                     ▼                                              │
│  Output 阶段（可多个并行输出）                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │   ES    │ │  Kafka  │ │  S3     │                           │
│  └─────────┘ └─────────┘ └─────────┘                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

关键参数：
  pipeline.workers: 4          # Filter 和 Output 的线程数（默认 CPU 核数）
  pipeline.batch.size: 125     # 每批处理的事件数
  pipeline.batch.delay: 50     # 等凑满 batch 的最大毫秒数
  queue.type: memory           # 队列类型：memory / persisted
  queue.max_bytes: 1gb         # 持久化队列大小
```

#### 2.2 Input 插件详解

```ruby
# beats input - 接收 Filebeat 数据
input {
  beats {
    port => 5044
    ssl => true
    ssl_certificate => "/etc/logstash/certs/server.crt"
    ssl_key => "/etc/logstash/certs/server.key"
    ssl_certificate_authorities => ["/etc/logstash/certs/ca.crt"]
  }
}

# file input - 直接读取文件
input {
  file {
    path => "/var/log/nginx/access.log"
    start_position => "beginning"
    sincedb_path => "/var/lib/logstash/sincedb_nginx"
    codec => "json"
    type => "nginx-access"
  }
}

# kafka input - 从 Kafka 消费
input {
  kafka {
    bootstrap_servers => "kafka-1:9092,kafka-2:9092,kafka-3:9092"
    topics => ["app-logs", "system-logs"]
    group_id => "logstash-consumers"
    consumer_threads => 4
    codec => json
    auto_offset_reset => "latest"
  }
}

# tcp/udp input - 接收 syslog 等
input {
  tcp {
    port => 5000
    codec => json_lines
    type => "tcp-logs"
  }
  udp {
    port => 5001
    codec => json
    type => "udp-logs"
  }
}

# syslog input - 接收 syslog
input {
  syslog {
    port => 5514
    type => "syslog"
  }
}

# http input - 接收 HTTP 推送
input {
  http {
    port => 8080
    codec => json
    response_headers => {
      "Content-Type" => "application/json"
    }
  }
}

# stdin input - 标准输入（调试用）
input {
  stdin {
    codec => json
  }
}
```

#### 2.3 Filter 插件详解

```ruby
# Grok 模式解析（最常用）
filter {
  grok {
    match => {
      "message" => [
        # Nginx combined log format
        '%{IPORHOST:client_ip} - %{DATA:user} \[%{HTTPDATE:timestamp}\] "%{WORD:method} %{URIPATHPARAM:request} HTTP/%{NUMBER:http_version}" %{NUMBER:status:int} %{NUMBER:bytes:int} "%{DATA:referrer}" "%{DATA:user_agent}"',
        # Java application log
        '%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] \[%{DATA:thread}\] %{DATA:class} - %{GREEDYDATA:log_message}',
        # Generic fallback
        '%{GREEDYDATA:message}'
      ]
    }
    overwrite => ["message"]
    tag_on_failure => ["_grokparsefailure"]
  }
}

# JSON 解析
filter {
  json {
    source => "message"
    target => "parsed"
    skip_on_invalid_json => true
  }
}

# Date 解析
filter {
  date {
    match => [
      "timestamp",
      "yyyy-MM-dd HH:mm:ss.SSS",
      "yyyy-MM-dd'T'HH:mm:ss.SSSZ",
      "ISO8601",
      "dd/MMM/yyyy:HH:mm:ss Z"
    ]
    target => "@timestamp"
    timezone => "Asia/Shanghai"
  }
}

# Mutate 字段操作
filter {
  mutate {
    # 重命名字段
    rename => { "host" => "hostname" }

    # 类型转换
    convert => {
      "response_time" => "float"
      "status_code" => "integer"
      "bytes" => "integer"
    }

    # 添加字段
    add_field => {
      "environment" => "production"
      "datacenter" => "cn-east"
    }

    # 删除字段
    remove_field => ["beat", "input", "ecs", "agent", "log"]

    # 合并字段
    merge => { "tags" => "new_tag" }

    # 字符串操作
    lowercase => ["level"]
    strip => ["message"]
    gsub => [
      "request", "\?.*", ""    # 去掉查询参数
    ]

    # 分割字段
    split => { "tags" => "," }
  }
}

# GeoIP 地理位置解析
filter {
  geoip {
    source => "client_ip"
    target => "geo"
    fields => ["country_name", "region_name", "city_name", "latitude", "longitude"]
  }
}

# User Agent 解析
filter {
  useragent {
    source => "user_agent"
    target => "ua"
  }
}

# 条件过滤
filter {
  if [type] == "nginx-access" {
    grok { ... }
  } else if [level] == "error" {
    mutate { add_tag => ["critical"] }
  }

  # 丢弃健康检查日志
  if [request] =~ /\/health/ {
    drop { }
  }
}

# Ruby 代码过滤（高级）
filter {
  ruby {
    code => '
      duration = event.get("duration_ms").to_f
      if duration > 1000
        event.set("slow_request", true)
        event.set("severity", "warning")
      end
    '
  }
}

# Kv 键值对解析
filter {
  kv {
    source => "message"
    field_split => " "
    value_split => "="
    target => "parsed_params"
  }
}

# Translate 映射转换
filter {
  translate {
    field => "[http][status_code]"
    destination => "[http][status_category]"
    dictionary => {
      "200" => "success"
      "201" => "success"
      "400" => "client_error"
      "404" => "not_found"
      "500" => "server_error"
      "503" => "service_unavailable"
    }
    fallback => "unknown"
  }
}
```

#### 2.4 Output 插件详解

```ruby
# Elasticsearch 输出
output {
  elasticsearch {
    hosts => ["https://es-node-1:9200", "https://es-node-2:9200"]
    index => "%{[@metadata][beat]}-%{+YYYY.MM.dd}"
    user => "logstash_writer"
    password => "${ES_PASSWORD}"
    ssl => true
    cacert => "/etc/logstash/certs/ca.crt"

    # 模板管理
    template_name => "logstash"
    template_overwrite => true

    # 性能参数
    workers => 4
    flush_size => 5000
    idle_flush_time => 1

    # 重试策略
    retry_max_interval => 64
    retry_max_count => 5
  }
}

# Kafka 输出
output {
  kafka {
    bootstrap_servers => "kafka-1:9092,kafka-2:9092"
    topic_id => "processed-logs"
    codec => json
    compression_type => "lz4"
    batch_size => 1000
  }
}

# 多输出（扇出模式）
output {
  if [level] == "error" {
    # 错误日志发送到告警系统
    http {
      url => "http://alertmanager:9095/api/alerts"
      http_method => "post"
      format => "json"
    }
  }

  # 所有日志发送到 ES
  elasticsearch {
    hosts => ["http://es:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"
  }

  # 同时输出到文件（备份）
  file {
    path => "/var/log/logstash/backup/%{+YYYY-MM-dd}/%{service}.log"
    codec => json_lines
  }
}
```

#### 2.5 Logstash 生产配置模板

```ruby
# /etc/logstash/conf.d/production.conf

# ========== Input ==========
input {
  beats {
    port => 5044
    ssl => false  # 内网环境可关闭，生产环境建议开启
  }
}

# ========== Filter ==========
filter {
  # 根据来源类型分别处理
  if [fields][log_type] == "nginx" {
    grok {
      match => {
        "message" => '%{IPORHOST:client_ip} - %{DATA:user} \[%{HTTPDATE:timestamp}\] "%{WORD:method} %{URIPATHPARAM:request} HTTP/%{NUMBER:http_version}" %{NUMBER:status:int} %{NUMBER:bytes:int} "%{DATA:referrer}" "%{DATA:user_agent}" %{NUMBER:response_time:float}'
      }
    }
    geoip { source => "client_ip" }
    useragent { source => "user_agent" }
  }

  else if [fields][log_type] == "application" {
    json {
      source => "message"
      skip_on_invalid_json => true
    }
  }

  else if [fields][log_type] == "system" {
    grok {
      match => {
        "message" => '%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:hostname} %{DATA:program}(?:\[%{POSINT:pid}\])?: %{GREEDYDATA:syslog_message}'
      }
    }
  }

  # 通用处理
  date {
    match => ["timestamp", "ISO8601", "dd/MMM/yyyy:HH:mm:ss Z"]
    target => "@timestamp"
  }

  mutate {
    remove_field => ["beat", "input", "ecs", "agent"]
  }
}

# ========== Output ==========
output {
  elasticsearch {
    hosts => ["http://es-node-1:9200", "http://es-node-2:9200"]
    index => "%{[fields][log_type]}-logs-%{+YYYY.MM.dd}"
    user => "logstash"
    password => "${ES_PASSWORD}"
  }
}
```

### 3. Fluentd 深入

#### 3.1 Fluentd 架构

```
Fluentd 统一日志层架构：

┌─────────────────────────────────────────────────────────────────┐
│                      Fluentd 架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  数据源（Inputs）                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  tail    │ │  forward │ │  syslog  │ │  http    │          │
│  │  文件监听 │ │  转发接收 │ │  syslog  │ │  HTTP    │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │                   │
│       └────────────┴────────────┴────────────┘                   │
│                        │                                          │
│                        ▼                                          │
│  ┌─────────────────────────────────────────────────┐            │
│  │              Event Router（事件路由器）            │            │
│  │                                                   │            │
│  │   <match pattern>                                 │            │
│  │     tag: app.nginx.access                         │            │
│  │     → 匹配 app.nginx.*                            │            │
│  │                                                   │            │
│  │   <filter pattern>                                │            │
│  │     对匹配的事件进行处理                            │            │
│  │                                                   │            │
│  │   <match>                                         │            │
│  │     输出到目标                                     │            │
│  └─────────────────────────────────────────────────┘            │
│                        │                                          │
│                        ▼                                          │
│  输出（Outputs）                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   es     │ │  s3     │ │  kafka  │ │ forward │          │
│  │  ES写入   │ │  S3存储  │ │  Kafka  │ │  转发    │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                   │
│  核心概念：                                                       │
│  - Tag：事件标签，用于路由                                        │
│  - Event：{ time, tag, record }                                 │
│  - Buffer：输出缓冲，支持持久化                                   │
│  - Plugin：可插拔架构，200+ 社区插件                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Fluentd 核心配置

```xml
<!-- /etc/fluent/fluent.conf -->

# ========== 系统配置 ==========
<system>
  workers 4
  root_dir /var/log/fluentd
  log_level info
  <log>
    format json
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </log>
</system>

# ========== Input: 采集 Nginx 日志 ==========
<source>
  @type tail
  @id nginx_tail
  path /var/log/nginx/access.log
  pos_file /var/log/fluentd/nginx-access.pos
  tag nginx.access
  read_from_head true
  <parse>
    @type regexp
    expression /^(?<remote>[^ ]*) (?<host>[^ ]*) (?<user>[^ ]*) \[(?<time>[^\]]*)\] "(?<method>\S+)(?: +(?<path>[^\"]*?)(?: +\S*)?)?" (?<code>[^ ]*) (?<size>[^ ]*)(?: "(?<referer>[^\"]*)" "(?<agent>[^\"]*)" "(?<x_forwarded_for>[^\"]*)")?/
    time_format %d/%b/%Y:%H:%M:%S %z
  </parse>
</source>

# ========== Input: 采集应用 JSON 日志 ==========
<source>
  @type tail
  @id app_tail
  path /var/log/app/*.log
  pos_file /var/log/fluentd/app.pos
  tag app.*
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%L%z
  </parse>
</source>

# ========== Input: 接收转发日志 ==========
<source>
  @type forward
  @id forward_input
  port 24224
  bind 0.0.0.0
  <security>
    self_hostname fluentd-aggregator
    shared_key my_secret_key
  </security>
</source>

# ========== Input: 接收 Syslog ==========
<source>
  @type syslog
  @id syslog_input
  port 5140
  bind 0.0.0.0
  tag system
  <parse>
    message_format rfc5424
  </parse>
</source>

# ========== Filter: 解析 Nginx 日志 ==========
<filter nginx.**>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    environment production
  </record>
</filter>

# ========== Filter: GeoIP 解析 ==========
<filter nginx.access>
  @type geoip
  geoip_lookup_keys remote
  <record>
    geo_country  ${country.names.en["remote"]}
    geo_city     ${city.names.en["remote"]}
    geo_lat      ${latitude["remote"]}
    geo_lon      ${longitude["remote"]}
  </record>
  <inject>
    tag_placeholder geo
  </inject>
</filter>

# ========== Filter: 添加 Kubernetes 元数据 ==========
<filter app.**>
  @type kubernetes_metadata
  @id k8s_metadata
  kubernetes_url https://kubernetes.default.svc
  verify_ssl true
  ca_file /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  bearer_token_file /var/run/secrets/kubernetes.io/serviceaccount/token
  skip_labels false
  skip_container_metadata false
  skip_master_url true
</filter>

# ========== Filter: 日志级别过滤 ==========
<filter **>
  @type grep
  <exclude>
    key level
    pattern /^debug$/i
  </exclude>
</filter>

# ========== Output: 发送到 Elasticsearch ==========
<match **>
  @type elasticsearch
  @id es_output
  host es-node-1
  port 9200
  scheme http
  user elastic
  password changeme
  index_name fluentd-${tag}
  type_name _doc
  include_tag_key true
  tag_key @log_name
  <buffer tag, time>
    @type file
    path /var/log/fluentd/buffer/es
    timekey 3600
    timekey_wait 60
    chunk_limit_size 256MB
    total_limit_size 8GB
    flush_mode interval
    flush_interval 30s
    retry_type exponential_backoff
    retry_max_interval 300
    overflow_action block
  </buffer>
</match>

# ========== Output: 发送到 S3（归档） ==========
<match **>
  @type s3
  @id s3_output
  aws_key_id "#{ENV['AWS_ACCESS_KEY_ID']}"
  aws_sec_key "#{ENV['AWS_SECRET_ACCESS_KEY']}"
  s3_bucket my-log-archive
  s3_region us-east-1
  path logs/${tag}/%Y/%m/%d/
  <buffer tag, time>
    @type file
    path /var/log/fluentd/buffer/s3
    timekey 3600
    timekey_wait 10m
    chunk_limit_size 256MB
  </buffer>
  <format>
    @type json
  </format>
</match>

# ========== Output: 错误日志发送到告警 ==========
<match *.error>
  @type http
  @id alert_output
  endpoint http://alertmanager:9095/api/alerts
  http_method post
  <format>
    @type json
  </format>
  <buffer>
    flush_mode interval
    flush_interval 5s
  </buffer>
</match>
```

#### 3.3 Fluentd vs Fluent Bit

```
Fluentd vs Fluent Bit 对比：

┌─────────────────┬──────────────────┬──────────────────┐
│ 特性            │ Fluentd          │ Fluent Bit       │
├─────────────────┼──────────────────┼──────────────────┤
│ 语言            │ Ruby + C         │ C                │
│ 内存占用        │ ~40MB            │ ~1MB             │
│ 插件生态        │ 500+ 插件        │ 100+ 内置插件     │
│ 适用场景        │ 聚合层/处理层     │ 边缘采集层        │
│ Buffer         │ 文件/内存         │ 文件/内存         │
│ 部署位置        │ 中间层           │ 每个节点          │
│ K8s DaemonSet  │ 可以（较重）      │ 推荐（轻量）      │
│ 配置复杂度      │ 中等             │ 低                │
│ 性能            │ 高               │ 极高              │
│ CNCF 状态      │ 毕业项目          │ 孵化项目          │
└─────────────────┴──────────────────┴──────────────────┘

推荐架构：
  Fluent Bit（边缘采集）→ Fluentd（聚合处理）→ Elasticsearch/Loki
```

### 4. Filebeat 深入

#### 4.1 Filebeat 架构

```
Filebeat 架构：

┌──────────────────────────────────────────────────────────────┐
│                      Filebeat                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  Harvester（收割器）- 每个文件一个                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │access.log│ │ error.log│ │ app.log  │                     │
│  │ Harvester│ │ Harvester│ │ Harvester│                     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘                     │
│       │            │            │                             │
│       └────────────┴────────────┘                             │
│                    │                                           │
│                    ▼                                           │
│  ┌────────────────────────────────────┐                      │
│  │          Input Registry             │                      │
│  │  记录每个文件的读取位置（inode/offset）│                      │
│  └──────────────────┬─────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌────────────────────────────────────┐                      │
│  │          Spooler（缓冲池）           │                      │
│  │  聚合事件，减少网络调用               │                      │
│  └──────────────────┬─────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌────────────────────────────────────┐                      │
│  │          Output（输出）              │                      │
│  │  Logstash / Elasticsearch / Kafka   │                      │
│  └────────────────────────────────────┘                      │
│                                                                │
│  关键特性：                                                    │
│  - At-least-once 语义                                         │
│  - 断点续传（Registry 文件）                                   │
│  - 背压机制（Backpressure）                                   │
│  - 自动发现（Autodiscover）                                   │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 4.2 Filebeat 核心配置

```yaml
# filebeat.yml

# ========== 输入配置 ==========
filebeat.inputs:

# Nginx 日志
- type: log
  enabled: true
  paths:
    - /var/log/nginx/access.log
    - /var/log/nginx/error.log
  fields:
    log_type: nginx
    environment: production
  fields_under_root: true
  multiline:
    pattern: '^\d{4}-\d{2}-\d{2}'
    negate: true
    match: after
    max_lines: 50

# 应用 JSON 日志
- type: log
  enabled: true
  paths:
    - /var/log/app/*.json
  json.keys_under_root: true
  json.add_error_key: true
  fields:
    log_type: application

# 容器日志（Docker）
- type: container
  enabled: true
  paths:
    - /var/lib/docker/containers/*/*.log
  processors:
    - add_kubernetes_metadata:
        host: ${NODE_NAME}

# ========== 模块配置 ==========
filebeat.modules:
- module: nginx
  access:
    enabled: true
    var.paths: ["/var/log/nginx/access.log"]
  error:
    enabled: true
    var.paths: ["/var/log/nginx/error.log"]

- module: system
  syslog:
    enabled: true
    var.paths: ["/var/log/syslog"]
  auth:
    enabled: true
    var.paths: ["/var/log/auth.log"]

- module: mysql
  slowlog:
    enabled: true
    var.paths: ["/var/log/mysql/slow.log"]
  error:
    enabled: true
    var.paths: ["/var/log/mysql/error.log"]

# ========== 处理器 ==========
processors:
  # 添加主机元数据
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~

  # 字段处理
  - drop_fields:
      fields: ["agent.ephemeral_id", "agent.id", "agent.name"]
      ignore_missing: true

  # 条件丢弃
  - drop_event:
      when:
        regexp:
          message: "^GET /health"

# ========== 输出配置 ==========
# 输出到 Logstash
output.logstash:
  hosts: ["logstash-1:5044", "logstash-2:5044"]
  loadbalance: true
  bulk_max_size: 2048
  worker: 2
  compression_level: 3
  ssl.certificate_authorities: ["/etc/filebeat/ca.crt"]

# 或输出到 Elasticsearch
# output.elasticsearch:
#   hosts: ["es-node-1:9200", "es-node-2:9200"]
#   index: "filebeat-%{[agent.version]}-%{+yyyy.MM.dd}"
#   protocol: "http"
#   username: "filebeat_writer"
#   password: "${ES_PASSWORD}"

# 或输出到 Kafka
# output.kafka:
#   hosts: ["kafka-1:9092", "kafka-2:9092"]
#   topic: "filebeat-logs"
#   partition.round_robin:
#     reachable_only: true
#   required_acks: 1
#   compression: gzip

# ========== 通用配置 ==========
name: "${HOSTNAME}"
tags: ["production", "cn-east"]

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat.log
  keepfiles: 7
  permissions: 0644

# 性能调优
queue.mem:
  events: 4096
  flush.min_events: 512
  flush.timeout: 5s

# 监控
monitoring.enabled: true
monitoring.elasticsearch:
  hosts: ["es-node-1:9200"]
```

#### 4.3 Filebeat Autodiscover（K8s 自动发现）

```yaml
# filebeat-k8s.yml
filebeat.autodiscover:
  providers:
    - type: kubernetes
      node: ${NODE_NAME}
      hints.enabled: true
      hints.default_config:
        type: container
        paths:
          - /var/log/containers/*${data.kubernetes.container.id}.log
      templates:
        - condition:
            contains:
              kubernetes.labels.app: "nginx"
          config:
            - type: container
              paths:
                - /var/log/containers/*${data.kubernetes.container.id}.log
              processors:
                - decode_json_fields:
                    fields: ["message"]
                    target: "json"
                    overwrite_keys: true

        - condition:
            contains:
              kubernetes.labels.app: "java-app"
          config:
            - type: container
              paths:
                - /var/log/containers/*${data.kubernetes.container.id}.log
              multiline.pattern: '^\d{4}-\d{2}-\d{2}'
              multiline.negate: true
              multiline.match: after

processors:
  - add_kubernetes_metadata:
      host: ${NODE_NAME}
      matchers:
        - logs_path:
            logs_path: "/var/log/containers/"
```

### 5. 三大采集工具对比

```
Logstash vs Fluentd vs Filebeat 对比：

┌─────────────────┬──────────────┬──────────────┬──────────────┐
│ 特性            │ Logstash     │ Fluentd      │ Filebeat     │
├─────────────────┼──────────────┼──────────────┼──────────────┤
│ 开发语言        │ JRuby        │ Ruby + C     │ Go           │
│ 内存占用        │ 200MB+       │ 40MB+        │ 10MB+        │
│ CPU 占用        │ 高           │ 中           │ 低           │
│ 延迟            │ 中等         │ 低           │ 极低         │
│ 吞吐量          │ 高           │ 高           │ 中高         │
│ 插件生态        │ 200+         │ 500+         │ 模块化       │
│ 配置格式        │ DSL (Ruby)   │ XML-like     │ YAML         │
│ 缓冲/重试       │ 支持         │ 支持         │ 支持         │
│ 适用场景        │ 重处理/聚合  │ 统一日志层   │ 轻量采集     │
│ K8s 支持        │ 部分         │ 原生         │ 原生         │
│ CNCF           │ 无           │ 毕业项目     │ 无           │
│ 所属公司        │ Elastic      │ Treasure     │ Elastic      │
│                 │              │ Data         │              │
│ 输出目标        │ 多样         │ 多样         │ 主要 ES/LS   │
│ 部署复杂度      │ 中           │ 中           │ 低           │
└─────────────────┴──────────────┴──────────────┴──────────────┘

选型建议：

Filebeat：
  ✓ 需要轻量级采集（每台机器部署）
  ✓ 日志格式相对简单
  ✓ 目标是 Elasticsearch 或 Logstash
  ✓ 资源有限的环境

Logstash：
  ✓ 需要复杂的日志解析（Grok、正则）
  ✓ 需要多数据源汇聚
  ✓ 需要丰富的数据富化（GeoIP、User Agent）
  ✓ 需要灵活的路由和扇出

Fluentd：
  ✓ K8s 环境（CNCF 生态）
  ✓ 需要统一日志层
  ✓ 多云/混合云环境
  ✓ 需要高可用和可靠投递

最佳组合：
  Filebeat（采集）→ Logstash（处理）→ Elasticsearch（存储）→ Kibana（可视化）
  Fluent Bit（边缘）→ Fluentd（聚合）→ Elasticsearch/Loki（存储）
```

### 6. SRE 实战案例

#### 6.1 日志丢失排查

```
故障现象：
  部分应用日志在 Kibana 中搜不到，但磁盘上的日志文件存在

排查链路：

1. 检查 Filebeat 状态
   curl -s "localhost:5067/stats" | jq '.filebeat'
   → events.active: 0, events.acked: 1000000, events.failed: 0

2. 检查 Logstash Pipeline 状态
   curl -s "localhost:9600/_node/stats/pipelines" | jq '.pipelines.main'
   → events.in: 1000000, events.filtered: 999000, events.out: 999000

   发现：filtered < in，说明部分事件被过滤了

3. 检查 Logstash 错误日志
   tail -f /var/log/logstash/logstash-plain.log
   → _grokparsefailure 超过 1000 条

4. 原因：Grok 模式不匹配新格式的日志
   解决：更新 Grok 模式或使用更宽松的模式

5. 检查 ES 写入状态
   curl -s "localhost:9200/_cat/indices?v&s=store.size:desc"
   → 发现索引大小比预期小

6. 检查 ES 错误日志
   → 发现 mapper_parsing_exception
   → 原因：新字段类型与映射不匹配

7. 修复方案：
   a) 更新索引模板
   b) 使用 pipeline 预处理数据
   c) 设置 Dead Letter Queue 收集失败事件
```

#### 6.2 日志采集性能瓶颈

```
故障现象：
  Logstash CPU 使用率持续 90%+，日志处理延迟增大

排查步骤：

1. 查看 Logstash Pipeline 指标
   curl -s "localhost:9600/_node/stats/pipelines" | jq '.pipelines.main'
   → events.duration_in_millis: 5000000
   → events.in: 100000
   → 平均处理时间 = 5000000 / 100000 = 50ms/事件

2. 查看热点 Filter
   → Grok 正则过于复杂
   → 使用 Grok Debugger 优化

3. 优化方案：
   a) 增加 pipeline.workers 数量
      pipeline.workers: 8  (从 4 增加到 8)

   b) 增大 batch.size
      pipeline.batch.size: 3000  (从 125 增加到 3000)

   c) 优化 Grok 模式
      - 使用更具体的模式代替 .* 等贪婪匹配
      - 预编译常用模式

   d) 使用多 Pipeline
      - 不同类型的日志使用不同的 Pipeline
      - 避免相互影响

   e) 部分处理下移到 Filebeat
      - 简单的 JSON 解析在 Filebeat 完成
      - 减轻 Logstash 负担
```

---

## 💻 实战练习

### 练习 1：搭建 Filebeat + Logstash + ES 日志管道

```bash
# 步骤 1：安装 Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.11.0-amd64.deb
sudo dpkg -i filebeat-8.11.0-amd64.deb

# 步骤 2：配置 Filebeat
cat > /etc/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/nginx/access.log
  fields:
    log_type: nginx
  json.keys_under_root: true
  json.add_error_key: true

output.logstash:
  hosts: ["localhost:5044"]

logging.level: info
EOF

# 步骤 3：配置 Logstash Pipeline
cat > /etc/logstash/conf.d/nginx.conf << 'EOF'
input {
  beats { port => 5044 }
}

filter {
  grok {
    match => { "message" => '%{IPORHOST:client_ip} - %{DATA:user} \[%{HTTPDATE:timestamp}\] "%{WORD:method} %{URIPATHPARAM:request} HTTP/%{NUMBER:http_version}" %{NUMBER:status:int} %{NUMBER:bytes:int}' }
  }
  date {
    match => ["timestamp", "dd/MMM/yyyy:HH:mm:ss Z"]
  }
  mutate {
    remove_field => ["message", "timestamp"]
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "nginx-access-%{+YYYY.MM.dd}"
  }
}
EOF

# 步骤 4：启动服务
sudo systemctl start filebeat
sudo systemctl start logstash

# 步骤 5：验证
curl -s "localhost:9200/nginx-access-*/_count"
# 生成测试数据
for i in $(seq 1 100); do
  echo "192.168.1.$i - - [$(date +%d/%b/%Y:%H:%M:%S %z)] \"GET /api/test HTTP/1.1\" 200 1234" >> /var/log/nginx/access.log
done
sleep 10
curl -s "localhost:9200/nginx-access-*/_count"
```

### 练习 2：Fluentd 多数据源汇聚

```bash
# 步骤 1：使用 Docker 部署 Fluentd
cat > fluent.conf << 'EOF'
<source>
  @type tail
  path /var/log/app/access.log
  pos_file /var/log/fluentd/access.pos
  tag app.access
  <parse>
    @type json
  </parse>
</source>

<filter app.**>
  @type record_transformer
  <record>
    hostname ${hostname}
    tag ${tag}
  </record>
</filter>

<match app.**>
  @type stdout
</match>
EOF

docker run -d --name fluentd \
  -v $(pwd)/fluent.conf:/fluentd/etc/fluent.conf \
  -v /var/log/app:/var/log/app \
  fluent/fluentd:v1.16

# 步骤 2：生成测试日志
echo '{"timestamp":"2026-05-06T10:00:00","level":"info","message":"Request processed","user_id":"12345"}' >> /var/log/app/access.log

# 步骤 3：查看输出
docker logs fluentd --follow
```

### 练习 3：日志采集故障排查

```bash
# 场景：Filebeat 采集到数据，但 ES 中没有对应索引

# 步骤 1：检查 Filebeat 状态
sudo filebeat test output
# Expected: logstash... OK

# 步骤 2：检查 Filebeat 注册表
cat /var/lib/filebeat/registry/filebeat/log.json | jq '.[] | select(.Source | contains("access"))'

# 步骤 3：检查 Logstash Pipeline 状态
curl -s "localhost:9600/_node/stats/pipelines?pretty"

# 步骤 4：检查 Logstash 错误日志
grep -i error /var/log/logstash/logstash-plain.log | tail -20

# 步骤 5：检查 ES 集群状态
curl -s "localhost:9200/_cluster/health?pretty"

# 步骤 6：检查 ES 索引
curl -s "localhost:9200/_cat/indices?v&s=index"

# 步骤 7：手动测试写入
curl -X POST "localhost:9200/test-index/_doc" -H 'Content-Type: application/json' -d'{"message":"test"}'
```

---

## 🎯 面试题精选

### 1. Logstash 的 Pipeline 由哪几部分组成？每部分的作用是什么？

**答**：Logstash Pipeline 由三部分组成：
- **Input**：数据输入，支持 beats、file、kafka、tcp 等多种输入源
- **Filter**：数据处理，支持 grok 解析、mutate 字段操作、date 时间解析、geoip 地理定位等
- **Output**：数据输出，支持 elasticsearch、kafka、file、http 等多种输出目标

事件在 Pipeline 中按 Input → Queue → Filter → Queue → Output 的顺序流动。

### 2. Filebeat 如何保证日志不丢失？

**答**：Filebeat 通过以下机制保证 At-least-once 语义：
- **Registry 文件**：记录每个文件的 inode 和读取偏移量，重启后断点续传
- **ACK 机制**：事件发送成功后才更新 Registry
- **背压机制**：当输出端处理不过来时，自动降低采集速度
- **内存队列**：在发送前缓存事件

### 3. Fluentd 的 Tag 机制是什么？有什么作用？

**答**：Tag 是 Fluentd 事件的核心标识，格式为点分字符串（如 `app.nginx.access`）。Tag 的作用：
- **路由**：通过 `<match>` 指令将事件路由到对应的输出
- **过滤**：通过 `<filter>` 指令对特定 Tag 的事件进行处理
- **模式匹配**：支持通配符，如 `app.**` 匹配所有 `app.` 开头的事件

### 4. Logstash 和 Fluentd 在缓冲机制上有什么区别？

**答**：
- **Logstash**：支持内存队列和持久化队列（基于磁盘），持久化队列保证宕机不丢数据
- **Fluentd**：Buffer 插件支持文件和内存两种模式，每个 Output 可以独立配置 Buffer 策略，支持 timekey（按时间分片）和 chunk_limit_size（按大小分片）

### 5. 如何选择日志采集方案？

**答**：
- **资源受限**：Filebeat（Go 编写，10MB 内存）
- **简单场景**：Filebeat → ES（无需 Logstash）
- **复杂处理**：Filebeat → Logstash → ES
- **K8s 生态**：Fluent Bit（边缘）→ Fluentd（聚合）→ ES/Loki
- **多云环境**：Fluentd（统一日志层）
- **大数据量**：Filebeat → Kafka → Logstash → ES（削峰填谷）

### 6. Filebeat 的 multiline 配置有什么作用？如何配置？

**答**：multiline 用于将多行日志（如 Java 异常堆栈）合并为一个事件。

配置示例：
```yaml
multiline.type: pattern
multiline.pattern: '^\d{4}-\d{2}-\d{2}'  # 以日期开头的行为新事件
multiline.negate: true                      # 不匹配该模式的行
multiline.match: after                      # 附加到上一行之后
multiline.max_lines: 50                     # 最大合并行数
```

### 7. Logstash 的 Dead Letter Queue（DLQ）是什么？

**答**：DLQ 用于存储处理失败的事件。当 Output 端拒绝事件（如 ES 映射冲突）时，事件会被写入 DLQ 而非丢失。后续可以通过专门的 DLQ Input 插件重新处理这些事件。

启用方式：
```ruby
dead_letter_queue.enable: true
path.dead_letter_queue: "/var/lib/logstash/dead_letter_queue"
```

### 8. Fluentd 的 Buffer overflow_action 有哪些选项？

**答**：
- `throw_exception`：抛出异常，停止处理（默认）
- `block`：阻塞输入，等待缓冲区释放（推荐生产环境）
- `drop_oldest_chunk`：丢弃最旧的缓冲块

生产环境建议使用 `block`，避免数据丢失。

### 9. 如何监控日志采集管道的健康状态？

**答**：
- **Filebeat**：通过 HTTP 监控接口 `localhost:5067/stats`，关注 `events.acked` 和 `events.failed`
- **Logstash**：通过 API `localhost:9600/_node/stats/pipelines`，关注 `events.in/out` 和 `events.duration_in_millis`
- **Fluentd**：通过 `fluentd-monitor-agent` 插件或 Prometheus exporter
- **告警指标**：事件丢失率、处理延迟、队列积压量、错误率

### 10. 在大规模日志场景下，如何设计日志采集架构？

**答**：

```
推荐架构：
  Filebeat/Fluent Bit（每台机器）
    → Kafka（缓冲层）
      → Logstash/Fluentd（处理层）
        → Elasticsearch/Loki（存储层）

关键设计点：
  1. 边缘采集使用轻量工具（Filebeat/Fluent Bit）
  2. Kafka 削峰填谷，解耦上下游
  3. 处理层可水平扩展
  4. 存储层使用 ILM 管理生命周期
  5. 多 Pipeline/Topic 隔离不同优先级日志
  6. 监控采集管道的健康状态
```

---

## 📚 深入阅读

- [Logstash 官方文档](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Fluentd 官方文档](https://docs.fluentd.org/)
- [Filebeat 官方文档](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
- [Fluent Bit 官方文档](https://docs.fluentbit.io/)
- [CNCF Fluentd 项目](https://www.fluentd.org/)

---

## ✅ 自检清单

- [ ] 理解 Logstash 的 Pipeline 执行模型
- [ ] 掌握 Input、Filter、Output 插件的配置
- [ ] 掌握 Grok 模式的编写和调试
- [ ] 理解 Fluentd 的 Tag 路由机制
- [ ] 掌握 Filebeat 的配置和模块系统
- [ ] 能根据场景选择合适的日志采集方案
- [ ] 理解三大采集工具的优缺点
- [ ] 掌握日志采集管道的监控方法
- [ ] 能排查日志丢失、延迟等常见问题
- [ ] 理解 Buffer 和重试机制
