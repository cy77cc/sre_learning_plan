# Day 140: 日志收集基础 — ELK（Elasticsearch 架构、索引/映射/分词、安装配置、集群管理、性能调优）

> 📅 日期：2026-05-05
> 📖 学习主题：Elasticsearch 核心架构、索引与映射机制、分词器、集群管理与性能调优
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 133 (可观测性基础), Day 134 (Prometheus 基础), Day 13 (日志管理)

## 🎯 学习目标

- 深入理解 Elasticsearch 的分布式架构与核心概念
- 掌握索引、映射、分词器的原理与配置
- 能够部署单节点和多节点 ES 集群
- 理解集群健康状态、分片分配与故障恢复机制
- 掌握 ES 性能调优的关键参数与最佳实践
- 能够设计生产级日志索引策略（ILM、Rollover、别名）

---

## 📖 核心知识点

### 1. ELK Stack 概述

ELK 是 Elasticsearch + Logstash + Kibana 的缩写，是业界最经典的日志收集与分析平台。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ELK Stack 全景架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  数据源层                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ 应用日志  │ │ 系统日志  │ │ 审计日志  │ │ 访问日志  │ │ 容器日志  │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │            │            │            │            │             │
│  采集层                                                           │       │
│  ┌────┴────────────┴────────────┴────────────┴────────────┴──────┐    │
│  │              Filebeat / Fluentd / Logstash Agent              │    │
│  └──────────────────────────┬────────────────────────────────────┘    │
│                              │                                         │
│  处理层                                                                │
│  ┌──────────────────────────┴────────────────────────────────────┐    │
│  │                    Logstash Pipeline                           │    │
│  │   Input → Filter (Grok/Mutate/GeoIP) → Output                │    │
│  └──────────────────────────┬────────────────────────────────────┘    │
│                              │                                         │
│  存储与索引层                                                          │
│  ┌──────────────────────────┴────────────────────────────────────┐    │
│  │                   Elasticsearch Cluster                        │    │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │    │
│  │   │ Node 1  │  │ Node 2  │  │ Node 3  │  │ Node N  │       │    │
│  │   │(Master) │  │(Data)   │  │(Data)   │  │(Coordin.)│       │    │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘       │    │
│  └──────────────────────────┬────────────────────────────────────┘    │
│                              │                                         │
│  可视化层                                                              │
│  ┌──────────────────────────┴────────────────────────────────────┐    │
│  │                         Kibana                                 │    │
│  │   Discover │ Visualize │ Dashboard │ Alerting │ Dev Tools     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### ELK 各组件职责

| 组件 | 职责 | 默认端口 | 数据流向 |
|------|------|----------|----------|
| Filebeat | 轻量级日志采集 | - | 日志文件 → Logstash/ES |
| Logstash | 日志解析、转换、富化 | 5044 (Beats), 9600 (API) | Input → Filter → Output |
| Elasticsearch | 分布式存储、索引、搜索 | 9200 (HTTP), 9300 (Transport) | 接收、索引、查询 |
| Kibana | 可视化、探索、告警 | 5601 | 从 ES 查询并展示 |

### 2. Elasticsearch 核心架构

#### 2.1 基本概念

```
Elasticsearch 概念层次：

Cluster（集群）
 └── Node（节点）
      └── Index（索引）= Database
           └── Shard（分片）= 数据分区
                └── Segment（段）= Lucene 索引
                     └── Document（文档）= 一行记录
                          └── Field（字段）= 列

类比关系型数据库：
  Cluster  ≈ 数据库集群
  Index    ≈ Database / Table
  Document ≈ Row
  Field    ≡ Column
  Mapping  ≈ Schema
  Shard    ≈ 水平分区
```

#### 2.2 节点类型

```
┌─────────────────────────────────────────────────────────────┐
│                    Elasticsearch 节点类型                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Master Node（主节点）                                        │
│  ├── 负责集群级别的元数据管理                                   │
│  ├── 索引创建/删除、分片分配                                    │
│  ├── 节点加入/离开集群                                         │
│  └── 建议：专用主节点，不存储数据                                │
│                                                               │
│  Data Node（数据节点）                                        │
│  ├── 存储数据、执行 CRUD、搜索、聚合                            │
│  ├── I/O 和 CPU 密集型                                        │
│  └── 建议：高配置，SSD 存储                                    │
│                                                               │
│  Coordinating Node（协调节点）                                │
│  ├── 接收客户端请求，路由到对应数据节点                          │
│  ├── 聚合各分片结果返回给客户端                                 │
│  └── 建议：独立部署，减轻数据节点压力                            │
│                                                               │
│  Ingest Node（预处理节点）                                    │
│  ├── 在索引前对文档进行预处理                                   │
│  ├── 类似轻量级 Logstash                                      │
│  └── 使用 Pipeline 处理文档                                   │
│                                                               │
│  ML Node（机器学习节点）                                      │
│  ├── 异常检测、数据帧分析                                      │
│  └── 需要付费功能                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3 分片与副本机制

```
索引 my-logs（2 主分片 + 1 副本）

         Primary Shard 0          Primary Shard 1
        ┌──────────────┐        ┌──────────────┐
        │  Doc 1,3,5,7 │        │  Doc 2,4,6,8 │
        │  ...          │        │  ...          │
        └──────┬───────┘        └──────┬───────┘
               │                       │
        ┌──────┴───────┐        ┌──────┴───────┐
        │  Replica 0   │        │  Replica 1   │
        │  (副本)       │        │  (副本)       │
        └──────────────┘        └──────────────┘

