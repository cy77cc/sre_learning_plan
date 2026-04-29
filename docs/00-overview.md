# SRE 工程师每日学习计划

> 📅 总周期：26 周（约 6.5 个月）  
> ⏰ 每日学习时间：2-3 小时  
> 🎯 目标：成为入门级 SRE 工程师，具备 AI/LLM Ops 能力  
> 📝 版本：v2.0 — 经 Review 补充（2026-04-29）

---

## 📋 学习阶段总览

| 阶段 | 周数 | 主题 |
|------|------|------|
| 第一阶段 | 1-4 周 | Linux 基础与 Shell 脚本 |
| 第二阶段 | 5-6 周 | 计算机网络 |
| 第三阶段 | 7-8 周 | Python 编程（SRE 导向）|
| 第四阶段 | 9-10 周 | Go 语言（SRE 导向）|
| 第五阶段 | 11 周 | 数据库运维（新增）|
| 第六阶段 | 12-13 周 | 容器化 Docker |
| 第七阶段 | 14-15 周 | Kubernetes |
| 第八阶段 | 16 周 | 云计算 AWS + IaC |
| 第九阶段 | 17-18 周 | 可观测性 |
| 第十阶段 | 19-20 周 | CI/CD 与 GitOps |
| 第十一阶段 | 21-22 周 | LLM Ops 大模型运维（新增）|
| 第十二阶段 | 23 周 | SRE 核心实战 |
| 第十三阶段 | 24 周 | Capstone 综合项目（新增）|
| 第十四阶段 | 25-26 周 | 面试准备与职业规划 |

---

## 📋 学习阶段总览

| 阶段 | 周数 | 主题 |
|------|------|------|
| 第一阶段 | 1-4 周 | Linux 基础与 Shell 脚本 |
| 第二阶段 | 5-6 周 | 计算机网络 |
| 第三阶段 | 7-10 周 | Python / Go 编程 |
| 第四阶段 | 11-14 周 | 容器化 Docker + Kubernetes |
| 第五阶段 | 15-18 周 | 云计算 AWS + IaC |
| 第六阶段 | 19-20 周 | 可观测性 |
| 第七阶段 | 21-22 周 | CI/CD 与自动化 |
| 第八阶段 | 23-24 周 | SRE 实战与面试准备 |

---

# 📖 第一阶段：Linux 基础与 Shell 脚本（第 1-4 周）

## Week 1：Linux 入门

### Day 1
- [ ] **学习内容**：Linux 简介与虚拟机安装
- [ ] 了解 Linux 历史、核心哲学（一切皆文件、小而专一工具、开源共享）
- [ ] 对比主流发行版：Ubuntu/Debian/Rocky/Alpine/Arch 的区别与适用场景
- [ ] 安装 VirtualBox 或配置 WSL2，创建第一个 Linux 虚拟机
- [ ] **SRE 实战案例**：某团队用 Ubuntu 16.04 跑生产服务 → EOL 后无法修复安全漏洞，导致被入侵
- [ ] **练习**：完成 Ubuntu 22.04 安装，执行系统更新，安装基础工具（curl, vim, htop, git）
- [ ] **扩展**：配置 SSH 密钥登录，设置防火墙基本规则

### Day 2
- [ ] **学习内容**：文件系统与目录结构 — FHS 标准详解
- [ ] 掌握 FHS（Filesystem Hierarchy Standard）核心目录：`/etc` `/var` `/usr` `/home` `/proc` `/dev`
- [ ] 理解 `/bin` vs `/usr/bin` vs `/usr/local/bin` 的区别（Ubuntu 16.04+ 合并为 usr-merge）
- [ ] 学习虚拟文件系统 `/proc`（进程信息）和 `/sys`（硬件信息）
- [ ] **SRE 实战案例**：工程师找 Nginx 日志时去 `/opt/nginx/logs`（不存在），实际在 `/var/log/nginx/`，延误故障处理 10 分钟
- [ ] **练习**：用 `tree -L 2 /` 查看目录结构，用 `ls -la` 分析根目录每个目录的用途
- [ ] **扩展**：查看 `/proc/cpuinfo`、`/proc/meminfo`、`/proc/loadavg` 获取系统信息

### Day 3
- [ ] **学习内容**：文件操作命令 — cp/mv/rm/touch/mkdir/find
- [ ] 掌握文件创建、复制、移动、删除操作，理解 `rm -rf` 的危险性
- [ ] 学习 `find` 命令：按名称、类型、时间、大小、权限查找文件
- [ ] 掌握文件查看命令：cat/less/head/tail/wc，特别是 `tail -f` 实时跟踪日志
- [ ] 理解硬链接与软链接的区别和使用场景
- [ ] **SRE 实战案例**：`rm -rf /tmp/* ~` 多了一个空格 → 删除了整个 home 目录
- [ ] **练习**：创建 30 天模拟日志文件，用 find 查找 7 天内修改过的文件，用 tail -f 监控日志
- [ ] **扩展**：用 find + xargs 打包 7 天前的旧日志进行归档

### Day 4
- [ ] **学习内容**：文本处理三剑客 — grep/sed/awk 与正则表达式
- [ ] **grep**：文本搜索，-i/-n/-c/-v/-r/-A/-B/-E 等选项，提取日志中的关键信息
- [ ] **sed**：流编辑器，替换/删除/插入文本，批量修改配置文件
- [ ] **awk**：文本分析工具，字段提取、统计计算、生成报表
- [ ] 掌握基础正则表达式：`.` `^` `$` `*` `+` `?` `[abc]` `{n,m}` 等
- [ ] **SRE 实战案例**：用 awk 分析 Nginx 访问日志 → 统计 QPS、状态码分布、Top 20 IP、5xx 错误率
- [ ] **练习**：用 grep 查找 auth.log 中的登录失败记录，用 awk 统计每个 IP 访问次数
- [ ] **扩展**：编写 Nginx 日志日报脚本（请求总数、状态码分布、Top URL、5xx 错误详情）

### Day 5
- [ ] **学习内容**：文件权限管理 — chmod/chown/chgrp 与数字权限
- [ ] 理解权限的三层结构：所有者/用户组/其他用户（rwx = 4/2/1）
- [ ] 掌握常用权限模式：755（目录/脚本）、644（配置文件）、600（私钥）
- [ ] 学习特殊权限：SUID（4000）、SGID（2000）、Sticky Bit（1000）
- [ ] 掌握 ACL 精细权限控制：setfacl/getfacl
- [ ] **SRE 实战案例**：Nginx 403 Forbidden → 目录权限 640 导致 www-data 无法进入目录，需要 755
- [ ] **练习**：创建共享目录 /srv/shared，设置 SGID 使新文件自动继承用户组
- [ ] **扩展**：排查 SSH 密钥登录失败（权限必须是 600/700），用 namei -l 追踪完整路径权限

### Day 6
- [ ] **学习内容**：用户与用户组管理 — useradd/usermod/userdel/sudo
- [ ] 理解用户类型：root(UID 0)、系统用户(1-999)、普通用户(1000+)
- [ ] 掌握关键文件：/etc/passwd、/etc/shadow、/etc/group、/etc/sudoers
- [ ] 学习用户创建/修改/删除的完整流程及安全检查
- [ ] 掌握 sudo 权限配置：visudo 安全编辑、最小权限原则、NOPASSWD 场景
- [ ] 密码策略：chage 设置过期时间，/etc/login.defs 系统默认策略
- [ ] **SRE 实战案例**：员工离职后未锁定账户 → 前员工用旧 SSH 密钥重新登录生产服务器
- [ ] **练习**：创建 SRE 用户并配置 SSH 密钥登录、sudo 权限（仅允许管理 nginx/docker）
- [ ] **扩展**：编写"新员工入职"和"员工离职清理"自动化脚本

### Day 7
- [ ] **复习与实战**：第一周综合练习
- [ ] **场景 1**：新购一台云服务器，完成从零到可用的全部配置
  - 创建用户、配置 SSH 密钥、设置 sudo 权限、安装基础工具
  - 配置防火墙（ufw）、设置时区、配置 Vim/Git
- [ ] **场景 2**：排查一台服务器的权限问题
  - 某 Web 应用返回 403，用 namei/getfacl 追踪权限链
  - 找出 777 权限文件并修复
- [ ] **场景 3**：日志分析挑战
  - 分析 auth.log 找出暴力破解的 IP（Failed password 最多的前 10 个）
  - 用 grep + awk 统计 Nginx 日志中的 5xx 错误率
- [ ] **实战项目**：编写服务器初始化脚本，支持 Ubuntu 和 Rocky Linux
- [ ] **自我评估**：能否不查阅文档完成常用文件操作？

## Week 2：进程管理与系统监控

### Day 8
- [ ] **学习内容**：进程管理基础 — ps/top/htop/pstree
- [ ] 理解进程概念：PID、PPID、进程状态（R/S/D/Z/T）
- [ ] 掌握 ps 命令：ps aux、ps -ef、按 CPU/内存排序
- [ ] 学习 top/htop 实时进程监控，理解 load average 含义
- [ ] 理解僵尸进程（Zombie）和孤儿进程的成因与处理方式
- [ ] **SRE 实战案例**：某服务 OOM Kill → dmesg 发现 Out of memory，通过 ps 按内存排序定位内存泄漏进程
- [ ] **练习**：用 ps aux --sort=-%mem 查找占用内存最多的进程，用 pstree 查看进程父子关系
- [ ] **扩展**：阅读 /proc/[PID]/ 目录，理解进程的内存映射、打开文件、环境变量

