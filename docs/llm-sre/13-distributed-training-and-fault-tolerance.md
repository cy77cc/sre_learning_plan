# LLM SRE 13：分布式训练与容错

> 📅 日期：2026-05-03
> 📖 学习主题：分布式训练并行策略、作业编排与容错恢复
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：12-training-infrastructure-and-gpu-clusters.md, PyTorch 基础

## 🎯 学习目标

完成本篇学习后，你应该能够：

- 画出 DDP/FSDP/TP/PP 的数据流和通信模式图，并解释每种并行策略的工程影响
- 解释 ZeRO 各阶段（1/2/3）的显存优化原理，计算不同阶段的显存占用
- 设计 checkpoint/resume 策略并评估 RTO（Recovery Time Objective）
- 诊断 NCCL hang、节点驱逐、网络抖动等分布式训练故障，给出完整排查链路
- 使用 torchrun 启动分布式训练作业，配置 NCCL 调试参数
- 为 Spot/Preemptible 实例场景设计弹性容错方案

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 为什么需要分布式训练

单卡 GPU 的显存和算力有限。以 LLaMA-70B 为例，仅模型参数就需要约 140GB（FP16），加上优化器状态（Adam 需要 2 倍参数量）、梯度和激活值，总显存需求轻松超过 500GB。即使是最新的 H100 80GB 也无法在单卡上完成训练。分布式训练通过将计算和存储分散到多张 GPU 上，使大模型训练成为可能。

但分布式训练引入了三个根本性挑战：

1. **通信开销**：GPU 之间需要同步梯度、交换参数，通信成为瓶颈
2. **故障半径扩大**：8 节点 64 卡的作业，任何一张卡出问题都会影响全局
3. **状态一致性**：恢复训练时需要保证所有 rank 的状态完全一致

从 SRE 角度看，分布式训练是一类"任何单点抖动都会扩散为全局退化"的系统。理解并行策略不是为了调算法，而是为了知道故障会从哪里冒出来、会扩散到多大范围、恢复路径是什么。

#### 1.2 并行策略详解

##### Data Parallelism (DP/DDP)

数据并行是最基础的并行策略。核心思想是每个 GPU 持有完整的模型副本，但处理不同的数据批次。

```text
DDP 通信模式图（4 GPU 示例）：

  GPU 0              GPU 1              GPU 2              GPU 3
  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
  │ 完整模型  │       │ 完整模型  │       │ 完整模型  │       │ 完整模型  │
  │ Batch A  │       │ Batch B  │       │ Batch C  │       │ Batch D  │
  └────┬─────┘       └────┬─────┘       └────┬─────┘       └────┬─────┘
       │                  │                  │                  │
       │   前向传播        │   前向传播        │   前向传播        │   前向传播
       │                  │                  │                  │
       v                  v                  v                  v
  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
  │ 本地梯度  │       │ 本地梯度  │       │ 本地梯度  │       │ 本地梯度  │
  └────┬─────┘       └────┬─────┘       └────┬─────┘       └────┬─────┘
       │                  │                  │                  │
       └──────────────────┴────────┬─────────┴──────────────────┘
                                   │
                              AllReduce
                              (梯度同步)
                                   │
       ┌──────────────────┬────────┴─────────┬──────────────────┐
       │                  │                  │                  │
       v                  v                  v                  v
  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
  │ 平均梯度  │       │ 平均梯度  │       │ 平均梯度  │       │ 平均梯度  │
  │ 更新参数  │       │ 更新参数  │       │ 更新参数  │       │ 更新参数  │
  └──────────┘       └──────────┘       └──────────┘       └──────────┘
```

**DDP 的关键特性**：

- 每个 rank 保存完整模型：参数 + 梯度 + 优化器状态
- AllReduce 通信：所有 rank 的梯度求平均，结果广播给所有 rank
- Ring AllReduce 算法：通信量 = 2 * (N-1)/N * 模型大小，与 GPU 数量近似无关
- 通信与计算可以重叠（gradient bucketing）

**DDP 的工程代价**：

- 显存占用 = 模型大小 * 3（参数 + 梯度 + 优化器状态），对大模型不友好
- AllReduce 需要所有 rank 同步，一个慢节点拖慢全局
- 模型必须能放进单卡显存

**PyTorch DDP 核心代码结构**：

```python
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

def setup(rank, world_size):
    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)

def train(rank, world_size):
    setup(rank, world_size)
    model = MyModel().to(rank)
    model = DDP(model, device_ids=[rank])
    optimizer = torch.optim.Adam(model.parameters())

    for batch in dataloader:
        loss = model(batch)
        loss.backward()       # 梯度自动 AllReduce
        optimizer.step()
        optimizer.zero_grad()

    dist.destroy_process_group()
```

##### FSDP / ZeRO Stage 1/2/3

FSDP（Fully Sharded Data Parallel）是 PyTorch 对 ZeRO（Zero Redundancy Optimizer）的实现。核心思想是把模型状态分片到不同 GPU 上，用通信换显存。

```text
FSDP/ZeRO 显存分布图（4 GPU，Stage 1/2/3 对比）：

ZeRO Stage 1（优化器状态分片）：
┌──────────────────────────────────────────────────────────────┐
│  GPU 0          GPU 1          GPU 2          GPU 3          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐       │
│  │参数(完整)│    │参数(完整)│    │参数(完整)│    │参数(完整)│       │
│  │梯度(完整)│    │梯度(完整)│    │梯度(完整)│    │梯度(完整)│       │
│  │优化器 1/4│    │优化器 1/4│    │优化器 1/4│    │优化器 1/4│       │
│  └────────┘    └────────┘    └────────┘    └────────┘       │
│  显存节省：~4x (仅优化器状态)                                   │
└──────────────────────────────────────────────────────────────┘

ZeRO Stage 2（优化器状态 + 梯度分片）：
┌──────────────────────────────────────────────────────────────┐
│  GPU 0          GPU 1          GPU 2          GPU 3          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐       │
│  │参数(完整)│    │参数(完整)│    │参数(完整)│    │参数(完整)│       │
│  │梯度 1/4 │    │梯度 1/4 │    │梯度 1/4 │    │梯度 1/4 │       │
│  │优化器 1/4│    │优化器 1/4│    │优化器 1/4│    │优化器 1/4│       │
│  └────────┘    └────────┘    └────────┘    └────────┘       │
│  显存节省：~8x (优化器状态 + 梯度)                              │
└──────────────────────────────────────────────────────────────┘

ZeRO Stage 3（优化器状态 + 梯度 + 参数全部分片）：
┌──────────────────────────────────────────────────────────────┐
│  GPU 0          GPU 1          GPU 2          GPU 3          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐       │
│  │参数 1/4 │    │参数 1/4 │    │参数 1/4 │    │参数 1/4 │       │
│  │梯度 1/4 │    │梯度 1/4 │    │梯度 1/4 │    │梯度 1/4 │       │
│  │优化器 1/4│    │优化器 1/4│    │优化器 1/4│    │优化器 1/4│       │
│  └────────┘    └────────┘    └────────┘    └────────┘       │
│  显存节省：~N倍 (N = GPU数量)，每卡只存 1/N 的全部状态          │
└──────────────────────────────────────────────────────────────┘
```

**ZeRO 各阶段的通信开销对比**：

| Stage | 分片内容 | 显存节省 | 通信量 | 适用场景 |
|-------|---------|---------|--------|---------|
| 0 (DDP) | 无 | 无 | 2 * model_size | 小模型，显存充足 |
| 1 | 优化器状态 | ~4x | 2 * model_size | 中等模型 |
| 2 | 优化器 + 梯度 | ~8x | 2 * model_size | 大模型，通信带宽充足 |
| 3 | 优化器 + 梯度 + 参数 | ~N * 3x | 3 * model_size | 超大模型，显存极度紧张 |

**关键理解**：ZeRO Stage 3 通信量比 Stage 2 多 50%，因为前向传播时需要临时收集完整参数（AllGather），用完后再释放。这是用通信换显存的直接代价。

**PyTorch FSDP 配置示例**：

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy

# Stage 2 等效配置
model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.SHARD_GRAD_OP,  # Stage 2
    auto_wrap_policy=transformer_auto_wrap_policy,
    mixed_precision=MixedPrecision(
        param_dtype=torch.bfloat16,
        reduce_dtype=torch.float32,
        buffer_dtype=torch.bfloat16,
    ),
)

