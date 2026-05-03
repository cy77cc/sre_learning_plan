# Day 174: 事故管理与 RCA

> 📅 日期：2026-05-03
> 📖 学习主题：事故管理与 RCA — 事故生命周期、响应流程、指挥体系 ICS、5 Whys、鱼骨图、时间线重建、事后复盘文化、无指责复盘
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 173（On-Call 实践）

---

## 🎯 学习目标

完成 Day 174 的学习后，你应该掌握：

- 理解事故管理的完整生命周期（检测→响应→恢复→复盘）
- 运用 ICS（事故指挥体系）进行有效的事故协调
- 掌握 5 Whys、鱼骨图等 RCA 根因分析方法
- 能够重建事故时间线并编写高质量的事后复盘报告
- 建立无指责复盘文化，推动组织学习
- 理解 MTTR、MTTD 等关键指标的含义和优化方向

---

## 📖 核心知识点

### 1. 事故管理概述

#### 1.1 什么是事故（Incident）

在 SRE 语境中，事故是指导致服务中断或服务质量下降的非计划事件。Google SRE Book 将事故定义为：

> "An incident is an event that leads to a reduction in the quality of service or threatens to do so."

事故与事件（Event）的区别：

```
┌─────────────────────────────────────────────────────────┐
│           事件 vs 事故 vs 灾难                            │
│                                                         │
│  事件 (Event)                                            │
│  └─ 系统中发生的任何可观察的变化                          │
│     例：CPU 使用率从 30% 升到 70%                        │
│                                                         │
│  事故 (Incident)                                         │
│  └─ 影响服务质量的事件，需要响应                          │
│     例：API 延迟从 100ms 升到 2s，用户投诉增加            │
│                                                         │
│  重大事故 (Major Incident)                               │
│  └─ 严重影响业务的事故，需要全组织响应                    │
│     例：全站宕机 30 分钟，影响数百万用户                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 Google SRE 的事故管理原则

Google SRE Book 提出了几个核心原则：

**1. 优先恢复，事后分析**
> "The first priority during an incident is to restore service, not to find the root cause."

在事故响应中，恢复服务是第一优先级。不要在事故进行中花大量时间找根因。

**2. 无指责文化（Blameless Culture）**
> "Blame is the enemy of learning."

指责个人会抑制信息共享和学习。事后复盘应聚焦于系统和流程的改进。

**3. 事后复盘是必须的**
> "Postmortems are a mandatory practice for any significant incident."

每次重大事故都应有事后复盘，这是组织学习的核心机制。

### 2. 事故生命周期

#### 2.1 完整生命周期

```
                    事故管理生命周期
                    
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  │   检测        分类        响应        恢复       │
  │   Detect  →  Triage  →  Respond  →  Resolve     │
  │     │          │          │          │           │
  │     ▼          ▼          ▼          ▼           │
  │  告警触发    确认级别    指挥协调    服务恢复     │
  │  用户报告    分配人员    诊断排查    验证确认     │
  │  监控发现    通知相关方  执行恢复    监控观察     │
  │                                                  │
  │   复盘        改进        归档                    │
  │   Review  →  Improve  →  Archive                 │
  │     │          │          │                      │
  │     ▼          ▼          ▼                      │
  │  时间线重建  Action Item  知识库                  │
  │  根因分析    跟踪落实    文档归档                 │
  │  无指责会议  优先级排序  趋势分析                 │
  │                                                  │
  └──────────────────────────────────────────────────┘
```

#### 2.2 检测阶段（Detect）

检测是事故生命周期的起点。检测来源包括：

```yaml
detection_sources:
  automated:
    - name: "Prometheus 告警"
      description: "基于指标阈值的自动告警"
      example: "HTTP 5xx 错误率 > 5% 持续 5 分钟"
      mttt: "1-5 分钟"
    
    - name: "日志告警"
      description: "基于日志模式的自动告警"
      example: "ERROR 级别日志突增 10x"
      mttt: "1-10 分钟"
    
    - name: "合成监控"
      description: "模拟用户行为的主动探测"
      example: "登录流程成功率 < 99%"
      mttt: "1-5 分钟"
  
  manual:
    - name: "用户报告"
      description: "用户通过客服或社交媒体报告"
      example: "用户在 Twitter 反馈无法下单"
      mttt: "10-60 分钟"
    
    - name: "内部发现"
      description: "工程师在工作中发现异常"
      example: "开发人员发现测试环境数据异常"
      mttt: "不固定"

  mttt_mean: "Mean Time To Detect - 平均检测时间"
```

#### 2.3 分类阶段（Triage）

分类阶段的核心任务是快速评估事故的严重程度并分配资源：

```
事故报告
    │
    ▼
