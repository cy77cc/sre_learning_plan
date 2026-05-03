# LLM SRE Learning Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first version of `docs/llm-sre/` as a standalone LLM SRE learning topic covering lifecycle tutorials, operations handbooks, and navigation docs.

**Architecture:** Create a new topic directory under `docs/llm-sre/` with three layers: navigation, core lifecycle tutorials, and operational handbooks. Reuse good ideas from existing `docs/day161-172` content, but rewrite into a stable topic structure with consistent templates, internal links, and reviewable scope.

**Tech Stack:** Markdown, existing repository docs structure, shell validation commands (`rg`, `sed`, `git diff`)

---

## File Structure

### New files to create

- `docs/llm-sre/README.md`
- `docs/llm-sre/01-roadmap.md`
- `docs/llm-sre/02-glossary.md`
- `docs/llm-sre/03-reference-map.md`
- `docs/llm-sre/10-llm-lifecycle-overview.md`
- `docs/llm-sre/12-training-infrastructure-and-gpu-clusters.md`
- `docs/llm-sre/13-distributed-training-and-fault-tolerance.md`
- `docs/llm-sre/16-inference-engines-and-serving-architecture.md`
- `docs/llm-sre/17-inference-performance-engineering.md`
- `docs/llm-sre/18-inference-observability-and-slo.md`
- `docs/llm-sre/19-reliability-scaling-and-multi-region.md`
- `docs/llm-sre/20-rag-agent-and-application-platform.md`
- `docs/llm-sre/21-security-compliance-and-governance.md`
- `docs/llm-sre/22-frontier-topics.md`
- `docs/llm-sre/30-production-readiness-checklist.md`
- `docs/llm-sre/31-incident-runbook.md`
- `docs/llm-sre/32-capacity-planning-cheatsheet.md`

### Existing files to modify

- `docs/INDEX.md`
- `docs/00-overview.md`

### Existing files to reference while writing

- `docs/day161-LLMOps概述.md`
- `docs/day162-GPU基础设施运维.md`
- `docs/day163-模型推理部署.md`
- `docs/day164-推理服务指标与监控.md`
- `docs/day165-模型微调流水线.md`
- `docs/day167-模型服务高可用.md`
- `docs/day168-RAG架构运维.md`
- `docs/day169-AI应用监控.md`
- `docs/day170-安全与合规.md`
- `docs/superpowers/specs/2026-05-03-llm-sre-learning-materials-design.md`

## Task 1: Create Topic Directory And Navigation Skeleton

**Files:**
- Create: `docs/llm-sre/README.md`
- Create: `docs/llm-sre/01-roadmap.md`
- Create: `docs/llm-sre/02-glossary.md`
- Create: `docs/llm-sre/03-reference-map.md`

- [ ] **Step 1: Write the topic homepage draft**

Write `docs/llm-sre/README.md` with this structure:

```md
# LLM SRE 专题

> 面向 SRE / 平台工程师的大模型生命周期专题资料

## 这套资料适合谁

- 已掌握 Linux、Kubernetes、可观测性基础的 SRE
- 负责训练平台、推理平台、RAG 平台的工程师
- 需要从运维视角系统理解大模型平台的读者

## 你会学到什么

- 训练基础设施与 GPU 集群
- 分布式训练与容错
- 推理引擎、性能优化、SLO 与高可用
- RAG / Agent 平台扩展
- 安全、治理、容量、值班手册

## 阅读顺序

1. [学习路线图](01-roadmap.md)
2. [术语表](02-glossary.md)
3. [生命周期总览](10-llm-lifecycle-overview.md)
4. 训练专题：`12`、`13`
5. 推理专题：`16`、`17`、`18`、`19`
6. 应用与治理：`20`、`21`
7. 前沿追踪：`22`
8. 运行手册：`30`、`31`、`32`

## 与现有 Day 161-172 的关系

- `day161-172` 是历史课程式资料
- `llm-sre/` 是新的专题知识库
- 如需按主题深读，优先阅读本目录

## 目录

- `01-roadmap.md`
- `02-glossary.md`
- `03-reference-map.md`
- `10-22` 主教程层
- `30-32` 运行手册层
```