# Stage 3 等效配置
model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,  # Stage 3
    auto_wrap_policy=transformer_auto_wrap_policy,
)
```

##### Tensor Parallelism (TP)

张量并行把单层的计算切分到多张 GPU 上。以 Transformer 的 MLP 层为例：

```text
Tensor Parallelism（TP=2，MLP 层切分）：

  输入 X（每张卡都有完整副本）
       │
       ├──────────────────────┐
       v                      v
  ┌─────────────┐       ┌─────────────┐
  │ GPU 0       │       │ GPU 1       │
  │ W_gate[:,0:N/2]      │ W_gate[:,N/2:N]    │
  │ W_up[:,0:N/2]        │ W_up[:,N/2:N]      │
  │             │       │             │
  │ Y0 = X @ W0 │       │ Y1 = X @ W1 │
  └──────┬──────┘       └──────┬──────┘
         │                     │
         │     AllReduce       │
         └────────┬────────────┘
                  v
          ┌──────────────┐
          │  Y = Y0 + Y1  │
          │  (完整结果)     │
          └──────────────┘
```

**TP 的关键特性**：

- 每层前向/反向都需要 AllReduce 或 AllGather 通信
- 通信频率极高（每层 2 次），对延迟极其敏感
- 必须使用节点内高速互联（NVLink），跨节点 TP 效率极差
- TP 度通常等于单节点 GPU 数（如 TP=8 对应 8 卡节点）

**TP 的工程代价**：

- 严重依赖 NVLink/NVSwitch，跨节点使用会因带宽不足导致训练极慢
- 通信与计算无法完全重叠，bubble 时间明显
- 模型结构需要支持列切分/行切分，不是所有层都能高效切分

##### Pipeline Parallelism (PP)

流水线并行把模型按层分成多个阶段，每个阶段放在不同 GPU 上。

```text
Pipeline Parallelism（PP=4，4 阶段流水线）：

时间 ──────────────────────────────────────────────────────►

GPU 0: [F0]─────────────[F4]─────────────[F8]──────[B8]────[B4]────[B0]
        │                │                │        │       │       │
GPU 1:      [F1]─────────────[F5]─────────────[F9]────[B9]────[B5]────[B1]
              │                │                │      │       │       │
GPU 2:            [F2]─────────────[F6]────────────[B10]──[B6]────[B2]
                    │                │                │      │       │
GPU 3:                  [F3]─────────────[F7]──────────[B11]──[B7]────[B3]

F = Forward, B = Backward
数字 = micro-batch 编号

Pipeline Bubble（气泡时间）：
┌─────────────────────────────────────────────────────────────┐
│  时间轴                                                      │
│  ├─ warmup ─┤──── steady state ────┤── cooldown ─┤          │
│  (填充管道)    (稳定吞吐)             (排空管道)               │
│                                                              │
│  bubble 比例 ≈ (PP - 1) / (PP + micro_batches - 1)          │
│  例：PP=4, micro_batches=16  → bubble ≈ 3/19 ≈ 15.8%        │
└─────────────────────────────────────────────────────────────┘
```

**PP 的关键特性**：

- 每个 GPU 只负责模型的一部分层
- 通过 micro-batching 实现流水线重叠，减少 bubble
- 通信量相对较小（只传递激活值和梯度），但对延迟敏感
- 需要仔细平衡各阶段的计算量

**PP 的工程代价**：

- Pipeline bubble 导致 GPU 利用率下降
- 各阶段负载不均衡会导致 straggler
- 恢复时需要重建整个流水线拓扑
- 调试困难：某个 stage 的问题会传播到下游

##### Expert Parallelism (EP)

专家并行是 MoE（Mixture of Experts）模型的专属策略。每个 expert 分布在不同 GPU 上，通过 All-to-All 通信路由 token。

```text
Expert Parallelism（EP=4，MoE 层）：

  输入 tokens
       │
       v
  ┌─────────────┐
  │  Router      │  ← 计算每个 token 应该发给哪个 expert
  │  (门控网络)   │
  └──────┬──────┘
         │
         │ All-to-All 通信
         │ (每个 token 路由到对应 expert 所在的 GPU)
         │
  ┌──────┴──────────────────────────────────────────┐
  │                                                  │
  v              v              v              v
┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐
│ GPU 0│    │ GPU 1│    │ GPU 2│    │ GPU 3│
│Expert│    │Expert│    │Expert│    │Expert│
│ 0,1  │    │ 2,3  │    │ 4,5  │    │ 6,7  │
└──┬───┘    └──┬───┘    └──┬───┘    └──┬───┘
   │           │           │           │
   │  All-to-All 通信（结果回传）
   └───────────┴─────┬─────┴───────────┘
                     v
              ┌──────────────┐
              │  合并输出      │
              └──────────────┘
```

**EP 的关键特性**：

- All-to-All 通信模式，通信量与 expert 数量和路由分布相关
- 负载不均衡是核心问题：热门 expert 过载，冷门 expert 空闲
- 尾延迟敏感：一个慢 expert 拖慢全局
- 通常与 TP/PP 组合使用

##### 混合并行策略（DP + TP + PP）

实际训练大模型时，通常需要组合多种并行策略。以 128 张 GPU 训练 70B 模型为例：

```text
混合并行拓扑图（DP=2, TP=8, PP=8, 共 128 GPU = 16 节点）：

                    ┌──────────────────────────────────────────────────┐
                    │              Data Parallel (DP = 2)               │
                    │                                                  │
    ┌───────────────┴───────────────┐    ┌───────────────┴───────────────┐
    │         DP Group 0            │    │         DP Group 1            │
    │                               │    │                               │
    │  ┌─────────────────────────┐  │    │  ┌─────────────────────────┐  │
    │  │  Pipeline (PP = 8)      │  │    │  │  Pipeline (PP = 8)      │  │
    │  │                         │  │    │  │                         │  │
    │  │  Stage0  Stage1 ... Stage7  │  │    │  │  Stage0  Stage1 ... Stage7  │  │
    │  │  ┌────┐ ┌────┐   ┌────┐│  │    │  │  ┌────┐ ┌────┐   ┌────┐│  │
    │  │  │TP=8│ │TP=8│   │TP=8││  │    │  │  │TP=8│ │TP=8│   │TP=8││  │
    │  │  │8GPU│ │8GPU│   │8GPU││  │    │  │  │8GPU│ │8GPU│   │8GPU││  │
    │  │  └────┘ └────┘   └────┘│  │    │  │  └────┘ └────┘   └────┘│  │
    │  └─────────────────────────┘  │    │  └─────────────────────────┘  │
    │         8 节点 64 GPU          │    │         8 节点 64 GPU          │
    └───────────────────────────────┘    └───────────────────────────────┘

总 GPU 数 = DP(2) * PP(8) * TP(8) = 128

通信模式：
  - TP 通信：节点内 NVLink（最高带宽，最低延迟）
  - PP 通信：节点间 InfiniBand（传递激活值，数据量较小）
  - DP 通信：节点间 InfiniBand（AllReduce 梯度，数据量最大）
```

**混合并行设计原则**：

1. **TP 优先放在节点内**：TP 通信频率最高，必须用最快的互联
2. **PP 可以跨节点**：PP 通信量相对较小，对带宽要求低于 TP
3. **DP 放在最外层**：DP 通信可以与计算重叠，对延迟容忍度最高
4. **总 GPU 数 = DP * TP * PP**：三个维度的乘积等于总并行度

#### 1.3 作业编排与 Rank 拓扑

##### World Size, Rank, Local Rank

分布式训练中的进程标识体系：

```text
Rank 标识体系（16 GPU，4 节点示例）：

节点 0 (Node Rank 0)           节点 1 (Node Rank 1)
┌──────────────────────┐       ┌──────────────────────┐
│ Global  │  Local     │       │ Global  │  Local     │
│ Rank    │  Rank      │       │ Rank    │  Rank      │
│─────────│────────────│       │─────────│────────────│
│  0      │    0       │       │  8      │    0       │
│  1      │    1       │       │  9      │    1       │
│  2      │    2       │       │ 10      │    2       │
│  3      │    3       │       │ 11      │    3       │
│  4      │    4       │       │ 12      │    4       │
│  5      │    5       │       │ 13      │    5       │
│  6      │    6       │       │ 14      │    6       │
│  7      │    7       │       │ 15      │    7       │
└──────────────────────┘       └──────────────────────┘

