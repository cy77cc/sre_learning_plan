# Day 110: ELB 负载均衡

> 📅 日期：2026-05-09
> 📖 学习主题：ALB/NLB/GLB 区别、健康检查、目标组、SSL 终止、基于路径路由、WebSocket、访问日志
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 106（EC2 基础）、Day 107（VPC 网络）

## 🎯 学习目标

- 理解 ALB、NLB、GWLB 的区别和适用场景
- 掌握目标组和健康检查的配置
- 能够配置 SSL/TLS 终止和基于路径的路由
- 理解 WebSocket 支持和访问日志分析
- 掌握 ELB 的故障排查方法

---

## 📖 核心知识点

### 1. ELB 类型对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    ELB 类型对比                                  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  ALB (Application Load Balancer)                           │ │
│  │  - 层级：L7 (HTTP/HTTPS/gRPC)                              │ │
│  │  - 路由：基于路径、主机名、HTTP 头、查询参数               │ │
│  │  - 特点：SSL 终止、WebSocket、HTTP/2、WAF 集成            │ │
│  │  - 适用：Web 应用、微服务 API                              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  NLB (Network Load Balancer)                               │ │
│  │  - 层级：L4 (TCP/UDP/TLS)                                  │ │
│  │  - 路由：基于 IP + 端口                                    │ │
│  │  - 特点：超低延迟、静态 IP、保留源 IP、极高吞吐           │ │
│  │  - 适用：TCP/UDP 应用、游戏服务器、IoT、极低延迟需求      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  GWLB (Gateway Load Balancer)                              │ │
│  │  - 层级：L3 (IP)                                           │ │
│  │  - 路由：基于 IP 协议                                      │ │
│  │  - 特点：透明网络流量插入、第三方虚拟设备                  │ │
│  │  - 适用：防火墙、IDS/IPS、深度包检查                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  CLB (Classic Load Balancer) — 已废弃                      │ │
│  │  - 不推荐新项目使用，迁移到 ALB 或 NLB                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  选型决策树：                                                    │
│  需要 HTTP/HTTPS 路由？ → ALB                                   │
│  需要 TCP/UDP 超低延迟？ → NLB                                  │
│  需要插入第三方设备？ → GWLB                                    │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 列出所有负载均衡器
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[*].[LoadBalancerArn,Type,DNSName,State.Code]" \
  --output table