分片分配规则：
  - 主分片和副本不会分配到同一节点
  - 文档通过 routing 算法分配到分片：shard = hash(_routing) % num_primary_shards
  - 主分片数量在索引创建后不可更改（除非 Reindex）
  - 副本数量可以动态调整
```

#### 2.4 写入流程

```
写入文档的完整流程：

Client
  │
  ▼
Coordinating Node（协调节点）
  │
  ▼ 根据 routing 计算目标分片
  │
  ▼
Primary Shard（主分片）
  │
  ├── 1. 写入 Translog（事务日志，保证持久性）
  ├── 2. 写入 In-memory Buffer（内存缓冲区）
  ├── 3. Refresh（默认每 1 秒）→ 生成新 Segment → 可搜索
  ├── 4. Flush（默认 30 分钟 / Translog 满 512MB）
  │      → 清空 Translog
  │      → 将 Segment 持久化到磁盘
  │      → 删除旧 Translog
  │
  ▼
Replica Shard（副本分片）
  │
  └── 同步复制到所有副本

关键点：
  - Refresh 后文档才可被搜索（近实时 NRT）
  - Translog 保证宕机不丢数据
  - Flush 后数据真正持久化
```

#### 2.5 读取流程

```
搜索请求的完整流程：

Client → GET /my-logs/_search?q=error
  │
  ▼
Coordinating Node
  │
  ├── 1. Query Phase（查询阶段）
  │      ├── 将请求广播到所有相关分片
  │      ├── 每个分片本地执行查询
  │      ├── 返回文档 ID + 排序值（不返回完整文档）
  │      └── 协调节点合并排序，确定需要的文档
  │
  ├── 2. Fetch Phase（获取阶段）
  │      ├── 根据文档 ID 向对应分片请求完整文档
  │      └── 组装最终结果返回给客户端
  │
  ▼
返回结果给 Client
```

### 3. 索引（Index）详解

#### 3.1 创建索引

```bash
# 创建索引并指定分片和副本数
curl -X PUT "localhost:9200/app-logs" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "5s",
    "index.codec": "best_compression",
    "index.translog.durability": "async",
    "index.translog.sync_interval": "5s"
  },
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "level": { "type": "keyword" },
      "message": { "type": "text", "analyzer": "standard" },
      "service": { "type": "keyword" },
      "host": { "type": "keyword" },
      "response_time": { "type": "float" },
      "status_code": { "type": "integer" },
      "user_agent": { "type": "text", "analyzer": "standard" },
      "geo": { "type": "geo_point" }
    }
  }
}'
```

#### 3.2 索引别名（Alias）

```bash
# 创建别名
curl -X POST "localhost:9200/_aliases" -H 'Content-Type: application/json' -d'
{
  "actions": [
    { "add": { "index": "app-logs-2026.05.05", "alias": "app-logs-write" } },
    { "add": { "index": "app-logs-2026.05.05", "alias": "app-logs-read" } },
    { "add": { "index": "app-logs-2026.05.04", "alias": "app-logs-read" } },
    { "add": { "index": "app-logs-2026.05.03", "alias": "app-logs-read" } }
  ]
}'

# 使用别名查询（自动查询所有关联索引）
curl "localhost:9200/app-logs-read/_search?q=level:error"

# 原子切换写入别名（零停机切换）
curl -X POST "localhost:9200/_aliases" -H 'Content-Type: application/json' -d'
{
  "actions": [
    { "remove": { "index": "app-logs-2026.05.05", "alias": "app-logs-write" } },
    { "add": { "index": "app-logs-2026.05.06", "alias": "app-logs-write" } }
  ]
}'
```

#### 3.3 索引生命周期管理（ILM）

```
ILM 策略的四个阶段：

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   Hot    │───▶│  Warm    │───▶│  Cold    │───▶│  Delete  │
│  热阶段   │    │  温阶段   │    │  冷阶段   │    │  删除     │
├──────────┤    ├──────────┤    ├──────────┤    ├──────────┤
│ 高性能SSD │    │ 普通磁盘  │    │ 归档存储  │    │ 自动删除  │
│ 可写入    │    │ 只读     │    │ 只读     │    │          │
│ Rollover │    │ Shrink  │    │ Freeze  │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

触发条件示例：
  Hot → Warm: 索引大小 > 50GB 或 时间 > 1 天
  Warm → Cold: 时间 > 7 天
  Cold → Delete: 时间 > 30 天
```

```bash
# 创建 ILM 策略
curl -X PUT "localhost:9200/_ilm/policy/logs-policy" -H 'Content-Type: application/json' -d'
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_primary_shard_size": "50gb",
            "max_age": "1d"
          },
          "set_priority": { "priority": 100 }
        }
      },
      "warm": {
        "min_age": "2d",
        "actions": {
          "shrink": { "number_of_shards": 1 },
          "forcemerge": { "max_num_segments": 1 },
          "set_priority": { "priority": 50 },
          "allocate": {
            "number_of_replicas": 0,
            "require": { "data": "warm" }
          }
        }
      },
      "cold": {
        "min_age": "7d",
        "actions": {
          "allocate": {
            "require": { "data": "cold" }
          },
          "set_priority": { "priority": 0 }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

# 创建索引模板，关联 ILM 策略
curl -X PUT "localhost:9200/_index_template/logs-template" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["app-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "index.lifecycle.name": "logs-policy",
      "index.lifecycle.rollover_alias": "app-logs-write"
    },
    "mappings": {
      "properties": {
        "timestamp": { "type": "date" },
        "level": { "type": "keyword" },
        "message": { "type": "text" },
        "service": { "type": "keyword" }
      }
    }
  },
  "priority": 200
}'
```

### 4. 映射（Mapping）详解

#### 4.1 字段类型

```
Elasticsearch 核心字段类型：

