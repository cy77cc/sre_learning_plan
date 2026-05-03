# Day 166: LLMOps 基础综合

> 📅 日期：2026-05-03
> 📖 学习主题：LLMOps 基础综合（完整推理服务部署, 监控告警, 扩缩容, 成本优化, 故障排查）
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 161 (LLMOps 概述), Day 162 (GPU 基础设施运维), Day 163 (模型推理部署), Day 164 (推理服务指标与监控), Day 165 (模型微调流水线)

---

## 🎯 学习目标

完成本日学习后，你将能够：

1. 设计和部署完整的 LLM 推理服务架构
2. 搭建端到端的监控告警系统
3. 实现基于指标的自动扩缩容策略
4. 掌握 LLM 服务的成本优化方法
5. 系统性地排查和解决 LLM 服务故障

---

## 📖 核心知识点

### 1. 完整推理服务架构设计

#### 1.1 生产级 LLM 服务架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                    生产级 LLM 推理服务架构                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                        客户端层                                 │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │ │
│  │  │ Web App  │ │ API 客户端│ │ Agent    │ │ 内部服务  │         │ │
│  │  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘         │ │
│  └────────┼────────────┼────────────┼────────────┼────────────────┘ │
│           │            │            │            │                   │
│           └────────────┴─────┬──────┴────────────┘                   │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      API 网关层 (Nginx/Kong)                    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │ │
│  │  │ 认证鉴权  │ │ 速率限制  │ │ 请求路由  │ │ 负载均衡  │         │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                           │                                          │
│                           ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      推理服务层 (Kubernetes)                     │ │
│  │                                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  Namespace: llm-inference                                 │ │ │
│  │  │                                                          │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │ │
│  │  │  │ vLLM Pod 1   │  │ vLLM Pod 2   │  │ vLLM Pod 3   │     │ │ │
│  │  │  │ GPU: 0,1     │  │ GPU: 2,3     │  │ GPU: 4,5     │     │ │ │
│  │  │  │ Llama-70B    │  │ Llama-70B    │  │ Qwen-72B     │     │ │ │
│  │  │  │ TP=2         │  │ TP=2         │  │ TP=2         │     │ │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘     │ │ │
│  │  │                                                          │ │ │
│  │  │  ┌─────────────────────────────────────────────────────┐ │ │ │
│  │  │  │  HPA (Horizontal Pod Autoscaler)                    │ │ │ │
│  │  │  │  ├─ 指标: vllm:num_requests_waiting > 50           │ │ │ │
│  │  │  │  ├─ 指标: avg_gpu_utilization > 85%                 │ │ │ │
│  │  │  │  ├─ 最小副本: 2 (高可用)                             │ │ │ │
│  │  │  │  └─ 最大副本: 10 (成本控制)                          │ │ │ │
│  │  │  └─────────────────────────────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                           │                                          │
│                           ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      存储层                                     │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │ │
│  │  │ 模型存储  │ │ 日志存储  │ │ 指标存储  │ │ 配置中心  │         │ │
│  │  │ S3/NFS   │ │ Loki     │ │Prometheus │ │ ConfigMap │         │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      可观测性层                                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │ │
│  │  │ Grafana  │ │ Alertmgr │ │ Jaeger   │ │ PagerDuty │         │ │
│  │  │ Dashboard│ │ 告警管理  │ │ 链路追踪  │ │ 通知渠道  │         │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

#### 1.2 Kubernetes 部署配置

```yaml
# llm-inference-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama-70b
  namespace: llm-inference
  labels:
    app: vllm
    model: llama-3.1-70b
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vllm
      model: llama-3.1-70b
  template:
    metadata:
      labels:
        app: vllm
        model: llama-3.1-70b
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      # 节点选择：GPU 节点
      nodeSelector:
        nvidia.com/gpu.product: "NVIDIA-A100-SXM4-80GB"

      # 容忍 GPU 节点的 taint
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule

      # 反亲和性：不同 Pod 分散到不同节点
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: vllm
                  model: llama-3.1-70b
              topologyKey: kubernetes.io/hostname

      # 初始化容器：下载模型
      initContainers:
      - name: model-downloader
        image: curlimages/curl:latest
        command:
        - sh
        - -c
        - |
          if [ ! -d /models/llama-3.1-70b ]; then
            echo "Model not found, downloading..."
            # 使用 huggingface-cli 下载
            huggingface-cli download meta-llama/Llama-3.1-70B-Instruct \
              --local-dir /models/llama-3.1-70b
          else
            echo "Model already exists"
          fi
        volumeMounts:
        - name: model-storage
          mountPath: /models

      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - "--model"
        - "/models/llama-3.1-70b"
        - "--host"
        - "0.0.0.0"
        - "--port"
        - "8000"
        - "--tensor-parallel-size"
        - "4"
        - "--max-model-len"
        - "32768"
        - "--gpu-memory-utilization"
        - "0.9"
        - "--max-num-seqs"
        - "64"
        - "--enable-chunked-prefill"
        - "--disable-log-requests"

        ports:
        - containerPort: 8000
          name: http
          protocol: TCP

        resources:
          limits:
            nvidia.com/gpu: 4
            memory: "128Gi"
            cpu: "32"
          requests:
            nvidia.com/gpu: 4
            memory: "64Gi"
            cpu: "16"

        volumeMounts:
        - name: model-storage
          mountPath: /models
        - name: shm
          mountPath: /dev/shm

        # 健康检查
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300  # 模型加载需要时间
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        startupProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          failureThreshold: 20  # 最多等待 10 分钟

        # 优雅关闭
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 30"]

      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: model-pvc
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 8Gi

      terminationGracePeriodSeconds: 60
      # 保证滚动更新时不中断服务
---
# Service
apiVersion: v1
kind: Service
metadata:
  name: vllm-llama-70b
  namespace: llm-inference
spec:
  selector:
    app: vllm
    model: llama-3.1-70b
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  type: ClusterIP
---
# HPA 自动扩缩容
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-llama-70b-hpa
  namespace: llm-inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-llama-70b
  minReplicas: 2
  maxReplicas: 6
  metrics:
  # 基于排队请求数
  - type: Pods
    pods:
      metric:
        name: vllm_num_requests_waiting
      target:
        type: AverageValue
        averageValue: "30"
  # 基于 GPU 利用率
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_GPU_UTIL
      target:
        type: AverageValue
        averageValue: "80"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 300
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
      - type: Pods
        value: 1
        periodSeconds: 600
```

