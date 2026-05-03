# Day 133: 可观测性基础 — SLO/SLI/SLA

> 📅 日期：2026-05-03
> 📖 学习主题：可观测性三大支柱、SLO 定义、SLI 选择、SLA 协议、错误预算、告警策略、值班实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 11 (系统监控命令), Day 88 (Docker 监控与日志), Day 112 (CloudWatch 监控)

---

## 🎯 学习目标

- 理解可观测性三大支柱（Metrics、Logs、Traces）的概念、区别与协作关系
- 掌握 SLI（Service Level Indicator）的选择方法与最佳实践
- 能够定义合理的 SLO（Service Level Objective）目标
- 理解 SLA（Service Level Agreement）与 SLO 的区别及法律约束
- 掌握错误预算（Error Budget）的计算方法与决策模型
- 能够设计基于 SLO 的告警策略与值班（On-Call）实践

---

## 📖 核心知识点

### 1. 可观测性三大支柱

#### 1.1 什么是可观测性

可观测性（Observability）是指通过系统的外部输出来推断其内部状态的能力。与传统监控不同，可观测性不仅告诉你"什么出了问题"，还能帮助你回答"为什么出了问题"。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    可观测性 vs 监控                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  监控（Monitoring）：                                                │
│    - 已知的未知（Known Unknowns）                                    │
│    - 预定义的指标和阈值                                              │
│    - 回答："系统是否正常？"                                          │
│    - 工具：Nagios、Zabbix、传统告警                                  │
│                                                                     │
│  可观测性（Observability）：                                         │
│    - 未知的未知（Unknown Unknowns）                                  │
│    - 可以探索和提问的系统                                            │
│    - 回答："为什么系统不正常？"                                      │
│    - 工具：Prometheus、Grafana、Jaeger、Loki                         │
│                                                                     │
│  关系：可观测性 ⊃ 监控                                               │
│  监控是可观测性的一个子集                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 三大支柱详解

```
┌─────────────────────────────────────────────────────────────────────┐
│                    可观测性三大支柱                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│   │   Metrics    │  │    Logs      │  │   Traces     │            │
│   │    指标       │  │    日志       │  │   链路追踪    │            │
│   ├──────────────┤  ├──────────────┤  ├──────────────┤            │
│   │ 数值型时间序列│  │ 离散事件记录 │  │ 请求调用链路 │            │
│   │              │  │              │  │              │            │
│   │ 特点：       │  │ 特点：       │  │ 特点：       │            │
│   │ - 聚合分析   │  │ - 上下文丰富 │  │ - 跨服务追踪 │            │
│   │ - 低存储成本 │  │ - 高存储成本 │  │ - 性能分析   │            │
│   │ - 实时告警   │  │ - 故障排查   │  │ - 依赖分析   │            │
│   │ - 趋势预测   │  │ - 审计合规   │  │ - 瓶颈定位   │            │
│   │              │  │              │  │              │            │
│   │ 回答：       │  │ 回答：       │  │ 回答：       │            │
│   │ "发生了什么" │  │ "为什么发生" │  │ "在哪里发生" │            │
│   │              │  │              │  │              │            │
│   │ 工具：       │  │ 工具：       │  │ 工具：       │            │
│   │ Prometheus   │  │ Loki/ELK    │  │ Jaeger       │            │
│   │ InfluxDB     │  │ Fluentd     │  │ Zipkin       │            │
│   │ VictoriaM    │  │ Vector      │  │ Tempo        │            │
│   └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                     │
│              三者协同工作，形成完整的可观测性体系                      │
│                                                                     │
│   发现问题（Metrics） → 定位原因（Logs） → 追踪链路（Traces）       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Metrics（指标）

指标是随时间变化的数值型数据，是最轻量的可观测性信号。

| 特性 | 说明 |
|------|------|
| 数据类型 | 数值型时间序列 |
| 存储效率 | 高（压缩比好） |
| 查询速度 | 快（聚合操作优化） |
| 适用场景 | 趋势分析、告警、容量规划 |
| 典型指标 | CPU 使用率、请求 QPS、错误率、延迟 P99 |

```
指标数据模型（以 Prometheus 为例）：

  指标名称 + 标签 = 时间序列

  http_requests_total{method="GET", status="200", handler="/api/users"}
  │                    │                                            │
  │                    └── 标签（Labels）：多维度标识                │
  └── 指标名称（Metric Name）：描述测量对象

  时间序列示例：
  t0: http_requests_total = 1000
  t1: http_requests_total = 1050
  t2: http_requests_total = 1120
  t3: http_requests_total = 1200
```

#### Logs（日志）

日志是离散的事件记录，包含丰富的上下文信息。

| 特性 | 说明 |
|------|------|
| 数据类型 | 非结构化/半结构化文本 |
| 存储效率 | 低（数据量大） |
| 查询速度 | 慢（需要全文搜索） |
| 适用场景 | 故障排查、审计、调试 |
| 典型日志 | 访问日志、错误日志、应用日志 |

```
日志级别层次：

  FATAL ──── 系统崩溃，必须立即处理
    │
  ERROR ──── 错误事件，需要关注
    │
  WARN  ──── 警告，可能演变为错误
    │
  INFO  ──── 一般信息，运行状态
    │
  DEBUG ──── 调试信息，开发环境使用
    │
  TRACE ──── 最详细的追踪信息

  结构化日志示例（JSON）：
  {
    "timestamp": "2026-05-03T10:30:45.123Z",
    "level": "ERROR",
    "service": "user-service",
    "trace_id": "abc123def456",
    "span_id": "span789",
    "message": "Failed to connect to database",
    "error": "connection timeout after 30s",
    "user_id": "user_12345",
    "request_id": "req_abcdef"
  }
