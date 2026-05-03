# LLM SRE 16：推理引擎与服务架构

> 📅 日期：2026-05-03
> 📖 学习主题：推理引擎选型、服务架构设计与部署模式
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：10-llm-lifecycle-overview.md, Kubernetes 基础, 容器技术

## 🎯 学习目标

完成本章学习后，你应该能够：

- 对比 vLLM、SGLang、TGI、Triton Inference Server、TensorRT-LLM 五种推理引擎的定位、优势、风险与适用场景，并给出选型决策框架
- 设计并解释 6 层推理平台架构（接入层、控制层、引擎层、模型/缓存层、基础设施层、观测/治理层）中每一层的职责与关键组件
- 实现单模型专用部署、多模型共享部署、多 LoRA 动态加载三种部署方案，并说明各自的容量规划与隔离策略
- 诊断并修复冷启动过长、模型加载失败、路由异常、LoRA 缓存失效等架构层问题
- 为推理平台制定可观测性信号暴露规范，覆盖体验指标、引擎指标、平台指标和基础设施指标

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 推理引擎对比

推理引擎是整个推理平台的核心执行层。不同引擎的核心差别不只在 benchmark 数字，而在于它们把优化点放在哪一层：有的强调通用高吞吐服务化，有的强调编译优化和极致性能，有的更适合复杂模型编排或企业内统一 serving 平台。

**引擎定位图**

```text
                        通用性 / 易用性
                            ^
                            |
               TGI ---------+--------- vLLM
              (HF 生态,      |      (OpenAI 兼容,
               稳妥平台化)    |       PagedAttention,
                             |       Continuous Batching)
                             |
                             |
          Triton ------------+------------- SGLang
         (多框架统一,         |           (RadixAttention,
          企业模型平台)        |            结构化生成,
                             |            推理工作流)
                             |
                             +-------------------------> 极致性能
                             |
                      TensorRT-LLM
                    (编译优化, 硬件绑定,
                     最高吞吐/最低延迟)
```

**各引擎详细对比**

| 维度 | vLLM | SGLang | TGI | Triton Inference Server | TensorRT-LLM |
| --- | --- | --- | --- | --- | --- |
| 核心技术 | PagedAttention, Continuous Batching | RadixAttention, 结构化生成引擎 | Hugging Face 生态集成, 流式输出 | 多框架 Model Ensemble, 动态 batching | NVIDIA 编译优化, FP8/INT4 量化 |
| API 兼容性 | OpenAI 兼容, 支持 Chat/Completion/Embedding | OpenAI 兼容, 额外支持推理 DSL | 自有 API + OpenAI 兼容层 | gRPC/HTTP 自有协议, 可封装 OpenAI 兼容层 | 需自建或配合 Triton 暴露 API |
| 吞吐表现 | 高, 长上下文场景优势明显 | 高, 结构化生成场景更优 | 中高, 稳定可靠 | 中高, 取决于后端引擎配置 | 最高, 编译后极致优化 |
| 易用性 | 高, pip install 即可启动 | 中高, 需理解 RadixAttention 模型 | 高, Docker 一键部署 | 中, 配置复杂, 需理解 Model Repository | 低, 构建链路长, 版本硬件耦合深 |
| 生态成熟度 | 高, 社区活跃, 版本迭代快 | 中, 快速成长, 但运维沉淀较少 | 高, Hugging Face 官方维护 | 高, NVIDIA 企业支持 | 高, NVIDIA 官方, 但使用门槛高 |
| 多模型支持 | 支持, 通过多实例或多引擎 | 支持, RadixAttention 共享前缀 | 支持, 多实例部署 | 原生支持, Model Repository 管理 | 支持, 但每模型需独立编译 |
| 多 LoRA 支持 | 原生支持, 运行时动态加载 | 支持, 前缀缓存可跨 LoRA 复用 | 支持, 但灵活性不如 vLLM | 需自建适配层 | 支持, 但编译链路复杂 |
| 运维代价 | 中, 版本升级频繁需关注兼容性 | 中, 需理解其调度模型 | 低, 部署心智负担小 | 高, 平台复杂度高 | 高, 构建、调试、回滚成本高 |
| 适用场景 | 通用文本生成平台, 高吞吐共享集群 | 结构化生成, 推理工作流, 前缀复用 | HF 模型仓库为中心的稳妥平台 | 企业统一模型平台, 多框架混合服务 | 稳定模型版本, 固定硬件池, 强性能目标 |

**选型决策框架**

选型时不要只看"单卡 tokens/s"。真正重要的是四个问题：

1. 是否能稳定暴露 TTFT/TPOT/TPS 指标？没有这些指标，SRE 无法做容量规划和告警。
2. 是否支持你的多租户治理模型？能否按租户、模型、优先级做资源隔离？
3. 是否便于发布回滚？模型版本切换是否需要重新编译？是否支持灰度？
4. 是否能让值班人员快速定位问题？错误信息是否清晰？日志是否结构化？

```text
选型决策树：

需要统一托管多种框架模型（LLM + CV + ASR）？
  |-- 是 --> Triton Inference Server
  |-- 否 --> 对性能有极致要求且模型版本稳定、硬件池固定？
               |-- 是 --> TensorRT-LLM
               |-- 否 --> 需要结构化生成 / 推理工作流 / 前缀复用？
                            |-- 是 --> SGLang
                            |-- 否 --> 以 HF 生态为中心、追求稳妥平台化？
                                         |-- 是 --> TGI
                                         |-- 否 --> vLLM（通用默认选择）
```

#### 1.2 六层推理平台架构

一个可运营的推理平台远不止"若干 Pod + GPU"。它是对外承诺延迟与可用性、对内管理显存与并发、对上承接租户策略、对下消化模型和硬件差异的控制系统。

**六层架构总览图**

```text
┌─────────────────────────────────────────────────────────────────┐
│                        客户端 / SDK / 应用                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 1 层：接入层                                                │
│  API Gateway / 负载均衡 / TLS 终止 / 鉴权 / 请求规范化          │
│  组件：Nginx / Envoy / Kong / APISIX / 云厂商 LB               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 2 层：控制层                                                │
│  模型路由 / 租户策略 / 限流 / 配额 / 优先级 / 灰度发布          │
│  组件：自研路由服务 / Istio VirtualService / K8s Gateway API    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 3 层：引擎层                                                │
│  推理引擎实例池 / 模型服务 Pod / GPU Worker                     │
│  组件：vLLM / SGLang / TGI / Triton / TensorRT-LLM             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 4 层：模型与缓存层                                          │
│  模型权重管理 / LoRA 适配器仓库 / KV Cache / Prefix Cache       │
│  组件：对象存储 / NFS / 本地 SSD / 共享内存                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 5 层：基础设施层                                            │
│  GPU 节点 / CPU 节点 / RDMA 网络 / 存储 / 容器编排              │
│  组件：K8s + GPU Operator / NVIDIA DCGM / 节点池管理            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               v
┌─────────────────────────────────────────────────────────────────┐
│  第 6 层：观测与治理层                                          │
│  指标 / 日志 / 链路追踪 / 审计 / 告警 / 成本分摊               │
│  组件：Prometheus / Grafana / Loki / Jaeger / OpenTelemetry     │
└─────────────────────────────────────────────────────────────────┘
```