### 2. 端到端监控告警

#### 2.1 监控体系设计

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM 服务监控体系                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  层级 1: 业务指标                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  请求成功率 > 99.5%                                     │ │
│  │  TTFT P95 < 1s                                         │ │
│  │  TPS P50 > 30 tokens/s                                 │ │
│  │  用户满意度 > 4.0/5.0                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  层级 2: 服务指标                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  QPS / 并发数                                          │ │
│  │  请求排队时间                                           │ │
│  │  错误率 / 超时率                                        │ │
│  │  端到端延迟分布                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  层级 3: 资源指标                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  GPU 利用率 / 显存 / 温度 / 功耗                        │ │
│  │  CPU / 内存 / 磁盘 IO                                   │ │
│  │  网络带宽 / 连接数                                      │ │
│  │  容器资源使用                                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  层级 4: 基础设施指标                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  节点状态 / K8s 事件                                    │ │
│  │  GPU ECC 错误 / PCIe 错误                               │ │
│  │  磁盘空间 / 网络连通性                                   │ │
│  │  证书有效期                                             │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 2.2 告警分级与响应

```yaml
# alerting-rules-complete.yml
groups:
  # P0: 立即响应（5 分钟内）
  - name: llm_p0_critical
    rules:
      - alert: LLM_Service_Down
        expr: up{job="vllm"} == 0
        for: 1m
        labels:
          severity: critical
          priority: p0
        annotations:
          summary: "LLM 推理服务不可用"
          description: "实例 {{ $labels.instance }} 已宕机"
          runbook: "1. 检查 Pod 状态 2. 查看容器日志 3. 检查 GPU 状态"

      - alert: LLM_Error_Rate_Critical
        expr: |
          rate(vllm_request_failure[5m]) /
          (rate(vllm_request_success[5m]) + rate(vllm_request_failure[5m])) > 0.1
        for: 2m
        labels:
          severity: critical
          priority: p0
        annotations:
          summary: "LLM 请求失败率超过 10%"
          description: "当前失败率: {{ $value | humanizePercentage }}"

      - alert: GPU_ECC_Uncorrectable
        expr: DCGM_FI_DEV_ECC_VOL_UNCORR > 0
        for: 0m
        labels:
          severity: critical
          priority: p0
        annotations:
          summary: "GPU 存在不可修复 ECC 错误"
          description: "GPU {{ $labels.gpu }} 需要更换"

  # P1: 15 分钟内响应
  - name: llm_p1_high
    rules:
      - alert: LLM_High_TTFT
        expr: histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
          priority: p1
        annotations:
          summary: "TTFT P95 超过 2 秒"

      - alert: LLM_High_Queue
        expr: vllm:num_requests_waiting > 50
        for: 3m
        labels:
          severity: warning
          priority: p1
        annotations:
          summary: "请求排队过多，需要扩容"

      - alert: GPU_Memory_Critical
        expr: |
          (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
        for: 5m
        labels:
          severity: warning
          priority: p1
        annotations:
          summary: "GPU 显存使用超过 95%，存在 OOM 风险"

      - alert: GPU_Temperature_High
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: warning
          priority: p1
        annotations:
          summary: "GPU 温度过高"

  # P2: 1 小时内响应
  - name: llm_p2_medium
    rules:
      - alert: LLM_TTFT_Elevated
        expr: histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
          priority: p2
        annotations:
          summary: "TTFT P95 超过 1 秒，接近 SLO"

      - alert: GPU_Utilization_High
        expr: avg_over_time(DCGM_FI_DEV_GPU_UTIL[15m]) > 90
        for: 30m
        labels:
          severity: warning
          priority: p2
        annotations:
          summary: "GPU 利用率持续过高，建议扩容"

  # P3: 工作日内处理
  - name: llm_p3_low
    rules:
      - alert: GPU_Utilization_Low
        expr: avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) < 20
        for: 4h
        labels:
          severity: info
          priority: p3
        annotations:
          summary: "GPU 利用率持续过低，建议缩容"

      - alert: LLM_Cost_Exceeds_Budget
        expr: llm_monthly_cost_estimate > llm_cost_budget
        for: 1h
        labels:
          severity: info
          priority: p3
        annotations:
          summary: "LLM 服务成本超出预算"
```

