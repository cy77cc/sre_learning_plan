# Day 34: DNS 协议 — 记录类型、解析链、TTL、DNS 安全

> 📅 日期：2026-05-02
> 📖 学习主题：DNS 协议 — 记录类型、解析链、TTL、DNS 安全、CoreDNS
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 32（IP 协议）

---

## 🎯 学习目标

完成 Day 34 的学习后，你应该掌握：
- 深入理解 DNS 协议架构和查询类型
- 掌握所有常见 DNS 记录类型及其用途
- 理解 DNS 完整解析链路（浏览器 → OS → 递归 DNS → 根 → TLD → 权威）
- 掌握 TTL 的作用和调优策略
- 了解 DNS 安全威胁和防护措施（DNSSEC、DoT、DoH）
- 掌握 DNS 负载均衡和故障转移
- 熟练使用 dig 命令进行 DNS 调试
- 能够排查 K8s Pod DNS 解析问题

---

## 📖 核心知识点

### 1. DNS 协议深入

#### 1.1 DNS 架构

```
                        . (根服务器，13 组)
                       /|\
                      / | \
                     /  |  \
                .com  .org  .net  .cn  ...  (顶级域名 TLD)
               / | \
              /  |  \
         example google github  ...  (二级域名)
          / \
       www   mail                    (子域名/主机名)
```

**DNS 服务器类型：**

| 类型 | 说明 | 示例 |
|------|------|------|
| 根 DNS 服务器 | 管理根域（.） | a.root-servers.net ~ m.root-servers.net |
| TLD DNS 服务器 | 管理顶级域名 | .com, .org, .cn 的权威服务器 |
| 权威 DNS 服务器 | 管理特定域名 | ns1.example.com |
| 递归 DNS 服务器 | 代替客户端查询 | ISP DNS, 8.8.8.8, 1.1.1.1 |

#### 1.2 递归查询 vs 迭代查询

```
递归查询（Recursive Query）：
  客户端 → 递归 DNS："请告诉我 www.example.com 的 IP"
  递归 DNS → 客户端："是 93.184.216.34"
  
  特点：递归 DNS 代替客户端完成所有查询工作
  场景：客户端 → 递归 DNS

迭代查询（Iterative Query）：
  递归 DNS → 根 DNS："www.example.com 的 IP？"
  根 DNS → 递归 DNS："我不知道，你去问 .com 的 TLD 服务器"
  递归 DNS → TLD DNS："www.example.com 的 IP？"
  TLD DNS → 递归 DNS："我不知道，你去问 example.com 的权威 DNS"
  递归 DNS → 权威 DNS："www.example.com 的 IP？"
  权威 DNS → 递归 DNS："是 93.184.216.34"
  
  特点：每次返回"参考答案"，告诉查询者去找谁
  场景：递归 DNS → 其他 DNS 服务器
```

#### 1.3 DNS 端口和协议

| 协议 | 端口 | 用途 | 特点 |
|------|------|------|------|
| UDP | 53 | 标准 DNS 查询 | 快速，最大 512 字节（EDNS 可扩展） |
| TCP | 53 | 区域传输、大响应 | 可靠，超过 512 字节时使用 |
| UDP/TCP | 853 | DNS over TLS (DoT) | 加密，防窃听 |
| TCP | 443 | DNS over HTTPS (DoH) | 加密，与 HTTPS 流量混合 |

```bash
# 查看 DNS 相关连接
ss -tunp | grep :53
ss -tunp | grep :853
ss -tunp | grep :443

# 测试 DNS over TLS
kdig @1.1.1.1 +tls example.com

# 测试 DNS over HTTPS
curl -s "https://dns.google/dns-query?name=example.com&type=A" -H "Accept: application/dns-json"
```

---

### 2. DNS 记录类型详解

#### 2.1 常见记录类型

| 记录类型 | 全称 | 用途 | 示例 |
|---------|------|------|------|
| A | Address | 域名 → IPv4 | `example.com. IN A 93.184.216.34` |
| AAAA | IPv6 Address | 域名 → IPv6 | `example.com. IN AAAA 2606:2800:220::1` |
| CNAME | Canonical Name | 域名别名 | `www.example.com. IN CNAME example.com.` |
| MX | Mail Exchange | 邮件服务器 | `example.com. IN MX 10 mail.example.com.` |
| NS | Name Server | 域名服务器 | `example.com. IN NS ns1.example.com.` |
| TXT | Text | 文本记录 | `example.com. IN TXT "v=spf1 -all"` |
| PTR | Pointer | IP → 域名（反向） | `34.216.184.93.in-addr.arpa. IN PTR example.com.` |
| SOA | Start of Authority | 区域起始授权 | 包含区域管理信息 |
| SRV | Service | 服务定位 | `_sip._tcp.example.com. IN SRV 10 60 5060 sip.example.com.` |
| CAA | CA Authorization | 限制 CA | `example.com. IN CAA 0 issue "letsencrypt.org"` |

#### 2.2 各记录类型详解

**A 记录和 AAAA 记录：**

```bash
# 查询 A 记录
dig example.com A +short
# 93.184.216.34

# 查询 AAAA 记录
dig example.com AAAA +short
# 2606:2800:220:1::247

# 一个域名可以有多个 A 记录（负载均衡）
dig google.com A +short
# 142.250.80.46
# 142.250.80.78
# 142.250.80.110
# ...
```

**CNAME 记录：**

