# Day 112: CloudWatch 监控

> 📅 日期：2026-05-03
> 📖 学习主题：CloudWatch 监控体系 — 指标、告警、日志、仪表盘、自定义指标、EventBridge、X-Ray、CloudTrail
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 105 (AWS 简介), Day 106 (EC2), Day 108 (S3), Day 110 (ELB)

## 🎯 学习目标

- 掌握 CloudWatch 指标体系与自定义指标的创建方式
- 理解 CloudWatch 告警的配置与多种比较运算符
- 熟练使用 CloudWatch Logs 进行日志收集、查询与分析
- 能够设计生产级 CloudWatch Dashboard
- 理解 EventBridge 事件驱动架构与 CloudTrail 审计日志
- 掌握 X-Ray 分布式追踪的核心概念与集成方式
- 能够构建完整的可观测性体系（Metrics + Logs + Traces）

---

## 📖 核心知识点

### 1. CloudWatch 概述与架构

CloudWatch 是 AWS 可观测性的核心服务，提供指标（Metrics）、日志（Logs）、告警（Alarms）、仪表盘（Dashboard）四大支柱。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CloudWatch 可观测性平台                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Metrics  │  │   Logs   │  │  Alarms  │  │   Dashboards     │   │
│  │  指标监控  │  │  日志收集  │  │  告警通知  │  │   可视化面板      │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └────────┬─────────┘   │
│        │             │             │                 │              │
│  ┌─────┴─────────────┴─────────────┴─────────────────┴─────────┐   │
│  │                    CloudWatch 核心引擎                        │   │
│  └─────┬─────────────┬─────────────┬─────────────────┬─────────┘   │
│        │             │             │                 │              │
│  ┌─────┴────┐  ┌─────┴────┐  ┌────┴─────┐  ┌───────┴────────┐   │
│  │  SNS     │  │ Lambda   │  │AutoScaling│  │  EventBridge   │   │
│  │  通知     │  │  自动修复  │  │  弹性伸缩  │  │  事件路由       │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 命名空间（Namespace）

命名空间是 CloudWatch 指标的容器，不同 AWS 服务使用不同的命名空间：

| 命名空间 | 服务 | 说明 |
|----------|------|------|
| `AWS/EC2` | EC2 | 实例级别指标 |
| `AWS/EBS` | EBS | 卷级别指标 |
| `AWS/ELB` | ELB | Classic Load Balancer |
| `AWS/ApplicationELB` | ALB | Application Load Balancer |
| `AWS/RDS` | RDS | 数据库指标 |
| `AWS/Lambda` | Lambda | 函数指标 |
| `AWS/S3` | S3 | 存储桶指标 |
| `AWS/ApiGateway` | API Gateway | API 指标 |
| `AWS/ECS` | ECS | 容器服务指标 |
| `AWS/EKS` | EKS | Kubernetes 指标 |
| `Custom/MyApp` | 自定义 | 用户自定义命名空间 |

#### 指标（Metrics）核心概念

```
指标 = 命名空间 + 指标名称 + 维度 + 时间戳 + 值

维度（Dimension）示例：
  InstanceId = i-1234567890abcdef0
  InstanceType = t3.medium
  AutoScalingGroupName = my-asg

统计周期（Period）：
  1s, 5s, 10s, 30s, 60s, 300s, 600s, 900s, 3600s, 86400s

统计类型（Statistic）：
  Minimum    - 最小值
  Maximum    - 最大值
  Sum        - 总和
  Average    - 平均值
  SampleCount- 样本数
  pNN.NN     - 百分位数（如 p99, p99.9）
```

### 2. CloudWatch 内置指标详解

#### EC2 指标

| 指标名称 | 说明 | 默认采集 | 周期 |
|----------|------|----------|------|
| `CPUUtilization` | CPU 使用率 | 是（5 分钟） | 1/5 分钟 |
| `NetworkIn` | 入站网络字节数 | 是 | 5 分钟 |
| `NetworkOut` | 出站网络字节数 | 是 | 5 分钟 |
| `DiskReadOps` | EBS 读操作数 | 是 | 5 分钟 |
| `DiskWriteOps` | EBS 写操作数 | 是 | 5 分钟 |
| `StatusCheckFailed` | 状态检查失败 | 是 | 1 分钟 |
| `StatusCheckFailed_System` | 系统状态检查 | 是 | 1 分钟 |
| `StatusCheckFailed_Instance` | 实例状态检查 | 是 | 1 分钟 |

**重要提示**：EC2 默认每 5 分钟采集一次基础指标，启用详细监控（Detailed Monitoring）可缩短到 1 分钟，额外收费。

```
基础监控 vs 详细监控：

基础监控（免费）：
  - 周期：300 秒（5 分钟）
  - 数据点：每小时 12 个
  - 适用于：一般监控场景

详细监控（收费）：
  - 周期：60 秒（1 分钟）
  - 数据点：每小时 60 个
  - 适用于：自动伸缩、实时告警
  - 费用：约 $3.00/实例/月（10 个指标）
```

#### 内存与磁盘指标（需要 CloudWatch Agent）

EC2 不自动报告内存和磁盘使用率，需要安装 CloudWatch Agent：

```bash
# 1. 安装 CloudWatch Agent
sudo yum install -y amazon-cloudwatch-agent
# 或
sudo dpkg -i amazon-cloudwatch-agent.deb

# 2. 配置文件生成向导
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# 3. 启动 Agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# 4. 验证 Agent 运行状态
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a status
```

CloudWatch Agent 配置文件示例：

```json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "namespace": "Custom/EC2",
    "metrics_collected": {
      "mem": {
        "measurement": [
          "mem_used_percent",
          "mem_total",
          "mem_used"
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          "used_percent",
          "inodes_free"
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "diskio": {
        "measurement": [
          "io_time",
          "read_bytes",
          "write_bytes"
        ],
        "metrics_collection_interval": 60
      },
      "swap": {
        "measurement": [
          "swap_used_percent"
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
```

#### ALB 关键指标