┌─────────────────────────────────────┐
│         快速评估（< 5 分钟）          │
│                                     │
│  1. 影响范围有多大？                  │
│     □ 全部用户  □ 部分用户  □ 内部    │
│                                     │
│  2. 核心功能是否受影响？              │
│     □ 完全不可用  □ 降级  □ 无影响    │
│                                     │
│  3. 是否有数据丢失风险？              │
│     □ 是    □ 否    □ 不确定         │
│                                     │
│  4. 是否正在恶化？                    │
│     □ 是（扩大中）  □ 否（稳定）     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│         分级判定                      │
│                                     │
│  全部用户 + 核心不可用 + 数据丢失     │
│  → P0（全站事故）                    │
│                                     │
│  部分用户 + 核心降级                  │
│  → P1（重大事故）                    │
│                                     │
│  部分用户 + 非核心不可用              │
│  → P2（一般事故）                    │
│                                     │
│  内部用户 + 轻微影响                  │
│  → P3（轻微事故）                    │
└─────────────────────────────────────┘
```

#### 2.4 响应阶段（Respond）

响应阶段的核心是组织人员进行故障排查和恢复：

```
┌─────────────────────────────────────────────────────────┐
│                   事故响应流程                            │
│                                                         │
│  1. 告警触发                                             │
│     │                                                   │
│     ▼                                                   │
│  2. 值班工程师确认 → 是否误报？                           │
│     │                  │                                │
│     │ 不是误报          │ 是误报 → 关闭告警               │
│     ▼                                                   │
│  3. 判断严重程度 → 分配级别                               │
│     │                                                   │
│     ▼                                                   │
│  4. 通知相关人员                                         │
│     • P0: 全员通知 + 工程经理 + VP                       │
│     • P1: 值班团队 + 相关开发                             │
│     • P2: 值班工程师                                     │
│     │                                                   │
│     ▼                                                   │
│  5. 建立沟通渠道                                         │
│     • 创建 Slack 事故频道 #inc-YYYYMMDD-xxx              │
│     • 启动 Zoom 事故桥接（P0/P1）                        │
│     │                                                   │
│     ▼                                                   │
│  6. 诊断排查                                             │
│     • 检查近期变更                                       │
│     • 查看监控面板                                       │
│     • 分析日志                                           │
│     • 检查依赖服务                                       │
│     │                                                   │
│     ▼                                                   │
│  7. 执行恢复                                             │
│     • 回滚 / 重启 / 扩容 / 降级                          │
│     │                                                   │
│     ▼                                                   │
│  8. 验证恢复 → 观察 15 分钟                              │
│     │                                                   │
│     ▼                                                   │
│  9. 关闭事故，安排复盘                                    │
└─────────────────────────────────────────────────────────┘
```

#### 2.5 恢复阶段（Resolve）

恢复策略按优先级排列：

```
┌─────────────────────────────────────────────────────────┐
│                 恢复策略优先级                            │
│                                                         │
│  优先级 1: 回滚（Rollback）                              │
│  ┌──────────────────────────────────────────┐           │
│  │ 如果事故由最近的部署引起                    │           │
│  │ kubectl rollout undo deployment/xxx       │           │
│  │ 或 git revert + 重新部署                   │           │
│  │ 预计恢复时间: 5-15 分钟                    │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  优先级 2: 扩容（Scale Up）                              │
│  ┌──────────────────────────────────────────┐           │
│  │ 如果事故由资源不足引起                      │           │
│  │ kubectl scale deployment xxx --replicas=20│           │
│  │ 预计恢复时间: 2-5 分钟                     │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  优先级 3: 重启（Restart）                               │
│  ┌──────────────────────────────────────────┐           │
│  │ 如果事故由进程状态异常引起                  │           │
│  │ kubectl rollout restart deployment/xxx    │           │
│  │ 预计恢复时间: 1-3 分钟                     │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  优先级 4: 降级（Degrade）                               │
│  ┌──────────────────────────────────────────┐           │
│  │ 如果无法快速修复，启用降级模式              │           │
│  │ 关闭非核心功能、限制写入、使用缓存数据      │           │
│  │ 预计恢复时间: 5-30 分钟                    │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  优先级 5: 切换（Failover）                              │
│  ┌──────────────────────────────────────────┐           │
│  │ 如果单点故障，切换到备用系统                │           │
│  │ DNS 切换 / 数据库主从切换                  │           │
│  │ 预计恢复时间: 10-60 分钟                   │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 3. 事故指挥体系（ICS）

#### 3.1 ICS 角色定义

ICS（Incident Command System）源自应急管理领域，被 Google 和其他科技公司广泛采用：

