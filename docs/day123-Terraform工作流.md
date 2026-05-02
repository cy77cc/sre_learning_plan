# Day 123: Terraform 工作流

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 工作流
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握状态管理
- 理解 workspace

---

## 📖 状态管理

```bash
terraform state list
terraform state show aws_instance.web
terraform state mv aws_instance.web aws_instance.new_web
```

### Remote State

```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}
```

### Workspace

```bash
terraform workspace new dev
terraform workspace new prod
terraform workspace select dev
```

---

## 📚 扩展阅读

- [Terraform 状态](https://developer.hashicorp.com/terraform/language/state)