| 指标名称 | 说明 | 关键阈值 |
|----------|------|----------|
| `RequestCount` | 请求数 | 监控流量趋势 |
| `TargetResponseTime` | 目标响应时间 | p99 < 3s |
| `HTTPCode_Target_5XX_Count` | 后端 5xx 错误 | < 1% |
| `HTTPCode_ELB_5XX_Count` | ALB 5xx 错误 | 应为 0 |
| `ActiveConnectionCount` | 活跃连接数 | 监控连接池 |
| `NewConnectionCount` | 新建连接数 | 监控连接风暴 |
| `TargetConnectionErrorCount` | 连接错误数 | 应接近 0 |
| `HealthyHostCount` | 健康主机数 | 应 > 0 |

#### RDS 关键指标

| 指标名称 | 说明 | 关键阈值 |
|----------|------|----------|
| `CPUUtilization` | CPU 使用率 | < 80% |
| `FreeableMemory` | 可用内存 | > 1GB |
| `FreeStorageSpace` | 可用存储空间 | > 20% |
| `DatabaseConnections` | 数据库连接数 | < max_connections 的 80% |
| `ReadLatency` | 读延迟 | < 10ms |
| `WriteLatency` | 写延迟 | < 10ms |
| `ReplicaLag` | 只读副本延迟 | < 30s |
| `SwapUsage` | Swap 使用量 | 应为 0 |

#### Lambda 关键指标

| 指标名称 | 说明 | 关键阈值 |
|----------|------|----------|
| `Invocations` | 调用次数 | 监控流量趋势 |
| `Errors` | 错误次数 | < 1% |
| `Duration` | 执行时间 | 接近超时时间告警 |
| `Throttles` | 被限流次数 | 应为 0 |
| `ConcurrentExecutions` | 并发执行数 | < 账户限制 |
| `IteratorAge` | 事件源迭代器年龄 | < 60s (Kinesis) |

### 3. CloudWatch 告警（Alarms）

#### 告警状态机

```
┌──────────────────────────────────────────────────────┐
│                CloudWatch Alarm 状态机                 │
│                                                       │
│  ┌─────────┐    指标超出阈值    ┌───────────┐         │
│  │  OK     │ ───────────────> │ ALARM     │         │
│  │  正常    │                  │ 告警中     │         │
│  └────┬────┘                  └─────┬─────┘         │
│       │                             │                │
│       │    指标恢复正常               │                │
│       │ <───────────────────────────┘                │
│       │                                              │
│  ┌────┴──────────────────────────────────────────┐   │
│  │  INSUFFICIENT_DATA（数据不足）                   │   │
│  │  - 初始化阶段                                    │   │
│  │  - 指标停止上报                                   │   │
│  │  - 周期内没有数据点                               │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

#### 比较运算符

| 运算符 | 说明 | 典型用途 |
|--------|------|----------|
| `GreaterThanThreshold` | 大于阈值 | CPU > 80% |
| `GreaterThanOrEqualToThreshold` | 大于等于阈值 | 错误数 >= 1 |
| `LessThanThreshold` | 小于阈值 | 可用内存 < 1GB |
| `LessThanOrEqualToThreshold` | 小于等于阈值 | 健康主机 <= 0 |
| `LessThanLowerOrGreaterThanUpperThreshold` | 异常检测 | 指标偏离正常范围 |

#### 静态阈值告警

```bash
# 创建 CPU 使用率告警
aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu-alarm" \
  --alarm-description "CPU utilization exceeds 80%" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --ok-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --treat-missing-data missing

# 查询告警状态
aws cloudwatch describe-alarms \
  --alarm-names "high-cpu-alarm"

# 修改告警阈值
aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu-alarm" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold

# 禁用告警
aws cloudwatch disable-alarm-actions \
  --alarm-names "high-cpu-alarm"

# 启用告警
aws cloudwatch enable-alarm-actions \
  --alarm-names "high-cpu-alarm"

# 删除告警
aws cloudwatch delete-alarms \
  --alarm-names "high-cpu-alarm"
```

#### 异常检测告警（Anomaly Detection）

异常检测使用机器学习自动学习指标的历史模式，无需手动设置阈值：

```bash
# 创建异常检测告警
aws cloudwatch put-metric-alarm \
  --alarm-name "anomaly-cpu-alarm" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 2 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/EC2",
          "MetricName": "CPUUtilization",
          "Dimensions": [
            {
              "Name": "InstanceId",
              "Value": "i-1234567890abcdef0"
            }
          ]
        },
        "Period": 300,
        "Stat": "Average"
      },
      "ReturnData": true
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)",
      "Label": "CPUUtilization (expected)",
      "ReturnData": true
    }
  ]'
```

#### 复合告警（Composite Alarm）

复合告警基于其他告警的状态组合触发，减少告警噪音：

```bash
# 创建子告警 1：高 CPU
aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu" \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# 创建子告警 2：高内存
aws cloudwatch put-metric-alarm \
  --alarm-name "high-memory" \
  --namespace "Custom/EC2" \
  --metric-name "mem_used_percent" \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold

# 创建复合告警：CPU 和内存同时过高
aws cloudwatch put-composite-alarm \
  --alarm-name "critical-resource-pressure" \
  --alarm-rule 'ALARM("high-cpu") AND ALARM("high-memory")' \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:critical-alerts
```

#### Metric Math 告警

使用 Metric Math 创建基于表达式的告警：

```bash
# 错误率告警：errors / requests * 100 > 5%
aws cloudwatch put-metric-alarm \
  --alarm-name "high-error-rate" \
  --evaluation-periods 3 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --metrics '[
    {
      "Id": "requests",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "RequestCount",
          "Dimensions": [
            {"Name": "LoadBalancer", "Value": "app/my-alb/1234567890"}
          ]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "HTTPCode_Target_5XX_Count",
          "Dimensions": [
            {"Name": "LoadBalancer", "Value": "app/my-alb/1234567890"}
          ]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "error_rate",
      "Expression": "errors / requests * 100",
      "Label": "Error Rate %",
      "ReturnData": true
    }
  ]'