```
┌─────────────────────────────────────────────────────────┐
│                 事故指挥体系 (ICS)                        │
│                                                         │
│              ┌──────────────┐                           │
│              │   Incident   │                           │
│              │   Commander  │                           │
│              │   (事故指挥官)│                           │
│              └──────┬───────┘                           │
│                     │                                   │
│     ┌───────────────┼───────────────┐                   │
│     │               │               │                   │
│     ▼               ▼               ▼                   │
│ ┌─────────┐   ┌──────────┐   ┌──────────┐              │
│ │  Tech   │   │Comms Lead│   │Planning/ │              │
│ │  Lead   │   │          │   │Ops Lead  │              │
│ │ 技术主管│   │ 沟通主管  │   │ 计划主管  │              │
│ └────┬────┘   └────┬─────┘   └────┬─────┘              │
│      │              │              │                    │
│      ▼              ▼              ▼                    │
│  ┌────────┐   ┌──────────┐   ┌──────────┐              │
│  │排查团队 │   │状态更新   │   │资源协调   │              │
│  │        │   │          │   │          │              │
│  │后端排查 │   │内部通知   │   │人员调配   │              │
│  │前端排查 │   │外部公告   │   │工具准备   │              │
│  │DB 排查  │   │用户沟通   │   │信息收集   │              │
│  └────────┘   └──────────┘   └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 各角色职责

**事故指挥官（Incident Commander）**：
- 全局掌控事故处理进度
- 分配和协调资源
- 做出关键决策（是否回滚、是否通知高管等）
- 确保沟通畅通
- 不直接参与技术排查（保持全局视角）

**技术主管（Tech Lead）**：
- 领导技术排查团队
- 分析日志、监控数据
- 执行恢复操作
- 向指挥官汇报技术进展

**沟通主管（Communications Lead）**：
- 定期更新内部状态（每 15 分钟 / 每 30 分钟）
- 管理对外公告（用户通知、媒体声明）
- 记录事故时间线
- 协调跨团队沟通

**计划主管（Planning/Ops Lead）**：
- 协调所需资源（人力、机器、权限）
- 跟踪所有 Action Item
- 管理后续跟进事项

#### 3.3 ICS 实践示例

```markdown
# 事故 #INC-20260428-001

## 指挥体系
| 角色 | 负责人 | 联系方式 |
|------|--------|----------|
| 事故指挥官 | Alice | Slack: @alice, Phone: 138xxxx |
| 技术主管 | Bob | Slack: @bob, Phone: 139xxxx |
| 沟通主管 | Carol | Slack: @carol, Phone: 137xxxx |
| 计划主管 | Dave | Slack: @dave, Phone: 136xxxx |

## 当前状态
- **级别**: P1
- **影响**: 用户下单功能异常，约 30% 用户受影响
- **开始时间**: 2026-04-28 14:30 UTC+8
- **当前阶段**: 排查中
- **指挥频道**: #inc-20260428-001
- **Zoom 桥接**: https://zoom.us/j/123456789

## 状态更新
| 时间 | 更新人 | 内容 |
|------|--------|------|
| 14:30 | Alice | 确认 P1 事故，启动 ICS |
| 14:45 | Bob | 发现 order-service 5xx 错误率 15% |
| 15:00 | Carol | 内部通知已发送，外部公告准备中 |
| 15:15 | Bob | 确认为最近部署引起，准备回滚 |
| 15:30 | Bob | 回滚完成，错误率降至 0.1% |
| 15:45 | Alice | 验证恢复，观察 15 分钟 |
| 16:00 | Alice | 确认恢复，关闭事故 |
```

### 4. 根因分析（RCA）方法

#### 4.1 5 Whys 方法

5 Whys 是最简单有效的根因分析方法，由丰田生产系统（TPS）发明：

```
问题：order-service 出现大量 5xx 错误

Why 1: 为什么出现 5xx 错误？
  → 因为数据库连接超时

Why 2: 为什么数据库连接超时？
  → 因为数据库连接池已满

Why 3: 为什么连接池已满？
  → 因为存在大量慢查询未释放连接

Why 4: 为什么存在大量慢查询？
  → 因为新加的索引查询使用了全表扫描

Why 5: 为什么新加的索引查询使用全表扫描？
  → 因为该索引在表数据量大时失效（缺少覆盖索引）

