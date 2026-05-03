# LLM SRE 学习专题资料 - 设计文档

> 日期：2026-05-03
> 状态：Approved
> 范围：`docs/llm-sre/` 专题目录第一版

## 背景

当前仓库已经包含一组 LLMOps 相关文档，主要集中在 `docs/day161-172`。这些文档覆盖了推理部署、GPU 运维、监控、高可用、RAG、安全等主题，但整体存在三个问题：

1. 生命周期覆盖不完整，训练基础设施、分布式训练、训练容错、模型制品治理等内容明显不足。
2. 文档结构偏课程日更风格，不适合作为专题知识库长期维护和持续扩展。
3. 部分文档质量不稳定，存在深度不一致和主题偏移问题，不能直接作为完整专题骨架复用。

目标是在不打乱现有 `dayXXX` 体系的前提下，新增一套独立的 `docs/llm-sre/` 专题资料，面向 SRE 主导、兼顾平台工程的学习与查阅场景，覆盖大模型训练到推理的全生命周期，并对业内前沿方向做分层整理。

## 设计目标

1. **读者定位明确**：以运维/SRE 为主读者，兼顾 AI 平台工程师，而不是研究员或纯算法工程师。
2. **生命周期完整**：覆盖数据、训练、评测、制品、推理、观测、容量、成本、可靠性、安全、应用平台扩展。
3. **兼顾两类场景**：既能按顺序系统学习，也能在值班、设计评审、排障时快速查阅。
4. **前沿内容有边界**：既覆盖当前业内热点，又避免变成论文罗列或厂商产品大全。
5. **易于演进维护**：信息架构稳定，文档模板统一，便于后续继续补充专题内容。

## 非目标

以下内容不作为第一版目标：

1. 不重写现有全部 `day161-172` 文档。
2. 不把专题内容重新映射回 `dayXXX` 课程体系。
3. 不做纯研究导向的算法推导、论文精读或数学证明。
4. 不做各家云厂商、推理引擎、向量数据库的穷举式大全。
5. 不在第一版内覆盖所有前沿方向的深度实践细节。

## 目标读者与使用方式

### 目标读者

1. 已具备基础 Linux、网络、容器、Kubernetes、可观测性知识的 SRE。
2. 需要理解 LLM 平台基础设施的运维工程师。
3. 负责训练平台、推理平台、RAG 平台或 AI 应用平台交付的平台工程师。

### 使用方式

1. **系统学习**
按 `README` 和 `01-roadmap.md` 给出的顺序，从生命周期总览开始阅读，再进入训练、推理、RAG、安全等专题。

2. **知识速查**
遇到指标、容量、故障、架构评审等问题时，直接进入 `20-运行手册层` 中的 checklist、runbook 和 cheatsheet。

3. **方案设计**
在做训练平台、推理平台和 AI 应用平台设计时，使用主教程中的设计权衡部分和运行手册中的评审模板。

## 信息架构

专题目录采用三层结构：

### `00-导航层`

作用是建立专题入口、路线图和资料地图，解决“先看什么、遇到问题去哪查”的问题。

计划包含：

- `README.md`
- `01-roadmap.md`
- `02-glossary.md`
- `03-reference-map.md`

### `10-主教程层`

作用是按大模型生命周期组织系统教程，覆盖从数据、训练、交付到推理和应用平台的关键工程问题。

计划包含：

- `10-llm-lifecycle-overview.md`
- `11-data-and-dataset-engineering.md`
- `12-training-infrastructure-and-gpu-clusters.md`
- `13-distributed-training-and-fault-tolerance.md`
- `14-training-observability-capacity-and-cost.md`
- `15-model-artifacts-registry-and-release.md`
- `16-inference-engines-and-serving-architecture.md`
- `17-inference-performance-engineering.md`
- `18-inference-observability-and-slo.md`
- `19-reliability-scaling-and-multi-region.md`
- `20-rag-agent-and-application-platform.md`
- `21-security-compliance-and-governance.md`
- `22-frontier-topics.md`

### `20-运行手册层`