#### 2.3 Grafana 综合 Dashboard

```json
{
  "dashboard": {
    "title": "LLM Ops 综合监控面板",
    "rows": [
      {
        "title": "服务概览",
        "panels": [
          {
            "title": "服务状态",
            "type": "stat",
            "targets": [
              {"expr": "up{job='vllm'}", "legendFormat": "实例 {{instance}}"}
            ],
            "fieldConfig": {
              "defaults": {
                "thresholds": {
                  "steps": [
                    {"value": 0, "color": "red"},
                    {"value": 1, "color": "green"}
                  ]
                }
              }
            }
          },
          {
            "title": "当前 QPS",
            "type": "stat",
            "targets": [
              {"expr": "sum(rate(vllm_request_success[1m]))", "legendFormat": "QPS"}
            ]
          },
          {
            "title": "活跃请求",
            "type": "stat",
            "targets": [
              {"expr": "sum(vllm:num_requests_running)", "legendFormat": "运行中"},
              {"expr": "sum(vllm:num_requests_waiting)", "legendFormat": "排队中"}
            ]
          }
        ]
      },
      {
        "title": "用户体验",
        "panels": [
          {
            "title": "TTFT 分布",
            "type": "timeseries",
            "targets": [
              {"expr": "histogram_quantile(0.50, rate(vllm:time_to_first_token_seconds_bucket[5m]))", "legendFormat": "P50"},
              {"expr": "histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m]))", "legendFormat": "P95"},
              {"expr": "histogram_quantile(0.99, rate(vllm:time_to_first_token_seconds_bucket[5m]))", "legendFormat": "P99"}
            ]
          },
          {
            "title": "生成速度 (TPS)",
            "type": "timeseries",
            "targets": [
              {"expr": "vllm:avg_generation_throughput_toks_per_s", "legendFormat": "TPS"}
            ]
          }
        ]
      },
      {
        "title": "GPU 资源",
        "panels": [
          {
            "title": "GPU 利用率",
            "type": "timeseries",
            "targets": [
              {"expr": "DCGM_FI_DEV_GPU_UTIL", "legendFormat": "GPU {{gpu}}"}
            ]
          },
          {
            "title": "显存使用",
            "type": "timeseries",
            "targets": [
              {"expr": "DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100", "legendFormat": "GPU {{gpu}}"}
            ]
          },
          {
            "title": "GPU 温度",
            "type": "gauge",
            "targets": [
              {"expr": "DCGM_FI_DEV_GPU_TEMP", "legendFormat": "GPU {{gpu}}"}
            ],
            "fieldConfig": {
              "defaults": {
                "min": 0, "max": 100,
                "thresholds": {
                  "steps": [
                    {"value": 0, "color": "green"},
                    {"value": 75, "color": "yellow"},
                    {"value": 85, "color": "red"}
                  ]
                }
              }
            }
          },
          {
            "title": "功耗",
            "type": "timeseries",
            "targets": [
              {"expr": "DCGM_FI_DEV_POWER_USAGE", "legendFormat": "GPU {{gpu}}"}
            ]
          }
        ]
      },
      {
        "title": "成本分析",
        "panels": [
          {
            "title": "Token 消耗趋势",
            "type": "timeseries",
            "targets": [
              {"expr": "increase(vllm:prompt_tokens[1h])", "legendFormat": "输入 tokens/h"},
              {"expr": "increase(vllm:generation_tokens[1h])", "legendFormat": "输出 tokens/h"}
            ]
          },
          {
            "title": "每千 Token 成本",
            "type": "stat",
            "targets": [
              {"expr": "llm_cost_per_1k_tokens", "legendFormat": "$/1K tokens"}
            ]
          }
        ]
      }
    ]
  }
}
```

### 3. 自动扩缩容策略