根本原因：新增索引设计不合理，缺少覆盖索引
改进措施：
1. 修复索引设计
2. 增加 SQL Review 流程
3. 添加慢查询监控告警
```

#### 4.2 鱼骨图（石川图 / 因果图）

鱼骨图适合分析复杂的、多因素导致的事故：

```
                         事故：API 延迟飙升
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
 人员因素       技术因素     流程因素     环境因素      外部因素
 (People)    (Technology)  (Process)  (Environment)  (External)
    │             │           │           │             │
    ├─新手值班    ├─连接池    ├─无慢查询  ├─流量突增    ├─上游服务
    │ 无 Runbook │  配置不当  │  监控     │  (促销活动) │  故障
    │             │           │           │             │
    ├─沟通不畅    ├─缓存     ├─部署未    ├─数据库      ├─DDoS
    │            │  命中率低  │  灰度发布 │  磁盘满     │  攻击
    │             │           │           │             │
    ├─缺乏经验    ├─日志     ├─无容量   ├─网络       ├─DNS
    │            │  过多     │  规划     │  抖动       │  解析慢
    │             │           │           │             │

         分析步骤：
         1. 列出每个分支的可能原因
         2. 通过数据验证每个假设
         3. 排除已确认的非原因
         4. 锁定根本原因
```

#### 4.3 时间线重建

时间线重建是 RCA 的基础，需要精确到分钟级别：

```
┌─────────────────────────────────────────────────────────┐
│              事故时间线：order-service 5xx                │
│                                                         │
│  时间 (UTC+8)    事件                       来源         │
│  ────────────    ─────────────────────     ──────       │
│  14:00          部署 order-service v2.3.1  CI/CD        │
│  14:05          部署完成，健康检查通过       K8s Events   │
│  14:10          慢查询数量开始增加          DB Metrics   │
│  14:15          连接池使用率 60% → 80%     App Metrics  │
│  14:20          P99 延迟 200ms → 1.5s     APM          │
│  14:25          5xx 错误率 0.1% → 8%      Prometheus   │
│  14:30          告警触发: HighErrorRate    Alertmanager │
│  14:32          Bob 确认告警               PagerDuty    │
│  14:35          创建事故频道               Slack        │
│  14:40          Alice 担任指挥官           Incident Log │
│  14:45          Bob 发现连接池耗尽         App Logs     │
│  14:50          决定回滚                   Incident Log │
│  14:55          回滚开始                   K8s Events   │
│  15:00          回滚完成                   K8s Events   │
│  15:05          5xx 错误率降至 0.5%       Prometheus   │
│  15:10          连接池恢复正常             App Metrics  │
│  15:15          验证用户下单功能正常        Smoke Test   │
│  15:30          关闭事故                   Incident Log │
│                                                         │
│  关键指标：                                              │
│  • MTTD（检测时间）: 25 分钟                             │
│  • MTTA（确认时间）: 2 分钟                              │
│  • MTTR（恢复时间）: 60 分钟                             │
│  • 影响时长: 25 分钟（14:05-14:30 未检测到）              │
└─────────────────────────────────────────────────────────┘
```

### 5. 事后复盘（Postmortem）

#### 5.1 事后复盘模板

```markdown
# 事故复盘报告

## 基本信息
| 字段 | 内容 |
|------|------|
| 事故编号 | INC-20260428-001 |
| 事故日期 | 2026-04-28 |
| 事故级别 | P1 - 重大事故 |
| 指挥官 | Alice Chen |
| 报告编写人 | Bob Wang |
| 复盘会议日期 | 2026-04-30 |

## 事故摘要
2026-04-28 14:30，order-service 出现大量 5xx 错误，约 30% 用户
无法完成下单。事故持续约 60 分钟，于 15:30 恢复。根本原因为
最新部署引入了不合理的数据库索引查询，导致连接池耗尽。

## 影响范围
- **受影响用户**: 约 60 万（DAU 200 万的 30%）
- **受影响功能**: 用户下单、支付确认
- **持续时间**: 60 分钟
- **业务损失**: 预估约 180 万元（基于日均 GMV 计算）
- **数据影响**: 无数据丢失

## 时间线
| 时间 (UTC+8) | 事件 |
|--------------|------|
| 14:00 | 部署 order-service v2.3.1 |
| 14:10 | 慢查询数量开始增加 |
| 14:25 | 5xx 错误率达到 8% |
| 14:30 | 告警触发 |
| 14:32 | 值班工程师确认 |
| 14:35 | 建立事故频道 |
| 14:45 | 定位到连接池问题 |
| 14:50 | 决定回滚 |
| 15:00 | 回滚完成 |
| 15:15 | 验证恢复 |
| 15:30 | 关闭事故 |

## 根因分析

### 5 Whys 分析
1. Why: 为什么出现 5xx？→ 数据库连接超时
2. Why: 为什么连接超时？→ 连接池已满
3. Why: 为什么连接池满？→ 大量慢查询占用连接
4. Why: 为什么有慢查询？→ 新加的索引查询导致全表扫描
5. Why: 为什么索引查询全表扫描？→ 索引设计缺少覆盖列

### 根本原因
order-service v2.3.1 引入的订单索引查询缺少覆盖索引，
在生产数据量（约 5000 万行）下导致全表扫描，每次查询耗时
从 10ms 飙升到 2s+，连接池（默认 100）被慢查询占满。

