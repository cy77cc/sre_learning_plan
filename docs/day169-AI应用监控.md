# Day 169: AI 应用监控

> 阶段七：AI 基础设施与 LLMOps | Week 25 | Day 2

## 今日学习目标

1. 掌握 Prompt 版本管理（追踪、A/B 测试、Prompt Registry）
2. 学会输出质量监控（幻觉检测、相关性评分、毒性检查）
3. 理解 Token 成本追踪与预算管理（按模型/端点/用户归因）
4. 掌握模型延迟监控（TTFT、TPOT、端到端延迟百分位）
5. 学会构建用户反馈闭环（点赞/点踩、人工评估流水线）
6. 理解模型漂移检测与 Prompt 迭代的 A/B 测试框架

---

## 核心知识点

### 1. AI 应用监控全景

#### 1.1 监控体系分层

```
┌──────────────────────────────────────────────────────────────────┐
│                    AI 应用监控体系分层                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  层级 1: 业务监控                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  用户满意度        回答质量评分        任务完成率            │ │
│  │  用户留存率        点赞/点踩比率       人工评估通过率        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  层级 2: 模型质量监控                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  幻觉检测率        回答相关性          毒性检测             │ │
│  │  Prompt 版本对比   模型漂移检测        输出一致性           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  层级 3: 性能监控                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  TTFT (首 Token 延迟)          TPOT (每 Token 延迟)       │ │
│  │  端到端延迟 P50/P95/P99        QPS / 并发数                │ │
│  │  请求排队时间                   超时率                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  层级 4: 成本监控                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Token 消耗量       按模型/用户/端点归因                    │ │
│  │  每千 Token 成本    预算告警        成本趋势                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  层级 5: 基础设施监控                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  GPU 利用率/温度    服务可用性       错误率                 │ │
│  │  Pod 状态           网络延迟         存储使用               │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2. Prompt 版本管理

#### 2.1 Prompt Registry 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Prompt Registry 架构                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Prompt Registry                         │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  Prompt: customer-support-v1                         │ │ │
│  │  │  ├── Version 1.0 (2026-01-15) - 初始版本             │ │ │
│  │  │  ├── Version 1.1 (2026-02-01) - 优化语气             │ │ │
│  │  │  ├── Version 1.2 (2026-03-10) - 添加约束             │ │ │
│  │  │  └── Version 2.0 (2026-04-01) - 重构结构             │ │ │
│  │  │                                                      │ │ │
│  │  │  当前生产版本: 1.2                                    │ │ │
│  │  │  A/B 测试: 1.2 (90%) vs 2.0 (10%)                   │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  Prompt: code-review-v1                              │ │ │
│  │  │  ├── Version 1.0 (2026-02-20)                        │ │ │
│  │  │  └── Version 1.1 (2026-04-15) - 添加安全检查         │ │ │
│  │  │                                                      │ │ │
│  │  │  当前生产版本: 1.1                                    │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  存储: PostgreSQL / Git (版本控制) / S3 (模板文件)        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    版本元数据                               │ │
│  │  {                                                          │ │
│  │    "prompt_id": "customer-support",                        │ │
│  │    "version": "1.2",                                       │ │
│  │    "template": "你是客服助手...",                           │ │
│  │    "model": "gpt-4o",                                      │ │
│  │    "parameters": {"temperature": 0.7, "max_tokens": 500}, │ │
│  │    "created_at": "2026-03-10T10:00:00Z",                  │ │
│  │    "created_by": "team-ai",                                │ │
│  │    "changelog": "添加回答长度约束",                        │ │
│  │    "metrics": {                                            │ │
│  │      "avg_quality_score": 4.2,                             │ │
│  │      "avg_latency_ms": 1200,                               │ │
│  │      "avg_tokens": 350,                                    │ │
│  │      "user_satisfaction": 0.85                             │ │
│  │    }                                                       │ │
│  │  }                                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.2 Prompt Registry 实现

```python
"""
prompt_registry.py
Prompt 版本管理系统
"""

import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime

@dataclass
class PromptVersion:
    """Prompt 版本"""
    prompt_id: str
    version: str
    template: str
    model: str
    parameters: dict
    created_at: str
    created_by: str
    changelog: str
    is_active: bool = False
    traffic_weight: float = 0.0  # A/B 测试流量权重
    metrics: dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                f"{self.prompt_id}:{self.version}:{self.template}".encode()
            ).hexdigest()[:12]

class PromptRegistry:
    """Prompt 注册中心"""

    def __init__(self, storage_backend=None):
        self.prompts: dict[str, list[PromptVersion]] = {}
        self.storage = storage_backend

    def register(self, prompt_id: str, version: str, template: str,
                 model: str, parameters: dict, created_by: str,
                 changelog: str = "") -> PromptVersion:
        """注册新版本"""
        pv = PromptVersion(
            prompt_id=prompt_id,
            version=version,
            template=template,
            model=model,
            parameters=parameters,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            changelog=changelog,
        )

        if prompt_id not in self.prompts:
            self.prompts[prompt_id] = []
        self.prompts[prompt_id].append(pv)

        return pv

    def get_active(self, prompt_id: str) -> Optional[PromptVersion]:
        """获取当前生产版本"""
        versions = self.prompts.get(prompt_id, [])
        for v in reversed(versions):
            if v.is_active:
                return v
        return versions[-1] if versions else None

    def get_version(self, prompt_id: str, version: str) -> Optional[PromptVersion]:
        """获取指定版本"""
        for v in self.prompts.get(prompt_id, []):
            if v.version == version:
                return v
        return None

    def promote(self, prompt_id: str, version: str):
        """提升为生产版本"""
        for v in self.prompts.get(prompt_id, []):
            v.is_active = (v.version == version)

    def rollback(self, prompt_id: str, target_version: str):
        """回滚到指定版本"""
        self.promote(prompt_id, target_version)

    def list_versions(self, prompt_id: str) -> list[dict]:
        """列出所有版本"""
        return [
            {
                "version": v.version,
                "created_at": v.created_at,
                "is_active": v.is_active,
                "traffic_weight": v.traffic_weight,
                "changelog": v.changelog,
                "metrics": v.metrics,
                "content_hash": v.content_hash,
            }
            for v in self.prompts.get(prompt_id, [])
        ]

    def setup_ab_test(self, prompt_id: str, versions_weights: dict[str, float]):
        """配置 A/B 测试"""
        total = sum(versions_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"权重之和必须为 1.0，当前为 {total}")

        for v in self.prompts.get(prompt_id, []):
            v.traffic_weight = versions_weights.get(v.version, 0.0)

    def select_version(self, prompt_id: str) -> PromptVersion:
        """根据 A/B 测试权重选择版本"""
        import random
        versions = self.prompts.get(prompt_id, [])
        active_versions = [v for v in versions if v.traffic_weight > 0]

        if not active_versions:
            return self.get_active(prompt_id)

        r = random.random()
        cumulative = 0.0
        for v in active_versions:
            cumulative += v.traffic_weight
            if r <= cumulative:
                return v

        return active_versions[-1]

    def update_metrics(self, prompt_id: str, version: str, metrics: dict):
        """更新版本指标"""
        pv = self.get_version(prompt_id, version)
        if pv:
            pv.metrics.update(metrics)