```

---

### 2. ALB 配置详解

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALB 架构                                      │
│                                                                 │
│  客户端                                                          │
│    │                                                            │
│    ▼                                                            │
│  ┌─────────────────────────────────────────────────┐           │
│  │  ALB (跨 2 个 AZ)                               │           │
│  │  DNS: sre-alb-xxx.us-east-1.elb.amazonaws.com   │           │
│  │                                                  │           │
│  │  ┌──────────────┐  ┌──────────────┐             │           │
│  │  │ Listener:443 │  │ Listener:80  │             │           │
│  │  │ (HTTPS)      │  │ (HTTP→HTTPS) │             │           │
│  │  └──────┬───────┘  └──────┬───────┘             │           │
│  │         │                 │                      │           │
│  │    ┌────┼────┐            │                      │           │
│  │    ▼    ▼    ▼            ▼                      │           │
│  │  ┌───┐┌───┐┌───┐      ┌──────┐                 │           │
│  │  │/  ││/api││/ws │      │Redirect│              │           │
│  │  │   ││   ││   │      │ → 443  │              │           │
│  │  └─┬─┘└─┬─┘└─┬─┘      └──────┘                 │           │
│  └────┼────┼────┼─────────────────────────────────┘           │
│       │    │    │                                               │
│       ▼    ▼    ▼                                               │
│  ┌────────┐ ┌────────┐ ┌────────┐                              │
│  │TG-Web │ │TG-API │ │TG-WS  │                              │
│  │       │ │       │ │       │                              │
│  │┌─────┐│ │┌─────┐│ │┌─────┐│                              │
│  ││EC2-1││ ││EC2-3││ ││EC2-5││                              │
│  ││EC2-2││ ││EC2-4││ ││EC2-6││                              │
│  │└─────┘│ │└─────┘│ │└─────┘│                              │
│  └────────┘ └────────┘ └────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name sre-app-alb \
  --type application \
  --scheme internet-facing \
  --ip-address-type ipv4 \
  --subnets subnet-public-1a subnet-public-1b \
  --security-groups sg-alb-sg \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# 创建目标组 — Web
TG_WEB_ARN=$(aws elbv2 create-target-group \
  --name sre-web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-0123456789abcdef0 \
  --target-type instance \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher "HttpCode=200" \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# 创建目标组 — API
TG_API_ARN=$(aws elbv2 create-target-group \
  --name sre-api-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-0123456789abcdef0 \
  --target-type instance \
  --health-check-protocol HTTP \
  --health-check-path /api/health \
  --health-check-interval-seconds 15 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher "HttpCode=200-299" \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# 创建 HTTPS 监听器（SSL 终止）
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --default-actions Type=forward,TargetGroupArn="$TG_WEB_ARN" \
  --query "Listeners[0].ListenerArn" --output text)

# 创建基于路径的路由规则
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions Type=forward,TargetGroupArn="$TG_API_ARN"

# 创建 WebSocket 路由规则
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 20 \
  --conditions '[{"Field":"path-pattern","Values":["/ws/*"]}]' \
  --actions Type=forward,TargetGroupArn="$TG_WS_ARN"

# 创建 HTTP → HTTPS 重定向
aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"

# 注册目标
aws elbv2 register-targets \
  --target-group-arn "$TG_WEB_ARN" \
  --targets Id=i-0123456789abcdef0 Id=i-0123456789abcdef1

# 查看目标健康状态
aws elbv2 describe-target-health \
  --target-group-arn "$TG_WEB_ARN" \
  --query "TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealthReason.Reason]"
```

---

### 3. NLB 配置

```bash
# 创建 NLB
NLB_ARN=$(aws elbv2 create-load-balancer \
  --name sre-tcp-nlb \
  --type network \
  --scheme internet-facing \
  --ip-address-type ipv4 \
  --subnets subnet-public-1a subnet-public-1b \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# 创建目标组（TCP）
TG_TCP_ARN=$(aws elbv2 create-target-group \
  --name sre-tcp-tg \
  --protocol TCP \
  --port 8080 \
  --vpc-id vpc-0123456789abcdef0 \
  --target-type instance \
  --health-check-protocol TCP \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# 创建 NLB 监听器
aws elbv2 create-listener \
  --load-balancer-arn "$NLB_ARN" \
  --protocol TCP \
  --port 8080 \
  --default-actions Type=forward,TargetGroupArn="$TG_TCP_ARN"

# NLB TLS 终止
aws elbv2 create-listener \
  --load-balancer-arn "$NLB_ARN" \
  --protocol TLS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn="$TG_TCP_ARN"
```

---

### 4. 健康检查

```
┌─────────────────────────────────────────────────────────────────┐
│                    健康检查流程                                   │
│                                                                 │
│  ALB                                           目标实例          │
│  ┌─────┐     HTTP GET /health                  ┌─────┐         │
│  │     │ ──────────────────────────────────────▶│     │         │
│  │     │     每 30 秒                           │     │         │
│  │     │                                        │     │         │
│  │     │◀──────────────────────────────────────│     │         │
│  │     │     HTTP 200 OK                        │     │         │
│  │     │                                        └─────┘         │
│  │     │     连续 2 次成功 → 标记为 healthy                     │
│  │     │                                                        │
│  │     │     HTTP 500 / 超时                                    │
│  │     │◀──────────────────────────────────────│     │         │
│  │     │                                        └─────┘         │
│  │     │     连续 3 次失败 → 标记为 unhealthy                   │
│  │     │     → 从目标组移除，不再发送流量                        │
│  └─────┘                                                        │
│                                                                 │
│  健康检查参数：                                                  │
│  - HealthCheckPath: /health                                     │
│  - HealthCheckIntervalSeconds: 30                               │
│  - HealthCheckTimeoutSeconds: 5                                 │
│  - HealthyThresholdCount: 2                                     │
│  - UnhealthyThresholdCount: 3                                   │
│  - Matcher: HttpCode=200-299                                    │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 修改健康检查配置
aws elbv2 modify-target-group \
  --target-group-arn "$TG_WEB_ARN" \
  --health-check-path /healthz \
  --health-check-interval-seconds 15 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher "HttpCode=200"

# 查看目标健康状态
aws elbv2 describe-target-health \
  --target-group-arn "$TG_WEB_ARN"

# 查看目标组属性
aws elbv2 describe-target-group-attributes \
  --target-group-arn "$TG_WEB_ARN"
```

