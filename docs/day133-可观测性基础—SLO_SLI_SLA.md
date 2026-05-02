# Day 133: 可观测性基础 — SLO/SLI/SLA

> 📅 日期：2026-05-05
> 📖 学习主题：可观测性基础 — SLO/SLI/SLA
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 深刻理解可观测性三大支柱（Metrics, Logs, Traces）的本质区别
- 能够准确区分并定义 SLI、SLO、SLA
- 掌握错误预算（Error Budget）的计算与管理策略
- 理解“黄金指标”在 SRE 实战中的应用

---

## 📖 详细知识点

### 1. 可观测性的本质

**监控（Monitoring） vs 可观测性（Observability）**

```
传统监控：
  定义：我们预先知道什么会坏（Known Unknowns）。
  做法：设定阈值，坏了报警。
  局限：对没想到的故障无能为力。

可观测性：
  定义：通过外部输出推断系统内部状态（Unknown Unknowns）。
  支柱：
    1. Metrics（指标）— "系统现在怎么样？"（聚合数据）
    2. Logs（日志）— "发生了什么具体事件？"（离散数据）
    3. Traces（链路）— "请求在哪一步慢了？"（上下文流转）
```

**三者关系**：
- 指标发现问题（Dashboard 看到延迟飙升）
- 链路定位范围（Jaeger 看到是支付服务慢了）
- 日志查明根因（Log 看到支付服务连不上 DB）

### 2. SLI, SLO, SLA 详解

这是 SRE 衡量系统健康状况的核心标准，必须严格区分。

| 术语 | 全称 | 含义 | 视角 | 示例 |
|------|------|------|------|------|
| **SLI** | Indicator | **指标**。实际测量的值。 | 系统 | 99.95% 的请求在 200ms 内返回。 |
| **SLO** | Objective | **目标**。期望达到的值。 | 内部 | 99.9% 的请求需在 200ms 内返回。 |
| **SLA** | Agreement | **承诺**。写进合同的底线。 | 客户 | 承诺 99.5% 可用，否则赔钱。 |

**层级关系：**
```
SLA (99.5%)  <--- 对外承诺，底线
   ↑
SLO (99.9%)  <--- 内部目标，缓冲
   ↑
SLI (99.95%) <--- 实际测量值
```

**为什么 SLO 要比 SLA 严？**
如果 SLO 和 SLA 一样，任何微小的波动都会导致违约。中间的差值就是**缓冲带**。

### 3. 错误预算（Error Budget）

**定义：**
$$ \text{Error Budget} = 100\% - \text{SLO} $$

**计算示例：**
假设 SLO 是 99.9%（每月不可用时间 < 43 分钟）。

| 周期 | 总时间 | 允许的不可用时间 |
|------|--------|----------------|
| 1 周 | 7 天 | ~10 分钟 |
| 1 月 | 30 天 | ~43 分钟 |
| 1 年 | 365 天 | ~8.76 小时 |

**预算消耗逻辑：**
1. **预算充足**：系统稳定，SRE 可以放心发版、做变更，追求速度。
2. **预算耗尽**：系统不稳定，SRE 必须冻结发布，全力修复 Bug、提升稳定性。

**SRE 的核心博弈**：
> "用错误预算换取发布速度。"

如果团队总是 100% 运行，说明太保守，应该加大发布力度；如果总是超预算，说明跑太快，需要减速。

### 4. 黄金指标（The Four Golden Signals）

Google SRE 书中定义的四个最关键的监控维度：

| 指标 | 说明 | 关注点 | 示例查询 (PromQL) |
|------|------|--------|------------------|
| **Latency** | 请求处理时间 | 区分成功与失败请求 | `histogram_quantile(0.99, rate(http_duration_bucket[5m]))` |
| **Traffic** | 系统负载 | QPS, 并发连接数 | `rate(http_requests_total[5m])` |
| **Errors** | 失败率 | HTTP 5xx, 异常 | `rate(http_errors_total[5m])` |
| **Saturation** | 资源利用 | CPU, 内存，队列长度 | `node_cpu_usage_percent` |

**实战经验**：
- 不要监控"平均延迟"，要看 P50, P90, P99。
- 只有 Error Rate 升高才报警，不要 CPU 到了 90% 就报警（那是 Saturation）。

### 5. 基于 SLO 的告警

**传统的错误做法**：
- "CPU > 80% 报警"（可能业务完全正常）
- "磁盘 > 90% 报警"（可能还有空间）

