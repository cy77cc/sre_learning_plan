# Day 111: Auto Scaling

> 📅 日期：2026-05-10
> 📖 学习主题：Launch Template、扩缩策略、生命周期钩子、预热、目标追踪、步进策略、预测性扩缩
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 106（EC2 基础）、Day 110（ELB 负载均衡）

## 🎯 学习目标

- 理解 Auto Scaling Group 的核心概念和组件
- 掌握 Launch Template 的创建和版本管理
- 能够配置多种扩缩策略（目标追踪、步进、简单、预测性）
- 理解生命周期钩子和实例预热机制
- 掌握 ASG 与 ALB 的集成和最佳实践

---

## 📖 核心知识点

### 1. Auto Scaling 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Auto Scaling 架构                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Launch Template（实例模板）                                │ │
│  │  - AMI ID                                                  │ │
│  │  - 实例类型                                                │ │
│  │  - 安全组                                                  │ │
│  │  - 密钥对                                                  │ │
│  │  - User Data                                               │ │
│  │  - IAM 角色                                                │ │
│  │  - EBS 配置                                                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Auto Scaling Group                                        │ │
│  │                                                            │ │
│  │  Min: 2    Desired: 3    Max: 10                           │ │
│  │                                                            │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │ │
│  │  │Instance │  │Instance │  │Instance │  │ (空位)  │     │ │
│  │  │ AZ-a   │  │ AZ-b   │  │ AZ-a   │  │         │     │ │
│  │  │ Running │  │ Running │  │ Running │  │         │     │ │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┘     │ │
│  │       │            │            │                         │ │
│  └───────┼────────────┼────────────┼─────────────────────────┘ │
│          │            │            │                             │
│          ▼            ▼            ▼                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ALB Target Group                                        │   │
│  │  - 健康检查自动注册/注销                                  │   │
│  │  - 流量自动分发到健康实例                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  扩缩触发：                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ CloudWatch   │  │ Scheduled    │  │ Predictive   │         │
│  │ 告警触发     │  │ 定时触发     │  │ 预测触发     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Launch Template

Launch Template 是 EC2 实例的配置模板，替代了旧的 Launch Configuration。

```bash
# 创建 Launch Template
aws ec2 create-launch-template \
  --launch-template-name sre-app-template \
  --version-description "v1.0 - Initial" \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m6i.large",
    "KeyName": "sre-key-2026",
    "SecurityGroupIds": ["sg-0123456789abcdef0"],
    "IamInstanceProfile": {
      "Name": "SRE-EC2-Profile"
    },
    "BlockDeviceMappings": [
      {
        "DeviceName": "/dev/xvda",
        "Ebs": {
          "VolumeSize": 50,
          "VolumeType": "gp3",
          "Iops": 3000,
          "Throughput": 125,
          "Encrypted": true,
          "DeleteOnTermination": true
        }
      }
    ],
    "Monitoring": {
      "Enabled": true
    },
    "CreditSpecification": {
      "CpuCredits": "unlimited"
    },
    "TagSpecifications": [
      {
        "ResourceType": "instance",
        "Tags": [
          {"Key": "Name", "Value": "sre-app"},
          {"Key": "Environment", "Value": "production"},
          {"Key": "Team", "Value": "sre"}
        ]
      }
    ],
    "UserData": "'$(base64 -w0 userdata.sh)'"
  }'

# 创建新版本
aws ec2 create-launch-template-version \
  --launch-template-name sre-app-template \
  --source-version 1 \
  --version-description "v1.1 - Updated AMI" \
  --launch-template-data '{
    "ImageId": "ami-0newami1234567890"
  }'

# 设置默认版本
aws ec2 modify-launch-template \
  --launch-template-name sre-app-template \
  --default-version 2

# 列出所有版本
aws ec2 describe-launch-template-versions \
  --launch-template-name sre-app-template \
  --query "LaunchTemplateVersions[*].[VersionNumber,Description,CreateTime,DefaultVersion]"

# 使用 Launch Template 启动实例
aws ec2 run-instances \
  --launch-template LaunchTemplateName=sre-app-template,Version=1 \
  --instance-type m6i.large
```

---

### 3. Auto Scaling Group 配置

