# Day 173: On-Call 实践

> 📅 日期：2026-05-03
> 📖 学习主题：On-Call 实践 — 值班制度设计、告警分级、升级策略、Runbook、告警疲劳治理、值班工具、值班后复盘
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 160-172（GitOps、LLMOps、监控基础）

---

## 🎯 学习目标

完成 Day 173 的学习后，你应该掌握：

- 设计合理的 On-Call 值班轮换制度，兼顾公平性与效率
- 建立多级告警分级体系（P0-P3），明确各级响应时效
- 编写高质量的 Runbook，将应急操作标准化
- 识别和治理告警疲劳问题，提升告警信噪比
- 使用 PagerDuty / OpsGenie 等工具管理值班和升级
- 建立值班后复盘机制，持续改进 On-Call 体验

---

## 📖 核心知识点

### 1. On-Call 概述与 Google SRE 理论基础

#### 1.1 什么是 On-Call

On-Call（值班）是指工程师在特定时间段内随时待命，负责响应和处理生产环境告警和事故。Google SRE Book 第 11 章明确指出：

> "Being on-call is a critical duty that ensures the reliability of production systems."

On-Call 是 SRE 实践的基石之一。一个设计良好的 On-Call 体系能够：

- 确保生产环境故障被及时发现和处理
- 保护工程师的工作生活平衡
- 通过反馈循环推动系统可靠性持续改进

#### 1.2 Google SRE 对 On-Call 的指导原则

Google SRE Book 提出了几条核心原则：

**50% 规则**：SRE 工程师花在运维工作上的时间不应超过 50%，剩余时间应用于工程工作。On-Call 是运维工作的一部分。

**事件量上限**：在 12 小时的 On-Call 班次中，工程师应处理不超过 2 个需要人工干预的事件。超过这个数量说明系统自动化程度不足或告警规则有问题。

**补偿机制**：On-Call 应当有合理的补偿（调休、加班费等），且不应被视为"免费"工作。

```
┌─────────────────────────────────────────────────────────┐
│              Google SRE On-Call 指导原则                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  50%规则  │    │ 事件上限  │    │ 补偿机制  │          │
│  │          │    │          │    │          │          │
│  │ 运维不超  │    │ 12h 班次  │    │ 调休/加班 │          │
│  │ 过 50%   │    │ ≤2 事件   │    │ 费补偿    │          │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘          │
│       │               │               │                │
│       ▼               ▼               ▼                │
│  工程时间保障    系统自动化驱动     可持续的值班         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2. 值班制度设计

#### 2.1 轮换模型

常见的值班轮换模型有以下几种：

**单人轮换（Primary-Only）**：

```
Week 1: Alice
Week 2: Bob
Week 3: Carol
Week 4: Dave
Week 5: Alice  (循环)
```

优点：职责清晰；缺点：单点压力大，无备份。

**主备轮换（Primary-Secondary）**：

```
Week 1: Primary=Alice   Secondary=Bob
Week 2: Primary=Bob     Secondary=Carol
Week 3: Primary=Carol   Secondary=Dave
Week 4: Primary=Dave    Secondary=Alice
```

优点：有备份保障；缺点：两人同时受影响。

**跟随太阳（Follow-the-Sun）**：

```
              UTC 时间轴
  00:00 ──────── 08:00 ──────── 16:00 ──────── 24:00
    │              │              │              │
    ├──────────────┤              │              │
    │  亚太团队     │              │              │
    │  (APAC)      │              │              │
    │              ├──────────────┤              │
    │              │  欧洲团队     │              │
    │              │  (EMEA)      │              │
    │              │              ├──────────────┤
    │              │              │  美洲团队     │
    │              │              │  (AMER)      │