**SRE 的正确做法**：
- **症状告警**：用户已经受到影响（如 5xx 错误率升高，P99 延迟超标）。**立即响应**。
- **预测告警**：根据消耗速度，预测错误预算即将耗尽。**白天工作时间处理**。

**燃烧率（Burn Rate）告警**：
- 燃烧率 = 1 意味着消耗速度刚好符合 SLO。
- 燃烧率 = 10 意味着你会在 30 天内耗尽一个月的预算。

---

## 🏗️ 实战：定义并监控 SLO

### 步骤 1：选择 SLI

对于 Web API，最好的 SLI 是**有效请求的比例**。
SLI = (2xx + 3xx 响应数) / (总请求数)

### 步骤 2：设定 SLO

我们要保证 99.9% 的请求在 300ms 内返回 200/300 状态码。

### 步骤 3：Prometheus 告警规则

```yaml
groups:
  - name: slo-burn-rate
    rules:
      # 短期高燃烧率（14.4x），持续 5 分钟 → Page
      - alert: ErrorBudgetBurn
        expr: |
          (
            1 - (
              sum(rate(http_requests_total{code=~"2..|3.."}[5m])) /
              sum(rate(http_requests_total[5m]))
            )
          ) > (14.4 * (1 - 0.999))
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error budget burn rate is 14.4x"

      # 长期低燃烧率（1x），持续 1 小时 → Ticket
      - alert: ErrorBudgetBurnLong
        expr: |
          (
            1 - (
              sum(rate(http_requests_total{code=~"2..|3.."}[1h])) /
              sum(rate(http_requests_total[1h]))
            )
          ) > (1 * (1 - 0.999))
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Error budget burning at normal rate"
```

---

## 🧪 练习题

### 练习 1：计算 SLO

某视频网站承诺：
- 99% 的用户播放成功率达标。
- P95 加载时间 < 2 秒。

请识别其中的 SLI 和 SLO。

<details>
<summary>答案</summary>

**SLI 1**: 播放成功的请求数 / 总请求数
**SLO 1**: 99%

**SLI 2**: 95% 分位的加载时间
**SLO 2**: < 2 秒
</details>

### 练习 2：预算决策

某服务 SLO 99.9%，本月剩余预算 20%。
此时有一个高风险的新功能上线，预计可能引发 0.05% 的错误率增长。
作为 SRE，你批准吗？

<details>
<summary>答案</summary>

**拒绝**。
剩余预算 20% 意味着已经没有多少容错空间。
上线预计消耗 0.05% 的预算（相对于剩余总额），这极有可能导致剩余预算瞬间耗尽，甚至跌破 SLA。
正确做法：先观察，确保系统稳定后再发布，或者在低峰期灰度发布。
</details>

### 练习 3：燃烧率计算

某服务 SLO 为 99.95%（每月 21.6 分钟不可用）。
过去 1 小时内，该服务累计宕机了 3 分钟。

1. 燃烧率是多少？
2. 如果保持这个速度，多少天会耗尽月度预算？
3. 应该触发什么级别的告警？

<details>
<summary>答案</summary>

1. **燃烧率计算**：
   - 1 小时实际消耗 = 3 分钟
   - 1 小时正常消耗 = 21.6 分钟 / 30 天 / 24 小时 ≈ 0.03 分钟
   - 燃烧率 = 3 / 0.03 = **100x**

2. **耗尽时间**：
   - 剩余预算 = 21.6 - 3 = 18.6 分钟
   - 消耗速度 = 3 分钟/小时
   - 耗尽时间 = 18.6 / 3 = 6.2 小时

3. **告警级别**：**P0/Critical**，必须立即响应！
   这是严重的燃烧率，6 小时内预算就会耗尽，说明系统正处于严重故障中。
</details>

---

## 📖 深入：错误预算策略表

Google 推荐的"多窗口多燃烧率"告警策略：

| 燃烧率 | 观察窗口 | 消耗完预算所需时间 | 严重程度 | 响应方式 |
|--------|---------|-------------------|---------|---------|
| **14.4x** | 1 小时 | 2 天 | Critical | 立即 PagerDuty |
| **6x** | 6 小时 | 5 天 | Critical | 立即 PagerDuty |
| **3x** | 1 天 | 10 天 | Warning | 工作时间处理 |
| **1x** | 3 天 | 30 天 | Info | 周报中提及 |