## 做得好的方面
- 告警在 25 分钟内触发（虽然可以更快）
- 值班工程师 2 分钟内确认
- 决策过程清晰，5 分钟内决定回滚
- 回滚操作顺利，5 分钟内完成
- 沟通及时，状态更新每 15 分钟

## 需要改进的方面
- 检测时间过长（25 分钟才发现问题）
- 部署前缺少 SQL Review
- 无慢查询监控告警
- Runbook 中缺少数据库连接池相关排查步骤
- 连接池配置未根据业务量调整

## Action Items
| 编号 | 行动项 | 优先级 | 负责人 | 截止日期 | 状态 |
|------|--------|--------|--------|----------|------|
| AI-1 | 修复订单索引，添加覆盖索引 | P0 | Bob | 2026-05-01 | Done |
| AI-2 | 建立 SQL Review 流程 | P1 | DBA Team | 2026-05-15 | In Progress |
| AI-3 | 添加慢查询监控告警 | P1 | SRE Team | 2026-05-08 | Done |
| AI-4 | 更新 Runbook | P2 | Bob | 2026-05-05 | Done |
| AI-5 | 优化连接池配置 | P2 | Bob | 2026-05-10 | In Progress |
| AI-6 | 增加部署前自动化测试 | P1 | Dev Team | 2026-05-20 | Todo |

## 经验教训
1. 部署前的代码 Review 应包含 SQL 性能检查
2. 连接池配置应根据业务量定期调整
3. 慢查询监控是必备的基础设施
4. 回滚是最有效的快速恢复手段，应确保回滚流程顺畅
```

### 6. 无指责复盘文化

#### 6.1 无指责复盘的核心理念

无指责复盘（Blameless Postmortem）是 Google SRE 的核心文化之一。其理念是：

```
┌─────────────────────────────────────────────────────────┐
│                无指责复盘 vs 指责文化                      │
│                                                         │
│  指责文化：                                               │
│  ┌───────────────────────────────────────┐               │
│  │ "Bob 部署了有 bug 的代码"               │               │
│  │ "Alice 没有及时发现告警"                │               │
│  │ "DBA 没有 Review SQL"                  │               │
│  │                                       │               │
│  │ 结果：                                 │               │
│  │ • 工程师害怕承认错误                    │               │
│  │ • 信息被隐藏                           │               │
│  │ • 同样的事故反复发生                    │               │
│  └───────────────────────────────────────┘               │
│                                                         │
│  无指责文化：                                             │
│  ┌───────────────────────────────────────┐               │
│  │ "部署流程缺少 SQL Review"              │               │
│  │ "告警检测时间过长"                     │               │
│  │ "监控覆盖不完整"                       │               │
│  │                                       │               │
│  │ 结果：                                 │               │
│  │ • 工程师愿意分享完整信息                │               │
│  │ • 系统性问题被识别和改进                │               │
│  │ • 组织持续学习和成长                    │               │
│  └───────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

#### 6.2 无指责复盘的实践要点

**1. 聚焦系统，而非个人**

```
错误示范：
"Bob 在没有测试的情况下就部署了代码"

正确示范：
"部署流程中缺少自动化测试和 SQL Review 环节"
```

**2. 假设善意（Assume Goodwill）**

```
错误示范：
"Alice 明明看到了告警，为什么没有立即处理？"

正确示范：
"告警到达 Alice 时，她正在处理另一个 P1 事故。
我们需要评估是否需要增加 On-Call 人数。"
```

**3. 关注"什么"而非"谁"**

```
错误示范：
"谁负责这个服务的部署？"

正确示范：
"这个服务的部署流程是什么？有哪些检查环节？"
```

**4. 承认复杂性**

```
现代系统是复杂适应性系统（Complex Adaptive System）。
事故往往是多个小因素叠加的结果，而非单一原因。

一个工程师的"错误"可能在不同的上下文中是"正确"的。
```

#### 6.3 无指责复盘会议流程

```
┌─────────────────────────────────────────────────────────┐
│               无指责复盘会议流程（60分钟）                 │
│                                                         │
│  0-5 min    开场                                        │
│             • 明确会议目标：学习和改进，非追责             │
│             • 确认所有人都理解无指责原则                   │
│                                                         │
│  5-15 min   时间线回顾                                   │
│             • 由参与者共同补充时间线                       │
│             • 不讨论原因，只确认事实                      │
│             • 记录到共享文档                              │
│                                                         │
│  15-35 min  根因分析                                     │
│             • 使用 5 Whys 或鱼骨图                       │
│             • 鼓励所有人发言                             │
│             • 不评判任何人的贡献                          │
│                                                         │
│  35-50 min  讨论改进措施                                 │
│             • 识别系统性改进机会                          │
│             • 讨论可行性                                  │
│             • 分配 Action Item                           │
│                                                         │
│  50-60 min  总结                                         │
│             • 确认 Action Item 和负责人                   │
│             • 设定 follow-up 会议时间                    │
│             • 收集会议反馈                                │
└─────────────────────────────────────────────────────────┘
```

