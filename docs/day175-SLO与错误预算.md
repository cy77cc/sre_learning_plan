# Day 175: SLO 与错误预算

> 📅 日期：2026-05-03
> 📖 学习主题：SLO 与错误预算 — SLO 定义方法、SLI 选择、错误预算计算、预算消耗策略、联系发布速度、多窗口多燃烧率告警、SLO 平台
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 173-174（On-Call 实践、事故管理）

---

## 🎯 学习目标

完成 Day 175 的学习后，你应该掌握：

- 理解 SLI、SLO、SLA 三者的关系和区别
- 为服务选择合适的 SLI 指标并定义 SLO
- 计算错误预算及其消耗速率
- 建立错误预算与发布速度的关联策略
- 配置多窗口多燃烧率告警
- 了解主流 SLO 平台（Sloth、OpenSLO、Google Cloud SLO）

---

## 📖 核心知识点

### 1. SLI / SLO / SLA 基础概念

#### 1.1 概念关系图

```
┌─────────────────────────────────────────────────────────┐
│              SLI / SLO / SLA 关系                        │
│                                                         │
│  SLI (Service Level Indicator)                          │
│  ┌───────────────────────────────────────┐              │
│  │  服务级别指标                          │              │
│  │  衡量服务行为的量化指标                 │              │
│  │  例：请求成功率、延迟 P99、吞吐量       │              │
│  └───────────────────┬───────────────────┘              │
│                      │                                  │
│                      │ 基于 SLI 设定目标                 │
│                      ▼                                  │
│  SLO (Service Level Objective)                          │
│  ┌───────────────────────────────────────┐              │
│  │  服务级别目标                          │              │
│  │  SLI 的目标值（内部承诺）              │              │
│  │  例：99.9% 可用性、P99 < 200ms        │              │
│  └───────────────────┬───────────────────┘              │
│                      │                                  │
│                      │ SLO 是 SLA 的内部目标             │
│                      ▼                                  │
│  SLA (Service Level Agreement)                          │
│  ┌───────────────────────────────────────┐              │
│  │  服务级别协议                          │              │
│  │  与客户的正式合同（有法律约束力）       │              │
│  │  例：99.9% 可用性，违约赔偿 10%        │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  关键理解：                                              │
│  • SLI 是"测量什么"                                      │
│  • SLO 是"目标是什么"                                    │
│  • SLA 是"承诺是什么（有后果）"                          │
│  • SLO 应比 SLA 更严格（留有缓冲）                       │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 Google SRE 对 SLO 的定义

Google SRE Book 第 4 章明确指出：

> "An SLO is a target value or range of values for a service level that is measured by an SLI."

> "Choosing an appropriate SLO is a business decision. The SLO should be set at a level that, if not met, will result in customer dissatisfaction."

SLO 的核心价值：

```
┌─────────────────────────────────────────────────────────┐
│                 SLO 的核心价值                            │
│                                                         │
│  1. 共同语言                                             │
│     • 开发和运维对"可靠性"有统一定义                      │
│     • 减少主观争论，基于数据决策                          │
│                                                         │
│  2. 决策依据                                             │
│     • 错误预算充足 → 可以大胆发布                        │
│     • 错误预算不足 → 冻结发布，专注稳定性                 │
│                                                         │
│  3. 客户预期管理                                         │
│     • 明确承诺的服务质量                                 │
│     • 避免过度承诺或过度工程                              │
│                                                         │
│  4. 绩效衡量                                             │
│     • 量化评估服务可靠性                                 │
│     • 指导资源分配和优先级排序                            │
└─────────────────────────────────────────────────────────┘
```

### 2. SLI 选择方法

#### 2.1 常见 SLI 类型

```
┌─────────────────────────────────────────────────────────┐
│                   SLI 类型分类                            │
│                                                         │
│  可用性 SLI                                              │
│  ┌───────────────────────────────────────┐              │
│  │ 成功率 = 成功请求数 / 总请求数         │              │
│  │ 可用时间 = 正常运行时间 / 总时间       │              │
│  │ 健康检查通过率 = 通过次数 / 检查次数   │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  延迟 SLI                                                │
│  ┌───────────────────────────────────────┐              │
│  │ P50 延迟 = 中位数延迟                  │              │
│  │ P90 延迟 = 90分位延迟                  │              │
│  │ P99 延迟 = 99分位延迟                  │              │
│  │ P999 延迟 = 99.9分位延迟               │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  吞吐量 SLI                                              │
│  ┌───────────────────────────────────────┐              │
│  │ QPS = 每秒查询数                       │              │
│  │ 成功事务数 / 时间窗口                   │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  正确性 SLI                                              │
│  ┌───────────────────────────────────────┐              │
│  │ 数据一致性 = 一致记录数 / 总记录数      │              │
│  │ 计算准确性 = 正确结果数 / 总计算数      │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  耐久性 SLI（存储类）                                    │
│  ┌───────────────────────────────────────┐              │
│  │ 数据存活率 = 存活对象数 / 写入对象数    │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 2.2 SLI 选择原则

