# LLM SRE 17：推理性能工程

> 📅 日期：2026-05-03
> 📖 学习主题：TTFT/TPOT/TPS 性能分析与优化策略
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：16-inference-engines-and-serving-architecture.md

## 🎯 学习目标

完成本章学习后，你应该能够：

1. **分析 Prefill 和 Decode 阶段的资源特征差异**——理解为什么同一个请求的不同阶段对算力和带宽的需求截然不同，以及这种差异如何影响系统设计。
2. **解释 KV Cache、Paged Attention、Continuous Batching 的工作原理**——不仅知道它们是什么，还能推导显存占用、碎片率和调度效率的数学关系。
3. **评估量化、Speculative Decoding、PD 分离的收益与代价**——在给定场景下选择合适的优化组合，并预判引入的复杂度。
4. **诊断 TTFT 飙升、TPOT 退化、TPS 瓶颈等性能问题**——建立从指标到根因的排查路径，避免"看到慢就加机器"的粗暴思路。

---

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 推理请求的生命周期

一条推理请求从进入系统到返回结果，通常经历三个阶段。理解这三个阶段是所有性能分析的起点：

```text
请求到达
   |
   v
┌──────────────────────────────────────────────────────┐
│  阶段 0：排队 / 限流 / 调度                            │
│  - 等待 GPU 资源释放                                   │
│  - 等待 batch 凑满或调度器分配                          │
│  - 指标：queue time                                   │
└──────────────────────┬───────────────────────────────┘
                       |
                       v
┌──────────────────────────────────────────────────────┐
│  阶段 1：Prefill（预填充）                              │
│  - 一次性处理整个输入序列                               │
│  - 计算所有 token 的 Key/Value，写入 KV Cache          │
│  - 并行计算，计算密集型                                │
│  - 指标：TTFT（Time To First Token）                  │
└──────────────────────┬───────────────────────────────┘
                       |
                       v
┌──────────────────────────────────────────────────────┐
│  阶段 2：Decode（解码生成）                             │
│  - 逐 token 自回归生成                                │
│  - 每步读取 KV Cache，生成一个 token                   │
│  - 串行迭代，带宽密集型                                │
│  - 指标：TPOT（Time Per Output Token）, TPS           │
└──────────────────────┬───────────────────────────────┘
                       |
                       v
              流式输出 / 返回结果
```

用户感知到的延迟是这三个阶段的总和。SRE 的第一步工作就是把这个总延迟拆开，确定瓶颈落在哪一段。

---

#### 1.2 Prefill 与 Decode 的资源特征对比

这是推理性能工程中最基本也最容易被忽略的区分：

```text
┌─────────────────────────────────────────────────────────────────┐
│              Prefill vs Decode 资源消耗对比                      │
├──────────────┬──────────────────────┬───────────────────────────┤
│   维度        │      Prefill        │        Decode             │
├──────────────┼──────────────────────┼───────────────────────────┤
│ 计算模式      │ 大矩阵乘法，高度并行  │ 小矩阵乘法，逐 token 串行  │
│ 瓶颈类型      │ 计算密集 (compute)    │ 带宽密集 (memory BW)      │
│ GPU 利用率    │ 高（大 kernel）       │ 低（小 kernel，频繁调度）  │
│ 输入敏感度    │ 与输入长度线性相关     │ 与输出长度线性相关         │
│ 并发特征      │ 单请求即可打满 GPU    │ 需要高并发才能提高利用率    │
│ 对应指标      │ TTFT                 │ TPOT, TPS                │
│ batch 效益    │ batch 增大收益递减    │ batch 增大收益显著         │
│ 显存压力      │ 激活值 + KV Cache 写入│ KV Cache 持续增长          │
└──────────────┴──────────────────────┴───────────────────────────┘
```

**为什么这个区分如此重要？**

因为优化方向完全不同：

- Prefill 慢 → 优化计算：减少输入长度、用更强的 GPU、Prefix Cache 复用、PD 分离把 Prefill 分配到计算资源池。
- Decode 慢 → 优化带宽和并发：增大批大小、量化减少 KV Cache 大小、Paged Attention 减少碎片、Continuous Batching 保持 GPU 忙碌。

如果把两者混在一起看，就会出现错误决策：比如用更激进的 Continuous Batching 去解决长上下文导致的 Prefill 超时，结果 batch 增大后 Prefill 更慢，TTFT 进一步恶化。

---

#### 1.3 KV Cache 深入

KV Cache 是推理性能工程的中心对象。它的存在源于 Transformer 自回归生成的数学结构。

**为什么需要 KV Cache？**

在 Transformer 的 Attention 机制中，第 `n` 个 token 生成时需要计算：

```
Attention(Q_n, K_1..n, V_1..n) = softmax(Q_n * K_1..n^T / sqrt(d)) * V_1..n
```

如果不缓存，每生成一个新 token，都要重新计算所有历史 token 的 Key 和 Value，时间复杂度为 O(n^2)。KV Cache 将已计算的 Key/Value 存在显存中，每步只需计算当前 token 的 Q/K/V 并追加，时间复杂度降为 O(n)。

**显存占用计算公式：**

```
KV Cache 显存 = 2 * num_layers * num_kv_heads * head_dim * seq_len * dtype_bytes * batch_size
```

其中：
- `2` 代表 Key 和 Value 两份
- `num_layers` 是 Transformer 层数
- `num_kv_heads` 是 KV Head 数量（GQA 架构下小于 Q Head 数）
- `head_dim` 是每个 head 的维度
- `seq_len` 是序列长度（输入 + 已生成输出）
- `dtype_bytes` 是数据类型字节数（FP16=2, FP8=1, INT8=1）
- `batch_size` 是并发请求数

**具体示例——Llama-3-70B 的 KV Cache 占用：**

```
参数：80 layers, 8 KV heads (GQA), head_dim=128, FP16 (2 bytes)

单请求、序列长度 4096：
  KV Cache = 2 * 80 * 8 * 128 * 4096 * 2
           = 2 * 80 * 8 * 128 * 4096 * 2
           = 1,342,177,280 bytes
           ≈ 1.25 GB

单请求、序列长度 32768（长上下文）：
  KV Cache = 2 * 80 * 8 * 128 * 32768 * 2
           ≈ 10.0 GB

并发 50 请求、平均序列长度 4096：
  KV Cache = 1.25 GB * 50 = 62.5 GB
```

对于 70B 模型在 80GB 显存的 A100/H100 上，KV Cache 很快就会成为显存的主要消费者，甚至超过模型权重本身。

```text
┌─────────────────────────────────────────────────────────────────┐
│                    GPU 显存布局（A100 80GB）                      │
│                                                                 │
│  ┌─────────────┐  模型权重 (FP16)           ~140 GB → 需量化    │
│  │             │  模型权重 (INT8)            ~70 GB              │
│  │             │  模型权重 (INT4)            ~35 GB              │
│  ├─────────────┤  框架开销 + 激活值          ~5-10 GB            │
│  ├─────────────┤  KV Cache（剩余空间）       可变                │
│  │             │                                                 │
│  │  并发请求数  │  = 可用 KV Cache 空间 / 单请求 KV Cache 大小   │
│  │  受限于此    │                                                 │
│  │             │                                                 │
│  └─────────────┘                                                 │
│                                                                 │
│  总显存 = 模型权重 + 框架开销 + KV Cache + 碎片预留              │
└─────────────────────────────────────────────────────────────────┘
```

