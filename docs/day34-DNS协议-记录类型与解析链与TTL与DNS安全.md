# Day 34: DNS 协议 — 记录类型、解析链、TTL 与 DNS 安全

> 📅 日期：2026-04-29  
> 📖 学习主题：DNS 协议 — 记录类型、解析链、TTL、DNS 安全  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 34 的学习后，你应该掌握：
- 理解 DNS 系统的基本架构和工作原理
- 掌握常见 DNS 记录类型及其用途
- 理解 DNS 完整解析链（递归查询 + 迭代查询）
- 掌握 TTL 的作用及对 DNS 变更的影响
- 了解 DNS 安全问题与防护措施
- 能够在 DNS 解析故障时快速定位和修复
- 使用 `dig +trace` 追踪完整 DNS 解析链
- 搭建 CoreDNS 并配置自定义解析

---

## 📖 详细知识点

### 1. DNS 概述

#### 1.1 什么是 DNS

DNS（Domain Name System，域名系统）是互联网的基础设施之一，负责将**人类可读的域名**（如 `www.example.com`）转换为**机器可读的 IP 地址**（如 `93.184.216.34`）。

```
用户输入：www.example.com
    │
    ▼
┌─────────────────┐
│   DNS 解析器     │  ← 你的电脑/路由器/DNS 服务器
│   执行解析查询   │
└────────┬────────┘
         │
         ▼
返回 IP：93.184.216.34
    │
    ▼
浏览器发起 HTTP 连接
```

#### 1.2 DNS 架构

DNS 是一个**分布式、层次化**的数据库系统：

```
                    . (根服务器，13组)
                   / \
                  /   \
           .com      .org      .net      .cn     (顶级域名 TLD)
          /    \        \
     example   google   mozilla               (二级域名)
        /  \
     www   mail                                (子域名/主机名)
```

#### 1.3 DNS 查询类型

| 类型 | 说明 | 谁发起 | 特点 |
|------|------|--------|------|
| 递归查询 | 客户端向 DNS 服务器发起，要求返回最终结果 | 客户端 → DNS | DNS 服务器代替客户端完成所有查询 |
| 迭代查询 | DNS 服务器之间的查询，返回参考答案 | DNS → DNS | 返回"去找这个服务器问" |

#### 1.4 DNS 端口

| 协议 | 端口 | 用途 |
|------|------|------|
| UDP | 53 | 标准 DNS 查询（大多数场景） |
| TCP | 53 | 区域传输（Zone Transfer）、大响应（>512 字节） |
| UDP/TCP | 853 | DNS over TLS (DoT) |
| TCP | 443 | DNS over HTTPS (DoH) |

---

### 2. DNS 记录类型

#### 2.1 常见记录类型详解

| 记录类型 | 全称 | 用途 | 示例 |
|---------|------|------|------|
| A | Address | 域名 → IPv4 地址 | `example.com. IN A 93.184.216.34` |
| AAAA | IPv6 Address | 域名 → IPv6 地址 | `example.com. IN AAAA 2606:2800:220::1` |
| CNAME | Canonical Name | 域名别名 → 真实域名 | `www.example.com. IN CNAME example.com.` |
| MX | Mail Exchange | 邮件服务器 | `example.com. IN MX 10 mail.example.com.` |
| NS | Name Server | 域名服务器 | `example.com. IN NS ns1.example.com.` |
| TXT | Text | 任意文本（SPF/DKIM/验证） | `example.com. IN TXT "v=spf1 -all"` |
| PTR | Pointer | IP → 域名（反向解析） | `34.216.184.93.in-addr.arpa. IN PTR example.com.` |
| SOA | Start of Authority | 区域起始授权 | 包含区域管理信息 |
| SRV | Service | 服务定位 | `_sip._tcp.example.com. IN SRV 10 60 5060 sip.example.com.` |
| CAA | Certification Authority Authorization | 限制可签发证书的 CA | `example.com. IN CAA 0 issue "letsencrypt.org"` |

