# LLM SRE 学习路线图

本路线图面向已有 Linux、容器、Kubernetes、监控告警和基础云平台知识的 SRE 和平台工程师。目标不是成为模型研究员，而是建立"能把 LLM 服务稳定、可观测、可扩展、可控地跑起来"的工程能力。

路线图将全部内容分为三个层级：**必学**（8 个核心主题）构建基础认知和推理平台核心能力，**进阶**（6 个专题）补齐治理、成本和数据面的系统能力，**前沿追踪**（持续更新）帮你判断哪些新方向值得投入。按每周 20-25 小时投入计算，三周可以跑通必学主线，进阶和前沿按需穿插。

---

## 学习路径总览

下面的 ASCII 图展示从零到生产就绪的整体学习流向。左侧是时间轴，右侧是能力目标。

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                         LLM SRE 学习路径总览                                │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  第 1 周：建立全局认知                                                       │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
  │  │ 10 生命周期│───▶│ 12 GPU与 │───▶│ 16 推理  │───▶│ 18 可观测│              │
  │  │   总览    │    │ 集群底座 │    │ 引擎架构 │    │ 性与SLO  │              │
  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
  │       │                               │                │                    │
  │       ▼                               ▼                ▼                    │
  │  第 2 周：推理平台核心                                                       │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐                               │
  │  │ 13 分布式│    │ 17 推理  │    │ 19 可靠性│                               │
  │  │ 训练容错 │    │ 性能工程 │    │ 扩缩容   │                               │
  │  └──────────┘    └──────────┘    └──────────┘                               │
  │       │                               │                │                    │
  │       ▼                               ▼                ▼                    │
  │  第 3 周：应用层与治理                                                       │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐                               │
  │  │ 20 RAG   │    │ 21 安全  │    │ 22 前沿  │                               │
  │  │ Agent平台│    │ 合规治理 │    │ 主题追踪 │                               │
  │  └──────────┘    └──────────┘    └──────────┘                               │
  │                                                                             │
  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
  │                                                                             │
  │  持续进阶（按需穿插）                                                        │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
  │  │安全合规  │  │训练观测  │  │模型制品  │  │数据工程  │  │多租户混合│     │
  │  │与治理    │  │与容量    │  │版本治理  │  │Pipeline  │  │部署策略  │     │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘
```

三个层级之间的关系：

- **必学**是地基。不理解生命周期和推理指标，进阶内容会变成碎片知识。
- **进阶**是系统能力。把单点知识串成平台视角：谁来用、怎么隔离、怎么计费、怎么回滚。
- **前沿**是决策输入。不需要全部深入，但要能判断"这个方向是否影响我们未来 6 个月的架构"。

---

## 必学模块（8 个核心主题）

必学模块按依赖顺序排列。建议按编号顺序学习，但 12/13 可并行、17/18 可并行。

---

### 1. LLM 生命周期总览

> 一句话：搞清楚 LLM 从数据到应用的完整链路，以及 SRE 在每个环节的职责边界。

- **预计学习时间**：3-4 小时
- **关键产出**：
  - 能画出预训练、微调、推理三阶段的目标、成本结构与责任边界
  - 能判断一个线上问题应该归属哪个阶段、由谁主导排查
  - 能解释为什么"只管推理"远远不够——数据和模型制品的治理直接影响推理稳定性
- **对应文档**：[10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)
- **知识依赖**：无（这是整个主题的入口）

---

### 2. 训练基础设施与 GPU 集群

> 一句话：理解 GPU 集群的组织方式——节点、网络、驱动、存储和调度系统如何协同，SRE 应该监控什么。

- **预计学习时间**：5-6 小时
- **关键产出**：
  - 能解释 GPU 显存、PCIe/NVLink 带宽、拓扑对训练性能的影响
  - 能列出自建集群和云托管集群各自需要关注的故障面
  - 能配置 GPU 节点级别的基础监控指标（XID 错误、ECC、温度、功耗）
- **对应文档**：[12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md)
- **知识依赖**：需要先学 [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)

---

### 3. 分布式训练与容错

> 一句话：搞懂分布式训练为什么难以稳定运行，以及 checkpoint 和容错策略如何设计。

- **预计学习时间**：6-8 小时
- **关键产出**：
  - 能解释 TP、PP、EP、DP 四种并行方式的适用边界、网络压力和故障半径
  - 能设计 checkpoint 策略（频率、存储、恢复时间目标）
  - 能判断一个训练任务挂掉后应该从哪里恢复、恢复需要多长时间
- **对应文档**：[13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md)
- **知识依赖**：需要先学 [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md)

---

### 4. 推理引擎与服务架构

> 一句话：理解推理服务的系统边界——引擎选型、网关设计、路由策略、冷启动和容量治理。

- **预计学习时间**：6-8 小时
- **关键产出**：
  - 能对比 vLLM、SGLang、TGI、Triton、TensorRT-LLM 的适用场景和资源约束
  - 能设计包含鉴权、调度、缓存、发布、观测和回滚的推理服务架构
  - 能解释 Paged Attention、Prefix Cache 等核心机制如何影响服务行为
- **对应文档**：[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)
- **知识依赖**：需要先学 [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)

---

### 5. 推理性能工程

> 一句话：聚焦 TTFT、TPOT、TPS 为什么变慢或抖动，以及哪些优化手段值得投入。

- **预计学习时间**：5-6 小时
- **关键产出**：
  - 能定位 TTFT 慢的根因：prefill 阶段计算、KV Cache 分配、调度排队
  - 能分析 TPOT 抖动来源：decode 批处理策略、显存碎片、多租户干扰
  - 能评估量化、投机解码、Chunked Prefill 等优化手段的收益与代价
- **对应文档**：[17-inference-performance-engineering.md](./17-inference-performance-engineering.md)
- **知识依赖**：需要先学 [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)

---

### 6. 推理可观测性与 SLO

> 一句话：设计推理服务的指标体系、SLO 和告警策略，建立从告警到根因的排查链路。

- **预计学习时间**：5-6 小时
- **关键产出**：
  - 能定义推理服务的核心 SLO：TTFT p99、TPOT p95、错误率、可用性
  - 能设计覆盖"慢、错、贵、抖"四个维度的告警规则
  - 能在事故中从指标、日志和链路追踪拼出根因链路，而不是只盯 GPU 利用率
- **对应文档**：[18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md)
- **知识依赖**：需要先学 [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)

---

### 7. 可靠性、扩缩容与多地域

> 一句话：让推理服务在流量波动、实例故障、区域故障和发布变更下保持可用。

- **预计学习时间**：6-8 小时
- **关键产出**：
  - 能设计 GPU 实例的弹性扩缩策略（冷启动开销、预热池、队列缓冲）
  - 能制定滚动升级和灰度发布方案，避免模型切换期间的请求丢失
  - 能设计多地域部署和故障切流方案，理解跨区域 KV Cache 同步的挑战
- **对应文档**：[19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md)
- **知识依赖**：需要先学 [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md)、[17-inference-performance-engineering.md](./17-inference-performance-engineering.md)

---

### 8. RAG、Agent 与应用平台

> 一句话：把"模型调用"扩展成可运行、可观测、可治理的完整应用系统。

- **预计学习时间**：5-6 小时
- **关键产出**：
  - 能诊断 RAG 链路的延迟瓶颈：检索、embedding、重排、上下文膨胀各环节的耗时分布
  - 能设计 Agent 工具调用的超时、重试和降级策略
  - 能评估向量库索引更新频率、embedding 漂移对线上质量的影响
- **对应文档**：[20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md)
- **知识依赖**：需要先学 [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md)、[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)

---

## 进阶模块（6 个专题）

进阶模块不强制学习顺序，按实际工作需要选择。每个专题都假设你已经完成必学模块中的相关内容。

---

### 1. 安全合规与治理

> 一句话：控制模型访问、阻断滥用、保护敏感数据并建立审计与归因能力。

- **预计学习时间**：4-5 小时
- **关键产出**：
  - 能设计 Prompt 注入检测和输出过滤的分层防御方案
  - 能实现模型访问的 RBAC 和 API Key 分级管理
  - 能建立请求级审计日志，满足合规回溯需求
- **对应文档**：[21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md)
- **知识依赖**：需要先学 [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md)（审计依赖可观测性基础设施）

---

### 2. 训练可观测性与容量

> 一句话：监控训练任务的资源使用、吞吐趋势和异常模式，为容量规划提供数据支撑。

- **预计学习时间**：4-5 小时
- **关键产出**：
  - 能设计训练任务级别的指标采集：MFU、loss 曲线、通信耗时、checkpoint 耗时
  - 能建立 GPU 集群利用率看板，识别闲置和热点
  - 能基于历史训练数据估算新任务的资源需求和排队时间
- **对应文档**：[12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md)（容量规划部分）、[13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md)（容错与监控部分）
- **知识依赖**：需要先学 [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md)、[13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md)

---

### 3. 模型制品与版本治理

> 一句话：管理模型权重、Adapter、tokenizer 等制品的版本、存储和回滚。

- **预计学习时间**：3-4 小时
- **关键产出**：
  - 能设计模型制品的版本命名、存储位置和生命周期策略
  - 能实现 LoRA/QLoRA Adapter 的热加载和快速回滚
  - 能建立模型制品与推理服务版本的映射关系，支持事故时的精确定位
- **对应文档**：[10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)（制品管理部分）、[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)（模型加载部分）
- **知识依赖**：需要先学 [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)、[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)

---

### 4. 数据工程

> 一句话：管理训练和 RAG 所依赖的数据 Pipeline——采集、清洗、标注、版本化和质量监控。

- **预计学习时间**：4-5 小时
- **关键产出**：
  - 能设计数据 Pipeline 的质量门禁：格式校验、去重率、毒性检测、PII 脱敏
  - 能建立数据版本与模型版本的追溯链路
  - 能诊断 embedding 索引陈旧导致的 RAG 质量下降问题
- **对应文档**：[10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)（数据阶段部分）、[20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md)（索引更新部分）
- **知识依赖**：需要先学 [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)、[20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md)

---

### 5. 多租户治理

> 一句话：在共享推理平台上实现配额、优先级、隔离和成本分摊。

- **预计学习时间**：4-5 小时
- **关键产出**：
  - 能设计基于请求优先级的调度策略，确保高优先级请求的 SLO
  - 能实现租户级别的配额管理和资源隔离（GPU 时间、并发数、队列深度）
  - 能建立按 token 用量的成本归因和分摊模型
- **对应文档**：[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)（多租户部分）、[17-inference-performance-engineering.md](./17-inference-performance-engineering.md)（隔离与干扰部分）
- **知识依赖**：需要先学 [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)、[17-inference-performance-engineering.md](./17-inference-performance-engineering.md)

---

### 6. 混合部署策略

> 一句话：在不同模型大小、不同 GPU 代际、在线/离线推理之间做出合理的混部决策。

- **预计学习时间**：3-4 小时
- **关键产出**：
  - 能评估不同 GPU 代际（A100/H100/L40S）对同一模型的性价比差异
  - 能设计在线推理和离线批处理的混部策略，利用时间窗口错峰
  - 能制定模型大小与 GPU 规格的匹配矩阵，避免资源浪费或性能不足
- **对应文档**：[19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md)（扩缩容策略部分）、[22-frontier-topics.md](./22-frontier-topics.md)（异构加速器部分）
- **知识依赖**：需要先学 [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md)、[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)

---

## 前沿追踪模块

前沿主题仍在快速演进，尚未形成稳定的平台定式。本模块不是核心入门材料，而是帮你判断哪些方向值得持续观察、试点或预研。

**跟踪原则**：

- **信号优先**：关注已经在生产环境被验证过至少一次的方向，而非纯学术论文。
- **容量影响优先**：优先跟踪直接影响容量、延迟、成本或运行模式变化的方向。
- **每周投入 1-2 小时**：1 个推理框架 release notes + 1 篇工程博客 + 1 个生产案例。

**当前值得跟踪的方向**（详见 [22-frontier-topics.md](./22-frontier-topics.md)）：

| 方向 | 影响面 | 深入时机 |
|------|--------|----------|
| MoE 推理调度与专家负载倾斜 | 容量规划、GPU 利用率 | 当团队开始部署 MoE 模型时 |
| Prefill/Decode 解耦架构 | 延迟、吞吐、成本 | 当当前架构的 TTFT/TPOT 无法同时满足 SLO 时 |
| 异构加速器与远端 KV Cache | 部署灵活性、成本 | 当 GPU 供应成为瓶颈或跨节点缓存成为需求时 |
| Agent 基础设施演进 | 可观测性、可靠性 | 当 Agent 调用链路的故障率开始影响业务时 |
| 投机解码与动态批处理 | 吞吐、成本 | 当在线推理成本占比超过预算 40% 时 |
| 模型越权与数据外泄防御 | 安全、合规 | 当平台接入企业敏感数据或多租户场景时 |

**何时深钻 vs 只看信号**：

- **深钻**：该方向已经出现在你的技术雷达的"采纳"或"试验"象限，且有明确的落地场景。
- **只看信号**：该方向仍在"评估"象限，或你的团队在未来 6 个月内不会遇到相关场景。

---

## 建议学习节奏

### 第 1 周：基础认知

**目标**：建立全局图，理解 LLM 服务的完整链路和核心指标。

| 天数 | 学习内容 | 时长 | 产出 |
|------|----------|------|------|
| Day 1-2 | 10 生命周期总览 | 3-4h | 能画出完整链路图，标注 SRE 职责边界 |
| Day 3-4 | 12 GPU 与集群底座 | 5-6h | 能列出 GPU 节点关键监控指标 |
| Day 5-6 | 16 推理引擎架构 | 6-8h | 能对比主流引擎的适用场景 |
| Day 7 | 18 可观测性与 SLO | 5-6h | 能定义推理服务核心 SLO |

**本周检查点**：能否回答"一个推理请求从进来到出去，经过了哪些组件、哪些指标能反映它好不好"。

---

### 第 2 周：推理平台核心

**目标**：把"能跑"推进到"能稳"——掌握性能调优、可靠性和容错。

| 天数 | 学习内容 | 时长 | 产出 |
|------|----------|------|------|
| Day 1-2 | 17 推理性能工程 | 5-6h | 能定位 TTFT/TPOT 慢的根因 |
| Day 3-4 | 13 分布式训练与容错 | 6-8h | 能设计 checkpoint 和恢复策略 |
| Day 5-7 | 19 可靠性扩缩容 | 6-8h | 能设计弹性扩缩和灰度发布方案 |

**本周检查点**：能否回答"服务变慢了，从告警到根因的排查路径是什么；实例挂了，恢复流程是什么"。

---

### 第 3 周：应用层与治理

**目标**：把"单点知识"串成系统能力——理解应用层依赖和安全治理。

| 天数 | 学习内容 | 时长 | 产出 |
|------|----------|------|------|
| Day 1-3 | 20 RAG/Agent 平台 | 5-6h | 能诊断 RAG 链路的延迟瓶颈 |
| Day 4-5 | 21 安全合规治理 | 4-5h | 能设计分层防御方案 |
| Day 6-7 | 22 前沿主题浏览 | 2-3h | 建立持续跟踪的习惯和信息源 |

**本周检查点**：能否回答"一个 RAG 请求的端到端链路中，哪些环节可能出安全问题、哪些环节可能出性能问题"。

---

### 按需：进阶与前沿

完成三周主线后，根据实际工作需要选择进阶模块：

- **接到多租户需求**：优先学"多租户治理"和"混合部署策略"。
- **开始管理训练集群**：优先学"训练可观测性与容量"。
- **模型迭代加速**：优先学"模型制品与版本治理"和"数据工程"。
- **每周固定投入**：1-2 小时跟踪前沿方向，保持技术敏感度。

---

## 按角色定制路径

不同角色的学习侧重点不同。下面是三种常见角色的建议路径。

---

### SRE 工程师

**核心职责**：保障推理服务的可用性、延迟和成本在可控范围内。

**学习优先级**：

```
必学（全部按顺序）──▶ 进阶：安全合规 ──▶ 进阶：多租户治理 ──▶ 前沿追踪
                                         └──▶ 进阶：混合部署策略
