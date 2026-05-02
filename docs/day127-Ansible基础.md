# Day 127: Ansible 基础

> 📅 日期：2026-05-04
> 📖 学习主题：Ansible 基础
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Playbook 编写
- 能运行 Ad-Hoc 命令

---

## 📖 Playbook

```yaml
- name: Install Nginx
  hosts: web
  become: yes
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present

    - name: Start nginx
      service:
        name: nginx
        state: started
        enabled: yes
```

### Ad-Hoc

```bash
ansible web -m ping
ansible web -m shell -a "uptime"
ansible all -m setup
```

---

## 📚 扩展阅读

- [Ansible Playbook](https://docs.ansible.com/ansible/latest/playbook_guide/)