**各层职责详解**

**第 1 层：接入层**

接入层是推理平台的门面，所有外部请求从此进入。职责包括：

- TLS 终止与证书管理
- 身份认证（API Key、JWT、OAuth2）
- 请求规范化（统一请求格式、版本适配）
- 负载均衡（轮询、最少连接、一致性哈希）
- 请求体大小限制与超时控制

关键设计原则：接入层不应理解模型语义。它只负责"谁能进来"和"往哪转发"，不负责"用哪个模型版本"。

**第 2 层：控制层**

控制层是推理平台的大脑，决定每个请求的去向。职责包括：

- 模型路由：根据请求中的 model 字段选择后端引擎池
- 租户策略：按租户分配配额、并发上限、优先级
- 限流与背压：令牌桶限流、并发限流、队列溢出保护
- 灰度发布：按比例、按租户、按请求特征分流到不同版本
- 回退策略：模型不可用时降级到备用模型或拒绝低优先级请求

关键设计原则：控制层的路由决策必须可审计。每个请求都应能回答"为什么被送到这个后端"。

**第 3 层：引擎层**

引擎层是推理平台的执行核心，负责将请求转化为 token 流。职责包括：

- 模型加载与初始化
- 请求调度与 batching
- KV Cache 管理与 Prefix Cache 复用
- 流式输出与增量 token 返回
- GPU 显存管理与 OOM 保护

关键设计原则：引擎层应暴露标准化的健康检查端点（/health、/ready）和结构化指标，供上层做路由决策。

**第 4 层：模型与缓存层**

模型与缓存层管理推理所需的数据资产。职责包括：

- 模型权重版本管理与分发
- LoRA 适配器仓库与动态加载
- KV Cache 生命周期管理（分配、复用、淘汰、换出）
- Prefix Cache 管理（跨请求的 prompt 前缀复用）
- Tokenizer 与配置文件管理

关键设计原则：权重文件应就近缓存。从远端对象存储拉取 70B 模型权重可能需要 5-10 分钟，而从本地 SSD 加载只需 30-60 秒。

**第 5 层：基础设施层**

基础设施层提供推理所需的物理资源。职责包括：

- GPU 节点池管理（机型选择、驱动版本、MIG 配置）
- RDMA/InfiniBand 网络配置（多卡推理场景）
- 存储管理（本地 SSD、NFS、对象存储）
- 容器编排（K8s + GPU Operator + 节点亲和性）
- 自动扩缩容（基于 GPU 利用率、队列深度、自定义指标）

关键设计原则：GPU 节点是稀缺资源。基础设施层应支持节点池分级：高优池（低延迟、预留）、标准池（常规流量）、批处理池（离线任务）。

**第 6 层：观测与治理层**

观测与治理层为前五层提供可见性和控制力。职责包括：

- 指标采集与可视化（Prometheus + Grafana）
- 日志聚合与检索（Loki / ELK）
- 链路追踪（Jaeger / OpenTelemetry）
- 告警规则与通知（Alertmanager / PagerDuty）
- 审计日志（谁在什么时候访问了什么模型）
- 成本分摊（按租户、按模型、按请求量）

关键设计原则：观测层必须能按模型、租户、实例、LoRA 适配器和发布版本切片查看指标。全局平均值会掩盖长尾问题。

#### 1.3 请求处理流程

理解一个请求从客户端到 GPU 再到响应的完整路径，是做架构诊断的基础。

**请求处理全流程图**

```text
客户端发起请求
    │
    │  POST /v1/chat/completions
    │  {"model": "qwen-72b", "messages": [...], "stream": true}
    │
    v
[接入层] API Gateway
    │  1. TLS 终止
    │  2. 提取 API Key, 验证身份
    │  3. 检查请求体大小 (< 10MB)
    │  4. 转发到控制层
    v
[控制层] 路由服务
    │  1. 解析 model 字段 -> "qwen-72b"
    │  2. 查询路由表 -> qwen-72b-pool (vLLM 实例池)
    │  3. 检查租户配额 (当前租户: 已用 8000/10000 tokens/min)
    │  4. 检查优先级 -> P1 (高优)
    │  5. 选择健康实例 -> pod-qwen-72b-3 (最少连接策略)
    │  6. 记录路由决策到 tracing span
    v
[引擎层] vLLM 实例 (pod-qwen-72b-3)
    │  1. 接收请求, 解析参数
    │  2. 查找 Prefix Cache -> 命中前 128 tokens
    │  3. 加入 waiting queue
    │  4. Continuous Batching 调度器合并请求
    │  5. KV Cache 分配 (PagedAttention)
    │  6. 模型前向计算 (GPU)
    │  7. 采样, 生成 token
    │  8. 流式返回 SSE chunk
    v
[缓存层] KV Cache / Prefix Cache
    │  - PagedAttention 按页分配显存
    │  - Prefix Cache 命中时跳过已计算的 prompt tokens
    │  - 缓存淘汰: LRU + 显存水位触发
    v
[基础设施层] GPU 节点
    │  - NVIDIA A100 80GB x 8
    │  - PCIe/NVLink 互联
    │  - CUDA 12.4 + cuDNN 9.x
    v
响应逐 chunk 返回客户端
    │  data: {"choices":[{"delta":{"content":"你"}}]}
    │  data: {"choices":[{"delta":{"content":"好"}}]}
    │  data: [DONE]
```

#### 1.4 部署模式

推理平台的部署模式直接影响资源利用率、隔离性和运维复杂度。SRE 需要根据业务特征选择合适的模式。

**三种部署模式对比图**

