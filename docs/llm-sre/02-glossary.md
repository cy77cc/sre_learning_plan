# LLM SRE 术语表

## 使用说明

本术语表收录 LLM SRE 学习与运维实践中高频出现的术语，按领域分组，每个条目包含五列信息：

| 列名 | 说明 |
|---|---|
| 术语 | 英文原词或缩写 |
| 中文全称 | 中文翻译或展开 |
| 一句话解释 | 不超过两句话的核心定义 |
| 运维关注点 | 该术语在生产环境中的关键运维视角 |
| 首次出现文档 | 在本专题中首次详细讨论的文档，使用相对路径链接 |

使用建议：

- 遇到陌生术语时，先在本表确认其运维含义，再通过"首次出现文档"深入阅读。
- 不同领域的术语可能存在交叉，例如 KV Cache 同时涉及推理指标和显存管理，本文以最核心归属分组。
- 每个分类开头有简短的领域说明，帮助理解该组术语的共同背景。
- 术语关系图和易混淆术语辨析放在文末，适合在通读全表后对照查阅。

## 按领域分类的术语表

### 推理指标类

推理指标是 LLM SRE 日常盯盘和告警判断的核心依据。与传统 HTTP 服务不同，LLM 推理的延迟和吞吐需要同时从 token 级别和请求级别两个维度观察。传统服务关注 QPS 和 P99 延迟就够了，但 LLM 服务中同样 QPS 的两个请求，一个输入 10 token、一个输入 8000 token，实际负载差距可达数百倍。因此，SRE 必须同时掌握 token 级指标（TTFT、TPOT、TPS）和请求级指标（E2E Latency、Queue Time、Waiting Requests），才能准确判断系统健康状态。

延迟分位数（P50/P95/P99）在 LLM 场景下的含义也与传统服务不同：由于推理是非确定性的、延迟分布更宽，P99 与 P50 的差距通常比传统 HTTP 服务大得多，尾延迟问题更突出。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| TTFT | Time To First Token（首 token 延迟） | 从请求进入推理引擎到首个输出 token 返回给用户的时间间隔。 | 区分延迟来源：排队等待、Prefill 计算、KV Cache 命中或模型冷启动；TTFT 直接影响用户感知的响应速度。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| TPOT | Time Per Output Token（单 token 延迟） | 生成阶段每个输出 token 的平均耗时。 | 反映 Decode 阶段效率，与 GPU 带宽利用率、批大小、量化精度直接相关；TPOT 抖动大时检查批次内请求竞争。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| TPS | Tokens Per Second（每秒 token 数） | 推理系统每秒处理或生成的 token 总量。 | 比 QPS 更能反映推理负载强度；结合 TTFT 和 TPOT 可以判断系统是否处于健康吞吐区间。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| E2E Latency | End-to-End Latency（端到端延迟） | 从客户端发出请求到收到完整响应的总耗时。 | 包含网络、排队、推理、序列化全链路；是 SLO 定义和用户体验评估的最终口径。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Queue Time | 排队时间 | 请求进入推理引擎后、在真正开始计算之前的等待时长。 | 排队时间突增通常意味着并发超限、GPU 实例不足或调度延迟；是容量扩容的先行指标。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Waiting Requests | 等待请求数 | 当前已被接收但尚未被推理实例接住的请求数量。 | 反映入口压力与扩容速度的匹配程度；持续积压说明 HPA 指标或扩容策略需要调整。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| P50 | 延迟第 50 百分位 | 50% 请求的延迟不超过此值，代表中位数体验。 | 用于衡量系统在正常负载下的典型表现；P50 稳定是前提，P99 可控才是目标。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| P95 | 延迟第 95 百分位 | 95% 请求的延迟不超过此值。 | 用于捕捉非极端但显著的延迟劣化；P95 与 P50 的差距越大，说明长尾越严重。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| P99 | 延迟第 99 百分位 | 99% 请求的延迟不超过此值。 | 常用于 SLO 定义和尾延迟告警；P99 突刺通常由 GC、预热、长上下文请求或批内竞争导致。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| QPS | Queries Per Second（每秒查询数） | 每秒到达的请求总数。 | 入口压力的宏观指标；LLM 场景下 QPS 相同但 token 分布不同时，实际负载差异巨大，需结合 TPS 看。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Prefill | 预填充阶段 | 处理输入 prompt 中所有 token、建立 KV Cache 初始状态的计算阶段。 | Prefill 是计算密集型，直接影响 TTFT；长 prompt 场景下 Prefill 时间可能占 E2E 延迟的大部分。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Decode | 解码阶段 | 基于已生成 token 和 KV Cache，逐个生成输出 token 的自回归阶段。 | Decode 是带宽敏感型，决定 TPOT 和持续吞吐；批大小、量化精度、显存带宽是主要影响因素。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Throughput | 吞吐量 | 推理系统在单位时间内处理的总工作量（可用 TPS 或完成的请求数衡量）。 | 吞吐和延迟通常此消彼长；运维目标是找到吞吐-延迟的帕累托最优区间。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Goodput | 有效吞吐 | 在满足 SLO 约束下的实际有效吞吐量。 | 总吞吐高但 SLO 达标率低时，Goodput 会暴露真实的服务质量；比单纯 TPS 更有业务意义。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Batch Size | 批大小 | 单个推理批次中同时处理的请求数量。 | 批大小越大吞吐越高但延迟也越高；需要在吞吐和延迟之间找到平衡点。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Concurrency | 并发数 | 同时被推理引擎处理的请求数量。 | 并发数受 GPU 显存和 KV Cache 容量限制；是容量规划的核心约束。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Streaming | 流式输出 | 推理引擎在生成过程中逐步将 token 返回给客户端，而非等生成完成后一次性返回。 | 降低用户感知的 TTFT 但增加连接管理复杂度；需要关注流式超时和断连处理。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 训练与并行类

并行策略决定了训练和微调如何利用多 GPU 资源。运维需要理解每种并行方式的通信模式、资源需求和故障影响面，以便做好集群规划和故障隔离。大模型训练通常采用多种并行策略的组合（例如 TP + PP + DP），运维需要理解每层并行的瓶颈在哪里。