作用是提供可直接用于上线评审、容量估算、值班排障和 dashboard 使用的操作性文档。

计划包含：

- `30-production-readiness-checklist.md`
- `31-incident-runbook.md`
- `32-capacity-planning-cheatsheet.md`
- `33-architecture-review-template.md`
- `34-oncall-metrics-dashboard-guide.md`

## 文档清单与边界

### 导航层文档

#### `README.md`

说明专题目标、读者对象、阅读顺序、与现有 `day161-172` 的关系，以及专题目录结构。

#### `01-roadmap.md`

按三层难度组织学习路线：

1. 必学
2. 进阶
3. 前沿跟踪

该文档负责告诉读者“什么必须掌握，什么可以后续补充”。

#### `02-glossary.md`

统一常见术语，避免多个主题反复解释同一概念。重点覆盖：

- TTFT、TPOT、TPS、E2E latency
- Prefill、Decode、KV Cache
- TP、PP、DP、EP、ZeRO、FSDP
- LoRA、QLoRA、MoE
- RAG、reranker、embedding、hybrid search
- Canary、shadow traffic、fallback、guardrail

#### `03-reference-map.md`

整理官方文档、论文、博客、开源项目和基准测试资料，作为索引而不是正文堆链接。

### 主教程层文档

#### `10-llm-lifecycle-overview.md`

从平台视角串起完整生命周期：

1. 数据与样本工程
2. 训练任务与集群
3. 模型评测与验收
4. 模型制品与版本治理
5. 推理部署与服务化
6. 观测、容量、成本、治理
7. RAG / Agent / 应用平台扩展

该文档是专题的总入口。

#### `11-data-and-dataset-engineering.md`

从 SRE 和平台工程视角讲数据工程，重点包括：

1. 数据源接入和权限边界
2. 清洗、去重、抽样、配比
3. 数据版本化和数据血缘
4. 训练数据与评测数据隔离
5. 数据存储、缓存和传输瓶颈
6. 数据安全与合规要求

#### `12-training-infrastructure-and-gpu-clusters.md`

重点讲训练平台的基础设施面，包括：

1. GPU 节点、NVLink、PCIe、RDMA、IB 网络
2. 镜像、驱动、CUDA、NCCL、容器运行时
3. K8s、Slurm 等调度体系的适用边界
4. 存储与 checkpoint I/O
5. 节点拓扑感知和资源隔离
6. 集群健康检查与变更管理

#### `13-distributed-training-and-fault-tolerance.md`

重点讲训练执行时的工程问题，包括：

1. DDP、FSDP、ZeRO、TP、PP、EP 的工程含义
2. 作业编排和 rank 拓扑
3. Checkpoint、resume、断点续训
4. 节点故障、NCCL hang、网络抖动处理
5. Spot / preemptible 资源策略
6. 失败重试与训练作业 SLA

#### `14-training-observability-capacity-and-cost.md`

重点讲训练期的观测和规划，包括：

1. GPU 利用率、MFU、吞吐、样本处理速率
2. 数据加载瓶颈、网络瓶颈、checkpoint 耗时
3. 训练成本模型和容量估算
4. 调参、批大小、并行策略对资源的影响
5. 训练任务告警与 dashboard

#### `15-model-artifacts-registry-and-release.md`

重点讲训练完成后的模型交付治理，包括：

1. 权重、tokenizer、config、adapter、量化产物管理
2. 模型注册与元数据管理
3. 版本命名、可追溯性、签名和校验
4. 从训练产物到推理产物的转换流程
5. 模型验收门禁和发布审批

#### `16-inference-engines-and-serving-architecture.md`

重点讲推理引擎与服务架构的选型边界，包括：

1. vLLM、SGLang、TGI、Triton、TensorRT-LLM 的定位
2. OpenAI 兼容 API、网关、鉴权、路由
3. 单模型、多模型、多租户部署模式
4. 冷启动、模型加载、缓存与预热

#### `17-inference-performance-engineering.md`

重点讲推理性能工程，包括：