```bash
# CNAME 将一个域名指向另一个域名
# 注意：CNAME 不能与其他记录共存（除了 DNSSEC 相关）

# 示例
dig www.github.com +noall +answer
# www.github.com.    3600    IN    CNAME    github.com.
# github.com.        60      IN    A        140.82.121.4

# CNAME 链
# cdn.example.com → lb.example.com → actual-server.example.com
# 解析时会递归查询 CNAME 目标
```

**MX 记录：**

```bash
# MX 记录指定邮件服务器，优先级数字越小越优先
dig example.com MX +noall +answer
# example.com.    3600    IN    MX    10 mail.example.com.
# example.com.    3600    IN    MX    20 mail2.example.com.

# 优先级相同则负载均衡
# example.com.    IN    MX    10 mail1.example.com.
# example.com.    IN    MX    10 mail2.example.com.
```

**TXT 记录：**

```bash
# TXT 记录用途：
# 1. SPF（发件人策略框架）
dig example.com TXT +short
# "v=spf1 include:_spf.example.com ~all"

# 2. DKIM（域名密钥识别邮件）
dig selector._domainkey.example.com TXT +short

# 3. DMARC（域名消息认证报告和一致性）
dig _dmarc.example.com TXT +short

# 4. 域名验证（Let's Encrypt、Google 等）
# _acme-challenge.example.com IN TXT "验证字符串"

# 5. 其他用途
dig _dmarc.example.com TXT +short
# "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
```

**SRV 记录：**

```bash
# SRV 记录格式：_服务._协议.域名 TTL IN SRV 优先级 权重 端口 目标

# 示例：查找 SIP 服务
dig _sip._tcp.example.com SRV +noall +answer
# _sip._tcp.example.com. 3600 IN SRV 10 60 5060 sip.example.com.
#                         ↑     ↑   ↑  ↑    ↑
#                         TTL   类型 优先级 权重 端口 目标

# K8s 中的 SRV 记录
# _tcp._http.my-service.default.svc.cluster.local
```

**SOA 记录：**

```bash
# SOA 记录包含区域的管理信息
dig example.com SOA +noall +answer
# example.com. 86400 IN SOA ns1.example.com. admin.example.com. (
#     2024010101  ; Serial（序列号）
#     3600        ; Refresh（刷新间隔）
#     900         ; Retry（重试间隔）
#     604800      ; Expire（过期时间）
#     86400       ; Minimum TTL（否定缓存 TTL）
# )

# Serial 用于主从同步，修改 DNS 记录后必须递增
# 从服务器根据 Serial 判断是否需要更新
```

**PTR 记录（反向解析）：**

```bash
# PTR 记录将 IP 地址解析为域名
# 反向解析区域：in-addr.arpa

# IPv4 反向解析
dig -x 93.184.216.34 +short
# example.com.

# IPv6 反向解析
dig -x 2606:2800:220::1 +short

# 反向解析区域格式：
# 34.216.184.93.in-addr.arpa. IN PTR example.com.

# 验证邮件服务器的 PTR 记录（反垃圾邮件）
dig -x 203.0.113.10 +short
# mail.example.com.
```

**CAA 记录：**

```bash
# CAA 记录限制哪些 CA 可以为域名签发证书
dig example.com CAA +short
# 0 issue "letsencrypt.org"
# 0 issuewild "letsencrypt.org"
# 0 iodef "mailto:caa@example.com"

# 参数说明：
# 0: 标志位（0=非关键，128=关键）
# issue: 允许签发普通证书的 CA
# issuewild: 允许签发通配符证书的 CA
# iodef: 违规报告地址
```

---

### 3. DNS 解析完整链路

#### 3.1 完整解析流程

```
用户在浏览器输入 www.example.com

┌─────────────────────────────────────────────────────────────┐
│ Step 1: 浏览器缓存                                           │
│   检查浏览器 DNS 缓存                                        │
│   → 命中：直接使用缓存的 IP                                   │
│   → 未命中：继续                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 操作系统缓存                                         │
│   检查 OS DNS 缓存（Linux: systemd-resolved/nscd）           │
│   → 命中：返回 IP                                            │
│   → 未命中：继续                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 本地 DNS 解析器（递归 DNS）                           │
│   查询 /etc/resolv.conf 中配置的 DNS 服务器                   │
│   → 缓存命中：返回 IP                                         │
│   → 缓存未命中：开始迭代查询                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 查询根服务器                                         │
│   递归 DNS → 根服务器："www.example.com 的 IP？"              │
│   根服务器 → 递归 DNS："去问 .com 的 TLD 服务器"               │
│   返回：.com TLD 服务器地址列表                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 查询 TLD 服务器                                      │
│   递归 DNS → .com TLD："www.example.com 的 IP？"              │
│   .com TLD → 递归 DNS："去问 example.com 的权威 DNS"           │
│   返回：ns1.example.com 地址                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: 查询权威 DNS                                         │
│   递归 DNS → ns1.example.com："www.example.com 的 IP？"       │
│   权威 DNS → 递归 DNS："93.184.216.34"                        │
│   返回：A 记录 + TTL                                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7: 缓存并返回结果                                       │
│   递归 DNS 缓存结果（按 TTL）                                 │
│   操作系统缓存结果                                             │
│   浏览器缓存结果                                               │
│   返回 IP 给浏览器                                            │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 DNS 缓存层次

| 缓存层级 | 位置 | TTL 影响 | 持久性 |
|---------|------|---------|--------|
| 浏览器缓存 | Chrome/Firefox 内部 | 尊重 TTL，部分有最短限制 | 关闭浏览器清除 |
| OS 缓存 | systemd-resolved/nscd | 完全遵循 TTL | 重启服务清除 |
| 递归 DNS 缓存 | ISP/8.8.8.8/1.1.1.1 | 遵循 TTL | 服务重启清除 |
| 应用缓存 | 应用程序内部 | 自定义 | 应用重启清除 |

```bash
# 查看各层缓存

