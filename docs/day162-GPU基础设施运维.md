# Day 162: GPU 基础设施运维

> 📅 日期：2026-05-03
> 📖 学习主题：GPU 基础设施运维（GPU 架构 CUDA/Tensor Core, 显存管理, GPU 虚拟化 MIG/MPS, 驱动安装, 监控 nvidia-smi/DCGM, 故障排查）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 161 (LLMOps 概述), Day 76-89 (Docker), Day 105-119 (AWS)

---

## 🎯 学习目标

完成本日学习后，你将能够：

1. 理解 GPU 硬件架构（SM, CUDA Core, Tensor Core）
2. 掌握 NVIDIA 驱动和 CUDA 工具链的安装与管理
3. 使用 nvidia-smi 和 DCGM 监控 GPU 状态
4. 理解 GPU 虚拟化技术（MIG, MPS, vGPU）
5. 掌握显存管理和常见 GPU 故障排查方法

---

## 📖 核心知识点

### 1. GPU 硬件架构

#### 1.1 NVIDIA GPU 架构层次

```
┌──────────────────────────────────────────────────────────────┐
│                    NVIDIA GPU 架构层次                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  GPU (例: A100)                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  GPC 0    GPC 1    GPC 2    GPC 3    ...  GPC 7       │ │
│  │  ┌────┐  ┌────┐  ┌────┐  ┌────┐       ┌────┐        │ │
│  │  │TPC │  │TPC │  │TPC │  │TPC │  ...  │TPC │        │ │
│  │  │TPC │  │TPC │  │TPC │  │TPC │       │TPC │        │ │
│  │  │TPC │  │TPC │  │TPC │  │TPC │       │TPC │        │ │
│  │  └────┘  └────┘  └────┘  └────┘       └────┘        │ │
│  │                                                        │ │
│  │  每个 TPC 包含:                                         │ │
│  │  ┌──────────────────────────────────────────┐         │ │
│  │  │  SM (Streaming Multiprocessor)            │         │ │
│  │  │  ┌─────────────────────────────────────┐ │         │ │
│  │  │  │  64 CUDA Cores (FP32)               │ │         │ │
│  │  │  │  32 FP64 Cores                      │ │         │ │
│  │  │  │  4 Tensor Cores (第3代)              │ │         │ │
│  │  │  │  4 Texture Units                    │ │         │ │
│  │  │  │  L1 Cache / Shared Memory (192KB)    │ │         │ │
│  │  │  └─────────────────────────────────────┘ │         │ │
│  │  └──────────────────────────────────────────┘         │ │
│  │                                                        │ │
│  │  L2 Cache: 40MB                                        │ │
│  │  HBM2e 显存: 80GB, 带宽 2039 GB/s                      │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 1.2 关键硬件组件

| 组件 | 说明 | A100 规格 | H100 规格 | SRE 关注点 |
|------|------|-----------|-----------|-----------|
| CUDA Core | 通用计算核心，执行 FP32/INT32 运算 | 6912 个 | 14592 个 | 决定并行计算能力 |
| Tensor Core | 矩阵运算加速，FP16/BF16/INT8 | 第3代，432 个 | 第4代，456 个 | LLM 推理的核心 |
| 显存 (VRAM) | 存储模型权重和中间结果 | 80GB HBM2e | 80GB HBM3 | 决定能运行的模型大小 |
| 显存带宽 | 数据传输速度 | 2039 GB/s | 3350 GB/s | Decode 阶段瓶颈 |
| L2 Cache | 二级缓存 | 40MB | 50MB | 减少显存访问 |
| NVLink | GPU 间高速互联 | 600 GB/s | 900 GB/s | 多卡并行效率 |

#### 1.3 CUDA 编程模型

```
┌──────────────────────────────────────────────────────────────┐
│                    CUDA 编程模型层次                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Grid (整个 GPU 任务)                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Block (0,0)    Block (1,0)    Block (2,0)    ...      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Thread 0 │  │ Thread 0 │  │ Thread 0 │            │ │
│  │  │ Thread 1 │  │ Thread 1 │  │ Thread 1 │            │ │
│  │  │ Thread 2 │  │ Thread 2 │  │ Thread 2 │            │ │
│  │  │ ...      │  │ ...      │  │ ...      │            │ │
│  │  │ Thread N │  │ Thread N │  │ Thread N │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  │                                                        │ │
│  │  Block (0,1)    Block (1,1)    Block (2,1)    ...      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ ...      │  │ ...      │  │ ...      │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  层次关系:                                                    │
│  - Grid 由多个 Block 组成                                     │
│  - Block 由多个 Thread 组成                                   │
│  - Block 内的 Thread 共享 Shared Memory                       │
│  - Thread 是最小执行单元                                      │
│                                                              │
│  LLM 推理映射:                                                │
│  - 矩阵乘法 (Attention, FFN) 映射到 Grid/Block               │
│  - 每个 Thread 计算矩阵的一个元素                              │
│  - Tensor Core 加速小矩阵块的乘累加                           │
└──────────────────────────────────────────────────────────────┘
```

#### 1.4 Tensor Core 与 LLM 推理

Tensor Core 是 LLM 推理的关键硬件加速单元：

```
┌──────────────────────────────────────────────────────────────┐
│              Tensor Core 矩阵运算示意                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  传统 CUDA Core: 一个时钟周期完成 1 次乘加运算                  │
│  Tensor Core:    一个时钟周期完成 64 次乘加运算 (4×4×4 矩阵)   │
│                                                              │
│  D = A × B + C                                               │
│                                                              │
│  ┌───┐   ┌───┐   ┌───┐   ┌───┐                              │
│  │ A │ × │ B │ + │ C │ = │ D │                              │
│  │4×4│   │4×4│   │4×4│   │4×4│                              │
│  └───┘   └───┘   └───┘   └───┘                              │
│                                                              │
│  数据类型支持:                                                │
│  - FP16 (半精度):  最常用，LLM 推理默认                       │
│  - BF16 (脑浮点):  训练常用，与 FP16 精度接近                 │
│  - FP8  (E4M3):   H100 支持，进一步提速                      │
│  - INT8 (整数):   量化推理使用                                │
│  - TF32:          A100+ 支持，兼顾精度和速度                  │
│                                                              │
│  LLM 推理中的应用:                                            │
│  - Attention: Q·K^T 和 Score·V 的矩阵乘法                    │
│  - FFN: 两层全连接的矩阵乘法                                  │
│  - Embedding: Token 到向量的查找（非 Tensor Core）            │
└──────────────────────────────────────────────────────────────┘
```

### 2. GPU 显存管理

#### 2.1 显存组成

```
┌──────────────────────────────────────────────────────────────┐
│              LLM 推理显存组成                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  总显存 (例: A100 80GB)                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  模型权重 (Model Weights)                               │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │  FP16: 参数量 × 2 bytes                        │   │ │
│  │  │  INT8: 参数量 × 1 byte                         │   │ │
│  │  │  INT4: 参数量 × 0.5 bytes                      │   │ │
│  │  │                                                │   │ │
│  │  │  例: Llama-3-70B FP16 = 70B × 2 = 140GB       │   │ │
│  │  │  例: Llama-3-8B  FP16 = 8B  × 2 = 16GB        │   │ │
│  │  │  例: Llama-3-8B  INT4 = 8B  × 0.5 = 4GB       │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  │                                                        │ │
│  │  KV Cache                                              │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │  大小 = 2 × num_layers × hidden_dim × seq_len  │   │ │
│  │  │        × batch_size × dtype_size               │   │ │
│  │  │                                                │   │ │
│  │  │  例: Llama-3-8B, 8K context, batch=1, FP16:    │   │ │
│  │  │  = 2 × 32 × 4096 × 8192 × 1 × 2 bytes        │   │ │
│  │  │  ≈ 4 GB                                        │   │ │
│  │  │                                                │   │ │
│  │  │  KV Cache 是动态增长的，随请求长度线性增加       │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  │                                                        │ │
│  │  激活值 (Activations)                                   │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │  推理时前向传播的中间结果                         │   │ │
│  │  │  推理阶段远小于训练阶段                          │   │ │
│  │  │  推理: 约数百 MB - 数 GB                         │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  │                                                        │ │
│  │  CUDA 运行时开销                                        │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │  CUDA Context: 约 500MB - 1GB                   │   │ │
│  │  │  cuBLAS workspace: 约 256MB - 1GB               │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 2.2 显存估算公式