```

### 3. 输出质量监控

#### 3.1 质量监控体系

```
┌──────────────────────────────────────────────────────────────────┐
│                    输出质量监控体系                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 幻觉检测 (Hallucination Detection)                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  方法 1: 基于上下文验证                                    │ │
│  │  ├── 将回答拆分为独立声明                                  │ │
│  │  ├── 对每个声明检查是否有上下文支持                        │ │
│  │  └── 无支持的声明 = 潜在幻觉                               │ │
│  │                                                            │ │
│  │  方法 2: 基于 LLM 自评估                                   │ │
│  │  ├── 让 LLM 评估自己的回答                                │ │
│  │  ├── 对比不同温度下的回答一致性                            │ │
│  │  └── 交叉验证多个模型的回答                                │ │
│  │                                                            │ │
│  │  方法 3: 事实核查                                          │ │
│  │  ├── 将回答中的事实声明提取出来                            │ │
│  │  ├── 与知识库/搜索引擎交叉验证                             │ │
│  │  └── 无法验证的声明标记为风险                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  2. 相关性评分 (Relevance Scoring)                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ├── 问题-回答相关性: 回答是否解决了问题                   │ │
│  │  ├── 上下文-回答相关性: 回答是否基于检索内容               │ │
│  │  ├── 指令遵循度: 回答是否遵循了系统提示中的指令            │ │
│  │  └── 使用 LLM-as-Judge 自动评分                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  3. 毒性检查 (Toxicity Checking)                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ├── 仇恨言论检测                                          │ │
│  │  ├── 侮辱性语言检测                                        │ │
│  │  ├── 不当内容检测                                          │ │
│  │  ├── PII 泄露检测                                          │ │
│  │  └── 使用分类器 + 规则引擎组合                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  4. 输出格式验证                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ├── JSON 格式正确性                                       │ │
│  │  ├── Markdown 格式规范                                     │ │
│  │  ├── 代码语法正确性                                        │ │
│  │  └── 长度限制检查                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2 质量监控实现

```python
"""
quality_monitor.py
AI 输出质量监控系统
"""

import re
import json
from dataclasses import dataclass
from typing import Optional
from prometheus_client import Histogram, Counter, Gauge

# Prometheus 指标
HALLUCINATION_SCORE = Histogram(
    'ai_output_hallucination_score',
    '幻觉检测评分',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

RELEVANCE_SCORE = Histogram(
    'ai_output_relevance_score',
    '回答相关性评分',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

TOXICITY_DETECTIONS = Counter(
    'ai_output_toxicity_total',
    '毒性内容检测次数',
    ['type']
)

QUALITY_GATE_PASSED = Counter(
    'ai_quality_gate_passed_total',
    '质量门禁通过次数',
    ['gate_name']
)

QUALITY_GATE_FAILED = Counter(
    'ai_quality_gate_failed_total',
    '质量门禁失败次数',
    ['gate_name']
)

@dataclass
class QualityResult:
    """质量检测结果"""
    hallucination_score: float     # 0=无幻觉, 1=严重幻觉
    relevance_score: float         # 0=完全不相关, 1=完全相关
    toxicity_score: float          # 0=无毒性, 1=有毒性
    toxicity_types: list[str]      # 毒性类型列表
    format_valid: bool             # 格式是否有效
    quality_passed: bool           # 是否通过质量门禁
    details: dict = None

class QualityMonitor:
    """输出质量监控器"""

    def __init__(self, llm_client=None, toxicity_model=None):
        self.llm = llm_client
        self.toxicity_model = toxicity_model
        self.quality_thresholds = {
            "max_hallucination": 0.3,
            "min_relevance": 0.7,
            "max_toxicity": 0.1,
        }

    async def check_quality(self, query: str, context: str,
                            response: str, prompt_version: str = "") -> QualityResult:
        """综合质量检查"""
        # 幻觉检测
        hallucination = await self._check_hallucination(context, response)

        # 相关性评分
        relevance = await self._check_relevance(query, response)

        # 毒性检查
        toxicity_score, toxicity_types = await self._check_toxicity(response)

        # 格式验证
        format_valid = self._validate_format(response)

        # 质量门禁判定
        quality_passed = (
            hallucination <= self.quality_thresholds["max_hallucination"]
            and relevance >= self.quality_thresholds["min_relevance"]
            and toxicity_score <= self.quality_thresholds["max_toxicity"]
            and format_valid
        )

        result = QualityResult(
            hallucination_score=hallucination,
            relevance_score=relevance,
            toxicity_score=toxicity_score,
            toxicity_types=toxicity_types,
            format_valid=format_valid,
            quality_passed=quality_passed,
        )

        # 更新指标
        HALLUCINATION_SCORE.observe(hallucination)
        RELEVANCE_SCORE.observe(relevance)
        for t in toxicity_types:
            TOXICITY_DETECTIONS.labels(type=t).inc()
        if quality_passed:
            QUALITY_GATE_PASSED.labels(gate_name="overall").inc()
        else:
            QUALITY_GATE_FAILED.labels(gate_name="overall").inc()

        return result

    async def _check_hallucination(self, context: str, response: str) -> float:
        """幻觉检测"""
        if not self.llm:
            return 0.0

        prompt = f"""请评估以下回答是否存在幻觉（即回答中的信息无法从上下文中推导出来）。

上下文:
{context}

回答:
{response}

评分标准:
- 0.0: 完全基于上下文，没有幻觉
- 0.3: 有少量推断，但基本合理
- 0.5: 有一半信息无法从上下文推导
- 0.7: 大量信息无法验证
- 1.0: 完全是虚构的

请只返回一个 0 到 1 之间的数字。"""

        try:
            result = await self.llm.generate(prompt)
            return max(0, min(1, float(result.strip())))
        except:
            return 0.0

    async def _check_relevance(self, query: str, response: str) -> float:
        """相关性检查"""
        if not self.llm:
            return 1.0

        prompt = f"""请评估以下回答与问题的相关性。

问题: {query}

回答: {response}

评分标准:
- 1.0: 完美回答了问题
- 0.7: 基本回答了问题
- 0.5: 部分相关
- 0.3: 略微相关
- 0.0: 完全不相关

请只返回一个 0 到 1 之间的数字。"""

        try:
            result = await self.llm.generate(prompt)
            return max(0, min(1, float(result.strip())))
        except:
            return 1.0

    async def _check_toxicity(self, text: str) -> tuple[float, list[str]]:
        """毒性检查"""
        toxicity_types = []

        # 简单规则检查
        patterns = {
            "hate_speech": r"(仇恨|歧视|侮辱)",
            "profanity": r"(脏话|粗口)",
            "threat": r"(威胁|恐吓)",
        }

        for ttype, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                toxicity_types.append(ttype)

        # 使用分类器（如果可用）
        if self.toxicity_model:
            try:
                result = self.toxicity_model.predict(text)
                if result["toxic"] and result["score"] > 0.5:
                    toxicity_types.append("model_detected")
            except:
                pass

        score = min(1.0, len(toxicity_types) * 0.3)
        return score, toxicity_types

    def _validate_format(self, text: str) -> bool:
        """格式验证"""
        # 检查长度
        if len(text) < 10:
            return False
        if len(text) > 10000:
            return False

        # 如果期望 JSON
        if text.strip().startswith("{"):
            try:
                json.loads(text)
            except:
                return False

        return True
```

