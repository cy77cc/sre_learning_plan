# LLM SRE 10：生命周期总览

> 📅 日期：2026-05-03
> 📖 学习主题：LLM 全生命周期架构与 SRE 职责
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：基础 Linux、容器、Kubernetes 概念

## 🎯 学习目标

完成本篇学习后，你应该能够：

- 能画出 LLM 全生命周期架构图并解释每个阶段的核心职责
- 能识别生命周期中的关键风险点和 SRE 介入点
- 能设计生命周期各阶段的 SLI/SLO
- 能诊断跨阶段问题的根因（如推理质量问题追溯到数据或训练）

---

## 📖 核心知识点

### 1. 概念与原理

#### 1.1 什么是 LLM 生命周期

LLM 生命周期是指一个大语言模型从原始数据采集到最终用户请求被响应的完整工程链路。它不是一条简单的线性流水线，而是一个包含多个反馈回路的闭环系统。每一个阶段的输出都是下一阶段的输入，同时下游的观测结果会反向驱动上游的迭代决策。

与传统软件开发生命周期（SDLC）相比，LLM 生命周期有几个根本性差异：

**核心差异一：制品不可解释。** 传统软件的制品是源代码和二进制，行为可推导。LLM 的制品是数十亿参数的权重矩阵，行为只能通过评测和观测来描述，无法通过静态分析确定。

**核心差异二：质量是概率性的。** 传统软件的 bug 是确定性的——给定输入，输出要么对要么错。LLM 的"质量"是一个分布——同一输入在不同温度、不同采样下可能产生不同但都合理的输出。这意味着测试、发布和回滚策略都需要重新设计。

**核心差异三：资源需求极度不对称。** 训练阶段需要数千张 GPU 运行数天到数周，推理阶段需要持续的在线算力，两者共享底层集群但资源曲线完全不同。容量规划的复杂度远超传统服务。

**核心差异四：数据是第一公民。** 传统软件中数据是运行时状态；在 LLM 系统中，数据既是训练原料也是评测基准，数据质量直接决定模型能力上限。数据工程不是"ETL 处理"，而是核心竞争力。

#### 1.2 LLM 生命周期的 7 个阶段详解

LLM 生命周期可以划分为 7 个阶段。每个阶段都有明确的工程边界、输入输出、关键指标和 SRE 关注点。

**阶段 1：数据与样本工程**

数据是生命周期的起点，也是最容易被低估的系统性风险源。这里不仅包含原始语料、指令样本、偏好数据和评测集，还包含数据清洗、脱敏、去重、版本化、分层存储和访问控制。

工程上的关键点不是"有没有数据"，而是"数据是否可追溯、可复现、可治理"。样本格式变化、去重策略调整、标签口径漂移、训练集与评测集污染，都会在后续阶段放大。SRE 和平台团队要关注数据管道 SLA、元数据完整性、批处理延迟、数据湖权限边界，以及回填和重跑能力。

**阶段 2：训练与 GPU 集群**

训练阶段把数据问题转化为资源问题。GPU 节点、网络拓扑、存储带宽、调度队列和容器环境，都会直接影响吞吐、稳定性和训练成本。训练平台基础设施、集群底座和资源治理属于 [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md)；分布式运行时、并行策略与容错恢复机制属于 [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md)。

这里的 SRE 关注点通常包括：驱动和 CUDA/NCCL 版本矩阵是否稳定、拓扑感知调度是否准确、checkpoint 通道是否可靠、训练作业是否有明确的资源边界、集群是否能隔离噪声租户。

**阶段 3：评测与验收门禁**

训练完成并不等于可发布。评测与验收阶段负责回答：模型是否比上一版更好，是否只是"换了一组权衡"，以及是否引入了新的风险。这里通常会同时存在离线基准、任务集回放、人工抽检、红队测试和安全合规检查。

从平台角度看，评测阶段需要强版本绑定。评测结果必须关联到具体的数据版本、训练配置、模型制品、tokenizer 和推理参数，否则结论不可复用。SRE 还需要确保评测环境隔离、资源配额明确、结果可审计。

**阶段 4：模型制品与发布管理**

模型一旦进入制品阶段，就应该像镜像、二进制或 Helm Chart 一样被管理。权重文件、tokenizer、配置文件、推理模板、量化版本、LoRA 适配器和签名元数据都属于制品的一部分。

发布阶段的关键能力包括：制品仓库、不可变版本、灰度与回滚、兼容性校验、审批流和审计留痕。SRE 要推动"模型版本"和"服务版本"解耦，避免把应用发布和模型切换绑定成一次高风险事件。

**阶段 5：推理与服务化**

推理阶段是用户最直接感知的部分，但它只是生命周期中的一个服务出口。此时问题从"模型能不能训练好"转变成"请求能不能稳定、低延迟、低成本地被处理"。核心主题包括批处理、KV Cache、并发控制、流式输出、弹性伸缩、降级策略和多模型路由。

SRE 在这里要像管理任何关键在线服务一样管理模型服务：定义可用性和延迟目标，区分 TTFT、TPOT、TPS 等 LLM 特有指标，设计限流、熔断、排队和后备策略。

**阶段 6：观测、容量、成本与治理**

很多组织把观测和治理当成上线后的补丁，这会直接导致成本失控和事故不可解释。LLM 系统需要同时观测基础设施、模型行为、应用效果和业务成本。

容量规划应覆盖训练和推理两种完全不同的资源曲线。成本治理则要下沉到 token、实验、租户、项目和团队维度。治理还包含权限、审计、数据合规、内容安全、第三方模型依赖管理和供应链可信度。

**阶段 7：RAG / Agent / 应用平台**

当模型进入 RAG、Agent 和应用平台阶段，系统边界再次扩大。问题不再只是模型本身，而是检索链路、工具调用、会话状态、外部 API、工作流编排和多阶段超时控制。很多线上故障最终表现为"模型答得不好"，但根因其实在索引过期、工具失败、上下文拼装错误或策略引擎失效。

#### 1.3 阶段间的依赖关系和反馈回路

LLM 生命周期不是单向流水线，而是一个多层反馈环路。理解这些回路是 SRE 进行故障归因和容量规划的前提。

**正向流（主链路）：** 数据 -> 训练 -> 评测 -> 制品 -> 推理 -> 应用。这是模型从原料到用户请求的主路径。

**反馈回路 1：线上观测 -> 数据回流。** 推理阶段收集的用户反馈、badcase、满意度评分等数据，会回流到数据工程阶段，成为下一轮训练的信号。这条回路的质量决定了模型能否持续改进。

**反馈回路 2：评测结果 -> 训练调优。** 评测阶段发现的能力短板会反馈给训练阶段，驱动超参调整、数据配比优化或训练策略变更。

**反馈回路 3：成本观测 -> 容量规划。** 推理阶段的成本和利用率数据会反馈到容量规划，影响训练集群和推理集群的资源分配比例。

**反馈回路 4：安全事件 -> 治理策略。** 线上发现的内容安全问题会反馈到评测门禁和治理规则，更新红队测试用例和过滤策略。

#### 1.4 ASCII 架构图