```python
#!/usr/bin/env python3
"""gpu_memory_estimator.py - GPU 显存需求估算"""

def estimate_model_memory(
    params_billions: float,
    dtype_bytes: int = 2,  # FP16=2, INT8=1, INT4=0.5
    overhead_ratio: float = 1.1,  # 10% 运行时开销
) -> float:
    """估算模型权重显存 (GB)"""
    params = params_billions * 1e9
    weight_bytes = params * dtype_bytes
    total_bytes = weight_bytes * overhead_ratio
    return total_bytes / 1e9

def estimate_kv_cache(
    num_layers: int,
    hidden_dim: int,
    num_kv_heads: int,
    head_dim: int,
    seq_length: int,
    batch_size: int = 1,
    dtype_bytes: int = 2,
) -> float:
    """估算 KV Cache 显存 (GB)"""
    # K 和 V 各一份，共 2 份
    kv_bytes = (
        2  # K + V
        * num_layers
        * num_kv_heads
        * head_dim
        * seq_length
        * batch_size
        * dtype_bytes
    )
    return kv_bytes / 1e9

def estimate_total_memory(
    params_billions: float,
    num_layers: int,
    hidden_dim: int,
    num_kv_heads: int,
    head_dim: int,
    seq_length: int = 4096,
    batch_size: int = 1,
    dtype_bytes: int = 2,
) -> dict:
    """估算总显存需求"""
    model_gb = estimate_model_memory(params_billions, dtype_bytes)
    kv_gb = estimate_kv_cache(
        num_layers, hidden_dim, num_kv_heads, head_dim,
        seq_length, batch_size, dtype_bytes
    )
    cuda_overhead_gb = 1.5  # CUDA context + workspace
    total = model_gb + kv_gb + cuda_overhead_gb

    return {
        "model_weights_gb": round(model_gb, 2),
        "kv_cache_gb": round(kv_gb, 2),
        "cuda_overhead_gb": cuda_overhead_gb,
        "total_gb": round(total, 2),
        "recommended_gpu": recommend_gpu(total),
    }

def recommend_gpu(total_gb: float) -> str:
    """推荐 GPU 型号"""
    if total_gb <= 8:
        return "RTX 4080 (16GB) 或 RTX 4090 (24GB)"
    elif total_gb <= 24:
        return "RTX 4090 (24GB) 或 A10G (24GB)"
    elif total_gb <= 40:
        return "A100 40GB 或 L40S (48GB)"
    elif total_gb <= 80:
        return "A100 80GB 或 H100 80GB"
    elif total_gb <= 160:
        return "2x A100 80GB (Tensor Parallel)"
    else:
        return "4x+ A100/H100 或考虑量化"

# 使用示例
if __name__ == "__main__":
    # Llama-3-8B, FP16
    result = estimate_total_memory(
        params_billions=8,
        num_layers=32,
        hidden_dim=4096,
        num_kv_heads=8,
        head_dim=128,
        seq_length=8192,
        batch_size=1,
        dtype_bytes=2,
    )
    print("=== Llama-3-8B (FP16, 8K context) ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Llama-3-70B, FP16
    result = estimate_total_memory(
        params_billions=70,
        num_layers=80,
        hidden_dim=8192,
        num_kv_heads=8,
        head_dim=128,
        seq_length=8192,
        batch_size=1,
        dtype_bytes=2,
    )
    print("\n=== Llama-3-70B (FP16, 8K context) ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Llama-3-70B, INT4 量化
    result = estimate_total_memory(
        params_billions=70,
        num_layers=80,
        hidden_dim=8192,
        num_kv_heads=8,
        head_dim=128,
        seq_length=8192,
        batch_size=1,
        dtype_bytes=0.5,  # INT4
    )
    print("\n=== Llama-3-70B (INT4, 8K context) ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
```

