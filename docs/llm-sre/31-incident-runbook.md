# LLM SRE 31：事故处置手册

> 📅 日期：2026-05-03
> 📖 学习主题：常见 LLM 平台事故的标准化处置流程
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：主教程 16-19 系列

## 🎯 学习目标

- 能独立处置 10 类常见 LLM 平台事故
- 能在限定时间内完成止血和恢复
- 能编写事后复盘报告
- 理解 LLM 平台事故与传统服务事故的本质差异
- 掌握事故升级路径与证据保留规范

---

## 📖 核心知识点

### 1. 为什么需要标准化事故处置

#### LLM 平台事故的特殊性

LLM 平台与传统 Web 服务存在本质差异，这些差异直接决定了事故处置策略的不同：

**资源模型不同**

传统服务以 CPU/内存为核心资源，而 LLM 推理服务以 GPU 显存为核心瓶颈。一块 A100 80GB 的显存同时承载模型权重、KV Cache、激活值和运行时开销，任何一项的波动都可能触发 OOM。GPU 资源不可像 CPU 那样被多个进程灵活共享，一旦显存耗尽，后果是实例直接崩溃而非排队等待。

**性能指标不同**

传统服务关注 QPS、P99 延迟和错误率。LLM 推理服务需要额外关注：
- TTFT（Time To First Token）：首 Token 延迟，直接影响用户体感
- Tokens/s：生成吞吐量，反映 Decode 阶段效率
- KV Cache 命中率：Prefix Cache 的有效性直接影响 TTFT
- Batch 利用率：GPU 是否被有效填满

**故障模式不同**

传统服务故障通常是请求级别的（超时、500 错误），而 LLM 平台故障往往是资源级别的：
- GPU OOM 导致实例反复重启形成重启风暴
- NCCL hang 导致多节点训练任务整体卡死
- 模型加载失败导致扩容完全失效
- 模型质量回退在指标上可能几乎不可见，但用户体验急剧恶化

**恢复手段不同**

传统服务重启即可恢复，LLM 平台的恢复可能涉及：
- 重新加载数十 GB 的模型权重（耗时数分钟）
- 重建 KV Cache（影响 Prefix Cache 命中率）
- 重新预热 Batch（影响吞吐量恢复速度）
- 切换模型版本（涉及路由、权重、Prompt 联动）

#### 标准化处置的价值

标准化处置流程解决三个核心问题：

1. **减少决策时间**：oncall 工程师不需要在高压环境下从零思考，直接按照检查清单执行
2. **避免遗漏关键步骤**：事故处置中常见的失误不是技术能力不足，而是高压下遗漏了某个检查项
3. **积累组织知识**：每次事故的处置经验通过复盘反馈到手册中，形成组织级的故障处理能力

#### 与传统服务事故的区别

| 维度 | 传统服务事故 | LLM 平台事故 |
|------|-------------|-------------|
| 核心资源 | CPU/内存 | GPU 显存/算力 |
| 扩容速度 | 秒级（容器启动） | 分钟级（模型加载） |
| 性能基线 | QPS/P99 | TTFT/tokens/s/batch |
| 质量退化 | 功能不可用 | 输出质量下降但服务存活 |
| 恢复手段 | 重启/扩容/回滚 | 重启/预热/切池/回滚联动 |
| 爆炸半径 | 请求级 | 实例级、模型池级、租户级 |
| 典型瓶颈 | 数据库/网络/依赖服务 | GPU 显存/NCCL/向量库 |

### 2. 事故处置通用流程

#### 标准七步流程

```
发现 -> 确认 -> 定级 -> 止血 -> 排查 -> 恢复 -> 复盘
```

**第一步：发现**

事故来源通常是：
- 监控告警（Prometheus/Grafana 阈值触发）
- 用户反馈（客服渠道、飞书群、工单系统）
- 定时巡检（SLO 看板异常）
- 依赖方通报（上游/下游团队发现异常）

**第二步：确认**

快速验证事故是否真实发生：
- 检查对应指标看板是否出现异常趋势
- 复现用户反馈的问题场景
- 排除监控系统自身故障（告警风暴 vs 真实事故）

**第三步：定级**

根据影响范围和严重程度确定事故等级：

| 等级 | 定义 | 响应要求 | 示例 |
|------|------|---------|------|
| P0 | 核心服务完全不可用 | 5 分钟内响应，全员就位 | 全局 GPU OOM、模型服务完全不可用 |
| P1 | 核心功能严重降级 | 10 分钟内响应，oncall + 二线 | TTFT 飙升 10 倍、tokens/s 下降 50% |
| P2 | 非核心功能受影响 | 30 分钟内响应，oncall 处理 | 向量检索超时、单租户资源争抢 |
| P3 | 局部异常，不影响用户 | 2 小时内响应，按计划修复 | 模型版本不一致但不影响服务 |

**第四步：止血**

止血的核心原则：**先恢复服务，再定位根因**。

止血动作按优先级排序：
1. 隔离故障范围（摘除异常实例/切走流量）
2. 降低压力（限流/缩小并发/缩短上下文）
3. 切换到备用方案（备用模型池/备用地域/降级路径）
4. 回滚最近变更（模型版本/Prompt/索引/配置）

**第五步：排查**

在止血措施生效后，开始系统性排查根因：
- 收集时间线：事故发生时间、最近变更时间、告警触发时间
- 对比基线：当前指标 vs 事故前指标 vs 上周同期
- 缩小范围：全局 vs 单池 vs 单实例 vs 单租户
- 定位变更：模型、配置、流量、基础设施四个维度

**第六步：恢复**

逐步恢复服务到正常状态：
1. 验证止血措施已生效（指标回落到目标区间）
2. 逐步放开限流/恢复并发
3. 确认备用方案可以切回主方案
4. 监控恢复过程中的指标波动

**第七步：复盘**

在事故结束后 48 小时内完成复盘：
- 编写事故时间线
- 分析根因（5 Whys 或鱼骨图）
- 制定改进项（短期修复 + 长期预防）
- 跟踪改进项落地

#### 升级条件与升级路径

**升级条件**

以下情况必须升级：
- 15 分钟内无法完成止血
- 影响范围扩大（单实例 -> 多实例 -> 全局）
- 影响高优先级租户或核心业务链路
- 需要跨团队协作（网络/存储/调度/驱动团队）
- 需要执行高风险操作（回滚模型版本、切换地域）

**升级路径**

```
L1 oncall（值班工程师）
  -> L2 二线（资深 SRE / 平台负责人）
    -> L3 三线（架构师 / 技术总监）
      -> CTO / VP Engineering（P0 事故持续 1 小时以上）
```

升级时需要同步的信息：
- 事故等级和影响范围
- 已执行的止血动作及其效果
- 当前排查方向和卡点
- 需要对方协助的具体事项

#### 证据保留要求

事故处置过程中必须保留以下证据：

**必须保留**
- 告警时间线（告警触发、确认、恢复的精确时间）
- 关键指标截图或导出数据（TTFT、tokens/s、错误率、GPU 利用率）
- 实例日志（事故前 10 分钟到恢复后 10 分钟）
- 变更记录（最近 24 小时内的所有变更）
- 操作记录（oncall 执行的所有止血动作）

**建议保留**
- 受影响请求的样本（包含 request/response）
- 配置快照（事故前后的配置对比）
- 通信记录（升级过程中的沟通内容）

---

### 3. 事故场景手册

---

#### 场景 1：GPU OOM

##### 症状

- TTFT 突然升高或出现大量超时
- 错误率急剧上升，实例日志出现 `CUDA out of memory` 或 ` RuntimeError: CUDA error: out of memory`
- KV Cache 分配失败，日志包含 `Failed to allocate KV cache`
- 容器被 OOM Killer 终止后反复重启，形成重启风暴
- 监控面板显示显存占用接近 100% 后突然归零（实例崩溃）

##### 前置检查

```bash
# 检查显存占用
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv

# 检查容器是否在反复重启
kubectl get pods -l app=llm-inference --sort-by='.status.containerStatuses[0].restartCount'

# 检查最近的发布记录
kubectl rollout history deployment/llm-inference

# 检查 KV Cache 水位（通过 Prometheus）
# kv_cache_usage_bytes / kv_cache_capacity_bytes
```

- 确认影响范围：单实例、单模型池还是全局
- 检查显存占用、KV Cache 水位、上下文长度分布
- 检查 waiting requests 数量和最近发布记录
- 确认是否有长上下文流量、RAG 拼接膨胀、热点 LoRA 切换或量化版本变更

##### 止血动作

**优先级 1：摘除反复 OOM 的实例**

```bash
# 标记节点不可调度，阻止新 Pod 调度上来
kubectl cordon <node-name>

# 删除反复重启的 Pod
kubectl delete pod <pod-name> -n llm-inference

# 如果是 StatefulSet，需要确认替换实例已就绪
```

原因：反复 OOM 重启会消耗 GPU 资源并触发更多调度，形成正反馈循环。