```

优点：无夜间值班；缺点：需要跨时区团队，交接复杂。

**分层轮换（Tiered Rotation）**：

```
┌─────────────────────────────────────────────────┐
│  Tier 1 (L1)  ──→  初级工程师 / NOC              │
│  • 接收告警，执行 Runbook                        │
│  • 处理已知问题                                  │
│  • 15 分钟内响应                                 │
├─────────────────────────────────────────────────┤
│  Tier 2 (L2)  ──→  高级工程师                    │
│  • 处理 L1 无法解决的问题                        │
│  • 深入排查，跨服务协调                          │
│  • 30 分钟内响应                                 │
├─────────────────────────────────────────────────┤
│  Tier 3 (L3)  ──→  架构师 / 技术负责人           │
│  • 架构级问题决策                                │
│  • 跨团队/跨BU 协调                              │
│  • 1 小时内响应                                  │
└─────────────────────────────────────────────────┘
```

#### 2.2 值班排班设计要素

一个好的值班排班制度需要考虑以下要素：

```yaml
# 值班排班配置示例
on_call_schedule:
  rotation:
    type: "weekly"           # 轮换周期：daily/weekly/biweekly
    handoff_time: "10:00"    # 交接时间（建议在上午）
    timezone: "Asia/Shanghai"
  
  team_size_minimum: 4       # 最少 4 人轮换（每人每月约 1 周）
  
  primary:
    name: "主值班"
    response_time: "5min"    # 确认告警的时间
    escalation_timeout: "15min"
  
  secondary:
    name: "副值班"
    response_time: "15min"   # 主值班未响应时升级
    escalation_timeout: "30min"
  
  constraints:
    max_consecutive_weeks: 2       # 最多连续值班 2 周
    min_gap_between_rotations: 2   # 两次值班间最少间隔 2 周
    no_holiday_override: true      # 节假日不额外安排
    holiday_on_call_bonus: true    # 节假日值班额外补偿
```

#### 2.3 值班人员能力矩阵

```
┌────────────┬─────────┬─────────┬─────────┬─────────┐
│ 技能领域    │ Alice   │ Bob     │ Carol   │ Dave    │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 前端服务    │ ★★★★★  │ ★★★☆☆  │ ★★★★☆  │ ★★☆☆☆  │
│ 后端服务    │ ★★★☆☆  │ ★★★★★  │ ★★★★★  │ ★★★★☆  │
│ 数据库      │ ★★☆☆☆  │ ★★★★☆  │ ★★☆☆☆  │ ★★★★★  │
│ 网络        │ ★★★☆☆  │ ★★★☆☆  │ ★★★★★  │ ★★★☆☆  │
│ K8s/容器    │ ★★★★☆  │ ★★★★★  │ ★★★☆☆  │ ★★★★☆  │
│ 安全事件    │ ★★☆☆☆  │ ★★☆☆☆  │ ★★☆☆☆  │ ★★★★☆  │
├────────────┼─────────┼─────────┼─────────┼─────────┤
│ 综合评级    │ L2      │ L2      │ L2      │ L3      │
│ 可值班服务  │ 前端+后端│ 全栈    │ 前端+网络│ 全栈+安全│
└────────────┴─────────┴─────────┴─────────┴─────────┘
```

### 3. 告警分级与响应时效

#### 3.1 告警分级体系

```
┌───────────────────────────────────────────────────────────────┐
│                      告警分级体系                               │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│  级别     │  影响     │  响应时间 │  解决时间 │  示例             │
├──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ P0-Crit  │ 全站不可用 │ 5 分钟   │ 1 小时   │ 主站宕机          │
│          │ 大面积中断 │          │          │ 支付系统故障       │
│          │ 数据丢失   │          │          │ 数据库主库挂掉     │
├──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ P1-High  │ 核心功能   │ 15 分钟  │ 4 小时   │ 搜索功能异常       │
│          │ 降级可用   │          │          │ API 延迟飙升      │
│          │ 部分用户   │          │          │ 某个区域服务中断   │
├──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ P2-Med   │ 非核心功能 │ 1 小时   │ 24 小时  │ 推荐系统异常       │
│          │ 受限影响   │          │          │ 批处理任务延迟     │
│          │ 有变通方案 │          │          │ 日志采集延迟       │
├──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ P3-Low   │ 轻微影响   │ 下一工作 │ 1 周     │ UI 显示异常        │
│          │ 无直接用户 │ 日       │          │ 非关键告警         │
│          │ 影响       │          │          │ 配额接近阈值       │
└──────────┴──────────┴──────────┴──────────┴──────────────────┘
```

#### 3.2 告警通知策略

```yaml
# 告警通知策略配置
alert_routing:
  P0_critical:
    channels:
      - phone_call         # 电话通知（必选）
      - sms                # 短信通知
      - slack_urgent       # Slack 紧急频道
      - pagerduty          # PagerDuty 触发
    notify:
      - primary_oncall     # 主值班
      - secondary_oncall   # 副值班（5 分钟后）
      - engineering_manager # 工程经理（15 分钟后）
      - vp_engineering     # VP（30 分钟后）
    auto_escalation: true
    escalation_interval: "5min"
  
  P1_high:
    channels:
      - slack_alert        # Slack 告警频道
      - pagerduty          # PagerDuty 触发
    notify:
      - primary_oncall
      - secondary_oncall   # 15 分钟后
    auto_escalation: true
    escalation_interval: "15min"
  
  P2_medium:
    channels:
      - slack_info         # Slack 信息频道
      - email              # 邮件通知
    notify:
      - primary_oncall
    auto_escalation: false
  
  P3_low:
    channels:
      - slack_info
    notify:
      - on_call_dashboard  # 仪表盘展示
    auto_escalation: false
    batch_window: "1h"     # 1 小时内合并通知
