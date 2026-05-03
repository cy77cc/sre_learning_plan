# Day 118: AWS SAA 认证刷题

> 📅 日期：2026-05-03
> 📖 学习主题：AWS SAA-C03 认证实战刷题 — 50 道场景题、考试策略、时间管理、常见陷阱
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 117 (AWS SAA 认证知识点梳理)

## 🎯 学习目标

1. 通过 50 道场景题巩固 SAA-C03 核心知识点
2. 掌握考试答题策略和时间管理技巧
3. 识别常见考试陷阱和易错点
4. 建立薄弱知识点识别和强化机制
5. 为 SAA 认证考试做好充分准备

---

## 📖 核心知识点

### 1. 考试策略与时间管理

```
┌──────────────────────────────────────────────────────────────┐
│                    SAA-C03 考试策略                            │
│                                                               │
│  时间分配：                                                    │
│  ├── 总时间：130 分钟                                         │
│  ├── 题目数量：65 题                                          │
│  ├── 每题平均：2 分钟                                         │
│  └── 检查时间：10-15 分钟                                     │
│                                                               │
│  答题策略：                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  第一轮（60-70 分钟）                                 │    │
│  │  ├── 快速回答所有题目                                 │    │
│  │  ├── 不确定的题目标记                                 │    │
│  │  └── 每题不超过 1.5 分钟                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  第二轮（40-50 分钟）                                 │    │
│  │  ├── 回顾标记的题目                                   │    │
│  │  ├── 深入分析不确定的选项                             │    │
│  │  └── 每题 2-3 分钟                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  第三轮（10-15 分钟）                                 │    │
│  │  ├── 检查所有答案                                     │    │
│  │  ├── 确保没有漏答                                     │    │
│  │  └── 最终确认                                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  评分规则：                                                    │
│  ├── 及格分数：720 / 1000（约 72%）                          │
│  ├── 单选题：1 分                                            │
│  ├── 多选题：2 分（全对才得分）                               │
│  └── 无倒扣分                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 2. 常见考试陷阱

```
┌──────────────────────────────────────────────────────────────┐
│                    常见考试陷阱                                 │
│                                                               │
│  陷阱 1：关键词误解                                           │
│  ├── "最便宜" → 不一定是最便宜的服务，而是最合适的方案       │
│  ├── "最简单" → 通常指托管服务或无服务器方案                 │
│  ├── "最安全" → 通常指加密、IAM、VPC 等安全特性             │
│  └── "最可靠" → 通常指 Multi-AZ、自动故障转移               │
│                                                               │
│  陷阱 2：服务混淆                                             │
│  ├── SQS vs SNS → 消息队列 vs 发布/订阅                     │
│  ├── ALB vs NLB → Layer 7 vs Layer 4                        │
│  ├── RDS vs Aurora → 标准数据库 vs AWS 自研                 │
│  ├── S3 vs EBS → 对象存储 vs 块存储                         │
│  └── Lambda vs Fargate → 函数计算 vs 容器计算               │
│                                                               │
│  陷阱 3：场景理解                                             │
│  ├── "实时" → 通常需要 Kinesis 或 DynamoDB Streams          │
│  ├── "批处理" → 通常可以使用 Spot Instance                  │
│  ├── "全球" → 通常需要 CloudFront 或多区域部署              │
│  └── "高可用" → 通常需要 Multi-AZ 或多区域                  │
│                                                               │
│  陷阱 4：成本计算                                             │
│  ├── 数据传输费用 → 出站收费，入站免费                       │
│  ├── NAT Gateway → 按小时 + 数据处理量收费                  │
│  ├── ALB → 按小时 + LCU 收费                                │
│  └── S3 请求费用 → PUT, GET, LIST 等操作收费                │
│                                                               │
│  陷阱 5：安全合规                                             │
│  ├── "加密" → 通常指 KMS 或 SSE                             │
│  ├── "审计" → 通常指 CloudTrail 或 Config                   │
│  ├── "合规" → 通常指 AWS Artifact 或 Security Hub           │
│  └── "访问控制" → 通常指 IAM 或 SCP                         │
└──────────────────────────────────────────────────────────────┘
```

### 3. 薄弱知识点识别

```
┌──────────────────────────────────────────────────────────────┐
│                    薄弱知识点识别                               │
│                                                               │
│  领域 1：设计弹性架构（30%）                                  │
│  ├── 高可用设计模式                                          │
│  │   ├── Multi-AZ vs Multi-Region                           │
│  │   ├── ALB 故障转移机制                                    │
│  │   └── Route 53 路由策略                                   │
│  ├── 解耦机制                                                │
│  │   ├── SQS 消息生命周期                                   │
│  │   ├── SNS 订阅协议                                       │
│  │   └── EventBridge 规则                                    │
│  └── 灾难恢复                                                │
│      ├── 四种模式对比                                        │
│      ├── RTO/RPO 计算                                        │
│      └── Aurora Global Database                              │
│                                                               │
│  领域 2：设计高性能架构（28%）                                │
│  ├── 存储选择                                                │
│  │   ├── S3 存储类别                                        │
│  │   ├── EBS 卷类型                                         │
│  │   └── EFS vs FSx                                         │
│  ├── 数据库选择                                              │
│  │   ├── RDS vs DynamoDB vs Redshift                        │
│  │   ├── Aurora 特性                                        │
│  │   └── 缓存策略                                           │
│  └── 网络优化                                                │
│      ├── CloudFront 缓存                                     │
│      ├── VPC Endpoint                                        │
│      └── Global Accelerator                                   │
│                                                               │
│  领域 3：设计安全应用程序（24%）                              │
│  ├── IAM 策略                                                │
│  │   ├── 策略评估逻辑                                       │
│  │   ├── SCP vs IAM Policy                                  │
│  │   └── 权限边界                                           │
│  ├── 数据加密                                                │
│  │   ├── SSE-S3 vs SSE-KMS vs SSE-C                        │
│  │   ├── 传输中加密                                         │
│  │   └── 客户端加密                                         │
│  └── 网络安全                                                │
│      ├── Security Group vs NACL                              │
│      ├── WAF 规则                                           │
│      └── Shield 防护                                         │
│                                                               │
│  领域 4：设计成本优化架构（18%）                              │
│  ├── 计算成本                                                │
│  │   ├── On-Demand vs Reserved vs Spot                      │
│  │   ├── Savings Plans                                       │
│  │   └── Right Sizing                                        │
│  ├── 存储成本                                                │
│  │   ├── S3 生命周期策略                                    │
│  │   ├── EBS 快照管理                                       │
│  │   └── Glacier 检索选项                                    │
│  └── 网络成本                                                │
│      ├── 数据传输费用                                       │
│      ├── NAT Gateway 成本                                    │
│      └── CloudFront 定价                                     │
└──────────────────────────────────────────────────────────────┘
```

### 4. 50 道场景题

#### 题目 1-10：弹性架构设计

**Q1**: 一个 Web 应用部署在单个 AZ 的 EC2 实例上，最近经历了一次 AZ 级别故障导致服务中断 4 小时。公司要求 RTO < 5 分钟。应该选择哪种架构？

A. 在同一 AZ 增加更多 EC2 实例
B. 使用 Auto Scaling Group 跨多个 AZ 部署
C. 使用 Route 53 故障转移到另一个区域
D. 使用 EC2 Auto Recovery

**答案**：B
**解析**：跨多个 AZ 部署 ASG 可以在单 AZ 故障时自动将流量路由到其他 AZ 的实例。RTO 取决于健康检查间隔和 ASG 扩缩速度，通常 < 5 分钟。A 选项仍在同一 AZ，C 选项过于复杂且成本高，D 选项只适用于硬件故障而非 AZ 故障。

---

**Q2**: 一个电商网站在促销期间流量增加 20 倍，促销结束后流量恢复正常。数据库查询响应时间从 10ms 增加到 500ms。最有效的优化方案是什么？

A. 增加 RDS 实例大小
B. 添加 ElastiCache Redis 缓存
C. 使用 DynamoDB 替代 RDS
D. 增加 RDS 读副本数量

**答案**：B
**解析**：ElastiCache Redis 可以缓存频繁查询的结果，将响应时间从 500ms 降低到 < 10ms。这是最常见的数据库性能优化方案。A 选项成本高且效果有限，C 选项需要重构应用，D 选项只适用于读密集型负载。

---

**Q3**: 一个应用需要处理用户上传的图片，包括缩放、裁剪和添加水印。处理时间约为 30 秒，用户可以等待处理结果。应该使用什么架构？

A. 同步 Lambda 函数处理
B. API Gateway + Lambda + SQS
C. S3 事件通知 + Lambda + S3
D. EC2 实例直接处理

**答案**：C
**解析**：S3 事件通知可以自动触发 Lambda 函数处理上传的图片。处理结果可以存储回 S3。这是无服务器文件处理的标准架构。A 选项 Lambda 超时限制 15 分钟但 30 秒是可行的，但不如 C 选项优雅。B 选项引入了不必要的 SQS，D 选项需要管理服务器。

---

**Q4**: 一个金融应用需要处理交易订单，要求消息严格按顺序处理，且不能有重复消息。应该使用什么？

A. SQS Standard
B. SQS FIFO
C. SNS
D. Kinesis Data Streams

**答案**：B
**解析**：SQS FIFO 保证消息严格按顺序处理（First-In-First-Out），并支持消息去重（基于 MessageDeduplicationId）。这是金融交易场景的标准选择。A 选项不保证顺序，C 选项是推送模式，D 选项适用于实时流处理。

---

**Q5**: 一个应用需要将数据从 us-east-1 复制到 eu-west-1，RPO < 1 秒。数据库是 MySQL。应该选择什么？

A. RDS Read Replicas（跨区域）
B. Aurora Global Database
C. DynamoDB Global Tables
D. S3 跨区域复制

**答案**：B
**解析**：Aurora Global Database 提供跨区域复制（< 1 秒延迟），并支持快速故障转移。这是 MySQL 兼容数据库跨区域复制的最佳选择。A 选项是异步复制，延迟较高。C 选项适用于 NoSQL，D 选项适用于文件存储。

---

**Q6**: 一个应用需要在 VPC 中访问 S3，但不能通过公网。VPC 有 100 个 EC2 实例同时访问 S3。最经济的方案是什么？

A. NAT Gateway
B. NAT Instance
C. VPC Gateway Endpoint
D. VPC Interface Endpoint

**答案**：C
**解析**：S3 Gateway Endpoint 免费且提供私有访问，无需通过公网。这是 VPC 中访问 S3 的标准方案。A 选项按小时和数据处理量收费，B 选项需要管理实例，D 选项按小时和数据传输收费。

---

**Q7**: 一个应用需要将日志数据实时发送到多个消费者（S3、Elasticsearch、Lambda）。应该使用什么架构？

A. 应用直接发送到每个消费者
B. SQS + 多个消费者轮询
C. SNS + SQS 扇出模式
D. Kinesis Data Streams + 多个消费者

**答案**：D
**解析**：Kinesis Data Streams 支持多个消费者同时读取数据流，适用于实时日志处理。C 选项也适用于扇出，但 Kinesis 更适合实时流处理。A 选项耦合度高，B 选项不是实时的。

---

**Q8**: 一个 Web 应用需要根据用户的地理位置返回不同的内容（例如，美国用户看到英文，中国用户看到中文）。应该使用什么？

A. Route 53 地理位置路由
B. CloudFront 地理限制
C. ALB 基于头部路由
D. Lambda@Edge

**答案**：D
**解析**：Lambda@Edge 可以在 CloudFront 边缘位置根据用户地理位置修改请求/响应。A 选项只路由到不同区域，B 选项只允许/拒绝访问，C 选项基于 HTTP 头部而非地理位置。

---

**Q9**: 一个应用需要存储用户会话数据，支持分布式锁，并且需要持久化。应该使用什么？

A. DynamoDB
B. ElastiCache Redis
C. ElastiCache Memcached
D. S3

**答案**：B
**解析**：ElastiCache Redis 支持分布式锁（SETNX）、持久化（RDB + AOF）和丰富的数据结构。这是分布式会话管理的标准选择。A 选项也可以但延迟较高，C 选项不支持持久化和分布式锁，D 选项不适合会话数据。

---

**Q10**: 一个应用需要将数据库从本地迁移到 AWS，最小化停机时间。数据库是 Oracle。应该使用什么？

A. AWS DMS（Database Migration Service）
B. AWS SCT（Schema Conversion Tool）
C. 直接导入导出
D. S3 + Lambda

**答案**：A
**解析**：AWS DMS 支持持续复制（CDC），可以在迁移过程中保持源数据库运行，最小化停机时间。B 选项只转换 schema，C 选项需要停机，D 选项不适用于数据库迁移。

---

#### 题目 11-20：高性能架构设计

**Q11**: 一个应用需要处理每秒 10 万次数据库读取请求，读取延迟 < 5ms。数据库是 DynamoDB。最有效的方案是什么？

A. 增加 DynamoDB 预配置容量
B. 使用 DynamoDB DAX
C. 使用 ElastiCache Redis
D. 使用 RDS + Read Replicas

**答案**：B
**解析**：DynamoDB DAX 提供微秒级读取延迟，可以处理每秒数百万次请求。这是 DynamoDB 读取性能优化的标准方案。A 选项延迟较高（毫秒级），C 选项需要修改应用代码，D 选项不是 DynamoDB。

---

**Q12**: 一个 Lambda 函数需要处理 S3 上传的文件，文件大小为 100MB-1GB。处理时间约为 5 分钟。应该使用什么架构？

A. 同步 Lambda 函数
B. S3 事件通知 + Lambda 异步调用
C. S3 事件通知 + SQS + Lambda
D. S3 事件通知 + SNS + Lambda

**答案**：C
**解析**：SQS 可以缓冲 S3 事件，Lambda 从 SQS 消费消息处理文件。这提供了更好的错误处理和重试机制。A 选项可能超时，B 选项异步调用但错误处理有限，D 选项 SNS 不提供持久化。

---

**Q13**: 一个应用需要将 JSON 数据转换为 Parquet 格式并存储在 S3 中，数据量为每天 1TB。应该使用什么？

A. Lambda
B. AWS Glue
C. EMR
D. Athena

**答案**：B
**解析**：AWS Glue 是 ETL 服务，可以自动转换数据格式（JSON → Parquet）。它支持自动扩缩容，适合批量数据处理。A 选项有执行时间限制，C 选项过于复杂，D 选项是查询服务而非 ETL。

---

**Q14**: 一个应用需要在 VPC 中运行 Lambda 函数，访问 RDS 数据库和 S3 存储桶。Lambda 函数每秒被调用 100 次。如何优化网络性能？

A. 将 Lambda 部署在公有子网
B. 将 Lambda 部署在私有子网 + NAT Gateway
C. 将 Lambda 部署在私有子网 + VPC Endpoint
D. 不将 Lambda 部署在 VPC 中

**答案**：C
**解析**：VPC Endpoint 可以提供私有访问 S3 和其他 AWS 服务，无需通过 NAT Gateway。这减少了延迟和成本。A 选项不安全，B 选项 NAT Gateway 有成本和性能限制，D 选项无法访问 RDS。

---

**Q15**: 一个应用需要处理实时视频流（每秒 1GB 数据），并进行实时分析。应该使用什么？

A. Kinesis Data Streams
B. Kinesis Data Firehose
C. Kinesis Video Streams
D. S3 + Lambda

**答案**：C
**解析**：Kinesis Video Streams 专门用于处理视频流数据。A 选项适用于数据流，B 选项适用于数据加载，D 选项不是实时处理。

---

**Q16**: 一个应用需要将数据库查询结果缓存 10 分钟，缓存命中率 > 90%。数据库查询模式是读多写少。应该使用什么缓存策略？

A. Write Through
B. Lazy Loading + TTL
C. Write Behind
D. Read Through

**答案**：B
**解析**：Lazy Loading（按需加载）+ TTL（过期时间）是最常见的缓存策略。当缓存未命中时从数据库加载，TTL 确保缓存数据不会过期太久。A 选项写入时更新缓存，C 选项异步写入数据库，D 选项类似于 Lazy Loading。

---

**Q17**: 一个应用需要将文件从 S3 下载到 EC2 实例，文件大小为 10GB。网络带宽为 1Gbps。最优化的下载方案是什么？

A. 使用 S3 Transfer Acceleration
B. 使用 VPC Endpoint
C. 使用 S3 Select
D. 使用 multipart download

**答案**：D
**解析**：Multipart download 可以并行下载文件的不同部分，充分利用网络带宽。A 选项适用于远距离上传，B 选项适用于私有访问，C 选项适用于查询部分数据。

---

**Q18**: 一个应用需要处理 DynamoDB 表的变更事件，并将变更发送到 Elasticsearch 进行全文搜索。应该使用什么架构？

A. DynamoDB Streams + Lambda + Elasticsearch
B. DynamoDB 直接查询 Elasticsearch
C. CloudWatch Events + Lambda + Elasticsearch
D. SNS + Lambda + Elasticsearch

**答案**：A
**解析**：DynamoDB Streams 捕获表的变更事件，Lambda 处理变更并发送到 Elasticsearch。这是 DynamoDB 与 Elasticsearch 集成的标准架构。B 选项 DynamoDB 不直接支持 Elasticsearch，C 选项 CloudWatch Events 不能捕获 DynamoDB 变更，D 选项 SNS 不提供持久化。

---

**Q19**: 一个应用需要将数据库从 MySQL 迁移到 PostgreSQL，同时保持应用兼容性。应该使用什么？

A. AWS DMS
B. AWS SCT + DMS
C. 直接导入导出
D. Aurora MySQL

**答案**：B
**解析**：AWS SCT（Schema Conversion Tool）可以转换数据库 schema（MySQL → PostgreSQL），AWS DMS 迁移数据。这是异构数据库迁移的标准流程。A 选项只迁移数据不转换 schema，C 选项需要停机，D 选项不是 PostgreSQL。

---

**Q20**: 一个应用需要将 Lambda 函数的冷启动时间从 5 秒降低到 < 1 秒。Lambda 使用 Java 运行时。最有效的方案是什么？

A. 增加 Lambda 内存
B. 使用 Provisioned Concurrency
C. 使用 SnapStart
D. 使用 Lambda@Edge

**答案**：C
**解析**：SnapStart 是 Java Lambda 的优化功能，可以显著减少冷启动时间（从秒级到毫秒级）。A 选项有一定效果但不显著，B 选项需要预付费，D 选项适用于边缘计算。

---

#### 题目 21-30：安全架构设计

**Q21**: 一个应用需要限制 IAM 用户只能在 us-east-1 区域创建 EC2 实例。应该使用什么？

A. SCP
B. IAM 条件键
C. VPC 限制
D. Resource Policy

**答案**：B
**解析**：IAM 条件键 `aws:RequestedRegion` 可以限制用户只能在特定区域操作。A 选项用于组织级别限制，C 选项限制网络，D 选项用于资源级别控制。

---

**Q22**: 一个应用需要加密 S3 中的敏感数据，并支持审计谁在什么时间访问了数据。应该使用什么？

A. SSE-S3
B. SSE-KMS
C. SSE-C
D. 客户端加密

**答案**：B
**解析**：SSE-KMS 使用 KMS 管理的密钥加密数据，支持 CloudTrail 审计密钥使用。A 选项不支持审计，C 选项需要客户提供密钥，D 选项需要客户端实现。

---

**Q23**: 一个应用需要跨账户访问 S3 存储桶，且不能共享长期凭证。应该使用什么？

A. S3 ACL
B. S3 Bucket Policy
C. IAM 角色和 AssumeRole
D. S3 Access Points

**答案**：C
**解析**：IAM 角色和 AssumeRole 是跨账户访问的标准方法，使用临时凭证（15 分钟 - 12 小时）。B 选项也可以但不如角色灵活，A 选项已弃用，D 选项适用于复杂的访问控制。

---

**Q24**: 一个应用需要将日志存储 7 年以满足合规要求，且日志量为每天 100GB。最经济的存储方案是什么？

A. CloudWatch Logs（永不过期）
B. CloudWatch Logs + S3 Standard
C. CloudWatch Logs + S3 Glacier Deep Archive
D. CloudWatch Logs + EBS

**答案**：C
**解析**：S3 Glacier Deep Archive 提供最低的存储成本（$0.00099/GB/月），适合长期归档。7 年日志量约为 255TB，使用 Glacier Deep Archive 可以显著降低成本。A 选项成本高，B 选项 S3 Standard 成本高，D 选项 EBS 不适合日志存储。

---

**Q25**: 一个应用需要监控 EC2 实例的内存使用率和磁盘使用率。应该使用什么？

A. CloudWatch 基础监控
B. CloudWatch 详细监控
C. CloudWatch Agent
D. EC2 Instance Metadata

**答案**：C
**解析**：CloudWatch Agent 可以收集自定义指标（内存、磁盘、进程等）。CloudWatch 基础监控和详细监控只收集 CPU、网络等标准指标。A 和 B 选项不收集内存和磁盘指标，D 选项只提供实例元数据。

---

**Q26**: 一个应用需要限制 S3 存储桶只能从特定 VPC 访问。应该使用什么？

A. S3 ACL
B. S3 Bucket Policy + VPC Endpoint
C. S3 CORS
D. S3 Access Points

**答案**：B
**解析**：S3 Bucket Policy 可以限制只有特定 VPC Endpoint 才能访问 S3 存储桶。这是 VPC 级别的 S3 访问控制。A 选项已弃用，C 选项用于跨域访问，D 选项适用于复杂的访问控制。

---

**Q27**: 一个应用需要将 IAM 策略的最大权限限制为 S3 和 EC2，即使用户被授予更多权限。应该使用什么？

A. SCP
B. IAM 权限边界
C. IAM 条件键
D. Resource Policy

**答案**：B
**解析**：IAM 权限边界（Permission Boundary）可以限制 IAM 用户或角色的最大权限。即使用户被授予更多权限，权限边界也会限制实际生效的权限。A 选项用于组织级别限制，C 选项用于条件限制，D 选项用于资源级别控制。

---

**Q28**: 一个应用需要将 CloudTrail 日志发送到另一个账户的 S3 存储桶进行集中审计。应该使用什么？

A. CloudTrail 跨账户日志记录
B. S3 跨区域复制
C. Lambda 函数复制日志
D. CloudWatch Logs 跨账户

**答案**：A
**解析**：CloudTrail 支持跨账户日志记录，可以将日志发送到另一个账户的 S3 存储桶。这是集中审计的标准方案。B 选项用于跨区域复制，C 选项需要自定义实现，D 选项 CloudWatch Logs 不直接支持跨账户。

---

**Q29**: 一个应用需要保护 Web 应用免受 SQL 注入和 XSS 攻击。应该使用什么？

A. Security Group
B. NACL
C. WAF
D. Shield

**答案**：C
**解析**：WAF（Web Application Firewall）可以检测和阻止 SQL 注入、XSS 等 Web 攻击。A 和 B 选项是网络层防护，D 选项是 DDoS 防护。

---

**Q30**: 一个应用需要确保 EC2 实例只能访问特定的 S3 存储桶。应该使用什么？

A. S3 Bucket Policy
B. IAM Instance Profile
C. Security Group
D. NACL

**答案**：B
**解析**：IAM Instance Profile 可以为 EC2 实例分配 IAM 角色，限制实例可以访问的 AWS 资源。A 选项也可以但需要配合 IAM 角色，C 和 D 选项是网络层防护。

---

#### 题目 31-40：成本优化设计

**Q31**: 一个应用运行在 m5.xlarge 实例上，CPU 利用率平均为 20%。最有效的成本优化方案是什么？

A. 使用 Reserved Instances
B. 使用 Spot Instances
C. Right Sizing 到 m5.large
D. 使用 Savings Plans

**答案**：C
**解析**：Right Sizing 是最直接的成本优化方案。CPU 利用率 20% 表示实例过大，可以降级到 m5.large（一半成本）。A 选项只降低单价不降低资源浪费，B 选项可能被中断，D 选项只降低单价。

---

**Q32**: 一个批处理作业需要运行 2 小时，可以在任何时间运行，且可以中断。最经济的 EC2 购买选项是什么？

A. On-Demand Instances
B. Reserved Instances
C. Spot Instances
D. Savings Plans

**答案**：C
**解析**：Spot Instances 可以节省高达 90%，适合可中断的批处理作业。A 选项成本最高，B 选项需要长期承诺，D 选项需要长期承诺。

---

**Q33**: 一个应用需要存储 10TB 的日志数据，每月访问 1-2 次，数据保留 3 年。最经济的存储方案是什么？

A. S3 Standard
B. S3 Standard-IA
C. S3 Glacier Flexible Retrieval
D. S3 Glacier Deep Archive

**答案**：D
**解析**：S3 Glacier Deep Archive 提供最低的存储成本（$0.00099/GB/月），适合很少访问的长期数据。3 年存储成本约为 $356，而 S3 Standard 约为 $2,765。A 和 B 选项成本高，C 选项成本中等。

---

**Q34**: 一个应用需要将 NAT Gateway 的数据传输成本降低 50%。最有效的方案是什么？

A. 使用 NAT Instance 替代
B. 使用 VPC Endpoint
C. 压缩数据
D. 减少出站流量

**答案**：B
**解析**：VPC Endpoint 可以避免通过 NAT Gateway 访问 AWS 服务（如 S3、DynamoDB），从而降低数据传输成本。A 选项需要管理实例，C 和 D 选项效果有限。

---

**Q35**: 一个应用需要将 S3 存储成本降低 30%，数据访问模式是：30 天内频繁访问，30-90 天偶尔访问，90 天后很少访问。应该使用什么策略？

A. S3 Intelligent-Tiering
B. S3 生命周期策略
C. S3 Standard-IA
D. S3 Glacier

**答案**：B
**解析**：S3 生命周期策略可以根据数据年龄自动转换存储类别。30 天后 → S3 Standard-IA，90 天后 → S3 Glacier Flexible Retrieval。A 选项自动分层但成本略高，C 和 D 选项只适用于特定类别。

---

**Q36**: 一个应用需要将 EC2 实例的成本降低 40%，且实例运行时间 > 1 年。最经济的方案是什么？

A. On-Demand Instances
B. Reserved Instances（1 年，全预付）
C. Spot Instances
D. Savings Plans（1 年）

**答案**：B
**解析**：Reserved Instances（1 年，全预付）可以节省约 40%。A 选项无折扣，C 选项可能被中断，D 选项折扣略低（约 30%）。

---

**Q37**: 一个应用需要将数据库查询结果缓存，但缓存数据可能过期。最经济的缓存方案是什么？

A. ElastiCache Redis
B. ElastiCache Memcached
C. DynamoDB DAX
D. CloudFront

**答案**：B
**解析**：ElastiCache Memcached 是最经济的缓存方案，适合简单的键值缓存。A 选项功能更丰富但成本更高，C 选项是 DynamoDB 专用缓存，D 选项是 CDN。

---

**Q38**: 一个应用需要将 Lambda 函数的执行成本降低 50%。最有效的方案是什么？

A. 增加 Lambda 内存
B. 减少 Lambda 内存
C. 使用 Provisioned Concurrency
D. 优化代码减少执行时间

**答案**：D
**解析**：Lambda 按执行时间计费（GB-秒），优化代码减少执行时间可以直接降低成本。A 选项增加成本，B 选项可能增加执行时间，C 选项需要预付费。

---

**Q39**: 一个应用需要将数据从 us-east-1 传输到 eu-west-1，数据量为 1TB/月。最经济的传输方案是什么？

A. 公网传输
B. S3 Transfer Acceleration
C. AWS Direct Connect
D. VPC Peering

**答案**：C
**解析**：AWS Direct Connect 提供专线连接，数据传输成本低于公网传输。A 选项成本最高，B 选项适用于上传加速，D 选项不支持跨区域。

---

**Q40**: 一个应用需要将 CloudWatch 日志存储 1 年，日志量为 100GB/月。最经济的存储方案是什么？

A. CloudWatch Logs（永不过期）
B. CloudWatch Logs + S3 Standard
C. CloudWatch Logs + S3 Glacier Deep Archive
D. CloudWatch Logs + EBS

**答案**：C
**解析**：S3 Glacier Deep Archive 提供最低的存储成本，适合长期归档。1 年日志量约为 1.2TB，使用 Glacier Deep Archive 可以显著降低成本。A 选项成本高，B 选项 S3 Standard 成本高，D 选项 EBS 不适合日志存储。

---

#### 题目 41-50：综合场景题

**Q41**: 一个电商网站需要设计一个全球部署的架构，用户分布在美国、欧洲和亚洲。要求：
- 静态资源加载时间 < 2 秒
- API 响应时间 < 200ms
- 数据库 RPO < 1 秒
- 99.99% 可用性

应该选择什么架构？

A. 单区域部署 + CloudFront
B. 多区域部署 + Route 53 地理位置路由
C. 多区域部署 + Aurora Global Database
D. 多区域部署 + DynamoDB Global Tables

**答案**：C
**解析**：Aurora Global Database 提供跨区域复制（< 1 秒 RPO）和快速故障转移。结合 CloudFront 和 Route 53 地理位置路由，可以满足全球部署需求。A 选项单区域不满足全球延迟需求，B 选项没有数据库复制，D 选项适用于 NoSQL 场景。

---

**Q42**: 一个金融应用需要处理每秒 1 万笔交易，要求：
- 交易顺序保证
- 不能有重复交易
- 交易持久化
- 审计追踪

应该使用什么架构？

A. SQS Standard + Lambda
B. SQS FIFO + Lambda
C. Kinesis Data Streams + Lambda
D. DynamoDB Streams + Lambda

**答案**：B
**解析**：SQS FIFO 保证消息顺序和去重，Lambda 处理交易并持久化到数据库。CloudTrail 提供审计追踪。A 选项不保证顺序，C 选项不保证去重，D 选项适用于 DynamoDB 变更事件。

---

**Q43**: 一个应用需要将本地数据中心的数据库迁移到 AWS，要求：
- 最小化停机时间
- 支持持续复制
- 数据库是 PostgreSQL

应该使用什么？

A. AWS DMS
B. AWS SCT + DMS
C. 直接导入导出
D. S3 + Lambda

**答案**：A
**解析**：AWS DMS 支持持续复制（CDC），可以在迁移过程中保持源数据库运行，最小化停机时间。B 选项用于异构迁移，C 选项需要停机，D 选项不适用于数据库迁移。

---

**Q44**: 一个应用需要设计一个无服务器架构，要求：
- API 响应时间 < 100ms
- 自动扩缩容
- 按需付费
- 支持 WebSocket

应该使用什么架构？

A. API Gateway + Lambda + DynamoDB
B. ALB + ECS Fargate + RDS
C. API Gateway + Lambda + ElastiCache
D. CloudFront + S3 + Lambda

**答案**：A
**解析**：API Gateway 支持 WebSocket，Lambda 提供无服务器计算，DynamoDB 提供按需付费的数据库。B 选项不是完全无服务器，C 选项 ElastiCache 需要管理实例，D 选项不支持 WebSocket。

---

**Q45**: 一个应用需要将日志数据实时分析并可视化，要求：
- 日志量：1GB/小时
- 分析延迟 < 5 分钟
- 支持 SQL 查询
- 可视化仪表盘

应该使用什么架构？

A. CloudWatch Logs + Logs Insights
B. S3 + Athena + QuickSight
C. Kinesis Data Firehose + S3 + Athena + QuickSight
D. Elasticsearch + Kibana

**答案**：C
**解析**：Kinesis Data Firehose 可以实时加载日志到 S3，Athena 提供 SQL 查询，QuickSight 提供可视化。A 选项 Logs Insights 延迟较高，B 选项不是实时加载，D 选项需要管理集群。

---

**Q46**: 一个应用需要设计一个高可用架构，要求：
- 99.99% 可用性
- RTO < 1 分钟
- RPO < 5 分钟
- 数据库是 MySQL

应该使用什么架构？

A. 单区域 + RDS Multi-AZ
B. 多区域 + RDS Read Replicas
C. 单区域 + Aurora Multi-AZ
D. 多区域 + Aurora Global Database

**答案**：D
**解析**：Aurora Global Database 提供跨区域复制（< 1 秒 RPO）和快速故障转移（< 1 分钟 RTO）。A 和 C 选项单区域不满足区域级灾难恢复，B 选项 RPO 较高。

---

**Q47**: 一个应用需要将文件从 S3 下载到 EC2 实例，文件大小为 100MB-10GB，下载频率为每秒 100 次。最优化的下载方案是什么？

A. 使用 S3 Transfer Acceleration
B. 使用 VPC Endpoint
C. 使用 S3 Select
D. 使用 multipart download + VPC Endpoint

**答案**：D
**解析**：Multipart download 可以并行下载文件的不同部分，VPC Endpoint 提供私有访问。这是 S3 下载性能优化的标准方案。A 选项适用于远距离上传，B 选项只提供私有访问，C 选项适用于查询部分数据。

---

**Q48**: 一个应用需要将 DynamoDB 表的变更事件发送到多个消费者（Lambda、SQS、SNS）。应该使用什么架构？

A. DynamoDB Streams + Lambda
B. DynamoDB Streams + EventBridge + 多个目标
C. DynamoDB 直接调用多个目标
D. CloudWatch Events + Lambda

**答案**：B
**解析**：DynamoDB Streams 捕获变更事件，EventBridge 可以将事件路由到多个目标（Lambda、SQS、SNS 等）。A 选项只有一个消费者，C 选项 DynamoDB 不直接支持，D 选项 CloudWatch Events 不能捕获 DynamoDB 变更。

---

**Q49**: 一个应用需要设计一个安全架构，要求：
- 数据加密（静态和传输中）
- 访问控制（最小权限）
- 审计追踪
- 合规性（PCI DSS）

应该使用什么服务组合？

A. KMS + IAM + CloudTrail + Config
B. S3 加密 + Security Group + VPC Flow Logs
C. WAF + Shield + GuardDuty
D. Secrets Manager + IAM + CloudTrail

**答案**：A
**解析**：KMS 提供数据加密，IAM 提供访问控制，CloudTrail 提供审计追踪，Config 提供合规检查。这是 PCI DSS 合规的标准服务组合。B 选项缺少审计和合规，C 选项缺少加密和访问控制，D 选项缺少合规检查。

---

**Q50**: 一个应用需要设计一个成本优化架构，要求：
- 计算成本降低 50%
- 存储成本降低 30%
- 网络成本降低 20%
- 不影响性能和可用性

最有效的综合方案是什么？

A. 使用 Spot Instances + S3 生命周期策略 + VPC Endpoint
B. 使用 Reserved Instances + S3 Standard + NAT Gateway
C. 使用 Savings Plans + S3 Intelligent-Tiering + CloudFront
D. 使用 On-Demand + S3 Glacier + Direct Connect

**答案**：A
**解析**：Spot Instances 可以节省高达 90%（计算成本），S3 生命周期策略可以自动转换存储类别（存储成本），VPC Endpoint 可以避免 NAT Gateway 数据传输费（网络成本）。B 选项 S3 Standard 成本高，C 选项折扣较低，D 选项 Glacier 检索成本高。

---

## 💻 实战练习

### 练习 1：基础操作 — 模拟考试环境

**目标**：在 130 分钟内完成 65 道模拟题

```bash
# 步骤 1：创建模拟考试环境
# 使用 AWS 官方练习题或第三方题库
# 推荐资源：
# - AWS Official Practice Exam
# - Tutorials Dojo
# - Whizlabs
# - A Cloud Guru

