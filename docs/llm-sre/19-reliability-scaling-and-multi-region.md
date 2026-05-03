# LLM SRE 19：可靠性、扩缩容与多地域

> 📅 日期：2026-05-03
> 📖 学习主题：高可用部署、弹性扩缩容、发布策略与故障恢复
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：18-inference-observability-and-slo.md, Kubernetes HPA

## 🎯 学习目标

完成本章学习后，你将能够：

1. 设计多副本 / 多 AZ / 多地域的推理服务部署架构，并理解每层的故障域与恢复路径
2. 配置基于 LLM 特有指标（queue time、KV Cache 水位、token 吞吐等）的 HPA / KEDA 自动扩缩容策略
3. 实现金丝雀 / Shadow / 蓝绿发布策略，并定义质量守护门禁与自动回滚条件
4. 设计 fallback / 熔断 / 限流 / 降级的可靠性模式，并通过演练验证其真实可用性

---

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 高可用部署架构

高可用不是"开更多副本"这么简单。LLM 推理服务的可用性取决于多个维度：单实例稳定性、跨节点分布、跨可用区容灾、以及跨地域的全局恢复能力。每一层都需要明确故障域边界、恢复时间目标（RTO）和数据一致性要求。

**多副本部署**

多副本是最基础的可靠性手段。单副本模型服务即使 GPU 很强，也经不起节点驱逐、驱动异常、显存碎片积累和滚动升级。副本数至少要满足单实例故障后仍能维持目标 SLO，而不是只满足平均负载。

关键配置要素：
- 负载均衡：Round-Robin、Least-Connections 或基于请求权重的路由
- 健康检查：HTTP `/health`、gRPC health check、GPU 显存探针
- 会话亲和：长对话场景下需要 sticky session，但要注意负载不均

**多 AZ 部署**

多可用区部署的重点是故障域隔离。实践上应同时使用 `podAntiAffinity`、`topologySpreadConstraints` 和节点池标签，让同一模型池的副本分散到不同节点、机架和可用区。否则看起来是三副本，实际上可能都挤在同一故障域里。

```text
                    ┌─────────────────────────────────────────────────┐
                    │              全局负载均衡 (GSLB)                 │
                    └──────────┬──────────────┬──────────────┬────────┘
                               │              │              │
                    ┌──────────▼──┐ ┌─────────▼───┐ ┌───────▼──────┐
                    │   AZ-1      │ │   AZ-2      │ │   AZ-3       │
                    │             │ │             │ │              │
                    │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌──────────┐ │
                    │ │Inference│ │ │ │Inference│ │ │ │Inference │ │
                    │ │Pod x2   │ │ │ │Pod x2   │ │ │ │Pod x2    │ │
                    │ └─────────┘ │ │ └─────────┘ │ │ └──────────┘ │
                    │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌──────────┐ │
                    │ │GPU Node │ │ │ │GPU Node │ │ │ │GPU Node  │ │
                    │ │Pool     │ │ │ │Pool     │ │ │ │Pool      │ │
                    │ └─────────┘ │ │ └─────────┘ │ │ └──────────┘ │
                    │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌──────────┐ │
                    │ │Local    │ │ │ │Local    │ │ │ │Local     │ │
                    │ │Cache    │ │ │ │Cache    │ │ │ │Cache     │ │
                    │ └─────────┘ │ │ └─────────┘ │ │ └──────────┘ │
                    └─────────────┘ └─────────────┘ └──────────────┘
```

图 1：多可用区部署架构图。每个 AZ 拥有独立的推理实例池、GPU 节点池和本地缓存。全局负载均衡器将请求分发到健康 AZ，并在某个 AZ 故障时自动摘除。

**多地域部署**

多地域部署进一步解决区域级故障、主干网络抖动和合规驻留问题，但也引入复制、一致性和成本复杂度。常见模式有三种：

- **Active-Active**：多地域同时接流量，恢复快，但要处理会话亲和、缓存命中下降和跨地域成本
- **Active-Standby**：主地域服务、备地域热待命，实现简单，但平时资源利用率较低
- **Regional Specialization**：不同地域承载不同模型或租户，便于合规隔离，但切换路径更复杂

```text
    ┌──────────────────────────────────────────────────────────────────┐
    │                    Global Traffic Manager                        │
    │            (DNS / GSLB / Health-based Routing)                   │
    └───────┬──────────────────────┬──────────────────────┬───────────┘
            │                      │                      │
   ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
   │  Region: US-East │   │ Region: EU-West  │   │ Region: AP-East │
   │                  │   │                  │   │                 │
   │ ┌──────────────┐ │   │ ┌──────────────┐ │   │ ┌─────────────┐ │
   │ │  Ingress +   │ │   │ │  Ingress +   │ │   │ │  Ingress +  │ │
   │ │  Rate Limit  │ │   │ │  Rate Limit  │ │   │ │  Rate Limit │ │
   │ └──────┬───────┘ │   │ └──────┬───────┘ │   │ └──────┬──────┘ │
   │        │         │   │        │         │   │        │        │
   │ ┌──────▼───────┐ │   │ ┌──────▼───────┐ │   │ ┌──────▼──────┐ │
   │ │ Model Pool   │ │   │ │ Model Pool   │ │   │ │ Model Pool  │ │
   │ │ (GPT-L, LoRA │ │   │ │ (GPT-L, EU  │ │   │ │ (GPT-L, AP  │ │
   │ │  variants)   │ │   │ │  adapters)   │ │   │ │  adapters)  │ │
   │ └──────────────┘ │   │ └──────────────┘ │   │ └─────────────┘ │
   │ ┌──────────────┐ │   │ ┌──────────────┐ │   │ ┌─────────────┐ │
   │ │ Weight Store  │ │   │ │ Weight Store  │   │ │ Weight Store │ │
   │ │ + KV Cache    │ │◄──┤ │ + KV Cache    │◄──┤ │ + KV Cache   │ │
   │ └──────────────┘ │   │ └──────────────┘ │   │ └─────────────┘ │
   │                  │   │                  │   │                 │
   │  Status: ACTIVE  │   │  Status: ACTIVE  │   │  Status: ACTIVE │
   └──────────────────┘   └──────────────────┘   └─────────────────┘
          ▲                        ▲                       ▲
          │     Cross-Region Model Weight Sync             │
          └────────────────────────────────────────────────┘
```

图 2：多地域 Active-Active 架构图。每个地域独立承载流量，拥有完整的推理池和权重存储。地域间通过异步同步机制保持模型权重、LoRA 适配器和路由配置一致。

LLM 场景下，多地域不仅是"再放一套 Deployment"。你还要同步模型权重、LoRA 制品、路由配置、Prompt 版本、RAG 索引和配额规则。控制面没有跟上时，切流成功也可能只会把故障搬到另一个地域。

#### 1.2 自动扩缩容