```

#### 3.3 升级策略（Escalation Policy）

升级策略确保告警不会被遗漏：

```
告警触发
    │
    ▼
┌─────────────┐    5min 未确认    ┌──────────────┐
│ Primary     │ ───────────────→ │ Secondary    │
│ On-Call     │                   │ On-Call      │
└──────┬──────┘                   └──────┬───────┘
       │                                  │
       │ 已确认                            │ 15min 未确认
       ▼                                  ▼
┌─────────────┐                   ┌──────────────┐
│ 开始处理     │                   │ Team Lead    │
│ 执行 Runbook │                   │ / Manager    │
└──────┬──────┘                   └──────┬───────┘
       │                                  │
       │ 30min 未解决                      │ 30min 未解决
       ▼                                  ▼
┌─────────────┐                   ┌──────────────┐
│ 升级到 L2   │                   │ VP / CTO     │
│ 高级工程师   │                   │ 全员动员      │
└─────────────┘                   └──────────────┘
```

### 4. Runbook 编写

#### 4.1 Runbook 的定义与价值

Runbook（运行手册）是预定义的、可执行的操作步骤，用于处理已知的告警和故障场景。Google SRE Book 强调：

> "The best incident response is one that has been practiced and documented before the incident occurs."

Runbook 的价值：

- **降低 MTTD（平均检测时间）**：快速识别问题类型
- **降低 MTTR（平均恢复时间）**：标准化恢复步骤
- **减少对专家的依赖**：任何 On-Call 工程师都能处理
- **知识传承**：避免"只有一个人能处理"的困境

#### 4.2 Runbook 模板

```markdown
# Runbook: [告警名称]

## 基本信息
| 字段 | 内容 |
|------|------|
| 告警名称 | Prometheus Alert: HighErrorRate |
| 严重级别 | P1-High |
| 影响服务 | user-service |
| 通知渠道 | #alerts-critical |
| 文档更新日期 | 2026-04-15 |

## 告警描述
user-service 的 HTTP 5xx 错误率在过去 5 分钟内超过 5%，
表明服务可能存在严重问题。

## 影响范围
- 受影响用户：所有 user-service 用户（约 200 万 DAU）
- 受影响功能：用户注册、登录、个人信息修改
- 预计业务损失：每分钟约 5000 元

## 前置条件
- [ ] 确认告警不是误报（检查是否在维护窗口）
- [ ] 确认近期是否有变更（部署、配置修改、数据库变更）
- [ ] 确认相关监控面板数据

## 诊断步骤

### Step 1: 确认服务状态
```bash
# 检查 Pod 状态
kubectl get pods -n production -l app=user-service

# 检查最近事件
kubectl get events -n production --sort-by='.lastTimestamp' | head -20

# 检查 Deployment 状态
kubectl describe deployment user-service -n production
```

### Step 2: 检查日志
```bash
# 查看最近的错误日志
kubectl logs -n production -l app=user-service --tail=100 --since=10m | grep -i error

# 检查 OOMKilled
kubectl get pods -n production -l app=user-service -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState}{"\n"}{end}'
```

### Step 3: 检查资源使用
```bash
# CPU 和内存使用情况
kubectl top pods -n production -l app=user-service

# 检查 HPA 状态
kubectl get hpa -n production user-service
```

### Step 4: 检查依赖服务
```bash
# 检查数据库连接
kubectl exec -it deploy/user-service -n production -- curl -s localhost:8080/health

# 检查下游服务
kubectl exec -it deploy/user-service -n production -- curl -s localhost:8080/dependencies
```

## 恢复步骤

### 方案 A: 最近有新部署（回滚）
```bash
# 查看最近的部署历史
kubectl rollout history deployment/user-service -n production

# 回滚到上一个版本
kubectl rollout undo deployment/user-service -n production

# 监控回滚状态
kubectl rollout status deployment/user-service -n production --timeout=300s
```

### 方案 B: 资源不足（扩容）
```bash
# 临时手动扩容
kubectl scale deployment user-service -n production --replicas=10

# 确认扩容完成
kubectl get pods -n production -l app=user-service -w
```

### 方案 C: 依赖服务异常
```bash
# 如果是数据库问题，联系 DBA
# 如果是下游服务问题，通知下游 On-Call
# 同时启用降级模式（如果支持）
```

