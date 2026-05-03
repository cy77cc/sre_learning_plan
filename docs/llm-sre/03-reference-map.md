# LLM SRE 参考地图

> 日期：2026-05-03
> 学习主题：LLM SRE 相关参考资料索引

## 使用说明

本参考地图是 LLM SRE 专题的资料索引层，目标是帮助你快速找到权威一手资料。它不是收藏夹，不追求"全"，而是每类资源只保留最值得长期跟踪的入口。

**优先级说明**：

| 优先级 | 含义 | 使用场景 |
|--------|------|----------|
| 必读 | 该领域的权威定义或核心工程实践，不读会在生产中踩坑 | 首次接触该主题、面试准备、方案设计前 |
| 推荐 | 高质量补充资料，能显著加深理解或提供实操参考 | 已有基础后深入学习、性能调优、故障复盘 |
| 按需 | 特定场景下有用，平时不必通读 | 遇到具体问题时定向查阅 |

**查阅策略**：

1. 查概念定义时，优先看官方文档，不先看二手总结
2. 查工程实现时，先看活跃开源项目的 README 和文档，再回到源码和 issue
3. 查性能优化时，先建立自己的指标基线，再看论文或博客中的收益数字，避免直接照搬
4. 查架构方案时，把资料按"单机推理、单集群、多租户平台、跨区域服务"四类分开看，减少误用
5. 每种框架最多保留 1 份官方入口、1 个基准实现、1 篇高质量经验文，避免收藏很多但从不复用

**与专题文档的关联**：本地图中每条资源的"关联文档"列指向本目录中的教程或手册，方便从资料直接跳回知识体系。

---

## 一、官方文档