1. Prefill/Decode 分解
2. KV Cache、paged attention、continuous batching
3. PD 分离、speculative decoding、prompt/prefix cache
4. 多 LoRA、多模型复用
5. 量化和显存优化
6. 不同优化手段的收益与副作用

#### `18-inference-observability-and-slo.md`

重点讲推理阶段的 SLO 与观测，包括：

1. TTFT、TPOT、tokens/s、queue time
2. GPU/CPU/显存/缓存指标
3. 请求级 tracing 和质量信号
4. 用户体验与基础设施指标的映射
5. 告警规则、SLO 和错误预算

#### `19-reliability-scaling-and-multi-region.md`

重点讲高可用与扩缩容，包括：

1. 多副本、多机房、多地域部署
2. HPA、KEDA、自定义指标扩缩容
3. 蓝绿、金丝雀、shadow traffic
4. fallback、熔断、限流、降级
5. 故障转移与灾备策略

#### `20-rag-agent-and-application-platform.md`

重点讲应用平台扩展，包括：

1. RAG 摄取、索引、检索、重排、生成链路
2. Embedding 服务和向量数据库运维
3. Agent runtime、tool calling、memory、session state
4. 在线评测和质量回路
5. AI 平台从模型服务到应用服务的边界

#### `21-security-compliance-and-governance.md`

重点讲安全与治理，包括：

1. 模型和数据资产访问控制
2. Prompt 注入、越权调用、内容安全
3. PII、审计、密钥与凭据管理
4. 多租户隔离和成本归因
5. 合规要求与企业治理要求

#### `22-frontier-topics.md`

该文档只做分层追踪，不做论文课。每个主题都回答四个问题：

1. 这是什么
2. 为什么重要
3. 对 SRE/平台工程有什么影响
4. 观察哪些指标和信号决定是否值得引入

第一版覆盖：

- MoE serving 与 expert parallel
- ultra-long context 与 context compression
- prefill-decode disaggregation
- SGLang 和结构化生成 runtime
- FP8 / INT4 推理落地
- inference cache hierarchy
- agent runtime 和 tool execution sandbox
- synthetic data 与自动评测流水线
- model routing 与 small-large cascade

### 运行手册层文档

#### `30-production-readiness-checklist.md`

用于训练平台、推理平台和 RAG 平台上线前检查，覆盖：

1. 容量
2. 可观测性
3. 回滚
4. 权限
5. 灰度
6. 审计
7. 故障演练

#### `31-incident-runbook.md`

覆盖常见事故场景，例如：

1. GPU OOM
2. 模型加载失败
3. TTFT 飙升
4. Tokens/s 明显下降
5. NCCL hang
6. 向量检索超时
7. 模型质量突然回退

#### `32-capacity-planning-cheatsheet.md`

提供容量估算公式、压测口径、样例和扩容决策参考。

#### `33-architecture-review-template.md`

提供训练平台、推理平台、RAG 平台架构评审的检查模板。

#### `34-oncall-metrics-dashboard-guide.md`

说明值班视角应该关注哪些图、如何解释、什么阈值需要动作。

## 写作模板

### 主教程模板

每篇主教程采用统一结构：

1. 这篇文档解决什么问题
2. 系统全景
3. 核心机制
4. SRE / 平台工程关注点
5. 关键指标与告警
6. 典型故障与排查路径
7. 设计权衡
8. 实践建议
9. 扩展阅读

该模板的目标是避免文档退化为“概念介绍 + 大段示例代码”，而是优先帮助读者理解工程边界和设计决策。

### 运行手册模板

每篇运行手册采用统一结构：

1. 适用场景
2. 前置检查
3. 排查步骤
4. 止血动作
5. 根因定位
6. 事后改进
7. 关联指标 / 日志 / 命令

这样可以把“系统教程”和“值班手册”清晰分离。

## 前沿内容分层

前沿内容采用三层分类，避免专题正文被热点堆积破坏结构。

### 核心必学

这些内容已经进入主流生产实践，应进入主教程正文：