### 4. Token 成本追踪

#### 4.1 成本归因模型

```
┌──────────────────────────────────────────────────────────────────┐
│                    Token 成本归因模型                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  归因维度                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  按模型归因                                                │ │
│  │  ├── gpt-4o:       $0.005/1K input, $0.015/1K output     │ │
│  │  ├── gpt-4o-mini:  $0.00015/1K input, $0.0006/1K output  │ │
│  │  ├── claude-3.5:   $0.003/1K input, $0.015/1K output     │ │
│  │  └── 本地模型:     GPU 小时成本 / 吞吐量                  │ │
│  │                                                            │ │
│  │  按端点归因                                                │ │
│  │  ├── /v1/chat/completions   (对话)                        │ │
│  │  ├── /v1/embeddings         (向量化)                      │ │
│  │  ├── /v1/completions        (文本补全)                    │ │
│  │  └── /internal/rag          (RAG 检索+生成)               │ │
│  │                                                            │ │
│  │  按用户归因                                                │ │
│  │  ├── user_001: 本月消耗 50 万 tokens ($2.50)             │ │
│  │  ├── user_002: 本月消耗 200 万 tokens ($10.00)           │ │
│  │  ├── team_a:   本月消耗 1000 万 tokens ($50.00)          │ │
│  │  └── team_b:   本月消耗 500 万 tokens ($25.00)           │ │
│  │                                                            │ │
│  │  按功能归因                                                │ │
│  │  ├── 客服对话:  40% 成本                                  │ │
│  │  ├── 代码生成:  30% 成本                                  │ │
│  │  ├── 内容创作:  20% 成本                                  │ │
│  │  └── 其他:      10% 成本                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2 成本追踪实现

```python
"""
cost_tracker.py
Token 成本追踪与预算管理系统
"""

import time
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from prometheus_client import Counter, Gauge, Histogram

# Prometheus 指标
TOKEN_USAGE = Counter(
    'ai_token_usage_total',
    'Token 使用量',
    ['model', 'type', 'user', 'endpoint']
)

COST_TOTAL = Counter(
    'ai_cost_dollars_total',
    '累计成本（美元）',
    ['model', 'user', 'endpoint']
)

BUDGET_USAGE = Gauge(
    'ai_budget_usage_ratio',
    '预算使用比例',
    ['user', 'period']
)

BUDGET_ALERTS = Counter(
    'ai_budget_alerts_total',
    '预算告警次数',
    ['user', 'severity']
)

# 模型定价
MODEL_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "qwen-72b": {"input": 0.001, "output": 0.002},  # 自部署成本
}

@dataclass
class TokenUsage:
    """Token 使用记录"""
    model: str
    user_id: str
    endpoint: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: str
    prompt_version: str = ""
    metadata: dict = field(default_factory=dict)

@dataclass
class BudgetConfig:
    """预算配置"""
    user_id: str
    monthly_limit_usd: float
    daily_limit_usd: float
    alert_threshold_pct: float = 0.8  # 80% 时告警
    hard_limit: bool = False           # 是否硬限制