world_size = 16（总 GPU 数）
node_rank = 0 或 1（节点编号）
local_rank = 0~7（节点内 GPU 编号）
global_rank = node_rank * gpus_per_node + local_rank
```

- **world_size**：总参与训练的进程数，通常等于总 GPU 数
- **rank**（global rank）：全局唯一编号，标识当前进程在所有参与进程中的位置
- **local_rank**：当前节点内的 GPU 编号，用于设置 `torch.cuda.set_device()`
- **node_rank**：节点编号，由调度器分配

**Rank 映射的工程影响**：

rank 到物理 GPU 的映射直接影响通信效率。如果 TP 组内的 rank 分散在不同节点上，TP 通信将走跨节点网络，性能大幅下降。正确的做法是让通信最频繁的 rank 优先落在同一节点的 NVLink 域内。

##### torchrun / elastic agent

`torchrun` 是 PyTorch 官方推荐的分布式训练启动器，替代了旧版 `torch.distributed.launch`。

```bash
# 基本启动：单节点 8 卡
torchrun \
    --nproc_per_node=8 \
    train.py \
    --model_name llama-70b \
    --batch_size 4

# 多节点启动：2 节点 16 卡
# 在节点 0 上执行：
torchrun \
    --nnodes=2 \
    --nproc_per_node=8 \
    --node_rank=0 \
    --master_addr=10.0.0.1 \
    --master_port=29500 \
    train.py

# 在节点 1 上执行：
torchrun \
    --nnodes=2 \
    --nproc_per_node=8 \
    --node_rank=1 \
    --master_addr=10.0.0.1 \
    --master_port=29500 \
    train.py

# 弹性训练模式（允许节点数变化）
torchrun \
    --nnodes=2:4 \
    --nproc_per_node=8 \
    --max_restarts=3 \
    --rdzv_backend=etcd \
    --rdzv_endpoint=etcd-server:2379 \
    train.py
```

**torchrun 关键参数详解**：

| 参数 | 说明 | 典型值 |
|------|------|--------|
| `--nnodes` | 参与训练的节点数 | 固定值或范围如 `2:4` |
| `--nproc_per_node` | 每节点启动的进程数 | 通常等于 GPU 数 |
| `--node_rank` | 当前节点编号 | 0 ~ nnodes-1 |
| `--master_addr` | rendezvous 主节点地址 | 节点 0 的 IP |
| `--master_port` | rendezvous 端口 | 29500 |
| `--max_restarts` | 每个进程最大重启次数 | 3 |
| `--rdzv_backend` | rendezvous 后端 | `etcd`, `c10d` |
| `--rdzv_endpoint` | rendezvous 服务地址 | etcd 地址 |
| `--redirects` | stdout/stderr 重定向 | `3` 表示重定向到文件 |

#### 1.4 Checkpoint 与断点续训

Checkpoint 是分布式训练容错的基石。它需要回答三个问题：保存什么、多久保存一次、恢复时如何校验一致性。

##### 需要保存的状态

一个完整的训练 checkpoint 应包含：

```text
Checkpoint 内容清单：

┌─────────────────────────────────────────────────────┐
│                    Checkpoint                        │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │  模型参数 (model state_dict)                     │ │
│  │  - 每个 rank 的完整参数（DDP）或分片参数（FSDP）    │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  优化器状态 (optimizer state_dict)                │ │
│  │  - Adam 的 m (一阶矩) 和 v (二阶矩)              │ │
│  │  - 学习率调度器状态                               │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  训练状态                                        │ │
│  │  - 当前 epoch 和 step 数                         │ │
│  │  - 随机数状态（Python, NumPy, CUDA）              │ │
│  │  - 数据加载器的 sampler 状态                      │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  元数据                                          │ │
│  │  - 并行配置（DP/TP/PP 大小）                      │ │
│  │  - 模型版本、数据版本                             │ │
│  │  - 保存时间、step 时间                            │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

只保存权重而不保存优化器状态和随机数状态，恢复后会出现 loss 曲线跳变。这是因为优化器的动量信息丢失，学习率调度器状态重置，导致参数更新方向突变。

##### 同步 Checkpoint vs 异步 Checkpoint

```text
同步 Checkpoint：
时间线：──── train ────│ BLOCK │──── train ────
                       保存 checkpoint
                       (所有 rank 等待)

异步 Checkpoint：
时间线：──── train ──────────── train ────────────
                       │       │
                       │  后台保存 │
                       │ (不阻塞)  │

异步 checkpoint 的实现方式：
1. 将状态复制到 CPU 内存（快，~1s）
2. 在后台线程中将 CPU 内存写入存储（慢，可能 10-60s）
3. 训练继续进行，不受写入影响
```

**同步 checkpoint**：所有 rank 暂停训练，等待 checkpoint 写入完成后继续。实现简单但会阻塞训练，对于 70B+ 模型，单次 checkpoint 可能耗时 5-15 分钟。

**异步 checkpoint**：将模型状态复制到 CPU 内存后立即恢复训练，后台线程负责将数据写入存储。对训练的阻塞时间从分钟级降到秒级，但实现更复杂，需要处理内存不足和写入失败的情况。

##### 分布式 Checkpoint（PyTorch DCP）

PyTorch Distributed Checkpoint (DCP) 是专门针对分布式训练设计的 checkpoint 方案：

```python
import torch.distributed.checkpoint as dcp

# 保存 checkpoint
def save_checkpoint(model, optimizer, step, path):
    state_dict = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "step": step,
    }
    dcp.save(
        state_dict=state_dict,
        storage_writer=dcp.FileSystemWriter(path),
    )

# 加载 checkpoint（支持不同并行度恢复）
def load_checkpoint(model, optimizer, path):
    state_dict = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
    }
    dcp.load(
        state_dict=state_dict,
        storage_reader=dcp.FileSystemReader(path),
    )
    return state_dict
```

**DCP 的关键优势**：

- 支持不同并行度下的 checkpoint 加载（如从 TP=8 的 checkpoint 恢复到 TP=4）
- 自动处理分片参数的重新分布
- 支持增量 checkpoint（只保存变化的部分）

##### Checkpoint/Resume 流程图

```text
正常 Checkpoint 流程：
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│ 训练循环  │────>│ 触发保存条件  │────>│ 收集所有状态   │────>│ 写入存储  │
│ (step N)  │     │ (每N步/时间)  │     │ (同步/异步)    │     │ (共享存储) │
└──────────┘     └──────────────┘     └───────────────┘     └────┬─────┘
                                                                 │
                                                            ┌────v─────┐
                                                            │ 写入元数据│
                                                            │ (版本号)  │
                                                            └──────────┘

故障恢复流程：
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│ 检测到故障│────>│ 节点重启/重调度│────>│ rendezvous    │────>│ 找到最新  │
│ (节点/OOM)│     │ (K8s/Slurm)  │     │ (重新组网)     │     │ checkpoint│
└──────────┘     └──────────────┘     └───────────────┘     └────┬─────┘
                                                                 │
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌────v─────┐
│ 恢复训练  │<────│ 验证状态一致  │<────│ 加载状态到GPU  │<────│ 广播路径  │
│ (step N+1)│     │ (loss对齐)   │     │ (map_location)│     │ (所有rank)│
└──────────┘     └──────────────┘     └───────────────┘     └──────────┘
```

##### RTO 评估

RTO（Recovery Time Objective）= 故障发生到恢复训练的时间。它由以下部分组成：

```text
RTO = T_detect + T_schedule + T_rendezvous + T_load + T_warmup

T_detect:    故障检测时间（心跳超时、健康检查失败）  ~30s - 5min
T_schedule:  新节点调度时间（K8s pod 重建）          ~30s - 5min
T_rendezvous: 重新组网时间（所有 rank 就位）          ~10s - 1min
T_load:      Checkpoint 加载时间                    ~30s - 10min
T_warmup:    恢复到正常训练速度（学习率预热等）        ~0s - 2min

典型 RTO：2 - 20 分钟（取决于模型大小和基础设施响应速度）
```

#### 1.5 容错策略

##### 节点故障检测与恢复

```text
故障检测与恢复流程图：

┌─────────────┐
│ 训练运行中   │
└──────┬──────┘
       │
       v
┌─────────────────┐    是    ┌──────────────┐
│ NCCL 超时/错误?  │────────>│ 进入故障处理  │
└────────┬────────┘         └──────┬───────┘
         │ 否                      │
         v                         v
┌─────────────────┐         ┌──────────────────┐
│ 节点健康检查     │         │ 收集诊断信息      │
│ (GPU/网络/磁盘)  │         │ (NCCL_DEBUG,日志) │
└────────┬────────┘         └──────┬───────────┘
         │                         │
         v                         v
┌─────────────────┐         ┌──────────────────┐
│ step time 异常?  │         │ 隔离故障节点      │
│ (straggler检测)  │         │ (标记不可用)      │
└────────┬────────┘         └──────┬───────────┘
         │                         │
         v                         v
┌─────────────────┐         ┌──────────────────┐
│ 指标正常         │         │ 重新 rendezvous   │
│ 继续训练         │         │ (排除故障节点)     │
└─────────────────┘         └──────┬───────────┘
                                   │
                                   v
                            ┌──────────────────┐
                            │ 加载最新 checkpoint│
                            └──────┬───────────┘
                                   │
                                   v
                            ┌──────────────────┐
                            │ 恢复训练          │
                            └──────────────────┘
```