```text
模式 1：单模型专用部署
┌─────────────────────────────────────┐
│  模型 A 专用池                      │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │vLLM    │ │vLLM    │ │vLLM    │  │
│  │实例 1  │ │实例 2  │ │实例 3  │  │
│  │模型 A  │ │模型 A  │ │模型 A  │  │
│  └────────┘ └────────┘ └────────┘  │
│  优点: 隔离性好, SLO 有保障          │
│  缺点: 资源利用率低, 碎片明显        │
└─────────────────────────────────────┘

模式 2：多模型共享部署
┌─────────────────────────────────────┐
│  共享池                             │
│  ┌──────────────────────────────┐  │
│  │  vLLM 实例 (模型 A + 模型 B) │  │
│  │  模型按需加载, 显存共享       │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  vLLM 实例 (模型 C + 模型 D) │  │
│  │  冷模型换入换出               │  │
│  └──────────────────────────────┘  │
│  优点: 资源利用率高                  │
│  缺点: 冷切换延迟, 显存争用          │
└─────────────────────────────────────┘

模式 3：基座模型 + 多 LoRA 部署
┌─────────────────────────────────────┐
│  基座模型池 (模型 A base)           │
│  ┌──────────────────────────────┐  │
│  │  vLLM 实例                    │  │
│  │  基座模型 A (常驻显存)         │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐    │  │
│  │  │LoRA1│ │LoRA2│ │LoRA3│    │  │
│  │  │(热) │ │(热) │ │(冷) │    │  │
│  │  └─────┘ └─────┘ └─────┘    │  │
│  └──────────────────────────────┘  │
│  优点: 灵活, 变体成本低              │
│  缺点: 适配器管理复杂, 冷 LoRA 抖动  │
└─────────────────────────────────────┘
```

**部署模式选型建议**

| 场景 | 推荐模式 | 理由 |
| --- | --- | --- |
| 主力模型, 严格 SLO | 单模型专用 | 隔离性最好, 延迟可预测 |
| 长尾模型, 低流量 | 多模型共享 | 提升利用率, 降低成本 |
| 行业定制, 租户定制 | 基座 + 多 LoRA | 变体成本低, 切换灵活 |
| A/B 测试, 灰度发布 | 单模型多版本 | 流量隔离, 便于对比 |
| 实验流量, 快速迭代 | 多模型共享 | 快速部署, 资源共享 |

#### 1.5 冷启动与预热

推理平台的冷启动远比普通 Web 服务昂贵。一个 70B 模型的冷启动可能包含以下阶段：

**冷启动全流程图**

```text
时间轴 (秒) -->
0s        10s       30s       60s       90s       120s      150s
|---------|---------|---------|---------|---------|---------|
│         │         │         │         │         │         │
v         v         v         v         v         v         v

[阶段 1]  [阶段 2]  [阶段 3]  [阶段 4]  [阶段 5]  [阶段 6]  [就绪]
容器创建   镜像拉取   权重加载   显存分配   图编译     预热请求
Pod       Docker    从存储     分配GPU    CUDA      发送合成
调度到    层下载     拉取权重   显存给     Kernel    请求预热
节点      (可缓存)  到内存     模型参数   编译       Prefix
                                      +CUDA      Cache
                                      Graph
                                      捕获

总耗时: 70B 模型约 120-180s, 7B 模型约 20-40s

优化手段:
  |-- [阶段 1-2] 预拉镜像到节点, 使用本地镜像缓存
  |-- [阶段 3]   权重预缓存到本地 SSD, 使用 NFS 就近存储
  |-- [阶段 4]   预分配显存池, 避免运行时碎片
  |-- [阶段 5]   使用 torch.compile 缓存, 跳过重复编译
  |-- [阶段 6]   预热请求覆盖典型上下文长度
```

**冷启动优化策略清单**

| 优化阶段 | 策略 | 效果 | 实施复杂度 |
| --- | --- | --- | --- |
| 容器创建 | 使用轻量基础镜像, 减少层大小 | 减少 5-15s | 低 |
| 镜像拉取 | 节点级镜像缓存, ImagePolicy 预拉取 | 消除镜像拉取时间 | 中 |
| 权重加载 | 本地 SSD 缓存, NFS 就近存储 | 减少 30-60s | 中 |
| 显存分配 | 预分配显存池, 使用 CUDA memory pool | 减少 2-5s | 低 |
| 图编译 | torch.compile 缓存, CUDA Graph 复用 | 减少 10-30s | 中 |
| 预热请求 | 合成请求覆盖典型长度, Prefix Cache 预热 | 减少首次请求延迟 | 中 |
| 扩容策略 | 分批拉实例, 避免同时争抢资源 | 减少资源争抢 | 低 |

**K8s 探针配置**

区分 startupProbe、readinessProbe 和 livenessProbe 至关重要：

- startupProbe：模型是否完成加载？在加载完成前，其他探针不生效。
- readinessProbe：模型是否准备好接收流量？应测试实际推理能力。
- livenessProbe：引擎进程是否健康？只检查进程存活，不检查推理能力。

#### 1.6 多 LoRA 部署详解

多 LoRA 部署是推理平台灵活性的关键能力，但也引入了新的运维挑战。

**多 LoRA 架构图**

```text
                     请求: {"model": "qwen-72b-legal", ...}
                                      |
                                      v
                              ┌───────────────┐
                              │   路由控制面    │
                              │ 解析模型名:    │
                              │ qwen-72b-legal │
                              │ -> 基座: qwen-72b
                              │ -> LoRA: legal  │
                              └───────┬───────┘
                                      |
                                      v
                    ┌─────────────────────────────────────┐
                    │         vLLM 实例池                   │
                    │                                      │
                    │  ┌─────────────────────────────────┐ │
                    │  │     基座模型: qwen-72b (常驻)    │ │
                    │  │     显存占用: ~140 GB (FP16)     │ │
                    │  ├─────────────────────────────────┤ │
                    │  │  LoRA 适配器缓存 (LRU):         │ │
                    │  │  ┌───────┐ ┌───────┐ ┌───────┐ │ │
                    │  │  │legal  │ │medical│ │finance│ │ │
                    │  │  │(2 GB) │ │(2 GB) │ │(2 GB) │ │ │
                    │  │  │命中x3 │ │命中x1 │ │未命中 │ │ │
                    │  │  └───────┘ └───────┘ └───────┘ │ │
                    │  └─────────────────────────────────┘ │
                    │                                      │
                    │  缓存策略: LRU, 最多保留 10 个适配器  │
                    │  淘汰策略: 显存水位 > 90% 时触发       │
                    └─────────────────────────────────────┘
```

**多 LoRA 运维挑战**

| 挑战 | 描述 | 应对策略 |
| --- | --- | --- |
| 冷 LoRA 加载延迟 | 首次加载适配器需从存储拉取, 增加 TTFT | 热点 LoRA 预加载到实例, LRU 缓存 |
| 显存容量规划 | 基座 + N 个 LoRA 的显存需求不确定 | 限制单实例 LoRA 数量, 显存水位监控 |
| 版本兼容性 | LoRA 与基座版本不匹配导致推理错误 | 制品发布流水线强制兼容性检查 |
| 缓存命中率下降 | 长尾 LoRA 挤占缓存空间 | LRU + 频率权重, 热点分离 |
| 扩容后缓存冷 | 新实例没有 LoRA 缓存 | 分批扩容 + LoRA 预热策略 |

