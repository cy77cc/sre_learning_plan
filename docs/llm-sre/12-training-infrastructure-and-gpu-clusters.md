# LLM SRE 12：训练基础设施与 GPU 集群

> 📅 日期：2026-05-03
> 📖 学习主题：GPU 集群架构、调度、存储与资源隔离
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Kubernetes 基础、Linux 网络、容器技术

## 🎯 学习目标

完成本篇学习后，你应该能够：

- 画出 GPU 集群的硬件拓扑图（节点内 NVLink + 节点间 InfiniBand/RoCE），并解释每个组件的作用
- 解释 NVIDIA 驱动 / CUDA / NCCL / OFED 版本矩阵的依赖关系，并说明版本不匹配会导致什么故障
- 对比 K8s 和 Slurm 在训练场景的适用边界，能根据业务需求做出合理选型
- 诊断常见的 GPU 集群故障（NCCL hang、checkpoint 超时、节点驱逐），并给出完整的排查链路
- 使用 nvidia-smi、DCGM、NCCL 环境变量等工具完成日常巡检与调优
- 设计一套面向多租户训练集群的资源隔离与监控告警方案

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 GPU 硬件架构

##### NVIDIA GPU 架构演进

理解 GPU 集群的第一步是了解 GPU 本身。NVIDIA 的数据中心 GPU 经历了几代关键演进：

| 架构 | 代表产品 | 显存 | 互联带宽 | 关键特性 |
|------|---------|------|---------|---------|
| Ampere | A100 80GB | 80GB HBM2e | 600 GB/s NVLink | 第三代 Tensor Core, MIG |
| Hopper | H100 80GB | 80GB HBM3 | 900 GB/s NVLink | 第四代 Tensor Core, FP8, Transformer Engine |
| Blackwell | B100/B200 | 192GB HBM3e | 1800 GB/s NVLink | 第五代 Tensor Core, 双芯封装 |

每一代架构的演进不只是算力提升，更重要的是显存容量和互联带宽的跃升。训练大型语言模型时，显存决定了单卡能承载的模型规模，互联带宽决定了多卡并行的通信效率。

##### NVLink 与 NVSwitch 拓扑

NVLink 是 NVIDIA 的 GPU 直连互联技术，相比 PCIe 有显著的带宽优势：

```
NVLink vs PCIe 带宽对比 (H100 为例):
┌─────────────────────────────────────────────────────────────┐
│                    单向带宽 (GB/s)                            │
│                                                              │
│  PCIe Gen5 x16    ████████ 32 GB/s                          │
│                                                              │
│  NVLink 4.0       ██████████████████████████████████ 450 GB/s│
│  (单条链路)                                                    │
│                                                              │
│  NVLink 4.0       ██████████████████████████████████████     │
│  (全部18条链路)                           900 GB/s (双向)      │
└─────────────────────────────────────────────────────────────┘
```

NVSwitch 则是实现节点内所有 GPU 全互联的关键芯片。在 8 卡 H100 节点中，通常使用 4 颗 NVSwitch 实现全连接拓扑，任意两块 GPU 之间都能获得相同的高带宽。

##### 节点内 GPU 拓扑图

以下是典型 8 卡 H100 节点的内部拓扑：

```
                    ┌─────────────────────────────────────────────┐
                    │              8-GPU H100 Node                 │
                    │                                              │
                    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
                    │  │ GPU 0  │ │ GPU 1  │ │ GPU 2  │ │ GPU 3  ││
                    │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘│
                    │      │NVLink    │NVLink    │NVLink    │NVLink│
                    │  ┌───┴──────────┴──────────┴──────────┴───┐  │
                    │  │           NVSwitch 0 + NVSwitch 1       │  │
                    │  └───┬──────────┬──────────┬──────────┬───┘  │
                    │      │NVLink    │NVLink    │NVLink    │NVLink│
                    │  ┌───┴────┐ ┌───┴────┐ ┌───┴────┐ ┌───┴────┐│
                    │  │ GPU 4  │ │ GPU 5  │ │ GPU 6  │ │ GPU 7  ││
                    │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘│
                    │      │          │          │          │      │
                    │  ┌───┴──────────┴──────────┴──────────┴───┐  │
                    │  │              PCIe Gen5 Switch           │  │
                    │  └───┬──────────┬──────────┬──────────┬───┘  │
                    │      │          │          │          │      │
                    │  ┌───┴────┐ ┌───┴────┐ ┌───┴────┐ ┌───┴────┐│
                    │  │ NIC 0  │ │ NIC 1  │ │ NVMe   │ │ NVMe   ││
                    │  │(RDMA)  │ │(RDMA)  │ │  SSD   │ │  SSD   ││
                    │  └────────┘ └────────┘ └────────┘ └────────┘│
                    │                                              │
                    │  ┌────────────────────────────────────────┐  │
                    │  │              CPU 0 + CPU 1              │  │
                    │  │         (双路 Intel/AMD EPYC)           │  │
                    │  │              DDR5 内存                   │  │
                    │  └────────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
```

GPU 到 NIC 的距离对训练性能影响很大。理想情况下，每块 GPU 应该有对应的 RDMA NIC，通过 PCIe 直连同一颗 CPU，避免跨 NUMA 访问。SRE 在做资产登记时，需要记录每块 GPU 对应的 NIC 和 NUMA 节点。

##### InfiniBand vs RoCE 网络

跨节点通信是分布式训练的瓶颈所在。两种主流的 RDMA 网络方案对比如下：

```
┌─────────────────────────────────────────────────────────────┐
│                 InfiniBand vs RoCE 对比                      │
├──────────────────┬───────────────────────────────────────────┤
│                  │  InfiniBand          │  RoCE v2           │
├──────────────────┼──────────────────────┼────────────────────┤
│  协议栈           │  专用IB协议           │  以太网 + RDMA      │
│  代际带宽         │  NDR 400G / XDR 800G │  400GbE / 800GbE   │
│  延迟             │  ~0.6 μs             │  ~1.5 μs           │
│  拥塞控制         │  自适应路由           │  ECN + PFC         │
│  管理工具         │  OpenSM / UFM        │  标准交换机管理      │
│  成本             │  高（专用设备）        │  中（复用以太网）    │
│  典型规模         │  万卡级集群           │  千卡级集群         │
│  适用场景         │  超大规模训练         │  中等规模+混合负载   │
└──────────────────┴──────────────────────┴────────────────────┘
```

对于万卡以上规模的训练集群，InfiniBand 通常是首选，因为其自适应路由和原生 RDMA 支持能在大规模 all-reduce 中提供更稳定的尾延迟。RoCE 在中等规模集群中是更具性价比的选择，但需要仔细配置 ECN 和 PFC 来避免以太网丢包导致的 RDMA 重传。

##### HBM 显存架构

HBM（High Bandwidth Memory）是数据中心 GPU 的显存技术：

```
HBM 演进:
┌──────────────────────────────────────────────────────┐
│  HBM2e (A100)    HBM3 (H100)    HBM3e (B200)        │
│  ─────────────   ─────────────  ─────────────────    │
│  带宽: 2 TB/s    带宽: 3.35 TB/s  带宽: 8 TB/s       │
│  容量: 80 GB     容量: 80 GB      容量: 192 GB        │
│  堆叠: 5-Hi      堆叠: 5-Hi       堆叠: 8-Hi         │
│  接口: 5120-bit  接口: 5120-bit   接口: 8192-bit      │
└──────────────────────────────────────────────────────┘
```

显存容量直接决定了单卡能训练的模型大小。以 70B 参数模型为例，使用 FP16 训练时仅权重就需要 140GB 显存，加上优化器状态和激活值，至少需要 4 张 H100（使用 ZeRO-3 分片）。HBM 带宽则影响计算单元能否被充分利用——如果显存带宽不足，Tensor Core 会因为等待数据而空转。

---

#### 1.2 软件栈

##### 软件栈层次图

GPU 训练平台的软件栈层次关系如下：