**健康检查最佳实践：**

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 健康检查路径 | /healthz | 专用端点，不检查依赖 |
| 间隔 | 10-30 秒 | 太频繁增加负载，太慢检测延迟 |
| 超时 | 3-5 秒 | 应该小于间隔 |
| 健康阈值 | 2 | 连续 2 次成功标记健康 |
| 不健康阈值 | 2-3 | 连续 2-3 次失败标记不健康 |

---

### 5. SSL/TLS 配置

```bash
# 请求 ACM 证书
aws acm request-certificate \
  --domain-name "*.example.com" \
  --subject-alternative-names "example.com" \
  --validation-method DNS \
  --query "CertificateArn" --output text

# 查看证书状态
aws acm list-certificates \
  --query "CertificateSummaryList[*].[CertificateArn,DomainName,Status]"

# ALB 监听器 SSL 策略
# 推荐策略：ELBSecurityPolicy-TLS13-1-2-2021-06
# 支持 TLS 1.2 和 1.3，禁用旧版本

# 查看可用的 SSL 策略
aws elbv2 describe-ssl-policies \
  --query "SslPolicies[*].[Name,SslProtocols[]]" \
  --output table

# 修改监听器 SSL 策略
aws elbv2 modify-listener \
  --listener-arn "$LISTENER_ARN" \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06

# 重定向 HTTP 到 HTTPS
aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTP \
  --port 80 \
  --default-actions '[{
    "Type": "redirect",
    "RedirectConfig": {
      "Protocol": "HTTPS",
      "Port": "443",
      "StatusCode": "HTTP_301"
    }
  }]'
```

---