**KV Cache 管理策略：**

| 策略 | 原理 | 适用场景 |
|------|------|----------|
| 全部驻留 | 所有活跃请求的 KV Cache 常驻显存 | 显存充足、并发可控 |
| LRU 换出 | 最久未访问的 KV Cache 换到 CPU 内存 | 长会话多、显存紧张 |
| KV Cache 压缩 | 对历史 KV 做量化或稀疏化 | 超长上下文、可容忍轻微精度损失 |
| 按需分配 | 只在需要时分配显存页 | 配合 Paged Attention 使用 |

---

#### 1.4 Paged Attention

Paged Attention 是 vLLM 引入的关键创新，解决了 KV Cache 的内存碎片问题。

**传统连续内存分配的问题：**

```text
传统方式：为每个请求预分配 max_seq_len 的连续内存

请求 A（实际用 200 tokens）：[████████░░░░░░░░░░░░]  预分配 2048，浪费 90%
请求 B（实际用 1500 tokens）：[██████████████████░░░░░] 预分配 2048，浪费 27%
请求 C（无法分配）：           [  碎片太多，连续空间不够  ]

问题：
1. 内部碎片：预分配过大，实际使用远小于分配
2. 外部碎片：释放后空间不连续，无法给新请求使用
3. 无法精确限制并发：只能按最坏情况估算
```

**Paged Attention 的分页管理：**

```text
Paged Attention：将 KV Cache 分成固定大小的页（block）

逻辑视图（请求 A 的 KV Cache）：
  [Block 0] [Block 1] [Block 2] [Block 3] ...

物理视图（GPU 显存中的 block pool）：
  ┌────────┬────────┬────────┬────────┬────────┬────────┐
  │ Block  │ Block  │ Block  │ Block  │ Block  │ Block  │
  │ A-0    │ B-0    │ A-1    │ C-0    │ B-1    │ A-2    │
  │ (used) │ (used) │ (used) │ (used) │ (used) │ (used) │
  ├────────┼────────┼────────┼────────┼────────┼────────┤
  │ Block  │ Block  │ Block  │ Block  │ ...    │ ...    │
  │ (free) │ (free) │ (free) │ (free) │        │        │
  └────────┴────────┴────────┴────────┴────────┴────────┘

页表（每个请求维护一个映射）：
  请求 A: [0→Block A-0, 1→Block A-1, 2→Block A-2]
  请求 B: [0→Block B-0, 1→Block B-1]
  请求 C: [0→Block C-0]

优势：
1. 按需分配：只分配实际需要的 block，无内部碎片
2. 无外部碎片：block 大小固定，任意位置可分配
3. 精确容量控制：block pool 用完即拒绝，不依赖估算
4. Copy-on-Write：共享前缀的请求可以共享 block
```

这个设计与操作系统的虚拟内存高度类似：逻辑地址连续但物理地址可以不连续，通过页表做映射。区别在于 Paged Attention 管理的是 GPU 显存中的 KV Cache block，而不是 CPU 内存中的页面。

**工程收益量化：**

| 指标 | 连续分配 | Paged Attention |
|------|---------|-----------------|
| 显存利用率 | 20%-60% | 90%-98% |
| 可支持并发数 | 受限于 max_seq_len 估算 | 受限于实际使用量 |
| 碎片导致的请求拒绝 | 常见 | 几乎不发生 |
| 前缀共享 | 不支持 | 支持 Copy-on-Write |

---

#### 1.5 Continuous Batching

Continuous Batching（也叫 Iteration-level Batching）是推理调度的核心优化。

**静态 Batching 的问题：**

```text
静态 Batching：等 batch 填满才开始推理，所有请求一起完成

时间 →
请求 A: [===Prefill===][=====Decode=====][完成]
请求 B: [===Prefill===][=====Decode============][完成]
请求 C: [===Prefill===][====Decode====][完成]
                                            ↑
                                     必须等最慢的完成
                                     才能开始下一批

问题：
1. 短请求等长请求：请求 A 完成后 GPU 空转
2. 新请求必须等整批完成：排队时间增加
3. GPU 利用率随请求长度差异增大而降低
```

**Continuous Batching 的调度流程：**

```text
Continuous Batching：每个 iteration 级别调度，完成的请求立即退出，新请求立即加入

时间 →
请求 A: [===Prefill===][=====Decode=====]→ 完成，立即退出
请求 B: [===Prefill===][=====Decode============]→ 完成
请求 C:              [===Prefill===][====Decode====]→ 完成
请求 D:                              [Prefill][==Decode==]→ 完成
请求 E:                                        [Prefill][Decode]→ 完成

调度器每步决策：
┌──────────────────────────────────────────────────────┐
│ iteration N 的调度决策：                               │
│ 1. 检查已完成的请求 → 释放其 KV Cache blocks          │
│ 2. 检查等待队列 → 新请求能否加入（显存/block 够不够）   │
│ 3. 对新加入的请求执行 Prefill                          │
│ 4. 对已有请求执行一步 Decode                           │
│ 5. 返回第 1 步                                        │
└──────────────────────────────────────────────────────┘
```

**关键设计点：**

1. **Prefill 和 Decode 混合调度**：同一个 iteration 中，新请求做 Prefill，老请求做 Decode。这会导致 Decode 请求被 Prefill 请求"抢占"，引起 TPOT 的短暂抖动。vLLM 通过 `scheduler_delay_ms` 等参数来平衡这个冲突。
2. **抢占机制**：当显存不足时，调度器可以"换出"低优先级请求的 KV Cache，为高优先级请求腾出空间。
3. **chunked prefill**：超长输入的 Prefill 可以分块执行，避免单个 Prefill 占用太长时间导致其他请求的 Decode 被饿死。

---

#### 1.6 性能优化手段

##### 1.6.1 量化（Quantization）

量化通过降低数值精度来减少显存占用和提高计算速度。

```text
┌─────────────────────────────────────────────────────────────────┐
│                     量化方案对比                                  │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│ 方案      │ 权重位宽  │ 显存节省  │ 精度损失  │ 典型场景            │
├──────────┼──────────┼──────────┼──────────┼─────────────────────┤
│ FP16     │ 16 bit   │ 基准     │ 无       │ 精度优先            │
│ FP8      │ 8 bit    │ ~50%    │ 极小     │ H100/H200 原生支持  │
│ INT8     │ 8 bit    │ ~50%    │ 小       │ 通用量化，兼容性好   │
│ INT4     │ 4 bit    │ ~75%    │ 中等     │ 显存极度紧张        │
│ GPTQ     │ 4 bit    │ ~75%    │ 中等     │ 离线量化，部署简单   │
│ AWQ      │ 4 bit    │ ~75%    │ 较小     │ 权重感知量化        │
│ GGUF     │ 2-8 bit  │ 可变    │ 可变     │ CPU/混合推理        │
└──────────┴──────────┴──────────┴──────────┴─────────────────────┘
```

**量化的收益边界：**

量化最直接的收益不是"推理更快"，而是"同样显存能装下更大的模型或更高的并发"。当系统瓶颈在显存时，量化能显著改善吞吐和并发；当瓶颈在计算内核调度或网络带宽时，量化不一定带来线性收益。

##### 1.6.2 Speculative Decoding