**优先级 2：下调资源使用上限**

```bash
# 通过 ConfigMap 下调最大上下文长度
kubectl edit configmap llm-inference-config
# 修改 max_model_len: 4096 -> 2048

# 或通过 API 热更新（如果支持）
curl -X POST http://inference-api/config -d '{"max_model_len": 2048}'

# 下调最大并发
curl -X POST http://inference-api/config -d '{"max_num_seqs": 16}'
```

原因：降低资源使用上限可以立即减少显存压力，是最快速的止血手段。

**优先级 3：执行流量限流**

```bash
# 对长请求限流（通过 API Gateway）
# 设置请求体大小限制
kubectl patch configmap gateway-config --patch '{"data":{"max_request_body":"65536"}}'

# 对低优先级租户执行限流
curl -X POST http://gateway/ratelimit -d '{"tenant": "low-priority", "qps": 5}'
```

原因：长请求和低优先级流量是显存压力的主要来源，限流可以快速释放资源。

**优先级 4：切到备用模型池**

```bash
# 修改路由规则，将流量切到备用池
kubectl apply -f routing-backup-pool.yaml

# 或通过 API Gateway 切流
curl -X POST http://gateway/routing -d '{"model": "llama-70b", "target_pool": "backup-pool"}'
```

**优先级 5：回滚到上一版**

```bash
# 回滚 Deployment
kubectl rollout undo deployment/llm-inference

# 或回滚到指定版本
kubectl rollout undo deployment/llm-inference --to-revision=<N>
```

##### 根因定位

```
GPU OOM 发生
    |
    +-- 单实例 OOM？
    |   |
    |   +-- 是 -> 检查该实例的请求特征
    |   |   |
    |   |   +-- 长上下文请求集中？-> 请求准入策略失效
    |   |   +-- KV Cache 异常膨胀？-> Paged Attention 参数变更
    |   |   +-- LoRA 热加载失败？-> LoRA 显存未释放
    |   |
    |   +-- 否 -> 检查全局因素
    |       |
    |       +-- 模型版本/量化配置变更？-> 版本回滚
    |       +-- 流量突增？-> 限流/扩容
    |       +-- 显存泄漏？-> 滚动重启
    |
    +-- 多实例同时 OOM？
        |
        +-- 检查是否有全局配置变更
        +-- 检查流量模式是否异常
        +-- 检查是否触发了重启风暴放大
```

**常见根因**

1. 上下文长度分布异常：某个租户或某类请求的上下文长度远超预期
2. KV Cache 参数配置不当：`gpu_memory_utilization` 设置过高，未预留足够的碎片空间
3. 新版本显存占用增大：模型权重或量化配置变更导致显存需求增加
4. 请求准入失效：并发限制或上下文长度限制未生效
5. LoRA 热加载异常：切换 LoRA 时旧 adapter 的显存未正确释放
6. Prefix Cache 失效：缓存命中率下降导致 KV Cache 重复计算

##### 后续改进

**短期修复**
- 为上下文长度、并发和 KV Cache 建立硬阈值告警（80% 预警，90% 紧急）
- 将 OOM 告警直接绑定降级动作（自动下调 max_model_len）
- 为 GPU 显存建立水位监控面板，实时展示各组件占用

**长期预防**
- 将长请求与常规请求分池部署，降低相互放大效应
- 建立显存预算管理机制，明确模型权重、KV Cache、激活值各自的显存配额
- 在推理引擎层面实现请求级别的显存预检，拒绝会触发 OOM 的请求
- 定期进行显存压力测试，验证当前配置在极端流量下的表现

##### 升级条件

- 15 分钟内无法止血（OOM 持续发生）
- 影响高优先级租户或核心业务链路
- 需要跨团队处理显存管理、GPU 调度或模型发布问题
- 需要执行全局回滚或切换备用模型池

##### 恢复判定

- OOM 告警停止触发，连续 10 分钟无新的 OOM 事件
- 错误率回落到基线范围（通常 < 0.1%）
- TTFT P95 恢复到目标区间
- 拒绝请求数回落到正常水平
- 实例重启次数不再增加

##### 需保留证据

- 告警时间线（OOM 首次发生时间、告警触发时间、oncall 响应时间）
- 实例日志（包含完整的 OOM 错误堆栈和上下文）
- 显存/KV Cache 监控曲线（事故前后 30 分钟）
- 变更记录（最近 24 小时的模型、配置、流量变更）
- 受影响请求样本（特别是触发 OOM 的长上下文请求）

##### 面试题关联

- Q: GPU OOM 和 CPU OOM 在处置策略上有什么本质区别？
- Q: 如何设计一个显存预算管理系统？
- Q: 什么是重启风暴？如何避免？

---

#### 场景 2：模型加载失败

##### 症状

- 新实例长时间卡在 Init 或 ContainerCreating 状态，readiness 探针持续失败
- 扩容操作生效但无新实例进入 Ready 状态，可用实例数不增加
- 实例日志出现 `Failed to load model weights`、`Tokenizer mismatch` 或 `CUDA initialization failed`
- HPA 显示 Desired > Ready，但扩容无法推进

##### 前置检查

```bash
# 检查 Pod 状态和事件
kubectl describe pod <pod-name> -n llm-inference

# 检查容器日志
kubectl logs <pod-name> -n llm-inference --tail=200

# 检查 Init 容器状态
kubectl get pods -n llm-inference -o wide

# 检查 PVC 和存储状态
kubectl get pvc -n llm-inference
kubectl describe pvc <pvc-name> -n llm-inference

# 检查节点 GPU 健康状态
kubectl get nodes -l accelerator=nvidia-gpu -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,GPU:.status.capacity.nvidia\.com/gpu
```

- 确认是单节点、单可用区还是整批实例失败
- 检查镜像版本、制品仓库状态、对象存储权限
- 检查磁盘空间和节点 GPU 健康状态
- 核对最近是否变更了权重路径、量化产物、Tokenizer、驱动或 CUDA/NCCL 版本

##### 止血动作

**优先级 1：暂停扩容**

```bash
# 暂停 HPA，防止故障放大到整池
kubectl patch hpa llm-inference-hpa -n llm-inference --patch '{"spec":{"minReplicas":0,"maxReplicas":0}}'

# 或直接设置为当前健康的实例数
kubectl scale deployment/llm-inference -n llm-inference --replicas=<healthy-count>
```

原因：如果加载失败是系统性问题，继续扩容只会产生更多失败实例，消耗资源并放大故障。

**优先级 2：切回稳定版本**

```bash
# 回滚到上一版稳定镜像和制品
kubectl rollout undo deployment/llm-inference -n llm-inference

# 确认回滚状态
kubectl rollout status deployment/llm-inference -n llm-inference
```

**优先级 3：切流到健康实例**

```bash
# 将流量切到现存健康实例
curl -X POST http://gateway/routing -d '{"strategy": "healthy-only"}'

# 或切到备用模型池
curl -X POST http://gateway/routing -d '{"model": "llama-70b", "target_pool": "backup-pool"}'
```

**优先级 4：隔离异常节点**

```bash
# 标记节点不可调度
kubectl cordon <node-name>

# 驱逐节点上的异常 Pod
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

##### 根因定位

```
模型加载失败
    |
    +-- 权重拉取失败？
    |   |
    |   +-- 网络超时？-> 检查对象存储连通性和带宽
    |   +-- 权限拒绝？-> 检查 IAM 角色和 Secret
    |   +-- 文件损坏？-> 校验权重文件 checksum
    |   +-- 磁盘空间不足？-> 清理本地缓存或扩容磁盘
    |
    +-- Tokenizer 不匹配？
    |   |
    |   +-- 版本不一致？-> 检查模型与 Tokenizer 是否来自同一发布单元
    |   +-- 配置错误？-> 检查 tokenizer_config.json
    |
    +-- 显存初始化失败？
    |   |
    |   +-- GPU 驱动问题？-> 检查 nvidia-smi 和驱动版本
    |   +-- CUDA 版本不兼容？-> 检查容器镜像中的 CUDA 版本
    |   +-- ECC 错误？-> 检查 GPU 硬件健康状态
    |
    +-- 校验错误？
        |
        +-- 权重完整性？-> 重新拉取并校验
        +-- 量化配置不匹配？-> 检查量化参数与权重是否一致