## 验证恢复
```bash
# 检查错误率恢复
curl -s 'http://prometheus:9090/api/v1/query?query=rate(http_requests_total{service="user-service",code=~"5.."}[5m]) / rate(http_requests_total{service="user-service"}[5m])'

# 检查 Pod 全部 Running
kubectl get pods -n production -l app=user-service

# 进行 smoke test
curl -s https://api.example.com/user-service/health
```

## 后续动作
- [ ] 在 Slack #incidents 频道更新状态
- [ ] 如果影响超过 30 分钟，通知相关业务方
- [ ] 记录事件时间线
- [ ] 安排事后复盘（如果需要）
```

#### 4.3 Runbook 最佳实践

```
┌─────────────────────────────────────────────────────────┐
│                 Runbook 最佳实践                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 可执行性                                             │
│     • 每个步骤都有具体命令                               │
│     • 命令可以直接复制粘贴执行                            │
│     • 明确说明每个命令的预期输出                          │
│                                                         │
│  2. 原子性                                               │
│     • 每个恢复方案独立完整                               │
│     • 步骤间有明确的判断条件                              │
│     • 失败时有回退方案                                   │
│                                                         │
│  3. 可维护性                                             │
│     • 定期 review 和更新                                 │
│     • 每次事故后补充新场景                               │
│     • 有明确的文档负责人                                 │
│                                                         │
│  4. 可发现性                                             │
│     • 与告警规则关联                                     │
│     • 统一目录结构                                       │
│     • 支持全文搜索                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5. 告警疲劳治理

#### 5.1 告警疲劳的危害

告警疲劳（Alert Fatigue）是 On-Call 中最严重的问题之一。当工程师收到过多无意义的告警时，会产生以下后果：

```
告警过多 → 习惯性忽略 → 真实告警被错过 → 事故扩大 → 信任危机
    │                                                        │
    └────────────────── 恶性循环 ──────────────────────────┘
```

#### 5.2 告警疲劳指标

```yaml
# 告警健康度指标
alert_health_metrics:
  # 每周人均告警数（目标：< 10）
  alerts_per_person_per_week: 8
  
  # 可操作告警比例（目标：> 90%）
  actionable_ratio: 0.92
  
  # 告警-事故转化率（目标：> 30%）
  alert_to_incident_ratio: 0.35
  
  # 平均告警确认时间（目标：< 5min）
  mean_time_to_acknowledge: "3min"
  
  # 重复告警比例（目标：< 10%）
  duplicate_ratio: 0.08
  
  # 无效告警比例（目标：< 5%）
  noise_ratio: 0.04
```

#### 5.3 告警治理策略

**策略 1：USE 方法 + RED 方法筛选**

```
USE 方法（基础设施）：
├── Utilization（利用率）：CPU > 80%, 内存 > 85%
├── Saturation（饱和度）：队列深度 > 100, 等待线程 > 50
└── Errors（错误数）：磁盘错误 > 0, 网络丢包 > 0.1%

RED 方法（服务层面）：
├── Rate（请求速率）：QPS 突降 50%+
├── Errors（错误率）：5xx > 1%
└── Duration（延迟）：P99 > 2x 基线
```

**策略 2：告警四象限分类**

```
                    高影响
                      │
         ┌────────────┼────────────┐
         │  立即告警    │   立即告警   │
         │  (高急高响)  │  (高急高响)  │
         │  P0/P1      │   P0/P1     │
    高急 ├────────────┼────────────┤ 低急
         │  记录+聚合   │   删除告警   │
         │  (低急高响)  │  (低急低响)  │
         │  P2/P3      │   不告警     │
         └────────────┼────────────┘
                      │
                    低影响
```

**策略 3：告警合并与去重**

```python
# 告警去重逻辑示例
class AlertDeduplicator:
    def __init__(self, window_seconds=300):
        self.window = window_seconds
        self.seen_alerts = {}
    
    def should_fire(self, alert):
        key = f"{alert.name}:{alert.labels}"
        now = time.time()
        
        if key in self.seen_alerts:
            last_fired = self.seen_alerts[key]
            if now - last_fired < self.window:
                return False  # 窗口内重复，不触发
        
        self.seen_alerts[key] = now
        return True

# 告警聚合逻辑示例
class AlertAggregator:
    """
    将同一服务的多个相关告警聚合为一个通知
    例如：CPU高 + 内存高 + 错误率高 → 聚合为一个告警
    """
    def __init__(self, aggregation_window=60):
        self.window = aggregation_window
        self.buffer = defaultdict(list)
    
    def add_alert(self, alert):
        service = alert.labels.get('service')
        self.buffer[service].append(alert)
    
    def flush(self):
        for service, alerts in self.buffer.items():
            if len(alerts) >= 3:  # 3+ 告警聚合
                self.send_aggregated(service, alerts)
            else:
                for alert in alerts:
                    self.send_individual(alert)
```