CPU 和内存不是 LLM 服务最好的扩容信号。很多时候请求排队时间（queue time）已经飙升，但 CPU 仍然很闲；GPU 利用率很高，也不代表继续加副本就会改善 TTFT。扩容应围绕请求排队、token 吞吐、显存水位和冷启动时间设计。

**HPA 基础**

Horizontal Pod Autoscaler（HPA）适合基于稳定指标做副本调节。它的优点是原生、简单，缺点是面对突刺和长冷启动时反应偏慢。HPA 的核心循环是：

```text
    ┌──────────────────────────────────────────────────────────────┐
    │                    HPA Control Loop                          │
    │                                                              │
    │   ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    │
    │   │  Metrics     │───▶│  Desired    │───▶│  Scale       │    │
    │   │  Server      │    │  Replicas   │    │  Deployment  │    │
    │   └──────┬──────┘    └─────────────┘    └──────────────┘    │
    │          │                                                  │
    │          │  Current: queue_time_p95 = 8s                    │
    │          │  Target:  queue_time_p95 = 2s                    │
    │          │  Current Replicas: 3                              │
    │          │                                                  │
    │          ▼                                                  │
    │   Desired = ceil(3 * (8 / 2)) = 12                         │
    │   → Scale to 12 replicas                                    │
    └──────────────────────────────────────────────────────────────┘
```

**KEDA 事件驱动扩缩容**

KEDA（Kubernetes Event-Driven Autoscaling）更适合事件驱动场景，例如从 Kafka、SQS、Redis Stream 或 Prometheus backlog 指标触发扩容。KEDA 的优势在于支持从零扩缩（scale to zero）和更灵活的触发器组合。

```text
    ┌────────────────────────────────────────────────────────────────┐
    │                   KEDA Scaling Flow                           │
    │                                                                │
    │   ┌────────────┐     ┌──────────────┐     ┌───────────────┐   │
    │   │  Scaler     │────▶│  ScaledObject │────▶│  HPA          │   │
    │   │  (Prometheus│     │  Controller   │     │  (manages     │   │
    │   │   /Redis/   │     │              │     │   replicas)   │   │
    │   │   Kafka)    │     └──────────────┘     └───────┬───────┘   │
    │   └────────────┘                                   │           │
    │         ▲                                          ▼           │
    │         │                                   ┌─────────────┐   │
    │         │        ┌──────────────┐           │  Deployment │   │
    │         └────────│  Prometheus  │◀──────────│  (Pods)     │   │
    │                  │  Adapter     │           └─────────────┘   │
    │                  └──────────────┘                              │
    │                                                                │
    │   Metric: queue_time_p95 = 8s                                 │
    │   Scale-to-zero: minReplicaCount = 0                          │
    │   Cooldown: 300s                                               │
    └────────────────────────────────────────────────────────────────┘
```

图 3：KEDA 扩缩容流程图。Scaler 从外部系统（Prometheus、Redis、Kafka 等）拉取指标，ScaledObject 控制器根据指标计算期望副本数，通过 HPA 管理 Deployment 的副本数。

**LLM 特有扩缩容指标**

LLM 推理服务的扩缩容指标与传统 Web 服务有本质区别。传统服务关注 QPS 和 CPU，而 LLM 服务需要关注请求排队、token 吞吐和显存水位：

| 指标 | 含义 | 适用场景 | 优势 |
|------|------|----------|------|
| `queue_time_p95` | 请求在队列中等待的 p95 时间 | 通用推理服务 | 最贴近用户体验 |
| `inflight_requests` | 当前正在处理的请求数 | 路由层 / batcher 层 | 反映真实并发压力 |
| `tokens_per_second` | 每秒生成的 token 数 | 吞吐敏感场景 | 接近真实负载强度 |
| `kv_cache_usage_ratio` | KV Cache 显存占用比例 | 长上下文场景 | 提前发现显存风险 |
| `cold_start_in_progress` | 是否有实例正在冷启动 | 扩容保护 | 避免未就绪实例被计入容量 |
| `waiting_requests` | 等待中的请求数量 | 批处理队列 | 评估积压程度 |

**扩缩容决策矩阵**

扩缩容策略需要同时定义上升、下降和保护条件。上升过慢会放大排队；下降过快会在模型加载成本很高的场景中造成抖动。

```text
    ┌───────────────────────────────────────────────────────────────┐
    │              扩缩容决策矩阵                                    │
    ├───────────────────────────────────────────────────────────────┤
    │                                                               │
    │  信号              │ 动作       │ 条件              │ 冷却期  │
    │  ─────────────────┼───────────┼──────────────────┼──────── │
    │  queue_time_p95   │ Scale Up  │ > 5s 持续 60s     │ 120s    │
    │  queue_time_p95   │ Scale Down│ < 1s 持续 300s    │ 600s    │
    │  kv_cache_usage   │ Scale Up  │ > 85% 持续 30s    │ 180s    │
    │  inflight_req     │ Scale Up  │ > 80% 容量 持续 60s│ 120s   │
    │  cold_start       │ Block Scale│ == 1 (进行中)     │ --      │
    │  error_rate       │ Scale Down│ > 5% (异常扩容)    │ --      │
    │                                                               │
    │  最小副本：2（保证单点故障冗余）                                │
    │  最大副本：由 GPU 配额决定                                      │
    │  预热池：额外 10% 容量缓冲                                     │
    └───────────────────────────────────────────────────────────────┘
```

对加载分钟级权重的大模型，建议结合最小副本、预热池和峰值前定时扩容，而不是只信任纯自动策略。

#### 1.3 发布策略

发布策略是可靠性体系的一部分，因为很多事故来自变更而不是硬件。LLM 服务发布不只是镜像升级，还包括模型版本切换、量化参数变化、Prompt 模板变更、LoRA 适配器替换和路由规则调整。

**金丝雀发布**

金丝雀发布适合逐步放量，重点观察 TTFT、错误率、回退率、截断率和用户反馈是否与基线偏离。对推理服务来说，单看 5xx 不够，因为质量退化通常先体现在输出差异和重试率上。