```

#### Traces（链路追踪）

链路追踪记录请求在分布式系统中的完整路径。

| 特性 | 说明 |
|------|------|
| 数据类型 | 有向无环图（DAG） |
| 存储效率 | 中 |
| 查询速度 | 中 |
| 适用场景 | 分布式系统调试、性能优化 |
| 典型工具 | Jaeger、Zipkin、Tempo、SkyWalking |

```
链路追踪示例（一个 HTTP 请求的完整链路）：

  Trace ID: abc123def456

  ┌─────────────────────────────────────────────────────────────────┐
  │  API Gateway (总耗时: 250ms)                                    │
  │  ├── [Span 1] auth-service        20ms                         │
  │  ├── [Span 2] user-service        80ms                         │
  │  │   ├── [Span 3] MySQL query     30ms                         │
  │  │   └── [Span 4] Redis cache     5ms                          │
  │  └── [Span 5] order-service       120ms                        │
  │      ├── [Span 6] PostgreSQL      50ms                         │
  │      ├── [Span 7] RabbitMQ        15ms                         │
  │      └── [Span 8] payment-service 40ms                         │
  │          └── [Span 9] 外部支付API  35ms                         │
  └─────────────────────────────────────────────────────────────────┘

  时间线：
  0ms    50ms   100ms  150ms  200ms  250ms
  ├──────┼──────┼──────┼──────┼──────┤
  │██████│██████│██████│██████│██████│ API Gateway
  │███   │      │      │      │      │ auth-service
  │      │████████████│      │      │ user-service
  │      │      │████████████████████│ order-service
  │      │      │      │      │██████│ payment-service
```

#### 1.3 三大支柱关联

```
三大支柱关联模型：

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  Metrics（指标）                                             │
  │    │                                                         │
  │    │  告警触发：error_rate > 5%                              │
  │    ▼                                                         │
  │  Logs（日志）                                                │
  │    │                                                         │
  │    │  关键字段：trace_id = abc123                            │
  │    ▼                                                         │
  │  Traces（链路追踪）                                          │
  │    │                                                         │
  │    │  定位：order-service → payment-service 超时             │
  │    ▼                                                         │
  │  根因分析：外部支付 API 响应缓慢                              │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  关联方式：
  1. Exemplar：指标数据点附带 trace_id
  2. Log-Trace Link：日志中包含 trace_id 和 span_id
  3. Metric-Log Link：通过标签（labels）关联
```

### 2. SLI — 服务级别指标

#### 2.1 SLI 定义

SLI（Service Level Indicator）是衡量服务某一方面质量的量化指标。它是用户可感知的服务质量的数值度量。

```
SLI = 好事件数 / 有效事件数 × 100%

示例：
  可用性 SLI = 成功请求数 / 总请求数 × 100%
  延迟 SLI   = 在阈值内完成的请求数 / 总请求数 × 100%
  正确性 SLI = 返回正确结果的请求数 / 总请求数 × 100%
```

#### 2.2 SLI 分类

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SLI 分类体系                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │   可用性 SLI    │  │   延迟 SLI      │  │   吞吐量 SLI    │    │
│  │  (Availability) │  │  (Latency)      │  │  (Throughput)   │    │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤    │
│  │ 成功请求比例    │  │ 请求完成时间    │  │ 处理速率        │    │
│  │                 │  │                 │  │                 │    │
│  │ http_requests   │  │ http_request    │  │ requests per    │    │
│  │ _total{code=   │  │ _duration       │  │ second (RPS)    │    │
│  │ "200"} /        │  │ _seconds{quant  │  │                 │    │
│  │ http_requests   │  │ ile="0.99"} <   │  │ messages per    │    │
│  │ _total          │  │ 0.3s            │  │ second          │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │   正确性 SLI    │  │   耐久性 SLI    │  │   质量 SLI      │    │
│  │  (Correctness)  │  │  (Durability)   │  │  (Quality)      │    │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤    │
│  │ 返回正确结果    │  │ 数据持久保存    │  │ 输出质量        │    │
│  │                 │  │                 │  │                 │    │
│  │ correct_results │  │ stored_objects  │  │ fresh_data_     │    │
│  │ / total_        │  │ / attempted_    │  │ requests /      │    │
│  │ results         │  │ stores          │  │ total_requests  │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.3 常见 SLI 指标

| 服务类型 | SLI 指标 | 计算方式 | 示例 |
|----------|----------|----------|------|
| HTTP 服务 | 可用性 | 成功请求数 / 总请求数 | 99.9% |
| HTTP 服务 | 延迟 | P99 < 300ms 的请求比例 | 99% |
| 数据库 | 可用性 | 可用时间 / 总时间 | 99.99% |
| 数据库 | 延迟 | 查询 P95 延迟 | < 50ms |
| 消息队列 | 吞吐量 | 每秒处理消息数 | 10000 msg/s |
| 消息队列 | 耐久性 | 成功持久化的消息比例 | 99.999% |
| 存储 | 耐久性 | 数据不丢失的概率 | 99.999999999% |
| 存储 | 可用性 | 读写成功比例 | 99.99% |
| CDN | 延迟 | 首字节时间 (TTFB) | < 100ms |
| CDN | 可用性 | 成功响应比例 | 99.95% |

#### 2.4 SLI 选择最佳实践

```
SLI 选择检查清单：

  ✅ 用户可感知：SLI 应该反映用户体验，而非内部实现细节
     好：API 响应时间
     差：CPU 使用率（用户不关心）

  ✅ 可度量：SLI 必须可以被准确、持续地测量
     好：HTTP 5xx 错误率
     差："系统稳定性"（无法量化）

  ✅ 可操作：SLI 变化时，团队能采取行动
     好：数据库查询延迟
     差：第三方 API 可用性（不可控）

  ✅ 聚合粒度合适：选择合适的聚合方式
     好：P99 延迟（排除异常值影响）
     差：平均延迟（被异常值扭曲）

  ✅ 有限数量：每个服务 2-5 个 SLI
     避免指标过多导致关注点分散

  ✅ 双向有效性：SLI 恶化 = 用户体验恶化
     验证：SLI 变差时，用户投诉是否增加？
```

#### 2.5 SLI 实现示例

```yaml
# Prometheus 中的 SLI 实现

