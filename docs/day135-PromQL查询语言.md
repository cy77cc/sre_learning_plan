# Day 135: PromQL 查询语言

> 📅 日期：2026-05-03
> 📖 学习主题：PromQL 选择器、聚合函数、常用函数、范围查询、子查询、Recording Rules、告警规则
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 133 (可观测性基础), Day 134 (Prometheus 基础)

---

## 🎯 学习目标

- 掌握 PromQL 的数据模型和向量类型
- 熟练使用标签匹配器和选择器
- 掌握常用聚合函数和内置函数
- 理解范围向量和子查询的使用
- 能够编写 Recording Rules 优化查询性能
- 能够编写 Alerting Rules 定义告警条件

---

## 📖 核心知识点

### 1. PromQL 数据模型

#### 1.1 向量类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PromQL 数据类型                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │   瞬时向量       │  │   范围向量       │                        │
│  │  (Instant Vector)│  │  (Range Vector)  │                        │
│  ├──────────────────┤  ├──────────────────┤                        │
│  │ 某个时间点的值   │  │ 一段时间内的值   │                        │
│  │                  │  │                  │                        │
│  │ http_requests    │  │ http_requests    │                        │
│  │ _total           │  │ _total[5m]       │                        │
│  │                  │  │                  │                        │
│  │ 返回：当前最新值 │  │ 返回：5分钟内    │                        │
│  │                  │  │ 的所有数据点     │                        │
│  └──────────────────┘  └──────────────────┘                        │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │   标量           │  │   字符串         │                        │
│  │  (Scalar)        │  │  (String)        │                        │
│  ├──────────────────┤  ├──────────────────┤                        │
│  │ 浮点数值         │  │ 字符串值         │                        │
│  │                  │  │                  │                        │
│  │ 0.999            │  │ "hello"          │                        │
│  │                  │  │                  │                        │
│  │ 使用较少         │  │ 使用较少         │                        │
│  └──────────────────┘  └──────────────────┘                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 时间序列结构

```
时间序列 = 指标名称 + 标签集 + 样本值

示例：
  http_requests_total{method="GET", handler="/api/users", status="200"}
  │                    │                                          │
  │                    └── 标签集（Labels）                       │
  └── 指标名称（Metric Name）                                    │

  样本值 = (值, 时间戳)
  (1234, 1620000000)
  (1235, 1620000015)
  (1237, 1620000030)
```

### 2. 选择器与标签匹配

#### 2.1 标签匹配器

```promql
# 精确匹配
http_requests_total{method="GET"}
http_requests_total{status="200", method="POST"}

# 不等于
http_requests_total{method!="GET"}

# 正则匹配（=~）
http_requests_total{status=~"2.."}
http_requests_total{handler=~"/api/.*"}

# 正则不匹配（!~）
http_requests_total{status!~"2.."}
http_requests_total{handler!~"/health"}
```

#### 2.2 指标名称匹配

```promql
# 精确匹配
http_requests_total

# 正则匹配指标名称
{__name__=~"http_requests_total"}

# 匹配多个指标
{__name__=~"http_requests_total|http_errors_total"}

# 匹配所有 http 开头的指标
{__name__=~"http_.+"}
```

#### 2.3 范围向量选择器

```promql
# 范围向量（过去 5 分钟的数据）
http_requests_total[5m]

# 支持的时间单位：
# s - 秒
# m - 分钟
# h - 小时
# d - 天
# w - 周
# y - 年

# 示例
http_requests_total[1h]      # 过去 1 小时
node_cpu_seconds_total[5m]   # 过去 5 分钟
http_request_duration_seconds_bucket[24h]  # 过去 24 小时
```

#### 2.4 偏移修饰符

```promql
# 查询 5 分钟前的值
http_requests_total offset 5m

# 对比当前值和 1 小时前的值
http_requests_total - http_requests_total offset 1h

# 计算增长率（当前 vs 1天前）
(http_requests_total - http_requests_total offset 1d) / http_requests_total offset 1d * 100
```

### 3. 聚合操作