```

#### 告警操作类型

| 操作类型 | 说明 | 典型用途 |
|----------|------|----------|
| SNS 通知 | 发送邮件/短信/HTTP | 通知运维人员 |
| Auto Scaling | 触发扩缩容 | CPU 高时扩容 |
| EC2 Action | 停止/终止/恢复实例 | 实例异常时重启 |
| Systems Manager | 执行 SSM 文档 | 自动化修复 |
| Lambda | 调用 Lambda 函数 | 自定义处理逻辑 |

#### treat-missing-data 参数

| 参数值 | 说明 | 适用场景 |
|--------|------|----------|
| `missing` | 保持当前状态（默认） | 一般场景 |
| `breaching` | 视为告警状态 | 关键指标缺失应告警 |
| `notBreaching` | 视为正常状态 | 指标间歇性上报 |
| `ignore` | 忽略数据点 | 维护窗口期 |

#### 告警最佳实践

```
SRE 告警设计原则：

1. 减少噪音
   - 使用 evaluation-periods 避免瞬时抖动
   - 设置 treat-missing-data 为 notBreaching（非关键指标）
   - 使用复合告警减少冗余通知

2. 分级告警
   - P0（紧急）：服务不可用，立即响应
   - P1（严重）：服务降级，30 分钟内响应
   - P2（警告）：性能下降，工作时间处理
   - P3（信息）：仅供记录，无需响应

3. 告警收敛
   - 使用告警抑制避免告警风暴
   - 设置合理的 evaluation-periods
   - 使用 ALARM -> OK 动作通知恢复

4. 通知渠道
   - SNS -> Email：低优先级
   - SNS -> SMS：高优先级
   - SNS -> PagerDuty/Opsgenie：生产告警
   - SNS -> Slack/Teams：团队协作
```

### 4. CloudWatch Logs 日志系统

#### 日志架构

```
┌──────────────────────────────────────────────────────────────┐
│                  CloudWatch Logs 架构                          │
│                                                               │
│  数据源                    收集层                 存储/分析层    │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │ EC2 实例  │───>│ CloudWatch Agent │───>│              │   │
│  └──────────┘    └──────────────────┘    │              │   │
│                                           │  Log Group   │   │
│  ┌──────────┐    ┌──────────────────┐    │  (日志组)     │   │
│  │ Lambda   │───>│ 内置集成          │───>│              │   │
│  └──────────┘    └──────────────────┘    │  Log Stream  │   │
│                                           │  (日志流)     │   │
│  ┌──────────┐    ┌──────────────────┐    │              │   │
│  │ ECS/EKS  │───>│ FireLens/Fluentd │───>│              │   │
│  └──────────┘    └──────────────────┘    │  Log Events  │   │
│                                           │  (日志事件)    │   │
│  ┌──────────┐    ┌──────────────────┐    │              │   │
│  │ VPC Flow │───>│ 内置集成          │───>│              │   │
│  │ Logs     │    └──────────────────┘    └──────┬───────┘   │
│  └──────────┘                                    │           │
│                                                  ▼           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   分析与操作                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │   │
│  │  │ Logs     │  │ Metric   │  │  Subscription     │  │   │
│  │  │ Insights │  │ Filters  │  │  Filters          │  │   │
│  │  │ (查询)    │  │ (指标)    │  │  (实时转发)        │  │   │
│  │  └──────────┘  └──────────┘  └───────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

#### 日志组与日志流管理

```bash
# 创建日志组
aws logs create-log-group \
  --log-group-name "/aws/ec2/my-app" \
  --retention-in-days 30

# 创建日志流
aws logs create-log-stream \
  --log-group-name "/aws/ec2/my-app" \
  --log-stream-name "i-1234567890abcdef0"

# 手动写入日志事件（需要 sequence token）
aws logs put-log-events \
  --log-group-name "/aws/ec2/my-app" \
  --log-stream-name "i-1234567890abcdef0" \
  --log-events '[
    {
      "timestamp": 1620000000000,
      "message": "Application started successfully"
    }
  ]'

# 查询日志（最近 1 小时）
aws logs filter-log-events \
  --log-group-name "/aws/ec2/my-app" \
  --start-time $(date -d '1 hour ago' +%s000) \
  --filter-pattern "ERROR"

# 设置保留策略
aws logs put-retention-policy \
  --log-group-name "/aws/ec2/my-app" \
  --retention-in-days 90

# 列出日志组
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/ec2"

# 删除日志组
aws logs delete-log-group \
  --log-group-name "/aws/ec2/my-app"
```

#### 日志保留策略

| 保留天数 | 适用场景 | 说明 |
|----------|----------|------|
| 1 天 | 调试日志 | 临时排查使用 |
| 7 天 | 开发环境 | 非关键环境 |
| 30 天 | 生产应用日志 | 常规保留 |
| 90 天 | 安全审计日志 | 合规要求 |
| 365 天 | 合规日志 | 长期归档（建议导出到 S3） |
| 永不删除 | 关键审计日志 | CloudTrail 等 |

#### Logs Insights 查询语言

Logs Insights 是 CloudWatch 的强大查询引擎，支持类 SQL 语法：

```sql
-- 基础查询：查找错误日志
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

-- 统计每分钟错误数
fields @timestamp, @message
| filter @message like /ERROR/
| stats count(*) as error_count by bin(1m) as time_bucket
| sort time_bucket desc

-- 分析响应时间分布
fields @timestamp, @message
| filter @message like /response_time/
| parse @message '"response_time": *' as response_time
| stats avg(response_time) as avg_rt,
        percentile(response_time, 50) as p50,
        percentile(response_time, 95) as p95,
        percentile(response_time, 99) as p99
  by bin(5m)

-- 查找慢请求
fields @timestamp, @message, @duration
| filter @type = "REPORT"
| filter @duration > 3000
| sort @duration desc
| limit 20

-- 统计不同 HTTP 状态码
fields @timestamp, @message
| parse @message '"status": *' as status_code
| stats count(*) as count by status_code
| sort count desc

-- 分析 Lambda 冷启动
fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| filter @initDuration > 0
| stats avg(@initDuration) as avg_cold_start,
        max(@initDuration) as max_cold_start,
        count(*) as cold_start_count
  by bin(1h)

-- 关联多个日志流
fields @timestamp, @message, @logStream
| filter (@logStream = "stream-1" and @message like /Request/)
  or (@logStream = "stream-2" and @message like /Response/)
| sort @timestamp asc
| limit 200
```

