# Day 121: Terraform 基础

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 基础
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Terraform 基本语法
- 能编写第一个 Terraform 配置

---

## 📖 基础语法

```hcl
# provider.tf
provider "aws" {
  region = "us-east-1"
}

# main.tf
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name = "web-server"
  }
}

resource "aws_security_group" "allow_ssh" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 命令

```bash
terraform init
terraform plan
terraform apply
terraform destroy
```

---

## 📚 扩展阅读

- [Terraform 教程](https://developer.hashicorp.com/terraform/tutorials)