数据并行是最基础的方式，但随着模型增大，单卡已无法容纳完整模型，因此需要引入参数分片（FSDP/ZeRO）。当模型进一步增大到需要跨越多个节点时，流水线并行和张量并行的组合就变得必要。MoE 架构的出现又引入了专家并行。这些并行方式的通信模式各不相同，对硬件拓扑的要求也不一样，运维必须根据集群的实际互联条件选择合适的策略。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| DDP | Distributed Data Parallel（分布式数据并行） | 每个 GPU 持有完整模型副本，各自处理不同数据，通过 AllReduce 同步梯度。 | 通信开销随模型增大而增大；单卡故障不影响其他卡，但需等待同步；显存利用率较低。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| FSDP | Fully Sharded Data Parallel（全分片数据并行） | 将模型参数、梯度和优化器状态分片到所有 GPU，计算时按需重组。 | 显存节省显著，但通信模式更复杂；分片策略和重组时机直接影响训练吞吐和恢复速度。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| ZeRO | Zero Redundancy Optimizer（零冗余优化器） | DeepSpeed 提出的分阶段分片策略，逐步消除数据并行中的冗余显存占用。 | ZeRO 分三个阶段（Stage 1/2/3），运维需根据显存和通信权衡选择阶段；与 FSDP 有功能重叠。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| TP | Tensor Parallelism（张量并行） | 将单个算子（如矩阵乘法）切分到多个 GPU 上并行计算。 | 对 GPU 间高速互联（NVLink）依赖极高；TP 通常在同一节点内使用，跨节点 TP 效率很低。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| PP | Pipeline Parallelism（流水线并行） | 将模型按层切分为多个阶段，不同阶段分布在不同 GPU 上流水执行。 | 气泡开销（bubble）会降低 GPU 利用率；阶段间均衡和 micro-batch 数量是调优重点。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| DP | Data Parallelism（数据并行） | 最基本的并行方式，多个副本各自处理不同数据批次。 | 扩展简单但显存成本线性增长；大规模场景下常与 FSDP/ZeRO 结合使用。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| EP | Expert Parallelism（专家并行） | 用于 MoE（混合专家）模型，将不同专家分布到不同 GPU 上。 | 路由倾斜可能导致部分 GPU 过载；跨节点专家调度的网络流量是关键瓶颈。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| MFU | Model FLOPs Utilization（模型浮点利用率） | 实际模型计算吞吐占硬件理论峰值的百分比。 | 是衡量训练效率的核心指标；MFU 低于预期时需排查通信、数据加载、编译或分片策略问题。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Gradient Accumulation | 梯度累积 | 在多个小 batch 上累积梯度后再执行一次参数更新，等效于大 batch 训练。 | 允许在显存不足时模拟大 batch；累积步数影响训练稳定性和收敛速度。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| Mixed Precision | 混合精度训练 | 在训练中同时使用 FP16/BF16 和 FP32，在保持精度的同时降低显存和加速计算。 | BF16 对溢出更友好，优先选择；需确保硬件支持；loss scaling 策略影响训练稳定性。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Checkpoint | 检查点 | 训练过程中定期保存的模型状态快照，包含权重、优化器状态和训练进度。 | 检查点大小随模型增大可达数百 GB；保存频率影响恢复时间和存储成本；是故障恢复的基础。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| AllReduce | 全归约 | 分布式训练中将所有 GPU 上的梯度进行归约（如求和）并广播回所有 GPU 的集合通信操作。 | 是 DDP 和 FSDP 的核心通信原语；通信量与模型参数量成正比；Ring AllReduce 和 Tree AllReduce 效率不同。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| MoE | Mixture of Experts（混合专家模型） | 由多个专家子网络和一个门控网络组成的模型架构，每次推理只激活部分专家。 | 显存占用大（所有专家都需加载但只用部分）；路由倾斜是主要性能问题；EP 并行是 MoE 的专属优化。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| Scaling Law | 缩放定律 | 描述模型性能如何随参数量、数据量和计算量增长的经验规律。 | 影响训练资源规划和成本预估；运维需要理解 Scaling Law 来判断投入产出比。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |

### KV Cache 与显存类

KV Cache 是 LLM 推理中显存消耗的主要来源，理解其管理机制对容量规划、长上下文支持和成本控制至关重要。在自回归生成过程中，每生成一个新 token 都需要访问之前所有 token 的 Key 和 Value 向量。如果不缓存这些向量，每个 token 的生成都需要重新计算整个历史，计算成本会随序列长度二次增长。KV Cache 通过空间换时间的方式解决了这个问题，但也带来了显存管理的挑战。

一个 70B 参数模型在 FP16 精度下单个请求的 KV Cache 可能占用数 GB 显存，而一块 A100 80GB 的 GPU 能同时服务的请求数直接取决于 KV Cache 的管理效率。Paged Attention 和 Prefix Cache 就是为了解决显存碎片和重复计算问题而设计的。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| KV Cache | Key/Value 缓存 | 在自回归生成过程中，缓存已计算 token 的 Key 和 Value 张量，避免重复计算。 | 直接决定单请求显存占用和最大并发数；KV Cache 越大，可服务的 batch 越小。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Prefix Cache | 前缀缓存 | 对相同 prompt 前缀的 KV Cache 进行跨请求复用，避免重复 Prefill。 | 命中率直接影响 TTFT 和 GPU 利用率；缓存失效策略和共享粒度是调优重点。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Paged Attention | 分页注意力 | 将 KV Cache 按固定大小的页（block）管理，类似操作系统虚拟内存分页。 | 消除显存碎片，提升显存利用率；页大小和缓存驱逐策略影响性能和命中率。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Continuous Batching | 连续批处理 | 在 Decode 过程中动态插入新请求、移除已完成请求，而非等整个批次完成。 | 显著提升吞吐和 GPU 利用率；但增加了调度复杂度，需关注公平性和饥饿问题。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Context Window | 上下文窗口 | 模型单次推理能够处理的最大 token 数量（输入 + 输出）。 | 上下文越长，KV Cache 显存占用越大；需要根据业务场景设置合理的最大上下文长度。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Max Batched Tokens | 最大批处理 token 数 | 推理引擎在单个批次中同时处理的 token 上限。 | 设置过大导致 OOM 或延迟飙升，设置过小浪费 GPU 利用率；需根据显存和模型大小调优。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| OOM | Out of Memory（显存溢出） | GPU 显存不足以容纳当前工作负载，导致推理或训练失败。 | LLM 场景下 OOM 通常由 KV Cache 膨胀、batch 过大或上下文过长导致；是容量规划的硬约束。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| VRAM | Video RAM（显存） | GPU 上的专用高速内存，用于存储模型权重、KV Cache、激活值等。 | 显存大小直接决定可部署的模型大小和并发请求数；是 LLM 服务最稀缺的资源之一。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| HBM | High Bandwidth Memory（高带宽显存） | 现代 GPU（如 A100、H100）使用的高带宽显存技术。 | HBM 带宽直接影响 Decode 阶段的 TPOT；HBM 容量决定了最大 KV Cache 和模型大小。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Offloading | 卸载 | 将不常用的数据（如 KV Cache、模型权重）从 GPU 显存转移到 CPU 内存或磁盘。 | 降低 OOM 风险但增加数据搬运延迟；需要在显存节省和性能损失之间权衡。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Tokenizer | 分词器 | 将文本切分为 token 序列的组件，是模型输入的预处理步骤。 | 分词器版本变更会影响 token 数量和模型行为；需要确保推理和训练使用相同的分词器。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Temperature | 温度参数 | 控制模型输出随机性的参数，值越高输出越多样，值越低输出越确定。 | 温度参数影响输出质量和一致性；运维需要了解业务场景对温度参数的约束。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Top-P / Top-K | 核采样 / K 采样 | 控制模型生成时候选 token 范围的参数，Top-P 按概率累积截断，Top-K 按数量截断。 | 与 Temperature 配合影响输出多样性；运维需了解参数对输出质量的影响。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 部署与架构类

推理引擎和部署架构的选择直接决定了推理服务的吞吐、延迟和运维复杂度。运维需要熟悉主流推理框架的能力边界和调优参数。当前主流的推理引擎各有侧重：vLLM 以 Paged Attention 和高吞吐见长，适合通用推理场景；SGLang 强调推理编排，适合 Agent 和多步推理；TGI 部署形态清晰，适合与 Hugging Face 生态集成；Triton 则适合多模型混合部署的企业级场景。