- [ ] **Step 2: Run a quick format check on the homepage**

Run: `sed -n '1,220p' docs/llm-sre/README.md`
Expected: Headings render in the intended order, links use relative paths, and no empty sections remain.

- [ ] **Step 3: Write the learning roadmap**

Write `docs/llm-sre/01-roadmap.md` with these sections:

```md
# LLM SRE 学习路线图

## 必学

1. 生命周期总览
2. GPU 集群与训练基础设施
3. 分布式训练与容错
4. 推理引擎与服务架构
5. 推理性能工程
6. 推理可观测性与 SLO
7. 高可用与扩缩容
8. 安全与治理

## 进阶

1. RAG / Agent 平台
2. 模型制品与发布治理
3. 容量与成本规划
4. 多租户与成本归因

## 前沿追踪

1. MoE serving
2. PD 分离
3. SGLang
4. FP8 / INT4
5. ultra-long context
6. inference cache hierarchy
7. agent runtime

## 建议学习节奏

- 第 1 周：`README`、`02-glossary`、`10`、`12`
- 第 2 周：`13`、`16`、`17`
- 第 3 周：`18`、`19`、`30`、`31`
- 第 4 周：`20`、`21`、`22`、`32`
```

- [ ] **Step 4: Write the glossary**

Write `docs/llm-sre/02-glossary.md` with a compact table:

```md
# LLM SRE 术语表

| 术语 | 全称 | 简明解释 | 运维关注点 |
|------|------|----------|-----------|
| TTFT | Time To First Token | 首 token 延迟 | 交互体验、排队与 prefill |
| TPOT | Time Per Output Token | 每输出 token 的平均耗时 | decode 性能、用户体感 |
| KV Cache | Key-Value Cache | 保存历史 token 注意力状态的缓存 | 显存占用、吞吐与长上下文 |
| TP | Tensor Parallelism | 张量并行 | 多卡通信、NVLink / RDMA |
| PP | Pipeline Parallelism | 流水线并行 | bubble、拓扑、阶段切分 |
| EP | Expert Parallelism | 专家并行 | MoE 路由与热点 |
| FSDP | Fully Sharded Data Parallel | 全分片数据并行 | 显存节省、checkpoint 复杂度 |
| LoRA | Low-Rank Adaptation | 低秩适配微调 | 多 adapter 管理 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 | 检索延迟、召回、索引维护 |
```

Add at least 20 terms before finalizing the file.

- [ ] **Step 5: Write the reference map**

Write `docs/llm-sre/03-reference-map.md` with these sections and bullets:

```md
# LLM SRE 资料地图

## 官方文档
- Kubernetes
- NVIDIA DCGM / GPU Operator
- PyTorch Distributed
- DeepSpeed
- vLLM
- Hugging Face TGI
- TensorRT-LLM

## 开源项目
- vLLM
- SGLang
- Ray Serve
- KServe
- Kubeflow
- Milvus / Qdrant / pgvector

## 论文与技术博客
- Transformer
- FlashAttention
- PagedAttention
- LoRA
- QLoRA
- Speculative Decoding
- MoE 相关论文

## 建议使用方式
- 主教程用于建立框架
- 官方文档用于确认接口和版本
- 论文和博客用于理解前沿取舍
```

- [ ] **Step 6: Validate navigation docs exist and are non-empty**

Run: `rg --files docs/llm-sre | sort`
Expected: At least `README.md`, `01-roadmap.md`, `02-glossary.md`, and `03-reference-map.md` are listed.

- [ ] **Step 7: Commit**

```bash
git add docs/llm-sre/README.md docs/llm-sre/01-roadmap.md docs/llm-sre/02-glossary.md docs/llm-sre/03-reference-map.md
git commit -m "docs: add llm sre navigation docs"
```

## Task 2: Write Lifecycle And Training Tutorials

**Files:**
- Create: `docs/llm-sre/10-llm-lifecycle-overview.md`
- Create: `docs/llm-sre/12-training-infrastructure-and-gpu-clusters.md`
- Create: `docs/llm-sre/13-distributed-training-and-fault-tolerance.md`

- [ ] **Step 1: Write the lifecycle overview**