#### 3.1 扩缩容决策模型

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM 服务扩缩容策略                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  扩容触发条件 (满足任一):                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  条件 1: 请求排队 > 50 (持续 3 分钟)                    │ │
│  │  含义: 当前容量不足以处理请求量                          │ │
│  │  动作: 新增 1 个 Pod                                    │ │
│  │                                                        │ │
│  │  条件 2: GPU 利用率 > 85% (持续 5 分钟)                 │ │
│  │  含义: GPU 接近满载                                     │ │
│  │  动作: 新增 1 个 Pod                                    │ │
│  │                                                        │ │
│  │  条件 3: TTFT P95 > 2s (持续 5 分钟)                   │ │
│  │  含义: 用户体验开始下降                                  │ │
│  │  动作: 新增 1 个 Pod                                    │ │
│  │                                                        │ │
│  │  冷却时间: 5 分钟 (避免频繁扩容)                         │ │
│  │  最大副本数: 6 (成本控制)                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  缩容触发条件 (同时满足):                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  条件 1: GPU 利用率 < 30% (持续 30 分钟)                │ │
│  │  条件 2: 请求排队 = 0 (持续 30 分钟)                    │ │
│  │  条件 3: 当前副本数 > 最小副本数 (2)                    │ │
│  │                                                        │ │
│  │  动作: 减少 1 个 Pod                                    │ │
│  │  冷却时间: 10 分钟 (避免频繁缩容)                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  特殊策略:                                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  预测性扩容:                                             │ │
│  │  ├─ 基于历史流量模式，在高峰前扩容                       │ │
│  │  ├─ 工作日 9:00 扩容到 4 个副本                         │ │
│  │  └─ 周末/夜间缩容到 2 个副本                            │ │
│  │                                                        │ │
│  │  定时扩容:                                               │ │
│  │  ├─ CronJob: 0 8 * * 1-5 (工作日 8:00)                │ │
│  │  └─ CronJob: 0 22 * * * (每天 22:00 缩容)             │ │
│  │                                                        │ │
│  │  优雅缩容:                                               │ │
│  │  ├─ 发送 SIGTERM 给目标 Pod                             │ │
│  │  ├─ 等待当前请求完成 (最长 300s)                        │ │
│  │  ├─ 从 Service 中移除 Endpoint                         │ │
│  │  └─ 删除 Pod                                           │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 3.2 自定义指标扩缩容

```yaml
# 自定义指标 HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-custom-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-llama-70b
  minReplicas: 2
  maxReplicas: 6
  metrics:
  # 自定义指标: 排队请求数
  - type: Pods
    pods:
      metric:
        name: vllm_num_requests_waiting
      target:
        type: AverageValue
        averageValue: "30"
  # 自定义指标: GPU 利用率
  - type: Pods
    pods:
      metric:
        name: gpu_utilization
      target:
        type: AverageValue
        averageValue: "80"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 300
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
      - type: Pods
        value: 1
        periodSeconds: 600
```

```python
# custom_metrics_adapter.py - 自定义指标适配器
"""
将 vLLM 和 GPU 指标转换为 K8s 自定义指标
供 HPA 使用
"""

from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
import time

class CustomMetricsAdapter:
    def __init__(self, prometheus_url: str):
        self.prom = PrometheusConnect(url=prometheus_url)
        config.load_incluster_config()
        self.custom_api = client.CustomObjectsApi()

    def get_queue_size(self, namespace: str, deployment: str) -> float:
        """获取平均排队请求数"""
        query = f'avg(vllm:num_requests_waiting{{namespace="{namespace}",deployment="{deployment}"}})'
        result = self.prom.custom_query(query)
        if result:
            return float(result[0]["value"][1])
        return 0

    def get_gpu_utilization(self, namespace: str, deployment: str) -> float:
        """获取平均 GPU 利用率"""
        query = f'avg(DCGM_FI_DEV_GPU_UTIL{{namespace="{namespace}",deployment="{deployment}"}})'
        result = self.prom.custom_query(query)
        if result:
            return float(result[0]["value"][1])
        return 0

    def publish_custom_metrics(self, namespace: str, deployment: str):
        """发布自定义指标到 K8s Metrics API"""
        queue_size = self.get_queue_size(namespace, deployment)
        gpu_util = self.get_gpu_utilization(namespace, deployment)

        # 通过 Custom Metrics API 发布
        self.custom_api.create_namespaced_custom_object(
            group="custom.metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods",
            body={
                "kind": "MetricValueList",
                "apiVersion": "custom.metrics.k8s.io/v1beta1",
                "metadata": {},
                "items": [
                    {
                        "describedObject": {
                            "kind": "Pod",
                            "namespace": namespace,
                            "name": deployment,
                        },
                        "metricName": "vllm_num_requests_waiting",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "value": str(queue_size),
                    }
                ],
            },
        )

    def run(self, namespace: str, deployment: str, interval: int = 30):
        """持续发布指标"""
        while True:
            try:
                self.publish_custom_metrics(namespace, deployment)
            except Exception as e:
                print(f"Error publishing metrics: {e}")
            time.sleep(interval)
```

### 4. 成本优化策略