```text
Speculative Decoding 工作流程：

小模型（Draft）快速猜测 K 个 token
   |
   v
[t_1, t_2, t_3, t_4, t_5]  ← 小模型输出（快，质量低）
   |
   v
大模型（Target）一次性验证这 K 个 token
   |
   v
[✓, ✓, ✗, -, -]  ← 验证结果：前 2 个接受，第 3 个拒绝
   |
   v
接受 t_1, t_2，从 t_3 开始由大模型重新生成

效果：
- 如果接受率高（如 80%+），相当于大模型每步生成多个 token
- 如果接受率低（如 30%），额外的验证成本反而拖慢速度
- 关键指标：接受率 (acceptance rate)
```

##### 1.6.3 PD 分离（Prefill-Decode Disaggregation）

```text
┌─────────────────────────────────────────────────────────────────┐
│                      PD 分离架构                                 │
│                                                                 │
│  ┌─────────────────────┐          ┌──────────────────────────┐ │
│  │   Prefill 资源池     │          │    Decode 资源池          │ │
│  │                     │          │                          │ │
│  │  ┌───────┐          │   KV     │  ┌───────┐              │ │
│  │  │GPU x N│ 计算优化  │  Cache   │  │GPU x M│ 带宽优化     │ │
│  │  │高算力  │──────────│─────────→│  │大显存  │              │ │
│  │  │A100   │  传输     │          │  │H100   │              │ │
│  │  └───────┘          │          │  └───────┘              │ │
│  │                     │          │                          │ │
│  │ 特点：              │          │ 特点：                   │ │
│  │ - 处理长上下文       │          │ - 维持高并发 Decode       │ │
│  │ - 可以用更强的 GPU   │          │ - Continuous Batching     │ │
│  │ - Prefill 完成后     │          │ - 追求低 TPOT             │ │
│  │   释放资源           │          │                          │ │
│  └─────────────────────┘          └──────────────────────────┘ │
│                                                                 │
│  调度器：根据请求特征分配到对应的资源池                            │
│  网络：KV Cache 在 Prefill 节点和 Decode 节点之间传输             │
└─────────────────────────────────────────────────────────────────┘
```

**PD 分离的适用条件：**

- 请求长度差异大（有的请求输入很长，有的输出很长）
- 集群规模较大（至少 10+ GPU），分资源池才有意义
- 网络延迟可控（RDMA 或高速互联），否则 KV Cache 传输成为瓶颈
- 团队有能力维护两套资源池的调度逻辑

##### 1.6.4 Prefix Cache

Prefix Cache 通过复用相同前缀的 KV Cache 来避免重复计算。

```text
场景：多个请求共享相同的 system prompt

请求 1: [system prompt 2000 tokens] + [用户问题 A 100 tokens]
请求 2: [system prompt 2000 tokens] + [用户问题 B 150 tokens]
请求 3: [system prompt 2000 tokens] + [用户问题 C 80 tokens]

无 Prefix Cache：
  每个请求都要 Prefill 2000+ tokens 的 system prompt
  Prefill 总计算量 = (2100 + 2150 + 2080) * cost_per_token

有 Prefix Cache：
  第一个请求正常 Prefill system prompt，结果缓存
  后续请求直接复用缓存，只需 Prefill 用户问题部分
  Prefill 总计算量 = 2100 + (150 + 80) * cost_per_token
  节省 ≈ 65% 的 Prefill 计算量
```

##### 1.6.5 性能优化决策树

```text
                    推理性能问题
                         │
            ┌────────────┼────────────┐
            v            v            v
       TTFT 高       TPOT 高       TPS 低
            │            │            │
     ┌──────┼──────┐     │      ┌─────┼─────┐
     v      v      v     v      v           v
  排队久  Prefill慢 冷启动  Decode慢    batch太小  GPU空闲
     │      │      │      │           │          │
     v      v      v      v           v          v
  扩容/   输入太长  预热   batch太小   调度策略   Continuous
  限流优化  │      策略    │         过于保守   Batching
     │      │             │                    未生效
     │  ┌───┼───┐    ┌────┼────┐
     │  v   v   v    v    v    v
     │ 前缀 缩短  PD  量化 增大 Paged
     │ 缓存 输入 分离     batch Attn
     │
     v
  请求结构优化（RAG top-k, 工具调用精简）
```

---

#### 1.7 多 LoRA 与多模型复用

多 LoRA 复用允许在同一套基础模型上加载多个 LoRA 适配器，避免为每个任务部署独立的服务实例。

**收益：**
- 显著减少 GPU 资源占用（N 个适配器只需 1 份基础模型权重）
- 适配器权重通常很小（几十 MB），可以在请求级别切换

**挑战：**
- LoRA 切换有开销：需要加载适配器权重，可能引起 TTFT 短暂升高
- 热点适配器争抢缓存：高频使用的 LoRA 会被频繁加载/卸载
- 容量模型失真：不同 LoRA 的请求特征差异大，统一的容量模型会失效

**SRE 关注点：**
- LoRA 缓存命中率：命中时 TTFT 接近基础模型，未命中时可能增加 10-50ms
- 适配器预热策略：高频 LoRA 应常驻缓存
- 与优先级配合：不同 LoRA 可能对应不同 SLA 等级

---

### 2. 命令/工具详解

#### 2.1 vLLM 性能调优参数

vLLM 提供了多个与性能直接相关的启动参数：

```bash
# 基础性能相关参数
vllm serve meta-llama/Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \              # 张量并行度
    --pipeline-parallel-size 1 \            # 流水线并行度
    --max-num-seqs 256 \                    # 最大并发请求数
    --max-num-batched-tokens 32768 \        # 最大 batch token 数
    --max-model-len 32768 \                 # 最大序列长度
    --gpu-memory-utilization 0.90 \         # GPU 显存利用率目标
    --enable-prefix-caching \               # 启用 Prefix Cache
    --enable-chunked-prefill \              # 启用分块 Prefill
    --quantization fp8 \                    # 量化方式
    --swap-space 4 \                        # CPU swap 空间 (GB)
    --scheduler-delay-ms 0                  # 调度延迟（控制 Prefill/Decode 混合程度）
```

**关键参数对性能的影响：**

| 参数 | 调大时的效果 | 调小时的效果 | SRE 建议 |
|------|------------|------------|----------|
| `max-num-seqs` | 更高并发，但可能增加排队和 TPOT | 更低延迟，但吞吐受限 | 根据 GPU 显存和 TPOT SLA 调整 |
| `max-num-batched-tokens` | Prefill 更快（更大 batch），但占用更多显存 | Prefill 更慢，但显存更安全 | 通常设为 max_model_len 或稍小 |
| `gpu-memory-utilization` | 更多显存给 KV Cache，并发更高 | 留更多缓冲，更安全 | 0.85-0.95，避免 OOM |
| `enable-prefix-caching` | 重复前缀场景 TTFT 大幅改善 | 无额外开销 | 只要有重复 system prompt 就开启 |
| `enable-chunked-prefill` | 长输入不会阻塞 Decode，TPOT 更稳定 | Prefill 更快完成 | 长短请求混合场景开启 |
| `swap-space` | 允许更多请求排队（换出到 CPU） | 更快拒绝超出容量的请求 | 4-8 GB，避免过多换入换出 |

#### 2.2 基准测试工具

##### vLLM Benchmark Suite

vLLM 自带基准测试工具，可以直接测量 TTFT、TPOT 和吞吐：