### 7. 关键指标（MTTD / MTTR / MTTA）

```
┌─────────────────────────────────────────────────────────┐
│                  事故管理关键指标                          │
│                                                         │
│  时间轴：                                                │
│  事故    检测    确认    开始     恢复    验证            │
│  发生    到达    告警    响应     服务    完成            │
│   │       │       │       │       │       │            │
│   ▼       ▼       ▼       ▼       ▼       ▼            │
│   ────────┼───────┼───────┼───────┼───────┼──          │
│           │       │       │       │       │            │
│           │       │       │       │       │            │
│   │←──────┤       │       │       │       │            │
│   │ MTTD  │       │       │       │       │            │
│   │(检测)  │       │       │       │       │            │
│   │       │       │       │       │       │            │
│   │       │←──────┤       │       │       │            │
│   │       │ MTTA  │       │       │       │            │
│   │       │(确认)  │       │       │       │            │
│   │       │       │       │       │       │            │
│   │       │       │←──────┤       │       │            │
│   │       │       │MTTStart│      │       │            │
│   │       │       │(开始) │       │       │            │
│   │       │       │       │       │       │            │
│   │       │       │←──────┼───────┤       │            │
│   │       │       │ MTTR  │       │       │            │
│   │       │       │(恢复) │       │       │            │
│   │       │       │       │       │       │            │
│   │←──────┼───────┼───────┼───────┤       │            │
│   │       │   TTD + TTA + TTR    │       │            │
│   │       │   总影响时间           │       │            │
│                                                         │
│  MTTD: Mean Time To Detect  - 平均检测时间              │
│  MTTA: Mean Time To Acknowledge - 平均确认时间          │
│  MTTR: Mean Time To Recover  - 平均恢复时间             │
│  MTBF: Mean Time Between Failures - 平均故障间隔         │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：事故响应模拟

**场景**：你的电商系统在双十一期间出现以下告警：

```
告警: HighErrorRate
服务: payment-service
错误率: 15%
开始时间: 2026-11-11 10:00
```

**任务**：按 ICS 体系组织响应。

```python
# incident_response_simulation.py

class IncidentResponse:
    def __init__(self, incident_id, severity):
        self.incident_id = incident_id
        self.severity = severity
        self.timeline = []
        self.roles = {}
        self.status = "detected"
    
    def assign_role(self, role, person):
        self.roles[role] = person
        self.add_event(f"{role} assigned to {person}")
    
    def add_event(self, description):
        import time
        self.timeline.append({
            'time': time.strftime('%H:%M:%S'),
            'event': description
        })
    
    def assess_impact(self, affected_users, affected_functions, data_loss):
        """评估事故影响"""
        if affected_users == "all" and affected_functions == "core":
            return "P0"
        elif affected_users == "partial" and affected_functions == "core":
            return "P1"
        elif affected_functions == "non-core":
            return "P2"
        else:
            return "P3"
    
    def execute_recovery(self, strategy):
        """执行恢复策略"""
        strategies = {
            'rollback': self._rollback,
            'scale_up': self._scale_up,
            'restart': self._restart,
            'failover': self._failover,
        }
        if strategy in strategies:
            return strategies[strategy]()
        return "Unknown strategy"
    
    def _rollback(self):
        self.add_event("Executing rollback...")
        self.add_event("Rollback completed successfully")
        return "Rollback completed"
    
    def _scale_up(self):
        self.add_event("Scaling up replicas...")
        self.add_event("Scale up completed")
        return "Scale up completed"
    
    def _restart(self):
        self.add_event("Restarting services...")
        self.add_event("Restart completed")
        return "Restart completed"
    
    def _failover(self):
        self.add_event("Initiating failover...")
        self.add_event("Failover completed")
        return "Failover completed"
    
    def generate_report(self):
        """生成事故报告"""
        report = f"""
# 事故报告: {self.incident_id}
## 级别: {self.severity}
## 状态: {self.status}
## 指挥体系:
"""
        for role, person in self.roles.items():
            report += f"- {role}: {person}\n"
        
        report += "\n## 时间线:\n"
        for event in self.timeline:
            report += f"- [{event['time']}] {event['event']}\n"
        
        return report