```
┌──────────────────────────────────────────────────────────────┐
│                     应用层                                     │
│  ┌──────────┐  ┌───────────┐  ┌─────────────┐                │
│  │ PyTorch   │  │DeepSpeed  │  │ Megatron-LM │                │
│  └─────┬────┘  └─────┬─────┘  └──────┬──────┘                │
│        │             │               │                        │
│  ┌─────┴─────────────┴───────────────┴──────┐                │
│  │              分布式通信层                    │                │
│  │    NCCL (NVIDIA Collective Communications) │                │
│  └─────────────────┬────────────────────────┘                │
│                    │                                          │
│  ┌─────────────────┴────────────────────────┐                │
│  │           RDMA/网络层                      │                │
│  │    OFED / libibverbs / RDMA Core          │                │
│  └─────────────────┬────────────────────────┘                │
│                    │                                          │
│  ┌─────────────────┴────────────────────────┐                │
│  │           CUDA 运行时                      │                │
│  │    CUDA Toolkit (cuda-runtime)            │                │
│  │    cuDNN / cuBLAS / TensorRT              │                │
│  └─────────────────┬────────────────────────┘                │
│                    │                                          │
│  ┌─────────────────┴────────────────────────┐                │
│  │           内核驱动层                        │                │
│  │    NVIDIA Driver (nvidia.ko)              │                │
│  └─────────────────┬────────────────────────┘                │
│                    │                                          │
│  ┌─────────────────┴────────────────────────┐                │
│  │           容器运行时                        │                │
│  │    NVIDIA Container Toolkit (nvidia-ctk)  │                │
│  └──────────────────────────────────────────┘                │
│                                                              │
│  ┌──────────────────────────────────────────┐                │
│  │           操作系统 & 内核                   │                │
│  │    Linux Kernel / IOMMU / VFIO            │                │
│  └──────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

##### 版本依赖链

这是训练平台最常见也最容易出问题的部分。各组件之间存在严格的版本依赖：

```
NVIDIA Driver (≥535)
    │
    ├── CUDA Runtime (12.x) ──── 必须 ≤ Driver 支持的最高版本
    │       │
    │       ├── cuDNN (≥8.9) ──── 必须匹配 CUDA 版本
    │       │
    │       └── NCCL (≥2.18) ──── 必须匹配 CUDA 版本
    │               │
    │               └── libnccl.so ──── 编译时和运行时版本必须一致
    │
    └── NVIDIA Container Toolkit
            │
            └── 容器内 CUDA 版本 ≤ 宿主机 Driver 支持的最高版本

OFED/MOFED (≥5.8)
    │
    ├── libibverbs ──── NCCL 使用 RDMA 时必须存在
    │
    └── 内核模块 ──── 必须与宿主机内核版本兼容
```

常见的版本不兼容故障包括：

1. 容器内 CUDA 12.4 + 宿主机 Driver 525 → Driver 版本过低，无法支持 CUDA 12.4
2. NCCL 2.18 编译时链接 CUDA 12.2，运行时加载 CUDA 12.4 的 libcudart → 符号解析失败
3. 容器内缺少 OFED 用户态库 → NCCL 退回到 TCP 通信，性能下降 10 倍以上

---

#### 1.3 调度系统

##### Kubernetes + NVIDIA 生态

在 Kubernetes 上运行 GPU 训练作业，需要以下组件协同工作：

```
┌──────────────────────────────────────────────────────────────┐
│                    Kubernetes GPU 调度架构                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                   控制面                               │    │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ API Server │  │  Scheduler   │  │  Controller  │  │    │
│  │  │            │  │  (拓扑感知)   │  │   Manager    │  │    │
│  │  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘  │    │
│  └────────┼────────────────┼─────────────────┼──────────┘    │
│           │                │                 │               │
│  ┌────────┴────────────────┴─────────────────┴──────────┐    │
│  │                   工作节点 (GPU Node)                  │    │
│  │                                                       │    │
│  │  ┌─────────────────────────────────────────────────┐  │    │
│  │  │           NVIDIA GPU Operator                    │  │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │  │    │
│  │  │  │ Device   │ │  NVIDIA  │ │   DCGM           │ │  │    │
│  │  │  │ Plugin   │ │  Driver  │ │   Exporter       │ │  │    │
│  │  │  └──────────┘ └──────────┘ └──────────────────┘ │  │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │  │    │
│  │  │  │  MIG     │ │ Validator│ │   Node Feature   │ │  │    │
│  │  │  │ Manager  │ │          │ │   Discovery      │ │  │    │
│  │  │  └──────────┘ └──────────┘ └──────────────────┘ │  │    │
│  │  └─────────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │    │
│  │  │ Pod:     │ │ Pod:     │ │ Pod:     │ │ Pod:     │ │    │
│  │  │ Train    │ │ Train    │ │ Infer    │ │ Monitor  │ │    │
│  │  │ Job 0    │ │ Job 1    │ │ Service  │ │ Agent    │ │    │
│  │  │ GPU 0-3  │ │ GPU 4-7  │ │ GPU MIG  │ │          │ │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │    │
│  └───────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

关键组件说明：

- **NVIDIA Device Plugin**：向 K8s 暴露 GPU 资源，使调度器能感知 `nvidia.com/gpu` 资源数量
- **NVIDIA GPU Operator**：自动化管理节点上的驱动、CUDA、DCGM 等全套组件
- **拓扑感知调度器**（Topology Manager）：确保 Pod 内的 GPU 之间通过 NVLink 直连，而不是跨 PCIe 桥
- **Node Feature Discovery**：自动发现并标记节点的 GPU 型号、NVLink 拓扑等硬件特征

##### Slurm 在大规模训练中的角色

Slurm 是 HPC 领域最成熟的调度系统，在大规模训练场景中有独特优势：

```
┌──────────────────────────────────────────────────────────────┐
│                     Slurm 调度架构                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              slurmctld (控制守护进程)                   │    │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ 作业队列    │  │  分区管理     │  │  资源记账     │  │    │
│  │  └────────────┘  └──────────────┘  └──────────────┘  │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐    │
│  │              slurmd (节点守护进程)                      │    │
│  │                                                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│  │  │ Node 0   │  │ Node 1   │  │ Node N   │            │    │
│  │  │ 8x GPU   │  │ 8x GPU   │  │ 8x GPU   │            │    │
│  │  │ GRES:8   │  │ GRES:8   │  │ GRES:8   │            │    │
│  │  └──────────┘  └──────────┘  └──────────┘            │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                              │
│  提交作业:                                                    │
│  $ srun --gpus-per-node=8 --nodes=4 --ntasks-per-node=8 \    │
│         --partition=train python train.py                    │
└──────────────────────────────────────────────────────────────┘
```

Slurm 的核心优势：

- **原生 GRES 调度**：GPU 作为 Generic Resource 直接调度，无需额外插件
- **分区（Partition）管理**：天然支持节点池隔离，可按 GPU 型号、用途划分
- **作业抢占**：支持基于优先级的作业抢占，适合多租户环境
- **裸机性能**：无容器开销，适合对性能极度敏感的场景

---

#### 1.4 存储与 Checkpoint

##### 集群存储架构

训练集群通常需要三层存储架构：