##### Spot/Preemptible 实例策略

Spot 实例可以节省 60-90% 的计算成本，但随时可能被回收。设计容错策略的核心是让中断成为可预算事件，而不是灾难事件。

**关键策略**：

1. **混合部署**：关键 rank（如 PP 的第一个和最后一个 stage）放在按需实例，中间 stage 放在 Spot 实例
2. **高频 checkpoint**：Spot 实例场景下，checkpoint 间隔从每小时缩短到每 10-15 分钟
3. **驱逐信号响应**：收到 2 分钟驱逐预警后，立即触发紧急 checkpoint
4. **弹性并行度**：使用 torchelastic 支持节点数变化，被驱逐后用更少节点继续训练

```python
# Spot 实例驱逐信号处理
import signal
import torch.distributed as dist

def handle_preemption(signum, frame):
    """收到 SIGTERM 后触发紧急 checkpoint"""
    print(f"Rank {dist.get_rank()}: 收到驱逐信号，触发紧急 checkpoint")
    save_emergency_checkpoint()
    # 等待所有 rank 完成保存
    dist.barrier()
    exit(0)

# 注册 SIGTERM 处理器（云厂商通常用 SIGTERM 通知驱逐）
signal.signal(signal.SIGTERM, handle_preemption)
```

##### 弹性训练（torchelastic）

torchelastic 允许训练作业在节点数变化时自动恢复，无需人工干预：

```text
弹性训练流程：

初始状态（4 节点 32 GPU）：
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│Node0│ │Node1│ │Node2│ │Node3│
│8 GPU│ │8 GPU│ │8 GPU│ │8 GPU│
└─────┘ └─────┘ └─────┘ └─────┘

Node2 被驱逐：
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│Node0│ │Node1│ │ XXX │ │Node3│
│8 GPU│ │8 GPU│ │驱逐  │ │8 GPU│
└─────┘ └─────┘ └─────┘ └─────┘

自动恢复（降级到 3 节点 24 GPU）：
┌─────┐ ┌─────┐ ┌─────┐
│Node0│ │Node1│ │Node3│
│8 GPU│ │8 GPU│ │8 GPU│
└─────┘ └─────┘ └─────┘
重新 rendezvous → 加载 checkpoint → 继续训练
(world_size 从 32 变为 24)
```

**弹性训练的限制**：

- 并行度变化可能导致 TP/PP 配置需要重新调整
- 小 batch size 训练效率下降
- checkpoint 需要支持不同 world_size 加载

### 2. 命令/工具详解

#### 2.1 torchrun 启动参数详解

```bash
# 完整的生产级启动脚本
#!/bin/bash
set -euo pipefail

# 环境变量
export MASTER_ADDR=${MASTER_ADDR:-"10.0.0.1"}
export MASTER_PORT=${MASTER_PORT:-29500}
export NCCL_DEBUG=${NCCL_DEBUG:-"WARN"}
export NCCL_IB_DISABLE=${NCCL_IB_DISABLE:-0}
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"eth0"}
export OMP_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=false

# torchrun 启动
torchrun \
    --nnodes=${NNODES} \
    --nproc_per_node=${NPROC_PER_NODE} \
    --node_rank=${NODE_RANK} \
    --master_addr=${MASTER_ADDR} \
    --master_port=${MASTER_PORT} \
    --max_restarts=3 \
    --log_dir=/var/log/training \
    --redirects=3 \
    --monitor-interval=5 \
    train.py \
    --config config.yaml \
    --checkpoint_dir /checkpoints/llama-70b \
    --save_interval 500
```

#### 2.2 NCCL 环境变量

NCCL 的行为通过环境变量控制，这些变量是排查分布式训练问题的关键：

| 环境变量 | 说明 | 推荐值/用法 |
|---------|------|------------|
| `NCCL_DEBUG` | 调试日志级别 | `INFO`（排查时）/ `WARN`（生产） |
| `NCCL_DEBUG_SUBSYS` | 指定子系统日志 | `ALL`, `INIT`, `NET`, `GRAPH` |
| `NCCL_IB_DISABLE` | 禁用 InfiniBand | `0`（启用 IB）/ `1`（回退到 TCP） |
| `NCCL_SOCKET_IFNAME` | 指定网络接口 | `eth0`, `bond0` |
| `NCCL_P2P_DISABLE` | 禁用 P2P 通信 | 通常 `0`，NVLink 有问题时设为 `1` |
| `NCCL_NET_GDR_LEVEL` | GPUDirect RDMA 级别 | `0`-`5`，按硬件能力设置 |
| `NCCL_TOPO_FILE` | 指定拓扑文件 | 自定义拓扑描述文件路径 |
| `NCCL_TIMEOUT` | 通信超时时间 | 默认 `30min`，按需调整 |
| `NCCL_ASYNC_ERROR_HANDLING` | 异步错误处理 | `1`（推荐启用） |

**NCCL_DEBUG 输出示例（排查通信问题）**：

```text
# 正常初始化日志
NCCL INFO NET/Plugin : Using [0] plugin=libnccl-net.so
NCCL INFO NET/IB : Using [0] mlx5_0:1/RoCE
NCCL INFO NET/IB : Using [1] mlx5_1:1/RoCE
NCCL INFO Using network IB
NCCL INFO comm 0x7f8b1c001460 rank 0 nranks 8 cudaDev 0 busId 10000:00:00.0
NCCL INFO comm 0x7f8b1c001460 rank 1 nranks 8 cudaDev 1 busId 10000:00:01.0
NCCL INFO Trees [0] 1/-1/-1->0->-1 [1] -1/-1/-1->0->1
NCCL INFO Channel 00 : 0[eb00] -> 1[eb01] via P2P/IPC
NCCL INFO Channel 01 : 0[eb00] -> 1[eb01] via P2P/IPC

# 异常日志（网络问题）
NCCL WARN mlx5_0:1/RoCE : Connection to rank 2 timed out after 30000ms
NCCL INFO NET/IB : Got completion from peer 2 with error 12 (Transport retry counter exceeded)
NCCL ERROR misc/socket.cc:481 'Connection reset by peer'
NCCL ERROR misc/socket.cc:529 'Connection closed by remote peer'
```

#### 2.3 PyTorch Profiler 分析通信瓶颈

```python
import torch
from torch.profiler import profile, record_function, ProfilerActivity

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    schedule=torch.profiler.schedule(wait=1, warmup=1, active=3, repeat=1),
    on_trace_ready=torch.profiler.tensorboard_trace_handler("/tmp/traces"),
    record_shapes=True,
    with_stack=True,
) as prof:
    for step, batch in enumerate(dataloader):
        if step >= 5:
            break
        with record_function("forward"):
            loss = model(batch)
        with record_function("backward"):
            loss.backward()
        with record_function("optimizer"):
            optimizer.step()
        prof.step()

# 查看通信操作耗时
print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))
# 重点关注：nccl:AllReduce, nccl:AllGather, nccl:ReduceScatter
```

#### 2.4 FSDP 配置参数

```python
from torch.distributed.fsdp import (
    FullyShardedDataParallel as FSDP,
    ShardingStrategy,
    BackwardPrefetch,
    MixedPrecision,
    CPUOffload,
)
from torch.distributed.fsdp.wrap import (
    transformer_auto_wrap_policy,
    size_based_auto_wrap_policy,
)
import functools

# Transformer 模型的自动包装策略
auto_wrap_policy = functools.partial(
    transformer_auto_wrap_policy,
    transformer_layer_cls={TransformerBlock},  # 指定要包装的层类
)

# 混合精度配置
mixed_precision_policy = MixedPrecision(
    param_dtype=torch.bfloat16,      # 参数存储精度
    reduce_dtype=torch.float32,       # 梯度归约精度
    buffer_dtype=torch.bfloat16,      # 缓冲区精度
)

# FSDP 模型初始化
model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,     # Stage 3
    cpu_offload=CPUOffload(offload_params=False),       # 是否 offload 到 CPU
    auto_wrap_policy=auto_wrap_policy,
    mixed_precision=mixed_precision_policy,
    backward_prefetch=BackwardPrefetch.BACKWARD_PRE,    # 预取优化
    device_id=torch.cuda.current_device(),
    limit_all_gathers=True,                              # 限制并发 AllGather
    forward_prefetch=True,                               # 前向预取
)
```

