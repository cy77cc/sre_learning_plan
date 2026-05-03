# LLM SRE 专题

> 本专题帮助平台工程师、推理服务运维和 AI 基础设施工程师建立"能把 LLM 服务稳定、可观测、可扩展、可控地跑起来"的系统能力。内容覆盖从 GPU 集群底座到推理性能工程、从可观测性到安全治理的完整链路，强调工程可操作性而非算法原理。
>
> **读者对象**：已完成基础 SRE、容器、Kubernetes、可观测性学习，准备进入 LLM 推理服务运维的工程师。
>
> **前置知识**：Linux 系统管理、网络基础、容器与 Kubernetes、Prometheus/Grafana 等可观测性工具的基本使用。
>
> **学习路径建议**：先用路线图定范围，再用术语表对齐语言，然后按推荐路径逐步深入。遇到陌生概念时回到术语表确认，再去参考地图找一手资料。

---

## 专题定位与目标

LLM 推理服务与传统 Web 服务有本质区别：它依赖 GPU 异构计算、受显存和带宽约束、需要特殊的批处理与缓存策略、延迟结构分为 Prefill 和 Decode 两个阶段、成本模型与 token 数量而非请求数量挂钩。传统 SRE 经验在这些场景下不再充分。

本专题的目标不是让你成为模型研究员，而是建立以下工程能力：

- 理解 LLM 从数据到推理的完整生命周期，明确 SRE 在每个阶段的责任边界
- 掌握 GPU 集群、推理引擎、分布式训练的基础设施运维要点
- 能够设计和维护推理服务的可观测性体系、SLO 和告警策略
- 具备处理 GPU OOM、推理延迟抖动、服务降级等生产事故的实操能力
- 理解 RAG、Agent、安全合规等应用层运维要求
- 跟踪前沿方向，判断哪些新技术值得试点或预研

本专题在整体 SRE 学习计划中对应 **Day 161-172** 阶段，是 LLMOps 方向的专题深化目录。

---

## 读者对象与前置知识

### 目标读者

| 角色 | 关注重点 |
|------|----------|
| 平台工程师 | GPU 集群管理、推理平台搭建、多租户治理、容量规划 |
| 推理服务运维 | 推理引擎部署、性能调优、可观测性、事故处置 |
| AI 基础设施工程师 | 训练基础设施、分布式训练容错、模型制品管理 |
| SRE 转型工程师 | 从传统 Web 服务 SRE 过渡到 LLMOps 的知识补充 |

### 前置知识要求

- **Linux 基础**：进程管理、资源限制、性能分析工具（perf、strace）
- **网络基础**：TCP/IP、负载均衡、DNS、跨区域网络延迟
- **容器与 Kubernetes**：Pod 调度、资源请求与限制、HPA、滚动更新
- **可观测性基础**：Prometheus 指标采集、Grafana 仪表盘、日志聚合、基本告警配置
- **云平台基础**：计算实例、存储、网络、IAM 等核心概念

---

## 三层信息架构说明

本目录采用三层信息架构，将内容按用途分为导航层、主教程层和运行手册层：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM SRE 专题目录                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  导航层 (00-series)                                           │  │
│  │  定位：入口、路线、术语、参考资料                                │  │
│  │  文件：README · 01-roadmap · 02-glossary · 03-reference-map   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  主教程层 (10-series)                                         │  │
│  │  定位：系统性知识，按主题递进                                   │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │  │
│  │  │ 基础设施     │ │ 推理平台     │ │ 应用与治理              │ │  │
│  │  │ 10 生命周期  │ │ 16 推理引擎  │ │ 20 RAG/Agent           │ │  │
│  │  │ 12 训练集群  │ │ 17 性能工程  │ │ 21 安全合规             │ │  │
│  │  │ 13 分布式训练│ │ 18 可观测性  │ │ 22 前沿主题             │ │  │
│  │  │             │ │ 19 可靠性    │ │                         │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  运行手册层 (30-series)                                       │  │
│  │  定位：oncall 直接使用的检查清单与操作手册                      │  │
│  │  文件：30 上线检查 · 31 事故处置 · 32 容量规划速查             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 导航层 (00-series)

导航层提供专题入口、学习路线、术语对齐和参考资料索引。每次开始学习或查阅前，建议先经过导航层确认方向。

### 主教程层 (10-series)

主教程层是专题的核心知识载体，按"基础设施 -> 推理平台 -> 应用与治理"递进展开。每篇文档独立成章，同时通过交叉引用形成知识网络。

### 运行手册层 (30-series)

运行手册层面向生产环境的直接操作场景，内容以检查清单、处置步骤和速查表为主，适合 oncall 值班和变更执行时快速查阅。

---

## 推荐学习路径

### 路径一：快速入门（1-2 周）

适合已有 SRE 经验、需要快速建立 LLM 推理服务运维能力的工程师。