```bash
# 安装 vLLM（如果尚未安装）
pip install vllm

# 基础吞吐测试：测试在线服务的最大吞吐
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3-8B-Instruct \
    --enable-prefix-caching &
# 等待服务启动...

# 使用 vLLM benchmark_throughput.py 测试离线吞吐
python benchmarks/benchmark_throughput.py \
    --backend vllm \
    --model meta-llama/Llama-3-8B-Instruct \
    --dataset ShareGPT_V3_unfiltered_cleaned_split.json \
    --num-prompts 1000 \
    --request-rate inf \
    --result-dir ./benchmark_results
```

**benchmark_throughput.py 典型输出：**

```
Throughput: 12.34 requests/s, 5678.90 total tokens/s, 2345.67 generated tokens/s

Results saved to ./benchmark_results/vllm_throughput_20260503_143022.json
```

```bash
# 延迟测试：测量 TTFT 和 TPOT 分布
python benchmarks/benchmark_latency.py \
    --backend vllm \
    --model meta-llama/Llama-3-8B-Instruct \
    --input-len 1024 \
    --output-len 256 \
    --num-iters 100 \
    --batch-size 1
```

**benchmark_latency.py 典型输出：**
```
Avg latency: 3.456 seconds
Avg TTFT: 0.234 seconds
Avg TPOT: 0.0126 seconds (79.4 tokens/s)
P50 latency: 3.401 seconds
P90 latency: 3.789 seconds
P99 latency: 4.123 seconds
```

```bash
# 带负载的在线延迟测试（需要服务已在运行）
python benchmarks/benchmark_serving.py \
    --backend openai \
    --base-url http://localhost:8000/v1 \
    --model meta-llama/Llama-3-8B-Instruct \
    --dataset-name random \
    --random-input-len 1024 \
    --random-output-len 256 \
    --num-prompts 500 \
    --request-rate 10.0 \
    --percentile-metrics ttft,tpot,itl,e2el
```

**benchmark_serving.py 典型输出（关键部分）：**

```
============ Serving Benchmark Result ============
Successful requests:                     500
Benchmark duration (s):                  52.34
Total input tokens:                      512000
Total generated tokens:                  128000
Request throughput (req/s):              9.55
Output token throughput (tok/s):         2446.12
Total Token throughput (tok/s):          12230.60

--------------- TTFT (ms) ----------------
Mean TTFT:                               156.23
Median TTFT:                             134.56
P90 TTFT:                                289.34
P95 TTFT:                                345.67
P99 TTFT:                                512.89
--------------- TPOT (ms) ----------------
Mean TPOT:                               14.56
Median TPOT:                             13.21
P90 TPOT:                                18.34
P95 TPOT:                                21.45
P99 TPOT:                                28.67
--------------- ITL (ms) -----------------
Mean ITL:                                13.89
Median ITL:                              12.45
P90 ITL:                                 17.56
P95 ITL:                                 20.12
P99 ITL:                                 26.78
===================================================
```

##### 2.2.2 llm-perf 工具

```bash
# 使用 llm-perf 进行更细致的性能分析
pip install llm-perf

# 运行基准测试，输出详细延迟分布
llm-perf benchmark \
    --endpoint http://localhost:8000/v1 \
    --model meta-llama/Llama-3-8B-Instruct \
    --concurrency 1,5,10,20,50,100 \
    --input-tokens 512,1024,2048,4096 \
    --output-tokens 128,256,512 \
    --duration 60 \
    --output-format json \
    --output-file perf_results.json
```

#### 2.3 性能分析方法

##### GPU Profiling

```bash
# 使用 nsys 进行 GPU 性能分析
nsys profile \
    --trace=cuda,nvtx,osrt \
    --output=profile_output \
    --force-overwrite=true \
    python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3-8B-Instruct

# 使用 ncu 进行 kernel 级别分析
ncu \
    --set full \
    --target-processes all \
    --kernel-name regex:.*attention.* \
    --output attention_profile \
    python benchmarks/benchmark_latency.py \
    --model meta-llama/Llama-3-8B-Instruct \
    --input-len 2048 --output-len 128
```

##### PyTorch Profiler 集成

```python
# 在推理代码中嵌入 profiler
import torch

with torch.profiler.profile(
    activities=[
        torch.profiler.ProfilerActivity.CPU,
        torch.profiler.ProfilerActivity.CUDA,
    ],
    schedule=torch.profiler.schedule(
        wait=5,      # 跳过前 5 步
        warmup=5,    # 预热 5 步
        active=20,   # 采样 20 步
        repeat=1
    ),
    on_trace_ready=torch.profiler.tensorboard_trace_handler('./logs'),
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
) as prof:
    for step, batch in enumerate(dataloader):
        model.generate(**batch)
        prof.step()
```

#### 2.4 GPU 监控指标解读

```bash
# 实时 GPU 监控
nvidia-smi dmon -s pucvmet -d 1

# 输出列说明：
# p: GPU 利用率 (%)
# u: 显存带宽利用率 (%)
# c: GPU 温度 (C)
# v: 显存温度 (C)
# m: 显存使用 (MB)
# e: ECC 错误计数
# t: GPU 热节流原因

# 更详细的指标
nvidia-smi --query-gpu=\
utilization.gpu,\
utilization.memory,\
memory.used,\
memory.total,\
temperature.gpu,\
power.draw,\
clocks.current.sm,\
clocks.current.memory \
--format=csv -l 1
```

**关键指标与性能问题的对应关系：**

| 指标 | 正常范围 | 异常信号 | 可能原因 |
|------|---------|---------|---------|
| GPU 利用率 | 70%-95% | < 50% | batch 太小、调度效率低 |
| 显存带宽利用率 | 60%-90% | > 95% | Decode 阶段带宽瓶颈 |
| 显存使用 | < 90% 总量 | > 95% | KV Cache 压力大，可能 OOM |
| GPU 温度 | < 80C | > 85C | 散热问题或持续高负载 |
| 功耗 | < TDP | 接近 TDP | 持续满载运行 |

---

### 3. SRE 实战案例

#### 案例 1：TTFT p95 突然升高

**背景：** 某 RAG 应用的 LLM 推理服务，使用 vLLM 部署 Llama-3-70B，正常情况下 TTFT p95 在 300ms 以内。某天下午 2 点，用户反馈"回答变慢了，等很久才开始出字"。

**症状：**

```text
时间线：
14:00  TTFT p95 = 280ms（正常）
14:15  TTFT p95 = 520ms（告警触发）
14:30  TTFT p95 = 1200ms（严重）
14:45  TTFT p95 = 1800ms（用户大量投诉）
```

Grafana 面板关键指标变化：

```text
┌─────────────────────────────────────────────────────────────────┐
│  TTFT p95 (ms)    ▲                                            │
│  2000 ┤                              ╭─────                    │
│  1500 ┤                         ╭────╯                         │
│  1000 ┤                    ╭────╯                              │
│   500 ┤              ╭─────╯                                   │
│   280 ┤──────────────╯                                         │
│       └──────────────────────────────────────→ 时间            │
│       14:00    14:15    14:30    14:45                         │
│                                                                 │
│  queue time (ms)  ▲                                           │
│   100 ┤           ╭───────────────                              │
│    50 ┤      ╭────╯                                            │
│    20 ┤──────╯                                                 │
│       └──────────────────────────────────────→ 时间            │
│                                                                 │
│  输入长度 p95 (tokens)  ▲                                     │
│  8000 ┤                    ╭───────────────                     │
│  4000 ┤              ╭─────╯                                   │
│  2000 ┤──────────────╯                                         │
│       └──────────────────────────────────────→ 时间            │
└─────────────────────────────────────────────────────────────────┘
```