```text
    ┌────────────────────────────────────────────────────────────────┐
    │                金丝雀发布流程                                   │
    │                                                                │
    │   ┌─────────┐                                                  │
    │   │ Traffic │                                                  │
    │   │ Source  │                                                  │
    │   └────┬────┘                                                  │
    │        │                                                       │
    │        ▼                                                       │
    │   ┌─────────────┐      ┌──────────────────┐                    │
    │   │  Ingress /  │      │  Traffic Split    │                    │
    │   │  Gateway    │─────▶│  Controller       │                    │
    │   └─────────────┘      └────────┬─────────┘                    │
    │                                 │                              │
    │                    ┌────────────┼────────────┐                 │
    │                    │            │            │                 │
    │                    ▼            │            ▼                 │
    │            ┌──────────┐         │    ┌──────────────┐          │
    │            │ Baseline │         │    │  Canary      │          │
    │            │ (95%)    │         │    │  (5%)        │          │
    │            │ v1.0     │         │    │  v1.1        │          │
    │            └──────────┘         │    └──────────────┘          │
    │                                 │            │                 │
    │                                 │            ▼                 │
    │                                 │    ┌──────────────┐          │
    │                                 │    │  Quality     │          │
    │                                 │    │  Analyzer    │          │
    │                                 │    │              │          │
    │                                 │    │  Compare:    │          │
    │                                 │    │  - TTFT      │          │
    │                                 │    │  - Error Rate│          │
    │                                 │    │  - Truncation│          │
    │                                 │    │  - Fallback %│          │
    │                                 │    └──────┬───────┘          │
    │                                 │           │                  │
    │                    ┌────────────┴───────────┘                  │
    │                    │                                           │
    │              ┌─────▼─────┐    ┌──────────────┐                │
    │              │  PROMOTE  │    │  ROLLBACK    │                │
    │              │  100%     │    │  to v1.0     │                │
    │              └───────────┘    └──────────────┘                │
    └────────────────────────────────────────────────────────────────┘
```

图 4：金丝雀发布流程图。流量按比例分配到基线和金丝雀实例，质量分析器持续对比 TTFT、错误率、截断率等指标。达标则晋升，不达标则自动回滚。

**Shadow Traffic（影子流量）**

影子流量适合验证新模型或新运行时的行为，但要明确它不应该影响主链路 SLO。shadow 请求需要隔离配额、日志和成本归因，否则很容易把实验流量误算进生产容量。

关键设计要点：
- Shadow 请求的结果不返回给用户，只用于指标采集和对比
- Shadow 请求必须有独立的超时和资源配额，不能抢占生产容量
- 影子流量的响应需要与生产响应进行离线对比（BLEU、ROUGE 或人工评测）

**蓝绿部署**

蓝绿发布适合需要快速切换的稳定版本替换，前提是两套环境都完成预热，并且连接状态、缓存与索引版本兼容。

关键设计要点：
- 蓝绿切换必须是原子操作，流量要么全在蓝、要么全在绿
- 旧环境（蓝）在切换后保留一段时间，便于快速回滚
- 预热阶段要确保新环境的模型权重已加载完毕、KV Cache 已初始化

**模型版本 vs 服务版本解耦**

LLM 平台的独特挑战在于，模型版本和服务版本的生命周期不同。模型可能每天更新权重，而服务代码可能每周才发布一次。因此需要将模型版本管理从服务发布流程中解耦：

- 服务版本：镜像 tag、代码分支、配置文件版本
- 模型版本：权重 hash、LoRA adapter ID、量化参数版本
- 路由版本：Prompt 模板版本、RAG 索引版本、工具配置版本

#### 1.4 可靠性模式

LLM 平台不能把每个请求都视为"必须在原计划上成功"。可靠性的核心能力之一，是在主路径不稳定时有明确的次优路径。

**Fallback（回退）**

Fallback 常见于三类场景：主模型不可用时切到备用模型，RAG 检索失败时退化为无检索回答或固定模板，工具调用超时时返回部分结果。fallback 的前提是质量边界可接受，否则只是把显式错误改成隐式错误。

```text
    ┌────────────────────────────────────────────────────────────────┐
    │                   Fallback 决策树                              │
    │                                                                │
    │                    请求到达                                     │
    │                       │                                        │
    │                       ▼                                        │
    │              ┌─────────────────┐                               │
    │              │ 主模型可用？     │                               │
    │              └────────┬────────┘                               │
    │                  是   │   否                                   │
    │         ┌─────────────┼────────────┐                          │
    │         ▼                           ▼                          │
    │  ┌──────────────┐          ┌──────────────┐                   │
    │  │ 主模型推理    │          │ 备用模型池    │                   │
    │  └──────┬───────┘          │ (较轻量/较便宜)│                  │
    │         │                  └──────┬───────┘                   │
    │         ▼                         │                           │
    │  ┌──────────────┐                 ▼                           │
    │  │ 质量检查      │          ┌──────────────┐                   │
    │  │ (截断率、     │    是    │ 备用模型可用？ │                   │
    │  │  空输出率)    │────────▶ └──────┬───────┘                   │
    │  └──────┬───────┘            否    │  是                       │
    │    是   │   否              │      │                          │
    │    │    │                   ▼      ▼                           │
    │    │    │            ┌────────┐ ┌────────┐                    │
    │    │    │            │降级响应│ │备用推理│                     │
    │    │    │            │(模板/  │ └────────┘                    │
    │    │    │            │ 简化)  │                               │
    │    ▼    ▼            └────────┘                               │
    │  ┌────────┐                                                   │
    │  │正常响应│                                                    │
    │  └────────┘                                                   │
    └────────────────────────────────────────────────────────────────┘
```

图 5：Fallback 决策树。请求首先尝试主模型，通过质量检查后返回正常响应。主模型不可用时依次尝试备用模型池，最终降级为模板响应。

**熔断（Circuit Breaking）**

熔断用于阻止故障扩散。某个下游 embedding 服务、向量库或工具服务持续超时时，继续压请求只会把线程池、连接池和重试预算一起打爆。

```text
    ┌────────────────────────────────────────────────────────────────┐
    │                  熔断器状态机                                   │
    │                                                                │
    │   ┌──────────┐    错误率 > 阈值     ┌──────────┐              │
    │   │  CLOSED  │─────────────────────▶│   OPEN   │              │
    │   │ (正常)   │    持续 N 次请求      │ (熔断)   │              │
    │   └──────────┘                      └────┬─────┘              │
    │        ▲                                  │                    │
    │        │                          超时到期 │                    │
    │        │                                  ▼                    │
    │   探测成功│                       ┌──────────────┐             │
    │        │                         │  HALF-OPEN   │             │
    │        │                         │  (半开探测)   │             │
    │        └─────────────────────────┤              │             │
    │                    探测请求成功    └──────┬───────┘             │
    │                                         │                     │
    │                                  探测失败│                     │
    │                                         ▼                     │
    │                                  回到 OPEN 状态               │
    │                                  (重置超时计时器)              │
    │                                                              │
    │   阈值配置示例：                                              │
    │   - 错误率 > 50% 持续 10 次请求 → 触发 OPEN                  │
    │   - OPEN 持续 30s → 进入 HALF-OPEN                          │
    │   - HALF-OPEN 放行 3 次探测请求                              │
    │   - 探测全部成功 → CLOSED；任一失败 → OPEN                   │
    └────────────────────────────────────────────────────────────────┘
```

图 6：熔断器状态机。CLOSED 状态正常放行请求；当错误率超过阈值持续一定次数后进入 OPEN 状态，阻断所有请求；超时后进入 HALF-OPEN 放行少量探测请求，根据探测结果决定回到 CLOSED 或重新 OPEN。