```
┌──────────────────────────────────────────────────────────────┐
│                    训练集群存储架构                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                 热数据层                               │    │
│  │    本地 NVMe SSD (每个节点 4-8 块 NVMe)               │    │
│  │    用途: 训练数据缓存、临时 checkpoint                  │    │
│  │    带宽: 7-14 GB/s (单节点)                           │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │ NFS/TCP                            │
│  ┌──────────────────────┴───────────────────────────────┐    │
│  │                 温数据层                               │    │
│  │    并行文件系统 (Lustre / GPFS / Weka)                │    │
│  │    用途: 训练数据集、checkpoint、共享代码               │    │
│  │    带宽: 100+ GB/s (聚合)                             │    │
│  │    特点: 高吞吐、POSIX 兼容、分布式元数据               │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │ S3 API                             │
│  ┌──────────────────────┴───────────────────────────────┐    │
│  │                 冷数据层                               │    │
│  │    对象存储 (S3 / MinIO)                              │    │
│  │    用途: 模型制品归档、数据集长期存储                    │    │
│  │    带宽: 取决于网络和节点数                             │    │
│  │    特点: 无限容量、低成本、最终一致性                    │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

##### Checkpoint I/O 优化

Checkpoint 写入是训练平台存储的最大挑战。一次 70B 模型的 checkpoint 可能达到 200-300GB，如果 100 个作业同时写入，会对存储系统产生巨大压力。

优化策略包括：

1. **异步 Checkpoint**：在后台线程写入，不阻塞训练
2. **分布式 Checkpoint**：每个 rank 只写自己的分片，避免单点瓶颈
3. **增量 Checkpoint**：只写变化的部分（需要框架支持）
4. **I/O 调度**：错峰写入，避免所有作业同时 checkpoint
5. **分级存储**：先写本地 NVMe，再异步同步到共享存储

---

### 2. 命令/工具详解

#### 2.1 nvidia-smi 详解

`nvidia-smi` 是 GPU 管理的基础工具。以下是常用命令和输出解读：

```bash
# 查看所有 GPU 的基本状态
$ nvidia-smi

+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03   Driver Version: 535.129.03   CUDA Version: 12.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA H100 80GB HBM3  On   | 00000000:1A:00.0 Off |                    0 |
| N/A   32C    P0    70W / 700W |      0MiB / 81559MiB |      0%      Default |
|                               |                      |             Disabled |
+-------------------------------+----------------------+----------------------+
|   1  NVIDIA H100 80GB HBM3  On   | 00000000:1B:00.0 Off |                    0 |
| N/A   35C    P0    72W / 700W |      0MiB / 81559MiB |      0%      Default |
|                               |                      |             Disabled |
+-------------------------------+----------------------+----------------------+

+-----------------------------------------------------------------------------+
| Processes:                                                                  |
|  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
|        ID   ID                                                   Usage       |
|=============================================================================|
|  No running processes found                                                  |
+-----------------------------------------------------------------------------+
```

输出字段解读：

- **Driver Version / CUDA Version**：宿主机驱动和 CUDA 版本，是排查兼容性问题的第一步
- **Temp**：GPU 核心温度，正常工作范围 30-85°C，超过 90°C 触发降频
- **Pwr:Usage/Cap**：当前功耗 / 最大功耗，H100 最大 700W
- **Memory-Usage**：显存使用量，训练时应接近满载但不触发 OOM
- **GPU-Util**：GPU 计算单元利用率，训练时应持续 90%+，突然降到 0% 说明有问题

```bash
# 持续监控（每 2 秒刷新）
$ nvidia-smi -l 2

# 只查询特定字段
$ nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv

# 输出示例
index, name, temperature.gpu, utilization.gpu, utilization.memory, memory.used, memory.total, power.draw
0, NVIDIA H100 80GB HBM3, 42, 95, 78, 63245, 81559, 580.32
1, NVIDIA H100 80GB HBM3, 44, 96, 80, 64123, 81559, 592.18
2, NVIDIA H100 80GB HBM3, 41, 94, 76, 62890, 81559, 575.64
3, NVIDIA H100 80GB HBM3, 43, 97, 82, 65234, 81559, 601.45

# 查看 GPU 拓扑（NVLink 连接关系）
$ nvidia-smi topo -m

        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    PIX     PIX
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    PIX     PIX
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    PIX     PIX
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    PIX     PIX
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    PIX     PIX
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      PIX     PIX
NIC0    PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX      X      PHB
NIC1    PIX     PIX     PIX     PIX     PIX     PIX     PIX     PIX     PHB      X

Legend:
  X    = Self
  NV18 = NVLink 18 lanes (900 GB/s)
  PIX  = Connected through PCIe switch
  PHB  = Connected through PCIe host bridge
  SYS  = Connected through PCIe across NUMA nodes
```

拓扑输出中，`NV18` 表示两块 GPU 之间有 18 条 NVLink 链路（900 GB/s 双向带宽），这是最佳连接方式。如果看到 `SYS`，说明两块 GPU 跨 NUMA 节点，通信性能会大幅下降。

```bash
# 查看 Xid 错误（GPU 硬件/驱动错误）
$ nvidia-smi -q | grep -A 5 "Xid"

        Xid Errors
            Count       : 0

# 查看 ECC 错误
$ nvidia-smi -q | grep -A 10 "ECC Mode"

ECC Mode
    Current                     : Enabled
    Pending                     : Enabled

ECC Errors
    Volatile
        SRAM Correctable      : 0
        SRAM Uncorrectable    : 0
        DRAM Correctable      : 2
        DRAM Uncorrectable    : 0
    Aggregate
        SRAM Correctable      : 15
        SRAM Uncorrectable    : 0
        DRAM Correctable      : 128
        DRAM Uncorrectable    : 0
```

ECC 错误是 GPU 健康的关键指标。`Uncorrectable` 错误意味着数据损坏，需要立即隔离节点。`Correctable` 错误如果突然增加，通常预示硬件老化。

#### 2.2 DCGM 诊断工具

NVIDIA DCGM（Data Center GPU Manager）是专为数据中心设计的 GPU 管理和监控工具：

```bash
# 安装 DCGM（通常通过 GPU Operator 自动部署）
$ apt-get install -y datacenter-gpu-manager

# 运行完整诊断
$ dcgmi diag -r 3

===============================
DCGM 3.3.6 Diagnostic
===============================
GPU 0: NVIDIA H100 80GB HBM3 [PCIe 0000:1a:00.0]
  Skipped: No firmware version to check.
  Skipping NVML library check.
  Software          : PASS
  Memory            : PASS
  Diagnostic        : PASS
  SM Stress         : PASS
  PCIe              : PASS
  Memory Bandwidth  : PASS
  Targeted Stress   : PASS
  NVLink            : PASS

GPU 1: NVIDIA H100 80GB HBM3 [PCIe 0000:1b:00.0]
  ...
===============================
Diagnostic Results:
   8 GPUs processed.
   All GPUs passed.
===============================
```

诊断级别说明：

- **Level 1**（快速）：检查基本功能，耗时约 30 秒
- **Level 2**（中等）：增加显存和 PCIe 测试，耗时约 2 分钟
- **Level 3**（完整）：包含压力测试和 NVLink 验证，耗时约 10 分钟

```bash
# 查看 GPU 活跃进程
$ dcgmi proc -l

+---------+-----------+------------------------------------------+
| GPU ID  | PID       | Process Name                             |
+---------+-----------+------------------------------------------+
| 0       | 12345     | python                                    |
| 0       | 12346     | python                                    |
| 1       | 12347     | python                                    |
+---------+-----------+------------------------------------------+

# 实时监控 GPU 指标
$ dmon -e POWER,TEMP,SM,SMCLK,MEMCLK,FB,GPUPC

# 输出:
# Entity  POWER   TEMP    SM      SMCLK   MEMCLK  FB      GPUPC
# GPU 0   580W    42C     95%     1980MHz 2619MHz 63245MiB 95%
# GPU 1   592W    44C     96%     1980MHz 2619MHz 64123MiB 96%

# 导出 Prometheus 指标格式（DCGM Exporter）
$ curl -s http://localhost:9400/metrics | head -20

# HELP DCGM_FI_DEV_GPU_UTIL GPU utilization
# TYPE DCGM_FI_DEV_GPU_UTIL gauge
DCGM_FI_DEV_GPU_UTIL{gpu="0",UUID="GPU-xxxx",container="",namespace="",pod=""} 95
DCGM_FI_DEV_GPU_UTIL{gpu="1",UUID="GPU-xxxx",container="",namespace="",pod=""} 96