在部署层面，弹性伸缩策略需要考虑 LLM 服务的特殊性：模型加载时间长（分钟级），GPU 资源昂贵且稀缺，传统基于 CPU 指标的 HPA 往往不适用。Canary、Shadow Traffic 和 Blue-Green 等发布策略也需要针对模型输出的非确定性做调整。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| vLLM | vLLM 推理引擎 | 基于 Paged Attention 的高吞吐 LLM 推理框架，支持 OpenAI 兼容 API。 | 关注 PagedAttention 配置、Prefix Cache 命中率、调度策略和版本升级兼容性。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| SGLang | SGLang 推理引擎 | 强调推理编排和复杂请求流的推理框架，适合 Agent 和多步推理场景。 | 关注请求编排效率、多轮推理的资源管理和长流程稳定性。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| TGI | Text Generation Inference（文本生成推理） | Hugging Face 出品的推理服务，部署形态清晰，生态集成度高。 | 关注模型加载方式、指标暴露格式和与 Hugging Face Hub 的集成。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Triton | Triton Inference Server | NVIDIA 推出的通用推理服务器，支持多模型、多后端和多种部署模式。 | 适合多模型混合部署；关注后端配置、模型仓库管理和并发模型加载。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| TensorRT-LLM | TensorRT-LLM | NVIDIA 针对 LLM 优化的推理加速库，通过编译优化提升推理性能。 | 关注模型编译耗时、精度验证和与 Triton/vLLM 的集成方式。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Ray Serve | Ray Serve 推理服务 | 基于 Ray 框架的模型服务组件，适合复杂推理工作流和弹性扩展。 | 关注 Ray 集群管理、Actor 模型的资源调度和多组件编排的稳定性。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| KServe | KServe 模型服务平台 | Kubernetes 原生的模型推理平台，提供标准化的模型部署和管理能力。 | 适合将 LLM 服务纳入 Kubernetes 原生治理体系；关注 InferenceService CRD 和自动扩缩配置。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| HPA | Horizontal Pod Autoscaler（水平 Pod 自动扩缩器） | 根据指标自动调整 Pod 副本数量的 Kubernetes 原生能力。 | 指标选错会导致扩容滞后或缩容过快；LLM 场景下建议基于 GPU 利用率或队列深度自定义指标。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| KEDA | Kubernetes Event-Driven Autoscaler（事件驱动扩缩器） | 基于事件源（消息队列、自定义指标等）驱动 Kubernetes 扩缩容的组件。 | 适合基于请求队列深度或 GPU 任务数的弹性策略；需关注指标延迟和冷却时间配置。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Canary | 金丝雀发布 | 将少量流量导到新版本进行验证，逐步扩大比例直到全量切换。 | 控制流量比例和回滚速度；LLM 场景下需同时对比延迟、吞吐和输出质量。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Shadow Traffic | 影子流量 | 将真实请求复制一份发送到新版本或新链路，但不将结果返回给用户。 | 适合无风险验证新模型或新配置；需确保影子流量不影响主链路容量和成本统计。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Blue-Green | 蓝绿部署 | 维护两套完整环境（蓝和绿），通过流量切换实现零停机部署。 | 切换速度快但资源成本翻倍；LLM 场景下模型加载时间是关键，需提前预热。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Rolling Update | 滚动更新 | 逐步用新版本 Pod 替换旧版本 Pod 的部署策略。 | Kubernetes 默认策略；LLM 场景下需注意新 Pod 的 Warmup 时间，避免滚动期间容量骤降。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Model Registry | 模型仓库 | 集中存储、版本管理和分发模型制品的系统。 | 关注模型版本一致性、制品存储成本和分发效率；是多环境部署的基础。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| A/B Testing | A/B 测试 | 将用户随机分为两组，分别体验不同版本，通过统计方法比较效果。 | LLM 场景下需要对比输出质量、用户满意度和业务指标；样本量和测试周期需要充足。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |

### RAG 与应用类

RAG 和 Agent 是 LLM 应用层的核心模式。RAG 通过在生成前检索外部知识来扩展模型的知识范围，Agent 则通过工具调用和多步推理来实现更复杂的任务。运维需要关注的不仅是推理链路本身，还包括检索链路、向量数据库、工具调用等整个应用栈的延迟和可靠性。

