# Day 116: AWS 高可用架构

> 📅 日期：2026-05-04
> 📖 学习主题：AWS 高可用架构
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解多 AZ 部署
- 能设计高可用架构

---

## 📖 高可用模式

```
最佳实践：
- 多 AZ 部署
- Auto Scaling
- ELB 负载均衡
- RDS Multi-AZ
- S3 跨区域复制

参考架构：
  Route 53 → CloudFront → ALB → Auto Scaling Group (多 AZ)
                                    ↓
                              RDS Multi-AZ
                                    ↓
                              ElastiCache (Cluster Mode)
```

---

## 📚 扩展阅读

- [AWS 架构中心](https://aws.amazon.com/architecture/)