# 1. 浏览器缓存
# Chrome: chrome://net-internals/#dns
# Firefox: about:networking#dns

# 2. Linux OS 缓存
# systemd-resolved
systemd-resolve --statistics
resolvectl statistics

# 清除 systemd-resolved 缓存
systemd-resolve --flush-caches
resolvectl flush-caches

# nscd（如果使用）
nscd -g  # 查看统计
nscd -i hosts  # 清除 hosts 缓存

# 3. 查看 /etc/resolv.conf
cat /etc/resolv.conf
# nameserver 8.8.8.8
# nameserver 1.1.1.1
```

---

### 4. TTL 的作用和调优

#### 4.1 TTL 的作用

```
TTL（Time To Live）决定 DNS 记录在缓存中存留的秒数：

影响因素：
  TTL 大 → 缓存时间长 → 查询延迟低 → 权威 DNS 负载低
            但：变更生效慢

  TTL 小 → 缓存时间短 → 变更生效快
            但：查询延迟高 → 权威 DNS 负载高
```

#### 4.2 TTL 策略建议

| 场景 | 推荐 TTL | 原因 |
|------|---------|------|
| 稳定不变的服务 | 86400（24 小时） | 减少查询，降低延迟 |
| 日常服务 | 3600（1 小时） | 平衡变更速度和查询量 |
| 即将迁移的服务 | 300（5 分钟） | 迁移前降低 TTL |
| 灾备切换 | 60（1 分钟） | 最小化切换影响 |
| 开发/测试环境 | 30（30 秒） | 快速验证变更 |

#### 4.3 DNS 迁移最佳实践

**错误做法：**

```
时间线：
T = 0:    直接修改 A 记录 203.0.113.10 → 203.0.113.20，TTL=3600
T = 0~1h: 仍有大量用户缓存了旧 IP，访问到旧服务器
T = 1h:   大部分缓存过期，但仍有部分用户受影响
```

**正确做法：**

```
时间线：
T = -24h: 提前 24 小时将 TTL 从 3600 改为 60
T = -1h:  等待旧 TTL（3600）过期，所有缓存都使用新 TTL=60
T = 0:    修改 A 记录 203.0.113.10 → 203.0.113.20
T = 0~1m: 最多 1 分钟，所有缓存过期，用户访问新 IP
T = +1h:  确认迁移成功，将 TTL 恢复为 3600
```

```bash
# DNS 迁移脚本
#!/bin/bash
# dns_migration.sh - DNS 迁移自动化脚本

DOMAIN="orders.example.com"
OLD_IP="203.0.113.10"
NEW_IP="203.0.113.50"
LOW_TTL=60
NORMAL_TTL=3600

# Phase 1: 降低 TTL
echo "Phase 1: 降低 TTL 到 $LOW_TTL"
# 调用 DNS API 修改 TTL
# curl -X PATCH "https://api.dns-provider.com/..." -d '{"ttl":60}'

# 验证 TTL
echo "验证 TTL:"
dig $DOMAIN +noall +answer

# Phase 2: 等待旧 TTL 过期
echo "Phase 2: 等待旧 TTL 过期（至少 1 小时）"
sleep 3600

# Phase 3: 修改 A 记录
echo "Phase 3: 修改 A 记录到 $NEW_IP"
# 调用 DNS API 修改 A 记录
# curl -X PATCH "https://api.dns-provider.com/..." -d '{"content":"203.0.113.50"}'

# Phase 4: 验证
echo "Phase 4: 验证解析结果"
for dns in 8.8.8.8 1.1.1.1 223.5.5.5; do
    result=$(dig +short $DOMAIN @$dns)
    echo "  $dns: $result"
done

# Phase 5: 恢复 TTL
echo "Phase 5: 恢复 TTL 到 $NORMAL_TTL"
# curl -X PATCH "https://api.dns-provider.com/..." -d '{"ttl":3600}'
```

---

### 5. DNS 安全

#### 5.1 DNS 安全威胁

| 威胁类型 | 描述 | 影响 | 防护措施 |
|---------|------|------|---------|
| DNS 劫持 | 篡改 DNS 响应 | 钓鱼、中间人 | DNSSEC、DoH/DoT |
| DNS 缓存投毒 | 注入伪造缓存记录 | 大规模用户受影响 | DNSSEC、随机源端口 |
| DNS 放大攻击 | 利用响应放大进行 DDoS | 目标被流量淹没 | 响应速率限制 |
| DNS 隧道 | 利用 DNS 传输隐蔽数据 | 数据泄露 | 深度包检测 |
| 域名劫持 | 获取域名管理权限 | 完全控制域名 | 注册商锁定 |

#### 5.2 DNS 劫持详解

```
DNS 劫持场景：

正常解析：
  用户 → DNS 查询 → 权威 DNS → 返回正确 IP (203.0.113.10)

劫持后：
  用户 → DNS 查询 → [攻击者拦截] → 返回恶意 IP (10.0.0.99)
  
  用户访问 10.0.0.99 → 钓鱼网站/恶意软件