### 3. NVIDIA 驱动与 CUDA 安装

#### 3.1 驱动安装（Ubuntu）

```bash
# 1. 检查当前 GPU 硬件
lspci | grep -i nvidia

# 2. 移除旧驱动（如有）
sudo apt-get purge -y nvidia-* libnvidia-*
sudo apt-get autoremove -y

# 3. 添加 NVIDIA 官方 PPA
sudo add-apt-repository -y ppa:graphics-drivers/ppa
sudo apt-get update

# 4. 查看推荐驱动版本
ubuntu-drivers devices

# 5. 安装推荐驱动（自动选择版本）
sudo ubuntu-drivers autoinstall

# 或者手动安装特定版本
# sudo apt-get install -y nvidia-driver-550

# 6. 安装 CUDA Toolkit（以 CUDA 12.x 为例）
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-4

# 7. 配置环境变量
cat >> ~/.bashrc << 'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF
source ~/.bashrc

# 8. 验证安装
nvidia-smi
nvcc --version
```

#### 3.2 Docker 中使用 GPU

```bash
# 1. 安装 NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 2. 配置 Docker runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. 测试 GPU 容器
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 4. 指定 GPU 数量
docker run --rm --gpus 2 nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 5. 指定特定 GPU
docker run --rm --gpus '"device=0,1"' nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

#### 3.3 Kubernetes GPU 支持

```yaml
# 1. 安装 NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.15.0/nvidia-device-plugin.yml

# 2. 验证 GPU 资源
kubectl get nodes -o json | jq '.items[].status.allocatable | {"nvidia.com/gpu"}'

# 3. GPU Pod 示例
# gpu-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference
spec:
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    resources:
      limits:
        nvidia.com/gpu: 2  # 请求 2 张 GPU
      requests:
        nvidia.com/gpu: 2
    args:
    - "--model"
    - "meta-llama/Llama-3-8B"
    - "--tensor-parallel-size"
    - "2"
    volumeMounts:
    - name: model-cache
      mountPath: /root/.cache
  volumes:
  - name: model-cache
    persistentVolumeClaim:
      claimName: model-cache-pvc
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

### 4. GPU 虚拟化技术

#### 4.1 MIG（Multi-Instance GPU）

```
┌──────────────────────────────────────────────────────────────┐
│                    MIG 分区示意 (A100 80GB)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  物理 A100 80GB                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  方案 1: 7 个等分实例                                    │ │
│  │  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐│ │
│  │  │ 10GB ││ 10GB ││ 10GB ││ 10GB ││ 10GB ││ 10GB ││ 10GB ││ │
│  │  │ 1/7  ││ 1/7  ││ 1/7  ││ 1/7  ││ 1/7  ││ 1/7  ││ 1/7  ││ │
│  │  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘│ │
│  │                                                        │ │
│  │  方案 2: 混合大小                                        │ │
│  │  ┌────────────────┐┌──────────────┐┌──────────┐┌──────┐│ │
│  │  │     40GB       ││    20GB      ││  10GB    ││ 10GB ││ │
│  │  │   (1/2 GPU)    ││  (1/4 GPU)  ││ (1/7)   ││(1/7) ││ │
│  │  └────────────────┘└──────────────┘└──────────┘└──────┘│ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  支持 MIG 的 GPU: A100, A30, H100                           │
│  不支持: A10G, V100, RTX 系列                                │
│                                                              │
│  MIG 优势:                                                   │
│  - 硬件级隔离，实例间完全独立                                  │
│  - 每个实例有独立的显存、缓存、计算资源                        │
│  - 故障隔离：一个实例崩溃不影响其他                            │
│  - 适合多租户场景                                             │
│                                                              │
│  MIG 限制:                                                   │
│  - 启用/禁用需要重启 GPU                                      │
│  - 不支持跨实例的 GPU 通信                                    │
│  - 配置后不能动态调整                                         │
└──────────────────────────────────────────────────────────────┘
```