**诊断过程——分层排查：**

**第一步：确认瓶颈在 Prefill 还是排队**

```bash
# 检查 vLLM 的 Prometheus 指标
curl -s http://localhost:8000/metrics | grep -E "vllm:num_requests_waiting|vllm:avg_prefill"

# 观察结果：
# vllm:num_requests_waiting 从 5 升到 30
# 排队时间确实增加了，但不是主因
```

queue time 从 20ms 升到 100ms，增加了约 80ms，但 TTFT 增加了 1500ms+。差距在 Prefill 阶段。

**第二步：检查输入长度分布**

```bash
# 从 Prometheus 查询输入长度
curl -s 'http://prometheus:9090/api/v1/query_range' \
    --data-urlencode 'query=histogram_quantile(0.95, rate(vllm:request_input_tokens_bucket[5m]))' \
    --data-urlencode 'start=2026-05-03T06:00:00Z' \
    --data-urlencode 'end=2026-05-03T07:00:00Z' \
    --data-urlencode 'step=60s' | jq '.data.result[0].values'

# 结果：输入长度 p95 从 2000 tokens 飙升到 8000 tokens
```

**第三步：追查输入膨胀来源**

```bash
# 抓取几个典型请求的输入结构
grep "prompt_tokens" /var/log/vllm/access.log | tail -20

# 发现请求结构：
# system prompt: ~500 tokens
# RAG context: ~6500 tokens  ← 这是问题所在
# user question: ~200 tokens
```

**第四步：确认 RAG 检索行为变化**

```bash
# 检查 RAG 服务的日志
grep "retrieval_results" /var/log/rag-service/app.log | tail -10

# 发现：RAG 的 top-k 从 5 被改为 20
# 每个检索结果平均 300 tokens，20 个结果 = 6000 tokens
# 加上 system prompt 和用户问题，总输入超过 7000 tokens
```

**根因：** RAG 服务的一个配置变更（top-k 从 5 改为 20）导致输入上下文从 ~2000 tokens 膨胀到 ~7000 tokens。Prefill 阶段的计算量与输入长度呈二次方关系（实际上是 O(n * d) 但 n 增长带来的 KV Cache 写入和 attention 计算增长显著），导致 TTFT 飙升。

**修复：**

1. **紧急修复**：回滚 RAG top-k 配置到 5。
2. **短期优化**：在 RAG 检索结果拼接前增加截断逻辑，确保总输入不超过 4096 tokens。
3. **中期优化**：启用 vLLM 的 `enable-chunked-prefill`，避免超长 Prefill 阻塞其他请求。
4. **长期优化**：启用 Prefix Cache，复用 system prompt 的 KV Cache。

**预防措施：**

```bash
# 设置输入长度监控告警
# Prometheus 告警规则
groups:
  - name: inference_performance
    rules:
      - alert: InputLengthP95High
        expr: histogram_quantile(0.95, rate(vllm:request_input_tokens_bucket[5m])) > 4096
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "输入长度 p95 超过 4096 tokens"
          description: "当前值: {{ $value }}，可能影响 TTFT"
```

**经验总结：**

1. TTFT 问题的第一步永远是看输入长度分布，而不是直接调引擎参数。
2. 上下游服务的配置变更可能直接影响推理性能，需要有端到端的变更追踪。
3. 对输入长度必须有硬限制和软告警两层防护。

---

#### 案例 2：TPS 瓶颈无法突破

**背景：** 某对话应用使用 vLLM 部署 Llama-3-8B，4 张 A100 GPU（tensor-parallel-size=4）。业务目标是 1000 TPS，但实测只到 600 TPS 就上不去了，GPU 利用率只有 55%。

**症状：**

```text
目标：1000 TPS
实际：600 TPS
GPU 利用率：55%
显存使用：45%
batch size 平均：8（远低于配置的 max_num_seqs=256）
```

这看起来很矛盾——GPU 利用率不高，显存也不紧张，为什么吞吐上不去？

**诊断过程：**

**第一步：检查 batch 组成**

```bash
# 通过 vLLM metrics 检查 batch 状态
curl -s http://localhost:8000/metrics | grep -E "vllm:num_requests_running|vllm:num_requests_waiting"

# 结果：
# vllm:num_requests_running 8-12（波动）
# vllm:num_requests_waiting 0-2（几乎不排队）
```

batch 一直在 8-12 之间，远低于 max_num_seqs=256。这意味着调度器总是在"等不到足够多的请求来填满 batch"。

**第二步：检查请求到达模式**

```bash
# 分析请求到达间隔
python3 << 'EOF'
import json
from collections import Counter

with open('/var/log/vllm/access.log') as f:
    timestamps = []
    for line in f:
        entry = json.loads(line)
        timestamps.append(entry['timestamp'])

# 计算每秒到达请求数
from datetime import datetime
second_counts = Counter()
for ts in timestamps:
    dt = datetime.fromisoformat(ts)
    second_counts[dt.strftime('%H:%M:%S')] += 1

# 分布
counts = list(second_counts.values())
print(f"平均 RPS: {sum(counts)/len(counts):.1f}")
print(f"最大 RPS: {max(counts)}")
print(f"最小 RPS: {min(counts)}")
print(f"P50 RPS: {sorted(counts)[len(counts)//2]}")

# 输出：
# 平均 RPS: 45.0
# 最大 RPS: 120
# 最小 RPS: 5
# P50 RPS: 38
EOF
```

**第三步：检查请求长度分布**

```bash
# 分析输入/输出长度
python3 << 'EOF'
import json

input_lens = []
output_lens = []

with open('/var/log/vllm/access.log') as f:
    for line in f:
        entry = json.loads(line)
        input_lens.append(entry['prompt_tokens'])
        output_lens.append(entry['completion_tokens'])

input_lens.sort()
output_lens.sort()

print(f"输入长度 - P50: {input_lens[len(input_lens)//2]}, "
      f"P90: {input_lens[int(len(input_lens)*0.9)]}, "
      f"P99: {input_lens[int(len(input_lens)*0.99)]}")
print(f"输出长度 - P50: {output_lens[len(output_lens)//2]}, "
      f"P90: {output_lens[int(len(output_lens)*0.9)]}, "
      f"P99: {output_lens[int(len(output_lens)*0.99)]}")

# 输出：
# 输入长度 - P50: 128, P90: 256, P99: 512
# 输出长度 - P50: 64, P90: 128, P99: 256

# 关键发现：请求很短！平均输入才 128 tokens，输出 64 tokens
EOF
```

**第四步：理解问题本质——流量过碎**

```text
┌─────────────────────────────────────────────────────────────────┐
│                    流量过碎问题示意                               │
│                                                                 │
│  理想情况（长请求）：                                            │
│  GPU: [████████████████████████████████████████]  利用率 90%+    │
│        每个请求有足够计算量填满 GPU 时间片                        │
│                                                                 │
│  实际情况（短请求碎片化）：                                       │
│  GPU: [██░██░██░██░██░██░██░██░██░██░██░██░██░██] 利用率 55%    │
│        每个请求很小，batch 也小，kernel 启动开销占比高             │
│                                                                 │
│  问题根源：                                                     │
│  - 请求平均长度太短（128 tokens 输入，64 tokens 输出）           │
│  - 请求到达间隔不均匀，batch 经常凑不满                          │
│  - 每个 iteration 的实际计算量远低于 GPU 容量                    │
└─────────────────────────────────────────────────────────────────┘
```

**根因分析：**