```bash
# 创建 ASG
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name sre-app-asg \
  --launch-template "LaunchTemplateName=sre-app-template,Version=\$Latest" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --vpc-zone-identifier "subnet-priv-1a,subnet-priv-1b" \
  --target-group-arns "arn:aws:elasticloadbalancing:...:targetgroup/sre-web-tg/xxx" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --termination-policies "OldestInstance" "Default" \
  --tags "Key=Name,Value=sre-app-asg,PropagateAtLaunch=true" \
         "Key=Environment,Value=production,PropagateAtLaunch=true"

# 查看 ASG
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names sre-app-asg \
  --query "AutoScalingGroups[0].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances[*].{Id:InstanceId,State:LifecycleState,AZ:AvailabilityZone}}"

# 修改 ASG
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name sre-app-asg \
  --min-size 3 \
  --max-size 20 \
  --desired-capacity 5

# 手动设置期望容量
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name sre-app-asg \
  --desired-capacity 5

# 实例刷新（滚动更新）
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name sre-app-asg \
  --preferences '{
    "MinHealthyPercentage": 90,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [50],
    "CheckpointDelay": 600
  }'

# 查看实例刷新状态
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name sre-app-asg
```

---

### 4. 扩缩策略

```
┌─────────────────────────────────────────────────────────────────┐
│                    扩缩策略类型                                  │
│                                                                 │
│  1. 目标追踪策略 (Target Tracking) — 推荐                       │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  设置目标值，ASG 自动调整保持目标                      │   │
│     │  例：CPU 目标 60%，ASG 自动增减实例                   │   │
│     │  简单易用，适合大多数场景                              │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  2. 步进策略 (Step Scaling)                                     │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  根据指标偏离程度执行不同幅度的调整                    │   │
│     │  例：CPU > 70% → +2 实例                              │   │
│     │      CPU > 85% → +5 实例                              │   │
│     │      CPU > 95% → +10 实例                             │   │
│     │  更精细的控制                                          │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. 简单策略 (Simple Scaling)                                   │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  固定数量或百分比调整                                  │   │
│     │  例：CPU > 70% → +2 实例                              │   │
│     │  有冷却期，防止频繁调整                                │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  4. 预测性扩缩 (Predictive Scaling)                             │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  基于历史数据预测未来负载                              │   │
│     │  提前扩容，避免延迟                                    │   │
│     │  适合有规律的流量模式（工作日高峰）                    │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  5. 定时策略 (Scheduled)                                        │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  在特定时间调整容量                                    │   │
│     │  例：每天 9:00 设为 10 台，22:00 设为 3 台            │   │
│     │  适合可预测的流量变化                                  │   │
│     └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.1 目标追踪策略

```bash
# 基于 CPU 使用率的目标追踪
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name sre-app-asg \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# 基于 ALB 请求数的目标追踪
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name sre-app-asg \
  --policy-name alb-request-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/sre-app-alb/xxx/targetgroup/sre-web-tg/xxx"
    },
    "TargetValue": 1000.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# 基于自定义指标的目标追踪
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name sre-app-asg \
  --policy-name custom-metric-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "CustomizedMetricSpecification": {
      "MetricName": "RequestLatency",
      "Namespace": "SRE/App",
      "Statistic": "Average",
      "Unit": "Milliseconds"
    },
    "TargetValue": 200.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

#### 4.2 步进策略

```bash
# 创建步进扩缩策略
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name sre-app-asg \
  --policy-name cpu-step-scaling \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 15,
      "ScalingAdjustment": 2
    },
    {
      "MetricIntervalLowerBound": 15,
      "MetricIntervalUpperBound": 25,
      "ScalingAdjustment": 5
    },
    {
      "MetricIntervalLowerBound": 25,
      "ScalingAdjustment": 10
    }
  ]' \
  --cooldown 300

# 创建 CloudWatch 告警触发步进策略
aws cloudwatch put-metric-alarm \
  --alarm-name "ASG-CPU-High" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 60 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=AutoScalingGroupName,Value=sre-app-asg \
  --alarm-actions "arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:xxx:policyName/cpu-step-scaling"
```

#### 4.3 预测性扩缩

```bash
# 启用预测性扩缩
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name sre-app-asg \
  --policy-name predictive-scaling \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [
      {
        "TargetValue": 60,
        "PredefinedMetricPairSpecification": {
          "PredefinedMetricType": "ASGCPUUtilization"
        }
      }
    ],
    "Mode": "ForecastAndScale",
    "SchedulingBufferTime": 300
  }'

# 查看预测性扩缩的预测
aws autoscaling describe-predictive-scaling-forecast \
  --auto-scaling-group-name sre-app-asg \
  --policy-name predictive-scaling
```

#### 4.4 定时策略