class CostTracker:
    """成本追踪器"""

    def __init__(self):
        self.usage_records: list[TokenUsage] = []
        self.budgets: dict[str, BudgetConfig] = {}
        self.monthly_costs: dict[str, float] = defaultdict(float)
        self.daily_costs: dict[str, float] = defaultdict(float)

    def calculate_cost(self, model: str, prompt_tokens: int,
                       completion_tokens: int) -> float:
        """计算成本"""
        pricing = MODEL_PRICING.get(model, {"input": 0.001, "output": 0.002})
        input_cost = prompt_tokens / 1000 * pricing["input"]
        output_cost = completion_tokens / 1000 * pricing["output"]
        return round(input_cost + output_cost, 6)

    def record_usage(self, model: str, user_id: str, endpoint: str,
                     prompt_tokens: int, completion_tokens: int,
                     prompt_version: str = "", **metadata) -> TokenUsage:
        """记录使用量"""
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        now = datetime.utcnow()

        usage = TokenUsage(
            model=model,
            user_id=user_id,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            timestamp=now.isoformat(),
            prompt_version=prompt_version,
            metadata=metadata,
        )

        self.usage_records.append(usage)

        # 更新累计
        month_key = now.strftime("%Y-%m")
        day_key = now.strftime("%Y-%m-%d")
        self.monthly_costs[f"{user_id}:{month_key}"] += cost
        self.daily_costs[f"{user_id}:{day_key}"] += cost

        # 更新 Prometheus 指标
        TOKEN_USAGE.labels(
            model=model, type="input", user=user_id, endpoint=endpoint
        ).inc(prompt_tokens)
        TOKEN_USAGE.labels(
            model=model, type="output", user=user_id, endpoint=endpoint
        ).inc(completion_tokens)
        COST_TOTAL.labels(model=model, user=user_id, endpoint=endpoint).inc(cost)

        # 检查预算
        self._check_budget(user_id, cost)

        return usage

    def _check_budget(self, user_id: str, new_cost: float):
        """检查预算"""
        budget = self.budgets.get(user_id)
        if not budget:
            return

        now = datetime.utcnow()
        month_key = now.strftime("%Y-%m")
        day_key = now.strftime("%Y-%m-%d")

        monthly_total = self.monthly_costs.get(f"{user_id}:{month_key}", 0)
        daily_total = self.daily_costs.get(f"{user_id}:{day_key}", 0)

        # 月度预算检查
        monthly_ratio = monthly_total / budget.monthly_limit_usd
        BUDGET_USAGE.labels(user=user_id, period="monthly").set(monthly_ratio)

        if monthly_ratio >= 1.0:
            BUDGET_ALERTS.labels(user=user_id, severity="exceeded").inc()
        elif monthly_ratio >= budget.alert_threshold_pct:
            BUDGET_ALERTS.labels(user=user_id, severity="warning").inc()

        # 日度预算检查
        daily_ratio = daily_total / budget.daily_limit_usd
        BUDGET_USAGE.labels(user=user_id, period="daily").set(daily_ratio)

        if daily_ratio >= 1.0:
            BUDGET_ALERTS.labels(user=user_id, severity="daily_exceeded").inc()

    def set_budget(self, user_id: str, monthly_limit: float,
                   daily_limit: float, alert_threshold: float = 0.8):
        """设置预算"""
        self.budgets[user_id] = BudgetConfig(
            user_id=user_id,
            monthly_limit_usd=monthly_limit,
            daily_limit_usd=daily_limit,
            alert_threshold_pct=alert_threshold,
        )

    def get_usage_report(self, user_id: str = None,
                         days: int = 30) -> dict:
        """获取使用报告"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        records = [
            r for r in self.usage_records
            if datetime.fromisoformat(r.timestamp) > cutoff
            and (user_id is None or r.user_id == user_id)
        ]

        if not records:
            return {"message": "No data"}

        # 按模型统计
        by_model = defaultdict(lambda: {"tokens": 0, "cost": 0, "count": 0})
        for r in records:
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["cost"] += r.cost_usd
            by_model[r.model]["count"] += 1

        # 按用户统计
        by_user = defaultdict(lambda: {"tokens": 0, "cost": 0, "count": 0})
        for r in records:
            by_user[r.user_id]["tokens"] += r.total_tokens
            by_user[r.user_id]["cost"] += r.cost_usd
            by_user[r.user_id]["count"] += 1

        # 按端点统计
        by_endpoint = defaultdict(lambda: {"tokens": 0, "cost": 0, "count": 0})
        for r in records:
            by_endpoint[r.endpoint]["tokens"] += r.total_tokens
            by_endpoint[r.endpoint]["cost"] += r.cost_usd
            by_endpoint[r.endpoint]["count"] += 1

        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.total_tokens for r in records)

        return {
            "period_days": days,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_requests": len(records),
            "avg_cost_per_request": round(total_cost / len(records), 6),
            "by_model": dict(by_model),
            "by_user": dict(by_user),
            "by_endpoint": dict(by_endpoint),
        }
```

### 5. 延迟监控

#### 5.1 延迟指标定义

```
┌──────────────────────────────────────────────────────────────────┐
│                    LLM 延迟指标定义                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TTFT (Time To First Token) - 首 Token 延迟                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  从请求发送到收到第一个生成的 Token 的时间                  │ │
│  │  包含: 网络传输 + 排队等待 + Prefill 计算                  │ │
│  │  SLO: P95 < 2s (交互场景), P95 < 5s (批处理场景)          │ │
│  │                                                            │ │
│  │  请求 ──→ [排队] ──→ [Prefill] ──→ 第一个 Token           │ │
│  │           0~500ms    100~2000ms                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  TPOT (Time Per Output Token) - 每 Token 延迟                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  生成每个 Token 的平均时间                                  │ │
│  │  包含: Decode 计算                                         │ │
│  │  SLO: P50 < 50ms, P95 < 100ms                             │ │
│  │                                                            │ │
│  │  Token1 ──Token2 ──Token3 ──...──TokenN                   │ │
│  │  |<-- TPOT -->|                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  E2E Latency - 端到端延迟                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  从请求发送到收到完整响应的时间                             │ │
│  │  = TTFT + (TPOT * output_tokens)                          │ │
│  │  SLO: P95 < 10s (短回答), P95 < 30s (长回答)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Inter-Token Latency (ITL) - Token 间延迟                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  连续两个 Token 之间的时间间隔                              │ │
│  │  反映流式输出的流畅度                                       │ │
│  │  SLO: P95 < 100ms                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  延迟分解示例 (70B 模型, A100):                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  网络传输:        5~20ms                                   │ │
│  │  排队等待:        0~500ms (取决于负载)                     │ │
│  │  Prefill:         100~2000ms (取决于输入长度)              │ │
│  │  TTFT:            105~2520ms                               │ │
│  │  Decode (每token): 20~50ms                                 │ │
│  │  生成 200 tokens:  4000~10000ms                            │ │
│  │  E2E:             4105~12520ms                              │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 延迟监控实现

```python
"""
latency_monitor.py
LLM 延迟监控系统
"""

import time
import asyncio
from dataclasses import dataclass
from typing import AsyncIterator
from prometheus_client import Histogram, Counter

# Prometheus 指标
TTFT_HISTOGRAM = Histogram(
    'llm_ttft_seconds',
    '首 Token 延迟',
    ['model', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

TPOT_HISTOGRAM = Histogram(
    'llm_tpot_seconds',
    '每 Token 延迟',
    ['model', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

E2E_HISTOGRAM = Histogram(
    'llm_e2e_latency_seconds',
    '端到端延迟',
    ['model', 'endpoint', 'status'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

ITL_HISTOGRAM = Histogram(
    'llm_inter_token_latency_seconds',
    'Token 间延迟',
    ['model'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

TOKEN_COUNT = Counter(
    'llm_tokens_generated_total',
    '生成的 Token 总数',
    ['model', 'type']
)

@dataclass
class LatencyMetrics:
    """延迟指标"""
    ttft_ms: float          # 首 Token 延迟
    tpot_ms: float          # 平均每 Token 延迟
    e2e_ms: float           # 端到端延迟
    itl_p50_ms: float       # Token 间延迟 P50
    itl_p95_ms: float       # Token 间延迟 P95
    prompt_tokens: int      # 输入 Token 数
    completion_tokens: int  # 输出 Token 数
    total_tokens: int       # 总 Token 数
    tokens_per_second: float  # 生成速度

class LatencyTracker:
    """延迟追踪器"""

    def __init__(self, model: str, endpoint: str = "/v1/chat/completions"):
        self.model = model
        self.endpoint = endpoint
        self.start_time: float = 0
        self.first_token_time: float = 0
        self.token_times: list[float] = []
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0

    def start(self, prompt_tokens: int = 0):
        """开始计时"""
        self.start_time = time.time()
        self.prompt_tokens = prompt_tokens
        self.token_times = []
        self.completion_tokens = 0

    def record_token(self):
        """记录一个 Token 生成"""
        now = time.time()
        if not self.token_times:
            self.first_token_time = now
        self.token_times.append(now)
        self.completion_tokens += 1

    def finish(self) -> LatencyMetrics:
        """完成并计算指标"""
        end_time = time.time()

        # TTFT
        ttft_ms = (self.first_token_time - self.start_time) * 1000 if self.token_times else 0

        # TPOT
        if len(self.token_times) > 1:
            decode_times = [
                (self.token_times[i] - self.token_times[i-1]) * 1000
                for i in range(1, len(self.token_times))
            ]
            tpot_ms = sum(decode_times) / len(decode_times)
            itl_p50_ms = sorted(decode_times)[len(decode_times) // 2]
            itl_p95_ms = sorted(decode_times)[int(len(decode_times) * 0.95)]
        else:
            tpot_ms = 0
            itl_p50_ms = 0
            itl_p95_ms = 0

        # E2E
        e2e_ms = (end_time - self.start_time) * 1000

        # TPS
        elapsed_s = end_time - self.first_token_time if self.token_times else 0
        tps = self.completion_tokens / elapsed_s if elapsed_s > 0 else 0

        metrics = LatencyMetrics(
            ttft_ms=round(ttft_ms, 2),
            tpot_ms=round(tpot_ms, 2),
            e2e_ms=round(e2e_ms, 2),
            itl_p50_ms=round(itl_p50_ms, 2),
            itl_p95_ms=round(itl_p95_ms, 2),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens,
            tokens_per_second=round(tps, 1),
        )

        # 更新 Prometheus
        TTFT_HISTOGRAM.labels(model=self.model, endpoint=self.endpoint).observe(ttft_ms / 1000)
        if tpot_ms > 0:
            TPOT_HISTOGRAM.labels(model=self.model, endpoint=self.endpoint).observe(tpot_ms / 1000)
        E2E_HISTOGRAM.labels(model=self.model, endpoint=self.endpoint, status="success").observe(e2e_ms / 1000)
        if itl_p50_ms > 0:
            ITL_HISTOGRAM.labels(model=self.model).observe(itl_p50_ms / 1000)
        TOKEN_COUNT.labels(model=self.model, type="prompt").inc(self.prompt_tokens)
        TOKEN_COUNT.labels(model=self.model, type="completion").inc(self.completion_tokens)

        return metrics

async def track_streaming_latency(model: str, stream: AsyncIterator,
                                   prompt_tokens: int = 0) -> LatencyMetrics:
    """追踪流式请求的延迟"""
    tracker = LatencyTracker(model)
    tracker.start(prompt_tokens)

    async for chunk in stream:
        tracker.record_token()
        yield chunk

    metrics = tracker.finish()
    return metrics
```

### 6. 用户反馈闭环

#### 6.1 反馈系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    用户反馈闭环系统                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    收集层                                   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │ │
│  │  │ 点赞    │ │ 点踩    │ │ 评论    │ │ 评分    │    │ │
│  │  │ 👍      │ │ 👎      │ │ 文字    │ │ 1~5星   │    │ │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘    │ │
│  └───────┼───────────┼───────────┼───────────┼───────────┘ │
│          │           │           │           │              │
│          └───────────┴─────┬─────┴───────────┘              │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    存储与分析                               │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  PostgreSQL / ClickHouse                             │ │ │
│  │  │  ├── 反馈记录 (user_id, query, response, rating)    │ │ │
│  │  │  ├── Prompt 版本关联                                 │ │ │
│  │  │  └── 时间戳、上下文信息                              │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  分析仪表板                                           │ │ │
│  │  │  ├── 整体满意度趋势                                   │ │ │
│  │  │  ├── 按 Prompt 版本对比                               │ │ │
│  │  │  ├── 负面反馈分类                                     │ │ │
│  │  │  └── 热门问题分析                                     │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    行动层                                   │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  人工评估流水线                                       │ │ │
│  │  │  ├── 抽样负面反馈进行人工审核                         │ │ │
│  │  │  ├── 标注幻觉/不相关/有害内容                        │ │ │
│  │  │  └── 生成改进数据集                                   │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  Prompt 迭代                                          │ │ │
│  │  │  ├── 基于负面反馈优化 Prompt                          │ │ │
│  │  │  ├── A/B 测试新版本                                   │ │ │
│  │  │  └── 确认改进后全量发布                               │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 6.2 反馈系统实现

```python
"""
feedback_system.py
用户反馈收集与分析系统
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
from prometheus_client import Counter as PromCounter, Gauge