# 步骤 2：时间管理
# 每题平均 2 分钟
# 第一轮：60-70 分钟（快速回答）
# 第二轮：40-50 分钟（回顾标记题）
# 第三轮：10-15 分钟（最终检查）

# 步骤 3：记录错题
cat > exam_notes.md << 'EOF'
# SAA-C03 模拟考试记录

## 考试信息
- 日期：2026-05-03
- 题目数量：65 题
- 考试时间：130 分钟
- 得分：XX/1000

## 错题分析
### 领域 1：设计弹性架构
- Q1: 错误原因 - 未考虑 AZ 故障场景
- Q5: 错误原因 - 混淆 RDS Read Replicas 和 Aurora Global Database

### 领域 2：设计高性能架构
- Q12: 错误原因 - 未考虑 Lambda 超时限制
- Q18: 错误原因 - 混淆 DynamoDB Streams 和 CloudWatch Events

### 领域 3：设计安全应用程序
- Q22: 错误原因 - 未考虑审计需求
- Q27: 错误原因 - 混淆 SCP 和权限边界

### 领域 4：设计成本优化架构
- Q31: 错误原因 - 未考虑 Right Sizing
- Q40: 错误原因 - 未考虑长期存储成本

## 薄弱知识点
1. Aurora Global Database 特性
2. DynamoDB Streams 和 EventBridge 集成
3. IAM 权限边界和 SCP 区别
4. S3 存储类别成本计算