Google SRE Book 推荐的 SLI 选择原则：

```
┌─────────────────────────────────────────────────────────┐
│                SLI 选择原则                               │
│                                                         │
│  1. 用户视角优先                                         │
│     ┌───────────────────────────────────────┐           │
│     │ 用户关心什么？  →  SLI 就测量什么       │           │
│     │ • 用户关心"能不能用" → 可用性 SLI       │           │
│     │ • 用户关心"快不快"  → 延迟 SLI         │           │
│     │ • 用户关心"对不对"  → 正确性 SLI       │           │
│     └───────────────────────────────────────┘           │
│                                                         │
│  2. 可测量                                               │
│     • SLI 必须能够被准确测量                             │
│     • 数据来源可靠且稳定                                 │
│     • 测量成本可接受                                     │
│                                                         │
│  3. 可行动                                               │
│     • SLI 变化时，团队知道如何应对                       │
│     • 与服务行为直接相关                                 │
│                                                         │
│  4. 不要太多                                             │
│     • 每个服务 3-5 个 SLI 即可                          │
│     • 关注核心用户体验路径                               │
└─────────────────────────────────────────────────────────┘
```

#### 2.3 不同类型服务的 SLI 示例

**Web 服务（API）**：

```yaml
# Web 服务 SLI 示例
sli_definitions:
  availability:
    name: "API 成功率"
    description: "HTTP 2xx/3xx 响应占总响应的比例"
    metric: |
      sum(rate(http_requests_total{code=~"2..|3.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
    good_events: "HTTP 状态码 2xx 或 3xx"
    total_events: "所有 HTTP 请求"
  
  latency:
    name: "API 延迟"
    description: "请求延迟低于 200ms 的比例"
    metric: |
      sum(rate(http_request_duration_seconds_bucket{le="0.2"}[5m]))
      /
      sum(rate(http_request_duration_seconds_count[5m]))
    good_events: "延迟 < 200ms 的请求"
    total_events: "所有请求"
  
  correctness:
    name: "API 正确性"
    description: "返回正确数据的请求比例"
    metric: "需要应用层埋点"
    good_events: "返回正确数据的请求"
    total_events: "所有请求"
```

**数据管道**：

```yaml
# 数据管道 SLI 示例
sli_definitions:
  freshness:
    name: "数据新鲜度"
    description: "数据在 SLA 时间内到达的比例"
    metric: |
      count(data_arrival_delay_seconds < 300)
      /
      count(data_arrival_delay_seconds)
    good_events: "5 分钟内到达的数据"
    total_events: "所有数据记录"
  
  correctness:
    name: "数据正确性"
    description: "正确处理的数据比例"
    metric: |
      count(records_processed - records_errored)
      /
      count(records_processed)
    good_events: "成功处理的记录"
    total_events: "所有记录"
  
  coverage:
    name: "数据覆盖度"
    description: "期望数据量中实际处理的比例"
    metric: "需要上游系统提供预期量"
```

**存储服务**：

```yaml
# 存储服务 SLI 示例
sli_definitions:
  durability:
    name: "数据耐久性"
    description: "写入后可成功读取的对象比例"
    metric: |
      successful_reads / total_reads
    good_events: "成功读取的对象"
    total_events: "所有读取请求"
  
  availability:
    name: "存储可用性"
    description: "成功读写请求的比例"
    metric: |
      (successful_reads + successful_writes) / (total_reads + total_writes)
    good_events: "成功的读写请求"
    total_events: "所有读写请求"
  
  latency:
    name: "读写延迟"
    description: "P99 读取延迟 < 100ms 的比例"
    metric: |
      count(read_latency_ms < 100) / count(read_latency_ms)
```

### 3. SLO 定义方法

#### 3.1 SLO 设定流程

