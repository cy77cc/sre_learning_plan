# Day 142: Kibana 日志可视化（安装配置、Discover、Visualize、Dashboard、索引模式、告警、最佳实践）

> 📅 日期：2026-05-07
> 📖 学习主题：Kibana 安装配置、Discover 日志探索、Visualize 可视化、Dashboard 仪表盘、告警系统
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 140 (Elasticsearch 基础), Day 141 (Logstash/Fluentd)

## 🎯 学习目标

- 掌握 Kibana 的安装配置与核心概念
- 熟练使用 Discover 进行日志搜索和过滤
- 掌握多种可视化图表的创建方法
- 能够设计生产级 Dashboard 仪表盘
- 理解 Kibana 告警系统的配置
- 掌握 KQL（Kibana Query Language）查询语法

---

## 📖 核心知识点

### 1. Kibana 概述与架构

```
Kibana 在 ELK Stack 中的位置：

┌─────────────────────────────────────────────────────────────────┐
│                    Kibana 架构                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  用户层                                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    浏览器 (Chrome/Firefox)                │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Kibana Server                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Discover │ │Visualize │ │ Dashboard│ │  DevTools │  │    │
│  │  │ 日志探索  │ │ 可视化    │ │  仪表盘   │ │  开发工具  │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Alerting │ │  Canvas  │ │  Maps   │ │  Machine │  │    │
│  │  │  告警     │ │  画布     │ │  地图    │ │  Learning│  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Elasticsearch Cluster                    │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │    │
│  │  │ Node 1  │  │ Node 2  │  │ Node 3  │                 │    │
│  │  └─────────┘  └─────────┘  └─────────┘                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 安装与配置

#### 2.1 Docker 部署

```yaml
# docker-compose.yml (Kibana 部分)
services:
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    environment:
      # ES 连接
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=kibana_system
      - ELASTICSEARCH_PASSWORD=${KIBANA_PASSWORD}

      # 服务配置
      - SERVER_NAME=kibana
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=5601
      - SERVER_BASEPATH=

      # 安全配置
      - XPACK_SECURITY_ENABLED=true
      - XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY=32位随机字符串

      # 性能配置
      - NODE_OPTIONS=--max-old-space-size=2048

      # 日志配置
      - LOGGING_ROOT_LEVEL=info
      - LOGGING_DESTINATION=stdout
    ports:
      - "5601:5601"
    volumes:
      - kibana-data:/usr/share/kibana/data
    networks:
      - elk-network
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:5601/api/status | grep -q 'available'"]
      interval: 30s
      timeout: 10s
      retries: 5
```

#### 2.2 kibana.yml 关键配置

```yaml
# kibana.yml 核心配置

# ========== 服务配置 ==========
server.name: kibana
server.host: "0.0.0.0"
server.port: 5601
server.basePath: ""                    # 反向代理时设置
server.publicBaseUrl: "https://kibana.example.com"

# ========== ES 连接 ==========
elasticsearch.hosts: ["http://es-node-1:9200", "http://es-node-2:9200"]
elasticsearch.username: "kibana_system"
elasticsearch.password: "${KIBANA_PASSWORD}"
elasticsearch.requestTimeout: 30000
elasticsearch.shardTimeout: 30000

# ========== 安全配置 ==========
xpack.security.enabled: true
xpack.encryptedSavedObjects.encryptionKey: "a]Vx{>3-!sH>wg}t3p#rR+u5h-x=Z.8f"

# ========== 性能配置 ==========
# Node.js 内存
node.options: "--max-old-space-size=2048"

# 图表渲染限制
# elasticsearch.maxBuckets: 65535
# vis_type_vega.enableExternalUrls: true

# ========== 日志配置 ==========
logging.root.level: info
logging.appenders.default:
  type: console
  layout:
    type: json
```

### 3. 索引模式（Data Views）

```
索引模式（Index Pattern / Data View）是 Kibana 查询 ES 数据的桥梁：