**策略 4：告警抑制**

```yaml
# Prometheus 告警抑制规则
inhibit_rules:
  # 如果 P0 告警已触发，抑制同一服务的 P2/P3 告警
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['service', 'instance']
  
  # 如果节点宕机，抑制该节点上所有 Pod 的告警
  - source_match:
      alertname: 'NodeDown'
    target_match_re:
      alertname: '.*'
    equal: ['node']
```

### 6. 值班工具：PagerDuty 与 OpsGenie

#### 6.1 PagerDuty

PagerDuty 是最流行的 On-Call 管理工具之一，核心功能包括：

```
┌─────────────────────────────────────────────────────────┐
│                   PagerDuty 架构                         │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ 监控源    │    │ 事件路由  │    │ 升级策略  │          │
│  │          │    │          │    │          │          │
│  │ Prometheus│──→│ 规则匹配  │──→│ 通知值班  │          │
│  │ Datadog  │    │ 服务映射  │    │ 人员     │          │
│  │ CloudWatch│    │ 优先级   │    │          │          │
│  └──────────┘    └──────────┘    └─────┬────┘          │
│                                        │               │
│                                        ▼               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ 分析报告  │    │ 状态更新  │    │ 通知渠道  │          │
│  │          │    │          │    │          │          │
│  │ 响应时间  │←──│ 事件日志  │←──│ 电话     │          │
│  │ MTTA/MTTR│    │ 时间线   │    │ 短信     │          │
│  │ 趋势分析  │    │ 指挥协调  │    │ App推送   │          │
│  └──────────┘    └──────────┘    │ Slack    │          │
│                                  └──────────┘          │
└─────────────────────────────────────────────────────────┘
```

**PagerDuty 配置示例：**

```json
{
  "service": {
    "name": "user-service-production",
    "escalation_policy": {
      "id": "P_ONCALL_ESCALATION",
      "name": "User Service Escalation",
      "escalation_rules": [
        {
          "escalation_delay_in_minutes": 5,
          "targets": [
            { "id": "P_PRIMARY", "type": "schedule_reference" }
          ]
        },
        {
          "escalation_delay_in_minutes": 15,
          "targets": [
            { "id": "P_SECONDARY", "type": "schedule_reference" }
          ]
        },
        {
          "escalation_delay_in_minutes": 30,
          "targets": [
            { "id": "P_MANAGER", "type": "user_reference" }
          ]
        }
      ]
    },
    "incident_urgency_rules": [
      {
        "type": "use_support_hours",
        "during_support_hours": { "urgency": "high" },
        "outside_support_hours": { "urgency": "low" }
      }
    ]
  }
}
```

#### 6.2 OpsGenie

OpsGenie（现属 Atlassian）是另一个流行的告警管理平台：

**OpsGenie 与 PagerDuty 对比：**

```
┌──────────────┬──────────────────┬──────────────────┐
│ 功能          │ PagerDuty        │ OpsGenie          │
├──────────────┼──────────────────┼──────────────────┤
│ 告警路由      │ ★★★★★           │ ★★★★☆            │
│ 升级策略      │ ★★★★★           │ ★★★★★            │
│ 调度管理      │ ★★★★★           │ ★★★★☆            │
│ 协作功能      │ ★★★★☆           │ ★★★★★            │
│ 分析报告      │ ★★★★★           │ ★★★★☆            │
│ 价格          │ 较高             │ 中等              │
│ Jira 集成     │ ★★★★☆           │ ★★★★★            │
│ 自定义集成    │ ★★★★★           │ ★★★★☆            │
│ 生态系统      │ 更成熟           │ 快速增长           │
└──────────────┴──────────────────┴──────────────────┘
```

#### 6.3 开源替代方案

```
┌─────────────────────────────────────────────────────────┐
│                  开源 On-Call 工具                        │
├──────────────┬──────────────────────────────────────────┤
│ Grafana      │ 告警路由、升级策略、                      │
│ OnCall      │ 调度管理、与 Grafana 深度集成              │
│              │ GitHub: grafana/oncall                    │
├──────────────┼──────────────────────────────────────────┤
│ Cabot        │ 轻量级监控和告警                          │
│              │ 适合小团队                                │
├──────────────┼──────────────────────────────────────────┤
│ OpenDuty     │ PagerDuty 开源替代                       │
│              │ 基于 Python                               │
├──────────────┼──────────────────────────────────────────┤
│ Botkube      │ Kubernetes 原生告警                      │
│              │ Slack/Teams 集成                          │
└──────────────┴──────────────────────────────────────────┘
```