### 2. 命令/工具详解

#### 2.1 vLLM 启动与配置

**基础启动命令**

```bash
# 最小启动：单卡部署 Qwen2.5-7B
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code

# 生产级启动：多卡张量并行 + 完整参数
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-72B-Instruct \
    --tensor-parallel-size 4 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 256 \
    --max-num-batched-tokens 65536 \
    --dtype auto \
    --quantization awq \
    --enforce-eager false \
    --enable-prefix-caching \
    --disable-log-requests \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name qwen-72b \
    --api-key sk-your-api-key-here
```

**vLLM 关键参数说明**

| 参数 | 说明 | 生产建议 |
| --- | --- | --- |
| --tensor-parallel-size | 张量并行度（使用几张 GPU） | 模型参数量 / 单卡显存，向上取整 |
| --max-model-len | 最大上下文长度 | 按业务需求设置，越长 KV Cache 占用越大 |
| --gpu-memory-utilization | GPU 显存利用率上限 | 0.85-0.92，留余量防 OOM |
| --max-num-seqs | 最大并发序列数 | 根据显存和延迟目标调优 |
| --max-num-batched-tokens | 单 batch 最大 token 数 | 影响吞吐上限 |
| --enable-prefix-caching | 启用 Prefix Cache | 多轮对话场景强烈建议开启 |
| --enforce-eager | 禁用 CUDA Graph | 调试时开启，生产关闭以提升性能 |
| --quantization | 量化方式 | awq/gptq/fp8，按硬件支持选择 |

**多 LoRA 启动配置**

```bash
# 启用 LoRA 支持
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-72B-Instruct \
    --tensor-parallel-size 4 \
    --enable-lora \
    --max-lora-rank 64 \
    --max-loras 8 \
    --max-cpu-loras 32 \
    --lora-modules \
        legal=/models/lora/qwen-72b-legal \
        medical=/models/lora/qwen-72b-medical \
        finance=/models/lora/qwen-72b-finance \
    --host 0.0.0.0 \
    --port 8000

# 使用 LoRA 发送请求
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "legal",
    "messages": [{"role": "user", "content": "分析这份合同的风险条款"}],
    "max_tokens": 1024
  }'
```

#### 2.2 SGLang 启动与配置

```bash
# 基础启动
python -m sglang.launch_server \
    --model-path Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 30000 \
    --trust-remote-code

# 生产级启动：启用 RadixAttention + 前缀缓存
python -m sglang.launch_server \
    --model-path Qwen/Qwen2.5-72B-Instruct \
    --tp 4 \
    --mem-fraction-static 0.88 \
    --max-running-requests 256 \
    --max-total-tokens 131072 \
    --chunked-prefill-size 8192 \
    --schedule-policy lpm \
    --host 0.0.0.0 \
    --port 30000

# 使用结构化生成 (JSON mode)
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "提取以下文本中的实体"}],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "entities",
        "schema": {
          "type": "object",
          "properties": {
            "persons": {"type": "array", "items": {"type": "string"}},
            "organizations": {"type": "array", "items": {"type": "string"}},
            "locations": {"type": "array", "items": {"type": "string"}}
          }
        }
      }
    }
  }'
```

**SGLang 关键参数说明**

| 参数 | 说明 | 生产建议 |
| --- | --- | --- |
| --tp | 张量并行度 | 与 vLLM 类似 |
| --mem-fraction-static | 静态显存分配比例 | 0.85-0.92 |
| --max-running-requests | 最大运行请求数 | 根据显存和延迟目标 |
| --schedule-policy | 调度策略 | lpm (longest prefix match) 适合多轮对话 |
| --chunked-prefill-size | 分块预填充大小 | 8192, 平衡首 token 延迟和吞吐 |

#### 2.3 TGI 启动与配置

```bash
# Docker 一键部署
docker run --gpus all \
    -p 8080:80 \
    -v /data/models:/data \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id Qwen/Qwen2.5-7B-Instruct \
    --max-input-tokens 4096 \
    --max-total-tokens 8192 \
    --max-batch-prefill-tokens 4096 \
    --max-concurrent-requests 128

# Kubernetes 部署 (Helm)
helm repo add text-generation-inference https://huggingface.github.io/text-generation-inference/
helm install tgi text-generation-inference/text-generation-inference \
    --set model.id=Qwen/Qwen2.5-72B-Instruct \
    --set resources.limits.nvidia.com/gpu=4 \
    --set volume.mounts=/data/models \
    --set env.HF_HUB_CACHE=/data/cache
```

#### 2.4 OpenAI 兼容 API 测试

```bash
# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# Chat Completion (非流式)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -d '{
    "model": "qwen-72b",
    "messages": [
      {"role": "system", "content": "你是一个有用的助手"},
      {"role": "user", "content": "解释什么是 PagedAttention"}
    ],
    "max_tokens": 512,
    "temperature": 0.7
  }'

# Chat Completion (流式)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -d '{
    "model": "qwen-72b",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 128,
    "stream": true
  }'

# Embedding
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-large-zh",
    "input": ["测试文本"]
  }'
```

#### 2.5 K8s 健康检查与探针配置

```yaml
# vLLM Deployment with probes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-qwen-72b
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm-qwen-72b
  template:
    metadata:
      labels:
        app: vllm-qwen-72b
        model: qwen-72b
        version: v1
    spec:
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.6.6
          args:
            - "--model"
            - "Qwen/Qwen2.5-72B-Instruct"
            - "--tensor-parallel-size"
            - "4"
            - "--max-model-len"
            - "32768"
            - "--gpu-memory-utilization"
            - "0.90"
            - "--enable-prefix-caching"
          ports:
            - containerPort: 8000
              name: http
          # startupProbe: 模型加载可能很慢，给足时间
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 30  # 最多等 300s
          # readinessProbe: 模型准备好接收流量
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 5
            failureThreshold: 3
          # livenessProbe: 进程是否存活
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 15
            failureThreshold: 5
          resources:
            limits:
              nvidia.com/gpu: 4
              memory: "128Gi"
            requests:
              nvidia.com/gpu: 4
              memory: "96Gi"
          volumeMounts:
            - name: model-cache
              mountPath: /root/.cache/huggingface
      volumes:
        - name: model-cache
          persistentVolumeClaim:
            claimName: model-cache-pvc
      nodeSelector:
        nvidia.com/gpu.product: "NVIDIA-A100-SXM4-80GB"
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: vllm-qwen-72b
```

### 3. SRE 实战案例

#### 案例 1：模型加载失败导致扩容无效

**故障现象**

某工作日上午 10:00，业务反馈推理服务响应变慢，P99 TTFT 从 800ms 飙升到 12s。监控显示推理引擎实例池的队列深度持续增长，HPA 触发扩容，新增了 3 个 Pod。但 10 分钟后，新 Pod 始终处于 NotReady 状态，队列深度继续增长，P99 TTFT 进一步恶化到 30s。