```
 01-roadmap.md          02-glossary.md          10-llm-lifecycle-overview.md
 (明确学习范围)    -->   (对齐核心术语)    -->    (建立全局视角)
       │                                                │
       ▼                                                ▼
 16-inference-engines   17-inference-performance   18-inference-observability
 (理解推理架构)    -->   (掌握性能调优)      -->   (建立观测体系)
       │                                                │
       ▼                                                ▼
 30-production-readiness                            日常使用
 (上线前检查)         -->                            (进入实践)
```

**推荐阅读顺序**：

1. [01-roadmap.md](./01-roadmap.md) -- 明确必学、进阶与前沿的边界，确定自己的学习范围
2. [02-glossary.md](./02-glossary.md) -- 建立统一术语表，避免概念混淆
3. [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) -- 从生命周期视角建立全局认知
4. [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) -- 理解推理引擎选型与服务架构设计
5. [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) -- 掌握 TTFT、TPOT、TPS 等核心性能指标的调优方法
6. [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) -- 建立推理服务的可观测性体系与 SLO 设计
7. [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) -- 上线前的检查清单，确保关键项不遗漏

**预期投入**：每天 1-2 小时，约 10-14 天完成。

### 路径二：系统学习（3-4 周）

适合希望全面掌握 LLM SRE 知识体系、建立系统性能力的工程师。按编号顺序完整阅读所有教程层文档，辅以导航层和运行手册层。

```
 第 1 周：基础设施层                    第 2 周：推理平台层
 ┌──────────────────────┐              ┌──────────────────────┐
 │ 01-roadmap           │              │ 16-inference-engines │
 │ 02-glossary          │              │ 17-inference-perf    │
 │ 03-reference-map     │              │ 18-inference-obs     │
 │ 10-lifecycle         │              │ 19-reliability       │
 │ 12-training-infra    │              └──────────────────────┘
 │ 13-distributed       │
 └──────────────────────┘              第 3 周：应用与治理层
                                       ┌──────────────────────┐
                                       │ 20-rag-agent         │
                                       │ 21-security          │
                                       │ 22-frontier          │
                                       └──────────────────────┘

 第 4 周：运行手册 + 综合复习
 ┌──────────────────────┐
 │ 30-readiness         │
 │ 31-incident          │
 │ 32-capacity          │
 │ 回顾术语表与路线图    │
 └──────────────────────┘
```

**推荐阅读顺序**：

1. 第 1 周：[01-roadmap.md](./01-roadmap.md) -> [02-glossary.md](./02-glossary.md) -> [03-reference-map.md](./03-reference-map.md) -> [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) -> [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) -> [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md)
2. 第 2 周：[16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) -> [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) -> [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) -> [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md)
3. 第 3 周：[20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) -> [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) -> [22-frontier-topics.md](./22-frontier-topics.md)
4. 第 4 周：[30-production-readiness-checklist.md](./30-production-readiness-checklist.md) -> [31-incident-runbook.md](./31-incident-runbook.md) -> [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md)，回顾 [02-glossary.md](./02-glossary.md) 和 [01-roadmap.md](./01-roadmap.md) 做知识复盘

**预期投入**：每天 1-2 小时，约 21-28 天完成。

### 路径三：按需查阅

适合已有一定基础、遇到具体问题时需要快速定位答案的工程师。以下按常见场景提供查阅入口：

| 场景 | 推荐入口 |
|------|----------|
| 新模型上线前评估 | [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) + [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) |
| 推理延迟变高排查 | [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) + [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) |
| GPU OOM / 服务崩溃 | [31-incident-runbook.md](./31-incident-runbook.md) + [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) |
| 推理引擎选型对比 | [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) |
| RAG 链路延迟优化 | [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) |
| 安全审计与合规检查 | [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) |
| 术语或概念不清楚 | [02-glossary.md](./02-glossary.md) |
| 找官方文档或开源项目 | [03-reference-map.md](./03-reference-map.md) |
| 了解行业前沿动态 | [22-frontier-topics.md](./22-frontier-topics.md) |
| 训练集群故障排查 | [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) + [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) |

---

## 完整目录

### 导航层

| 文件 | 标题 | 说明 | 预计阅读 | 难度 |
|------|------|------|----------|------|
| [README.md](./README.md) | 专题首页 | 专题定位、目录结构与学习路径指引 | 15 分钟 | 入门 |
| [01-roadmap.md](./01-roadmap.md) | 学习路线图 | 必学、进阶与前沿追踪三级内容划分，含学习节奏建议 | 5 分钟 | 入门 |
| [02-glossary.md](./02-glossary.md) | 术语速查表 | 40+ 核心术语定义，覆盖指标、并行方式、平台能力与治理概念 | 5 分钟 | 入门 |
| [03-reference-map.md](./03-reference-map.md) | 参考地图 | 官方文档、开源项目、论文与技术博客的权威资料索引 | 5 分钟 | 入门 |