```bash
# 工作日早上扩容
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name sre-app-asg \
  --scheduled-action-name morning-scale-up \
  --recurrence "0 9 * * MON-FRI" \
  --min-size 5 \
  --max-size 20 \
  --desired-capacity 10

# 晚上缩容
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name sre-app-asg \
  --scheduled-action-name evening-scale-down \
  --recurrence "0 22 * * MON-FRI" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3

# 周末最小容量
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name sre-app-asg \
  --scheduled-action-name weekend-minimum \
  --recurrence "0 0 * * SAT" \
  --min-size 2 \
  --max-size 5 \
  --desired-capacity 2

# 查看定时操作
aws autoscaling describe-scheduled-actions \
  --auto-scaling-group-name sre-app-asg
```

---

### 5. 生命周期钩子

生命周期钩子在实例状态变化时执行自定义操作。

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASG 生命周期                                   │
│                                                                 │
│  启动流程：                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Pending  │───▶│ Pending  │───▶│ In       │───▶│ Running  │ │
│  │          │    │ Wait     │    │ Service  │    │          │ │
│  │ 创建中   │    │ (钩子)   │    │ 注册到   │    │ 运行中   │ │
│  │          │    │ 自定义   │    │ 目标组   │    │          │ │
│  └──────────┘    │ 初始化   │    └──────────┘    └──────────┘ │
│                  └──────────┘                                   │
│                       │                                         │
│                  complete-lifecycle-action                      │
│                  (完成钩子，继续启动)                            │
│                                                                 │
│  终止流程：                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Running  │───▶│ Termina- │───▶│ Termina- │───▶│Terminated│ │
│  │          │    │ ting     │    │ ting     │    │          │ │
│  │ 运行中   │    │ Wait     │    │ Proceed  │    │ 已终止   │ │
│  │          │    │ (钩子)   │    │          │    │          │ │
│  └──────────┘    │ 优雅     │    └──────────┘    └──────────┘ │
│                  │ 关闭     │                                   │
│                  └──────────┘                                   │
│                       │                                         │
│                  complete-lifecycle-action                      │
│                  (完成钩子，继续终止)                            │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 SNS 主题用于生命周期钩子通知
aws sns create-topic --name asg-lifecycle-hooks

# 创建 Lifecycle Hook — 启动时
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name sre-app-asg \
  --lifecycle-hook-name app-init-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 600 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:sns:us-east-1:123456789012:asg-lifecycle-hooks \
  --role-arn arn:aws:iam::123456789012:role/ASGLifecycleRole

# 创建 Lifecycle Hook — 终止时
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name sre-app-asg \
  --lifecycle-hook-name graceful-shutdown-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
  --heartbeat-timeout 300 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:sns:us-east-1:123456789012:asg-lifecycle-hooks \
  --role-arn arn:aws:iam::123456789012:role/ASGLifecycleRole

# 使用 Lambda 处理生命周期钩子
cat > /tmp/lifecycle-handler.py << 'EOF'
import boto3
import json

def handler(event, context):
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        lifecycle_hook_name = message['LifecycleHookName']
        instance_id = message['EC2InstanceId']
        lifecycle_action_token = message['LifecycleActionToken']
        
        asg_name = message['AutoScalingGroupName']
        
        if 'launching' in message.get('LifecycleTransition', ''):
            # 启动钩子 — 执行初始化
            print(f"Initializing instance {instance_id}")
            # 执行自定义初始化逻辑
            # 例如：注册到配置中心、预热缓存等
            
            # 完成生命周期动作
            boto3.client('autoscaling').complete_lifecycle_action(
                LifecycleHookName=lifecycle_hook_name,
                AutoScalingGroupName=asg_name,
                LifecycleActionToken=lifecycle_action_token,
                LifecycleActionResult='CONTINUE'
            )
        
        elif 'terminating' in message.get('LifecycleTransition', ''):
            # 终止钩子 — 优雅关闭
            print(f"Gracefully shutting down instance {instance_id}")
            # 执行清理逻辑
            # 例如：从负载均衡器注销、完成进行中的请求、保存状态
            
            # 完成生命周期动作
            boto3.client('autoscaling').complete_lifecycle_action(
                LifecycleHookName=lifecycle_hook_name,
                AutoScalingGroupName=asg_name,
                LifecycleActionToken=lifecycle_action_token,
                LifecycleActionResult='CONTINUE'
            )
    
    return {'statusCode': 200}
EOF

# 记录生命周期事件到 SQS（替代 SNS）
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name sre-app-asg \
  --lifecycle-hook-name app-init-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 600 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:sqs:us-east-1:123456789012:asg-lifecycle