```

**常见根因**

1. 对象存储权限变更：IAM 角色过期或权限被收回
2. 权重文件不完整：上传中断或传输错误导致文件损坏
3. 版本不一致：模型权重、Tokenizer、推理引擎不属于同一发布单元
4. GPU 驱动问题：节点驱动版本与容器镜像中的 CUDA 版本不兼容
5. 磁盘空间不足：本地缓存占满磁盘，无法写入新权重
6. 网络带宽瓶颈：大批量拉取权重时带宽不足

##### 后续改进

**短期修复**
- 将模型加载前置为发布门禁：在 CI/CD 中加入离线的镜像和制品兼容性校验
- 为权重拉取、校验、显存预热和 readiness 分段打点，明确卡在哪一步
- 保持上一版制品和热实例可用，避免发布后只能硬扛

**长期预防**
- 将模型制品预拉取到节点本地缓存，减少运行时拉取风险
- 建立制品版本矩阵，确保模型权重、Tokenizer、量化产物、推理引擎版本一一对应
- 为节点 GPU 健康状态建立准入检查，不健康的节点不参与模型部署
- 实现权重加载的断点续传和校验重试机制

##### 升级条件

- 整池扩容受阻超过 10 分钟
- 需要制品仓库、对象存储或节点团队共同介入
- 影响多个模型池或多个可用区

##### 恢复判定

- 新实例可以在 5 分钟内通过 readiness 探针
- 扩容操作恢复生效，HPA Desired = Ready
- 流量不再依赖应急切流，主池可以正常服务

##### 需保留证据

- 加载失败日志（完整的错误堆栈和上下文）
- 制品引用信息（权重路径、版本号、checksum）
- 节点事件（kubectl describe 输出）
- 镜像版本信息（镜像 tag、digest）
- 对象存储/文件系统错误记录

##### 面试题关联

- Q: 模型加载失败的排查思路是什么？如何快速区分是存储问题还是 GPU 问题？
- Q: 如何设计一个可靠的模型制品发布流程？
- Q: 为什么不能简单地重启来解决模型加载失败？

---

#### 场景 3：TTFT 飙升

##### 症状

- TTFT P95/P99 快速抬升（例如从 500ms 上升到 5s）
- 用户明显感知首包变慢，应用层显示"正在思考"时间过长
- 常伴随 queue time 上升、waiting requests 增加
- 可能出现冷启动堆积（新实例预热期间 TTFT 异常高）

##### 前置检查

```bash
# 查看 TTFT 分布（通过 Prometheus）
# ttft_p50, ttft_p95, ttft_p99

# 区分 TTFT 上升的来源
# queue_time: 请求在队列中等待的时间
# prefill_time: Prefill 阶段的计算时间
# 首次加载时间: 冷启动导致的额外延迟

# 检查 Prefix Cache 命中率
# prefix_cache_hit_rate

# 检查 waiting requests 数量
# waiting_requests_count

# 检查输入长度分布
# input_length_p50, input_length_p95, input_length_p99
```

- 先区分 TTFT 上升是由 queue time、Prefill 还是冷启动造成
- 检查流量峰值、输入长度分布和 Prefix Cache 命中率
- 查看是否有新模型发布、路由切换、索引版本变更或 RAG 上下文膨胀

##### 止血动作

**优先级 1：对非核心流量限流**

```bash
# 通过 API Gateway 对低优先级接口限流
curl -X POST http://gateway/ratelimit -d '{
  "endpoint": "/api/v1/chat/completions",
  "priority": "low",
  "qps": 10
}'

# 对批量接口暂停服务
curl -X POST http://gateway/circuit-break -d '{"endpoint": "/api/v1/batch"}'
```

原因：非核心流量抢占资源是 TTFT 飙升的常见原因，限流可以立即释放资源给核心链路。

**优先级 2：强制扩容到已预热实例**

```bash
# 检查是否有预热实例可用
kubectl get pods -n llm-inference -l warm=true

# 如果有预热实例，修改路由将流量导入
curl -X POST http://gateway/routing -d '{"strategy": "prefer-warm"}'

# 如果没有预热实例，触发预热
curl -X POST http://inference-api/warmup -d '{"replicas": 3}'
```

**优先级 3：临时缩短上下文上限**

```bash
# 缩短最大上下文长度，减少 Prefill 计算量
curl -X POST http://inference-api/config -d '{"max_model_len": 2048}'

# 关闭高开销的 reranker
curl -X POST http://inference-api/config -d '{"enable_reranker": false}'

# 缩小检索的 top-k
curl -X POST http://inference-api/config -d '{"rag_top_k": 3}'
```

**优先级 4：回滚最近变更**

```bash
# 如果根因来自新版本或新路由，立即回滚
kubectl rollout undo deployment/llm-inference -n llm-inference
```

##### 根因定位

```
TTFT 飙升
    |
    +-- queue time 升高？
    |   |
    |   +-- 流量突增？-> 检查 QPS 变化趋势
    |   +-- 实例不足？-> 检查 HPA 状态和扩容速度
    |   +-- 请求堆积？-> 检查 waiting requests
    |
    +-- Prefill 时间升高？
    |   |
    |   +-- 输入长度增加？-> 检查 input_length 分布
    |   +-- Prefix Cache 失效？-> 检查缓存命中率
    |   +-- GPU 利用率低？-> 检查 batch 调度策略
    |
    +-- 冷启动延迟？
        |
        +-- 新实例预热慢？-> 检查模型加载时间
        +-- 扩容触发不及时？-> 检查 HPA 配置
```

**常见根因**

1. 流量突增超出容量规划：突发流量导致请求排队
2. Prefix Cache 命中率下降：Prompt 模板变更或缓存驱逐策略不当
3. 输入长度分布变化：RAG 上下文膨胀或长文档查询增多
4. 扩容不及时：HPA 配置过于保守或 readiness 探针过慢
5. 调度失衡：部分实例过载而其他实例空闲
6. 新版本 Prefill 效率下降：模型或推理引擎变更导致 Prefill 变慢

##### 后续改进

**短期修复**
- 保证所有核心告警同时展示 TTFT 和 queue time，避免误判
- 建立流量峰值前的预热和容量保底策略
- 优化 Prefix Cache 驱逐策略，提高缓存命中率

**长期预防**
- 为 RAG 请求单独监控上下文 token 数与拼接模板变更
- 实现智能路由，将长请求和短请求分发到不同的实例
- 建立自适应的 Prefill-Decode 分离架构（PD 分离）
- 优化 HPA 配置，使用 TTFT 作为扩缩容指标之一

##### 升级条件

- 连续两个观察窗口（每个窗口 5 分钟）未恢复
- 需要业务侧做强限流、功能降级或跨地域切流
- 影响核心业务链路（如客服对话、实时翻译）

##### 恢复判定

- TTFT P95 恢复到目标区间（通常 < 1s）
- queue time 回落到正常水平
- waiting requests 回落到正常范围
- 用户侧首包延迟恢复正常体感

##### 需保留证据

- TTFT/queue time 监控曲线（事故前后 30 分钟）
- 扩容事件记录（HPA 触发时间和扩缩容动作）
- 流量切换记录（路由变更历史）
- 请求长度分布变化（input_length 分位数对比）
- 灰度/发布记录（最近的模型或配置变更）

##### 面试题关联

- Q: TTFT 和 TBT（Time Between Tokens）分别影响什么用户体验？
- Q: Prefix Cache 的工作原理是什么？为什么会失效？
- Q: 如何设计一个智能路由策略来优化 TTFT？

---

#### 场景 4：tokens/s 下降

##### 症状

- 实例或模型池的 tokens/s 持续低于基线（例如从 30 tokens/s 降到 10 tokens/s）
- 常伴随 GPU 忙碌度下降、batch size 变小
- 输出吞吐抖动，部分请求生成速度明显变慢
- 用户感知为"回答生成变慢"

##### 前置检查

```bash
# 检查 tokens/s 指标
# tokens_per_second（按实例、模型池、租户分组）

# 检查 GPU 利用率
nvidia-smi --query-gpu=index,utilization.gpu --format=csv -l 5

# 检查 batch 指标
# batch_size_avg, running_requests, waiting_requests

# 检查请求长度结构
# output_length_p50, output_length_p95
```

- 检查是全局下降、单模型下降还是单租户下降
- 对比 GPU 利用率、batch size、running requests 和请求长度结构
- 确认是否刚上线了新量化方案、Speculative Decoding、Prefix Cache 或多 LoRA 复用策略

##### 止血动作

**优先级 1：切回稳定模型池**

```bash
# 将热点流量切回稳定模型池
curl -X POST http://gateway/routing -d '{
  "model": "llama-70b",
  "target_pool": "stable-pool"
}'

# 关闭收益不稳定的优化开关
curl -X POST http://inference-api/config -d '{
  "enable_speculative_decoding": false,
  "enable_prefix_caching": false
}'
```

原因：新上线的优化策略如果效果不达标，反而会降低吞吐量，切回稳定配置可以立即恢复。

**优先级 2：降低并发目标**

```bash
# 降低并发目标，避免系统在低效 batch 上空转
curl -X POST http://inference-api/config -d '{"max_num_seqs": 8}'
```

原因：当 batch 调度策略异常时，降低并发可以避免系统在低效状态下空转。

**优先级 3：对长输出限流**

```bash
# 对长输出或长上下文流量单独限流
curl -X POST http://gateway/ratelimit -d '{
  "condition": {"output_length_gt": 2048},
  "qps": 5
}'
```

##### 根因定位

```
tokens/s 下降
    |
    +-- GPU 利用率低？
    |   |
    |   +-- batch size 小？-> 检查 batch 调度策略
    |   +-- 请求被限流？-> 检查并发限制配置
    |   +-- 调度失衡？-> 检查各实例负载分布
    |
    +-- GPU 利用率正常但 tokens/s 低？
    |   |
    |   +-- Decode 效率下降？-> 检查 Decode 吞吐
    |   +-- 显存带宽瓶颈？-> 检查显存带宽利用率
    |   +-- 量化方案影响？-> 对比量化前后性能
    |
    +-- 单模型/单租户下降？
        |
        +-- LoRA 切换开销？-> 检查 LoRA 热加载频率
        +-- 特定请求模式？-> 分析慢请求特征