文本类型：
  text      - 全文检索，会被分词，不支持排序/聚合
  keyword   - 精确值，不分词，支持排序/聚合、过滤

数值类型：
  byte      - [-128, 127]
  short     - [-32768, 32767]
  integer   - [-2^31, 2^31-1]
  long      - [-2^63, 2^63-1]
  float     - 32 位单精度
  double    - 64 位双精度
  half_float - 16 位半精度
  scaled_float - 缩放浮点数

日期类型：
  date      - 日期，支持多种格式
  date_nanos - 纳秒精度日期

布尔类型：
  boolean   - true/false

二进制类型：
  binary    - Base64 编码的二进制数据

范围类型：
  integer_range, long_range, float_range, date_range

特殊类型：
  geo_point   - 地理坐标
  geo_shape   - 地理形状
  ip          - IPv4/IPv6
  completion  - 自动补全
  token_count - 词项计数
```

#### 4.2 映射参数详解

```bash
# 动态映射 vs 显式映射
# ES 会自动推断字段类型（动态映射），但生产环境建议显式定义

# 显式映射示例
curl -X PUT "localhost:9200/app-logs" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "timestamp": {
        "type": "date",
        "format": "yyyy-MM-dd HH:mm:ss.SSS||epoch_millis"
      },
      "level": {
        "type": "keyword",
        "ignore_above": 10
      },
      "message": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "service": {
        "type": "keyword"
      },
      "request": {
        "properties": {
          "method": { "type": "keyword" },
          "path": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
          "duration_ms": { "type": "float" },
          "status_code": { "type": "short" }
        }
      },
      "tags": {
        "type": "keyword"
      },
      "host": {
        "type": "object",
        "properties": {
          "name": { "type": "keyword" },
          "ip": { "type": "ip" },
          "os": {
            "properties": {
              "name": { "type": "keyword" },
              "version": { "type": "keyword" }
            }
          }
        }
      }
    }
  }
}'
```

#### 4.3 动态映射控制

```
dynamic 参数的三个值：

true（默认）：
  - 自动添加新字段的映射
  - 适合开发环境
  - 可能导致 mapping explosion

strict：
  - 遇到未知字段直接报错
  - 适合生产环境
  - 保证数据结构一致

false：
  - 忽略未知字段，不报错也不索引
  - 数据会存储在 _source 中
  - 不会被搜索到

Runtime Fields（运行时字段）：
  - 在查询时动态计算
  - 不占用索引空间
  - 适合临时分析
```

```bash
# 使用 Runtime Field 进行临时分析
curl -X GET "localhost:9200/app-logs/_search" -H 'Content-Type: application/json' -d'
{
  "runtime_mappings": {
    "response_category": {
      "type": "keyword",
      "script": {
        "source": """
          int code = doc["status_code"].value;
          if (code < 300) emit("success");
          else if (code < 400) emit("redirect");
          else if (code < 500) emit("client_error");
          else emit("server_error");
        """
      }
    }
  },
  "aggs": {
    "by_category": {
      "terms": { "field": "response_category" }
    }
  }
}'
```

### 5. 分词器（Analyzer）

#### 5.1 分词器组成

```
分词器的三个组件：

┌──────────────────────────────────────────────────────────┐
│                    Analyzer 分词器                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Character Filter（字符过滤器）                            │
│  ├── 在分词前对原始文本进行处理                             │
│  ├── html_strip: 去除 HTML 标签                           │
│  ├── mapping: 字符替换                                    │
│  └── pattern_replace: 正则替换                            │
│                                                          │
│  Tokenizer（分词器）                                      │
│  ├── 将文本拆分为词项（Token）                              │
│  ├── standard: 按 Unicode 文本分割                        │
│  ├── whitespace: 按空格分割                               │
│  ├── keyword: 不分割，整个输入作为一个词项                   │
│  ├── pattern: 按正则分割                                  │
│  └── ngram / edge_ngram: N-gram 分词                      │
│                                                          │
│  Token Filter（词项过滤器）                                │
│  ├── 对分词结果进行后处理                                   │
│  ├── lowercase: 转小写                                    │
│  ├── uppercase: 转大写                                    │
│  ├── stop: 去除停用词                                     │
│  ├── synonym: 同义词替换                                  │
│  ├── stemmer: 词干提取                                    │
│  └── ngram / edge_ngram: N-gram 过滤                      │
│                                                          │
└──────────────────────────────────────────────────────────┘

处理流程：
  "The Quick Brown Fox" 
    → Character Filter → "The Quick Brown Fox"
    → Tokenizer → ["The", "Quick", "Brown", "Fox"]
    → Token Filter (lowercase + stop) → ["quick", "brown", "fox"]
```

#### 5.2 内置分词器

```bash
# 测试 standard 分词器
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "standard",
  "text": "The Quick Brown Fox jumps over the lazy dog"
}'

# 测试 simple 分词器（按非字母字符分割，转小写）
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "simple",
  "text": "The Quick Brown Fox jumps over the lazy dog"
}'

