# LLM SRE 18：推理可观测性与 SLO

> 📅 日期：2026-05-03
> 📖 学习主题：推理服务四层可观测性、SLO 设计与告警策略
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：17-inference-performance-engineering.md, Prometheus 基础

## 🎯 学习目标

完成本章学习后，你应该能够：

1. **设计四层可观测性体系（体验层、服务层、资源层、质量层）**——理解每一层要采集什么指标、为什么采集、指标之间如何形成因果链，避免"堆砌几十个图表却无法定位问题"的困境。
2. **定义 LLM 推理服务的 SLI/SLO 和错误预算**——为 TTFT、TPOT、可用性、输出质量分别建立可度量的目标，并计算和跟踪错误预算消耗速率。
3. **设计与用户影响绑定的告警规则**——用多窗口、多燃烧率告警替代简单阈值告警，减少告警疲劳的同时确保真正的用户影响不被遗漏。
4. **搭建三屏值班 Dashboard（体验、容量、诊断）**——从全局异常快速钻取到"哪个模型、哪个租户、哪批实例出问题"，让值班人员在事故中能快速形成行动决策。

---

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 为什么 LLM 推理服务需要专门的可观测性体系

传统 Web 服务的可观测性围绕"请求-响应"模型：QPS、延迟、错误率三板斧基本够用。LLM 推理服务的不同之处在于：

- **延迟结构复杂**：一次推理请求的延迟包含排队、Prefill、Decode 三个阶段，每个阶段的瓶颈完全不同（计算密集 vs 带宽密集 vs 调度竞争）。
- **资源高度耦合**：GPU 利用率、显存占用、KV Cache 水位相互影响，单看任何一个指标都会误判。
- **输出质量不稳定**：同一模型、同一输入，输出质量可能因版本、量化、LoRA 适配器不同而变化——传统服务没有这一维度。
- **流式输出改变体验感知**：用户感知的不是"总延迟"，而是"首包时间"和"流式连贯性"，传统的 P99 延迟指标不能直接反映体验。

因此，LLM 推理可观测性需要一个分层模型，把用户体验、服务行为、资源消耗和输出质量串联成因果链。

#### 1.2 四层可观测性模型

四层模型从上到下分别是：体验层、服务层、资源层、质量层。每层回答一个核心问题：

```text
┌─────────────────────────────────────────────────────────────────┐
│                    四层可观测性架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  体验层 —— "用户感觉怎么样？"                               │  │
│  │  TTFT / TPOT / TPS / E2E Latency / 用户满意度             │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │ 发现异常                          │
│                             v                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  服务层 —— "系统在做什么？"                                 │  │
│  │  QPS / 成功率 / 队列长度 / 批处理效率 / 路由状态            │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │ 定位瓶颈                          │
│                             v                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  资源层 —— "硬件够不够用？"                                 │  │
│  │  GPU 利用率 / 显存 / KV Cache / CPU / 网络 / 磁盘 IO      │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │ 解释行为                          │
│                             v                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  质量层 —— "结果对不对？"                                   │  │
│  │  空响应率 / 截断率 / 工具调用成功率 / 安全拦截率 / 人工评分  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  SRE 的工作：把四层串成因果链                                    │
│  "TTFT 上升" --> "队列变长" --> "GPU 显存不足" --> "KV Cache 命中下降" │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**体验层指标详解**

| 指标 | 定义 | 测量方法 | 运维意义 |
| --- | --- | --- | --- |
| TTFT (Time to First Token) | 从请求到达到收到第一个输出 token 的时间 | 服务端打点：收到请求时间戳 - 第一个 token 生成时间戳 | 用户对"响应速度"的直接感知；TTFT 上升通常意味着 Prefill 变慢或排队变长 |
| TPOT (Time Per Output Token) | 每个输出 token 的平均生成时间 | (总输出时间 - TTFT) / 输出 token 数 | 流式输出的连贯性；TPOT 波动大意味着用户看到"一顿一顿"的输出 |
| TPS (Tokens Per Second) | 系统每秒生成的 token 总量 | 所有并发请求的输出 token 求和 / 时间窗口 | 系统吞吐能力；TPS 下降但 QPS 不变说明单请求效率退化 |
| E2E Latency | 端到端延迟，从请求到达到完整响应返回 | 服务端打点 | 非流式场景的核心指标；流式场景下重要性低于 TTFT + TPOT |
| 用户满意度 | 用户对输出的主观评价 | 点赞/点踩、显式评分、隐式信号（重试率、中止率） | SLO 的终极校准指标；技术指标正常但满意度下降说明质量问题 |

**服务层指标详解**

| 指标 | 定义 | 运维意义 |
| --- | --- | --- |
| QPS (Queries Per Second) | 每秒处理的请求数 | 流量基线；异常波动需要排查来源 |
| 成功率 | 非 5xx 响应占总请求的比例 | 可用性 SLO 的核心 SLI |
| 队列长度 (Waiting Requests) | 在队列中等待被调度的请求数 | 排队是 TTFT 上升的第一信号 |
| 批处理效率 (Batch Size) | 每个 Decode step 处理的并发请求数 | GPU 利用率的直接驱动因素 |
| 路由状态 | 各模型池/实例的流量分配 | 路由打偏会导致局部过载 |

**资源层指标详解**

| 指标 | 定义 | 运维意义 |
| --- | --- | --- |
| GPU 利用率 | GPU 计算单元的活跃时间占比 | 判断 batch 是否充分；但低利用率不一定意味着空闲（可能是带宽瓶颈） |
| 显存使用率 | 已分配显存 / 总显存 | 接近上限时 OOM 风险急剧上升 |
| KV Cache 占用 | KV Cache 已用显存 / KV Cache 上限 | 决定能同时服务多少并发请求和多长上下文 |
| CPU 使用率 | CPU 核心的活跃时间占比 | 影响 tokenization、路由决策、日志处理 |
| 网络 IO | 网卡吞吐和延迟 | 模型权重拉取、分布式推理通信 |

**质量层指标详解**

| 指标 | 定义 | 运维意义 |
| --- | --- | --- |
| 空响应率 | 返回空字符串或仅含空白的响应比例 | 模型异常或 prompt 过滤过严 |
| 截断率 | 因达到 max_tokens 而被截断的响应比例 | max_tokens 设置不合理或模型生成失控 |
| 工具调用成功率 | 工具/函数调用成功执行的比例 | Agent 场景的核心质量指标 |
| 安全拦截率 | 被安全策略拦截的请求比例 | 拦截率突变说明 prompt 注入攻击或策略过严 |
| 人工评分 | 标注员对输出质量的评分 | 定期校准自动指标的准确性 |

#### 1.3 请求生命周期与指标标注

理解一个请求从进入到返回的完整生命周期，是设计可观测性的基础：

```text
                        请求生命周期与指标标注