**图 1：LLM 全生命周期总览**

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM 全生命周期架构                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │  1.数据工程   │───>│  2.训练集群   │───>│  3.评测门禁   │         │
│   │              │    │              │    │              │         │
│   │ · 语料采集    │    │ · 分布式训练   │    │ · 离线基准    │         │
│   │ · 清洗脱敏    │    │ · checkpoint  │    │ · 红队测试    │         │
│   │ · 版本管理    │    │ · 容错恢复    │    │ · 安全合规    │         │
│   │ · 数据血缘    │    │ · 资源调度    │    │ · 质量门禁    │         │
│   └──────┬───────┘    └──────────────┘    └──────┬───────┘         │
│          │                                        │                 │
│          │         ┌──────────────────┐           │                 │
│          │         │  观测 / 成本 / 治理│           │                 │
│          │         │  (贯穿所有阶段)    │           │                 │
│          │         └──────────────────┘           │                 │
│          │                                        │                 │
│          v                                        v                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │ 7.应用平台   │<───│  5.推理服务   │<───│  4.制品发布   │         │
│   │              │    │              │    │              │         │
│   │ · RAG        │    │ · 批处理      │    │ · 模型仓库    │         │
│   │ · Agent      │    │ · 流式输出    │    │ · 灰度发布    │         │
│   │ · 工作流编排  │    │ · 弹性伸缩    │    │ · 回滚策略    │         │
│   │ · 工具调用    │    │ · 降级策略    │    │ · 版本管理    │         │
│   └──────────────┘    └──────────────┘    └──────────────┘         │
│                                                                     │
│   <────────────────── 反馈回路 ──────────────────>                  │
│   线上观测 ──> 数据回流 ──> 训练调优 ──> 重新评测                    │
└─────────────────────────────────────────────────────────────────────┘
```

**图 2：数据流与制品流**

```text
┌─────────────────────────────────────────────────────────────────┐
│                      数据流与制品流                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  原始语料 ──> 清洗管道 ──> 版本化数据集 ──> 训练数据加载器       │
│      │            │              │               │              │
│      │            │              │               v              │
│      │            │              │         ┌──────────┐         │
│      │            │              │         │ 训练作业  │         │
│      │            │              │         └────┬─────┘         │
│      │            │              │              │               │
│      │            │              │              v               │
│      │            │              │         checkpoint           │
│      │            │              │              │               │
│      │            │              │              v               │
│      │            │              │         ┌──────────┐         │
│      │            │              │         │ 评测管道  │         │
│      │            │              │         └────┬─────┘         │
│      │            │              │              │               │
│      │            │              │              v               │
│      │            │              │         模型制品              │
│      │            │              │         (权重+配置)           │
│      │            │              │              │               │
│      │            │              │              v               │
│      │            │              │         ┌──────────┐         │
│      │            │              │         │ 制品仓库  │         │
│      │            │              │         └────┬─────┘         │
│      │            │              │              │               │
│      │            │              │              v               │
│      │            │              │         ┌──────────┐         │
│      │            │              │         │ 灰度发布  │         │
│      │            │              │         └────┬─────┘         │
│      │            │              │              │               │
│      v            v              v              v               │
│  ┌──────────────────────────────────────────────────┐           │
│  │              元数据注册中心 (Registry)              │           │
│  │  数据版本 / 训练配置 / 模型签名 / 发布记录          │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  关键原则：每个制品都必须能追溯到产生它的数据和配置                │
└─────────────────────────────────────────────────────────────────┘
```

**图 3：故障传播路径**

```text
┌─────────────────────────────────────────────────────────────────┐
│                      故障传播路径                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  数据层故障                                                     │
│  ┌─────────────────┐                                           │
│  │ · 评测集污染     │──────┐                                    │
│  │ · 标签口径漂移   │      │                                    │
│  │ · 去重策略变更   │      │                                    │
│  │ · 数据管道延迟   │      │                                    │
│  └─────────────────┘      │                                    │
│                           v                                    │
│  训练层故障              ┌─────────────────┐                    │
│  ┌─────────────────┐    │                 │                    │
│  │ · GPU 故障       │───>│  评测结果失真   │                    │
│  │ · checkpoint 损坏│    │  (误判模型质量)  │                    │
│  │ · 资源竞争       │    │                 │                    │
│  │ · 驱动版本不兼容  │    └────────┬────────┘                    │
│  └─────────────────┘             │                             │
│                                  v                             │
│  发布层故障              ┌─────────────────┐                    │
│  ┌─────────────────┐    │                 │                    │
│  │ · 制品版本混淆   │───>│  低质量模型上线  │                    │
│  │ · 灰度策略失效   │    │                 │                    │
│  │ · 回滚链路断裂   │    └────────┬────────┘                    │
│  └─────────────────┘             │                             │
│                                  v                             │
│  推理层故障              ┌─────────────────┐                    │
│  ┌─────────────────┐    │                 │                    │
│  │ · 显存溢出       │───>│  用户体验退化   │───> 业务损失        │
│  │ · 批处理超时     │    │  · 延迟飙升     │                    │
│  │ · KV Cache 污染  │    │  · 质量下降     │                    │
│  │ · 量化精度损失   │    │  · 服务不可用   │                    │
│  └─────────────────┘    │                 │                    │
│                         └─────────────────┘                    │
│                                                                 │
│  SRE 核心职责：在每一层建立检测点，缩短故障传播链                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.5 对比表格：传统软件生命周期 vs LLM 生命周期

| 维度 | 传统软件 SDLC | LLM 生命周期 |
|------|-------------|-------------|
| **制品形态** | 源代码 + 二进制 | 权重文件 + tokenizer + 配置 |
| **行为可预测性** | 确定性（给定输入，输出固定） | 概率性（温度、采样影响输出） |
| **测试方法** | 单元测试、集成测试、E2E | 基准评测、红队测试、人工抽检 |
| **质量度量** | 覆盖率、通过率、bug 数 | 准确率、BLEU/ROUGE、人类偏好评分 |
| **发布策略** | 蓝绿部署、金丝雀发布 | 灰度发布 + A/B 测试 + 模型版本切换 |
| **回滚粒度** | 代码版本回滚 | 模型权重版本 + 推理配置回滚 |
| **资源需求** | CPU 密集型，弹性伸缩成熟 | GPU 密集型，弹性伸缩复杂且昂贵 |
| **数据依赖** | 数据是运行时状态 | 数据是核心竞争力和训练原料 |
| **故障模式** | 确定性 bug | 质量退化、分布漂移、幻觉 |
| **观测重点** | 延迟、错误率、吞吐 | 延迟、质量分数、token 成本、幻觉率 |
| **迭代周期** | 天到周 | 周到月（取决于训练成本） |
| **团队协作** | 前后端、DevOps | 算法、平台、数据、SRE、应用 |
| **版本管理** | Git + 语义化版本 | Git + 数据版本 + 模型注册表 + 配置版本 |
| **安全边界** | 代码安全、依赖扫描 | 内容安全、对抗攻击、数据泄露、供应链 |

#### 1.6 每个阶段的核心工程问题

| 阶段 | 核心工程问题 | SRE 介入点 |
|------|------------|-----------|
| 数据工程 | 数据是否可追溯、可复现、可治理？ | 管道 SLA、元数据完整性、数据血缘 |
| 训练集群 | 训练作业是否能稳定完成？ | 资源调度、checkpoint 可靠性、故障恢复 |
| 评测门禁 | 评测结果是否可信、可复现？ | 环境隔离、版本绑定、结果审计 |
| 制品发布 | 制品是否不可变、可回滚？ | 制品仓库、版本管理、灰度策略 |
| 推理服务 | 请求是否稳定、低延迟、低成本？ | 可用性目标、限流熔断、容量弹性 |
| 观测治理 | 系统是否可观测、成本是否可控？ | 统一日志指标追踪、成本分摊 |
| 应用平台 | 复合工作流是否端到端可靠？ | 链路追踪、超时控制、降级策略 |

---

### 2. 命令/工具详解

#### 2.1 生命周期管理核心工具链

LLM 生命周期管理依赖一套工具链来实现自动化和可观测性。以下是各阶段的关键工具。

**数据版本管理**

```bash
# DVC (Data Version Control) - 数据版本管理
# 初始化 DVC 仓库
dvc init

# 追踪数据集版本
dvc add data/training_dataset/
git add data/training_dataset.dvc .gitignore
git commit -m "feat: add training dataset v2.1"

# 数据版本回滚
dvc checkout data/training_dataset/ --rev v2.0

# 查看数据变更历史
dvc diff --rev HEAD~3

# 数据管道运行
dvc repro  # 根据 dvc.yaml 重跑数据管道
```

**实验追踪与模型注册**