# 测试 whitespace 分词器（按空格分割，不转小写）
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "whitespace",
  "text": "The Quick Brown Fox jumps over the lazy dog"
}'

# 测试 keyword 分词器（不分割）
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "keyword",
  "text": "The Quick Brown Fox jumps over the lazy dog"
}'
```

#### 5.3 中文分词器

```bash
# 安装 IK 分词器（中文分词标准方案）
# 下载与 ES 版本匹配的 IK 插件
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.11.0/elasticsearch-analysis-ik-8.11.0.zip

# 测试 IK 智能分词
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ik_smart",
  "text": "中华人民共和国国歌"
}'
# 结果：["中华人民共和国", "国歌"]

# 测试 IK 最细粒度分词
curl -X POST "localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ik_max_word",
  "text": "中华人民共和国国歌"
}'
# 结果：["中华人民共和国", "中华人民", "中华", "华人", "人民共和国", "人民", "共和国", "共和", "国歌"]

# 使用 IK 分词器创建索引
curl -X PUT "localhost:9200/chinese-logs" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "analysis": {
      "analyzer": {
        "ik_analyzer": {
          "type": "custom",
          "tokenizer": "ik_max_word",
          "filter": ["lowercase"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "analyzer": "ik_analyzer",
        "search_analyzer": "ik_smart"
      }
    }
  }
}'
```

#### 5.4 自定义分词器

```bash
# 创建自定义分词器
curl -X PUT "localhost:9200/custom-analyzer-index" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "analysis": {
      "filter": {
        "my_stop": {
          "type": "stop",
          "stopwords": ["the", "is", "at", "on", "a", "an"]
        },
        "my_synonym": {
          "type": "synonym",
          "synonyms": [
            "error,failure,exception",
            "warn,warning",
            "info,information"
          ]
        }
      },
      "analyzer": {
        "log_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "char_filter": ["html_strip"],
          "filter": [
            "lowercase",
            "my_stop",
            "my_synonym"
          ]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "message": {
        "type": "text",
        "analyzer": "log_analyzer"
      }
    }
  }
}'
```

### 6. 安装与配置

#### 6.1 Docker Compose 部署 ELK

```yaml
# docker-compose.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - node.name=es-node-1
      - cluster.name=elk-cluster
      - discovery.type=single-node
      - bootstrap.memory_lock=true
      - xpack.security.enabled=false
      - xpack.security.http.ssl.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - es-data:/usr/share/elasticsearch/data
      - es-logs:/usr/share/elasticsearch/logs
    ports:
      - "9200:9200"
      - "9300:9300"
    networks:
      - elk-network
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'"]
      interval: 30s
      timeout: 10s
      retries: 5

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    environment:
      - "LS_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml
    ports:
      - "5044:5044"
      - "9600:9600"
    networks:
      - elk-network
    depends_on:
      elasticsearch:
        condition: service_healthy

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - xpack.security.enabled=false
    ports:
      - "5601:5601"
    networks:
      - elk-network
    depends_on:
      elasticsearch:
        condition: service_healthy

volumes:
  es-data:
  es-logs:

networks:
  elk-network:
    driver: bridge
```

#### 6.2 Elasticsearch 关键配置

```yaml
# elasticsearch.yml 关键配置
cluster.name: elk-cluster                    # 集群名称
node.name: es-node-1                         # 节点名称
node.roles: [master, data, ingest]           # 节点角色

path.data: /var/lib/elasticsearch            # 数据目录
path.logs: /var/log/elasticsearch            # 日志目录

network.host: 0.0.0.0                        # 监听地址
http.port: 9200                              # HTTP 端口
transport.port: 9300                         # 集群通信端口

discovery.seed_hosts: ["es-node-1", "es-node-2", "es-node-3"]  # 集群发现
cluster.initial_master_nodes: ["es-node-1", "es-node-2", "es-node-3"]

# 内存锁定（避免 swap）
bootstrap.memory_lock: true

# 安全配置
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true

# 跨域配置（Kibana 需要）
http.cors.enabled: true
http.cors.allow-origin: "*"
```

```bash
# jvm.options 关键配置
# 堆内存设置（建议为物理内存的 50%，不超过 32GB）
-Xms16g
-Xmx16g

# GC 配置（ES 8.x 默认使用 G1GC）
-XX:+UseG1GC
-XX:G1HeapRegionSize=4m
-XX:InitiatingHeapOccupancyPercent=30
```

### 7. 集群管理

#### 7.1 集群健康状态

```bash
# 查看集群健康状态
curl -s "localhost:9200/_cluster/health?pretty"
# 返回：
# {
#   "cluster_name": "elk-cluster",
#   "status": "green",          # green/yellow/red
#   "number_of_nodes": 3,
#   "number_of_data_nodes": 2,
#   "active_primary_shards": 10,
#   "active_shards": 20,
#   "relocating_shards": 0,
#   "initializing_shards": 0,
#   "unassigned_shards": 0
# }

# 状态含义：
# green  - 所有主分片和副本都正常
# yellow - 所有主分片正常，部分副本未分配（单节点常见）
# red    - 部分主分片未分配（数据可能丢失）

# 查看索引级别健康状态
curl -s "localhost:9200/_cluster/health?level=indices&pretty"

