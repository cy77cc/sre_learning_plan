# Day 129: Ansible Roles

> 📅 日期：2026-05-07
> 📖 学习主题：Role 目录结构、依赖管理、Galaxy、自定义 Role、服务器初始化 Role、监控部署 Role
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 128（Ansible 常用模块）

## 🎯 学习目标

- 理解 Role 的目录结构和各目录的用途
- 掌握 Role 的创建、使用和依赖管理
- 能使用 Ansible Galaxy 搜索和安装 Role
- 编写服务器初始化 Role 和监控部署 Role
- 掌握 Role 的最佳实践

---

## 📖 核心知识点

### 1. Role 概述与目录结构

#### 1.1 什么是 Role

Role 是 Ansible 中组织 Playbook 的最佳方式。它将任务、变量、文件、模板等按功能拆分为独立的、可复用的组件。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Role 的价值                                    │
│                                                                 │
│  没有 Role（单文件 Playbook）：                                  │
│  ┌─────────────────────────────────────────────┐               │
│  │ site.yml (2000+ 行)                         │               │
│  │ - 所有任务混在一起                           │               │
│  │ - 难以复用                                   │               │
│  │ - 难以测试                                   │               │
│  │ - 难以维护                                   │               │
│  └─────────────────────────────────────────────┘               │
│                                                                 │
│  使用 Role（模块化组织）：                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ common/  │ │ nginx/   │ │ app/     │ │ monitor/ │          │
│  │          │ │          │ │          │ │          │          │
│  │ 基础配置 │ │ Web 服务 │ │ 应用部署 │ │ 监控部署 │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│       ↑            ↑            ↑            ↑                 │
│       └────────────┴────────────┴────────────┘                 │
│                    site.yml                                     │
│              （组合各 Role 的入口）                              │
│                                                                 │
│  优势：                                                         │
│  ✓ 模块化 — 每个 Role 职责单一                                  │
│  ✓ 可复用 — 不同项目/环境共享 Role                              │
│  ✓ 可测试 — 每个 Role 独立测试                                  │
│  ✓ 社区 — Galaxy 上有数千个现成 Role                            │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 Role 目录结构

```
roles/
└── nginx/                          # Role 名称
    ├── tasks/                      # 任务目录（必须）
    │   └── main.yml               # 主任务入口
    │   ├── install.yml            # 安装任务（可选，被 include）
    │   ├── configure.yml          # 配置任务
    │   └── service.yml            # 服务管理任务
    │
    ├── handlers/                   # 处理程序目录
    │   └── main.yml               # 处理程序定义
    │
    ├── templates/                  # Jinja2 模板目录
    │   ├── nginx.conf.j2
    │   └── vhost.conf.j2
    │
    ├── files/                      # 静态文件目录
    │   ├── ssl/
    │   │   ├── cert.pem
    │   │   └── key.pem
    │   └── custom_errors/
    │       └── 50x.html
    │
    ├── vars/                       # 变量目录（高优先级）
    │   └── main.yml               # Role 变量
    │
    ├── defaults/                   # 默认变量目录（低优先级）
    │   └── main.yml               # 默认变量（可被覆盖）
    │
    ├── meta/                       # 元数据目录
    │   └── main.yml               # Role 依赖、作者信息
    │
    ├── tests/                      # 测试目录
    │   ├── inventory
    │   └── test.yml
    │
    └── README.md                   # Role 说明文档
```

#### 1.3 各目录详解