#### 指标过滤器（Metric Filters）

指标过滤器从日志中提取数值并创建自定义指标：

```bash
# 创建指标过滤器：统计错误日志数量
aws logs put-metric-filter \
  --log-group-name "/aws/ec2/my-app" \
  --filter-name "ErrorCount" \
  --filter-pattern "ERROR" \
  --metric-transformations '[
    {
      "metricName": "ErrorCount",
      "metricNamespace": "Custom/MyApp",
      "metricValue": "1",
      "defaultValue": 0
    }
  ]'

# 创建指标过滤器：提取数值
aws logs put-metric-filter \
  --log-group-name "/aws/ec2/my-app" \
  --filter-name "ResponseTime" \
  --filter-pattern '[time, request_id, level="INFO", msg="response_time", rt]' \
  --metric-transformations '[
    {
      "metricName": "ResponseTime",
      "metricNamespace": "Custom/MyApp",
      "metricValue": "$rt",
      "defaultValue": 0
    }
  ]'

# 创建指标过滤器：统计特定 HTTP 状态码
aws logs put-metric-filter \
  --log-group-name "/aws/api-gateway/access-logs" \
  --filter-name "5xxErrors" \
  --filter-pattern '[ip, user, timestamp, request, status_code=5*, size]' \
  --metric-transformations '[
    {
      "metricName": "5xxErrorCount",
      "metricNamespace": "Custom/APIGateway",
      "metricValue": "1",
      "defaultValue": 0
    }
  ]'
```

#### 日志订阅过滤器（Subscription Filters）

实时将日志转发到其他服务进行处理：

```bash
# 创建订阅过滤器：转发到 Lambda
aws logs put-subscription-filter \
  --log-group-name "/aws/ec2/my-app" \
  --filter-name "real-time-process" \
  --filter-pattern "ERROR" \
  --destination-arn arn:aws:lambda:us-east-1:123456789012:function:log-processor \
  --distribution "Random"

# 创建订阅过滤器：转发到 Kinesis Data Firehose（S3 存档）
aws logs put-subscription-filter \
  --log-group-name "/aws/ec2/my-app" \
  --filter-name "s3-archive" \
  --filter-pattern "" \
  --destination-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/log-archive \
  --distribution "Random"

# 创建跨账户日志转发
aws logs put-subscription-filter \
  --log-group-name "/aws/ec2/my-app" \
  --filter-name "cross-account" \
  --filter-pattern "" \
  --destination-arn arn:aws:logs:us-east-1:999999999999:destination:central-logs \
  --distribution "Random"
```

### 5. 自定义指标（Custom Metrics）

#### 使用 AWS CLI 发布自定义指标

```bash
# 发布单个数据点
aws cloudwatch put-metric-data \
  --namespace "Custom/MyApp" \
  --metric-name "OrderProcessingTime" \
  --dimensions Environment=production,Service=order-service \
  --unit Milliseconds \
  --value 245

# 发布多个数据点
aws cloudwatch put-metric-data \
  --namespace "Custom/MyApp" \
  --metric-data '[
    {
      "MetricName": "ActiveUsers",
      "Dimensions": [
        {
          "Name": "Environment",
          "Value": "production"
        }
      ],
      "Value": 1500,
      "Unit": "Count",
      "Timestamp": "2026-05-03T10:00:00Z"
    },
    {
      "MetricName": "QueueDepth",
      "Dimensions": [
        {
          "Name": "QueueName",
          "Value": "order-processing"
        }
      ],
      "Value": 42,
      "Unit": "Count"
    }
  ]'

# 发布高分辨率指标（1 秒粒度）
aws cloudwatch put-metric-data \
  --namespace "Custom/MyApp" \
  --metric-name "RequestLatency" \
  --storage-resolution 1 \
  --unit Milliseconds \
  --value 15
```

#### 使用 SDK 发布自定义指标（Python）

```python
import boto3
from datetime import datetime, timezone

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def publish_custom_metric(metric_name, value, unit='Count', dimensions=None):
    """发布自定义指标到 CloudWatch"""
    metric_data = {
        'MetricName': metric_name,
        'Value': value,
        'Unit': unit,
        'Timestamp': datetime.now(timezone.utc)
    }

    if dimensions:
        metric_data['Dimensions'] = [
            {'Name': k, 'Value': v} for k, v in dimensions.items()
        ]

    cloudwatch.put_metric_data(
        Namespace='Custom/MyApp',
        MetricData=[metric_data]
    )

# 使用示例
publish_custom_metric('ActiveConnections', 150, 'Count',
                      {'Environment': 'production', 'Region': 'us-east-1'})
```

#### EMF（Embedded Metric Format）

EMF 允许在日志中嵌入指标数据，无需单独调用 PutMetricData API：

```json
{
  "_aws": {
    "Timestamp": 1620000000000,
    "CloudWatchMetrics": [
      {
        "Namespace": "Custom/MyApp",
        "Dimensions": [["Environment", "Service"]],
        "Metrics": [
          {
            "Name": "ProcessingTime",
            "Unit": "Milliseconds"
          },
          {
            "Name": "OrderCount",
            "Unit": "Count"
          }
        ]
      }
    ]
  },
  "Environment": "production",
  "Service": "order-service",
  "ProcessingTime": 245,
  "OrderCount": 1,
  "OrderId": "ORD-12345"
}
```

### 6. CloudWatch Dashboard

#### 创建仪表盘