#### 2.5 分布式 Checkpoint API

```python
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import (
    get_state_dict,
    set_state_dict,
)

# 保存（推荐方式，使用 get_state_dict 处理 FSDP 分片）
def save_checkpoint(model, optimizer, step, path):
    # get_state_dict 自动处理 FSDP 的分片参数
    model_state, optim_state = get_state_dict(model, optimizer)
    state_dict = {
        "model": model_state,
        "optimizer": optim_state,
        "step": step,
    }
    dcp.save(state_dict, storage_writer=dcp.FileSystemWriter(path))

# 加载（支持不同并行度）
def load_checkpoint(model, optimizer, path):
    model_state, optim_state = get_state_dict(model, optimizer)
    state_dict = {
        "model": model_state,
        "optimizer": optim_state,
    }
    dcp.load(state_dict, storage_reader=dcp.FileSystemReader(path))
    set_state_dict(model, optimizer, model_state, optim_state)
```

### 3. SRE 实战案例

#### 案例 1：NCCL hang 导致训练卡死

**背景**：一个 8 节点 64 卡的 LLaMA-70B 训练作业，使用 DP=8, TP=8 的并行策略。训练运行了 3 天后，step time 从稳定的 2.1s 突然停止推进。

**症状**：

```text
# 训练日志
[2026-05-01 03:14:22] Step 15230, loss: 1.847, step_time: 2.1s
[2026-05-01 03:14:24] Step 15231, loss: 1.845, step_time: 2.1s
[2026-05-01 03:14:26] Step 15232, loss: 1.843, step_time: 2.1s
# 日志在此处停止，没有任何新的输出
# GPU 利用率监控显示：
#   rank 0-7 (node0): GPU 利用率 0%，显存占用正常
#   rank 8-15 (node1): GPU 利用率 100%，显存占用正常
#   rank 16-63: GPU 利用率 0%，显存占用正常
```

**诊断步骤**：

第一步，确认是通信层 hang 而不是代码逻辑问题。检查各 rank 的日志发现 node1 的 8 个 rank 仍在计算，其他 rank 已经完成计算在等待 AllReduce。这说明某个 rank 提前进入了 collective 通信，但另一个 rank 没有按时参与。

第二步，启用 NCCL_DEBUG 收集详细日志：

```bash
# 重启作业，设置 NCCL 调试
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=ALL
export NCCL_TIMEOUT=300000  # 5 分钟超时
```

NCCL_DEBUG 输出关键信息：

```text
# node0 的 rank 0 日志
NCCL INFO AllReduce: opCount=15233 sendbuff=0x7f2a3c000000 recvbuff=0x7f2a3c000000 count=1048576
NCCL WARN NET/IB : Send to rank 8 timed out after 300000ms
NCCL ERROR misc/socket.cc:481 'Connection reset by peer' [node1:8]

# node1 的 rank 8 日志
NCCL INFO AllReduce: opCount=15232 sendbuff=0x7f3b4d000000 recvbuff=0x7f3b4d000000 count=1048576
NCCL WARN NET/IB : Send to rank 0 timed out after 300000ms
```

第三步，检查网络连通性：

```bash
# 在 node0 上测试到 node1 的 RDMA 连通性
ibping -S  # 在 node1 上启动 server
ibping -c 100 node1  # 从 node0 ping

# 检查网卡错误计数
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_rcv_errors
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_xmit_discards

# 检查交换机端口
show interfaces counters errors  # 交换机 CLI
```

发现 node0 到 node1 的 RDMA 链路存在间歇性丢包，`port_rcv_errors` 计数在持续增长。

第四步，检查 dmesg 系统日志：

```bash
dmesg | grep -i "mlx5\|infiniband\|error"
# [345678.123] mlx5_0:mlx5_0:1: CQE with error syndrome 0x05 (Work Request Flushed Error)
# [345678.456] mlx5_0:mlx5_0:1: CQE with error syndrome 0x0a (Remote Access Error)
```

**根因**：node0 的 ConnectX-7 网卡出现了硬件错误，导致 RDMA 通信间歇性失败。NCCL 的 AllReduce 操作在等待该网卡的响应时超时，但由于 NCCL 默认的超时时间较长（30 分钟），整个作业表现为"卡死"而非快速失败。

**修复过程**：

```bash
# 1. 隔离故障节点
kubectl cordon node0  # 标记节点不可调度

# 2. 终止当前卡死的作业
kubectl delete pod training-job-0  # 删除 node0 上的 pod

# 3. 重新调度作业（排除 node0）
# 修改调度器配置，将 node0 加入黑名单
kubectl label node node0 hardware-issue=mlx5-error

# 4. 作业自动重启，在 7 个健康节点 + 1 个新节点上恢复
# torchrun 的 --max_restarts=3 机制自动触发重启
# 加载最近的 checkpoint（15230 步），继续训练
```

**预防措施**：

1. **NCCL 健康检查**：在训练循环中定期检查 NCCL 通信状态
2. **自动隔离**：当 NCCL 错误率超过阈值时，自动将节点标记为不可用
3. **缩短超时**：将 NCCL_TIMEOUT 从默认 30 分钟缩短到 5 分钟，快速失败而非长时间卡死
4. **网络监控**：持续监控 RDMA 网卡的错误计数，在错误率上升时预警

```python
# NCCL 健康检查代码
import torch.distributed as dist

def check_nccl_health():
    """定期检查 NCCL 通信是否正常"""
    try:
        tensor = torch.ones(1).cuda()
        dist.all_reduce(tensor, timeout=timedelta(seconds=30))
        return tensor.item() == dist.get_world_size()
    except Exception as e:
        logger.error(f"NCCL health check failed: {e}")
        return False

# 在训练循环中每 100 步检查一次
if step % 100 == 0:
    if not check_nccl_health():
        logger.error("NCCL health check failed, initiating recovery")
        trigger_recovery()
```

#### 案例 2：Spot 实例被驱逐导致训练中断

**背景**：一个使用 Spot 实例的 16 节点 128 卡训练作业，checkpoint 间隔为每 30 分钟一次。凌晨 2:17 收到告警，训练作业失败，丢失了约 25 分钟的训练进度。

**症状**：

```text
# K8s events
2:17:03  Warning  Preempted    pod/training-job-12  Preempted by pod default/high-priority-job on node ip-10-0-5-23
2:17:03  Warning  Preempted    pod/training-job-8   Preempted by pod default/high-priority-job on node ip-10-0-5-19
2:17:05  Warning  Unhealthy    pod/training-job-0   Readiness probe failed: connection refused

# 训练日志
[2026-05-02 02:17:03] Rank 96: Caught SIGTERM, initiating graceful shutdown
[2026-05-02 02:17:03] Rank 97: Caught SIGTERM, initiating graceful shutdown
...
[2026-05-02 02:17:05] Rank 0: NCCL timeout waiting for ranks [96, 97, 98, 99, 100, 101, 102, 103]
[2026-05-02 02:17:35] Rank 0: Training failed after NCCL timeout
```

**诊断步骤**：

第一步，检查 K8s events 确认驱逐原因：

```bash
kubectl get events --sort-by='.lastTimestamp' | grep -i preempt
# 显示 4 个节点被更高优先级的作业抢占

kubectl describe node ip-10-0-5-23 | grep -A5 "Conditions"
# Spot interruption: true
```

第二步，确认 checkpoint 状态：

```bash
ls -la /checkpoints/llama-70b/
# drwxr-xr-x  2 root root 4096 May  2 01:47 step-14800  ← 最新 checkpoint
# drwxr-xr-x  2 root root 4096 May  2 01:17 step-14500
# 当前训练在 step 15100 左右，丢失了约 300 步（~25 分钟）的进度
```

第三步，分析驱逐时间线：

```text
时间线分析：
01:47:00  最后一次成功 checkpoint (step 14800)
01:47:00 - 02:17:03  正常训练，推进约 300 步
02:17:03  收到 SIGTERM（4 个节点被驱逐）
02:17:05  NCCL 超时，作业失败
02:17:05 - 02:20:00  等待 K8s 重新调度
02:20:00  新节点就位，开始恢复
02:25:00  从 checkpoint 14800 恢复训练
```

**根因**：云厂商回收了 4 个 Spot 节点用于高优先级作业。由于 checkpoint 间隔为 30 分钟，最近一次 checkpoint 在 25 分钟前，导致丢失了约 25 分钟的训练进度。此外，作业没有配置 SIGTERM 信号处理器来触发紧急 checkpoint。

**修复过程**：