┌──────────────────────────────────────────────────────────────┐
│                    Data View / Index Pattern                   │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  Data View: "nginx-logs-*"                                     │
│  ├── 匹配索引: nginx-logs-2026.05.01, nginx-logs-2026.05.02  │
│  ├── 时间字段: @timestamp                                      │
│  └── 字段属性:                                                 │
│      ├── client_ip: keyword                                    │
│      ├── method: keyword                                       │
│      ├── request: text                                         │
│      ├── status: number                                        │
│      ├── bytes: number                                         │
│      └── response_time: number                                 │
│                                                                │
│  作用：                                                        │
│  1. 定义搜索范围（哪些索引）                                    │
│  2. 定义时间过滤字段                                           │
│  3. 定义字段类型和格式                                         │
│  4. 支持通配符匹配多个索引                                     │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

```bash
# 通过 API 创建 Data View
curl -X POST "localhost:5601/api/data_views/data_view" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "data_view": {
      "title": "app-logs-*",
      "timeFieldName": "@timestamp",
      "name": "Application Logs",
      "fieldAttrs": {
        "level": { "customLabel": "日志级别" },
        "service": { "customLabel": "服务名称" }
      }
    }
  }'
```

### 4. Discover 日志探索

#### 4.1 KQL 查询语法

```
KQL（Kibana Query Language）语法：

精确匹配：
  status: 200                    # 字段值精确匹配
  status: (200 or 201)           # 多值匹配
  not status: 500                # 排除

全文搜索：
  error                          # 搜索所有字段包含 "error"
  "connection timeout"           # 短语搜索

范围查询：
  response_time > 1000           # 大于
  response_time >= 500           # 大于等于
  response_time < 100            # 小于
  bytes >= 1000 and bytes <= 5000 # 范围

通配符：
  host: web-*                    # 前缀通配
  message: *error*               # 包含匹配（性能差，慎用）

存在性：
  error.message: *               # 字段存在
  not error.message: *           # 字段不存在

布尔组合：
  status: 500 and service: payment-service
  status: 500 or status: 503
  (status: 500 or status: 503) and service: payment-service

嵌套字段：
  host.os.name: "Linux"
  request.method: "POST"
```

#### 4.2 Lucene 查询语法

```
Lucene 查询语法（Kibana 也支持）：

模糊搜索：
  message:error                   # 包含 error
  message:"connection timeout"    # 短语匹配
  message:err~                    # 模糊匹配（编辑距离 2）

通配符：
  host:web?                       # 单字符匹配
  host:web*                       # 多字符匹配

正则表达式：
  message:/error|exception/       # 正则匹配

范围：
  response_time:[500 TO 1000]    # 闭区间
  response_time:{500 TO 1000}    # 开区间

布尔：
  status:500 AND service:payment
  status:500 OR status:503
  NOT status:200

提升：
  message:error^2 message:warning  # error 权重更高
```

#### 4.3 Discover 界面功能

```
Discover 核心功能：

┌─────────────────────────────────────────────────────────────────┐
│  Discover 界面布局                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  顶部工具栏                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Data View: [nginx-logs-* ▼]  时间: [Last 24 hours ▼]    │    │
│  │ 查询栏: [status: 500 and service: payment    ] [Search]  │    │
│  │ [Add filter] [Save] [Share] [Inspect]                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  左侧边栏                                                         │
│  ┌──────────────┐                                               │
│  │ 字段列表      │                                               │
│  │ ├── Available │                                               │
│  │ │  ├── @timestamp │                                          │
│  │ │  ├── client_ip  │                                          │
│  │ │  ├── level      │  点击字段 → 查看 Top Values              │
│  │ │  ├── message    │                                          │
│  │ │  └── service    │                                          │
│  │ └── Selected     │                                           │
│  │    (已选字段)     │                                           │
│  └──────────────┘                                               │
│                                                                   │
│  主区域                                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 时间柱状图（文档分布）                                      │    │
│  │ ▂▃▅▇█▇▅▃▂▃▅▇█▇▅▃▂                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 文档列表                                                  │    │
│  │ 10:30:00 | error | payment-service | Connection timeout   │    │
│  │ 10:30:01 | error | user-service    | NullPointerException │    │
│  │ 10:30:02 | error | order-service   | Database error       │    │
│  │ ... (共 1,234 hits)                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

关键操作：
  1. 选择 Data View → 确定搜索范围
  2. 设置时间范围 → 过滤时间窗口
  3. 输入 KQL/Lucene 查询 → 筛选日志
  4. 添加 Filter → 结构化过滤
  5. 选择显示字段 → 定制视图
  6. 保存搜索 → 复用查询
```