FEEDBACK_RECEIVED = PromCounter(
    'ai_feedback_received_total',
    '收到的反馈数',
    ['type', 'rating']
)

SATISFACTION_SCORE = Gauge(
    'ai_user_satisfaction_score',
    '用户满意度评分',
    ['model', 'prompt_version']
)

@dataclass
class Feedback:
    """用户反馈"""
    feedback_id: str
    request_id: str
    user_id: str
    rating: int                 # 1-5 或 thumbs up/down
    feedback_type: str          # thumbs, stars, detailed
    comment: str = ""
    categories: list[str] = field(default_factory=list)  # 不满意的类别
    prompt_version: str = ""
    model: str = ""
    query: str = ""
    response: str = ""
    timestamp: str = ""

class FeedbackCollector:
    """反馈收集器"""

    def __init__(self, storage=None):
        self.feedbacks: list[Feedback] = []
        self.storage = storage

    def submit_feedback(self, request_id: str, user_id: str,
                        rating: int, feedback_type: str = "thumbs",
                        comment: str = "", categories: list[str] = None,
                        prompt_version: str = "", model: str = "",
                        query: str = "", response: str = "") -> Feedback:
        """提交反馈"""
        feedback = Feedback(
            feedback_id=f"fb_{int(time.time()*1000)}",
            request_id=request_id,
            user_id=user_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
            categories=categories or [],
            prompt_version=prompt_version,
            model=model,
            query=query,
            response=response,
            timestamp=datetime.utcnow().isoformat(),
        )

        self.feedbacks.append(feedback)

        # 更新指标
        rating_label = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
        FEEDBACK_RECEIVED.labels(type=feedback_type, rating=rating_label).inc()

        return feedback

    def get_satisfaction_rate(self, prompt_version: str = None,
                              days: int = 7) -> float:
        """计算满意度"""
        cutoff = datetime.utcnow().timestamp() - days * 86400
        recent = [
            f for f in self.feedbacks
            if datetime.fromisoformat(f.timestamp).timestamp() > cutoff
            and (prompt_version is None or f.prompt_version == prompt_version)
        ]

        if not recent:
            return 0.0

        positive = sum(1 for f in recent if f.rating >= 4)
        return round(positive / len(recent), 4)

    def get_negative_feedback_summary(self, days: int = 7) -> dict:
        """负面反馈汇总"""
        cutoff = datetime.utcnow().timestamp() - days * 86400
        negative = [
            f for f in self.feedbacks
            if datetime.fromisoformat(f.timestamp).timestamp() > cutoff
            and f.rating <= 2
        ]

        category_counts = Counter()
        for f in negative:
            for cat in f.categories:
                category_counts[cat] += 1

        return {
            "total_negative": len(negative),
            "satisfaction_rate": self.get_satisfaction_rate(days=days),
            "top_categories": category_counts.most_common(10),
            "sample_feedbacks": [
                {
                    "query": f.query[:100],
                    "rating": f.rating,
                    "comment": f.comment,
                    "categories": f.categories,
                }
                for f in negative[:20]
            ],
        }
