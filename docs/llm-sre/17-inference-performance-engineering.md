# LLM SRE 17：推理性能工程

## 这篇文档解决什么问题

这篇文档聚焦推理性能工程的核心问题：TTFT 为什么变慢，TPOT 为什么抖动，TPS（tokens/s）为什么提不上去，以及哪些优化手段值得用、哪些只是把复杂度提前透支。很多团队在性能调优时只盯单次 benchmark，却忽略了真实线上流量的长度分布、并发结构和多租户噪声。

本文的重点不是“某个参数怎么配”，而是建立一条从请求结构到 GPU 资源，再到平台容量与告警的分析路径。

## 系统全景

推理性能问题通常沿着三段传播：请求进入系统后先排队，再经历 Prefill，最后进入 Decode。任何一段失衡，都会在用户侧表现为 TTFT、TPOT、TPS（tokens/s）或 queue time 异常。

```text
请求到达
   |
   v
排队 / 限流 / 调度
   |
   v
Prefill（处理输入上下文，建立 KV Cache）
   |
   v
Decode（逐 token 生成）
   |
   v
流式输出 / 完成请求
```

性能工程的本质是把这三段拆开看，再决定该优化算力、显存、批处理、缓存命中还是路由策略。直接追一个“总体延迟”指标，通常无法指导动作。

## Prefill 与 Decode 的资源特征

Prefill 更像大批量矩阵计算，计算密度高，对输入长度极其敏感，通常决定 TTFT 的大头。长 prompt、RAG 拼接、工具调用上下文膨胀，都会先打在 Prefill 上。Decode 则是逐 token 自回归生成，更受显存带宽、KV Cache 访问和调度效率影响，通常决定 TPOT 和持续输出流畅度。

这意味着同一个系统可能同时存在两类瓶颈：一类是长上下文让 Prefill 爆炸，另一类是高并发生成把 Decode 拖慢。把它们混在一起看，会导致错误调优，例如用更激进的 batching 去解决本质上的长上下文问题，结果 TTFT 更差。

## KV Cache、paged attention、continuous batching

KV Cache 是性能工程的中心对象之一。它决定显存占用、长上下文承载能力和请求复用效率。上下文越长、并发会话越多、输出越慢，KV Cache 压力越大。显存不够时，请求会被拒绝、换出，或者迫使 batch 缩小。

Paged attention 的价值在于把 KV Cache 管理从“大块连续内存”改成“分页管理”，降低碎片和扩容成本。continuous batching 的价值在于让短请求完成后新请求可以尽快补进 batch，提高 GPU 忙碌度，减少静态批处理的空转时间。

这两类技术的工程意义不是“平均吞吐更漂亮”，而是能否在真实混合流量下稳定控制 tail latency。SRE 需要看的是显存利用率、KV Cache 占用、batch 波动、排队长度和超时率是否一起改善。

## 量化、显存与吞吐

量化最直接的收益通常不是“绝对更快”，而是“同样显存能装下更大的模型，或在同一模型下容纳更高并发和更长上下文”。当系统瓶颈是显存时，量化往往能显著改善 TTFT 和吞吐；当瓶颈已经落到带宽、调度或路由层，量化未必带来线性收益。

不同量化方案的工程代价主要在三点：精度风险、构建与兼容性复杂度、问题排查门槛。平台团队要特别警惕“为了追求更小显存占用而引入多个量化分支”，因为这会直接增加制品管理、回滚和灰度验证成本。

## speculative decoding、PD 分离、prefix cache

speculative decoding 通过小模型先猜测若干 token，再由大模型验证，以降低 Decode 延迟。它适合输出较长、验证接受率较高的场景；如果接受率低，额外协调成本会抵消收益。PD 分离通常指把 Prefill 与 Decode 拆到不同资源池，分别优化计算密集和带宽敏感阶段，适合请求长度差异大、集群规模较大的平台。

prefix cache 则更适合高重复前缀场景，例如固定 system prompt、模板化检索上下文、热点工作流。它能降低 Prefill 开销，但前提是前缀稳定、命中率可观，而且缓存失效和版本切换语义足够清楚。

这三种优化都不是默认项。它们引入了更多状态、更多命中假设和更多回退逻辑，值班团队必须能看见收益，也能在异常时快速关闭。

## 多 LoRA 与多模型复用

多 LoRA 和多模型复用的核心收益是提升资源利用率，减少“每个变体一整套服务”的浪费。但它的性能挑战也最明显：适配器切换会拉高 TTFT，热点 LoRA 会争抢缓存，长尾模型会稀释 batch 质量，多模型混跑会让容量模型失真。

