# Day 126: Ansible 简介

> 📅 日期：2026-05-04
> 📖 学习主题：Ansible 简介
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Ansible 的工作原理
- 能安装和配置 Ansible

---

## 📖 Ansible

### 特点

- 无代理（SSH）
- 幂等性
- YAML 配置

### 安装

```bash
pip install ansible
ansible --version
```

### Inventory

```ini
[web]
web01 ansible_host=10.0.1.10
web02 ansible_host=10.0.1.11

[db]
db01 ansible_host=10.0.2.10
```

---

## 📚 扩展阅读

- [Ansible 文档](https://docs.ansible.com/)