**排查过程**

```text
排查时间线：
10:00  告警触发: TTFT P99 > 5s
10:02  查看 Grafana: 队列深度从 50 增长到 200
10:03  确认 HPA 已触发扩容: 3 个新 Pod 创建
10:05  检查新 Pod 状态: NotReady (startupProbe 未通过)
10:08  查看新 Pod 日志:
       ERROR: Failed to load model weights
       FileNotFoundError: /models/qwen-72b/model-00003-of-00004.safetensors
10:10  检查 PVC: 模型缓存 PVC 只有 3 个分片文件, 缺少第 3 个
10:12  检查制品仓库: 最近一次模型更新上传了 4 个分片, 但 PVC 预热脚本只复制了前 3 个
10:15  根因确认: 模型版本从 v2.3 升级到 v2.4, 分片数从 3 变成 4, 但 PVC 预热脚本硬编码了 3 个分片
```

**根因分析**

模型权重文件在制品仓库中更新了版本（从 v2.3 到 v2.4），分片数量从 3 增加到 4。但节点级的 PVC 预热脚本是硬编码的，只复制了 3 个分片文件。新扩容的 Pod 使用的是没有完整权重的 PVC，导致模型加载失败。

已有 Pod 之所以正常，是因为它们在旧版本时已经加载了完整的模型到显存中，不需要重新从 PVC 读取。

**修复措施**

紧急修复：
1. 手动将缺失的分片文件复制到所有节点的 PVC
2. 重启 NotReady 的 Pod，确认模型加载成功
3. 验证新 Pod 开始接流量，队列深度下降

长期预防：
1. PVC 预热脚本改为动态读取分片列表，不再硬编码
2. 模型制品发布流水线增加"分片完整性校验"步骤
3. startupProbe 增加更详细的错误日志输出，缩短故障定位时间
4. 建立模型版本与 PVC 预热脚本的兼容性矩阵

**经验总结**

- 模型加载失败是推理平台最常见的扩容失败原因，必须有独立的监控和告警
- PVC 预热脚本应该从制品仓库动态获取文件清单，而不是硬编码
- startupProbe 的超时时间要足够长（70B 模型可能需要 3 分钟），但也要有进度反馈
- 扩容分批进行，每批验证就绪后再扩下一批

#### 案例 2：多 LoRA 部署导致 TTFT 飙升

**故障现象**

某推理平台部署了基座模型 Qwen2.5-72B + 15 个 LoRA 适配器，服务于 15 个不同租户。监控发现：大多数租户的 TTFT P99 在 500ms 左右，但 3 个低频租户的 TTFT P99 持续在 3-5s。这些低频租户的请求量不大（每天 100-200 次），但每次请求的首 token 延迟都很高。

**排查过程**

```text
排查时间线：
Day 1  监控发现: 3 个租户 TTFT P99 > 3s, 其他租户正常
Day 1  检查引擎日志: 这 3 个租户的请求触发了 LoRA 加载
       INFO: Loading LoRA adapter 'tenant-low-freq-3' from /models/lora/tenant-low-freq-3
       INFO: LoRA adapter loaded in 2847ms
Day 1  分析 LoRA 缓存:
       - 单实例最多缓存 8 个 LoRA
       - 当前缓存: 7 个高频租户的 LoRA + 1 个中频租户的 LoRA
       - 3 个低频租户的 LoRA 不在缓存中
Day 2  验证: 手动预加载这 3 个 LoRA 后, TTFT 降至 400ms
Day 2  确认根因: LRU 缓存策略下, 低频 LoRA 被高频 LoRA 淘汰
```

**根因分析**

LoRA 缓存采用 LRU 策略，单实例最多缓存 8 个适配器。平台有 15 个 LoRA，其中 7 个高频租户几乎持续占用缓存，1 个中频租户偶尔被缓存。3 个低频租户的 LoRA 每次请求都需要从存储加载，耗时约 2-3 秒，直接叠加到 TTFT 上。

更深层的问题是：LoRA 的显存占用（每个约 2GB）使得缓存数量受限，而缓存策略没有考虑租户的 SLO 要求。

**修复措施**

紧急修复：
1. 将 3 个低频租户的 LoRA 加入预加载列表，实例启动时自动加载
2. 增加 LoRA 缓存容量（从 8 个增加到 12 个），需要评估显存影响

长期优化：
1. 改进缓存策略：从纯 LRU 改为 LRU + 频率权重 + SLO 优先级
2. 建立 LoRA 使用分析仪表盘，按缓存命中率排序
3. 对低频但对延迟敏感的租户，考虑预留缓存槽位
4. 评估是否需要按 LoRA 热度分池部署（热点 LoRA 专用池 vs 冷 LoRA 共享池）

**经验总结**

- 多 LoRA 部署的缓存策略不能只看访问频率，还要考虑租户 SLO
- LoRA 缓存命中率应该作为核心监控指标，低于阈值时告警
- 冷 LoRA 加载时间（2-3s）对用户体验影响巨大，需要在容量规划中考虑
- 定期审查 LoRA 使用模式，淘汰不再使用的适配器，释放缓存空间

### 4. 容量规划与资源治理

#### 4.1 显存预算模型

推理引擎的显存占用由四部分组成：

```text
总显存 = 模型权重 + KV Cache + LoRA 适配器 + 运行时开销

示例: Qwen2.5-72B on A100-80GB x 4

模型权重 (FP16):     72B * 2 bytes = 144 GB (分布在 4 卡, 每卡 36 GB)
模型权重 (AWQ INT4): 72B * 0.5 bytes = 36 GB (分布在 4 卡, 每卡 9 GB)
KV Cache:            max_model_len * n_layers * 2 * head_dim * batch_size
                     32768 * 80 * 2 * 128 * batch / 4 cards
                     ≈ 每个并发请求 ~2 GB (32k 上下文)
LoRA (rank=64):      每个适配器 ~2 GB
运行时开销:          CUDA context + 临时 buffer ≈ 2-3 GB / 卡

AWQ 量化后每卡预算:
  模型权重:    9 GB
  运行时开销:  3 GB
  LoRA 缓存:   8 GB (4 个适配器)
  KV Cache:    60 GB (剩余)
  -> 可支持约 30 个并发请求 (32k 上下文)
```

#### 4.2 容量规划公式