- LoRA / QLoRA
- KV Cache
- continuous batching
- paged attention
- quantization 基础
- TTFT / TPOT / tokens per second
- GPU 调度与多副本高可用
- RAG 基础架构
- 数据、模型、prompt 版本管理

### 进阶必知

这些内容在成熟团队中较常见，应在主教程中介绍，但深度低于核心部分：

- FSDP / DeepSpeed / ZeRO
- NCCL、RDMA、NVLink、拓扑感知调度
- speculative decoding
- prompt / prefix cache
- 多 LoRA 服务
- reranker / hybrid search
- online eval / canary / shadow traffic
- 多租户隔离与成本归因

### 前沿追踪

这些内容统一收敛到 `22-frontier-topics.md`，重点关注适用条件和观测信号：

- MoE serving
- prefill-decode disaggregation
- SGLang
- FP8 / INT4 大规模落地
- ultra-long context
- agent runtime
- inference cache hierarchy
- synthetic data
- model routing

## 与现有文档的关系

现有 `docs/day161-172` 不删除、不重写为第一版前置条件。

处理策略如下：

1. 将其视为历史课程资料和局部参考素材。
2. 新专题内容独立成目录，不依赖原有课程结构。
3. 对质量较好的内容吸收其主题边界和部分案例。
4. 对明显偏题或结构不稳的内容不直接复用。
5. 在专题首页说明新旧资料的定位差异。

## 第一版交付范围

第一版目标不是一次性写满整个知识库，而是交付一套完整可读、结构稳定的专题基础版。

第一版建议交付：

1. 导航层全部文档
2. 8-10 篇关键主教程
3. 3-5 篇运行手册

优先级顺序如下：

1. `README.md`
2. `01-roadmap.md`
3. `02-glossary.md`
4. `10-llm-lifecycle-overview.md`
5. `12-training-infrastructure-and-gpu-clusters.md`
6. `13-distributed-training-and-fault-tolerance.md`
7. `16-inference-engines-and-serving-architecture.md`
8. `17-inference-performance-engineering.md`
9. `18-inference-observability-and-slo.md`
10. `19-reliability-scaling-and-multi-region.md`
11. `20-rag-agent-and-application-platform.md`
12. `21-security-compliance-and-governance.md`
13. `22-frontier-topics.md`
14. `30-production-readiness-checklist.md`
15. `31-incident-runbook.md`
16. `32-capacity-planning-cheatsheet.md`

暂不纳入第一版的内容：

1. 各家云厂商专项方案对比大全
2. 过深的分布式训练算法推导
3. 全量论文综述
4. 细到单个开源项目配置参数全集

## 质量标准

1. 每篇文档必须有明确的目标读者和适用场景。
2. 每篇主教程必须解释工程机制和设计权衡，而不是只列术语。
3. 每篇运行手册必须能直接用于值班或评审，不写空泛原则。
4. 前沿内容必须解释工程影响和观察信号，不能只写热点摘要。
5. 所有文档结构统一，避免重复、冲突和概念漂移。
6. 不留 TODO、TBD 或空标题。

## 风险与控制

### 风险 1：范围过大，第一版难以完成

控制方式：

1. 先交付基础目录和高优先级主题。
2. 明确第一版不追求全量覆盖。

### 风险 2：文档变成课程讲义堆砌，不利于速查

控制方式：

1. 把教程层和运行手册层拆开。
2. 统一 runbook/checklist 模板。

### 风险 3：前沿内容过多，主线失焦

控制方式：

1. 用“核心必学 / 进阶必知 / 前沿追踪”三层收敛。
2. 把热点内容集中到 `22-frontier-topics.md`。

## 成功标准

满足以下条件即可认为本设计成功：

1. `docs/llm-sre/` 能作为独立专题入口使用。
2. 读者能按路线图完成系统学习，而不是在现有 `dayXXX` 结构中来回跳转。
3. 训练、推理、RAG、安全、可靠性、观测、前沿等主题都有清晰落点。
4. 值班、容量评估、上线评审可直接使用运行手册层文档。
5. 后续继续扩展专题时，不需要推翻当前信息架构。