```
┌─────────────────────────────────────────────────────────────────┐
│                    Role 目录详解                                  │
├──────────────┬──────────────────────────────────────────────────┤
│   目录       │   说明                                           │
├──────────────┼──────────────────────────────────────────────────┤
│ tasks/       │ 包含 Role 要执行的任务列表                        │
│ (必须)       │ main.yml 是入口文件                              │
│              │ 可以使用 include_tasks 拆分                      │
├──────────────┼──────────────────────────────────────────────────┤
│ handlers/    │ 包含被 notify 触发的处理程序                      │
│              │ main.yml 是入口文件                              │
│              │ 通常用于重启服务、重载配置                        │
├──────────────┼──────────────────────────────────────────────────┤
│ templates/   │ 包含 Jinja2 模板文件                             │
│              │ 使用 template 模块时自动查找                     │
│              │ 文件名通常以 .j2 结尾                            │
├──────────────┼──────────────────────────────────────────────────┤
│ files/       │ 包含静态文件                                     │
│              │ 使用 copy/file 模块时自动查找                    │
│              │ 不需要模板渲染的文件放这里                        │
├──────────────┼──────────────────────────────────────────────────┤
│ vars/        │ 包含 Role 变量（高优先级）                        │
│              │ 通常不应被调用者覆盖                              │
│              │ 用于 Role 内部使用的固定值                        │
├──────────────┼──────────────────────────────────────────────────┤
│ defaults/    │ 包含默认变量（低优先级）                          │
│              │ 可被调用者轻松覆盖                                │
│              │ 提供合理的默认值                                  │
├──────────────┼──────────────────────────────────────────────────┤
│ meta/        │ 包含 Role 元数据                                 │
│              │ 定义依赖关系                                     │
│              │ 定义作者、许可证、支持平台                        │
├──────────────┼──────────────────────────────────────────────────┤
│ tests/       │ 包含测试文件                                     │
│              │ 用于 Molecule 或手动测试                          │
└──────────────┴──────────────────────────────────────────────────┘
```

### 2. 创建第一个 Role

#### 2.1 使用 ansible-galaxy 初始化

```bash
# 创建 Role 骨架
ansible-galaxy role init roles/nginx

# 查看生成的目录结构
tree roles/nginx/
# roles/nginx/
# ├── defaults
# │   └── main.yml
# ├── files
# ├── handlers
# │   └── main.yml
# ├── meta
# │   └── main.yml
# ├── README.md
# ├── tasks
# │   └── main.yml
# ├── templates
# ├── tests
# │   ├── inventory
# │   └── test.yml
# └── vars
#     └── main.yml
```

#### 2.2 完整的 Nginx Role 示例

```yaml
# roles/nginx/defaults/main.yml
---
# 默认变量（可被调用者覆盖）
nginx_port: 80
nginx_user: nginx
nginx_worker_processes: "{{ ansible_processor_vcpus }}"
nginx_worker_connections: 1024
nginx_keepalive_timeout: 65
nginx_gzip_enabled: true
nginx_client_max_body_size: "50m"
nginx_server_name: "_"
nginx_ssl_enabled: false
nginx_ssl_certificate: ""
nginx_ssl_certificate_key: ""
nginx_log_dir: /var/log/nginx
nginx_conf_dir: /etc/nginx
nginx_extra_directives: []
```

```yaml
# roles/nginx/vars/main.yml
---
# Role 内部变量（高优先级，不应被覆盖）
nginx_package_name: nginx
nginx_service_name: nginx
nginx_config_file: "{{ nginx_conf_dir }}/nginx.conf"
nginx_default_vhost: "{{ nginx_conf_dir }}/conf.d/default.conf"
```

```yaml
# roles/nginx/tasks/main.yml
---
# 主任务入口
- name: Include OS-specific variables
  include_vars: "{{ ansible_os_family }}.yml"
  tags: [always]

- name: Install Nginx
  include_tasks: install.yml
  tags: [install, packages]

- name: Configure Nginx
  include_tasks: configure.yml
  tags: [config]

- name: Manage Nginx service
  include_tasks: service.yml
  tags: [services]
```

```yaml
# roles/nginx/tasks/install.yml
---
- name: Install Nginx package
  package:
    name: "{{ nginx_package_name }}"
    state: present
  notify: Restart nginx

- name: Ensure Nginx log directory exists
  file:
    path: "{{ nginx_log_dir }}"
    state: directory
    owner: "{{ nginx_user }}"
    group: "{{ nginx_user }}"
    mode: "0755"
```