#### 3.1 聚合函数

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PromQL 聚合函数                                    │
├──────────────┬──────────────────────────────────────────────────────┤
│ 函数          │ 说明                                                │
├──────────────┼──────────────────────────────────────────────────────┤
│ sum          │ 求和                                                │
│ min          │ 最小值                                              │
│ max          │ 最大值                                              │
│ avg          │ 平均值                                              │
│ stddev       │ 标准差                                              │
│ stdvar       │ 方差                                                │
│ count        │ 计数                                                │
│ count_values │ 按值计数                                            │
│ bottomk      │ 最小的 k 个值                                       │
│ topk         │ 最大的 k 个值                                       │
│ quantile     │ 分位数                                              │
│ group        │ 分组（不聚合，只按标签分组）                        │
└──────────────┴──────────────────────────────────────────────────────┘
```

#### 3.2 聚合示例

```promql
# 1. 按 job 分组求和（总 QPS）
sum(rate(http_requests_total[5m])) by (job)

# 2. 按 job 和 method 分组
sum(rate(http_requests_total[5m])) by (job, method)

# 3. 排除某些标签后聚合
sum without(instance) (rate(http_requests_total[5m]))

# 4. 不分组（全局聚合）
sum(rate(http_requests_total[5m]))

# 5. Top 5 最繁忙的服务
topk(5, sum(rate(http_requests_total[5m])) by (job))

# 6. 最不繁忙的 3 个节点
bottomk(3, sum(rate(node_network_receive_bytes_total[5m])) by (instance))

# 7. 计算 P99 分位数
quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 8. 按状态码分组计数
count_values("status", http_requests_total)

# 9. 统计有多少个实例在运行
count(up == 1)

# 10. 统计有多少个实例宕机
count(up == 0)
```

#### 3.3 聚合组合

```promql
# 错误率计算
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# 按服务分组的错误率
sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (job) (rate(http_requests_total[5m]))

# 只显示错误率 > 1% 的服务
(
  sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
  /
  sum by (job) (rate(http_requests_total[5m]))
) > 0.01
```

### 4. 常用函数

#### 4.1 速率函数

```promql
# rate() - 计算 Counter 的每秒增长率（平滑）
rate(http_requests_total[5m])

# increase() - 计算 Counter 在时间范围内的增量
increase(http_requests_total[1h])

# irate() - 计算瞬时增长率（基于最后两个数据点）
irate(http_requests_total[5m])

# deriv() - 计算 Gauge 的每秒导数（变化率）
deriv(node_memory_MemFree_bytes[5m])
```

```
rate() vs irate() vs increase()：

  rate():
  ├── 基于时间范围内所有数据点计算平均速率
  ├── 结果平滑，适合告警和趋势分析
  ├── 推荐用于 Recording Rules
  └── 示例：rate(http_requests_total[5m])

  irate():
  ├── 只基于最后两个数据点计算瞬时速率
  ├── 结果波动大，适合观察瞬时变化
  ├── 不推荐用于告警（容易误报）
  └── 示例：irate(http_requests_total[5m])

  increase():
  ├── 计算时间范围内的总增量
  ├── 等同于 rate() × 时间范围（秒）
  └── 示例：increase(http_requests_total[1h]) = rate() × 3600
```

#### 4.2 数学函数

```promql
# abs() - 绝对值
abs(node_memory_MemFree_bytes - node_memory_MemAvailable_bytes)

# ceil() - 向上取整
ceil(node_load1)

# floor() - 向下取整
floor(node_load1)

# round() - 四舍五入
round(node_load1, 0.1)  # 保留一位小数

# clamp() - 限制在范围内
clamp(node_cpu_usage, 0, 100)

# clamp_min() / clamp_max() - 限制最小/最大值
clamp_min(node_cpu_usage, 0)
clamp_max(node_cpu_usage, 100)

# sort() / sort_desc() - 排序
sort_desc(node_memory_MemFree_bytes)
```

#### 4.3 时间函数

```promql
# time() - 当前 Unix 时间戳
time()

# timestamp() - 获取样本的时间戳
timestamp(up)

# day_of_week() - 星期几（0=Sunday）
day_of_week()

# hour() - 小时（0-23）
hour()

# minute() - 分钟（0-59）
minute()
```

#### 4.4 缺失数据处理

```promql
# absent() - 检测时间序列是否存在
absent(up{job="api"})