### 5. Visualize 可视化

#### 5.1 可视化类型

```
Kibana 可视化类型：

┌──────────────────────────────────────────────────────────────┐
│                    可视化类型大全                               │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  基础图表                                                      │
│  ├── Line（折线图）- 趋势分析                                  │
│  ├── Area（面积图）- 累积趋势                                  │
│  ├── Bar（柱状图）- 分类对比                                   │
│  ├── Horizontal Bar（水平柱状图）- 分类对比（大量类别）         │
│  ├── Pie（饼图）- 占比分析（≤5 类别）                          │
│  ├── Donut（环形图）- 占比分析                                 │
│  └── Gauge（仪表盘）- 单值展示                                 │
│                                                                │
│  统计图表                                                      │
│  ├── Metric（指标）- 单个数值                                  │
│  ├── Goal（目标）- 进度展示                                    │
│  └── TSVB（Time Series Visual Builder）- 高级时序分析          │
│                                                                │
│  地理图表                                                      │
│  ├── Maps（地图）- 地理分布                                    │
│  └── Coordinate Map（坐标地图）- 热力图                        │
│                                                                │
│  数据表                                                        │
│  ├── Data Table（数据表）- 表格展示                            │
│  └── Lens（拖拽式可视化）- 推荐使用                            │
│                                                                │
│  高级                                                          │
│  ├── Vega（自定义可视化）- 完全自定义                          │
│  ├── Timelion（时序分析）- 时序对比                            │
│  └── Canvas（画布）- 报告和演示                                │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 常用可视化配置

```
Lens（推荐的可视化方式）：

1. 错误率趋势图（折线图）
   - Y 轴: Count of documents
   - X 轴: @timestamp (按小时)
   - 过滤: level: "error"
   - 分组: service.keyword

2. HTTP 状态码分布（饼图）
   - 指标: Count
   - 分组: status.keyword
   - 过滤: 最近 24 小时

3. 平均响应时间（指标）
   - 指标: Average of response_time
   - 过滤: 最近 1 小时

4. Top 10 慢请求（数据表）
   - 指标: response_time (Top 10)
   - 分组: request.keyword
   - 排序: response_time DESC

5. 日志级别分布（柱状图）
   - Y 轴: Count
   - X 轴: level.keyword
   - 分组: @timestamp (按天)
```

#### 5.3 TSVB 高级可视化

```
TSVB（Time Series Visual Builder）配置示例：

1. 错误率百分比
   - Metric: Count
   - Filter: level: "error"
   - Calculation: count_errors / count_total * 100
   - 显示: 百分比趋势线

2. P99 延迟
   - Metric: Percentile of response_time (99th)
   - Group By: service.keyword
   - 显示: 多服务 P99 对比

3. 请求量 QPS
   - Metric: Count
   - Aggregation: Rate (per second)
   - Group By: method.keyword
   - 显示: 各 HTTP 方法的 QPS
```

### 6. Dashboard 设计

#### 6.1 Dashboard 设计原则

```
Dashboard 设计最佳实践：

┌──────────────────────────────────────────────────────────────┐
│                    Dashboard 设计原则                          │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. 分层设计                                                   │
│     ┌────────────────────────────────────┐                   │
│     │  Layer 1: 关键指标（顶部）           │                   │
│     │  QPS | 错误率 | P99延迟 | 可用性    │                   │
│     ├────────────────────────────────────┤                   │
│     │  Layer 2: 趋势分析（中部）           │                   │
│     │  错误趋势 | 流量趋势 | 延迟趋势     │                   │
│     ├────────────────────────────────────┤                   │
│     │  Layer 3: 分布分析（中下部）         │                   │
│     │  状态码分布 | 服务分布 | 地域分布   │                   │
│     ├────────────────────────────────────┤                   │
│     │  Layer 4: 详细数据（底部）           │                   │
│     │  Top 错误 | 慢请求 | 异常日志       │                   │
│     └────────────────────────────────────┘                   │
│                                                                │
│  2. 配色规范                                                   │
│     - 绿色/蓝色: 正常指标                                      │
│     - 黄色/橙色: 警告指标                                      │
│     - 红色: 错误/异常指标                                      │
│     - 灰色: 参考/基线数据                                      │
│                                                                │
│  3. 交互设计                                                   │
│     - 添加时间范围选择器                                       │
│     - 支持下钻（Drill-down）                                   │
│     - 使用变量（Variables）实现动态过滤                         │
│     - 合理使用面板标题和描述                                   │
│                                                                │
│  4. 性能优化                                                   │
│     - 避免过多面板（建议 ≤20 个）                              │
│     - 使用合理的时间间隔                                       │
│     - 避免高基数聚合                                           │
│     - 使用缓存                                                 │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 生产级 Dashboard 示例