```yaml
# roles/nginx/tasks/configure.yml
---
- name: Deploy main Nginx configuration
  template:
    src: nginx.conf.j2
    dest: "{{ nginx_config_file }}"
    owner: root
    group: root
    mode: "0644"
    validate: "nginx -t -c %s"
  notify: Reload nginx

- name: Remove default virtual host
  file:
    path: "{{ nginx_default_vhost }}"
    state: absent
  notify: Reload nginx

- name: Deploy virtual host configuration
  template:
    src: vhost.conf.j2
    dest: "{{ nginx_conf_dir }}/conf.d/{{ item.name }}.conf"
    owner: root
    group: root
    mode: "0644"
    validate: "nginx -t -c {{ nginx_config_file }}"
  loop: "{{ nginx_vhosts | default([]) }}"
  notify: Reload nginx
```

```yaml
# roles/nginx/tasks/service.yml
---
- name: Ensure Nginx is started and enabled
  service:
    name: "{{ nginx_service_name }}"
    state: started
    enabled: yes

- name: Check Nginx is responding
  uri:
    url: "http://localhost:{{ nginx_port }}/"
    method: GET
    status_code: 200
    timeout: 5
  register: nginx_health
  retries: 3
  delay: 2
  until: nginx_health.status == 200
  ignore_errors: yes
```

```yaml
# roles/nginx/handlers/main.yml
---
- name: Restart nginx
  service:
    name: "{{ nginx_service_name }}"
    state: restarted

- name: Reload nginx
  service:
    name: "{{ nginx_service_name }}"
    state: reloaded
```

```jinja2
{# roles/nginx/templates/nginx.conf.j2 #}
# Managed by Ansible - DO NOT EDIT MANUALLY
user {{ nginx_user }};
worker_processes {{ nginx_worker_processes }};
error_log {{ nginx_log_dir }}/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections {{ nginx_worker_connections }};
    use epoll;
    multi_accept on;
}

http {
    include       {{ nginx_conf_dir }}/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log {{ nginx_log_dir }}/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout {{ nginx_keepalive_timeout }};
    types_hash_max_size 2048;
    client_max_body_size {{ nginx_client_max_body_size }};

{% if nginx_gzip_enabled %}
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
{% endif %}

{% for directive in nginx_extra_directives %}
    {{ directive }}
{% endfor %}

    include {{ nginx_conf_dir }}/conf.d/*.conf;
}
```

```yaml
# roles/nginx/meta/main.yml
---
galaxy_info:
  role_name: nginx
  author: SRE Team
  description: Install and configure Nginx web server
  license: MIT
  min_ansible_version: "2.14"
  platforms:
    - name: EL
      versions:
        - "8"
        - "9"
    - name: Ubuntu
      versions:
        - focal
        - jammy
    - name: Debian
      versions:
        - bullseye
        - bookworm
  galaxy_tags:
    - web
    - nginx
    - http
    - server

dependencies: []
# 如果有依赖，这样定义：
# dependencies:
#   - role: common
#   - role: firewall
#     vars:
#       firewall_allowed_ports:
#         - 80
#         - 443
```

### 3. 使用 Role

#### 3.1 在 Playbook 中引用 Role

```yaml
# site.yml
---
# 方式 1：简单引用
- name: Configure web servers
  hosts: webservers
  become: yes
  roles:
    - common
    - nginx
    - app

# 方式 2：带参数引用
- name: Configure web servers
  hosts: webservers
  become: yes
  roles:
    - role: common
      tags: [common]
    - role: nginx
      vars:
        nginx_port: 80
        nginx_server_name: "example.com"
        nginx_ssl_enabled: true
      tags: [nginx]
    - role: app
      vars:
        app_version: "2.1.0"
      tags: [app]

# 方式 3：使用 roles 段 + 条件
- name: Configure servers
  hosts: all
  become: yes
  roles:
    - role: common
    - role: nginx
      when: "'webservers' in group_names"
    - role: postgresql
      when: "'dbservers' in group_names"

# 方式 4：使用 include_role（动态引用）
- name: Configure servers
  hosts: all
  become: yes
  tasks:
    - name: Include common role
      include_role:
        name: common

    - name: Include nginx role for web servers
      include_role:
        name: nginx
      when: "'webservers' in group_names"
      vars:
        nginx_port: 80

    - name: Include app role
      include_role:
        name: app
      vars:
        app_version: "{{ app_version }}"
```

#### 3.2 import_role vs include_role

