# Day 120: Terraform 简介

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 简介
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 IaC 和 Terraform
- 能安装和配置 Terraform

---

## 📖 Terraform

### IaC 优势

```
优势：
- 版本控制基础设施
- 可重复部署
- 文档化
- 减少人为错误
```

### 安装

```bash
# Linux
curl -fsSL https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip -o terraform.zip
unzip terraform.zip
sudo mv terraform /usr/local/bin/
```

### 工作流

```
write → plan → apply → destroy
```

---

## 📚 扩展阅读

- [Terraform 文档](https://developer.hashicorp.com/terraform)