**限流（Rate Limiting）**

限流解决容量保护问题，常见维度包括租户、模型、请求 token、并发会话和工具调用次数。

常见限流算法：
- **令牌桶（Token Bucket）**：允许突发流量，长期速率受控
- **滑动窗口（Sliding Window）**：比固定窗口更平滑，避免窗口边界突刺
- **漏桶（Leaky Bucket）**：强制平滑输出速率，适合保护后端

**降级（Degradation）**

降级要有层次，而不是只有"返回 503"。常见做法包括：

- 降低最大上下文长度，优先保住整体可用性
- 关闭 reranker、工具调用或多步 agent 链路，缩短关键路径
- 将长文本生成改为摘要模式，限制输出 token 上限
- 将低优先级租户切到便宜或较慢的备用池

这些机制要提前演练。没有演练的 fallback，往往会在真正故障时暴露出配置失效、质量不可接受或成本失控的问题。

---

### 2. 命令/工具详解

#### 2.1 KEDA ScaledObject 配置

以下是一个完整的 KEDA ScaledObject 配置示例，基于 Prometheus 指标 `queue_time_p95` 驱动扩缩容：

```yaml
# keda-scaledobject-llm.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: llm-inference-scaler
  namespace: llm-serving
spec:
  scaleTargetRef:
    name: llm-inference-deployment    # 目标 Deployment 名称
  minReplicaCount: 2                    # 最小副本数，保证冗余
  maxReplicaCount: 20                   # 最大副本数，受 GPU 配额限制
  cooldownPeriod: 600                   # 缩容冷却期（秒），大模型加载慢需要更长
  idleReplicaCount: 0                   # 空闲时缩容到 0（可选）
  pollingInterval: 15                   # 指标轮询间隔（秒）
  advanced:
    restoreToOriginalReplicaCount: false
    horizontalPodAutoscalerConfig:
      name: llm-inference-hpa
      behavior:
        scaleUp:
          stabilizationWindowSeconds: 60
          policies:
            - type: Percent
              value: 100                # 每次最多扩容 100%
              periodSeconds: 60
            - type: Pods
              value: 4                  # 或每次最多增加 4 个 Pod
              periodSeconds: 60
          selectPolicy: Max
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
            - type: Percent
              value: 25                 # 每次最多缩容 25%
              periodSeconds: 120
          selectPolicy: Min
  triggers:
    # 触发器 1：基于 Prometheus 的 queue_time_p95
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: queue_time_p95_seconds
        query: |
          histogram_quantile(0.95,
            sum(rate(inference_request_queue_duration_seconds_bucket{
              deployment="llm-inference-deployment",
              namespace="llm-serving"
            }[5m])) by (le)
          )
        threshold: "2"                  # 阈值：2 秒
        activationThreshold: "0.5"      # 激活阈值：低于此值不扩容
    # 触发器 2：基于 Prometheus 的 kv_cache_usage_ratio
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: kv_cache_usage_ratio
        query: |
          avg(vllm:gpu_cache_usage_perc{
            deployment="llm-inference-deployment",
            namespace="llm-serving"
          })
        threshold: "0.85"               # 阈值：85%
        activationThreshold: "0.6"      # 激活阈值：60%
    # 触发器 3：基于 Prometheus 的 inflight_requests
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: inflight_requests_ratio
        query: |
          sum(vllm:num_requests_running{
            deployment="llm-inference-deployment"
          }) /
          sum(vllm:num_requests_max{
            deployment="llm-inference-deployment"
          })
        threshold: "0.8"                # 阈值：80% 容量
        activationThreshold: "0.5"
```

#### 2.2 HPA 自定义指标配置

如果不用 KEDA，原生 HPA 也支持自定义指标，但需要 Prometheus Adapter：

```yaml
# hpa-custom-metrics.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llm-inference-hpa
  namespace: llm-serving
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-inference-deployment
  minReplicas: 2
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
  metrics:
    # 指标 1：queue_time_p95（来自 Prometheus Adapter）
    - type: Pods
      pods:
        metric:
          name: queue_time_p95_seconds
        target:
          type: AverageValue
          averageValue: "2"              # 目标：每个 Pod 平均 queue time < 2s
    # 指标 2：GPU 显存使用率
    - type: Pods
      pods:
        metric:
          name: gpu_memory_usage_ratio
        target:
          type: AverageValue
          averageValue: "0.8"            # 目标：每个 Pod 显存使用 < 80%
    # 指标 3：CPU 利用率（兜底指标）
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

Prometheus Adapter 配置（将自定义 Prometheus 指标暴露给 HPA）：

```yaml
# prometheus-adapter-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
      - seriesQuery: 'inference_request_queue_duration_seconds_bucket{namespace!="",pod!=""}'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          matches: "^(.*)_seconds_bucket$"
          as: "${1}_seconds"
        metricsQuery: |
          histogram_quantile(0.95,
            sum(rate(<<.Series>>{<<.LabelMatchers>>}[5m])) by (<<.GroupBy>>, le)
          )
      - seriesQuery: 'vllm:gpu_cache_usage_perc{namespace!="",pod!=""}'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          as: "gpu_memory_usage_ratio"
        metricsQuery: |
          avg(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)
```

#### 2.3 Istio 金丝雀流量分配

使用 Istio VirtualService 实现金丝雀流量分配：

```yaml
# istio-canary-virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: llm-inference-vs
  namespace: llm-serving
spec:
  hosts:
    - llm-inference.llm-serving.svc.cluster.local
  http:
    - match:
        - headers:
            x-canary:
              exact: "true"             # 通过 Header 强制路由到金丝雀
      route:
        - destination:
            host: llm-inference.llm-serving.svc.cluster.local
            subset: canary
          weight: 100
    - route:                            # 默认路由：按权重分配
        - destination:
            host: llm-inference.llm-serving.svc.cluster.local
            subset: stable
          weight: 95
        - destination:
            host: llm-inference.llm-serving.svc.cluster.local
            subset: canary
          weight: 5
      timeout: 120s                     # 推理请求需要较长超时
      retries:
        attempts: 2
        perTryTimeout: 60s
        retryOn: 5xx
---
# DestinationRule 定义稳定版和金丝雀子集
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: llm-inference-dr
  namespace: llm-serving
spec:
  host: llm-inference.llm-serving.svc.cluster.local
  subsets:
    - name: stable
      labels:
        version: v1.0
    - name: canary
      labels:
        version: v1.1
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    outlierDetection:
      consecutive5xxErrors: 5           # 连续 5 个 5xx 错误
      interval: 30s                     # 检测间隔
      baseEjectionTime: 60s             # 最短摘除时间
      maxEjectionPercent: 50            # 最多摘除 50% 实例