# 列出生命周期钩子
aws autoscaling describe-lifecycle-hooks \
  --auto-scaling-group-name sre-app-asg

# 删除生命周期钩子
aws autoscaling delete-lifecycle-hook \
  --auto-scaling-group-name sre-app-asg \
  --lifecycle-hook-name app-init-hook
```

---

### 6. 实例预热

```
┌─────────────────────────────────────────────────────────────────┐
│                    实例预热                                       │
│                                                                 │
│  问题：新实例启动后立即接收流量，但应用未完全初始化              │
│                                                                 │
│  时间线：                                                        │
│  ─────┬─────┬─────┬─────┬─────┬─────▶                          │
│       │     │     │     │     │                                 │
│    创建  启动  OS   应用  健康  接收                              │
│    实例  完成  初始化 启动 检查 流量                              │
│                 │     │     │                                    │
│                 └─────┴─────┘                                    │
│                  预热期（不接收流量）                             │
│                                                                 │
│  解决方案：                                                      │
│  1. HealthCheckGracePeriod：ASG 等待时间                        │
│  2. Target Group 的慢启动（Slow Start）                         │
│  3. Lifecycle Hook：自定义初始化完成后才标记就绪                │
│  4. Warm Pools：预启动的实例池，快速响应扩容                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.1 Warm Pool

```bash
# 创建 Warm Pool
aws autoscaling put-warm-pool \
  --auto-scaling-group-name sre-app-asg \
  --pool-state Stopped \
  --min-size 2 \
  --max-group-prepared-capacity 5 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'

# 查看 Warm Pool
aws autoscaling describe-warm-pool \
  --auto-scaling-group-name sre-app-asg

# Warm Pool 实例状态：
# - Running：预启动的实例，立即可用
# - Stopped：已停止的实例，需要启动（更省成本）
```

#### 6.2 慢启动（Slow Start）

```bash
# 配置目标组的慢启动
aws elbv2 modify-target-group-attributes \
  --target-group-arn "$TG_ARN" \
  --attributes Key=slow_start.duration_seconds,Value=300

# 慢启动期间，ALB 逐步增加发送到新目标的流量
# 300 秒内，流量从 0 逐渐增加到满负载
# 防止新实例被过多流量冲击
```

---

### 7. ASG 与 ALB 集成

```bash
# ASG 自动注册到 ALB 目标组
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name sre-app-asg \
  --launch-template "LaunchTemplateName=sre-app-template,Version=\$Latest" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --vpc-zone-identifier "subnet-priv-1a,subnet-priv-1b" \
  --target-group-arns "arn:aws:elasticloadbalancing:...:targetgroup/sre-web-tg/xxx" \
  --health-check-type ELB \
  --health-check-grace-period 300

# 健康检查类型：
# - EC2：检查实例状态（默认）
# - ELB：检查 ALB 健康检查 + 实例状态（推荐）

# 终止策略：
# - OldestInstance：终止最旧的实例
# - NewestInstance：终止最新的实例
# - OldestLaunchTemplate：终止使用旧模板的实例
# - AllocationStrategy：按分配策略终止
# - Default：默认策略

# 实例保护
aws autoscaling set-instance-protection \
  --auto-scaling-group-name sre-app-asg \
  --instance-ids i-0123456789abcdef0 \
  --protected-from-scale-in

# 实例暂停
aws autoscaling enter-standby \
  --auto-scaling-group-name sre-app-asg \
  --instance-ids i-0123456789abcdef0 \
  --should-decrement-desired-capacity

# 恢复实例
aws autoscaling exit-standby \
  --auto-scaling-group-name sre-app-asg \
  --instance-ids i-0123456789abcdef0
```

---

### 8. SRE 实战案例

#### 案例 1：ASG 不扩容导致服务降级

**故障现象：** 流量突增但 ASG 未扩容，应用响应超时。

```bash
# 1. 检查 ASG 状态
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names sre-app-asg \
  --query "AutoScalingGroups[0].{Desired:DesiredCapacity,Min:MinSize,Max:MaxSize,Instances:length(Instances)}"

# 2. 检查扩缩活动历史
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name sre-app-asg \
  --query "Activities[*].[StartTime,StatusCode,StatusMessage,Description]"

# 3. 检查 CloudWatch 告警状态
aws cloudwatch describe-alarms \
  --alarm-names "ASG-CPU-High" \
  --query "MetricAlarms[*].[StateValue,StateReason]"

# 4. 检查是否已达最大容量
# 如果 DesiredCapacity == MaxSize，ASG 无法继续扩容

# 5. 检查实例启动失败
aws ec2 describe-instances \
  --filters "Name=tag:aws:autoscaling:groupName,Values=sre-app-asg" \
            "Name=instance-state-name,Values=pending,stopping,terminated" \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,StateReason.Message]"

# 根因：ASG 的 MaxSize 设置为 5，已达上限
# 解决方案：增加 MaxSize，或使用预测性扩缩提前扩容
```