#### 2.2 SOA 记录详解

SOA（Start of Authority）记录是每个 DNS 区域必须有的记录，包含区域的管理信息：

```
example.com.  IN  SOA  ns1.example.com. admin.example.com. (
    2024010101  ; Serial（序列号，格式 YYYYMMDDNN）
    3600        ; Refresh（从服务器刷新间隔，1小时）
    900         ; Retry（失败后重试间隔，15分钟）
    604800      ; Expire（数据过期时间，7天）
    86400       ; Minimum/Negative TTL（缓存否定响应时间，1天）
)
```

| 字段 | 含义 | SRE 关注点 |
|------|------|-----------|
| Serial | 区域版本号，每次修改需递增 | 从服务器以此判断是否更新 |
| Refresh | 从服务器检查主服务器更新的间隔 | 影响配置传播速度 |
| Retry | 从服务器连接失败后的重试间隔 | 影响故障恢复速度 |
| Expire | 从服务器无法连接主服务器时的数据有效期 | 影响数据一致性 |
| Minimum TTL | 否定响应（NXDOMAIN）的缓存时间 | 影响无效域名查询频率 |

#### 2.3 记录优先级（MX 记录）

MX 记录的优先级数字**越小越优先**：

```
example.com.  IN  MX  10  mail1.example.com.    ← 优先
example.com.  IN  MX  20  mail2.example.com.    ← 备用
example.com.  IN  MX  30  mail3.example.com.    ← 第三备用
```

如果优先级相同，则进行**负载均衡**（轮询）。

---

### 3. DNS 解析链

#### 3.1 完整解析流程

当你在浏览器输入 `www.example.com` 时，完整的 DNS 解析链如下：

```
Step 1: 本地缓存查询
    │
    ├── 浏览器缓存 → 命中？返回
    ├── 操作系统缓存 → 命中？返回
    │
    ▼ (未命中)
Step 2: 本地 DNS 解析器（ISP/公共 DNS）
    │
    ├── 解析器缓存 → 命中？返回
    │
    ▼ (未命中，开始迭代查询)
Step 3: 根服务器（Root Server）
    │  "我不知道 example.com 的 IP，但你去问 .com 的 TLD 服务器"
    │  返回：.com TLD 服务器地址
    ▼
Step 4: TLD 服务器（.com）
    │  "我不知道 example.com 的 IP，但你去问 example.com 的权威 DNS"
    │  返回：ns1.example.com 地址
    ▼
Step 5: 权威 DNS 服务器（ns1.example.com）
    │  "www.example.com 的 IP 是 93.184.216.34"
    │  返回：A 记录 93.184.216.34
    ▼
Step 6: 结果返回
    │
    ├── 解析器缓存结果（按 TTL）
    ├── 操作系统缓存
    └── 返回给应用程序
```