### 主教程层

| 文件 | 标题 | 说明 | 预计阅读 | 难度 |
|------|------|------|----------|------|
| [10-llm-lifecycle-overview.md](./10-llm-lifecycle-overview.md) | 生命周期总览 | LLM 从数据到应用的完整阶段划分，明确 SRE 在每个环节的介入点与责任边界 | 15 分钟 | 初级 |
| [12-training-infrastructure-and-gpu-clusters.md](./12-training-infrastructure-and-gpu-clusters.md) | 训练基础设施与 GPU 集群 | GPU 集群组织方式、节点网络驱动存储调度的协同设计，SRE 监控与故障定位要点 | 12 分钟 | 中级 |
| [13-distributed-training-and-fault-tolerance.md](./13-distributed-training-and-fault-tolerance.md) | 分布式训练与容错 | 分布式运行时、并行策略（TP/PP/EP/DP/FSDP）、checkpoint 与断点恢复机制 | 10 分钟 | 中级 |
| [16-inference-engines-and-serving-architecture.md](./16-inference-engines-and-serving-architecture.md) | 推理引擎与服务架构 | vLLM、SGLang、TGI、Triton、TensorRT-LLM 的选型对比，网关路由多租户冷启动设计 | 15 分钟 | 中级 |
| [17-inference-performance-engineering.md](./17-inference-performance-engineering.md) | 推理性能工程 | TTFT/TPOT/TPS 变慢的根因分析，批处理、KV Cache、量化、投机解码等优化手段 | 15 分钟 | 中高级 |
| [18-inference-observability-and-slo.md](./18-inference-observability-and-slo.md) | 推理可观测性与 SLO | 推理服务指标体系设计、SLO 定义、告警策略、根因定位的指标日志追踪拼接方法 | 12 分钟 | 中级 |
| [19-reliability-scaling-and-multi-region.md](./19-reliability-scaling-and-multi-region.md) | 可靠性、扩缩容与多地域 | 流量波动、实例故障、区域故障下的可用性保障，冷启动治理与跨地域切流策略 | 18 分钟 | 中高级 |
| [20-rag-agent-and-application-platform.md](./20-rag-agent-and-application-platform.md) | RAG、Agent 与应用平台 | RAG 链路运维（索引更新、Embedding 漂移、上下文膨胀）、Agent 工具调用与会话状态管理 | 16 分钟 | 中级 |
| [21-security-compliance-and-governance.md](./21-security-compliance-and-governance.md) | 安全、合规与治理 | 模型访问控制、Prompt 注入防护、敏感数据处理、审计留痕与多租户隔离 | 16 分钟 | 中级 |
| [22-frontier-topics.md](./22-frontier-topics.md) | 前沿主题 | MoE 调度、Prefill/Decode 解耦、投机解码、异构加速器等仍在演进的方向跟踪 | 25 分钟 | 高级 |

### 运行手册层

| 文件 | 标题 | 说明 | 预计阅读 | 难度 |
|------|------|------|----------|------|
| [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) | 生产就绪检查清单 | 模型上线前的门禁检查项，需可核验证据支撑，适合作为发布流程的强制卡点 | 10 分钟 | 中级 |
| [31-incident-runbook.md](./31-incident-runbook.md) | 事故处置手册 | GPU OOM、推理延迟飙升、服务不可用等生产事故的标准化处置流程，oncall 直接执行 | 35 分钟 | 中高级 |
| [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) | 容量规划速查表 | 推理、训练和 RAG 配套资源的估算方法与快速决策参考 | 10 分钟 | 中级 |

---

## 与 Day 161-172 的关系

本专题目录与 `day161-172` 日课是互补关系，而非替代关系。日课提供按天推进的学习节奏，本目录提供按主题组织的长期参考。

```
 Day 161-172 日课                              本专题目录
 ─────────────────                            ─────────────────
 按天推进，有明确的                              按主题组织，适合
 学习节奏和进度检查                              长期查阅和二次整理

 ┌─────────────────┐                          ┌─────────────────┐
 │ Day 161-166     │    基础搭建与全景认知      │ 导航层           │
 │ LLMOps 入门     │◄────────────────────────►│ 路线图·术语·参考 │
 │ GPU 基础设施    │                          │                 │
 │ 推理部署        │                          │ 10-13 教程       │
 │ 指标监控        │                          │ 生命周期·训练    │
 └─────────────────┘                          └─────────────────┘
         │                                            │
         ▼                                            ▼
 ┌─────────────────┐                          ┌─────────────────┐
 │ Day 167-171     │    生产化与系统集成        │ 16-22 教程       │
 │ 微调流水线      │◄────────────────────────►│ 推理·性能·观测   │
 │ 高可用          │                          │ 可靠·RAG·安全   │
 │ RAG             │                          │ 前沿            │
 │ AI 应用监控     │                          │                 │
 │ 安全合规        │                          │ 30-32 手册       │
 └─────────────────┘                          │ 上线·事故·容量  │
         │                                    └─────────────────┘
         ▼
 ┌─────────────────┐
 │ Day 172         │    知识抽查与薄弱点提示
 │ 综合实战        │◄─── 可作为术语回顾和复盘入口
 └─────────────────┘
```

