# Day 11: 系统监控命令 — uptime/free/df/vmstat/sar/iostat

> 📅 日期：2026-04-25  
> 📖 学习主题：系统监控命令 — uptime/free/df/vmstat/sar/iostat  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 11 的学习后，你应该掌握：
- 理解 系统监控命令 — uptime/free/df/vmstat/sar/iostat 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. 系统负载监控

#### 1.1 uptime 与 Load Average

Load Average 表示 1/5/15 分钟内的平均负载（运行队列中的进程数）。

**SRE 经验法则**：load < CPU 核数 = 健康；load > CPU 核数 = 过载。

```bash
$ uptime
 14:30:25 up 30 days, 2:15,  load average: 0.50, 1.20, 0.80
```

**SRE 实战排查**：
```bash
# 生产告警：load 15.2（4 核机器）→ 严重过载！

# 定位高 CPU 进程
ps aux --sort=-%cpu | head -10

# 查看进程状态分布
ps aux | awk '{print $8}' | sort | uniq -c
# D（不可中断睡眠）太多 = IO 等待
# R（运行）太多 = CPU 瓶颈

# 查看 IO 等待
vmstat 1 5
# wa 高 = 磁盘瓶颈
```

#### 1.2 free — 内存监控

**关键**：看 `available` 而非 `free`！Linux 会用空闲内存做缓存。

```bash
$ free -h
              total   used   free   buff/cache   available
Mem:           16Gi   8.2Gi  1.1Gi     6.7Gi       7.3Gi
```

```bash
# 真正的内存问题：available 很低 + swap 持续增加 = OOM 风险
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
```

#### 1.3 df/du — 磁盘

```bash
df -h                    # 磁盘使用率
df -i                    # inode 使用率
du -sh /* 2>/dev/null | sort -rh | head -10  # 大目录
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null  # 大文件
```

#### 1.4 vmstat — 综合性能

```bash
vmstat 1 5
# r > CPU 核数 = CPU 瓶颈
# b > 0 = 磁盘瓶颈
# si/so > 0 = 内存不足
# wa 高 = IO 等待
```

#### 1.5 sar — 历史数据回溯

```bash
# 启用 sysstat
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat

sar -u    # CPU 历史
sar -r    # 内存历史
sar -d    # 磁盘 IO 历史
sar -n DEV  # 网络历史
```

---

### 2. SRE 实战：一键健康检查脚本

```bash
#!/bin/bash
echo "=== 健康检查 $(date) ==="
echo "负载: $(uptime | awk -F'load average:' '{print $2}')"
echo "内存:"; free -h | grep Mem
echo "磁盘:"; df -h / | tail -1
echo "Top CPU:"; ps aux --sort=-%cpu | head -4
echo "Top MEM:"; ps aux --sort=-%mem | head -4
echo "IO 等待:"; vmstat 1 1 | tail -1
echo "错误日志:"; journalctl -p err --since "5 min ago" --no-pager | tail -3
```

---

### 3. 常见问题

| 问题 | 排查思路 |
|------|---------|
| Load 高但 CPU 使用率低 | 检查 vmstat 的 wa，可能是磁盘瓶颈 |
| 内存告警但 available 充足 | 正常！Linux 用空闲内存做缓存 |
| Swap 持续增加 | 内存不足，排查内存泄漏 |
| 磁盘使用率持续增长 | 检查日志轮转配置、临时文件 |


---

## 💻 实战练习

### 练习 1：运维实时监控脚本

```bash
#!/bin/bash
# ops_dashboard.sh
while true; do
    clear
    echo "=== SRE OPS DASHBOARD $(date '+%H:%M:%S') ==="
    load=$(cat /proc/loadavg | awk '{print $1", "$2", "$3}')
    cpu_idle=$(vmstat 1 2 | tail -1 | awk '{print $15}')
    echo "CPU Load: $load | Idle: ${cpu_idle}%"
    echo "Memory: $(free -h | grep Mem)"
    echo "Disk:"
    df -h / /data 2>/dev/null | tail -n+2 | \
        awk '{printf "  %-15s %s/%s (%s)\n", $6, $3, $2, $5}'
    echo "Top Processes:"
    ps aux --sort=-%cpu | head -4 | tail -3 | \
        awk '{printf "  PID:%-8s CPU:%5s%% MEM:%5s%% %s\n", $2, $3, $4, $11}'
    echo "Services:"
    for svc in nginx mysql docker ssh; do
        status=$(systemctl is-active $svc 2>/dev/null)
        [ "$status" = "active" ] && echo "  [OK] $svc" || echo "  [!!] $svc"
    done
    sleep 5
done
```

### 练习 2：历史数据回溯

```bash
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
systemctl restart sysstat
sar -u          # CPU 历史
sar -r          # 内存历史
sar -d -p       # 磁盘 IO
sar -u -s 14:00 -e 15:00  # 特定时间段
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

*由 SRE 学习计划自动生成 | 2026-04-25 10:57:57*  
*Generated by Hermes Agent with review*