#### 3.2 解析链可视化

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────────┐
│  客户端   │─────▶│ 递归 DNS  │─────▶│ 根服务器  │      │              │
│          │      │ 解析器    │      │ .         │      │              │
│          │◀─────│          │◀─────│ 返回 TLD  │      │              │
│          │      │          │      │ 地址      │      │              │
│          │      │          │─────▶│ .com TLD  │      │              │
│          │◀─────│          │◀─────│ 返回 NS   │      │              │
│          │      │          │      │ 地址      │      │              │
│  获取 IP  │      │          │─────▶│ 权威 DNS  │      │              │
│ 93.184.. │◀─────│ 缓存结果 │◀─────│ 返回 A    │      │              │
│          │      │ (TTL)    │      │ 记录      │      │              │
└──────────┘      └──────────┘      └──────────┘      └──────────────┘
```

#### 3.3 缓存与 TTL

DNS 缓存存在于多个层级，每一层都按照 TTL（Time To Live）来决定缓存过期时间。

| 缓存层级 | 位置 | TTL 影响 |
|---------|------|---------|
| 浏览器缓存 | Chrome/Firefox 等浏览器内部 | 尊重 DNS TTL，部分浏览器有最短 TTL |
| OS 缓存 | Windows DNS Client / Linux nscd / systemd-resolved | 完全遵循 TTL |
| 递归 DNS 缓存 | ISP DNS / 8.8.8.8 / 1.1.1.1 | 遵循 TTL，但可能有上限 |
| 权威 DNS 缓存 | 域名注册商的 NS 服务器 | 不缓存自己的数据 |

---

### 4. TTL（生存时间）详解

#### 4.1 TTL 的作用

TTL 决定了 DNS 记录在缓存中可以存留的秒数。它直接影响：

- **DNS 变更的传播速度**：TTL 越小，变更生效越快
- **DNS 查询的延迟**：TTL 越小，缓存命中率越低，解析延迟越高
- **权威 DNS 的负载**：TTL 越小，权威 DNS 收到的查询越多

#### 4.2 TTL 策略建议

| 场景 | 推荐 TTL | 原因 |
|------|---------|------|
| 稳定不变的服务 | 86400（24 小时） | 减少查询，降低延迟 |
| 日常服务 | 3600（1 小时） | 平衡变更速度和查询量 |
| 即将迁移的服务 | 300（5 分钟） | 迁移前降低 TTL，加速切换 |
| 灾备切换 | 60（1 分钟） | 最小化切换影响时间 |
| 开发/测试环境 | 30（30 秒） | 快速验证配置变更 |

#### 4.3 TTL 变更的最佳实践

**场景**：需要将 `api.example.com` 从 `203.0.113.10` 迁移到 `203.0.113.20`。

**错误做法**：
```
时间线：
T = 0:    直接修改 A 记录 203.0.113.10 → 203.0.113.20，TTL=3600
T = 0~1h: 仍有大量用户缓存了旧 IP，访问到旧服务器
T = 1h:   大部分缓存过期，但仍有部分用户受影响
```

**正确做法**：
```
时间线：
T = -24h: 提前 24 小时将 TTL 从 3600 改为 60
T = -1h:  等待旧 TTL 过期，所有缓存都已使用新 TTL=60
T = 0:    修改 A 记录 203.0.113.10 → 203.0.113.20
T = 0~1m: 最多 1 分钟，所有缓存过期，用户访问新 IP
T = +1h:  确认迁移成功，可将 TTL 恢复为 3600
```

---

### 5. DNS 安全

#### 5.1 DNS 安全威胁

| 威胁类型 | 描述 | 影响 |
|---------|------|------|
| DNS 劫持 | 攻击者篡改 DNS 响应，指向恶意 IP | 钓鱼、中间人攻击 |
| DNS 缓存投毒 | 向 DNS 缓存注入伪造记录 | 大规模用户被导向恶意站点 |
| DNS 放大攻击 | 利用 DNS 响应放大进行 DDoS | 目标服务器被大量流量淹没 |
| DNS 隧道 | 利用 DNS 协议传输隐蔽数据 | 数据泄露、绕过防火墙 |
| 域名劫持 | 攻击者获取域名管理权限 | 完全控制域名解析 |

#### 5.2 DNS 安全防护措施

| 防护措施 | 说明 | 部署方式 |
|---------|------|---------|
| DNSSEC | 数字签名验证 DNS 响应真实性 | 在权威 DNS 上启用签名 |
| DNS over TLS (DoT) | 使用 TLS 加密 DNS 查询 | 端口 853 |
| DNS over HTTPS (DoH) | 使用 HTTPS 加密 DNS 查询 | 端口 443 |
| 响应速率限制 (RRL) | 限制同一查询的响应频率 | 权威 DNS 配置 |
| Split DNS | 内外网分离解析 | 内网/外网部署不同 DNS |
| 监控与告警 | 监控 DNS 解析异常 | Prometheus + DNS exporter |

#### 5.3 DNSSEC 原理

DNSSEC 通过在 DNS 记录上添加数字签名，确保 DNS 响应的完整性和真实性：

```
权威 DNS 使用私钥签名：
    A 记录 + 私钥签名 → 带签名的 RRSIG 记录