#### 4.1 成本优化全景

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM 服务成本优化策略                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  策略 1: 模型优化 (节省 50-75%)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ├─ 使用量化模型 (INT4: 显存减 4 倍)                    │ │
│  │  ├─ 选择合适大小的模型 (8B vs 70B)                      │ │
│  │  ├─ 使用 MoE 模型 (激活参数少)                          │ │
│  │  └─ 蒸馏小模型替代大模型                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  策略 2: 推理优化 (节省 30-50%)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ├─ PagedAttention 提高显存利用率                       │ │
│  │  ├─ Continuous Batching 提高 GPU 利用率                  │ │
│  │  ├─ 限制最大上下文长度                                  │ │
│  │  ├─ 使用 FP8 推理 (H100)                               │ │
│  │  └─ 开启 Chunked Prefill                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  策略 3: 基础设施优化 (节省 20-40%)                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ├─ 使用 Spot/抢占实例 (节省 60-70%)                    │ │
│  │  ├─ 自动扩缩容 (低谷期缩容)                             │ │
│  │  ├─ 预留实例 (长期使用折扣)                              │ │
│  │  ├─ 多模型共享 GPU (MIG/MPS)                            │ │
│  │  └─ 选择合适的 GPU 型号                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  策略 4: 架构优化 (节省 10-30%)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ├─ 语义缓存 (相似请求复用结果)                         │ │
│  │  ├─ 请求合并 (批量处理)                                 │ │
│  │  ├─ 分级服务 (不同 SLA 不同价格)                        │ │
│  │  ├─ 边缘推理 (小模型部署到边缘)                         │ │
│  │  └─ 混合部署 (在线+离线共享 GPU)                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  成本计算示例:                                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  场景: 100K 请求/天, 平均 700 tokens/请求               │ │
│  │                                                        │ │
│  │  优化前: 4x A100 80GB                                  │ │
│  │  月成本 = 4 × $3/h × 730h = $8,760                    │ │
│  │  每 1K tokens = $8,760 / (100K × 700 × 30 / 1000)     │ │
│  │            = $8,760 / 2,100K = $0.0042                 │ │
│  │                                                        │ │
│  │  优化后: 2x A100 80GB (INT4 量化 + 批处理优化)          │ │
│  │  月成本 = 2 × $3/h × 730h = $4,380                    │ │
│  │  每 1K tokens = $4,380 / 2,100K = $0.0021              │ │
│  │                                                        │ │
│  │  节省: 50% ($4,380/月)                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 5. 故障排查方法论

#### 5.1 故障排查流程

```
┌──────────────────────────────────────────────────────────────┐
│                LLM 服务故障排查流程                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: 确认故障现象                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  □ 服务完全不可用？还是部分不可用？                       │ │
│  │  □ 影响所有用户？还是特定用户/模型？                     │ │
│  │  □ 从什么时候开始？触发条件是什么？                      │ │
│  │  □ 有没有变更操作（部署/配置/扩容）？                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 2: 检查服务状态                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  kubectl get pods -n llm-inference                     │ │
│  │  kubectl describe pod <pod-name>                       │ │
│  │  kubectl logs <pod-name> --tail=100                    │ │
│  │  → 确认 Pod 状态、重启次数、事件                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 3: 检查 GPU 状态                                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  kubectl exec <pod> -- nvidia-smi                      │ │
│  │  → 检查 GPU 可见性、显存、温度、ECC 错误                │ │
│  │  dmesg | grep -i nvidia                                │ │
│  │  → 检查驱动/硬件错误                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 4: 检查推理引擎                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  curl http://<pod>:8000/health                         │ │
│  │  curl http://<pod>:8000/metrics                        │ │
│  │  → 检查 vLLM 状态、请求队列、错误率                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 5: 检查资源使用                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  kubectl top pod <pod-name>                            │ │
│  │  → CPU、内存使用是否异常                                │ │
│  │  检查 Grafana Dashboard                                │ │
│  │  → GPU 利用率、显存、TTFT、TPS 趋势                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 6: 检查网络和依赖                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  kubectl exec <pod> -- curl localhost:8000/health      │ │
│  │  → 本地连通性                                           │ │
│  │  检查 Service/Endpoint                                 │ │
│  │  → 服务发现是否正常                                     │ │
│  │  检查 Ingress/Gateway                                  │ │
│  │  → 外部访问是否正常                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Step 7: 根因分析与修复                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  5 Why 分析法:                                          │ │
│  │  为什么服务不可用？→ Pod Crash                         │ │
│  │  为什么 Pod Crash？→ OOM Killed                        │ │
│  │  为什么 OOM？→ 显存不足                                │ │
│  │  为什么显存不足？→ 长上下文请求消耗过多 KV Cache        │ │
│  │  为什么 KV Cache 过大？→ 没有限制 max_model_len        │ │
│  │  根因: 需要配置 --max-model-len 限制                    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 常见故障与处理

| 故障现象 | 可能原因 | 排查方法 | 解决方案 |
|----------|----------|----------|----------|
| Pod CrashLoopBackOff | OOM / CUDA 错误 | `kubectl logs --previous` | 调整显存限制、减小 batch |
| TTFT 突然升高 | 请求排队、GPU 满载 | 检查 `num_requests_waiting` | 扩容、限制请求速率 |
| TPS 下降 | GPU 降频、显存带宽饱和 | 检查温度、`mem_copy_util` | 散热、优化模型 |
| 请求超时 | 模型加载慢、推理卡住 | 检查 startup probe | 增加超时、重启服务 |
| 输出质量下降 | 量化精度、温度参数 | 对比不同温度输出 | 调整参数、换用高精度模型 |
| GPU 掉卡 | 硬件故障 | `dmesg \| grep NVRM` | 隔离故障 GPU、更换硬件 |
| 显存泄漏 | KV Cache 未释放 | 监控显存趋势 | 重启服务、升级 vLLM |
| 多卡通信超时 | NVLink/网络问题 | `nvidia-smi topo -m` | 检查硬件、调整 NCCL 配置 |

#### 5.3 故障排查脚本

```bash
#!/bin/bash
# llm_troubleshoot.sh - LLM 服务故障排查脚本