# 查看分片级别健康状态
curl -s "localhost:9200/_cluster/health?level=shards&pretty"
```

#### 7.2 节点管理

```bash
# 查看节点信息
curl -s "localhost:9200/_cat/nodes?v&h=name,heap.percent,ram.percent,cpu,load_1m,disk.used_percent,node.role"
# name       heap.percent ram.percent cpu load_1m disk.used_percent node.role
# es-node-1           45          72   5    0.5              35.2  dim
# es-node-2           38          68   3    0.3              28.7  dim
# es-node-3           52          75   8    0.8              42.1  dim

# 查看分片分配
curl -s "localhost:9200/_cat/shards?v&h=index,shard,prirep,state,docs,store,node"
# index          shard prirep state      docs store    node
# app-logs-00001 0     p     STARTED    5000 2.1mb    es-node-1
# app-logs-00001 0     r     STARTED    5000 2.1mb    es-node-2
# app-logs-00001 1     p     STARTED    4800 1.9mb    es-node-2
# app-logs-00001 1     r     STARTED    4800 1.9mb    es-node-3

# 查看未分配分片的原因
curl -s "localhost:9200/_cluster/allocation/explain?pretty"
```

#### 7.3 多节点集群部署

```yaml
# docker-compose-multi.yml - 3 节点集群
version: '3.8'

services:
  es-node-1:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: es-node-1
    environment:
      - node.name=es-node-1
      - cluster.name=elk-cluster
      - discovery.seed_hosts=es-node-1,es-node-2,es-node-3
      - cluster.initial_master_nodes=es-node-1,es-node-2,es-node-3
      - node.roles=master,data,ingest
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=false
    ulimits:
      memlock: { soft: -1, hard: -1 }
    volumes:
      - es-data-1:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - es-net

  es-node-2:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: es-node-2
    environment:
      - node.name=es-node-2
      - cluster.name=elk-cluster
      - discovery.seed_hosts=es-node-1,es-node-2,es-node-3
      - cluster.initial_master_nodes=es-node-1,es-node-2,es-node-3
      - node.roles=master,data,ingest
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=false
    ulimits:
      memlock: { soft: -1, hard: -1 }
    volumes:
      - es-data-2:/usr/share/elasticsearch/data
    ports:
      - "9201:9200"
    networks:
      - es-net

  es-node-3:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: es-node-3
    environment:
      - node.name=es-node-3
      - cluster.name=elk-cluster
      - discovery.seed_hosts=es-node-1,es-node-2,es-node-3
      - cluster.initial_master_nodes=es-node-1,es-node-2,es-node-3
      - node.roles=master,data,ingest
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=false
    ulimits:
      memlock: { soft: -1, hard: -1 }
    volumes:
      - es-data-3:/usr/share/elasticsearch/data
    ports:
      - "9202:9200"
    networks:
      - es-net

volumes:
  es-data-1:
  es-data-2:
  es-data-3:

networks:
  es-net:
    driver: bridge
```

### 8. 性能调优

#### 8.1 内存调优

```
JVM 堆内存调优原则：

┌─────────────────────────────────────────────────────────┐
│                  内存分配策略                              │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  物理内存 ─┬── JVM Heap（50%，≤32GB）                     │
│            │   ├── Segment 缓存                           │
│            │   ├── 聚合结果缓存                            │
│            │   └── 索引缓冲区                              │
│            │                                              │
│            ├── Lucene Off-Heap（剩余内存的大部分）          │
│            │   ├── 文件系统缓存（OS Page Cache）            │
│            │   └── Lucene 段缓存                           │
│            │                                              │
│            └── 系统预留（2GB+）                             │
│                                                           │
│  关键点：                                                  │
│  1. 堆内存不要超过 32GB（压缩指针失效）                     │
│  2. 建议堆内存 = 物理内存 × 50%，上限 32GB                 │
│  3. 留足够内存给 Lucene 的文件系统缓存                      │
│  4. 锁定内存避免 swap（bootstrap.memory_lock=true）        │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

#### 8.2 索引调优

```bash
# 批量写入优化（Bulk API）
curl -X POST "localhost:9200/_bulk" -H 'Content-Type: application/json' -d'
{"index": {"_index": "app-logs"}}
{"timestamp": "2026-05-05T10:00:00", "level": "info", "message": "Request processed"}
{"index": {"_index": "app-logs"}}
{"timestamp": "2026-05-05T10:00:01", "level": "error", "message": "Connection timeout"}
'

# Bulk 最佳实践：
# 1. 每批 5-15MB（不要超过 100MB）
# 2. 使用 ndjson 格式
# 3. 并发写入使用多个 worker
# 4. 写入时关闭副本，完成后打开

# 写入优化：临时关闭副本
curl -X PUT "localhost:9200/app-logs/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "number_of_replicas": 0,
    "refresh_interval": "-1",
    "translog.durability": "async",
    "translog.sync_interval": "30s"
  }
}'

# 写入完成后恢复
curl -X PUT "localhost:9200/app-logs/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "number_of_replicas": 1,
    "refresh_interval": "1s",
    "translog.durability": "request"
  }
}'
```

#### 8.3 查询调优

```bash
# 使用 filter 代替 query（filter 可缓存）
# 不推荐
curl -X GET "localhost:9200/app-logs/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        { "match": { "message": "error" } },
        { "range": { "timestamp": { "gte": "now-1h" } } }
      ]
    }
  }
}'

# 推荐（filter 走缓存，不计算评分）
curl -X GET "localhost:9200/app-logs/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        { "match": { "message": "error" } }
      ],
      "filter": [
        { "range": { "timestamp": { "gte": "now-1h" } } },
        { "term": { "level": "error" } }
      ]
    }
  }
}'

# 避免深分页（使用 search_after）
curl -X GET "localhost:9200/app-logs/_search" -H 'Content-Type: application/json' -d'
{
  "size": 100,
  "sort": [
    { "timestamp": "desc" },
    { "_id": "asc" }
  ],
  "search_after": ["2026-05-05T10:00:00", "abc123"]
}'
```