这不是引擎配置问题，而是流量模式问题。短请求 + 低并发 = GPU 大部分时间在等新请求，而不是在计算。具体来说：

1. 请求太短：平均 128 tokens 输入的 Prefill 几乎瞬间完成，Decode 只需要 64 步。
2. 并发太低：45 RPS 平均，每个请求在 Decode 阶段停留约 0.8 秒（64 tokens / 80 tokens/s），同时在 flight 的请求只有约 36 个。
3. batch 凑不满：由于请求短且完成快，Continuous Batching 的优势无法发挥，batch size 长期维持在 8-12。

**修复方案：**

1. **请求合并（Request Merging）**：在负载均衡层将同一用户的连续短请求合并为一个更长的请求。

```python
# 请求合并逻辑示意
class RequestMerger:
    def __init__(self, merge_window_ms=50, max_merge_count=10):
        self.merge_window = merge_window_ms
        self.max_merge = max_merge_count
        self.pending = []

    async def add_request(self, request):
        self.pending.append(request)
        if len(self.pending) >= self.max_merge:
            return await self.flush()
        await asyncio.sleep(self.merge_window / 1000)
        return await self.flush()

    async def flush(self):
        if not self.pending:
            return None
        batch = self.pending
        self.pending = []
        # 将多个请求的输入拼接为一个 batch
        merged_input = concatenate_prompts([r.prompt for r in batch])
        result = await inference_client.generate(merged_input)
        return split_results(result, batch)
```

2. **调度策略优化**：调整 `scheduler_delay_ms` 参数，让调度器稍微等待以积累更多请求。

```bash
# 增加调度延迟，积累更多请求
vllm serve meta-llama/Llama-3-8B-Instruct \
    --scheduler-delay-ms 10 \           # 等 10ms 让更多请求到达
    --max-num-seqs 64 \                 # 降低最大并发（短请求不需要那么多）
    --max-num-batched-tokens 8192       # 降低 batch token 限制
```

3. **容量规划调整**：对于短请求场景，考虑用更少但更强的 GPU 配置。

```text
优化前：4 x A100 (tensor-parallel=4)
  - 模型被切分到 4 张卡
  - 每张卡只处理 1/4 的计算
  - 通信开销大，短请求来不及填满

优化后：2 x A100 (tensor-parallel=2)
  - 模型只切分到 2 张卡
  - 每张卡处理更多计算
  - 通信开销减半
  - 可以部署 2 个独立实例，总体吞吐更高
```

4. **流量模式优化**：在应用层引导用户行为，增加请求长度。

```text
应用层优化建议：
1. 将多轮对话的上下文累积传递（而不是每次只发最新一轮）
2. 增加 system prompt 提供更多任务上下文
3. 引导用户一次性提出更完整的问题
```

**优化结果：**

```text
优化措施                     TPS提升    GPU利用率提升
──────────────────────────────────────────────────────
请求合并（50ms窗口）           +25%       +15%
调度延迟调整（10ms）           +10%       +8%
TP 改为 2，部署 2 实例         +40%       +20%
──────────────────────────────────────────────────────
总体：600 TPS → 1050 TPS      +75%       55% → 85%
```

**预防措施：**

```bash
# 监控 batch 质量
# Prometheus 告警
- alert: BatchSizeLow
  expr: avg_over_time(vllm:num_requests_running[5m]) < 20
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "平均 batch size 过低，GPU 利用率不足"
    description: "当前平均 batch size: {{ $value }}，建议检查流量模式"
```

**经验总结：**

1. GPU 利用率低 + 吞吐上不去 = 流量模式问题，不是引擎参数问题。
2. 短请求场景下，Tensor Parallelism 的通信开销可能超过计算收益。
3. 请求合并是短请求场景最有效的优化手段之一。
4. 容量规划要根据实际请求长度分布来设计，不能只看模型大小。

---

## 💻 实战练习

### 练习 1：基础操作——使用 vLLM Benchmark 测量性能指标

**目标：** 学会使用 vLLM 的基准测试工具测量 TTFT、TPOT 和 TPS，并理解不同负载下的性能表现。

**步骤：**

```bash
# 1. 启动 vLLM 服务（使用小模型方便测试）
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9 \
    --enable-prefix-caching

# 2. 等待服务就绪
curl http://localhost:8000/health

# 3. 下载测试数据集
wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json

# 4. 运行吞吐测试
python benchmarks/benchmark_throughput.py \
    --backend vllm \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --dataset ShareGPT_V3_unfiltered_cleaned_split.json \
    --num-prompts 200

# 5. 运行在线服务延迟测试
python benchmarks/benchmark_serving.py \
    --backend openai \
    --base-url http://localhost:8000/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --dataset ShareGPT_V3_unfiltered_cleaned_split.json \
    --num-prompts 200 \
    --request-rate 5.0

# 6. 测试不同请求速率下的性能
for rate in 1 5 10 20 50; do
    echo "=== Request Rate: $rate ==="
    python benchmarks/benchmark_serving.py \
        --backend openai \
        --base-url http://localhost:8000/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --dataset-name random \
        --random-input-len 512 \
        --random-output-len 128 \
        --num-prompts 100 \
        --request-rate $rate
done
```

**预期输出分析：**

你应该观察到：
- 请求速率增加时，TTFT 和 TPOT 都会逐渐升高
- 在某个临界点后，延迟会急剧上升（排队效应）
- TPS 会在达到峰值后趋于稳定（GPU 容量饱和）

**记录你的发现：**

```text
请求速率    TTFT p95    TPOT p95    TPS       GPU利用率
────────────────────────────────────────────────────────
1 req/s     ___ms       ___ms       ___       ___%
5 req/s     ___ms       ___ms       ___       ___%
10 req/s    ___ms       ___ms       ___       ___%
20 req/s    ___ms       ___ms       ___       ___%
50 req/s    ___ms       ___ms       ___       ___%
```

---

### 练习 2：进阶场景——Prefix Cache 性能对比

**目标：** 配置并验证 Prefix Cache 的性能收益，理解缓存命中/未命中场景下的 TTFT 差异。

**步骤：**