```bash
# MLflow - 实验追踪和模型注册
# 启动 MLflow 服务端
mlflow server \
  --backend-store-uri postgresql://user:pass@db:5432/mlflow \
  --default-artifact-root s3://mlflow-artifacts/ \
  --host 0.0.0.0 \
  --port 5000

# 在训练脚本中记录实验
python train.py \
  --mlflow-tracking-uri http://mlflow:5000 \
  --experiment-name "llama-7b-sft-v3" \
  --run-name "lr-2e-5-epochs-3"

# 注册模型到模型仓库
mlflow models register-model \
  --model-uri "runs:/<run_id>/model" \
  --name "llama-7b-sft" \
  --description "Llama 7B SFT model trained on v2.1 dataset"

# 查看模型版本历史
mlflow models list-versions --name "llama-7b-sft"

# 设置模型阶段（Staging/Production/Archived）
mlflow models transition-model-version-stage \
  --name "llama-7b-sft" \
  --version 3 \
  --stage Production

# 回滚模型到上一个版本
mlflow models transition-model-version-stage \
  --name "llama-7b-sft" \
  --version 2 \
  --stage Production
```

**Weights & Biases 实验追踪**

```bash
# W&B 初始化
pip install wandb
wandb login

# 在训练脚本中使用
python train.py \
  --wandb-project "llm-sre-training" \
  --wandb-entity "my-org" \
  --wandb-run-name "sft-run-20260503"

# 查看实验对比
wandb online  # 实时同步
wandb offline  # 离线模式，稍后同步
```

**评测工具链**

```bash
# lm-evaluation-harness - 标准化评测
# 运行基准评测
lm_eval --model hf \
  --model_args pretrained=./models/llama-7b-sft-v3,dtype=float16 \
  --tasks mmlu,hellaswag,arc_challenge \
  --device cuda:0 \
  --batch_size 16 \
  --output_path ./eval_results/v3/

# 对比两个模型版本
lm_eval --model hf \
  --model_args pretrained=./models/llama-7b-sft-v2,dtype=float16 \
  --tasks mmlu,hellaswag,arc_challenge \
  --device cuda:0 \
  --batch_size 16 \
  --output_path ./eval_results/v2/

# 评测结果对比脚本
python compare_evals.py \
  --baseline ./eval_results/v2/ \
  --candidate ./eval_results/v3/ \
  --threshold 0.02  # 退化超过 2% 则告警
```

**模型制品管理**

```bash
# Hugging Face Hub - 模型仓库
# 推送模型到 Hub
huggingface-cli upload \
  my-org/llama-7b-sft-v3 \
  ./models/llama-7b-sft-v3/ \
  --commit-message "Release v3: improved reasoning"

# 下载指定版本
huggingface-cli download \
  my-org/llama-7b-sft-v3 \
  --revision v3.0 \
  --local-dir ./models/llama-7b-sft-v3/

# 模型签名验证
python -c "
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    'my-org/llama-7b-sft-v3',
    revision='v3.0'
)
print(f'Config: {model.config}')
print(f'Parameters: {model.num_parameters()}')
"
```

**发布与灰度工具**

```bash
# 使用 Kubernetes 进行灰度发布
# 金丝雀部署配置
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-serving-canary
  namespace: inference
spec:
  replicas: 2  # 少量副本作为金丝雀
  selector:
    matchLabels:
      app: llm-serving
      version: v3
  template:
    metadata:
      labels:
        app: llm-serving
        version: v3
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:v0.4.0
        args:
        - "--model"
        - "my-org/llama-7b-sft-v3"
        - "--tensor-parallel-size"
        - "2"
        - "--max-model-len"
        - "4096"
        resources:
          limits:
            nvidia.com/gpu: 2
---
# 流量分配：90% 旧版本，10% 新版本
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: llm-serving-routing
  namespace: inference
spec:
  hosts:
  - llm-serving
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: llm-serving
        subset: v3
  - route:
    - destination:
        host: llm-serving
        subset: v2
      weight: 90
    - destination:
        host: llm-serving
        subset: v3
      weight: 10
EOF

# Prometheus 查询金丝雀指标对比
# 延迟对比
promql 'histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{
    app="llm-serving",
    version=~"v2|v3"
  }[5m])
) by (version)'

# 错误率对比
promql 'rate(http_requests_total{
  app="llm-serving",
  status=~"5..",
  version=~"v2|v3"
}[5m]) / rate(http_requests_total{
  app="llm-serving",
  version=~"v2|v3"
}[5m]) by (version)'
```

#### 2.2 工具选型对比

| 工具 | 主要用途 | 优势 | 劣势 | 适用场景 |
|------|---------|------|------|---------|
| **MLflow** | 实验追踪、模型注册 | 开源、生态成熟、自托管 | UI 较朴素、大规模性能一般 | 中小团队、自建平台 |
| **Weights & Biases** | 实验追踪、可视化 | 可视化优秀、协作便捷 | SaaS 为主、数据出境风险 | 算法团队日常实验 |
| **DVC** | 数据版本管理 | 轻量、Git 集成好 | 大规模数据性能一般 | 数据版本化、管道编排 |
| **Hugging Face Hub** | 模型仓库、社区协作 | 生态丰富、模型发现便捷 | 依赖外部服务 | 开源模型管理 |
| **MLflow Models** | 模型部署、服务化 | 标准化接口、多框架支持 | 生产级功能有限 | 模型服务化 |
| **Prometheus + Grafana** | 指标监控 | 成熟、可扩展 | 需要自建告警规则 | 推理服务监控 |
| **OpenTelemetry** | 分布式追踪 | 标准化、多语言支持 | 配置复杂 | 端到端链路追踪 |
| **Argo Rollouts** | 渐进式发布 | K8s 原生、策略丰富 | 学习曲线陡 | 生产级灰度发布 |

#### 2.3 工具链集成架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 工具链集成架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  数据层                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │   DVC    │  │   Delta  │  │  Feast   │                      │
│  │ 数据版本  │  │  Lake    │  │ 特征存储  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │                             │
│       v             v             v                             │
│  ┌──────────────────────────────────────┐                       │
│  │         元数据注册中心 (Registry)      │                       │
│  └──────────────────────────────────────┘                       │
│       │             │             │                             │
│       v             v             v                             │
│  训练层                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ MLflow   │  │   W&B    │  │ Ray      │                      │
│  │ 实验追踪  │  │ 可视化   │  │ 训练编排  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │                             │
│       v             v             v                             │
│  发布层                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ HF Hub  │  │  Argo    │  │ Istio    │                      │
│  │ 模型仓库  │  │ Rollouts │  │ 流量管理  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │                             │
│       v             v             v                             │
│  观测层                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │Prometheus│  │  Grafana │  │  OTel    │                      │
│  │  指标    │  │  可视化   │  │  追踪    │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. SRE 实战案例

#### 案例 1：推理质量回退追溯到训练数据问题

**背景：** 某 LLM 平台在例行模型更新后，线上收到用户反馈"模型回答质量明显下降"，表现为特定领域（医疗问答）的准确率从 85% 骤降至 62%。SRE 需要快速定位根因并恢复服务。

**阶段一：症状识别**

```bash
# 1. 查看线上质量指标告警
# Prometheus 查询：按领域分类的回答质量分数
promql 'avg by (domain) (
  llm_response_quality_score{
    model_version="v3.2",
    env="production"
  }
)'

# 输出：
# {domain="medical"} 0.62  (vs 正常值 0.85)
# {domain="legal"} 0.78   (正常)
# {domain="tech"} 0.81    (正常)

# 2. 查看 badcase 样本
kubectl logs -l app=llm-serving,version=v3.2 \
  --since=1h | jq 'select(.quality_score < 0.5)' | head -20

# 3. 对比旧版本相同输入的输出
curl -X POST http://llm-serving-v3-1/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "阿司匹林的作用机制是什么？"}]}'

curl -X POST http://llm-serving-v3-2/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "阿司匹林的作用机制是什么？"}]}'

# v3.1 输出正确答案
# v3.2 输出明显偏离医学常识的回答
```

**阶段二：分层诊断**