客户端                    网关/路由层              推理引擎                   模型执行
  |                         |                      |                         |
  | --- HTTP 请求 -------->|                      |                         |
  |                         |                      |                         |
  |                    [路由决策]                   |                         |
  |                    [认证/限流]                  |                         |
  |                         |                      |                         |
  |                         | --- 转发请求 ------->|                         |
  |                         |                      |                         |
  |                         |                 [进入队列]                      |
  |                         |                 queue_time 开始计时             |
  |                         |                      |                         |
  |                         |                 [调度器分配]                     |
  |                         |                 queue_time 结束                 |
  |                         |                      |                         |
  |                         |                      | ---- Prefill 阶段 ---->|
  |                         |                      |   处理所有输入 token      |
  |                         |                      |   计算 KV Cache          |
  |                         |                      |   TTFT = queue_time     |
  |                         |                      |        + prefill_time   |
  |                         |                      |<--- 第一个 token -------|
  |                         |                      |                         |
  |<--- 流式 SSE ----------|<--- 流式转发 ---------|                         |
  |                         |                      |                         |
  |                         |                      | ---- Decode 阶段 ----->|
  |                         |                      |   逐 token 自回归生成    |
  |                         |                      |   TPOT = decode_time    |
  |                         |                      |        / num_tokens     |
  |                         |                      |<--- token by token ----|
  |                         |                      |                         |
  |<--- 流式 SSE ----------|<--- 流式转发 ---------|                         |
  |                         |                      |                         |
  |                         |                      | [生成完成/达到上限]       |
  |<--- 流式结束 ----------|<--- 流式结束 ---------|                         |
  |                         |                      |                         |
  |                    [记录指标]                   |                         |
  |                    TTFT, TPOT, TPS             |                         |
  |                    输入/输出 token 数           |                         |
  |                    状态码, 错误类型              |                         |
```

关键测量点：

- **TTFT** = 请求到达时间戳 - 第一个 token 返回时间戳（包含 queue_time + prefill_time + 网络开销）
- **TPOT** = (最后一个 token 时间戳 - 第一个 token 时间戳) / 输出 token 数
- **Queue Time** = 请求进入队列时间戳 - 调度器分配时间戳
- **E2E Latency** = 最后一个 token 返回时间戳 - 请求到达时间戳

#### 1.4 SLO 与错误预算

**SLI（Service Level Indicator）** 是你实际测量的服务行为指标。**SLO（Service Level Objective）** 是你对 SLI 的目标承诺。**错误预算（Error Budget）** 是 SLO 允许的"失败空间"。

对于 LLM 推理服务，建议定义以下 SLI/SLO：

```text
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 推理服务 SLO 定义                         │
├──────────────┬──────────────────────────────────────────────────┤
│  SLI 名称     │  定义与计算方法                                   │
├──────────────┼──────────────────────────────────────────────────┤
│  可用性       │  成功请求数 / 总请求数                             │
│              │  (排除 5xx、超时、连接错误)                        │
│              │  目标：99.9%（每月允许 43.8 分钟不可用）            │
├──────────────┼──────────────────────────────────────────────────┤
│  TTFT 延迟    │  TTFT p95 < 目标值的请求占比                     │
│              │  目标：95% 的请求 TTFT < 2s（交互场景）            │
│              │  目标：95% 的请求 TTFT < 5s（长上下文场景）        │
├──────────────┼──────────────────────────────────────────────────┤
│  TPOT 延迟    │  TPOT p95 < 目标值的请求占比                     │
│              │  目标：95% 的请求 TPOT < 100ms                    │
├──────────────┼──────────────────────────────────────────────────┤
│  输出质量     │  非空、非截断、非安全拦截的响应占比                │
│              │  目标：99% 的响应通过质量检查                      │
└──────────────┴──────────────────────────────────────────────────┘
```

**错误预算计算**

以可用性 SLO 99.9% 为例：

```text
错误预算 = 1 - SLO = 1 - 99.9% = 0.1%

一个月（30 天）的总分钟数 = 30 × 24 × 60 = 43,200 分钟
允许的错误分钟数 = 43,200 × 0.1% = 43.2 分钟

等效为：每 1000 个请求允许 1 个失败请求

消耗速率计算：
  当前消耗速率 = 过去 1 小时错误数 / 过去 1 小时总请求数
  预计月度消耗 = 当前消耗速率 × 本月剩余小时数

  如果预计月度消耗 > 错误预算总量，需要立即行动
```

**错误预算消耗速率与行动策略**

```text
消耗速率     状态          行动策略
─────────────────────────────────────────────────────
  < 50%     健康          正常发布节奏，可接受一定的实验性变更
 50-80%     关注          减少非必要发布，加强监控频率
 80-100%    警告          冻结非关键发布，启动问题排查
  > 100%    耗尽          停止所有发布，全力恢复，事后复盘
```

#### 1.5 告警设计

传统阈值告警的问题：一个静态阈值无法适应流量波动、版本变更和业务节奏。LLM 推理服务的告警应该基于用户影响和错误预算消耗来设计。

**多窗口、多燃烧率告警**

燃烧率（Burn Rate）表示错误预算被消耗的速率。1.0 表示按预期速率消耗，2.0 表示以两倍速率消耗。

```text
┌─────────────────────────────────────────────────────────────────┐
│               多窗口多燃烧率告警策略                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  燃烧率      短窗口    长窗口    告警级别    含义                 │
│  ──────     ───────   ───────  ─────────  ─────────────────     │
│  14.4x       1 小时    5 分钟   P1-紧急    1 小时内耗尽月预算     │
│   6.0x       6 小时   30 分钟   P2-严重    6 小时内耗尽月预算     │
│   3.0x       1 天      2 小时   P3-警告    1 天内耗尽月预算       │
│   1.0x       3 天      6 小时   P4-通知    3 天内耗尽月预算       │
│                                                                 │
│  规则：短窗口 AND 长窗口同时满足才触发告警                        │
│  目的：短窗口防止误报，长窗口防止漏报                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**告警决策流程**

```text
                    告警决策流程图

                   指标异常检测
                       |
                       v
             ┌───────────────────┐
             │  短窗口是否满足？   │
             └────────┬──────────┘
                      |
            否 -------+------- 是
            |                  |
            v                  v
         忽略          ┌───────────────────┐
                       │  长窗口是否满足？   │
                       └────────┬──────────┘
                                |
                      否 -------+------- 是
                      |                  |
                      v                  v
                   忽略          ┌───────────────────┐
                                 │  错误预算是否充足？ │
                                 └────────┬──────────┘
                                          |
                                否 -------+------- 是
                                |                  |
                                v                  v
                          记录事件          ┌───────────────────┐
                          (不告警)          │  触发告警           │
                                           │  + 附带 Runbook     │
                                           │  + 通知值班人员      │
                                           │  + 更新错误预算仪表  │
                                           └───────────────────┘
```

**告警分级与升级策略**