# 模拟事故响应
incident = IncidentResponse("INC-20261111-001", "P1")
incident.assign_role("指挥官", "Alice")
incident.assign_role("技术主管", "Bob")
incident.assign_role("沟通主管", "Carol")
incident.add_event("告警触发: payment-service 错误率 15%")
incident.add_event("确认为 P1 事故")
incident.add_event("建立事故频道 #inc-20261111-001")
incident.add_event("Bob 开始排查")
incident.add_event("发现支付网关连接超时")
incident.execute_recovery("failover")
incident.status = "resolved"
print(incident.generate_report())
```

### 练习 2：5 Whys 根因分析

**场景**：分析以下事故的根本原因。

**事故描述**：2026-03-15 09:00，用户报告无法登录系统。排查发现 Redis 集群主节点内存溢出，导致所有依赖 Redis 的服务不可用。

```python
# five_whys_analysis.py

class FiveWhysAnalysis:
    def __init__(self, problem_statement):
        self.problem = problem_statement
        self.whys = []
        self.root_cause = None
        self.improvements = []
    
    def add_why(self, question, answer):
        self.whys.append({
            'level': len(self.whys) + 1,
            'question': question,
            'answer': answer
        })
    
    def set_root_cause(self, cause):
        self.root_cause = cause
    
    def add_improvement(self, action, priority, owner, deadline):
        self.improvements.append({
            'action': action,
            'priority': priority,
            'owner': owner,
            'deadline': deadline
        })
    
    def generate_report(self):
        report = f"# 5 Whys 分析报告\n\n"
        report += f"## 问题描述\n{self.problem}\n\n"
        report += f"## 5 Whys 分析\n"
        
        for why in self.whys:
            report += f"\n**Why {why['level']}**: {why['question']}\n"
            report += f"→ {why['answer']}\n"
        
        report += f"\n## 根本原因\n{self.root_cause}\n\n"
        report += f"## 改进措施\n"
        for i, imp in enumerate(self.improvements, 1):
            report += f"\n{i}. {imp['action']}\n"
            report += f"   - 优先级: {imp['priority']}\n"
            report += f"   - 负责人: {imp['owner']}\n"
            report += f"   - 截止日期: {imp['deadline']}\n"
        
        return report

# 进行分析
analysis = FiveWhysAnalysis(
    "2026-03-15 09:00 用户无法登录，Redis 集群主节点内存溢出"
)

analysis.add_why(
    "为什么用户无法登录？",
    "认证服务无法连接 Redis，所有登录请求返回 500 错误"
)
analysis.add_why(
    "为什么认证服务无法连接 Redis？",
    "Redis 主节点 OOM 被 kill，哨兵未能及时切换"
)
analysis.add_why(
    "为什么 Redis 主节点 OOM？",
    "Redis 内存使用率已达 98%，新写入触发 OOM"
)
analysis.add_why(
    "为什么内存使用率这么高？",
    "Session 缓存未设置过期时间，大量过期 session 堆积"
)
analysis.add_why(
    "为什么 Session 缓存未设置过期时间？",
    "上周上线新版本时修改了 Redis 配置，漏掉了 TTL 设置"
)

analysis.set_root_cause(
    "Redis 配置变更缺少 Review 和测试环节，导致 Session TTL 被移除"
)

analysis.add_improvement(
    "修复 Redis Session TTL 配置", "P0", "Dev Team", "2026-03-16"
)
analysis.add_improvement(
    "建立 Redis 配置变更 Review 流程", "P1", "SRE Team", "2026-03-30"
)
analysis.add_improvement(
    "添加 Redis 内存使用率告警（85%）", "P1", "SRE Team", "2026-03-20"
)
analysis.add_improvement(
    "建立 Redis 配置基线和漂移检测", "P2", "SRE Team", "2026-04-15"
)

print(analysis.generate_report())
```

### 练习 3：编写事后复盘报告

**场景**：根据以下事故信息，编写完整的事后复盘报告。

**事故信息**：
- 2026-04-15 03:20，API 网关错误率突增到 30%
- 影响约 50% 用户，核心下单功能不可用
- 排查发现是新部署的 rate-limiter 配置错误，将正常流量误判为异常
- 03:50 回滚完成，04:00 服务完全恢复
- 影响时长 40 分钟

```markdown
# 事故复盘报告模板

## 基本信息
- 事故编号：INC-20260415-001
- 事故日期：2026-04-15
- 事故级别：P1
- 指挥官：[填写]
- 报告编写人：[填写]

## 事故摘要
[用 2-3 句话描述事故]

## 影响范围
- 受影响用户：约 50%
- 受影响功能：下单、支付
- 持续时间：40 分钟
- 业务损失：[计算]

## 时间线
[按时间顺序列出关键事件]

## 根因分析
[使用 5 Whys 或鱼骨图分析]

## 做得好的方面
[列出 3-5 个做得好的点]

## 需要改进的方面
[列出 3-5 个需要改进的点]