## 改进计划
1. 复习 Aurora Global Database 文档
2. 练习 DynamoDB Streams 和 EventBridge 集成场景
3. 深入理解 IAM 权限边界和 SCP
4. 计算不同 S3 存储类别的成本
EOF

echo "模拟考试完成，请查看 exam_notes.md 分析错题"
```

### 练习 2：进阶场景 — 薄弱知识点强化

**目标**：针对薄弱知识点进行专项练习

```bash
# 步骤 1：识别薄弱知识点
# 根据模拟考试结果，识别薄弱领域

# 步骤 2：专项练习 - Aurora Global Database
echo "=== Aurora Global Database 专项练习 ==="
echo "Q1: Aurora Global Database 的 RPO 是多少？"
echo "A: < 1 秒"
echo ""
echo "Q2: Aurora Global Database 支持多少个区域？"
echo "A: 最多 5 个辅助区域"
echo ""
echo "Q3: Aurora Global Database 的故障转移时间是多少？"
echo "A: < 1 分钟"

# 步骤 3：专项练习 - DynamoDB Streams
echo ""
echo "=== DynamoDB Streams 专项练习 ==="
echo "Q1: DynamoDB Streams 保证什么顺序？"
echo "A: 分区内的顺序"
echo ""
echo "Q2: DynamoDB Streams 可以触发什么服务？"
echo "A: Lambda"
echo ""
echo "Q3: DynamoDB Streams 和 EventBridge 有什么区别？"
echo "A: Streams 是 DynamoDB 专用，EventBridge 是通用事件总线"