| 级别 | 触发条件 | 响应时间 | 通知方式 | 升级策略 |
| --- | --- | --- | --- | --- |
| P1-紧急 | 燃烧率 14.4x，1 小时内可能耗尽月预算 | 5 分钟 | 电话 + 短信 + 即时通讯 | 15 分钟无响应升级到 On-Call Lead |
| P2-严重 | 燃烧率 6.0x，6 小时内可能耗尽月预算 | 15 分钟 | 短信 + 即时通讯 | 30 分钟无响应升级到 On-Call Lead |
| P3-警告 | 燃烧率 3.0x，1 天内可能耗尽月预算 | 1 小时 | 即时通讯 | 下一工作日跟进 |
| P4-通知 | 燃烧率 1.0x，3 天内可能耗尽月预算 | 下一工作日 | 邮件 + Dashboard | 纳入周报 |

#### 1.6 Dashboard 设计

值班 Dashboard 的核心原则是"从全局到局部，从症状到根因"。建议按三屏组织：

```text
┌─────────────────────────────────────────────────────────────────┐
│               三屏 Dashboard 布局                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  屏 1：用户体验                                          │    │
│  │                                                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │    │
│  │  │ TTFT p95 │  │ TPOT p95 │  │ 成功率    │  │ 错误预算│  │    │
│  │  │  1.2s    │  │  85ms    │  │ 99.95%   │  │ 67%剩余 │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘  │    │
│  │                                                         │    │
│  │  [TTFT 时序图]           [TPOT 时序图]                   │    │
│  │  [成功率时序图]          [队列长度时序图]                  │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  屏 2：容量与资源                                        │    │
│  │                                                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │    │
│  │  │ GPU 利用  │  │ 显存使用  │  │ KV Cache │  │ 扩缩容 │  │    │
│  │  │  72%     │  │  85%     │  │  68%     │  │ 稳定   │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘  │    │
│  │                                                         │    │
│  │  [GPU 利用率热力图]       [显存分布直方图]                │    │
│  │  [KV Cache 趋势图]       [Batch Size 分布]              │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  屏 3：诊断与排查                                        │    │
│  │                                                         │    │
│  │  [按模型分组的 TTFT 分布]  [按租户分组的错误率]           │    │
│  │  [请求分布热力图]          [版本对比图]                   │    │
│  │  [最近 Trace 采样列表]     [错误日志流]                   │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. 命令/工具详解

#### 2.1 Prometheus 指标采集配置

**vLLM 指标端点**

vLLM 默认在 `/metrics` 路径暴露 Prometheus 格式指标。以下是典型的 Prometheus scrape 配置：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'vllm-inference'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    static_configs:
      - targets: ['vllm-instance-1:8000', 'vllm-instance-2:8000']
        labels:
          model: 'qwen-72b'
          env: 'production'
    metric_relabel_configs:
      # 过滤不需要的高基数指标
      - source_labels: [__name__]
        regex: 'vllm:request_prompt_tokens_bucket'
        action: drop
```

**vLLM 暴露的核心指标**

```text
# 请求级指标
vllm:request_success_total              # 成功请求计数（按 finish_reason 分类）
vllm:e2e_request_latency_seconds        # 端到端延迟直方图
vllm:time_to_first_token_seconds        # TTFT 直方图
vllm:time_per_output_token_seconds      # TPOT 直方图
vllm:num_requests_running               # 正在处理的请求数
vllm:num_requests_waiting               # 排队等待的请求数
vllm:num_requests_swapped               # 被换出到 CPU 的请求数

# 资源级指标
vllm:gpu_cache_usage_perc               # KV Cache 使用率
vllm:gpu_memory_usage_bytes             # GPU 显存使用量
vllm:num_preemptions_total              # 请求抢占次数

# 批处理指标
vllm:avg_batch_size                     # 平均 batch 大小
vllm:num_batched_tokens_total           # batch 处理的 token 总量
```

**DCGM Exporter 部署与配置**

DCGM (Data Center GPU Manager) Exporter 提供 GPU 硬件级指标：

```yaml
# dcgm-exporter daemonset (Kubernetes)
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
      annotations:
        prometheus.io/scrape: 'true'
        prometheus.io/port: '9400'
    spec:
      nodeSelector:
        nvidia.com/gpu.present: 'true'
      containers:
        - name: dcgm-exporter
          image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.8-3.6.0-ubuntu22.04
          ports:
            - containerPort: 9400
              name: metrics
          env:
            - name: DCGM_EXPORTER_LISTEN_ADDRESS
              value: ':9400'
            - name: DCGM_EXPORTER_COLLECTORS
              value: '/etc/dcgm-exporter/default-counters.csv'
          securityContext:
            capabilities:
              add: ['SYS_ADMIN']
```

DCGM Exporter 暴露的关键指标：

```text
DCGM_FI_DEV_GPU_UTIL                   # GPU 利用率 (0-100)
DCGM_FI_DEV_MEM_COPY_UTIL              # 显存带宽利用率 (0-100)
DCGM_FI_DEV_FB_USED                    # 已使用显存 (MiB)
DCGM_FI_DEV_FB_FREE                    # 可用显存 (MiB)
DCGM_FI_DEV_GPU_TEMP                   # GPU 温度 (摄氏度)
DCGM_FI_DEV_POWER_USAGE                # 功耗 (瓦特)
DCGM_FI_DEV_SM_CLOCK_CURRENT           # 当前 SM 时钟频率 (MHz)
DCGM_FI_DEV_PCIE_TX_THROUGHPUT         # PCIe 发送吞吐 (KB/s)
DCGM_FI_DEV_PCIE_RX_THROUGHPUT         # PCIe 接收吞吐 (KB/s)
```

#### 2.2 PromQL 查询示例

**TTFT p95 查询**

```promql
# TTFT p95（过去 5 分钟）
histogram_quantile(0.95,
  sum(rate(vllm:time_to_first_token_seconds_bucket{model="qwen-72b"}[5m]))
  by (le, model)
)

# TTFT p99（过去 5 分钟），按实例分组
histogram_quantile(0.99,
  sum(rate(vllm:time_to_first_token_seconds_bucket[5m]))
  by (le, instance)
)

# TTFT 超过 2 秒的请求比例
sum(rate(vllm:time_to_first_token_seconds_bucket{le="2.0"}[5m]))
/
sum(rate(vllm:time_to_first_token_seconds_count[5m]))
```

**TPOT p95 查询**

```promql
# TPOT p95（过去 5 分钟）
histogram_quantile(0.95,
  sum(rate(vllm:time_per_output_token_seconds_bucket[5m]))
  by (le, model)
)

# TPOT 超过 100ms 的请求比例
1 - (
  sum(rate(vllm:time_per_output_token_seconds_bucket{le="0.1"}[5m]))
  /
  sum(rate(vllm:time_per_output_token_seconds_count[5m]))
)
```

**GPU 利用率查询**

```promql
# 平均 GPU 利用率（按节点）
avg(DCGM_FI_DEV_GPU_UTIL) by (instance)

# GPU 利用率超过 90% 的节点数
count(DCGM_FI_DEV_GPU_UTIL > 90)

# GPU 显存使用率
(DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100
```

