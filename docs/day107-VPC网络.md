# Day 107: VPC 网络

> 📅 日期：2026-05-04
> 📖 学习主题：VPC 网络
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 VPC 架构
- 掌握子网、路由表、NAT 网关
- 能设计高可用网络架构

---

## 📖 VPC 组件

### 1. 核心组件

| 组件 | 说明 |
|------|------|
| VPC | 虚拟网络 |
| 子网 | IP 地址范围 |
| 路由表 | 流量路由规则 |
| Internet Gateway | 公网出入口 |
| NAT Gateway | 私网出公网 |
| 安全组 | 实例级防火墙 |
| NACL | 子网级防火墙 |

### 2. 创建 VPC

```bash
aws ec2 create-vpc --cidr-block 10.0.0.0/16
aws ec2 create-subnet --vpc-id vpc-xxxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
```

### 3. 架构

```
VPC (10.0.0.0/16)
├── Public Subnet (10.0.1.0/24)
│   ├── NAT Gateway
│   └── Load Balancer
├── Private Subnet (10.0.2.0/24)
│   └── Application Servers
└── Private Subnet (10.0.3.0/24)
    └── Database
```

---

## 📚 扩展阅读

- [VPC 文档](https://docs.aws.amazon.com/vpc/)