```

**常见根因**

1. Batch 被打散：多模型、多 LoRA、碎片化流量导致 batch 无法有效填充
2. 量化方案收益不达标：新量化方案在特定场景下性能反而下降
3. Speculative Decoding 失效：投机采样的命中率过低，反而增加了计算开销
4. 显存带宽瓶颈：KV Cache 过大导致 Decode 阶段受显存带宽限制
5. 调度策略保守：限流策略过于保守，限制了 batch 的有效填充
6. CPU/tokenization 瓶颈：tokenization 或日志写入成为隐藏瓶颈

##### 后续改进

**短期修复**
- 固化每次性能优化的回滚条件，不让值班时临时猜测
- 用流量回放持续校验 tokens/s 基线，不只看离线 benchmark
- 建立按模型池和租户分层的吞吐容量线

**长期预防**
- 实现自适应的 batch 调度策略，根据请求特征动态调整 batch 组成
- 建立性能优化的 A/B 测试框架，新策略必须在生产流量上验证
- 为 Decode 阶段建立独立的性能监控，区分 Prefill 和 Decode 的效率

##### 升级条件

- 吞吐下降持续超过 15 分钟
- 需要关闭核心优化开关或回退版本
- 需要调整租户配额或重新规划容量

##### 恢复判定

- tokens/s 恢复到稳定基线（允许 5% 的波动）
- batch size 恢复到正常水平
- GPU 忙碌度恢复到正常范围
- 未再依赖临时限流维持吞吐稳定

##### 需保留证据

- tokens/s 基线对比数据（事故前后的吞吐量对比）
- batch 指标（batch size、running requests、waiting requests）
- 优化开关状态（哪些开关被开启/关闭）
- 模型池路由记录（流量在各池之间的分布）
- 实例性能日志（各实例的吞吐量差异）

##### 面试题关联

- Q: Prefill 和 Decode 的性能瓶颈分别是什么？
- Q: 如何设计一个有效的 batch 调度策略？
- Q: Speculative Decoding 的原理和适用场景是什么？

---

#### 场景 5：NCCL Hang

##### 症状

- 多节点训练或推理扩展任务长时间无进展
- GPU 利用率异常低（接近 0%）或部分 rank 不前进
- 日志出现 `NCCL timeout`、`collective operation timeout` 或 `rank X failed to join collective`
- 作业运行时间远超预期但没有报错退出

##### 前置检查

```bash
# 检查作业状态
kubectl get pods -n training -l job-name=<job-name>

# 检查各 rank 的日志
kubectl logs <pod-name> -n training -c nccl-init --tail=100

# 检查 GPU 硬件状态
nvidia-smi --query-gpu=index,name,temperature.gpu,ecc.errors.corrected.aggregate.total,ecc.errors.uncorrected.aggregate.total --format=csv

# 检查网络连通性
kubectl exec <pod-name> -n training -- ibstat  # InfiniBand
kubectl exec <pod-name> -n training -- show_gids  # RoCE

# 检查节点事件
kubectl describe node <node-name>
```

- 确认是单作业问题还是同一节点池的普遍问题
- 检查最近驱动、CUDA、NCCL、OFED、容器镜像和交换机配置变更
- 核对受影响作业的节点拓扑、网卡错误计数、Xid/ECC 和调度落点

##### 止血动作

**优先级 1：终止无法恢复的作业**

```bash
# 删除已确定无法恢复的作业
kubectl delete job <job-name> -n training

# 释放被占用的 GPU 资源
kubectl delete pod -l job-name=<job-name> -n training
```

原因：hang 住的作业会持续占用 GPU 资源，如果不释放，后续作业也无法正常运行。

**优先级 2：隔离异常节点**

```bash
# 将异常节点从调度池摘除
kubectl cordon <node-name>

# 标记节点状态
kubectl label node <node-name> nccl-issue=true

# 阻止新作业落入异常节点
kubectl taint node <node-name> nccl-issue=true:NoSchedule
```

**优先级 3：回退到稳定配置**

```bash
# 回退到上一套稳定的驱动/NCCL/镜像组合
# 通常需要更新 Job 的容器镜像配置
kubectl apply -f job-stable-config.yaml

# 必要时缩小训练规模
kubectl patch job <job-name> -n training --patch '{"spec":{"parallelism":2}}'
```

**优先级 4：降级到单节点验证**

```bash
# 将作业降级为单节点运行，确认是否是多节点通信问题
kubectl patch job <job-name> -n training --patch '{
  "spec": {
    "parallelism": 1,
    "completions": 1
  }
}'
```

##### 根因定位

```
NCCL Hang 发生
    |
    +-- 单作业 hang？
    |   |
    |   +-- 特定节点组合？-> 检查节点拓扑和网络路径
    |   +-- 特定通信模式？-> 检查 AllReduce/AllGather/P2P
    |   +-- 环境变量问题？-> 检查 NCCL_* 环境变量
    |
    +-- 多作业同时 hang？
    |   |
    |   +-- 同一节点池？-> 检查交换机/网卡状态
    |   +-- 全局性问题？-> 检查驱动/NCCL 版本变更
    |
    +-- 间歇性 hang？
        |
        +-- 网络抖动？-> 检查 PFC/ECN 计数器
        +-- 热点节点？-> 检查节点温度和功耗
        +-- 竞争条件？-> 检查 rank 映射和初始化顺序
```

**常见根因**

1. 网络配置问题：RoCE/InfiniBand 配置错误、PFC/ECN 未正确启用
2. 驱动版本不兼容：CUDA/NCCL/OFED 版本之间存在已知的兼容性问题
3. 节点硬件故障：网卡错误、GPU Xid 错误、ECC 错误
4. 容器环境问题：缺少 NCCL 依赖库、环境变量配置错误
5. 交换机问题：交换机丢包、缓冲区溢出、固件 bug
6. rank 映射错误：checkpoint 恢复后 rank 映射不一致

##### 后续改进

**短期修复**
- 建立经过验证的 NCCL 版本矩阵（CUDA、NCCL、OFED、驱动的兼容组合）
- 为多节点作业保留网络与集体通信基线压测结果
- 建立节点健康准入检查，不健康的节点不参与多节点作业

**长期预防**
- 将异常节点自动隔离和复检纳入日常运维流程
- 建立 NCCL hang 的自动检测和作业自动重启机制
- 定期进行网络压力测试，验证集群在高负载下的通信稳定性
- 为关键训练任务建立 checkpoint 自动保存机制，减少 hang 导致的损失

##### 升级条件

- 影响多作业或整节点池
- 需要网络、集群、驱动团队协同排障
- 怀疑是交换机或网卡硬件故障

##### 恢复判定

- 作业可以重新初始化并持续推进
- NCCL timeout 不再出现
- 异常节点已被隔离或修复
- 新作业可以在健康节点上正常完成

##### 需保留证据

- 作业日志（各 rank 的完整日志）
- rank/节点映射信息
- 交换机或网卡错误计数
- 节点事件（kubectl describe 输出）
- 版本矩阵（CUDA、NCCL、OFED、驱动版本）

##### 面试题关联

- Q: NCCL 的集体通信原语有哪些？各自的应用场景是什么？
- Q: 如何排查 NCCL hang 问题？排查的关键步骤是什么？
- Q: RoCE 和 InfiniBand 在 NCCL 通信中的区别是什么？

---

#### 场景 6：向量检索超时

##### 症状

- RAG 请求端到端延迟显著升高
- 检索阶段出现 timeout 错误，日志包含 `vector search timeout` 或 `retrieval deadline exceeded`
- 空召回率激增（检索返回空结果）
- 应用层降级到无检索的回答模式（直接用 LLM 回答，不检索知识库）

##### 前置检查

```bash
# 检查向量库状态
curl http://vector-db:9200/_cluster/health?pretty

# 检查索引状态
curl http://vector-db:9200/_cat/indices?v

# 检查慢查询日志
curl http://vector-db:9200/_cat/tasks?v&detailed=true

# 检查 CPU/内存/磁盘水位
kubectl top pods -n vector-db

# 检查分片分布
curl http://vector-db:9200/_cat/shards?v&s=state
```

- 确认超时落在 query embedding、向量检索、reranker 还是元数据过滤阶段
- 检查向量库 CPU/内存/磁盘水位、分片热点和索引构建任务
- 核对是否刚进行了索引发布、embedding 模型升级或离线重建

##### 止血动作

**优先级 1：缩小检索范围**

```bash
# 缩小 top-k
curl -X POST http://rag-api/config -d '{"retrieval_top_k": 3}'

