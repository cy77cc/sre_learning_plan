# SRE 工程师每日学习计划

> 📅 总周期：24 周（约 6 个月）  
> ⏰ 每日学习时间：2-3 小时  
> 🎯 目标：成为入门级 SRE 工程师

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
- [ ] 安装 VirtualBox 或 WSL2
- [ ] 安装 Ubuntu 22.04 LTS
- [ ] 了解 Linux 历史和发行版区别
- [ ] **练习**：完成 Ubuntu 桌面版安装，更新系统包

### Day 2
- [ ] **学习内容**：文件系统与目录结构
- [ ] 学习 FHS 标准（/bin, /etc, /home, /var, /usr 等）
- [ ] 常用命令：ls, cd, pwd, tree
- [ ] **练习**：使用 tree 查看目录结构，用 ls -la 分析根目录

### Day 3
- [ ] **学习内容**：文件操作命令
- [ ] cp, mv, rm, mkdir, rmdir, touch
- [ ] cat, less, more, head, tail, wc
- [ ] **练习**：复制、移动、查找文件，用 tail -f 监控日志

### Day 4
- [ ] **学习内容**：文本处理基础
- [ ] grep, sed, awk 基础用法
- [ ] 正则表达式入门
- [ ] **练习**：用 grep 查找日志中的错误关键字

### Day 5
- [ ] **学习内容**：文件权限与所有权
- [ ] chmod, chown, chgrp
- [ ] 数字权限（755, 644 等）
- [ ] **练习**：创建一个共享目录，设置合理的权限

### Day 6
- [ ] **学习内容**：用户与用户组管理
- [ ] useradd, usermod, userdel
- [ ] groupadd, groups, id
- [ ] sudo 权限配置
- [ ] **练习**：创建开发用户组和多个用户

### Day 7
- [ ] **复习与实战**：综合练习
- [ ] 完成一个简单的文件管理脚本
- [ ] **测试**：自己设计几个场景进行练习

---

## Week 2：进程管理与系统监控

### Day 8
- [ ] **学习内容**：进程管理基础
- [ ] ps, top, htop, pstree
- [ ] 进程状态（R/S/D/Z）
- [ ] **练习**：用 ps 和 top 查看系统进程

### Day 9
- [ ] **学习内容**：进程控制
- [ ] kill, killall, pkill
- [ ] 信号机制（SIGTERM, SIGKILL）
- [ ] **练习**：启动一个后台进程，然后用 kill 停止它

### Day 10
- [ ] **学习内容**： systemd 基础
- [ ] systemctl start/stop/restart/enable/disable
- [ ] systemd 单元文件基础
- [ ] **练习**：编写一个简单的 systemd 服务单元

### Day 11
- [ ] **学习内容**：系统监控命令
- [ ] uptime, free, df, du
- [ ] vmstat, iostat, sar
- [ ] **练习**：分析服务器资源使用情况

### Day 12
- [ ] **学习内容**：磁盘管理
- [ ] fdisk, mkfs, mount, umount
- [ ] df -h, du -sh 分析磁盘
- [ ] **练习**：挂载一个新区进行练习

### Day 13
- [ ] **学习内容**：日志管理
- [ ] journalctl 用法
- [ ] /var/log 目录结构
- [ ] rsyslog 基础
- [ ] **练习**：使用 journalctl 过滤特定服务的日志

### Day 14
- [ ] **复习与实战**
- [ ] 搭建一个小型的 LAMP 环境
- [ ] 练习服务管理和日志分析

---

## Week 3：Shell 脚本编程（上）

### Day 15
- [ ] **学习内容**：Shell 脚本基础
- [ ] #! 解释器声明
- [ ] 变量定义与使用
- [ ] 环境变量 vs 本地变量
- [ ] **练习**：编写第一个 Hello World 脚本

### Day 16
- [ ] **学习内容**：变量进阶
- [ ] 引号区别（单引号/双引号/反引号）
- [ ] read 命令读取输入
- [ ] readonly 和 export
- [ ] **练习**：编写交互式问候脚本

### Day 17
- [ ] **学习内容**：条件判断
- [ ] test 和 [ ] 用法
- [ ] if/elif/else 结构
- [ ] 常见比较运算符（-eq, -gt, -z, -f 等）
- [ ] **练习**：编写服务健康检查脚本

### Day 18
- [ ] **学习内容**：循环结构
- [ ] for 循环
- [ ] while 循环
- [ ] until 循环
- [ ] **练习**：批量创建用户脚本