# HELP DCGM_FI_DEV_FB_USED Framebuffer memory used (in MiB)
# TYPE DCGM_FI_DEV_FB_USED gauge
DCGM_FI_DEV_FB_USED{gpu="0",UUID="GPU-xxxx",container="",namespace="",pod=""} 63245
```

DCGM Exporter 是将 GPU 指标暴露给 Prometheus 的标准方式。以下是关键指标清单：

| 指标名 | 含义 | 告警阈值建议 |
|--------|------|-------------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 计算利用率 | 训练时 < 80% 持续 10 分钟 |
| `DCGM_FI_DEV_FB_USED` | 显存使用量 | > 95% 最大容量 |
| `DCGM_FI_DEV_GPU_TEMP` | GPU 温度 | > 85°C |
| `DCGM_FI_DEV_POWER_USAGE` | 功耗 | > 650W (H100) |
| `DCGM_FI_DEV_ECC_SBE_VOL` | 可纠正 ECC 错误 | 突增 > 100/小时 |
| `DCGM_FI_DEV_ECC_DBE_VOL` | 不可纠正 ECC 错误 | 任何 > 0 |
| `DCGM_FI_DEV_XID_ERRORS` | Xid 错误 | 任何 > 0 |
| `DCGM_FI_DEV_NVLINK_CRC_FLIT` | NVLink CRC 错误 | 突增 |

#### 2.3 NCCL 环境变量调优

NCCL（NVIDIA Collective Communications Library）是多 GPU / 多节点训练的核心通信库。通过环境变量可以精细调优其行为：

```bash
# 常用 NCCL 调优环境变量

# 指定通信后端（IB=InfiniBand, NET=Socket）
export NCCL_IB_DISABLE=0          # 启用 InfiniBand（默认）
export NCCL_NET=IB                # 强制使用 IB 后端

# 指定使用的网络接口
export NCCL_IB_HCA=mlx5_0,mlx5_1  # 指定 IB HCA 设备
export NCCL_SOCKET_IFNAME=eth0     # Socket 通信的网络接口

# 调试和日志
export NCCL_DEBUG=INFO             # 日志级别: VERSION/WARN/INFO/DEBUG/TRACE
export NCCL_DEBUG_SUBSYS=ALL       # 子系统: INIT/GRAPH/NET/ALL
export NCCL_DEBUG_FILE=/tmp/nccl_%h_%p.log  # 日志输出到文件

# 性能调优
export NCCL_ALGO=Ring              # 算法: Ring/Tree/Collnet
export NCCL_PROTO=Simple           # 协议: Simple/LL/LL128
export NCCL_MIN_NCHANNELS=4        # 最小通道数
export NCCL_MAX_NCHANNELS=16       # 最大通道数
export NCCL_BUFFSIZE=8388608       # 缓冲区大小 (bytes)

# 跨节点通信
export NCCL_IB_GID_INDEX=3         # RoCE GID 索引
export NCCL_IB_TC=136              # InfiniBand Traffic Class
export NCCL_IB_TIMEOUT=22          # IB 超时（2^22 微秒）
export NCCL_IB_RETRY_CNT=7         # IB 重试次数
```

```bash
# 运行时检查 NCCL 版本和配置
$ python -c "import torch; print(torch.cuda.nccl.version())"
(2, 18, 5)

# 验证 NCCL 是否使用 RDMA
$ NCCL_DEBUG=INFO python -c "
import torch
import torch.distributed as dist
dist.init_process_group('nccl')
t = torch.ones(1024, device='cuda')
dist.all_reduce(t)
print('NCCL all_reduce OK')
" 2>&1 | grep -E "(NET|IB|Using)"

# 期望输出:
# NCCL INFO NET/IB : Using [0] mlx5_0:1/RoCE
# NCCL INFO Using network IB
```

#### 2.4 Kubernetes GPU 调度命令

```bash
# 查看集群 GPU 资源
$ kubectl get nodes -o custom-columns=\
  NAME:.metadata.name,\
  GPU:.status.allocatable.nvidia\\.com/gpu,\
  GPU_MODEL:.metadata.labels.nvidia\\.com/gpu\.product

# 输出:
# NAME          GPU   GPU_MODEL
# gpu-node-01   8     NVIDIA-H100-80GB-HBM3
# gpu-node-02   8     NVIDIA-H100-80GB-HBM3
# gpu-node-03   8     NVIDIA-A100-80GB-PCIE

# 查看 GPU 调度情况
$ kubectl describe node gpu-node-01 | grep -A 20 "Allocated resources"

# Allocated resources:
#   Resource           Requests     Limits
#   --------           --------     ------
#   nvidia.com/gpu     4            4
#   cpu                8000m        16000m
#   memory             64Gi         128Gi

# 提交 GPU 训练作业
$ cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: training-job-01
  labels:
    app: llm-training
spec:
  containers:
  - name: trainer
    image: nvcr.io/nvidia/pytorch:23.10-py3
    resources:
      limits:
        nvidia.com/gpu: 8
      requests:
        nvidia.com/gpu: 8
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    command: ["python", "train.py"]
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H100-80GB-HBM3"
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
EOF

# 查看作业调度事件
$ kubectl describe pod training-job-01 | grep -A 10 "Events"

# Events:
#   Type    Reason     Message
#   ----    ------     -------
#   Normal  Scheduled  Successfully assigned default/training-job-01 to gpu-node-01
#   Normal  Pulled     Container image already present on machine
#   Normal  Created    Created container trainer
#   Normal  Started    Started container trainer

# 使用 Volcano 实现 Gang Scheduling（全部 Pod 同时调度）
$ cat <<EOF | kubectl apply -f -
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
spec:
  minAvailable: 4      # 至少 4 个 Pod 才启动
  schedulerName: volcano
  policies:
  - event: PodEvicted
    action: RestartJob
  tasks:
  - replicas: 4
    name: trainer
    template:
      spec:
        containers:
        - name: trainer
          image: nvcr.io/nvidia/pytorch:23.10-py3
          resources:
            limits:
              nvidia.com/gpu: 8
EOF

# 查看 Volcano 队列状态
$ kubectl get vcqueue
# NAME      STATE    WEIGHT
# default   Open     1
# train     Open     3
# infer     Open     1
```

#### 2.5 Checkpoint 工具与最佳实践

```bash
# PyTorch 分布式 Checkpoint (torch.distributed.checkpoint)
# 保存
import torch.distributed.checkpoint as dcp

state = {
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "step": global_step,
}

# 使用分布式 Checkpoint，每个 rank 只写自己的分片
dcp.save(state, storage_writer=dcp.FileSystemWriter("/shared/checkpoint/step_1000"))

# 加载
dcp.load(state, storage_reader=dcp.FileSystemReader("/shared/checkpoint/step_1000"))

# 监控 checkpoint 写入性能
$ iostat -x 1 | grep -E "nvme|lustre"

# 输出:
# Device   r/s    w/s    rMB/s  wMB/s  await  svctm  %util
# nvme0n1  1200   8500   47     332    0.8    0.1    85.2
# nvme1n1  1100   8200   43     320    0.9    0.1    82.1

# 检查存储延迟
$ dd if=/dev/zero of=/shared/checkpoint/testfile bs=1M count=1024 oflag=direct
1024+0 records in
1024+0 records out
1073741824 bytes (1.1 GB) copied, 0.823456 s, 1.3 GB/s
```

---

### 3. SRE 实战案例

#### 案例 1：NCCL 初始化 hang 住

**症状描述**

一个 64 卡（8 节点 x 8 GPU）的分布式训练作业在启动后卡住。作业日志显示所有 rank 都通过了数据加载阶段，但在进入第一个 `all_reduce` 操作时全部 hang 住。GPU 利用率为 0%，作业无任何输出。

**排查步骤**

```
排查流程图:
┌─────────────────────────────────────────┐
│         作业 hang 在初始化阶段             │
└────────────────┬────────────────────────┘
                 │
         ┌───────┴───────┐
         ▼               ▼
   检查 NCCL 日志     检查 GPU 状态
   (NCCL_DEBUG=INFO)  (nvidia-smi)
         │               │
         ▼               ▼
   NCCL 版本是否       GPU 是否全部
   与驱动匹配？        可见且正常？
         │               │
    ┌────┴────┐     ┌────┴────┐
    ▼         ▼     ▼         ▼
  版本匹配  版本不匹配  正常     异常
    │         │       │         │
    ▼         ▼       ▼         ▼
  检查网络  修复版本   检查IB    隔离节点
  连通性    矩阵      连通性
    │                │
    ▼                ▼
  ibstat/           ibstat
  ibping            异常