### 7. 值班后复盘

#### 7.1 复盘流程

值班后复盘（Post-Shift Review）是持续改进 On-Call 体验的关键环节：

```
值班结束
    │
    ▼
┌─────────────┐
│ 数据收集     │  • 告警数量和分布
│ (自动化)     │  • MTTA / MTTR
│              │  • 升级次数
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 自我回顾     │  • 有哪些告警是可以自动化的？
│ (值班工程师) │  • 有哪些 Runbook 需要更新？
│              │  • 是否遇到了未知问题？
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 团队复盘     │  • 每周值班回顾会议
│ (周会)       │  • 分享经验和教训
│              │  • 讨论改进措施
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 持续改进     │  • 更新 Runbook
│ (Action)     │  • 调整告警规则
│              │  • 优化自动化
└─────────────┘
```

#### 7.2 值班报告模板

```markdown
# 值班报告 - [姓名] - [日期范围]

## 概览
| 指标 | 数值 |
|------|------|
| 值班时长 | 7 天 (Mon-Sun) |
| 告警总数 | 23 |
| 可操作告警 | 19 (82.6%) |
| 需要人工处理 | 5 |
| MTTA（平均确认时间） | 4.2 分钟 |
| MTTR（平均恢复时间） | 28 分钟 |
| 升级次数 | 1 |
| 误报告警 | 4 |

## 重要事件
### 事件 1: 2026-04-28 数据库连接池耗尽
- **触发时间**: 03:15
- **恢复时间**: 03:42
- **影响**: user-service 5xx 错误率升至 12%
- **处理方式**: 重启应用实例释放连接池
- **根因**: 慢查询导致连接未及时释放

## 改进建议
1. [ ] 优化数据库慢查询（@DBA Team, 优先级：高）
2. [ ] 添加连接池监控告警阈值（@SRE Team, 优先级：中）
3. [ ] 更新 Runbook：添加连接池相关排查步骤（@On-Call, 本周完成）
4. [ ] 删除过期告警规则：disk_usage_warning_staging（@SRE Team, 低优先级）

## 告警质量反馈
| 告警名称 | 是否可操作 | 建议 |
|----------|-----------|------|
| HighCPUProduction | 是 | 保持 |
| DiskWarnStaging | 否 | 删除 - 从未需要处理 |
| LatencyP99High | 是 | 保持 |
| CertExpiry30Days | 部分 | 改为提前 7 天告警 |
```

---

## 💻 实战练习

### 练习 1：设计 On-Call 轮换方案

**场景**：你的团队有 8 名 SRE 工程师，需要为一个 7x24 的生产系统设计 On-Call 方案。

**要求**：
1. 设计主备轮换方案
2. 定义各级别告警的响应时效
3. 编写升级策略
4. 考虑节假日安排

**参考方案**：

```python
# oncall_rotation.py
from datetime import datetime, timedelta

class OnCallRotation:
    def __init__(self, team_members):
        self.team = team_members
        self.rotation = []
        self.build_rotation()
    
    def build_rotation(self):
        """
        8 人团队，主备轮换
        每人每 8 周值班 1 周（主） + 1 周（备）
        两次值班间隔至少 6 周
        """
        n = len(self.team)
        for week in range(n):
            primary_idx = week % n
            secondary_idx = (week + 1) % n
            self.rotation.append({
                'week': week + 1,
                'primary': self.team[primary_idx],
                'secondary': self.team[secondary_idx],
            })
    
    def get_oncall(self, date):
        week_num = date.isocalendar()[1] % len(self.rotation)
        return self.rotation[week_num]
    
    def is_holiday(self, date):
        holidays = [
            '2026-01-01', '2026-01-29', '2026-01-30',
            '2026-04-05', '2026-05-01', '2026-06-25',
            '2026-10-01', '2026-10-02', '2026-10-03',
        ]
        return date.strftime('%Y-%m-%d') in holidays

# 使用示例
team = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Henry']
rotation = OnCallRotation(team)
today = datetime.now()
oncall = rotation.get_oncall(today)
print(f"今日主值班: {oncall['primary']}, 副值班: {oncall['secondary']}")
```

### 练习 2：编写 Runbook

**场景**：为以下告警编写完整的 Runbook：
- `RedisMemoryHigh` - Redis 内存使用率超过 85%