```bash
# 创建仪表盘
aws cloudwatch put-dashboard \
  --dashboard-name "SRE-Production-Overview" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "title": "EC2 CPU Utilization",
          "metrics": [
            ["AWS/EC2", "CPUUtilization", "InstanceId", "i-1234567890abcdef0", {"label": "Web-Server-1"}],
            ["AWS/EC2", "CPUUtilization", "InstanceId", "i-0987654321fedcba0", {"label": "Web-Server-2"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "view": "timeSeries",
          "stacked": false,
          "annotations": {
            "horizontal": [
              {
                "label": "Critical",
                "value": 80,
                "color": "#d62728"
              }
            ]
          }
        }
      },
      {
        "type": "metric",
        "x": 12,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "title": "ALB Request Count & Response Time",
          "metrics": [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/my-alb/1234567890", {"stat": "Sum", "yAxis": "left"}],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/my-alb/1234567890", {"stat": "p99", "yAxis": "right"}]
          ],
          "period": 60,
          "region": "us-east-1",
          "view": "timeSeries"
        }
      },
      {
        "type": "log",
        "x": 0,
        "y": 6,
        "width": 24,
        "height": 6,
        "properties": {
          "title": "Error Log Analysis",
          "query": "SOURCE \"/aws/ec2/my-app\" | fields @timestamp, @message | filter @message like /ERROR/ | stats count(*) by bin(5m)",
          "region": "us-east-1",
          "stacked": false,
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "x": 0,
        "y": 12,
        "width": 8,
        "height": 6,
        "properties": {
          "title": "RDS Connections",
          "metrics": [
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", "my-db", {"stat": "Average"}]
          ],
          "period": 300,
          "region": "us-east-1",
          "view": "gauge",
          "annotations": {
            "horizontal": [
              {"label": "Warning", "value": 80, "color": "#ff7f0e"},
              {"label": "Critical", "value": 100, "color": "#d62728"}
            ]
          }
        }
      }
    ]
  }'
```

#### 仪表盘最佳实践

```
SRE 仪表盘设计原则：

1. 分层设计
   Level 1: 全局概览（服务健康度、SLI/SLO）
   Level 2: 服务级别（延迟、错误率、流量、饱和度）
   Level 3: 实例级别（单个节点详细指标）
   Level 4: 调试面板（日志、追踪、事件）

2. USE 方法（适用于基础设施）
   - Utilization：CPU、内存、磁盘使用率
   - Saturation：队列深度、等待数
   - Errors：错误率、失败请求

3. RED 方法（适用于服务）
   - Rate：请求速率
   - Errors：错误率
   - Duration：请求延迟

4. 黄金指标（Google SRE）
   - Latency：延迟
   - Traffic：流量
   - Errors：错误
   - Saturation：饱和度
```

### 7. EventBridge 事件驱动架构

#### EventBridge 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    EventBridge 架构                            │
│                                                               │
│  事件源                      事件总线               事件目标    │
│  ┌──────────┐    ┌───────────────────────┐    ┌──────────┐  │
│  │ AWS 服务  │───>│                       │───>│ Lambda   │  │
│  │ (EC2,RDS) │    │                       │    └──────────┘  │
│  └──────────┘    │                       │    ┌──────────┐  │
│  ┌──────────┐    │   Event Bus           │───>│ SQS      │  │
│  │ 自定义应用 │───>│   (事件总线)           │    └──────────┘  │
│  └──────────┘    │                       │    ┌──────────┐  │
│  ┌──────────┐    │   - 默认总线            │───>│ SNS      │  │
│  │ SaaS 应用 │───>│   - 自定义总线          │    └──────────┘  │
│  │ (Zendesk) │    │   - 合作伙伴总线        │    ┌──────────┐  │
│  └──────────┘    │                       │───>│ Step Func │  │
│                  │   ┌───────────────┐   │    └──────────┘  │
│                  │   │  Rules        │   │    ┌──────────┐  │
│                  │   │  (规则匹配)    │   │───>│ ECS Task │  │
│                  │   └───────────────┘   │    └──────────┘  │
│                  └───────────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

#### EventBridge 规则配置

```bash
# 创建自定义事件总线
aws events create-event-bus \
  --name "my-app-events"

# 创建规则：EC2 实例状态变更通知
aws events put-rule \
  --name "ec2-state-change" \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["EC2 Instance State-change Notification"],
    "detail": {
      "state": ["stopped", "terminated"]
    }
  }' \
  --state ENABLED \
  --description "Notify when EC2 instances stop or terminate"

# 添加 SNS 目标
aws events put-targets \
  --rule "ec2-state-change" \
  --targets "Id"="sns-notification","Arn"="arn:aws:sns:us-east-1:123456789012:ops-alerts"

# 创建规则：自定义应用事件
aws events put-rule \
  --name "order-events" \
  --event-pattern '{
    "source": ["my-app.order-service"],
    "detail-type": ["Order Created", "Order Completed", "Order Failed"],
    "detail": {
      "orderType": ["premium", "enterprise"]
    }
  }' \
  --state ENABLED

# 创建定时规则（cron 表达式）
aws events put-rule \
  --name "daily-report" \
  --schedule-expression "cron(0 8 * * ? *)" \
  --state ENABLED

# 创建定时规则（rate 表达式）
aws events put-rule \
  --name "health-check" \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED

# 发送自定义事件
aws events put-events \
  --entries '[
    {
      "Source": "my-app.order-service",
      "DetailType": "Order Created",
      "Detail": "{\"orderId\":\"ORD-12345\",\"amount\":99.99,\"orderType\":\"premium\"}",
      "EventBusName": "my-app-events"
    }
  ]'
```

#### EventBridge vs SNS 对比

| 特性 | EventBridge | SNS |
|------|------------|-----|
| 消息路由 | 基于规则过滤 | 基于订阅 |
| 消息格式 | 结构化 JSON 事件 | 原始消息 |
| 目标服务 | 15+ AWS 服务 | 主要 Lambda/SQS/HTTP |
| 消息转换 | 支持输入转换器 | 不支持 |
| 事件回放 | 不支持 | 不支持 |
| Schema Registry | 支持 | 不支持 |
| 适用场景 | 事件驱动架构 | 通知/消息推送 |

### 8. X-Ray 分布式追踪

#### X-Ray 架构

