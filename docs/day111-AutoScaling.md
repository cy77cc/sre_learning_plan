# Day 111: Auto Scaling

> 📅 日期：2026-05-04
> 📖 学习主题：Auto Scaling
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Auto Scaling Group
- 能配置基于指标的自动扩缩容

---

## 📖 Auto Scaling

### 组件

```
Launch Template → 定义实例配置
Auto Scaling Group → 管理实例组
Scaling Policy → 扩缩容规则
```

### 配置

```bash
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name my-asg \
    --launch-template LaunchTemplateName=my-template \
    --min-size 2 --max-size 10 --desired-capacity 3 \
    --vpc-zone-identifier "subnet-1,subnet-2"
```

---

## 📚 扩展阅读

- [Auto Scaling 文档](https://docs.aws.amazon.com/autoscaling/)