```
┌─────────────────────────────────────────────────────────────────┐
│           import_role vs include_role 对比                       │
├──────────────────┬──────────────────────────────────────────────┤
│   特性           │   import_role          include_role          │
├──────────────────┼──────────────────────────────────────────────┤
│   加载时机       │   静态（解析时）       动态（运行时）          │
│   标签继承       │   继承父级标签         不继承                  │
│   条件判断       │   支持（应用到所有）   支持（每次执行）        │
│   循环           │   不支持               支持                   │
│   性能           │   更快（预解析）       稍慢（动态加载）        │
│   适用场景       │   固定引用             条件引用/循环引用        │
└──────────────────┴──────────────────────────────────────────────┘
```

### 4. Role 依赖管理

```yaml
# roles/app/meta/main.yml
---
galaxy_info:
  role_name: app
  author: SRE Team
  description: Deploy application
  license: MIT
  min_ansible_version: "2.14"

# 定义依赖关系
dependencies:
  # 依赖 common Role
  - role: common

  # 依赖 nginx Role，并传递参数
  - role: nginx
    vars:
      nginx_port: 80
      nginx_server_name: "{{ app_domain }}"

  # 依赖 firewall Role
  - role: firewall
    vars:
      firewall_allowed_ports:
        - "{{ app_port }}"
        - 80
        - 443
    when: enable_firewall | default(true)
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Role 依赖关系图                                │
│                                                                 │
│                     ┌─────────┐                                │
│                     │  app    │                                │
│                     └────┬────┘                                │
│                          │                                     │
│            ┌─────────────┼─────────────┐                       │
│            │             │             │                       │
│            ▼             ▼             ▼                       │
│      ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│      │ common  │  │  nginx  │  │firewall │                   │
│      └─────────┘  └─────────┘  └─────────┘                   │
│            │                                                    │
│            ▼                                                    │
│      ┌─────────┐                                               │
│      │  users  │                                               │
│      └─────────┘                                               │
│                                                                 │
│  执行顺序：users → common → nginx → firewall → app             │
│  （依赖 Role 先执行）                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Ansible Galaxy

#### 5.1 Galaxy 命令行使用

```bash
# 搜索 Role
ansible-galaxy search nginx --author geerlingguy
ansible-galaxy search nginx --platform EL

# 查看 Role 信息
ansible-galaxy info geerlingguy.nginx

# 安装 Role
ansible-galaxy role install geerlingguy.nginx
ansible-galaxy role install geerlingguy.nginx,5.0.0    # 指定版本

# 安装到指定目录
ansible-galaxy install geerlingguy.nginx -p ./roles/

# 从 requirements 文件批量安装
ansible-galaxy install -r requirements.yml

# 列出已安装的 Role
ansible-galaxy list

# 删除 Role
ansible-galaxy remove geerlingguy.nginx

# 初始化新 Role
ansible-galaxy role init myrole
```

#### 5.2 requirements.yml 文件

```yaml
# requirements.yml
---
roles:
  # 从 Galaxy 安装
  - name: geerlingguy.nginx
    version: "5.0.0"

  - name: geerlingguy.docker
    version: "6.1.0"

  - name: geerlingguy.postgresql
    version: "3.5.0"

  # 从 Git 仓库安装
  - name: custom-role
    src: https://github.com/example/ansible-role-custom.git
    version: "v1.2.0"
    scm: git

  # 从本地路径安装
  - name: local-role
    src: ./local-roles/my-role

# 也可以定义 Collections
collections:
  - name: community.general
    version: ">= 8.0.0"
  - name: community.docker
    version: ">= 3.0.0"
```

```bash
# 安装所有依赖
ansible-galaxy role install -r requirements.yml
ansible-galaxy collection install -r requirements.yml

# 安装到项目本地目录
ansible-galaxy role install -r requirements.yml -p ./roles/
```

### 6. 自定义 Role 实战

#### 6.1 服务器初始化 Role（common）

```yaml
# roles/common/defaults/main.yml
---
# 系统基础配置
common_timezone: "Asia/Shanghai"
common_hostname_set: true
common_update_packages: true

# 用户管理
common_admin_users:
  - name: ansible
    groups: [wheel]
    ssh_key: ""