```

#### 2.4 Envoy 熔断器配置

通过 Istio 的 DestinationRule 配置熔断策略：

```yaml
# circuit-breaker-destination-rule.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: embedding-service-dr
  namespace: llm-serving
spec:
  host: embedding-service.llm-serving.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100             # 最大 TCP 连接数
        connectTimeout: 5s              # 连接超时
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 50     # HTTP/1.1 最大等待请求数
        http2MaxRequests: 200           # HTTP/2 最大并发请求数
        maxRequestsPerConnection: 100   # 每连接最大请求数
        maxRetries: 3                   # 最大重试次数
    outlierDetection:
      consecutive5xxErrors: 5           # 触发条件：连续 5 个 5xx
      consecutiveGatewayErrors: 5       # 触发条件：连续 5 个网关错误
      interval: 10s                     # 检测间隔
      baseEjectionTime: 30s             # 最短摘除时间
      maxEjectionTime: 300s             # 最长摘除时间
      maxEjectionPercent: 50            # 最大摘除比例
      minHealthPercent: 30              # 最小健康比例
```

#### 2.5 限流中间件配置

使用 EnvoyFilter 配置全局限流：

```yaml
# ratelimit-envoyfilter.yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: llm-ratelimit-filter
  namespace: llm-serving
spec:
  workloadSelector:
    labels:
      app: llm-inference
  configPatches:
    - applyTo: HTTP_FILTER
      match:
        context: SIDECAR_INBOUND
        listener:
          filterChain:
            filter:
              name: envoy.filters.network.http_connection_manager
              subFilter:
                name: envoy.filters.http.router
      patch:
        operation: INSERT_BEFORE
        value:
          name: envoy.filters.http.local_ratelimit
          typed_config:
            "@type": type.googleapis.com/udpa.type.v1.TypedStruct
            type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
            value:
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 100           # 桶容量
                tokens_per_fill: 10       # 每次填充量
                fill_interval: 1s         # 填充间隔
              filter_enabled:
                runtime_key: local_rate_limit_enabled
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                runtime_key: local_rate_limit_enforced
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              response_headers_to_add:
                - append_action: OVERWRITE_IF_EXISTS_OR_ADD
                  header:
                    key: x-local-rate-limit
                    value: "true"
              local_rate_limit_per_downstream_connection: false
```

#### 2.6 多地域 DNS 切流配置

使用 External-DNS 和健康检查实现多地域自动切流：

```yaml
# global-traffic-policy.yaml
apiVersion: networking.gke.io/v1
kind: MultiClusterService
metadata:
  name: llm-inference-mcs
  namespace: llm-serving
spec:
  template:
    spec:
      selector:
        app: llm-inference
      ports:
        - port: 8080
          targetPort: 8080
---
# 健康检查策略（以 GCP 为例）
apiVersion: networking.gke.io/v1
kind: HealthCheckPolicy
metadata:
  name: llm-inference-health
  namespace: llm-serving
spec:
  default:
    config:
      type: HTTP
      httpHealthCheck:
        port: 8080
        requestPath: /health
      checkIntervalSec: 10
      timeoutSec: 5
      healthyThreshold: 2
      unhealthyThreshold: 3
```

---

### 3. SRE 实战案例

#### 案例 1：流量突增导致服务雪崩

**背景**

某 LLM 平台在周一下午 2 点遭遇流量突增。平时 QPS 约 500，某大客户突然将批量任务上线，QPS 在 5 分钟内飙升到 3000。服务开始出现大面积超时，用户体验急剧恶化。

**症状表现**

```text
    时间线：
    14:00  QPS 500 → 正常，TTFT p95 = 1.2s
    14:02  QPS 1200 → queue_time_p95 开始上升到 3s
    14:04  QPS 2500 → queue_time_p95 = 12s，开始出现 504
    14:05  QPS 3000 → 大量请求超时，级联失败
    14:06  HPA 开始扩容 → 但新 Pod 冷启动需要 180s
    14:08  用户投诉涌入 → 成功率降至 60%
    14:10  触发限流 → 成功率回升到 85%
    14:15  新 Pod 就绪 → 成功率恢复到 95%
    14:20  完全恢复 → QPS 稳定在 2800，TTFT p95 = 1.8s
```

**诊断过程**

第一步：检查用户体验指标

```bash
# 查询 TTFT p95 趋势
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(inference_request_duration_seconds_bucket{phase="ttft"}[5m])) by (le))'

# 查询 queue time
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(inference_request_queue_duration_seconds_bucket[5m])) by (le))'

# 查询错误率
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(inference_request_total{status=~"5.."}[5m])) / sum(rate(inference_request_total[5m]))'
```

第二步：检查扩缩容状态

```bash
# 检查 HPA 状态
kubectl get hpa -n llm-serving

# 检查 Pod 状态
kubectl get pods -n llm-serving -l app=llm-inference -o wide

# 检查 KEDA 事件
kubectl describe scaledobject llm-inference-scaler -n llm-serving

# 检查 GPU 利用率
kubectl top pods -n llm-serving -l app=llm-inference --containers
```

第三步：检查扩缩容事件日志

```bash
# 查看 HPA 事件
kubectl describe hpa llm-inference-hpa -n llm-serving | grep -A 20 Events

# 查看 Pod 启动时间
kubectl get pods -n llm-serving -l app=llm-inference \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.startTime}{"\t"}{range .status.conditions[?(@.type=="Ready")]}{.lastTransitionTime}{end}{"\n"}{end}'
```

**根因分析**

```text
    根因链：
    大客户批量任务上线 (触发因素)
        ↓
    QPS 5 分钟内 6 倍增长 (直接原因)
        ↓
    HPA 扩容触发，但冷启动需 180s (放大因素)
        ↓
    现有 6 个 Pod 队列积压 → queue time 飙升 (症状)
        ↓
    用户端超时重试 → 流量进一步放大 (恶性循环)
        ↓
    级联失败：重试风暴 + 排队雪崩 (最终故障)
```

核心问题：
1. **最小副本数不足**：只有 6 个 Pod，没有为突发流量预留缓冲
2. **扩容速度慢**：大模型冷启动 180s，HPA 反应滞后
3. **缺少限流保护**：没有按租户限流，单个大客户可以冲垮整个服务
4. **缺少降级策略**：没有在容量不足时降级输出质量来保全可用性

**修复措施**

即时修复：
1. 启用限流：对大客户 QPS 限制在 800，超出部分返回 429
2. 手动扩容：将最小副本从 6 调到 12
3. 启用降级：将最大输出 token 从 4096 降到 1024，减少单请求占用时间

```yaml
# 修复后的限流配置
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: llm-serving
data:
  config.yaml: |
    domain: llm-ratelimit
    descriptors:
      - key: tenant_id
        value: "big-customer-001"
        rate_limit:
          unit: second
          requests_per_unit: 800
      - key: tenant_id
        value: "default"
        rate_limit:
          unit: second
          requests_per_unit: 200