**要求**：
1. 包含完整的诊断步骤
2. 包含至少 2 种恢复方案
3. 包含验证步骤
4. 包含后续动作

```markdown
# Runbook: RedisMemoryHigh

## 告警描述
Redis 实例内存使用率超过 85%，可能导致新写入失败或
Redis 服务不可用。

## 前置检查
- [ ] 确认告警实例（主库 or 从库）
- [ ] 检查是否有近期大批量数据导入
- [ ] 检查是否有慢查询

## 诊断步骤

### Step 1: 确认内存使用
```bash
redis-cli -h <host> -p <port> info memory
# 关注 used_memory_human 和 maxmemory_human
```

### Step 2: 分析 Key 分布
```bash
# 大 Key 扫描
redis-cli -h <host> -p <port> --bigkeys

# 检查过期策略
redis-cli -h <host> -p <port> config get maxmemory-policy
```

### Step 3: 检查慢日志
```bash
redis-cli -h <host> -p <port> slowlog get 20
```

## 恢复方案

### 方案 A: 清理过期数据
```bash
# 检查有哪些大 Key
redis-cli -h <host> -p <port> --bigkeys

# 手动删除无用大 Key（谨慎操作）
redis-cli -h <host> -p <port> del <key_name>
```

### 方案 B: 扩容内存
```bash
# 如果是 ElastiCache
aws elasticache modify-cache-cluster \
  --cache-cluster-id <cluster-id> \
  --cache-node-type cache.r6g.xlarge

# 如果是自建 Redis
# 修改 maxmemory 配置并重启
```

## 验证
```bash
redis-cli -h <host> -p <port> info memory | grep used_memory
# 确认内存使用率降到 70% 以下
```
```

### 练习 3：告警疲劳分析

**场景**：分析以下告警数据，识别需要治理的告警规则。

```python
# alert_analysis.py
import json
from collections import Counter, defaultdict

# 模拟一周的告警数据
alerts = [
    {"name": "HighCPU", "service": "api", "time": "2026-04-21 08:00", "actionable": True},
    {"name": "HighCPU", "service": "api", "time": "2026-04-21 08:05", "actionable": True},
    {"name": "HighCPU", "service": "api", "time": "2026-04-21 08:10", "actionable": True},
    {"name": "DiskWarn", "service": "staging", "time": "2026-04-21 10:00", "actionable": False},
    {"name": "DiskWarn", "service": "staging", "time": "2026-04-22 10:00", "actionable": False},
    {"name": "DiskWarn", "service": "staging", "time": "2026-04-23 10:00", "actionable": False},
    {"name": "CertExpiry", "service": "web", "time": "2026-04-24 09:00", "actionable": True},
    {"name": "LatencyHigh", "service": "api", "time": "2026-04-25 14:00", "actionable": True},
    # ... 更多告警
]

def analyze_alerts(alerts):
    """分析告警质量，提出治理建议"""
    
    # 统计告警分布
    alert_counts = Counter(a['name'] for a in alerts)
    
    # 统计不可操作告警
    non_actionable = [a for a in alerts if not a['actionable']]
    non_actionable_counts = Counter(a['name'] for a in non_actionable)
    
    # 统计重复告警（同名同服务 5 分钟内多次触发）
    duplicate_groups = defaultdict(list)
    for a in alerts:
        key = f"{a['name']}:{a['service']}"
        duplicate_groups[key].append(a['time'])
    
    print("=== 告警质量分析报告 ===\n")
    print(f"告警总数: {len(alerts)}")
    print(f"可操作告警: {sum(1 for a in alerts if a['actionable'])}")
    print(f"不可操作告警: {len(non_actionable)}")
    
    print("\n--- 建议删除的告警规则 ---")
    for name, count in non_actionable_counts.most_common():
        print(f"  {name}: {count} 次不可操作，建议删除或调整")
    
    print("\n--- 需要去重的告警 ---")
    for key, times in duplicate_groups.items():
        if len(times) > 2:
            print(f"  {key}: {len(times)} 次触发，建议添加去重规则")

analyze_alerts(alerts)
```

---

## 🎯 面试题精选

### 面试题 1：请设计一个 On-Call 值班方案

**考察点**：对 On-Call 制度的整体理解，包括轮换、升级、补偿。

**参考答案要点**：
1. 采用主备轮换，确保有备份
2. 轮换周期为 1 周，最少 4 人参与
3. 定义 P0-P3 告警级别和响应时效
4. 设置升级策略（Primary → Secondary → Manager → VP）
5. 节假日有额外补偿
6. 每周进行值班回顾

### 面试题 2：什么是告警疲劳？如何治理？