```bash
# 1. 等待新节点调度（K8s 自动处理）
# 2. 确认新节点就位
kubectl get nodes -l node-type=spot

# 3. 重新启动训练作业（从最近 checkpoint 恢复）
torchrun \
    --nnodes=16 \
    --nproc_per_node=8 \
    --max_restarts=5 \
    train.py \
    --resume_from /checkpoints/llama-70b/step-14800

# 4. 验证恢复成功
# 确认 loss 曲线没有跳变，step time 正常
```

**预防措施**：

1. **缩短 checkpoint 间隔**：从 30 分钟缩短到 10 分钟
2. **紧急 checkpoint 机制**：收到 SIGTERM 后立即触发 checkpoint
3. **混合部署**：关键节点使用按需实例
4. **Spot 容量监控**：监控 Spot 实例可用性，在容量紧张时自动切换到按需实例

```python
# 紧急 checkpoint 信号处理器
import signal
import torch.distributed as dist

emergency_checkpoint_triggered = False

def sigterm_handler(signum, frame):
    """Spot 实例驱逐信号处理"""
    global emergency_checkpoint_triggered
    if not emergency_checkpoint_triggered:
        emergency_checkpoint_triggered = True
        rank = dist.get_rank()
        print(f"[Rank {rank}] 收到 SIGTERM，触发紧急 checkpoint")
        try:
            save_emergency_checkpoint()
            dist.barrier()  # 等待所有 rank 完成
        except Exception as e:
            print(f"[Rank {rank}] 紧急 checkpoint 失败: {e}")
        finally:
            sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)
```

## 💻 实战练习

### 练习 1：基础操作 -- 使用 torchrun 启动 DDP 训练

**目标**：理解 torchrun 的启动机制，观察 DDP 的梯度同步行为。

**步骤**：

1. 准备一个简单的训练脚本 `ddp_demo.py`：

```python
import os
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

def setup():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    torch.cuda.set_device(rank)
    return rank

def main():
    rank = setup()
    world_size = dist.get_world_size()

    # 简单模型
    model = nn.Linear(10, 10).cuda()
    model = DDP(model, device_ids=[rank])
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

    # 每个 rank 使用不同的数据
    for step in range(10):
        # 模拟不同 rank 看到不同数据
        x = torch.randn(32, 10).cuda() + rank
        y = model(x)
        loss = y.mean()
        loss.backward()

        # 打印梯度（验证 AllReduce 生效）
        grad_norm = model.module.weight.grad.norm().item()
        print(f"[Rank {rank}] Step {step}, loss={loss.item():.4f}, "
              f"grad_norm={grad_norm:.6f}")

        optimizer.step()
        optimizer.zero_grad()

    dist.destroy_process_group()

if __name__ == "__main__":
    main()
```

2. 使用 torchrun 启动：

```bash
# 单节点 4 卡
torchrun --nproc_per_node=4 ddp_demo.py

# 观察输出：不同 rank 的梯度在 AllReduce 后应该相同
```

3. 验证梯度同步：在 step 0，各 rank 的梯度在 backward 后不同（因为输入数据不同），但 AllReduce 后所有 rank 的梯度应该相同。

**预期结果**：

```text
[Rank 0] Step 0, loss=0.1234, grad_norm=0.567890
[Rank 1] Step 0, loss=0.2345, grad_norm=0.567890  ← 与 Rank 0 相同
[Rank 2] Step 0, loss=0.3456, grad_norm=0.567890  ← 与 Rank 0 相同
[Rank 3] Step 0, loss=0.4567, grad_norm=0.567890  ← 与 Rank 0 相同
```

### 练习 2：进阶场景 -- 配置 FSDP 并对比 ZeRO Stage 1/2/3

**目标**：理解不同 ZeRO Stage 的显存占用差异，学会配置 FSDP。

**步骤**：

1. 准备 FSDP 训练脚本 `fsdp_demo.py`：

```python
import os
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy
import functools

class LargeModel(nn.Module):
    def __init__(self, hidden_size=4096, num_layers=12):
        super().__init__()
        self.layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, hidden_size * 4),
                nn.GELU(),
                nn.Linear(hidden_size * 4, hidden_size),
            ) for _ in range(num_layers)
        ])
        self.output = nn.Linear(hidden_size, 1000)

    def forward(self, x):
        for layer in self.layers:
            x = x + layer(x)
        return self.output(x)

def get_memory_usage():
    """获取当前 GPU 显存使用情况"""
    return {
        "allocated": torch.cuda.memory_allocated() / 1024**3,  # GB
        "reserved": torch.cuda.memory_reserved() / 1024**3,    # GB
    }

def main():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    torch.cuda.set_device(rank)

    # 测试不同 ZeRO Stage
    strategies = {
        "Stage1_SHARD_GRAD_OP": ShardingStrategy.SHARD_GRAD_OP,
        "Stage2_SHARD_GRAD_OP": ShardingStrategy.SHARD_GRAD_OP,
        "Stage3_FULL_SHARD": ShardingStrategy.FULL_SHARD,
    }

    for name, strategy in strategies.items():
        model = LargeModel().cuda()
        model = FSDP(model, sharding_strategy=strategy)

        optimizer = torch.optim.Adam(model.parameters())

        # 前向 + 反向
        x = torch.randn(16, 4096).cuda()
        loss = model(x).sum()
        loss.backward()
        optimizer.step()

        mem = get_memory_usage()
        if rank == 0:
            print(f"{name}: allocated={mem['allocated']:.2f}GB, "
                  f"reserved={mem['reserved']:.2f}GB")

        del model, optimizer
        torch.cuda.empty_cache()

    dist.destroy_process_group()

if __name__ == "__main__":
    main()
```

2. 运行并观察显存差异：

```bash
torchrun --nproc_per_node=4 fsdp_demo.py
```

3. 记录并对比不同 Stage 的显存占用，验证 ZeRO Stage 3 的显存节省效果。

**预期结果**：Stage 3 的显存占用约为 Stage 1 的 1/3（因为 4 张 GPU 分片）。

### 练习 3：故障排查挑战 -- 模拟 NCCL hang

**目标**：体验 NCCL hang 的诊断过程，学会使用 NCCL_DEBUG 排查问题。

**步骤**：

1. 创建一个会触发 NCCL hang 的脚本 `nccl_hang_sim.py`：

```python
import os
import torch
import torch.distributed as dist
import time

def main():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    world_size = dist.get_world_size()

    # 正常训练循环
    for step in range(100):
        tensor = torch.ones(1024, 1024).cuda()

        if step == 50 and rank == 0:
            # 模拟 rank 0 在 step 50 时卡住（不参与 collective）
            print(f"[Rank 0] 模拟卡住，不参与 AllReduce")
            time.sleep(300)  # 等待 5 分钟
        else:
            dist.all_reduce(tensor)
            print(f"[Rank {rank}] Step {step} completed")

    dist.destroy_process_group()

if __name__ == "__main__":
    main()
```

2. 启动作业并观察 hang 现象：

```bash
# 启用 NCCL 调试
export NCCL_DEBUG=INFO
export NCCL_TIMEOUT=60000  # 60 秒超时

torchrun --nproc_per_node=2 nccl_hang_sim.py
```

3. 观察输出：在 step 50 时，rank 1 会打印等待 rank 0 的 NCCL 警告，最终超时失败。

4. 分析 NCCL_DEBUG 输出，识别以下关键信息：
   - 哪个 rank 没有参与 collective
   - 超时时间
   - 通信操作类型（AllReduce）

5. 思考解决方案：
   - 如何缩短超时时间，快速失败而非长时间等待
   - 如何实现自动检测 hang 并触发恢复
   - 如何在生产环境中配置 NCCL_TIMEOUT

## 🎯 面试题精选

### 题目 1：DDP vs FSDP 的区别和选型

**问题**：请对比 DDP 和 FSDP 的区别，以及在什么场景下选择哪种方案。

**参考答案**：

DDP（DistributedDataParallel）和 FSDP（FullyShardedDataParallel）的核心区别在于模型状态的存储方式。

DDP 中每个 rank 保存完整的模型参数、梯度和优化器状态，通过 AllReduce 同步梯度。优点是实现简单、通信模式固定（Ring AllReduce），缺点是显存冗余度高。对于 7B 模型，Adam 优化器需要约 120GB 显存（参数 14GB + 梯度 14GB + 优化器状态 ~84GB），单卡放不下。

FSDP 是 PyTorch 对 ZeRO 的实现，将模型状态分片到多个 GPU 上。Stage 2 分片优化器状态和梯度，Stage 3 还额外分片参数。优点是显存占用与 GPU 数量成反比，缺点是通信更复杂（需要 AllGather 临时收集参数），checkpoint 逻辑更复杂。