# 步骤 4：专项练习 - IAM 权限边界
echo ""
echo "=== IAM 权限边界专项练习 ==="
echo "Q1: IAM 权限边界的作用是什么？"
echo "A: 限制 IAM 用户或角色的最大权限"
echo ""
echo "Q2: IAM 权限边界和 SCP 有什么区别？"
echo "A: 权限边界用于用户/角色，SCP 用于组织"
echo ""
echo "Q3: 如何创建 IAM 权限边界？"
echo "A: 创建 IAM 策略并附加为权限边界"

# 步骤 5：专项练习 - S3 存储类别成本
echo ""
echo "=== S3 存储类别成本专项练习 ==="
echo "Q1: S3 Standard 的存储成本是多少？"
echo "A: $0.023/GB/月（前 50TB）"
echo ""
echo "Q2: S3 Glacier Deep Archive 的存储成本是多少？"
echo "A: $0.00099/GB/月"
echo ""
echo "Q3: 如何计算 10TB 数据存储 3 年的成本？"
echo "A: 10TB * 1024GB * $0.00099/GB/月 * 36 月 = $356"

echo ""
echo "薄弱知识点强化完成！"
```

### 练习 3：故障排查挑战 — 考试策略优化

**场景**：优化考试策略，提高答题效率

```bash
# 步骤 1：分析答题时间分布
cat > time_analysis.md << 'EOF'
# 答题时间分析