```

长期预防：
1. **容量缓冲**：最小副本从 6 调到 10，确保单客户突增不会冲垮服务
2. **预热池**：维护 2 个预热 Pod，随时可接管流量
3. **定时扩容**：工作日下午 1-3 点提前扩容到 15 个 Pod
4. **租户隔离**：大客户路由到独立模型池，避免互相影响

```yaml
# 预热池配置：保持 2 个 idle Pod
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: llm-inference-scaler
  namespace: llm-serving
spec:
  minReplicaCount: 10                  # 提升最小副本
  maxReplicaCount: 30
  idleReplicaCount: 10                 # 空闲时保持 10 个
  # ...
```

**经验总结**

- 扩容速度要和流量增速匹配：如果冷启动需要 180s，就要靠预热池和定时扩容来弥补
- 限流是第一道防线：不能让单个客户冲垮整个服务
- 降级比不可用好：宁可返回缩短的回答，也不要让用户等到超时
- 演练扩容场景：定期用 load test 验证扩容策略是否真实有效

---

#### 案例 2：金丝雀发布后质量回退

**背景**

某团队发布模型 v1.1（从 v1.0 升级），通过金丝雀方式将 5% 流量切到新版本。上线 2 小时后，客服收到多起投诉，用户反映模型回答质量下降，但监控面板上错误率（5xx）几乎没变化。

**症状表现**

```text
    时间线：
    10:00  金丝雀上线，5% 流量切到 v1.1
    10:30  指标正常：错误率 0.1%，TTFT p95 = 1.3s
    11:00  客服收到第一起投诉："模型回答变短了"
    11:30  投诉增加到 5 起，内容类似
    12:00  SRE 开始排查，发现金丝雀池的截断率偏高
    12:30  确认根因：v1.1 在长输入场景下输出截断
    12:45  触发回滚，将流量全部切回 v1.0
    13:00  投诉停止，确认恢复
```

**诊断过程**

第一步：对比金丝雀与基线实例的核心指标

```bash
# 对比 TTFT
echo "=== Canary TTFT ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(inference_request_duration_seconds_bucket{version="v1.1",phase="ttft"}[5m])) by (le))'

echo "=== Baseline TTFT ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(inference_request_duration_seconds_bucket{version="v1.0",phase="ttft"}[5m])) by (le))'

# 对比截断率
echo "=== Canary Truncation Rate ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(inference_response_truncated_total{version="v1.1"}[5m])) / sum(rate(inference_request_total{version="v1.1"}[5m]))'

echo "=== Baseline Truncation Rate ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(inference_response_truncated_total{version="v1.0"}[5m])) / sum(rate(inference_request_total{version="v1.0"}[5m]))'

# 对比平均输出 token 数
echo "=== Canary Avg Output Tokens ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=avg(inference_output_tokens_sum{version="v1.1"} / inference_output_tokens_count{version="v1.1"})'

echo "=== Baseline Avg Output Tokens ==="
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=avg(inference_output_tokens_sum{version="v1.0"} / inference_output_tokens_count{version="v1.0"})'
```

第二步：分析截断与输入长度的关系

```bash
# 按输入长度分桶，对比截断率
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(inference_response_truncated_total{version="v1.1"}[5m])) by (input_length_bucket) / sum(rate(inference_request_total{version="v1.1"}[5m])) by (input_length_bucket)'
```

发现：当输入 token 超过 2048 时，v1.1 的截断率从 v1.0 的 2% 飙升到 35%。

第三步：检查模型配置变更

```bash
# 对比 v1.0 和 v1.1 的配置差异
diff <(kubectl get configmap model-config-v10 -n llm-serving -o yaml) \
     <(kubectl get configmap model-config-v11 -n llm-serving -o yaml)
```

发现：v1.1 的配置中 `max_position_embeddings` 从 8192 改成了 4096，这是量化优化时的配置错误。

**根因分析**

```text
    根因链：
    模型 v1.1 量化优化 (变更)
        ↓
    误将 max_position_embeddings 从 8192 改为 4096 (配置错误)
        ↓
    超过 4096 token 的输入被截断 (直接原因)
        ↓
    但截断不产生 5xx 错误，只产生较短回答 (隐蔽性)
        ↓
    监控只看错误率，未监控截断率 (监控盲区)
        ↓
    用户感知质量下降，但系统指标正常 (告警失效)
```

核心问题：
1. **配置变更未审计**：量化过程中修改了关键配置但未标注
2. **质量守护指标不全**：金丝雀对比只看错误率和 TTFT，忽略了截断率
3. **评测覆盖不足**：评测集中长输入样本不够，未能在发布前发现

**修复措施**

即时修复：
1. 触发回滚，将流量切回 v1.0
2. 修正 v1.1 的配置，恢复 `max_position_embeddings = 8192`
3. 补充长输入场景的评测用例

长期预防：

```yaml
# 金丝雀质量守护门禁配置
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: llm-inference-canary
  namespace: llm-serving
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-inference-deployment
  progressDeadlineSeconds: 600
  analysis:
    interval: 60s
    threshold: 5                           # 最大失败次数
    maxWeight: 50                          # 金丝雀最大流量比例
    stepWeight: 10                         # 每次增加的流量比例
    metrics:
      # 门禁 1：错误率
      - name: error-rate
        thresholdRange:
          max: 0.01                        # 错误率不能超过 1%
        interval: 60s
      # 门禁 2：截断率（新增）
      - name: truncation-rate
        thresholdRange:
          max: 0.05                        # 截断率不能超过 5%
        interval: 60s
      # 门禁 3：平均输出 token 数（新增）
      - name: avg-output-tokens
        thresholdRange:
          min: 200                         # 平均输出不能低于 200 token
        interval: 60s
      # 门禁 4：TTFT
      - name: ttft-p95
        thresholdRange:
          max: 3000                        # TTFT p95 不能超过 3s
        interval: 60s
      # 门禁 5：fallback 比例
      - name: fallback-rate
        thresholdRange:
          max: 0.02                        # fallback 比例不能超过 2%
        interval: 60s