选型建议：
- 模型能放进单卡显存 → DDP（简单、高效）
- 模型放不进单卡但通信带宽充足 → FSDP Stage 2（显存和通信的平衡）
- 模型非常大、显存极度紧张 → FSDP Stage 3（最大显存节省）
- 需要跨节点训练且节点间带宽有限 → 考虑 TP + PP 组合而非纯 FSDP Stage 3

### 题目 2：ZeRO Stage 1/2/3 分别优化了什么

**问题**：详细解释 ZeRO 的三个阶段分别优化了什么，通信开销如何变化。

**参考答案**：

ZeRO（Zero Redundancy Optimizer）通过消除数据并行中的冗余存储来降低显存占用。

Stage 1（优化器状态分片）：每个 rank 只保存 1/N 的优化器状态（N 为 GPU 数量）。例如 Adam 优化器的 m 和 v 矩阵。梯度 AllReduce 后，每个 rank 只更新自己负责的那部分参数的优化器状态。通信量与 DDP 相同（AllReduce 梯度）。

Stage 2（优化器状态 + 梯度分片）：在 Stage 1 基础上，梯度也只保留 1/N。反向传播时，梯度通过 ReduceScatter 聚合到负责该参数的 rank，而不是 AllReduce 到所有 rank。通信量与 DDP 相同（ReduceScatter + AllGather 等价于 AllReduce）。

Stage 3（优化器状态 + 梯度 + 参数全部分片）：在 Stage 2 基础上，模型参数也只保存 1/N。前向传播时通过 AllGather 临时收集完整参数，用完后释放。反向传播时再次 AllGather 收集参数计算梯度，然后 ReduceScatter 分发梯度。通信量比 Stage 2 多约 50%（多了前向和反向的 AllGather）。

显存节省比例（N 个 GPU）：
- Stage 1：优化器状态从 N 份降到 1 份，节省约 4x
- Stage 2：优化器状态 + 梯度从 N 份降到 1 份，节省约 8x
- Stage 3：全部状态从 N 份降到 1 份，节省约 N * 3x

### 题目 3：TP vs PP 的适用场景

**问题**：Tensor Parallelism 和 Pipeline Parallelism 各自适用于什么场景？如何选择？

**参考答案**：

Tensor Parallelism（TP）将单层的计算切分到多张 GPU 上，例如将一个线性层的权重矩阵按列或行切分。每层的前向和反向传播都需要 AllReduce 或 AllGather 通信。

TP 的特点是通信频率极高（每层至少 2 次通信），但每次通信的数据量相对较小（激活值大小）。因此 TP 对通信延迟极其敏感，必须使用最低延迟的互联。在实践中，TP 几乎只在节点内使用（通过 NVLink/NVSwitch），跨节点 TP 的效率极差。

Pipeline Parallelism（PP）将模型按层分成多个阶段，每个阶段放在不同 GPU 上。通信只发生在相邻阶段之间，传递激活值和梯度。

PP 的特点是通信频率较低（每个 micro-batch 只需要相邻 stage 间通信），通信数据量也较小（只有激活值）。但 PP 引入了 pipeline bubble，即在流水线填充和排空阶段 GPU 会空闲。bubble 比例 ≈ (PP-1)/(PP+micro_batches-1)。

选型建议：
- 单层参数量非常大（如 175B 模型的某个 FFN 层）→ 必须用 TP
- 模型层数很多但单层不大 → 优先考虑 PP
- 节点内 NVLink 带宽充足 → TP 放节点内
- 节点间带宽有限 → PP 可以跨节点
- 实际大模型训练通常组合使用：TP 在节点内，PP 跨节点，DP 在最外层

### 题目 4：如何设计分布式训练的容错策略

**问题**：为一个 128 卡的 LLaMA-70B 训练作业设计容错策略，需要考虑哪些方面？

**参考答案**：

容错策略需要覆盖检测、恢复和预防三个层面。

**检测层面**：
- NCCL 超时机制：设置合理的 NCCL_TIMEOUT（建议 5-10 分钟），避免长时间卡死
- 健康检查：定期执行小规模 AllReduce 测试，验证通信链路正常
- Step time 监控：step time 突然增加可能预示着节点变慢或通信问题
- 节点健康：监控 GPU 温度、ECC 错误、网络丢包率

**恢复层面**：
- Checkpoint 策略：每 10-15 分钟保存一次，支持异步 checkpoint 减少阻塞
- 紧急 checkpoint：收到 SIGTERM（Spot 驱逐）时立即触发 checkpoint
- 自动重启：配置 torchrun --max_restarts=5，自动从最近 checkpoint 恢复
- RTO 评估：目标 RTO < 10 分钟，包括故障检测 + 调度 + checkpoint 加载

**预防层面**：
- 混合部署：关键节点（PP 首尾 stage）使用按需实例
- 冗余设计：如果使用 Spot 实例，确保有按需实例作为 fallback
- 版本管理：checkpoint 格式向前兼容，支持不同并行度恢复
- 故障注入：定期模拟节点故障、网络中断，验证容错机制有效性

### 题目 5：Checkpoint 策略如何平衡 RTO 和训练效率

**问题**：Checkpoint 间隔越短，RTO 越低，但会增加训练开销。如何找到平衡点？

**参考答案**：

平衡 checkpoint 策略需要量化两个成本：checkpoint 开销和故障重算成本。

**Checkpoint 开销**：每次 checkpoint 的时间 = 状态收集时间 + 写入存储时间。对于 70B 模型，同步 checkpoint 可能需要 5-10 分钟。如果每 10 分钟 checkpoint 一次，那么 10% 的训练时间用于 checkpoint。

**故障重算成本**：如果 checkpoint 间隔为 T，故障发生时平均丢失 T/2 的训练进度。重算成本 = T/2 * 每步训练成本。

**优化方案**：

1. **异步 checkpoint**：将阻塞时间从分钟级降到秒级，checkpoint 间隔可以更短
2. **增量 checkpoint**：只保存变化的部分，减少写入量
3. **本地盘中转**：先写本地 NVMe SSD，后台异步上传到共享存储
4. **分层 checkpoint**：关键状态（参数）高频保存，非关键状态（优化器）低频保存

**平衡点计算**：

假设训练总时长 H，checkpoint 间隔 T，单次 checkpoint 耗时 C，平均故障间隔 MTBF。
- checkpoint 总开销 = H/T * C
- 故障重算期望 = H/MTBF * T/2
- 总成本 = H/T * C + H/MTBF * T/2

对 T 求导，最优 T = sqrt(2 * C * MTBF)。

例如 C=5 分钟，MTBF=24 小时，最优 T ≈ 38 分钟。如果使用异步 checkpoint 将 C 降到 30 秒，最优 T ≈ 9 分钟。

### 题目 6：如何诊断 NCCL hang

**问题**：训练作业卡住不动，GPU 利用率下降，如何判断是 NCCL hang？

**参考答案**：

NCCL hang 的典型表现是训练停止推进，部分或全部 GPU 利用率下降到 0%，但作业没有退出。

诊断步骤：

1. **确认是否是通信层问题**：检查各 rank 的日志，看是否有 rank 提前退出或卡在某个 collective 操作。如果所有 rank 都在等待，说明是通信层 hang；如果某个 rank 已经退出但其他 rank 不知道，说明是错误处理机制问题。

2. **启用 NCCL_DEBUG**：设置 `NCCL_DEBUG=INFO`，查看 NCCL 的详细日志。关注 `timed out`、`connection reset`、`error` 等关键词。

3. **检查网络连通性**：使用 ibping 测试 RDMA 连通性，检查网卡错误计数（`/sys/class/infiniband/*/ports/*/counters/`），查看交换机端口错误。

4. **检查节点健康**：dmesg 查看内核错误，nvidia-smi 查看 GPU 状态，检查 ECC 错误。

5. **检查 NCCL 版本兼容性**：NCCL、CUDA、驱动、OFED 版本不匹配是常见根因。使用 NVIDIA 官方的版本矩阵进行验证。

6. **检查拓扑配置**：确认 rank 到 GPU 的映射是否合理，TP 组是否在同一节点内。

### 题目 7：Spot 实例训练如何保证训练进度不丢失

**问题**：使用 Spot 实例训练大模型，如何保证训练进度不因实例回收而大量丢失？

**参考答案**：

Spot 实例随时可能被回收（通常有 2 分钟预警），需要从 checkpoint、信号处理、弹性设计三个方面保障。

