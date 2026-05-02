# Day 105: AWS 简介与账户管理

> 📅 日期：2026-05-04
> 📖 学习主题：AWS 简介与账户管理
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 AWS 的核心服务
- 掌握账户安全和 IAM 基础
- 了解 AWS 全球基础设施

---

## 📖 AWS 核心服务

### 1. 计算

| 服务 | 说明 |
|------|------|
| EC2 | 虚拟机 |
| Lambda | 无服务器函数 |
| ECS/EKS | 容器服务 |
| Elastic Beanstalk | 平台即服务 |

### 2. 存储

| 服务 | 说明 |
|------|------|
| S3 | 对象存储 |
| EBS | 块存储 |
| EFS | 文件存储 |
| Glacier | 归档存储 |

### 3. 数据库

| 服务 | 说明 |
|------|------|
| RDS | 关系型数据库 |
| DynamoDB | NoSQL |
| ElastiCache | 缓存 |
| Redshift | 数据仓库 |

### 4. 网络

| 服务 | 说明 |
|------|------|
| VPC | 虚拟私有云 |
| Route 53 | DNS |
| CloudFront | CDN |
| API Gateway | API 管理 |

### 5. IAM 基础

```
IAM（Identity and Access Management）：
- Users：用户
- Groups：用户组
- Roles：角色（服务或临时访问）
- Policies：权限策略

最佳实践：
- 遵循最小权限原则
- 启用 MFA
- 使用角色而非访问密钥
- 定期轮换密钥
```

### 6. CLI 配置

```bash
aws configure
aws sts get-caller-identity
aws ec2 describe-instances
```

---

## 📚 扩展阅读

- [AWS 文档](https://docs.aws.amazon.com/)
- [AWS 免费套餐](https://aws.amazon.com/free/)
