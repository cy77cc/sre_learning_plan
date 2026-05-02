# Day 122: Terraform 进阶

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 进阶
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握变量、输出、模块

---

## 📖 进阶特性

### 变量

```hcl
variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "env" {
  type    = string
  default = "dev"
}
```

### 输出

```hcl
output "instance_ip" {
  value = aws_instance.web.public_ip
}
```

### 模块

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  cidr = "10.0.0.0/16"
}
```

---

## 📚 扩展阅读

- [Terraform 模块](https://developer.hashicorp.com/terraform/language/modules)