```

**重点深入**：

- 推理可观测性与 SLO（建立告警和排查能力）
- 可靠性、扩缩容与多地域（掌握故障恢复和弹性策略）
- 推理性能工程（能定位慢请求的根因）

**可以暂缓**：

- 训练基础设施的底层细节（除非同时负责训练集群）
- 数据工程的 Pipeline 实现（除非 RAG 质量问题直接影响推理 SLO）

---

### 平台工程师

**核心职责**：构建和维护推理/训练平台，为上层业务提供自助能力。

**学习优先级**：

```
必学（全部按顺序）──▶ 进阶：多租户治理 ──▶ 进阶：模型制品版本治理 ──▶ 进阶：混合部署策略
                      └──▶ 进阶：数据工程 ──▶ 前沿追踪
```

**重点深入**：

- 推理引擎与服务架构（平台的核心组件选型和设计）
- 训练基础设施与 GPU 集群（平台底座的规划和运维）
- 多租户治理（平台规模化的核心挑战）

**可以暂缓**：

- 单次事故的排查细节（这是 SRE 的核心职责）
- 前沿方向的深度调研（关注信号即可，SRE 会推动落地评估）

---

### 值班负责人

**核心职责**：在事故中快速定位问题、协调资源、恢复服务。

**学习优先级**：

```
必学 10（生命周期）──▶ 必学 16（推理架构）──▶ 必学 18（可观测性）──▶ 必学 19（可靠性）
                                                    │
                                                    ├──▶ 必学 17（性能工程）
                                                    │
                                                    └──▶ 进阶：安全合规