```bash
# 第 1 层：确认推理层是否正常
# 检查推理引擎配置
kubectl get pod llm-serving-v3-2-xxx -o yaml | grep -A 20 "args:"
# 确认：量化配置、采样参数、tokenizer 版本均与 v3.1 一致

# 检查 GPU 显存和利用率
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total \
  --format=csv -l 5
# 确认：GPU 状态正常，无显存溢出

# 结论：推理层排除

# 第 2 层：确认评测门禁是否漏放
# 查看 v3.2 的评测报告
mlflow experiments list | grep "v3.2"
mlflow runs list --experiment-id <exp_id> --order-by "metrics.medical_acc DESC"

# 查看医疗领域评测分数
python -c "
import mlflow
run = mlflow.get_run('<run_id>')
print('medical_acc:', run.data.metrics.get('medical_acc'))
print('medical_f1:', run.data.metrics.get('medical_f1'))
"

# 发现：评测报告显示 medical_acc=0.83，但线上只有 0.62
# 评测结果与线上表现不一致，怀疑评测集有问题

# 第 3 层：确认评测集是否被污染
# 检查评测集版本
dvc diff --rev HEAD~5 -- data/eval/medical/
# 发现：5 个 commit 前，评测集被替换为新版本

git log --oneline -- data/eval/medical/
# 输出：
# a1b2c3d refactor: update medical eval set with new data
# e4f5g6h fix: remove duplicate questions from medical eval

# 检查新评测集的统计特征
python -c "
import json
with open('data/eval/medical/eval_v2.json') as f:
    new_data = json.load(f)
with open('data/eval/medical/eval_v1.json') as f:
    old_data = json.load(f)

print(f'旧评测集: {len(old_data)} 条')
print(f'新评测集: {len(new_data)} 条')

# 检查难度分布
old_difficulties = [d['difficulty'] for d in old_data]
new_difficulties = [d['difficulty'] for d in new_data]
print(f'旧评测集难度分布: easy={old_difficulties.count(\"easy\")}, medium={old_difficulties.count(\"medium\")}, hard={old_difficulties.count(\"hard\")}')
print(f'新评测集难度分布: easy={new_difficulties.count(\"easy\")}, medium={new_difficulties.count(\"medium\")}, hard={new_difficulties.count(\"hard\")}')
"

# 输出：
# 旧评测集: 500 条，难度分布: easy=150, medium=200, hard=150
# 新评测集: 300 条，难度分布: easy=200, medium=80, hard=20

# 发现：新评测集大幅缩减，且简单题占比从 30% 升至 67%
# 评测集质量下降，导致评测结果虚高

# 第 4 层：确认训练数据是否有变化
dvc diff -- data/training/medical/
# 发现：训练数据也有变更

git log --oneline -- data/training/medical/
# 输出：
# b2c3d4e feat: add new medical QA pairs from web crawl
# c3d4e5f fix: remove low quality samples

# 检查新增训练数据质量
python -c "
import json
with open('data/training/medical/new_data.json') as f:
    new_samples = json.load(f)

# 抽样检查质量
import random
samples = random.sample(new_samples, 10)
for i, s in enumerate(samples):
    print(f'样本 {i+1}:')
    print(f'  问题: {s[\"question\"][:80]}...')
    print(f'  答案: {s[\"answer\"][:80]}...')
    print(f'  来源: {s[\"source\"]}')
    print()
"
# 发现：新增数据来自低质量网页爬取，包含大量错误医学信息
```

**阶段三：根因确认**

```bash
# 完整根因链
# 1. 数据工程师更新了医疗训练数据，从网页爬取新增了 5000 条样本
# 2. 其中约 30% 包含错误或过时的医学信息
# 3. 评测集也被同步更新，但新评测集质量更差（题目更简单、覆盖更窄）
# 4. 评测结果显示质量提升（0.83），实际是因为评测集变简单了
# 5. 模型被发布到线上，真实用户的问题比评测集复杂得多
# 6. 线上质量暴露了训练数据的问题

# 根因：训练数据质量把关缺失 + 评测集质量退化 = 虚假的质量提升
```

**阶段四：修复**

```bash
# 紧急修复：回滚到 v3.1
kubectl set image deployment/llm-serving \
  vllm=myregistry/llm-serving:v3.1 -n inference

# 确认回滚成功
kubectl rollout status deployment/llm-serving -n inference

# 验证线上质量恢复
promql 'avg by (domain) (
  llm_response_quality_score{
    model_version="v3.1",
    env="production"
  }
)'
# {domain="medical"} 0.85 (恢复)

# 永久修复：
# 1. 回滚训练数据到干净版本
dvc checkout data/training/medical/ --rev clean-v2.0

# 2. 回滚评测集到 v1 版本
dvc checkout data/eval/medical/ --rev v1.0

# 3. 建立数据质量门禁
# 在 CI 中添加数据质量检查
cat <<'EOF' >> .github/workflows/data-quality.yml
- name: Check data quality
  run: |
    python scripts/check_data_quality.py \
      --data-path data/training/medical/ \
      --min-quality-score 0.7 \
      --max-error-rate 0.05 \
      --check-medical-facts true
EOF

# 4. 建立评测集质量基线
cat <<'EOF' >> .github/workflows/eval-quality.yml
- name: Validate eval set
  run: |
    python scripts/validate_eval_set.py \
      --eval-path data/eval/medical/ \
      --min-difficulty-distribution '{"easy": 0.2, "medium": 0.4, "hard": 0.4}' \
      --min-coverage 0.8
EOF
```

**阶段五：预防措施**

```bash
# 1. 建立数据变更审批流程
# 所有数据变更必须经过 PR review，至少需要 2 人审批
# CODEOWNERS 文件中添加数据目录的 owner
echo "data/training/ @data-team @sre-team" >> .github/CODEOWNERS
echo "data/eval/ @data-team @sre-team @ml-team" >> .github/CODEOWNERS

# 2. 建立数据版本基线机制
# 每次数据变更必须标注影响范围
cat <<'EOF' >> .github/pull_request_template.md
## 数据变更说明
- [ ] 变更类型：新增 / 修改 / 删除
- [ ] 影响领域：[填写]
- [ ] 质量检查：通过 / 待验证
- [ ] 评测集是否同步更新：是 / 否
- [ ] 回滚方案：[填写]
EOF

# 3. 建立评测-线上一致性监控
# 定期对比评测分数和线上质量分数
promql 'abs(
  avg_over_time(eval_medical_acc[1h])
  -
  avg_over_time(online_medical_quality[1h])
) > 0.1'
# 差异超过 10% 则告警

# 4. 建立数据质量仪表板
# Grafana 面板包含：
# - 训练数据统计量趋势
# - 评测集覆盖率变化
# - 评测 vs 线上一致性
# - 数据变更历史
```

---

#### 案例 2：模型发布后线上延迟飙升

**背景：** 某 LLM 平台发布新模型后，P99 延迟从 2s 飙升到 15s，用户大量投诉。SRE 需要在不回滚的情况下快速定位并解决问题。

**阶段一：症状识别**

```bash
# 1. 查看延迟告警
promql 'histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{
    app="llm-serving",
    env="production"
  }[5m])
) by (model_version)'
# 输出：
# {model_version="v2.1"} 2.1s  (正常)
# {model_version="v3.0"} 15.3s (异常)

# 2. 查看延迟分布
promql 'histogram_quantile(0.50,
  rate(http_request_duration_seconds_bucket{
    model_version="v3.0",
    env="production"
  }[5m])
)'
# P50 = 1.8s (正常)
# 说明长尾请求导致 P99 飙升

# 3. 查看请求分布
promql 'sum by (input_tokens_bucket) (
  rate(http_requests_total{
    model_version="v3.0",
    env="production"
  }[5m])
)'
# 发现：长输入请求（>2048 tokens）延迟特别高
```

**阶段二：分层诊断**