```bash
# MIG 管理命令

# 1. 检查 GPU 是否支持 MIG
nvidia-smi -i 0 --query-gpu=mig.mode.current --format=csv

# 2. 启用 MIG（需要 root，会中断现有进程）
sudo nvidia-smi -i 0 -mig 1

# 3. 查看可用的 MIG 实例配置
nvidia-smi mig -lgip

# 4. 创建 MIG 实例
# 创建 1g.10gb 实例（1/7 GPU 计算 + 10GB 显存）
sudo nvidia-smi mig -cgi 19 -C

# 5. 查看已创建的实例
nvidia-smi mig -lgi

# 6. 查看实例对应的设备
nvidia-smi -L

# 7. 删除所有 MIG 实例
sudo nvidia-smi mig -dci
sudo nvidia-smi mig -dgi

# 8. 禁用 MIG
sudo nvidia-smi -i 0 -mig 0
```

#### 4.2 MPS（Multi-Process Service）

```
┌──────────────────────────────────────────────────────────────┐
│                    MPS 工作原理                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  无 MPS:                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Process A │  │ Process B │  │ Process C │                  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘                  │
│        │             │             │                         │
│        ▼             ▼             ▼                         │
│  ┌──────────────────────────────────────┐                   │
│  │           GPU (上下文切换开销大)       │                   │
│  └──────────────────────────────────────┘                   │
│                                                              │
│  有 MPS:                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Process A │  │ Process B │  │ Process C │                  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘                  │
│        │             │             │                         │
│        ▼             ▼             ▼                         │
│  ┌──────────────────────────────────────┐                   │
│  │     MPS Server (统一调度，减少切换)    │                   │
│  └──────────────────┬───────────────────┘                   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────┐                   │
│  │           GPU (并行执行)              │                   │
│  └──────────────────────────────────────┘                   │
│                                                              │
│  MPS 优势:                                                   │
│  - 多进程共享 GPU，提高利用率                                  │
│  - 减少上下文切换开销                                         │
│  - 支持细粒度资源共享                                         │
│  - 不需要重启 GPU                                             │
│                                                              │
│  MPS 限制:                                                   │
│  - 无硬件级隔离                                               │
│  - 一个进程崩溃可能影响其他进程                                 │
│  - 仅支持 Linux                                              │
│  - 需要 Volta 架构 (V100) 或更新                              │
└──────────────────────────────────────────────────────────────┘
```

```bash
# MPS 管理命令

# 1. 启动 MPS daemon
sudo nvidia-cuda-mps-control -d

# 2. 验证 MPS 运行
ps aux | grep mps

# 3. 设置 MPS 管道目录
export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-log

# 4. 停止 MPS
echo quit | sudo nvidia-cuda-mps-control

# 5. 限制特定进程的 GPU 使用比例（通过 cgroups）
# 这需要配合 CUDA MPS 使用
```

#### 4.3 MIG vs MPS 选择指南

| 场景 | 推荐技术 | 原因 |
|------|----------|------|
| 多租户生产环境 | MIG | 硬件隔离，故障不传播 |
| 同一团队多进程 | MPS | 更高的利用率 |
| LLM 推理 + 训练混合 | MIG | 互不干扰 |
| 开发/测试环境 | MPS | 配置简单 |
| A100/H100 集群 | MIG | 硬件支持好 |
| 消费级 GPU | MPS | 不支持 MIG |

### 5. GPU 监控

#### 5.1 nvidia-smi 详解

```bash
# 1. 基本信息
nvidia-smi
# 输出示例:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 550.54.15    Driver Version: 550.54.15    CUDA Version: 12.4     |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  NVIDIA A100 80GB    On   | 00000000:00:04.0 Off |                    0 |
# | N/A   35C    P0    62W / 300W |  78000MiB / 81920MiB |     85%      Default |
# +-------------------------------+----------------------+----------------------+

# 2. 查询特定字段
nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv

# 3. 持续监控（每秒刷新）
nvidia-smi -l 1
# 或者更灵活的方式
watch -n 1 nvidia-smi

# 4. 查看 GPU 进程
nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv

# 5. 查看 GPU 拓扑（多卡互联）
nvidia-smi topo -m

# 6. 查看 GPU 错误信息
nvidia-smi -q -d ECC
nvidia-smi -q -d TEMPERATURE
nvidia-smi -q -d POWER

# 7. 设置 GPU 持久化模式（减少启动延迟）
sudo nvidia-smi -pm 1

# 8. 设置功耗限制
sudo nvidia-smi -pl 300  # 设置为 300W

# 9. 重置 GPU（紧急情况）
sudo nvidia-smi -r  # 需要无进程使用 GPU
```

#### 5.2 nvidia-smi 输出解读