# 关闭 reranker
curl -X POST http://rag-api/config -d '{"enable_reranker": false}'

# 降级到关键词检索
curl -X POST http://rag-api/config -d '{"retrieval_mode": "keyword"}'
```

原因：缩小检索范围可以立即减少向量库的计算压力，是最快的止血手段。

**优先级 2：暂停离线任务**

```bash
# 暂停离线重建或批量导入
curl -X POST http://vector-admin/tasks/pause -d '{"task_type": "index_rebuild"}'

# 暂停批量导入
curl -X POST http://vector-admin/tasks/pause -d '{"task_type": "bulk_import"}'
```

原因：离线任务会与在线查询竞争 CPU/内存/磁盘资源，暂停离线任务可以释放资源给在线查询。

**优先级 3：切到备用分片**

```bash
# 将热点租户切到备用分片
curl -X POST http://vector-admin/routing -d '{
  "tenant": "hot-tenant",
  "target_shard": "shard-backup"
}'

# 或切到只读副本
curl -X POST http://vector-admin/routing -d '{"mode": "read-replica"}'
```

**优先级 4：回滚索引版本**

```bash
# 如果新索引发布后触发超时，切回上一版索引
curl -X POST http://vector-admin/index/rollback -d '{"index": "knowledge-base", "version": "v1.2.3"}'
```

##### 根因定位

```
向量检索超时
    |
    +-- query embedding 超时？
    |   |
    |   +-- embedding 模型负载高？-> 检查 embedding 服务状态
    |   +-- 网络延迟？-> 检查服务间网络
    |
    +-- 向量检索超时？
    |   |
    |   +-- CPU/内存瓶颈？-> 检查向量库资源使用
    |   +-- 分片热点？-> 检查分片负载分布
    |   +-- 索引参数问题？-> 检查 HNSW/IVF 参数
    |
    +-- reranker 超时？
    |   |
    |   +-- reranker 模型负载高？-> 检查 reranker 服务状态
    |   +-- top-k 过大？-> 减少需要 rerank 的文档数
    |
    +-- 元数据过滤超时？
        |
        +-- 过滤条件复杂？-> 优化过滤表达式
        +-- 索引缺失？-> 检查元数据字段索引
```

**常见根因**

1. 离线任务抢占资源：索引重建或批量导入与在线查询竞争资源
2. 分片热点：某个分片承载了过多的查询请求
3. 索引参数不当：HNSW 的 ef_search 或 IVF 的 nprobe 设置不合理
4. embedding 模型变更：新 embedding 模型的维度或性能发生变化
5. 元数据过滤效率低：缺少元数据字段索引导致全量扫描
6. 冷热数据混放：频繁访问的热数据和冷数据在同一分片上

##### 后续改进

**短期修复**
- 将离线构建与在线查询资源隔离，避免重建拖垮主链路
- 为 query embedding、检索、reranker 分别设超时和熔断
- 保留索引发布回滚开关和版本审计

**长期预防**
- 建立向量库的容量规划，根据数据量和 QPS 选择合适的分片策略
- 实现智能分片路由，根据查询特征动态选择最优分片
- 建立索引参数的自动调优机制，根据数据特征自动选择 HNSW/IVF 参数
- 为 RAG 链路建立端到端的 tracing，明确各阶段的耗时分布

##### 升级条件

- 超时影响核心问答路径超过一个观察窗口（5 分钟）
- 需要索引回滚、分片迁移或存储团队介入
- 影响多个租户或多个知识库

##### 恢复判定

- 检索超时率回落到基线（通常 < 0.1%）
- 端到端延迟恢复到目标区间
- 空召回率回落到正常水平
- 降级回答比例回到基线

##### 需保留证据

- 慢查询样本（包含查询语句和执行计划）
- 索引版本信息
- 分片水位和负载分布
- 离线任务执行记录
- 超时请求的 tracing 信息

##### 面试题关联

- Q: HNSW 和 IVF 索引的原理和适用场景分别是什么？
- Q: 如何设计一个高可用的向量检索系统？
- Q: RAG 链路中各个阶段的性能瓶颈分别是什么？

---

#### 场景 7：模型质量突然回退

##### 症状

- 指标层面：空响应率升高、截断率上升、工具调用失败率增加、人工差评比例上升
- 业务反馈：答案跑偏、引用缺失、工具误调用、风格异常、出现幻觉
- 可能伴随指标看似正常但用户体验急剧恶化（质量退化是主观的）

##### 前置检查

```bash
# 检查质量守护指标
# empty_response_rate, truncation_rate, tool_failure_rate, human_negative_rate

# 检查最近变更
# 模型版本、LoRA、Prompt 模板、索引版本、reranker、工具 schema

# 抽样检查受影响请求
curl http://log-api/samples -d '{
  "filter": {"quality_flag": "negative"},
  "limit": 20,
  "time_range": "1h"
}'

# 检查是否伴随性能退化
# ttft, error_rate, fallback_model_ratio
```

- 先确认影响范围：全量流量、灰度流量、特定租户还是特定任务链路
- 核对最近变更：基础模型、LoRA、Prompt 模板、索引版本、reranker、工具 schema
- 检查是否伴随 TTFT、错误率或回退模型比例变化

##### 止血动作

**优先级 1：停止灰度并回滚**

```bash
# 停止灰度发布
curl -X POST http://canary-api/stop -d '{"model": "llama-70b-v3"}'

# 切回上一版稳定模型
kubectl rollout undo deployment/llm-inference -n llm-inference

# 回滚 Prompt 模板
curl -X POST http://prompt-api/rollback -d '{"template": "rag-default", "version": "v1.2"}'

# 回滚索引版本
curl -X POST http://vector-admin/index/rollback -d '{"index": "knowledge-base", "version": "v1.2.3"}'
```

原因：质量回退通常由最近的变更引起，回滚是最直接的修复手段。

**优先级 2：关闭高风险功能**

```bash
# 关闭自动工具调用
curl -X POST http://inference-api/config -d '{"enable_tool_calling": false}'

# 切到人工兜底路径
curl -X POST http://gateway/routing -d '{"strategy": "human-fallback"}'
```

**优先级 3：为关键租户启用保守配置**

```bash
# 启用保守模板
curl -X POST http://prompt-api/config -d '{
  "tenant": "critical-tenant",
  "template": "conservative-v1"
}'

# 固定检索策略
curl -X POST http://rag-api/config -d '{
  "tenant": "critical-tenant",
  "retrieval_mode": "fixed",
  "top_k": 5
}'
```

##### 根因定位

```
模型质量回退
    |
    +-- 全量回退？
    |   |
    |   +-- 模型版本变更？-> 回滚模型
    |   +-- Prompt 模板变更？-> 回滚 Prompt
    |   +-- 工具 schema 变更？-> 回滚工具配置
    |
    +-- 灰度回退？
    |   |
    |   +-- 新模型质量不达标？-> 停止灰度
    |   +-- LoRA 绑定错误？-> 检查 LoRA 路由
    |
    +-- 局部回退？
        |
        +-- 特定任务链路？-> 检查链路配置
        +-- 特定租户？-> 检查租户级配置
        +-- 特定知识库？-> 检查索引版本
```

**常见根因**

1. 基础模型版本变更：新版本模型在特定任务上表现下降
2. Prompt 模板变更：模板修改导致模型行为变化
3. 索引版本不一致：embedding 模型与索引版本不匹配
4. LoRA 绑定错误：错误的 LoRA adapter 被绑定到特定租户
5. 工具 schema 变更：工具定义修改导致模型无法正确调用工具
6. Prompt 注入防护误伤：安全过滤规则过于严格，误伤正常请求

##### 后续改进

**短期修复**
- 将质量守护指标纳入灰度准入，不只看延迟和错误率
- 保留线上请求抽样、引用来源和工具摘要，方便快速回放
- 建立模型、Prompt、索引和工具配置的联动发布与回滚机制

**长期预防**
- 建立自动化质量评测流水线，每次发布前在标准评测集上验证
- 实现线上请求的自动质量打分，及时发现质量退化
- 为模型、Prompt、索引建立版本依赖图，确保联动一致性
- 建立 A/B 测试框架，新版本必须在真实流量上验证质量

##### 升级条件

- 影响高风险业务场景（如客服、金融问答）
- 影响关键租户
- 需要回退多个发布单元联合排查

##### 恢复判定

- 质量守护指标回到基线
- 人工抽样确认主要错误模式消失
- 灰度保持关闭或恢复稳定
- 业务方确认用户体验恢复正常

##### 需保留证据

- 受影响请求样本（包含完整的 request/response）
- 新旧版本输出对比
- 索引/Prompt/模型版本信息
- 工具调用摘要
- 人工反馈记录

##### 面试题关联

- Q: 如何建立模型质量的线上监控体系？
- Q: 灰度发布中如何平衡质量验证和发布速度？
- Q: 如何设计一个模型、Prompt、索引的联动发布机制？

---

#### 场景 8：API Gateway 限流异常

##### 症状

- 大量请求返回 429 Too Many Requests 或 503 Service Unavailable
- 用户反馈正常请求被拒绝，但后端服务负载并不高
- 限流计数器显示异常值（过高或过低）
- 部分租户被意外限流或限流策略未生效

##### 前置检查

```bash
# 检查 Gateway 状态
kubectl get pods -n gateway -l app=api-gateway