递归 DNS 验证：
    收到 A 记录 + RRSIG → 使用公钥验证签名
    验证通过 → 返回给客户端
    验证失败 → 拒绝响应
```

**DNSSEC 记录类型：**

| 记录 | 说明 |
|------|------|
| RRSIG | 资源记录签名 |
| DNSKEY | DNS 公钥 |
| DS | 委派签名者（父区域指向子区域的指纹） |
| NSEC/NSEC3 | 否定存在证明（证明某记录不存在） |

---

## 🏥 SRE 实战案例：DNS 解析到旧 IP → 修改 TTL 为 60 缩短影响

### 场景描述

某电商平台的订单服务域名 `orders.example.com` 需要从旧机房迁移到新机房。

**迁移前配置：**
- 域名：`orders.example.com`
- 当前 IP（旧机房）：`203.0.113.10`
- 新 IP（新机房）：`203.0.113.50`
- 当前 TTL：3600 秒（1 小时）

**问题**：在迁移窗口中，直接修改 DNS 记录后，大量用户仍在访问旧 IP，导致订单失败。

### 时间线还原

```
10:00  → 运维团队直接修改 A 记录: 203.0.113.10 → 203.0.113.50
10:05  → 收到告警：旧机房订单服务 QPS 未下降
10:15  → 大量用户投诉下单失败
10:30  → 发现原因：DNS 缓存 TTL=3600，大量用户仍解析到旧 IP
11:00  → TTL 开始过期，流量逐渐切换到新 IP
11:30  → 所有缓存过期，流量完全切换
```

**影响范围**：约 30 分钟的服务降级，影响约 15% 的用户。

### 正确的迁移方案

```bash
# =============================================
# Phase 1: 迁移前 24 小时
# =============================================

# 1. 查询当前 TTL
dig orders.example.com +noall +answer
# orders.example.com.  3600  IN  A  203.0.113.10

# 2. 降低 TTL（通过 DNS 管理控制台或 API）
# 将 TTL 从 3600 改为 60
# 使用云厂商 API 或 DNS 提供商的 API
# 示例（Cloudflare API）:
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  --data '{"ttl":60}'

# 3. 验证 TTL 已更新
dig orders.example.com +noall +answer
# orders.example.com.  60  IN  A  203.0.113.10   ← TTL 已变为 60

# =============================================
# Phase 2: 等待旧 TTL 过期（至少等待 1 小时）
# =============================================

# 4. 确认缓存中不再有旧 TTL 的记录
# 在不同地区进行 DNS 查询
dig @8.8.8.8 orders.example.com +noall +answer
dig @1.1.1.1 orders.example.com +noall +answer
dig @114.114.114.114 orders.example.com +noall +answer

# 5. 确认所有递归 DNS 都使用新 TTL=60
# 如果仍然看到 TTL > 60，说明还有缓存使用旧值
# 继续等待直到所有显示 TTL ≤ 60

# =============================================
# Phase 3: 执行迁移（T=0）
# =============================================

# 6. 记录当前时间
date "+%Y-%m-%d %H:%M:%S"

# 7. 修改 A 记录到新 IP
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  --data '{"content":"203.0.113.50"}'

# 8. 验证 DNS 记录已更新
dig orders.example.com +noall +answer
# orders.example.com.  60  IN  A  203.0.113.50   ← 已更新

# =============================================
# Phase 4: 监控切换进度
# =============================================

# 9. 持续监控 DNS 解析和流量切换
while true; do
    echo "$(date): $(dig +short orders.example.com @8.8.8.8)"
    echo "$(date): $(dig +short orders.example.com @1.1.1.1)"
    echo "$(date): $(dig +short orders.example.com @114.114.114.114)"
    sleep 10