```

**经验总结**

- 错误率不是唯一的质量指标：截断率、输出长度、fallback 比例同样重要
- 配置变更需要和代码变更一样严格审计
- 金丝雀门禁要覆盖质量维度，不只是可用性维度
- 评测集要覆盖边界场景：长输入、特殊字符、多轮对话

---

## 💻 实战练习

### 练习 1：基础操作 - 配置 KEDA 基于队列长度的自动扩缩容

**目标**：为一个模拟的 LLM 推理服务配置 KEDA 自动扩缩容，基于 Prometheus 指标 `queue_time_p95` 驱动。

**步骤**：

1. 部署一个模拟的 LLM 推理服务（可以使用简单的 HTTP 服务模拟队列行为）
2. 部署 Prometheus 和 Prometheus Adapter
3. 创建 KEDA ScaledObject 配置
4. 使用 `hey` 或 `locust` 生成负载，观察扩缩容行为
5. 验证冷却期和缩容行为

**验证标准**：
- 负载增加时，Pod 数量在 2 分钟内开始增加
- 负载降低后，Pod 在冷却期结束后逐步缩容
- 最小副本数始终得到保证

```bash
# 验证命令
kubectl get hpa -n llm-serving -w       # 持续观察 HPA 变化
kubectl get pods -n llm-serving -w      # 持续观察 Pod 变化
kubectl describe scaledobject -n llm-serving  # 查看 KEDA 事件
```

### 练习 2：进阶场景 - 实现金丝雀发布流程

**目标**：使用 Istio 实现金丝雀发布，包含流量分配、指标对比和自动回滚。

**步骤**：

1. 部署 Istio 到测试集群
2. 创建两个版本的推理服务 Deployment（v1.0 和 v1.1）
3. 配置 VirtualService 进行流量分配（95/5）
4. 配置 Flagger 进行自动化金丝雀分析
5. 模拟 v1.1 质量退化（注入错误或修改配置）
6. 观察自动回滚行为

**验证标准**：
- 流量按配置比例分配到两个版本
- 质量指标异常时，金丝雀自动回滚
- 回滚过程中用户无感知

```bash
# 验证命令
kubectl get canary -n llm-serving -w                  # 观察金丝雀状态
kubectl describe virtualservice llm-inference-vs      # 查看路由规则
istioctl proxy-config routes deploy/istio-ingressgateway -n istio-system  # 查看实际路由
```

### 练习 3：故障排查挑战 - 模拟流量突增场景

**目标**：模拟一个流量突增场景，验证限流和降级策略是否有效。

**步骤**：

1. 部署推理服务，配置限流（每租户 QPS 限制 100）
2. 配置降级策略（队列积压时降低最大输出 token）
3. 使用负载测试工具模拟单租户 QPS 突增到 500
4. 观察限流是否生效（429 响应比例）
5. 观察降级是否生效（输出 token 数下降）
6. 验证其他租户不受影响

**验证标准**：
- 超限请求返回 429，不超过配置的 QPS 限制
- 降级触发后，平均输出 token 数下降
- 其他租户的 TTFT 和错误率不受影响

```bash
# 验证命令
# 检查限流状态
curl -s http://llm-inference/metrics | grep ratelimit

# 检查降级状态
curl -s http://llm-inference/metrics | grep degradation

# 检查各租户的 QPS
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(inference_request_total[1m])) by (tenant_id)'
```

---

## 🎯 面试题精选

### 问题 1：LLM 服务的扩缩容指标与传统 Web 服务有什么区别？

**参考答案**：

传统 Web 服务的扩缩容通常基于 CPU 利用率、内存使用率和请求 QPS。这些指标在 LLM 推理场景下往往不够准确：

1. **CPU 不是瓶颈**：LLM 推理主要受 GPU 限制，CPU 利用率可能很低但服务已经过载
2. **QPS 不能反映负载强度**：一个处理 100 token 的请求和一个处理 8000 token 的请求，资源消耗差异巨大
3. **队列时间更贴近用户体验**：`queue_time_p95` 直接反映了用户等待时间，是更好的扩容信号
4. **KV Cache 水位决定长上下文能力**：`kv_cache_usage_ratio` 在长上下文场景下至关重要，CPU 指标无法反映
5. **冷启动时间差异大**：LLM 服务冷启动可能需要 1-3 分钟加载权重，缩容策略需要更保守

因此，LLM 服务应该使用 `queue_time_p95`、`inflight_requests`、`tokens_per_second`、`kv_cache_usage_ratio` 和 `cold_start_in_progress` 等自定义指标驱动扩缩容。

### 问题 2：金丝雀发布如何验证模型质量？

**参考答案**：

金丝雀发布验证模型质量需要多维度指标，不能只看传统的错误率：

1. **功能指标**：错误率（5xx）、超时率、截断率
2. **性能指标**：TTFT p95、TPOT p95、端到端延迟
3. **质量指标**：
   - 输出长度分布：平均输出 token 数是否下降
   - Fallback 比例：触发降级的请求是否增加
   - 输出差异评分：使用 BLEU/ROUGE 对比金丝雀与基线的输出
4. **用户反馈**：主动收集金丝雀用户的满意度评分

自动回滚条件应设置为：任一质量指标偏离基线超过阈值（如截断率 > 5%、fallback 比例 > 2%、TTFT p95 > 3s）持续 N 分钟，自动触发回滚。

### 问题 3：熔断、限流、降级分别适用于什么场景？

**参考答案**：

| 模式 | 适用场景 | 作用 | 示例 |
|------|----------|------|------|
| **限流** | 防止单一来源过载 | 控制进入系统的请求速率 | 每租户 QPS 限制、每 API key 并发限制 |
| **熔断** | 下游服务故障 | 阻止故障扩散，快速失败 | Embedding 服务超时，停止发送请求 |
| **降级** | 系统资源不足 | 降低服务质量换取可用性 | 队列积压时缩短输出长度 |

三者通常组合使用：限流是第一道防线（入口保护），熔断是第二道防线（故障隔离），降级是最后手段（质量换可用性）。

### 问题 4：多地域部署的数据一致性挑战有哪些？

**参考答案**：

LLM 多地域部署涉及多种数据的一致性挑战：

1. **模型权重**：大模型权重文件可能数十 GB，跨地域同步需要时间和带宽。解决方案是预分发 + 版本哈希校验
2. **LoRA 适配器**：每个租户可能有不同 LoRA，需要在所有地域保持一致。解决方案是中心化存储 + 异步复制
3. **Prompt 模板**：Prompt 变更需要在所有地域生效。解决方案是 Prompt Registry + 版本控制
4. **RAG 索引**：向量索引的构建和更新需要在每个地域独立进行，但查询结果要一致。解决方案是异步索引更新 + 版本标记
5. **配额和路由规则**：租户配额在跨地域时需要全局一致。解决方案是集中式配额服务或 CRDTs

关键是区分哪些数据需要强一致（配额），哪些可以最终一致（模型权重），并为每类数据选择合适的同步策略。

### 问题 5：如何设计 LLM 服务的 Fallback 策略？

**参考答案**：

LLM Fallback 策略应该分层设计：

1. **模型级 Fallback**：主模型不可用时，切换到备用模型（通常更轻量、更便宜）
2. **功能级 Fallback**：
   - RAG 检索失败 → 退化为无检索的纯模型回答
   - 工具调用超时 → 返回部分结果或告知用户
   - 多步 Agent 链路中断 → 返回已完成步骤的结果
3. **质量级 Fallback**：
   - 长输出被截断 → 返回截断内容 + 提示
   - 模型输出质量评分低 → 触发重新生成或切换模型
4. **容量级 Fallback**：
   - 队列积压严重 → 缩短最大输出长度
   - 高优先级租户资源不足 → 抢占低优先级租户的配额

设计原则：
- Fallback 的质量边界必须提前定义并被业务接受
- 每种 Fallback 都要有监控和告警
- 定期演练 Fallback 路径，确保配置有效

### 问题 6：如何避免扩缩容过程中的"抖动"（Thrashing）？

**参考答案**：

扩缩容抖动是指 Pod 数量在短时间内反复增减，导致服务不稳定。避免方法：

1. **设置合理的冷却期**：扩容冷却 60-120s，缩容冷却 300-600s
2. **使用稳定窗口**：HPA 的 `stabilizationWindowSeconds` 可以平滑决策
3. **多指标取最大值**：使用 `selectPolicy: Max`，多个指标中取最大期望副本数
4. **缩容速率限制**：每次最多缩容 25%，分批缩容
5. **最小副本保底**：设置最小副本数，避免缩容到 0 后的冷启动
6. **预热池**：维护空闲 Pod，避免频繁创建销毁

### 问题 7：如何评估一个 LLM 服务的容量规划是否合理？

**参考答案**：

评估 LLM 服务容量规划需要考虑多个维度：

1. **峰值流量覆盖**：当前副本数能否承受历史峰值流量的 1.5-2 倍
2. **单点故障冗余**：任意一个 Pod 故障后，剩余容量是否仍能满足 SLO
3. **扩容速度匹配**：从触发扩容到新 Pod 就绪的时间内，现有 Pod 能否扛住
4. **成本效率**：GPU 利用率是否在合理范围（60-80%），闲置资源是否过多
5. **降级空间**：启用降级策略后，能额外承载多少流量
6. **地域冗余**：单地域故障时，其他地域是否有足够容量接管

建议通过定期负载测试验证容量规划，测试场景应包括：正常流量、突发流量、Pod 故障、地域故障。

### 问题 8：蓝绿部署和金丝雀发布在 LLM 场景下如何选择？

**参考答案**：

| 维度 | 蓝绿部署 | 金丝雀发布 |
|------|----------|-----------|
| 风险 | 较高（一次性全量切换） | 较低（逐步放量） |
| 回滚速度 | 极快（切回旧环境） | 中等（逐步缩量） |
| 资源成本 | 高（需要两套完整环境） | 低（只需额外少量副本） |
| 验证能力 | 弱（只有切换后才能观察） | 强（持续对比新旧版本） |
| 适用场景 | 稳定版本替换、紧急修复 | 模型更新、配置变更 |

LLM 场景建议：
- **模型权重更新**：使用金丝雀发布，逐步验证质量
- **服务代码升级**：使用蓝绿部署，快速切换和回滚
- **紧急修复**：使用蓝绿部署，最小化故障时间
- **Prompt 模板变更**：使用金丝雀发布，验证输出质量

### 问题 9：在 LLM 服务中，如何设计限流策略才能既保护服务又不过度限制合法用户？

**参考答案**：

LLM 限流策略设计需要考虑以下维度：

1. **按租户限流**：每个租户独立配额，避免单个大客户冲垮共享服务
2. **按模型限流**：不同模型资源消耗不同，应有不同限额
3. **按 token 限流**：不只限制请求数，还要限制总 token 消耗
4. **优先级队列**：高优先级租户的请求优先处理
5. **弹性限流**：在系统负载低时自动放宽限制
6. **429 响应语义**：返回 `Retry-After` 头部，告知客户端何时重试

```yaml
# 多维度限流配置示例
descriptors:
  - key: tenant_id
    value: "premium"
    rate_limit:
      requests_per_unit: 500
      tokens_per_unit: 1000000
      unit: minute
  - key: tenant_id
    value: "standard"
    rate_limit:
      requests_per_unit: 100
      tokens_per_unit: 200000
      unit: minute