# 检查限流配置
curl http://gateway:8080/admin/ratelimit/config | jq .

# 检查限流计数器
curl http://gateway:8080/admin/ratelimit/counters | jq .

# 检查 429/503 错误率
# http_requests_total{status=~"429|503"}

# 检查后端服务负载
kubectl top pods -n llm-inference
```

- 确认是全局限流还是特定租户/接口被限流
- 检查限流配置是否被意外修改
- 确认后端服务是否真的过载

##### 止血动作

**优先级 1：临时放宽限流阈值**

```bash
# 临时放宽限流阈值
curl -X POST http://gateway:8080/admin/ratelimit/config -d '{
  "tenant": "all",
  "qps_limit": 1000,
  "burst": 200
}'

# 或临时关闭限流
curl -X POST http://gateway:8080/admin/ratelimit/disable -d '{"tenant": "affected-tenant"}'
```

原因：如果限流配置异常导致正常请求被误杀，临时放宽阈值可以立即恢复服务。

**优先级 2：回滚限流配置**

```bash
# 回滚到上一版限流配置
curl -X POST http://gateway:8080/admin/ratelimit/rollback -d '{"version": "v1.2"}'

# 或重新加载配置
curl -X POST http://gateway:8080/admin/ratelimit/reload
```

**优先级 3：增加后端容量**

```bash
# 如果后端确实过载，增加实例数
kubectl scale deployment/llm-inference -n llm-inference --replicas=20

# 或切到备用池
curl -X POST http://gateway/routing -d '{"target_pool": "backup-pool"}'
```

##### 根因定位

```
API Gateway 限流异常
    |
    +-- 正常请求被拒绝？
    |   |
    |   +-- 限流配置错误？-> 检查限流规则
    |   +-- 限流计数器异常？-> 检查 Redis/内存计数器
    |   +-- 时间窗口问题？-> 检查限流算法配置
    |
    +-- 限流未生效？
    |   |
    |   +-- 配置未同步？-> 检查配置分发机制
    |   +-- 限流规则匹配失败？-> 检查规则表达式
    |
    +-- 部分租户被限流？
        |
        +-- 租户配额耗尽？-> 检查租户级配额
        +-- 租户级配置错误？-> 检查租户限流规则
```

**常见根因**

1. 限流配置错误：阈值设置过低或规则匹配范围过大
2. 限流计数器异常：Redis 故障或内存计数器溢出
3. 配置分发延迟：新配置未及时同步到所有 Gateway 实例
4. 时间窗口问题：滑动窗口算法实现 bug 导致限流提前触发
5. 租户识别错误：IP 或 API Key 识别逻辑有误
6. 后端容量不足：后端服务确实过载，限流是预期行为

##### 后续改进

**短期修复**
- 建立限流配置的变更审计，所有变更必须经过审批
- 为限流计数器建立健康检查，异常时自动切换到备用计数器
- 建立限流配置的灰度发布机制，新配置先在小流量上验证

**长期预防**
- 实现自适应限流，根据后端负载动态调整限流阈值
- 建立限流的多级防护：租户级、接口级、全局级
- 为限流建立完善的监控和告警，及时发现异常
- 实现限流的优雅降级，被限流的请求返回有意义的错误信息

##### 升级条件

- 影响多个核心租户或核心接口
- 需要修改限流配置或代码
- 后端服务确实过载需要紧急扩容

##### 恢复判定

- 429/503 错误率回落到正常水平
- 限流计数器显示正确的数值
- 用户反馈不再有正常请求被拒绝的情况
- 后端服务负载在正常范围内

##### 需保留证据

- 限流配置变更记录
- 限流计数器快照
- 429/503 错误日志样本
- Gateway 访问日志
- 后端服务负载数据

##### 面试题关联

- Q: 常见的限流算法有哪些？各自适用场景是什么？
- Q: 如何设计一个多租户的限流系统？
- Q: 限流和熔断的区别是什么？

---

#### 场景 9：多租户资源争抢

##### 症状

- 某个租户的请求延迟突然升高，但其他租户正常
- 某个租户的 tokens/s 下降，但全局 tokens/s 正常
- 出现租户间的"噪声邻居"效应：大租户的流量高峰影响小租户
- GPU 利用率正常但特定租户的请求被排队

##### 前置检查

```bash
# 检查各租户的资源使用情况
curl http://inference-api/tenant/metrics | jq .

# 检查租户级的请求分布
# requests_per_tenant, tokens_per_tenant

# 检查租户级的延迟分布
# ttft_per_tenant, latency_per_tenant

# 检查是否有租户超过配额
curl http://gateway/tenant/quota | jq .
```

- 确认是哪个租户受到影响
- 检查该租户的流量是否突增
- 检查资源配额是否被超过
- 检查是否有租户在进行批量任务

##### 止血动作

**优先级 1：对问题租户限流**

```bash
# 对问题租户执行限流
curl -X POST http://gateway/ratelimit -d '{
  "tenant": "problem-tenant",
  "qps": 50
}'
```

原因：如果某个租户的流量突增导致资源争抢，限流可以立即释放资源给其他租户。

**优先级 2：为关键租户预留资源**

```bash
# 为关键租户预留资源
curl -X POST http://inference-api/tenant/reserve -d '{
  "tenant": "critical-tenant",
  "reserved_replicas": 5
}'
```

**优先级 3：将问题租户切到独立池**

```bash
# 将问题租户切到独立的模型池
curl -X POST http://gateway/routing -d '{
  "tenant": "problem-tenant",
  "target_pool": "isolated-pool"
}'
```

##### 根因定位

```
多租户资源争抢
    |
    +-- 单租户流量突增？
    |   |
    |   +-- 正常业务高峰？-> 弹性扩容 + 配额管理
    |   +-- 异常流量（爬虫/攻击）？-> 限流 + 封禁
    |
    +-- 占用资源过多？
    |   |
    |   +-- 长上下文请求？-> 单独分池
    |   +-- 批量任务？-> 调度到离线池
    |
    +-- 配额管理失效？
        |
        +-- 配额配置错误？-> 修正配额
        +-- 配额执行失败？-> 检查配额执行机制
```

**常见根因**

1. 某租户流量突增：业务高峰或异常流量导致资源争抢
2. 长上下文请求集中：某个租户的请求上下文长度远超其他租户
3. 批量任务影响在线请求：租户的批量任务占用大量 GPU 资源
4. 配额管理失效：配额限制未正确执行
5. 共享池资源不足：共享模型池的容量无法满足所有租户的需求
6. 调度策略不公平：调度器未考虑租户间的公平性

##### 后续改进

**短期修复**
- 建立租户级的资源配额管理，明确每个租户的 QPS、并发和 tokens/s 上限
- 为租户级指标建立独立监控面板
- 建立租户间的资源隔离机制

**长期预防**
- 实现基于优先级的调度，确保关键租户的请求优先处理
- 建立租户级别的弹性扩缩容，根据租户流量自动调整资源
- 将大租户和小租户分池部署，避免噪声邻居效应
- 实现租户级的成本核算，让租户了解自己的资源使用情况

##### 升级条件

- 影响多个关键租户
- 需要调整全局资源分配策略
- 需要将租户迁移到独立池

##### 恢复判定

- 受影响租户的延迟恢复正常
- 租户间的资源争抢不再发生
- 各租户的 QPS 和 tokens/s 在配额范围内

##### 需保留证据

- 租户级资源使用数据
- 流量分布变化
- 配额执行日志
- 调度决策日志

##### 面试题关联

- Q: 如何设计一个多租户的资源隔离方案？
- Q: 什么是噪声邻居效应？如何缓解？
- Q: 如何实现公平的 GPU 资源调度？

---

#### 场景 10：模型版本混乱

##### 症状

- 同一个请求在不同实例上返回不同结果
- 部分实例的性能指标与其他实例差异明显
- 用户反馈模型行为不一致（有时好有时差）
- 灰度比例与预期不符（灰度 10% 但看起来远超 10%）

##### 前置检查

```bash
# 检查各实例的模型版本
kubectl get pods -n llm-inference -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,STATUS:.status.phase

# 检查模型版本标签
kubectl get pods -n llm-inference -l app=llm-inference --show-labels

# 检查路由配置
curl http://gateway/routing/config | jq .