**KV Cache 与队列查询**

```promql
# KV Cache 使用率
vllm:gpu_cache_usage_perc{model="qwen-72b"}

# 排队请求数
vllm:num_requests_waiting{model="qwen-72b"}

# 排队超过 10 秒的请求数（需要 histogram）
histogram_quantile(0.95,
  sum(rate(vllm:e2e_request_latency_seconds_bucket[5m]))
  by (le, model)
) - histogram_quantile(0.95,
  sum(rate(vllm:time_to_first_token_seconds_bucket[5m]))
  by (le, model)
)
```

**错误预算消耗速率查询**

```promql
# 可用性 SLI：成功率
sum(rate(vllm:request_success_total{finish_reason="stop"}[30d]))
/
sum(rate(vllm:e2e_request_latency_seconds_count[30d]))

# 错误预算剩余比例
1 - (
  (1 - sum(rate(vllm:request_success_total{finish_reason="stop"}[30d]))
       / sum(rate(vllm:e2e_request_latency_seconds_count[30d])))
  / (1 - 0.999)  # SLO = 99.9%
)

# 30 天滚动窗口的错误预算消耗速率
# （过去 1 小时的错误率 / SLO 允许的月度错误率）× (30天 / 1小时)
(
  1 - sum(rate(vllm:request_success_total{finish_reason="stop"}[1h]))
      / sum(rate(vllm:e2e_request_latency_seconds_count[1h]))
) / (1 - 0.999) * (30 * 24)
```

#### 2.3 Grafana Dashboard JSON 模板

以下是体验屏核心面板的 JSON 配置片段：

```json
{
  "dashboard": {
    "title": "LLM Inference - 用户体验",
    "tags": ["llm", "inference", "sre"],
    "timezone": "browser",
    "panels": [
      {
        "title": "TTFT p95",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(vllm:time_to_first_token_seconds_bucket{model=\"$model\"}[5m])) by (le))",
            "legendFormat": "TTFT p95",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 1.5 },
                { "color": "red", "value": 3.0 }
              ]
            }
          }
        }
      },
      {
        "title": "TPOT p95",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 6, "y": 0 },
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(vllm:time_per_output_token_seconds_bucket{model=\"$model\"}[5m])) by (le))",
            "legendFormat": "TPOT p95",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 0.08 },
                { "color": "red", "value": 0.15 }
              ]
            }
          }
        }
      },
      {
        "title": "成功率",
        "type": "gauge",
        "gridPos": { "h": 4, "w": 6, "x": 12, "y": 0 },
        "targets": [
          {
            "expr": "sum(rate(vllm:request_success_total{model=\"$model\"}[5m])) / sum(rate(vllm:e2e_request_latency_seconds_count{model=\"$model\"}[5m]))",
            "legendFormat": "成功率",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "min": 0,
            "max": 1,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                { "color": "red", "value": null },
                { "color": "yellow", "value": 0.99 },
                { "color": "green", "value": 0.999 }
              ]
            }
          }
        }
      },
      {
        "title": "排队请求数",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 18, "y": 0 },
        "targets": [
          {
            "expr": "sum(vllm:num_requests_waiting{model=\"$model\"})",
            "legendFormat": "Waiting",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "mode": "absolute",
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 10 },
                { "color": "red", "value": 50 }
              ]
            }
          }
        }
      },
      {
        "title": "TTFT 分布（按百分位）",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 4 },
        "targets": [
          {
            "expr": "histogram_quantile(0.50, sum(rate(vllm:time_to_first_token_seconds_bucket{model=\"$model\"}[5m])) by (le))",
            "legendFormat": "p50",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.95, sum(rate(vllm:time_to_first_token_seconds_bucket{model=\"$model\"}[5m])) by (le))",
            "legendFormat": "p95",
            "refId": "B"
          },
          {
            "expr": "histogram_quantile(0.99, sum(rate(vllm:time_to_first_token_seconds_bucket{model=\"$model\"}[5m])) by (le))",
            "legendFormat": "p99",
            "refId": "C"
          }
        ]
      },
      {
        "title": "请求速率与错误率",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 4 },
        "targets": [
          {
            "expr": "sum(rate(vllm:e2e_request_latency_seconds_count{model=\"$model\"}[5m]))",
            "legendFormat": "QPS",
            "refId": "A"
          },
          {
            "expr": "sum(rate(vllm:e2e_request_latency_seconds_count{model=\"$model\"}[5m])) - sum(rate(vllm:request_success_total{model=\"$model\"}[5m]))",
            "legendFormat": "错误数/s",
            "refId": "B"
          }
        ]
      }
    ],
    "templating": {
      "list": [
        {
          "name": "model",
          "type": "query",
          "query": "label_values(vllm:e2e_request_latency_seconds_count, model)",
          "refresh": 2,
          "multi": true,
          "includeAll": true
        }
      ]
    }
  }
}
```

#### 2.4 OpenTelemetry 集成配置

使用 OpenTelemetry SDK 在推理服务中注入链路追踪：

```python
# otel_config.py - vLLM 自定义指标暴露示例
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "vllm-inference",
    "service.version": "0.6.0",
    "deployment.environment": "production",
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("vllm.inference")

async def traced_inference(request):
    with tracer.start_as_current_span("inference_request") as span:
        span.set_attribute("model", request.model)
        span.set_attribute("input_tokens", len(request.prompt_tokens))
        span.set_attribute("max_tokens", request.max_tokens)

        with tracer.start_as_current_span("queue_wait"):
            # 排队等待
            await wait_for_slot(request)
            span.set_attribute("queue_time_ms", queue_time)

        with tracer.start_as_current_span("prefill"):
            # Prefill 阶段
            first_token = await model_prefill(request)
            span.set_attribute("prefill_time_ms", prefill_time)
            span.set_attribute("ttft_ms", queue_time + prefill_time)

        with tracer.start_as_current_span("decode"):
            # Decode 阶段
            tokens = []
            async for token in model_decode(first_token):
                tokens.append(token)
            span.set_attribute("decode_time_ms", decode_time)
            span.set_attribute("output_tokens", len(tokens))
            span.set_attribute("tpot_ms", decode_time / len(tokens))

        return tokens
```

#### 2.5 自定义指标暴露（vLLM / SGLang metrics endpoint）

**vLLM 启动时启用指标**

```bash
# vLLM 启动命令，启用 Prometheus 指标
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2-72B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 32768 \
    --enable-prefix-caching \
    --port 8000 \
    --disable-log-requests
    # vLLM 默认在 :8000/metrics 暴露 Prometheus 指标
```

**SGLang 启动时启用指标**

```bash
# SGLang 启动命令，启用 Prometheus 指标
python -m sglang.launch_server \
    --model Qwen/Qwen2-72B-Instruct \
    --tp 4 \
    --mem-fraction-static 0.88 \
    --max-total-token 65536 \
    --port 30000 \
    --enable-metrics
    # SGLang 在 :30000/metrics 暴露 Prometheus 指标
```