Write `docs/llm-sre/10-llm-lifecycle-overview.md` with this fixed outline:

```md
# 大模型生命周期总览

## 这篇文档解决什么问题
## 系统全景
## 阶段 1：数据与样本工程
## 阶段 2：训练与集群
## 阶段 3：评测与验收
## 阶段 4：模型制品与发布
## 阶段 5：推理与服务化
## 阶段 6：观测、容量、成本与治理
## 阶段 7：RAG / Agent / 应用平台
## SRE 在整个生命周期中的职责
## 常见组织误区
## 扩展阅读
```

The “系统全景” section must include one ASCII lifecycle diagram.

- [ ] **Step 2: Validate the lifecycle overview is topic-focused**

Run: `rg -n "SRE 在整个生命周期中的职责|ASCII|扩展阅读" docs/llm-sre/10-llm-lifecycle-overview.md`
Expected: All three section markers are present and correctly named.

- [ ] **Step 3: Write the training infrastructure tutorial**

Write `docs/llm-sre/12-training-infrastructure-and-gpu-clusters.md` with these sections:

```md
# 训练基础设施与 GPU 集群

## 这篇文档解决什么问题
## 系统全景
## GPU 节点、拓扑与互联
## 驱动、CUDA、NCCL 与容器环境
## 调度体系：Kubernetes vs Slurm
## 存储、checkpoint 与数据通道
## 资源隔离与多租户
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

Add one comparison table for `Kubernetes vs Slurm` and one fault table for `故障现象 / 优先检查项 / 常见根因`.

- [ ] **Step 4: Write the distributed training tutorial**

Write `docs/llm-sre/13-distributed-training-and-fault-tolerance.md` with these sections:

```md
# 分布式训练与容错

## 这篇文档解决什么问题
## 系统全景
## DDP、FSDP、ZeRO、TP、PP、EP 的工程影响
## rank 拓扑与作业编排
## checkpoint / resume / 断点续训
## Spot / preemptible 与容错策略
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

The “典型故障与排查路径” section must explicitly cover `NCCL hang`, `checkpoint 过慢`, and `节点中途被驱逐`.

- [ ] **Step 5: Review the three training docs side-by-side**

Run: `sed -n '1,120p' docs/llm-sre/10-llm-lifecycle-overview.md && sed -n '1,120p' docs/llm-sre/12-training-infrastructure-and-gpu-clusters.md && sed -n '1,120p' docs/llm-sre/13-distributed-training-and-fault-tolerance.md`
Expected: Shared structure is consistent, but each file has a distinct scope and does not duplicate the others.

- [ ] **Step 6: Commit**

```bash
git add docs/llm-sre/10-llm-lifecycle-overview.md docs/llm-sre/12-training-infrastructure-and-gpu-clusters.md docs/llm-sre/13-distributed-training-and-fault-tolerance.md
git commit -m "docs: add llm sre lifecycle and training tutorials"
```

## Task 3: Write Inference Architecture And Performance Tutorials

**Files:**
- Create: `docs/llm-sre/16-inference-engines-and-serving-architecture.md`
- Create: `docs/llm-sre/17-inference-performance-engineering.md`
- Create: `docs/llm-sre/18-inference-observability-and-slo.md`

- [ ] **Step 1: Write the inference engine selection tutorial**

Write `docs/llm-sre/16-inference-engines-and-serving-architecture.md` with this outline:

```md
# 推理引擎与服务架构

## 这篇文档解决什么问题
## 系统全景
## 引擎对比：vLLM / SGLang / TGI / Triton / TensorRT-LLM
## API 网关、鉴权、路由与多租户
## 单模型、多模型与多 LoRA 部署模式
## 冷启动、模型加载与预热
## 关键指标与告警
## 设计权衡
## 实践建议
## 扩展阅读
```

The engine comparison must include one table with columns `引擎`, `优势`, `风险`, `适用场景`.

- [ ] **Step 2: Write the performance engineering tutorial**

Write `docs/llm-sre/17-inference-performance-engineering.md` with this outline:

```md
# 推理性能工程

## 这篇文档解决什么问题
## 系统全景
## Prefill 与 Decode 的资源特征
## KV Cache、paged attention、continuous batching
## 量化、显存与吞吐
## speculative decoding、PD 分离、prefix cache
## 多 LoRA 与多模型复用
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

This file must contain one “优化手段 / 收益 / 代价 / 何时不该用” table.

- [ ] **Step 3: Write the observability and SLO tutorial**

Write `docs/llm-sre/18-inference-observability-and-slo.md` with this outline:

```md
# 推理可观测性与 SLO

## 这篇文档解决什么问题
## 系统全景
## 核心指标：TTFT、TPOT、tokens/s、queue time
## 资源指标：GPU、显存、CPU、缓存
## 请求级 tracing 与质量信号
## 告警设计与错误预算
## 仪表盘建议
## 典型故障与排查路径
## 实践建议
## 扩展阅读
```

The file must include one Prometheus-style alert table with columns `告警名`, `条件`, `影响`, `处理动作`.

- [ ] **Step 4: Validate inference docs for key terminology consistency**

Run: `rg -n "TTFT|TPOT|KV Cache|continuous batching|PD 分离|speculative decoding" docs/llm-sre/16-inference-engines-and-serving-architecture.md docs/llm-sre/17-inference-performance-engineering.md docs/llm-sre/18-inference-observability-and-slo.md`
Expected: Terms appear in the correct files and are spelled consistently across all three.

- [ ] **Step 5: Commit**

```bash
git add docs/llm-sre/16-inference-engines-and-serving-architecture.md docs/llm-sre/17-inference-performance-engineering.md docs/llm-sre/18-inference-observability-and-slo.md
git commit -m "docs: add llm sre inference tutorials"
```

## Task 4: Write Reliability, Application Platform, And Governance Tutorials

**Files:**
- Create: `docs/llm-sre/19-reliability-scaling-and-multi-region.md`
- Create: `docs/llm-sre/20-rag-agent-and-application-platform.md`
- Create: `docs/llm-sre/21-security-compliance-and-governance.md`
- Create: `docs/llm-sre/22-frontier-topics.md`

- [ ] **Step 1: Write the reliability and scaling tutorial**

Write `docs/llm-sre/19-reliability-scaling-and-multi-region.md` with this outline:

```md
# 高可用、扩缩容与多地域

## 这篇文档解决什么问题
## 系统全景
## 多副本、多可用区、多地域部署
## 扩缩容：HPA、KEDA、自定义指标
## 灰度、shadow traffic、蓝绿与回滚
## fallback、熔断、限流、降级
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

- [ ] **Step 2: Write the RAG and agent platform tutorial**

Write `docs/llm-sre/20-rag-agent-and-application-platform.md` with this outline:

```md
# RAG、Agent 与应用平台

## 这篇文档解决什么问题
## 系统全景
## 文档摄取、切分、向量化、索引与检索
## embedding 服务与向量数据库运维
## reranker、上下文拼接与生成链路
## agent runtime、tool calling、memory、session state
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

Include one table comparing `pgvector`, `Milvus`, and `Qdrant`.

- [ ] **Step 3: Write the security and governance tutorial**

Write `docs/llm-sre/21-security-compliance-and-governance.md` with this outline:

```md
# 安全、合规与治理

## 这篇文档解决什么问题
## 系统全景
## 数据与模型资产访问控制
## Prompt 注入、越权调用与内容安全
## 密钥、审计、PII 与合规
## 多租户隔离与成本归因
## 关键指标与告警
## 典型故障与排查路径
## 设计权衡
## 实践建议
## 扩展阅读
```

- [ ] **Step 4: Write the frontier topics guide**

Write `docs/llm-sre/22-frontier-topics.md` with one repeated subsection template per topic:

```md
## [主题名]