```
┌──────────────────────────────────────────────────────────────┐
│                nvidia-smi 关键字段解读                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  温度 (Temperature)                                          │
│  ├─ < 60°C: 正常                                             │
│  ├─ 60-80°C: 偏高，关注散热                                   │
│  ├─ 80-90°C: 危险，可能降频                                   │
│  └─ > 90°C: 严重，需要立即处理                                │
│                                                              │
│  功耗 (Power Draw)                                           │
│  ├─ 正常范围: 额定功耗的 30-90%                               │
│  ├─ 接近 TDP: 满载运行                                        │
│  └─ 远低于预期: 可能利用率低或受限                             │
│                                                              │
│  GPU 利用率 (GPU-Util)                                       │
│  ├─ 0%: 空闲                                                 │
│  ├─ 1-50%: 低负载                                            │
│  ├─ 50-85%: 正常工作负载                                      │
│  ├─ 85-100%: 高负载                                          │
│  └─ 持续 100%: 可能需要扩容                                   │
│                                                              │
│  显存使用 (Memory-Usage)                                     │
│  ├─ 已用显存/总显存                                           │
│  ├─ > 90%: 接近 OOM 风险                                     │
│  └─ 注意: 与 nvidia-smi 报告的可能不完全准确                  │
│                                                              │
│  ECC 错误                                                    │
│  ├─ Uncorrectable: 不可修复错误，GPU 可能需要更换              │
│  └─ Correctable: 可修复错误，持续增长需关注                   │
└──────────────────────────────────────────────────────────────┘
```

#### 5.3 DCGM（Data Center GPU Manager）

DCGM 是 NVIDIA 提供的数据中心 GPU 管理和监控工具。

```bash
# 1. 安装 DCGM
# Ubuntu
curl -fsSL https://nvidia.github.io/dcgm/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-dcgm-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/nvidia-dcgm-keyring.gpg] https://nvidia.github.io/dcgm/ubuntu22.04/$(ARCH) /" | sudo tee /etc/apt/sources.list.d/nvidia-dcgm.list
sudo apt-get update
sudo apt-get install -y datacenter-gpu-manager

# 2. 启动 DCGM 服务
sudo systemctl --now enable nvidia-dcgm

# 3. 使用 dcgmi 查看 GPU 信息
dcgmi discovery -l

# 4. 运行 GPU 健康检查
dcgmi diag -r 1  # 级别 1 (快速检查)
dcgmi diag -r 2  # 级别 2 (标准检查)
dcgmi diag -r 3  # 级别 3 (全面检查)

# 5. 查看 GPU 统计信息
dcgmi dmon -e 155,150,151,203,204 -d 1000
# 155 = GPU 利用率
# 150 = 显存使用
# 151 = 显存带宽利用率
# 203 = GPU 温度
# 204 = 功耗

# 6. 配置 GPU 监控字段
dcgmi dmon -c  # 列出所有可用计数器
```

#### 5.4 DCGM Exporter（Prometheus 集成）

```bash
# 1. 使用 Docker 运行 DCGM Exporter
docker run -d --gpus all \
  --name dcgm-exporter \
  -p 9400:9400 \
  -v /proc:/proc:ro \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.8-3.6.0-ubuntu22.04

# 2. 验证指标输出
curl http://localhost:9400/metrics

# 3. 关键指标
# DCGM_FI_DEV_GPU_UTIL          - GPU 利用率
# DCGM_FI_DEV_MEM_COPY_UTIL     - 显存带宽利用率
# DCGM_FI_DEV_SM_ACTIVE         - SM 活跃比例
# DCGM_FI_DEV_SM_OCCUPANCY      - SM 占用率
# DCGM_FI_DEV_TENSOR_ACTIVE     - Tensor Core 活跃比例
# DCGM_FI_DEV_GPU_TEMP          - GPU 温度
# DCGM_FI_DEV_POWER_USAGE       - 功耗
# DCGM_FI_DEV_FB_USED           - 已用显存
# DCGM_FI_DEV_FB_FREE           - 空闲显存
# DCGM_FI_DEV_ECC_VOL_UNCORR    - 不可修复 ECC 错误
```

```yaml
# Prometheus 配置
# prometheus.yml
scrape_configs:
  - job_name: 'dcgm-exporter'
    scrape_interval: 10s
    static_configs:
      - targets: ['dcgm-exporter:9400']
        labels:
          cluster: 'gpu-cluster-01'

  # Grafana Dashboard ID: 12239 (NVIDIA DCGM Exporter Dashboard)
```

#### 5.5 自定义 GPU 监控脚本

```bash
#!/bin/bash
# gpu_monitor.sh - GPU 监控脚本

set -euo pipefail

LOG_FILE="/var/log/gpu_monitor.log"
ALERT_TEMP=85
ALERT_UTIL=95
ALERT_MEM=90

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_gpu_health() {
    local gpu_count
    gpu_count=$(nvidia-smi -L | wc -l)
    log "检测到 $gpu_count 张 GPU"

    local issues=0

    for i in $(seq 0 $((gpu_count - 1))); do
        local info
        info=$(nvidia-smi -i "$i" \
            --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,ecc.errors.corrected.aggregate.total,ecc.errors.uncorrected.aggregate.total \
            --format=csv,noheader,nounits)

        IFS=', ' read -r name temp util mem_used mem_total power ecc_corr ecc_uncorr <<< "$info"

        # 计算显存使用百分比
        local mem_pct=$((mem_used * 100 / mem_total))

        log "GPU $i ($name): Temp=${temp}C Util=${util}% Mem=${mem_used}/${mem_total}MB(${mem_pct}%) Power=${power}W"

        # 温度检查
        if [ "$temp" -gt "$ALERT_TEMP" ]; then
            log "ALERT: GPU $i 温度过高: ${temp}C > ${ALERT_TEMP}C"
            issues=$((issues + 1))
        fi

        # 利用率检查
        if [ "$util" -gt "$ALERT_UTIL" ]; then
            log "WARN: GPU $i 利用率过高: ${util}%"
        fi

        # 显存检查
        if [ "$mem_pct" -gt "$ALERT_MEM" ]; then
            log "ALERT: GPU $i 显存使用过高: ${mem_pct}%"
            issues=$((issues + 1))
        fi

        # ECC 错误检查
        if [ "$ecc_uncorr" -gt 0 ]; then
            log "CRITICAL: GPU $i 存在不可修复 ECC 错误: $ecc_uncorr"
            issues=$((issues + 1))
        fi
    done

    if [ "$issues" -eq 0 ]; then
        log "所有 GPU 状态正常"
    else
        log "发现 $issues 个问题需要关注"
    fi
}

# 主循环
while true; do
    check_gpu_health
    echo "---"
    sleep 60
done
```