# 1. 可用性 SLI
# 公式：成功请求数 / 总请求数
# PromQL:
sum(rate(http_requests_total{code=~"2.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# 2. 延迟 SLI（P99 < 300ms）
# 公式：在阈值内完成的请求数 / 总请求数
# PromQL:
sum(rate(http_request_duration_seconds_bucket{le="0.3"}[5m]))
/
sum(rate(http_request_duration_seconds_count[5m]))

# 3. 吞吐量 SLI
# PromQL:
sum(rate(http_requests_total[5m]))

# 4. 错误率 SLI
# PromQL:
sum(rate(http_requests_total{code=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

### 3. SLO — 服务级别目标

#### 3.1 SLO 定义

SLO（Service Level Objective）是 SLI 的目标值，定义了服务应该达到的质量水平。它是团队内部的质量承诺。

```
SLO = SLI 的目标值

示例：
  SLO：可用性 >= 99.9%（每月最多 43.2 分钟不可用）
  SLO：P99 延迟 < 300ms（99% 的请求在 300ms 内完成）
  SLO：错误率 < 0.1%（每 1000 个请求最多 1 个错误）
```

#### 3.2 SLO 可用性等级

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SLO 可用性等级对照表                               │
├────────────┬──────────────┬────────────────────────────────────────┤
│ 可用性等级  │ 年度不可用时间│ 适用场景                               │
├────────────┼──────────────┼────────────────────────────────────────┤
│ 99%        │ 3.65 天      │ 内部工具、开发环境                      │
│ 99.9%      │ 8.76 小时    │ 一般业务服务                           │
│ 99.95%     │ 4.38 小时    │ 重要业务服务                           │
│ 99.99%     │ 52.56 分钟   │ 核心业务、支付系统                      │
│ 99.999%    │ 5.26 分钟    │ 金融交易、电信核心网                    │
│ 99.9999%   │ 31.5 秒      │ 生命安全系统、航空管制                  │
└────────────┴──────────────┴────────────────────────────────────────┘

换算公式：
  每月不可用时间 = 总时间 × (1 - 可用性百分比)

  99.9% 可用性：
    30天 × 24小时 × 60分钟 × 0.001 = 43.2 分钟/月

  99.99% 可用性：
    30天 × 24小时 × 60分钟 × 0.0001 = 4.32 分钟/月
```

#### 3.3 SLO 定义流程

```
SLO 定义流程：

  1. 识别关键用户旅程
     │
     ├── 用户注册流程
     ├── 商品搜索流程
     ├── 下单支付流程
     └── 订单查询流程
     │
     ▼
  2. 为每个旅程定义 SLI
     │
     ├── 注册：成功率、响应时间
     ├── 搜索：结果返回时间、结果相关性
     ├── 下单：成功率、支付延迟
     └── 查询：响应时间、数据一致性
     │
     ▼
  3. 设置 SLO 目标
     │
     ├── 参考历史数据（当前基线）
     ├── 参考用户期望（调研反馈）
     ├── 参考业务需求（竞品对比）
     └── 参考技术约束（架构能力）
     │
     ▼
  4. 确定测量窗口
     │
     ├── 滚动窗口（Rolling Window）：过去 30 天
     ├── 日历窗口（Calendar Window）：自然月
     └── 选择建议：滚动窗口更平滑，日历窗口更直观
     │
     ▼
  5. 持续审查和调整
     │
     ├── 每季度审查 SLO 是否合理
     ├── 根据业务变化调整目标
     └── 根据用户反馈优化指标
```

#### 3.4 SLO 定义示例

```yaml
# SLO 定义文档示例

service: user-api
owner: platform-team
description: 用户 API 服务

slos:
  - name: availability
    description: API 可用性
    sli:
      type: ratio
      good_events: http_requests_total{code=~"2.."}
      total_events: http_requests_total
    target: 0.999  # 99.9%
    window: 30d    # 滚动 30 天

  - name: latency
    description: API 延迟
    sli:
      type: threshold
      metric: http_request_duration_seconds
      threshold: 0.3  # 300ms
      comparison: less_than
    target: 0.99   # 99% 的请求 < 300ms
    window: 30d

  - name: error-rate
    description: 错误率
    sli:
      type: ratio
      good_events: http_requests_total{code=~"2..|3.."}
      total_events: http_requests_total
    target: 0.9995  # 错误率 < 0.05%
    window: 30d
```

### 4. SLA — 服务级别协议

#### 4.1 SLA 定义

SLA（Service Level Agreement）是服务提供商与客户之间的正式协议，通常具有法律约束力。

```
SLA vs SLO vs SLI 层级关系：

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │   SLA（协议）                                                │
  │   ├── 法律约束力：是                                         │
  │   ├── 定义方：服务提供商 ↔ 客户                              │
  │   ├── 内容：服务承诺 + 违约赔偿                              │
  │   │                                                          │
  │   │   ┌──────────────────────────────────────────────────┐  │
  │   │   │                                                  │  │
  │   │   │   SLO（目标）                                    │  │
  │   │   │   ├── 法律约束力：否（内部承诺）                  │  │
  │   │   │   ├── 定义方：SRE 团队                           │  │
  │   │   │   ├── 内容：SLI 的目标值                         │  │
  │   │   │   │                                              │  │
  │   │   │   │   ┌──────────────────────────────────────┐  │  │
  │   │   │   │   │                                      │  │  │
  │   │   │   │   │   SLI（指标）                        │  │  │
  │   │   │   │   │   ├── 类型：度量值                    │  │  │
  │   │   │   │   │   ├── 定义方：SRE 团队               │  │  │
  │   │   │   │   │   └── 内容：服务质量的量化度量        │  │  │
  │   │   │   │   │                                      │  │  │
  │   │   │   │   └──────────────────────────────────────┘  │  │
  │   │   │   │                                              │  │
  │   │   │   └──────────────────────────────────────────────┘  │
  │   │   │                                                      │
  │   │   └──────────────────────────────────────────────────────┘  │
  │   │                                                              │
  └──────────────────────────────────────────────────────────────────┘

  关系：
    SLI → 度量服务质量
    SLO → SLI 的目标值（内部承诺）
    SLA → SLO 的法律化（外部协议）

  通常：SLA 目标 < SLO 目标（留出缓冲）
    SLO: 99.9%  （内部目标）
    SLA: 99.5%  （对外承诺，留 0.4% 缓冲）
```

#### 4.2 SLA 组成要素

```
SLA 核心组成：

  1. 服务定义
     ├── 服务范围：明确包含和排除的服务
     ├── 服务时间：7×24、5×8、指定时段
     └── 服务等级：不同等级对应不同承诺

  2. 性能指标
     ├── 可用性：如 99.9%
     ├── 延迟：如 P99 < 500ms
     ├── 吞吐量：如支持 10000 QPS
     ├── 持久性：如 99.999999999%（11 个 9）
     └── 恢复时间：如 RTO < 1 小时

  3. 测量方法
     ├── 测量工具：Prometheus + Grafana
     ├── 测量周期：自然月 / 滚动 30 天
     ├── 测量点：从哪个端点测量
     └── 排除项：计划维护、不可抗力

  4. 违约条款
     ├── 赔偿方式：服务信用、退款
     ├── 赔偿比例：
     │   可用性 99.9% - 99.0% → 10% 服务信用
     │   可用性 99.0% - 95.0% → 25% 服务信用
     │   可用性 < 95.0%       → 50% 服务信用
     └── 赔偿上限：通常为月度费用的一定比例

  5. 排除条款
     ├── 计划维护窗口
     ├── 不可抗力（自然灾害、战争）
     ├── 客户自身原因
     └── 第三方服务故障
```

### 5. 错误预算（Error Budget）

#### 5.1 错误预算概念

错误预算是 SLO 的反面表达。如果 SLO 是 99.9% 可用性，那么错误预算就是 0.1% — 即允许的不可用比例。

```
错误预算计算：

  可用性 SLO = 99.9%
  错误预算 = 1 - 99.9% = 0.1%

  每月错误预算（30 天）：
    30 × 24 × 60 × 0.001 = 43.2 分钟

  每月错误预算（按请求数）：
    如果月请求量 = 100,000,000
    允许错误请求数 = 100,000,000 × 0.001 = 100,000

  ┌──────────────────────────────────────────────────────────────┐
  │                    错误预算可视化                              │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  月份：2026年5月                                             │
  │  SLO：99.9%                                                  │
  │  错误预算：43.2 分钟                                         │
  │                                                              │
  │  ████████████████████████████████████████████░░░░░░░░░░░░░  │
  │  ├── 已消耗 32 分钟 (74%) ──┤├── 剩余 11.2 分钟 (26%) ──┤  │
  │                                                              │
  │  状态：⚠️ 预算消耗过快，需要关注                              │
  │                                                              │
  │  ┌──────────────────────────────────────────────────────┐   │
  │  │ 预算消耗速率：                                       │   │
  │  │ 当前日期：5月15日（50% 时间已过）                     │   │
  │  │ 已消耗：74%                                          │   │
  │  │ 预期月末消耗：148%（将超标）                          │   │
  │  │                                                      │   │
  │  │ ⚠️ 如果继续当前速率，将在 5月20日耗尽预算              │   │
  │  └──────────────────────────────────────────────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 5.2 错误预算策略

```
错误预算决策模型：

  ┌──────────────────────────────────────────────────────────────┐
  │                    错误预算状态机                              │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  健康（预算 > 50%）                                          │
  │    │                                                         │
  │    │ 可以做：                                                │
  │    │   - 进行高风险变更（新功能上线、架构调整）              │
  │    │   - 进行混沌工程实验                                    │
  │    │   - 推动技术债务清理                                    │
  │    │   - 降低值班强度                                        │
  │    ▼                                                         │
  │  警告（预算 20%-50%）                                        │
  │    │                                                         │
  │    │ 应该做：                                                │
  │    │   - 放慢变更节奏                                        │
  │    │   - 增加代码审查力度                                    │
  │    │   - 优先修复可靠性问题                                  │
  │    │   - 开始复盘故障                                        │
  │    ▼                                                         │
  │  危险（预算 < 20%）                                          │
  │    │                                                         │
  │    │ 必须做：                                                │
  │    │   - 冻结非紧急变更                                      │
  │    │   - 全员聚焦可靠性                                      │
  │    │   - 增加值班人员                                        │
  │    │   - 启动专项治理                                        │
  │    ▼                                                         │
  │  耗尽（预算 = 0%）                                           │
  │    │                                                         │
  │    │ 紧急行动：                                              │
  │    │   - 停止所有变更                                        │
  │    │   - 只允许 P0 故障修复                                  │
  │    │   - 启动全链路排查                                      │
  │    │   - 向管理层汇报                                        │
  │    ▼                                                         │
  │  超支（预算 < 0%）                                           │
  │    │                                                         │
  │    │ 后果：                                                  │
  │    │   - 违反 SLO 承诺                                       │
  │    │   - 可能触发 SLA 赔偿                                   │
  │    │   - 需要根本原因分析（RCA）                              │
  │    │   - 制定长期改进计划                                    │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 5.3 错误预算计算示例

```python
# 错误预算计算脚本

from datetime import datetime, timedelta

def calculate_error_budget(slo_target, window_days, total_requests):
    """
    计算错误预算

    Args:
        slo_target: SLO 目标（如 0.999 表示 99.9%）
        window_days: 测量窗口天数
        total_requests: 总请求数
    """
    error_budget_pct = 1 - slo_target
    total_minutes = window_days * 24 * 60
    error_budget_minutes = total_minutes * error_budget_pct
    error_budget_requests = total_requests * error_budget_pct

    return {
        "error_budget_pct": f"{error_budget_pct * 100:.1f}%",
        "error_budget_minutes": f"{error_budget_minutes:.1f} 分钟",
        "error_budget_requests": int(error_budget_requests),
    }

# 示例
budget = calculate_error_budget(
    slo_target=0.999,      # 99.9% 可用性
    window_days=30,         # 30 天窗口
    total_requests=100_000_000  # 1 亿请求
)
print(budget)
# 输出：
# {
#   'error_budget_pct': '0.1%',
#   'error_budget_minutes': '43.2 分钟',
#   'error_budget_requests': 100000
# }
```

```yaml
# Prometheus 中的错误预算告警

groups:
  - name: error_budget_alerts
    rules:
      # 错误预算消耗速率告警
      - alert: ErrorBudgetBurnRateHigh
        expr: |
          (
            1 - (
              sum(rate(http_requests_total{code=~"2.."}[1h]))
              /
              sum(rate(http_requests_total[1h]))
            )
          ) / (1 - 0.999) > 14.4
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "错误预算消耗速率过高（14.4x）"
          description: "当前小时消耗速率是预期的 14.4 倍，按此速率将在 2 天内耗尽月度错误预算"

      # 错误预算剩余量告警
      - alert: ErrorBudgetLow
        expr: |
          (
            1 - (
              sum(increase(http_requests_total{code=~"2.."}[30d]))
              /
              sum(increase(http_requests_total[30d]))
            )
          ) < 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "错误预算剩余不足 20%"
          description: "当前 30 天窗口内错误预算已消耗超过 80%"
```

### 6. 基于 SLO 的告警策略

#### 6.1 告警分级

```
┌─────────────────────────────────────────────────────────────────────┐
│                    告警分级体系                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  P0 - 致命（Critical）                                              │
│  ├── 定义：服务完全不可用                                          │
│  ├── 响应时间：5 分钟                                              │
│  ├── 通知方式：电话 + 短信 + 即时通讯                              │
│  ├── 处理要求：立即响应，全员投入                                  │
│  └── 示例：支付服务完全不可用、数据库主库宕机                      │
│                                                                     │
│  P1 - 严重（High）                                                  │
│  ├── 定义：服务部分不可用或性能严重下降                            │
│  ├── 响应时间：15 分钟                                             │
│  ├── 通知方式：短信 + 即时通讯                                     │
│  ├── 处理要求：值班人员立即处理                                    │
│  └── 示例：API 延迟飙升、错误率超过 5%                             │
│                                                                     │
│  P2 - 一般（Medium）                                                │
│  ├── 定义：服务性能下降但仍在可用范围                              │
│  ├── 响应时间：1 小时                                              │
│  ├── 通知方式：即时通讯                                            │
│  ├── 处理要求：工作时间内处理                                      │
│  └── 示例：磁盘使用率超过 80%、非核心服务错误率上升                │
│                                                                     │
│  P3 - 低（Low）                                                     │
│  ├── 定义：潜在风险，需要关注                                      │
│  ├── 响应时间：24 小时                                             │
│  ├── 通知方式：邮件                                                │
│  ├── 处理要求：排期处理                                            │
│  └── 示例：证书即将过期、依赖版本过旧                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.2 多窗口多燃烧速率告警

Google SRE 团队提出的多窗口多燃烧速率（Multi-Window, Multi-Burn-Rate）告警策略是基于 SLO 告警的最佳实践。

```
多窗口多燃烧速率告警策略：

  ┌──────────────────────────────────────────────────────────────────┐
  │  告警级别    │ 燃烧速率 │ 短窗口 │ 长窗口 │ 触发条件            │
  ├──────────────┼──────────┼────────┼────────┼─────────────────────┤
  │  P0 Critical │ 14.4x    │ 1h     │ 5m     │ 2天内耗尽预算       │
  │  P0 Critical │ 6x       │ 6h     │ 30m    │ 5天内耗尽预算       │
  │  P1 High     │ 3x       │ 1d     │ 2h     │ 10天内耗尽预算      │
  │  P1 High     │ 1x       │ 3d     │ 6h     │ 30天内耗尽预算      │
  │  P2 Medium   │ 0.246x   │ 30d    │ 3h     │ SLO 刚好达标        │
  └──────────────┴──────────┴────────┴────────┴─────────────────────┘

  燃烧速率（Burn Rate）= 错误预算消耗速率 / 预期消耗速率

  示例：
    SLO = 99.9%，错误预算 = 0.1%
    燃烧速率 1x = 恰好在窗口结束时耗尽预算
    燃烧速率 14.4x = 在 2 天内耗尽 30 天的预算

  计算：
    14.4x 燃烧速率时：
    0.1% × 14.4 = 1.44% 错误率
    30天 / 14.4 = 2.08 天耗尽预算
```

#### 6.3 Prometheus 告警规则

```yaml
# 基于 SLO 的告警规则（Multi-Window Multi-Burn-Rate）

groups:
  - name: slo_alerts
    interval: 30s
    rules:
      # ============================================
      # P0 Critical: 14.4x 燃烧速率（2天内耗尽预算）
      # ============================================
      - record: slo:error_ratio:rate5m
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          )

      - record: slo:error_ratio:rate1h
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          )

      - alert: SLOBurnRateCritical
        expr: |
          slo:error_ratio:rate5m > (14.4 * 0.001)
          and
          slo:error_ratio:rate1h > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          priority: P0
        annotations:
          summary: "SLO 燃烧速率严重超标"
          description: "当前错误率 {{ $value | humanizePercentage }}，14.4x 燃烧速率，预计 2 天内耗尽月度错误预算"

      # ============================================
      # P0 Critical: 6x 燃烧速率（5天内耗尽预算）
      # ============================================
      - record: slo:error_ratio:rate30m
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[30m]))
            /
            sum(rate(http_requests_total[30m]))
          )

      - record: slo:error_ratio:rate6h
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          )

      - alert: SLOBurnRateHigh
        expr: |
          slo:error_ratio:rate30m > (6 * 0.001)
          and
          slo:error_ratio:rate6h > (6 * 0.001)
        for: 5m
        labels:
          severity: critical
          priority: P0
        annotations:
          summary: "SLO 燃烧速率高"
          description: "6x 燃烧速率，预计 5 天内耗尽月度错误预算"

      # ============================================
      # P1 High: 3x 燃烧速率（10天内耗尽预算）
      # ============================================
      - record: slo:error_ratio:rate2h
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[2h]))
            /
            sum(rate(http_requests_total[2h]))
          )

      - record: slo:error_ratio:rate1d
        expr: |
          1 - (
            sum(rate(http_requests_total{code=~"2.."}[1d]))
            /
            sum(rate(http_requests_total[1d]))
          )

      - alert: SLOBurnRateMedium
        expr: |
          slo:error_ratio:rate2h > (3 * 0.001)
          and
          slo:error_ratio:rate1d > (3 * 0.001)
        for: 10m
        labels:
          severity: warning
          priority: P1
        annotations:
          summary: "SLO 燃烧速率中等"
          description: "3x 燃烧速率，预计 10 天内耗尽月度错误预算"

      # ============================================
      # P2 Medium: 错误预算即将耗尽
      # ============================================
      - alert: ErrorBudgetExhausted
        expr: |
          (
            1 - (
              sum(increase(http_requests_total{code=~"2.."}[30d]))
              /
              sum(increase(http_requests_total[30d]))
            )
          ) < 0.1
        for: 5m
        labels:
          severity: warning
          priority: P2
        annotations:
          summary: "错误预算即将耗尽"
          description: "30 天窗口内错误预算剩余不足 10%，需要减少变更并聚焦可靠性"
```

### 7. 值班（On-Call）实践

#### 7.1 值班制度设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                    值班制度设计                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  轮转周期：                                                        │
│  ├── 一周轮转：每周一上午 10:00 交接                               │
│  ├── 两人值班：主值班 + 副值班                                      │
│  └── 交接内容：当前问题、已知风险、待办事项                        │
│                                                                     │
│  值班职责：                                                        │
│  ├── 响应告警：在 SLA 规定时间内响应                              │
│  ├── 故障处理：协调资源、定位问题、恢复服务                        │
│  ├── 变更审批：审批生产环境变更                                    │
│  ├── 文档更新：记录故障处理过程                                    │
│  └── 事后复盘：组织故障复盘会议                                    │
│                                                                     │
│  值班补偿：                                                        │
│  ├── 值班津贴：每天固定津贴                                        │
│  ├── 告警补贴：每次处理告警额外补贴                                │
│  ├── 调休：夜间值班次日可调休半天                                  │
│  └── 季度奖励：值班表现优秀者额外奖励                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 7.2 值班最佳实践

```
值班检查清单：

  □ 值班前准备
    ├── 确认告警通知渠道正常（手机、即时通讯）
    ├── 检查监控仪表盘是否正常显示
    ├── 了解当前系统状态和已知问题
    ├── 确认是否有计划维护窗口
    └── 确认后援支持人员联系方式

  □ 值班期间
    ├── 响应告警：5 分钟内响应 P0/P1 告警
    ├── 升级机制：15 分钟内未解决则升级
    ├── 沟通透明：在事故频道更新处理进展
    ├── 记录日志：记录每一步操作和决策
    └── 寻求帮助：遇到不熟悉的问题及时求助

  □ 故障处理流程
    ├── 1. 确认故障：验证告警是否真实
    ├── 2. 评估影响：确定影响范围和严重程度
    ├── 3. 快速恢复：优先恢复服务，再查根因
    ├── 4. 通知相关方：通知团队和利益相关者
    ├── 5. 记录时间线：记录每个关键操作的时间
    └── 6. 事后复盘：组织复盘会议

  □ 值班后交接
    ├── 更新值班日志
    ├── 交接未完成的事项
    ├── 分享值班期间的经验教训
    └── 反馈告警质量问题
```

#### 7.3 值班质量度量

```yaml
# 值班质量指标

oncall_metrics:
  # 告警响应时间
  - name: alert_response_time
    description: 从告警触发到值班人员确认的时间
    target:
      P0: "< 5 分钟"
      P1: "< 15 分钟"
      P2: "< 1 小时"
      P3: "< 24 小时"

  # 告警解决时间
  - name: alert_resolution_time
    description: 从告警触发到问题解决的时间
    target:
      P0: "< 30 分钟"
      P1: "< 2 小时"
      P2: "< 8 小时"
      P3: "< 1 周"

  # 误报率
  - name: false_positive_rate
    description: 无需人工干预的告警比例
    target: "< 10%"

  # 值班负荷
  - name: oncall_load
    description: 每次值班期间处理的告警数量
    target: "< 5 个/天"

  # MTTR
  - name: mttr
    description: 平均故障恢复时间
    target: "< 30 分钟"
```

### 8. SRE 实战案例

#### 8.1 电商平台 SLO 定义

```
电商平台 SLO 体系示例：

  ┌──────────────────────────────────────────────────────────────┐
  │  服务：电商平台                                               │
  │  SLO 体系定义：                                              │
  ├──────────────────────────────────────────────────────────────┤
  │                                                              │
  │  1. 商品搜索服务                                             │
  │     ├── SLI：搜索请求成功率                                   │
  │     ├── SLO：99.95%（30天滚动窗口）                          │
  │     └── 错误预算：每月 21.6 分钟                              │
  │                                                              │
  │  2. 用户认证服务                                             │
  │     ├── SLI：登录请求成功率                                   │
  │     ├── SLO：99.99%（30天滚动窗口）                          │
  │     └── 错误预算：每月 4.32 分钟                              │
  │                                                              │
  │  3. 订单创建服务                                             │
  │     ├── SLI：下单请求成功率                                   │
  │     ├── SLO：99.99%（30天滚动窗口）                          │
  │     └── 错误预算：每月 4.32 分钟                              │
  │                                                              │
  │  4. 支付处理服务                                             │
  │     ├── SLI：支付请求成功率                                   │
  │     ├── SLO：99.999%（30天滚动窗口）                         │
  │     └── 错误预算：每月 0.432 分钟                             │
  │                                                              │
  │  5. 订单查询服务                                             │
  │     ├── SLI：查询请求 P99 延迟 < 500ms                       │
  │     ├── SLO：99.9%（30天滚动窗口）                           │
  │     └── 错误预算：每月 43.2 分钟                              │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  整体可用性 = 所有服务 SLO 的乘积
    = 99.95% × 99.99% × 99.99% × 99.999% × 99.9%
    ≈ 99.83%

  说明：分布式系统的整体可用性低于单个组件
        这就是为什么需要在架构层面做容错设计
```

#### 8.2 故障排查案例：错误预算快速消耗

```
场景：
  电商平台在 5 月 10 日上午 10:00 发现错误预算消耗速率异常
  当前 30 天窗口错误预算剩余 35%，但过去 1 小时消耗了 15%

  排查过程：

  1. 检查 SLI 指标
     │
     │  查询当前错误率：
     │  sum(rate(http_requests_total{code=~"5.."}[5m]))
     │  / sum(rate(http_requests_total[5m]))
     │  = 2.3%（正常值 < 0.1%）
     │
     ▼
  2. 定位错误来源
     │
     │  按服务维度分析：
     │  - user-service: 错误率 0.05%（正常）
     │  - product-service: 错误率 0.1%（正常）
     │  - order-service: 错误率 8.5%（异常！）
     │  - payment-service: 错误率 0.02%（正常）
     │
     ▼
  3. 分析 order-service
     │
     │  检查日志：
     │  ERROR: Connection pool exhausted
     │  ERROR: Too many connections to database
     │
     │  检查数据库指标：
     │  mysql_global_status_threads_connected = 150
     │  mysql_global_variables_max_connections = 151
     │  → 数据库连接池已满
     │
     ▼
  4. 根因分析
     │
     │  原因：5月10日是促销活动首日，订单量激增
     │  数据库连接池配置过小，无法处理突增流量
     │
     ▼
  5. 修复措施
     │
     ├── 紧急：增加数据库连接池大小
     ├── 紧急：启用数据库读写分离
     ├── 短期：优化慢查询
     └── 长期：引入连接池中间件
     │
     ▼
  6. 复盘改进
     │
     ├── 增加连接池使用率告警（> 80% 告警）
     ├── 在促销前进行压力测试
     ├── 建立容量规划模型
     └── 更新 SLO，考虑促销期间的流量模型
```

---

## 💻 实战练习

### 练习 1：定义服务 SLO

**目标**：为一个微服务定义完整的 SLI/SLO 体系

**步骤**：

```yaml
# 1. 选择一个服务（假设为 user-service）
# 2. 识别关键用户旅程
# 3. 为每个旅程定义 SLI
# 4. 设置 SLO 目标

# SLO 定义模板
service: user-service
owner: platform-team

slos:
  - name: api-availability
    description: API 可用性
    sli:
      type: ratio
      good_events: |
        sum(rate(http_requests_total{
          service="user-service",
          code=~"2.."
        }[5m]))
      total_events: |
        sum(rate(http_requests_total{
          service="user-service"
        }[5m]))
    target: 0.999
    window: 30d

  - name: api-latency
    description: API 延迟
    sli:
      type: threshold
      metric: http_request_duration_seconds
      threshold: 0.3
    target: 0.99
    window: 30d

  - name: error-rate
    description: 错误率
    sli:
      type: ratio
      good_events: |
        sum(rate(http_requests_total{
          service="user-service",
          code!~"5.."
        }[5m]))
      total_events: |
        sum(rate(http_requests_total{
          service="user-service"
        }[5m]))
    target: 0.9995
    window: 30d
```

### 练习 2：计算错误预算

**目标**：编写脚本计算错误预算消耗

```python
#!/usr/bin/env python3
"""
错误预算计算器
"""

from datetime import datetime, timedelta

class ErrorBudgetCalculator:
    def __init__(self, slo_target: float, window_days: int):
        self.slo_target = slo_target
        self.window_days = window_days
        self.error_budget_pct = 1 - slo_target

    def calculate_budget(self, total_requests: int) -> dict:
        """计算错误预算"""
        total_minutes = self.window_days * 24 * 60
        return {
            "error_budget_pct": self.error_budget_pct,
            "error_budget_minutes": total_minutes * self.error_budget_pct,
            "error_budget_requests": int(total_requests * self.error_budget_pct),
        }

    def calculate_remaining(
        self,
        total_requests: int,
        failed_requests: int
    ) -> dict:
        """计算剩余错误预算"""
        budget = self.calculate_budget(total_requests)
        remaining_requests = budget["error_budget_requests"] - failed_requests
        remaining_pct = remaining_requests / budget["error_budget_requests"]

        return {
            "total_budget": budget["error_budget_requests"],
            "consumed": failed_requests,
            "remaining": remaining_requests,
            "remaining_pct": f"{remaining_pct * 100:.1f}%",
            "status": self._get_status(remaining_pct),
        }

    def _get_status(self, remaining_pct: float) -> str:
        if remaining_pct > 0.5:
            return "HEALTHY"
        elif remaining_pct > 0.2:
            return "WARNING"
        elif remaining_pct > 0:
            return "DANGER"
        else:
            return "EXHAUSTED"

    def predict_exhaustion_date(
        self,
        consumed: int,
        total: int,
        days_elapsed: int
    ) -> str:
        """预测错误预算耗尽日期"""
        if consumed == 0:
            return "No errors consumed"
        budget = self.calculate_budget(total)
        daily_burn_rate = consumed / days_elapsed
        remaining = budget["error_budget_requests"] - consumed
        days_remaining = remaining / daily_burn_rate
        exhaustion_date = datetime.now() + timedelta(days=days_remaining)
        return exhaustion_date.strftime("%Y-%m-%d")


# 使用示例
if __name__ == "__main__":
    calc = ErrorBudgetCalculator(slo_target=0.999, window_days=30)

    # 计算总预算
    budget = calc.calculate_budget(total_requests=100_000_000)
    print(f"错误预算: {budget}")

    # 计算剩余
    remaining = calc.calculate_remaining(
        total_requests=100_000_000,
        failed_requests=50_000
    )
    print(f"剩余预算: {remaining}")

    # 预测耗尽日期
    date = calc.predict_exhaustion_date(
        consumed=50_000,
        total=100_000_000,
        days_elapsed=15
    )
    print(f"预计耗尽日期: {date}")
```

### 练习 3：设计值班制度

**目标**：为一个 10 人团队设计值班制度

```yaml
# 值班制度设计

team:
  name: platform-sre
  size: 10
  regions:
    - name: 亚太
      timezone: Asia/Shanghai
      members: 6
    - name: 北美
      timezone: America/New_York
      members: 4

oncall:
  rotation:
    type: weekly
    start_day: Monday
    start_time: "10:00"
    primary_count: 1
    secondary_count: 1

  schedule:
    # 亚太工作时间（9:00-21:00 CST）
    - name: asia-business-hours
      timezone: Asia/Shanghai
      start: "09:00"
      end: "21:00"
      primary: 亚太团队成员轮值
      secondary: 北美团队成员轮值

    # 北美工作时间（9:00-21:00 EST）
    - name: na-business-hours
      timezone: America/New_York
      start: "09:00"
      end: "21:00"
      primary: 北美团队成员轮值
      secondary: 亚太团队成员轮值

    # 非工作时间
    - name: off-hours
      primary: 按地区轮值
      secondary: 按地区轮值

  escalation:
    - level: 1
      timeout: 5m
      notify: primary
    - level: 2
      timeout: 15m
      notify: secondary
    - level: 3
      timeout: 30m
      notify: team-lead
    - level: 4
      timeout: 60m
      notify: director

  compensation:
    weekday_oncall: 500 CNY/天
    weekend_oncall: 1000 CNY/天
    alert_handling: 100 CNY/次
    overtime_leave: 4h（夜间值班次日）
```

---

## 🎯 面试题精选

### 1. 什么是可观测性的三大支柱？它们之间有什么关系？

**参考答案**：

可观测性的三大支柱是 Metrics（指标）、Logs（日志）和 Traces（链路追踪）。

- **Metrics**：数值型时间序列数据，适合聚合分析和实时告警，存储效率高。回答"发生了什么"。
- **Logs**：离散的事件记录，包含丰富的上下文信息，适合故障排查和审计。回答"为什么发生"。
- **Traces**：请求在分布式系统中的完整调用链路，适合性能分析和依赖梳理。回答"在哪里发生"。

三者关系：互为补充，通过 Exemplar（指标附带 trace_id）、日志中的 trace_id 等方式关联，形成从发现问题到定位根因的完整链路。

### 2. SLI、SLO、SLA 三者有什么区别？

**参考答案**：

- **SLI（Service Level Indicator）**：服务级别指标，是衡量服务质量的量化度量，如可用性 99.9%、P99 延迟 300ms。
- **SLO（Service Level Objective）**：服务级别目标，是 SLI 的目标值，是团队内部的质量承诺，如可用性 >= 99.9%。
- **SLA（Service Level Agreement）**：服务级别协议，是与客户的正式协议，具有法律约束力，通常包含违约赔偿条款。

关键区别：
- SLI 是度量，SLO 是目标，SLA 是协议
- SLO 是内部承诺，SLA 是外部承诺
- 通常 SLA 目标 < SLO 目标（留出缓冲）
- SLO 违反会影响团队考核，SLA 违反会导致经济损失

### 3. 什么是错误预算？如何使用错误预算指导决策？

**参考答案**：

错误预算是 SLO 的反面表达。如果 SLO 是 99.9% 可用性，那么错误预算就是 0.1%，即允许的不可用比例。

错误预算的决策模型：
- **健康（>50%）**：可以进行高风险变更、混沌工程实验
- **警告（20%-50%）**：放慢变更节奏，增加代码审查
- **危险（<20%）**：冻结非紧急变更，全员聚焦可靠性
- **耗尽（0%）**：停止所有变更，只允许紧急修复

错误预算的核心价值：
1. 平衡可靠性与迭代速度
2. 为变更决策提供数据支持
3. 避免过度追求 100% 可用性
4. 促进 SRE 与开发团队协作

### 4. 如何设计基于 SLO 的告警策略？

**参考答案**：

基于 SLO 的告警策略采用"多窗口多燃烧速率"（Multi-Window Multi-Burn-Rate）方法：

| 告警级别 | 燃烧速率 | 短窗口 | 长窗口 | 触发条件 |
|----------|----------|--------|--------|----------|
| P0 Critical | 14.4x | 1h | 5m | 2天内耗尽预算 |
| P0 Critical | 6x | 6h | 30m | 5天内耗尽预算 |
| P1 High | 3x | 1d | 2h | 10天内耗尽预算 |
| P1 High | 1x | 3d | 6h | 30天内耗尽预算 |

燃烧速率 = 错误预算消耗速率 / 预期消耗速率

使用两个窗口（短窗口确认问题存在，长窗口避免误报）可以有效平衡告警灵敏度和准确性。

### 5. 如何选择合适的 SLI？

**参考答案**：

选择 SLI 的原则：
1. **用户可感知**：SLI 应反映用户体验，而非内部实现细节（好：API 响应时间；差：CPU 使用率）
2. **可度量**：SLI 必须可以被准确、持续地测量
3. **可操作**：SLI 变化时团队能采取行动
4. **聚合粒度合适**：P99 延迟比平均延迟更能反映用户体验
5. **有限数量**：每个服务 2-5 个 SLI，避免关注点分散

常见 SLI 类型：
- 可用性：成功请求 / 总请求
- 延迟：在阈值内完成的请求比例
- 吞吐量：每秒处理请求数
- 正确性：返回正确结果的比例
- 耐久性：数据持久保存的比例

### 6. SLA 中通常包含哪些内容？

**参考答案**：

SLA 通常包含以下内容：
1. **服务定义**：服务范围、服务时间、服务等级
2. **性能指标**：可用性、延迟、吞吐量、持久性、恢复时间
3. **测量方法**：测量工具、测量周期、测量点、排除项
4. **违约条款**：赔偿方式（服务信用/退款）、赔偿比例、赔偿上限
5. **排除条款**：计划维护、不可抗力、客户自身原因、第三方故障

典型赔偿梯度：
- 可用性 99.9% - 99.0% → 10% 服务信用
- 可用性 99.0% - 95.0% → 25% 服务信用
- 可用性 < 95.0% → 50% 服务信用

### 7. 为什么分布式系统的整体可用性低于单个组件？

**参考答案**：

根据可用性计算公式，串联系统的整体可用性 = 各组件可用性的乘积。

假设一个请求链路经过 5 个服务，每个服务可用性为 99.9%：
整体可用性 = 99.9%^5 = 99.5%

这就是为什么：
1. 需要在架构层面做容错设计（熔断、降级、重试）
2. 非关键路径应该做异步解耦
3. 需要合理设置 SLO，不能所有服务都要求 99.99%
4. 需要通过缓存、CDN 等手段减少依赖链路

### 8. 值班制度设计需要考虑哪些因素？

**参考答案**：

值班制度设计需要考虑：
1. **轮转周期**：建议一周轮转，避免疲劳
2. **值班人数**：主值班 + 副值班，互相备份
3. **时区覆盖**：考虑全球化团队的时区差异
4. **升级机制**：明确各级别的升级路径和超时时间
5. **补偿机制**：值班津贴、调休、告警补贴
6. **交接流程**：标准化交接内容和流程
7. **培训机制**：新成员需要 shadow 老值班人员
8. **质量度量**：响应时间、解决时间、误报率、值班负荷

---

## 📚 深入阅读

1. **《Site Reliability Engineering》** - Google SRE 团队著，SRE 领域的圣经
2. **《The Site Reliability Workbook》** - Google SRE 团队著，SRE 实践手册
3. **《Implementing Service Level Objectives》** - Alex Hidalgo 著，SLO 实施指南
4. **Google SRE Book - Chapter 3: Embracing Risk** - 错误预算的详细讲解
5. **Google SRE Book - Chapter 4: Service Level Objectives** - SLO 定义方法
6. **Prometheus Best Practices** - https://prometheus.io/docs/practices/
7. **SLO Tracker** - https://sloth.dev/ - SLO 管理工具

---

## ✅ 自检清单

- [ ] 能够解释可观测性三大支柱的概念和区别
- [ ] 能够为一个服务定义合适的 SLI
- [ ] 能够设置合理的 SLO 目标
- [ ] 理解 SLA 与 SLO 的区别及法律约束
- [ ] 能够计算错误预算和燃烧速率
- [ ] 掌握多窗口多燃烧速率告警策略
- [ ] 能够设计值班制度和升级机制
- [ ] 理解错误预算如何指导变更决策
- [ ] 能够用 PromQL 实现 SLI 查询
- [ ] 能够设计完整的 SLO 体系文档
