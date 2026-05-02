# Day 109: RDS 数据库

> 📅 日期：2026-05-04
> 📖 学习主题：RDS 数据库
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 RDS 的核心功能
- 能创建和管理 RDS 实例

---

## 📖 RDS

### 1. 支持的引擎

- MySQL
- PostgreSQL
- MariaDB
- Oracle
- SQL Server
- Aurora

### 2. 创建 RDS

```bash
aws rds create-db-instance \
    --db-instance-identifier mydb \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --master-username admin \
    --master-user-password secret123 \
    --allocated-storage 20
```

### 3. 特性

- 自动备份
- 多 AZ 部署
- 读副本
- 自动扩展存储

---

## 📚 扩展阅读

- [RDS 文档](https://docs.aws.amazon.com/rds/)