done

# 10. 监控旧/新机房流量
# 在负载均衡器上查看
watch -n 5 'curl -s http://lb-metrics/qps?host=orders.example.com'

# =============================================
# Phase 5: 确认完成，恢复 TTL
# =============================================

# 11. 确认所有流量已切换到新 IP（等待约 10 分钟）
# 旧机房 QPS 降为 0

# 12. 恢复 TTL 到正常值
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  --data '{"ttl":3600}'
```

### DNS 迁移检查清单

| 阶段 | 检查项 | 状态 |
|------|--------|------|
| Phase 1 | 查询当前 TTL | □ |
| | 降低 TTL 到 60 | □ |
| | 验证 TTL 已生效 | □ |
| Phase 2 | 等待至少 1 小时（旧 TTL 时间） | □ |
| | 多地验证 TTL 均为 60 | □ |
| Phase 3 | 修改 A 记录到新 IP | □ |
| | 验证 A 记录已更新 | □ |
| Phase 4 | 多地验证解析到新 IP | □ |
| | 监控旧机房流量下降 | □ |
| | 监控新机房流量上升 | □ |
| Phase 5 | 确认旧机房流量为 0 | □ |
| | 恢复 TTL 到正常值 | □ |

### 经验总结

```
✅ 变更 DNS 前，务必检查当前 TTL 值
✅ 迁移前至少 24 小时降低 TTL
✅ 使用 +trace 或多地 dig 验证缓存状态
✅ 迁移过程中持续监控 DNS 解析和流量
✅ 重要服务考虑使用 CNAME + CDN/负载均衡器，避免直接改 A 记录
✅ 迁移完成后记得恢复 TTL
```

---

## 📝 练习：用 dig +trace 追踪完整 DNS 解析链

### 练习 1：基本 DNS 查询

```bash
# 1. 基本 A 记录查询
dig example.com

# 解读输出：
# ;; QUESTION SECTION:
# ;example.com.                 IN      A
#
# ;; ANSWER SECTION:
# example.com.          3600    IN      A       93.184.216.34
#                          ↑
#                        TTL = 3600 秒

# 2. 简洁输出（只看答案）
dig example.com +noall +answer

# 3. 查询特定记录类型
dig example.com AAAA     # IPv6
dig example.com MX       # 邮件服务器
dig example.com NS       # 域名服务器
dig example.com TXT      # 文本记录
dig example.com SOA      # 起始授权
dig example.com ANY      # 所有记录（部分服务器已禁用）

# 4. 指定 DNS 服务器查询
dig @8.8.8.8 example.com          # 使用 Google DNS
dig @1.1.1.1 example.com          # 使用 Cloudflare DNS
dig @114.114.114.114 example.com  # 使用国内 DNS
dig @ns1.example.com example.com  # 使用权威 DNS

# 5. 反向 DNS 查询（PTR）
dig -x 93.184.216.34
# 或
dig +short -x 93.184.216.34
```

### 练习 2：追踪完整 DNS 解析链

```bash
# +trace 会从根服务器开始，展示完整的迭代查询过程
dig +trace example.com

# 典型输出解读：
#
# ; <<>> DiG 9.16.1 <<>> +trace example.com
# ;; global options: +cmd
#
# ; <<>> 第一步：查询根服务器
# .                       518400  IN      NS      a.root-servers.net.
# ...
#
# ; <<>> 第二步：查询 .com TLD 服务器
# ;; Received 123 bytes from 198.41.0.4#53(a.root-servers.net)
# com.                    172800  IN      NS      a.gtld-servers.net.
# ...
#
# ; <<>> 第三步：查询 example.com 权威 DNS
# ;; Received 234 bytes from 192.5.6.30#53(a.gtld-servers.net)
# example.com.            172800  IN      NS      a.iana-servers.net.
# example.com.            172800  IN      NS      b.iana-servers.net.
#
# ; <<>> 第四步：获取最终 A 记录
# ;; Received 89 bytes from 199.43.135.53#53(a.iana-servers.net)
# example.com.            86400   IN      A       93.184.216.34
# example.com.            86400   IN      NS      a.iana-s.
```

### 练习 3：深入分析

```bash
# 1. 追踪并保存到文件
dig +trace example.com > dns_trace.log