```

**第一步：收集 NCCL 日志**

```bash
# 重新运行作业，启用 NCCL 调试日志
$ NCCL_DEBUG=INFO NCCL_DEBUG_SUBSYS=ALL python train.py 2>&1 | tee nccl_debug.log

# 关键日志片段（正常情况）:
# node-01:34567:34567 [0] NCCL INFO NET/IB : Using [0] mlx5_0:1/RoCE [1] mlx5_1:1/RoCE
# node-01:34567:34567 [0] NCCL INFO Using network IB
# node-01:34567:34567 [0] NCCL INFO comm 0x7f1234567890 rank 0 nranks 64 cudaDev 0 busId 1a:00.0
# node-01:34567:34567 [0] NCCL INFO Trees [0] -1/-1/-1->1->2 [1] -1/-1/-1->1->2

# 关键日志片段（异常情况 - 版本不匹配）:
# node-01:34567:34567 [0] NCCL INFO NET/IB : Using [0] mlx5_0:1/RoCE
# node-01:34567:34567 [0] NCCL WARN NET/IB : libibverbs not found
# node-01:34567:34567 [0] NCCL INFO NET/Socket : Using eth0
# (此处 NCCL 退回 TCP 通信，后续 all_reduce 会非常慢或超时)
```

**第二步：检查版本矩阵**

```bash
# 检查宿主机驱动版本
$ nvidia-smi --query-gpu=driver_version --format=csv,noheader
535.129.03

# 检查容器内 CUDA 版本
$ docker exec training-pod nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Cuda compilation tools, release 12.4, V12.4.131

# 检查容器内 NCCL 版本
$ docker exec training-pod python -c "import torch; print(torch.cuda.nccl.version())"
(2, 19, 3)

# 检查容器内 OFED 是否存在
$ docker exec training-pod ls /usr/lib/x86_64-linux-gnu/libibverbs*
ls: cannot access '/usr/lib/x86_64-linux-gnu/libibverbs*': No such file or directory
```

**根因定位**

容器内缺少 OFED 用户态库（libibverbs）。NCCL 在初始化时尝试使用 InfiniBand/RDMA 后端，但找不到 `libibverbs`，于是退回 TCP Socket 通信。在 64 卡规模下，TCP 通信无法完成 all_reduce 操作，导致超时 hang 住。

此外，NCCL 2.19 需要 CUDA 12.4，而宿主机 Driver 535 最高只支持 CUDA 12.2，存在版本不兼容。

**修复方案**

```bash
# 1. 回退到兼容版本
# 使用 CUDA 12.2 基础镜像 + NCCL 2.18 + 包含 OFED 的镜像
FROM nvcr.io/nvidia/pytorch:23.10-py3

# 安装 OFED 用户态库
RUN apt-get update && apt-get install -y \
    libibverbs1 \
    libibverbs-dev \
    librdmacm1 \
    librdmacm-dev \
    ibverbs-utils \
    perftest

# 验证
RUN ibv_devinfo

# 2. 建立版本准入门禁脚本
cat > /usr/local/bin/check-gpu-env.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "=== GPU Environment Version Check ==="

# 检查驱动版本
DRIVER_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
echo "Driver: $DRIVER_VER"

# 检查 CUDA 版本
CUDA_VER=$(nvcc --version | grep "release" | sed 's/.*release //' | sed 's/,.*//')
echo "CUDA: $CUDA_VER"

# 检查 NCCL 版本
NCCL_VER=$(python -c "import torch; print('.'.join(map(str, torch.cuda.nccl.version())))")
echo "NCCL: $NCCL_VER"

# 检查 OFED
if ibv_devinfo > /dev/null 2>&1; then
    echo "OFED: OK ($(ibv_devinfo | grep hca_id | head -1))"
else
    echo "OFED: MISSING - NCCL will fallback to TCP!"
    exit 1
fi

# 版本兼容性检查
DRIVER_MAJOR=$(echo $DRIVER_VER | cut -d. -f1)
CUDA_MAJOR=$(echo $CUDA_VER | cut -d. -f1)
CUDA_MINOR=$(echo $CUDA_VER | cut -d. -f2)

if [ "$DRIVER_MAJOR" -lt 535 ] && [ "$CUDA_MAJOR" -ge 12 ]; then
    echo "ERROR: Driver $DRIVER_VER too old for CUDA $CUDA_VER"
    exit 1
fi

echo "=== All checks passed ==="
SCRIPT
chmod +x /usr/local/bin/check-gpu-env.sh
```

**预防措施**

1. 建立并维护版本矩阵文档，记录每组经过验证的版本组合
2. 在 CI/CD 流程中加入 GPU 环境检查步骤
3. 使用 GPU Operator 统一管理节点上的驱动和组件版本
4. 为每个基础镜像维护一个经过验证的标签，禁止使用未经测试的组合

---

#### 案例 2：Checkpoint 超时导致训练中断

**症状描述**

一个 70B 模型训练作业在每 1000 步进行 checkpoint 保存时，频繁出现超时失败。失败不是每次都发生，而是大约每 3-5 次 checkpoint 中就有一次超时。超时后作业被调度器判定为失败并重启，导致训练进度回退。

**排查步骤**

```
排查流程图:
┌─────────────────────────────────────────┐
│        Checkpoint 周期性超时               │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 检查存储       检查网络      检查作业
 I/O 指标      带宽          并发情况
    │            │            │
    ▼            ▼            ▼
 IOPS 正常？   带宽充足？    多作业同时
 延迟正常？    无丢包？      checkpoint？
    │            │            │
    └────────────┼────────────┘
                 ▼
         分析写入模式
         (文件数量/大小)
                 │
                 ▼
         定位热点路径
         / 元数据瓶颈
```

**第一步：监控存储 I/O**

```bash
# 在 checkpoint 期间实时监控存储 I/O
$ iostat -x 1

# 输出（异常情况）:
# Device   r/s    w/s    rMB/s  wMB/s  await  svctm  %util
# lustre-0  50     25000  2      980    45.2   0.8    98.5
# lustre-0  48     28000  2      1020   52.1   0.9    99.2
# lustre-0  52     1500   2      60     2.1    0.1    15.3   ← checkpoint 结束后恢复正常

# await (平均等待时间) 从正常的 2ms 飙升到 45-52ms
# %util 接近 100%，说明存储已经完全饱和
```

**第二步：分析 Checkpoint 写入模式**

```bash
# 统计 checkpoint 目录下的文件数量和大小
$ find /shared/checkpoint/step_1000 -type f | wc -l
16384

$ du -sh /shared/checkpoint/step_1000
287G    /shared/checkpoint/step_1000

$ find /shared/checkpoint/step_1000 -type f -exec ls -la {} \; | awk '{print $5}' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count/1024, "KB, Count:", count}'
Avg: 17.5 KB, Count: 16384
```

问题清晰了：checkpoint 产生了 16384 个小文件（平均 17.5KB），总计 287GB。小文件对并行文件系统的元数据服务造成巨大压力，导致元数据操作延迟飙升，进而导致写入超时。

**第三步：检查并发写入**

```bash
# 检查是否有多个作业同时进行 checkpoint
$ kubectl get pods -l app=llm-training -o wide
# NAME                NODE          STATUS
# training-job-01     gpu-node-01   Running
# training-job-02     gpu-node-02   Running
# training-job-03     gpu-node-03   Running

# 查看存储端的并发连接数
$ lctl get_param osc.*.stats
# 显示多个客户端同时在写入，I/O 模式高度重叠
```

**根因定位**

1. **小文件问题**：70B 模型使用 ZeRO-3 分片后，64 个 rank 各自写入自己的分片，产生 16384 个小文件
2. **并发冲突**：3 个训练作业几乎同时触发 checkpoint（都在第 1000 步），导致存储元数据服务过载
3. **无 I/O 调度**：checkpoint 直接写入共享存储，没有经过本地缓存或异步队列

**修复方案**

```python
# 方案 1: 使用分布式 Checkpoint，合并小文件
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint import FileSystemWriter

