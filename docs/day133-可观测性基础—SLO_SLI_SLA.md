# Day 133: 可观测性基础 — SLO/SLI/SLA

> 📅 日期：2026-05-04
> 📖 学习主题：可观测性基础 — SLO/SLI/SLA
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解三大支柱：指标、日志、链路
- 掌握 SLO/SLI/SLA 的定义

---

## 📖 三大支柱

### 1. Metrics（指标）

```
数值型数据，随时间变化
示例：CPU 使用率、请求延迟、错误率
工具：Prometheus、Datadog
```

### 2. Logs（日志）

```
离散事件记录
示例：错误日志、访问日志
工具：ELK、Loki
```

### 3. Traces（链路）

```
请求在系统中的完整路径
示例：API → Service A → Service B → DB
工具：Jaeger、Zipkin
```

## SLI/SLO/SLA

```
SLI（Service Level Indicator）— 实际测量值
  例：99.95% 的请求在 200ms 内响应

SLO（Service Level Objective）— 目标值
  例：99.9% 的请求在 200ms 内响应

SLA（Service Level Agreement）— 合同承诺
  例：99.5% 可用性，否则赔偿
```

## 错误预算

```
错误预算 = 100% - SLO
例：SLO = 99.9%，错误预算 = 0.1%
这意味着每月可以有 ~43 分钟的不可用时间

当错误预算耗尽：
- 停止发布新功能
- 专注稳定性
- 修复 Bug
```

---

## 📚 扩展阅读

- [Google SRE Book - SLO 章节](https://sre.google/sre-book/service-level-objectives/)