劫持方式：
1. 本地 DNS 劫持：修改 hosts 文件、恶意软件
2. 路由器 DNS 劫持：入侵路由器修改 DNS 配置
3. ISP DNS 劫持：ISP 篡改 DNS 响应（插入广告）
4. 中间人攻击：网络层拦截 DNS 流量
```

**防护措施：**

```bash
# 1. 使用加密 DNS（DoH/DoT）
# 配置 systemd-resolved 使用 DoT
# /etc/systemd/resolved.conf
# [Resolve]
# DNS=1.1.1.1#cloudflare-dns.com
# DNSOverTLS=yes

# 2. 使用 DNSSEC
# 验证 DNSSEC 签名
dig example.com +dnssec +noall +answer

# 3. 监控 DNS 变化
#!/bin/bash
# monitor_dns.sh
DOMAIN="example.com"
EXPECTED_IP="203.0.113.10"
CURRENT_IP=$(dig +short $DOMAIN A)

if [ "$CURRENT_IP" != "$EXPECTED_IP" ]; then
    echo "ALERT: DNS change detected for $DOMAIN"
    echo "Expected: $EXPECTED_IP"
    echo "Current: $CURRENT_IP"
    # 发送告警
fi

# 4. 使用多个 DNS 服务器对比
for dns in 8.8.8.8 1.1.1.1 223.5.5.5 114.114.114.114; do
    echo "$dns: $(dig +short example.com @$dns)"
done
```

#### 5.3 DNS 缓存投毒

```
DNS 缓存投毒原理：

1. 攻击者向递归 DNS 发送大量查询请求
2. 同时发送伪造的 DNS 响应
3. 如果伪造响应先于真实响应到达，递归 DNS 会缓存伪造记录
4. 后续查询该域名的用户都会得到错误的 IP

防护措施：
1. DNSSEC：验证 DNS 响应的数字签名
2. 随机化源端口：增加伪造难度
3. 随机化事务 ID：增加猜测难度
4. 缩短缓存时间：减少影响范围
```

#### 5.4 DNSSEC 原理

```
DNSSEC 通过数字签名验证 DNS 响应的真实性：

签名过程（权威 DNS）：
  1. 对 DNS 记录计算哈希
  2. 使用私钥对哈希签名
  3. 生成 RRSIG 记录（签名）

验证过程（递归 DNS）：
  1. 收到 DNS 记录 + RRSIG
  2. 使用 DNSKEY 中的公钥验证签名
  3. 验证 DS 记录确认公钥的真实性
  4. 验证通过 → 返回结果
  5. 验证失败 → 拒绝响应

DNSSEC 记录类型：
  RRSIG: 资源记录签名
  DNSKEY: DNS 公钥
  DS: 委派签名者（父→子的信任链）
  NSEC/NSEC3: 否定存在证明
```

```bash
# 验证 DNSSEC
dig example.com +dnssec +noall +answer
# example.com.    3600    IN    A    93.184.216.34
# example.com.    3600    IN    RRSIG A 13 2 3600 (
#                 20240101000000 20231201000000
#                 12345 example.com.
#                 abcdef1234567890... )

# 查看 DNSKEY
dig example.com DNSKEY +noall +answer

# 查看 DS 记录
dig example.com DS +noall +answer

# 使用 delv 工具验证 DNSSEC
delv example.com A
```

#### 5.5 DNS over HTTPS (DoH) 和 DNS over TLS (DoT)

```
传统 DNS：
  明文传输，容易被窃听和篡改
  
DNS over TLS (DoT)：
  使用 TLS 加密 DNS 查询
  端口：853
  协议：TCP + TLS
  
DNS over HTTPS (DoH)：
  使用 HTTPS 加密 DNS 查询
  端口：443
  协议：HTTPS
  优点：与普通 HTTPS 流量混合，难以被封锁
```

```bash
# 配置 systemd-resolved 使用 DoT
# /etc/systemd/resolved.conf
[Resolve]
DNS=1.1.1.1#cloudflare-dns.com
DNS=8.8.8.8#dns.google
DNSOverTLS=yes
DNSSEC=yes

# 重启服务
systemctl restart systemd-resolved

# 测试 DoH
curl -s "https://dns.google/dns-query?name=example.com&type=A" \
    -H "Accept: application/dns-json" | jq .

curl -s "https://cloudflare-dns.com/dns-query?name=example.com&type=A" \
    -H "Accept: application/dns-json" | jq .
```

---

### 6. DNS 负载均衡

#### 6.1 轮询（Round Robin）

```bash
# 一个域名配置多个 A 记录
dig google.com A +short
# 142.250.80.46
# 142.250.80.78
# 142.250.80.110

# 客户端按顺序使用不同的 IP
# 第 1 次查询：142.250.80.46
# 第 2 次查询：142.250.80.78
# 第 3 次查询：142.250.80.110

# 优点：简单，无需额外设备
# 缺点：不支持健康检查，无法按权重分配
```

#### 6.2 加权轮询

```bash
# 使用 DNS 服务商的加权轮询功能
# 示例：Cloudflare、AWS Route 53、阿里云 DNS

# 配置示例（伪代码）：
# www.example.com A 203.0.113.10 weight=80
# www.example.com A 203.0.113.20 weight=20
# → 80% 流量到 .10，20% 流量到 .20
```

#### 6.3 地理位置路由

```bash
# 根据用户地理位置返回最近的服务器 IP

# 中国用户 → 203.0.113.10（国内机房）
# 美国用户 → 198.51.100.10（美国机房）
# 欧洲用户 → 192.0.2.10（欧洲机房）