```bash
# 第 1 层：检查推理引擎配置差异
# 对比 v2.1 和 v3.0 的推理配置
kubectl get deployment llm-serving-v2-1 -o yaml | grep -A 30 "args:" > /tmp/v2.1-config.yaml
kubectl get deployment llm-serving-v3-0 -o yaml | grep -A 30 "args:" > /tmp/v3.0-config.yaml
diff /tmp/v2.1-config.yaml /tmp/v3.0-config.yaml

# 发现差异：
# v3.0 新增了 --enable-prefix-caching=false
# v3.0 修改了 --max-num-batched-tokens=8192 (v2.1 是 16384)
# v3.0 修改了 --gpu-memory-utilization=0.85 (v2.1 是 0.90)

# 第 2 层：检查模型本身的变化
# 对比模型配置
python -c "
from transformers import AutoConfig
config_v2 = AutoConfig.from_pretrained('my-org/llama-7b-v2.1')
config_v3 = AutoConfig.from_pretrained('my-org/llama-7b-v3.0')
print('v2.1 num_layers:', config_v2.num_layers)
print('v3.0 num_layers:', config_v3.num_layers)
print('v2.1 num_heads:', config_v2.num_attention_heads)
print('v3.0 num_heads:', config_v3.num_attention_heads)
print('v2.1 hidden_size:', config_v2.hidden_size)
print('v3.0 hidden_size:', config_v3.hidden_size)
"

# 发现：v3.0 模型结构未变，但使用了更大的 context window (8192 -> 32768)

# 第 3 层：检查 KV Cache 使用情况
# 查看 v3.0 的 KV Cache 占用
kubectl exec -it llm-serving-v3-0-xxx -- \
  python -c "
import torch
# 查看 GPU 显存分配
print('GPU Memory Summary:')
print(torch.cuda.memory_summary())
"

# 发现：KV Cache 占用了大量显存，导致批处理能力下降

# 第 4 层：检查批处理效率
# 查看批处理统计
curl http://llm-serving-v3-0:8080/metrics | grep "vllm:num_requests_running"
# 发现：并发请求数只有 2-3 个（正常应该是 8-16 个）

curl http://llm-serving-v3-0:8080/metrics | grep "vllm:gpu_cache_usage"
# 发现：GPU Cache 使用率高达 95%，几乎没有空间容纳新请求
```

**阶段三：根因确认**

```bash
# 完整根因链
# 1. v3.0 模型支持 32K context window（v2.1 是 8K）
# 2. 推理配置中的 max-num-batched-tokens 被误设为 8192
#    （本意是限制单批次 token 数，但实际限制了并行度）
# 3. 同时 gpu-memory-utilization 从 0.90 降到 0.85
# 4. prefix-caching 被禁用，导致长输入的 KV Cache 无法复用
# 5. 结果：长输入请求独占 GPU，其他请求排队等待
# 6. P50 正常是因为短请求不受影响，P99 飙升是因为长请求延迟极高

# 根因：推理配置不匹配模型特性 + 资源分配不合理
```

**阶段四：修复**

```bash
# 方案 A：调整推理配置（推荐，无需回滚模型）
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-serving-v3-0
  namespace: inference
spec:
  template:
    spec:
      containers:
      - name: vllm
        args:
        - "--model"
        - "my-org/llama-7b-v3.0"
        - "--tensor-parallel-size"
        - "2"
        - "--max-model-len"
        - "32768"
        - "--max-num-batched-tokens"
        - "32768"        # 恢复到合理值
        - "--gpu-memory-utilization"
        - "0.92"         # 提高显存利用率
        - "--enable-prefix-caching"  # 启用 prefix caching
        - "--max-num-seqs"
        - "16"           # 最大并发序列数
        - "--chunked-prefill-size"
        - "2048"         # 分块预填充，减少长请求对其他请求的影响
EOF

# 方案 B：如果方案 A 不生效，灰度回滚到 v2.1
# 逐步将流量从 v3.0 切回 v2.1
kubectl scale deployment llm-serving-v3-0 --replicas=1 -n inference
kubectl scale deployment llm-serving-v2-1 --replicas=5 -n inference

# 验证修复效果
promql 'histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{
    model_version="v3.0",
    env="production"
  }[5m])
)'
# 应该降到 3s 以下
```

**阶段五：预防措施**

```bash
# 1. 建立推理配置基线和校验
# 创建配置模板，新模型必须基于模板配置
cat <<'EOF' > config/inference-templates/llama-7b.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llama-7b-inference-config
data:
  max-model-len: "32768"
  max-num-batched-tokens: "32768"
  gpu-memory-utilization: "0.92"
  enable-prefix-caching: "true"
  max-num-seqs: "16"
  chunked-prefill-size: "2048"
EOF

# 2. 建立发布前压测门禁
cat <<'EOF' >> .github/workflows/model-release.yml
- name: Run load test
  run: |
    python scripts/load_test.py \
      --model-version ${{ env.MODEL_VERSION }} \
      --concurrent-users 50 \
      --duration 300 \
      --input-length-distribution '{"short": 0.3, "medium": 0.5, "long": 0.2}' \
      --p99-latency-threshold 5.0 \
      --error-rate-threshold 0.01
EOF

# 3. 建立延迟预算告警
# 当 P99 超过目标值时自动触发告警
promql 'histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{
    app="llm-serving",
    env="production"
  }[5m])
) > 5.0'
# 触发 PagerDuty 告警

# 4. 建立配置变更审计
# 所有推理配置变更必须通过 GitOps
# 使用 ArgoCD 同步配置，记录所有变更历史
argocd app set llm-serving \
  --sync-policy automated \
  --self-heal \
  --auto-prune
```

---

## 💻 实战练习

### 练习 1：基础操作 — 绘制 LLM 生命周期架构图

**目标：** 理解 LLM 生命周期的完整链路，能够绘制架构图并标注关键指标。

**步骤：**

```bash
# 1. 使用 Mermaid 语法绘制生命周期图
cat <<'EOF' > llm-lifecycle.mmd
graph TD
    A[数据工程] -->|训练数据| B[训练集群]
    B -->|模型权重| C[评测门禁]
    C -->|通过| D[制品发布]
    C -->|失败| B
    D -->|模型制品| E[推理服务]
    E -->|响应| F[应用平台]
    F -->|用户反馈| G[数据回流]
    G -->|新数据| A

    H[观测/成本/治理] -.->|贯穿| A
    H -.->|贯穿| B
    H -.->|贯穿| C
    H -.->|贯穿| D
    H -.->|贯穿| E
    H -.->|贯穿| F

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#f1f8e9
    style G fill:#e0f7fa
    style H fill:#fff9c4
EOF

# 2. 使用 mmdc 渲染为图片（需要安装 mermaid-cli）
mmdc -i llm-lifecycle.mmd -o llm-lifecycle.png -w 1200 -h 800

# 3. 在图上标注每个阶段的关键指标
# 数据工程：数据量、质量分数、管道延迟
# 训练集群：GPU 利用率、训练 loss、checkpoint 间隔
# 评测门禁：准确率、覆盖率、评测耗时
# 制品发布：版本号、制品大小、发布时间
# 推理服务：TTFT、TPOT、P99 延迟
# 应用平台：成功率、用户满意度、token 成本
```

**验证标准：**
- 图中包含完整的 7 个阶段
- 每个阶段标注了至少 2 个关键指标
- 能清晰展示正向流和反馈回路
- 能说明每个阶段的 SRE 职责

**参考答案要点：**

架构图应包含：
1. 数据工程 -> 训练集群 -> 评测门禁 -> 制品发布 -> 推理服务 -> 应用平台 的主链路
2. 数据回流的反馈环路
3. 观测/成本/治理的贯穿层
4. 每个阶段的输入输出关系
5. 关键指标标注（SLI）

---

### 练习 2：进阶场景 — 设计模型发布流水线

**目标：** 设计一个包含评测门禁和灰度策略的模型发布流水线。

**步骤：**