# absent_over_time() - 检测范围向量是否为空
absent_over_time(up{job="api"}[5m])

# vector() - 创建一个常量向量
vector(1)

# label_replace() - 添加/替换标签
label_replace(up, "host", "$1", "instance", "(.*):.*")

# label_join() - 合并标签
label_join(up, "full_name", "-", "job", "instance")
```

#### 4.5 预测函数

```promql
# predict_linear() - 线性预测
# 预测 4 小时后磁盘是否满
predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0

# holt_winters() - 平滑预测
holt_winters(http_requests_total[1h], 0.3, 0.1)
```

### 5. 范围查询与子查询

#### 5.1 范围查询

```promql
# 范围查询返回一段时间内的所有数据点
http_requests_total[5m]

# 常用于 rate/increase 等函数
rate(http_requests_total[5m])
increase(http_requests_total[1h])

# 范围选择器不能直接用于绘图，需要配合函数使用
# 错误：直接查询范围向量
# 正确：使用 rate/increase 等函数处理
```

#### 5.2 子查询

```promql
# 子查询：对范围向量的结果再进行查询
# 语法：<instant_query>[<range>:<resolution>]

# 示例：过去 1 小时内，每分钟的 QPS 最大值
max_over_time(rate(http_requests_total[5m])[1h:1m])

# 示例：过去 24 小时内，每小时的 P99 延迟
max_over_time(histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))[24h:1h])

# 示例：过去 1 天内，每 5 分钟的错误率最大值
max_over_time(
  (
    rate(http_requests_total{status=~"5.."}[5m])
    /
    rate(http_requests_total[5m])
  )[1d:5m]
)

# 子查询的分辨率
# [1h:1m] 表示过去 1 小时，每 1 分钟一个数据点
# [1d:5m] 表示过去 1 天，每 5 分钟一个数据点
# [1w:1h] 表示过去 1 周，每 1 小时一个数据点
```

#### 5.3 @ 修饰符

```promql
# @ 修饰符：指定查询的时间点
http_requests_total @ 1620000000

# 结合范围向量
rate(http_requests_total[5m] @ 1620000000)

# 使用 start() 和 end()
rate(http_requests_total[5m] @ start())
rate(http_requests_total[5m] @ end())
```

### 6. Recording Rules

#### 6.1 Recording Rules 概述

```
Recording Rules 的作用：

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  问题：                                                      │
  │  ├── 复杂查询每次都要重新计算                                │
  │  ├── Dashboard 加载慢                                        │
  │  └── 告警规则重复计算相同表达式                              │
  │                                                              │
  │  解决：                                                      │
  │  ├── 预先计算结果，存储为新指标                              │
  │  ├── 提高查询性能                                            │
  │  └── 简化 PromQL                                             │
  │                                                              │
  │  工作原理：                                                  │
  │  ┌──────────┐     ┌──────────────┐     ┌──────────────┐   │
  │  │ PromQL   │────▶│ Rule Engine  │────▶│ 新时间序列   │   │
  │  │ 表达式   │     │ 定期评估     │     │ 存储到 TSDB  │   │
  │  └──────────┘     └──────────────┘     └──────────────┘   │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

#### 6.2 Recording Rules 配置