# 配置每个 rank 写入更大的 chunks，减少文件数量
writer = FileSystemWriter(
    path="/shared/checkpoint/step_1000",
    per_rank_write_limit=256 * 1024 * 1024,  # 256MB per chunk
)

state = {
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "step": global_step,
}

dcp.save(state, storage_writer=writer)

# 方案 2: 先写本地 NVMe，再异步同步
import threading
import shutil

def async_checkpoint(state, local_path, remote_path):
    """本地保存 + 异步同步到共享存储"""
    # 第一步：快速写入本地 NVMe（高带宽、低延迟）
    torch.save(state, local_path)

    # 第二步：后台线程同步到共享存储
    def sync_to_remote():
        shutil.copy2(local_path, remote_path)
        os.remove(local_path)

    thread = threading.Thread(target=sync_to_remote)
    thread.start()
    return thread

# 方案 3: 错峰 checkpoint 调度
import time
import random

def staggered_checkpoint(rank, step, interval=1000):
    """每个 rank 根据 rank ID 错开 checkpoint 时间"""
    if step % interval == 0:
        # 基于 rank ID 错开 0-60 秒
        delay = (rank % 64) * 1.0
        time.sleep(delay)
        return True
    return False
```

**监控改进**

```bash
# 添加 checkpoint 性能监控指标
# Prometheus 告警规则
groups:
- name: checkpoint_alerts
  rules:
  - alert: CheckpointDurationHigh
    expr: checkpoint_duration_seconds > 300
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Checkpoint 耗时超过 5 分钟"
      description: "作业 {{ $labels.job }} 的 checkpoint 耗时 {{ $value }}s"

  - alert: CheckpointFailed
    expr: increase(checkpoint_failures_total[1h]) > 0
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "Checkpoint 失败"
      description: "作业 {{ $labels.job }} 在过去 1 小时内 checkpoint 失败 {{ $value }} 次"

  - alert: StorageLatencyHigh
    expr: storage_write_latency_p99_seconds > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "存储写入延迟升高"
      description: "存储系统 P99 写入延迟 {{ $value }}s"
```

---

## 💻 实战练习

### 练习 1：基础操作 — 使用 nvidia-smi 和 DCGM 检查 GPU 集群健康状态

**目标**：熟悉 GPU 状态检查工具，能快速判断节点健康状况。

**步骤**：

```bash
# 1. 检查所有 GPU 的基本状态
$ nvidia-smi

# 记录以下信息：
# - 驱动版本
# - CUDA 版本
# - 每块 GPU 的温度、功耗、显存使用情况
# - 是否有正在运行的进程

# 2. 检查 GPU 拓扑
$ nvidia-smi topo -m

# 回答以下问题：
# - GPU 之间是通过什么方式连接的？（NVLink/PCIe）
# - GPU 到 NIC 的连接路径是什么？（PIX/SYS）
# - 哪些 GPU 之间的通信性能最好？

# 3. 检查 ECC 错误
$ nvidia-smi -q | grep -A 15 "ECC"

# 回答以下问题：
# - ECC 是否启用？
# - 有多少 Correctable 错误？
# - 是否有 Uncorrectable 错误？

# 4. 运行 DCGM 诊断
$ dcgmi diag -r 2

# 回答以下问题：
# - 所有 GPU 是否通过诊断？
# - 哪些测试项目的结果需要注意？

# 5. 查看 Xid 错误
$ nvidia-smi -q | grep -A 5 "Xid"

# 回答以下问题：
# - 是否有 Xid 错误？
# - Xid 错误代码是什么？（常见: 31=GPU 内存页 retirement, 74=NVLINK 错误）
```

**预期输出示例**：

```
=== 节点健康报告 ===
节点: gpu-node-01
驱动: 535.129.03
CUDA: 12.2
GPU 数量: 8x NVIDIA H100 80GB HBM3

GPU 拓扑:
  - 所有 GPU 通过 NVLink 18 lanes 互联 (NV18)
  - GPU 0-3 到 NIC 0: PIX (同一 PCIe Switch)
  - GPU 4-7 到 NIC 1: PIX (同一 PCIe Switch)

ECC 状态:
  - 模式: Enabled
  - 可纠正错误: 128 (正常范围)
  - 不可纠正错误: 0

DCGM 诊断:
  - Level 2: 全部通过

Xid 错误: 无

结论: 节点健康，可投入使用
```

---

### 练习 2：进阶场景 — 配置 Kubernetes GPU 调度，实现拓扑感知

**目标**：在 Kubernetes 集群中配置 GPU 调度，确保 Pod 获得拓扑最优的 GPU 分配。

**前置条件**：一个安装了 NVIDIA GPU Operator 的 Kubernetes 集群。

**步骤**：

```bash
# 1. 检查 GPU Operator 状态
$ kubectl get pods -n gpu-operator-resources

# 预期输出:
# NAME                                      READY   STATUS
# nvidia-device-plugin-daemonset-xxx        1/1     Running
# nvidia-dcgm-exporter-xxx                  1/1     Running
# nvidia-driver-daemonset-xxx               1/1     Running
# gpu-feature-discovery-xxx                 1/1     Running

# 2. 查看节点 GPU 标签
$ kubectl get node gpu-node-01 --show-labels | tr ',' '\n' | grep nvidia

# 预期标签:
# nvidia.com/gpu.count=8
# nvidia.com/gpu.family=hopper
# nvidia.com/gpu.product=NVIDIA-H100-80GB-HBM3
# nvidia.com/gpu.memory=81559
# nvidia.com/mig.capable=false

# 3. 配置拓扑感知调度（需要 Topology Manager）
# 编辑 kubelet 配置
$ cat <<EOF > /etc/kubernetes/kubelet-config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
topologyManagerPolicy: best-effort
topologyManagerScope: pod
cpuManagerPolicy: static
EOF

# 4. 部署一个需要拓扑感知的训练作业
$ cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: topo-aware-training
  annotations:
    # 请求拓扑最优的 GPU 分配
    nvidia.com/topology-aware: "true"