set -euo pipefail

NAMESPACE="${1:-llm-inference}"
DEPLOYMENT="${2:-vllm-llama-70b}"

echo "============================================"
echo "LLM 服务故障排查报告"
echo "时间: $(date)"
echo "命名空间: $NAMESPACE"
echo "部署: $DEPLOYMENT"
echo "============================================"

# 1. Pod 状态
echo ""
echo "--- Pod 状态 ---"
kubectl get pods -n "$NAMESPACE" -l "app=vllm,model=$DEPLOYMENT" -o wide

# 2. Pod 事件
echo ""
echo "--- 最近事件 ---"
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -20

# 3. Pod 日志
echo ""
echo "--- 最近日志 (每个 Pod 最后 50 行) ---"
for pod in $(kubectl get pods -n "$NAMESPACE" -l "app=vllm" -o jsonpath='{.items[*].metadata.name}'); do
    echo "=== $pod ==="
    kubectl logs "$pod" -n "$NAMESPACE" --tail=50 2>/dev/null || echo "无法获取日志"
done

# 4. GPU 状态
echo ""
echo "--- GPU 状态 ---"
for pod in $(kubectl get pods -n "$NAMESPACE" -l "app=vllm" -o jsonpath='{.items[*].metadata.name}'); do
    echo "=== $pod ==="
    kubectl exec "$pod" -n "$NAMESPACE" -- nvidia-smi --query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu,ecc.errors.uncorrected.aggregate.total --format=csv 2>/dev/null || echo "无法获取 GPU 信息"
done

# 5. 资源使用
echo ""
echo "--- 资源使用 ---"
kubectl top pods -n "$NAMESPACE" -l "app=vllm" 2>/dev/null || echo "metrics-server 不可用"

# 6. 服务端点
echo ""
echo "--- Service Endpoints ---"
kubectl get endpoints -n "$NAMESPACE" -l "app=vllm"

# 7. 健康检查
echo ""
echo "--- 健康检查 ---"
for pod in $(kubectl get pods -n "$NAMESPACE" -l "app=vllm" -o jsonpath='{.items[*].metadata.name}'); do
    echo "=== $pod ==="
    kubectl exec "$pod" -n "$NAMESPACE" -- curl -s http://localhost:8000/health 2>/dev/null || echo "健康检查失败"
done

# 8. vLLM 指标
echo ""
echo "--- vLLM 关键指标 ---"
for pod in $(kubectl get pods -n "$NAMESPACE" -l "app=vllm" -o jsonpath='{.items[*].metadata.name}'); do
    echo "=== $pod ==="
    kubectl exec "$pod" -n "$NAMESPACE" -- curl -s http://localhost:8000/metrics 2>/dev/null | grep -E "^vllm:" | head -20 || echo "无法获取指标"
done

echo ""
echo "============================================"
echo "排查完成"
echo "============================================"
```

---

## 💻 实战练习

### 练习 1：完整服务部署

**目标**：在 Kubernetes 上部署完整的 LLM 推理服务，包含监控和自动扩缩容。

```bash
#!/bin/bash
# deploy_complete_llm_service.sh

set -euo pipefail

echo "=== 部署完整 LLM 推理服务 ==="

# 1. 创建命名空间
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: llm-inference
  labels:
    app.kubernetes.io/part-of: llm-ops
EOF

# 2. 部署 GPU 设备插件
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.15.0/nvidia-device-plugin.yml

# 3. 创建模型存储 PVC
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-pvc
  namespace: llm-inference
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 200Gi
EOF

# 4. 部署 vLLM 服务
kubectl apply -f llm-inference-deployment.yaml

# 5. 部署 DCGM Exporter
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: llm-inference
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.8-3.6.0-ubuntu22.04
        ports:
        - containerPort: 9400
        securityContext:
          capabilities:
            add: ["SYS_ADMIN"]
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
EOF

# 6. 部署 Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.enabled=true

# 7. 等待服务就绪
echo "等待服务启动..."
kubectl wait --for=condition=ready pod -l app=vllm -n llm-inference --timeout=600s

# 8. 验证
echo ""
echo "=== 部署验证 ==="
kubectl get pods -n llm-inference
kubectl get svc -n llm-inference

echo ""
echo "=== 部署完成 ==="
```

### 练习 2：故障演练

**目标**：模拟常见故障并练习排查和恢复。

```bash
#!/bin/bash
# fault_injection.sh - LLM 服务故障演练

echo "=== 故障演练 ==="

# 演练 1: 模拟 OOM
echo ""
echo "--- 演练 1: 模拟 OOM ---"
echo "发送超长上下文请求..."
for i in $(seq 1 10); do
    curl -s http://localhost:8000/v1/chat/completions \
      -d '{
        "model": "test",
        "messages": [{"role": "user", "content": "'$(python3 -c "print('x ' * 50000)")'"}],
        "max_tokens": 100
      }' &