## 时间分布
- 领域 1（20 题）：35 分钟（平均 1.75 分钟/题）
- 领域 2（18 题）：40 分钟（平均 2.22 分钟/题）
- 领域 3（16 题）：30 分钟（平均 1.88 分钟/题）
- 领域 4（11 题）：25 分钟（平均 2.27 分钟/题）
- 总计：130 分钟

## 问题分析
1. 领域 2 和领域 4 答题时间较长
2. 领域 2 涉及计算题（成本计算、性能优化）
3. 领域 4 涉及成本计算（存储、计算、网络）

## 优化策略
1. 领域 2：提前准备计算公式
2. 领域 4：提前计算常见存储成本
3. 标记题：第一轮标记不确定题，第二轮深入分析
4. 检查题：最后 10 分钟检查所有答案
EOF

# 步骤 2：准备计算公式
cat > formulas.md << 'EOF'
# SAA-C03 计算公式

## 成本计算
### S3 存储成本
- S3 Standard: $0.023/GB/月（前 50TB）
- S3 Standard-IA: $0.0125/GB/月
- S3 Glacier Deep Archive: $0.00099/GB/月

### EC2 成本
- On-Demand: 按小时计费
- Reserved: 1 年全预付节省 40%，3 年全预付节省 60%
- Spot: 按需价格的 10-90%