### 这是什么
### 为什么重要
### 对 SRE / 平台工程的影响
### 应该观察哪些指标和信号
### 适用边界
```

Cover these topics in this exact order:

1. MoE serving
2. ultra-long context
3. prefill-decode disaggregation
4. SGLang / structured generation runtime
5. FP8 / INT4
6. inference cache hierarchy
7. agent runtime
8. synthetic data / automated eval
9. model routing / small-large cascade

- [ ] **Step 5: Validate the four docs for boundary separation**

Run: `rg -n "^## " docs/llm-sre/19-reliability-scaling-and-multi-region.md docs/llm-sre/20-rag-agent-and-application-platform.md docs/llm-sre/21-security-compliance-and-governance.md docs/llm-sre/22-frontier-topics.md`
Expected: Each file has a complete section structure and topic boundaries are visibly different.

- [ ] **Step 6: Commit**

```bash
git add docs/llm-sre/19-reliability-scaling-and-multi-region.md docs/llm-sre/20-rag-agent-and-application-platform.md docs/llm-sre/21-security-compliance-and-governance.md docs/llm-sre/22-frontier-topics.md
git commit -m "docs: add llm sre reliability and governance tutorials"
```

## Task 5: Write Operational Handbook Docs

**Files:**
- Create: `docs/llm-sre/30-production-readiness-checklist.md`
- Create: `docs/llm-sre/31-incident-runbook.md`
- Create: `docs/llm-sre/32-capacity-planning-cheatsheet.md`

- [ ] **Step 1: Write the production readiness checklist**

Write `docs/llm-sre/30-production-readiness-checklist.md` with these sections:

```md
# LLM 平台上线检查清单

## 适用场景
## 训练平台检查项
## 推理平台检查项
## RAG / Agent 平台检查项
## 灰度与回滚检查项
## 安全与审计检查项
## 演练与交接检查项
```

Use markdown checkboxes throughout the body.

- [ ] **Step 2: Write the incident runbook**

Write `docs/llm-sre/31-incident-runbook.md` with one subsection per incident:

```md
## GPU OOM
### 症状
### 前置检查
### 止血动作
### 根因定位
### 后续改进

## TTFT 飙升
...
```

Include at least these incidents:

1. GPU OOM
2. 模型加载失败
3. TTFT 飙升
4. tokens/s 下降
5. NCCL hang
6. 向量检索超时
7. 模型质量突然回退

- [ ] **Step 3: Write the capacity planning cheatsheet**

Write `docs/llm-sre/32-capacity-planning-cheatsheet.md` with these sections:

```md
# LLM 平台容量规划速查表

## 适用场景
## 推理容量估算
## 训练容量估算
## KV Cache 与上下文长度估算
## 压测口径
## 扩容决策
## 常见误判
```

Include at least one simple formula block for each of `推理容量估算`, `训练容量估算`, and `KV Cache`.

- [ ] **Step 4: Validate operational docs are action-oriented**

Run: `rg -n "适用场景|前置检查|止血动作|扩容决策|检查项" docs/llm-sre/30-production-readiness-checklist.md docs/llm-sre/31-incident-runbook.md docs/llm-sre/32-capacity-planning-cheatsheet.md`
Expected: All runbook-oriented markers exist and the docs read like operational material rather than tutorials.

- [ ] **Step 5: Commit**

```bash
git add docs/llm-sre/30-production-readiness-checklist.md docs/llm-sre/31-incident-runbook.md docs/llm-sre/32-capacity-planning-cheatsheet.md
git commit -m "docs: add llm sre operational handbooks"
```

## Task 6: Link Topic Into Existing Docs Indexes

**Files:**
- Modify: `docs/INDEX.md`
- Modify: `docs/00-overview.md`

- [ ] **Step 1: Add the topic to the main docs index**

Insert a new section near the LLMOps area in `docs/INDEX.md`:

```md
## 🤖 LLM SRE 专题

| 文档 | 说明 |
|------|------|
| [README](llm-sre/README.md) | 专题入口与阅读顺序 |
| [Roadmap](llm-sre/01-roadmap.md) | 学习路线图 |
| [Glossary](llm-sre/02-glossary.md) | 术语表 |
| [Lifecycle](llm-sre/10-llm-lifecycle-overview.md) | 生命周期总览 |
| [Training](llm-sre/12-training-infrastructure-and-gpu-clusters.md) | 训练基础设施 |
| [Inference](llm-sre/16-inference-engines-and-serving-architecture.md) | 推理引擎与架构 |
| [Runbooks](llm-sre/31-incident-runbook.md) | 事故运行手册 |
```

- [ ] **Step 2: Add a short topic pointer to the overview**

Add a short “专题延伸” subsection to `docs/00-overview.md` near the LLMOps phase:

```md
### 专题延伸：LLM SRE