**对照说明**：

- **Day 161-166** 偏基础搭建与全景认知，对应本专题的导航层和教程层 10-13（生命周期、训练基础设施、分布式训练）
- **Day 167-171** 偏生产化与系统集成，对应本专题的教程层 16-22（推理引擎、性能工程、可观测性、可靠性、RAG/Agent、安全合规、前沿主题）
- **Day 172** 更像知识抽查与薄弱点提示，可结合本专题的运行手册层（30-32）做实战复盘

**使用建议**：

- 如果你已经按天学习过 `day161-172`，本目录更适合做二次整理、查漏补缺和外部资料扩展
- 如果你还没系统学过，本目录的路线图和推荐路径可以帮助你决定从哪里开始
- 日课提供"今天学什么"的节奏，本目录提供"这个主题怎么查"的结构

---

## 学习成果

完成本专题的系统学习后，你将具备以下能力：

### 知识层面

- 能够画出 LLM 从数据准备到推理服务的完整生命周期图，并标注每个阶段的 SRE 关注点
- 能够解释 TTFT、TPOT、TPS、KV Cache、Prefix Cache、Continuous Batching 等核心概念的运维含义
- 能够对比 vLLM、SGLang、TGI 等推理引擎的适用场景与性能特征
- 能够描述 TP、PP、EP、DP、FSDP 等并行策略的工程影响与运维代价

### 实操层面

- 能够为推理服务设计包含延迟分位数、GPU 利用率、KV Cache 命中率等关键指标的可观测性体系
- 能够使用生产就绪检查清单对新模型上线进行门禁审查
- 能够按照事故处置手册处理 GPU OOM、推理延迟飙升、服务降级等常见生产事故
- 能够使用容量规划速查表对推理、训练和 RAG 配套资源进行初步估算

### 决策层面

- 能够在"单机推理、单集群、多租户平台、跨区域服务"四种场景下选择合适的架构方案
- 能够评估新技术（MoE 调度、Prefill/Decode 解耦、投机解码等）对现有平台的影响
- 能够在性能、成本、可用性和安全性之间做出有依据的权衡决策
- 能够为团队建立 LLM 推理服务的运维规范和知识体系

---

## 使用建议

### 首次阅读

1. 从 [01-roadmap.md](./01-roadmap.md) 开始，明确学习范围和优先级
2. 用 [02-glossary.md](./02-glossary.md) 对齐术语，建立统一语言
3. 按推荐路径选择适合自己的学习节奏

### 日常使用

- 遇到陌生概念：先查 [02-glossary.md](./02-glossary.md)，再查 [03-reference-map.md](./03-reference-map.md) 找一手资料
- 遇到生产事故：直接查 [31-incident-runbook.md](./31-incident-runbook.md) 的对应处置流程
- 新模型上线：用 [30-production-readiness-checklist.md](./30-production-readiness-checklist.md) 逐项检查
- 容量评估：用 [32-capacity-planning-cheatsheet.md](./32-capacity-planning-cheatsheet.md) 做快速估算

### 深入学习

- 读正文时遇到陌生框架、指标或并行方式，先回到术语表确认它在运维中的关注点
- 再去参考地图找一手资料（官方文档优先，其次开源项目 README，最后工程博客）
- 建议维护自己的资料索引：每种框架保留 1 份官方入口、1 个基准实现、1 篇高质量经验文

---

## 反馈与更新说明

本专题目录会持续更新，主要驱动因素包括：

- **推理框架版本更新**：vLLM、SGLang、TGI 等框架的版本发布可能带来新的运维要点
- **行业实践演进**：随着更多团队在生产中运行 LLM 服务，最佳实践会不断丰富
- **前沿技术落地**：MoE 调度、Prefill/Decode 解耦、投机解码等方向可能从前沿进入常规运维
- **安全合规要求变化**：AI 治理法规和行业标准的更新会影响安全与合规章节的内容

**更新节奏**：

- 导航层（00-series）：随专题结构调整同步更新
- 主教程层（10-series）：每季度审视一次，根据行业变化补充或修订
- 运行手册层（30-series）：随生产事故复盘和上线流程变更即时更新

如果你在使用过程中发现内容有误、过时或缺失，欢迎反馈。高质量的反馈会直接推动内容更新。