```bash
# 1. 启动不带 Prefix Cache 的服务
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --max-model-len 4096 \
    --port 8001 \
    --gpu-memory-utilization 0.9

# 2. 启动带 Prefix Cache 的服务
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --max-model-len 4096 \
    --port 8002 \
    --gpu-memory-utilization 0.9 \
    --enable-prefix-caching

# 3. 构造测试脚本
cat << 'PYTHON' > test_prefix_cache.py
import time
import requests
import statistics

SYSTEM_PROMPT = """你是一个专业的技术助手，精通 Linux 系统管理、网络配置、
安全策略、性能调优、容器编排、微服务架构、数据库优化、CI/CD 流程、
监控告警、日志分析等 SRE 相关技术领域。请根据用户的问题提供详细、
准确、实用的回答。""" * 5  # 重复 5 次增加长度

QUESTIONS = [
    "如何排查 Linux 服务器的 CPU 使用率过高问题？",
    "请解释 Kubernetes Pod 的生命周期。",
    "如何配置 Nginx 的反向代理和负载均衡？",
    "Redis 集群模式和哨兵模式有什么区别？",
    "如何使用 Prometheus 和 Grafana 搭建监控系统？",
]

def test_endpoint(base_url, name, num_rounds=3):
    results = []
    for round_num in range(num_rounds):
        for i, question in enumerate(QUESTIONS):
            payload = {
                "model": "meta-llama/Llama-3.1-8B-Instruct",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 64,
                "stream": False
            }
            start = time.time()
            resp = requests.post(f"{base_url}/v1/chat/completions", json=payload)
            ttft = resp.json()["usage"]["prompt_tokens"]  # 简化示意
            elapsed = time.time() - start
            results.append({"round": round_num, "q": i, "latency": elapsed})
    return results

# 测试无 Prefix Cache
print("Testing WITHOUT Prefix Cache...")
no_cache_results = test_endpoint("http://localhost:8001", "no-cache")

# 测试有 Prefix Cache（第二轮开始应该命中缓存）
print("Testing WITH Prefix Cache...")
cache_results = test_endpoint("http://localhost:8002", "with-cache")

# 对比结果
no_cache_latencies = [r["latency"] for r in no_cache_results]
cache_first_round = [r["latency"] for r in cache_results if r["round"] == 0]
cache_later_rounds = [r["latency"] for r in cache_results if r["round"] > 0]

print(f"\n=== Results ===")
print(f"No Cache - Avg: {statistics.mean(no_cache_latencies):.3f}s")
print(f"With Cache (1st round) - Avg: {statistics.mean(cache_first_round):.3f}s")
print(f"With Cache (2nd+ round) - Avg: {statistics.mean(cache_later_rounds):.3f}s")
print(f"Cache Hit Speedup: {statistics.mean(no_cache_latencies)/statistics.mean(cache_later_rounds):.2f}x")
PYTHON

# 4. 运行测试
python test_prefix_cache.py
```

**预期结果：**

```text
=== Results ===
No Cache - Avg: 1.234s
With Cache (1st round) - Avg: 1.256s     ← 第一轮需要完整 Prefill
With Cache (2nd+ round) - Avg: 0.345s    ← 后续轮次复用前缀缓存
Cache Hit Speedup: 3.58x
```

**思考题：**

1. 如果 system prompt 经常变化（比如包含当前日期），Prefix Cache 的命中率会如何变化？
2. 在什么场景下 Prefix Cache 的收益最小？
3. 如何监控 Prefix Cache 的命中率？

---

### 练习 3：故障排查挑战——TTFT 飙升排查

**目标：** 给定一个 TTFT 飙升的故障场景，完成从排队到 Prefill 的分层排查，定位根因并制定修复方案。

**场景描述：**

你负责一个使用 vLLM 部署的 LLM 推理服务。以下是告警信息：

```text
[CRITICAL] TTFT p95 > 2000ms for 5 minutes
Service: llm-inference-prod
Model: Qwen2.5-72B-Instruct
Cluster: us-east-1
Current TTFT p95: 2345ms
Normal TTFT p95: 350ms
```

**可用的监控数据：**

```text
指标                              5分钟前      当前
──────────────────────────────────────────────────────
TTFT p95                         350ms       2345ms
TTFT p50                         180ms       890ms
TPOT p95                         18ms        22ms       ← 基本不变
queue time p95                   30ms        120ms      ← 略有增加
waiting requests                 5           15         ← 增加不多
input tokens p95                 2048        8192       ← 显著增加
KV Cache usage                   65%         92%        ← 接近上限
Prefix Cache hit rate            78%         12%        ← 急剧下降
GPU utilization                  80%         85%        ← 基本正常
batch size avg                   32          28         ← 基本正常
```

**你的任务：**

1. 分析上述数据，确定 TTFT 飙升的主要原因。
2. 给出排查步骤和根因推断。
3. 制定短期和长期的修复方案。
4. 写出预防类似问题的告警规则。

**参考答案框架：**

```text
分析过程：

1. TPOT 基本不变 → Decode 阶段正常，问题不在 Decode
2. queue time 只增加 90ms → 排队不是主因
3. input tokens p95 从 2048 飙升到 8192 → 输入长度是关键变量
4. Prefix Cache hit rate 从 78% 降到 12% → 缓存失效导致 Prefill 计算量剧增
5. KV Cache usage 从 65% 升到 92% → 更长的输入占用更多 KV Cache

根因推断：
输入长度增加（可能是 RAG 上下文膨胀或新功能上线）+
Prefix Cache 失效（可能是模型版本更新或 prompt 结构变化）
= Prefill 计算量剧增 = TTFT 飙升

修复方案：
短期：
  - 确认输入长度增加的来源（检查 RAG/上游服务配置）
  - 回滚导致 Prefix Cache 失效的变更
  - 临时降低 max_model_len 限制过长输入

长期：
  - 对输入长度设置硬限制和软告警
  - 监控 Prefix Cache 命中率并设置告警
  - 启用 chunked-prefill 避免长输入阻塞
  - 实现输入长度的自动截断逻辑
```

---

## 🎯 面试题精选

### 面试题 1：Prefill 和 Decode 的资源特征差异是什么？为什么这个区分对 SRE 很重要？

**参考答案：**

Prefill 阶段是一次性处理整个输入序列，计算所有 token 的 Key/Value 并写入 KV Cache。它是计算密集型的，GPU 利用率高，性能与输入长度线性相关，主要影响 TTFT。

Decode 阶段是逐 token 自回归生成，每步只需要计算一个 token 的 Q 并读取整个 KV Cache。它是带宽密集型的，GPU 利用率低（因为 kernel 小且频繁启动），性能受显存带宽和 batch size 影响，主要影响 TPOT 和 TPS。

这个区分对 SRE 重要是因为优化方向完全不同：
- Prefill 慢 → 优化计算：减少输入长度、Prefix Cache、PD 分离到计算资源池。
- Decode 慢 → 优化带宽和并发：增大批大小、量化减少 KV Cache、Continuous Batching。

如果混在一起看，可能用更激进的 batching 去解决长上下文问题，结果 batch 增大后 Prefill 更慢，TTFT 恶化。

---

### 面试题 2：KV Cache 的显存占用如何计算？在容量规划中如何考虑？

**参考答案：**

KV Cache 显存公式：

```
KV Cache = 2 * num_layers * num_kv_heads * head_dim * seq_len * dtype_bytes * batch_size
```

以 Llama-3-70B（80 layers, 8 KV heads, head_dim=128, FP16）为例：
- 单请求、4096 tokens：约 1.25 GB
- 单请求、32768 tokens：约 10 GB
- 50 并发、4096 tokens：约 62.5 GB

容量规划时需要：
1. 预留模型权重空间（INT8 约 70GB，INT4 约 35GB）
2. 预留框架开销（5-10 GB）
3. 剩余空间全部给 KV Cache
4. 用「剩余空间 / 单请求 KV Cache 大小」得出最大并发数
5. 考虑请求长度分布，用 p90 或 p95 输入长度来估算

---

### 面试题 3：Paged Attention 解决了什么问题？它和操作系统的虚拟内存有什么相似之处？

**参考答案：**

Paged Attention 解决了 KV Cache 的内存碎片问题。传统方式为每个请求预分配最大序列长度的连续内存，导致：
1. 内部碎片：实际使用远小于分配（短请求浪费严重）
2. 外部碎片：释放后的空间不连续，无法给新请求使用
3. 无法精确控制并发：只能按最坏情况估算

Paged Attention 将 KV Cache 分成固定大小的 block，通过页表做逻辑到物理的映射。这和操作系统虚拟内存的相似之处：
- 逻辑地址连续，物理地址可以不连续
- 通过页表做地址映射
- 按需分配，减少浪费
- 支持 Copy-on-Write（共享前缀时）