```text
所需实例数 = 峰值 QPS / (单实例 QPS * 目标利用率)

单实例 QPS ≈ 1000 / (TTFT + avg(TPOT) * avg(output_tokens))

示例:
  峰值 QPS: 50
  TTFT: 500ms
  TPOT: 30ms
  平均输出 tokens: 200
  单实例 QPS = 1000 / (500 + 30 * 200) = 1000 / 6500 ≈ 0.15 QPS
  目标利用率: 70%
  所需实例数 = 50 / (0.15 * 0.7) ≈ 476 个实例

  (注意: 这是理论值, 实际需要考虑 Continuous Batching 的吞吐提升)
  Continuous Batching 后单实例 QPS 可提升 5-10x
  -> 实际所需实例数 ≈ 48-96 个
```

## 💻 实战练习

### 练习 1：基础操作 -- 部署 vLLM 并测试 OpenAI 兼容 API

**目标**：部署一个 vLLM 实例，验证其 OpenAI 兼容 API 的可用性。

**步骤**：

1. 准备环境：确保有至少 1 张 GPU（建议 A100 40GB 或以上），安装 Python 3.10+ 和 CUDA 12.x。

2. 安装 vLLM：
```bash
pip install vllm
```

3. 启动 vLLM 服务：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192
```

4. 测试健康检查：
```bash
curl http://localhost:8000/health
# 期望输出: {"status": "ok"}

curl http://localhost:8000/v1/models
# 期望输出: 包含模型 ID 的 JSON
```

5. 测试非流式请求：
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "用一句话解释什么是 PagedAttention"}],
    "max_tokens": 128
  }'
```

6. 测试流式请求：
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "列出 3 个 SRE 最重要的指标"}],
    "max_tokens": 256,
    "stream": true
  }'
```

7. 测试并发请求：使用 Python 脚本发送 10 个并发请求，观察 TTFT 和吞吐变化。
```python
import asyncio
import httpx
import time

async def send_request(client, prompt):
    start = time.time()
    response = await client.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64
        }
    )
    elapsed = time.time() - start
    return elapsed