**考察点**：对告警质量问题的理解和解决能力。

**参考答案要点**：
1. 告警疲劳是指工程师因收到过多无意义告警而对所有告警麻木
2. 治理方法：USE/RED 方法筛选、四象限分类、告警合并去重、告警抑制
3. 监控告警健康度指标（可操作率、转化率等）
4. 定期 review 告警规则，删除无效告警

### 面试题 3：Runbook 应该包含哪些内容？

**考察点**：对标准化操作文档的理解。

**参考答案要点**：
1. 基本信息（告警名称、级别、影响服务）
2. 告警描述和影响范围
3. 前置检查条件
4. 诊断步骤（具体命令和预期输出）
5. 恢复方案（多个方案，每个独立完整）
6. 验证步骤
7. 后续动作

### 面试题 4：如何评估一个 On-Call 体系的好坏？

**考察点**：对 On-Call 质量指标的理解。

**参考答案要点**：
1. MTTA（平均确认时间）< 5 分钟
2. MTTR（平均恢复时间）满足 SLO
3. 每周人均告警数 < 10
4. 可操作告警比例 > 90%
5. 工程师满意度调查
6. 值班报告质量

### 面试题 5：P0 和 P2 告警在响应流程上有什么区别？

**考察点**：对告警分级和升级策略的理解。

**参考答案要点**：
1. P0：电话通知、5 分钟响应、立即升级、全员通知
2. P2：Slack 通知、1 小时响应、不自动升级、下一工作日处理
3. 通知渠道不同（电话 vs Slack）
4. 升级策略不同（自动 vs 不升级）
5. 沟通频率不同（每 15 分钟更新 vs 每日更新）

### 面试题 6：如何处理 On-Call 中的"狼来了"问题？

**考察点**：对告警质量影响工程师行为的理解。

**参考答案要点**：
1. "狼来了"指过多误报导致工程师不再信任告警
2. 解决方案：严格告警准入标准、定期清理无效告警
3. 引入告警健康度指标和定期 review 机制
4. 使用告警分级让重要告警脱颖而出

### 面试题 7：Follow-the-Sun 模式的优缺点是什么？

**考察点**：对不同值班模式的理解。

**参考答案要点**：
1. 优点：无夜间值班、工程师工作生活平衡好
2. 缺点：需要跨时区团队、交接成本高、沟通协调复杂
3. 适用场景：全球化公司、有多个研发中心
4. 关键挑战：交接质量、知识传递、时区差异

### 面试题 8：PagerDuty 和 OpsGenie 你会选哪个？为什么？

**考察点**：对工具选型的理解和实际使用经验。

**参考答案要点**：
1. 两者都是成熟的商业产品
2. PagerDuty 告警路由和分析更强，价格较高
3. OpsGenie 与 Jira/Atlassian 生态集成更好，价格适中
4. 选择考虑因素：团队规模、预算、已有工具链、集成需求

---

## 📚 深入阅读

### 官方文档与书籍
- [Google SRE Book - Chapter 11: Being On-Call](https://sre.google/sre-book/being-on-call/) - On-Call 的理论基础
- [Google SRE Workbook - On-Call](https://sre.google/workbook/on-call/) - 实践指导
- [PagerDuty Documentation](https://support.pagerduty.com/) - 工具文档
- [OpsGenie Documentation](https://docs.opsgenie.com/) - 工具文档
- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/) - 开源替代方案

### 推荐文章
- [Incident Management for Operations - Rob Schnepp](https://www.oreilly.com/library/view/incident-management-for/9781491917619/)
- [The On-Call Handbook - Julia Evans](https://jvns.ca/blog/2023/07/26/on-call/)
- [Alert Fatigue and How to Combat It](https://www.pagerduty.com/resources/learn/alert-fatigue/)

### 实践工具
- [PagerDuty Incident Response Documentation](https://response.pagerduty.com/) - 事故响应指南
- [SRE Weekly Newsletter](https://sreweekly.com/) - SRE 周刊
- [On-Call Rotation Calculator](https://www.when2meet.com/) - 排班协调工具

---

## ✅ 自检清单

- [ ] 能设计合理的 On-Call 主备轮换方案
- [ ] 能定义 P0-P3 告警分级和响应时效
- [ ] 能编写结构完整的 Runbook
- [ ] 能识别告警疲劳问题并提出治理方案
- [ ] 了解 PagerDuty / OpsGenie 的核心功能和配置
- [ ] 能设计升级策略（Escalation Policy）
- [ ] 理解 Google SRE 对 On-Call 的 50% 规则和事件量上限
- [ ] 能编写值班报告并进行值班后复盘