```yaml
# /etc/prometheus/rules/recording_rules.yml
groups:
  - name: http_recording_rules
    interval: 30s  # 评估间隔
    rules:
      # 1. 预计算每秒请求数（按 job 分组）
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)

      # 2. 预计算错误率（按 job 分组）
      - record: job:http_error_rate:ratio5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
          /
          sum(rate(http_requests_total[5m])) by (job)

      # 3. 预计算 P99 延迟
      - record: job:http_request_duration:p99
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # 4. 预计算 P95 延迟
      - record: job:http_request_duration:p95
        expr: |
          histogram_quantile(0.95,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # 5. 预计算平均延迟
      - record: job:http_request_duration:avg
        expr: |
          sum(rate(http_request_duration_seconds_sum[5m])) by (job)
          /
          sum(rate(http_request_duration_seconds_count[5m])) by (job)

  - name: node_recording_rules
    interval: 30s
    rules:
      # 6. 预计算 CPU 使用率
      - record: instance:node_cpu:usage
        expr: |
          100 - (
            avg by (instance) (
              rate(node_cpu_seconds_total{mode="idle"}[5m])
            ) * 100
          )

      # 7. 预计算内存使用率
      - record: instance:node_memory:usage
        expr: |
          (1 - (
            node_memory_MemAvailable_bytes
            /
            node_memory_MemTotal_bytes
          )) * 100

      # 8. 预计算磁盘使用率
      - record: instance:node_disk:usage
        expr: |
          (1 - (
            node_filesystem_avail_bytes{fstype!="tmpfs"}
            /
            node_filesystem_size_bytes{fstype!="tmpfs"}
          )) * 100

      # 9. 预计算网络接收速率
      - record: instance:node_network:receive_rate
        expr: |
          sum by (instance) (
            rate(node_network_receive_bytes_total{device!="lo"}[5m])
          )

      # 10. 预计算网络发送速率
      - record: instance:node_network:transmit_rate
        expr: |
          sum by (instance) (
            rate(node_network_transmit_bytes_total{device!="lo"}[5m])
          )
```

#### 6.3 Recording Rules 命名规范

```
Recording Rules 命名规范：

  格式：level:metric:operations

  level（聚合级别）：
  ├── job       - 按 job 聚合
  ├── instance  - 按 instance 聚合
  ├── cluster   - 按 cluster 聚合
  └── global    - 全局聚合

  metric（指标名称）：
  ├── http_requests
  ├── node_cpu
  ├── node_memory
  └── http_request_duration

  operations（操作）：
  ├── rate5m    - 5 分钟速率
  ├── ratio5m   - 5 分钟比率
  ├── p99       - P99 分位数
  ├── p95       - P95 分位数
  ├── avg       - 平均值
  ├── sum       - 总和
  └── count     - 计数

  示例：
  ├── job:http_requests:rate5m
  ├── job:http_error_rate:ratio5m
  ├── job:http_request_duration:p99
  ├── instance:node_cpu:usage
  └── instance:node_memory:usage

  使用预计算指标：
  # 原来（每次都要计算）
  sum(rate(http_requests_total[5m])) by (job)

  # 现在（直接查询预计算结果）
  job:http_requests:rate5m
```

### 7. Alerting Rules

#### 7.1 Alerting Rules 配置

```yaml
# /etc/prometheus/rules/alerting_rules.yml
groups:
  - name: node_alerts
    rules:
      # CPU 使用率告警
      - alert: HighCPUUsage
        expr: instance:node_cpu:usage > 80
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "CPU 使用率过高"
          description: "实例 {{ $labels.instance }} CPU 使用率 {{ $value | printf \"%.1f\" }}%，持续 5 分钟"

      # 内存使用率告警
      - alert: HighMemoryUsage
        expr: instance:node_memory:usage > 90
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "内存使用率过高"
          description: "实例 {{ $labels.instance }} 内存使用率 {{ $value | printf \"%.1f\" }}%，持续 5 分钟"

      # 磁盘使用率告警
      - alert: HighDiskUsage
        expr: instance:node_disk:usage > 85
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "磁盘使用率过高"
          description: "实例 {{ $labels.instance }} 磁盘使用率 {{ $value | printf \"%.1f\" }}%，持续 10 分钟"

      # 磁盘将在 4 小时内满
      - alert: DiskWillFillIn4Hours
        expr: predict_linear(node_filesystem_avail_bytes{fstype!="tmpfs"}[1h], 4*3600) < 0
        for: 30m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "磁盘预计 4 小时内满"
          description: "实例 {{ $labels.instance }} 磁盘 {{ $labels.mountpoint }} 预计 4 小时内满"

      # 实例宕机
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "实例宕机"
          description: "实例 {{ $labels.instance }} 已宕机超过 1 分钟"

  - name: http_alerts
    rules:
      # 错误率告警
      - alert: HighErrorRate
        expr: job:http_error_rate:ratio5m > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "HTTP 错误率过高"
          description: "服务 {{ $labels.job }} 错误率 {{ $value | humanizePercentage }}，持续 5 分钟"

      # 延迟告警
      - alert: HighLatency
        expr: job:http_request_duration:p99 > 1
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "P99 延迟过高"
          description: "服务 {{ $labels.job }} P99 延迟 {{ $value | printf \"%.2f\" }}s，持续 5 分钟"

      # QPS 突增告警
      - alert: QPSSpike
        expr: |
          job:http_requests:rate5m > 2 * job:http_requests:rate5m offset 1h
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "QPS 突增"
          description: "服务 {{ $labels.job }} QPS 是 1 小时前的 2 倍以上"

  - name: slo_alerts
    rules:
      # SLO 燃烧速率告警（14.4x，2天内耗尽预算）
      - alert: SLOBurnRateCritical
        expr: |
          (
            1 - (
              sum by (job) (rate(http_requests_total{status=~"2.."}[1h]))
              /
              sum by (job) (rate(http_requests_total[1h]))
            )
          ) > (14.4 * 0.001)
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "SLO 燃烧速率严重超标"
          description: "服务 {{ $labels.job }} 错误预算燃烧速率 14.4x，预计 2 天内耗尽月度预算"
```