```json
{
  "title": "应用日志监控 Dashboard",
  "description": "实时监控应用日志状态",
  "panelsJSON": [
    {
      "title": "QPS（每秒请求数）",
      "type": "metric",
      "gridData": { "x": 0, "y": 0, "w": 6, "h": 4 },
      "config": {
        "metric": { "type": "count" },
        "interval": "1m"
      }
    },
    {
      "title": "错误率",
      "type": "metric",
      "gridData": { "x": 6, "y": 0, "w": 6, "h": 4 },
      "config": {
        "metric": { "type": "count" },
        "filter": "level: error",
        "percentage": true
      }
    },
    {
      "title": "P99 延迟",
      "type": "metric",
      "gridData": { "x": 12, "y": 0, "w": 6, "h": 4 },
      "config": {
        "metric": { "type": "percentile", "field": "response_time", "percentile": 99 }
      }
    },
    {
      "title": "错误趋势",
      "type": "line",
      "gridData": { "x": 0, "y": 4, "w": 12, "h": 8 },
      "config": {
        "metrics": [{ "type": "count" }],
        "split_group": "level.keyword",
        "time_field": "@timestamp"
      }
    },
    {
      "title": "HTTP 状态码分布",
      "type": "pie",
      "gridData": { "x": 12, "y": 4, "w": 12, "h": 8 },
      "config": {
        "metric": { "type": "count" },
        "bucket": { "type": "terms", "field": "status.keyword", "size": 10 }
      }
    }
  ]
}
```

### 7. Kibana 告警系统

#### 7.1 告警规则类型

```
Kibana 告警规则类型：

┌──────────────────────────────────────────────────────────────┐
│                    Alerting 告警系统                           │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  规则类型：                                                    │
│  ├── Elasticsearch Query - 基于查询条件                       │
│  ├── Threshold - 指标阈值                                     │
│  ├── Anomaly Detection - 异常检测（ML）                       │
│  └── Custom - 自定义规则                                      │
│                                                                │
│  连接器（Actions）：                                           │
│  ├── Email - 邮件通知                                         │
│  ├── Slack - Slack 消息                                       │
│  ├── Webhook - HTTP 回调                                      │
│  ├── PagerDuty - 事件管理                                     │
│  ├── ServiceNow - ITSM                                        │
│  └── Index - 写入 ES 索引                                     │
│                                                                │
│  告警流程：                                                    │
│  规则触发 → 条件评估 → 创建告警 → 执行动作                     │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 7.2 告警规则配置

```json
// 通过 API 创建告警规则
{
  "name": "应用错误率告警",
  "rule_type_id": ".es-query",
  "consumer": "alerts",
  "schedule": {
    "interval": "1m"
  },
  "params": {
    "index": ["app-logs-*"],
    "timeField": "@timestamp",
    "esQuery": "{\"bool\":{\"must\":[{\"match\":{\"level\":\"error\"}}]}}",
    "threshold": [100],
    "thresholdComparator": ">",
    "timeWindowSize": 5,
    "timeWindowUnit": "m",
    "size": 100,
    "searchType": "esQuery"
  },
  "actions": [
    {
      "group": "threshold_met",
      "id": "slack-connector-id",
      "params": {
        "message": "应用错误率告警：最近 5 分钟错误数 {{context.hits}} 超过阈值 100"
      }
    },
    {
      "group": "threshold_met",
      "id": "email-connector-id",
      "params": {
        "to": ["oncall@example.com"],
        "subject": "[告警] 应用错误率异常",
        "body": "服务 {{context.service}} 最近 5 分钟错误数 {{context.hits}}"
      }
    }
  ],
  "tags": ["application", "error"],
  "notify_when": "onActiveAlert",
  "enabled": true
}
```

### 8. Kibana Dev Tools

```
Dev Tools 是 Kibana 内置的 Elasticsearch 交互工具：