#### 案例 2：实例频繁启动和终止（抖动）

```bash
# 1. 检查扩缩活动
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name sre-app-asg \
  --query "Activities[*].[StartTime,EndTime,StatusCode,Description]" \
  --max-items 20

# 2. 检查 CloudWatch 指标波动
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=sre-app-asg \
  --start-time $(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average

# 3. 检查缩容冷却期
aws autoscaling describe-policies \
  --auto-scaling-group-name sre-app-asg \
  --query "ScalingPolicies[*].[PolicyName,ScalingAdjustment,Cooldown]"

# 根因：缩容冷却期太短，导致扩容后很快又缩容
# 解决方案：
# 1. 增加 ScaleInCooldown（300 秒 → 600 秒）
# 2. 使用步进策略代替简单策略
# 3. 增加 CloudWatch 告警的评估周期
```

#### 案例 3：实例刷新导致服务中断

```bash
# 1. 检查实例刷新状态
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name sre-app-asg \
  --query "InstanceRefreshes[*].[InstanceRefreshId,Status,PercentageComplete]"

# 2. 检查最小健康百分比
# 如果 MinHealthyPercentage 太低，可能在替换过程中没有足够健康实例

# 3. 安全的实例刷新配置
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name sre-app-asg \
  --preferences '{
    "MinHealthyPercentage": 90,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [25, 50, 75, 100],
    "CheckpointDelay": 600,
    "SkipMatching": true
  }'

# 4. 如果出问题，取消实例刷新
aws autoscaling cancel-instance-refresh \
  --auto-scaling-group-name sre-app-asg
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建 ASG

```bash
# 步骤 1: 创建 Launch Template
aws ec2 create-launch-template \
  --launch-template-name exercise-template \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t3.micro",
    "SecurityGroupIds": ["sg-xxxx"]
  }'

# 步骤 2: 创建 ASG
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name exercise-asg \
  --launch-template "LaunchTemplateName=exercise-template,Version=\$Latest" \
  --min-size 1 \
  --max-size 5 \
  --desired-capacity 2 \
  --vpc-zone-identifier "subnet-priv-1a,subnet-priv-1b" \
  --health-check-type EC2 \
  --health-check-grace-period 300

# 步骤 3: 查看 ASG
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names exercise-asg

# 步骤 4: 创建目标追踪策略
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name exercise-asg \
  --policy-name cpu-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0
  }'

# 步骤 5: 清理
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name exercise-asg --force-delete
aws ec2 delete-launch-template --launch-template-name exercise-template
```

### 练习 2：进阶场景 — 配置生命周期钩子

```bash
# 步骤 1: 创建 SQS 队列
QUEUE_URL=$(aws sqs create-queue \
  --queue-name exercise-lifecycle \
  --query "QueueUrl" --output text)

QUEUE_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names QueueArn \
  --query "Attributes.QueueArn" --output text)

# 步骤 2: 创建 Lifecycle Hook
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name exercise-asg \
  --lifecycle-hook-name exercise-init \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 300 \
  --default-result CONTINUE \
  --notification-target-arn "$QUEUE_ARN"

# 步骤 3: 验证钩子
aws autoscaling describe-lifecycle-hooks \
  --auto-scaling-group-name exercise-asg

# 步骤 4: 检查生命周期事件
aws sqs receive-message --queue-url "$QUEUE_URL"
```

### 练习 3：故障排查挑战 — ASG 不缩容

**场景：** 流量下降后 ASG 保持高容量，成本增加。

```bash
# 排查步骤
# 1. 检查 ASG 当前状态
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names sre-app-asg \
  --query "AutoScalingGroups[0].{Desired:DesiredCapacity,Min:MinSize,Instances:length(Instances)}"

# 2. 检查是否启用缩容
aws autoscaling describe-policies \
  --auto-scaling-group-name sre-app-asg \
  --query "ScalingPolicies[*].[PolicyName,PolicyType,AdjustmentType]"

