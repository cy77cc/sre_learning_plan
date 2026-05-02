# Day 129: Ansible Roles

> 📅 日期：2026-05-04
> 📖 学习主题：Ansible Roles
> ⏰ 计划学习时间：2-3 小时

---

## 📖 Roles

```
roles/
  nginx/
    tasks/
      main.yml
    handlers/
      main.yml
    templates/
      nginx.conf.j2
    vars/
      main.yml
    defaults/
      main.yml
    files/
```

### 使用

```yaml
- hosts: web
  roles:
    - nginx
```

---

## 📚 扩展阅读

- [Ansible Roles](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