**验证指标端点**

```bash
# 检查 vLLM 指标是否正常暴露
curl -s http://localhost:8000/metrics | head -20

# 检查 DCGM Exporter 指标
curl -s http://localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL

# 测试 PromQL 查询
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(vllm:time_to_first_token_seconds_bucket[5m])) by (le))' \
  | jq '.data.result'
```

---

### 3. SRE 实战案例

#### 案例 1：TTFT 告警频繁但用户体验未受影响

**症状**

周一早上，值班人员收到多条 P2 告警："TTFT p99 超过 5 秒，持续 30 分钟"。但查看用户反馈渠道和满意度指标，没有用户抱怨。

**诊断过程**

```text
排查步骤                                      结论
──────────────────────────────────────────────────────────────────
1. 查看 TTFT p95 vs p99                       p95 = 1.8s（正常）
   Dashboard: 体验屏                          p99 = 6.2s（告警）
                                               差距巨大，说明长尾问题

2. 查看请求分布直方图                           95% 请求在 2s 以内
   Dashboard: 诊断屏                           4.9% 请求在 2-5s
                                               0.1% 请求在 5-30s

3. 筛选 TTFT > 5s 的请求特征                   全部来自同一租户
   按租户分组查看                               该租户 input_tokens 均 > 50000
                                               使用的模型为 qwen-72b

4. 检查该租户的请求模式                         批量提交了大量长文档摘要任务
   查看请求日志                                 单个请求 input_tokens 最高 120000
                                               这些请求 Prefill 阶段本身就需 3-5s

5. 检查该租户对整体指标的影响                    该租户 QPS 占比仅 0.3%
   计算加权影响                                 但贡献了 80% 的 p99 尾部延迟
                                               其他用户体验完全不受影响
```

**根因**

一个内部数据处理团队在批量提交超长上下文（50K-120K tokens）的文档摘要任务。这些请求的 Prefill 阶段本身就需 3-5 秒，属于正常的计算时间，不是系统异常。但由于它们混在同一个指标池中，拉高了全局 p99。

**修复**

```text
立即修复：
  1. 为该租户创建独立的 SLI 监控面板（按租户标签过滤）
  2. 调整告警规则：增加按租户分组的条件，避免单一租户触发全局告警

长期修复：
  1. 将长上下文请求路由到专用模型池（更大的 batch 容忍度，更宽松的 SLO）
  2. 引入分层 SLO：
     - 交互式请求（input < 8K）：TTFT p95 < 2s
     - 长上下文请求（input 8K-64K）：TTFT p95 < 5s
     - 超长上下文请求（input > 64K）：TTFT p95 < 15s
  3. 改用基于燃烧率的多窗口告警，降低长尾延迟对告警的干扰
```

**预防措施**

```promql
# 改进后的告警规则：仅关注交互式请求的 TTFT
histogram_quantile(0.95,
  sum(rate(vllm:time_to_first_token_seconds_bucket{input_tokens_bucket="<8k"}[5m]))
  by (le)
) > 2.0

# 长上下文请求单独告警（阈值更宽松）
histogram_quantile(0.95,
  sum(rate(vllm:time_to_first_token_seconds_bucket{input_tokens_bucket="8k-64k"}[10m]))
  by (le)
) > 5.0
```

**经验总结**

- p99 对长尾极其敏感，少量异常请求就能触发告警。SLO 应主要基于 p95 或更合理的分位数。
- 不同请求模式（短交互 vs 长文档）应有不同 SLO，混在一起会导致告警失真。
- 告警规则应支持按租户、模型、请求类型分组，避免局部问题触发全局告警。

#### 案例 2：GPU 利用率低但用户延迟高

**症状**

用户反馈"响应变慢了"，但运维团队查看 Dashboard 发现 GPU 利用率只有 30%，远低于正常水平（60-75%）。初步判断"资源充足，不是容量问题"，但用户延迟确实很高。

**诊断过程**

```text
排查步骤                                      结论
──────────────────────────────────────────────────────────────────
1. 确认延迟指标                                 TTFT p95 = 4.5s（正常 < 2s）
   Dashboard: 体验屏                          TPOT p95 = 120ms（正常 < 80ms）
                                               延迟确实异常

2. 查看队列状态                                 num_requests_waiting = 85
   Dashboard: 容量屏                          排队严重，但 GPU 利用率低
                                               矛盾！GPU 空闲但请求在排队

3. 检查 batch 大小                              avg_batch_size = 1.2
   Dashboard: 容量屏                          正常应该 8-16
                                               batch 严重碎片化

4. 分析请求结构                                 过去 1 小时请求模式变化：
   Dashboard: 诊断屏                          - 短请求（< 512 tokens）占比从 80% 降到 20%
                                               - 长请求（> 4K tokens）占比从 5% 升到 60%
                                               - 来源：新上线的 RAG 应用

5. 检查 KV Cache 使用情况                       KV Cache 使用率 = 92%
   查看 vllm:gpu_cache_usage_perc              接近上限
                                               长请求占满 KV Cache，无法容纳更多 batch

6. 检查抢占事件                                 vllm:num_preemptions = 高
   查看 preempt 指标                           频繁抢占导致 GPU 在等待 KV 换入换出
                                               GPU 利用率低是因为"在等"而不是"空闲"
```

**根因分析**

```text
                    根因链条

  新 RAG 应用上线
       |
       v
  大量长上下文请求涌入（input 4K-16K tokens）
       |
       v
  KV Cache 被长请求占满（92% 使用率）
       |
       v
  新请求无法获得 KV Cache 空间
       |
       +---> 频繁抢占（preemption）：GPU 等待换入换出
       |
       +---> Batch Size 缩小到 1-2：无法充分利用 GPU 并行能力
       |
       v
  GPU 利用率低（"在等"而非"空闲"）
  用户延迟高（排队 + 小 batch 低效）
```

这是一个典型的"GPU 利用率低 ≠ 系统空闲"的案例。GPU 利用率衡量的是计算单元的活跃时间，但当 GPU 在等待显存换入换出时，利用率会显示为低值。

**修复**

```text
立即修复：
  1. 限制该 RAG 应用的并发请求数（限流）
  2. 调整 max_model_len 限制，截断过长输入
  3. 临时扩容一组专门处理长上下文的实例

长期修复：
  1. 请求合并（Prompt Batching）：
     - 将同一用户的多个短 RAG 检索结果合并为一个长 prompt
     - 减少请求数，提高单请求的 batch 效率
  2. 分层路由：
     - 短请求（< 2K tokens）路由到专用短请求池（小 KV Cache，高并发）
     - 长请求（> 4K tokens）路由到专用长请求池（大 KV Cache，低并发）
  3. KV Cache 管理优化：
     - 启用 Prefix Cache，复用 RAG 应用的公共 system prompt
     - 调整 gpu_memory_utilization，为 KV Cache 预留更多空间
  4. 监控增强：
     - 同时监控 GPU 利用率和 batch 大小，两者同时异常才告警
     - 增加 KV Cache 使用率告警（> 85% 持续 5 分钟）
     - 增加抢占率告警（preemptions/s > 阈值）
```