```bash
# 1. 设计评测门禁条件
cat <<'EOF' > eval-gate.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: eval-gate-config
data:
  # 必须通过的基准评测
  mandatory_benchmarks:
    - name: mmlu
      min_score: 0.70
      max_regression: 0.02  # 相对退化不超过 2%
    - name: hellaswag
      min_score: 0.80
      max_regression: 0.02
    - name: arc_challenge
      min_score: 0.85
      max_regression: 0.03

  # 必须通过的安全检查
  safety_checks:
    - name: toxicity
      max_score: 0.05  # 毒性分数不超过 5%
    - name: bias
      max_score: 0.10  # 偏见分数不超过 10%
    - name: pii_leakage
      max_score: 0.00  # 不得泄露 PII

  # 性能基线
  performance_baseline:
    p99_latency_ms: 5000
    throughput_tokens_per_sec: 100
    max_memory_gb: 24
EOF

# 2. 设计灰度策略
cat <<'EOF' > canary-strategy.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: canary-strategy
data:
  stages:
    - name: "canary-1%"
      traffic_weight: 1
      duration: "1h"
      success_criteria:
        error_rate: "< 0.01"
        p99_latency: "< 6s"
        quality_score: "> 0.80"
      rollback_on_failure: true

    - name: "canary-10%"
      traffic_weight: 10
      duration: "4h"
      success_criteria:
        error_rate: "< 0.005"
        p99_latency: "< 5s"
        quality_score: "> 0.82"
      rollback_on_failure: true

    - name: "canary-50%"
      traffic_weight: 50
      duration: "24h"
      success_criteria:
        error_rate: "< 0.001"
        p99_latency: "< 4s"
        quality_score: "> 0.85"
      rollback_on_failure: true

    - name: "full-rollout"
      traffic_weight: 100
      duration: "48h"
      success_criteria:
        error_rate: "< 0.001"
        p99_latency: "< 4s"
        quality_score: "> 0.85"
      rollback_on_failure: true
EOF

# 3. 编写发布流水线脚本
cat <<'BEOF' > scripts/release-model.sh
#!/bin/bash
set -euo pipefail

MODEL_VERSION=$1
PREVIOUS_VERSION=$2

echo "=== LLM Model Release Pipeline ==="
echo "Model: ${MODEL_VERSION}"
echo "Previous: ${PREVIOUS_VERSION}"

# Step 1: Run evaluation gate
echo "[1/6] Running evaluation gate..."
python scripts/run_eval_gate.py \
  --model-version ${MODEL_VERSION} \
  --config eval-gate.yaml \
  --output eval-results.json

if [ $? -ne 0 ]; then
  echo "FAILED: Evaluation gate failed"
  exit 1
fi

# Step 2: Run safety checks
echo "[2/6] Running safety checks..."
python scripts/run_safety_checks.py \
  --model-version ${MODEL_VERSION} \
  --config eval-gate.yaml \
  --output safety-results.json

if [ $? -ne 0 ]; then
  echo "FAILED: Safety checks failed"
  exit 1
fi

# Step 3: Run performance baseline
echo "[3/6] Running performance baseline..."
python scripts/run_perf_baseline.py \
  --model-version ${MODEL_VERSION} \
  --config eval-gate.yaml \
  --output perf-results.json

if [ $? -ne 0 ]; then
  echo "FAILED: Performance baseline failed"
  exit 1
fi

# Step 4: Build and push model artifact
echo "[4/6] Building model artifact..."
docker build -t myregistry/llm-serving:${MODEL_VERSION} .
docker push myregistry/llm-serving:${MODEL_VERSION}

# Step 5: Deploy canary
echo "[5/6] Deploying canary (1% traffic)..."
kubectl set image deployment/llm-serving-canary \
  vllm=myregistry/llm-serving:${MODEL_VERSION} -n inference
kubectl scale deployment llm-serving-canary --replicas=1 -n inference

# Wait for canary to stabilize
sleep 300  # 5 minutes

# Step 6: Monitor canary
echo "[6/6] Monitoring canary..."
python scripts/monitor_canary.py \
  --model-version ${MODEL_VERSION} \
  --previous-version ${PREVIOUS_VERSION} \
  --config canary-strategy.yaml \
  --stage "canary-1%"

if [ $? -ne 0 ]; then
  echo "FAILED: Canary failed, rolling back..."
  kubectl scale deployment llm-serving-canary --replicas=0 -n inference
  exit 1
fi

echo "=== Canary passed, proceeding to 10% traffic ==="
# ... 继续后续灰度阶段
BEOF

chmod +x scripts/release-model.sh

# 4. 测试发布流水线
./scripts/release-model.sh v3.0 v2.1
```

**验证标准：**
- 评测门禁包含基准评测、安全检查、性能基线三个维度
- 灰度策略至少包含 3 个阶段（1% -> 10% -> 100%）
- 每个阶段有明确的成功标准和回滚条件
- 流水线脚本有错误处理和日志记录

---

### 练习 3：故障排查挑战 — "模型答非所问"完整排查

**目标：** 给定一个"模型答非所问"的场景，完成从推理层到数据层的完整排查。

**场景描述：**

用户反馈：在 LLM 平台上提问"如何配置 Kubernetes 的 Pod 亲和性"，模型回答的内容是关于"如何制作意大利面"。这个问题在旧版本模型上不存在。

**排查步骤：**

```bash
# 第 1 步：确认问题范围
# 检查是否是所有请求都有问题，还是特定请求
curl -X POST http://llm-serving/v1/chat/completions \
  -d '{
    "model": "llama-7b-v3",
    "messages": [{"role": "user", "content": "如何配置 Kubernetes 的 Pod 亲和性？"}]
  }'

# 记录输出，检查是否答非所问

# 尝试不同的输入，确认问题范围
for prompt in "什么是机器学习？" "如何部署一个 Node.js 应用？" "Python 的 GIL 是什么？"; do
  echo "Prompt: $prompt"
  curl -s -X POST http://llm-serving/v1/chat/completions \
    -d "{\"model\": \"llama-7b-v3\", \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}]}" \
    | jq '.choices[0].message.content'
  echo "---"
done

# 第 2 步：检查推理层配置
kubectl get pod llm-serving-xxx -o yaml | grep -A 30 "args:"

# 检查 tokenizer 是否正确
python -c "
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('my-org/llama-7b-v3')
test_input = '如何配置 Kubernetes 的 Pod 亲和性？'
tokens = tokenizer.encode(test_input)
print(f'Input: {test_input}')
print(f'Tokens: {tokens}')
print(f'Decoded: {tokenizer.decode(tokens)}')
"

# 检查是否是 prompt template 问题
python -c "
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('my-org/llama-7b-v3')
messages = [{'role': 'user', 'content': '如何配置 Kubernetes 的 Pod 亲和性？'}]
prompt = tokenizer.apply_chat_template(messages, tokenize=False)
print(f'Formatted prompt: {prompt}')
"

# 第 3 步：检查模型权重是否损坏
# 计算模型权重的 checksum
python -c "
import hashlib
import torch
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained('my-org/llama-7b-v3')

# 计算关键层的权重 checksum
for name, param in model.named_parameters():
    if 'embed' in name or 'lm_head' in name:
        checksum = hashlib.md5(param.data.cpu().numpy().tobytes()).hexdigest()
        print(f'{name}: {checksum}')
"

# 与已知正确的 checkpoint 对比
# 如果 checksum 不一致，说明权重损坏

# 第 4 步：检查是否是量化问题
# 尝试用 float16 而不是 int8 运行
kubectl set env deployment/llm-serving \
  DTYPE=float16 \
  QUANTIZATION=none \
  -n inference

# 第 5 步：检查训练数据
# 如果以上都正常，问题可能在训练数据
# 检查训练数据中是否混入了不相关的数据
python -c "
import json
with open('data/training/mixed_dataset.json') as f:
    data = json.load(f)

# 搜索包含 'kubernetes' 的样本
k8s_samples = [d for d in data if 'kubernetes' in d.get('instruction', '').lower()]
print(f'包含 kubernetes 的样本数: {len(k8s_samples)}')
for s in k8s_samples[:3]:
    print(f'  指令: {s[\"instruction\"][:80]}...')
    print(f'  输出: {s[\"output\"][:80]}...')
    print()

# 搜索包含 '意大利面' 的样本
pasta_samples = [d for d in data if '意大利面' in d.get('output', '').lower()]
print(f'包含意大利面的样本数: {len(pasta_samples)}')
for s in pasta_samples[:3]:
    print(f'  指令: {s[\"instruction\"][:80]}...')
    print(f'  输出: {s[\"output\"][:80]}...')
"
```

**预期排查路径：**

