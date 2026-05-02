# Day 132: IaC 阶段总结

> 📅 日期：2026-05-04
> 📖 学习主题：IaC 阶段总结：Terraform + Ansible 综合实践
> ⏰ 计划学习时间：2-3 小时

---

## 📖 总结

### Terraform vs Ansible

| 特性 | Terraform | Ansible |
|------|-----------|---------|
| 用途 | 基础设施编排 | 配置管理 |
| 语言 | HCL | YAML |
| 执行 | 声明式 | 命令式 |
| 状态 | 有状态管理 | 无状态 |

### 工作流

```
Terraform → 创建基础设施（VPC、EC2、RDS）
    ↓
Ansible → 配置服务器（安装软件、部署应用）
```

---

## 📚 扩展阅读

- [Terraform + Ansible 集成](https://developer.hashicorp.com/terraform/tutorials/provision/ansible)
