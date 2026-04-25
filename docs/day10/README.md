# Day 10: systemd 服务管理 — systemctl/单元文件

> 📅 日期：2026-04-25  
> 📖 学习主题：systemd 服务管理 — systemctl/单元文件  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 10 的学习后，你应该掌握：
- 理解 systemd 服务管理 — systemctl/单元文件 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. 学习主题概述

systemd 服务管理 — systemctl/单元文件

#### 1.1 什么是 systemd

systemd 是 Linux 系统中主要的系统和服务管理器，取代了传统的 SysV init 系统。它采用并行启动机制，大大加快了系统启动速度。systemd 的核心概念是**单元（Unit）**，包括服务单元、挂载单元、套接字单元等。

#### 1.2 systemd 架构

| 组件 | 说明 |
|------|------|
| systemd | 主进程（PID 1），管理系统生命周期 |
| systemctl | 命令行管理工具 |
| systemd-analyze | 分析启动性能 |
| journalctl | 查看日志 |
| systemd-run | 运行临时或瞬态单元 |

---

### 2. systemctl 基础命令

#### 2.1 服务管理

```bash
# 启动服务
sudo systemctl start nginx

# 停止服务
sudo systemctl stop nginx

# 重启服务
sudo systemctl restart nginx

# 重新加载配置（不中断连接）
sudo systemctl reload nginx

# 查看服务状态
sudo systemctl status nginx
```

#### 2.2 开机自启管理

```bash
# 启用开机自启
sudo systemctl enable nginx

# 禁用开机自启
sudo systemctl disable nginx

# 检查是否启用
systemctl is-enabled nginx

# 重新加载 systemd 配置
sudo systemctl daemon-reload
```

#### 2.3 查看系统状态

```bash
# 查看所有运行中的单元
systemctl list-units --type=service --state=running

# 查看失败的单元
systemctl --failed --type=service

# 查看所有已加载的单元
systemctl list-unit-files
```

---

### 3. systemd 单元文件

#### 3.1 单元文件位置

| 路径 | 说明 |
|------|------|
| `/etc/systemd/system/` | 系统管理员创建的服务 |
| `/run/systemd/system/` | 运行时生成的服务 |
| `/usr/lib/systemd/system/` | 软件包安装的服务 |

#### 3.2 服务单元文件示例

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application Server
Documentation=https://myapp.example.com
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/bin/python3 /opt/myapp/server.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 3.3 常用 [Service] 类型

| Type | 说明 | 适用场景 |
|------|------|---------|
| simple | 主进程即为服务进程 | 大多数服务 |
| forking | 主进程 fork 子进程 | 传统守护进程 |
| oneshot | 执行一次就退出 | 一次性任务 |
| notify | 进程启动后发送就绪通知 | 复杂服务 |
| dbus | 依赖 D-Bus 信号 | 需要 D-Bus 的服务 |

#### 3.4 常用 [Unit] 指令

| 指令 | 说明 |
|------|------|
| Description | 单元描述 |
| Documentation | 文档链接 |
| After | 在哪些单元之后启动 |
| Before | 在哪些单元之前启动 |
| Wants | 弱依赖（启动此单元时也启动所列单元） |
| Requires | 强依赖（所列单元失败则此单元也失败） |
| WantedBy | 哪个 target 包含此单元 |

---

### 4. systemd 常用 target

```bash
# 查看当前 target
systemctl get-default

# 切换 target（临时）
sudo systemctl isolate multi-user.target

# 设置默认 target
sudo systemctl set-default multi-user.target

# 列出所有 target
systemctl list-units --type=target --all
```

| Target | 说明 | 对应 SysV 运行级别 |
|--------|------|-------------------|
| poweroff.target | 系统关机 | runlevel 0 |
| rescue.target | 救援模式 | runlevel 1 |
| multi-user.target | 多用户（无图形） | runlevel 3 |
| graphical.target | 多用户（带图形） | runlevel 5 |
| reboot.target | 重启 | runlevel 6 |

---

### 5. 日志管理（journalctl）

```bash
# 查看所有日志
sudo journalctl

# 查看当前启动日志
journalctl -b

# 查看上次启动日志
journalctl -b -1

# 实时跟踪日志
journalctl -f

# 查看特定服务的日志
journalctl -u nginx

# 按时间范围过滤
journalctl --since "10 minutes ago"
journalctl --since "2024-01-01 00:00:00" --until "2024-01-01 12:00:00"

# 查看错误级别日志
journalctl -p err

# 日志占用空间
journalctl --disk-usage

# 清理旧日志
sudo journalctl --vacuum-size=500M
```

---

### 6. 实战练习

#### 练习 1：创建一个简单的 systemd 服务

```bash
# 1. 创建 Python 测试脚本
sudo tee /opt/hello.py << 'EOF'
#!/usr/bin/env python3
import time
while True:
    print("Hello from systemd service!")
    time.sleep(30)
EOF
sudo chmod +x /opt/hello.py

# 2. 创建服务单元文件
sudo tee /etc/systemd/system/hello.service << 'EOF'
[Unit]
Description=Hello World Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/hello.py
Restart=on-failure
User=www-data

[Install]
WantedBy=multi-user.target
EOF

# 3. 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable hello
sudo systemctl start hello

# 4. 检查状态
systemctl status hello
journalctl -u hello -f
```

#### 练习 2：分析系统启动性能

```bash
# 查看启动时间分析
systemd-analyze

# 查看各服务启动耗时
systemd-analyze blame

# 查看关键链（最耗时路径）
systemd-analyze critical-chain

# 保存启动报告
systemd-analyze plot > startup.svg
```

#### 练习 3：服务管理实战

```bash
# 1. 查看 nginx 服务状态
systemctl status nginx

# 2. 查看 nginx 的依赖关系
systemctl list-dependencies nginx

# 3. 强制重启服务（模拟故障恢复）
sudo systemctl try-restart nginx

# 4. 查看服务是否配置为开机自启
systemctl is-enabled nginx
```

---

### 7. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 服务启动失败 | `journalctl -u <服务名>` 查看日志 |
| 服务一直重启 | 检查 `Restart=on-failure` 配置，增加 `RestartSec` |
| 开机未自启 | `systemctl enable <服务>` 并 `daemon-reload` |
| 端口被占用 | `ss -tlnp` 或 `lsof -i :端口` 查找冲突进程 |
| 服务卡住无法停止 | `sudo systemctl kill -s KILL <服务名>` |

---

### 8. 扩展阅读

- `man systemctl` — systemctl 完整手册
- `man systemd.unit` — 单元文件格式
- `man journalctl` — 日志查看器手册
- `man systemd.service` — 服务单元配置
- systemd 官方文档：https://www.freedesktop.org/wiki/Software/systemd/


---

## 💻 实战练习

### 练习 1：编写企业级 systemd 服务

```bash
#!/bin/bash
# 创建应用
mkdir -p /opt/myapp/{logs,config}
useradd -r -s /sbin/nologin myapp

# 创建服务单元
cat > /etc/systemd/system/myapp.service << 'EOF'
[Unit]
Description=My Application Server
After=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/app.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StartLimitInterval=300
StartLimitBurst=5

# 安全加固
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now myapp
systemctl status myapp
```

### 练习 2：启动性能分析

```bash
systemd-analyze
systemd-analyze blame | head -20
systemd-analyze critical-chain
systemd-analyze plot > /tmp/startup.svg
```


---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-04-25 10:58:13*  
*Generated by Hermes Agent with review*
