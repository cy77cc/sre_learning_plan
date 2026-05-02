# Day 130: Ansible 进阶

> 📅 日期：2026-05-04
> 📖 学习主题：Ansible 进阶
> ⏰ 计划学习时间：2-3 小时

---

## 📖 进阶

### Variables

```yaml
vars:
  http_port: 80
  app_name: myapp
```

### Handlers

```yaml
handlers:
  - name: restart nginx
    service:
      name: nginx
      state: restarted
```

### Conditionals

```yaml
tasks:
  - name: Install for Debian
    apt:
      name: nginx
    when: ansible_os_family == "Debian"
```

### Loops

```yaml
tasks:
  - name: Create users
    user:
      name: "{{ item }}"
    loop:
      - alice
      - bob
```

---

## 📚 扩展阅读

- [Ansible 进阶](https://docs.ansible.com/ansible/latest/user_guide/)