### Day 9
- [ ] **学习内容**：进程控制 — kill/killall/pkill/信号机制
- [ ] 理解 Linux 信号：SIGTERM(15) 优雅终止、SIGKILL(9) 强制终止、SIGHUP(1) 重载配置
- [ ] 掌握 kill/killall/pkill 的区别和使用场景
- [ ] 学习进程优先级：nice/renice 调整进程优先级
- [ ] 后台作业管理：&、jobs、fg、bg、Ctrl+Z
- [ ] **SRE 实战案例**：服务升级时应该用 kill -15（优雅关闭，完成当前请求）而非 kill -9（强制中断，可能丢失数据）
- [ ] **练习**：启动后台进程，用 kill -15 优雅终止，观察日志中的 shutdown 消息
- [ ] **扩展**：用 strace 跟踪进程系统调用，定位进程挂起原因

### Day 10
- [ ] **学习内容**：systemd 服务管理 — systemctl/单元文件
- [ ] 理解 systemd 架构：PID 1 进程、单元（Unit）、依赖关系
- [ ] 掌握 systemctl 操作：start/stop/restart/reload/enable/disable/status
- [ ] 学习编写 systemd 单元文件：[Unit]、[Service]、[Install] 段
- [ ] 理解 Service 类型：simple/forking/oneshot/notify
- [ ] 掌握 journalctl 日志管理：-f 跟踪、-u 指定服务、--since 时间过滤
- [ ] **SRE 实战案例**：服务启动失败 → journalctl -u nginx 查看日志，发现端口被占用 → ss -tlnp 定位冲突进程
- [ ] **练习**：编写一个 Python 脚本作为 systemd 服务，配置自动重启（Restart=on-failure）
- [ ] **扩展**：用 systemd-analyze blame 分析启动耗时最长的服务，优化启动速度