```
┌─────────────────────────────────────────────────────────┐
│                 SLO 设定流程                              │
│                                                         │
│  Step 1: 识别关键用户旅程                                │
│  ┌───────────────────────────────────────┐              │
│  │ 用户旅程：浏览商品 → 加入购物车 → 下单  │              │
│  │         → 支付 → 查看订单              │              │
│  │                                       │              │
│  │ 识别哪些旅程对业务最关键               │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Step 2: 选择 SLI                                       │
│  ┌───────────────────────────────────────┐              │
│  │ 每个关键旅程选择 1-3 个 SLI            │              │
│  │ 例：下单成功率、下单延迟 P99           │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Step 3: 确定基线                                        │
│  ┌───────────────────────────────────────┐              │
│  │ 收集历史数据，了解当前表现              │              │
│  │ 例：过去 30 天可用性 99.95%            │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Step 4: 设定目标                                        │
│  ┌───────────────────────────────────────┐              │
│  │ 基于业务需求和用户期望设定目标          │              │
│  │ 例：可用性目标 99.9%                   │              │
│  │ （比 SLA 的 99.5% 更严格）             │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Step 5: 达成共识                                        │
│  ┌───────────────────────────────────────┐              │
│  │ 与开发、产品、业务方对齐 SLO            │              │
│  │ 确保所有人理解 SLO 的含义和影响         │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Step 6: 持续迭代                                        │
│  ┌───────────────────────────────────────┐              │
│  │ 每季度 review SLO                      │              │
│  │ 根据业务变化和用户反馈调整              │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 常见 SLO 设定参考

```
┌────────────────┬─────────────┬──────────────────────────┐
│ 服务类型        │ 建议 SLO    │ 说明                      │
├────────────────┼─────────────┼──────────────────────────┤
│ 面向用户的 API  │ 99.9%       │ 约 43 分钟/月不可用       │
│ （核心业务）    │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 面向用户的 API  │ 99.5%       │ 约 3.6 小时/月不可用      │
│ （非核心）      │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 内部微服务      │ 99.9%       │ 内部服务也需要高可用      │
│                │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 批处理任务      │ 99.0%       │ 允许偶尔失败，可重试      │
│                │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 数据管道        │ 99.5%       │ 数据新鲜度和正确性        │
│                │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 存储服务        │ 99.999%     │ 数据耐久性 11 个 9       │
│ （数据耐久性）  │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 搜索服务        │ 99.9%       │ 可用 + P99 < 500ms       │
│                │             │                          │
├────────────────┼─────────────┼──────────────────────────┤
│ 登录服务        │ 99.95%      │ 登录是关键路径            │
│                │             │                          │
└────────────────┴─────────────┴──────────────────────────┘
```

#### 3.3 SLO 的时间窗口

```
┌─────────────────────────────────────────────────────────┐
│                  SLO 时间窗口选择                         │
│                                                         │
│  滚动窗口（Rolling Window）                              │
│  ┌───────────────────────────────────────┐              │
│  │ 过去 N 天的 SLI 表现                   │              │
│  │                                       │              │
│  │ 常见选择：                             │              │
│  │ • 28 天（4 周）                        │              │
│  │ • 30 天                                │              │
│  │ • 90 天（季度）                        │              │
│  │                                       │              │
│  │ 优点：反映近期表现                     │              │
│  │ 缺点：大事故影响时间长                 │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  日历窗口（Calendar Window）                             │
│  ┌───────────────────────────────────────┐              │
│  │ 按自然月/季度计算                      │              │
│  │                                       │              │
│  │ 优点：与业务周期对齐                   │              │
│  │ 缺点：月初"预算重置"问题               │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  推荐：28 天滚动窗口                                     │
│  • 与月度 review 周期对齐                                │
│  • 避免日历窗口的月初问题                                │
│  • 业界最常用的选择                                      │
└─────────────────────────────────────────────────────────┘
```

### 4. 错误预算（Error Budget）

#### 4.1 错误预算计算

```
┌─────────────────────────────────────────────────────────┐
│                 错误预算计算                              │
│                                                         │
│  公式：                                                  │
│  错误预算 = 1 - SLO 目标值                               │
│                                                         │
│  例 1: SLO = 99.9%                                      │
│  错误预算 = 1 - 0.999 = 0.001 = 0.1%                    │
│                                                         │
│  28 天窗口内允许的不可用时间：                            │
│  28 天 × 24 小时 × 60 分钟 × 0.001 = 40.32 分钟         │
│                                                         │
│  例 2: SLO = 99.95%                                     │
│  错误预算 = 1 - 0.9995 = 0.0005 = 0.05%                 │
│                                                         │
│  28 天窗口内允许的不可用时间：                            │
│  28 天 × 24 小时 × 60 分钟 × 0.0005 = 20.16 分钟        │
│                                                         │
│  例 3: SLO = 99.5%                                      │
│  错误预算 = 1 - 0.995 = 0.005 = 0.5%                    │
│                                                         │
│  28 天窗口内允许的不可用时间：                            │
│  28 天 × 24 小时 × 60 分钟 × 0.005 = 201.6 分钟         │
└─────────────────────────────────────────────────────────┘
```

#### 4.2 错误预算消耗示例

```python
# error_budget_calculator.py
from datetime import datetime, timedelta

class ErrorBudget:
    def __init__(self, slo_target, window_days=28):
        self.slo_target = slo_target
        self.window_days = window_days
        self.budget_pct = 1 - slo_target
        self.total_minutes = window_days * 24 * 60
        self.budget_minutes = self.total_minutes * self.budget_pct
    
    def remaining_budget(self, error_minutes):
        """计算剩余错误预算"""
        used_pct = error_minutes / self.total_minutes
        remaining_pct = self.budget_pct - used_pct
        remaining_minutes = self.budget_minutes - error_minutes
        return {
            'remaining_pct': remaining_pct * 100,
            'remaining_minutes': remaining_minutes,
            'used_pct': used_pct * 100,
            'budget_consumed_pct': (error_minutes / self.budget_minutes) * 100
        }
    
    def burn_rate(self, error_minutes_per_day):
        """计算燃烧率（消耗速率）"""
        daily_budget_minutes = self.budget_minutes / self.window_days
        return error_minutes_per_day / daily_budget_minutes
    
    def days_until_budget_exhausted(self, error_minutes_per_day):
        """计算预算耗尽天数"""
        if error_minutes_per_day <= 0:
            return float('inf')
        daily_budget = self.budget_minutes / self.window_days
        if error_minutes_per_day <= daily_budget:
            return float('inf')  # 不会耗尽
        remaining = self.budget_minutes
        days = 0
        while remaining > 0:
            remaining -= (error_minutes_per_day - daily_budget)
            days += 1
        return days

