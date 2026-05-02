# Day 125: 实战项目：EKS 基础设施

> 📅 日期：2026-05-04
> 📖 学习主题：实战项目：EKS 基础设施
> ⏰ 计划学习时间：2-3 小时

---

## 🏗️ 项目

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0.0"

  cluster_name    = "my-cluster"
  cluster_version = "1.27"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    workers = {
      min_size     = 2
      max_size     = 5
      desired_size = 3
      instance_types = ["t3.medium"]
    }
  }
}
```

---

## 📚 扩展阅读

- [EKS 模块](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws)