### Day 11
- [ ] **学习内容**：系统监控命令 — uptime/free/df/vmstat/sar/iostat
- [ ] **uptime/load average**：1/5/15 分钟负载，CPU 核数与负载的关系（负载 > 核数 = 过载）
- [ ] **free**：内存使用情况，理解 buff/cache 与 available 的区别
- [ ] **df/du**：磁盘空间分析，找出大文件和大目录
- [ ] **vmstat**：虚拟内存统计，进程/内存/IO/CPU 综合信息
- [ ] **sar**：系统活动报告（sysstat 包），历史性能数据回溯
- [ ] **SRE 实战案例**：服务器响应变慢 → uptime 发现 load 飙升 → vmstat 发现 iowait 过高 → df 发现 /var/log 满了
- [ ] **练习**：用 free -h 分析内存，用 du -sh /* 排查磁盘使用，用 sar -u 1 5 实时查看 CPU
- [ ] **扩展**：配置 sysstat 采集历史数据（/etc/default/sysstat ENABLED=true），用 sar -f 查看历史记录

### Day 12
- [ ] **学习内容**：磁盘管理 — fdisk/mkfs/mount/LVM
- [ ] 理解磁盘设备命名：/dev/sda、/dev/nvme0n1、/dev/vda（云盘）
- [ ] 掌握分区工具：fdisk（MBR）、parted（GPT）
- [ ] 学习文件系统格式化：mkfs.ext4、mkfs.xfs
- [ ] 掌握挂载管理：mount/umount、/etc/fstab 自动挂载
- [ ] 了解 LVM（逻辑卷管理）：pvcreate/vgcreate/lvcreate，在线扩容
- [ ] **SRE 实战案例**：生产服务器磁盘报警 → fdisk -l 发现新盘未挂载 → mkfs.ext4 格式化 → 写入 fstab → mount -a
- [ ] **练习**：创建一个虚拟磁盘（dd if=/dev/zero of=/tmp/disk.img bs=1M count=100），分区、格式化、挂载
- [ ] **扩展**：配置 LVM，演示在线扩容（lvextend + resize2fs）

### Day 13
- [ ] **学习内容**：日志管理 — journalctl/rsyslog/logrotate/日志分析
- [ ] 理解 Linux 日志体系：/var/log 目录结构、syslog 协议
- [ ] 掌握 journalctl 高级用法：-p 优先级过滤、-f 实时跟踪、--disk-usage 查看占用
- [ ] 学习 logrotate 日志轮转：daily/weekly/monthly、compress、rotate N、size
- [ ] 掌握常见日志分析：/var/log/syslog、auth.log、kern.log、dmesg
- [ ] **SRE 实战案例**：磁盘告警 → 发现 /var/log/nginx/access.log 高达 50GB → 配置 logrotate 按天轮转、压缩保留 30 天 → 磁盘恢复正常
- [ ] **练习**：编写 nginx logrotate 配置（每天轮转、保留 30 天、压缩、轮转后 reload nginx）
- [ ] **扩展**：用 tail -f /var/log/auth.log | grep "Failed password" 实时监控暴力破解攻击

### Day 14
- [ ] **复习与实战**：第二周综合实战 — 搭建 LAMP 环境
- [ ] **任务**：从零搭建 Apache + MySQL + PHP 环境
  - 用 apt 安装 apache2、mysql-server、php、libapache2-mod-php
  - 配置 Apache 虚拟主机（/etc/apache2/sites-available/）
  - 创建 MySQL 数据库和用户，编写 PHP 测试页面
  - 编写 systemd 服务文件管理应用
  - 配置日志轮转和监控
- [ ] **要求**：
  - 所有服务设置开机自启（systemctl enable）
  - 配置防火墙（ufw allow 80/tcp）
  - 创建应用专用用户（非 root 运行）
  - 编写部署脚本（一键安装 + 配置）
- [ ] **扩展挑战**：
  - 配置 HTTPS（Let's Encrypt 或自签名证书）
  - 用 curl 编写健康检查脚本
  - 配置 Apache 访问日志的自动分析
- [ ] **自我评估**：能否独立完成从 0 到部署一个 Web 应用？

## Week 3：Shell 脚本编程（上）

### Day 15
- [ ] **学习内容**：Shell 脚本基础 — 变量/环境变量/引号/#! 解释器
- [ ] 理解 shebang：#!/bin/bash vs #!/bin/sh vs #!/usr/bin/env bash
- [ ] 变量定义与引用：VAR=value、${VAR}、${VAR:-default}、${VAR:=default}
- [ ] 环境变量：export、env、set、printenv、.bashrc/.profile 加载顺序
- [ ] 引号区别：单引号（不展开）、双引号（展开变量）、反引号/$( ) 命令替换
- [ ] 特殊变量：$0 $1 $2 $# $@ $* $? $$ $!
- [ ] **SRE 实战案例**：脚本中 `rm -rf $DIR/` 当 $DIR 为空时 → 变成 `rm -rf /` → 应该用 `rm -rf "${DIR:?}/"`
- [ ] **练习**：编写第一个脚本（打印系统信息：主机名、IP、内存、磁盘使用率）
- [ ] **扩展**：编写一个接受参数的脚本，支持 -h 显示帮助信息

### Day 16
- [ ] **学习内容**：Shell 条件判断 — if/elif/else/test 运算符
- [ ] 文件测试：-f（文件）、-d（目录）、-e（存在）、-s（非空）、-r（可读）、-w（可写）、-x（可执行）
- [ ] 字符串比较：= != -z（空串）-n（非空）
- [ ] 数值比较：-eq -ne -gt -ge -lt -le
- [ ] 逻辑运算符：&&（与）||（或）!（非）-a（与）-o（或）
- [ ] [[ ]] vs [ ]：[[ ]] 支持 && || 正则匹配，推荐使用
- [ ] **SRE 实战案例**：部署脚本中检查"目录是否存在"和"服务是否运行"，不满足条件时自动退出
- [ ] **练习**：编写服务健康检查脚本（检查进程是否存在、端口是否监听、磁盘是否充足）
- [ ] **扩展**：编写安装前环境检查脚本（检查 OS 版本、内核版本、依赖包是否安装）

### Day 17
- [ ] **学习内容**：Shell 循环结构 — for/while/until
- [ ] for 循环：for var in list、for((i=0; i<n; i++))、for file in *.log
- [ ] while 循环：while condition、while read line（逐行读取文件）
- [ ] until 循环：until condition（条件为假时执行）
- [ ] 循环控制：break、continue、shift
- [ ] **SRE 实战案例**：批量创建 100 个用户、批量检查 50 台服务器磁盘使用率、逐个处理日志文件
- [ ] **练习**：编写批量创建用户脚本（从 users.txt 读取用户名，创建用户并设置初始密码）
- [ ] **扩展**：编写批量服务器巡检脚本（SSH 登录每台服务器，收集 CPU/内存/磁盘信息）

### Day 18
- [ ] **学习内容**：Shell 函数 — 函数定义/参数传递/返回值/作用域
- [ ] 函数定义：function name() { } 和 name() { }
- [ ] 参数传递：$1 $2 ${@} ${#}（参数个数）
- [ ] 返回值：return（0-255），与 echo 输出的区别
- [ ] 变量作用域：local 关键字，全局变量与局部变量
- [ ] 函数库模式：将常用函数放在 functions.sh 中，用 source 引入
- [ ] **SRE 实战案例**：将"日志记录"、"错误处理"、"服务检查"封装为函数，在多个脚本中复用
- [ ] **练习**：将 Day 17 的批量用户脚本改写为函数版本（create_user、check_user、delete_user）
- [ ] **扩展**：编写一个函数库（log_info/log_error/log_warn），支持日志级别和颜色输出

### Day 19
- [ ] **学习内容**：Case 语句与 select 菜单
- [ ] case ... esac：多分支条件匹配，支持通配符 *
- [ ] select 菜单：生成交互式数字菜单，配合 PS3 提示符
- [ ] 实战模式：服务管理菜单（启动/停止/重启/状态/退出）
- [ ] 菜单脚本最佳实践：输入验证、错误处理、退出机制
- [ ] **SRE 实战案例**：编写运维工具菜单（一键查看服务状态/日志/磁盘/内存/网络）
- [ ] **练习**：编写服务管理菜单脚本（支持 nginx/mysql/docker 的 start/stop/restart/status）
- [ ] **扩展**：给菜单添加颜色、日志记录功能，记录每次操作

### Day 20
- [ ] **学习内容**：数组操作 — 索引数组/关联数组/数组遍历
- [ ] 索引数组：arr=(a b c)、${arr[0]}、${arr[@]}、${#arr[@]}、${arr[@]:start:len}
- [ ] 关联数组（Bash 4.0+）：declare -A、arr[key]=value、遍历 keys
- [ ] 数组排序：sort 命令配合数组操作
- [ ] **SRE 实战案例**：用关联数组存储服务器监控指标（server_name → IP → 状态），批量巡检后生成报告
- [ ] **练习**：编写日志分析脚本，用数组统计每个 HTTP 状态码的出现次数
- [ ] **扩展**：编写多服务器批量管理脚本，用数组存储服务器列表，并行检查状态

### Day 21
- [ ] **学习内容**：字符串处理与正则 — sed/awk 进阶
- [ ] 字符串操作：${#var}（长度）、${var:offset:length}（截取）、${var#pattern}（前缀删除）
- [ ] 字符串替换：${var/pattern/replacement}、${var//pattern/replacement}（全部替换）
- [ ] 大小写转换：${var^^}（大写）、${var,,}（小写）
- [ ] sed 进阶：多行处理、地址范围、正则捕获组
- [ ] awk 进阶：数组、函数、BEGIN/END、格式化输出
- [ ] **SRE 实战案例**：从 Nginx 日志中提取时间戳并转换为可读格式，生成日报
- [ ] **练习**：编写字符串处理脚本，从配置文件中提取并替换特定值
- [ ] **扩展**：编写配置文件管理脚本，支持备份、修改、回滚操作

## Week 4：Shell 脚本编程（下）+ 实战项目

### Day 22
- [ ] **学习内容**：脚本调试与信号处理 — set/trap/debug
- [ ] 调试选项：set -x（打印执行命令）、set -e（遇错退出）、set -u（未定义变量报错）
- [ ] 安全模式：set -euo pipefail（推荐的脚本开头）
- [ ] trap 命令：捕捉信号（EXIT/INT/TERM/ERR），执行清理操作
- [ ] 调试技巧：bash -x script.sh、PS4 设置、函数调用追踪
- [ ] **SRE 实战案例**：部署脚本中加入 trap 'cleanup' EXIT，确保失败时回滚、清理临时文件
- [ ] **练习**：编写带错误处理的脚本（检查前置条件、失败时清理、记录详细日志）
- [ ] **扩展**：用 set -x 调试一个复杂脚本，追踪变量变化和命令执行流程

### Day 23
- [ ] **学习内容**：expect 自动化交互 — SSH 自动登录/批量配置
- [ ] expect 基础：spawn、expect、send、interact
- [ ] expect 模式匹配：精确匹配、正则匹配、超时处理
- [ ] autoexpect：自动录制 expect 脚本
- [ ] **SRE 实战场景**：批量服务器初始化需要交互式确认（首次 SSH 连接、密码修改、软件安装确认）
- [ ] **练习**：编写 SSH 自动登录脚本（首次连接自动接受密钥、输入密码）
- [ ] **扩展**：编写批量密码修改脚本，自动处理 passwd 交互提示

### Day 24
- [ ] **实战项目**：服务器初始化脚本
- [ ] **需求**：编写一个完整的服务器初始化脚本（server_init.sh），支持：
  - 参数检查（-h 帮助、--user 用户名、--ssh-key 公钥路径）
  - 系统更新（apt update && apt upgrade）
  - 创建指定用户，配置 SSH 密钥登录
  - 安装基础工具包（curl, vim, htop, git, net-tools, ufw）
  - 配置防火墙（允许 SSH、HTTP、HTTPS）
  - 配置 NTP 时间同步
  - 配置 sysstat 性能监控
  - 生成初始化报告（所有配置项的当前状态）
- [ ] **要求**：使用 set -euo pipefail、函数封装、日志记录、错误处理
- [ ] **验收标准**：在干净的 Ubuntu 22.04 上运行一次即可得到可用的生产环境

### Day 25
- [ ] **实战项目**：日志监控告警脚本
- [ ] **需求**：编写一个实时日志监控脚本（log_monitor.sh），支持：
  - 监控指定日志文件（/var/log/nginx/error.log 或 /var/log/syslog）
  - 定义告警规则（关键字：ERROR、CRITICAL、OutOfMemory、segfault）
  - 统计告警频率（同一错误 N 秒内出现超过 M 次触发告警）
  - 告警通知（支持钉钉/企业微信 Webhook、邮件、本地日志）
  - 支持多日志文件同时监控
- [ ] **要求**：后台运行（守护进程模式）、日志轮转感知、不重复告警
- [ ] **验收标准**：模拟错误日志输入，验证告警规则触发和通知发送

### Day 26
- [ ] **实战项目**：自动备份脚本
- [ ] **需求**：编写一个自动备份脚本（backup.sh），支持：
  - 备份目标目录/数据库/配置文件
  - 增量备份 + 全量备份策略
  - 压缩备份文件（tar.gz）
  - 计算备份文件 MD5 校验
  - 自动删除超过 N 天的旧备份
  - 备份完成后发送通知（成功/失败）
  - 支持远程同步（rsync/SCP 到备份服务器）
- [ ] **要求**：带锁机制（防止重复执行）、日志记录、错误回滚
- [ ] **验收标准**：在 cron 中定时运行，验证备份文件完整性和可恢复性

### Day 27
- [ ] **学习内容**：Bash 脚本编程进阶 — 高级技巧
- [ ] 子 shell 与进程替换：( )、{ }、<( )、>( )
- [ ] 并行执行：& 后台执行 + wait 等待
- [ ] 命名管道（mkfifo）和进程间通信
- [ ] 使用 xargs 和 GNU parallel 进行并行处理
- [ ] 脚本打包与分发：tar + 安装脚本模式
- [ ] **SRE 实战案例**：用 parallel 加速 100 台服务器的并发巡检（比串行快 10 倍）
- [ ] **练习**：编写并行脚本，同时检查多台服务器的磁盘、内存、CPU 状态
- [ ] **扩展**：将常用脚本打包成可执行工具，支持 --version、--help

### Day 28
- [ ] **阶段总结与测试**：Linux 基础与 Shell 脚本综合能力评估
- [ ] **理论测试**：
  - 解释 Linux 文件权限 755/644/600 的含义
  - 说明 SIGTERM 和 SIGKILL 的区别
  - 解释 systemd 中 [Unit]/[Service]/[Install] 的作用
  - 说明 grep -E 和 grep -P 的区别
- [ ] **实操测试**：
  - 在 10 分钟内完成：创建用户 → 配置 SSH → 安装 nginx → 编写 systemctl 服务 → 验证访问
  - 分析 Nginx 日志：找出 Top 10 IP、5xx 错误率、平均响应时间
  - 编写一个 Shell 脚本：检查磁盘使用率，超过 90% 发送告警
- [ ] **项目回顾**：
  - 服务器初始化脚本是否能在干净系统上一键完成？
  - 日志监控脚本是否稳定运行无内存泄漏？
  - 备份脚本的恢复流程是否验证过？
- [ ] **达标标准**：能独立完成日常 Linux 运维任务，不查阅文档完成 80% 常用命令

## Week 5：网络基础（上）

### Day 29
- [ ] **学习内容**：OSI 七层模型与 TCP/IP 协议栈
- [ ] 掌握 OSI 七层，理解每层职责、典型协议和设备
- [ ] 理解数据封装与解封装过程，MTU 对分片的影响
- [ ] **SRE 实战案例**：网站打不开 → ping 通 → telnet 不通 → 定位防火墙
- [ ] **练习**：画出 OSI 模型，标注 HTTP 请求经过的每一层
- [ ] **扩展**：用 `tcpdump -v` 观察 TCP 数据包封装

### Day 30
- [ ] **学习内容**：TCP 协议详解 — 三次握手、四次挥手、状态机
- [ ] TCP 11 种状态、TIME_WAIT 调优、CLOSE_WAIT 成因
- [ ] TCP 拥塞控制、KeepAlive 机制
- [ ] **SRE 实战案例**：大量 CLOSE_WAIT → 应用未关闭连接 → 文件描述符耗尽 → OOM
- [ ] **练习**：用 `ss -tan` 查看 TCP 状态统计
- [ ] **扩展**：用 `sysctl` 查看/调整 TCP 内核参数

### Day 31
- [ ] **学习内容**：UDP 协议、QUIC（HTTP/3）
- [ ] **SRE 实战案例**：DNS 查询超时 → UDP 53 被丢弃 → TCP 53 回退
- [ ] **练习**：用 netcat 发送 UDP 数据包，对比 TCP 延迟

### Day 32
- [ ] **学习内容**：IP 协议 — 地址分类、子网掩码、CIDR、NAT
- [ ] IPv4 私有地址段、IPv6 基础、双栈共存
- [ ] **SRE 实战案例**：云服务器私有 IP + NAT 网关，NAT 带宽瓶颈
- [ ] **练习**：完成 5 道子网划分题
- [ ] **扩展**：配置 Linux 双栈

### Day 33
- [ ] **学习内容**：路由基础 — 路由表、默认网关、静态路由
- [ ] **SRE 实战案例**：容器网络不通 → `ip route show` 发现 Pod 路由缺失
- [ ] **练习**：查看/分析/修改路由表
- [ ] **扩展**：搭建两个 namespace 配置跨路由

### Day 34
- [ ] **学习内容**：DNS 协议 — 记录类型、解析链、TTL、DNS 安全
- [ ] **SRE 实战案例**：DNS 解析到旧 IP → 修改 TTL 为 60 缩短影响
- [ ] **练习**：用 `dig +trace` 追踪完整 DNS 解析链
- [ ] **扩展**：搭建 CoreDNS 配置自定义解析

### Day 35
- [ ] **复习与实战**：从 URL 到页面的完整过程
- [ ] 画出 DNS → TCP → TLS → HTTP 流程图
- [ ] 编写网络诊断脚本
- [ ] 分析 `curl -vvv` 输出
- [ ] **自我评估**：能否解释"网站打不开"的 5 种可能原因？

## Week 6：网络工具与实战

### Day 36
- [ ] **学习内容**：ping/traceroute/mtr/dig
- [ ] **SRE 实战案例**：mtr 发现丢包 80% → 确认运营商问题
- [ ] **练习**：用 mtr 分析到多个云厂商的网络质量
- [ ] **扩展**：用 `fping` 批量 ping 生成延迟报告

### Day 37
- [ ] **学习内容**：nc/curl/wget 进阶
- [ ] curl 时间分解
- [ ] **SRE 实战案例**：nc 测试端口通但应用连不上 → bind-address 问题
- [ ] **练习**：编写健康检查脚本
- [ ] **扩展**：用 curl `--resolve` 强制解析测试

### Day 38
- [ ] **学习内容**：tcpdump 抓包分析
- [ ] BPF 过滤语法、Wireshark 基础
- [ ] **SRE 实战案例**：连接超时 → tcpdump → TCP 重传过多
- [ ] **练习**：抓取 HTTP 流量和 DNS 查询

### Day 39
- [ ] **学习内容**：iptables/nftables 防火墙 + 云安全组
- [ ] **SRE 实战案例**：fail2ban + iptables 自动封禁恶意 IP
- [ ] **练习**：配置基本防火墙规则
- [ ] **扩展**：配置端口转发、安装 fail2ban

### Day 40
- [ ] **学习内容**：HTTP/HTTPS 协议深入
- [ ] HTTP 方法/状态码、TLS 握手、HTTP/2/HTTP/3
- [ ] **SRE 实战案例**：502 Bad Gateway → Nginx 上游崩溃
- [ ] **练习**：用 curl 测试 HTTP 场景
- [ ] **扩展**：用 `openssl s_client` 检查证书

### Day 41
- [ ] **学习内容**：Socket 编程与 Nginx/HAProxy 负载均衡
- [ ] Socket 模型、多路复用、ulimit、反向代理
- [ ] **SRE 实战案例**：Nginx "Too many open files" → 调整 ulimit
- [ ] **练习**：用 Python socket 编写 TCP Server
- [ ] **扩展**：配置 Nginx 负载均衡

### Day 42
- [ ] **阶段总结**：网络基础综合评估
- [ ] **理论测试**：TIME_WAIT vs CLOSE_WAIT、HTTPS 流程、DNS 解析链
- [ ] **实操测试**：tcpdump 抓包、网络诊断脚本、curl 时间分解
- [ ] **自我评估**：能否独立完成网络故障排查？


## Week 7：Python 编程（SRE 导向）

### Day 43
- [ ] **学习内容**：Python 环境搭建与开发规范
- [ ] pyenv/virtualenv、PEP 8、black/flake8
- [ ] **SRE 实战场景**：生产脚本用 venv 隔离依赖
- [ ] **练习**：搭建环境，运行第一个 SRE 脚本
- [ ] **扩展**：配置 VS Code/pyright LSP

### Day 44
- [ ] **学习内容**：数据类型与配置文件处理
- [ ] 字符串、字典与 JSON、YAML 处理（PyYAML）
- [ ] **SRE 实战案例**：解析配置文件，验证必填字段
- [ ] **练习**：读取 YAML 配置，检查缺失字段

### Day 45
- [ ] **学习内容**：系统命令执行与文件操作
- [ ] subprocess、pathlib
- [ ] **SRE 实战案例**：用 subprocess 执行 `df -h` 解析磁盘使用率
- [ ] **练习**：编写脚本执行 `ps aux`，找 CPU 前 10 进程

### Day 46
- [ ] **学习内容**：函数、日志模块与异常处理
- [ ] 函数定义、logging 模块、try/except、重试模式
- [ ] **SRE 实战案例**：API 调用失败 → 自动重试 3 次 → 失败发告警
- [ ] **练习**：实现 retry() 装饰器

### Day 47
- [ ] **学习内容**：正则表达式与日志解析
- [ ] re 模块、贪婪/非贪婪、分组捕获
- [ ] **SRE 实战案例**：用正则提取 Nginx 日志 IP/状态码，统计 Top 20
- [ ] **练习**：编写日志分析函数

### Day 48
- [ ] **学习内容**：网络编程与 HTTP 客户端
- [ ] socket、requests、aiohttp 异步
- [ ] **SRE 实战案例**：用 requests 调用 K8s API
- [ ] **练习**：编写健康检查脚本，并发检查 10 个 URL
- [ ] **扩展**：实现 Webhook 告警机器人

### Day 49
- [ ] **学习内容**：数据库交互（SQLite）
- [ ] sqlite3、SQL 查询、数据表设计
- [ ] **SRE 实战案例**：将监控指标存入 SQLite，查询历史趋势
- [ ] **练习**：设计监控数据表

## Week 8：Python 进阶与 SRE 实战

### Day 50
- [ ] **学习内容**：并发编程
- [ ] threading vs multiprocessing、concurrent.futures、asyncio
- [ ] **SRE 实战案例**：并发检查 100 台服务器，比串行快 10 倍
- [ ] **练习**：用 ThreadPoolExecutor 批量 SSH 执行

### Day 51
- [ ] **学习内容**：CLI 工具开发
- [ ] typer/click、rich 彩色输出
- [ ] **SRE 实战案例**：将运维脚本整合为 CLI 工具
- [ ] **练习**：用 typer 编写 CLI，支持 `check`/`deploy`/`logs`

### Day 52
- [ ] **学习内容**：装饰器与高级技巧
- [ ] @timer/@retry、上下文管理器
- [ ] **SRE 实战案例**：为 API 调用添加重试和超时装饰器
- [ ] **练习**：编写常用装饰器库

### Day 53
- [ ] **学习内容**：面向对象设计（SRE 工具架构）
- [ ] 类与对象、dataclass、组合模式
- [ ] **SRE 实战案例**：设计 Server/Monitor/Alert 类
- [ ] **练习**：用 dataclass 设计配置管理类

### Day 54
- [ ] **实战项目**：主机监控系统（Python 版）
- [ ] **需求**：psutil 采集 + SQLite 存储 + Flask 展示 + 阈值告警

### Day 55
- [ ] **实战项目**：批量管理工具
- [ ] **需求**：YAML 读取服务器列表 + 并发 SSH 执行 + 结果汇总

### Day 56
- [ ] **Python 阶段测试**
- [ ] **理论测试**：GIL、threading vs multiprocessing
- [ ] **实操测试**：重写 Shell 日志分析脚本、实现 retry 装饰器、编写 CLI
- [ ] **自我评估**：能否用 Python 独立完成日常 SRE 自动化任务？


## Week 9：Go 语言基础（SRE 导向）

### Day 57
- [ ] **学习内容**：Go 环境搭建
- [ ] 安装 Go、Go Modules、golangci-lint、GOPROXY
- [ ] **SRE 视角**：K8s/Prometheus/Terraform/Docker 都是 Go 写的
- [ ] **练习**：搭建环境，编写 Hello World，编译为二进制

### Day 58
- [ ] **学习内容**：Go 基础语法
- [ ] 变量/数据类型/控制流程、struct
- [ ] **SRE 实战案例**：定义 Server 结构体
- [ ] **练习**：完成 Tour of Go 前 30 题

### Day 59
- [ ] **学习内容**：函数与错误处理
- [ ] 多返回值、defer、error 接口
- [ ] **SRE 实战案例**：优雅关闭 HTTP 服务
- [ ] **练习**：编写文件读取函数，处理错误

### Day 60
- [ ] **学习内容**：数据结构
- [ ] 切片、Map、sync.Map
- [ ] **SRE 实战案例**：用 Map 存储指标缓存
- [ ] **练习**：实现 LRU 缓存

### Day 61
- [ ] **学习内容**：接口与组合
- [ ] 接口定义、隐式实现、组合优于继承
- [ ] **SRE 实战案例**：定义 Checker 接口
- [ ] **练习**：设计 Monitor 接口

### Day 62
- [ ] **学习内容**：并发编程（核心）
- [ ] goroutine、channel、sync（WaitGroup/Mutex）
- [ ] **SRE 实战案例**：用 goroutine + channel 实现并发健康检查
- [ ] **练习**：实现 Worker Pool 模式

## Week 10：Go 进阶与 SRE 实战

### Day 63
- [ ] **学习内容**：标准库与网络编程
- [ ] net/http、encoding/json、os/exec
- [ ] **SRE 实战案例**：用 net/http 编写健康检查 Server
- [ ] **练习**：实现 HTTP Server（/health /metrics /config）

### Day 64
- [ ] **学习内容**：CLI 工具开发
- [ ] cobra 库、viper 配置管理
- [ ] **SRE 实战案例**：用 cobra 编写 kube-tools CLI
- [ ] **练习**：编写 CLI 工具

### Day 65
- [ ] **学习内容**：Context 与超时控制
- [ ] context 包、避免 goroutine 泄漏
- [ ] **SRE 实战案例**：HTTP 请求超时控制
- [ ] **练习**：用 context 实现带超时的并发健康检查

### Day 66
- [ ] **学习内容**：测试与基准测试
- [ ] go test、table-driven tests、基准测试
- [ ] **SRE 实战案例**：为核心监控逻辑编写测试
- [ ] **练习**：编写完整单元测试

### Day 67
- [ ] **实战项目**：Prometheus Exporter
- [ ] **需求**：采集指标 + 暴露 /metrics + SIGHUP 热重载

### Day 68
- [ ] **实战项目**：并发服务发现工具
- [ ] **需求**：并发扫描 IP 段端口 + 识别服务 + 输出报告

### Day 69
- [ ] **Go 阶段测试**
- [ ] **理论测试**：goroutine vs thread、channel 阻塞、defer 顺序
- [ ] **实操测试**：并发健康检查器、Worker Pool、单元测试
- [ ] **自我评估**：能否用 Go 编写运维工具和 Exporter？


## Week 11：数据库运维（新增）

### Day 70
- [ ] **学习内容**：MySQL 基础与架构
- [ ] 三层架构、InnoDB vs MyISAM、binlog/redo log/undo log
- [ ] **SRE 实战案例**：binlog 占满磁盘 → 配置自动清理
- [ ] **练习**：安装 MySQL，创建数据库/用户/表

### Day 71
- [ ] **学习内容**：MySQL 性能调优
- [ ] 慢查询日志、EXPLAIN、索引原理
- [ ] **SRE 实战案例**：慢查询 → EXPLAIN 全表扫描 → 加索引 → QPS 提升 10 倍
- [ ] **练习**：创建测试表，模拟慢查询并优化

### Day 72
- [ ] **学习内容**：MySQL 高可用与备份
- [ ] 主从复制、备份策略（mysqldump/xtrabackup/PITR）
- [ ] **SRE 实战案例**：误删数据 → 用 binlog 恢复
- [ ] **练习**：配置主从复制，测试故障切换

### Day 73
- [ ] **学习内容**：Redis 运维基础
- [ ] 数据类型、持久化（RDB/AOF）、内存淘汰策略
- [ ] **SRE 实战案例**：Redis 内存爆满 → 大 Key 排查
- [ ] **练习**：安装 Redis，测试数据类型

### Day 74
- [ ] **学习内容**：Redis 高可用与集群
- [ ] Sentinel、Redis Cluster
- [ ] **SRE 实战案例**：Sentinel 故障转移 → 30 秒内自动切换
- [ ] **练习**：配置 Redis Sentinel，模拟故障
- [ ] **扩展**：搭建 Redis Cluster（3 主 3 从）

### Day 75
- [ ] **复习与实战**：数据库综合评估
- [ ] **场景**：MySQL 慢查询优化、Redis 大 Key 排查、误删数据恢复
- [ ] **自我评估**：能否独立完成数据库日常运维？

## Week 11：Docker 基础

### Day 76
- [ ] **学习内容**：Docker 简介与安装
- [ ] 容器 vs 虚拟机：共享内核、轻量、秒级启动
- [ ] Docker 架构：Client → Daemon → Registry
- [ ] **SRE 实战场景**：微服务部署 → 每个服务一个容器 → 环境一致性、快速扩缩容
- [ ] **练习**：安装 Docker，运行 hello-world

### Day 77
- [ ] **学习内容**：Docker 镜像基础
- [ ] 镜像分层存储、docker images/pull/rmi/tag
- [ ] Dockerfile 基础：FROM/RUN/CMD
- [ ] **练习**：编写第一个 Dockerfile

### Day 78
- [ ] **学习内容**：Dockerfile 进阶构建
- [ ] 多阶段构建：builder 编译 → runtime 仅复制产物
- [ ] **SRE 实战案例**：Go 应用多阶段构建 → 最终镜像仅 10MB
- [ ] **练习**：构建 Nginx 自定义镜像

### Day 79
- [ ] **学习内容**：Docker 容器管理
- [ ] docker run/ps/exec/stop/logs 常用操作
- [ ] **SRE 实战场景**：部署 Redis 容器 → -d -p -v --name
- [ ] **练习**：运行并管理多个容器

### Day 80
- [ ] **学习内容**：Docker 数据管理
- [ ] Volumes/Bind Mount/tmpfs
- [ ] **SRE 实战场景**：MySQL 数据卷持久化 → 删除容器数据不丢失
- [ ] **练习**：创建数据卷，验证数据保留

### Day 81
- [ ] **学习内容**：Docker 网络管理
- [ ] bridge/host/none 网络、用户定义网络
- [ ] **SRE 实战场景**：微服务 → 自定义网络 → 容器间通过服务名通信
- [ ] **练习**：验证容器间通过名称通信

### Day 82
- [ ] **实战项目**：Docker 化 Web 应用
- [ ] **需求**：Dockerfile + docker-compose（app + redis + postgres）+ 健康检查
- [ ] **验收**：docker-compose up -d → curl → 200 OK

## Week 12：Docker 进阶

### Day 83
- [ ] **学习内容**：Dockerfile 最佳实践
- [ ] 优化镜像大小、层缓存、安全基线
- [ ] **SRE 实战案例**：1.2GB → 150MB
- [ ] **练习**：优化 Dockerfile

### Day 84
- [ ] **学习内容**：docker-compose 多容器编排
- [ ] services/networks/volumes
- [ ] **练习**：用 compose 搭建 LEMP 环境

### Day 85
- [ ] **学习内容**：Docker 私有仓库
- [ ] Docker Registry、Harbor
- [ ] **练习**：搭建私有 Registry

### Day 86
- [ ] **学习内容**：Docker 安全
- [ ] 容器逃逸风险、Trivy 漏洞扫描
- [ ] **SRE 实战案例**：--privileged 模式 → 逃逸到宿主机
- [ ] **练习**：用 Trivy 扫描镜像

### Day 87
- [ ] **学习内容**：Docker 网络进阶
- [ ] overlay/macvlan 网络、网络隔离
- [ ] **练习**：验证网络隔离

### Day 88
- [ ] **学习内容**：Docker 监控与日志
- [ ] docker stats、日志轮转
- [ ] **SRE 实战案例**：日志爆满 → 配置日志轮转
- [ ] **练习**：配置日志轮转

### Day 89
- [ ] **Docker 阶段测试**：多容器应用部署 + 安全扫描
- [ ] **自我评估**：能否独立完成 Docker 化部署？

## Week 13：Kubernetes 基础（上）

### Day 90
- [ ] **学习内容**：Kubernetes 简介与架构
- [ ] Master/Worker 组件、核心概念
- [ ] **SRE 实战场景**：传统部署 → K8s 部署
- [ ] **练习**：安装 minikube

### Day 91
- [ ] **学习内容**：Kubernetes Pod
- [ ] 探针：liveness/readiness/startup
- [ ] **SRE 实战场景**：启动慢 → startup probe 避免误重启
- [ ] **练习**：编写 Pod YAML

### Day 92
- [ ] **学习内容**：Kubernetes Deployment
- [ ] 滚动更新、回滚、扩缩容
- [ ] **SRE 实战场景**：发布 → 滚动更新 → 发现问题 → 秒级回滚
- [ ] **练习**：部署应用，执行滚动更新并回滚

### Day 93
- [ ] **学习内容**：Kubernetes StatefulSet
- [ ] 有状态应用管理
- [ ] **SRE 实战场景**：MySQL 集群 → 稳定 Pod 名称用于主从复制
- [ ] **练习**：部署 StatefulSet

### Day 94
- [ ] **学习内容**：DaemonSet & Job/CronJob
- [ ] **SRE 实战场景**：Fluent Bit 用 DaemonSet 部署日志收集
- [ ] **练习**：创建 CronJob

### Day 95
- [ ] **学习内容**：Kubernetes Service
- [ ] ClusterIP/NodePort/LoadBalancer
- [ ] **SRE 实战场景**：Pod IP 变化 → Service 自动更新 → 前端无感知
- [ ] **练习**：创建 Service

### Day 96
- [ ] **学习内容**：Kubernetes Ingress
- [ ] HTTP/HTTPS 路由、Ingress Controller
- [ ] **SRE 实战场景**：多域名 → Ingress 路由 → 无需多个 LoadBalancer
- [ ] **练习**：安装 Nginx Ingress Controller

## Week 14：Kubernetes 进阶

### Day 97
- [ ] **学习内容**：ConfigMap 与 Secret
- [ ] **SRE 实战案例**：数据库密码 → Secret → RBAC 控制访问
- [ ] **练习**：创建 ConfigMap 和 Secret

### Day 98
- [ ] **学习内容**：存储 — PV/PVC/StorageClass
- [ ] **SRE 实战场景**：数据库持久化 → PVC
- [ ] **练习**：创建 PVC 并挂载

### Day 99
- [ ] **学习内容**：RBAC 权限管理
- [ ] Role/ClusterRole/RoleBinding/ServiceAccount
- [ ] **练习**：创建 Role 绑定到 ServiceAccount

### Day 100
- [ ] **学习内容**：调度器与亲和性
- [ ] nodeAffinity/podAntiAffinity/Taint & Toleration
- [ ] **SRE 实战场景**：数据库调度到高性能节点
- [ ] **练习**：用 nodeAffinity 调度 Pod

### Day 101
- [ ] **学习内容**：HPA 与扩缩容
- [ ] **SRE 实战场景**：大促流量 → HPA 自动扩容 → 流量下降自动缩容
- [ ] **练习**：配置 HPA，测试自动扩缩容

### Day 102
- [ ] **学习内容**：Helm 包管理器
- [ ] Chart/Release/Repository
- [ ] **SRE 实战场景**：部署 Prometheus → helm install → 一条命令
- [ ] **练习**：用 Helm 部署应用

### Day 103
- [ ] **实战项目**：搭建 K8s 生产级应用
- [ ] **需求**：Web + API + DB + Service + Ingress + HPA
- [ ] **验收**：kubectl apply → 所有服务正常

### Day 104
- [ ] **K8s 阶段测试**：部署完整应用 + 理论测试
- [ ] **自我评估**：能否独立完成 K8s 应用部署？

## Week 15：AWS 基础

### Day 105
- [ ] **学习内容**：AWS 简介与账户管理
- [ ] Region/AZ/IAM 用户与角色、MFA
- [ ] **SRE 实战场景**：生产不用 root → IAM 用户 → 最小权限
- [ ] **练习**：创建 IAM 用户

### Day 106
- [ ] **学习内容**：EC2 基础
- [ ] 实例类型、AMI、安全组、密钥对
- [ ] **练习**：启动 EC2 实例，SSH 登录

### Day 107
- [ ] **学习内容**：VPC 网络
- [ ] 子网规划、NAT Gateway、路由表
- [ ] **SRE 实战场景**：公有子网放 LB → 私有子网放应用和数据库
- [ ] **练习**：搭建 VPC 环境

### Day 108
- [ ] **学习内容**：S3 对象存储
- [ ] 生命周期策略、静态网站托管
- [ ] **SRE 实战场景**：备份数据分层存储 → 节省 70% 成本
- [ ] **练习**：配置 S3 静态网站托管

### Day 109
- [ ] **学习内容**：RDS 数据库
- [ ] Multi-AZ、自动备份、Point-in-Time Recovery
- [ ] **SRE 实战场景**：Multi-AZ → 自动故障转移 → RPO ≈ 0
- [ ] **练习**：创建 RDS 实例

### Day 110
- [ ] **学习内容**：ELB 负载均衡
- [ ] CLB/ALB/NLB、健康检查
- [ ] **SRE 实战场景**：ALB 分发流量 → 自动剔除故障实例
- [ ] **练习**：配置 ALB

### Day 111
- [ ] **学习内容**：Auto Scaling
- [ ] ASG、扩缩容策略
- [ ] **SRE 实战场景**：白天扩容 → 夜间缩容 → 节省成本
- [ ] **练习**：配置 ASG

## Week 16：AWS 进阶

### Day 112
- [ ] **学习内容**：CloudWatch 监控
- [ ] 指标、告警、日志
- [ ] **SRE 实战场景**：CPU > 80% → Alarm → SNS → 告警
- [ ] **练习**：配置监控告警

### Day 113
- [ ] **学习内容**：Route 53 DNS
- [ ] 路由策略、健康检查
- [ ] **SRE 实战场景**：延迟路由 → 用户访问最近区域
- [ ] **练习**：配置域名解析

### Day 114
- [ ] **学习内容**：EKS 弹性 Kubernetes
- [ ] **SRE 实战场景**：不想管理 Control Plane → EKS
- [ ] **练习**：创建 EKS 集群

### Day 115
- [ ] **学习内容**：AWS 安全
- [ ] IAM 最小权限、KMS 加密
- [ ] **SRE 实战场景**：审计 IAM 权限 → 缩小到仅需要
- [ ] **练习**：权限审计

### Day 116
- [ ] **学习内容**：AWS 高可用架构
- [ ] Well-Architected Framework
- [ ] **SRE 实战场景**：设计电商系统 → ALB + ASG + RDS Multi-AZ
- [ ] **练习**：设计高可用架构图

### Day 117
- [ ] **备考**：AWS SAA 认证知识点梳理
- [ ] **练习**：完成 30 道模拟题

### Day 118
- [ ] **备考**：AWS SAA 认证刷题
- [ ] **练习**：完成 50 道模拟题

### Day 119
- [ ] **自我评估**：AWS 知识掌握
- [ ] **目标**：准备 AWS SAA 认证考试

### 补充：阿里云对照表
| AWS 服务 | 阿里云对应 | 说明 |
|----------|-----------|------|
| EC2 | ECS | 云服务器 |
| VPC | VPC | 专有网络 |
| S3 | OSS | 对象存储 |
| RDS | RDS | 云数据库 |
| ELB/ALB | SLB/ALB | 负载均衡 |
| EKS | ACK | 容器服务 |
| CloudWatch | 云监控 | 监控服务 |
| Route 53 | 云解析 DNS | DNS 服务 |


## Week 17：Terraform IaC

### Day 120
- [ ] **学习内容**：Terraform 简介
- [ ] IaC 理念、Terraform vs CloudFormation
- [ ] **SRE 实战场景**：手动创建 → Terraform → 声明式、可重复
- [ ] **练习**：安装 Terraform

### Day 121
- [ ] **学习内容**：Terraform 基础
- [ ] provider/resource/variable、init/plan/apply/destroy
- [ ] **SRE 实战场景**：plan 预览变更 → apply 创建 → 代码即文档
- [ ] **练习**：用 Terraform 创建 EC2

### Day 122
- [ ] **学习内容**：Terraform 进阶
- [ ] output/data source/模块
- [ ] **SRE 实战场景**：模块化 → dev/test/prod 各一套
- [ ] **练习**：编写模块化配置

### Day 123
- [ ] **学习内容**：Terraform 工作流
- [ ] workspace、远程状态（S3 + DynamoDB）
- [ ] **SRE 实战场景**：团队协作 → S3 状态 + DynamoDB 锁定
- [ ] **练习**：配置远程状态

### Day 124
- [ ] **实战项目**：VPC 模块化
- [ ] **需求**：可复用 VPC 模块（CIDR/子网/路由）
- [ ] **验收**：多 workspace 复用

### Day 125
- [ ] **实战项目**：EKS 基础设施
- [ ] **需求**：Terraform 搭建完整 EKS（VPC + EKS + Node Group）
- [ ] **验收**：terraform apply → kubectl get nodes 就绪

## Week 18：Ansible 配置管理

### Day 126
- [ ] **学习内容**：Ansible 简介
- [ ] 无代理、SSH 驱动、YAML 语法
- [ ] **SRE 实战场景**：批量配置 100 台服务器 → 一条命令
- [ ] **练习**：安装 Ansible，配置 Inventory

### Day 127
- [ ] **学习内容**：Ansible 基础
- [ ] Inventory、Ad-hoc、Playbook
- [ ] **练习**：编写第一个 Playbook

### Day 128
- [ ] **学习内容**：Ansible 常用模块
- [ ] apt/yum/copy/file/service/template
- [ ] **练习**：批量配置管理

### Day 129
- [ ] **学习内容**：Ansible Roles
- [ ] Role 结构、Ansible Galaxy
- [ ] **练习**：编写 nginx Role

### Day 130
- [ ] **学习内容**：Ansible 进阶
- [ ] Jinja2 模板、变量优先级、Facts
- [ ] **练习**：用 Jinja2 生成配置

### Day 131
- [ ] **实战项目**：自动化部署
- [ ] **需求**：安装依赖 → 部署代码 → 配置 → 启动 → 健康检查
- [ ] **验收**：ansible-playbook → 自动部署完成

### Day 132
- [ ] **IaC 阶段总结**：Terraform + Ansible 综合实践
- [ ] **自我评估**：能否用 IaC 管理基础设施？

## Week 19：监控体系

### Day 133
- [ ] **学习内容**：可观测性基础 — SLO/SLI/SLA
- [ ] 黄金指标、USE/RED 方法、错误预算
- [ ] **SRE 实战场景**：定义 SLO 99.95% → 每月最多 21.6 分钟不可用
- [ ] **练习**：定义服务的 SLO/SLI

### Day 134
- [ ] **学习内容**：Prometheus 基础
- [ ] Pull 模型、时间序列数据库
- [ ] **SRE 实战场景**：传统监控 push → Prometheus pull → 自描述指标
- [ ] **练习**：安装 Prometheus，配置 node_exporter

### Day 135
- [ ] **学习内容**：PromQL 查询语言
- [ ] Counter/Gauge/Histogram/Summary
- [ ] **SRE 实战案例**：QPS → rate(http_requests_total[5m])
- [ ] **练习**：编写 PromQL 查询

### Day 136
- [ ] **学习内容**：Grafana 可视化
- [ ] 仪表盘创建、常用面板类型
- [ ] **SRE 实战场景**：运维大屏 → 一目了然
- [ ] **练习**：创建监控仪表盘

### Day 137
- [ ] **学习内容**：Kubernetes 监控
- [ ] kube-state-metrics、node-exporter、cAdvisor
- [ ] **SRE 实战场景**：Pod 频繁重启 → 监控 restart_count → 告警
- [ ] **练习**：部署 kube-prometheus-stack

### Day 138
- [ ] **学习内容**：Alertmanager 告警
- [ ] 告警规则、分级、通知渠道
- [ ] **SRE 实战场景**：CPU > 90% → P2 告警 → 钉钉通知
- [ ] **练习**：配置告警规则

### Day 139
- [ ] **实战项目**：搭建完整监控体系
- [ ] **需求**：Prometheus + Grafana + Alertmanager + 自定义指标
- [ ] **验收**：模拟故障 → 触发告警 → 收到通知

## Week 20：日志与链路追踪

### Day 140
- [ ] **学习内容**：日志收集基础 — ELK
- [ ] **SRE 实战场景**：多服务器日志 → ELK 集中收集 → 排查效率提升 10 倍
- [ ] **练习**：安装 Elasticsearch

### Day 141
- [ ] **学习内容**：Logstash/Fluentd 日志采集
- [ ] **SRE 实战场景**：Nginx 日志 → Fluent Bit → 结构化 → Elasticsearch
- [ ] **练习**：配置 Fluent Bit

### Day 142
- [ ] **学习内容**：Kibana 日志可视化
- [ ] **SRE 实战场景**：生产故障 → Kibana 搜索 ERROR → 快速定位
- [ ] **练习**：创建日志仪表盘

### Day 143
- [ ] **学习内容**：Loki 日志系统
- [ ] Loki vs ELK：成本降低 80%
- [ ] **练习**：搭建 Loki + Promtail + Grafana

### Day 144
- [ ] **学习内容**：链路追踪 — Jaeger
- [ ] Trace/Span 概念
- [ ] **SRE 实战场景**：API 慢 → Jaeger → 数据库查询占 80% → 优化 SQL
- [ ] **练习**：安装 Jaeger

### Day 145
- [ ] **学习内容**：APM 集成
- [ ] OpenTelemetry SDK、分布式追踪
- [ ] **SRE 实战场景**：用户反馈慢 → APM → 第三方 API 超时 → 添加重试
- [ ] **练习**：集成 OpenTelemetry

### Day 146
- [ ] **可观测性阶段总结**：三大支柱
- [ ] **综合项目**：Metrics + Logs + Traces + Alerts
- [ ] **自我评估**：能否独立搭建监控体系？

## Week 21：CI/CD 基础

### Day 147
- [ ] **学习内容**：CI/CD 概念与 GitOps
- [ ] CI/CD 区别、GitOps 理念
- [ ] **SRE 实战场景**：手动部署 → CI/CD → 自动化、可回滚
- [ ] **练习**：理解 CI/CD 流程

### Day 148
- [ ] **学习内容**：GitHub Actions
- [ ] Workflow 语法、Marketplace
- [ ] **SRE 实战场景**：push → lint → test → build → push image
- [ ] **练习**：编写第一个 CI 流程

### Day 149
- [ ] **学习内容**：GitLab CI
- [ ] .gitlab-ci.yml、Runner 配置
- [ ] **练习**：配置 GitLab CI Pipeline

### Day 150
- [ ] **学习内容**：Jenkins
- [ ] Pipeline 语法、插件生态
- [ ] **练习**：创建 Jenkins Pipeline

### Day 151
- [ ] **学习内容**：构建工具集成
- [ ] Maven/Gradle/npm/pip
- [ ] **练习**：CI 中集成构建步骤

### Day 152
- [ ] **学习内容**：CI 中构建和推送镜像
- [ ] Docker build、镜像标签策略
- [ ] **SRE 实战场景**：CI → 构建 → 推送 Harbor → 更新 K8s
- [ ] **练习**：CI 中构建并推送镜像

### Day 153
- [ ] **实战项目**：完整 CI/CD 流程
- [ ] **需求**：代码提交 → 构建 → 测试 → 推送 → 部署
- [ ] **验收**：git push → 自动部署完成

## Week 22：DevOps 高级实践

### Day 154
- [ ] **学习内容**：ArgoCD — GitOps
- [ ] **SRE 实战场景**：kubectl apply → ArgoCD 监听 Git → 自动同步
- [ ] **练习**：部署 ArgoCD

### Day 155
- [ ] **学习内容**：部署策略
- [ ] Rolling/Blue-Green/Canary
- [ ] **SRE 实战场景**：Canary → 5% 流量 → 监控 → 逐步放量
- [ ] **练习**：配置金丝雀发布

### Day 156
- [ ] **学习内容**：密钥管理 — Vault
- [ ] **SRE 实战场景**：硬编码密码 → Vault 动态凭据
- [ ] **练习**：安装 Vault

### Day 157
- [ ] **学习内容**：多环境管理
- [ ] dev → staging → production
- [ ] **练习**：配置多环境部署

### Day 158
- [ ] **学习内容**：混沌工程
- [ ] Chaos Monkey/Litmus/Chaos Mesh
- [ ] **SRE 实战场景**：定期混沌实验 → 随机杀 Pod → 验证自动恢复
- [ ] **练习**：注入网络延迟故障

### Day 159
- [ ] **学习内容**：安全扫描集成
- [ ] SAST/DAST/Trivy
- [ ] **SRE 实战场景**：CI 集成 Trivy → 发现 CVE → 阻断部署
- [ ] **练习**：CI 中集成安全扫描

### Day 160
- [ ] **阶段总结**：完整 GitOps 流水线
- [ ] **自我评估**：能否设计和实现完整 CI/CD？


## Week 21：LLM Ops 基础（新增）

### Day 161
- [ ] **学习内容**：LLM Ops 概述
- [ ] LLM Ops vs MLOps 差异：模型规模、推理延迟关注 TTFT/TPOT
- [ ] **SRE 实战场景**：大模型服务 vs 传统 Web 服务的运维差异
- [ ] **练习**：阅读《大模型运维系统学习指南》，整理知识框架

### Day 162
- [ ] **学习内容**：GPU 基础设施运维
- [ ] nvidia-smi、NVLink、CUDA 版本管理、MIG 分区
- [ ] **SRE 实战案例**：GPU OOM → nvidia-smi 排查 → 调整 batch size
- [ ] **练习**：编写 GPU 监控脚本

### Day 163
- [ ] **学习内容**：模型推理部署
- [ ] vLLM、Ollama、llama.cpp、TGI 对比
- [ ] 推理优化：PagedAttention、Continuous Batching、量化
- [ ] **SRE 实战案例**：vLLM 部署 7B 模型 → 调整 tensor_parallel_size → 吞吐量提升 3 倍
- [ ] **练习**：用 Ollama 部署本地模型，测试量化版本

### Day 164
- [ ] **学习内容**：推理服务指标与监控
- [ ] TTFT/TPOT、吞吐量、并发数
- [ ] **SRE 实战案例**：TTFT 飙升 → KV Cache 满 → 调整 max_num_seqs
- [ ] **练习**：编写推理服务 Prometheus Exporter

### Day 165
- [ ] **学习内容**：模型微调流水线
- [ ] LoRA/QLoRA、Axolotl/TRL/Unsloth
- [ ] **SRE 实战案例**：微调 OOM → QLoRA + 梯度检查点 → 显存减半
- [ ] **练习**：用 Unsloth 微调小模型

### Day 166
- [ ] **复习与实战**：LLM Ops 基础综合
- [ ] **场景**：部署本地 LLM 服务 + 监控 + API 暴露
- [ ] **自我评估**：能否独立完成模型推理部署？

## Week 22：LLM 生产运维（新增）

### Day 167
- [ ] **学习内容**：模型服务高可用
- [ ] 多副本、负载均衡、基于 GPU 利用率的自动扩缩容
- [ ] **SRE 实战案例**：单节点故障 → 多副本 + HPA → 无缝切换
- [ ] **练习**：用 K8s 部署多副本模型服务

### Day 168
- [ ] **学习内容**：RAG 架构运维
- [ ] 向量数据库（Milvus/pgvector）、Embedding 服务
- [ ] **SRE 实战案例**：向量检索延迟 → HNSW 索引 → 查询从 2s → 50ms
- [ ] **练习**：部署 pgvector，测试向量检索

### Day 169
- [ ] **学习内容**：AI 应用监控
- [ ] Prompt 版本管理、输出质量监控、token 成本追踪
- [ ] **SRE 实战案例**：输出质量下降 → 对比 Prompt 版本 → 回滚
- [ ] **练习**：实现 token 成本追踪

### Day 170
- [ ] **学习内容**：安全与合规
- [ ] Prompt 注入检测、内容审核、数据脱敏
- [ ] **SRE 实战案例**：Prompt 注入 → 添加过滤层 → 拦截
- [ ] **练习**：实现 Prompt 注入检测

### Day 171
- [ ] **实战项目**：LLM 服务全链路
- [ ] **需求**：部署 + 高可用 + 监控 + 告警 + 成本控制
- [ ] **验收**：完整可运行的 LLM 服务

### Day 172
- [ ] **LLM Ops 阶段测试**
- [ ] **理论测试**：TTFT vs TPOT、LoRA 原理、vLLM 优化
- [ ] **实操测试**：部署模型服务 + 编写监控
- [ ] **自我评估**：能否独立运维生产级 LLM 服务？


## Week 23：SRE 核心实践

### Day 173
- [ ] **学习内容**：On-Call 实践
- [ ] 告警分级、应急响应流程
- [ ] **SRE 实战案例**：凌晨 3 点告警 → 确认 → 回滚 → 10 分钟恢复 → RCA
- [ ] **练习**：设计 On-Call 流程文档

### Day 174
- [ ] **学习内容**：事故管理与 RCA
- [ ] 无责文化、事后复盘
- [ ] **练习**：编写 RCA 报告（模拟数据库宕机）

### Day 175
- [ ] **学习内容**：SLO 与错误预算
- [ ] **SRE 实战场景**：预算消耗 80% → 暂停新功能 → 专注稳定性
- [ ] **练习**：设定 SLO，设计消耗策略

### Day 176
- [ ] **学习内容**：容量规划
- [ ] 性能测试、扩缩容策略
- [ ] **SRE 实战场景**：双 11 → 预估 10 倍流量 → 提前扩容 → 压测验证
- [ ] **练习**：用 wrk 进行压力测试

### Day 177
- [ ] **学习内容**：灾备与恢复
- [ ] RPO/RTO、多活架构
- [ ] **SRE 实战场景**：数据库主节点故障 → 切换备节点 → RPO < 1 分钟
- [ ] **练习**：设计灾备方案

### Day 178
- [ ] **学习内容**：成本优化
- [ ] **SRE 实战场景**：$10,000 → $6,000 → 预留实例 + Spot + 自动缩容
- [ ] **练习**：分析成本，提出优化方案

### Day 179
- [ ] **实战项目**：综合 SRE 实践
- [ ] **需求**：SLO + 监控 + 告警 + On-Call + 灾备 + 成本优化
- [ ] **验收**：完整 SRE 文档 + 实际部署


## Week 24：Capstone 综合项目（新增）

### Day 180
- [ ] **项目规划**：从零搭建生产级 SRE 平台
- [ ] 设计架构：VPC + EKS + 微服务 + 可观测性 + CI/CD
- [ ] 编写项目计划书

### Day 181
- [ ] **基础设施**：Terraform 创建 VPC + EKS
- [ ] **验收**：`terraform apply` → `kubectl get nodes` 就绪

### Day 182
- [ ] **应用部署**：部署微服务 + K8s 资源
- [ ] **验收**：`kubectl apply` → 所有服务正常运行

### Day 183
- [ ] **可观测性**：Prometheus + Grafana + Loki + Jaeger
- [ ] **验收**：模拟故障 → 触发告警 → 收到通知

### Day 184
- [ ] **CI/CD**：GitHub Actions → 构建 → ArgoCD 部署
- [ ] **验收**：`git push` → 自动部署

### Day 185
- [ ] **混沌工程**：注入故障，验证自动恢复
- [ ] **验收**：每种故障有对应告警和恢复策略

### Day 186
- [ ] **文档与复盘**：架构文档、运维手册、RCA 报告
- [ ] **验收**：完整 SRE 文档 + 实际部署可演示


## Week 25-26：面试准备与职业规划

### Day 187
- [ ] **学习内容**：简历优化
- [ ] STAR 法则、量化成果
- [ ] **练习**：撰写简历

### Day 188
- [ ] **学习内容**：面试题 — Linux 与网络
- [ ] **练习**：模拟面试

### Day 189
- [ ] **学习内容**：面试题 — 容器与 K8s
- [ ] **练习**：模拟面试

### Day 190
- [ ] **学习内容**：面试题 — 运维与系统设计
- [ ] **练习**：模拟面试

### Day 191
- [ ] **学习内容**：认证准备
- [ ] CKA 考试技巧、AWS SAA 冲刺

### Day 192
- [ ] **学习内容**：软技能
- [ ] 沟通技巧、团队协作、STAR 法则

### Day 193
- [ ] **学习内容**：职业规划
- [ ] 薪资谈判、持续学习

### Day 194
- [ ] **学习内容**：新起点 — 开始投递简历
- [ ] **里程碑**：🎉 24 周完成！入门级 SRE 工程师！
- [ ] **下一步**：CKA/AWS SAA 认证、开源贡献、技术博客

## 📊 里程碑检查点

| 时间 | 里程碑 |
|------|--------|
| 第 4 周末 | ✅ 完成 Linux 基础与 Shell 脚本 |
| 第 6 周末 | ✅ 网络基础扎实 |
| 第 8 周末 | ✅ Python 编程（SRE 导向）熟练 |
| 第 10 周末 | ✅ Go 语言（SRE 导向）熟练 |
| 第 11 周末 | ✅ 数据库运维基础 |
| 第 13 周末 | ✅ Docker 容器化 |
| 第 15 周末 | ✅ K8s 应用部署 |
| 第 16 周末 | ✅ AWS 基础 + 阿里云对照 |
| 第 18 周末 | ✅ IaC（Terraform + Ansible）|
| 第 20 周末 | ✅ 可观测性平台搭建 |
| 第 22 周末 | ✅ 完整 CI/CD 流水线 |
| 第 24 周末 | ✅ Capstone 综合项目完成 |
| 第 26 周末 | 🎉 入门级 SRE + LLM Ops 工程师！ |

---

## 📚 推荐学习资源

### 书籍
- 《SRE：Google 运维解密》《Linux 鸟哥的私房菜》《Kubernetes 权威指南》
- 《深入理解 Prometheus》《Terraform 实战》
- 《The Practice of System and Network Administration》
- 《Site Reliability Engineering Workbook》

### 在线课程
- Coursera: Google IT Support Certificate
- Udemy: AWS Certified Solutions Architect
- Linux Foundation: CKA 认证课程
- Killercoda: 交互式 K8s 学习（原 Katacoda 替代）
- KodeKloud: K8s 实战练习

### 练习平台
- [KodeKloud](https://kodekloud.com) - K8s 实战
- [Play with Docker](https://play.docker.com) - Docker 练习
- [Killercoda](https://killercoda.com) - 交互式学习
- [Grafana Play](https://play.grafana.org) - 可视化示例

### 社区与博客
- Kubernetes 官方文档、CNCF 云原生社区
- 极客时间 SRE 专栏、阿里云开发者社区

### 认证推荐
| 认证 | 厂商 | 难度 | 备考周期 | 费用 |
|------|------|------|---------|------|
| CKA | CNCF | 中高 | 2-3 个月 | ~$395 |
| CKS | CNCF | 高 | 1-2 个月 | ~$395 |
| AWS SAA | AWS | 中 | 1-2 个月 | ~$150 |
| 阿里云 ACP | 阿里云 | 中 | 1-2 个月 | ~¥1200 |

---

## 💪 成功秘诀

1. **每天坚持**：哪怕只有 1 小时，保持连续性
2. **动手实践**：只看不动手等于没学
3. **记笔记**：好记性不如烂笔头
4. **做项目**：把知识点串起来
5. **找同伴**：加入学习群互相督促
6. **教别人**：能讲清楚才是真的懂

---

> 🚀 *坚持 6.5 个月，你一定能成为合格的 SRE 工程师，具备 AI/LLM Ops 能力！加油！*