# 示例：99.9% SLO
budget_999 = ErrorBudget(0.999, 28)
print(f"SLO: 99.9%")
print(f"错误预算: {budget_999.budget_pct*100:.2f}%")
print(f"错误预算（分钟）: {budget_999.budget_minutes:.1f} 分钟")
print(f"错误预算（小时）: {budget_999.budget_minutes/60:.1f} 小时")
print()

# 假设今天有 10 分钟不可用
result = budget_999.remaining_budget(10)
print(f"已消耗 10 分钟后:")
print(f"  剩余预算: {result['remaining_minutes']:.1f} 分钟")
print(f"  预算消耗: {result['budget_consumed_pct']:.1f}%")
print()

# 燃烧率分析
burn = budget_999.burn_rate(2)  # 每天 2 分钟错误
print(f"每天 2 分钟错误的燃烧率: {burn:.2f}x")
days = budget_999.days_until_budget_exhausted(2)
print(f"预算耗尽天数: {days} 天")
```

#### 4.3 错误预算消耗策略

```
┌─────────────────────────────────────────────────────────┐
│              错误预算消耗策略                              │
│                                                         │
│  预算充足（> 50%）                                       │
│  ┌───────────────────────────────────────┐              │
│  │ 策略：正常发布节奏                      │              │
│  │ • 可以进行常规发布                      │              │
│  │ • 可以尝试高风险变更（灰度发布）        │              │
│  │ • 可以进行性能优化实验                  │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  预算中等（20%-50%）                                     │
│  ┌───────────────────────────────────────┐              │
│  │ 策略：谨慎发布                          │              │
│  │ • 增加发布前 Review 环节                │              │
│  │ • 只发布必要的变更                      │              │
│  │ • 加强监控和告警                        │              │
│  │ • 准备好回滚方案                        │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  预算不足（< 20%）                                       │
│  ┌───────────────────────────────────────┐              │
│  │ 策略：冻结发布，专注稳定性              │              │
│  │ • 停止非紧急发布                        │              │
│  │ • 优先修复稳定性问题                    │              │
│  │ • 增加测试覆盖率                        │              │
│  │ • 与管理层沟通风险                      │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  预算耗尽（0%）                                          │
│  ┌───────────────────────────────────────┐              │
│  │ 策略：紧急响应                          │              │
│  │ • 全面冻结发布                          │              │
│  │ • 组织专门的稳定性项目                  │              │
│  │ • 与业务方沟通降级方案                  │              │
│  │ • 重新评估 SLO 是否合理                 │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 4.4 错误预算与发布速度的关联

```
┌─────────────────────────────────────────────────────────┐
│           错误预算与发布速度关联模型                        │
│                                                         │
│  发布频率                                                │
│     ▲                                                   │
│     │                                                   │
│  高 │         ┌─────────────────┐                       │
│     │         │   正常发布       │                       │
│     │         │   预算充足时     │                       │
│     │         └────────┬────────┘                       │
│     │                  │                                │
│  中 │    ┌─────────────┘                                │
│     │    │     ┌─────────────────┐                      │
│     │    │     │  谨慎发布        │                      │
│     │    │     │  预算中等时       │                      │
│     │    │     └────────┬────────┘                      │
│     │    │              │                                │
│  低 │    │    ┌─────────┘                                │
│     │    │    │     ┌─────────────────┐                  │
│     │    │    │     │  冻结发布        │                  │
│     │    │    │     │  预算不足时       │                  │
│     │    │    │     └─────────────────┘                  │
│     │    │    │                                          │
│     └────┴────┴─────────────────────────────→           │
│        100%   50%   20%    0%    错误预算剩余            │
│                                                         │
│  策略联动：                                              │
│  • CI/CD 流水线自动检查错误预算                           │
│  • 预算不足时自动阻止非紧急发布                           │
│  • 通过 API 获取当前预算状态                              │
└─────────────────────────────────────────────────────────┘
```

### 5. 多窗口多燃烧率告警

#### 5.1 燃烧率告警概念

传统的阈值告警（错误率 > 5%）无法区分"短时间严重故障"和"长时间轻微劣化"。燃烧率告警解决了这个问题：