**改进后的监控告警**

```promql
# 组合告警：GPU 利用率低 AND batch 小 AND 排队多
(
  avg(DCGM_FI_DEV_GPU_UTIL) < 40
  and
  avg(vllm:avg_batch_size) < 3
  and
  sum(vllm:num_requests_waiting) > 20
)
# 这个组合条件说明：GPU 看起来空闲，但实际上有请求在排队
# 根因通常是 KV Cache 压力或请求碎片化
```

**经验总结**

- GPU 利用率是必要但不充分的健康指标。必须和 batch 大小、KV Cache 使用率、排队长度一起看。
- "利用率低但延迟高"的典型根因是请求碎片化或 KV Cache 压力，不是"资源充足"。
- 新应用上线前应做容量评估，特别是对请求模式（长短、并发）的评估。
- 分层路由是解决长短请求混合的有效方案，避免长请求饿死短请求。

---

## 💻 实战练习

### 练习 1：基础操作——配置 Prometheus 采集 vLLM 指标并创建基础 Dashboard

**目标**：在本地环境搭建 Prometheus + Grafana，采集 vLLM 指标并创建一个包含 TTFT、TPOT、成功率、排队数的基础 Dashboard。

**步骤**

1. 启动 vLLM 服务（使用小模型即可）：

```bash
# 使用 Docker 启动 vLLM
docker run -d --gpus all \
    -p 8000:8000 \
    --name vllm-test \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2-1.5B-Instruct \
    --max-model-len 4096

# 验证指标端点
curl http://localhost:8000/metrics | head -30
```

2. 配置 Prometheus 采集：

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vllm'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

3. 启动 Prometheus 和 Grafana：

```bash
docker run -d -p 9090:9090 \
    -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

docker run -d -p 3000:3000 \
    -e GF_SECURITY_ADMIN_PASSWORD=admin \
    grafana/grafana
```

4. 在 Grafana 中创建 Dashboard，包含以下面板：
   - TTFT p95 时序图
   - TPOT p95 时序图
   - 成功率 gauge 图
   - 排队请求数 stat 图

5. 生成测试流量并观察指标变化：

```bash
# 使用 curl 生成测试请求
for i in $(seq 1 100); do
  curl -s http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "Qwen/Qwen2-1.5B-Instruct",
      "messages": [{"role": "user", "content": "解释什么是 SRE，用三句话"}],
      "max_tokens": 200
    }' > /dev/null &
done
```

**预期结果**：Grafana Dashboard 能实时展示 TTFT、TPOT、成功率和排队数的变化趋势。

---

### 练习 2：进阶场景——设计一个基于燃烧率的 TTFT 告警规则

**目标**：编写一个 Prometheus 告警规则，使用多窗口多燃烧率策略检测 TTFT 异常。

**步骤**

1. 理解燃烧率计算：

```text
燃烧率 = 实际错误消耗速率 / 预期错误消耗速率

SLO = 95% 的请求 TTFT < 2s
允许的"慢请求"比例 = 5%
30 天总分钟数 = 43,200 分钟
允许的"慢分钟数" = 43,200 × 5% = 2,160 分钟

如果过去 1 小时全是慢请求：
  燃烧率 = (100% / 5%) × (60分钟 / 43200分钟) × 43200 = 20x
  含义：1 小时内消耗了 20 倍的月度预算（即 20 小时的预算）

更实际的计算：
  如果过去 1 小时慢请求比例 = 30%
  燃烧率 = 30% / 5% = 6x
  含义：按此速率 5 天就会耗尽月度预算
```

2. 编写告警规则文件：

```yaml
# ttft_alerts.yml
groups:
  - name: ttft_burn_rate
    rules:
      # 快速燃烧：1 小时内可能耗尽月预算
      - alert: TTFTBurnRateCritical
        expr: |
          (
            1 - histogram_quantile(0.95,
              sum(rate(vllm:time_to_first_token_seconds_bucket[1h])) by (le)
            ) > bool 0.05
          ) and (
            1 - histogram_quantile(0.95,
              sum(rate(vllm:time_to_first_token_seconds_bucket[5m])) by (le)
            ) > bool 0.05
          )
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "TTFT SLO 快速燃烧（燃烧率 > 14x）"
          description: "过去 1 小时和 5 分钟的 TTFT p95 均超过 2s 目标"
          runbook_url: "https://wiki.internal/runbooks/ttft-burn-rate"

      # 中速燃烧：6 小时内可能耗尽月预算
      - alert: TTFTBurnRateHigh
        expr: |
          (
            1 - histogram_quantile(0.95,
              sum(rate(vllm:time_to_first_token_seconds_bucket[6h])) by (le)
            ) > bool 0.05
          ) and (
            1 - histogram_quantile(0.95,
              sum(rate(vllm:time_to_first_token_seconds_bucket[30m])) by (le)
            ) > bool 0.05
          )
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TTFT SLO 中速燃烧（燃烧率 > 6x）"
          description: "过去 6 小时和 30 分钟的 TTFT p95 均超过 2s 目标"
          runbook_url: "https://wiki.internal/runbooks/ttft-burn-rate"
```

3. 使用 `promtool` 验证规则：

```bash
# 验证规则语法
promtool check rules ttft_alerts.yml

# 使用测试数据验证规则逻辑
cat > test_data.txt << 'EOF'
# 模拟正常场景：TTFT p95 = 1.2s
vllm:time_to_first_token_seconds_bucket{le="1.0"} 100
vllm:time_to_first_token_seconds_bucket{le="2.0"} 950
vllm:time_to_first_token_seconds_bucket{le="+Inf"} 1000
vllm:time_to_first_token_seconds_count 1000
EOF
```

**预期结果**：告警规则能正确区分快速燃烧（P1）和中速燃烧（P2），并且短窗口 + 长窗口的组合能减少误报。

---

### 练习 3：故障排查挑战——GPU 利用率低但延迟高

**场景描述**

你是一名值班 SRE，收到用户反馈"API 响应变慢了"。打开 Dashboard 看到以下数据：