# 检查灰度流量分布
curl http://gateway/canary/distribution | jq .
```

- 确认哪些实例运行的是哪个版本
- 检查路由配置是否正确
- 检查灰度流量分配是否符合预期
- 检查是否有未完成的发布或回滚

##### 止血动作

**优先级 1：统一版本**

```bash
# 将所有实例统一到稳定版本
kubectl rollout undo deployment/llm-inference -n llm-inference

# 或强制重新部署
kubectl rollout restart deployment/llm-inference -n llm-inference
```

原因：版本混乱的根因是存在多个版本同时服务，统一版本可以立即消除不一致性。

**优先级 2：修正路由配置**

```bash
# 修正路由配置，确保流量按预期分配
curl -X POST http://gateway/routing/config -d '{
  "model": "llama-70b",
  "stable_weight": 100,
  "canary_weight": 0
}'
```

**优先级 3：停止灰度发布**

```bash
# 停止灰度发布
curl -X POST http://canary-api/stop -d '{"model": "llama-70b"}'
```

##### 根因定位

```
模型版本混乱
    |
    +-- 多版本并存？
    |   |
    |   +-- 发布未完成？-> 检查发布状态
    |   +-- 回滚未完成？-> 检查回滚状态
    |   +-- 扩容拉取了新版本？-> 检查镜像 tag
    |
    +-- 路由配置错误？
    |   |
    |   +-- 灰度比例错误？-> 检查灰度配置
    |   +-- 路由规则冲突？-> 检查路由规则
    |
    +-- 配置不一致？
        |
        +-- Prompt 版本不一致？-> 检查 Prompt 配置
        +-- 工具 schema 不一致？-> 检查工具配置