# 2. 查看权威 DNS 服务器
dig example.com NS +noall +answer
dig example.com NS | grep "IN.*NS"

# 3. 查询权威 DNS 直接获取记录
# 先获取 NS
NS_SERVER=$(dig example.com NS +short | head -1)
# 再向权威 DNS 查询
dig @$NS_SERVER example.com A +noall +answer

# 4. 检查 DNSSEC 签名状态
dig example.com +dnssec +noall +answer
# 查看 RRSIG 记录

# 5. 检查 CNAME 链
dig +trace www.github.com +noall +answer
# 可能看到：
# www.github.com.  3600  IN  CNAME  github.com.
# github.com.      60    IN  A      140.82.121.4

# 6. 测量 DNS 解析延迟
dig example.com +stats | grep "Query time"
# 多次测量取平均
for i in {1..5}; do
    dig example.com +stats 2>/dev/null | grep "Query time"
done

# 7. 比较不同 DNS 服务器的解析结果
echo "=== Google DNS (8.8.8.8) ==="
dig @8.8.8.8 example.com +noall +answer

echo "=== Cloudflare DNS (1.1.1.1) ==="
dig @1.1.1.1 example.com +noall +answer

echo "=== 阿里 DNS (223.5.5.5) ==="
dig @223.5.5.5 example.com +noall +answer

# 8. 批量查询多个域名
for domain in google.com github.com example.com; do
    echo -n "$domain → "
    dig +short $domain A
done
```

### 练习 4：nslookup 对比

```bash
# nslookup 是另一种 DNS 查询工具
nslookup example.com
nslookup example.com 8.8.8.8

# 交互模式
nslookup
> server 8.8.8.8
> set type=MX
> example.com
> set type=NS
> example.com
> exit
```

---

## 🚀 扩展实践：搭建 CoreDNS 配置自定义解析

### 实验目标

使用 CoreDNS 搭建一个内部 DNS 服务器，配置自定义域名解析，实现类似 Kubernetes 集群内 DNS 的功能。

### 环境准备

```bash
# 安装 CoreDNS
# 方法 1: 直接下载二进制
wget https://github.com/coredns/coredns/releases/download/v1.11.1/coredns_1.11.1_linux_amd64.tgz
tar -xzf coredns_1.11.1_linux_amd64.tgz
mv coredns /usr/local/bin/

# 方法 2: 使用 Docker
docker run -d --name coredns \
  -p 53:53/udp -p 53:53/tcp \
  -v /etc/coredns:/rootfs/etc/coredns \
  coredns/coredns:latest

# 验证安装
coredns -version
# CoreDNS-1.11.1
# linux/amd64, go1.21.0, ...
```

### Corefile 配置

CoreDNS 使用 `Corefile` 作为配置文件：

```bash
# 创建配置目录
mkdir -p /etc/coredns

# 创建 Corefile
cat > /etc/coredns/Corefile << 'EOF'
# 全局配置
. {
    # 错误日志
    errors
    
    # 健康检查端点
    health :8080
    
    # Prometheus 指标
    prometheus :9153
}

# 自定义域名区域：example.local
example.local {
    # 日志
    log
    
    # 错误日志
    errors
    
    # 静态主机文件
    hosts {
        10.0.1.10    web-server.example.local
        10.0.1.11    api-server.example.local
        10.0.1.12    db-server.example.local
        10.0.2.10    cache-01.example.local
        10.0.2.11    cache-02.example.local
        
        # 泛域名解析
        10.0.3.0    *.monitoring.example.local
        
        # 回退到系统 /etc/hosts
        fallthrough
    }
    
    # TTL 设置
    ttl 60
}