# 使用 GeoIP 数据库
# dig @geo-dns.example.com www.example.com
# 从中国查询：203.0.113.10
# 从美国查询：198.51.100.10
```

#### 6.4 故障转移（DNS Failover）

```
场景：主服务器故障时自动切换到备用服务器

配置：
  www.example.com A 203.0.113.10 (主)
  www.example.com A 203.0.113.20 (备用)

DNS 服务商健康检查：
  每 30 秒检查 203.0.113.10 是否可用
  如果连续 3 次检查失败：
    → 移除 203.0.113.10 的 A 记录
    → 只返回 203.0.113.20

  当 203.0.113.10 恢复后：
    → 重新添加 A 记录
    → 流量切换回主服务器
```

---

### 7. CoreDNS（K8s 内部 DNS）

#### 7.1 CoreDNS 简介

```
CoreDNS 是 Kubernetes 默认的 DNS 服务器：
- 插件化架构
- 支持多种后端（文件、etcd、Kubernetes API）
- 高性能、低延迟
- 支持 Prometheus 监控

K8s 中的 DNS 记录格式：
  Service: <service>.<namespace>.svc.cluster.local
  Pod: <pod-ip-dashed>.<namespace>.pod.cluster.local
  
示例：
  my-service.default.svc.cluster.local → ClusterIP
  10-244-1-5.default.pod.cluster.local → Pod IP
```

#### 7.2 CoreDNS 配置

```bash
# 查看 CoreDNS 配置
kubectl -n kube-system get configmap coredns -o yaml

# 典型 Corefile：
# .:53 {
#     errors
#     health {
#         lameduck 5s
#     }
#     ready
#     kubernetes cluster.local in-addr.arpa ip6.arpa {
#         pods insecure
#         fallthrough in-addr.arpa ip6.arpa
#         ttl 30
#     }
#     prometheus :9153
#     forward . /etc/resolv.conf {
#         max_concurrent 1000
#     }
#     cache 30
#     loop
#     reload
#     loadbalance
# }

# 查看 CoreDNS Pod
kubectl -n kube-system get pods -l k8s-app=kube-dns

# 查看 CoreDNS 日志
kubectl -n kube-system logs -l k8s-app=kube-dns

# 查看 CoreDNS 指标
kubectl -n kube-system port-forward svc/kube-dns 9153:9153
curl http://localhost:9153/metrics
```

#### 7.3 K8s DNS 解析流程

```
Pod 内 DNS 解析流程：

Pod (10.244.1.5) → CoreDNS (10.96.0.10)

1. Pod 查询 my-service.default.svc.cluster.local
   → CoreDNS 返回 ClusterIP

2. Pod 查询 google.com
   → CoreDNS 转发到上游 DNS（/etc/resolv.conf）

3. Pod 查询 10-244-1-5.default.pod.cluster.local
   → CoreDNS 返回 Pod IP

Pod 的 /etc/resolv.conf：
  nameserver 10.96.0.10
  search default.svc.cluster.local svc.cluster.local cluster.local
  ndots:5

ndots:5 说明：
  如果域名中的点数 < 5，会自动追加 search 域名
  my-service → 查询 my-service.default.svc.cluster.local
  www.example.com (3个点 < 5) → 先查询 www.example.com.default.svc.cluster.local
```

---

### 8. dig 命令高级用法

#### 8.1 基本查询

```bash
# 基本 A 记录查询
dig example.com

# 输出解读：
# ;; QUESTION SECTION:
# ;example.com.                 IN      A
#
# ;; ANSWER SECTION:
# example.com.          3600    IN      A       93.184.216.34
#
# ;; Query time: 28 msec
# ;; SERVER: 8.8.8.8#53(8.8.8.8)

# 简洁输出
dig +short example.com
# 93.184.216.34

# 只显示答案
dig +noall +answer example.com

# 查询特定记录类型
dig example.com A
dig example.com AAAA
dig example.com MX
dig example.com NS
dig example.com TXT
dig example.com SOA
dig example.com SRV
dig example.com CAA
dig example.com ANY      # 所有记录（部分服务器禁用）

# 反向查询
dig -x 93.184.216.34
dig +short -x 93.184.216.34
```

#### 8.2 高级查询选项

```bash
# 指定 DNS 服务器
dig @8.8.8.8 example.com
dig @1.1.1.1 example.com
dig @ns1.example.com example.com  # 直接查询权威 DNS

# 追踪完整解析链
dig +trace example.com
# 从根服务器开始，展示完整的迭代查询过程

# 使用 TCP（而非 UDP）
dig +tcp example.com

# 设置端口
dig -p 5353 example.com

# 设置超时和重试
dig +time=5 +tries=3 example.com

# 不使用搜索域
dig +search example.com
dig +ndots=5 example.com

# 显示 DNSSEC 信息
dig +dnssec example.com

# 查询 CHAOS 类（查看 BIND 版本）
dig @8.8.8.8 version.bind chaos TXT

# 批量查询
for domain in google.com github.com example.com; do
    echo -n "$domain → "
    dig +short $domain A
done

# 从文件读取域名批量查询
while read domain; do
    echo -n "$domain → "
    dig +short $domain A
done < domains.txt
```

#### 8.3 +trace 详解

```bash
# +trace 展示完整的迭代查询过程
dig +trace example.com

