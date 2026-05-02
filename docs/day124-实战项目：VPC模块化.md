# Day 124: 实战项目：VPC 模块化

> 📅 日期：2026-05-04
> 📖 学习主题：实战项目：VPC 模块化
> ⏰ 计划学习时间：2-3 小时

---

## 🏗️ 项目

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "my-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}
```

---

## 📚 扩展阅读

- [VPC 模块](https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws)