```

### 7. 模型漂移检测

#### 7.1 漂移检测策略

```python
"""
drift_detector.py
模型漂移检测系统
"""

import numpy as np
from dataclasses import dataclass
from collections import deque
from scipy import stats

@dataclass
class DriftAlert:
    """漂移告警"""
    metric_name: str
    drift_type: str       # gradual, sudden
    severity: str         # warning, critical
    current_value: float
    baseline_value: float
    drift_magnitude: float
    timestamp: str

class DriftDetector:
    """模型漂移检测器"""

    def __init__(self, window_size: int = 1000, alert_threshold: float = 0.1):
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self.baselines: dict[str, dict] = {}
        self.windows: dict[str, deque] = {}

    def set_baseline(self, metric_name: str, values: list[float]):
        """设置基线（使用历史正常数据）"""
        self.baselines[metric_name] = {
            "mean": np.mean(values),
            "std": np.std(values),
            "median": np.median(values),
            "p25": np.percentile(values, 25),
            "p75": np.percentile(values, 75),
        }
        self.windows[metric_name] = deque(maxlen=self.window_size)

    def add_observation(self, metric_name: str, value: float) -> DriftAlert | None:
        """添加观测值并检测漂移"""
        if metric_name not in self.windows:
            self.windows[metric_name] = deque(maxlen=self.window_size)

        self.windows[metric_name].append(value)

        if metric_name not in self.baselines:
            return None

        # 至少需要 100 个样本
        if len(self.windows[metric_name]) < 100:
            return None

        baseline = self.baselines[metric_name]
        current_values = list(self.windows[metric_name])

        # KS 检验：检测分布变化
        ks_stat, p_value = stats.ks_2samp(
            np.random.normal(baseline["mean"], baseline["std"], 100),
            current_values[-100:]
        )

        # 均值偏移检测
        current_mean = np.mean(current_values[-100:])
        mean_shift = abs(current_mean - baseline["mean"]) / (baseline["std"] + 1e-8)

        if p_value < 0.01 or mean_shift > 3:
            severity = "critical" if mean_shift > 5 else "warning"
            return DriftAlert(
                metric_name=metric_name,
                drift_type="gradual" if mean_shift < 5 else "sudden",
                severity=severity,
                current_value=current_mean,
                baseline_value=baseline["mean"],
                drift_magnitude=round(mean_shift, 2),
                timestamp=datetime.utcnow().isoformat(),
            )

        return None