**Checkpoint 优化**：
- 缩短间隔到 10-15 分钟（按需实例可以 30-60 分钟）
- 使用异步 checkpoint，减少对训练的阻塞
- 先写本地 NVMe，后台上传到对象存储（S3/OSS）

**信号处理**：
- 注册 SIGTERM 处理器，收到驱逐信号后立即触发紧急 checkpoint
- 使用 `dist.barrier()` 等待所有 rank 完成保存
- 设置合理的超时，避免某个 rank 保存失败导致全局等待

**弹性设计**：
- 使用 torchelastic 支持节点数变化
- checkpoint 支持不同 world_size 加载（PyTorch DCP 原生支持）
- 设计降级策略：被驱逐后用更少节点继续训练（batch size 相应减小）

**混合部署**：
- 关键 rank（如 PP 的第一个和最后一个 stage）使用按需实例
- 中间 stage 可以使用 Spot 实例
- 配置 PodDisruptionBudget 限制同时被驱逐的节点数

### 题目 8：FSDP 的通信开销为什么比 DDP 大

**问题**：ZeRO Stage 3 的通信量比 DDP 多约 50%，这多出来的通信是什么？

**参考答案**：

DDP 的通信模式是：反向传播时 AllReduce 梯度。通信量 = 2 * (N-1)/N * 模型大小（Ring AllReduce 的通信量公式）。

FSDP Stage 3 的通信模式包含三个部分：
1. **前向传播**：每层计算前，AllGather 收集完整参数。通信量 ≈ 模型大小
2. **反向传播**：每层计算前，AllGather 再次收集完整参数。通信量 ≈ 模型大小
3. **梯度归约**：ReduceScatter 分发梯度到各 rank。通信量 ≈ 模型大小

总通信量 ≈ 3 * 模型大小，比 DDP 的 2 * 模型大小多 50%。

多出来的 1 * 模型大小来自前向传播时的 AllGather。DDP 中每个 rank 有完整参数，不需要通信；FSDP Stage 3 中参数是分片的，必须临时收集完整参数才能计算。

可以通过 `backward_prefetch=BackwardPrefetch.BACKWARD_PRE` 优化：在反向传播当前层时，提前 AllGather 下一层的参数，实现通信与计算重叠。但总通信量不会减少，只是隐藏了部分延迟。

### 题目 9：如何评估分布式训练的网络带宽需求

**问题**：训练一个 70B 模型，使用 DP=8, TP=8 的并行策略，如何评估网络带宽需求？

**参考答案**：

网络带宽需求取决于通信模式和通信量。

**TP 通信**（节点内 NVLink）：
- 每层前向 1 次 AllReduce，反向 1 次 AllReduce
- 每次通信量 = 2 * batch_size * seq_len * hidden_size * 2 bytes (FP16)
- 假设 batch=1, seq=2048, hidden=8192 → 每次约 64MB
- 70B 约 80 层，每步通信量 ≈ 80 * 2 * 64MB = 10GB
- 要求 NVLink 带宽 > 10GB / step_time

**DP 通信**（节点间 InfiniBand）：
- 每步 1 次 AllReduce 梯度
- 通信量 = 2 * 模型大小 = 2 * 140GB = 280GB（理论值，考虑 gradient accumulation 会减少）
- 如果 gradient accumulation = 8，实际每步通信量 = 280GB / 8 = 35GB
- 要求 IB 带宽 > 35GB / step_time

**实际计算**：
假设目标 step_time = 3 秒：
- TP 需要 NVLink 带宽 > 10GB / 3s ≈ 3.3 GB/s（NVLink 4.0 提供 450 GB/s，完全满足）
- DP 需要 IB 带宽 > 35GB / 3s ≈ 11.7 GB/s（单条 400Gbps IB ≈ 50 GB/s，满足）

如果节点间使用多条 IB 链路（如 4 条 400Gbps），总带宽约 200 GB/s，可以支撑更高的并行度。

### 题目 10：分布式训练中如何处理 straggler 问题

**问题**：分布式训练中某个节点明显比其他节点慢（straggler），导致整体 step time 被拖慢，如何处理？

**参考答案**：

Straggler 是分布式训练中最常见的性能问题之一，因为 AllReduce 需要所有 rank 同步，一个慢节点拖慢全局。

**检测**：
- 监控每个 rank 的 step time，识别明显高于平均值的 rank
- 使用 PyTorch Profiler 分析每个 rank 的计算和通信耗时
- 监控 GPU 利用率和显存带宽，识别性能下降的节点

**常见原因**：
- **硬件问题**：GPU 降频（温度过高）、ECC 错误、NVLink 错误
- **网络问题**：某个节点的 IB 链路丢包、交换机端口拥塞
- **软件问题**：某个 rank 的数据加载慢（CPU 瓶颈）、NUMA 配置不当
- **资源竞争**：多租户环境下资源争抢

**处理策略**：

1. **隔离故障节点**：将 straggler 节点标记为不可用，作业自动迁移到健康节点
2. **梯度累积**：增加 gradient accumulation steps，减少 AllReduce 频率
3. **异步训练**：使用异步 SGD（但会影响收敛性）
4. **慢节点检测与驱逐**：在训练循环中定期检测 straggler，自动驱逐并重新 rendezvous

```python
# Straggler 检测示例
def detect_straggler(step_times, threshold=1.5):
    """检测 step time 超过平均值 threshold 倍的 rank"""
    avg_time = sum(step_times) / len(step_times)
    stragglers = [i for i, t in enumerate(step_times)
                  if t > avg_time * threshold]
    return stragglers
```

## 📚 深入阅读

### 官方文档

- [PyTorch FSDP 官方文档](https://pytorch.org/tutorials/intermediate/FSDP_tutorial.html) -- FSDP 的完整使用指南
- [PyTorch Distributed Checkpoint](https://pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html) -- DCP 的使用方法和最佳实践
- [NCCL 文档](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/) -- NCCL 环境变量和调试方法
- [torchrun 文档](https://pytorch.org/docs/stable/elastic/run.html) -- torchrun 启动器的完整参数说明

### 论文

- [ZeRO: Memory Optimizations Toward Training Trillion Parameter Models](https://arxiv.org/abs/1910.02054) -- ZeRO 的原始论文，详细解释三个阶段的原理
- [Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism](https://arxiv.org/abs/1909.08053) -- Megatron-LM 的 TP 实现
- [GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism](https://arxiv.org/abs/1811.06965) -- Pipeline Parallelism 的原始论文
- [PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel](https://arxiv.org/abs/2304.11277) -- PyTorch FSDP 的设计和实践经验

### 工程实践

- [NVIDIA Megatron-LM](https://github.com/NVIDIA/Megatron-LM) -- 大模型训练的参考实现
- [DeepSpeed](https://github.com/microsoft/DeepSpeed) -- 微软的分布式训练框架，ZeRO 的原始实现
- [torchtitan](https://github.com/pytorch/torchtitan) -- PyTorch 官方的大模型训练示例

### 相关文档

- [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) -- GPU 集群架构与调度
- [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) -- LLM 生命周期总览
- [02-glossary.md](./02-glossary.md) -- 术语表

## ✅ 自检清单

完成本篇学习后，检查自己是否能够回答以下问题：

**概念理解**：
- [ ] 能画出 DDP 的 AllReduce 通信模式，并解释 Ring AllReduce 的通信量公式
- [ ] 能解释 ZeRO Stage 1/2/3 分别分片了什么，通信开销如何变化
- [ ] 能说明 TP 为什么必须放在节点内，PP 为什么可以跨节点
- [ ] 能解释 FSDP 前向传播时为什么要 AllGather 参数

**工程能力**：
- [ ] 能使用 torchrun 启动多节点分布式训练作业
- [ ] 能配置 FSDP 的 sharding_strategy、mixed_precision、auto_wrap_policy
- [ ] 能使用 PyTorch DCP 保存和加载分布式 checkpoint
- [ ] 能配置 NCCL 环境变量进行调试和调优

**故障排查**：
- [ ] 能通过 NCCL_DEBUG 日志判断 NCCL hang 的根因
- [ ] 能诊断 Spot 实例驱逐导致的训练中断，并设计恢复方案
- [ ] 能识别 straggler 节点并给出隔离/修复方案
- [ ] 能评估 checkpoint 策略的 RTO 和训练效率平衡

**设计能力**：
- [ ] 能为大模型训练设计混合并行策略（DP + TP + PP）
- [ ] 能为 Spot 实例场景设计弹性容错方案
- [ ] 能设计 checkpoint 策略，平衡保存频率和训练效率
- [ ] 能评估分布式训练的网络带宽需求和 RTO 目标