```

### 问题 10：如何验证熔断器配置是否合理？

**参考答案**：

验证熔断器配置需要关注以下方面：

1. **阈值合理性**：错误率阈值是否太敏感（频繁触发）或太宽松（不起作用）
2. **恢复速度**：半开状态的探测频率和数量是否合理
3. **级联影响**：熔断后是否影响了上游服务
4. **误伤率**：是否因为阈值设置不当而错误地摘除了健康实例

验证方法：
- 在测试环境注入故障（延迟注入、错误注入），观察熔断行为
- 分析历史告警数据，确认熔断器是否在该触发时触发
- 监控 `outlier_detection.ejections_active` 指标，确认摘除率是否合理
- 定期审查熔断器配置，根据服务变化调整阈值

---

## 📚 深入阅读

- [02-glossary.md](./02-glossary.md) - 术语表，包含本章涉及的所有专业术语
- [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) - 推理引擎与服务架构，本章的前置基础
- [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) - 推理性能工程，扩缩容指标的底层原理
- [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) - 可观测性与 SLO，本章指标体系的基础
- [Kubernetes HPA 官方文档](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [KEDA 官方文档](https://keda.sh/docs/)
- [Istio 流量管理](https://istio.io/latest/docs/tasks/traffic-management/)
- [Flagger 金丝雀发布](https://docs.flagger.app/)
- [Google SRE Book - Managing Risk](https://sre.google/sre-book/managing-risk/)

---

## ✅ 自检清单

完成本章学习后，请确认你已掌握以下内容：

- [ ] 能够解释多副本、多 AZ、多地域部署的故障域差异和适用场景
- [ ] 能够画出 Active-Active 多地域架构图，并说明数据同步策略
- [ ] 能够编写 KEDA ScaledObject 配置，使用 queue_time_p95 和 kv_cache_usage_ratio 作为扩缩容指标
- [ ] 能够编写 HPA 自定义指标配置，并解释 scaleUp/scaleDown 的行为参数
- [ ] 能够配置 Istio VirtualService 实现金丝雀流量分配
- [ ] 能够解释金丝雀发布中需要监控的质量指标（不只是错误率）
- [ ] 能够画出熔断器状态机，并解释 CLOSED/OPEN/HALF-OPEN 的转换条件
- [ ] 能够配置 Envoy 的熔断器和限流中间件
- [ ] 能够设计 LLM 服务的 Fallback 决策树（模型级、功能级、质量级、容量级）
- [ ] 能够解释降级的层次策略（上下文缩短、功能关闭、输出限制）
- [ ] 能够诊断流量突增导致的服务雪崩，并设计预防措施
- [ ] 能够诊断金丝雀发布后的质量回退，并设计质量守护门禁
- [ ] 能够回答关于扩缩容指标选择、熔断 vs 限流 vs 降级、多地域一致性等面试问题
