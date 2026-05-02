# Day 110: ELB 负载均衡

> 📅 日期：2026-05-04
> 📖 学习主题：ELB 负载均衡
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 ALB/NLB/GLB 的区别
- 能配置 Application Load Balancer

---

## 📖 ELB 类型

| 类型 | 层级 | 用途 |
|------|------|------|
| ALB | L7 (HTTP/HTTPS) | Web 应用 |
| NLB | L4 (TCP/UDP) | 高性能、静态 IP |
| GWLB | L3 | 第三方虚拟设备 |
| Classic | L4/L7 | 旧版 |

### ALB 配置

```bash
aws elbv2 create-load-balancer --name my-alb --subnets subnet-1 subnet-2
aws elbv2 create-target-group --name my-tg --protocol HTTP --port 80 --vpc-id vpc-xxx
aws elbv2 create-listener --load-balancer-arn arn:xxx --protocol HTTP --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:xxx
```

---

## 📚 扩展阅读

- [ELB 文档](https://docs.aws.amazon.com/elasticloadbalancing/)