# 典型输出：
# ; <<>> DiG 9.16.1 <<>> +trace example.com
#
# ; 第一步：查询根服务器
# .                       518400  IN      NS      a.root-servers.net.
# .                       518400  IN      NS      b.root-servers.net.
# ...
#
# ; 第二步：查询 .com TLD
# ;; Received 123 bytes from 198.41.0.4#53(a.root-servers.net) in 10 ms
# com.                    172800  IN      NS      a.gtld-servers.net.
# ...
#
# ; 第三步：查询 example.com 权威 DNS
# ;; Received 234 bytes from 192.5.6.30#53(a.gtld-servers.net) in 20 ms
# example.com.            172800  IN      NS      a.iana-servers.net.
#
# ; 第四步：获取最终结果
# ;; Received 89 bytes from 199.43.135.53#53(a.iana-servers.net) in 30 ms
# example.com.            86400   IN      A       93.184.216.34
```

#### 8.4 DNS 调试技巧

```bash
# 1. 测量 DNS 解析延迟
dig example.com +stats | grep "Query time"

# 多次测量取平均
for i in {1..10}; do
    dig example.com +stats 2>/dev/null | grep "Query time"
done | awk '{sum+=$4; n++} END {print "Average:", sum/n, "ms"}'

# 2. 比较不同 DNS 服务器
echo "=== Google (8.8.8.8) ==="
dig @8.8.8.8 example.com +noall +answer +stats

echo "=== Cloudflare (1.1.1.1) ==="
dig @1.1.1.1 example.com +noall +answer +stats

echo "=== 阿里 (223.5.5.5) ==="
dig @223.5.5.5 example.com +noall +answer +stats

# 3. 检查 CNAME 链
dig +trace www.github.com +noall +answer
# www.github.com.  3600  IN  CNAME  github.com.
# github.com.      60    IN  A      140.82.121.4

# 4. 检查 DNSSEC 签名状态
dig example.com +dnssec +noall +answer

# 5. 查询特定域名服务器
dig @ns1.example.com example.com A +noall +answer

# 6. 检查 SOA 序列号（用于主从同步检查）
dig example.com SOA +short

# 7. 检查区域传输（需要有权限）
dig @ns1.example.com example.com AXFR
```

---

## 💻 实战练习

### 练习 1：基本 DNS 查询

```bash
# 1. 查询各种记录类型
dig example.com A +short
dig example.com AAAA +short
dig example.com MX +noall +answer
dig example.com NS +noall +answer
dig example.com TXT +noall +answer
dig example.com SOA +noall +answer

# 2. 使用不同 DNS 服务器
dig @8.8.8.8 example.com +short
dig @1.1.1.1 example.com +short
dig @223.5.5.5 example.com +short

# 3. 反向解析
dig -x 93.184.216.34 +short

# 4. 测量解析延迟
dig example.com +stats | grep "Query time"
```

### 练习 2：追踪完整解析链

```bash
# 使用 +trace 追踪
dig +trace example.com

# 分析输出：
# 1. 根服务器返回了哪些 TLD 服务器？
# 2. TLD 服务器返回了哪些权威 DNS？
# 3. 最终的 A 记录是什么？
# 4. 每一步的查询时间是多少？

# 练习：追踪你自己的域名
dig +trace your-domain.com

# 追踪并保存到文件
dig +trace example.com > trace_output.txt
```

### 练习 3：DNS 故障排查

```bash
# 场景：某域名无法解析，排查原因

# 1. 检查本地 DNS 配置
cat /etc/resolv.conf

# 2. 测试本地 DNS
dig @$(grep nameserver /etc/resolv.conf | head -1 | awk '{print $2}') example.com

# 3. 测试公共 DNS
dig @8.8.8.8 example.com
dig @1.1.1.1 example.com

# 4. 追踪解析链
dig +trace example.com

# 5. 检查是否有 CNAME 问题
dig example.com +noall +answer

# 6. 检查 DNSSEC
dig example.com +dnssec +noall +answer

# 7. 检查防火墙
iptables -L -n | grep 53
# 确保 UDP/TCP 53 端口未被阻止

# 8. 测试 TCP 模式
dig +tcp example.com
```

---

## 🏥 SRE 实战案例

### 案例 1：DNS 解析到旧 IP — 修改 TTL 缩短影响

**场景：**
电商平台订单服务域名 `orders.example.com` 从旧机房迁移到新机房。

**问题：** 直接修改 DNS 记录后，大量用户仍访问旧 IP。

**正确迁移方案：**

```bash
# Phase 1: 迁移前 24 小时
# 查询当前 TTL
dig orders.example.com +noall +answer
# orders.example.com.  3600  IN  A  203.0.113.10

# 降低 TTL 到 60
# 通过 DNS 管理 API 修改

# Phase 2: 等待旧 TTL 过期（至少 1 小时）
# 多地验证 TTL 已更新
dig @8.8.8.8 orders.example.com +noall +answer
dig @1.1.1.1 orders.example.com +noall +answer
dig @223.5.5.5 orders.example.com +noall +answer

# Phase 3: 执行迁移
# 修改 A 记录到新 IP
# 203.0.113.10 → 203.0.113.50

# Phase 4: 监控切换进度
while true; do
    echo "$(date): $(dig +short orders.example.com @8.8.8.8)"
    sleep 10
done