### 6. GPU 故障排查

#### 6.1 常见故障分类

```
┌──────────────────────────────────────────────────────────────┐
│                    GPU 常见故障分类                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 硬件故障                                                  │
│  ├─ ECC 错误 (可修复/不可修复)                                │
│  ├─ GPU 掉卡 (GPU 从 PCIe 总线消失)                          │
│  ├─ 温度过高导致降频                                          │
│  └─ 功耗异常                                                  │
│                                                              │
│  2. 驱动/运行时故障                                            │
│  ├─ CUDA 初始化失败                                           │
│  ├─ 驱动版本不兼容                                            │
│  ├─ CUDA OOM (显存不足)                                       │
│  └─ 内核模块加载失败                                          │
│                                                              │
│  3. 推理引擎故障                                              │
│  ├─ 模型加载失败 (格式/版本不兼容)                            │
│  ├─ 推理超时                                                  │
│  ├─ 输出异常 (NaN/Inf)                                       │
│  └─ 内存泄漏                                                  │
│                                                              │
│  4. 集群级故障                                                │
│  ├─ NVLink 通信错误                                           │
│  ├─ NCCL 集合通信超时                                         │
│  ├─ PCIe 带宽瓶颈                                             │
│  └─ 节点间网络问题                                            │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 故障排查流程

```bash
#!/bin/bash
# gpu_troubleshoot.sh - GPU 故障排查脚本

echo "===== GPU 故障排查报告 ====="
echo "时间: $(date)"
echo ""

# 1. 检查驱动状态
echo "--- 驱动信息 ---"
nvidia-smi -q | grep -E "Driver Version|CUDA Version|GPU 0000"
echo ""

# 2. 检查 GPU 可见性
echo "--- GPU 列表 ---"
nvidia-smi -L
echo ""

# 3. 检查 GPU 状态
echo "--- GPU 状态 ---"
nvidia-smi --query-gpu=index,name,temperature.gpu,power.draw,ecc.errors.corrected.aggregate.total,ecc.errors.uncorrected.aggregate.total --format=csv
echo ""

# 4. 检查 dmesg 中的 GPU 错误
echo "--- dmesg GPU 错误 (最近 50 条) ---"
dmesg | grep -i -E "nvidia|gpu|nvrm|cuda" | tail -50
echo ""

# 5. 检查 GPU 进程
echo "--- GPU 进程 ---"
nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv 2>/dev/null || echo "无 GPU 进程"
echo ""

# 6. 检查 PCIe 链路
echo "--- PCIe 链路状态 ---"
nvidia-smi -q -d PCIE
echo ""

# 7. 检查持久化模式
echo "--- 持久化模式 ---"
nvidia-smi -pm 0 2>&1 || echo "无法查询持久化模式"
echo ""

# 8. 检查 CUDA 功能
echo "--- CUDA 功能测试 ---"
python3 -c "
import subprocess
result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader'],
                       capture_output=True, text=True)
print('GPU 利用率:', result.stdout.strip())
" 2>/dev/null || echo "Python 不可用"

# 9. 检查 ECC 错误详情
echo "--- ECC 错误详情 ---"
nvidia-smi -q -d ECC 2>/dev/null | grep -A5 "ECC Errors" || echo "ECC 信息不可用"
echo ""

echo "===== 排查完成 ====="
```

#### 6.3 常见问题处理

| 问题 | 排查命令 | 解决方案 |
|------|----------|----------|
| GPU OOM | `nvidia-smi` 查看显存 | 减小 batch size / 使用量化 / 增加 GPU |
| GPU 掉卡 | `dmesg \| grep NVRM` | 检查 PCIe 连接，可能需要更换硬件 |
| 温度过高 | `nvidia-smi -q -d TEMPERATURE` | 检查散热，清理风扇，降低功耗限制 |
| ECC 错误 | `nvidia-smi -q -d ECC` | 不可修复错误需更换 GPU |
| 驱动不兼容 | `nvidia-smi` + `nvcc --version` | 更新驱动或 CUDA 版本 |
| 推理卡住 | `nvidia-smi` 查看进程 | 检查 CUDA 错误日志，重启服务 |
| 利用率低 | `dcgmi dmon` | 检查批处理大小，开启 MPS |

---

## 💻 实战练习

### 练习 1：GPU 环境搭建与验证

**目标**：在一台有 GPU 的机器上完成 NVIDIA 驱动和 CUDA 的安装验证。

```bash
# 1. 验证 GPU 硬件
echo "=== GPU 硬件信息 ==="
lspci | grep -i nvidia