common_deploy_users:
  - name: deploy
    system: true

# 安全配置
common_ssh_port: 22
common_ssh_permit_root_login: "no"
common_ssh_password_auth: "no"
common_ssh_max_auth_tries: 3
common_fail2ban_enabled: true

# 系统调优
common_sysctl_settings:
  net.core.somaxconn: 65535
  net.ipv4.tcp_max_syn_backlog: 65535
  net.ipv4.ip_local_port_range: "1024 65535"
  net.ipv4.tcp_tw_reuse: 1
  net.ipv4.tcp_fin_timeout: 30
  vm.swappiness: 10
  vm.overcommit_memory: 1
  fs.file-max: 2097152

# 文件描述符限制
common_nofile_soft: 655350
common_nofile_hard: 655350

# NTP 配置
common_ntp_enabled: true
common_ntp_servers:
  - ntp.aliyun.com
  - ntp.tencent.com

# 基础软件包
common_packages:
  - vim
  - htop
  - iotop
  - sysstat
  - net-tools
  - lsof
  - strace
  - tcpdump
  - jq
  - curl
  - wget
  - git
  - tree
  - unzip
  - rsync
```

```yaml
# roles/common/tasks/main.yml
---
- name: Include OS-specific variables
  include_vars: "{{ ansible_os_family }}.yml"
  tags: [always]

- name: System preparation
  include_tasks: system.yml
  tags: [system]

- name: User management
  include_tasks: users.yml
  tags: [users]

- name: Security hardening
  include_tasks: security.yml
  tags: [security]

- name: System tuning
  include_tasks: tuning.yml
  tags: [tuning]

- name: Install common packages
  include_tasks: packages.yml
  tags: [packages]
```

```yaml
# roles/common/tasks/system.yml
---
- name: Set timezone
  timezone:
    name: "{{ common_timezone }}"
  when: common_timezone is defined

- name: Set hostname
  hostname:
    name: "{{ inventory_hostname }}"
  when: common_hostname_set | default(true)

- name: Update /etc/hosts
  lineinfile:
    path: /etc/hosts
    regexp: "^127\\.0\\.1\\.1"
    line: "127.0.1.1 {{ inventory_hostname }}"
  when: common_hostname_set | default(true)

- name: Update all packages (RedHat)
  yum:
    name: "*"
    state: latest
    update_cache: yes
  when:
    - common_update_packages | default(true)
    - ansible_os_family == "RedHat"

- name: Update all packages (Debian)
  apt:
    upgrade: dist
    update_cache: yes
    cache_valid_time: 3600
  when:
    - common_update_packages | default(true)
    - ansible_os_family == "Debian"

- name: Configure NTP (chrony)
  template:
    src: chrony.conf.j2
    dest: /etc/chrony.conf
    owner: root
    group: root
    mode: "0644"
  notify: Restart chrony
  when: common_ntp_enabled | default(true)

- name: Ensure chrony is running
  service:
    name: chronyd
    state: started
    enabled: yes
  when: common_ntp_enabled | default(true)
```

```yaml
# roles/common/tasks/users.yml
---
- name: Create admin users
  user:
    name: "{{ item.name }}"
    groups: "{{ item.groups | default([]) }}"
    append: yes
    shell: /bin/bash
    create_home: yes
    state: present
  loop: "{{ common_admin_users }}"

- name: Set SSH keys for admin users
  authorized_key:
    user: "{{ item.name }}"
    key: "{{ item.ssh_key }}"
    state: present
  loop: "{{ common_admin_users }}"
  when: item.ssh_key is defined and item.ssh_key | length > 0

- name: Configure sudo for admin users
  copy:
    content: "{{ item.name }} ALL=(ALL) NOPASSWD:ALL\n"
    dest: "/etc/sudoers.d/{{ item.name }}"
    mode: "0440"
    owner: root
    group: root
    validate: "visudo -cf %s"
  loop: "{{ common_admin_users }}"
  when: "'wheel' in (item.groups | default([]))"

- name: Create deploy users
  user:
    name: "{{ item.name }}"
    system: "{{ item.system | default(true) }}"
    shell: /bin/bash
    create_home: yes
    state: present
  loop: "{{ common_deploy_users }}"