```
┌────────────────────────────────────────────────────────────────┐
│                    X-Ray 分布式追踪                              │
│                                                                 │
│  客户端请求流程：                                                 │
│                                                                 │
│  Client ──> API Gateway ──> Lambda ──> DynamoDB                 │
│    │           │              │           │                     │
│    ▼           ▼              ▼           ▼                     │
│  Segment 1  Segment 2    Segment 3    Segment 4                │
│  (前端)     (网关)        (函数)        (数据库)                   │
│                                                                 │
│  通过 Trace ID 串联所有 Segment：                                │
│                                                                 │
│  Trace ID: 1-5f4dcc3b-5aae-6d10-b7a2-d17398b5c1e0             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Segment 1 (API Gateway)                                  │   │
│  │ ├─ Subsegment: Request Validation                        │   │
│  │ ├─ Subsegment: Authentication                            │   │
│  │ └─ Subsegment: Route to Backend                          │   │
│  │     └─────────────────────────────────────────────────┐  │   │
│  │     │ Segment 2 (Lambda)                               │  │   │
│  │     │ ├─ Subsegment: Business Logic                    │  │   │
│  │     │ ├─ Subsegment: Database Query                    │  │   │
│  │     │ │   └─────────────────────────────────────────┐ │  │   │
│  │     │ │   │ Segment 3 (DynamoDB)                     │ │  │   │
│  │     │ │   │ ├─ Subsegment: GetItem                  │ │  │   │
│  │     │ │   │ └─ Subsegment: PutItem                  │ │  │   │
│  │     │ │   └─────────────────────────────────────────┘ │  │   │
│  │     │ └─ Subsegment: Response Formatting               │  │   │
│  │     └─────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

#### X-Ray SDK 集成（Python）

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from flask import Flask

app = Flask(__name__)

# 配置 X-Ray
xray_recorder.configure(
    service='my-api-service',
    context_missing='LOG_ERROR',
    sampling_rules={
        "version": 2,
        "rules": [
            {
                "description": "Sample all requests",
                "host": "*",
                "http_method": "*",
                "url_path": "*",
                "fixed_target": 1,
                "rate": 0.1
            }
        ],
        "default": {
            "fixed_target": 1,
            "rate": 0.05
        }
    }
)

# 添加中间件
XRayMiddleware(app, xray_recorder)

@app.route('/api/orders')
def get_orders():
    # 手动创建子段
    subsegment = xray_recorder.begin_subsegment('fetch_orders')
    try:
        orders = database.query('SELECT * FROM orders')
        subsegment.put_metadata('order_count', len(orders))
        return {'orders': orders}
    except Exception as e:
        subsegment.add_exception(e)
        raise
    finally:
        xray_recorder.end_subsegment()

# 注解（Annotation）- 可用于搜索和过滤
subsegment.put_annotation('customer_type', 'premium')

# 元数据（Metadata）- 详细的调试信息
subsegment.put_metadata('request', {'body': request.json}, 'input')
```

#### X-Ray 采样策略

| 场景 | 采样策略 | 说明 |
|------|----------|------|
| 健康检查 | 0% 采样 | 无追踪价值 |
| 正常请求 | 5-10% 采样 | 控制成本 |
| 错误请求 | 100% 采样 | 完整追踪 |
| 关键业务 | 50-100% 采样 | 全面分析 |
| 调试模式 | 100% 采样 | 临时开启 |

### 9. CloudTrail 审计日志

#### CloudTrail 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    CloudTrail 架构                            │
│                                                               │
│  API 调用来源：                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Console  │  │   CLI    │  │   SDK    │  │  服务     │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └─────────────┴─────────────┴─────────────┘            │
│                            │                                  │
│                    ┌───────▼───────┐                          │
│                    │  CloudTrail   │                          │
│                    │  (API 记录)    │                          │
│                    └───────┬───────┘                          │
│            ┌───────────────┼───────────────┐                  │
│            ▼               ▼               ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  S3 Bucket   │  │  CloudWatch  │  │  EventBridge │       │
│  │  (长期存储)    │  │  Logs        │  │  (实时处理)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  记录内容：                                                     │
│  - 谁（userIdentity）                                        │
│  - 做了什么（eventName）                                      │
│  - 什么时候（eventTime）                                      │
│  - 从哪里（sourceIPAddress）                                  │
│  - 结果如何（errorCode）                                      │
└──────────────────────────────────────────────────────────────┘
```

#### CloudTrail 配置

```bash
# 创建 Trail
aws cloudtrail create-trail \
  --name "management-trail" \
  --s3-bucket-name "my-cloudtrail-logs-123456789012" \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --is-organization-trail

# 启用日志记录
aws cloudtrail start-logging \
  --name "management-trail"

# 查看 Trail 状态
aws cloudtrail get-trail-status \
  --name "management-trail"

# 查询最近的 API 调用
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --start-time 2026-05-03T00:00:00Z \
  --end-time 2026-05-03T23:59:59Z \
  --max-results 10

# 创建 S3 数据事件记录
aws cloudtrail put-event-selectors \
  --trail-name "management-trail" \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::my-sensitive-bucket/"]
        }
      ]
    }
  ]'
```

#### Management Events vs Data Events

| 特性 | Management Events | Data Events |
|------|-------------------|-------------|
| 默认开启 | 是 | 否 |
| 记录内容 | 控制平面操作 | 数据平面操作 |
| 示例 | 创建 EC2、修改 IAM | S3 对象读写、Lambda 调用 |
| 费用 | 免费 | 按事件数量收费 |
| CloudTrail Insights | 支持 | 不支持 |

### 10. 可观测性三大支柱整合

```
┌──────────────────────────────────────────────────────────────┐
│              可观测性三大支柱（Three Pillars）                   │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Metrics   │  │    Logs     │  │   Traces    │          │
│  │   指标       │  │   日志       │  │   追踪       │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ CloudWatch  │  │ CloudWatch  │  │   X-Ray     │          │
│  │ Metrics     │  │ Logs        │  │             │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│                ┌──────────────────┐                          │
│                │  统一分析平台     │                          │
│                │  CloudWatch      │                          │
│                │  ServiceLens     │                          │
│                └──────────────────┘                          │
│                                                               │
│  指标告诉你 "什么出了问题"                                     │
│  日志告诉你 "为什么出了问题"                                    │
│  追踪告诉你 "问题在哪里出了"                                    │
└──────────────────────────────────────────────────────────────┘
```

### 11. SRE 实战案例：构建生产级监控体系

#### 场景：电商系统监控架构

```
生产环境监控需求：
- 3 个微服务：API Gateway、Order Service、Payment Service
- 2 个数据库：RDS MySQL、DynamoDB
- 1 个消息队列：SQS
- 目标：99.9% 可用性，P99 延迟 < 500ms