done
wait
echo "检查 Pod 状态..."
kubectl get pods -n llm-inference

# 演练 2: 模拟 GPU 温度过高
echo ""
echo "--- 演练 2: 模拟 GPU 压力 ---"
echo "运行 GPU 压力测试..."
kubectl exec -n llm-inference deploy/vllm-llama-70b -- \
  python3 -c "
import torch
# 创建大矩阵运算模拟 GPU 压力
for i in range(100):
    a = torch.randn(4096, 4096, device='cuda')
    b = torch.randn(4096, 4096, device='cuda')
    c = torch.mm(a, b)
" &
echo "监控 GPU 温度..."
watch -n 1 "kubectl exec -n llm-inference deploy/vllm-llama-70b -- nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"

# 演练 3: 模拟服务过载
echo ""
echo "--- 演练 3: 模拟服务过载 ---"
echo "发送大量并发请求..."
for i in $(seq 1 100); do
    curl -s http://localhost:8000/v1/chat/completions \
      -d '{"model":"test","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' &
done
wait
echo "检查排队情况..."
kubectl exec -n llm-inference deploy/vllm-llama-70b -- \
  curl -s http://localhost:8000/metrics | grep num_requests

echo ""
echo "=== 演练完成 ==="
```

### 练习 3：成本优化分析

**目标**：分析当前服务成本并提出优化建议。

```bash
#!/bin/bash
# cost_optimization_analysis.sh

echo "=== LLM 服务成本优化分析 ==="

# 1. 采集当前使用数据
echo "--- 当前使用数据 ---"
echo "GPU 数量:"
kubectl get nodes -l nvidia.com/gpu.present=true --no-headers | wc -l

echo "GPU 型号:"
kubectl get nodes -o json | jq -r '.items[].status.allocatable | keys[]' | grep nvidia

echo "GPU 利用率:"
kubectl exec -n llm-inference deploy/vllm-llama-70b -- \
  nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader

echo "显存使用:"
kubectl exec -n llm-inference deploy/vllm-llama-70b -- \
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# 2. 采集请求数据
echo ""
echo "--- 请求统计 ---"
echo "总请求数 (最近 24h):"
curl -s "http://prometheus:9090/api/v1/query?query=sum(increase(vllm_request_success[24h]))" | jq '.data.result[0].value[1]'

echo "平均 QPS:"
curl -s "http://prometheus:9090/api/v1/query?query=avg(rate(vllm_request_success[1h]))" | jq '.data.result[0].value[1]'

echo "TTFT P95:"
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(vllm:time_to_first_token_seconds_bucket[1h]))" | jq '.data.result[0].value[1]'

# 3. 生成优化建议
echo ""
echo "--- 优化建议 ---"
GPU_UTIL=$(kubectl exec -n llm-inference deploy/vllm-llama-70b -- \
  nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader | head -1)

if [ "$GPU_UTIL" -lt 30 ]; then
    echo "[高优先级] GPU 利用率仅 ${GPU_UTIL}%, 建议:"
    echo "  1. 缩减 GPU 数量"
    echo "  2. 启用 GPU 共享 (MIG/MPS)"
    echo "  3. 部署更多模型到同一 GPU"
elif [ "$GPU_UTIL" -lt 60 ]; then
    echo "[中优先级] GPU 利用率 ${GPU_UTIL}%, 建议:"
    echo "  1. 优化批处理参数"
    echo "  2. 增加并发限制"
else
    echo "[正常] GPU 利用率 ${GPU_UTIL}%"
fi