### 数据传输成本
- 入站：免费
- 同区域出站：免费（S3 到 EC2）
- 跨区域出站：$0.02/GB
- 公网出站：$0.09/GB（前 10TB）

## 性能计算
### RTO/RPO
- RTO: 恢复时间目标
- RPO: 恢复点目标
- Multi-AZ: RTO < 1 分钟，RPO = 0
- Aurora Global: RTO < 1 分钟，RPO < 1 秒

### 吞吐量
- SQS Standard: 无限制
- SQS FIFO: 300 条/秒（批处理 3000）
- Kinesis: 每个分片 1MB/秒写入，2MB/秒读取

## 安全计算
### IAM 策略评估
- 显式 Deny > 显式 Allow > 隐式 Deny

### 加密选项
- SSE-S3: 免费，无审计
- SSE-KMS: 收费，支持审计
- SSE-C: 免费，客户提供密钥
EOF

# 步骤 3：模拟考试练习
echo "=== 模拟考试练习 ==="
echo "规则："
echo "1. 130 分钟完成 65 题"
echo "2. 每题平均 2 分钟"
echo "3. 标记不确定题"
echo "4. 最后 10 分钟检查"
echo ""
echo "开始计时..."

# 步骤 4：答题策略
cat > exam_strategy.md << 'EOF'
# 考试策略