```

**重点深入**：

- 推理可观测性与 SLO（值班的核心技能——从告警到根因）
- 可靠性、扩缩容与多地域（故障恢复的标准操作）
- 推理引擎与服务架构（知道问题出在哪个组件）

**可以暂缓**：

- 训练侧内容（除非值班范围覆盖训练集群）
- 数据工程和前沿追踪（按需补充即可）

**值班速查**：完成上述路径后，建议配合 [30-production-readiness-checklist.md](./30-production-readiness-checklist.md)（生产就绪检查清单）和 [31-incident-runbook.md](./31-incident-runbook.md)（事故应急手册）建立值班工具箱。

---

## 知识依赖图

下面的 ASCII 图展示各文档之间的依赖关系。箭头表示"建议先学"。虚线表示"有帮助但非必须"。

```
                              ┌──────────────┐
                              │ 10 生命周期   │
                              │    总览       │
                              └──────┬───────┘
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                   ┌──────────┐ ┌──────────┐ ┌──────────┐
                   │ 12 GPU与 │ │ 16 推理  │ │ 21 安全  │
                   │ 集群底座 │ │ 引擎架构 │ │ 合规治理 │
                   └────┬─────┘ └────┬─────┘ └──────────┘
                        ▼            │
                   ┌──────────┐      ├──────────────────┐
                   │ 13 分布式│      ▼          ▼       │
                   │ 训练容错 │ ┌──────────┐ ┌──────────┐│
                   └──────────┘ │ 17 推理  │ │ 18 可观测││
                                │ 性能工程 │ │ 性与SLO  ││
                                └────┬─────┘ └────┬─────┘│
                                     │            │      │
                                     ▼            ▼      │
                                ┌──────────────────┐     │
                                │ 19 可靠性扩缩容   │     │
                                └────────┬─────────┘     │
                                         │               │
                                         ▼               ▼
                                ┌──────────────────────────┐
                                │ 20 RAG/Agent 应用平台     │
                                └──────────────────────────┘

                     ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
                       进阶模块（可选，按需深入）
                     │                                       │
                       22 前沿主题 ← 持续跟踪，不设终点
                     │                                       │
                       辅助文档：
                       02-glossary.md        术语表
                     │ 03-reference-map.md   参考资料索引
                       30-production-readiness-checklist.md
                     │ 31-incident-runbook.md
                       32-capacity-planning-cheatsheet.md
                     └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

**读图说明**：

- 从 10 出发的三条路径分别指向训练侧（12→13）、推理侧（16→17/18→19→20）和治理侧（21）。
- 训练侧（12→13）和推理侧（16→17/18）可以并行学习，两者在"混合部署"处汇合。
- 19（可靠性）是推理侧的集大成章节，依赖 17 和 18 的知识。
- 20（RAG/Agent）是应用层的集大成章节，依赖 19 和 16 的知识。
- 21（安全合规）相对独立，但理解 18 的可观测性基础设施有助于设计审计方案。

---

## 附：辅助文档索引

| 文档 | 用途 | 何时使用 |
|------|------|----------|
| [02-glossary.md](./02-glossary.md) | 术语表 | 遇到不熟悉的缩写或概念时查阅 |
| [03-reference-map.md](./03-reference-map.md) | 参考资料索引 | 需要原始论文、官方文档或工程博客时查阅 |
| [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) | 生产就绪检查清单 | 模型或服务上线前逐项检查 |
| [31-incident-runbook.md](./31-incident-runbook.md) | 事故应急手册 | 值班时遇到告警或事故时查阅 |
| [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) | 容量规划速查表 | 评估资源需求或做容量预算时查阅 |