常用操作：

1. 集群健康
   GET _cluster/health

2. 查看索引
   GET _cat/indices?v&s=store.size:desc

3. 搜索日志
   GET app-logs-*/_search
   {
     "query": {
       "bool": {
         "must": [
           { "match": { "level": "error" } }
         ],
         "filter": [
           { "range": { "@timestamp": { "gte": "now-1h" } } }
         ]
       }
     },
     "size": 10,
     "sort": [{ "@timestamp": "desc" }]
   }

4. 聚合分析
   GET app-logs-*/_search
   {
     "size": 0,
     "aggs": {
       "by_service": {
         "terms": { "field": "service.keyword", "size": 20 },
         "aggs": {
           "error_count": {
             "filter": { "term": { "level": "error" } }
           },
           "avg_response_time": {
             "avg": { "field": "response_time" }
           }
         }
       }
     }
   }

5. 查看分片分配
   GET _cat/shards?v&h=index,shard,prirep,state,docs,store,node

6. 查看慢查询
   GET _nodes/hot_threads
```

### 9. SRE 实战案例

#### 9.1 日志量突增排查

```
故障现象：
  Dashboard 显示日志量突然增加 10 倍，需要排查原因

排查步骤：

1. 打开 Discover，查看时间柱状图
   → 确认日志量在 10:30 开始突增

2. 按服务分组查看
   → 发现 payment-service 日志量占比 80%

3. 按日志级别过滤
   → 发现 level:warn 日志量激增
   → 内容：「Rate limit exceeded for API key xxx」

4. 查看具体的日志内容
   → 发现大量重试请求

5. 根因：
   → 第三方支付 API 限流，客户端不断重试导致日志暴增

6. 修复：
   → 实施退避重试策略
   → 添加限流日志采样
```

#### 9.2 Dashboard 性能优化

```
问题：Dashboard 加载时间超过 30 秒

优化方案：

1. 减少面板数量
   → 将 30 个面板减少到 15 个
   → 合并相似的面板

2. 优化查询
   → 使用 filter 代替 query（可缓存）
   → 限制聚合的 cardinality
   → 使用合理的 time interval

3. 使用 Data View 缓存
   → 启用 Data View 的字段缓存

4. 调整刷新间隔
   → 从自动刷新改为手动刷新
   → 设置合理的刷新间隔（30s+）

5. 使用 TSVB 代替 Lens（特定场景）
   → TSVB 在某些聚合场景下性能更好
```

---

## 💻 实战练习

### 练习 1：创建完整的日志分析 Dashboard

```bash
# 目标：创建一个包含 6 个面板的 Dashboard

# 步骤 1：创建 Data View
# 在 Kibana → Stack Management → Data Views
# 创建 "app-logs-*" Data View，时间字段选 @timestamp

# 步骤 2：创建可视化面板
# Panel 1: 错误数量指标（Metric）
# Panel 2: 日志趋势折线图（Line）
# Panel 3: 错误级别分布（Pie）
# Panel 4: Top 10 服务错误数（Bar）
# Panel 5: 响应时间分布（Histogram）
# Panel 6: 最新错误日志表（Saved Search）

# 步骤 3：组装 Dashboard
# 创建 Dashboard，添加所有面板
# 设置全局时间范围：Last 24 hours
# 添加过滤器：environment: production
```

### 练习 2：配置告警规则

```bash
# 目标：配置错误率告警

# 步骤 1：创建 Webhook 连接器
# Stack Management → Connectors → Create → Webhook
# URL: http://alertmanager:9095/api/alerts
# Method: POST

# 步骤 2：创建告警规则
# Stack Management → Rules → Create Rule
# Type: Elasticsearch query
# Query: level: "error"
# Threshold: > 100 errors in 5 minutes
# Action: Send to Webhook

# 步骤 3：验证告警
# 生成超过阈值的错误日志
# 确认告警触发并发送通知
```

### 练习 3：高级查询与分析

```bash
# 目标：使用 KQL 和聚合进行深度分析

# 场景：分析支付服务的错误模式

# 查询 1：最近 1 小时的错误分布
# KQL: service: "payment" and level: "error"
# 按 error_type 分组，查看 Top 10