### 6. 基于路径的路由

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALB 路由规则                                   │
│                                                                 │
│  条件类型：                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  path-pattern        /api/*, /images/*.jpg               │   │
│  │  host-header         api.example.com, web.example.com    │   │
│  │  http-header         X-Custom-Header: value              │   │
│  │  http-request-method GET, POST                           │   │
│  │  query-string        ?version=2                          │   │
│  │  source-ip           203.0.113.0/24                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  优先级评估：                                                    │
│  Listener:443                                                   │
│  ├── Rule 1 (Priority: 1)                                      │
│  │   Condition: host-header = api.example.com                  │
│  │   Action: Forward → TG-API                                  │
│  ├── Rule 2 (Priority: 10)                                     │
│  │   Condition: path-pattern = /api/*                         │
│  │   Action: Forward → TG-API                                  │
│  ├── Rule 3 (Priority: 20)                                     │
│  │   Condition: path-pattern = /static/*                      │
│  │   Action: Forward → TG-Static                               │
│  └── Default Rule (Priority: default)                          │
│      Action: Forward → TG-Web                                  │
│                                                                 │
│  注意：规则按优先级评估，第一条匹配的规则生效                   │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建基于主机名的路由
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 1 \
  --conditions '[{"Field":"host-header","Values":["api.example.com"]}]' \
  --actions Type=forward,TargetGroupArn="$TG_API_ARN"

# 创建基于路径的路由
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions Type=forward,TargetGroupArn="$TG_API_ARN"

# 创建基于查询字符串的路由
aws elbv2 create-rule \
  --listener-arn "$LISTENER_ARN" \
  --priority 30 \
  --conditions '[{"Field":"query-string","Values":[{"Key":"version","Value":"2"}]}]' \
  --actions Type=forward,TargetGroupArn="$TG_API_V2_ARN"

# 列出所有规则
aws elbv2 describe-rules \
  --listener-arn "$LISTENER_ARN" \
  --query "Rules[*].[Priority,Conditions[*].{Field:Field,Values:Values},Actions[*].TargetGroupArn]"

# 修改默认规则
aws elbv2 modify-rule \
  --rule-arn "$DEFAULT_RULE_ARN" \
  --actions Type=forward,TargetGroupArn="$TG_WEB_ARN"
```

---

### 7. WebSocket 支持

ALB 原生支持 WebSocket 和 HTTP/2 协议。

```bash
# WebSocket 连接通过 ALB 时：
# - ALB 支持 WebSocket 升级（HTTP 101）
# - 空闲超时默认 60 秒，可配置到 4000 秒
# - 需要目标组支持 WebSocket

# 配置目标组增加空闲超时
aws elbv2 modify-target-group-attributes \
  --target-group-arn "$TG_WS_ARN" \
  --attributes Key=slow_start.duration_seconds,Value=60 \
               Key=deregistration_delay.timeout_seconds,Value=30

# ALB 属性配置
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "$ALB_ARN" \
  --attributes Key=idle_timeout.timeout_seconds,Value=300 \
               Key=routing.http2.enabled,Value=true \
               Key=routing.http.drop_invalid_header_fields.enabled,Value=true
```

---

### 8. 访问日志

```bash
# 创建 S3 Bucket 存储访问日志
aws s3 mb s3://sre-alb-access-logs --region us-east-1

# 设置 ALB 日志交付权限
aws s3api put-bucket-policy \
  --bucket sre-alb-access-logs \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::123456789012:root"
        },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::sre-alb-access-logs/AWSLogs/*"
      },
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "delivery.logs.amazonaws.com"
        },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::sre-alb-access-logs/AWSLogs/*",
        "Condition": {
          "StringEquals": {
            "s3:x-amz-acl": "bucket-owner-full-control"
          }
        }
      },
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "delivery.logs.amazonaws.com"
        },
        "Action": "s3:GetBucketAcl",
        "Resource": "arn:aws:s3:::sre-alb-access-logs"
      }
    ]
  }'

# 启用 ALB 访问日志
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "$ALB_ARN" \
  --attributes Key=access_logs.s3.enabled,Value=true \
               Key=access_logs.s3.bucket,s3-alb-access-logs \
               Key=access_logs.s3.prefix,sre-app

# ALB 访问日志格式示例：
# type timestamp elb client:port target:port request_processing_time
# target_processing_time response_processing_time elb_status_code
# target_status_code received_bytes sent_bytes
# "request" "user_agent" ssl_cipher ssl_protocol
# target_group_arn "trace_id" "domain_name" "chosen_cert_arn"
# matched_rule_priority request_creation_time "actions_executed"
# "redirect_url" "error_reason" "target:port_list"
# "target_status_code_list" "classification" "classification_reason"
```

---

### 9. SRE 实战案例

#### 案例 1：ALB 目标组全部不健康

**故障现象：** 所有目标实例显示 unhealthy，ALB 返回 503。

```bash
# 1. 检查目标健康状态
aws elbv2 describe-target-health \
  --target-group-arn "$TG_WEB_ARN" \
  --query "TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealthReason.Reason]"

# 2. 检查健康检查配置
aws elbv2 describe-target-group-attributes \
  --target-group-arn "$TG_WEB_ARN"

# 3. 检查安全组（ALB 到实例的 80 端口）
aws ec2 describe-security-groups \
  --group-ids sg-app-sg \
  --query "SecurityGroups[*].IpPermissions"

# 4. 检查应用健康端点
curl -v http://10.0.10.5:80/health

# 5. 检查实例是否在目标组中
aws elbv2 describe-target-health \
  --target-group-arn "$TG_WEB_ARN"

# 根因：健康检查路径 /healthz 返回 404，应用实际健康端点是 /health
# 解决方案：修改目标组健康检查路径
```

#### 案例 2：HTTPS 证书错误

```bash
# 1. 检查 ACM 证书状态
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:... \
  --query "Certificate.{Status:Status,DomainName:DomainName,NotAfter:NotAfter}"

# 2. 检查证书域名是否匹配
# ALB 需要证书域名匹配请求的 Host 头

# 3. 检查监听器配置
aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --query "Listeners[*].[Port,Protocol,SslPolicy,Certificates[*].CertificateArn]"

# 4. 测试 SSL 连接
openssl s_client -connect sre-alb-xxx.us-east-1.elb.amazonaws.com:443 \
  -servername example.com

# 根因：证书过期或域名不匹配
# 解决方案：续期证书或添加正确的域名
```

#### 案例 3：NLB 保留源 IP 问题

```bash
# 1. 检查 NLB 目标组属性
aws elbv2 describe-target-group-attributes \
  --target-group-arn "$TG_TCP_ARN"

# 2. 检查是否启用了源 IP 保留
# proxy_protocol_v2.enabled = true/false

# 3. 检查实例看到的源 IP
# 从实例内部：
# tcpdump -i eth0 port 8080 -nn

# NLB 默认保留源 IP（不同于 ALB）
# 如果使用 proxy_protocol，需要应用解析 PROXY protocol header
```

### 8. 连接排空与目标组属性

```bash
# 配置连接排空（Deregistration Delay）
# 当目标被注销时，ALB 会等待正在进行的请求完成
aws elbv2 modify-target-group-attributes \
  --target-group-arn "$TG_WEB_ARN" \
  --attributes Key=deregistration_delay.timeout_seconds,Value=300

# 推荐值：
# - 短请求（API）：30-60 秒
# - 长请求（WebSocket）：300 秒
# - 文件上传：300 秒

# 配置慢启动（Slow Start）
# 新注册的目标在指定时间内逐步增加流量
aws elbv2 modify-target-group-attributes \
  --target-group-arn "$TG_WEB_ARN" \
  --attributes Key=slow_start.duration_seconds,Value=300

# 配置粘性会话（Sticky Sessions）
aws elbv2 modify-target-group-attributes \
  --target-group-arn "$TG_WEB_ARN" \
  --attributes Key=stickiness.enabled,Value=true \
               Key=stickiness.type,Value=app_cookie \
               Key=stickiness.app_cookie.cookie_name,Value=SESSIONID \
               Key=stickiness.app_cookie.duration_seconds,Value=86400

# 加权目标组（用于金丝雀发布）
aws elbv2 modify-listener \
  --listener-arn "$LISTENER_ARN" \
  --default-actions '[
    {
      "Type": "forward",
      "ForwardConfig": {
        "TargetGroups": [
          {"TargetGroupArn": "arn:tg-stable", "Weight": 90},
          {"TargetGroupArn": "arn:tg-canary", "Weight": 10}
        ],
        "TargetGroupStickinessConfig": {
          "Enabled": true,
          "DurationSeconds": 3600
        }
      }
    }
  ]'

# ALB 属性配置
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "$ALB_ARN" \
  --attributes Key=idle_timeout.timeout_seconds,Value=60 \
               Key=routing.http2.enabled,Value=true \
               Key=routing.http.drop_invalid_header_fields.enabled,Value=true \
               Key=access_logs.s3.enabled,Value=true \
               Key=access_logs.s3.bucket,sre-alb-logs \
               Key=access_logs.s3.prefix,sre-app
```

### 9. 错误代码详解

```
┌─────────────────────────────────────────────────────────────────┐
│                    ELB 错误代码                                  │
│                                                                 │
│  ALB 错误：                                                      │
│  ┌──────────┬──────────────────────────────────────────────┐   │
│  │ 400      │ Bad Request — 请求格式错误                    │   │
│  │ 401      │ Unauthorized — 未认证                        │   │
│  │ 403      │ Forbidden — WAF 拒绝                         │   │
│  │ 404      │ Not Found — 无匹配路由规则                   │   │
│  │ 405      │ Method Not Allowed — HTTP 方法不支持         │   │
│  │ 408      │ Request Timeout — 客户端超时                 │   │
│  │ 413      │ Payload Too Large — 请求体超过限制           │   │
│  │ 421      │ Misdirected Request — SNI 不匹配             │   │
│  │ 429      │ Too Many Requests — WAF 速率限制             │   │
│  │ 460      │ Client IP 被 WAF 阻止                        │   │
│  │ 500      │ Internal Server Error — ALB 内部错误         │   │
│  │ 502      │ Bad Target — 目标返回无效响应                │   │
│  │ 503      │ No Target — 无健康目标                       │   │
│  │ 504      │ Target Timeout — 目标响应超时                │   │
│  │ 561      │ Auth Error — 认证失败（Cognito/OIDC）       │   │
│  └──────────┴──────────────────────────────────────────────┘   │
│                                                                 │
│  NLB 错误：                                                      │
│  ┌──────────┬──────────────────────────────────────────────┐   │
│  │ 0        │ Connection timed out — 连接超时              │   │
│  │ 502      │ Bad Gateway — 目标返回无效响应               │   │
│  └──────────┴──────────────────────────────────────────────┘   │
│                                                                 │
│  排查顺序：                                                      │
│  502 → 检查目标应用是否正常返回 HTTP 响应                       │
│  503 → 检查目标组是否有健康目标                                 │
│  504 → 检查应用响应时间，调整超时设置                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建 ALB

```bash
# 步骤 1: 创建安全组
ALB_SG=$(aws ec2 create-security-group \
  --group-name exercise-alb-sg \
  --description "Exercise ALB" \
  --vpc-id vpc-xxxx \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$ALB_SG" --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
  --group-id "$ALB_SG" --protocol tcp --port 443 --cidr 0.0.0.0/0

# 步骤 2: 创建 ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name exercise-alb \
  --type application \
  --subnets subnet-pub-1a subnet-pub-1b \
  --security-groups "$ALB_SG" \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# 步骤 3: 创建目标组
TG_ARN=$(aws elbv2 create-target-group \
  --name exercise-tg \
  --protocol HTTP --port 80 \
  --vpc-id vpc-xxxx \
  --health-check-path / \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# 步骤 4: 创建监听器
aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn="$TG_ARN"

# 步骤 5: 注册目标
aws elbv2 register-targets \
  --target-group-arn "$TG_ARN" \
  --targets Id=i-instance1 Id=i-instance2

# 步骤 6: 检查健康状态
aws elbv2 describe-target-health --target-group-arn "$TG_ARN"
```

### 练习 2：进阶场景 — 基于路径的路由

```bash
# 步骤 1: 创建多个目标组
TG_WEB=$(aws elbv2 create-target-group \
  --name exercise-web-tg --protocol HTTP --port 80 \
  --vpc-id vpc-xxxx --health-check-path / \
  --query "TargetGroups[0].TargetGroupArn" --output text)

TG_API=$(aws elbv2 create-target-group \
  --name exercise-api-tg --protocol HTTP --port 8080 \
  --vpc-id vpc-xxxx --health-check-path /api/health \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# 步骤 2: 创建监听器（默认 → Web）
LISTENER=$(aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn="$TG_WEB" \
  --query "Listeners[0].ListenerArn" --output text)

# 步骤 3: 添加路径规则
aws elbv2 create-rule \
  --listener-arn "$LISTENER" \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions Type=forward,TargetGroupArn="$TG_API"

# 步骤 4: 验证路由
curl http://<ALB-DNS>/           # → Web 目标组
curl http://<ALB-DNS>/api/users  # → API 目标组
```

### 练习 3：故障排查挑战 — 502 Bad Gateway

**场景：** ALB 返回 502 Bad Gateway。

```bash
# 排查步骤
# 1. 检查目标健康状态
aws elbv2 describe-target-health --target-group-arn "$TG_ARN"

# 2. 检查目标是否注册
aws elbv2 describe-target-group \
  --target-group-arn "$TG_ARN" \
  --query "TargetGroups[0].TargetGroupArn"

# 3. 检查目标应用是否监听正确端口
# SSH 到实例：
# ss -tlnp | grep 80

# 4. 检查目标应用是否返回有效 HTTP 响应
# curl -v http://localhost:80/

# 5. 检查安全组（ALB → 实例）
# ALB 安全组 → 实例安全组是否允许 80 端口

# 6. 检查 NACL
# 子网 NACL 是否允许 ALB 到实例的流量

# 答案：常见原因
# - 目标应用未启动
# - 安全组未开放端口
# - 目标组端口与应用端口不匹配
# - 应用返回非 HTTP 响应
```

---

## 🎯 面试题精选

### 题目 1：ALB 和 NLB 的区别？什么时候用哪个？

**答：**
- **ALB**：L7 层，支持 HTTP/HTTPS 路由、SSL 终止、基于路径/主机路由、WebSocket、WAF 集成。适用于 Web 应用和 API。
- **NLB**：L4 层，支持 TCP/UDP/TLS，超低延迟，保留源 IP，静态 IP。适用于游戏服务器、IoT、极低延迟需求。

### 题目 2：ALB 如何实现蓝绿部署？

**答：**
1. 创建两个目标组（Blue 和 Green）
2. 监听器默认路由到 Blue
3. 部署新版本到 Green 目标组
4. 验证 Green 健康后，修改监听器规则路由到 Green
5. 如果出问题，快速切回 Blue
6. 可以使用加权路由实现金丝雀发布（10% → 50% → 100%）

### 题目 3：健康检查返回什么状态码才算健康？

**答：** 默认接受 200-299 范围的状态码。可以通过 Matcher 参数自定义，例如：
- `200`：只有 200 OK
- `200-299`：任何 2xx
- `200,301,302`：特定状态码

### 题目 4：ALB 的空闲超时是什么？如何配置？

**答：** 空闲超时是 ALB 在关闭连接前等待客户端数据的时间。默认 60 秒，可配置到 4000 秒。对于 WebSocket 长连接，需要增加超时时间。

### 题目 5：如何在 ALB 上实现 WAF 保护？

**答：**
1. 创建 WAF Web ACL
2. 配置规则（IP 黑名单、速率限制、SQL 注入防护等）
3. 将 WAF Web ACL 关联到 ALB
4. 在 WAF 中监控和分析流量

### 题目 6：NLB 如何保留客户端源 IP？

**答：** NLB 默认保留客户端源 IP（不同于 ALB 使用 NAT）。目标实例看到的是客户端的真实 IP，不是 ALB 的 IP。但需要注意：
- 目标实例的安全组需要允许客户端 IP 范围
- 如果启用了 Proxy Protocol v2，需要应用解析 PROXY header

### 题目 7：ALB 的跨可用区负载均衡是如何工作的？

**答：** ALB 默认启用跨 AZ 负载均衡。每个 AZ 中的 ALB 节点将流量分发到同 AZ 的目标实例。如果某个 AZ 中没有注册目标，流量会被路由到其他 AZ。注意跨 AZ 流量会产生数据传输费用。

### 题目 8：如何排查 ALB 的 504 Gateway Timeout？

**答：**
1. 检查目标实例的响应时间（应用是否过慢）
2. 检查 ALB 空闲超时设置
3. 检查目标组的慢启动设置
4. 检查网络延迟（目标实例是否在同一个 Region）
5. 检查应用日志（是否有长时间运行的请求）

---

## 📚 深入阅读

- [ELB 官方文档](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html)
- [ALB 最佳实践](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancer-getting-started.html)
- [NLB 最佳实践](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/network-load-balancer-getting-started.html)
- [健康检查配置](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)
- [SSL 策略](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)

---

## ✅ 自检清单

- [ ] 能够区分 ALB、NLB、GWLB 的适用场景
- [ ] 能够创建和配置 ALB（监听器、目标组、规则）
- [ ] 能够配置健康检查并排查不健康目标
- [ ] 能够配置 SSL/TLS 终止
- [ ] 能够创建基于路径和主机名的路由规则
- [ ] 理解 WebSocket 和 HTTP/2 的支持
- [ ] 能够配置和分析 ALB 访问日志
- [ ] 能够排查 ELB 常见故障（502、503、504）
- [ ] 理解跨可用区负载均衡的工作原理
- [ ] 能够实现蓝绿部署和金丝雀发布
- [ ] 理解连接排空和慢启动的工作原理