```

```yaml
# roles/common/tasks/security.yml
---
- name: Configure SSH
  lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "{{ item.regexp }}"
    line: "{{ item.line }}"
    backup: yes
  loop:
    - { regexp: '^#?Port\s', line: "Port {{ common_ssh_port }}" }
    - { regexp: '^#?PermitRootLogin', line: "PermitRootLogin {{ common_ssh_permit_root_login }}" }
    - { regexp: '^#?PasswordAuthentication', line: "PasswordAuthentication {{ common_ssh_password_auth }}" }
    - { regexp: '^#?MaxAuthTries', line: "MaxAuthTries {{ common_ssh_max_auth_tries }}" }
    - { regexp: '^#?X11Forwarding', line: "X11Forwarding no" }
    - { regexp: '^#?UseDNS', line: "UseDNS no" }
  notify: Restart sshd

- name: Install fail2ban
  package:
    name: fail2ban
    state: present
  when: common_fail2ban_enabled | default(true)

- name: Configure fail2ban
  template:
    src: jail.local.j2
    dest: /etc/fail2ban/jail.local
    owner: root
    group: root
    mode: "0644"
  notify: Restart fail2ban
  when: common_fail2ban_enabled | default(true)

- name: Ensure fail2ban is running
  service:
    name: fail2ban
    state: started
    enabled: yes
  when: common_fail2ban_enabled | default(true)
```

```yaml
# roles/common/tasks/tuning.yml
---
- name: Configure sysctl parameters
  sysctl:
    name: "{{ item.key }}"
    value: "{{ item.value }}"
    state: present
    reload: yes
    sysctl_file: /etc/sysctl.d/99-ansible.conf
  loop: "{{ common_sysctl_settings | dict2items }}"

- name: Configure file descriptor limits
  pam_limits:
    domain: "*"
    limit_type: "{{ item.type }}"
    limit_item: nofile
    value: "{{ item.value }}"
  loop:
    - { type: soft, value: "{{ common_nofile_soft }}" }
    - { type: hard, value: "{{ common_nofile_hard }}" }
```

```yaml
# roles/common/tasks/packages.yml
---
- name: Install common packages (RedHat)
  yum:
    name: "{{ common_packages }}"
    state: present
  when: ansible_os_family == "RedHat"

- name: Install common packages (Debian)
  apt:
    name: "{{ common_packages }}"
    state: present
    update_cache: yes
    cache_valid_time: 3600
  when: ansible_os_family == "Debian"
```

```yaml
# roles/common/handlers/main.yml
---
- name: Restart sshd
  service:
    name: sshd
    state: restarted

- name: Restart chrony
  service:
    name: chronyd
    state: restarted

- name: Restart fail2ban
  service:
    name: fail2ban
    state: restarted
```

#### 6.2 监控部署 Role（node_exporter）

```yaml
# roles/node_exporter/defaults/main.yml
---
node_exporter_version: "1.7.0"
node_exporter_port: 9100
node_exporter_listen_address: "0.0.0.0:{{ node_exporter_port }}"
node_exporter_user: node_exporter
node_exporter_group: node_exporter
node_exporter_install_dir: /usr/local/bin
node_exporter_textfile_dir: /var/lib/node_exporter/textfile_collector
node_exporter_enabled_collectors:
  - cpu
  - diskstats
  - filesystem
  - loadavg
  - meminfo
  - netdev
  - netstat
  - os
  - textfile
  - time
  - uname
node_exporter_disabled_collectors:
  - infiniband
  - nfsd
```

```yaml
# roles/node_exporter/tasks/main.yml
---
- name: Create node_exporter user
  user:
    name: "{{ node_exporter_user }}"
    system: yes
    shell: /sbin/nologin
    create_home: no
    state: present
  tags: [install]

- name: Create directories
  file:
    path: "{{ item }}"
    state: directory
    owner: "{{ node_exporter_user }}"
    group: "{{ node_exporter_group }}"
    mode: "0755"
  loop:
    - "{{ node_exporter_textfile_dir }}"