#### 8.4 操作系统调优

```bash
# /etc/sysctl.conf
vm.max_map_count=262144          # ES 要求最低值
vm.swappiness=1                   # 尽量避免 swap
net.core.somaxconn=65535          # 最大连接队列
net.ipv4.tcp_max_syn_backlog=65535

# /etc/security/limits.conf
elasticsearch soft nofile 65536
elasticsearch hard nofile 65536
elasticsearch soft nproc 4096
elasticsearch hard nproc 4096
elasticsearch soft memlock unlimited
elasticsearch hard memlock unlimited

# 禁用 swap
sudo swapoff -a

# 文件系统选择
# 推荐 XFS 或 ext4
# 禁用磁盘访问时间更新
# mount -o noatime /dev/sdb /var/lib/elasticsearch
```

### 9. SRE 实战案例

#### 9.1 集群 Red 状态故障排查

```
故障现象：
  集群状态变为 Red，部分索引不可用

排查步骤：

1. 查看集群健康状态
   curl -s "localhost:9200/_cluster/health?pretty"
   → status: red, unassigned_shards: 5

2. 查看未分配分片
   curl -s "localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"
   → app-logs-00003  0  p  UNASSIGNED  NODE_LEFT

3. 查看分片分配失败原因
   curl -s "localhost:9200/_cluster/allocation/explain?pretty"
   → 原因：节点 es-node-3 离线，且无其他可用节点

4. 检查节点状态
   curl -s "localhost:9200/_cat/nodes?v"
   → 只有 es-node-1 和 es-node-2 在线

5. 修复步骤：
   a) 尝试恢复 es-node-3
      - 检查磁盘空间、内存、网络
      - 重启节点：systemctl restart elasticsearch
      - 查看节点日志：tail -f /var/log/elasticsearch/elk-cluster.log

   b) 如果节点无法恢复，强制分配分片
      curl -X POST "localhost:9200/_cluster/reroute" -H 'Content-Type: application/json' -d'
      {
        "commands": [{
          "allocate_stale_primary": {
            "index": "app-logs-00003",
            "shard": 0,
            "node": "es-node-1",
            "accept_data_loss": true
          }
        }]
      }'

   c) 长期方案：增加节点数，确保副本数 < 节点数
```

#### 9.2 磁盘空间不足处理

```
故障现象：
  ES 节点磁盘使用率超过 85%，集群变为只读

排查步骤：

1. 查看磁盘使用率
   curl -s "localhost:9200/_cat/allocation?v"
   → shards disk.indices disk.used disk.avail disk.total disk.percent
   →    50       120gb     180gb      20gb      200gb         90

2. ES 内置磁盘水位线：
   - low（85%）：不再分配新分片到该节点
   - high（90%）：尝试将分片从该节点移走
   - flood_stage（95%）：索引变为只读

3. 紧急处理：
   a) 删除旧索引释放空间
      curl -X DELETE "localhost:9200/app-logs-2026.04.*"

   b) 调整水位线（临时）
      curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
      {
        "persistent": {
          "cluster.routing.allocation.disk.watermark.low": "90%",
          "cluster.routing.allocation.disk.watermark.high": "95%",
          "cluster.routing.allocation.disk.watermark.flood_stage": "97%"
        }
      }'

   c) 解除只读
      curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' -d'
      {
        "index.blocks.read_only_allow_delete": null
      }'

4. 长期方案：
   - 实施 ILM 策略自动清理旧索引
   - 增加磁盘容量或添加节点
   - 优化索引策略减少存储占用
```

---

## 💻 实战练习

### 练习 1：部署单节点 ELK 环境

**目标**：使用 Docker Compose 部署完整的 ELK 环境并验证功能

```bash
# 步骤 1：创建目录结构
mkdir -p elk-lab/{elasticsearch,logstash/{config,pipeline},kibana}

# 步骤 2：创建 Elasticsearch 配置
cat > elk-lab/elasticsearch/elasticsearch.yml << 'EOF'
cluster.name: lab-cluster
node.name: es-lab
discovery.type: single-node
xpack.security.enabled: false
xpack.security.http.ssl.enabled: false
EOF

# 步骤 3：创建 Logstash Pipeline
cat > elk-lab/logstash/pipeline/logstash.conf << 'EOF'
input {
  beats {
    port => 5044
  }
  tcp {
    port => 5000
    codec => json_lines
  }
}

filter {
  if [message] =~ /^\{/ {
    json {
      source => "message"
    }
  }
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
  date {
    match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
    target => "@timestamp"
  }
  mutate {
    add_field => { "environment" => "lab" }
    remove_field => ["host", "agent", "ecs", "log"]
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "lab-logs-%{+YYYY.MM.dd}"
  }
  stdout {
    codec => rubydebug
  }
}
EOF

# 步骤 4：创建 Logstash 配置
cat > elk-lab/logstash/config/logstash.yml << 'EOF'
http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: ["http://elasticsearch:9200"]
EOF

# 步骤 5：创建 docker-compose.yml（使用前面的模板）

# 步骤 6：启动环境
cd elk-lab && docker-compose up -d

# 步骤 7：验证
curl -s "localhost:9200/_cluster/health?pretty"
curl -s "localhost:9200/_cat/nodes?v"

# 步骤 8：写入测试数据
curl -X POST "localhost:9200/lab-logs/_doc" -H 'Content-Type: application/json' -d'
{
  "timestamp": "2026-05-05T10:30:00",
  "level": "error",
  "message": "Database connection timeout after 30s",
  "service": "user-service",
  "host": "web-01",
  "response_time": 30000
}'

# 步骤 9：查询验证
curl -s "localhost:9200/lab-logs/_search?q=level:error&pretty"
```