## 第一轮（60-70 分钟）
1. 快速阅读题目和选项
2. 识别关键词（最便宜、最简单、最安全、最可靠）
3. 排除明显错误选项
4. 选择最佳答案
5. 标记不确定题

## 第二轮（40-50 分钟）
1. 回顾标记题
2. 深入分析每个选项
3. 使用排除法
4. 选择最佳答案

## 第三轮（10-15 分钟）
1. 检查所有答案
2. 确保没有漏答
3. 最终确认

## 常见陷阱
1. 关键词误解
2. 服务混淆
3. 场景理解
4. 成本计算
5. 安全合规
EOF

echo "考试策略准备完成！"
echo "请查看 time_analysis.md, formulas.md, exam_strategy.md"
```

---

## 🎯 面试题精选

### Q1: 如何准备 SAA-C03 考试？

**参考答案**：
SAA-C03 考试准备建议：
1. **学习路径**：
   - 完成 AWS 官方培训课程
   - 阅读 AWS 白皮书和文档
   - 使用模拟考试练习

2. **重点复习**：
   - 领域 1（30%）：弹性架构设计
   - 领域 2（28%）：高性能架构设计
   - 领域 3（24%）：安全架构设计
   - 领域 4（18%）：成本优化设计

3. **练习资源**：
   - AWS Official Practice Exam
   - Tutorials Dojo
   - Whizlabs
   - A Cloud Guru

4. **考试策略**：
   - 时间管理（每题 2 分钟）
   - 标记不确定题
   - 排除法
   - 关键词识别

### Q2: SAA-C03 和 SAP-C02 有什么区别？

**参考答案**：
- **SAA-C03（Solutions Architect Associate）**：
  - 难度：中级
  - 题目数量：65 题
  - 考试时间：130 分钟
  - 及格分数：720/1000
  - 有效期：3 年
  - 适用人群：解决方案架构师

- **SAP-C02（Solutions Architect Professional）**：
  - 难度：高级
  - 题目数量：75 题
  - 考试时间：180 分钟
  - 及格分数：750/1000
  - 有效期：3 年
  - 适用人群：高级解决方案架构师

建议：先通过 SAA-C03，再准备 SAP-C02。

### Q3: 如何识别考试中的关键词？

**参考答案**：
考试中的关键词及其含义：
1. **"最便宜"** → 最经济的方案，不一定是最低价
2. **"最简单"** → 托管服务或无服务器方案
3. **"最安全"** → 加密、IAM、VPC 等安全特性
4. **"最可靠"** → Multi-AZ、自动故障转移
5. **"实时"** → Kinesis、DynamoDB Streams
6. **"批处理"** → Spot Instance、Lambda
7. **"全球"** → CloudFront、多区域部署
8. **"高可用"** → Multi-AZ、多区域

### Q4: 如何处理考试中的计算题？

**参考答案**：
考试中的计算题类型：
1. **成本计算**：
   - S3 存储成本（存储类别、数据量、时间）
   - EC2 实例成本（购买选项、使用时间）
   - 数据传输成本（方向、数据量）

2. **性能计算**：
   - RTO/RPO（灾难恢复模式）
   - 吞吐量（SQS、Kinesis）
   - 延迟（CloudFront、VPC Endpoint）

3. **安全计算**：
   - IAM 策略评估（Deny > Allow）
   - 加密选项（SSE-S3 vs SSE-KMS）

准备建议：
- 提前计算常见存储成本
- 熟悉 RTO/RPO 概念
- 理解 IAM 策略评估逻辑

### Q5: 如何处理考试中的不确定题？

**参考答案**：
处理不确定题的策略：
1. **标记题目**：第一轮标记不确定题
2. **排除法**：排除明显错误选项
3. **关键词分析**：识别题目中的关键词
4. **场景分析**：理解题目场景和需求
5. **最佳实践**：选择 AWS 推荐的最佳实践
6. **最后检查**：最后 10 分钟检查所有答案

注意事项：
- 不要花费太多时间在单题上
- 使用排除法缩小选择范围
- 选择最符合 AWS 最佳实践的选项
- 不要留空（无倒扣分）

### Q6: 如何准备考试中的安全相关题目？

**参考答案**：
安全相关题目准备：
1. **IAM 策略**：
   - 策略评估逻辑（Deny > Allow）
   - SCP vs IAM Policy
   - 权限边界

2. **数据加密**：
   - SSE-S3 vs SSE-KMS vs SSE-C
   - 传输中加密（TLS）
   - 客户端加密

3. **网络安全**：
   - Security Group vs NACL
   - VPC Endpoint
   - WAF 规则

4. **审计和合规**：
   - CloudTrail 审计日志
   - Config 合规检查
   - Security Hub 安全中心

### Q7: 如何准备考试中的成本优化题目？

**参考答案**：
成本优化题目准备：
1. **计算成本**：
   - On-Demand vs Reserved vs Spot
   - Savings Plans
   - Right Sizing

2. **存储成本**：
   - S3 存储类别和生命周期策略
   - EBS 快照管理
   - Glacier 检索选项

3. **网络成本**：
   - 数据传输费用
   - NAT Gateway 成本
   - CloudFront 定价

4. **数据库成本**：
   - RDS vs Aurora vs DynamoDB
   - ElastiCache 缓存策略
   - 读写分离

### Q8: 如何处理考试中的多选题？

**参考答案**：
多选题处理策略：
1. **理解题目要求**：确定需要选择几个选项
2. **分析每个选项**：判断每个选项是否正确
3. **排除明显错误**：排除明显错误的选项
4. **选择最佳组合**：选择最符合题目要求的组合

注意事项：
- 多选题全对才得分
- 不要多选或少选
- 使用排除法缩小范围
- 选择最符合 AWS 最佳实践的组合

### Q9: 如何处理考试中的长题目？

**参考答案**：
长题目处理策略：
1. **快速浏览**：快速浏览题目和选项
2. **识别关键信息**：识别关键需求和约束
3. **排除无关信息**：忽略无关的背景信息
4. **分析选项**：分析每个选项是否满足需求
5. **选择最佳答案**：选择最符合需求的选项

关键信息：
- 需求：高可用、高性能、安全、成本
- 约束：RTO、RPO、合规、预算
- 技术：数据库、存储、计算、网络

### Q10: 如何在考试中管理时间？

**参考答案**：
时间管理策略：
1. **时间分配**：
   - 第一轮：60-70 分钟（快速回答）
   - 第二轮：40-50 分钟（回顾标记题）
   - 第三轮：10-15 分钟（最终检查）

2. **答题速度**：
   - 每题平均 2 分钟
   - 简单题 < 1 分钟
   - 复难题 2-3 分钟

3. **标记策略**：
   - 标记不确定题
   - 标记需要计算的题
   - 标记需要深入分析的题

4. **检查策略**：
   - 最后 10 分钟检查所有答案
   - 确保没有漏答
   - 最终确认

---

## 📚 延伸阅读

- [AWS SAA-C03 考试指南](https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Exam-Guide.pdf)
- [AWS 官方练习题](https://aws.amazon.com/certification/certified-solutions-architect-associate/)
- [Tutorials Dojo SAA-C03 练习题](https://tutorialsdojo.com/aws-certified-solutions-architect-associate-saa-c03/)
- [Whizlabs SAA-C03 练习题](https://www.whizlabs.com/aws-solutions-architect-associate/)
- [A Cloud Guru SAA-C03 课程](https://acloudguru.com/course/aws-certified-solutions-architect-associate-saa-c03)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)

---

## ✅ 今日自检清单

- [ ] 能够在 130 分钟内完成 65 道模拟题
- [ ] 掌握考试答题策略和时间管理技巧
- [ ] 能够识别常见考试陷阱和易错点
- [ ] 能够完成 50 道场景题并理解解析
- [ ] 能够识别薄弱知识点并进行专项练习
- [ ] 掌握成本计算公式和方法
- [ ] 理解 RTO/RPO 概念和计算
- [ ] 掌握 IAM 策略评估逻辑
- [ ] 能够处理考试中的多选题和长题目
- [ ] 能够在考试中管理时间