# 集群内部域名：cluster.local（模拟 Kubernetes）
cluster.local {
    errors
    log
    
    # 自定义记录
    hosts {
        10.96.0.1    kubernetes.default.svc.cluster.local
        10.96.0.10   kube-dns.kube-system.svc.cluster.local
        fallthrough
    }
    
    # 服务发现（需要 etcd 插件）
    # etcd cluster.local {
    #     endpoint http://localhost:2379
    # }
    
    ttl 30
}

# 转发外部 DNS 查询
. {
    forward . 8.8.8.8 1.1.1.1 {
        # 健康检查上游 DNS
        health_check 5s
        # 最大并发
        max_concurrent 1000
    }
    
    # 缓存
    cache 300
    
    # 负载均衡（轮询）
    loop
}
EOF
```

### 启动与测试

```bash
# 启动 CoreDNS
coredns -conf /etc/coredns/Corefile

# 或使用 systemd 管理
cat > /etc/systemd/system/coredns.service << 'EOF'
[Unit]
Description=CoreDNS DNS Server
After=network.target

[Service]
ExecStart=/usr/local/bin/coredns -conf /etc/coredns/Corefile
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable coredns
systemctl start coredns
systemctl status coredns

# =============================================
# 测试自定义解析
# =============================================

# 测试静态主机解析
dig @127.0.0.1 web-server.example.local +noall +answer
# web-server.example.local.  60  IN  A  10.0.1.10

dig @127.0.0.1 api-server.example.local +noall +answer
# api-server.example.local.  60  IN  A  10.0.1.11

# 测试集群域名解析
dig @127.0.0.1 kubernetes.default.svc.cluster.local +noall +answer
# kubernetes.default.svc.cluster.local.  30  IN  A  10.96.0.1

# 测试外部域名转发
dig @127.0.0.1 example.com +noall +answer
# 应该返回公网 IP

# 测试反向解析
dig @127.0.0.1 -x 10.0.1.10 +noall +answer

# 测试不存在的域名
dig @127.0.0.1 nonexistent.example.local +noall +answer
# 应该返回 NXDOMAIN

# =============================================
# 验证监控指标
# =============================================

# CoreDNS 暴露 Prometheus 指标
curl http://localhost:9153/metrics | grep coredns

# 健康检查
curl http://localhost:8080/health

# 查看日志
journalctl -u coredns -f
```

### CoreDNS 进阶配置

```bash
# 1. 使用 Rewrite 插件实现域名重写
# 场景：将旧域名重定向到新域名
cat >> /etc/coredns/Corefile << 'EOF'

example.com {
    # 将 orders.example.com 重写为 orders-v2.example.com
    rewrite name exact orders.example.com orders-v2.example.com
    
    # 子域名重写
    rewrite name regex (.*)\.old\.example\.com {1}.new.example.com
    
    forward . 8.8.8.8
    cache 30
}
EOF

# 2. 使用 Template 插件实现动态记录
cat >> /etc/coredns/Corefile << 'EOF'

service.local {
    template IN A service.local {
        match "^web-(\d+)\.service\.local\.$"
        answer "web-{1}.service.local. 60 IN A 10.0.1.{1}"
        fallthrough
    }
    
    errors
    log
}
EOF

# 3. 使用 Rewrite 实现 DNS 视图（Split DNS）
cat >> /etc/coredns/Corefile << 'EOF'

. {
    # 根据来源 IP 返回不同结果
    view internal {
        acl 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16
        rewrite name example.com internal.example.com
    }
    
    forward . 8.8.8.8
    cache 300
}
EOF

# 4. 使用 Auto 插件自动加载区域文件
cat >> /etc/coredns/Corefile << 'EOF'

example.local {
    auto {
        directory /etc/coredns/zones
        reload 10s
    }
    errors
    log
}
EOF