### 练习 2：设计日志索引策略

**目标**：为微服务架构设计完整的索引模板和 ILM 策略

```bash
# 场景：电商系统有 10 个微服务，每天产生 50GB 日志
# 要求：
#   1. 按服务和日期分离索引
#   2. 热数据保留 3 天，温数据 7 天，30 天后删除
#   3. 查询时可以跨服务搜索

# 步骤 1：创建 ILM 策略
curl -X PUT "localhost:9200/_ilm/policy/ecommerce-logs" -H 'Content-Type: application/json' -d'
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": { "max_primary_shard_size": "30gb", "max_age": "1d" },
          "set_priority": { "priority": 100 }
        }
      },
      "warm": {
        "min_age": "3d",
        "actions": {
          "forcemerge": { "max_num_segments": 1 },
          "shrink": { "number_of_shards": 1 },
          "set_priority": { "priority": 50 }
        }
      },
      "delete": { "min_age": "30d", "actions": { "delete": {} } }
    }
  }
}'

# 步骤 2：创建索引模板
curl -X PUT "localhost:9200/_index_template/ecommerce-logs-tpl" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["ecommerce-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "index.lifecycle.name": "ecommerce-logs",
      "index.lifecycle.rollover_alias": "ecommerce-logs-write"
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "service": { "type": "keyword" },
        "level": { "type": "keyword" },
        "trace_id": { "type": "keyword" },
        "span_id": { "type": "keyword" },
        "message": { "type": "text", "fields": { "keyword": { "type": "keyword", "ignore_above": 512 } } },
        "request": {
          "properties": {
            "method": { "type": "keyword" },
            "path": { "type": "keyword" },
            "status": { "type": "short" },
            "duration_ms": { "type": "float" }
          }
        },
        "user_id": { "type": "keyword" },
        "order_id": { "type": "keyword" }
      }
    }
  }
}'

# 步骤 3：创建初始索引和别名
curl -X PUT "localhost:9200/ecommerce-logs-000001" -H 'Content-Type: application/json' -d'
{
  "aliases": {
    "ecommerce-logs-write": { "is_write_index": true },
    "ecommerce-logs-read": {}
  }
}'

# 步骤 4：验证 ILM 策略
curl -s "localhost:9200/ecommerce-logs-000001/_ilm/explain?pretty"
```

### 练习 3：性能调优与故障排查

**目标**：模拟生产问题并进行排查

```bash
# 场景：ES 查询延迟突然从 50ms 升到 2s，需要排查

# 步骤 1：检查集群健康
curl -s "localhost:9200/_cluster/health?pretty"
curl -s "localhost:9200/_cat/nodes?v&h=name,heap.percent,ram.percent,cpu,load_1m"

# 步骤 2：查看热点线程
curl -s "localhost:9200/_nodes/hot_threads"

# 步骤 3：查看慢查询日志
curl -X PUT "localhost:9200/app-logs/_settings" -H 'Content-Type: application/json' -d'
{
  "index.search.slowlog.threshold.query.warn": "1s",
  "index.search.slowlog.threshold.query.info": "500ms",
  "index.search.slowlog.threshold.fetch.warn": "500ms",
  "index.search.slowlog.level": "info"
}'

# 步骤 4：查看任务列表
curl -s "localhost:9200/_tasks?detailed=true&group_by=parents"

# 步骤 5：使用 Profile API 分析查询
curl -X GET "localhost:9200/app-logs/_search" -H 'Content-Type: application/json' -d'
{
  "profile": true,
  "query": {
    "bool": {
      "must": [{ "match": { "message": "error" } }],
      "filter": [{ "range": { "@timestamp": { "gte": "now-1h" } } }]
    }
  }
}'

# 步骤 6：检查段合并状态
curl -s "localhost:9200/_cat/segments?v&h=index,shard,segment,size,size.memory"
```

---

## 🎯 面试题精选

### 1. Elasticsearch 的倒排索引是什么？它和 B+ Tree 有什么区别？

**答**：倒排索引（Inverted Index）是一种将文档内容映射到文档 ID 的数据结构。它由两部分组成：

- **词项字典（Term Dictionary）**：存储所有不重复的词项，按字母顺序排列
- **倒排列表（Posting List）**：每个词项对应的文档 ID 列表，以及词频、位置等信息

与 B+ Tree 的区别：
- B+ Tree 适合精确查找和范围查询，倒排索引适合全文搜索
- 倒排索引通过词项直接定位文档，B+ Tree 需要逐层遍历
- 倒排索引支持模糊匹配、分词搜索，B+ Tree 不支持
- ES 中 keyword 类型字段使用 FST（Finite State Transducer）而非传统倒排索引

### 2. ES 的 refresh 和 flush 有什么区别？