# 2. 验证驱动版本
echo "=== 驱动信息 ==="
nvidia-smi --query-gpu=driver_version,cuda_version --format=csv,noheader

# 3. 验证 CUDA 工具链
echo "=== CUDA 版本 ==="
nvcc --version

# 4. 验证 Docker GPU 支持
echo "=== Docker GPU 测试 ==="
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 5. 验证 Python CUDA 支持
echo "=== PyTorch CUDA 测试 ==="
python3 -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
print(f'CUDA 版本: {torch.version.cuda}')
print(f'GPU 数量: {torch.cuda.device_count()}')
for i in range(torch.cuda.device_count()):
    print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
    print(f'    显存: {torch.cuda.get_device_properties(i).total_mem / 1e9:.1f} GB')
"

# 6. 运行 GPU 健康检查
echo "=== GPU 健康检查 ==="
nvidia-smi -q -d TEMPERATURE,POWER,ECC
```

### 练习 2：GPU 监控 Dashboard 搭建

**目标**：使用 DCGM Exporter + Prometheus + Grafana 搭建 GPU 监控面板。

```yaml
# docker-compose-gpu-monitoring.yml
version: '3.8'

services:
  # GPU 指标导出器
  dcgm-exporter:
    image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.8-3.6.0-ubuntu22.04
    runtime: nvidia
    environment:
      - DCGM_EXPORTER_LISTEN_ADDRESS=:9400
    ports:
      - "9400:9400"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # Prometheus 采集
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

  # Grafana 可视化
  grafana:
    image: grafana/grafana:10.4.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"

volumes:
  prometheus_data:
  grafana_data:
```

```yaml
# prometheus.yml
global:
  scrape_interval: 10s

scrape_configs:
  - job_name: 'dcgm-exporter'
    static_configs:
      - targets: ['dcgm-exporter:9400']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

```bash
# 启动监控栈
docker compose -f docker-compose-gpu-monitoring.yml up -d

# 验证指标采集
curl http://localhost:9400/metrics | head -20

# Grafana 中导入 Dashboard ID: 12239
# 访问 http://localhost:3000 (admin/admin123)
```

### 练习 3：MIG 分区与资源隔离

**目标**：在 A100/H100 上配置 MIG，实现多模型资源隔离。

```bash
#!/bin/bash
# mig_setup.sh - MIG 分区配置脚本

GPU_ID=0

echo "=== MIG 分区配置 ==="

# 1. 检查 MIG 支持
echo "检查 MIG 支持..."
nvidia-smi -i $GPU_ID --query-gpu=mig.mode.current --format=csv,noheader

# 2. 启用 MIG
echo "启用 MIG..."
sudo nvidia-smi -i $GPU_ID -mig 1

# 3. 查看可用的 MIG 配置
echo "可用 MIG 配置:"
nvidia-smi mig -lgip -i $GPU_ID

# 4. 创建 MIG 实例
# 方案: 创建 2 个 1g.10gb 实例（用于小模型）+ 1 个 3g.20gb 实例（用于中等模型）
echo "创建 MIG 实例..."
sudo nvidia-smi mig -cgi 9,9,15 -C -i $GPU_ID
# 9  = 1g.10gb (1/7 GPU + 10GB)
# 15 = 3g.20gb (3/7 GPU + 20GB)

# 5. 查看创建的实例
echo "已创建的 MIG 实例:"
nvidia-smi mig -lgi -i $GPU_ID

# 6. 查看 MIG 设备
echo "MIG 设备列表:"
nvidia-smi -L

# 7. 测试隔离性
echo "测试: 在 MIG 实例上运行进程..."
CUDA_VISIBLE_DEVICES=MIG-GPU-xxxx ./your_inference_process &
```

---

## 🎯 面试题精选

### 1. 解释 GPU 的 SM、CUDA Core、Tensor Core 的关系和作用。

**参考答案**：
- **SM（Streaming Multiprocessor）**：GPU 的基本计算单元，包含多个 CUDA Core、Tensor Core、共享内存等。一个 GPU 由多个 SM 组成（如 A100 有 108 个 SM）。
- **CUDA Core**：SM 中的通用计算核心，执行 FP32、INT32 等标量运算。每个 SM 有 64 个 CUDA Core（A100）。
- **Tensor Core**：SM 中的矩阵运算加速器，专门执行矩阵乘累加运算（D = A×B + C）。每个 SM 有 4 个 Tensor Core（A100 第3代），一个周期可完成 4×4×4 矩阵乘法。

关系：SM 是容器，CUDA Core 和 Tensor Core 是其中的计算单元。LLM 推理主要依赖 Tensor Core 进行矩阵运算加速。

### 2. LLM 推理时显存主要被什么占用？如何估算显存需求？

**参考答案**：
显存主要由四部分组成：
1. **模型权重**：参数量 × 数据类型大小。如 70B 模型 FP16 需要 140GB。
2. **KV Cache**：与层数、隐藏维度、序列长度、batch size 成正比。动态增长，是并发瓶颈。
3. **激活值**：推理时前向传播的中间结果，通常数百 MB。
4. **CUDA 运行时开销**：CUDA Context 和 cuBLAS workspace，约 1-2GB。

估算公式：总显存 ≈ 模型权重 + KV Cache + 2GB（开销）。KV Cache = 2 × 层数 × 头数 × 头维度 × 序列长度 × batch × 数据类型大小。