```text
┌─────────────────────────────────────────────────────────────────┐
│  练习 3：故障排查 Dashboard 快照                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TTFT p95:    4.8s  (目标 < 2s)      [红色]                     │
│  TPOT p95:    130ms (目标 < 100ms)    [红色]                     │
│  成功率:      99.2% (目标 > 99.9%)    [黄色]                     │
│  排队数:      120                    [红色]                     │
│                                                                 │
│  GPU 利用率:  25%   (正常 60-75%)     [绿色 - 看起来正常]        │
│  显存使用:    88%   (正常 < 85%)      [黄色]                     │
│  KV Cache:    95%   (正常 < 80%)      [红色]                     │
│  Batch Size:  1.5   (正常 8-16)      [红色]                     │
│  抢占率:      高                      [红色]                     │
│                                                                 │
│  最近变更: 2 小时前上线了新的 RAG 检索应用                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**你的任务**

1. 画出根因链条（从症状到根因）
2. 列出立即需要执行的 3 个操作
3. 设计长期预防方案
4. 编写一条组合告警规则，下次能更早发现类似问题

**参考答案思路**

```text
根因链条：
  新 RAG 应用上线 --> 长上下文请求激增 --> KV Cache 被占满 (95%)
       --> 频繁抢占 (preemption) --> Batch Size 缩小 (1.5)
       --> GPU "在等不在算" (利用率 25%) --> 排队堆积 (120)
       --> 用户延迟飙升 (TTFT 4.8s)

立即操作：
  1. 限流新 RAG 应用的并发（快速止血）
  2. 扩容长上下文专用池（增加容量）
  3. 调整 max_model_len 限制（控制单请求 KV 占用）

长期预防：
  1. 分层路由（短请求/长请求分离）
  2. Prefix Cache 优化（复用 system prompt）
  3. 新应用上线前的容量评估流程

组合告警规则：
  GPU 利用率 < 40% AND batch_size < 3 AND waiting_requests > 20
  持续 5 分钟触发 P2 告警
```

---

## 🎯 面试题精选

### 面试题 1：LLM 推理服务与传统 Web 服务的可观测性有什么本质差异？

**参考答案**

差异主要体现在四个维度：

1. **延迟结构不同**：传统 Web 服务的延迟是单一的"请求-处理-响应"；LLM 推理的延迟分为排队、Prefill、Decode 三个阶段，每个阶段的瓶颈类型不同（调度竞争 vs 计算密集 vs 带宽密集），需要分别度量和优化。

2. **资源耦合度不同**：传统服务的 CPU/内存/网络相对独立；LLM 推理的 GPU 利用率、显存、KV Cache 深度耦合——KV Cache 占满会导致抢占，抢占会降低 batch 效率，batch 变小会导致 GPU 利用率下降，但 GPU 利用率下降的根因不是"资源空闲"。

3. **多了"输出质量"维度**：传统服务的响应是确定性的（JSON 结构、数据库查询结果）；LLM 的输出是概率性的，同一个请求可能返回不同质量的结果。SLO 必须包含质量指标（空响应率、截断率、工具调用成功率），否则会保护"快速返回错误结果"。

4. **流式输出改变体验感知**：传统服务用 P99 延迟衡量体验；LLM 流式场景下，用户感知的是 TTFT（首包时间）和 TPOT（流式连贯性），总延迟的含义被弱化了。指标设计必须匹配用户的实际感知。

---

### 面试题 2：如何为 TTFT 和 TPOT 定义 SLO？

**参考答案**

TTFT SLO 定义步骤：

1. **确定 SLI**：TTFT p95（不是 p99，p99 对长尾太敏感）。
2. **按请求类型分层**：交互式请求（input < 8K tokens）和长上下文请求（input > 8K tokens）应有不同目标。
3. **参考基线**：采集过去 30 天的 TTFT 数据，取正常运行时的 p95 作为基线。
4. **设定目标**：交互式 TTFT p95 < 2s，长上下文 TTFT p95 < 5s。
5. **验证可行性**：目标应略宽松于当前基线（留 10-20% 余量），过紧会导致错误预算快速耗尽。

TPOT SLO 定义类似，但关注点不同：

- TPOT 影响流式输出的连贯性，用户对 TPOT 泤动更敏感。
- 建议 TPOT p95 < 100ms（对应约 10 tokens/s 的输出速率）。
- TPOT 的 SLO 应关注方差（稳定性），而不仅仅是绝对值。

关键原则：SLO 应基于用户可感知的体验，而不是技术指标的"好看程度"。如果用户满意度调查显示 TTFT < 3s 时满意度 > 90%，那么 SLO 目标就应该是 < 3s，而不是追求 < 1s。

---

### 面试题 3：错误预算如何影响发布决策？

**参考答案**

错误预算是连接"可靠性目标"和"发布节奏"的桥梁：

1. **预算充足时（> 50%）**：正常发布节奏，可以做灰度发布、A/B 测试、新功能上线。预算充足意味着你有"失败空间"，可以承受发布带来的风险。

2. **预算紧张时（20-50%）**：减少非必要发布，只发布高优先级修复。发布时使用更保守的灰度策略（如 1% -> 5% -> 20% -> 100%），每步观察错误预算消耗。

3. **预算即将耗尽时（< 20%）**：冻结所有非关键发布。已进入发布流程的变更需要回滚或暂停。团队应集中精力排查导致预算消耗的问题。

4. **预算耗尽时（0%）**：停止所有发布，全力恢复。事后复盘：为什么预算消耗这么快？SLO 是否合理？监控是否遗漏了什么？

实际操作中，可以在 CI/CD 流水线中集成错误预算检查：

```bash
# 在发布流水线中检查错误预算
BUDGET_REMAINING=$(curl -s "$PROMETHEUS/api/v1/query" \
  --data-urlencode "query=..." | jq '.data.result[0].value[1]')

if (( $(echo "$BUDGET_REMAINING < 0.2" | bc -l) )); then
  echo "ERROR: 错误预算剩余不足 20%，冻结发布"
  exit 1