监控架构：

┌─────────────────────────────────────────────────────────────┐
│                    电商系统监控架构                            │
│                                                              │
│  应用层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ API Gateway ──> Order Service ──> Payment Service   │    │
│  │     │                │                  │            │    │
│  │     ▼                ▼                  ▼            │    │
│  │   X-Ray            X-Ray              X-Ray         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  指标层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ CloudWatch Metrics                                   │    │
│  │ - API GW: 5xxRate, Latency, RequestCount            │    │
│  │ - Order:  ErrorRate, ProcessingTime, QueueDepth     │    │
│  │ - Payment: SuccessRate, Latency, TransactionCount   │    │
│  │ - RDS:    CPU, Connections, ReadLatency             │    │
│  │ - SQS:    ApproximateAge, NumberOfMessagesSent      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  告警层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - P0: 5xx > 5% 持续 2 分钟 → PagerDuty + SMS        │    │
│  │ - P1: P99 > 500ms 持续 5 分钟 → Slack + Email        │    │
│  │ - P2: Error Rate > 1% 持续 10 分钟 → Slack           │    │
│  │ - P3: Queue Depth > 1000 持续 5 分钟 → Slack         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

#### 故障排查链路

```
故障排查流程示例：

1. 告警触发：P0-API-5xx-Rate 告警
   → 收到 PagerDuty 通知

2. 查看 Dashboard L1：全局概览
   → 发现 Order Service 的 5xx 错误率突增

3. 查看 Dashboard L2：Order Service 详情
   → P99 延迟从 200ms 上升到 2000ms
   → 错误率从 0.1% 上升到 15%

4. 查看 X-Ray 追踪
   → 发现 Payment Service 调用超时
   → 根因：Payment Service 的 DynamoDB 表读取延迟异常

5. 查看 CloudWatch Logs
   → 搜索 Payment Service 错误日志
   → 发现 "ProvisionedThroughputExceededException"

6. 根因分析
   → DynamoDB 表的读容量单位（RCU）不足
   → 促销活动导致流量激增

7. 修复操作
   → 临时：DynamoDB 开启 On-Demand 模式
   → 长期：配置 Auto Scaling 策略

8. 验证恢复
   → 5xx 错误率恢复到 0.1% 以下
   → P99 延迟恢复到 200ms
```

---

## 💻 实战练习

### 练习 1：基础操作 — CloudWatch 指标与告警

**目标**：创建自定义指标、配置告警、验证告警触发

```bash
# 步骤 1：创建自定义命名空间和指标
aws cloudwatch put-metric-data \
  --namespace "SRE-Lab/App" \
  --metric-name "RequestCount" \
  --dimensions Environment=lab,Service=web \
  --unit Count \
  --value 100

# 步骤 2：验证指标已创建
aws cloudwatch list-metrics \
  --namespace "SRE-Lab/App" \
  --metric-name "RequestCount"

# 步骤 3：创建告警
aws cloudwatch put-metric-alarm \
  --alarm-name "lab-high-request-count" \
  --namespace "SRE-Lab/App" \
  --metric-name "RequestCount" \
  --dimensions Environment=lab,Service=web \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching

# 步骤 4：发送测试数据触发告警
for i in $(seq 1 10); do
  aws cloudwatch put-metric-data \
    --namespace "SRE-Lab/App" \
    --metric-name "RequestCount" \
    --dimensions Environment=lab,Service=web \
    --unit Count \
    --value $(( RANDOM % 200 + 400 ))
  sleep 1
done

# 步骤 5：检查告警状态
aws cloudwatch describe-alarms \
  --alarm-names "lab-high-request-count" \
  --query 'MetricAlarms[0].StateValue'

# 清理
aws cloudwatch delete-alarms --alarm-names "lab-high-request-count"
```

### 练习 2：进阶场景 — CloudWatch Logs Insights 分析

**目标**：使用 Logs Insights 分析应用日志，提取关键指标

```bash
# 步骤 1：创建日志组和日志流
aws logs create-log-group --log-group-name "/lab/app-logs"
aws logs create-log-stream \
  --log-group-name "/lab/app-logs" \
  --log-stream-name "app-instance-1"

# 步骤 2：创建指标过滤器
aws logs put-metric-filter \
  --log-group-name "/lab/app-logs" \
  --filter-name "500-errors" \
  --filter-pattern '"status":500' \
  --metric-transformations '[
    {
      "metricName": "Error500Count",
      "metricNamespace": "SRE-Lab/Logs",
      "metricValue": "1",
      "defaultValue": 0
    }
  ]'

# 步骤 3：使用 Logs Insights 查询（等待几分钟后）
QUERY_ID=$(aws logs start-query \
  --log-group-name "/lab/app-logs" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20' \
  --query 'queryId' --output text)

# 步骤 4：获取查询结果
aws logs get-query-results --query-id "$QUERY_ID"

# 清理
aws logs delete-log-group --log-group-name "/lab/app-logs"
```

### 练习 3：故障排查挑战 — 定位性能瓶颈

**场景**：你的 Web 应用突然出现大量 5xx 错误，使用 CloudWatch 工具链定位问题