echo ""
echo "=== 分析完成 ==="
```

---

## 🎯 面试题精选

### 1. 设计一个生产级的 LLM 推理服务架构，需要考虑哪些方面？

**参考答案**：
需要考虑以下方面：

1. **高可用**：多副本部署（最少 2 个），跨节点分散，健康检查 + 自动重启
2. **性能**：选择合适的推理引擎（vLLM），配置批处理和量化，流式输出
3. **可观测性**：TTFT/TPS/GPU 利用率监控，告警规则，Dashboard
4. **扩缩容**：基于 GPU 利用率和队列深度的 HPA，定时扩缩容策略
5. **成本优化**：量化模型，Spot 实例，自动缩容，GPU 共享
6. **安全**：API 认证，速率限制，输入验证，日志审计
7. **容灾**：优雅关闭，请求超时控制，故障自动恢复
8. **存储**：模型持久化存储，快速加载

### 2. LLM 服务的 SLI/SLO 如何定义？

**参考答案**：
SLI（指标）：
- 可用性：健康检查成功率
- 延迟：TTFT P95 和 TPS P50
- 质量：请求成功率（非 5xx）

SLO（目标）：
- 可用性 > 99.9%（每月 43 分钟不可用）
- TTFT P95 < 1s（交互场景）
- TPS P50 > 30 tokens/s
- 请求成功率 > 99.5%

错误预算策略：
- 预算充足：正常发布
- 预算紧张：限制发布频率，增加 review
- 预算耗尽：冻结发布，专注稳定性

### 3. 如何实现 LLM 服务的自动扩缩容？

**参考答案**：
关键指标和阈值：
- 扩容：排队请求数 > 30（持续 3 分钟）或 GPU 利用率 > 85%（持续 5 分钟）
- 缩容：GPU 利用率 < 30%（持续 30 分钟）且排队 = 0

实现方式：
1. 使用 Kubernetes HPA + 自定义指标
2. 通过 Prometheus Adapter 将 vLLM 指标暴露给 HPA
3. 配置稳定窗口（扩容 5 分钟，缩容 10 分钟）防止抖动
4. 设置最小/最大副本数（最小 2 保证高可用）

注意事项：
- GPU 实例启动慢（5-15 分钟），需要提前扩容
- 模型加载慢（2-5 分钟），需要 startup probe
- 缩容时需要等待请求完成（优雅关闭）

### 4. 如何排查 LLM 服务延迟突然升高的问题？

**参考答案**：
系统性排查步骤：

1. **确认范围**：所有请求还是部分？所有模型还是特定模型？
2. **检查排队**：`vllm:num_requests_waiting` 是否升高？是则容量不足。
3. **检查 GPU**：利用率是否 100%？温度是否过高导致降频？
4. **检查显存**：是否接近 OOM？KV Cache 是否异常增长？
5. **检查网络**：客户端到服务端的网络延迟是否正常？
6. **检查输入**：是否有大量长上下文请求？输入 token 数是否异常？
7. **检查变更**：最近是否有部署、配置变更？
8. **检查资源**：CPU、内存是否充足？是否有资源竞争？

常见原因：
- GPU 满载需要扩容
- 长上下文请求阻塞队列
- GPU 温度过高降频
- 显存不足导致频繁 GC

### 5. 如何降低 LLM 推理成本？请给出具体的优化方案。

**参考答案**：
分层优化：

**第一层：模型优化（节省 50-75%）**
- 使用 INT4 量化（AWQ/GPTQ），显存减 4 倍
- 选择合适大小的模型（8B 能满足就不用 70B）
- 使用 MoE 模型（DeepSeek-V3 激活参数仅 37B/671B）

**第二层：推理优化（节省 30-50%）**
- 开启 Continuous Batching 提高吞吐
- 限制 max_model_len 减少 KV Cache
- 使用 FP8 推理（H100）

**第三层：基础设施优化（节省 20-40%）**
- 使用 Spot 实例（节省 60-70%，适合非关键服务）
- 自动扩缩容（低谷期缩容）
- 预留实例（长期使用折扣）

**第四层：架构优化（节省 10-30%）**
- 语义缓存（相似请求复用）
- 请求合并（批量处理）
- 分级服务（不同 SLA 不同配置）

### 6. 描述一次完整的 LLM 服务故障排查过程。

**参考答案**：
场景：用户反馈 API 响应变慢，偶有超时。

1. **确认现象**：检查 Grafana Dashboard，发现 TTFT P95 从 500ms 升到 3s，排队请求数 > 100。
2. **检查 Pod**：`kubectl get pods` 发现 3 个 Pod 都在运行，但 `kubectl top pod` 显示 CPU 使用率高。
3. **检查 GPU**：`nvidia-smi` 显示 GPU 利用率 98%，温度 88°C（接近降频阈值）。
4. **检查日志**：`kubectl logs` 发现大量长上下文请求（> 30K tokens）。
5. **根因分析**：新上线的功能使用了长上下文 RAG，导致 Prefill 时间大幅增加，GPU 满载。
6. **临时修复**：限制 max_model_len 为 16K，增加 1 个副本。
7. **长期修复**：优化 RAG 的 chunk 大小，启用 Chunked Prefill，配置请求级别的超时和限制。

---

## 📚 深入阅读

### 架构设计
- [vLLM Production Guide](https://docs.vllm.ai/en/latest/serving/deploying_with_docker.html) - 生产部署指南
- [Kubernetes GPU Scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/) - GPU 调度
- [NVIDIA Device Plugin](https://github.com/NVIDIA/k8s-device-plugin) - K8s GPU 支持

### 监控与运维
- [Prometheus Operator](https://prometheus-operator.dev/) - K8s 监控
- [Grafana LLM Dashboard](https://grafana.com/grafana/dashboards/) - Dashboard 模板
- [Google SRE Book](https://sre.google/) - SRE 理论基础

### 成本优化
- [AWS GPU Pricing](https://aws.amazon.com/ec2/pricing/) - GPU 实例价格
- [Spot Instance Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html) - Spot 实例指南

---

## ✅ 自检清单

- [ ] 能设计生产级 LLM 推理服务架构
- [ ] 能编写 Kubernetes 部署配置（Deployment, Service, HPA）
- [ ] 能搭建完整的监控告警系统
- [ ] 能设计告警分级策略（P0-P3）
- [ ] 能实现基于自定义指标的自动扩缩容
- [ ] 能列举至少 5 种成本优化策略
- [ ] 能系统性排查 LLM 服务故障
- [ ] 能编写故障排查脚本
- [ ] 能进行故障演练
- [ ] 完成了所有 3 个实战练习

---

*由 SRE 学习计划生成 | 2026-05-03*