# 3. 检查 CloudWatch 告警状态
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?contains(AlarmName,'ASG')].[AlarmName,StateValue,StateReason]"

# 4. 检查实例保护
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names sre-app-asg \
  --query "AutoScalingGroups[0].Instances[*].[InstanceId,ProtectedFromScaleIn]"

# 5. 检查生命周期钩子是否卡住
aws autoscaling describe-lifecycle-hooks \
  --auto-scaling-group-name sre-app-asg

# 答案：常见原因
# - 缩容策略未配置
# - 实例保护阻止缩容
# - 生命周期钩子卡住（未调用 complete-lifecycle-action）
# - CloudWatch 告警未触发缩容
# - ScaleInCooldown 设置太长
```

---

## 🎯 面试题精选

### 题目 1：ASG 的 Desired、Min、Max 有什么关系？

**答：**
- **MinSize**：最小实例数，ASG 不会缩容到低于此值
- **MaxSize**：最大实例数，ASG 不会扩容到超过此值
- **DesiredCapacity**：期望实例数，在 Min 和 Max 之间

关系：`Min <= Desired <= Max`。扩缩策略调整的是 DesiredCapacity。

### 题目 2：目标追踪和步进策略的区别？

**答：**
- **目标追踪**：设置目标值（如 CPU 60%），ASG 自动调整保持目标。简单易用，推荐大多数场景。
- **步进策略**：根据指标偏离程度执行不同幅度的调整。更精细控制，适合复杂场景。

目标追踪相当于自动驾驶，步进策略相当于手动挡。

### 题目 3：什么是 Warm Pool？

**答：** Warm Pool 是一组预启动的实例，用于快速响应扩容需求。实例可以是 Running 状态（立即可用）或 Stopped 状态（需要启动，更省成本）。当 ASG 需要扩容时，优先从 Warm Pool 取实例，避免等待实例启动。

### 题目 4：生命周期钩子的典型使用场景？

**答：**
- **启动钩子**：注册到服务发现、预热缓存、下载配置、初始化数据库连接池
- **终止钩子**：从负载均衡器注销、完成进行中的请求、保存状态、发送通知

### 题目 5：ASG 的健康检查类型有什么区别？

**答：**
- **EC2**：只检查实例状态（Running/Stopped/Terminated）
- **ELB**：检查 ALB 健康检查 + 实例状态。如果 ALB 健康检查失败，实例会被标记为不健康并替换。

推荐使用 ELB 类型，确保只有健康实例接收流量。

### 题目 6：如何实现蓝绿部署？

**答：**
1. 创建新的 Launch Template 版本
2. 执行 Instance Refresh（滚动替换）
3. 或者：创建新的 ASG → 验证 → 切换 ALB 目标组 → 删除旧 ASG

使用 Instance Refresh 更简单，使用新 ASG 更安全（可以快速回滚）。

### 题目 7：预测性扩缩的工作原理？

**答：** 预测性扩缩使用机器学习分析历史负载数据（至少 14 天），预测未来 48 小时的负载。在预测的负载增加前自动扩容，避免延迟。适合有规律的流量模式（如工作日高峰）。

### 题目 8：ASG 跨可用区如何分布实例？

**答：** ASG 默认均匀分布实例到所有配置的可用区。如果某个 AZ 的实例被终止，ASG 会在其他 AZ 补充。可以使用 `--vpc-zone-identifier` 控制可用区选择。

---

## 📚 深入阅读

- [Auto Scaling 官方文档](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)
- [Launch Template](https://docs.aws.amazon.com/autoscaling/ec2/userguide/launch-templates.html)
- [扩缩策略](https://docs.aws.amazon.com/autoscaling/ec2/userguide/scaling_policies.html)
- [生命周期钩子](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)
- [预测性扩缩](https://docs.aws.amazon.com/autoscaling/ec2/userguide/predictive-scaling.html)
- [Warm Pool](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-warm-pools.html)

---

## ✅ 自检清单

- [ ] 能够创建和管理 Launch Template
- [ ] 能够创建 Auto Scaling Group 并配置参数
- [ ] 能够配置目标追踪扩缩策略
- [ ] 能够配置步进扩缩策略
- [ ] 能够配置定时扩缩策略
- [ ] 理解预测性扩缩的工作原理
- [ ] 能够配置生命周期钩子
- [ ] 理解实例预热机制（Warm Pool、Slow Start）
- [ ] 能够实现 ASG 与 ALB 的集成
- [ ] 能够排查 ASG 常见故障（不扩容、不缩容、抖动）