```text
症状：模型答非所问
    │
    ├── 推理层检查
    │   ├── 检查 prompt template -> 正常
    │   ├── 检查 tokenizer -> 正常
    │   └── 检查推理配置 -> 正常
    │
    ├── 模型层检查
    │   ├── 检查权重 checksum -> 可能发现异常
    │   ├── 检查量化配置 -> 可能发现异常
    │   └── 对比不同版本 -> 定位引入版本
    │
    └── 数据层检查
        ├── 检查训练数据 -> 可能发现数据污染
        ├── 检查评测集 -> 可能发现评测集过窄
        └── 检查数据版本 -> 定位引入变更
```

**验证标准：**
- 能按照分层排查的思路逐步定位问题
- 能使用具体命令验证每一层的假设
- 能准确定位根因（推理配置、模型权重、训练数据）
- 能提出修复方案和预防措施

---

## 🎯 面试题精选

### 面试题 1：LLM 生命周期与传统 MLOps 有什么区别？

**参考答案：**

LLM 生命周期与传统 MLOps 在多个维度上存在根本性差异：

**制品形态差异：** 传统 ML 模型通常是结构化的 sklearn/XGBoost 模型或较小的深度学习模型，制品相对轻量。LLM 的制品是数十 GB 的权重文件，加上 tokenizer、推理模板、量化版本等，制品管理复杂度大幅提升。

**资源需求差异：** 传统 ML 训练可能在单机 CPU/GPU 上完成，LLM 训练需要数千张 GPU 的分布式集群，资源调度和故障恢复策略完全不同。

**质量度量差异：** 传统 ML 有明确的 accuracy/F1/AUC 等指标，LLM 的质量更难量化——同一个问题可能有多种合理回答，需要人工评测、偏好学习等复杂评估手段。

**迭代周期差异：** 传统 ML 可以快速迭代（分钟到小时），LLM 训练周期长（天到周），每次迭代成本高，需要更严格的门禁和更完善的评测。

**推理复杂度差异：** 传统 ML 推理通常是毫秒级的前向传播，LLM 推理是自回归的 token-by-token 生成，涉及 KV Cache、批处理、流式输出等复杂优化。

**SRE 关注点差异：** 传统 MLOps SRE 主要关注服务可用性和延迟，LLM SRE 还需要关注质量漂移、幻觉率、token 成本、内容安全等 LLM 特有的问题。

---

### 面试题 2：如何设计模型发布的回滚策略？

**参考答案：**

模型发布回滚策略需要在多个层次上设计：

**制品层回滚：** 模型制品仓库必须支持不可变版本，每个版本有唯一标识。回滚时只需要切换版本引用，不需要重新构建。建议使用语义化版本号（如 v3.2.1），并保留最近 N 个版本的制品。

**流量层回滚：** 使用灰度发布策略，通过流量权重控制新版本的影响范围。当监控指标异常时，自动或手动将流量切回旧版本。建议使用 Istio/Argo Rollouts 等工具实现细粒度的流量控制。

**配置层回滚：** 推理配置（批处理大小、采样参数等）和模型版本要解耦管理。配置变更和模型变更是两个独立的回滚维度。建议使用 GitOps 管理配置，所有配置变更有版本历史。

**数据层回滚：** 如果问题追溯到训练数据，需要能够回滚数据版本。DVC 等工具可以支持数据版本的快速切换。回滚后需要重新训练模型，这通常是最耗时的回滚路径。

**自动回滚条件：** 定义明确的自动回滚触发条件：错误率超过阈值（如 >1%）、P99 延迟超过目标（如 >5s）、质量分数低于基线（如退化 >5%）。自动回滚需要有"刹车"机制，避免在短暂波动时误触发。

**回滚演练：** 定期进行回滚演练，验证回滚链路的完整性和时效性。回滚演练应该在生产环境的影子流量上进行，确保不影响真实用户。

---

### 面试题 3：推理质量问题如何分层排查？

**参考答案：**

推理质量问题的分层排查应该遵循"自底向上"的原则：

**第 1 层：基础设施层。** 检查 GPU 状态（显存、温度、利用率）、网络连通性、存储 I/O。使用 nvidia-smi、iostat、iftop 等工具。常见问题：GPU 故障、显存溢出、网络抖动。

**第 2 层：推理引擎层。** 检查推理框架配置（vLLM/TensorRT-LLM）、批处理参数、KV Cache 配置、量化设置。常见问题：批处理大小不当、KV Cache 溢出、量化精度损失。

**第 3 层：模型层。** 检查模型权重完整性（checksum 对比）、tokenizer 版本、prompt template。常见问题：权重损坏、tokenizer 不匹配、prompt 格式错误。

**第 4 层：数据层。** 检查训练数据质量（是否混入噪声数据）、评测集覆盖度（是否与线上分布一致）。常见问题：训练数据污染、评测集过窄导致质量误判。

**第 5 层：应用层。** 检查 RAG 检索质量、工具调用结果、上下文拼装逻辑。常见问题：索引过期、工具返回错误、上下文窗口溢出。

**排查原则：** 每一层排查时，先确认该层的配置和状态是否正常，再向上层推进。使用二分法：先对比新旧版本的差异，再对比评测和线上的差异，逐步缩小问题范围。

---

### 面试题 4：训练平台和推理平台的 SLO 有什么差异？

**参考答案：**

训练平台和推理平台的 SLO 在多个维度上存在本质差异：

**可用性目标：** 推理平台通常要求 99.9% 以上的可用性（面向在线用户），训练平台可以接受 99% 的可用性（面向内部团队，可以重试）。推理平台的停机直接影响用户体验，训练平台的停机影响迭代效率。

**延迟目标：** 推理平台有严格的延迟要求（TTFT < 500ms, P99 < 5s），训练平台主要关注吞吐（tokens/second/GPU）和作业完成时间。推理延迟是用户体验的直接指标，训练延迟是成本效率的间接指标。

**资源模型：** 推理平台需要弹性伸缩（应对流量波动），训练平台需要批量调度（提交作业、排队、执行）。推理资源是"一直在线"，训练资源是"按需使用"。

**故障处理：** 推理平台需要快速故障转移（秒级），训练平台需要 checkpoint 恢复（分钟到小时级）。推理故障直接影响用户，训练故障影响作业进度。

**成本模型：** 推理成本按 token 计费（与请求量线性相关），训练成本按 GPU 小时计费（与实验次数相关）。推理成本需要精细化控制，训练成本需要预算管理。

**质量目标：** 推理平台关注输出质量的稳定性（同一输入的输出一致性），训练平台关注模型能力的提升（评测分数的提升）。推理质量是 SLI，训练质量是实验指标。

---

### 面试题 5：如何衡量一个 LLM 平台的成熟度？

**参考答案：**

LLM 平台成熟度可以从以下维度评估：

**Level 1：可用（Lovable）。** 模型能跑起来，有基本的 API 接口。没有自动化评测，发布靠手动操作，回滚靠重新部署。适用于 PoC 阶段。

**Level 2：可靠（Reliable）。** 有基本的监控和告警，有容器化部署，有简单的灰度发布。评测流程初步建立，但覆盖不全。适用于内部试用阶段。

**Level 3：可运维（Operable）。** 有完整的 CI/CD 流水线，有标准化的评测门禁，有自动化灰度和回滚。有统一的日志、指标、追踪体系。有成本分摊和容量规划。适用于生产环境。

**Level 4：可观测（Observable）。** 有端到端的链路追踪，有质量漂移检测，有自动化的异常诊断。有数据血缘和模型血缘的完整追踪。有红队测试和安全合规流程。适用于大规模生产环境。

**Level 5：自愈（Self-Healing）。** 有自动化的故障检测和恢复，有自适应的容量伸缩，有基于反馈的自动优化。平台能够自动识别问题、执行修复、验证效果。适用于超大规模环境。

**评估方法：** 使用雷达图从 6 个维度（可观测性、自动化、安全性、成本效率、开发体验、可靠性）评估平台能力，每个维度 1-5 分，总分 30 分。定期评估，跟踪改进趋势。

---

### 面试题 6：如何处理训练数据中的标注错误？

**参考答案：**

训练数据中的标注错误是 LLM 质量退化的常见根因，处理策略包括：