fi
```

---

### 面试题 4：如何设计值班 Dashboard，让值班人员在事故中快速行动？

**参考答案**

三屏设计原则：

1. **屏 1：用户体验（第一眼看到）**：TTFT p95、TPOT p95、成功率、错误预算剩余。这四个指标回答"用户现在是否受影响"。用红/黄/绿颜色编码，异常一眼可见。

2. **屏 2：容量与资源（下钻一层）**：GPU 利用率、显存、KV Cache、排队数、batch 大小、扩缩容状态。当屏 1 发现异常时，屏 2 帮助判断是容量问题、调度问题还是配置问题。

3. **屏 3：诊断与排查（深入细节）**：按模型/租户/实例分组的详细指标、请求分布热力图、最近的 Trace 采样、错误日志流。当屏 2 定位到方向后，屏 3 提供具体的排查线索。

关键设计原则：

- **全局到局部**：Dashboard 顶部是全局聚合指标，往下钻取可以按模型、租户、实例分组。
- **症状到根因**：屏 1 是症状（延迟高），屏 2 是原因方向（KV Cache 满），屏 3 是根因（某租户长请求激增）。
- **每个面板有行动意义**：如果一个面板在事故中不会被查看，就不要放进去。宁可少而精，不要多而杂。

---

### 面试题 5：告警疲劳如何解决？

**参考答案**

告警疲劳的根因是"太多不重要的告警淹没了重要告警"。解决方案：

1. **用燃烧率替代静态阈值**：静态阈值（如 TTFT > 3s）在流量波动时频繁误报。燃烧率告警关注"错误预算被消耗的速度"，只有真正影响 SLO 的异常才触发。

2. **多窗口组合**：短窗口 + 长窗口同时满足才告警。短窗口防止"缓慢恶化但持续时间长"的漏报，长窗口防止"短暂波动"的误报。

3. **告警分级与路由**：P1 电话叫醒，P2 短信通知，P3 即时通讯消息，P4 邮件周报。不是所有告警都需要立即响应。

4. **告警与 Runbook 绑定**：每个告警附带处理手册，值班人员收到告警后知道"看哪个大盘、执行什么动作"。没有 Runbook 的告警不应该存在。

5. **定期清理**：每月审查告警列表，删除 30 天内没有触发过或触发了但无人处理的告警。一个没人看的告警比没有告警更糟——它消耗注意力。

6. **引入"告警静默"和"维护窗口"**：已知的计划内变更（如版本发布、扩缩容）期间，临时静默相关告警，避免"自己吓自己"。

---

### 面试题 6：如何判断"GPU 利用率低"是好事还是坏事？

**参考答案**

GPU 利用率低有三种可能：

1. **真的空闲**：流量低，GPU 在等待请求。这是好事——有充足的容量余量。检查 QPS 和并发请求数即可确认。

2. **在等显存操作**：KV Cache 压力大，GPU 在等待 KV 换入换出（preemption）。这是坏事——GPU 看起来空闲，但实际上请求在排队。需要同时看 KV Cache 使用率、抢占率和 batch 大小来确认。

3. **在等调度**：请求在队列中等待，但调度器没有分配到这个 GPU。可能是路由问题或调度器 bug。需要同时看排队数和调度器日志。

判断方法：不要单独看 GPU 利用率，要看组合指标：

- GPU 利用率高 + 排队多 = 容量不足，需要扩容
- GPU 利用率低 + 排队少 = 正常空闲，容量充足
- GPU 利用率低 + 排队多 + batch 小 = KV Cache 压力或调度问题
- GPU 利用率低 + KV Cache 满 + 抢占多 = KV Cache 压力，需要分层路由或扩容

---

### 面试题 7：如何用 OpenTelemetry 对 LLM 推理请求做链路追踪？

**参考答案**

LLM 推理请求的链路追踪需要覆盖以下 span：

1. **root span**：整个请求的生命周期（从 HTTP 请求到达到完整响应返回）。
2. **queue span**：排队等待阶段，记录 queue_time。
3. **prefill span**：Prefill 阶段，记录 input_tokens 数量和 prefill 耗时。
4. **decode span**：Decode 阶段，记录 output_tokens 数量和 decode 耗时。
5. **downstream spans**：如果有工具调用、RAG 检索、重试回退等，每个都是独立 span。

关键属性（attributes）：

- `model`：使用的模型名称
- `input_tokens`：输入 token 数
- `output_tokens`：输出 token 数
- `queue_time_ms`：排队时间
- `ttft_ms`：首 token 时间
- `tpot_ms`：每 token 时间
- `finish_reason`：完成原因（stop/length/error）
- `tenant_id`：租户标识
- `retry_count`：重试次数

实现要点：

- 使用 `BatchSpanProcessor` 而非 `SimpleSpanProcessor`，避免链路追踪本身成为性能瓶颈。
- 采样率根据流量调整：低流量 100% 采样，高流量 1-10% 采样，但错误请求 100% 采样。
- 确保 span 的 parent-child 关系正确，否则无法重建请求路径。

---

### 面试题 8：KV Cache 使用率告警阈值应该怎么设？

**参考答案**

KV Cache 使用率告警需要分两层：

1. **黄色告警（85%）**：KV Cache 接近饱和，新的长上下文请求可能被拒绝或触发抢占。此时应检查是否有异常的长请求激增，考虑限流或扩容。

2. **红色告警（95%）**：KV Cache 严重不足，频繁抢占导致 TTFT 和 TPOT 同时恶化。此时应立即执行止血操作（限流、截断长请求、扩容）。

但阈值不是固定的，需要根据场景调整：

- 如果模型配置了较大的 `gpu_memory_utilization`（如 0.95），KV Cache 空间本身就有限，阈值应更保守（如 80%/90%）。
- 如果使用了 Prefix Cache，KV Cache 的"有效使用率"比表面数字低（因为前缀可以复用），阈值可以稍高。
- 如果业务以长上下文为主（如文档摘要），KV Cache 消耗快是正常的，阈值应更宽松，但需要配合排队数和 batch 大小一起看。

告警不应只看 KV Cache 使用率，应组合判断：

- KV Cache > 85% AND 抢占率上升 = 真实压力
- KV Cache > 85% AND 抢占率不变 = 可能只是长请求多，但系统还能处理

---

## 📚 深入阅读

- [Google SRE Book - Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)：SLO 设计的经典参考
- [Google SRE Book - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)：多窗口多燃烧率告警的原始论文
- [Prometheus - Histograms and Summaries](https://prometheus.io/docs/practices/histograms/)：理解 histogram_quantile 的原理和陷阱
- [vLLM Documentation - Metrics](https://docs.vllm.ai/en/latest/serving/metrics.html)：vLLM 暴露的完整指标列表
- [OpenTelemetry - LLM Observability](https://opentelemetry.io/docs/specs/semconv/gen-ai/)：GenAI 可观测性的语义约定
- [DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter)：GPU 指标采集的官方工具
- [Grafana - Dashboard Design Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)：Dashboard 设计最佳实践
- [02-glossary.md](./02-glossary.md)：术语表
- [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md)：推理引擎与服务架构
- [17-inference-performance-engineering.md](./17-inference-performance-engineering.md)：推理性能工程

---

## ✅ 自检清单

完成本章学习后，请逐项检查自己是否掌握：

- [ ] 能画出四层可观测性模型（体验、服务、资源、质量），并解释每层的核心指标
- [ ] 能定义 TTFT、TPOT、TPS、Queue Time 的 SLO，并说明为什么选择这些分位数和阈值
- [ ] 能计算错误预算和消耗速率，并解释消耗速率如何影响发布决策
- [ ] 能设计多窗口多燃烧率告警规则，并解释短窗口和长窗口各自的作用
- [ ] 能解释"GPU 利用率低但延迟高"的根因链条（KV Cache 压力 → 抢占 → batch 碎片化）
- [ ] 能搭建三屏值班 Dashboard（体验、容量、诊断），并说明每个面板的行动意义
- [ ] 能使用 PromQL 查询 TTFT p95、GPU 利用率、KV Cache 使用率等关键指标
- [ ] 能配置 DCGM Exporter 采集 GPU 硬件指标
- [ ] 能用 OpenTelemetry 对 LLM 推理请求做链路追踪，覆盖 queue/prefill/decode 三个阶段
- [ ] 能解决告警疲劳问题：燃烧率告警、分级路由、定期清理