# 查询 2：慢请求分析
# KQL: service: "payment" and response_time > 5000
# 按 request.path 分组，查看最慢的接口

# 查询 3：错误率趋势
# 使用 TSVB 创建错误率百分比图
# 分子: level: "error"
# 分母: 全部日志
# 时间间隔: 1 分钟
```

---

## 🎯 面试题精选

### 1. KQL 和 Lucene 查询语法有什么区别？

**答**：
- **KQL**：Kibana 原生语法，更简洁直观，支持字段自动补全，不支持正则表达式
- **Lucene**：传统查询语法，功能更强大，支持正则、模糊匹配、权重调整

KQL 是推荐使用的语法，简单场景足够。需要复杂匹配时使用 Lucene。

### 2. 如何优化 Kibana Dashboard 的性能？

**答**：
1. 减少面板数量（建议 ≤20 个）
2. 使用 filter 代替 query（filter 可缓存）
3. 设置合理的刷新间隔
4. 限制聚合的 cardinality（terms size 不要太大）
5. 使用合理的时间间隔（避免 1 秒粒度查看 30 天数据）
6. 启用 Data View 缓存
7. 避免在大范围数据上使用高基数聚合

### 3. Data View（索引模式）的作用是什么？

**答**：Data View 是 Kibana 查询 ES 数据的桥梁，它定义了：
- 查询哪些索引（支持通配符）
- 使用哪个字段作为时间过滤
- 每个字段的类型和显示格式
- 支持字段别名和格式化

### 4. Kibana 告警系统有哪些告警规则类型？

**答**：
- **Elasticsearch Query**：基于 ES 查询条件，当匹配文档数超过阈值时触发
- **Threshold**：基于指标聚合值，如错误率、平均延迟超过阈值
- **Anomaly Detection**：基于机器学习的异常检测
- **Index Threshold**：索引级别的阈值告警
- **Custom**：自定义规则

### 5. 如何在 Kibana 中实现日志下钻分析？

**答**：
1. 从 Dashboard 的概览面板发现异常
2. 点击面板跳转到 Discover（设置 drill-down link）
3. 在 Discover 中使用 KQL 细化查询
4. 按字段分组（如 service、host、level）
5. 查看具体日志内容
6. 使用字段过滤缩小范围

### 6. TSVB 和 Lens 有什么区别？什么时候用哪个？

**答**：
- **Lens**：拖拽式可视化，简单易用，推荐日常使用
- **TSVB**：配置式可视化，功能更强大，支持复杂计算（如百分比、排名）

推荐：简单图表用 Lens，需要复杂计算或自定义样式的用 TSVB。

### 7. Kibana 的 saved objects 有哪些类型？

**答**：
- **Search**：保存的搜索查询
- **Visualization**：保存的可视化图表
- **Dashboard**：保存的仪表盘
- **Data View**：保存的索引模式
- **Rule**：保存的告警规则
- **Connector**：保存的告警连接器
- **Canvas Workpad**：保存的画布
- **Map**：保存的地图

### 8. 如何在 Kibana 中进行日志的实时监控？

**答**：
1. 创建 Dashboard 并设置自动刷新（5-30 秒）
2. 使用 KQL 实时查询最新日志
3. 配置告警规则实现异常通知
4. 使用 Discover 的实时模式查看最新文档
5. 设置 Watcher（旧版）或 Alerting（新版）实现定时检查

---

## 📚 深入阅读

- [Kibana 官方文档](https://www.elastic.co/guide/en/kibana/current/index.html)
- [KQL 查询语法](https://www.elastic.co/guide/en/kibana/current/kuery-query.html)
- [Kibana Lens](https://www.elastic.co/guide/en/kibana/current/lens.html)
- [Kibana Alerting](https://www.elastic.co/guide/en/kibana/current/alerting-getting-started.html)

---

## ✅ 自检清单

- [ ] 能够安装和配置 Kibana
- [ ] 掌握 KQL 和 Lucene 查询语法
- [ ] 能够使用 Discover 搜索和过滤日志
- [ ] 掌握多种可视化图表的创建方法
- [ ] 能够设计生产级 Dashboard
- [ ] 理解告警系统的配置
- [ ] 掌握 Dev Tools 的常用操作
- [ ] 能够进行日志下钻分析
- [ ] 理解 Dashboard 性能优化方法