```bash
# 模拟故障场景：创建指标

# 1. 创建模拟指标（5xx 错误率飙升）
for hour in 0 1 2 3; do
  for min in 0 15 30 45; do
    TIMESTAMP="2026-05-03T$(printf '%02d' $hour):$(printf '%02d' $min):00Z"
    ERROR_COUNT=$(( hour > 1 ? (RANDOM % 50 + 100) : (RANDOM % 5 + 1) ))
    aws cloudwatch put-metric-data \
      --namespace "SRE-Lab/Troubleshoot" \
      --metric-name "HTTP5xxErrors" \
      --timestamp "$TIMESTAMP" \
      --unit Count \
      --value $ERROR_COUNT 2>/dev/null
  done
done

# 2. 查询指标数据
aws cloudwatch get-metric-statistics \
  --namespace "SRE-Lab/Troubleshoot" \
  --metric-name "HTTP5xxErrors" \
  --start-time 2026-05-03T00:00:00Z \
  --end-time 2026-05-03T04:00:00Z \
  --period 3600 \
  --statistics Sum

# 3. 创建告警
aws cloudwatch put-metric-alarm \
  --alarm-name "troubleshoot-5xx" \
  --namespace "SRE-Lab/Troubleshoot" \
  --metric-name "HTTP5xxErrors" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold

# 4. 检查告警状态
aws cloudwatch describe-alarms \
  --alarm-names "troubleshoot-5xx" \
  --query 'MetricAlarms[0].[StateValue,StateReason]'

# 挑战：编写一个脚本自动分析错误率上升的时间点和趋势

# 清理
aws cloudwatch delete-alarms --alarm-names "troubleshoot-5xx"
```

---

## 🎯 面试题精选

### Q1: CloudWatch 基础监控和详细监控有什么区别？

**答案**：
- **基础监控**（Basic Monitoring）：免费，每 5 分钟采集一次指标，适用于一般监控场景
- **详细监控**（Detailed Monitoring）：收费（约 $3/实例/月），每 1 分钟采集一次指标，适用于需要快速响应的场景（如自动伸缩、实时告警）
- 决策依据：如果使用 Auto Scaling 策略需要基于 CPU 等指标快速扩缩容，应启用详细监控

### Q2: 如何设计一个减少告警噪音的告警策略？

**答案**：
1. 使用 `evaluation-periods` 避免瞬时抖动（如设置连续 3 个周期才触发）
2. 使用复合告警（Composite Alarm）组合多个条件，减少单独告警
3. 设置 `treat-missing-data` 为 `notBreaching` 避免数据缺失时误报
4. 使用异常检测（Anomaly Detection）替代静态阈值，自动适应流量模式
5. 告警分级：P0（紧急）→ P1（严重）→ P2（警告）→ P3（信息）
6. 使用告警抑制：当 P0 告警触发时，抑制相关的 P1/P2 告警

### Q3: CloudWatch Logs Insights 和 Metric Filters 有什么区别？

**答案**：
| 特性 | Logs Insights | Metric Filters |
|------|---------------|----------------|
| 用途 | 实时查询和分析日志 | 从日志中提取数值创建指标 |
| 查询语言 | 类 SQL 语法 | 模式匹配语法 |
| 输出 | 日志记录 | CloudWatch 指标 |
| 适用场景 | 故障排查、日志分析 | 监控告警、趋势分析 |
| 费用 | 按扫描数据量收费 | 按指标数据点收费 |

### Q4: X-Ray 采样策略如何设计？

**答案**：
- **固定目标（Fixed Target）**：每秒固定采集的请求数（如 1 req/s），确保低流量时也有追踪数据
- **采样率（Rate）**：超出固定目标后的采样比例（如 10%），高流量时控制成本
- **最佳实践**：健康检查 0%、正常请求 5-10%、错误请求 100%、关键业务 50-100%

### Q5: CloudTrail 的 Management Events 和 Data Events 有什么区别？

**答案**：
- **Management Events**：默认开启，记录控制平面操作（如创建 EC2、修改安全组），免费
- **Data Events**：默认不开启，记录数据平面操作（如 S3 对象读写、Lambda 调用），按事件数量收费
- **CloudTrail Insights**：可选功能，自动检测异常 API 调用模式，额外收费

### Q6: 如何使用 CloudWatch 构建 SLI/SLO 监控？

**答案**：
使用 Metric Math 创建可用性指标：
```
availability = (RequestCount - 5xxCount) / RequestCount * 100
```
当 availability < 99.9% 时触发告警，配合 evaluation-periods = 4（如 5 分钟周期则为 20 分钟）避免瞬时波动。

### Q7: EventBridge 和 SNS 的区别是什么？

**答案**：
- EventBridge 基于规则过滤，支持结构化事件、输入转换、Schema Registry
- SNS 基于订阅，主要用于消息推送和通知
- EventBridge 适合事件驱动架构，SNS 适合简单的通知场景

### Q8: 如何在多账户环境中集中管理 CloudWatch 日志？

**答案**：
1. 使用订阅过滤器将日志转发到中心账户的 Kinesis Data Firehose
2. Firehose 将日志存入中心账户的 S3
3. 在中心账户使用 Athena 查询跨账户日志
4. 或使用 CloudWatch Logs 的跨账户日志共享功能（通过 Resource Policy）

---

## 📚 深入阅读

- [CloudWatch 官方文档](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [CloudWatch Logs Insights 查询语法](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [X-Ray 开发者指南](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [EventBridge 用户指南](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
- [CloudTrail 用户指南](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
- [AWS 可观测性最佳实践](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Effective_Alarming.html)

---

## ✅ 自检清单

- [ ] 能够解释 CloudWatch 指标的命名空间、维度、周期、统计类型
- [ ] 能够配置静态阈值告警、异常检测告警、复合告警
- [ ] 能够使用 Logs Insights 编写查询语句分析日志
- [ ] 能够创建指标过滤器从日志中提取指标
- [ ] 能够使用 AWS CLI 和 SDK 发布自定义指标
- [ ] 能够设计生产级 CloudWatch Dashboard
- [ ] 能够配置 EventBridge 规则实现事件驱动架构
- [ ] 能够集成 X-Ray 实现分布式追踪
- [ ] 能够配置 CloudTrail 进行安全审计
- [ ] 能够设计完整的可观测性体系（Metrics + Logs + Traces）
- [ ] 能够根据告警进行完整的故障排查链路