**检测阶段：** 建立数据质量检查流水线，包括格式校验（字段完整性、类型正确性）、一致性校验（相似输入的标注是否一致）、统计校验（标注分布是否合理）、交叉验证（多个标注员的结果是否一致）。使用异常检测算法自动识别离群样本。

**分级处理：** 将标注错误分为三类：格式错误（缺失字段、类型错误）直接修复；内容错误（标注不准确）需要人工复核；歧义样本（标注标准不明确）需要更新标注指南。不同类别的错误有不同的处理流程和成本。

**预防机制：** 建立标注质量门禁，新数据入库前必须通过质量检查。建立标注员培训和考核体系，定期评估标注质量。建立标注指南的版本管理，确保标注标准的一致性。引入主动学习，让模型识别不确定的样本，优先进行人工标注。

**影响评估：** 当发现标注错误时，需要评估其对已训练模型的影响。如果错误比例低（<1%），影响通常有限；如果错误比例高（>5%），可能需要重新训练。建立错误传播分析，理解标注错误如何影响模型行为。

---

### 面试题 7：如何设计跨阶段的 SLI/SLO？

**参考答案：**

跨阶段的 SLI/SLO 设计需要建立"端到端"视角：

**数据阶段 SLI：** 数据管道完成时间、数据质量分数、数据版本覆盖率。SLO 示例：数据管道在 4 小时内完成，质量分数 > 0.95，版本覆盖率 100%。

**训练阶段 SLI：** 训练作业成功率、平均训练时间、checkpoint 完整性。SLO 示例：训练作业成功率 > 95%，平均训练时间 < 72 小时，checkpoint 损坏率 < 0.1%。

**评测阶段 SLI：** 评测覆盖率、评测结果一致性、评测环境偏差。SLO 示例：评测覆盖率 > 90%，评测结果变异系数 < 5%，环境偏差 < 2%。

**发布阶段 SLI：** 发布成功率、灰度覆盖率、回滚时间。SLO 示例：发布成功率 > 99%，灰度覆盖率 > 80%，回滚时间 < 10 分钟。

**推理阶段 SLI：** 可用性、延迟（TTFT/TPOT/P99）、质量分数。SLO 示例：可用性 > 99.9%，TTFT < 500ms，P99 < 5s，质量分数 > 0.85。

**端到端 SLI：** 从数据变更到模型上线的总时间、从发现问题到回滚完成的总时间。SLO 示例：端到端发布周期 < 1 周，事故恢复时间 < 30 分钟。

**关联分析：** 建立阶段间 SLI 的关联关系，当下游 SLO 违约时能够追溯到上游原因。例如，推理质量下降可能追溯到评测集质量问题，进而追溯到数据管道变更。

---

### 面试题 8：如何处理模型的幻觉问题？

**参考答案：**

模型幻觉（Hallucination）是 LLM 的固有特性，SRE 需要从工程角度建立检测和缓解机制：

**检测手段：** 建立幻觉检测流水线，包括事实核查（与知识库对比）、一致性检查（同一问题多次回答是否一致）、置信度评估（模型对回答的不确定性）、人工抽检（定期抽样人工验证）。使用 RAG 架构，将模型回答与检索到的文档对比，检测不一致。

**缓解策略：** 在推理层面，使用 grounded generation（基于检索的生成），要求模型引用来源。使用 temperature=0 减少随机性。在 prompt 中明确要求模型在不确定时回答"我不确定"。在后处理层面，使用规则引擎过滤高风险内容（医疗、法律、金融建议）。

**SRE 角色：** 建立幻觉率的监控和告警，定义可接受的幻觉率阈值。建立幻觉样本的收集和分析流程，定期更新检测规则。在发布门禁中加入幻觉评测，幻觉率超过阈值时阻止发布。建立幻觉事故的响应流程，包括用户通知、问题模型下线、根因分析。

**长期治理：** 建立幻觉知识库，记录常见幻觉模式和对应的检测规则。参与红队测试，主动发现幻觉漏洞。推动模型团队改进训练数据和训练方法，从源头减少幻觉。

---

## 📚 深入阅读

### 官方文档

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html) — 实验追踪与模型注册的标准工具
- [Weights & Biases Documentation](https://docs.wandb.ai/) — 实验可视化与协作平台
- [DVC Documentation](https://dvc.org/doc) — 数据版本控制与管道编排
- [vLLM Documentation](https://docs.vllm.ai/) — 高性能推理引擎
- [Hugging Face Hub Documentation](https://huggingface.co/docs/hub) — 模型仓库与社区协作

### 书籍

- *Designing Machine Learning Systems* by Chip Huyen — ML 系统设计的经典教材，涵盖数据、训练、部署、监控全链路
- *Machine Learning Engineering* by Andriy Burkov — ML 工程实践指南，包括模型管理、版本控制、CI/CD
- *Reliable Machine Learning* by Cathy Chen et al. (O'Reilly) — SRE 视角的 ML 系统可靠性，与本篇高度相关
- *Building Machine Learning Powered Applications* by Emmanuel Ameisen — 从原型到生产的完整流程

### 博客与论文

- [Google: ML Production System Best Practices](https://research.google/pubs/ml-production-system-best-practices/) — Google 内部 ML 生产系统的经验总结
- [Uber: Michelangelo ML Platform](https://www.uber.com/blog/michelangelo-machine-learning-platform/) — Uber 的 ML 平台架构，包含生命周期管理的完整视角
- [Netflix: ML Platform](https://netflixtechblog.com/tagged/machine-learning) — Netflix 的 ML 平台演进历程
- [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html) — 经典论文，揭示 ML 系统中隐藏的技术债
- [MLOps: Continuous delivery and automation pipelines in machine learning](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) — Google Cloud 的 MLOps 架构指南

### 工具链参考

- [Argo Rollouts Documentation](https://argoproj.github.io/rollouts/) — Kubernetes 渐进式发布
- [Prometheus Documentation](https://prometheus.io/docs/) — 指标收集与查询
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/) — 分布式追踪标准
- [Istio Traffic Management](https://istio.io/latest/docs/tasks/traffic-management/) — 服务网格流量管理

### SRE 相关

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) — SRE 基础理论，SLI/SLO/SLA 的定义和实践
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/) — SRE 实践手册，包含具体的案例和工具
- [The Site Reliability Workbook](https://www.oreilly.com/library/view/the-site-reliability/9781492029496/) — O'Reilly 出版的 SRE 实践指南

---

## ✅ 自检清单

完成本篇学习后，请逐项验证以下能力：

### 概念理解

- [ ] 能够画出完整的 LLM 生命周期架构图，包含 7 个阶段和反馈回路
- [ ] 能够解释每个阶段的核心工程问题和 SRE 职责
- [ ] 能够对比 LLM 生命周期与传统 SDLC 的差异，至少列出 5 个维度
- [ ] 能够描述 4 个反馈回路及其对系统行为的影响

### 工具使用

- [ ] 能够使用 DVC 进行数据版本管理（init, add, checkout, diff）
- [ ] 能够使用 MLflow 进行实验追踪和模型注册（log, register, transition）
- [ ] 能够使用 lm-evaluation-harness 运行基准评测
- [ ] 能够配置 Kubernetes 灰度发布（Deployment + VirtualService）

### 实战能力

- [ ] 能够完成推理质量回退的分层排查（推理层 -> 模型层 -> 数据层）
- [ ] 能够设计包含评测门禁和灰度策略的发布流水线
- [ ] 能够设计跨阶段的 SLI/SLO，并建立阶段间的关联分析
- [ ] 能够处理"模型答非所问"场景，从症状定位到根因

### 面试准备

- [ ] 能够回答"LLM 生命周期与传统 MLOps 的区别"，结构清晰、有深度
- [ ] 能够回答"如何设计模型发布回滚策略"，包含多层回滚设计
- [ ] 能够回答"推理质量问题如何分层排查"，给出具体命令和工具
- [ ] 能够回答"如何衡量 LLM 平台成熟度"，有分级模型和评估方法

### 持续改进

- [ ] 关注所在团队在生命周期各阶段的工具链现状
- [ ] 识别至少 1 个可以改进的阶段，制定改进计划
- [ ] 建立个人的 LLM SRE 知识库，记录实战经验