- name: Download node_exporter
  get_url:
    url: "https://github.com/prometheus/node_exporter/releases/download/v{{ node_exporter_version }}/node_exporter-{{ node_exporter_version }}.linux-amd64.tar.gz"
    dest: "/tmp/node_exporter-{{ node_exporter_version }}.tar.gz"
    mode: "0644"
  register: download_result
  tags: [install]

- name: Extract node_exporter
  unarchive:
    src: "/tmp/node_exporter-{{ node_exporter_version }}.tar.gz"
    dest: /tmp
    remote_src: yes
  when: download_result.changed
  tags: [install]

- name: Install node_exporter binary
  copy:
    src: "/tmp/node_exporter-{{ node_exporter_version }}.linux-amd64/node_exporter"
    dest: "{{ node_exporter_install_dir }}/node_exporter"
    owner: root
    group: root
    mode: "0755"
    remote_src: yes
  notify: Restart node_exporter
  tags: [install]

- name: Deploy systemd service
  template:
    src: node_exporter.service.j2
    dest: /etc/systemd/system/node_exporter.service
    owner: root
    group: root
    mode: "0644"
  notify:
    - Reload systemd
    - Restart node_exporter
  tags: [config]

- name: Start and enable node_exporter
  systemd:
    name: node_exporter
    state: started
    enabled: yes
    daemon_reload: yes
  tags: [services]

- name: Verify node_exporter is running
  uri:
    url: "http://localhost:{{ node_exporter_port }}/metrics"
    method: GET
    status_code: 200
    timeout: 5
  register: metrics_check
  retries: 3
  delay: 2
  until: metrics_check.status == 200
  tags: [verify]