### 1.1 推理引擎

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [vLLM 官方文档](https://docs.vllm.ai/) | 高吞吐 LLM 推理引擎的权威参考，覆盖 PagedAttention、连续批处理、Prefix Cache、OpenAI 兼容 API 等核心机制 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [vLLM GitHub](https://github.com/vllm-project/vllm) | 源码、Issue、Release Notes、性能基准数据的第一手来源 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [SGLang 官方文档](https://sgl-project.github.io/) | 面向复杂推理编排和 Agent 场景的推理框架文档，涵盖 RadixAttention、结构化生成、前端 DSL | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [SGLang GitHub](https://github.com/sgl-project/sglang) | 源码和社区讨论，适合跟踪前沿优化特性 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Text Generation Inference (TGI) 文档](https://huggingface.co/docs/text-generation-inference) | Hugging Face 官方推理服务文档，部署形态清晰，与 HF 生态深度集成 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [TGI GitHub](https://github.com/huggingface/text-generation-inference) | 源码、Docker 镜像、配置参考和社区 Issue | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [TensorRT-LLM 文档](https://nvidia.github.io/TensorRT-LLM/) | NVIDIA 官方 LLM 推理优化引擎，覆盖量化、KV Cache 管理、Inflight Batching 等能力 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [TensorRT-LLM GitHub](https://github.com/NVIDIA/TensorRT-LLM) | 源码和模型支持矩阵，适合确认特定模型的兼容性 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Triton Inference Server 文档](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/) | NVIDIA 企业级模型服务框架，覆盖多模型并发、后端抽象、模型仓库管理 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Triton Inference Server GitHub](https://github.com/triton-inference-server/server) | 源码和部署示例，适合理解多后端集成方式 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp) | C/C++ 实现的轻量推理引擎，适合理解量化推理和非 GPU 环境部署 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 1.2 GPU 与集群硬件

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [NVIDIA CUDA Toolkit 文档](https://docs.nvidia.com/cuda/) | GPU 编程和计算能力的权威参考，适合理解推理引擎底层依赖 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [NVIDIA NCCL 文档](https://docs.nvidia.com/deeplearning/nccl/) | 多 GPU/多节点集合通信库文档，分布式训练和推理 TP 的底层依赖 | 必读 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [NVIDIA DCGM 文档](https://docs.nvidia.com/datacenter/dcgm/latest/) | GPU 集群健康检查、性能监控和诊断工具的官方文档 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [NVIDIA DCGM Exporter GitHub](https://github.com/NVIDIA/dcgm-exporter) | 将 DCGM 指标导出为 Prometheus 格式的标准组件 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [NVIDIA GPU 架构白皮书](https://www.nvidia.com/en-us/data-center/technologies/) | 各代 GPU（A100/H100/H200/B200）的架构详解，适合选型和容量规划 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [NVLink 和 NVSwitch 技术文档](https://www.nvidia.com/en-us/data-center/nvlink/) | GPU 互联技术参考，直接影响 TP 性能和多 GPU 推理效率 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [NVIDIA MIG 文档](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/) | Multi-Instance GPU 技术文档，适合多租户 GPU 隔离场景 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [NVIDIA MPS 文档](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/) | Multi-Process Service，允许多个进程共享同一 GPU，适合推理场景的轻量隔离 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [NVIDIA cuDNN 文档](https://docs.nvidia.com/deeplearning/cudnn/) | GPU 深度学习原语库，推理引擎的底层计算依赖 | 按需 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [InfiniBand 技术文档](https://network.nvidia.com/technology/infiniband/) | 高性能互联网络技术，多节点训练和推理集群的核心网络基础 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [RDMA 网络文档](https://network.nvidia.com/technology/rdma/) | 远程直接内存访问技术，NCCL 集合通信的底层网络传输 | 推荐 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |

### 1.3 容器与编排

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Kubernetes 官方文档](https://kubernetes.io/docs/) | 容器编排权威参考，调度、资源管理、HPA、探针、滚动升级等机制的第一手来源 | 必读 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [NVIDIA Device Plugin for Kubernetes](https://github.com/NVIDIA/k8s-device-plugin) | 将 GPU 暴露为 Kubernetes 可调度资源的标准插件 | 必读 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/) | 在 Kubernetes 上自动化部署 GPU 驱动、运行时和监控组件的 Operator | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [KServe 文档](https://kserve.github.io/website/) | Kubernetes 原生的模型推理服务框架，覆盖自动扩缩容、流量切分、模型版本管理 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [KServe GitHub](https://github.com/kserve/kserve) | 源码和部署示例，适合理解与 Kubernetes 生态的集成方式 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Slurm 文档](https://slurm.schedmd.com/documentation.html) | HPC 集群调度器文档，大规模训练集群的常用调度方案 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [Kueue 文档](https://kubernetes.io/docs/concepts/workload-queues/) | Kubernetes 原生作业队列管理，适合 GPU 资源排队和多租户配额管理 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [Volcano 文档](https://volcano.sh/en/docs/) | Kubernetes 上的批量计算调度器，支持 GPU 共享、gang scheduling 等 AI 训练场景 | 按需 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [Istio 文档](https://istio.io/latest/docs/) | 服务网格，适合推理服务的流量管理、灰度发布和可观测性增强 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Envoy 文档](https://www.envoyproxy.io/docs/envoy/) | 高性能代理，推理网关的底层数据面，适合理解请求路由和负载均衡机制 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Gateway API 文档](https://gateway-api.sigs.k8s.io/) | Kubernetes 原生的网关 API 标准，适合构建推理服务的统一入口 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Argo Workflows 文档](https://argoproj.github.io/workflows/) | Kubernetes 原生的工作流引擎，适合编排模型训练和微调流水线 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |

### 1.4 可观测性

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [OpenTelemetry 文档](https://opentelemetry.io/docs/) | 分布式追踪、指标和日志的统一规范，LLM 请求全链路追踪的标准方案 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Prometheus 文档](https://prometheus.io/docs/) | 指标采集和告警的标准工具，GPU 指标和推理指标的核心存储 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Grafana 文档](https://grafana.com/docs/) | 可视化和仪表盘平台，GPU 和推理服务监控面板的构建工具 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [PyTorch Profiler 文档](https://pytorch.org/docs/stable/profiler.html) | 训练和推理的性能分析工具，适合定位 GPU 计算瓶颈 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Loki 文档](https://grafana.com/docs/loki/) | 日志聚合系统，适合收集推理引擎日志和 GPU 驱动日志 | 推荐 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Tempo 文档](https://grafana.com/docs/tempo/) | 分布式追踪后端，OpenTelemetry 兼容，适合存储 LLM 请求链路追踪数据 | 推荐 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Alertmanager 文档](https://prometheus.io/docs/alerting/latest/alertmanager/) | Prometheus 告警管理器，GPU OOM、推理延迟飙升等告警的路由和通知组件 | 必读 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |

### 1.5 向量数据库与 RAG 基础设施

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Milvus 文档](https://milvus.io/docs) | 高性能向量数据库，适合大规模 RAG 场景的向量检索 | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Milvus GitHub](https://github.com/milvus-io/milvus) | 源码和部署方案，适合理解分布式向量检索架构 | 按需 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Qdrant 文档](https://qdrant.tech/documentation/) | Rust 实现的向量数据库，部署轻量，适合中小规模 RAG 场景 | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Qdrant GitHub](https://github.com/qdrant/qdrant) | 源码和性能基准数据 | 按需 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [pgvector 文档](https://github.com/pgvector/pgvector) | PostgreSQL 向量检索扩展，适合已有 PG 基础设施的团队快速接入 RAG | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Weaviate 文档](https://weaviate.io/developers/weaviate) | 向量数据库，内置多种 Embedding 模型集成，适合快速原型验证 | 按需 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Chroma 文档](https://docs.trychroma.com/) | 轻量级嵌入式向量数据库，适合开发测试和小规模场景 | 按需 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Jina AI 文档](https://jina.ai/) | 嵌入模型和重排序模型的服务化框架，RAG 检索质量优化的常用组件 | 按需 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [TEI (Text Embeddings Inference) GitHub](https://github.com/huggingface/text-embeddings-inference) | Hugging Face 的嵌入模型推理服务，高性能向量化组件 | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |

### 1.6 模型生态与工具链

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Hugging Face Transformers 文档](https://huggingface.co/docs/transformers/) | 模型加载、Tokenizer、推理接口的事实标准库 | 必读 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Hugging Face PEFT 文档](https://huggingface.co/docs/peft/) | 参数高效微调（LoRA、QLoRA 等）的官方实现文档 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Hugging Face Hub 文档](https://huggingface.co/docs/hub/) | 模型仓库管理、版本控制和模型分发的平台文档 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [PyTorch 文档](https://pytorch.org/docs/stable/) | 训练框架权威参考，覆盖 FSDP、分布式训练、Profiler 等核心能力 | 必读 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [DeepSpeed 文档](https://www.deepspeed.ai/docs/) | 微软的分布式训练优化库，ZeRO 优化、推理加速、混合引擎的核心参考 | 推荐 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [Megatron-LM GitHub](https://github.com/NVIDIA/Megatron-LM) | NVIDIA 的大规模 LLM 训练框架，TP/PP/EP 等并行策略的参考实现 | 推荐 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [bitsandbytes GitHub](https://github.com/TimDettmers/bitsandbytes) | 量化工具库，LLM.int8() 和 QLoRA 的底层实现 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [GPTQ GitHub](https://github.com/IST-DASLab/gptq) | 后训练量化方法实现，将 LLM 量化到 4/3/2 bit | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [AWQ GitHub](https://github.com/mit-han-lab/llm-awq) | 激活感知权重量化方法，推理友好的量化方案 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [AutoGPTQ GitHub](https://github.com/AutoGPTQ/AutoGPTQ) | GPTQ 量化的易用封装，适合快速对模型进行量化 | 按需 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 1.7 安全与合规

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) | LLM 应用安全风险的权威清单，Prompt 注入、数据泄露等威胁的分类参考 | 必读 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [NIST AI Risk Management Framework](https://www.nist.gov/artificial-intelligence) | AI 系统风险管理的标准化框架，适合合规审计和治理设计 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [EU AI Act 官方文本](https://artificialintelligenceact.eu/) | 欧盟 AI 法规，高风险 AI 系统合规要求的第一手来源 | 按需 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |

---

## 二、开源项目

### 2.1 推理引擎

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| vLLM | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 高吞吐 LLM 推理引擎，PagedAttention 和连续批处理的标杆实现 | 非常活跃，周级更新 | 生产级 LLM 推理服务的默认选择 |
| SGLang | [sgl-project/sglang](https://github.com/sgl-project/sglang) | 面向复杂推理编排的框架，RadixAttention 实现高效 Prefix Cache | 非常活跃 | Agent/多轮对话/复杂推理流程 |
| TGI | [huggingface/text-generation-inference](https://github.com/huggingface/text-generation-inference) | HF 生态的推理服务，部署形态清晰，与 HF 模型库无缝集成 | 活跃 | HF 模型快速部署、标准化推理服务 |
| TensorRT-LLM | [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | NVIDIA 官方 LLM 推理优化引擎，极致性能调优 | 活跃 | NVIDIA GPU 上追求极致推理性能 |
| Triton Inference Server | [triton-inference-server/server](https://github.com/triton-inference-server/server) | 企业级多模型服务框架，支持多种推理后端 | 活跃 | 多模型并发服务、企业级部署 |
| llama.cpp | [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) | C/C++ 轻量推理引擎，支持多种量化格式 | 非常活跃 | 边缘设备、CPU 推理、量化部署 |
| Ollama | [ollama/ollama](https://github.com/ollama/ollama) | 本地 LLM 运行工具，一行命令启动推理服务 | 非常活跃 | 开发测试、本地原型验证 |
| Ray Serve | [ray-project/ray](https://github.com/ray-project/ray) | 分布式模型服务编排，支持弹性扩展和多组件推理工作流 | 活跃 | 复杂推理流水线、多模型编排 |

### 2.2 训练框架

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| DeepSpeed | [microsoft/DeepSpeed](https://github.com/microsoft/DeepSpeed) | 微软分布式训练库，ZeRO 系列优化和 DeepSpeed-MoE 的参考实现 | 活跃 | 大规模分布式训练、显存优化 |
| Megatron-LM | [NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM) | NVIDIA 大规模 LLM 训练框架，TP/PP/EP 的工业级实现 | 活跃 | 超大规模模型训练、并行策略参考 |
| PyTorch FSDP | [pytorch/pytorch](https://github.com/pytorch/pytorch) | PyTorch 原生的全分片数据并行，与 PyTorch 生态深度集成 | 非常活跃 | 标准分布式训练方案 |
| ColossalAI | [hpcaitech/ColossalAI](https://github.com/hpcaitech/ColossalAI) | 面向大模型的高效分布式训练工具，提供多种并行策略 | 活跃 | 快速搭建分布式训练环境 |
| OpenRLHF | [OpenRLHF/OpenRLHF](https://github.com/OpenRLHF/OpenRLHF) | 基于 Ray 的 RLHF 训练框架，支持 PPO/DPO/RLHF 全流程 | 活跃 | 对齐训练（RLHF/DPO） |
| LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) | 一站式 LLM 微调框架，支持 100+ 模型和多种微调方法 | 非常活跃 | 快速微调实验、LoRA/QLoRA 微调 |
| Axolotl](https://github.com/axolotl-ai-cloud/axolotl) | 面向研究者的微调工具，配置驱动，支持多种训练后端 | 活跃 | 灵活的微调实验 |

### 2.3 RAG 与 Agent 框架

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| LangChain | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | LLM 应用开发框架，提供链式调用、RAG、Agent 等标准化组件 | 非常活跃 | RAG 应用快速开发、Agent 构建 |
| LlamaIndex | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 数据框架，专注于将私有数据与 LLM 连接的索引和检索 | 非常活跃 | 企业级 RAG 系统 |
| Haystack | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 端到端 NLP/RAG 框架，模块化设计，支持多种检索和生成组件 | 活跃 | 生产级 RAG 管道 |
| Dify | [langgenius/dify](https://github.com/langgenius/dify) | 可视化 LLM 应用开发平台，内置 RAG 引擎和工作流编排 | 非常活跃 | 低代码 LLM 应用构建 |
| FastGPT | [labring/FastGPT](https://github.com/labring/FastGPT) | 基于 LLM 的知识库问答平台，内置向量检索和对话管理 | 活跃 | 企业知识库问答 |
| CrewAI | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 多 Agent 协作框架，角色定义和任务编排 | 活跃 | 多 Agent 协作场景 |
| AutoGen | [microsoft/autogen](https://github.com/microsoft/autogen) | 微软多 Agent 对话框架，支持复杂 Agent 工作流 | 活跃 | 多 Agent 对话和协作 |

### 2.4 可观测性与监控工具

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| DCGM Exporter | [NVIDIA/dcgm-exporter](https://github.com/NVIDIA/dcgm-exporter) | GPU 指标导出为 Prometheus 格式的标准组件 | 活跃 | GPU 监控的基础设施层 |
| OpenLLMetry | [traceloop/openllmetry](https://github.com/traceloop/openllmetry) | 基于 OpenTelemetry 的 LLM 应用可观测性 SDK | 活跃 | LLM 请求追踪和指标采集 |
| LangSmith | [langchain-ai/langsmith](https://github.com/langchain-ai/langsmith-docs) | LangChain 官方的追踪和评估平台 | 活跃 | LangChain 应用的调试和监控 |
| Phoenix | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | LLM 应用可观测性工具，支持追踪、评估和嵌入分析 | 活跃 | LLM 应用的质量监控 |
| Prometheus | [prometheus/prometheus](https://github.com/prometheus/prometheus) | 指标采集和时序数据库，监控基础设施的事实标准 | 非常活跃 | 所有场景的指标存储 |
| Grafana | [grafana/grafana](https://github.com/grafana/grafana) | 可视化和仪表盘平台 | 非常活跃 | 监控面板构建 |
| Jaeger | [jaegertracing/jaeger](https://github.com/jaegertracing/jaeger) | 分布式追踪系统，OpenTelemetry 兼容 | 活跃 | 请求链路追踪 |

### 2.5 模型管理与实验跟踪

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| MLflow | [mlflow/mlflow](https://github.com/mlflow/mlflow) | 机器学习生命周期管理，实验跟踪、模型注册和部署 | 非常活跃 | 模型版本管理和实验记录 |
| Weights & Biases | [wandb/wandb](https://github.com/wandb/wandb) | 实验跟踪和可视化平台，训练过程监控 | 非常活跃 | 训练实验跟踪、模型对比 |
| DVC | [iterative/dvc](https://github.com/iterative/dvc) | 数据版本控制，Git-like 的大文件和数据集管理 | 活跃 | 训练数据和模型制品的版本管理 |
| ZenML | [zenml-io/zenml](https://github.com/zenml-io/zenml) | MLOps 框架，标准化 ML 管道定义和执行 | 活跃 | ML 管道标准化和可复现性 |
| BentoML | [bentoml/BentoML](https://github.com/bentoml/BentoML) | 模型服务化框架，将模型打包为标准化部署单元 | 活跃 | 模型服务化和容器化部署 |
| SkyPilot](https://github.com/skypilot-org/skypilot) | 跨云 AI 训练和推理的统一调度框架 | 活跃 | 多云 GPU 资源调度和成本优化 |

### 2.6 基础设施工具

| 项目 | GitHub 地址 | 一句话定位 | 活跃状态 | 典型使用场景 |
|------|------------|-----------|---------|-------------|
| KServe | [kserve/kserve](https://github.com/kserve/kserve) | Kubernetes 原生模型推理服务框架 | 活跃 | 模型服务的 Kubernetes 集成 |
| NVIDIA GPU Operator | [NVIDIA/gpu-operator](https://github.com/NVIDIA/gpu-operator) | Kubernetes GPU 环境自动化部署 | 活跃 | GPU 集群初始化和管理 |
| KubeRay | [ray-project/kuberay](https://github.com/ray-project/kuberay) | 在 Kubernetes 上运行 Ray 集群的 Operator | 活跃 | 分布式推理和训练的编排 |
| Hugging Face Hub Client | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) | 模型仓库交互的 Python 客户端 | 非常活跃 | 模型上传下载、版本管理 |

---

## 三、论文与技术博客

### 3.1 必读论文

| 论文 | 作者/年份 | 一句话总结 | SRE 关联度 | 关联文档 |
|------|----------|-----------|-----------|----------|
| [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | Vaswani et al., 2017 | 提出 Transformer 架构，奠定所有现代 LLM 的基础 | 理解 LLM 推理的底层计算模式 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180) | Kwon et al., 2023 | 提出 PagedAttention，将操作系统的虚拟内存思想应用于 KV Cache 管理 | 直接影响推理服务的吞吐和显存效率 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) | Hu et al., 2021 | 通过低秩分解实现参数高效微调，大幅降低微调的显存和计算需求 | 改变微调流程和模型制品管理方式 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314) | Dettmers et al., 2023 | 在量化模型上进行 LoRA 微调，单卡即可微调 65B 模型 | 降低微调硬件门槛，影响容量规划 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Efficiently Scaling Transformer Inference](https://arxiv.org/abs/2211.05102) | Pope et al., 2022 | Google 关于 Transformer 推理效率优化的系统性分析，涵盖批处理、量化和并行策略 | 推理性能优化的理论基础 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135) | Dao et al., 2022 | 通过 IO 感知的算法设计实现注意力计算加速，减少显存占用 | 主流推理引擎的底层优化依赖 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning](https://arxiv.org/abs/2307.08691) | Dao, 2023 | FlashAttention 的改进版本，进一步提升并行效率 | 推理和训练性能优化 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [ZeRO: Memory Optimizations Toward Training Trillion Parameter Models](https://arxiv.org/abs/1910.02054) | Rajbhandari et al., 2020 | DeepSpeed 的核心优化，通过分片减少分布式训练的显存占用 | 分布式训练显存优化的理论基础 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism](https://arxiv.org/abs/1909.08053) | Shoeybi et al., 2019 | 提出张量并行和流水线并行的实用方案，大规模训练的工程参考 | 分布式训练并行策略 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |
| [Mixtral of Experts](https://arxiv.org/abs/2401.04088) | Jiang et al., 2024 | 混合专家模型的工程实现参考，MoE 架构的路由和负载均衡问题 | MoE 推理调度和负载均衡挑战 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437) | DeepSeek, 2024 | MoE 架构 + Multi-head Latent Attention，代表前沿模型的工程实践 | 前沿架构对推理平台的影响 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) | Lewis et al., 2020 | 提出 RAG 范式，将检索与生成结合 | RAG 系统架构的理论基础 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) | Wei et al., 2022 | 提出思维链提示方法，影响推理服务的 token 消耗和延迟模型 | 影响容量规划和 SLO 设计 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |

### 3.2 推荐论文

| 论文 | 作者/年份 | 一句话总结 | SRE 关联度 | 关联文档 |
|------|----------|-----------|-----------|----------|
| [Orca: A Distributed Serving System for Transformer-Based Generative Models](https://www.usenix.org/conference/osdi22/presentation/yu) | Yu et al., 2022 | 提出连续批处理（Iteration-level Scheduling），后来被 vLLM 等框架广泛采用 | 推理引擎批处理策略的理论基础 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [SGLang: Efficient Execution of Structured Language Model Programs](https://arxiv.org/abs/2312.07104) | Zheng et al., 2024 | 提出 RadixAttention 和推理编排 DSL，优化复杂 LLM 程序的执行效率 | 推理编排和 Prefix Cache 优化 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Towards Efficient Generative Large Language Model Serving: A Survey from Algorithms to Systems](https://arxiv.org/abs/2312.15234) | Miao et al., 2023 | LLM 推理优化的综述，系统性梳理从算法到系统的优化空间 | 全面了解推理优化方向 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245) | Ainslie et al., 2023 | 提出分组查询注意力，减少 KV Cache 大小，提升推理效率 | KV Cache 优化策略 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [SpecInfer: Accelerating Generative Large Language Model Serving with Tree-based Speculative Inference and Verification](https://arxiv.org/abs/2305.09781) | Miao et al., 2023 | 投机解码的系统实现参考，通过小模型猜测 + 大模型验证提升吞吐 | 投机解码工程实现 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving](https://arxiv.org/abs/2401.09670) | Zhong et al., 2024 | 将 Prefill 和 Decode 阶段解耦到不同硬件，优化整体吞吐 | Prefill/Decode 解耦架构 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving](https://arxiv.org/abs/2407.00079) | Qin et al., 2024 | Moonshot AI 的 KV Cache 为中心的解耦架构实践 | KV Cache 管理和解耦架构 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [LLM in a flash: Efficient Large Language Model Inference with Limited Memory](https://arxiv.org/abs/2312.11514) | Alizadeh et al., 2024 | Apple 研究在内存受限设备上高效运行 LLM 的方法 | 边缘推理和量化部署 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556) | Hoffmann et al., 2022 | Chinchilla 论文，提出计算最优的模型大小与数据量比例 | 训练资源配置和容量规划参考 | [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) |
| [A Survey on Large Language Model Hallucination via a Creativity Perspective](https://arxiv.org/abs/2402.00253) | Huang et al., 2024 | LLM 幻觉问题综述，理解模型输出质量的局限性 | 输出质量监控和 SLO 设计参考 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |

### 3.3 工程博客

#### 推理引擎团队博客

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [vLLM 博客](https://blog.vllm.ai/) | vLLM 版本发布、性能基准、新特性解读 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [SGLang 博客](https://lmsys.org/blog/) | SGLang 和 LMSYS 团队的技术博客，覆盖推理优化和系统设计 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Hugging Face 博客](https://huggingface.co/blog) | HF 生态动态，模型发布，推理和训练工具更新 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [NVIDIA 技术博客](https://developer.nvidia.com/blog/) | GPU 技术、TensorRT、推理优化、集群管理的工程实践 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |

#### 云厂商 AI 工程博客

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [AWS Machine Learning Blog](https://aws.amazon.com/blogs/machine-learning/) | AWS 上的 LLM 部署、SageMaker 推理优化和大规模训练实践 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Google Cloud AI Blog](https://cloud.google.com/blog/products/ai-machine-learning) | GCP 上的 Vertex AI、TPU 推理和分布式训练实践 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Azure AI Blog](https://techcommunity.microsoft.com/t5/ai-azure-ai-blog/bg-p/AzureAIBlog) | Azure AI 服务、模型部署和企业级 AI 平台实践 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Anthropic 研究博客](https://www.anthropic.com/research) | Anthropic 的安全对齐研究和工程实践 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [OpenAI 博客](https://openai.com/blog) | 模型发布、API 更新和安全研究 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |

#### 社区工程博客

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [The Batch (Andrew Ng)](https://www.deeplearning.ai/the-batch/) | AI 行业动态和工程实践的周报 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [Chip Huyen 博客](https://huyenchip.com/blog/) | ML 系统设计和 LLMOps 的高质量工程文章 | 必读 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Eugene Yan 博客](https://eugeneyan.com/) | 推荐系统和 LLM 应用的工程实践 | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [Lilian Weng 博客](https://lilianweng.github.io/) | 深度学习和 LLM 主题的深度技术文章 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Simon Willison 博客](https://simonwillison.net/) | LLM 工具生态和应用开发的实践跟踪 | 推荐 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| [MLOps Community 博客](https://mlops.community/blog/) | MLOps 和 LLMOps 工程实践的社区博客 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Towards Data Science](https://towardsdatascience.com/) | 数据科学和 ML 工程的技术文章，LLM 相关内容丰富 | 按需 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |

#### 模型提供商官方文档

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [OpenAI API 文档](https://platform.openai.com/docs/) | OpenAI API 的参考标准，推理接口设计的事实基准 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Anthropic API 文档](https://docs.anthropic.com/) | Claude API 文档，长上下文和工具调用的参考 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Google Gemini API 文档](https://ai.google.dev/docs) | Gemini API 文档，多模态推理的参考 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Mistral API 文档](https://docs.mistral.ai/) | Mistral 模型的 API 文档，开源模型的商业推理服务参考 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |

#### 值得关注的年度报告和白皮书

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [State of AI Report](https://www.stateof.ai/) | 年度 AI 行业综合报告，覆盖研究、产业和安全 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [Stanford AI Index Report](https://aiindex.stanford.edu/) | 斯坦福年度 AI 指数报告，数据驱动的行业趋势分析 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [CNCF AI/WG White Papers](https://github.com/cncf/tag-ai) | 云原生基金会 AI 工作组的白皮书，Kubernetes 上运行 AI 工作负载的指导 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |

---

## 四、基准测试与评测资料

### 4.1 推理性能基准

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [vLLM 性能基准](https://docs.vllm.ai/en/latest/features/performance.html) | vLLM 官方性能数据和基准测试方法 | 必读 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [SGLang 性能基准](https://sgl-project.github.io/references/benchmark.html) | SGLang 官方性能对比数据 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Anyscale LLM 推理基准](https://www.anyscale.com/blog/comparing-llm-serving-frameworks) | 多推理框架的横向性能对比 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Artificial Analysis](https://artificialanalysis.ai/) | LLM 推理服务的独立性能和成本分析平台 | 推荐 | [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) |

### 4.2 模型评测

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Open LLM Leaderboard (Hugging Face)](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard) | 开源 LLM 的标准化评测排行榜 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [LMSYS Chatbot Arena](https://chat.lmsys.org/) | 基于人类偏好的 LLM 对比评测平台，ELO 排名 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [MMLU 基准](https://arxiv.org/abs/2009.03300) | 大规模多任务语言理解评测，模型能力的通用参考 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [HELM (Stanford)](https://crfm.stanford.edu/helm/) | 斯坦福的全面语言模型评测框架 | 按需 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |

### 4.3 GPU 与集群基准

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [MLPerf Inference](https://mlcommons.org/benchmarks/inference/) | MLCommons 的标准推理性能基准，涵盖多种硬件和模型 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [MLPerf Training](https://mlcommons.org/benchmarks/training/) | MLCommons 的标准训练性能基准 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [NVIDIA Deep Learning Performance Guide](https://docs.nvidia.com/deeplearning/performance/dl-performance-matrix/) | NVIDIA 官方的深度学习性能优化指南和基准数据 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [LLMPerf Leaderboard](https://github.com/ray-project/llmperf-leaderboard) | 开源 LLM 推理性能评测排行榜，覆盖多个框架和硬件配置 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Hugging Face Optimum Benchmark](https://github.com/huggingface/optimum-benchmark) | HF 官方的模型推理性能基准测试工具 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

---

## 五、社区与会议

### 5.1 推荐会议

| 会议 | 一句话定位 | 推荐关注优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [MLSys](https://mlsys.org/) | 聚焦机器学习系统工程的学术会议，涵盖推理优化、分布式训练、集群管理 | 必读 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [NeurIPS](https://neurips.cc/) | 机器学习顶级会议，模型架构和训练方法的前沿研究 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [ICML](https://icml.cc/) | 机器学习顶级会议，与 NeurIPS 互补 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [ICLR](https://iclr.cc/) | 表示学习会议，Transformer 架构改进的常见发表地 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [KubeCon + CloudNativeCon](https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/) | Kubernetes 和云原生生态会议，GPU 调度和 AI 工作负载相关议题 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [GTC (GPU Technology Conference)](https://www.nvidia.com/gtc/) | NVIDIA 技术大会，GPU 技术和 AI 基础设施的最新动态 | 推荐 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |
| [QCon / ArchSummit](https://qcon.net/) | 软件架构和工程实践会议，LLM 工程化议题 | 按需 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |

### 5.2 推荐 Newsletter 和信息源

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [The Batch](https://www.deeplearning.ai/the-batch/) | Andrew Ng 主编的 AI 周报，覆盖行业动态和工程实践 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [TLDR AI](https://tldr.tech/ai) | AI 领域的每日新闻摘要 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |
| [Interconnects (Nathan Lambert)](https://www.interconnects.ai/) | AI 对齐和 RLHF 方向的深度分析 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [Latent Space](https://www.latent.space/) | AI 工程和 LLMOps 的播客和 Newsletter | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [Hugging Face Daily Papers](https://huggingface.co/papers) | 每日精选 AI 论文，适合跟踪研究前沿 | 推荐 | [22-frontier-topics.md](./22-frontier-topics.md) |

### 5.3 社区论坛

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [vLLM GitHub Discussions](https://github.com/vllm-project/vllm/discussions) | vLLM 社区讨论，部署问题和最佳实践 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Hugging Face 论坛](https://discuss.huggingface.co/) | HF 生态的社区支持，模型部署和微调问题 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/) | 本地 LLM 部署和量化技术的 Reddit 社区 | 推荐 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| [Kubernetes Slack (#sig-scheduling)](https://kubernetes.slack.com/) | Kubernetes 调度相关讨论，GPU 调度问题可在此寻求帮助 | 按需 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) |

---

## 六、AI 网关与 LLMOps 平台

### 6.1 AI 网关

AI 网关是 LLM 推理服务与上游客户端之间的中间层，提供统一的 API 入口、负载均衡、限流、鉴权和可观测性能力。

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [LiteLLM 文档](https://docs.litellm.ai/) | 统一的 LLM API 代理，将 100+ 模型提供商的 API 统一为 OpenAI 兼容格式 | 必读 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [LiteLLM GitHub](https://github.com/BerriAI/litellm) | 源码和部署示例，适合理解多模型路由和限流实现 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Portkey AI Gateway](https://portkey.ai/docs) | AI 网关，提供路由、缓存、降级和可观测性 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Portkey GitHub](https://github.com/Portkey-AI/gateway) | 开源 AI 网关实现 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Kong AI Gateway](https://docs.konghq.com/gateway/latest/ai/) | Kong 的 AI 网关插件，适合已有 Kong 基础设施的团队 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/) | Cloudflare 的 AI 网关服务，边缘节点加速和缓存 | 按需 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |

### 6.2 LLMOps 平台

LLMOps 平台提供模型从训练到部署到监控的端到端管理能力。

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Langfuse 文档](https://langfuse.com/docs) | 开源 LLM 可观测性和评估平台，支持追踪、评分和 Prompt 管理 | 推荐 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Langfuse GitHub](https://github.com/langfuse/langfuse) | 源码和自托管部署方案 | 推荐 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Hugging Face TGI + Inference Endpoints](https://huggingface.co/docs/inference-endpoints/) | HF 的托管推理服务，从自托管 TGI 到全托管端点的完整方案 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [BentoCloud 文档](https://www.bentoml.com/cloud) | BentoML 的云平台，模型部署和自动扩缩容 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Lepton AI](https://www.lepton.ai/) | 轻量级 LLM 部署平台，快速上线推理服务 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Fireworks AI](https://fireworks.ai/) | 高性能推理服务提供商，开源模型的快速推理 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Together AI](https://www.together.ai/) | 开源模型推理平台，提供 API 和微调服务 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |

### 6.3 Prompt 管理与评估

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Promptfoo](https://promptfoo.dev/) | LLM 评估和红队测试框架，适合持续集成中的 Prompt 质量检查 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [Promptfoo GitHub](https://github.com/promptfoo/promptfoo) | 源码和评估用例模板 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [Hugging Face Evaluate](https://huggingface.co/docs/evaluate/) | 模型评估工具库，标准化的评估指标实现 | 推荐 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) |
| [DeepEval](https://docs.confident-ai.com/) | LLM 评估框架，支持多种评估维度和 CI 集成 | 按需 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| [Guardrails AI](https://www.guardrailsai.com/) | LLM 输出验证和防护框架，结构化输出保障 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | NVIDIA 的 LLM 安全防护框架，对话流控制和内容过滤 | 推荐 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |

---

## 七、云平台 LLM 服务文档

| 资源 | 一句话定位 | 推荐阅读优先级 | 关联文档 |
|------|-----------|---------------|----------|
| [Amazon SageMaker 推理文档](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html) | AWS 上的模型部署和推理服务文档 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Google Vertex AI 文档](https://cloud.google.com/vertex-ai/docs) | GCP 上的模型训练和部署平台文档 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Azure AI Studio 文档](https://learn.microsoft.com/en-us/azure/ai-studio/) | Azure 上的 AI 应用开发和模型部署文档 | 推荐 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| [Anyscale 文档](https://docs.anyscale.com/) | 基于 Ray 的托管推理和训练平台文档 | 推荐 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Modal 文档](https://modal.com/docs) | 无服务器 GPU 推理和训练平台，适合快速原型验证 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| [Replicate 文档](https://replicate.com/docs) | 托管模型推理平台，API 驱动 | 按需 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |

---

## 八、学习路径参考资源映射

以下将本专题的学习路径与参考资料做映射，方便按学习阶段查阅资料。

### 8.1 路径一：快速入门阶段

| 学习阶段 | 核心文档 | 必读参考资料 | 推荐参考资料 |
|----------|----------|-------------|-------------|
| 全局认知 | [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) | HF Transformers 文档、Attention Is All You Need | Chip Huyen 博客、Lilian Weng 博客 |
| 推理架构 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) | vLLM 文档、SGLang 文档、TGI 文档 | KServe 文档、Triton 文档 |
| 性能调优 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) | PagedAttention 论文、FlashAttention 论文 | vLLM 性能基准、SGLang 性能基准 |
| 可观测性 | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) | OpenTelemetry 文档、Prometheus 文档、DCGM Exporter | OpenLLMetry、Grafana 文档 |
| 上线检查 | [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) | OWASP Top 10 for LLM | NIST AI RMF |

### 8.2 路径二：系统学习阶段

| 学习阶段 | 核心文档 | 必读参考资料 | 推荐参考资料 |
|----------|----------|-------------|-------------|
| 训练基础设施 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) | NVIDIA DCGM 文档、K8s Device Plugin | GPU 架构白皮书、Slurm 文档、NVIDIA GPU Operator |
| 分布式训练 | [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) | NCCL 文档、PyTorch 文档 | DeepSpeed 文档、Megatron-LM、ZeRO 论文 |
| 可靠性与扩展 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) | Kubernetes 文档 | AWS/GCP/Azure AI 博客、KServe 文档 |
| RAG/Agent | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) | RAG 论文 | LangChain、LlamaIndex、Milvus 文档 |
| 安全合规 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) | OWASP Top 10 for LLM | EU AI Act、NIST AI RMF、Anthropic 博客 |
| 前沿主题 | [22-frontier-topics.md](./22-frontier-topics.md) | Mixtral 论文、DeepSeek-V3 报告 | DistServe 论文、SpecInfer 论文、Mooncake 论文 |
| 容量规划 | [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) | Chinchilla 论文 | Artificial Analysis、MLPerf 基准 |

---

## 九、场景化速查索引

以下按生产常见场景组织参考资料，方便遇到具体问题时快速定位。

### 9.1 推理延迟变高

| 排查步骤 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 确认延迟类型（TTFT/TPOT/E2E） | [02-glossary.md](./02-glossary.md) 推理指标类术语 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| 检查批处理和队列状态 | vLLM 连续批处理文档 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| 分析 GPU 计算瓶颈 | PyTorch Profiler 文档、NVIDIA Nsight | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| 检查 KV Cache 命中率 | vLLM Prefix Cache 文档 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| 评估量化方案 | bitsandbytes、GPTQ、AWQ 文档 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 9.2 GPU OOM 事故

| 排查步骤 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 确认 OOM 来源（模型加载/KV Cache/显存碎片） | [31-incident-runbook.md](./31-incident-runbook.md) | [31-incident-runbook.md](./31-incident-runbook.md) |
| 检查 GPU 显存使用 | DCGM 文档、nvidia-smi | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| 评估 KV Cache 策略 | PagedAttention 论文、vLLM 文档 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |
| 考虑模型量化或并行策略调整 | TensorRT-LLM 量化文档 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 9.3 模型上线前评估

| 检查维度 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 性能基准测试 | vLLM/SGLang 性能基准、MLPerf | [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) |
| 容量评估 | Chinchilla 论文、Artificial Analysis | [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) |
| 安全检查 | OWASP Top 10 for LLM、Promptfoo | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| 可观测性就绪 | OpenTelemetry 文档、DCGM Exporter | [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |

### 9.4 推理引擎选型

| 决策维度 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 吞吐优先 | vLLM 性能基准、SGLang 性能基准 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| 生态兼容性 | TGI 文档（HF 生态）、Triton 文档（NVIDIA 生态） | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| Agent/编排场景 | SGLang 文档、Ray Serve 文档 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| 边缘/轻量部署 | llama.cpp、Ollama 文档 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) |

### 9.5 RAG 系统搭建

| 组件选择 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 向量数据库选型 | Milvus/Qdrant/pgvector 文档 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| 嵌入模型服务 | TEI 文档、Jina AI 文档 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| RAG 框架集成 | LangChain/LlamaIndex 文档 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| 检索质量评估 | RAG 论文、Hugging Face Evaluate | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |

### 9.6 多地域部署

| 关注维度 | 参考资料 | 关联文档 |
|----------|---------|----------|
| 跨区域模型同步 | Hugging Face Hub 文档 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| 流量切分 | Istio 文档、Gateway API 文档 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| 云厂商多区域方案 | AWS/GCP/Azure AI 文档 | [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |

---

## 十、资料维护建议

### 10.1 版本跟踪

以下关键组件建议跟踪其版本更新：

| 组件 | 当前参考版本 | 更新频率 | 变更影响范围 |
|------|-------------|---------|-------------|
| vLLM | v0.8.x | 每周 | 推理参数、性能特征、API 兼容性 |
| SGLang | v0.4.x | 每两周 | 推理编排、RadixAttention 行为 |
| TGI | v3.x | 每月 | 部署配置、指标暴露方式 |
| NVIDIA GPU 驱动 | 550.x+ | 每季度 | CUDA 兼容性、MIG 行为 |
| Kubernetes | 1.30+ | 每季度 | 调度策略、设备插件 API |
| Prometheus | 2.53+ | 每季度 | 查询语法、存储行为 |

### 10.2 资料筛选原则

- **宁少勿多**：每类资源最多保留 3-5 个核心入口，避免信息过载
- **一手优先**：官方文档和论文始终优先于二手博客和教程
- **活跃优先**：优先跟踪活跃维护的项目，停止更新超过 6 个月的资源降低优先级
- **生产验证优先**：优先参考有大规模生产验证的方案，而非仅在论文中出现的方案

### 10.3 与专题文档的交叉引用

本参考地图与专题内其他文档的关系：

| 文档 | 与本地图的关系 |
|------|--------------|
| [01-roadmap.md](./01-roadmap.md) | 路线图定义"学什么"，本地图定义"去哪找" |
| [02-glossary.md](./02-glossary.md) | 术语表定义"是什么"，本地图提供"官方定义在哪" |
| [10-22 系列教程](./README.md) | 教程是知识载体，本地图是教程引用的外部资料索引 |
| [30-32 系列手册](./README.md) | 手册是操作指南，本地图是手册中工具和组件的官方入口 |