async def main():
    prompts = [f"用一句话解释概念 {i}" for i in range(10)]
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [send_request(client, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        print(f"并发 10 请求完成, 平均延迟: {sum(results)/len(results):.2f}s")
        print(f"最大延迟: {max(results):.2f}s, 最小延迟: {min(results):.2f}s")

asyncio.run(main())
```

**验收标准**：
- 健康检查返回正常
- 非流式和流式请求均返回正确结果
- 并发请求场景下 TTFT 和延迟在合理范围内

### 练习 2：进阶场景 -- 配置多 LoRA 部署并测试动态切换

**目标**：在 vLLM 上配置多个 LoRA 适配器，验证动态切换能力。

**步骤**：

1. 准备 LoRA 适配器（如果没有现成的，可以用 PEFT 快速训练一个小的测试适配器）：
```python
# 快速创建测试 LoRA (仅用于练习)
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"],
)

model = get_peft_model(model, lora_config)
model.save_pretrained("/models/lora/test-adapter-1")
```

2. 启动 vLLM 并加载多个 LoRA：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --enable-lora \
    --max-loras 4 \
    --max-cpu-loras 16 \
    --lora-modules \
        adapter1=/models/lora/test-adapter-1 \
        adapter2=/models/lora/test-adapter-2 \
    --host 0.0.0.0 \
    --port 8000
```

3. 测试不同 LoRA 的请求：
```bash
# 使用 adapter1
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "adapter1",
    "messages": [{"role": "user", "content": "测试适配器 1"}],
    "max_tokens": 64
  }'

# 使用 adapter2
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "adapter2",
    "messages": [{"role": "user", "content": "测试适配器 2"}],
    "max_tokens": 64
  }'
```

4. 监控 LoRA 缓存状态：观察日志中 LoRA 加载/卸载事件。

**验收标准**：
- 多个 LoRA 适配器均可正常加载和使用
- 不同 LoRA 请求返回不同结果
- 理解 LoRA 缓存淘汰机制

### 练习 3：故障排查挑战 -- 模拟模型加载失败

**目标**：模拟一个模型加载失败场景，完成完整的排查和修复流程。

**步骤**：

1. 故意破坏模型文件：
```bash
# 备份原始文件
cp /models/qwen-7b/config.json /models/qwen-7b/config.json.bak

# 修改 config.json 中的某个关键字段 (如 hidden_size)
# 使其与实际权重不匹配
sed -i 's/"hidden_size": 4096/"hidden_size": 8192/' /models/qwen-7b/config.json
```

2. 尝试启动 vLLM 并观察错误：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model /models/qwen-7b \
    --host 0.0.0.0 \
    --port 8000
# 预期: 启动失败, 输出模型加载错误日志
```

3. 按排查清单逐项检查：
   - 检查模型文件完整性（config.json, tokenizer, safetensors 分片）
   - 检查文件权限
   - 检查显存是否足够
   - 检查 CUDA 版本兼容性
   - 检查 transformers / vLLM 版本兼容性

4. 修复并验证：
```bash
# 恢复原始 config.json
cp /models/qwen-7b/config.json.bak /models/qwen-7b/config.json

# 重新启动
python -m vllm.entrypoints.openai.api_server \
    --model /models/qwen-7b \
    --host 0.0.0.0 \
    --port 8000
# 预期: 启动成功
```

5. 记录排查过程：编写一份故障排查报告，包括症状、排查步骤、根因、修复措施和预防建议。

**验收标准**：
- 能够识别模型加载失败的常见错误模式
- 能够按系统化流程排查问题
- 能够编写完整的故障排查报告

## 🎯 面试题精选

### 面试题 1：vLLM vs SGLang vs TGI 的选型决策

**问题**：你的团队需要为一个通用文本生成平台选择推理引擎，候选方案有 vLLM、SGLang 和 TGI。你会如何做选型决策？

**参考答案**：

选型决策应从四个维度评估：

1. **性能需求**：如果核心需求是高吞吐的通用文本生成，vLLM 的 PagedAttention + Continuous Batching 是成熟方案。如果涉及大量结构化生成（JSON、SQL）或推理工作流，SGLang 的 RadixAttention 和结构化生成引擎更有优势。

2. **运维成熟度**：TGI 作为 Hugging Face 官方维护的引擎，部署心智负担最小，Docker 一键部署。vLLM 社区活跃但版本迭代快，需要关注升级兼容性。SGLang 快速成长但运维经验沉淀较少。

3. **多租户治理**：如果需要多 LoRA 动态加载、按租户路由、配额管理，vLLM 的多 LoRA 支持最为成熟。TGI 也支持但灵活性不如 vLLM。

4. **团队能力**：如果团队对 HF 生态熟悉，TGI 的学习曲线最低。如果团队有性能调优能力，vLLM 提供了丰富的调参空间。

**决策建议**：对于通用文本生成平台，vLLM 是默认首选。如果团队追求稳妥且以 HF 生态为中心，选 TGI。如果有大量结构化生成需求，考虑 SGLang。

---

### 面试题 2：如何设计推理平台的 API Gateway

**问题**：推理平台的 API Gateway 需要承担哪些职责？与普通 Web 服务的 Gateway 有什么区别？

**参考答案**：

推理平台的 API Gateway 除了承担标准 Web Gateway 的职责（TLS 终止、认证、限流、负载均衡）外，还需要处理以下推理特有的需求：

1. **模型语义路由**：根据请求中的 model 字段将请求路由到对应的引擎池，而不是简单的轮询。需要维护模型到引擎池的映射表。

2. **Token 配额管理**：除了请求级别的限流，还需要 token 级别的配额管理（每分钟允许消耗多少 input/output tokens）。

3. **流式响应代理**：SSE (Server-Sent Events) 流式响应的代理比普通 HTTP 响应复杂，需要正确处理 chunk 传输、连接超时和客户端断开。

4. **请求体验证**：验证 model 是否存在、messages 格式是否正确、max_tokens 是否在允许范围内。推理请求的参数验证比普通 API 更复杂。

5. **成本追踪**：按请求记录 input/output token 数量，用于成本分摊和计费。需要在 Gateway 层做 token 计数，而不是依赖引擎报告。

6. **回退与降级**：当模型不可用时，能够自动降级到备用模型或返回缓存的响应。

**关键设计原则**：Gateway 不应理解模型语义，但需要理解推理 API 的语义。

---

### 面试题 3：冷启动优化有哪些手段

**问题**：一个 70B 模型的推理服务冷启动需要 2-3 分钟。你会如何优化？

**参考答案**：

冷启动优化需要按阶段分析：

1. **容器创建阶段**：使用轻量基础镜像（精简不必要的依赖），减少镜像层数。效果：减少 5-15 秒。

2. **镜像拉取阶段**：在 GPU 节点上配置镜像预拉取（DaemonSet 或 K8s ImagePolicy），确保镜像已在节点本地。效果：消除镜像拉取时间。

3. **权重加载阶段**：将模型权重缓存到节点本地 SSD 或 NFS 就近存储，避免从远端对象存储拉取。70B 模型权重约 140GB（FP16），从对象存储加载可能需要 5-10 分钟，从本地 SSD 加载只需 30-60 秒。效果：减少 30-60 秒。

4. **显存分配阶段**：使用 CUDA memory pool 预分配显存，避免运行时碎片化。效果：减少 2-5 秒。

5. **图编译阶段**：使用 torch.compile 缓存，避免每次冷启动都重新编译 CUDA kernel。效果：减少 10-30 秒。

6. **预热阶段**：发送合成请求覆盖典型上下文长度，预热 Prefix Cache 和 KV Cache。效果：减少首次请求延迟。

7. **扩容策略**：分批拉起实例，避免同时争抢对象存储带宽、PCIe 和显存。

8. **架构层面**：考虑预留实例（warm pool），保持一定数量的已加载模型实例处于待命状态。

---

### 面试题 4：多 LoRA 部署的挑战和解决方案

**问题**：你的推理平台需要支持 50 个 LoRA 适配器，每个对应一个租户。如何设计部署方案？

**参考答案**：

50 个 LoRA 远超单实例缓存容量，需要系统化的部署策略：

1. **缓存策略设计**：
   - 分析 LoRA 访问模式：80% 的请求可能集中在 10 个热点 LoRA
   - 使用 LRU + 频率权重的缓存策略，而非纯 LRU
   - 对延迟敏感但低频的 LoRA，设置"保底缓存"槽位

2. **分层部署**：
   - 热点 LoRA（10 个）：预加载到所有实例，常驻缓存
   - 温 LoRA（15 个）：按需加载，LRU 缓存
   - 冷 LoRA（25 个）：专用实例池或按需加载

3. **显存容量规划**：
   - 每个 LoRA（rank=64）约 2GB 显存
   - 单实例缓存 10 个热点 LoRA 需要 20GB 显存
   - 需要在模型权重、KV Cache 和 LoRA 缓存之间平衡显存预算

4. **监控与告警**：
   - 监控 LoRA 缓存命中率，低于 80% 时告警
   - 监控冷 LoRA 加载时间，超过阈值时告警
   - 定期审查 LoRA 使用模式，淘汰不再使用的适配器

5. **版本管理**：
   - LoRA 与基座模型版本的兼容性检查
   - 制品发布流水线中强制校验

---

### 面试题 5：如何实现推理服务的灰度发布

**问题**：你需要将推理服务从模型版本 A 升级到版本 B，如何设计灰度发布方案？

**参考答案**：

推理服务的灰度发布比普通 Web 服务更复杂，因为模型切换涉及权重加载和显存分配：

1. **流量切分策略**：
   - 按比例：10% 流量到新版本，90% 到旧版本，逐步增加
   - 按租户：选择内部测试租户先使用新版本
   - 按请求特征：特定 model 字段路由到新版本

2. **实例池管理**：
   - 新版本部署到独立的实例池
   - 通过控制层路由将指定流量导入新池
   - 旧版本实例池保持不变，随时可回退

3. **质量监控**：
   - 对比新旧版本的 TTFT、TPOT、TPS 指标
   - 监控错误率、OOM 率、超时率
   - 人工抽检输出质量

4. **回退条件**：
   - 自动回退：错误率超过阈值、P99 延迟超过阈值
   - 手动回退：输出质量不满足要求

5. **全量发布**：
   - 灰度验证通过后，逐步将流量迁移到新版本
   - 旧版本实例池在流量清零后缩容

---

### 面试题 6：Prefix Cache 的工作原理和运维注意事项

**问题**：解释 Prefix Cache 的工作原理。作为 SRE，你需要关注哪些运维指标？

**参考答案**：

**工作原理**：

Prefix Cache 的核心思想是：多个请求如果共享相同的 prompt 前缀（如系统提示词），可以复用这些前缀的 KV Cache，避免重复计算。

工作流程：
1. 请求到达时，引擎计算 prompt 的 hash
2. 在 Prefix Cache 中查找匹配的前缀
3. 如果命中，直接复用已有的 KV Cache，跳过前缀部分的 prefill 计算
4. 只对新增部分做 prefill，然后进入 decode 阶段

**SRE 需要关注的指标**：

1. **Prefix Cache 命中率**：命中率低意味着大量重复计算，浪费 GPU 算力。低于 50% 需要排查原因（前缀不一致、缓存淘汰过快等）。

2. **Prefix Cache 内存占用**：缓存占用的显存会影响可支持的并发数。需要监控缓存大小和淘汰频率。

3. **缓存淘汰频率**：频繁淘汰意味着缓存容量不足，需要增加显存预算或优化缓存策略。

4. **前缀一致性**：如果系统提示词频繁变化，会导致缓存命中率下降。需要评估提示词版本管理策略。

5. **首 token 延迟变化**：Prefix Cache 命中时 TTFT 应该显著低于未命中时。如果差异不大，说明缓存收益有限。

---

### 面试题 7：如何诊断推理服务的 TTFT 飙升

**问题**：用户反馈推理服务的首 token 延迟从 500ms 飙升到 5s。你会如何排查？

**参考答案**：

TTFT 飙升的排查需要从多个层面入手：

1. **确认问题范围**：
   - 是所有请求还是特定模型/租户？如果是特定模型，可能是该模型的实例出了问题
   - 是突然恶化还是逐渐恶化？突然恶化可能是实例故障，逐渐恶化可能是资源耗尽

2. **检查队列深度**：
   - 如果队列深度持续增长，说明引擎处理能力不足或实例不够
   - 可能原因：实例 OOM 重启、HPA 未及时扩容、流量突增

3. **检查 GPU 状态**：
   - GPU 利用率是否接近 100%？如果是，说明引擎负载饱和
   - 显存是否接近上限？如果显存耗尽，新请求无法分配 KV Cache
   - 是否有 ECC 错误或 GPU 掉卡？

4. **检查 Prefix Cache**：
   - 缓存命中率是否下降？可能是缓存被淘汰或前缀变化
   - 缓存大小是否达到上限？

5. **检查请求特征**：
   - 是否有异常长的输入请求？长输入会占用大量 prefill 时间
   - 是否有大量并发请求同时到达？

6. **检查基础设施**：
   - 网络延迟是否正常？RDMA/InfiniBand 是否有错误？
   - 节点是否在驱逐 Pod？是否有资源争抢？

---

### 面试题 8：推理平台的多租户隔离方案

**问题**：如何在同一套推理基础设施上实现多租户隔离？

**参考答案**：

多租户隔离需要在多个层面实施：

1. **网络层隔离**：通过 K8s NetworkPolicy 限制 Pod 间通信，确保租户流量只到达指定实例池。

2. **实例池隔离**：
   - 专用池：关键租户使用独立的 GPU 实例池，完全隔离
   - 共享池：非关键租户共享实例池，通过配额限制资源使用

3. **配额管理**：
   - 每租户每分钟 token 配额
   - 每租户并发请求上限
   - 每租户可用模型列表

4. **路由隔离**：通过 API Key 或 JWT 中的租户标识，将请求路由到对应的实例池。

5. **监控隔离**：每个租户有独立的监控面板，展示其资源使用、延迟指标和配额消耗。

6. **故障隔离**：单租户的异常流量不应影响其他租户。通过限流和背压实现。

---

### 面试题 9：如何评估推理引擎的 GPU 利用率

**问题**：GPU 利用率 90% 是好是坏？如何正确评估推理引擎的 GPU 资源使用效率？

**参考答案**：

GPU 利用率 90% 不一定好，需要结合上下文分析：

1. **利用率 vs 效率**：
   - GPU 利用率高但吞吐低，可能是因为长上下文请求占用大量计算但产出 token 少
   - GPU 利用率低但吞吐高，可能是 Continuous Batching 效率高，每 batch 处理大量请求

2. **正确评估指标**：
   - Tokens/s/GPU：每张 GPU 每秒生成的 token 数，是最直接的效率指标
   - MFU (Model FLOPS Utilization)：实际 FLOPS 占理论峰值的比例
   - 显存利用率：已用显存占总显存的比例
   - 队列深度：等待处理的请求数，反映服务能力是否匹配需求

3. **优化方向**：
   - 如果 GPU 利用率高但 Tokens/s 低，可能是请求特征问题（长输入短输出）
   - 如果 GPU 利用率低但队列深度高，可能是调度效率问题
   - 如果显存利用率低，可以增加 batch size 或启用更大上下文长度

---

### 面试题 10：推理服务的容量规划方法论

**问题**：如何为一个推理服务做容量规划？需要考虑哪些因素？

**参考答案**：

推理服务的容量规划需要考虑以下因素：

1. **流量模型**：
   - 峰值 QPS 和平均 QPS
   - 请求特征：平均输入/输出 token 长度
   - 流量模式：是否有明显的峰谷

2. **性能目标**：
   - TTFT SLA：P99 首 token 延迟上限
   - TPOT SLA：P99 token 间延迟上限
   - 可用性目标：99.9% 还是 99.95%

3. **容量公式**：
   - 单实例 QPS = 1000 / (TTFT + TPOT * avg_output_tokens)
   - Continuous Batching 后需要乘以 batch 效率系数
   - 所需实例数 = 峰值 QPS / (单实例 QPS * 目标利用率)

4. **冗余设计**：
   - 预留 20-30% 的 buffer 应对突发流量
   - 跨可用区部署，容忍单区故障
   - 预留扩容空间，冷启动时间纳入考量

5. **成本优化**：
   - 使用量化模型降低单卡资源需求
   - 峰谷时段使用不同实例数（HPA）
   - 离线任务使用竞价实例

## 📚 深入阅读

- [01-roadmap.md](./01-roadmap.md) -- 学习路线图
- [02-glossary.md](./02-glossary.md) -- 术语表
- [03-reference-map.md](./03-reference-map.md) -- 参考资料索引
- [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) -- LLM 生命周期总览
- [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) -- 推理性能工程
- [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) -- 推理可观测性与 SLO
- vLLM 官方文档: https://docs.vllm.ai/
- SGLang 官方文档: https://sgl-project.github.io/
- TGI 官方文档: https://huggingface.co/docs/text-generation-inference/
- NVIDIA Triton Inference Server: https://docs.nvidia.com/deeplearning/triton-inference-server/
- TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM

## ✅ 自检清单

完成本章学习后，请确认你能够回答以下问题：

- [ ] 能否列举 vLLM、SGLang、TGI、Triton、TensorRT-LLM 的核心差异和适用场景？
- [ ] 能否画出推理平台的六层架构图并解释每层的职责？
- [ ] 能否描述一个请求从客户端到 GPU 再到响应的完整路径？
- [ ] 能否解释单模型、多模型、多 LoRA 三种部署模式的优劣？
- [ ] 能否列出冷启动的各个阶段和对应的优化策略？
- [ ] 能否说明 K8s 中 startupProbe、readinessProbe、livenessProbe 的区别和配置？
- [ ] 能否解释 Prefix Cache 的工作原理和运维注意事项？
- [ ] 能否给出一个推理平台的显存预算模型？
- [ ] 能否描述多 LoRA 部署的缓存策略和运维挑战？
- [ ] 能否设计一个推理服务的灰度发布方案？
- [ ] 能否排查模型加载失败、TTFT 飙升、LoRA 缓存失效等架构层问题？
- [ ] 能否为推理服务做容量规划，包括实例数计算和冗余设计？