### Day 19
- [ ] **学习内容**：Case 语句与菜单
- [ ] case ... esac 结构
- [ ] select 菜单
- [ ] **练习**：编写简易的服务管理菜单

### Day 20
- [ ] **学习内容**：函数
- [ ] 函数定义与调用
- [ ] 参数传递（$1, $2, $@, $*）
- [ ] 返回值处理
- [ ] **练习**：将昨天的菜单改写成函数版本

### Day 21
- [ ] **学习内容**：数组
- [ ] 数组定义与访问
- [ ] 数组遍历
- [ ] 关联数组
- [ ] **练习**：编写一个日志分析统计脚本

---

## Week 4：Shell 脚本编程（下）+ 实战项目

### Day 22
- [ ] **学习内容**：字符串处理
- [ ] ${#var}, ${var:offset:length}
- [ ] ${var/pattern/replacement}
- [ ] sed 和 awk 进阶
- [ ] **练习**：字符串提取和替换练习

### Day 23
- [ ] **学习内容**：信号与trap
- [ ] trap 命令
- [ ] 脚本调试（set -x, set -e）
- [ ] **练习**：编写带错误处理的脚本

### Day 24
- [ ] **学习内容**：expect 自动化交互
- [ ] expect 基本命令
- [ ] spawn, send, expect
- [ ] **练习**：编写 SSH 自动登录脚本

### Day 25
- [ ] **实战项目**：服务器初始化脚本
- [ ] 编写一个服务器初始化脚本（安装常用软件、配置SSH等）

### Day 26
- [ ] **实战项目**：日志监控告警脚本
- [ ] 编写一个实时日志关键词监控脚本

### Day 27
- [ ] **实战项目**：备份脚本
- [ ] 编写一个自动备份脚本（压缩、加密、远程同步）

### Day 28
- [ ] **阶段总结与测试**
- [ ] 回顾第一阶段所有知识点
- [ ] 完成一个综合运维脚本
- [ ] **自我评估**：达到 Linux 基础达标标准了吗？

---

# 📖 第二阶段：计算机网络（第 5-6 周）

## Week 5：网络基础

### Day 29
- [ ] **学习内容**：OSI 七层模型
- [ ] 每层的职责和设备
- [ ] 数据封装与解封装过程
- [ ] **练习**：画出 OSI 模型并解释一次 HTTP 请求

### Day 30
- [ ] **学习内容**：TCP 协议详解
- [ ] 三次握手过程
- [ ] 四次挥手过程
- [ ] TCP 状态转换图
- [ ] **练习**：用 tcpdump 抓包观察握手

### Day 31
- [ ] **学习内容**：UDP 协议
- [ ] UDP 头部结构
- [ ] TCP vs UDP 区别
- [ ] 适用场景
- [ ] **练习**：对比 TCP 和 UDP 的区别

### Day 32
- [ ] **学习内容**：IP 协议基础
- [ ] IP 地址分类（A/B/C/D/E 类）
- [ ] 子网掩码与 CIDR
- [ ] 私有 IP vs 公有 IP
- [ ] **练习**：进行子网划分练习

### Day 33
- [ ] **学习内容**：路由基础
- [ ] 路由表解析
- [ ] 默认网关
- [ ] static route
- [ ] **练习**：查看和分析本机路由表

### Day 34
- [ ] **学习内容**：DNS 协议
- [ ] DNS 查询过程（递归/迭代）
- [ ] DNS 记录类型（A, AAAA, CNAME, MX, TXT）
- [ ] **练习**：使用 dig 命令进行 DNS 查询

### Day 35
- [ ] **复习与实战**
- [ ] 理解浏览器输入 URL 到显示页面的全过程
- [ ] 抓包分析 HTTP 请求

---

## Week 6：网络工具与实战

### Day 36
- [ ] **学习内容**：网络诊断工具
- [ ] ping, traceroute, mtr
- [ ] nslookup, dig
- [ ] **练习**：用 mtr 分析网络质量

### Day 37
- [ ] **学习内容**：网络连接工具
- [ ] telnet, nc (netcat)
- [ ] curl, wget 进阶用法
- [ ] **练习**：用 nc 测试端口连通性

### Day 38
- [ ] **学习内容**：tcpdump 抓包
- [ ] 常用过滤表达式
- [ ] 协议分析
- [ ] **练习**：抓取 HTTP 流量并分析

### Day 39
- [ ] **学习内容**：iptables/nftables 基础
- [ ] 表、链、规则概念
- [ ] 常用命令
- [ ] **练习**：配置基本的防火墙规则

### Day 40
- [ ] **学习内容**：HTTP/HTTPS 协议
- [ ] HTTP 请求方法、状态码
- [ ] HTTPS 工作原理（TLS 握手）
- [ ] HTTP/2, HTTP/3 简介
- [ ] **练习**：用 curl 测试各种 HTTP 场景

### Day 41
- [ ] **学习内容**：Socket 编程基础
- [ ] 了解 TCP/UDP Socket 原理
- [ ] **练习**：理解 TCP Server/Client 模型

### Day 42
- [ ] **阶段总结**
- [ ] 搭建一个简易的 Web Server
- [ ] **自我评估**：网络基础知识掌握了吗？

---

# 📖 第三阶段：编程语言 Python / Go（第 7-10 周）

## Week 7：Python 基础（上）

### Day 43
- [ ] **学习内容**：Python 环境搭建
- [ ] 安装 Python 3.10+
- [ ] pyenv 或 conda 管理多版本
- [ ] pip 和 virtualenv
- [ ] **练习**：搭建开发环境，运行第一个程序

### Day 44
- [ ] **学习内容**：变量与数据类型
- [ ] 数字、字符串、布尔
- [ ] 类型转换
- [ ] **练习**：数据类型转换练习

### Day 45
- [ ] **学习内容**：运算符与表达式
- [ ] 算术、比较、逻辑、位运算
- [ ] **练习**：编写一个计算器程序

### Day 46
- [ ] **学习内容**：控制流程
- [ ] if/elif/else
- [ ] for, while 循环
- [ ] break, continue, pass
- [ ] **练习**：打印九九乘法表

### Day 47
- [ ] **学习内容**：数据结构 - 列表
- [ ] 列表操作（增删改查）
- [ ] 列表推导式
- [ ] **练习**：列表操作练习

### Day 48
- [ ] **学习内容**：数据结构 - 元组与集合
- [ ] 元组不可变性
- [ ] 集合操作（交集、并集、差集）
- [ ] **练习**：集合操作练习

### Day 49
- [ ] **学习内容**：数据结构 - 字典
- [ ] 字典创建与操作
- [ ] 字典方法
- [ ] **练习**：统计单词频率

---

## Week 8：Python 基础（下）

### Day 50
- [ ] **学习内容**：函数
- [ ] 函数定义与调用
- [ ] 默认参数、可变参数
- [ ] 匿名函数 lambda
- [ ] **练习**：编写函数实现日志解析

### Day 51
- [ ] **学习内容**：模块与包
- [ ] import 机制
- [ ] 标准库（os, sys, json, datetime）
- [ ] **练习**：编写一个工具模块

### Day 52
- [ ] **学习内容**：文件操作
- [ ] 读写文件
- [ ] 上下文管理器 with
- [ ] **练习**：实现文件备份脚本

### Day 53
- [ ] **学习内容**：错误与异常
- [ ] try/except/finally
- [ ] 自定义异常
- [ ] **练习**：异常处理练习

### Day 54
- [ ] **学习内容**：正则表达式
- [ ] re 模块用法
- [ ] 贪婪 vs 非贪婪
- [ ] **练习**：用正则提取日志中的 IP 和时间戳

### Day 55
- [ ] **学习内容**：面向对象编程
- [ ] 类与对象
- [ ] 继承、多态
- [ ] **练习**：设计一个服务器类

### Day 56
- [ ] **学习内容**：Python 进阶
- [ ] 装饰器
- [ ] 生成器
- [ ] 上下文管理器
- [ ] **练习**：编写一个性能计时装饰器

---

## Week 9：Python 实战

### Day 57
- [ ] **实战项目**：主机监控系统
- [ ] 监控 CPU、内存、磁盘使用率
- [ ] 数据采集与存储

### Day 58
- [ ] **实战项目**：日志分析工具
- [ ] 实现日志解析、统计、告警功能

### Day 59
- [ ] **实战项目**：批量管理工具
- [ ] 用 paramiko 实现 SSH 批量执行命令

### Day 60
- [ ] **学习内容**：多线程与多进程
- [ ] threading, multiprocessing
- [ ] GIL 概念
- [ ] **练习**：并行下载文件

### Day 61
- [ ] **学习内容**：网络编程
- [ ] socket 编程
- [ ] **练习**：实现 TCP Server/Client

### Day 62
- [ ] **学习内容**：HTTP 客户端
- [ ] requests 库
- [ ] API 调用
- [ ] **练习**：调用一个公开 API 并处理返回

### Day 63
- [ ] **Python 阶段测试**
- [ ] 完成一个综合项目（选一个）
- [ ] **自我评估**：Python 是否达到熟练水平？

---

## Week 10：Go 语言

### Day 64
- [ ] **学习内容**：Go 环境搭建
- [ ] 安装 Go
- [ ] GOPATH vs Go Modules
- [ ] **练习**：搭建环境，运行 Hello World

### Day 65
- [ ] **学习内容**：Go 基础语法
- [ ] 变量、数据类型
- [ ] 控制流程
- [ ] **练习**：Go 基础语法练习

### Day 66
- [ ] **学习内容**：函数与错误处理
- [ ] 多返回值
- [ ] error 接口
- [ ] defer/panic/recover
- [ ] **练习**：错误处理练习

### Day 67
- [ ] **学习内容**：数据结构
- [ ] 数组、切片、Map
- [ ] 结构体
- [ ] **练习**：数据结构练习

### Day 68
- [ ] **学习内容**：接口与面向对象
- [ ] 接口定义
- [ ] 组合优于继承
- [ ] **练习**：设计一个接口

### Day 69
- [ ] **学习内容**：并发编程
- [ ] goroutine
- [ ] channel
- [ ] select
- [ ] **练习**：并发爬虫练习

### Day 70
- [ ] **学习内容**：Go 标准库与网络
- [ ] net/http
- [ ] json 处理
- [ ] **练习**：实现一个 HTTP Server

---

# 📖 第四阶段：容器化 Docker + Kubernetes（第 11-14 周）

## Week 11：Docker 基础

### Day 71
- [ ] **学习内容**：Docker 简介与安装
- [ ] Docker 架构（Client/Server/Registry）
- [ ] 安装 Docker Engine
- [ ] **练习**：安装 Docker，运行第一个容器

### Day 72
- [ ] **学习内容**：镜像基础
- [ ] 镜像概念与分层
- [ ] docker images, docker pull
- [ ] Dockerfile 基础指令（FROM, RUN, CMD）
- [ ] **练习**：编写第一个 Dockerfile

### Day 73
- [ ] **学习内容**：镜像构建进阶
- [ ] COPY, ADD, EXPOSE, ENV
- [ ] 多阶段构建
- [ ] **练习**：构建一个 Nginx 镜像

### Day 74
- [ ] **学习内容**：容器管理
- [ ] docker run, docker ps, docker exec
- [ ] 容器生命周期
- [ ] 端口映射与容器互联
- [ ] **练习**：运行并管理多个容器

### Day 75
- [ ] **学习内容**：数据管理
- [ ] 数据卷（Volumes）
- [ ] 绑定挂载
- [ ] tmpfs 挂载
- [ ] **练习**：数据持久化练习

### Day 76
- [ ] **学习内容**：网络管理
- [ ] Docker 网络模式（bridge/host/none/container）
- [ ] 用户定义网络
- [ ] **练习**：搭建桥接网络

### Day 77
- [ ] **实战项目**：Docker 化应用
- [ ] 将一个 Web 应用容器化

---

## Week 12：Docker 进阶

### Day 78
- [ ] **学习内容**：Dockerfile 最佳实践
- [ ] 优化镜像大小
- [ ] 层缓存优化
- [ ] 安全基线
- [ ] **练习**：优化一个 Dockerfile

### Day 79
- [ ] **学习内容**：docker-compose
- [ ] docker-compose.yml 语法
- [ ] 多容器编排
- [ ] **练习**：用 compose 搭建 LAMP/LEMP 环境

### Day 80
- [ ] **学习内容**：私有仓库
- [ ] Docker Registry
- [ ] Harbor 部署
- [ ] 镜像推送拉取
- [ ] **练习**：搭建私有镜像仓库

### Day 81
- [ ] **学习内容**：Docker 安全
- [ ] 容器逃逸风险
- [ ] 用户命名空间
- [ ] 安全扫描
- [ ] **练习**：学习 Docker 安全配置

### Day 82
- [ ] **学习内容**：Docker 网络进阶
- [ ] DNS 服务发现
- [ ] Ingress 网络
- [ ] **练习**：容器网络配置练习

### Day 83
- [ ] **学习内容**：监控与日志
- [ ] docker stats
- [ ] 日志驱动
- [ ] **练习**：容器监控练习

### Day 84
- [ ] **Docker 阶段测试**
- [ ] 完成一个完整的多容器应用
- [ ] **自我评估**：Docker 是否熟练？

---

## Week 13：Kubernetes 基础（上）

### Day 85
- [ ] **学习内容**：K8s 简介与架构
- [ ] K8s 核心概念
- [ ] Master/Node 组件
- [ ] **练习**：安装 minikube 或 kind

### Day 86
- [ ] **学习内容**：Pod
- [ ] Pod 定义与创建
- [ ] Pod 生命周期
- [ ] 探针（liveness/readiness）
- [ ] **练习**：编写 Pod YAML

### Day 87
- [ ] **学习内容**：Workloads - Deployment
- [ ] Deployment 概念
- [ ] 滚动更新与回滚
- [ ] **练习**：部署一个应用并更新

### Day 88
- [ ] **学习内容**：Workloads - StatefulSet
- [ ] StatefulSet vs Deployment
- [ ] 有状态应用管理
- [ ] **练习**：部署一个有状态服务

### Day 89
- [ ] **学习内容**：Workloads - DaemonSet & Job
- [ ] DaemonSet 用法
- [ ] Job 和 CronJob
- [ ] **练习**：创建定时任务

### Day 90
- [ ] **学习内容**：Service
- [ ] Service 类型（ClusterIP/NodePort/LoadBalancer）
- [ ] 负载均衡
- [ ] **练习**：创建并访问 Service

### Day 91
- [ ] **学习内容**：Ingress
- [ ] Ingress 概念与配置
- [ ] Ingress Controller
- [ ] **练习**：配置 Ingress 访问应用

---

## Week 14：Kubernetes 进阶

### Day 92
- [ ] **学习内容**：ConfigMap 与 Secret
- [ ] 配置管理
- [ ] Secret 类型与使用
- [ ] **练习**：应用配置管理

### Day 93
- [ ] **学习内容**：存储
- [ ] PV/PVC
- [ ] StorageClass
- [ ] **练习**：存储挂载练习

### Day 94
- [ ] **学习内容**：RBAC
- [ ] Role/ClusterRole
- [ ] RoleBinding/ClusterRoleBinding
- [ ] **练习**：权限配置练习

### Day 95
- [ ] **学习内容**：调度器
- [ ] 调度策略
- [ ] 亲和性与反亲和性
- [ ] **练习**：高级调度配置

### Day 96
- [ ] **学习内容**：HPA 与扩缩容
- [ ] HorizontalPodAutoscaler
- [ ] 自动扩缩容配置
- [ ] **练习**：配置 HPA

### Day 97
- [ ] **学习内容**：Helm
- [ ] Helm 概念与使用
- [ ] Chart 结构
- [ ] **练习**：用 Helm 部署应用

### Day 98
- [ ] **实战项目**：搭建 K8s 集群
- [ ] 使用 kubeadm 或云厂商创建集群
- [ ] 部署一个生产级应用

### Day 99
- [ ] **K8s 阶段测试**
- [ ] 准备 CKA 考试知识点
- [ ] **自我评估**：K8s 掌握程度

---

# 📖 第五阶段：云计算 AWS + IaC（第 15-18 周）

## Week 15：AWS 基础

### Day 100
- [ ] **学习内容**：AWS 简介与账户
- [ ] AWS 全球基础设施
- [ ] 创建 AWS 账户
- [ ] IAM 用户与角色
- [ ] **练习**：创建 IAM 用户和角色

### Day 101
- [ ] **学习内容**：EC2 基础
- [ ] 实例类型与定价
- [ ] AMI 选择
- [ ] 安全组配置
- [ ] **练习**：启动第一个 EC2 实例

### Day 102
- [ ] **学习内容**：VPC 网络
- [ ] VPC 创建
- [ ] 子网规划（公有/私有）
- [ ] NAT Gateway/Instance
- [ ] **练习**：搭建 VPC 环境

### Day 103
- [ ] **学习内容**：S3 存储
- [ ] S3 桶创建与权限
- [ ] 存储类与生命周期
- [ ] **练习**：配置 S3 静态网站托管

### Day 104
- [ ] **学习内容**：RDS 数据库
- [ ] RDS 创建
- [ ] 多可用区
- [ ] 备份与恢复
- [ ] **练习**：创建 RDS 实例

### Day 105
- [ ] **学习内容**：ELB 负载均衡
- [ ] CLB/ALB/NLB
- [ ] 目标组配置
- [ ] **练习**：配置 Application Load Balancer

### Day 106
- [ ] **学习内容**：Auto Scaling
- [ ] 启动配置
- [ ] ASG 策略
- [ ] **练习**：配置 ASG

---

## Week 16：AWS 进阶

### Day 107
- [ ] **学习内容**：CloudWatch
- [ ] 指标与告警
- [ ] 日志收集
- [ ] **练习**：配置监控告警

### Day 108
- [ ] **学习内容**：Route 53 DNS
- [ ] DNS 托管
- [ ] 路由策略
- [ ] **练习**：配置域名解析

### Day 109
- [ ] **学习内容**：EKS 弹性 Kubernetes
- [ ] EKS 集群创建
- [ ] 节点组管理
- [ ] **练习**：创建 EKS 集群

### Day 110
- [ ] **学习内容**：AWS 安全
- [ ] IAM 策略与权限
- [ ] 安全最佳实践
- [ ] **练习**：权限审计

### Day 111
- [ ] **学习内容**：AWS 架构设计
- [ ] 高可用架构
- [ ] Well-Architected Framework
- [ ] **练习**：设计一个高可用架构

### Day 112
- [ ] **备考**：AWS SAA 认证
- [ ] 考试知识点梳理
- [ ] 模拟题练习

### Day 113
- [ ] **备考**：AWS SAA 认证
- [ ] 继续刷题
- [ ] 查漏补缺

### Day 114
- [ ] **自我评估**：AWS 知识掌握
- [ ] **目标**：开始准备 AWS SAA 认证考试

---

## Week 17：Terraform IaC

### Day 115
- [ ] **学习内容**：Terraform 简介
- [ ] Terraform vs CloudFormation
- [ ] 安装 Terraform
- [ ] **练习**：安装并运行 Terraform

### Day 116
- [ ] **学习内容**：Terraform 基础
- [ ] provider, resource, variable
- [ ] terraform init/plan/apply/destroy
- [ ] **练习**：用 Terraform 创建 EC2

### Day 117
- [ ] **学习内容**：Terraform 进阶
- [ ] output, data source
- [ ] 状态管理
- [ ] **练习**：模块化配置

### Day 118
- [ ] **学习内容**：Terraform 工作流
- [ ] workspace
- [ ] 远程状态
- [ ] **练习**：配置远程状态

### Day 119
- [ ] **实战项目**：VPC 模块化
- [ ] 编写可复用的 VPC 模块

### Day 120
- [ ] **实战项目**：EKS 基础设施
- [ ] 用 Terraform 搭建完整 EKS 集群

---

## Week 18：Ansible 配置管理

### Day 121
- [ ] **学习内容**：Ansible 简介
- [ ] Ansible vs Chef/Puppet
- [ ] 安装 Ansible
- [ ] **练习**：安装 Ansible

### Day 122
- [ ] **学习内容**：Ansible 基础
- [ ] Inventory
- [ ] Ad-hoc 命令
- [ ] Playbook 基础
- [ ] **练习**：编写第一个 Playbook

### Day 123
- [ ] **学习内容**：Ansible 模块
- [ ] 常用模块（yum, apt, copy, file, service）
- [ ] **练习**：批量配置管理

### Day 124
- [ ] **学习内容**：Ansible Roles
- [ ] Role 结构
- [ ] Galaxy 市场
- [ ] **练习**：编写一个 Role

### Day 125
- [ ] **学习内容**：Ansible 进阶
- [ ] 模板（Jinja2）
- [ ] 变量与 Facts
- [ ] **练习**：动态配置

### Day 126
- [ ] **实战项目**：自动化部署
- [ ] 编写完整的自动化部署 Playbook

### Day 127
- [ ] **IaC 阶段总结**
- [ ] 综合练习：Terraform + Ansible 自动化

---

# 📖 第六阶段：可观测性（第 19-20 周）

## Week 19：监控体系

### Day 128
- [ ] **学习内容**：可观测性基础
- [ ] 监控黄金指标（USE/RED）
- [ ] SLO/SLI/SLA 概念
- [ ] **练习**：定义服务的 SLO

### Day 129
- [ ] **学习内容**：Prometheus 基础
- [ ] Prometheus 架构
- [ ] 安装与配置
- [ ] **练习**：安装 Prometheus

### Day 130
- [ ] **学习内容**：Prometheus 进阶
- [ ] PromQL 查询
- [ ] 指标类型（Counter/Gauge/Histogram/Summary）
- [ ] **练习**：编写 PromQL 查询

### Day 131
- [ ] **学习内容**：Grafana 可视化
- [ ] 安装 Grafana
- [ ] 数据源配置
- [ ] 仪表盘创建
- [ ] **练习**：创建监控仪表盘

### Day 132
- [ ] **学习内容**：Kubernetes 监控
- [ ] kube-state-metrics
- [ ] node-exporter
- [ ] **练习**：K8s 集群监控

### Day 133
- [ ] **学习内容**：Alertmanager
- [ ] 告警规则配置
- [ ] 告警静默
- [ ] **练习**：配置告警通知

### Day 134
- [ ] **实战项目**：搭建完整监控体系
- [ ] Prometheus + Grafana + Alertmanager

---

## Week 20：日志与链路追踪

### Day 135
- [ ] **学习内容**：日志收集基础
- [ ] ELK 架构
- [ ] Elasticsearch 概念
- [ ] **练习**：安装 Elasticsearch

### Day 136
- [ ] **学习内容**：Logstash/Fluentd
- [ ] 日志采集配置
- [ ] 过滤器解析
- [ ] **练习**：配置日志收集

### Day 137
- [ ] **学习内容**：Kibana
- [ ] 日志搜索
- [ ] 可视化
- [ ] **练习**：创建日志仪表盘

### Day 138
- [ ] **学习内容**：Loki 日志系统
- [ ] Loki vs ELK
- [ ] 安装与配置
- [ ] **练习**：搭建 Loki

### Day 139
- [ ] **学习内容**：链路追踪
- [ ] 链路追踪概念
- [ ] Jaeger 架构
- [ ] **练习**：安装 Jaeger

### Day 140
- [ ] **学习内容**：APM 集成
- [ ] 应用埋点
- [ ] 分布式追踪
- [ ] **练习**：应用集成追踪

### Day 141
- [ ] **可观测性阶段总结**
- [ ] 搭建完整的可观测性平台
- [ ] **自我评估**：是否掌握三大支柱

---

# 📖 第七阶段：CI/CD 与自动化（第 21-22 周）

## Week 21：CI/CD 基础

### Day 142
- [ ] **学习内容**：CI/CD 概念
- [ ] 持续集成/持续交付/持续部署
- [ ] GitOps 理念
- [ ] **练习**：理解 CI/CD 流程

### Day 143
- [ ] **学习内容**：GitHub Actions
- [ ] Workflow 语法
- [ ] Marketplace
- [ ] **练习**：编写第一个 CI 流程

### Day 144
- [ ] **学习内容**：GitLab CI
- [ ] .gitlab-ci.yml
- [ ] Runner 配置
- [ ] **练习**：配置 GitLab CI

### Day 145
- [ ] **学习内容**：Jenkins
- [ ] Jenkins 安装
- [ ] Pipeline 语法
- [ ] **练习**：创建 Jenkins Pipeline

### Day 146
- [ ] **学习内容**：构建工具
- [ ] Maven/Gradle (Java)
- [ ] npm/yarn (Node)
- [ ] **练习**：集成构建步骤

### Day 147
- [ ] **学习内容**：镜像构建与推送
- [ ] Docker build in CI
- [ ] 镜像仓库集成
- [ ] **练习**：CI 中构建并推送镜像

### Day 148
- [ ] **实战项目**：完整 CI/CD 流程
- [ ] 代码提交 → 构建 → 测试 → 部署

---

## Week 22：DevOps 高级实践

### Day 149
- [ ] **学习内容**：ArgoCD
- [ ] GitOps 实践
- [ ] Application CRD
- [ ] **练习**：部署 ArgoCD

### Day 150
- [ ] **学习内容**：部署策略
- [ ] 滚动部署
- [ ] Blue-Green 部署
- [ ] Canary 部署
- [ ] **练习**：配置金丝雀发布

### Day 151
- [ ] **学习内容**：密钥管理
- [ ] Vault 基础
- [ ] Sealed Secrets
- [ ] **练习**：集成 Vault

### Day 152
- [ ] **学习内容**：环境管理
- [ ] 多环境配置
- [ ] 环境隔离策略
- [ ] **练习**：多环境部署

### Day 153
- [ ] **学习内容**：Chaos Engineering
- [ ] Chaos Monkey
- [ ] Litmus
- [ ] **练习**：简单的混沌实验

### Day 154
- [ ] **学习内容**：安全扫描
- [ ] SAST/DAST
- [ ] Trivy 镜像扫描
- [ ] **练习**：集成安全扫描

### Day 155
- [ ] **阶段总结**
- [ ] 完整的 GitOps 部署流水线

---

# 📖 第八阶段：SRE 实战与面试（第 23-24 周）

## Week 23：SRE 核心实践

### Day 156
- [ ] **学习内容**：On-Call 实践
- [ ] 告警分级
- [ ] 应急响应流程
- [ ] **练习**：设计 On-Call 流程

### Day 157
- [ ] **学习内容**：事故管理
- [ ] 事故分级与升级
- [ ] 事后复盘（RCA）
- [ ] **练习**：学习写 RCA 报告

### Day 158
- [ ] **学习内容**：SLO 与错误预算
- [ ] SLO 设定方法
- [ ] 错误预算管理
- [ ] **练习**：为一个服务设定 SLO

### Day 159
- [ ] **学习内容**：容量规划
- [ ] 性能测试
- [ ] 扩缩容策略
- [ ] **练习**：容量规划练习

### Day 160
- [ ] **学习内容**：灾备与恢复
- [ ] RPO/RTO
- [ ] 灾备方案
- [ ] **练习**：设计灾备方案

### Day 161
- [ ] **学习内容**：成本优化
- [ ] 云成本分析
- [ ] 资源优化
- [ ] **练习**：成本优化实践

### Day 162
- [ ] **实战项目**：综合 SRE 实践
- [ ] 设计并实施一个完整的 SRE 方案

---

## Week 24：面试准备

### Day 163
- [ ] **学习内容**：简历优化
- [ ] SRE 简历要点
- [ ] 项目经验描述
- [ ] **练习**：撰写简历

### Day 164
- [ ] **学习内容**：面试题 - Linux
- [ ] 常见面试题
- [ ] 场景题练习
- [ ] **练习**：模拟面试

### Day 165
- [ ] **学习内容**：面试题 - 网络
- [ ] 网络常见问题
- [ ] 排错思路
- [ ] **练习**：模拟面试

### Day 166
- [ ] **学习内容**：面试题 - K8s
- [ ] K8s 面试题
- [ ] 架构设计题
- [ ] **练习**：模拟面试

### Day 167
- [ ] **学习内容**：面试题 - 运维
- [ ] 脚本题
- [ ] 系统设计
- [ ] **练习**：模拟面试

### Day 168
- [ ] **学习内容**：认证准备
- [ ] CKA 考试技巧
- [ ] AWS SAA 冲刺

### Day 169
- [ ] **学习内容**：软技能
- [ ] 沟通技巧
- [ ] 团队协作
- [ ] **练习**：STAR 法则

### Day 170
- [ ] **学习内容**：offer 谈判
- [ ] 薪资谈判
- [ ] 职业规划
- [ ] **新起点**：开始投递简历

---

## 📊 里程碑检查点

| 时间 | 里程碑 |
|------|--------|
| 第 4 周末 | ✅ 完成 Linux 基础 |
| 第 6 周末 | ✅ 网络基础扎实 |
| 第 10 周末 | ✅ Python/Go 熟练 |
| 第 14 周末 | ✅ CKA 认证到手 |
| 第 18 周末 | ✅ AWS SAA + Terraform |
| 第 20 周末 | ✅ 可观测性平台搭建 |
| 第 22 周末 | ✅ 完整 CI/CD 流水线 |
| 第 24 周末 | 🎉 入门级 SRE！ |

---

## 📚 推荐学习资源

### 书籍
- 《SRE：Google 运维解密》
- 《Linux 鸟哥的私房菜》
- 《Kubernetes 权威指南》
- 《深入理解 Prometheus》
- 《Terraform 实战》

### 在线课程
- Coursera: Google IT Support Certificate
- Udemy: AWS Certified Solutions Architect
- Linux Foundation: CKA 认证课程
- Katacoda: 交互式 K8s 学习

### 练习平台
- [KodeKloud](https://kodekloud.com) - K8s 实战练习
- [Play with Docker](https://play.docker.com) - Docker 练习
- [Play with Kubernetes](https://playwithkubernetes.com) - K8s 集群
- [LeetCode](https://leetcode.com) - 算法练习
- [Grafana Play](https://play.grafana.org) - 可视化示例

### 社区与博客
- Kubernetes 官方文档
- Medium SRE 专栏
- 云原生社区 CNCF
- 极客时间 SRE 专栏

---

## 💪 成功秘诀

1. **每天坚持**：哪怕只有 1 小时，保持连续性
2. **动手实践**：只看不动手等于没学
3. **记笔记**：好记性不如烂笔头
4. **做项目**：把知识点串起来
5. **找同伴**：加入学习群互相督促
6. **教别人**：能讲清楚才是真的懂

---

> 🚀 *坚持 6 个月，你一定能成为合格的 SRE 工程师！加油！*