**答**：
- **Refresh**：将内存缓冲区（In-memory Buffer）的数据生成新的 Segment，使其可被搜索。默认每秒执行一次。Refresh 后数据在内存中可搜索，但未持久化到磁盘。
- **Flush**：将内存中的 Segment 持久化到磁盘，清空 Translog。默认 30 分钟或 Translog 满 512MB 时执行。Flush 后数据才真正持久化。

关键区别：Refresh 是近实时搜索的关键（NRT），Flush 是数据持久化的保证。

### 3. 如何优化 ES 的写入性能？

**答**：
1. **使用 Bulk API**：批量写入，每批 5-15MB
2. **临时关闭副本**：写入时 `number_of_replicas: 0`
3. **关闭 Refresh**：`refresh_interval: -1`
4. **使用异步 Translog**：`translog.durability: async`
5. **增大索引缓冲区**：`indices.memory.index_buffer_size`
6. **使用合适的分片数**：避免过多分片（每个分片是一个 Lucene 索引）
7. **使用 SSD 磁盘**
8. **调整 Merge 策略**：减少段合并频率

### 4. ES 集群状态 Red、Yellow、Green 分别代表什么？

**答**：
- **Green**：所有主分片和副本分片都正常分配
- **Yellow**：所有主分片正常分配，但部分副本分片未分配（单节点集群常见）
- **Red**：部分主分片未分配，意味着有数据丢失风险

### 5. 什么是分片（Shard）？如何确定分片数量？

**答**：分片是索引的水平分区，每个分片是一个独立的 Lucene 索引。

分片数量确定原则：
- 单个分片大小建议 10-50GB
- 分片数 = 预估数据量 / 单分片大小
- 主分片数量创建后不可更改
- 分片数不宜过多（每个分片占用约 1MB 堆内存 + 文件句柄）
- 日志场景：按日期滚动索引，每个索引 3-5 个分片

### 6. 解释 ES 的写入流程，为什么是近实时（Near Real-Time）？

**答**：写入流程：文档 → 协调节点 → 主分片（写入 Translog + Buffer）→ Refresh（生成 Segment）→ 副本同步。

近实时的原因：文档写入后先进入内存缓冲区，需要等待 Refresh（默认 1 秒）后才会生成新的 Segment 并可被搜索。这个 1 秒的延迟就是"近实时"的含义。

### 7. 什么是 ILM？它的作用是什么？

**答**：ILM（Index Lifecycle Management）是 ES 的索引生命周期管理功能。它根据预定义的策略自动管理索引的生命周期，包括：

- **Hot 阶段**：高写入，使用 SSD
- **Warm 阶段**：只读，可降低副本数，合并段
- **Cold 阶段**：归档，可冻结索引
- **Delete 阶段**：自动删除过期索引

ILM 解决了日志数据量增长导致的存储成本和查询性能问题。

### 8. ES 中 text 和 keyword 类型有什么区别？

**答**：
- **text**：全文检索类型，内容会被分词器处理，适合长文本搜索，不支持排序和聚合（除非使用 fielddata，不推荐）
- **keyword**：精确值类型，不分词，适合枚举值、ID、标签等，支持排序、聚合、过滤

最佳实践：使用 multi-field 同时设置两种类型，如 `"message": {"type": "text", "fields": {"keyword": {"type": "keyword"}}}`

### 9. 如何处理 ES 的 mapping explosion 问题？

**答**：mapping explosion 是指索引中的字段数量过多导致内存占用过大。

解决方案：
1. 设置 `dynamic: strict`，拒绝未知字段
2. 使用 `index.mapping.total_fields.limit` 限制字段数（默认 1000）
3. 使用 `index.mapping.depth.limit` 限制嵌套深度
4. 避免使用动态字段名（如将用户输入作为字段名）
5. 使用 nested 类型代替 object 类型存储数组对象
6. 定期审查和清理无用字段

### 10. ES 的 Filter 和 Query 有什么区别？

**答**：
- **Query**：计算相关性评分（_score），结果按评分排序，不缓存
- **Filter**：不计算评分，只有是/否两种结果，结果会被缓存

最佳实践：
- 精确匹配、范围查询、存在性检查使用 Filter
- 全文搜索、相关性排序使用 Query
- 在 bool 查询中，精确条件放 filter，文本搜索放 must

---

## 📚 深入阅读

- [Elasticsearch 官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Elasticsearch: The Definitive Guide](https://www.elastic.co/guide/en/elasticsearch/guide/current/index.html)
- [Elasticsearch 性能调优指南](https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-indexing-speed.html)
- [ILM 最佳实践](https://www.elastic.co/guide/en/elasticsearch/reference/current/ilm-best-practices.html)
- [中文分词器 IK Analysis](https://github.com/medcl/elasticsearch-analysis-ik)

---

## ✅ 自检清单

- [ ] 能画出 ELK Stack 的完整架构图
- [ ] 理解 ES 的节点类型及其职责
- [ ] 掌握分片、副本的分配机制
- [ ] 理解写入流程（Buffer → Refresh → Flush → Translog）
- [ ] 理解读取流程（Query Phase → Fetch Phase）
- [ ] 能创建索引、定义映射、配置分词器
- [ ] 能使用 ILM 策略管理索引生命周期
- [ ] 能部署单节点和多节点 ES 集群
- [ ] 掌握集群健康状态的含义和排查方法
- [ ] 掌握写入和查询的性能调优方法
- [ ] 能处理磁盘空间不足、节点故障等常见问题
- [ ] 理解 text 和 keyword 类型的区别