spec:
  containers:
  - name: trainer
    image: nvcr.io/nvidia/pytorch:23.10-py3
    resources:
      limits:
        nvidia.com/gpu: 8
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_TOPO_FILE
      value: "/etc/nvidia/topo.xml"
    command: ["python", "-c", "
import torch
import torch.distributed as dist
dist.init_process_group('nccl')
# 打印每个 GPU 的 NVLink 邻居
for i in range(8):
    for j in range(8):
        if i != j:
            props = torch.cuda.get_device_properties(i)
            print(f'GPU {i} <-> GPU {j}: NVLink')
print('Topology check complete')
"]
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H100-80GB-HBM3"
EOF

# 5. 验证 GPU 分配是否拓扑最优
$ kubectl exec topo-aware-training -- nvidia-smi topo -m

# 预期: 分配到的 8 块 GPU 应该通过 NVLink 全互联
# 而不是分散在不同 PCIe Switch 下
```

**验证标准**：

- 所有 8 块 GPU 之间显示 `NV18` 连接
- 没有 `SYS` 或 `NODE` 连接（跨 NUMA）
- NCCL 日志显示使用 IB 后端而非 TCP

---

### 练习 3：故障排查挑战 — 模拟 NCCL hang 场景，完成完整排查

**目标**：模拟一个 NCCL hang 故障，练习从症状到根因的完整排查链路。

**场景设置**：

```bash
# 场景：故意制造一个 NCCL 版本不匹配的环境

# 1. 创建一个包含错误版本 NCCL 的容器
$ cat > Dockerfile.broken-nccl << 'EOF'
FROM nvcr.io/nvidia/pytorch:23.10-py3

# 升级 NCCL 到不兼容的版本
RUN pip install nvidia-nccl-cu12==2.19.3 --force-reinstall

# 移除 OFED 库，模拟缺失
RUN rm -f /usr/lib/x86_64-linux-gnu/libibverbs*
RUN rm -f /usr/lib/x86_64-linux-gnu/librdmacm*
EOF

$ docker build -f Dockerfile.broken-nccl -t broken-nccl:latest .

# 2. 创建一个简单的分布式训练脚本
$ cat > train_hang_test.py << 'PYEOF'
import torch
import torch.distributed as dist
import os

def main():
    dist.init_process_group('nccl')
    rank = dist.get_rank()
    world_size = dist.get_world_size()

    print(f"[Rank {rank}] Initializing...")

    # 这个 all_reduce 会 hang（如果 NCCL 通信有问题）
    tensor = torch.ones(1024, device='cuda')
    print(f"[Rank {rank}] Starting all_reduce...")
    dist.all_reduce(tensor)
    print(f"[Rank {rank}] all_reduce complete! Result: {tensor[0].item()}")

if __name__ == "__main__":
    main()
PYEOF

# 3. 运行（预期会 hang）
$ docker run --gpus all --rm -it broken-nccl:latest \
    python train_hang_test.py

# 作业会卡在 "Starting all_reduce..." 不再输出
```

**你的任务**：

按照以下步骤完成排查，并记录每一步的发现：

```
排查清单:
┌──┬─────────────────────────────────────┬──────────┬──────────┐
│# │ 检查项                               │ 期望结果  │ 实际结果  │
├──┼─────────────────────────────────────┼──────────┼──────────┤
│1 │ nvidia-smi 查看 GPU 状态             │ 全部正常  │          │
│2 │ nvidia-smi topo -m 查看拓扑          │ NVLink   │          │
│3 │ NCCL_DEBUG=INFO 查看 NCCL 日志       │ 使用 IB  │          │
│4 │ 检查 NCCL 版本                       │ 匹配     │          │
│5 │ 检查容器内 libibverbs                │ 存在     │          │
│6 │ 检查宿主机 vs 容器 CUDA 版本         │ 兼容     │          │
│7 │ ibv_devinfo 检查 IB 设备             │ 正常     │          │
│8 │ 定位根因                              │          │          │
│9 │ 制定修复方案                          │          │          │
│10│ 验证修复后作业正常运行                │ 通过     │          │
└──┴─────────────────────────────────────┴──────────┴──────────┘
```

**参考答案**（先自己尝试排查，再对答案）：

<details>
<summary>点击展开参考答案</summary>

1. `nvidia-smi` 输出正常，8 块 H100 全部可见，温度正常
2. `nvidia-smi topo -m` 显示 NV18 连接，拓扑正常
3. NCCL 日志显示 `NET/IB : libibverbs not found`，退回 TCP
4. NCCL 版本 2.19.3，但容器内 CUDA 12.2，可能存在兼容问题
5. `ls /usr/lib/x86_64-linux-gnu/libibverbs*` → 文件不存在
6. 宿主机 Driver 535 支持 CUDA 12.2，容器内也是 12.2 → 兼容
7. 无法运行（因为容器内库缺失）
8. 根因：NCCL 退回 TCP 后，在多卡 all_reduce 时 TCP 通信超时导致 hang
9. 修复：安装 OFED 用户态库，或使用包含 OFED 的基础镜像
10. 修复后重新运行，作业正常完成

</details>

---

## 🎯 面试题精选

### 问题 1：NVLink vs PCIe 的性能差异和适用场景

**参考答案**：

NVLink 和 PCIe 是 GPU 互联的两种主要方式，性能差异显著：

**带宽对比**（H100 为例）：
- PCIe Gen5 x16：单向 32 GB/s，双向 64 GB/s
- NVLink 4.0：单向 450 GB/s（单条链路），全部 18 条链路双向 900 GB/s

NVLink 带宽是 PCIe 的约 14 倍。

**适用场景**：
- NVLink：多 GPU 训练（特别是模型并行和流水线并行），需要频繁的 GPU 间通信
- PCIe：推理服务（GPU 间通信少），或者 GPU 与 CPU/NIC 之间的连接

**SRE 关注点**：
- 需要确保调度器将同一作业的 GPU 分配到 NVLink 直连的 GPU 上
- 通过 `nvidia-smi topo -m` 验证拓扑
- NVLink 错误（通过 `DCGM_FI_DEV_NVLINK_CRC_FLIT` 指标监控）会导致通信性能下降

---

### 问题 2：如何设计 GPU 集群的网络架构

**参考答案**：

GPU 集群通常需要三张独立的网络：

```
网络架构设计:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  计算网络 (RDMA)          存储网络          管理网络       │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────┐  │
│  │  InfiniBand  │    │  Ethernet    │   │  Ethernet   │  │
│  │  NDR 400G    │    │  100GbE      │   │  10GbE      │  │
│  │              │    │              │   │             │  │
│  │  用途:       │    │  用途:       │   │  用途:      │  │
│  │  all-reduce  │    │  数据读写    │   │  K8s/Slurm  │  │
│  │  P2P 通信    │    │  Checkpoint  │   │  监控/日志   │  │
│  └──────────────┘    └──────────────┘   └─────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**设计要点**：

1. **计算网络**：专用 RDMA 网络，低延迟、高带宽，用于 all-reduce 等集合通信
2. **存储网络**：连接并行文件系统，需要高吞吐但延迟要求稍低
3. **管理网络**：K8s API、监控、日志等管理流量，带宽要求最低

**为什么要隔离**：如果让 all-reduce 和 checkpoint I/O 共享网络，checkpoint 写入会导致 all-reduce 延迟抖动，直接影响训练性能。

---

### 问题 3：K8s vs Slurm 的选型决策

**参考答案**：

| 决策因素 | 选择 Kubernetes | 选择 Slurm |
|---------|----------------|------------|
| 平台目标 | 统一云原生资源池 | 最大化训练吞吐 |
| 团队背景 | 云原生/SRE 团队 | HPC 团队 |
| 工作负载 | 训练 + 推理混合 | 大规模纯训练 |
| 弹性需求 | 需要频繁扩缩容 | 相对稳定的集群规模 |
| 多租户 | 需要精细的 RBAC/配额 | 简单的队列/分区即可 |
| 生态集成 | GitOps、服务网格、可观测性 | 传统 HPC 工具链 |

**混合方案**：很多团队同时使用两者。K8s 作为统一控制面，管理推理服务和轻量训练；Slurm 管理大规模训练作业，通过 K8s Job 或自定义控制器触发 Slurm 作业提交。

---

### 问题 4：Checkpoint 策略设计

**参考答案**：

好的 checkpoint 策略需要平衡三个目标：恢复速度、存储成本、对训练性能的影响。

**设计要素**：

1. **保存频率**：根据平均故障间隔（MTBF）决定。如果 MTBF 是 24 小时，checkpoint 间隔设为 1-2 小时
2. **保存方式**：异步 + 分布式，不阻塞训练
3. **存储层级**：本地 NVMe（热）→ 共享存储（温）→ 对象存储（冷）
4. **保留策略**：保留最近 N 个 + 每天一个 + 每周一个

**关键指标监控**：
- checkpoint 耗时（P50/P99）
- checkpoint 大小
- 恢复耗时
- 存储使用量

---

### 问题 5：GPU 故障检测与隔离

**参考答案**：

GPU 故障检测分为主动检测和被动检测：

**主动检测**：
- 定期运行 DCGM 诊断（Level 1 每小时，Level 3 每天）
- 监控 ECC 错误趋势
- 监控温度和功耗异常

**被动检测**：
- Xid 错误（内核级 GPU 错误）
- 作业失败日志分析
- GPU 利用率异常

**隔离流程**：

```
故障检测 → 自动标记节点 → 驱逐 Pod → 人工确认 → 维修/更换 → 验证 → 恢复
```

**自动隔离规则**：
- 出现 Uncorrectable ECC 错误 → 立即隔离
- Xid 错误连续出现 3 次 → 隔离
- GPU 温度持续 > 90°C → 告警 + 降低调度优先级
- NVLink CRC 错误突增 → 告警 + 标记为待检查

---

### 问题 6：如何诊断 all-reduce 性能低于预期

**参考答案**：

all-reduce 性能低的常见原因和排查方法：

1. **网络问题**：检查 IB/RoCE 网络是否正常
   - `ibstat` 检查链路状态
   - `ibping` 测试端到端连通性
   - 检查交换机错误计数

2. **拓扑问题**：GPU 是否通过最优路径通信
   - `nvidia-smi topo -m` 验证 NVLink 连接
   - 检查 GPU 到 NIC 的路径
   - 确认没有跨 NUMA 访问

3. **NCCL 配置**：NCCL 参数是否合理
   - `NCCL_ALGO` 选择合适的算法
   - `NCCL_DEBUG=INFO` 查看 NCCL 选择的通信路径
   - 检查是否回退到 TCP

4. **拥塞问题**：多作业是否共享网络
   - 检查是否有其他作业同时在用网络
   - 检查存储网络是否与计算网络隔离

---

### 问题 7：MIG（Multi-Instance GPU）的适用场景和限制

**参考答案**：

MIG 是 NVIDIA A100/H100 支持的 GPU 分区技术，将一块物理 GPU 切分为多个独立实例。

**适用场景**：
- 推理服务：多个小模型推理实例共享一块 GPU
- 多租户隔离：不同租户获得完全独立的 GPU 资源
- 开发/测试：为开发人员提供小块 GPU 资源

**限制**：
- 同一 MIG 实例内的进程共享该实例的显存和计算
- 不同 MIG 实例之间完全隔离，不能通信
- 不适合需要跨 GPU 通信的分布式训练

**H100 MIG 配置示例**：

```bash
# 查看 MIG 支持
$ nvidia-smi mig -lgip

# 创建 MIG 实例
$ nvidia-smi mig -cgi 19,19 -C

# 说明: 19 = 1g.20gb 配置（每实例 1 个 GPU slice, 20GB 显存）
# H100 最多可切分为 7 个 MIG 实例
```

---

### 问题 8：如何设计 GPU 集群的监控告警体系

**参考答案**：

```
监控层次:
┌─────────────────────────────────────────────────────────────┐
│                      告警分层设计                             │
├──────────┬───────────────────────┬───────────────────────────┤
│  层级     │  指标                 │  告警阈值                  │
├──────────┼───────────────────────┼───────────────────────────┤
│  硬件层   │  ECC 错误             │  Uncorrectable > 0        │
│          │  Xid 错误             │  任何 Xid                  │
│          │  温度                 │  > 85°C                   │
│          │  功耗                 │  > 650W (H100)            │
│          │  NVLink CRC 错误      │  突增 > 100/小时           │
├──────────┼───────────────────────┼───────────────────────────┤
│  通信层   │  NCCL 通信延迟        │  P99 > 100ms              │
│          │  IB 链路错误          │  任何错误                  │
│          │  TCP 重传率           │  > 1%                     │
├──────────┼───────────────────────┼───────────────────────────┤
│  作业层   │  GPU 利用率           │  < 80% 持续 10 分钟        │
│          │  Step time            │  突增 > 20%               │
│          │  Checkpoint 耗时      │  > 300 秒                 │
│          │  作业失败率           │  > 5%                     │
├──────────┼───────────────────────┼───────────────────────────┤
│  调度层   │  排队时间             │  P95 > 1 小时             │
│          │  资源碎片率           │  > 30%                    │
│          │  节点不可用数         │  > 5%                     │
└──────────┴───────────────────────┴───────────────────────────┘
```

**关键原则**：
- 告警必须能关联到业务影响（不只是底层指标）
- 设置告警聚合，避免单个节点故障产生大量告警
- 建立告警升级机制：自动恢复 → 值班 SRE → 团队 Lead

---

### 问题 9：如何处理 GPU 节点的灰度发布和滚动升级

**参考答案**：

GPU 节点升级是一个高风险操作，需要谨慎处理：

**升级顺序**：
1. 驱动版本（宿主机）
2. CUDA 版本（容器基础镜像）
3. NCCL/框架版本（应用层）

**灰度策略**：
- 第一批：1-2 个节点（金丝雀）
- 第二批：10% 节点
- 第三批：50% 节点
- 第四批：全部节点

**每批次验证**：
- 运行 DCGM 诊断 Level 3
- 运行标准训练基准测试（all-reduce bandwidth）
- 运行真实训练作业 1 小时
- 检查 NCCL 通信是否正常

**回滚条件**：
- DCGM 诊断失败
- 基准测试性能下降 > 10%
- 任何 NCCL 通信错误

---

### 问题 10：如何优化大规模训练的数据加载

**参考答案**：

数据加载是训练流水线中容易被忽视的瓶颈：

**常见问题**：
- 共享存储 IOPS 不足
- 小文件过多导致元数据瓶颈
- 数据预处理 CPU 不足

**优化方案**：

1. **本地缓存**：将热门数据集缓存到节点本地 NVMe
   ```bash
   # 使用 Alluxio 或直接 rsync
   rsync -av --progress /shared/dataset/ /local/cache/dataset/
   ```

2. **数据格式优化**：使用 WebDataset 或 TFRecord 格式
   - 将小文件打包成大文件（tar/TFRecord）
   - 支持流式读取，减少随机 I/O

3. **预取和异步加载**：
   ```python
   DataLoader(dataset, num_workers=8, prefetch_factor=2, pin_memory=True)
   ```

4. **CPU 资源预留**：为数据加载预留足够的 CPU 核心
   ```yaml
   resources:
     requests:
       cpu: "32"      # 数据加载需要 CPU
       memory: "64Gi"
     limits:
       nvidia.com/gpu: "8"
   ```

---

## 📚 深入阅读

- [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) — LLM 生命周期概览
- [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) — 分布式训练与容错
- [02-glossary.md](./02-glossary.md) — 术语表
- [03-reference-map.md](./03-reference-map.md) — 参考资料索引
- [NVIDIA DCGM 官方文档](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/)
- [NCCL 官方文档](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
- [Slurm 官方文档](https://slurm.schedmd.com/)

---

## ✅ 自检清单

完成本篇学习后，用以下清单检验自己的掌握程度：

### 概念理解
- [ ] 能画出 8 卡 H100 节点的内部拓扑（GPU、NVLink、NVSwitch、NIC、PCIe）
- [ ] 能解释 NVLink、InfiniBand、RoCE 的区别和适用场景
- [ ] 能解释 NVIDIA Driver → CUDA → NCCL → OFED 的版本依赖关系
- [ ] 能对比 K8s 和 Slurm 在 GPU 调度上的差异
- [ ] 能解释 MIG 的工作原理和适用场景

### 工具使用
- [ ] 能使用 `nvidia-smi` 查看 GPU 状态、拓扑、ECC 错误
- [ ] 能使用 DCGM 进行 GPU 诊断（Level 1/2/3）
- [ ] 能配置 NCCL 环境变量进行通信调优
- [ ] 能使用 `kubectl` 查看和管理 GPU 资源
- [ ] 能使用 DCGM Exporter 将 GPU 指标暴露给 Prometheus

### 故障排查
- [ ] 能排查 NCCL 初始化 hang 的完整链路
- [ ] 能排查 checkpoint 超时问题
- [ ] 能识别常见的 GPU 故障模式（Xid 错误、ECC 错误、NVLink 错误）
- [ ] 能区分单节点问题、拓扑问题、共享资源问题和调度问题

### 设计能力
- [ ] 能设计 GPU 集群的网络架构（计算网络、存储网络、管理网络）
- [ ] 能设计 checkpoint 策略（频率、存储层级、保留策略）
- [ ] 能设计 GPU 集群的监控告警体系
- [ ] 能设计多租户 GPU 集群的资源隔离方案

### 面试准备
- [ ] 能回答 NVLink vs PCIe 的性能差异和适用场景
- [ ] 能回答 K8s vs Slurm 的选型决策
- [ ] 能回答 GPU 故障检测与隔离方案
- [ ] 能回答 Checkpoint 策略设计
- [ ] 能回答 all-reduce 性能排查方法