# Phase 5: 确认完成，恢复 TTL
# 恢复 TTL 到 3600
```

**经验总结：**
- 迁移前至少 24 小时降低 TTL
- 使用多地 dig 验证缓存状态
- 重要服务考虑使用 CNAME + CDN
- 迁移完成后记得恢复 TTL

### 案例 2：DNS 劫持导致流量被导向恶意服务器

**场景：**
用户报告访问公司网站时被重定向到钓鱼网站。

**排查过程：**

```bash
# 1. 多地 DNS 查询对比
echo "=== 本地 DNS ==="
dig @$(grep nameserver /etc/resolv.conf | head -1 | awk '{print $2}') www.company.com +short

echo "=== Google DNS ==="
dig @8.8.8.8 www.company.com +short

echo "=== Cloudflare DNS ==="
dig @1.1.1.1 www.company.com +short

echo "=== 阿里 DNS ==="
dig @223.5.5.5 www.company.com +short

# 发现本地 DNS 返回的 IP 与其他不同

# 2. 检查本地 DNS 配置
cat /etc/resolv.conf
# 发现 DNS 服务器被修改为未知地址

# 3. 检查路由器 DNS 配置
# 登录路由器管理界面，检查 DNS 设置

# 4. 检查 hosts 文件
cat /etc/hosts
# 检查是否有异常条目

# 5. 检查是否有恶意软件
# 运行杀毒软件扫描

# 6. 抓包分析
tcpdump -i eth0 -n port 53
# 观察 DNS 请求和响应
```

**解决方案：**

```bash
# 1. 修复本地 DNS 配置
# /etc/resolv.conf
nameserver 8.8.8.8
nameserver 1.1.1.1

# 2. 配置 DoH/DoT 防止再次被劫持
# /etc/systemd/resolved.conf
[Resolve]
DNS=1.1.1.1#cloudflare-dns.com
DNSOverTLS=yes

# 3. 启用 DNSSEC 验证

# 4. 部署 DNS 监控
#!/bin/bash
# dns_monitor.sh
EXPECTED_IP="203.0.113.10"
CURRENT_IP=$(dig +short www.company.com @8.8.8.8)
if [ "$CURRENT_IP" != "$EXPECTED_IP" ]; then
    echo "ALERT: DNS hijacking detected!"
    # 发送告警
fi
```

### 案例 3：K8s Pod DNS 解析失败排查

**场景：**
K8s 集群中，Pod 无法解析外部域名。

**排查过程：**

```bash
# 1. 检查 Pod 内的 DNS 配置
kubectl exec -it my-pod -- cat /etc/resolv.conf
# nameserver 10.96.0.10
# search default.svc.cluster.local svc.cluster.local cluster.local
# ndots:5

# 2. 在 Pod 内测试 DNS
kubectl exec -it my-pod -- nslookup kubernetes.default
# 应该能解析

kubectl exec -it my-pod -- nslookup google.com
# 如果失败，问题在 CoreDNS 转发

# 3. 检查 CoreDNS 状态
kubectl -n kube-system get pods -l k8s-app=kube-dns
# 确认 CoreDNS Pod 运行正常

# 4. 查看 CoreDNS 日志
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=100
# 检查是否有错误

# 5. 检查 CoreDNS 配置
kubectl -n kube-system get configmap coredns -o yaml
# 检查 forward 配置是否正确

# 6. 测试 CoreDNS 解析
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup google.com 10.96.0.10

# 7. 检查上游 DNS
kubectl -n kube-system exec -it coredns-xxx -- nslookup google.com 8.8.8.8

# 8. 检查网络策略
kubectl get networkpolicy -A
# 确认没有阻止 DNS 流量（UDP 53）

# 9. 检查 CoreDNS 服务
kubectl -n kube-system get svc kube-dns
# 确认服务正常
```

**常见原因和解决方案：**

```bash
# 原因 1：CoreDNS Pod 异常
kubectl -n kube-system delete pod -l k8s-app=kube-dns
# K8s 会自动重建 Pod

# 原因 2：上游 DNS 不可达
# 修改 CoreDNS ConfigMap 的 forward 配置
kubectl -n kube-system edit configmap coredns
# forward . 8.8.8.8 1.1.1.1  # 使用可靠的公共 DNS

# 原因 3：DNS 缓存问题
# 重启 CoreDNS 清除缓存
kubectl -n kube-system rollout restart deployment coredns

# 原因 4：网络策略阻止 DNS
# 检查并修改 NetworkPolicy