# 监控的关键指标
DRIFT_METRICS = [
    "response_quality_score",    # 回答质量
    "relevance_score",           # 相关性
    "hallucination_rate",        # 幻觉率
    "avg_response_length",       # 平均回答长度
    "user_satisfaction",         # 用户满意度
    "task_completion_rate",      # 任务完成率
]
```

### 8. A/B 测试框架

#### 8.1 A/B 测试实现

```python
"""
ab_testing.py
Prompt A/B 测试框架
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional
from scipy import stats
import numpy as np

@dataclass
class ABTestConfig:
    """A/B 测试配置"""
    test_id: str
    name: str
    variants: dict[str, float]   # variant_name -> traffic_weight
    metric: str                  # 主要评估指标
    min_sample_size: int = 100
    significance_level: float = 0.05
    start_time: str = ""
    end_time: str = ""
    status: str = "running"      # running, completed, stopped

@dataclass
class VariantResult:
    """变体结果"""
    variant_name: str
    sample_size: int
    metric_mean: float
    metric_std: float
    metric_values: list[float] = field(default_factory=list)

class ABTestFramework:
    """A/B 测试框架"""

    def __init__(self):
        self.tests: dict[str, ABTestConfig] = {}
        self.results: dict[str, dict[str, list[float]]] = {}  # test_id -> variant -> values

    def create_test(self, config: ABTestConfig):
        """创建 A/B 测试"""
        self.tests[config.test_id] = config
        self.results[config.test_id] = {v: [] for v in config.variants}
        config.start_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def assign_variant(self, test_id: str, user_id: str) -> str:
        """为用户分配变体（基于用户 ID 哈希，保证同一用户始终分到同一组）"""
        config = self.tests.get(test_id)
        if not config:
            return "control"

        hash_val = int(hashlib.md5(f"{test_id}:{user_id}".encode()).hexdigest(), 16)
        normalized = (hash_val % 10000) / 10000.0

        cumulative = 0.0
        for variant, weight in config.variants.items():
            cumulative += weight
            if normalized < cumulative:
                return variant

        return list(config.variants.keys())[-1]

    def record_result(self, test_id: str, variant: str, metric_value: float):
        """记录结果"""
        if test_id in self.results and variant in self.results[test_id]:
            self.results[test_id][variant].append(metric_value)

    def analyze_test(self, test_id: str) -> dict:
        """分析测试结果"""
        config = self.tests.get(test_id)
        if not config:
            return {"error": "Test not found"}

        test_results = self.results.get(test_id, {})
        variants = {}

        for variant_name, values in test_results.items():
            if len(values) < 10:
                variants[variant_name] = {"status": "insufficient_data", "n": len(values)}
                continue

            variants[variant_name] = VariantResult(
                variant_name=variant_name,
                sample_size=len(values),
                metric_mean=round(np.mean(values), 4),
                metric_std=round(np.std(values), 4),
            )

        # 统计显著性检验
        variant_names = list(test_results.keys())
        if len(variant_names) >= 2:
            control_values = test_results[variant_names[0]]
            treatment_values = test_results[variant_names[1]]

            if len(control_values) >= 10 and len(treatment_values) >= 10:
                t_stat, p_value = stats.ttest_ind(control_values, treatment_values)
                is_significant = p_value < config.significance_level
                lift = (np.mean(treatment_values) - np.mean(control_values)) / np.mean(control_values) * 100
            else:
                is_significant = False
                lift = 0.0
                p_value = 1.0
        else:
            is_significant = False
            lift = 0.0
            p_value = 1.0

        return {
            "test_id": test_id,
            "name": config.name,
            "status": config.status,
            "metric": config.metric,
            "variants": {k: {
                "sample_size": v.sample_size if isinstance(v, VariantResult) else v.get("n", 0),
                "mean": v.metric_mean if isinstance(v, VariantResult) else None,
                "std": v.metric_std if isinstance(v, VariantResult) else None,
            } for k, v in variants.items()},
            "statistical_test": {
                "p_value": round(p_value, 4),
                "is_significant": is_significant,
                "lift_pct": round(lift, 2),
                "recommendation": "可以发布" if is_significant and lift > 0 else "继续观察" if not is_significant else "不建议发布",
            },
        }
```

### 9. SRE 场景：Prompt 输出质量下降排查

```
┌──────────────────────────────────────────────────────────────────┐
│    SRE 场景：输出质量下降 → 对比 Prompt 版本 → 回滚              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  T0: 监控告警触发                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Alert: AI_Output_Quality_Degraded                         │ │
│  │  用户满意度: 4.2 → 3.5 (最近 1 小时)                      │ │
│  │  幻觉检测率: 5% → 18%                                     │ │
│  │  负面反馈数: +300%                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  T0+5min: 排查变更                                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  变更记录:                                                  │ │
│  │  ├── 30 分钟前: Prompt 版本从 v1.2 升级到 v2.0            │ │
│  │  ├── 15 分钟前: 新版本开始接收 20% 流量                    │ │
│  │  └── 5 分钟前: 质量指标开始下降                            │ │
│  │                                                            │ │
│  │  对比分析:                                                  │ │
│  │  ┌─────────────┬──────────────┬──────────────┐            │ │
│  │  │ 指标        │ v1.2 (旧)    │ v2.0 (新)    │            │ │
│  │  ├─────────────┼──────────────┼──────────────┤            │ │
│  │  │ 满意度      │ 4.2          │ 3.1          │            │ │
│  │  │ 幻觉率      │ 5%           │ 22%          │            │ │
│  │  │ 相关性      │ 0.88         │ 0.71         │            │ │
│  │  │ 平均延迟    │ 1200ms       │ 1800ms       │            │ │
│  │  └─────────────┴──────────────┴──────────────┘            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  T0+10min: 立即回滚                                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. 将 v2.0 流量权重设为 0%                               │ │
│  │  2. 将 v1.2 流量权重设为 100%                             │ │
│  │  3. 通知 Prompt 工程团队                                   │ │
│  │                                                            │ │
│  │  命令:                                                     │ │
│  │  prompt-registry rollback customer-support v1.2            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  T0+15min: 验证恢复                                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  满意度: 3.5 → 4.1 (回升中)                               │ │
│  │  幻觉率: 18% → 6% (恢复正常)                              │ │
│  │  服务恢复正常                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  T0+1h: 事后分析                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  根因: v2.0 的 Prompt 移除了"只基于上下文回答"的约束      │ │
│  │  改进:                                                      │ │
│  │  ├── 所有 Prompt 变更必须经过质量评估流水线                │ │
│  │  ├── 金丝雀发布比例从 20% 降至 5%                         │ │
│  │  ├── 添加自动回滚规则: 质量下降 >10% 自动回滚             │ │
│  │  └── 建立 Prompt 变更 review 流程                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 实战练习

### 练习 1: 搭建 Prompt Registry

**目标**: 实现一个简单的 Prompt 版本管理系统，支持注册、查询、回滚和 A/B 测试。

```python
# prompt_registry_demo.py
from prompt_registry import PromptRegistry

# 1. 初始化
registry = PromptRegistry()

# 2. 注册版本
registry.register(
    prompt_id="customer-support",
    version="1.0",
    template="你是客服助手。请基于以下信息回答用户问题：\n{context}\n\n用户问题：{query}",
    model="gpt-4o",
    parameters={"temperature": 0.7, "max_tokens": 500},
    created_by="team-ai",
    changelog="初始版本"
)

registry.register(
    prompt_id="customer-support",
    version="1.1",
    template="你是专业的客服助手。请严格基于以下信息回答，不要编造信息。\n{context}\n\n用户问题：{query}\n\n如果信息不足，请说「抱歉，我无法回答这个问题」。",
    model="gpt-4o",
    parameters={"temperature": 0.5, "max_tokens": 500},
    created_by="team-ai",
    changelog="添加反幻觉约束"
)

# 3. 设置生产版本
registry.promote("customer-support", "1.1")

# 4. 配置 A/B 测试
registry.register(
    prompt_id="customer-support",
    version="2.0",
    template="你是一个AI客服。请回答用户问题。\n上下文：{context}\n问题：{query}",
    model="gpt-4o-mini",
    parameters={"temperature": 0.3, "max_tokens": 300},
    created_by="team-ai",
    changelog="测试简化 Prompt"
)

registry.setup_ab_test("customer-support", {"1.1": 0.8, "2.0": 0.2})

# 5. 模拟流量分配
results = {"1.1": 0, "2.0": 0}
for i in range(1000):
    v = registry.select_version("customer-support")
    results[v.version] += 1

print(f"A/B 测试流量分配: {results}")

# 6. 回滚
registry.rollback("customer-support", "1.0")
print(f"回滚后版本: {registry.get_active('customer-support').version}")
```

### 练习 2: 实现质量监控流水线

**目标**: 构建一个完整的输出质量监控流水线，包含幻觉检测、相关性评分和质量门禁。

```bash
# 1. 部署监控组件
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: quality-monitor-config
  namespace: ai-monitoring
data:
  config.yaml: |
    quality_gates:
      max_hallucination: 0.3
      min_relevance: 0.7
      max_toxicity: 0.1
    
    alert_rules:
      - metric: hallucination_rate
        threshold: 0.15
        window: 10m
        severity: warning
      - metric: relevance_score
        threshold: 0.6
        window: 5m
        severity: critical
EOF

# 2. 测试质量检查
python3 -c "
from quality_monitor import QualityMonitor

monitor = QualityMonitor()

# 模拟质量检查
result = monitor._validate_format('这是一个正常的回答。')
print(f'格式验证: {result}')

result = monitor._validate_format('x')
print(f'短文本验证: {result}')
"
```

### 练习 3: 配置 Token 成本告警

**目标**: 实现 Token 成本追踪和预算告警系统。

```python
# cost_tracking_demo.py
from cost_tracker import CostTracker

# 1. 初始化
tracker = CostTracker()

# 2. 设置用户预算
tracker.set_budget(
    user_id="user_001",
    monthly_limit=50.0,   # $50/月
    daily_limit=5.0,      # $5/天
    alert_threshold=0.8   # 80% 时告警
)

# 3. 模拟请求
import random
models = ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet"]

for i in range(100):
    model = random.choice(models)
    usage = tracker.record_usage(
        model=model,
        user_id="user_001",
        endpoint="/v1/chat/completions",
        prompt_tokens=random.randint(100, 2000),
        completion_tokens=random.randint(50, 500),
        prompt_version="1.1",
    )

# 4. 查看报告
report = tracker.get_usage_report(user_id="user_001")
print(f"总成本: ${report['total_cost_usd']}")
print(f"总请求: {report['total_requests']}")
print(f"按模型: {report['by_model']}")
```

---

## 面试题精选

### 1. 如何管理 Prompt 的版本？

**参考答案**：

Prompt 版本管理需要以下能力：
1. **注册中心**：存储 Prompt 模板、参数、版本号、变更日志
2. **版本控制**：每个变更有唯一标识，支持回滚
3. **元数据追踪**：关联模型、温度等参数
4. **指标关联**：每个版本关联质量指标（满意度、幻觉率等）
5. **流量管理**：支持 A/B 测试的流量分割
6. **审计日志**：谁在什么时候修改了什么

### 2. 如何检测 LLM 输出中的幻觉？

**参考答案**：

幻觉检测方法：
1. **基于上下文验证**：将回答拆分为声明，逐个检查是否有上下文支持
2. **LLM 自评估**：让 LLM 评估自己的回答，对比多次生成的一致性
3. **事实核查**：将事实声明与知识库/搜索引擎交叉验证
4. **NLI 模型**：使用自然语言推理模型判断回答是否被上下文蕴含
5. **多模型交叉**：用不同模型回答同一问题，不一致处可能是幻觉

### 3. 如何追踪和控制 AI 应用的 Token 成本？

**参考答案**：

追踪维度：
- 按模型：不同模型定价不同
- 按用户/团队：责任归属
- 按功能端点：区分用途

控制手段：
1. 设置用户/团队级别的月度/日度预算
2. 预算达到 80% 时告警，100% 时限制
3. 使用 Prompt 压缩减少 Token 消耗
4. 选择合适大小的模型（能用小模型就不用大模型）
5. 实现语义缓存减少重复请求

### 4. TTFT 和 TPOT 分别代表什么？如何优化？

**参考答案**：

- **TTFT（Time To First Token）**：首 Token 延迟，反映用户等待感知
  - 优化：减小输入长度、使用 Speculative Decoding、增加 Prefill 并行度
- **TPOT（Time Per Output Token）**：每 Token 延迟，反映生成速度
  - 优化：使用更快的模型、量化推理、增大 Decode batch size

### 5. 如何实现 Prompt 的 A/B 测试？

**参考答案**：

1. **用户分组**：基于用户 ID 哈希保证一致性
2. **流量分配**：配置不同版本的流量权重
3. **指标收集**：为每个版本收集质量指标（满意度、幻觉率、延迟）
4. **统计检验**：使用 t 检验判断差异是否显著（p < 0.05）
5. **决策**：显著优于对照组则发布，否则继续观察

### 6. 什么是模型漂移？如何检测？

**参考答案**：

模型漂移指模型性能随时间逐渐下降，原因包括：
- 输入数据分布变化
- 用户行为模式变化
- 外部知识更新

检测方法：
1. **统计检验**：KS 检验检测指标分布变化
2. **滑动窗口**：对比近期指标与历史基线
3. **用户反馈**：监控满意度趋势
4. **质量评估**：定期用标注数据集评估

### 7. 如何构建用户反馈闭环？

**参考答案**：

1. **收集**：点赞/点踩、星级评分、文字评论
2. **存储**：关联请求 ID、Prompt 版本、模型信息
3. **分析**：负面反馈分类（幻觉、不相关、有害）
4. **行动**：
   - 负面反馈样本进行人工审核
   - 生成 Prompt 改进数据集
   - 迭代 Prompt 并 A/B 测试
5. **验证**：确认新版本满意度提升

### 8. 如何设计 AI 应用的告警体系？

**参考答案**：

分级告警：
- **P0（立即响应）**：服务不可用、错误率 >10%、毒性输出
- **P1（15 分钟）**：质量下降 >20%、TTFT P95 >5s、预算超限
- **P2（1 小时）**：质量下降 >10%、用户满意度下降
- **P3（工作日）**：成本趋势异常、模型漂移

### 9. LLM-as-Judge 是什么？有什么局限性？

**参考答案**：

LLM-as-Judge 是使用 LLM 来评估 LLM 输出质量的方法。

优点：自动化、可扩展、成本低
局限性：
1. 评估模型自身的偏见
2. 对微妙的质量差异不敏感
3. 可能被冗长但低质量的回答迷惑
4. 需要与人工评估对齐验证

### 10. 如何降低 AI 应用的 Token 成本？

**参考答案**：

1. **Prompt 优化**：压缩系统提示，去除冗余指令
2. **模型选择**：简单任务用小模型，复杂任务用大模型
3. **语义缓存**：相似查询复用结果
4. **批量处理**：非实时请求合并处理
5. **输出限制**：设置合理的 max_tokens
6. **RAG 优化**：减少检索文档数量，只传最相关的

---

## 延伸阅读

- [Langfuse - Open Source LLM Observability](https://langfuse.com/) - LLM 可观测性平台
- [LangSmith](https://smith.langchain.com/) - LangChain 监控平台
- [RAGAS Evaluation](https://docs.ragas.io/) - RAG 评估框架
- [OpenAI Token Pricing](https://openai.com/pricing) - Token 定价
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - Prompt 工程指南
- [Prometheus Best Practices](https://prometheus.io/docs/practices/) - Prometheus 最佳实践
- [A/B Testing Statistics](https://www.evanmiller.org/ab-testing/) - A/B 测试统计方法

---

## 今日自检清单

- [ ] 理解 Prompt 版本管理的核心概念（Registry、Version、Rollback）
- [ ] 能实现幻觉检测、相关性评分、毒性检查
- [ ] 掌握 Token 成本追踪和预算管理
- [ ] 理解 TTFT、TPOT、E2E Latency 的含义和优化方向
- [ ] 能构建用户反馈收集和分析系统
- [ ] 理解模型漂移检测的方法（KS 检验、滑动窗口）
- [ ] 能实现 Prompt A/B 测试框架
- [ ] 能设计 AI 应用的告警体系
- [ ] 理解质量门禁的配置和执行
- [ ] 完成了所有 3 个实战练习

---

*由 SRE 学习计划生成 | 2026-05-03*