```
┌─────────────────────────────────────────────────────────┐
│              燃烧率告警 vs 传统告警                        │
│                                                         │
│  传统告警：                                              │
│  ┌───────────────────────────────────────┐              │
│  │ 如果错误率 > 5% 持续 5 分钟 → 告警     │              │
│  │                                       │              │
│  │ 问题：                                │              │
│  │ • 不知道错误预算消耗了多少              │              │
│  │ • 不知道是否需要紧急响应               │              │
│  │ • 无法区分严重程度                     │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  燃烧率告警：                                            │
│  ┌───────────────────────────────────────┐              │
│  │ 燃烧率 = 实际错误率 / 预期错误率        │              │
│  │                                       │              │
│  │ 燃烧率 = 1: 正常消耗错误预算           │              │
│  │ 燃烧率 = 2: 消耗速度是正常的 2 倍      │              │
│  │ 燃烧率 = 14.4: 1 小时耗尽 1 月预算     │              │
│  │                                       │              │
│  │ 优势：                                │              │
│  │ • 与错误预算直接关联                   │              │
│  │ • 可以根据严重程度设置不同告警          │              │
│  │ • 支持多窗口验证（减少误报）           │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 多窗口多燃烧率告警矩阵

Google SRE Workbook 推荐的多窗口多燃烧率告警配置：

```
┌────────────────┬────────────┬────────────┬──────────────┐
│  燃烧率         │ 短窗口     │ 长窗口     │ 告警级别      │
│                │ (快速检测)  │ (减少误报)  │              │
├────────────────┼────────────┼────────────┼──────────────┤
│ 14.4x          │ 5 分钟     │ 1 小时     │ P0 (Page)    │
│ (1h 内耗尽)    │            │            │              │
├────────────────┼────────────┼────────────┼──────────────┤
│ 6x             │ 30 分钟    │ 6 小时     │ P0 (Page)    │
│ (1天内耗尽)    │            │            │              │
├────────────────┼────────────┼────────────┼──────────────┤
│ 3x             │ 2 小时     │ 1 天       │ P1 (Page)    │
│ (2天内耗尽)    │            │            │              │
├────────────────┼────────────┼────────────┼──────────────┤
│ 1x             │ 6 小时     │ 3 天       │ P2 (Ticket)  │
│ (预算正常消耗)  │            │            │              │
└────────────────┴────────────┴────────────┴──────────────┘
```

#### 5.3 Prometheus 告警规则配置

```yaml
# prometheus_slo_alerts.yml
groups:
  - name: slo_alerts
    rules:
      # 99.9% SLO，28 天窗口
      # 允许的错误率 = 0.001 = 0.1%
      # 预期错误率 = 0.001 / (28 * 24 * 60) = 每分钟 0.0000025
      
      # 燃烧率 14.4x（1小时内耗尽一个月的预算）
      - alert: SLOBurnRateCritical
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > (14.4 * 0.001)
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          slo: "api-availability"
        annotations:
          summary: "SLO 燃烧率 14.4x - 1小时内将耗尽月度错误预算"
          description: "当前错误率 {{ $value | humanizePercentage }}，需要立即响应"
      
      # 燃烧率 6x（1天内耗尽月度预算）
      - alert: SLOBurnRateHigh
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[30m]))
            /
            sum(rate(http_requests_total[30m]))
          ) > (6 * 0.001)
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > (6 * 0.001)
        for: 5m
        labels:
          severity: critical
          slo: "api-availability"
        annotations:
          summary: "SLO 燃烧率 6x - 1天内将耗尽月度错误预算"
      
      # 燃烧率 3x（2天内耗尽月度预算）
      - alert: SLOBurnRateMedium
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[2h]))
            /
            sum(rate(http_requests_total[2h]))
          ) > (3 * 0.001)
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[1d]))
            /
            sum(rate(http_requests_total[1d]))
          ) > (3 * 0.001)
        for: 30m
        labels:
          severity: warning
          slo: "api-availability"
        annotations:
          summary: "SLO 燃烧率 3x - 2天内将耗尽月度错误预算"
      
      # 燃烧率 1x（正常消耗，但需要关注）
      - alert: SLOBurnRateWatch
        expr: |
          (
            sum(rate(http_requests_total{code=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > (1 * 0.001)
          and
          (
            sum(rate(http_requests_total{code=~"5.."}[3d]))
            /
            sum(rate(http_requests_total[3d]))
          ) > (1 * 0.001)
        for: 2h
        labels:
          severity: warning
          slo: "api-availability"
        annotations:
          summary: "SLO 燃烧率 1x - 错误预算正常消耗中"
```

### 6. SLO 平台与工具

#### 6.1 开源 SLO 工具

```
┌─────────────────────────────────────────────────────────┐
│                  SLO 工具生态                            │
│                                                         │
│  Sloth                                                  │
│  ┌───────────────────────────────────────┐              │
│  │ 基于 Prometheus 的 SLO 管理工具         │              │
│  │ • 使用 YAML 定义 SLO                   │              │
│  │ • 自动生成 Prometheus 告警规则           │              │
│  │ • 支持多窗口多燃烧率                    │              │
│  │ • GitHub: sloberun/sloth               │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  OpenSLO                                                │
│  ┌───────────────────────────────────────┐              │
│  │ SLO 定义的开放标准                      │              │
│  │ • 厂商无关的 SLO 规范                   │              │
│  │ • 支持多种后端实现                      │              │
│  │ • GitHub: OpenSLO/OpenSLO              │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Google Cloud SLO                                       │
│  ┌───────────────────────────────────────┐              │
│  │ Google Cloud Monitoring 内置 SLO       │              │
│  │ • 原生支持 SLI/SLO 定义                │              │
│  │ • 内置燃烧率告警                        │              │
│  │ • 与 GCP 深度集成                      │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Datadog SLO                                            │
│  ┌───────────────────────────────────────┐              │
│  │ Datadog 内置 SLO 功能                  │              │
│  │ • 支持多种 SLI 类型                    │              │
│  │ • 可视化错误预算                        │              │
│  │ • 与告警系统集成                        │              │
│  └───────────────────────────────────────┘              │
│                                                         │
│  Nobl9                                                  │
│  ┌───────────────────────────────────────┐              │
│  │ 专业 SLO 平台（SaaS）                  │              │
│  │ • 支持多种数据源                        │              │
│  │ • 高级错误预算分析                      │              │
│  │ • 团队协作功能                          │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 6.2 Sloth 配置示例

```yaml
# sloth_config.yaml
apiVersion: sloth.slok.dev/v1
kind: PrometheusServiceLevel
metadata:
  name: user-service-availability
  namespace: production
spec:
  service: "user-service"
  labels:
    team: "platform"
    tier: "critical"
  
  slos:
    - name: "availability"
      objective: 99.9
      description: "用户服务可用性 SLO"
      sli:
        events:
          error_query: |
            sum(rate(http_requests_total{
              service="user-service",
              code=~"5.."
            }[{{.window}}]))
          total_query: |
            sum(rate(http_requests_total{
              service="user-service"
            }[{{.window}}]))
      alerting:
        name: "UserServiceHighErrorRate"
        labels:
          severity: "critical"
        annotations:
          summary: "用户服务错误率过高"
        page_alert:
          labels:
            severity: "page"
        ticket_alert:
          labels:
            severity: "ticket"
    
    - name: "latency"
      objective: 99.0
      description: "用户服务延迟 SLO (P99 < 500ms)"
      sli:
        events:
          error_query: |
            sum(rate(http_request_duration_seconds_count{
              service="user-service"
            }[{{.window}}])) -
            sum(rate(http_request_duration_seconds_bucket{
              service="user-service",
              le="0.5"
            }[{{.window}}]))
          total_query: |
            sum(rate(http_request_duration_seconds_count{
              service="user-service"
            }[{{.window}}]))
      alerting:
        name: "UserServiceHighLatency"
        labels:
          severity: "warning"
```

---

## 💻 实战练习

### 练习 1：定义 SLI 和 SLO

**场景**：为一个电商系统的以下服务定义 SLI 和 SLO：

1. 商品搜索服务
2. 订单服务
3. 支付服务

```python
# sli_slo_definition.py

class SLIDefinition:
    def __init__(self, name, description, good_events, total_events, metric_query):
        self.name = name
        self.description = description
        self.good_events = good_events
        self.total_events = total_events
        self.metric_query = metric_query

class SLODefinition:
    def __init__(self, name, sli, target, window_days=28):
        self.name = name
        self.sli = sli
        self.target = target
        self.window_days = window_days
        self.error_budget = 1 - target
        self.budget_minutes = window_days * 24 * 60 * self.error_budget

# 商品搜索服务
search_availability_sli = SLIDefinition(
    name="搜索成功率",
    description="搜索请求返回成功结果的比例",
    good_events="HTTP 200 且响应包含搜索结果",
    total_events="所有搜索请求",
    metric_query='sum(rate(search_requests_total{status="success"}[5m])) / sum(rate(search_requests_total[5m]))'
)

search_latency_sli = SLIDefinition(
    name="搜索延迟",
    description="P99 延迟低于 500ms 的比例",
    good_events="延迟 < 500ms 的搜索请求",
    total_events="所有搜索请求",
    metric_query='sum(rate(search_duration_seconds_bucket{le="0.5"}[5m])) / sum(rate(search_duration_seconds_count[5m]))'
)

search_availability_slo = SLODefinition(
    name="搜索服务可用性",
    sli=search_availability_sli,
    target=0.999,
    window_days=28
)

search_latency_slo = SLODefinition(
    name="搜索服务延迟",
    sli=search_latency_sli,
    target=0.99,
    window_days=28
)

# 订单服务
order_availability_sli = SLIDefinition(
    name="订单创建成功率",
    description="订单创建请求成功的比例",
    good_events="订单创建成功（HTTP 201）",
    total_events="所有订单创建请求",
    metric_query='sum(rate(order_create_total{status="success"}[5m])) / sum(rate(order_create_total[5m]))'
)

order_availability_slo = SLODefinition(
    name="订单服务可用性",
    sli=order_availability_sli,
    target=0.9995,
    window_days=28
)

# 支付服务
payment_availability_sli = SLIDefinition(
    name="支付成功率",
    description="支付请求成功的比例",
    good_events="支付成功（状态为 success）",
    total_events="所有支付请求",
    metric_query='sum(rate(payment_total{status="success"}[5m])) / sum(rate(payment_total[5m]))'
)

payment_availability_slo = SLODefinition(
    name="支付服务可用性",
    sli=payment_availability_sli,
    target=0.9999,
    window_days=28
)

# 输出 SLO 定义
services = [
    ("商品搜索", [search_availability_slo, search_latency_slo]),
    ("订单服务", [order_availability_slo]),
    ("支付服务", [payment_availability_slo]),
]

for service_name, slos in services:
    print(f"\n=== {service_name} ===")
    for slo in slos:
        print(f"  SLO: {slo.name}")
        print(f"    SLI: {slo.sli.name}")
        print(f"    目标: {slo.target*100:.2f}%")
        print(f"    错误预算: {slo.error_budget*100:.3f}%")
        print(f"    28天允许不可用: {slo.budget_minutes:.1f} 分钟")
```

### 练习 2：错误预算计算与策略

**场景**：你的服务 SLO 为 99.9%（28 天窗口），当前已消耗 60% 的错误预算。团队计划在下周进行一次大版本发布。

**任务**：
1. 计算剩余错误预算
2. 评估是否应该发布
3. 制定发布策略

```python
# error_budget_strategy.py

class ErrorBudgetAdvisor:
    def __init__(self, slo_target, window_days=28):
        self.slo_target = slo_target
        self.window_days = window_days
        self.error_budget = 1 - slo_target
        self.total_minutes = window_days * 24 * 60
        self.budget_minutes = self.total_minutes * self.error_budget
    
    def assess_release_risk(self, budget_consumed_pct, change_risk):
        """
        评估发布风险
        budget_consumed_pct: 已消耗预算百分比
        change_risk: 变更风险 (low/medium/high)
        """
        remaining_pct = 100 - budget_consumed_pct
        
        risk_matrix = {
            'low': {'green': 50, 'yellow': 20, 'red': 5},
            'medium': {'green': 70, 'yellow': 40, 'red': 15},
            'high': {'green': 85, 'yellow': 60, 'red': 30},
        }
        
        thresholds = risk_matrix[change_risk]
        
        if remaining_pct >= thresholds['green']:
            return {
                'decision': 'GO',
                'risk': 'LOW',
                'recommendation': '正常发布，预算充足',
                'actions': ['按计划发布', '保持标准监控']
            }
        elif remaining_pct >= thresholds['yellow']:
            return {
                'decision': 'CAUTION',
                'risk': 'MEDIUM',
                'recommendation': '谨慎发布，预算中等',
                'actions': [
                    '增加发布前 Review',
                    '准备回滚方案',
                    '灰度发布（先 10% 流量）',
                    '增加监控告警敏感度'
                ]
            }
        elif remaining_pct >= thresholds['red']:
            return {
                'decision': 'HOLD',
                'risk': 'HIGH',
                'recommendation': '建议推迟非紧急发布',
                'actions': [
                    '只发布紧急修复',
                    '增加灰度比例和时间',
                    '准备详细的回滚计划',
                    '通知管理层风险'
                ]
            }
        else:
            return {
                'decision': 'STOP',
                'risk': 'CRITICAL',
                'recommendation': '冻结发布，专注稳定性',
                'actions': [
                    '停止所有非紧急发布',
                    '组织稳定性项目',
                    '重新评估 SLO 目标',
                    '与业务方沟通降级方案'
                ]
            }

# 使用示例
advisor = ErrorBudgetAdvisor(0.999, 28)

print("=== SLO 概览 ===")
print(f"SLO 目标: {advisor.slo_target*100:.1f}%")
print(f"错误预算: {advisor.error_budget*100:.2f}%")
print(f"28天允许不可用: {advisor.budget_minutes:.1f} 分钟")
print()

# 已消耗 60%，计划发布高风险变更
print("=== 发布评估 ===")
print(f"已消耗预算: 60%")
print(f"剩余预算: 40%")
print(f"变更风险: high")
print()

assessment = advisor.assess_release_risk(60, 'high')
print(f"决策: {assessment['decision']}")
print(f"风险: {assessment['risk']}")
print(f"建议: {assessment['recommendation']}")
print("行动项:")
for action in assessment['actions']:
    print(f"  - {action}")
```

### 练习 3：配置燃烧率告警

**场景**：为你的服务配置 Prometheus 多窗口多燃烧率告警。

```yaml
# 实战练习：配置 SLO 燃烧率告警
# 
# 背景：你的 API 服务 SLO 为 99.9%（28天窗口）
# 任务：配置以下燃烧率告警
#
# 1. 燃烧率 14.4x（1小时耗尽月预算）→ P0 告警
#    短窗口: 5分钟，长窗口: 1小时
#
# 2. 燃烧率 6x（1天耗尽月预算）→ P0 告警
#    短窗口: 30分钟，长窗口: 6小时
#
# 3. 燃烧率 3x（2天耗尽月预算）→ P1 告警
#    短窗口: 2小时，长窗口: 1天
#
# 4. 燃烧率 1x（预算正常消耗）→ P2 工单
#    短窗口: 6小时，长窗口: 3天

# 参考配置（在练习 1 的基础上）
# Prometheus 告警规则
groups:
  - name: api_slo_alerts
    rules:
      # 你的告警规则写在这里
      # 参考本章 5.3 节的配置示例
      pass
```

---

## 🎯 面试题精选

### 面试题 1：什么是 SLI、SLO、SLA？它们之间是什么关系？

**考察点**：对 SRE 核心概念的理解。

**参考答案要点**：
1. SLI（Service Level Indicator）：衡量服务行为的量化指标，如成功率、延迟
2. SLO（Service Level Objective）：SLI 的目标值，是内部承诺
3. SLA（Service Level Agreement）：与客户的正式合同，有法律约束力
4. SLI 是测量什么，SLO 是目标是什么，SLA 是承诺是什么
5. SLO 应比 SLA 更严格，留有缓冲

### 面试题 2：什么是错误预算？如何计算？

**考察点**：对错误预算机制的理解。

**参考答案要点**：
1. 错误预算 = 1 - SLO 目标值
2. 例：99.9% SLO → 错误预算 0.1%
3. 28 天窗口：28 × 24 × 60 × 0.001 = 40.32 分钟
4. 错误预算是发布速度和稳定性的平衡机制

### 面试题 3：如何选择合适的 SLI？

**考察点**：对 SLI 选择方法的掌握。

**参考答案要点**：
1. 用户视角优先：用户关心什么就测量什么
2. 可测量：数据来源可靠
3. 可行动：SLI 变化时团队知道如何应对
4. 不要太多：每服务 3-5 个即可
5. 常见类型：可用性、延迟、吞吐量、正确性

### 面试题 4：错误预算不足时应该怎么做？

**考察点**：对错误预算策略的理解。

**参考答案要点**：
1. 预算 > 50%：正常发布
2. 预算 20%-50%：谨慎发布，增加 Review
3. 预算 < 20%：冻结非紧急发布
4. 预算耗尽：全面冻结，专注稳定性
5. 核心是平衡发布速度和稳定性

### 面试题 5：什么是燃烧率告警？比传统告警好在哪里？

**考察点**：对高级告警策略的理解。

**参考答案要点**：
1. 燃烧率 = 实际错误率 / 预期错误率
2. 燃烧率 14.4x 表示 1 小时耗尽月度预算
3. 优势：与错误预算直接关联、可区分严重程度
4. 多窗口验证减少误报
5. Google SRE Workbook 推荐的实践

### 面试题 6：SLO 应该设多高？99.9% 还是 99.99%？

**考察点**：对 SLO 设定的业务理解。

**参考答案要点**：
1. 不是越高越好，要平衡成本和收益
2. 99.9% = 43 分钟/月不可用
3. 99.99% = 4.3 分钟/月不可用
4. 从 99.9% 到 99.99% 的成本可能是 10 倍
5. 应基于用户期望和业务需求设定

### 面试题 7：如何让 SLO 真正落地，而不只是写在文档里？

**考察点**：对 SLO 实践的理解。

**参考答案要点**：
1. 自动化采集和计算 SLI
2. 将 SLO 与 CI/CD 流水线集成
3. 错误预算与发布策略联动
4. 定期 review 和调整 SLO
5. 建立 SLO Dashboard，可视化展示

---

## 📚 深入阅读

### 官方文档与书籍
- [Google SRE Book - Chapter 4: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook - SLO Engineering](https://sre.google/workbook/implementing-slos/)
- [Google SRE Workbook - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)

### 推荐文章
- [The Art of SLOs - Google](https://sre.google/resources/practices-and-processes/art-of-slos/)
- [SLO-based Alerting - Alex Hidalgo](https://www.usenix.org/conference/srecon19americas/presentation/hidalgo)
- [Alerting on SLOs like Google - Frederic Branczyk](https://grafana.com/blog/2021/05/26/alerting-on-slos-like-google/)

### 实践工具
- [Sloth - SLO Tool](https://sloth.dev/) - 基于 Prometheus 的 SLO 工具
- [OpenSLO](https://openslo.com/) - SLO 开放标准
- [Nobl9](https://nobl9.com/) - 专业 SLO 平台
- [Google Cloud SLO](https://cloud.google.com/stackdriver/docs/slo) - GCP 原生 SLO

---

## ✅ 自检清单

- [ ] 能区分 SLI、SLO、SLA 的概念和关系
- [ ] 能为不同类型的服务选择合适的 SLI
- [ ] 能计算错误预算及其消耗速率
- [ ] 能根据错误预算制定发布策略
- [ ] 能配置多窗口多燃烧率告警
- [ ] 了解主流 SLO 工具（Sloth、OpenSLO 等）
- [ ] 理解 SLO 的时间窗口选择
- [ ] 能回答 SLO 相关面试题