#### 7.2 告警模板

```yaml
# 告警注解中使用模板
annotations:
  # 基本变量
  summary: "实例 {{ $labels.instance }} CPU 使用率过高"
  description: "当前值: {{ $value | printf \"%.1f\" }}%"

  # 标签引用
  instance: "{{ $labels.instance }}"
  job: "{{ $labels.job }}"

  # 值格式化
  value_raw: "{{ $value }}"
  value_pct: "{{ $value | humanizePercentage }}"
  value_float: "{{ $value | printf \"%.2f\" }}"
  value_human: "{{ $value | humanize }}"

  # 时间
  startsAt: "{{ $startsAt }}"

  # 多标签
  description: |
    实例: {{ $labels.instance }}
    任务: {{ $labels.job }}
    当前值: {{ $value | printf "%.1f" }}%
    阈值: 80%
    持续时间: 5 分钟
```

### 8. PromQL 最佳实践

#### 8.1 性能优化

```
PromQL 性能优化建议：

  1. 使用 Recording Rules 预计算复杂查询
     ├── 将 Dashboard 中的复杂查询预计算
     ├── 将告警规则中的重复表达式预计算
     └── 合理设置评估间隔

  2. 避免高基数聚合
     ├── 不要按高基数标签（如 request_id）聚合
     ├── 使用 without() 排除不需要的标签
     └── 监控查询的序列数量

  3. 合理选择时间范围
     ├── 告警规则使用较短的时间窗口（5m）
     ├── Dashboard 使用较长的时间窗口（1h）
     └── 避免使用过长的时间范围（>1d）

  4. 使用适当的函数
     ├── Counter 使用 rate() 而非 irate()
     ├── Gauge 使用直接查询或 deriv()
     └── Histogram 使用 histogram_quantile()

  5. 避免子查询
     ├── 子查询性能开销大
     ├── 尽量使用 Recording Rules 替代
     └── 如果必须使用，限制分辨率
```

#### 8.2 常见陷阱

```
PromQL 常见陷阱：

  1. 忘记 rate() 处理 Counter
     ❌ http_requests_total          # 只显示绝对值
     ✅ rate(http_requests_total[5m]) # 计算速率

  2. 忘记处理 Counter 重置
     rate() 函数自动处理，手动计算时需要注意

  3. 使用 irate() 进行告警
     ❌ irate() 波动大，容易误报
     ✅ rate() 平滑，适合告警

  4. 除零错误
     ❌ a / b                        # b 为 0 时出错
     ✅ a / (b > 0)                  # 安全除法

  5. 标签不匹配
     ❌ sum(a) + sum(b)              # 标签不匹配
     ✅ sum by (job) (a) + sum by (job) (b)

  6. 忘记 by/without
     ❌ sum(rate(http_requests_total[5m]))  # 丢失标签
     ✅ sum by (job) (rate(http_requests_total[5m]))
```

### 9. SRE 实战案例

#### 9.1 RED 方法查询

```promql
# RED 方法（Rate, Errors, Duration）
# 用于面向请求的服务

# Rate - 每秒请求数
sum(rate(http_requests_total[5m])) by (job)

# Errors - 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
/
sum(rate(http_requests_total[5m])) by (job)

# Duration - P99 延迟
histogram_quantile(0.99,
  sum by (job, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

#### 9.2 USE 方法查询

```promql
# USE 方法（Utilization, Saturation, Errors）
# 用于基础设施资源

