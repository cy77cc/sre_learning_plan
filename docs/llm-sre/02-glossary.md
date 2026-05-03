# LLM SRE 术语表

| 术语 | 中文/全称 | 一句话解释 | 运维关注点 |
|---|---|---|---|
| TTFT | Time To First Token | 从请求进入到首个 token 返回的时间 | 看首包慢在排队、Prefill 还是模型冷启动 |
| TPOT | Time Per Output Token | 平均每个输出 token 的生成时间 | 看 Decode 效率、带宽瓶颈与吞吐稳定性 |
| QPS | Queries Per Second | 每秒请求数 | 结合并发、排队和限流判断入口压力 |
| TPS | Tokens Per Second | 每秒处理或生成的 token 数 | 比单纯 QPS 更能反映推理负载强度 |
| P50/P95/P99 | 延迟分位数 | 延迟分布的统计切面 | P99 常用于发现尾延迟和抖动问题 |
| KV Cache | Key/Value Cache | 保存历史 token 的注意力缓存 | 直接影响显存占用、长上下文能力和复用效率 |
| Prefix Cache | 前缀缓存 | 复用相同提示前缀的计算结果 | 看命中率、失效率和跨请求复用收益 |
| Prefill | 预填充阶段 | 处理输入上下文并建立初始状态 | 计算重、对 TTFT 和批处理策略影响大 |
| Decode | 解码阶段 | 逐 token 自回归生成输出 | 带宽敏感，决定 TPOT 与持续吞吐 |
| Context Window | 上下文窗口 | 单次可处理的最大 token 数 | 影响显存、KV Cache 规模和请求准入策略 |
| Batch Size | 批大小 | 同时合批处理的请求数 | 提高吞吐但可能放大尾延迟 |
| Continuous Batching | 连续批处理 | 动态把新请求并入现有批次 | 看调度效率、排队长度与公平性 |
| Paged Attention | 分页注意力 | 以分页方式管理 KV Cache 的技术 | 重点看碎片率、显存利用率和长会话稳定性 |
| TP | Tensor Parallelism | 张量并行 | 跨卡通信与 NVLink/PCIe 拓扑常是瓶颈 |
| PP | Pipeline Parallelism | 流水线并行 | 看分段均衡、气泡开销和阶段间等待 |
| EP | Expert Parallelism | 专家并行 | 关注路由倾斜、跨节点流量和 MoE 热点 |
| DP | Data Parallelism | 数据并行 | 多副本扩展简单，但显存成本高 |
| FSDP | Fully Sharded Data Parallel | 全分片数据并行 | 训练/微调时看显存节省、重组通信与恢复复杂度 |
| LoRA | Low-Rank Adaptation | 低秩适配微调方法 | 关注 Adapter 制品管理、加载延迟与回滚 |
| QLoRA | Quantized LoRA | 量化基础上的 LoRA 微调 | 看显存占用下降与精度回归风险 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 | 运维上要盯检索延迟、召回质量和上下文膨胀 |
| Embedding | 向量化表示 | 把文本映射为向量以便检索 | 关注模型版本一致性和向量重建成本 |
| Re-ranker | 重排模型 | 对召回结果再次排序 | 常是额外延迟来源，要评估收益是否值得 |
| MIG | Multi-Instance GPU | 将单卡切成多个隔离实例 | 关注资源切分粒度、隔离性与利用率损失 |
| MPS | Multi-Process Service | GPU 多进程共享机制 | 适合轻量共享，但要防止相互干扰 |
| HPA | Horizontal Pod Autoscaler | 横向扩缩容 | 指标选错会导致扩容滞后或抖动放大 |
| Warmup | 预热 | 提前加载模型和运行关键路径 | 直接影响冷启动、首包延迟和发布稳定性 |
| Quantization | 量化 | 用更低精度表示权重或激活 | 降低显存和成本，但要验证质量损失 |
| Speculative Decoding | 投机解码 | 用小模型辅助加速生成 | 关注接受率、额外开销与收益边界 |
| SLO | Service Level Objective | 服务目标阈值 | 需要用延迟、错误率、可用性和成本共同定义 |
| Error Budget | 错误预算 | 在 SLO 下允许消耗的失败空间 | 用于约束上线节奏、实验强度与稳定性风险 |