```

```jinja2
{# roles/node_exporter/templates/node_exporter.service.j2 #}
[Unit]
Description=Prometheus Node Exporter
Documentation=https://prometheus.io/docs/guides/node-exporter/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={{ node_exporter_user }}
Group={{ node_exporter_group }}
ExecStart={{ node_exporter_install_dir }}/node_exporter \
{% for collector in node_exporter_enabled_collectors %}
  --collector.{{ collector }} \
{% endfor %}
{% for collector in node_exporter_disabled_collectors %}
  --no-collector.{{ collector }} \
{% endfor %}
  --collector.textfile.directory={{ node_exporter_textfile_dir }} \
  --web.listen-address={{ node_exporter_listen_address }}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```yaml
# roles/node_exporter/handlers/main.yml
---
- name: Reload systemd
  systemd:
    daemon_reload: yes

- name: Restart node_exporter
  service:
    name: node_exporter
    state: restarted
```

### 7. Role 项目结构

```
ansible-project/
├── ansible.cfg                    # Ansible 配置
├── inventory/
│   ├── production/
│   │   ├── hosts.yml             # 生产环境主机
│   │   ├── group_vars/
│   │   │   ├── all.yml           # 所有主机变量
│   │   │   ├── webservers.yml    # Web 服务器变量
│   │   │   └── dbservers.yml     # 数据库服务器变量
│   │   └── host_vars/
│   │       └── web01.yml         # 特定主机变量
│   └── staging/
│       ├── hosts.yml
│       └── group_vars/
│           └── all.yml
├── roles/
│   ├── common/                   # 基础配置 Role
│   ├── nginx/                    # Nginx Role
│   ├── app/                      # 应用 Role
│   ├── postgresql/               # PostgreSQL Role
│   └── node_exporter/            # 监控 Role
├── playbooks/
│   ├── site.yml                  # 主入口
│   ├── webservers.yml            # Web 服务器 Playbook
│   ├── dbservers.yml             # 数据库 Playbook
│   └── deploy.yml                # 部署 Playbook
├── requirements.yml              # Role 依赖
└── Makefile                      # 常用命令
```

```yaml
# playbooks/site.yml
---
- name: Configure all servers
  import_playbook: webservers.yml

- name: Configure database servers
  import_playbook: dbservers.yml
```

```yaml
# playbooks/webservers.yml
---
- name: Configure web servers
  hosts: webservers
  become: yes

  pre_tasks:
    - name: Verify connectivity
      ping:

  roles:
    - role: common
    - role: nginx
    - role: node_exporter
    - role: app
```

---

## 💻 实战练习

### 练习 1：创建自定义 Role

**目标：** 使用 ansible-galaxy 创建一个 Redis Role

```bash
# 1. 初始化 Role
ansible-galaxy role init roles/redis

# 2. 编写 defaults/main.yml
# 3. 编写 tasks/main.yml
# 4. 编写 templates/redis.conf.j2
# 5. 编写 handlers/main.yml
```

### 练习 2：Role 依赖管理

**目标：** 创建一个有依赖关系的复合 Role

```yaml
# roles/webapp/meta/main.yml
dependencies:
  - role: common
  - role: nginx
  - role: redis
  - role: node_exporter
```

### 练习 3：使用 Galaxy Role

**目标：** 使用 requirements.yml 安装社区 Role 并在 Playbook 中使用

```yaml
# requirements.yml
roles:
  - name: geerlingguy.docker
  - name: geerlingguy.postgresql
```

---

## 🎯 面试题精选

### 1. Ansible Role 的目录结构中，defaults 和 vars 有什么区别？

**参考答案：**
- **defaults/main.yml**：定义默认变量，优先级最低，可被调用者轻松覆盖。用于提供合理的默认值。
- **vars/main.yml**：定义 Role 内部变量，优先级较高，不应被调用者覆盖。用于 Role 内部使用的固定值。

优先级：vars > defaults。调用者可以通过 `vars` 参数覆盖 defaults 中的变量，但不应覆盖 vars 中的变量。

### 2. 如何在 Role 之间共享变量？

**参考答案：**
有几种方式：
1. 使用 inventory group_vars/host_vars 定义共享变量
2. 在 Role 的 defaults 中定义变量，供其他 Role 引用
3. 使用 `set_fact` 在 Play 级别设置变量
4. 使用 `include_vars` 加载共享变量文件
5. 通过 Role 的 `vars` 参数传递变量

### 3. import_role 和 include_role 有什么区别？

**参考答案：**
- **import_role**：静态引用，在 Playbook 解析时加载 Role。标签会继承到 Role 中的所有任务，但不支持循环。
- **include_role**：动态引用，在 Playbook 运行时加载 Role。标签不会继承，但支持条件判断和循环。

推荐：固定引用使用 import_role，条件/循环引用使用 include_role。

### 4. 如何测试 Ansible Role？

**参考答案：**
1. **Molecule**：官方推荐的 Role 测试框架，支持 Docker/Vagrant 测试环境
2. **ansible-lint**：静态分析 Role 代码质量
3. **手动测试**：使用 `--check` 模式和 `--diff` 参数
4. **CI/CD 集成**：在 GitLab CI/GitHub Actions 中运行测试

### 5. Role 的依赖是如何执行的？执行顺序是什么？

**参考答案：**
Role 依赖在 meta/main.yml 中定义。执行顺序为：
1. 先执行依赖 Role 的任务（按依赖列表顺序）
2. 再执行当前 Role 的任务
3. 如果有嵌套依赖，最底层的 Role 先执行

例如：app 依赖 common 和 nginx，则执行顺序为 common → nginx → app。

---

## 📚 深入阅读

- [Ansible Roles Documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
- [Ansible Galaxy](https://galaxy.ansible.com/)
- [Ansible Role Development](https://docs.ansible.com/ansible/latest/dev_guide/developing_roles.html)
- [Molecule Documentation](https://molecule.readthedocs.io/)
- [Geerlingguy's Ansible Roles](https://github.com/geerlingguy)

---

## ✅ 自检清单

- [ ] 理解 Role 的目录结构和各目录的用途
- [ ] 掌握 defaults 和 vars 的区别和优先级
- [ ] 能使用 ansible-galaxy 初始化和管理 Role
- [ ] 掌握 Role 的引用方式（roles 段、include_role、import_role）
- [ ] 理解 Role 依赖的执行顺序
- [ ] 能使用 requirements.yml 管理 Role 依赖
- [ ] 完成服务器初始化 Role（common）的编写
- [ ] 完成监控部署 Role（node_exporter）的编写
- [ ] 掌握 Role 的最佳实践（模块化、可复用、可测试）