# CPU Utilization - CPU 使用率
100 - (
  avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  ) * 100
)

# CPU Saturation - 负载/核心数
node_load1 / count by (instance) (node_cpu_seconds_total{mode="idle"})

# Memory Utilization - 内存使用率
(1 - (
  node_memory_MemAvailable_bytes
  /
  node_memory_MemTotal_bytes
)) * 100

# Memory Saturation - Swap 使用
rate(node_vmstat_pswpin[5m]) + rate(node_vmstat_pswpout[5m])

# Disk Utilization - 磁盘使用率
(1 - (
  node_filesystem_avail_bytes{fstype!="tmpfs"}
  /
  node_filesystem_size_bytes{fstype!="tmpfs"}
)) * 100

# Disk Saturation - IO 队列长度
node_disk_io_time_seconds_total

# Network Utilization - 网络使用率
rate(node_network_receive_bytes_total{device!="lo"}[5m])
/
node_network_speed_bytes{device!="lo"}

# Network Errors - 网络错误
rate(node_network_receive_errs_total{device!="lo"}[5m])
+
rate(node_network_transmit_errs_total{device!="lo"}[5m])
```

#### 9.3 容量规划查询

```promql
# 预测磁盘何时满
predict_linear(node_filesystem_avail_bytes{fstype!="tmpfs"}[7d], 30*24*3600) < 0

# 预测内存是否会在 24 小时内不足
predict_linear(node_memory_MemAvailable_bytes[1h], 24*3600) < 0

# 计算 QPS 增长趋势
(
  sum(rate(http_requests_total[1d]))
  -
  sum(rate(http_requests_total[1d] offset 7d))
)
/
sum(rate(http_requests_total[1d] offset 7d))
* 100
```

---

## 💻 实战练习

### 练习 1：基础 PromQL 查询

**目标**：编写基本的 PromQL 查询

```promql
# 1. 查询所有节点的 CPU 使用率
100 - (
  avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  ) * 100
)

# 2. 查询内存使用率最高的 5 个节点
topk(5,
  (1 - (
    node_memory_MemAvailable_bytes
    /
    node_memory_MemTotal_bytes
  )) * 100
)

# 3. 查询磁盘使用率
(1 - (
  node_filesystem_avail_bytes{fstype!="tmpfs"}
  /
  node_filesystem_size_bytes{fstype!="tmpfs"}
)) * 100 > 80

# 4. 查询网络接收速率（MB/s）
rate(node_network_receive_bytes_total{device!="lo"}[5m]) / 1024 / 1024
```

### 练习 2：编写 Recording Rules

**目标**：为常用查询创建 Recording Rules

```yaml
groups:
  - name: practice_recording_rules
    interval: 30s
    rules:
      # 1. 预计算 CPU 使用率
      - record: instance:cpu:usage5m
        expr: |
          100 - (
            avg by (instance) (
              rate(node_cpu_seconds_total{mode="idle"}[5m])
            ) * 100
          )

      # 2. 预计算内存使用率
      - record: instance:memory:usage5m
        expr: |
          (1 - (
            node_memory_MemAvailable_bytes
            /
            node_memory_MemTotal_bytes
          )) * 100

      # 3. 预计算磁盘使用率
      - record: instance:disk:usage
        expr: |
          (1 - (
            node_filesystem_avail_bytes{fstype!="tmpfs"}
            /
            node_filesystem_size_bytes{fstype!="tmpfs"}
          )) * 100

      # 4. 预计算网络接收速率
      - record: instance:network:receive_rate5m
        expr: |
          sum by (instance) (
            rate(node_network_receive_bytes_total{device!="lo"}[5m])
          )