**为什么需要多窗口？**
- 短期高燃烧（14.4x + 1h）：捕捉突发故障，避免漏报
- 长期低燃烧（1x + 3d）：捕捉慢性退化，避免疲劳

---

## 📖 深入：Prometheus SLO 实现细节

### 1. 比率 SLO（Request-based）

适用于 HTTP API、RPC 服务。

```promql
# 分子：成功请求
sum(rate(http_requests_total{code=~"2..|3..",job="api"}[30d]))

# 分母：总请求
sum(rate(http_requests_total{job="api"}[30d]))

# SLO 表达式
(
  sum(rate(http_requests_total{code=~"2..|3..",job="api"}[30d]))
  /
  sum(rate(http_requests_total{job="api"}[30d]))
) >= 0.999
```

### 2. 延迟 SLO（Latency-based）

适用于关注响应时间的服务。

```promql
# 使用 Histogram 计算 P99 延迟 < 300ms 的比例
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="api"}[30d])) by (le))
< 0.3
```

### 3. 可用性 SLO（Availability-based）

适用于有健康检查的服务。

```promql
# 过去 30 天健康检查成功率
sum_over_time(up{job="api"}[30d]) / count_over_time(up{job="api"}[30d]) >= 0.999
```

---

## 🏗️ 实战：Grafana SLO Dashboard

### 创建 SLO 面板

```json
{
  "dashboard": {
    "title": "API SLO Dashboard",
    "panels": [
      {
        "title": "Error Budget Remaining",
        "type": "stat",
        "targets": [
          {
            "expr": "1 - (\n  (\n    sum(rate(http_requests_total{code=~\"2..|3..\"}[30d]))\n    /\n    sum(rate(http_requests_total[30d]))\n  ) - 0.999\n) / (1 - 0.999)"
          }
        ],
        "thresholds": [
          { "value": 0, "color": "red" },
          { "value": 0.5, "color": "yellow" },
          { "value": 1, "color": "green" }
        ]
      },
      {
        "title": "P99 Latency",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      }
    ]
  }
}
```

---

## 📖 深入：SLO 的常见陷阱

### 陷阱 1：SLO 设置得过于严格

```
错误：SLO 99.999%（全年 5 分钟不可用）
后果：团队不敢发版，创新停滞，SRE 沦为"守门员"
正确：根据业务实际设定，内部服务 99.9% 通常足够
```

### 陷阱 2：SLO 设置得过于宽松

```
错误：SLO 99%（全年 3.65 天不可用）
后果：用户体验差但没人报警，预算永远用不完
正确：参考用户投诉率和业务指标调整
```

### 陷阱 3：用技术指标代替用户体验

```
错误：监控 CPU < 80%
问题：CPU 低不代表用户爽（可能是请求根本没进来）
正确：监控用户实际感知的指标（延迟、错误率）
```

### 陷阱 4：忽略长尾延迟

```
错误：只关注平均延迟或 P50
问题：P50=100ms 不代表所有用户都快，P99 可能已经 10s 了
正确：同时监控 P50、P95、P99
```

---

## 🏗️ 实战：SRE 周报模板

```markdown
# SRE Weekly Report - Week 42

## SLO 状态
| 服务 | SLO | 实际 SLI | 预算剩余 | 状态 |
|------|-----|---------|---------|------|
| API Gateway | 99.9% | 99.95% | 65% | ✅ 健康 |
| Payment Service | 99.95% | 99.92% | 15% | ⚠️ 警告 |
| User Service | 99.9% | 99.99% | 88% | ✅ 健康 |

## 事件回顾
- **2026-10-15 14:30**: Payment Service 延迟飙升（P99=5s），持续 15 分钟
  - 根因：数据库慢查询
  - 影响：消耗 2% 月度预算
  - 修复：添加索引

## 预算消耗趋势
- 本周消耗：3%
- 月度累计：85%
- 预测：月底前耗尽风险 ⚠️

## 行动项
- [ ] 优化 Payment Service 慢查询
- [ ] 审查 User Service 发布频率（预算过剩）
- [ ] 更新 Alertmanager 路由规则
```

---

## 📚 扩展阅读

- [Google SRE Book - SLO 章节](https://sre.google/sre-book/service-level-objectives/)
- [Prometheus SLO 文档](https://prometheus.io/docs/practices/slo/)
- [Google SRE Workbook - 错误预算政策](https://sre.google/workbook/implementing-slos/)
- [Honeycomb - Observability vs Monitoring](https://www.honeycomb.io/blog/observability-vs-monitoring)