不同之处是 Paged Attention 管理的是 GPU 显存中的 KV Cache block，通常没有换入换出到磁盘的多级层次。

---

### 面试题 4：Continuous Batching 相比静态 Batching 的优势是什么？它对尾延迟有什么影响？

**参考答案：**

静态 Batching 必须等整批请求都完成才能开始下一批，导致：
- 短请求等长请求，GPU 空转
- 新请求必须等整批完成，排队时间增加
- GPU 利用率随请求长度差异增大而降低

Continuous Batching（Iteration-level Batching）在每个 iteration 级别调度：
- 已完成的请求立即退出，释放 KV Cache
- 新请求立即加入，不需要等整批完成
- Prefill 和 Decode 可以在同一个 iteration 中混合执行

对尾延迟的影响：
- 积极面：短请求不再被长请求拖累，p50 和 p90 延迟改善明显
- 消极面：Prefill 和 Decode 混合执行可能导致 Decode 请求被 Prefill"抢占"，引起 TPOT 的短暂抖动，p99 可能反而升高
- 解决方案：chunked-prefill 将长 Prefill 分块执行，减少对 Decode 的影响

---

### 面试题 5：量化在什么场景下收益最大？什么场景下应该谨慎使用？

**参考答案：**

量化收益最大的场景：
1. 显存瓶颈：当系统显存不足以承载目标并发或上下文长度时，INT8/INT4 可以将显存占用减半甚至更多。
2. 大模型部署：70B+ 模型在单卡或少量卡上部署时，量化是必要的。
3. Decode 阶段优化：量化后的权重读取更快，对带宽密集的 Decode 有直接加速。

量化应该谨慎的场景：
1. 精度敏感任务：数学推理、代码生成、长链推理等任务对精度要求高，量化可能导致质量明显下降。
2. 瓶颈不在显存：如果瓶颈已经在计算调度、网络带宽或排队，量化不一定带来线性收益。
3. 频繁版本切换：多个量化分支会增加制品管理、回滚和灰度验证成本。

实践建议：先用 FP8（如果有 H100/H200），再考虑 INT8，最后考虑 INT4。每一步都需要做精度评估。

---

### 面试题 6：PD 分离的适用条件是什么？它引入了哪些额外的复杂度？

**参考答案：**

PD 分离将 Prefill 和 Decode 分配到不同的资源池，各自优化。适用条件：
1. 请求长度差异大：有的请求输入很长（RAG 场景），有的输出很长（生成场景）
2. 集群规模较大：至少 10+ GPU，分资源池才有意义
3. 网络延迟可控：RDMA 或高速互联，否则 KV Cache 传输成为瓶颈
4. 团队有运维能力：维护两套资源池的调度和监控

引入的额外复杂度：
1. KV Cache 传输：Prefill 完成后需要将 KV Cache 传输到 Decode 节点，增加网络开销
2. 调度复杂度：需要智能路由，根据请求特征分配到合适的资源池
3. 故障域扩大：Prefill 节点故障影响所有新请求，Decode 节点故障影响所有进行中的请求
4. 容量规划更难：需要分别估算 Prefill 和 Decode 的容量需求
5. 监控分段：需要分别监控 Prefill 和 Decode 阶段的指标

---

### 面试题 7：如何定位 TTFT 飙升的根因？请给出系统化的排查路径。

**参考答案：**

TTFT = queue time + Prefill time。排查路径：

**第一步：确认瓶颈在哪一段**
- 看 queue time：如果 queue time 占 TTFT 的大部分 → 排队问题 → 扩容或限流
- 看 Prefill time：如果 Prefill 占大部分 → Prefill 问题 → 继续下一步

**第二步：检查输入长度分布**
- 输入长度 p95/p99 是否突然增加
- 常见原因：RAG 上下文膨胀、工具调用结果过长、新功能上线导致 prompt 变长
- 解决：输入截断、RAG top-k 优化、prompt 精简

**第三步：检查 Prefix Cache 命中率**
- 命中率是否下降
- 常见原因：prompt 结构变化、模型版本更新、缓存容量不足
- 解决：恢复 prompt 一致性、增加缓存容量

**第四步：检查 KV Cache 状态**
- KV Cache 是否接近上限
- 如果接近上限，调度器可能需要换出旧请求的 KV Cache
- 解决：降低并发、减小 max_model_len、量化减少 KV Cache 大小

**第五步：检查冷启动**
- 是否有新实例刚上线
- 冷实例的第一次请求 TTFT 会明显偏高
- 解决：预热策略、滚动更新时保持足够热实例

---

### 面试题 8：Speculative Decoding 的原理是什么？在什么条件下收益最大？

**参考答案：**

Speculative Decoding 使用一个小而快的 Draft 模型先猜测 K 个 token，然后由大模型一次性验证这些 token。如果验证通过，就跳过了 K 次自回归生成；如果某个 token 被拒绝，就从该位置开始由大模型重新生成。

收益条件：
1. 接受率高：当 Draft 模型和 Target 模型的输出分布接近时（比如同系列的小模型），接受率可达 70%-90%，每步等效生成多个 token。
2. 输出较长：输出越长，累积的加速效果越明显。
3. 验证成本低于 K 次独立 Decode：大模型一次性验证 K 个 token 的计算量小于 K 次独立 Decode（通常成立，因为可以并行）。

不适合的场景：
1. 接受率低：如果低于 50%，额外的验证成本抵消了收益。
2. 输出很短：只有几个 token 的输出不值得启动 Speculative Decoding。
3. 缺乏观测能力：无法监控接受率，就无法判断是否真正受益。

---

## 📚 深入阅读

- [vLLM 官方文档 - 性能调优](https://docs.vllm.ai/en/latest/performance/benchmarks.html)
- [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)
- [Orca: A Distributed Serving System for Transformer-Based Generative Models](https://www.usenix.org/conference/osdi22/presentation/yu)
- [SpecInfer: Accelerating Generative Large Language Model Serving with Tree-based Speculative Inference and Verification](https://arxiv.org/abs/2305.09781)
- [Splitwise: Efficient Generative LLM Inference Using Phase Disaggregation](https://arxiv.org/abs/2311.18677)
- [Sarathi-Serve: Efficient Chunked-Prefill-Based LLM Inference](https://arxiv.org/abs/2403.02310)
- [02-glossary.md](./02-glossary.md)
- [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md)
- [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)
- [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md)

---

## ✅ 自检清单

完成本章学习后，用以下问题检验自己的理解：

- [ ] 能否画出推理请求的三阶段生命周期并标注各阶段的指标？
- [ ] 能否推导 KV Cache 的显存占用公式并计算具体模型的占用量？
- [ ] 能否解释 Paged Attention 如何减少内存碎片，以及它与 OS 虚拟内存的类比？
- [ ] 能否说明 Continuous Batching 的调度流程以及对 TTFT/TPOT 的影响？
- [ ] 能否在给定场景下选择合适的量化方案（FP8/INT8/INT4）并评估风险？
- [ ] 能否解释 Speculative Decoding 的工作原理和适用条件？
- [ ] 能否设计 PD 分离的架构并说明适用场景和引入的复杂度？
- [ ] 能否从 TTFT 飙升的告警出发，完成分层排查（排队→Prefill→输入长度→缓存）？
- [ ] 能否分析"GPU 利用率低但吞吐上不去"的流量过碎问题？
- [ ] 能否使用 vLLM benchmark 工具进行系统化的性能测试？