## Action Items
[列出改进措施、优先级、负责人、截止日期]

## 经验教训
[总结 3-5 条关键教训]
```

---

## 🎯 面试题精选

### 面试题 1：什么是无指责复盘？为什么它重要？

**考察点**：对事后复盘文化的理解。

**参考答案要点**：
1. 无指责复盘聚焦于系统改进，而非追究个人责任
2. 重要性：鼓励信息透明、促进组织学习、防止同样事故重复发生
3. 实践要点：假设善意、关注"什么"而非"谁"、承认系统复杂性
4. Google SRE Book 明确推荐此实践

### 面试题 2：请描述一个完整的事故响应流程

**考察点**：对事故管理流程的掌握。

**参考答案要点**：
1. 检测：告警触发或用户报告
2. 分类：评估影响，确定级别
3. 响应：分配角色，建立沟通渠道，开始排查
4. 恢复：执行恢复策略（回滚/扩容/重启）
5. 验证：确认服务恢复正常
6. 复盘：事后分析，制定改进措施

### 面试题 3：什么是 ICS？在事故中各角色如何协作？

**考察点**：对事故指挥体系的理解。

**参考答案要点**：
1. ICS 是事故指挥系统，源自应急管理
2. 核心角色：事故指挥官、技术主管、沟通主管、计划主管
3. 指挥官全局协调，不直接参与技术排查
4. 技术主管领导排查团队
5. 沟通主管管理内外部沟通

### 面试题 4：如何用 5 Whys 进行根因分析？

**考察点**：对 RCA 方法的掌握。

**参考答案要点**：
1. 从表面问题出发，连续追问"为什么"
2. 每个 Why 的答案应该是可验证的事实
3. 通常 5 次追问可以到达根本原因
4. 根本原因通常是流程或系统层面的缺陷
5. 基于根因制定改进措施

### 面试题 5：MTTD 和 MTTR 分别代表什么？如何优化？

**考察点**：对事故管理指标的理解。

**参考答案要点**：
1. MTTD: Mean Time To Detect，平均检测时间
2. MTTR: Mean Time To Recover，平均恢复时间
3. MTTD 优化：完善监控覆盖、设置合理告警阈值、增加合成监控
4. MTTR 优化：完善 Runbook、自动化恢复、定期演练

### 面试题 6：在事故进行中，你会优先做什么？

**考察点**：对事故响应优先级的理解。

**参考答案要点**：
1. 优先恢复服务，而非寻找根因
2. 快速评估影响范围，确定事故级别
3. 建立沟通渠道，通知相关人员
4. 尝试快速恢复手段（回滚、扩容、重启）
5. 恢复后再进行深入分析

### 面试题 7：如何确保事后复盘的 Action Item 得到落实？

**考察点**：对复盘闭环管理的理解。

**参考答案要点**：
1. 每个 Action Item 有明确的负责人和截止日期
2. 使用 Issue Tracker 跟踪进度
3. 定期 review 未完成的 Action Item
4. 将 Action Item 完成率纳入团队 KPI
5. 安排 follow-up 会议验证效果

---

## 📚 深入阅读

### 官方文档与书籍
- [Google SRE Book - Chapter 10: Software Engineering in SRE](https://sre.google/sre-book/software-engineering-in-sre/)
- [Google SRE Book - Chapter 11: Being On-Call](https://sre.google/sre-book/being-on-call/)
- [Google SRE Workbook - Postmortem Culture](https://sre.google/workbook/postmortem-culture/)
- [Google SRE Workbook - Managing Incidents](https://sre.google/workbook/managing-incidents/)

### 推荐文章
- [Postmortem Template - PagerDuty](https://postmortems.pagerduty.com/)
- [Incident Command for IT - John Allspaw](https://www.oreilly.com/library/view/incident-command-for/9781491917619/)
- [Blameless Postmortems](https://sre.google/workbook/postmortem-culture/)

### 实践工具
- [PagerDuty Incident Response](https://response.pagerduty.com/)
- [Jeli.io](https://jeli.io/) - 事故分析平台
- [Rootly](https://rootly.com/) - 事故管理平台
- [Firehydrant](https://firehydrant.io/) - 事故响应平台

---

## ✅ 自检清单

- [ ] 理解事故管理的完整生命周期
- [ ] 能描述 ICS 各角色的职责和协作方式
- [ ] 能用 5 Whys 方法进行根因分析
- [ ] 能用鱼骨图分析多因素事故
- [ ] 能重建事故时间线
- [ ] 能编写完整的事后复盘报告
- [ ] 理解无指责复盘的理念和实践要点
- [ ] 理解 MTTD、MTTA、MTTR 等关键指标
- [ ] 能设计事故响应流程和升级策略