如果平台已经在多租户环境下承受高峰流量，复用策略必须和优先级、配额、预热一起设计。否则表面上 GPU 利用率更高，实际上 TPOT 和 queue time 会变得更不稳定。

## 关键指标与告警

性能工程需要把优化动作和指标绑定起来。建议至少持续观察：

- TTFT、TPOT、TPS（tokens/s）、queue time 的 p50/p95/p99。
- Prefill token 吞吐与 Decode token 吞吐，避免只看总体吞吐。
- running requests、waiting requests、batch size、max batched tokens。
- KV Cache 占用率、碎片趋势、Prefix Cache 命中率、换出次数。
- 每模型、每租户的输入长度、输出长度与超时率。

告警设计应服务于性能退化定位，例如“TTFT p95 上升且 waiting requests 增加”“TPOT p95 上升但 queue time 正常”“KV Cache 占用长期接近上限并伴随请求拒绝”。这样才能区分是排队问题、Prefill 问题还是 Decode 问题。

## 典型故障与排查路径

| 故障现象 | 优先检查项 | 常见根因 |
| --- | --- | --- |
| TTFT 突然升高 | queue time、输入长度分布、Prefill 吞吐、冷启动记录 | 流量突发、长 prompt 激增、实例扩容未热身、Prefix Cache 失效 |
| TPOT 变差且流式输出发抖 | Decode token 吞吐、KV Cache 占用、batch 波动 | 显存带宽吃紧、连续批处理效率下降、长会话挤占共享资源 |
| TPS（tokens/s）上不去 | GPU 利用率、batch size、请求长度分布 | batch 太小、调度保守、流量过碎、实例池切分过细 |
| 频繁 OOM 或拒绝请求 | 显存水位、KV Cache 增长、上下文长度配置 | max context 过大、并发过高、量化/分页策略不合理 |
| 某些优化上线后收益反而变差 | 命中率、接受率、回退率、实例日志 | speculative decoding 接受率低、prefix cache 命中不足、PD 分离带来额外网络与调度开销 |

排查顺序建议固定化：先判断慢在排队、Prefill 还是 Decode；再看是全局现象、单模型现象还是单租户现象；最后再落到具体优化开关和实例日志。

## 设计权衡

| 优化手段 | 收益 | 代价 | 何时不该用 |
| --- | --- | --- | --- |
| continuous batching | 提升 GPU 忙碌度和总体吞吐，改善混合请求利用率 | 调度更复杂，尾延迟分析更难 | 低并发、强隔离、请求长度高度一致时 |
| paged attention | 降低 KV Cache 碎片，提高显存利用率和长上下文稳定性 | 引擎实现更复杂，排障要理解页级行为 | 负载简单、上下文短、显存并不紧张时 |
| 量化 | 降低显存占用，提升可承载模型规模或并发 | 精度回归验证、构建链路和兼容性复杂 | 质量风险不可接受、版本切换频繁时 |
| speculative decoding | 降低 Decode 延迟，改善长输出场景 TPOT | 需要辅助模型与接受率监控，回退逻辑复杂 | 输出很短、接受率低、平台缺乏观测能力时 |
| PD 分离 | 分别优化 Prefill 与 Decode 资源池，提高大规模平台弹性 | 网络与控制面复杂度上升，请求编排更难 | 集群很小、请求结构单一、团队值班经验不足时 |
| prefix cache | 降低重复前缀的 Prefill 成本，改善 TTFT | 缓存失效、版本一致性和命中管理复杂 | prompt 高度离散、前缀变化快时 |

性能工程没有免费的优化。所有优化都在用复杂度换收益，关键是确认收益是否稳定、可观测、可回退。

## 实践建议

- 先建立分段指标：TTFT、TPOT、queue time、Prefill/Decode token 吞吐必须拆开看。
- 先优化请求结构，再优化内核参数。无约束的上下文膨胀会吞掉大多数引擎优化收益。
- 只有在命中率、接受率可测的前提下，才上线 prefix cache 或 speculative decoding。
- 多模型、多 LoRA 平台优先做容量分层和热点预热，再追求极限共享。
- 把“关闭优化开关后的退路”预先写进运行手册，否则性能优化会变成值班风险。

## 扩展阅读

- [02-glossary.md](./02-glossary.md)
- [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)
- [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)
- [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md)