```

### 练习 3：编写告警规则

**目标**：编写完整的告警规则

```yaml
groups:
  - name: practice_alerts
    rules:
      # 1. CPU 使用率告警
      - alert: HighCPUUsage
        expr: instance:cpu:usage5m > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "实例 {{ $labels.instance }} CPU 使用率 {{ $value | printf \"%.1f\" }}%"

      # 2. 内存使用率告警
      - alert: HighMemoryUsage
        expr: instance:memory:usage5m > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "内存使用率过高"
          description: "实例 {{ $labels.instance }} 内存使用率 {{ $value | printf \"%.1f\" }}%"

      # 3. 磁盘将在 4 小时内满
      - alert: DiskWillFillSoon
        expr: predict_linear(node_filesystem_avail_bytes{fstype!="tmpfs"}[1h], 4*3600) < 0
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "磁盘预计 4 小时内满"
          description: "实例 {{ $labels.instance }} 磁盘 {{ $labels.mountpoint }} 预计 4 小时内满"

      # 4. 实例宕机
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "实例宕机"
          description: "实例 {{ $labels.instance }} 已宕机超过 1 分钟"
```

---

## 🎯 面试题精选

### 1. rate() 和 irate() 有什么区别？各适用于什么场景？

**参考答案**：

- **rate()**：基于时间范围内所有数据点计算平均速率，结果平滑，适合告警和趋势分析
- **irate()**：只基于最后两个数据点计算瞬时速率，结果波动大，适合观察瞬时变化

推荐：告警和 Recording Rules 使用 rate()，Dashboard 中观察瞬时变化使用 irate()。

### 2. 如何在 PromQL 中安全地进行除法运算？

**参考答案**：

使用 `(b > 0)` 过滤掉分母为 0 的情况：
```promql
# 安全除法
a / (b > 0)

# 或使用 or 运算提供默认值
(a / b) or vector(0)
```

### 3. Recording Rules 的命名规范是什么？

**参考答案**：

格式：`level:metric:operations`
- level：聚合级别（job、instance、cluster、global）
- metric：指标名称
- operations：操作（rate5m、ratio5m、p99、avg 等）

示例：`job:http_requests:rate5m`、`instance:node_cpu:usage`

### 4. 如何使用 PromQL 实现 RED 方法监控？

**参考答案**：

```promql
# Rate - 每秒请求数
sum(rate(http_requests_total[5m])) by (job)

# Errors - 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
/
sum(rate(http_requests_total[5m])) by (job)

# Duration - P99 延迟
histogram_quantile(0.99,
  sum by (job, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

### 5. 如何使用 predict_linear() 进行容量规划？

**参考答案**：

```promql
# 预测 4 小时后磁盘是否满
predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0

# 预测 24 小时后内存是否不足
predict_linear(node_memory_MemAvailable_bytes[1h], 24*3600) < 0
```

### 6. 告警规则中的 for 字段有什么作用？

**参考答案**：

`for` 字段定义告警条件必须持续满足的时间才会触发告警。例如 `for: 5m` 表示条件必须持续 5 分钟才触发。

作用：
- 避免瞬时波动导致的误报
- 区分暂时性问题和持续性问题
- 给系统自愈的机会

### 7. 子查询有什么性能问题？如何优化？

**参考答案**：

子查询的性能问题：
1. 每个数据点都需要执行一次内部查询
2. 分辨率越高，计算量越大
3. 时间范围越长，数据量越大

优化方法：
1. 使用 Recording Rules 预计算
2. 降低子查询的分辨率
3. 限制时间范围
4. 避免嵌套子查询

---

## 📚 深入阅读

1. **PromQL 官方文档** - https://prometheus.io/docs/prometheus/latest/querying/basics/
2. **PromQL 函数参考** - https://prometheus.io/docs/prometheus/latest/querying/functions/
3. **Recording Rules** - https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/
4. **Alerting Rules** - https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
5. **PromQL 最佳实践** - https://prometheus.io/docs/practices/

---

## ✅ 自检清单

- [ ] 理解 PromQL 的四种数据类型
- [ ] 熟练使用标签匹配器（=、!=、=~、!~）
- [ ] 掌握范围向量和偏移修饰符
- [ ] 能够使用聚合函数（sum、avg、topk 等）
- [ ] 掌握 rate()、increase()、irate() 的区别
- [ ] 能够编写 Recording Rules
- [ ] 能够编写 Alerting Rules
- [ ] 理解 RED 方法和 USE 方法
- [ ] 能够使用 predict_linear() 进行容量规划
- [ ] 了解 PromQL 的性能优化技巧