RAG 链路的延迟通常是推理延迟的 2-5 倍（加上检索和重排），因此端到端优化需要同时关注检索效率和推理效率。Agent 场景更加复杂，一次用户请求可能触发多次推理和多次工具调用，运维需要关注整个执行链的超时控制和资源隔离。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| RAG | Retrieval-Augmented Generation（检索增强生成） | 在生成前先从外部知识库检索相关文档，将检索结果作为上下文输入给模型。 | 运维需同时监控检索延迟、召回质量和上下文膨胀对推理性能的影响。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Embedding | 向量化表示 | 将文本映射为高维向量，用于语义相似度计算和向量检索。 | 关注 Embedding 模型版本一致性、向量维度对存储和检索速度的影响。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Re-ranker | 重排模型 | 对初步召回的文档进行二次排序，提升最终结果的相关性。 | 常是额外延迟来源，需评估精度提升是否值得额外的推理开销。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Vector Database | 向量数据库 | 专门存储和检索高维向量的数据库系统（如 Milvus、Pinecone、Qdrant）。 | 关注索引构建时间、查询延迟、数据一致性和水平扩展能力。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Chunking | 文档切分 | 将长文档切分为适合 Embedding 和检索的小段落。 | 切分策略影响召回质量；chunk 大小、重叠度和切分边界需要根据业务场景调优。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Hybrid Search | 混合检索 | 同时使用向量检索（语义）和关键词检索（精确匹配），合并结果排序。 | 需要调和两种检索的权重和结果融合策略；比纯向量检索更复杂但召回更全面。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Tool Calling | 工具调用 | 让模型在生成过程中触发外部 API、函数或系统动作。 | 关注调用超时、幂等性、权限边界和失败回退；工具调用链越长，端到端延迟越高。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Session State | 会话状态 | 多轮对话或 Agent 执行过程中的上下文状态信息。 | 关注状态膨胀（长对话导致 KV Cache 增长）、状态一致性和跨租户隔离。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Agent Runtime | Agent 运行时 | 支撑 Agent 循环（感知-思考-行动）执行的底层运行环境。 | 关注运行时资源占用、执行超时控制、并发 Agent 数量限制和异常恢复机制。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Retrieval Latency | 检索延迟 | 从发起检索请求到返回检索结果的耗时。 | 是 RAG 链路延迟的主要组成部分；需要区分向量检索延迟和关键词检索延迟分别监控。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Context Window Bloat | 上下文膨胀 | RAG 检索结果过多导致输入给模型的上下文超出合理长度。 | 增加 Prefill 时间和 KV Cache 显存占用；需要控制检索结果数量和截断策略。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Recall Rate | 召回率 | 检索系统返回相关文档的比例。 | 召回率低会导致模型缺乏足够上下文，影响输出质量；需要定期评估和调优检索策略。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Grounding | 接地/事实锚定 | 让模型基于检索到的事实生成回答，而非依赖内部知识。 | 减少幻觉但增加检索链路依赖；需要监控接地质量和检索失败的降级策略。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| Hallucination | 幻觉 | 模型生成看似合理但实际不准确或虚构的内容。 | 是 LLM 服务质量的核心挑战；需要通过 RAG、Guardrail 和输出检测来缓解。 | [./20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |

### 安全与治理类

LLM 服务的安全边界比传统服务更宽，需要同时覆盖输入安全、输出安全、访问控制和数据合规。传统 API 的安全主要关注认证、授权和注入攻击，LLM 服务在此基础上还需要关注提示注入、输出内容安全、PII 泄露等新攻击面。

Guardrail（安全护栏）是 LLM 安全的核心组件，通常部署在推理链路的输入和输出两端。输入端 Guardrail 负责检测提示注入和恶意请求，输出端 Guardrail 负责过滤有害内容和 PII。运维需要关注 Guardrail 引入的额外延迟和误杀率，并持续迭代检测规则。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| Prompt Injection | 提示注入攻击 | 通过在输入中嵌入恶意指令，试图改变模型行为或泄露系统信息。 | 需要输入检测和过滤机制；与 Guardrail 配合使用；运维需关注攻击检测率和误杀率。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Jailbreak | 越狱攻击 | 绕过模型安全限制，诱导模型生成违规内容的攻击手法。 | 与 Prompt Injection 相关但更侧重绕过安全对齐；需要持续更新检测规则。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Guardrail | 安全护栏 | 对模型的输入和输出进行安全检查和过滤的机制或组件。 | 关注检测规则的覆盖范围、误杀率和额外延迟；护栏策略需要持续迭代。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| OIDC | OpenID Connect（开放身份认证协议） | 基于 OAuth 2.0 的身份认证层，用于验证用户身份并获取基本信息。 | 常用于统一人类用户和服务身份接入；关注 token 过期、刷新机制和身份提供方的可用性。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| ABAC | Attribute-Based Access Control（基于属性的访问控制） | 根据用户属性、资源属性和环境属性动态做出访问控制决策。 | 适合按租户、环境、数据分类和地域做细粒度授权；策略复杂度高于 RBAC。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| RBAC | Role-Based Access Control（基于角色的访问控制） | 根据用户被分配的角色来决定其可访问的资源和操作权限。 | 实现简单、易审计；但角色爆炸问题在多租户场景下会变得棘手。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| PII | Personally Identifiable Information（个人可识别信息） | 能够直接或间接识别特定个人的信息，如姓名、身份证号、邮箱等。 | LLM 输入输出中可能包含 PII；需要检测、脱敏和审计机制满足合规要求。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Content Safety | 内容安全 | 检测和过滤模型输出中的有害、违规或不当内容的机制。 | 需要覆盖暴力、色情、仇恨言论等类别；关注检测准确率和对用户体验的影响。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| SSO | Single Sign-On（单点登录） | 用户一次登录即可访问多个关联系统的认证机制。 | 简化用户管理但扩大了单点故障影响面；SSO 服务不可用时需要有降级登录方案。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Audit Log | 审计日志 | 记录用户操作和系统事件的日志，用于合规审计和安全事件追溯。 | LLM 场景下需记录请求输入、模型输出、工具调用和访问控制决策；日志存储和保留策略需满足合规要求。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Multi-Tenancy | 多租户 | 单个推理服务同时服务多个租户（团队、客户或业务线）的架构模式。 | 需要关注资源隔离（GPU 配额、KV Cache 限制）、数据隔离和性能隔离（防邻居干扰）。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Data Residency | 数据驻留 | 数据存储和处理的地理位置要求。 | LLM 推理可能涉及跨境数据传输；需要满足不同地区的数据合规要求（如 GDPR、中国数据安全法）。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| Model Card | 模型卡片 | 记录模型能力、限制、训练数据和评估结果的标准化文档。 | 帮助运维了解模型的适用场景和已知问题；是模型治理和合规的基础文档。 | [./21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |

### 可靠性与运维类

可靠性工程是 SRE 的核心职责。LLM 服务的特殊性在于 GPU 资源昂贵、模型加载慢、推理延迟高，传统的弹性伸缩和故障恢复策略需要针对性调整。例如，传统服务的冷启动通常是秒级，而 LLM 服务的冷启动可能需要分钟级的模型加载时间；传统服务可以通过增加实例快速扩容，但 LLM 服务受限于 GPU 资源，扩容速度远慢于传统服务。

SLO/SLI/Error Budget 三件套在 LLM 场景下需要扩展定义：除了传统的延迟和错误率，还需要纳入 token 级指标、输出质量和 GPU 利用率。错误预算的消耗速度也比传统服务更快，因为 GPU 故障（Xid Error、ECC 错误）的影响面更大。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| SLO | Service Level Objective（服务级别目标） | 服务必须达到的可靠性目标，通常以延迟、错误率或可用性百分比表示。 | LLM 服务的 SLO 需要同时覆盖延迟（TTFT/TPOT/E2E）、错误率和可用性；目标过高会限制迭代速度。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| SLI | Service Level Indicator（服务级别指标） | 衡量服务实际表现的具体指标，是 SLO 的度量基础。 | 选择正确的 SLI 比设置 SLO 更重要；LLM 场景下需涵盖 token 级延迟、请求成功率和输出质量。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Error Budget | 错误预算 | 在 SLO 允许范围内可以消耗的失败额度，通常按时间窗口计算。 | 错误预算耗尽时应冻结变更、优先修复；预算充足时可适度增加实验和上线频率。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Fallback | 回退/降级 | 主路径异常时切换到备用模型、备用链路或降级服务模式。 | 需要预设回退条件和备用方案；评估回退后的质量损失、可用性收益和成本变化。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Circuit Breaking | 熔断 | 当下游服务错误率超过阈值时自动停止请求，防止级联故障。 | 熔断阈值和恢复策略需要根据 LLM 服务的延迟特性调整；过早熔断影响可用性，过晚熔断放大故障。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Rate Limiting | 限流 | 对请求速率进行控制，防止系统过载。 | LLM 限流维度包括 QPS、TPS、并发请求数和 GPU 资源使用量；需区分租户和优先级。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Degradation | 服务降级 | 在资源不足或异常时主动降低服务质量以保全核心功能。 | LLM 降级手段包括缩短上下文、降低输出长度、切换小模型或返回缓存结果。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Warmup | 预热 | 在服务启动或发布后提前加载模型、建立连接池和预跑推理请求。 | 直接影响冷启动时间和首次请求延迟；预热不充分会导致发布后 P99 飙升。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Cold Start | 冷启动 | 服务实例从零开始启动到可以处理请求的完整过程。 | LLM 冷启动包含模型加载、权重传输和 GPU 初始化，耗时可能达分钟级；是扩缩容策略的核心约束。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Graceful Degradation | 优雅降级 | 在系统压力增大时逐步降低非核心功能，保障核心功能可用。 | LLM 场景下可按优先级关闭工具调用、缩短上下文、降低输出长度，而非直接拒绝请求。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Bulkhead | 舱壁隔离 | 将系统资源隔离为独立的舱，防止单个舱的故障扩散到其他舱。 | LLM 场景下可按租户、模型或优先级隔离 GPU 资源和请求队列。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Retry | 重试 | 请求失败后自动重新发送请求的机制。 | LLM 推理重试成本高（每次重试都消耗 GPU 资源）；需要限制重试次数和间隔，避免放大故障。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Timeout | 超时 | 为请求设置的最大等待时间，超过后自动终止。 | LLM 推理超时设置需要考虑模型大小、输入长度和输出长度；超时过短导致有效请求被拒绝，过长导致资源浪费。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Health Check | 健康检查 | 定期检测服务实例是否正常运行的机制。 | LLM 健康检查需要验证 GPU 状态、模型加载状态和推理能力，而不仅仅是进程存活。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| Multi-Region | 多区域部署 | 将服务部署在多个地理区域，提供就近访问和容灾能力。 | LLM 多区域部署需要考虑模型同步、GPU 资源分配和跨区域流量调度；成本比传统服务更高。 | [./19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |

### 量化与优化类

量化和优化技术通过降低计算精度或改变推理策略来减少资源消耗、提升吞吐。运维需要理解每种技术的质量-性能权衡。量化是最直接的优化手段：将模型权重从 FP16 量化到 INT4 可以将显存占用减少到原来的 1/4，使得原本需要多卡才能部署的模型可以在单卡上运行。

但量化不是免费的午餐。INT4 量化虽然节省显存最多，但精度损失也最大，需要在目标场景下做充分的质量评估。投机解码（Speculative Decoding）是另一种优化思路，通过用小模型辅助大模型来提升生成速度，但接受率和额外开销需要仔细调优。LoRA 和 QLoRA 则是微调层面的优化，通过只训练少量参数来降低微调成本。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| Quantization | 量化 | 用更低的数值精度表示模型权重或激活值，以减少显存和计算量。 | 量化后需要验证输出质量是否可接受；不同量化方案（PTQ/QAT）的精度损失不同。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| PTQ | Post-Training Quantization（训练后量化） | 在模型训练完成后进行的量化，不需要重新训练。 | 操作简单但精度损失可能比 QAT 大；适合快速部署场景。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| QAT | Quantization-Aware Training（量化感知训练） | 在训练过程中模拟量化效果，使模型学会适应低精度表示。 | 精度损失比 PTQ 小但需要额外训练成本；适合对精度要求高的场景。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| INT8 | 8 位整数量化 | 将权重或激活从 FP16/FP32 量化为 8 位整数。 | 显存占用约减半，推理速度提升明显；大多数场景下精度损失可接受。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| INT4 | 4 位整数量化 | 将权重量化为 4 位整数，进一步压缩模型大小。 | 显存节省更多但精度风险更高；需在目标场景下做充分的质量评估。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| FP8 | 8 位浮点量化 | 使用 8 位浮点格式（E4M3/E5M2）进行推理或训练。 | 需要硬件支持（如 H100）；FP8 在训练和推理中均有应用，精度介于 FP16 和 INT8 之间。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| FP16 | 16 位浮点 | 使用 16 位浮点精度进行推理或训练。 | 推理和训练的常用精度；比 FP32 节省一半显存，大多数场景下精度足够。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| BF16 | Brain Float 16 | Google 提出的 16 位浮点格式，指数位比 FP16 更多，动态范围更大。 | 对溢出更友好，训练稳定性优于 FP16；已成为大模型训练的主流精度选择。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| FP32 | 32 位浮点 | 标准单精度浮点格式，精度最高但显存和计算成本也最高。 | 训练中通常用于存储优化器状态；推理中一般不使用，除非精度要求极高。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Speculative Decoding | 投机解码 | 用小型草稿模型快速生成多个候选 token，由大模型一次性验证。 | 关注接受率（acceptance rate）和额外开销；接受率越高，加速效果越好。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| LoRA | Low-Rank Adaptation（低秩适配） | 通过在模型中插入低秩矩阵进行微调，只训练少量新增参数。 | 关注 Adapter 制品管理、多 Adapter 加载切换延迟和版本回滚策略。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| QLoRA | Quantized LoRA（量化低秩适配） | 在量化模型基础上进行 LoRA 微调，进一步降低微调的显存需求。 | 允许在消费级 GPU 上微调大模型；但量化引入的精度损失可能影响微调效果。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| PEFT | Parameter-Efficient Fine-Tuning（参数高效微调） | 泛指只训练少量参数即可适配模型的一类微调方法（包括 LoRA、Adapter、Prefix Tuning 等）。 | 降低了微调门槛和成本；运维需管理多种 PEFT 方法的制品格式和加载方式。 | [./13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| Flash Attention | 闪速注意力 | 通过优化 GPU 内存访问模式加速注意力计算的算法。 | 不改变计算结果但显著提升速度；需要特定 CUDA 版本支持；是推理引擎的常用优化。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| CUDA Graph | CUDA 图 | 将多个 CUDA 操作预编译为一个执行图，减少 CPU-GPU 交互开销。 | 在 Decode 阶段可显著降低调度延迟；但首次编译有开销，且不适合动态 shape 场景。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Kernel Fusion | 算子融合 | 将多个小算子合并为一个大算子，减少 kernel 启动和内存访问开销。 | 是推理引擎和编译器的常用优化手段；融合策略影响性能和显存使用。 | [./17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| Dynamic Batching | 动态批处理 | 根据当前负载动态调整批大小，而非使用固定批大小。 | 与 Continuous Batching 配合使用；需要在吞吐和延迟之间动态平衡。 | [./16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |

### GPU 与硬件类

GPU 和高速互联是 LLM 服务的物理基础。运维需要掌握硬件指标、故障诊断方法和资源隔离机制。NVIDIA GPU 是当前 LLM 服务的主流硬件，从 A100 到 H100 再到 B200，每代 GPU 在算力、显存容量和互联带宽上都有显著提升。运维需要理解不同代际 GPU 的能力差异，以便做出合理的采购和部署决策。

GPU 故障是 LLM 服务运维中最棘手的问题之一。Xid Error 是 NVIDIA 驱动报告的硬件错误，不同编号对应不同故障类型。ECC 错误计数持续增长是 GPU 老化的前兆。MIG 和 MPS 是两种 GPU 资源隔离方式，MIG 提供硬件级隔离但粒度固定，MPS 提供进程级共享但隔离性较弱。运维需要根据多租户需求选择合适的隔离策略。

| 术语 | 中文全称 | 一句话解释 | 运维关注点 | 首次出现文档 |
|---|---|---|---|---|
| NVLink | NVLink 高速互联 | NVIDIA GPU 之间的高速点对点互连技术，带宽远超 PCIe。 | TP 并行对 NVLink 带宽依赖极高；NVLink 拓扑和带宽直接影响多卡推理和训练效率。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| NVSwitch | NVSwitch 交换芯片 | 在多 GPU 系统中提供全互联带宽的交换芯片。 | 确保所有 GPU 间通信带宽一致；NVSwitch 故障会导致部分 GPU 间通信退化。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| PCIe | PCI Express（高速串行总线） | CPU 与 GPU 之间以及 GPU 与 GPU 之间的标准互连接口。 | PCIe 带宽远低于 NVLink，是跨 GPU 通信的瓶颈；PCIe 代数（Gen4/Gen5）影响数据传输速度。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| InfiniBand | InfiniBand 网络 | 高性能计算和 AI 集群常用的高速网络互连技术。 | 关注 RDMA 带宽、端口错误计数和子网管理器健康状态；是跨节点训练的关键基础设施。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| RoCE | RDMA over Converged Ethernet（融合以太网上的 RDMA） | 在以太网上实现 RDMA 远程直接内存访问的协议。 | 比 InfiniBand 成本低但配置更复杂；关注 PFC 流控、ECN 标记和无损网络配置。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| MIG | Multi-Instance GPU（多实例 GPU） | 将单块物理 GPU 切分为多个隔离的 GPU 实例，各自拥有独立的计算和显存资源。 | 适合多租户隔离；但切分粒度固定，可能造成资源碎片化和利用率下降。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| MPS | Multi-Process Service（多进程服务） | 允许多个进程共享同一 GPU 的 CUDA 上下文，提升轻量任务的 GPU 利用率。 | 适合小模型或多模型共享 GPU；但进程间无强隔离，需防止相互干扰。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| DCGM | Data Center GPU Manager（数据中心 GPU 管理器） | NVIDIA 提供的 GPU 健康检查、诊断和监控工具集。 | GPU 指标采集的标准入口；集成 Prometheus Exporter 后可用于告警和容量分析。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Xid Error | Xid 错误 | NVIDIA 驱动报告的 GPU 硬件或驱动层面错误，以 Xid 编号标识。 | 不同 Xid 编号对应不同故障类型（ECC、掉卡、驱动崩溃等）；是 GPU 故障诊断的关键入口。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| ECC | Error Correcting Code（错误纠正码） | GPU 显存的硬件纠错机制，可检测并纠正单位错误、检测双位错误。 | ECC 错误计数持续增长是 GPU 老化或故障的前兆；严重时需要主动替换硬件。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| GPU Utilization | GPU 利用率 | GPU 计算核心在采样周期内处于活跃状态的时间占比。 | GPU 利用率低说明存在等待或空闲；但利用率高不代表效率高（可能在做低效计算）。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| GPU Memory Utilization | GPU 显存利用率 | GPU 显存被使用的比例。 | 显存利用率接近 100% 时有 OOM 风险；需要预留空间给突发负载和 KV Cache 增长。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| CUDA | Compute Unified Device Architecture（统一计算设备架构） | NVIDIA 的 GPU 并行计算平台和编程模型。 | 是 LLM 推理和训练的底层运行时；CUDA 版本兼容性影响推理引擎和模型的部署。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| RDMA | Remote Direct Memory Access（远程直接内存访问） | 允许计算机直接访问远程计算机内存的技术，无需 CPU 介入。 | 是跨节点训练通信的基础；InfiniBand 和 RoCE 都基于 RDMA；降低通信延迟和 CPU 开销。 | [./12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| Telemetry | 遥测 | 自动收集和传输系统运行数据（指标、日志、追踪）的机制。 | LLM 遥测需要覆盖 GPU 指标、推理指标、应用指标和业务指标；是可观测性的数据基础。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| Prometheus | Prometheus 监控系统 | 开源的监控和告警系统，采用拉取模式采集指标。 | LLM 推理指标的标准采集后端；关注指标基数控制和查询性能。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| OpenTelemetry | OpenTelemetry 可观测性框架 | 提供分布式追踪、指标和日志的统一采集规范和 SDK。 | 是 LLM 请求追踪的标准方案；需要确保推理引擎和应用层都正确集成。 | [./18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |

## 术语关系图

以下 ASCII 图展示关键概念之间的依赖和关联关系，帮助建立整体认知。图中用箭头表示依赖或数据流向，用方框表示概念分组。

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户请求入口                                │
│                      QPS / Rate Limiting                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             v
┌─────────────────────────────────────────────────────────────────────┐
│                      推理引擎层                                      │
│                                                                     │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│   │     vLLM        │   │     SGLang      │   │   TGI / Triton  │  │
│   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘  │
│            │                     │                     │            │
│            └─────────────────────┼─────────────────────┘            │
│                                  │                                  │
│                                  v                                  │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                    核心调度机制                                │  │
│   │                                                              │  │
│   │  Continuous Batching ──> 动态合批 ──> 提升 GPU 利用率         │  │
│   │  Paged Attention ──> KV Cache 分页管理 ──> 消除显存碎片       │  │
│   │  Prefix Cache ──> 前缀复用 ──> 减少重复 Prefill              │  │
│   └──────────────────────────────────────────────────────────────┘  │
│                                  │                                  │
│                                  v                                  │
│   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐   │
│   │   KV Cache       │   │  Context Window  │   │   OOM 风险   │   │
│   │   显存占用       │   │  上下文长度限制   │   │   容量约束   │   │
│   └──────────────────┘   └──────────────────┘   └──────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              v              v              v
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │   TTFT   │  │   TPOT   │  │  E2E Latency │
        │  Prefill │  │  Decode  │  │   全链路     │
        │  计算密集 │  │  带宽敏感 │  │              │
        └──────────┘  └──────────┘  └──────────────┘
              │              │              │
              v              v              v
        ┌──────────────────────────────────────────┐
        │          延迟分位数与 SLO                  │
        │                                          │
        │  P50 (中位数) / P95 / P99 (尾延迟)       │
        │  SLI (度量) ──> SLO (目标) ──> Error Budget (余量) │
        │  Goodput (有效吞吐 = 满足 SLO 的吞吐)    │
        └──────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        并行策略 (训练侧)                             │
│                                                                     │
│   数据并行演进:                                                      │
│   DP ──> DDP (AllReduce 梯度) ──> FSDP/ZeRO (分片参数)             │
│                                                                     │
│   模型并行组合:                                                      │
│   TP (节点内, NVLink 依赖) ──┬──> 3D 混合并行                       │
│   PP (节点间, 跨层流水线) ───┤                                      │
│   EP (MoE 专家路由) ─────────┘                                      │
│                                                                     │
│   微调优化:                                                          │
│   Full Fine-tuning ──> LoRA (低秩) ──> QLoRA (量化+低秩)           │
│   Mixed Precision (BF16/FP16) + Gradient Accumulation              │
│   Checkpoint (故障恢复基础) + AllReduce (通信原语)                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        RAG / Agent 应用链路                          │
│                                                                     │
│   用户输入 ──> Guardrail (输入检测)                                  │
│                    │                                                 │
│                    v                                                 │
│   Embedding ──> Vector DB ──> 初步检索                               │
│                    │                                                 │
│                    v                                                 │
│   Re-ranker ──> 重排 ──> 上下文拼接                                  │
│                    │                                                 │
│                    v                                                 │
│   LLM 推理 (TTFT + TPOT) ──> Guardrail (输出检测)                   │
│                    │                                                 │
│                    v                                                 │
│   Tool Calling ──> 外部 API ──> Agent Runtime                       │
│                    │                                                 │
│                    v                                                 │
│   Session State (多轮上下文) ──> 响应返回用户                        │
│                                                                     │
│   关键延迟组成: Retrieval Latency + Prefill + Decode + Tool Latency │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        硬件与资源层                                  │
│                                                                     │
│   节点内互联:                                                        │
│   GPU ──NVLink──> NVSwitch ──> 全互联带宽                           │
│   GPU ──PCIe──> CPU/主机内存 (Offloading)                          │
│                                                                     │
│   跨节点互联:                                                        │
│   InfiniBand (RDMA, 低延迟) ──> 训练集群首选                        │
│   RoCE (以太网 RDMA, 成本低) ──> 推理集群可选                       │
│                                                                     │
│   资源隔离:                                                          │
│   MIG (硬件级切分, 粒度固定) ──> 多租户强隔离                       │
│   MPS (进程级共享, 灵活) ──> 轻量任务共享                           │
│                                                                     │
│   监控与诊断:                                                        │
│   DCGM ──> GPU 指标采集 ──> Prometheus                             │
│   Xid Error ──> 硬件故障分类                                        │
│   ECC ──> 显存纠错 / 老化预警                                       │
│   GPU Utilization / Memory Utilization ──> 资源使用率               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        发布与弹性                                    │
│                                                                     │
│   弹性伸缩:                                                          │
│   HPA (Kubernetes 原生) ──> 自定义指标 (GPU/队列)                   │
│   KEDA (事件驱动) ──> 消息队列/自定义指标                           │
│   Cold Start (分钟级) ──> Warmup (预加载模型)                       │
│                                                                     │
│   发布策略:                                                          │
│   Canary (少量真实流量验证) ──> 逐步扩大                            │
│   Shadow Traffic (复制流量只读验证) ──> 无用户影响                   │
│   Blue-Green (双环境切换) ──> 零停机但资源翻倍                      │
│   Rolling Update (逐步替换) ──> K8s 默认策略                        │
│                                                                     │
│   可靠性模式:                                                        │
│   Fallback (主路径异常切备用) ──> 质量/成本权衡                     │
│   Circuit Breaking (错误率超阈值停止请求) ──> 防级联                │
│   Rate Limiting (QPS/TPS/并发限制) ──> 防过载                      │
│   Degradation (主动降低质量保核心) ──> 优雅降级                     │
│   Bulkhead (资源舱隔离) ──> 防扩散                                  │
│   Retry (失败重试) ──> 需限制次数防放大                             │
└─────────────────────────────────────────────────────────────────────┘
```

## 易混淆术语辨析

以下表格对比容易混淆的术语，帮助在实际运维中做出正确判断。每组对比都从定义、适用场景和运维关注点三个维度展开。

### TP vs PP vs DP vs EP

这四种并行策略是大模型训练和推理中最基础的并行方式，理解它们的区别对集群规划和性能调优至关重要。

| 维度 | TP（张量并行） | PP（流水线并行） | DP（数据并行） | EP（专家并行） |
|---|---|---|---|---|
| 切分对象 | 单个算子（矩阵乘法） | 模型的层 | 数据批次 | MoE 模型的专家 |
| 并行粒度 | 细粒度，同一层内 | 中粒度，按层分段 | 粗粒度，整个模型副本 | 依赖专家数量 |
| 通信模式 | AllReduce / AllGather（高频） | 点对点发送激活值（阶段间） | AllReduce 梯度（每步） | AllToAll（跨专家路由） |
| 互联要求 | 最高，需 NVLink | 中等，跨节点可接受 | 最低，带宽足够即可 | 高，需快速路由 |
| 典型范围 | 节点内（8 GPU） | 跨节点 | 跨节点 | 跨节点 |
| 显存效率 | 中等，每卡持有部分层 | 中等，每卡持有部分层 | 低，每卡持有完整模型 | 高，每卡只持有部分专家 |
| 运维关注 | NVLink 带宽和拓扑 | 气泡率和阶段均衡 | 梯度同步开销 | 路由倾斜和负载均衡 |
| 典型组合 | TP + PP + DP | TP + PP + DP | 与 FSDP/ZeRO 结合 | 与 TP + DP 结合 |

### SLO vs SLI vs Error Budget

这三个概念是可靠性工程的基石，它们之间有严格的层级关系：SLI 是度量，SLO 是目标，Error Budget 是余量。

| 维度 | SLI | SLO | Error Budget |
|---|---|---|---|
| 定义 | 衡量服务表现的具体指标 | 服务必须达到的目标值 | SLO 允许范围内可消耗的失败额度 |
| 性质 | 度量（事实） | 目标（承诺） | 余量（风险容忍度） |
| 示例 | 过去 5 分钟 P99 TTFT = 800ms | P99 TTFT < 1000ms（30 天窗口） | 30 天内允许 0.1% 请求超过 1000ms |
| 变化频率 | 随请求实时变化 | 按季度或半年评审调整 | 按时间窗口消耗和重置 |
| 运维用途 | 监控告警的输入信号 | 定义"足够好"的可靠性标准 | 决定是否冻结变更、增加实验 |
| 关系 | SLI 是 SLO 的度量基础 | SLO 是 Error Budget 的计算依据 | Error Budget 是 SLO 的衍生品 |
| LLM 特殊性 | 需涵盖 token 级指标和输出质量 | 目标过高会限制迭代和实验 | GPU 故障消耗预算更快 |

### Canary vs Shadow Traffic vs Blue-Green

三种发布策略的风险等级和资源成本各不相同，选择时需要综合考虑发布频率、回滚要求和资源预算。

| 维度 | Canary | Shadow Traffic | Blue-Green |
|---|---|---|---|
| 流量分配 | 将少量真实流量导到新版本 | 复制真实流量到新版本，但结果不返回用户 | 两套环境各承接 100% 容量，切换时全量转移 |
| 用户影响 | 少量用户会体验到新版本 | 零用户影响 | 切换瞬间影响所有用户 |
| 验证方式 | 对比新旧版本的指标 | 对比新旧版本的输出和指标 | 切换前做充分预验证 |
| 回滚速度 | 快，调小流量比例即可 | 快，停止复制即可 | 快，切回旧环境 |
| 资源成本 | 低，新版本只需少量实例 | 中，新版本需承接复制流量 | 高，需维护两套完整环境 |
| 适用场景 | 新版本有一定信心，需逐步验证 | 新版本风险高或需要输出质量对比 | 需要零停机且切换速度要求高 |
| LLM 特殊考量 | 需对比延迟、吞吐和输出质量 | 模型输出非确定性，需多次对比 | 模型加载时间长，需提前预热 |

### LoRA vs QLoRA vs Full Fine-tuning

三种微调方式在成本、质量和适用场景上有显著差异。选择时需要根据可用 GPU 资源、精度要求和迭代频率综合判断。

| 维度 | LoRA | QLoRA | Full Fine-tuning |
|---|---|---|---|
| 训练参数量 | 极少（原模型的 0.1%-1%） | 极少（与 LoRA 相当） | 全部参数 |
| 显存需求 | 中等 | 低（可在消费级 GPU 上训练） | 高（需多卡或分布式） |
| 基座模型精度 | FP16/BF16 | 量化（INT4/NF4） | FP16/BF16/FP32 |
| 训练速度 | 快 | 快 | 慢 |
| 输出质量 | 接近全量微调 | 略低于 LoRA | 最高质量 |
| 制品管理 | Adapter 文件小，便于版本管理 | Adapter 文件小，需记录量化方案 | 完整模型权重，存储成本高 |
| 运维关注 | 多 Adapter 加载切换延迟 | 量化精度损失的评估 | 显存规划、检查点存储和恢复时间 |
| 适用场景 | 快速迭代、多任务适配 | GPU 资源受限、原型验证 | 精度要求极高、预训练数据充足 |

### Prefix Cache vs KV Cache vs Context Cache

三种缓存机制虽然名称相似，但作用层面和实现方式完全不同。

| 维度 | KV Cache | Prefix Cache | Context Cache |
|---|---|---|---|
| 定义 | 缓存已计算 token 的 Key/Value 张量 | 跨请求复用相同前缀的 KV Cache | 在推理服务外部缓存上下文计算结果 |
| 粒度 | 单请求级别 | 跨请求级别（相同前缀） | 跨会话/跨请求级别 |
| 存储位置 | GPU 显存内 | GPU 显存或主机内存 | 外部存储（如 API 服务端缓存） |
| 生命周期 | 随请求结束而释放 | 按缓存策略保留和驱逐 | 按 TTL 或显式管理 |
| 主要收益 | 避免 Decode 阶段重复计算 | 减少相同前缀的 Prefill 时间 | 减少 API 调用的上下文传输和计算 |
| 运维关注 | 显存占用和 OOM 风险 | 命中率、缓存大小和驱逐策略 | 缓存一致性、存储成本和失效机制 |
| 典型实现 | 所有推理引擎内置 | vLLM Automatic Prefix Caching | Anthropic Context Caching API |
| 关系 | Prefix Cache 的基础数据结构 | 基于 KV Cache 的跨请求复用 | 独立于推理引擎的外部缓存层 |

### Quantization 精度方案对比

不同精度格式在位宽、数值类型、显存节省和硬件要求上各不相同。选择时需要综合考虑硬件条件、精度要求和性能目标。

| 维度 | FP32 | BF16 | FP16 | FP8 | INT8 | INT4 |
|---|---|---|---|---|---|---|
| 位宽 | 32 位 | 16 位 | 16 位 | 8 位 | 8 位 | 4 位 |
| 数值类型 | 浮点 | 浮点 | 浮点 | 浮点 | 整数 | 整数 |
| 动态范围 | 最大 | 大 | 中 | 中 | 小 | 最小 |
| 显存节省（vs FP32） | 基线 | 50% | 50% | 75% | 75% | 87.5% |
| 精度损失 | 无 | 极低 | 低 | 低 | 低 | 中到高 |
| 硬件要求 | 通用 GPU | A100+ / V100 | 通用 GPU | H100+ / Ada | 通用 GPU | 通用 GPU |
| 典型用途 | 优化器状态存储 | 训练+推理 | 训练+推理 | 训练+推理 | 推理部署 | 资源受限推理 |
| 运维关注 | 存储成本高 | 溢出风险低 | 可能溢出 | 硬件兼容性 | 质量回归测试 | 精度评估和回退 |

### 发布策略 vs 可靠性模式

发布策略和可靠性模式虽然都涉及流量管理，但目的和时机不同。发布策略关注如何安全地推出新版本，可靠性模式关注如何在异常情况下保护系统。

| 维度 | 发布策略 | 可靠性模式 |
|---|---|---|
| 目的 | 安全地推出新版本 | 在异常情况下保护系统 |
| 时机 | 正常发布流程 | 异常或故障时触发 |
| 典型手段 | Canary、Shadow Traffic、Blue-Green、Rolling Update | Fallback、Circuit Breaking、Rate Limiting、Degradation |
| 关注指标 | 新旧版本对比（延迟、吞吐、质量） | 系统整体健康（错误率、延迟、可用性） |
| 回滚触发 | 新版本指标劣化 | 错误率超阈值或资源耗尽 |
| LLM 特殊性 | 模型输出非确定性，需多次对比 | GPU 资源稀缺，降级策略更激进 |

### 推理引擎对比

主流推理引擎在设计理念、优化策略和适用场景上各有侧重。选择时需要根据业务需求、团队技术栈和运维能力综合判断。

| 维度 | vLLM | SGLang | TGI | Triton | TensorRT-LLM |
|---|---|---|---|---|---|
| 核心优势 | Paged Attention 高吞吐 | 推理编排和复杂请求流 | 部署简洁，生态集成 | 多模型混合部署 | 编译优化极致性能 |
| 适用场景 | 通用推理 | Agent / 多步推理 | HF 生态集成 | 企业级多模型 | 性能敏感场景 |
| Prefix Cache | 支持 | 支持 | 部分支持 | 需配置 | 支持 |
| Continuous Batching | 支持 | 支持 | 支持 | 支持 | 支持 |
| OpenAI 兼容 API | 原生支持 | 支持 | 支持 | 需适配 | 需适配 |
| 多模态支持 | 支持 | 支持 | 支持 | 原生支持 | 支持 |
| 运维复杂度 | 低 | 中 | 低 | 高 | 高（需编译） |
| 社区活跃度 | 高 | 高 | 中 | 中 | 中 |

### 可观测性三支柱

LLM 服务的可观测性需要同时覆盖指标（Metrics）、日志（Logs）和追踪（Traces）三个支柱，缺一不可。

| 维度 | 指标（Metrics） | 日志（Logs） | 追踪（Traces） |
|---|---|---|---|
| 定义 | 聚合的数值型时间序列数据 | 离散的事件记录 | 请求在分布式系统中的完整路径 |
| 典型工具 | Prometheus + Grafana | ELK / Loki | Jaeger / Tempo / OpenTelemetry |
| LLM 关注点 | TTFT、TPOT、GPU 利用率、KV Cache 使用率 | 推理错误、模型加载事件、安全告警 | 请求在检索、推理、工具调用各阶段的耗时 |
| 采样策略 | 全量采集（高频聚合） | 按级别采样（错误全量，正常采样） | 按比例采样（1%-10%） |
| 存储成本 | 低（聚合后数据量小） | 高（原始日志量大） | 中（按采样比例） |
| 运维价值 | 实时告警和趋势分析 | 故障根因分析和审计 | 性能瓶颈定位和依赖分析 |

## 术语速查索引

以下按字母顺序列出所有术语，方便快速定位。

| 术语 | 所属分类 | 页内跳转 |
|---|---|---|
| ABAC | 安全与治理类 | [跳转](#安全与治理类) |
| Agent Runtime | RAG 与应用类 | [跳转](#rag-与应用类) |
| AllReduce | 训练与并行类 | [跳转](#训练与并行类) |
| A/B Testing | 部署与架构类 | [跳转](#部署与架构类) |
| BF16 | 量化与优化类 | [跳转](#量化与优化类) |
| Blue-Green | 部署与架构类 | [跳转](#部署与架构类) |
| Bulkhead | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Canary | 部署与架构类 | [跳转](#部署与架构类) |
| Checkpoint | 训练与并行类 | [跳转](#训练与并行类) |
| Chunking | RAG 与应用类 | [跳转](#rag-与应用类) |
| Circuit Breaking | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Cold Start | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Concurrency | 推理指标类 | [跳转](#推理指标类) |
| Content Safety | 安全与治理类 | [跳转](#安全与治理类) |
| Context Window | KV Cache 与显存类 | [跳转(#kv-cache-与显存类) |
| Context Window Bloat | RAG 与应用类 | [跳转](#rag-与应用类) |
| Continuous Batching | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| CUDA | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| CUDA Graph | 量化与优化类 | [跳转](#量化与优化类) |
| DCGM | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| DDP | 训练与并行类 | [跳转](#训练与并行类) |
| Decode | 推理指标类 | [跳转](#推理指标类) |
| Degradation | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| DP | 训练与并行类 | [跳转](#训练与并行类) |
| Dynamic Batching | 量化与优化类 | [跳转](#量化与优化类) |
| E2E Latency | 推理指标类 | [跳转](#推理指标类) |
| ECC | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Embedding | RAG 与应用类 | [跳转](#rag-与应用类) |
| EP | 训练与并行类 | [跳转](#训练与并行类) |
| Error Budget | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Fallback | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| FSDP | 训练与并行类 | [跳转](#训练与并行类) |
| Flash Attention | 量化与优化类 | [跳转](#量化与优化类) |
| FP16 | 量化与优化类 | [跳转](#量化与优化类) |
| FP32 | 量化与优化类 | [跳转](#量化与优化类) |
| FP8 | 量化与优化类 | [跳转](#量化与优化类) |
| Goodput | 推理指标类 | [跳转](#推理指标类) |
| GPU Memory Utilization | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| GPU Utilization | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Graceful Degradation | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Gradient Accumulation | 训练与并行类 | [跳转](#训练与并行类) |
| Grounding | RAG 与应用类 | [跳转](#rag-与应用类) |
| Guardrail | 安全与治理类 | [跳转](#安全与治理类) |
| Hallucination | RAG 与应用类 | [跳转](#rag-与应用类) |
| HPA | 部署与架构类 | [跳转](#部署与架构类) |
| HBM | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| Health Check | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Hybrid Search | RAG 与应用类 | [跳转](#rag-与应用类) |
| InfiniBand | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| INT4 | 量化与优化类 | [跳转](#量化与优化类) |
| INT8 | 量化与优化类 | [跳转](#量化与优化类) |
| Jailbreak | 安全与治理类 | [跳转](#安全与治理类) |
| KEDA | 部署与架构类 | [跳转](#部署与架构类) |
| Kernel Fusion | 量化与优化类 | [跳转](#量化与优化类) |
| KServe | 部署与架构类 | [跳转](#部署与架构类) |
| KV Cache | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| LoRA | 量化与优化类 | [跳转](#量化与优化类) |
| Max Batched Tokens | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| MFU | 训练与并行类 | [跳转](#训练与并行类) |
| MIG | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Mixed Precision | 训练与并行类 | [跳转](#训练与并行类) |
| Model Card | 安全与治理类 | [跳转](#安全与治理类) |
| Model Registry | 部署与架构类 | [跳转](#部署与架构类) |
| MoE | 训练与并行类 | [跳转](#训练与并行类) |
| MPS | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Multi-Region | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Multi-Tenancy | 安全与治理类 | [跳转](#安全与治理类) |
| NVLink | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| NVSwitch | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| OIDC | 安全与治理类 | [跳转](#安全与治理类) |
| Offloading | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| OOM | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| OpenTelemetry | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| P50 | 推理指标类 | [跳转](#推理指标类) |
| P95 | 推理指标类 | [跳转](#推理指标类) |
| P99 | 推理指标类 | [跳转](#推理指标类) |
| Paged Attention | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| PCIe | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| PEFT | 量化与优化类 | [跳转](#量化与优化类) |
| PII | 安全与治理类 | [跳转](#安全与治理类) |
| PP | 训练与并行类 | [跳转](#训练与并行类) |
| Prefix Cache | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| Prefill | 推理指标类 | [跳转](#推理指标类) |
| Prometheus | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Prompt Injection | 安全与治理类 | [跳转](#安全与治理类) |
| PTQ | 量化与优化类 | [跳转](#量化与优化类) |
| QAT | 量化与优化类 | [跳转](#量化与优化类) |
| QLoRA | 量化与优化类 | [跳转](#量化与优化类) |
| QPS | 推理指标类 | [跳转](#推理指标类) |
| Quantization | 量化与优化类 | [跳转](#量化与优化类) |
| Queue Time | 推理指标类 | [跳转](#推理指标类) |
| RAG | RAG 与应用类 | [跳转](#rag-与应用类) |
| Rate Limiting | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| RBAC | 安全与治理类 | [跳转](#安全与治理类) |
| RDMA | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Re-ranker | RAG 与应用类 | [跳转](#rag-与应用类) |
| Recall Rate | RAG 与应用类 | [跳转](#rag-与应用类) |
| Retrieval Latency | RAG 与应用类 | [跳转](#rag-与应用类) |
| Retry | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| RoCE | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Rolling Update | 部署与架构类 | [跳转](#部署与架构类) |
| Scaling Law | 训练与并行类 | [跳转](#训练与并行类) |
| Session State | RAG 与应用类 | [跳转](#rag-与应用类) |
| Shadow Traffic | 部署与架构类 | [跳转](#部署与架构类) |
| SLI | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| SLO | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| SGLang | 部署与架构类 | [跳转](#部署与架构类) |
| Speculative Decoding | 量化与优化类 | [跳转](#量化与优化类) |
| SSO | 安全与治理类 | [跳转](#安全与治理类) |
| Streaming | 推理指标类 | [跳转](#推理指标类) |
| Telemetry | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| Temperature | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| TensorRT-LLM | 部署与架构类 | [跳转](#部署与架构类) |
| Throughput | 推理指标类 | [跳转](#推理指标类) |
| Timeout | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| TGI | 部署与架构类 | [跳转](#部署与架构类) |
| Tokenizer | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| Tool Calling | RAG 与应用类 | [跳转](#rag-与应用类) |
| Top-P / Top-K | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| TP | 训练与并行类 | [跳转](#训练与并行类) |
| TPOT | 推理指标类 | [跳转](#推理指标类) |
| TPS | 推理指标类 | [跳转](#推理指标类) |
| Triton | 部署与架构类 | [跳转](#部署与架构类) |
| TTFT | 推理指标类 | [跳转](#推理指标类) |
| Vector Database | RAG 与应用类 | [跳转](#rag-与应用类) |
| vLLM | 部署与架构类 | [跳转](#部署与架构类) |
| VRAM | KV Cache 与显存类 | [跳转](#kv-cache-与显存类) |
| Waiting Requests | 推理指标类 | [跳转](#推理指标类) |
| Warmup | 可靠性与运维类 | [跳转](#可靠性与运维类) |
| Xid Error | GPU 与硬件类 | [跳转](#gpu-与硬件类) |
| ZeRO | 训练与并行类 | [跳转](#训练与并行类) |

## 术语数量统计

| 分类 | 术语数量 |
|---|---|
| 推理指标类 | 16 |
| 训练与并行类 | 14 |
| KV Cache 与显存类 | 13 |
| 部署与架构类 | 14 |
| RAG 与应用类 | 13 |
| 安全与治理类 | 12 |
| 可靠性与运维类 | 14 |
| 量化与优化类 | 16 |
| GPU 与硬件类 | 14 |
| **合计** | **126** |