# 创建区域文件
mkdir -p /etc/coredns/zones
cat > /etc/coredns/zones/db.example.local << 'EOF'
$TTL 60
@   IN  SOA ns1.example.local. admin.example.local. (
    2024010101  ; serial
    3600        ; refresh
    900         ; retry
    604800      ; expire
    86400       ; minimum
)

@       IN  NS  ns1.example.local.
ns1     IN  A   10.0.0.1
web     IN  A   10.0.1.10
api     IN  A   10.0.1.11
db      IN  A   10.0.1.12
mail    IN  MX  10  mail.example.local.
mail    IN  A   10.0.1.20
EOF
```

### CoreDNS 在 Kubernetes 中的角色

```bash
# Kubernetes 默认使用 CoreDNS 作为集群 DNS
# 查看 CoreDNS 配置
kubectl -n kube-system get configmap coredns -o yaml

# 查看 CoreDNS Pod
kubectl -n kube-system get pods -l k8s-app=kube-dns

# CoreDNS 在 K8s 中的 Corefile 通常包含：
# .:53 {
#     errors
#     health { lameduck 5s }
#     ready
#     kubernetes cluster.local in-addr.arpa ip6.arpa {
#         pods insecure
#         fallthrough in-addr.arpa ip6.arpa
#     }
#     prometheus :9153
#     forward . /etc/resolv.conf
#     cache 30
#     loop
#     reload
#     loadbalance
# }
```

---

## 📚 扩展阅读与资源

### 参考文档
- [RFC 1035 - DNS 规范](https://datatracker.ietf.org/doc/html/rfc1035)
- [RFC 4033/4034/4035 - DNSSEC](https://datatracker.ietf.org/doc/html/rfc4033)
- [RFC 7858 - DNS over TLS](https://datatracker.ietf.org/doc/html/rfc7858)
- [RFC 8484 - DNS over HTTPS](https://datatracker.ietf.org/doc/html/rfc8484)
- [CoreDNS 官方文档](https://coredns.io/manual/)

### 实用工具
| 工具 | 用途 |
|------|------|
| `dig` | DNS 查询（推荐） |
| `nslookup` | DNS 查询（传统） |
| `host` | 简洁 DNS 查询 |
| `dnstop` | DNS 流量分析 |
| `dnsperf` | DNS 性能测试 |
| `kdig` | DNSSEC 感知查询 |

### 公共 DNS 服务

| 服务商 | IPv4 | IPv6 | 特点 |
|--------|------|------|------|
| Google | 8.8.8.8, 8.8.4.4 | 2001:4860:4860::8888 | 全球覆盖广 |
| Cloudflare | 1.1.1.1, 1.0.0.1 | 2606:4700:4700::1111 | 隐私保护，快速 |
| 阿里 | 223.5.5.5, 223.6.6.6 | 2400:3200::1 | 国内快速 |
| 腾讯 | 119.29.29.29 | — | 国内，防劫持 |
| 114 | 114.114.114.114 | — | 国内老牌 |

---

## 📝 总结

| 知识点 | 关键要点 |
|--------|---------|
| DNS 架构 | 分布式层次化系统，根 → TLD → 权威 DNS |
| 记录类型 | A/AAAA/CNAME/MX/NS/TXT/SOA 等，各司其职 |
| 解析链 | 递归查询 + 迭代查询，多级缓存加速 |
| TTL | 控制缓存时间，变更前提前降低 TTL |
| DNS 安全 | DNSSEC/DoT/DoH 是主要防护手段 |
| SRE 实战 | DNS 迁移需遵循"降 TTL → 等待 → 改记录 → 监控"流程 |
| CoreDNS | 现代 DNS 服务器，K8s 默认组件，支持丰富插件 |

---

> 💡 **SRE 思考题**：如果你的线上服务通过 CDN 访问，CDN 的 CNAME 指向了某个域名，当 CDN 切换节点时，你的 DNS TTL 应该如何设置才能保证用户体验和切换速度的平衡？