# 原因 5：ndots 配置导致大量无效查询
# 优化 Pod 的 dnsConfig
# spec:
#   dnsConfig:
#     options:
#       - name: ndots
#         value: "2"
```

---

## 🎯 面试题精选（10 道）

### 题目 1：DNS 解析过程

**题目**：描述从浏览器输入 URL 到获得 IP 地址的完整 DNS 解析过程。

**答案**：
1. 浏览器缓存 → OS 缓存 → 本地 DNS 服务器
2. 本地 DNS 迭代查询：根服务器 → TLD 服务器 → 权威 DNS
3. 根服务器返回 TLD 服务器地址
4. TLD 服务器返回权威 DNS 地址
5. 权威 DNS 返回最终 A 记录
6. 结果缓存在各层，返回给浏览器

### 题目 2：递归 vs 迭代查询

**题目**：递归查询和迭代查询有什么区别？

**答案**：
- 递归查询：客户端 → DNS 服务器，要求返回最终结果
- 迭代查询：DNS 服务器之间，返回"去找这个服务器问"
- 客户端到本地 DNS 是递归，本地 DNS 到其他 DNS 是迭代

### 题目 3：DNS 缓存投毒

**题目**：什么是 DNS 缓存投毒？如何防护？

**答案**：
攻击者向 DNS 缓存注入伪造记录，使用户被导向恶意网站。防护措施：DNSSEC、随机源端口、随机事务 ID、缩短缓存时间。

### 题目 4：CNAME 和 A 记录

**题目**：CNAME 记录和 A 记录有什么区别？为什么不建议过多使用 CNAME？

**答案**：
- A 记录直接指向 IP，CNAME 指向另一个域名
- CNAME 会增加一次额外查询，增加延迟
- CNAME 不能与其他记录共存
- 过多 CNAME 会增加 DNS 故障风险

### 题目 5：TTL 的作用

**题目**：DNS TTL 有什么作用？如何选择合适的 TTL 值？

**答案**：
TTL 控制缓存时间。稳定服务用大 TTL（86400），即将迁移用小 TTL（300），灾备用更小 TTL（60）。迁移前需提前降低 TTL。

### 题目 6：DNSSEC

**题目**：DNSSEC 是什么？它解决了什么问题？

**答案**：
DNSSEC 通过数字签名验证 DNS 响应的真实性和完整性，防止 DNS 劫持和缓存投毒。使用 RRSIG、DNSKEY、DS 记录建立信任链。

### 题目 7：MX 记录

**题目**：MX 记录的优先级是如何工作的？

**答案**：
MX 记录优先级数字越小越优先。邮件服务器会先尝试连接优先级高的（数字小的），失败后再尝试优先级低的。相同优先级则负载均衡。

### 题目 8：反向解析

**题目**：什么是 DNS 反向解析？有什么用途？

**答案**：
反向解析将 IP 地址解析为域名（PTR 记录）。用途：邮件服务器验证（反垃圾邮件）、日志分析、安全审计。

### 题目 9：CoreDNS

**题目**：K8s 中 CoreDNS 的作用是什么？Pod 如何解析域名？

**答案**：
CoreDNS 是 K8s 默认 DNS，负责解析 Service 名称和外部域名。Pod 的 /etc/resolv.conf 指向 CoreDNS，ndots=5 会导致先搜索 search 域名。

### 题目 10：DNS 负载均衡

**题目**：DNS 如何实现负载均衡？有什么局限性？

**答案**：
DNS 负载均衡通过配置多个 A 记录实现轮询。局限性：不支持健康检查、缓存导致切换慢、无法按权重分配。更好的方案是使用 CDN 或负载均衡器。

---

## 📚 深入阅读

### RFC 文档
- [RFC 1034 - Domain Names: Concepts and Facilities](https://datatracker.ietf.org/doc/html/rfc1034)
- [RFC 1035 - Domain Names: Implementation and Specification](https://datatracker.ietf.org/doc/html/rfc1035)
- [RFC 4033/4034/4035 - DNSSEC](https://datatracker.ietf.org/doc/html/rfc4033)
- [RFC 7858 - DNS over TLS](https://datatracker.ietf.org/doc/html/rfc7858)
- [RFC 8484 - DNS over HTTPS](https://datatracker.ietf.org/doc/html/rfc8484)

### 推荐书籍
- 《DNS 与 BIND》- Cricket Liu
- 《TCP/IP 详解 卷一：协议》- W. Richard Stevens
- 《Kubernetes in Action》- Marko Lukša

### 实用工具
| 工具 | 用途 |
|------|------|
| `dig` | DNS 查询（推荐） |
| `nslookup` | DNS 查询（传统） |
| `host` | 简洁 DNS 查询 |
| `kdig` | 支持 DoT/DoH |
| `delv` | DNSSEC 验证 |
| `dnstop` | DNS 流量分析 |
| `dnsperf` | DNS 性能测试 |

### 公共 DNS 服务
| 服务商 | IPv4 | IPv6 | 特点 |
|--------|------|------|------|
| Google | 8.8.8.8, 8.8.4.4 | 2001:4860:4860::8888 | 全球覆盖 |
| Cloudflare | 1.1.1.1, 1.0.0.1 | 2606:4700:4700::1111 | 隐私保护 |
| 阿里 | 223.5.5.5, 223.6.6.6 | 2400:3200::1 | 国内快速 |
| 腾讯 | 119.29.29.29 | — | 防劫持 |
| 114 | 114.114.114.114 | — | 国内老牌 |

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 DNS 架构（根 → TLD → 权威）
- [ ] 掌握递归查询和迭代查询的区别
- [ ] 能解释所有常见 DNS 记录类型
- [ ] 理解 DNS 完整解析链路
- [ ] 掌握 TTL 的作用和调优策略
- [ ] 了解 DNS 安全威胁和防护措施
- [ ] 理解 DNSSEC 工作原理
- [ ] 了解 CoreDNS 在 K8s 中的作用

### 实操检查点
- [ ] 能使用 dig 查询各种记录类型
- [ ] 能使用 dig +trace 追踪解析链
- [ ] 能使用 dig 测量解析延迟
- [ ] 能配置 DNS 迁移（降 TTL → 改记录 → 监控）
- [ ] 能排查 DNS 解析故障
- [ ] 能排查 K8s Pod DNS 问题
- [ ] 能配置 DoH/DoT

---

> 💡 **SRE 思考题**：如果你的线上服务通过 CDN 访问，CDN 的 CNAME 指向了某个域名，当 CDN 切换节点时，你的 DNS TTL 应该如何设置才能保证用户体验和切换速度的平衡？
>
> **提示**：CDN 通常有较短的 TTL（60-300 秒），但你的域名指向 CDN 的 CNAME 可以有较长的 TTL。关键是 CDN 内部的切换对用户是透明的。