```

**常见根因**

1. 发布过程被中断：发布到一半时遇到问题，部分实例已更新部分未更新
2. 回滚不彻底：回滚操作未覆盖所有实例
3. 扩容拉取了错误版本：新扩容的实例拉取了新版本而非当前版本
4. 灰度配置错误：灰度比例设置错误导致流量分配异常
5. 镜像 tag 被覆盖：同一个 tag 被指向了不同的镜像 digest
6. 配置不一致：不同实例加载了不同版本的配置

##### 后续改进

**短期修复**
- 建立发布状态的实时监控，确保发布过程完整覆盖所有实例
- 为模型版本建立一致性检查，定期验证所有实例的版本是否一致
- 使用不可变的镜像 digest 而非 tag 进行部署

**长期预防**
- 实现 GitOps 的发布流程，所有变更通过 Git 控制
- 建立发布前的预检机制，验证镜像、配置、路由的一致性
- 实现自动化的版本一致性巡检，发现不一致时自动告警
- 为灰度发布建立完善的流量监控，确保灰度比例符合预期

##### 升级条件

- 影响多个租户或核心业务
- 需要紧急回滚或统一版本
- 怀疑镜像仓库或配置中心有问题

##### 恢复判定

- 所有实例运行相同版本
- 路由配置正确，流量分配符合预期
- 用户反馈模型行为一致性恢复正常
- 灰度比例与配置一致

##### 需保留证据

- 各实例的版本信息
- 路由配置快照
- 灰度流量分布数据
- 发布/回滚操作记录

##### 面试题关联

- Q: 如何设计一个可靠的模型发布流程？
- Q: 灰度发布的最佳实践是什么？
- Q: 如何保证大规模部署中的版本一致性？

---

## 💻 实战练习

### 练习 1：基础操作 -- 熟悉事故处置流程和工具

**目标**：掌握事故处置的基本工具和流程

**任务清单**：

1. **监控面板操作**
   - 打开 Grafana 面板，找到 LLM 推理服务的核心指标
   - 识别 TTFT、tokens/s、错误率、GPU 利用率四个核心指标
   - 学会设置告警阈值

2. **日志查询**
   - 使用 `kubectl logs` 查看推理服务日志
   - 学会使用日志系统（如 ELK/Loki）查询特定错误模式
   - 练习提取事故相关的日志片段

3. **止血工具操作**
   - 练习使用 `kubectl` 进行 Pod 管理（删除、重启、扩缩容）
   - 练习使用 API Gateway 的限流配置
   - 练习使用路由切换工具

4. **模拟演练**
   - 按照 GPU OOM 的处置流程，完成一次完整的模拟演练
   - 记录每一步的操作和耗时
   - 撰写一份简化的复盘报告

**预期输出**：
- 熟悉核心监控面板
- 能独立执行基本的止血操作
- 完成一份模拟事故的复盘报告

### 练习 2：进阶场景 -- 模拟复合事故（多个根因叠加）

**目标**：处理多个根因叠加的复杂事故

**场景描述**：

某天下午 3 点，监控告警触发：
- TTFT P95 从 500ms 上升到 5s
- tokens/s 从 30 下降到 15
- 部分实例出现 OOM 重启
- 向量检索超时率上升到 5%

经过初步排查发现：
1. 某个大租户在进行批量 RAG 查询，上下文长度是平时的 3 倍
2. 向量库正在进行索引重建，占用了大量 CPU 资源
3. 模型池刚刚完成一次灰度发布，新版本的显存占用增加了 10%
4. HPA 配置过于保守，未能及时扩容

**任务清单**：

1. 按照优先级对四个根因进行排序
2. 为每个根因制定止血动作
3. 制定根因定位的排查路径
4. 设计恢复方案（如何逐步恢复到正常状态）
5. 撰写复盘报告，提出长期改进项

**预期输出**：
- 完整的事故处置方案
- 排查路径图（ASCII 决策树）
- 复盘报告（包含时间线、根因分析、改进项）

### 练习 3：故障排查挑战 -- 限时完成一个完整事故处置

**目标**：在限定时间内完成从发现到恢复的完整处置

**规则**：
- 时间限制：30 分钟
- 从告警触发开始计时
- 必须完成：确认、定级、止血、排查、恢复五个步骤
- 最后 5 分钟用于撰写复盘摘要

**挑战场景**：

晚上 9 点，你收到告警：
- 模型推理服务错误率从 0.1% 上升到 15%
- 多个实例的 GPU 利用率降到 0%
- 日志中出现大量 `NCCL timeout` 错误
- 用户反馈"AI 不回答问题了"

你需要：
1. 在 5 分钟内完成确认和定级
2. 在 10 分钟内执行止血动作
3. 在 10 分钟内完成根因定位
4. 在 5 分钟内完成恢复和复盘摘要

**评分标准**：
- 是否在规定时间内完成
- 止血动作是否有效
- 根因定位是否准确
- 复盘报告是否完整

**预期输出**：
- 完整的处置记录（含时间线）
- 根因分析
- 复盘摘要

---

## 🎯 面试题精选

### 题目 1：事故处置的标准流程是什么？

**参考答案**：

标准的事故处置流程包含七个步骤：发现 -> 确认 -> 定级 -> 止血 -> 排查 -> 恢复 -> 复盘。

核心原则是**先恢复服务，再定位根因**。在止血阶段，oncall 工程师的目标是尽快恢复服务，而不是找出问题的根因。止血手段包括：隔离故障范围、降低压力、切换到备用方案、回滚最近变更。

在恢复阶段，需要逐步验证服务恢复正常，而不是一次性放开所有限制。最后的复盘环节非常重要，它将事故经验转化为组织知识，防止同类事故再次发生。

### 题目 2：如何判断事故等级？

**参考答案**：

事故等级通常根据两个维度判断：**影响范围**和**严重程度**。

- P0：核心服务完全不可用，影响全量用户。例如全局 GPU OOM、模型服务完全不可用。响应要求：5 分钟内响应，全员就位。
- P1：核心功能严重降级，影响大部分用户。例如 TTFT 飙升 10 倍、tokens/s 下降 50%。响应要求：10 分钟内响应，oncall + 二线。
- P2：非核心功能受影响，影响部分用户。例如向量检索超时、单租户资源争抢。响应要求：30 分钟内响应，oncall 处理。
- P3：局部异常，不影响用户。例如模型版本不一致但不影响服务。响应要求：2 小时内响应，按计划修复。

判断时需要同时考虑技术指标和业务影响，有时候技术指标看起来不严重但业务影响很大（如模型质量回退），需要灵活判断。

### 题目 3：止血 vs 根因修复，优先级如何判断？

**参考答案**：

**止血永远优先于根因修复**。原因如下：

1. **时间紧迫性**：事故每持续一分钟都在影响用户，止血可以快速恢复服务
2. **信息不对称**：在事故初期，我们通常不知道根因是什么，但可以采取通用的止血措施
3. **风险控制**：在排查根因的过程中，服务持续处于异常状态，可能引发连锁反应

典型的止血手段包括：
- 隔离故障范围（摘除异常实例）
- 降低压力（限流/缩短上下文）
- 切换到备用方案（备用模型池/备用地域）
- 回滚最近变更

根因修复应该在止血之后进行，通常在事故恢复后的复盘阶段完成。

### 题目 4：事后复盘的关键要素有哪些？

**参考答案**：

一份好的复盘报告应该包含以下要素：

1. **事故时间线**：精确记录事故发生、发现、响应、止血、恢复的每个时间点
2. **影响范围**：受影响的用户数、持续时间、业务损失
3. **根因分析**：使用 5 Whys 或鱼骨图分析根本原因
4. **止血措施**：记录执行了哪些止血动作，效果如何
5. **改进项**：
   - 短期修复：立即可以执行的修复措施
   - 长期预防：需要投入资源的系统性改进
6. **责任归属**：不是为了追责，而是明确改进项的负责人和截止时间
7. **经验教训**：这次事故教会了我们什么

复盘的核心原则是**对事不对人**，目标是改进系统而不是指责个人。

### 题目 5：如何建立事故响应文化？

**参考答案**：

建立良好的事故响应文化需要从以下几个方面入手：

1. **标准化流程**：建立标准化的事故处置流程和手册，让每个人都知道该怎么做
2. **定期演练**：定期进行故障注入演练（Chaos Engineering），让团队熟悉事故处置
3. **无责复盘**：建立无责复盘文化，鼓励分享错误和教训
4. **工具支持**：投资建设监控、告警、自动化止血工具，降低事故处置的门槛
5. **知识沉淀**：将每次事故的经验转化为手册、检查清单或自动化脚本
6. **oncall 机制**：建立合理的 oncall 轮值制度，确保 24/7 有专人负责
7. **升级文化**：鼓励在无法独立解决问题时及时升级，不要害怕"惊动领导"

### 题目 6：GPU OOM 和 CPU OOM 在处置策略上有什么本质区别？

**参考答案**：

GPU OOM 和 CPU OOM 的本质区别在于资源特性和恢复方式：

**资源特性**：
- CPU OOM：操作系统会触发 OOM Killer 终止占用内存最多的进程，其他进程不受影响
- GPU OOM：CUDA 运行时直接报错退出，整个进程崩溃，可能影响同一 GPU 上的其他进程

**恢复方式**：
- CPU OOM：重启进程即可恢复，内存会被操作系统回收
- GPU OOM：需要重新加载模型权重（数十 GB），预热 KV Cache，恢复时间更长

**处置策略**：
- CPU OOM：通常通过扩容或优化内存使用来解决
- GPU OOM：需要同时考虑显存预算管理（模型权重、KV Cache、激活值的分配）、请求准入控制（拒绝会触发 OOM 的请求）、以及快速恢复机制（预加载模型权重）

### 题目 7：如何设计一个显存预算管理系统？

**参考答案**：

显存预算管理系统应该包含以下组件：

1. **预算分配**：
   - 模型权重：固定的显存占用
   - KV Cache：根据并发请求数和上下文长度动态分配
   - 激活值：根据 batch size 和模型结构计算
   - 运行时开销：CUDA 运行时、NCCL 通信缓冲区等

2. **实时监控**：
   - 各组件的显存占用实时监控
   - 显存水位告警（80% 预警，90% 紧急）
   - 显存碎片化程度监控

3. **准入控制**：
   - 请求级别的显存预检：在接收请求前估算所需的显存量
   - 如果预估显存会超限，拒绝请求并返回有意义的错误信息
   - 支持动态调整准入阈值

4. **自动降级**：
   - 当显存水位过高时，自动下调 max_model_len
   - 当显存水位过高时，自动减少 max_num_seqs
   - 支持配置自动降级的触发条件和降级幅度

### 题目 8：NCCL hang 的排查思路是什么？

**参考答案**：

NCCL hang 的排查应该按照以下步骤进行：

1. **确认范围**：
   - 是单作业问题还是同节点池的普遍问题？
   - 是特定节点组合还是所有节点组合都有问题？

2. **检查硬件**：
   - GPU 状态：`nvidia-smi` 检查 ECC 错误、Xid 错误、温度
   - 网卡状态：`ibstat`（InfiniBand）或 `show_gids`（RoCE）检查网卡健康
   - 交换机状态：检查交换机丢包、缓冲区溢出

3. **检查软件**：
   - 驱动版本：CUDA、NCCL、OFED 版本是否兼容
   - 环境变量：NCCL_* 环境变量是否正确
   - 容器环境：是否缺少依赖库

4. **检查网络**：
   - PFC/ECN 计数器：是否有流控触发
   - 网络延迟：节点间的网络延迟是否正常
   - 带宽利用率：是否接近饱和

5. **检查作业配置**：
   - rank 映射：rank 到节点/GPU 的映射是否正确
   - 通信模式：AllReduce、AllGather、P2P 是否有特定问题
   - checkpoint：恢复 checkpoint 后 rank 状态是否一致

### 题目 9：如何设计一个高可用的向量检索系统？

**参考答案**：

高可用的向量检索系统应该从以下几个方面设计：

1. **分片策略**：
   - 按租户或数据集分片，避免单个分片过大
   - 支持动态分片，根据数据量自动调整分片数
   - 为热点分片建立只读副本

2. **索引策略**：
   - 选择合适的索引算法（HNSW 适合高召回场景，IVF 适合大规模数据）
   - 支持索引的增量更新，避免全量重建
   - 保留索引的多版本，支持快速回滚

3. **资源隔离**：
   - 离线构建与在线查询资源隔离
   - 不同租户的查询资源隔离
   - embedding 模型与向量检索资源隔离

4. **降级策略**：
   - 向量检索超时时降级到关键词检索
   - reranker 超时时跳过 rerank 直接返回
   - 支持返回缓存的检索结果

5. **监控告警**：
   - 检索延迟分位数监控
   - 空召回率监控
   - 分片负载均衡监控

### 题目 10：如何保证大规模部署中的版本一致性？

**参考答案**：

保证大规模部署中的版本一致性需要从以下几个方面入手：

1. **不可变部署**：
   - 使用镜像 digest 而非 tag 进行部署，避免 tag 被覆盖
   - 配置文件版本化，与镜像版本绑定
   - 使用 GitOps 管理所有部署配置

2. **发布流程**：
   - 实现原子化发布，要么全部更新要么全部不更新
   - 发布前预检：验证镜像、配置、路由的一致性
   - 发布后验证：检查所有实例的版本是否一致

3. **一致性巡检**：
   - 定期检查所有实例的版本信息
   - 发现不一致时自动告警
   - 支持自动修复不一致（重新部署）

4. **灰度管理**：
   - 灰度发布时严格控制流量分配
   - 监控灰度实例和稳定实例的行为差异
   - 灰度完成后统一版本再全量发布

---

## 📚 深入阅读

1. **Google SRE Book** - Chapter 14: Managing Incidents
   - Google 的事故管理最佳实践
   - 事故指挥系统（ICS）在 SRE 中的应用

2. **PagerDuty Incident Response Guide**
   - 完整的事故响应流程
   - 事故指挥官（IC）的角色和职责

3. **vLLM Documentation - Troubleshooting**
   - vLLM 推理引擎的故障排查指南
   - GPU OOM、KV Cache 等问题的处理

4. **NCCL Documentation - Debugging**
   - NCCL 通信问题的调试指南
   - 环境变量和日志分析

5. **Elasticsearch Guide - Performance Tuning**
   - 向量检索性能优化
   - HNSW/IVF 索引参数调优

6. **Chaos Engineering**
   - Netflix 的 Chaos Engineering 实践
   - 如何设计故障注入实验

---

## ✅ 自检清单

完成本手册学习后，请确认以下各项：

### 知识理解

- [ ] 理解 LLM 平台事故与传统服务事故的区别
- [ ] 掌握事故处置的七步标准流程
- [ ] 理解事故等级的判断标准
- [ ] 掌握升级条件和升级路径
- [ ] 理解证据保留的重要性

### 事故处置能力

- [ ] 能独立处置 GPU OOM 事故
- [ ] 能独立处置模型加载失败事故
- [ ] 能独立处置 TTFT 飙升事故
- [ ] 能独立处置 tokens/s 下降事故
- [ ] 能独立处置 NCCL hang 事故
- [ ] 能独立处置向量检索超时事故
- [ ] 能独立处置模型质量回退事故
- [ ] 能独立处置 API Gateway 限流异常事故
- [ ] 能独立处置多租户资源争抢事故
- [ ] 能独立处置模型版本混乱事故

### 工具使用

- [ ] 熟练使用 kubectl 进行 Pod 管理
- [ ] 熟练使用监控面板查看核心指标
- [ ] 熟练使用日志系统查询错误信息
- [ ] 熟练使用 API Gateway 的限流和路由配置

### 复盘能力

- [ ] 能撰写完整的复盘报告
- [ ] 能使用 5 Whys 或鱼骨图分析根因
- [ ] 能制定短期修复和长期预防的改进项
- [ ] 能进行无责复盘，聚焦系统改进

### 面试准备

- [ ] 能清晰描述事故处置的标准流程
- [ ] 能解释事故等级的判断标准
- [ ] 能说明止血 vs 根因修复的优先级
- [ ] 能列举复盘报告的关键要素
- [ ] 能描述如何建立事故响应文化