如果你已经完成 Day 161-172，并希望从平台与运维视角系统梳理大模型训练、推理、RAG、安全与前沿方向，可继续阅读：

- `docs/llm-sre/README.md`
- `docs/llm-sre/10-llm-lifecycle-overview.md`
- `docs/llm-sre/31-incident-runbook.md`
```

- [ ] **Step 3: Validate the new links resolve cleanly**

Run: `rg -n "llm-sre/" docs/INDEX.md docs/00-overview.md`
Expected: Both files contain the new section and all links point to the new topic directory.

- [ ] **Step 4: Commit**

```bash
git add docs/INDEX.md docs/00-overview.md
git commit -m "docs: link llm sre topic from main indexes"
```

## Task 7: Perform Final Quality Review

**Files:**
- Review only: `docs/llm-sre/*.md`
- Review only: `docs/INDEX.md`
- Review only: `docs/00-overview.md`

- [ ] **Step 1: Scan for placeholders and empty headings**

Run: `rg -n "TODO|TBD|占位|待补|待定|^##$|^###$" docs/llm-sre docs/INDEX.md docs/00-overview.md`
Expected: No matches.

- [ ] **Step 2: Scan for accidental topic drift from old day docs**

Run: `rg -n "systemd|LAMP|Apache|journalctl" docs/llm-sre`
Expected: No irrelevant legacy topics appear unless explicitly used as contrast examples in one sentence.

- [ ] **Step 3: Review file inventory against the approved spec**

Run: `rg --files docs/llm-sre | sort`
Expected: The created files match the first-version scope from `docs/superpowers/specs/2026-05-03-llm-sre-learning-materials-design.md`.

- [ ] **Step 4: Manually review internal consistency**

Read these files in order and verify naming consistency:

```bash
sed -n '1,120p' docs/llm-sre/README.md
sed -n '1,160p' docs/llm-sre/01-roadmap.md
sed -n '1,200p' docs/llm-sre/02-glossary.md
sed -n '1,220p' docs/llm-sre/18-inference-observability-and-slo.md
sed -n '1,220p' docs/llm-sre/31-incident-runbook.md
```

Expected: Terms such as `TTFT`, `TPOT`, `KV Cache`, `PD 分离`, and `shadow traffic` are used consistently.

- [ ] **Step 5: Review the final git diff**

Run: `git diff --stat HEAD~6..HEAD`
Expected: The diff shows only the intended new topic files and index updates.

- [ ] **Step 6: Commit final polish if needed**

```bash
git add docs/llm-sre docs/INDEX.md docs/00-overview.md
git commit -m "docs: polish llm sre topic consistency"
```

Only create this commit if the review in Steps 1-5 required actual content changes.

## Self-Review

### Spec coverage

The approved spec requires:

1. A standalone `docs/llm-sre/` topic directory.
2. Three-layer information architecture.
3. Navigation docs.
4. First-version lifecycle, training, inference, reliability, RAG, governance, frontier, and operations docs.
5. Links back into repository-level indexes.

This plan covers those requirements in Tasks 1-6. No spec section is left without a corresponding task.

### Placeholder scan

This plan contains no `TODO`, `TBD`, “implement later”, or undefined “write tests for the above” placeholders. Every task includes exact file paths and explicit validation commands.

### Naming consistency

The file names used in tasks match the approved spec:

- `10-llm-lifecycle-overview.md`
- `12-training-infrastructure-and-gpu-clusters.md`
- `13-distributed-training-and-fault-tolerance.md`
- `16-inference-engines-and-serving-architecture.md`
- `17-inference-performance-engineering.md`
- `18-inference-observability-and-slo.md`
- `19-reliability-scaling-and-multi-region.md`
- `20-rag-agent-and-application-platform.md`
- `21-security-compliance-and-governance.md`
- `22-frontier-topics.md`
- `30-production-readiness-checklist.md`
- `31-incident-runbook.md`
- `32-capacity-planning-cheatsheet.md`

No later task introduces a conflicting file name or conflicting term spelling.