### 3. MIG 和 MPS 的区别是什么？各自适用于什么场景？

**参考答案**：
- **MIG（Multi-Instance GPU）**：硬件级分区，将一个物理 GPU 划分为多个独立实例，每个实例有独立的显存、缓存、计算资源。适用于多租户生产环境，提供强隔离。需要 A100/H100，配置变更需重启 GPU。
- **MPS（Multi-Process Service）**：软件级共享，多个进程通过 MPS Server 共享同一个 GPU。适用于同一团队的多进程场景，提高利用率。无硬件隔离，一个进程崩溃可能影响其他。

选择：多租户/不同团队用 MIG；同团队多进程用 MPS。

### 4. 如何排查 GPU OOM（显存不足）问题？

**参考答案**：
1. 使用 `nvidia-smi` 查看当前显存使用和进程
2. 检查是否是模型太大（参数量 × 数据类型 > 显存）
3. 检查 KV Cache 是否增长过大（长上下文或大 batch）
4. 检查是否有显存泄漏（显存使用随时间单调增长）
5. 解决方案：减小 batch size、使用量化（INT4/INT8）、使用张量并行（多 GPU）、限制上下文长度、使用 vLLM 的显存管理（PagedAttention）

### 5. 什么是 ECC 错误？如何处理？

**参考答案**：
ECC（Error Correcting Code）错误是 GPU 显存中的位翻转错误。
- **可修复 ECC 错误**：硬件自动纠正，不影响计算正确性，但持续增长可能预示硬件退化。
- **不可修复 ECC 错误**：无法自动纠正，可能导致计算结果错误或 GPU 故障。

处理方式：
1. 使用 `nvidia-smi -q -d ECC` 检查错误计数
2. 可修复错误：监控趋势，持续增长需关注
3. 不可修复错误：立即将该 GPU 从服务中移除，安排硬件更换
4. 生产环境建议启用 ECC（牺牲少量性能换取数据完整性）

### 6. 如何在 Kubernetes 中实现 GPU 资源的高效调度？

**参考答案**：
1. **安装 NVIDIA Device Plugin**：让 K8s 识别 GPU 资源
2. **使用 nodeSelector/nodeAffinity**：将 GPU Pod 调度到 GPU 节点
3. **配置资源请求**：使用 `nvidia.com/gpu` 资源请求
4. **使用 MIG**：在 A100/H100 上配置 MIG，提供更细粒度的 GPU 资源
5. **GPU 共享**：使用 MPS 或 Time-sharing 让多个 Pod 共享 GPU
6. **拓扑感知调度**：使用 GPU Topology 调度器，确保多卡 Pod 调度到 NVLink 互联的 GPU 上
7. **优先级和抢占**：使用 PriorityClass 区分训练和推理任务

### 7. 什么是 GPU 持久化模式？为什么推荐在生产环境开启？

**参考答案**：
GPU 持久化模式（Persistence Mode）让 NVIDIA 驱动保持加载状态，即使没有 CUDA 应用在运行。

默认情况下，驱动会在最后一个 CUDA 应用退出后卸载，下一个应用启动时重新加载。重新加载需要初始化 CUDA Context，耗时数秒。

生产环境推荐开启的原因：
- 减少 CUDA 应用启动延迟（从数秒降到毫秒）
- 避免驱动加载/卸载的开销
- `nvidia-smi` 始终可用来监控
- 开启方式：`sudo nvidia-smi -pm 1`

---

## 📚 深入阅读

### 官方文档
- [NVIDIA CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/) - CUDA 编程指南
- [NVIDIA Data Center GPU Manager](https://docs.nvidia.com/datacenter/dcgm/latest/) - DCGM 官方文档
- [NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/) - MIG 配置指南
- [NVIDIA MPS Documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/ops/mps.html) - MPS 使用指南
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) - Docker GPU 支持

### 工具
- [DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter) - GPU 指标导出到 Prometheus
- [nvidia-smi 手册](https://developer.download.nvidia.com/compute/DCGM/docs/nvidia-smi-367.38.pdf) - 完整命令参考
- [GPU Burn](https://github.com/wilicc/gpu-burn) - GPU 压力测试工具

### 博客
- [Understanding the GPU Architecture](https://developer.nvidia.com/blog/cuda-refresher-cuda-programming-model/) - NVIDIA 官方博客
- [GPU Memory Deep Dive](https://www.telesens.co/2019/07/14/gpu-memory-deep-dive/) - 显存深度解析

---

## ✅ 自检清单

- [ ] 能解释 GPU 的 SM、CUDA Core、Tensor Core 的关系
- [ ] 能估算给定模型的显存需求
- [ ] 能安装和验证 NVIDIA 驱动和 CUDA
- [ ] 能在 Docker 和 Kubernetes 中配置 GPU 支持
- [ ] 能使用 nvidia-smi 查看和解读 GPU 状态
- [ ] 能使用 DCGM 和 DCGM Exporter 监控 GPU
- [ ] 能配置 MIG 实现 GPU 资源隔离
- [ ] 能配置 MPS 实现 GPU 共享
- [ ] 能排查常见的 GPU 故障（OOM、温度、ECC）
- [ ] 完成了至少 2 个实战练习

---

*由 SRE 学习计划生成 | 2026-05-03*
