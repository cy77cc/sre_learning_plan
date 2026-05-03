# LLM SRE 参考地图

这份参考地图只列值得长期跟踪的一手或高信号资料，不追求“全”，重点是帮助你快速找到权威定义、主流实现和工程经验。

## 官方文档

- NVIDIA 文档：GPU、CUDA、驱动、DCGM、MIG/MPS 相关能力的第一手入口，适合查硬件能力、监控指标和兼容性矩阵。
- Kubernetes 文档：调度、资源管理、设备插件、HPA、探针、滚动升级等基础机制的权威来源。
- PyTorch 文档：训练、分布式、FSDP、Profiler 与 CUDA 交互行为的参考标准。
- Hugging Face 文档：模型制品、Tokenizer、Transformers、PEFT、Text Generation Inference 等生态入口。
- vLLM 官方文档：推理服务参数、Paged Attention、连续批处理、Prefix Cache 等机制说明。
- OpenTelemetry 文档：把 LLM 请求接入 tracing、metrics、logs 的通用规范来源。

## 开源项目

- vLLM：当前最常见的高吞吐 LLM 推理框架之一，适合研究批处理、KV Cache 管理和 OpenAI 兼容服务。
- Hugging Face TGI：部署形态清晰，适合对照理解推理服务网关、模型加载与指标暴露方式。
- SGLang：更强调推理编排与复杂请求流，适合关注 Agent/长流程场景。
- Triton Inference Server：适合理解多模型服务、后端抽象与企业级部署方式。
- Ray Serve：适合研究模型服务编排、弹性扩展与多组件推理工作流。
- KServe：适合把模型服务纳入 Kubernetes 原生平台治理体系。
- NVIDIA DCGM Exporter：GPU 指标采集标准组件，适合作为 Prometheus 集成入口。
- llama.cpp：适合理解量化、本地推理与非 GPU 重型环境下的部署权衡。

## 论文与技术博客

- Attention Is All You Need：理解 Transformer 起点即可，不需要把精力放在公式推导细节上。
- LoRA / QLoRA 论文：重点看为什么能省显存，以及它对训练与上线流程带来的制品变化。
- PagedAttention / vLLM 相关论文与博客：重点看它如何提升吞吐、减少显存碎片。
- Google、Meta、NVIDIA、Anthropic、OpenAI、Hugging Face 工程博客：优先看发布后总结的性能、可靠性、容量和安全经验。
- 云厂商技术博客：适合看 GPU 集群、弹性调度、成本优化和大规模实战案例，但要注意厂商方案会带有平台前提。

## 建议使用方式

- 查概念定义时，优先官方文档，不先看二手总结。
- 查工程实现时，先看活跃开源项目的 README、参数说明、FAQ，再回到源码和 issue。
- 查性能优化时，先建立自己的指标基线，再看论文或博客中的收益数字，避免直接照搬。
- 查架构方案时，把资料按“单机推理、单集群、多租户平台、跨区域服务”四类分开看，减少误用。
- 长期维护一个自己的资料索引：每种框架最多保留 1 份官方入口、1 个基准实现、1 篇高质量经验文，避免收藏很多但从不复用。
