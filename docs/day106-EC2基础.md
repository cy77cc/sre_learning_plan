# Day 106: EC2 基础

> 📅 日期：2026-05-04
> 📖 学习主题：EC2 基础
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 EC2 实例类型
- 能创建和管理 EC2 实例
- 掌握安全组配置

---

## 📖 EC2

### 1. 实例类型

| 类型 | 用途 |
|------|------|
| t3/t4g | 通用，突发性能 |
| m5/m6g | 通用，均衡 |
| c5/c6g | 计算优化 |
| r5/r6g | 内存优化 |
| i3 | 存储优化 |

### 2. 创建实例

```bash
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.micro \
    --key-name my-key \
    --security-group-ids sg-xxxx \
    --subnet-id subnet-xxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=my-server}]'
```

### 3. 安全组

```bash
# 入站规则
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxx \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0
```

### 4. 常用操作

```bash
aws ec2 describe-instances
aws ec2 start-instances --instance-ids i-xxxx
aws ec2 stop-instances --instance-ids i-xxxx
aws ec2 terminate-instances --instance-ids i-xxxx
```

---

## 📚 扩展阅读

- [EC2 文档](https://docs.aws.amazon.com/ec2/)
