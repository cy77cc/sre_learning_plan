# Day 128: Ansible 常用模块

> 📅 日期：2026-05-06
> 📖 学习主题：file/copy/template/service/yum/apt/user/cron/command/shell/raw 模块及组合实战
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 127（Ansible 基础）

## 🎯 学习目标

- 掌握 12 个核心模块的参数和用法
- 理解 command、shell、raw 模块的区别
- 能组合多个模块完成实际运维任务
- 掌握模块返回值的使用（register）

---

## 📖 核心知识点

### 1. 文件管理模块

#### 1.1 file 模块 — 文件和目录管理

```yaml
tasks:
  # 创建目录
  - name: Create application directories
    file:
      path: "{{ item }}"
      state: directory
      owner: deploy
      group: deploy
      mode: "0755"
    loop:
      - /opt/myapp
      - /opt/myapp/config
      - /opt/myapp/logs
      - /opt/myapp/data

  # 创建文件
  - name: Create log file
    file:
      path: /var/log/myapp/app.log
      state: touch
      owner: deploy
      group: deploy
      mode: "0644"
      modification_time: preserve
      access_time: preserve

  # 创建符号链接
  - name: Create symlink to current release
    file:
      src: /opt/myapp/releases/{{ app_version }}
      dest: /opt/myapp/current
      state: link
      owner: deploy
      group: deploy
      force: yes

  # 删除文件/目录
  - name: Remove old releases
    file:
      path: "{{ item }}"
      state: absent
    loop:
      - /opt/myapp/releases/old_version
      - /tmp/build_artifacts

  # 设置文件权限
  - name: Set permissions on config files
    file:
      path: /opt/myapp/config
      owner: deploy
      group: deploy
      mode: "u=rwX,g=rX,o="
      recurse: yes

  # 创建临时目录
  - name: Create temporary directory
    file:
      path: /tmp/ansible_temp_{{ ansible_date_time.epoch }}
      state: directory
      mode: "0700"
    register: temp_dir

  # 检查文件状态（stat）
  - name: Check if config file exists
    stat:
      path: /opt/myapp/config/app.conf
      checksum_algorithm: sha256
    register: config_stat

  - name: Display file info
    debug:
      var: config_stat.stat
    when: config_stat.stat.exists
```

#### 1.2 copy 模块 — 复制文件

```yaml
tasks:
  # 复制本地文件到远程
  - name: Copy SSL certificates
    copy:
      src: files/ssl/
      dest: /etc/ssl/myapp/
      owner: root
      group: root
      mode: "0600"
      backup: yes          # 备份已存在的文件

  # 直接写入内容
  - name: Create motd file
    copy:
      content: |
        ========================================
        Server: {{ ansible_hostname }}
        Environment: {{ app_env | default('production') }}
        Managed by Ansible - DO NOT EDIT
        ========================================
      dest: /etc/motd
      owner: root
      group: root
      mode: "0644"

  # 复制并解压
  - name: Copy application archive
    copy:
      src: files/myapp-{{ app_version }}.tar.gz
      dest: /tmp/myapp-{{ app_version }}.tar.gz
      mode: "0644"

  # 使用 decrypt 解密 Vault 加密的文件
  - name: Copy encrypted configuration
    copy:
      src: files/encrypted.conf
      dest: /opt/myapp/config/app.conf
      decrypt: yes
      owner: deploy
      group: deploy
      mode: "0640"

  # 复制并校验
  - name: Copy binary with verification
    copy:
      src: files/myapp
      dest: /usr/local/bin/myapp
      owner: root
      group: root
      mode: "0755"
      checksum: sha256:abc123...
```

#### 1.3 template 模块 — Jinja2 模板渲染

```yaml
tasks:
  - name: Deploy application config
    template:
      src: templates/app.conf.j2
      dest: /opt/myapp/config/app.conf
      owner: deploy
      group: deploy
      mode: "0640"
      backup: yes
      validate: "python3 -c 'import json; json.load(open(\"%s\"))'"  # 验证 JSON 格式
    notify: Restart application

  - name: Deploy Nginx config with validation
    template:
      src: templates/nginx.conf.j2
      dest: /etc/nginx/conf.d/myapp.conf
      owner: root
      group: root
      mode: "0644"
      validate: "nginx -t -c %s"    # 验证 Nginx 配置
    notify: Reload Nginx

  - name: Deploy with custom newline sequence
    template:
      src: templates/config.ini.j2
      dest: /opt/myapp/config.ini
      owner: deploy
      group: deploy
      mode: "0640"
      newline_sequence: "\r\n"      # Windows 换行符
      trim_blocks: true              # 移除块后第一个换行
      lstrip_blocks: true            # 移除块前的空白
```

### 2. 包管理模块

#### 2.1 yum 模块 — RHEL/CentOS 包管理

```yaml
tasks:
  # 安装单个包
  - name: Install Nginx
    yum:
      name: nginx
      state: present

  # 安装多个包
  - name: Install required packages
    yum:
      name:
        - nginx
        - python3
        - python3-pip
        - curl
        - wget
        - vim
        - htop
        - net-tools
        - lsof
        - strace
      state: present

  # 安装特定版本
  - name: Install specific version
    yum:
      name: "nginx-1.20.1"
      state: present

  # 更新到最新版本
  - name: Update all packages
    yum:
      name: "*"
      state: latest
      update_cache: yes

  # 卸载包
  - name: Remove unnecessary packages
    yum:
      name:
        - telnet
        - rsh-server
      state: absent

  # 安装 RPM 包
  - name: Install from RPM URL
    yum:
      name: "https://example.com/repo/package-1.0-1.el8.x86_64.rpm"
      state: present
      disable_gpg_check: yes

  # 安装包组
  - name: Install development tools
    yum:
      name: "@Development Tools"
      state: present

  # 从本地 RPM 文件安装
  - name: Install local RPM
    yum:
      name: /tmp/package.rpm
      state: present

  # 仅下载不安装
  - name: Download package only
    yum:
      name: nginx
      state: present
      download_only: yes
      download_dir: /tmp/packages
```

#### 2.2 apt 模块 — Debian/Ubuntu 包管理

```yaml
tasks:
  # 安装包
  - name: Install required packages
    apt:
      name:
        - nginx
        - python3
        - python3-pip
        - curl
        - jq
      state: present
      update_cache: yes
      cache_valid_time: 3600    # 缓存 1 小时内不更新

  # 安装特定版本
  - name: Install specific version
    apt:
      name: "nginx=1.18.0-0ubuntu1"
      state: present

  # 添加 PPA 源
  - name: Add Ansible PPA
    apt_repository:
      repo: "ppa:ansible/ansible"
      state: present

  # 添加 GPG 密钥和仓库
  - name: Add Docker GPG key
    apt_key:
      url: https://download.docker.com/linux/ubuntu/gpg
      state: present

  - name: Add Docker repository
    apt_repository:
      repo: "deb [arch=amd64] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable"
      state: present
      filename: docker

  # 更新所有包
  - name: Upgrade all packages
    apt:
      upgrade: dist
      update_cache: yes

  # 自动移除不需要的包
  - name: Autoremove packages
    apt:
      autoremove: yes

  # 安装 .deb 文件
  - name: Install deb package
    apt:
      deb: /tmp/package.deb
      state: present
```

### 3. 服务管理模块

#### 3.1 service 模块

```yaml
tasks:
  # 启动服务
  - name: Start Nginx
    service:
      name: nginx
      state: started

  # 停止服务
  - name: Stop application
    service:
      name: myapp
      state: stopped

  # 重启服务
  - name: Restart application
    service:
      name: myapp
      state: restarted

  # 重载服务
  - name: Reload Nginx
    service:
      name: nginx
      state: reloaded

  # 设置开机自启
  - name: Enable Nginx on boot
    service:
      name: nginx
      enabled: yes

  # 禁用开机自启
  - name: Disable unnecessary service
    service:
      name: cups
      enabled: no
      state: stopped

  # 使用 systemd 管理自定义服务
  - name: Deploy systemd service file
    template:
      src: templates/myapp.service.j2
      dest: /etc/systemd/system/myapp.service
      owner: root
      group: root
      mode: "0644"
    notify: Reload systemd

  - name: Reload systemd
    systemd:
      daemon_reload: yes

  - name: Start and enable application
    systemd:
      name: myapp
      state: started
      enabled: yes
      masked: no

  # systemd 高级用法
  - name: Check service status
    systemd:
      name: myapp
    register: service_status

  - name: Display service info
    debug:
      msg: |
        Active: {{ service_status.status.ActiveState }}
        SubState: {{ service_status.status.SubState }}
        MainPID: {{ service_status.status.MainPID }}
```

### 4. 用户管理模块

#### 4.1 user 模块

```yaml
tasks:
  # 创建系统用户
  - name: Create deploy user
    user:
      name: deploy
      system: yes
      shell: /bin/bash
      create_home: yes
      home: /home/deploy
      comment: "Application deploy user"
      state: present

  # 创建普通用户
  - name: Create developer users
    user:
      name: "{{ item.name }}"
      shell: /bin/bash
      groups: "{{ item.groups | default([]) }}"
      append: yes
      state: present
    loop:
      - { name: alice, groups: ["wheel", "docker"] }
      - { name: bob, groups: ["wheel"] }
      - { name: charlie }

  # 设置密码（使用加密密码）
  - name: Set user password
    user:
      name: deploy
      password: "{{ 'secret_password' | password_hash('sha512') }}"
      update_password: on_create    # 仅在创建时设置密码

  # 删除用户
  - name: Remove inactive user
    user:
      name: olduser
      state: absent
      remove: yes        # 同时删除家目录
      force: yes         # 强制删除（即使用户已登录）

  # 管理 SSH 密钥
  - name: Add SSH authorized key
    authorized_key:
      user: deploy
      key: "{{ lookup('file', '~/.ssh/ansible_key.pub') }}"
      state: present
      exclusive: yes     # 仅保留此密钥

  # 批量添加 SSH 密钥
  - name: Add multiple SSH keys
    authorized_key:
      user: deploy
      key: "{{ item }}"
      state: present
    loop:
      - "{{ lookup('file', '~/.ssh/key1.pub') }}"
      - "{{ lookup('file', '~/.ssh/key2.pub') }}"

  # 从 URL 获取密钥
  - name: Add GitHub user keys
    authorized_key:
      user: deploy
      key: "https://github.com/username.keys"
      state: present
```

### 5. 定时任务模块

#### 5.1 cron 模块

```yaml
tasks:
  # 创建定时任务
  - name: Schedule database backup
    cron:
      name: "Database backup"
      minute: "0"
      hour: "2"
      day: "*"
      month: "*"
      weekday: "*"
      user: postgres
      job: "/usr/local/bin/pg_backup.sh >> /var/log/pg_backup.log 2>&1"
      state: present

  # 每 5 分钟执行
  - name: Health check every 5 minutes
    cron:
      name: "Health check"
      minute: "*/5"
      hour: "*"
      job: "/usr/local/bin/health_check.sh"
      state: present

  # 使用特殊时间字符串
  - name: Run at reboot
    cron:
      name: "Cleanup on reboot"
      special_time: reboot
      job: "/usr/local/bin/cleanup.sh"
      state: present

  # 环境变量
  - name: Set cron environment
    cronvar:
      name: MAILTO
      value: "ops@example.com"
      user: root

  # 禁用定时任务（注释掉）
  - name: Disable old backup job
    cron:
      name: "Old backup"
      state: absent

  # 安装 crontab 文件
  - name: Install crontab from file
    cron:
      name: "{{ item.name }}"
      minute: "{{ item.minute }}"
      hour: "{{ item.hour }}"
      job: "{{ item.job }}"
      state: present
    loop:
      - { name: "Log rotation", minute: "0", hour: "3", job: "/usr/sbin/logrotate /etc/logrotate.conf" }
      - { name: "Temp cleanup", minute: "30", hour: "1", job: "find /tmp -mtime +7 -delete" }
      - { name: "Disk check", minute: "0", hour: "6", job: "/usr/local/bin/disk_check.sh" }
```

### 6. 命令执行模块

#### 6.1 command vs shell vs raw 对比

```
┌─────────────────────────────────────────────────────────────────┐
│           command vs shell vs raw 模块对比                       │
│                                                                 │
│  ┌─────────────┬──────────────┬──────────────┬─────────────┐   │
│  │   特性      │   command    │    shell     │     raw     │   │
│  ├─────────────┼──────────────┼──────────────┼─────────────┤   │
│  │ 执行方式    │ 直接执行      │ 通过 shell   │ 原始 SSH    │   │
│  │             │ 不通过 shell  │ (sh/bash)    │ 执行        │   │
│  ├─────────────┼──────────────┼──────────────┼─────────────┤   │
│  │ 管道 |      │ 不支持       │ 支持         │ 支持        │   │
│  │ 重定向 >    │ 不支持       │ 支持         │ 支持        │   │
│  │ 通配符 *    │ 不支持       │ 支持         │ 支持        │   │
│  │ 环境变量    │ 不支持       │ 支持         │ 支持        │   │
│  ├─────────────┼──────────────┼──────────────┼─────────────┤   │
│  │ Python 依赖 │ 需要         │ 需要         │ 不需要      │   │
│  │ 幂等性      │ 可配置       │ 可配置       │ 不支持      │   │
│  │ 安全性      │ 最高         │ 中等         │ 最低        │   │
│  ├─────────────┼──────────────┼──────────────┼─────────────┤   │
│  │ 适用场景    │ 执行命令     │ 复杂命令     │ 初始化/     │   │
│  │             │ （推荐）     │ 管道/重定向  │ 无 Python   │   │
│  └─────────────┴──────────────┴──────────────┴─────────────┘   │
│                                                                 │
│  推荐优先级：command > shell > raw                              │
│  使用 command 模块更安全（防止 shell 注入）                      │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.2 command 模块

```yaml
tasks:
  # 基本命令执行
  - name: Get application version
    command: /opt/myapp/bin/myapp --version
    register: app_version_result
    changed_when: false          # 此命令不会产生变更

  - name: Display version
    debug:
      msg: "Application version: {{ app_version_result.stdout }}"

  # 使用 creates 参数实现幂等性
  - name: Compile application
    command: make build
    args:
      chdir: /opt/myapp/src
      creates: /opt/myapp/bin/myapp    # 如果文件存在则跳过

  # 使用 removes 参数实现幂等性
  - name: Clean build artifacts
    command: make clean
    args:
      chdir: /opt/myapp/src
      removes: /opt/myapp/bin/myapp    # 如果文件不存在则跳过

  # 带参数的命令
  - name: Run database migration
    command: >
      /opt/myapp/venv/bin/python manage.py migrate
      --database={{ db_name }}
      --verbosity=1
    args:
      chdir: /opt/myapp/code
    environment:
      DJANGO_SETTINGS_MODULE: "myapp.settings.production"
      DATABASE_URL: "postgres://{{ db_user }}:{{ db_pass }}@{{ db_host }}/{{ db_name }}"
    register: migration_result

  # 检查命令结果
  - name: Verify migration
    debug:
      msg: "Migration output: {{ migration_result.stdout_lines }}"
    when: migration_result.changed
```

#### 6.3 shell 模块

```yaml
tasks:
  # 使用管道
  - name: Get disk usage percentage
    shell: df -h / | tail -1 | awk '{print $5}' | sed 's/%//'
    register: disk_usage
    changed_when: false

  - name: Alert if disk is full
    debug:
      msg: "WARNING: Root disk usage is {{ disk_usage.stdout }}%"
    when: disk_usage.stdout | int > 80

  # 使用重定向
  - name: Generate report
    shell: |
      echo "=== System Report ===" > /tmp/report.txt
      echo "Date: $(date)" >> /tmp/report.txt
      echo "Hostname: $(hostname)" >> /tmp/report.txt
      echo "Uptime: $(uptime)" >> /tmp/report.txt
      echo "Disk:" >> /tmp/report.txt
      df -h >> /tmp/report.txt
      echo "Memory:" >> /tmp/report.txt
      free -h >> /tmp/report.txt
    args:
      creates: /tmp/report.txt    # 幂等性

  # 使用环境变量
  - name: Run application script
    shell: ./scripts/deploy.sh
    args:
      chdir: /opt/myapp
    environment:
      APP_ENV: production
      APP_VERSION: "{{ app_version }}"
      DATABASE_URL: "{{ database_url }}"
      PATH: "/opt/myapp/bin:{{ ansible_env.PATH }}"

  # 多行脚本
  - name: Perform maintenance tasks
    shell: |
      set -euo pipefail

      # Stop application gracefully
      systemctl stop myapp || true
      sleep 5

      # Clean up old logs
      find /var/log/myapp -name "*.log" -mtime +30 -delete

      # Restart application
      systemctl start myapp

      # Verify
      sleep 3
      if ! systemctl is-active myapp > /dev/null; then
        echo "ERROR: Application failed to start"
        exit 1
      fi
    register: maintenance_result

  # 使用 executable 指定 shell
  - name: Run with specific shell
    shell: echo $BASH_VERSION
    args:
      executable: /bin/bash
    register: bash_version
    changed_when: false
```

#### 6.4 raw 模块

```yaml
tasks:
  # 不需要 Python 的场景（如初始化新服务器）
  - name: Install Python on remote host
    raw: apt-get update && apt-get install -y python3
    when: ansible_python_interpreter is not defined

  # 检查远程主机基本信息（无需 Python）
  - name: Check remote OS
    raw: cat /etc/os-release
    register: os_info
    changed_when: false

  # 安装 bootstrap 依赖
  - name: Bootstrap CentOS
    raw: yum install -y python3 libselinux-python
    when: ansible_os_family == "RedHat"

  - name: Bootstrap Ubuntu
    raw: apt-get update && apt-get install -y python3 python3-apt
    when: ansible_os_family == "Debian"
```

### 7. 其他常用模块

#### 7.1 lineinfile 模块 — 精确修改文件行

```yaml
tasks:
  # 修改配置文件中的某一行
  - name: Set SSH port
    lineinfile:
      path: /etc/ssh/sshd_config
      regexp: '^#?Port\s'
      line: 'Port 2222'
      state: present
      backup: yes
    notify: Restart sshd

  # 在文件末尾添加行
  - name: Add custom config
    lineinfile:
      path: /etc/security/limits.conf
      line: '* soft nofile 655350'
      state: present
      create: yes

  # 删除匹配的行
  - name: Remove old config
    lineinfile:
      path: /etc/hosts
      regexp: '^192\.168\.1\.100'
      state: absent

  # 在指定行之前插入
  - name: Insert config before marker
    lineinfile:
      path: /etc/nginx/nginx.conf
      insertbefore: '^http {'
      line: '# Custom configuration'

  # 使用 backrefs 仅在匹配时替换
  - name: Update version in config
    lineinfile:
      path: /opt/myapp/config.ini
      regexp: '^version\s*=\s*.*'
      line: 'version = {{ app_version }}'
      backrefs: yes
```

#### 7.2 blockinfile 模块 — 块级文件编辑

```yaml
tasks:
  - name: Add custom SSH config block
    blockinfile:
      path: /etc/ssh/sshd_config
      marker: "# {mark} ANSIBLE MANAGED - Custom SSH Settings"
      block: |
        PermitRootLogin no
        PasswordAuthentication no
        MaxAuthTries 3
        ClientAliveInterval 300
        ClientAliveCountMax 2
      state: present
    notify: Restart sshd

  - name: Add hosts entries
    blockinfile:
      path: /etc/hosts
      marker: "# {mark} ANSIBLE MANAGED - Application Servers"
      block: |
        {% for host in groups['webservers'] %}
        {{ hostvars[host]['ansible_default_ipv4']['address'] }} {{ hostvars[host]['ansible_hostname'] }}
        {% endfor %}
      state: present
```

#### 7.3 uri 模块 — HTTP 请求

```yaml
tasks:
  # 健康检查
  - name: Health check
    uri:
      url: "http://localhost:{{ app_port }}/health"
      method: GET
      status_code: 200
      return_content: yes
    register: health
    retries: 5
    delay: 10
    until: health.status == 200

  # 发送 Slack 通知
  - name: Send Slack notification
    uri:
      url: "{{ slack_webhook_url }}"
      method: POST
      body_format: json
      body:
        text: "Deployment completed: {{ app_name }} v{{ app_version }} on {{ inventory_hostname }}"
        channel: "#ops"
        username: "Ansible Bot"
      status_code: 200
    when: slack_webhook_url is defined

  # API 调用
  - name: Register with service discovery
    uri:
      url: "http://consul:8500/v1/agent/service/register"
      method: PUT
      body_format: json
      body:
        Name: "{{ app_name }}"
        Address: "{{ ansible_default_ipv4.address }}"
        Port: "{{ app_port }}"
        Check:
          HTTP: "http://localhost:{{ app_port }}/health"
          Interval: "10s"
      status_code: 200
```

#### 7.4 git 模块

```yaml
tasks:
  - name: Clone application repository
    git:
      repo: "https://github.com/example/myapp.git"
      dest: /opt/myapp/code
      version: "{{ app_version }}"       # 分支、标签或 commit hash
      force: yes                          # 强制更新
      accept_hostkey: yes                 # 自动接受主机密钥
      key_file: ~/.ssh/deploy_key         # SSH 密钥
      depth: 1                            # 浅克隆（节省空间）
    become_user: deploy

  # 更新现有仓库
  - name: Update application code
    git:
      repo: "https://github.com/example/myapp.git"
      dest: /opt/myapp/code
      version: "{{ app_version }}"
      force: yes
      update: yes                         # 更新已有仓库
    become_user: deploy
```

### 8. 模块组合实战

#### 8.1 完整的 Web 服务器部署

```yaml
---
# deploy-webserver.yml
- name: Deploy and configure web server
  hosts: webservers
  become: yes
  gather_facts: yes

  vars:
    app_name: mywebapp
    app_version: "2.1.0"
    app_port: 8080
    deploy_user: deploy

  tasks:
    # 1. 安装基础软件包
    - name: Install required packages
      package:
        name:
          - nginx
          - python3
          - python3-pip
          - git
          - curl
          - jq
        state: present
      tags: [install]

    # 2. 创建用户和目录
    - name: Create deploy user
      user:
        name: "{{ deploy_user }}"
        system: yes
        shell: /bin/bash
        create_home: yes
        state: present
      tags: [users]

    - name: Create application directories
      file:
        path: "{{ item }}"
        state: directory
        owner: "{{ deploy_user }}"
        group: "{{ deploy_user }}"
        mode: "0755"
      loop:
        - /opt/{{ app_name }}
        - /opt/{{ app_name }}/config
        - /opt/{{ app_name }}/logs
        - /var/log/{{ app_name }}
      tags: [config]

    # 3. 部署代码
    - name: Clone application code
      git:
        repo: "https://github.com/example/{{ app_name }}.git"
        dest: /opt/{{ app_name }}/code
        version: "{{ app_version }}"
        force: yes
      become_user: "{{ deploy_user }}"
      register: code_result
      tags: [deploy]

    # 4. 安装依赖
    - name: Install Python dependencies
      pip:
        requirements: /opt/{{ app_name }}/code/requirements.txt
        virtualenv: /opt/{{ app_name }}/venv
        virtualenv_command: python3 -m venv
      become_user: "{{ deploy_user }}"
      when: code_result.changed
      tags: [deploy]

    # 5. 部署配置文件
    - name: Deploy application config
      template:
        src: templates/app.conf.j2
        dest: /opt/{{ app_name }}/config/app.conf
        owner: "{{ deploy_user }}"
        group: "{{ deploy_user }}"
        mode: "0640"
      notify: Restart application
      tags: [config]

    - name: Deploy Nginx config
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/conf.d/{{ app_name }}.conf
        validate: "nginx -t -c /etc/nginx/nginx.conf"
      notify: Reload Nginx
      tags: [config, nginx]

    - name: Deploy systemd service
      template:
        src: templates/app.service.j2
        dest: /etc/systemd/system/{{ app_name }}.service
      notify:
        - Reload systemd
        - Restart application
      tags: [config, services]

    # 6. 启动服务
    - name: Reload systemd
      systemd:
        daemon_reload: yes
      tags: [services]

    - name: Start and enable services
      service:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - nginx
        - "{{ app_name }}"
      tags: [services]

    # 7. 健康检查
    - name: Wait for application to be ready
      uri:
        url: "http://localhost:{{ app_port }}/health"
        method: GET
        status_code: 200
      register: health
      until: health.status == 200
      retries: 10
      delay: 5
      tags: [verify]

    # 8. 清理
    - name: Clean up old releases
      shell: |
        cd /opt/{{ app_name }}/code
        git gc --auto
      become_user: "{{ deploy_user }}"
      changed_when: false
      tags: [maintenance]

  handlers:
    - name: Reload systemd
      systemd:
        daemon_reload: yes

    - name: Restart application
      service:
        name: "{{ app_name }}"
        state: restarted

    - name: Reload Nginx
      service:
        name: nginx
        state: reloaded
```

---

## 💻 实战练习

### 练习 1：文件管理综合练习

**目标：** 使用 file、copy、template 模块完成服务器文件系统配置

```yaml
# practice-file-management.yml
---
- name: File management practice
  hosts: webservers
  become: yes

  vars:
    app_name: myapp

  tasks:
    # 1. 创建目录结构
    - name: Create directory structure
      file:
        path: "{{ item }}"
        state: directory
        owner: root
        group: root
        mode: "0755"
      loop:
        - /opt/{{ app_name }}
        - /opt/{{ app_name }}/bin
        - /opt/{{ app_name }}/config
        - /opt/{{ app_name }}/data
        - /opt/{{ app_name }}/logs

    # 2. 复制配置文件
    - name: Copy default config
      copy:
        content: |
          [app]
          name = {{ app_name }}
          port = 8080
          debug = false

          [logging]
          level = info
          file = /opt/{{ app_name }}/logs/app.log
        dest: /opt/{{ app_name }}/config/app.ini
        mode: "0640"

    # 3. 创建符号链接
    - name: Create symlink to config
      file:
        src: /opt/{{ app_name }}/config/app.ini
        dest: /etc/{{ app_name }}.conf
        state: link

    # 4. 设置递归权限
    - name: Set directory permissions
      file:
        path: /opt/{{ app_name }}
        owner: root
        group: root
        mode: "u=rwX,g=rX,o="
        recurse: yes

    # 5. 验证
    - name: Verify file structure
      shell: find /opt/{{ app_name }} -type f -o -type d | sort
      register: file_list
      changed_when: false

    - name: Display file structure
      debug:
        var: file_list.stdout_lines
```

### 练习 2：服务管理综合练习

**目标：** 使用 service 和 systemd 模块管理多个服务

```yaml
# practice-service-management.yml
---
- name: Service management practice
  hosts: webservers
  become: yes

  tasks:
    # 1. 检查所有服务状态
    - name: Check service status
      shell: systemctl is-active {{ item }} || echo "inactive"
      loop:
        - nginx
        - sshd
        - chronyd
      register: service_status
      changed_when: false

    - name: Display service status
      debug:
        msg: "{{ item.item }}: {{ item.stdout }}"
      loop: "{{ service_status.results }}"

    # 2. 确保关键服务运行
    - name: Ensure critical services are running
      service:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - nginx
        - sshd
        - chronyd

    # 3. 创建并管理自定义服务
    - name: Create simple web service script
      copy:
        content: |
          #!/bin/bash
          while true; do
            echo -e "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello from $(hostname)" | nc -l -p 9090 -q 1
          done
        dest: /opt/simple-web.sh
        mode: "0755"

    - name: Create systemd service
      copy:
        content: |
          [Unit]
          Description=Simple Web Service
          After=network.target

          [Service]
          Type=simple
          ExecStart=/opt/simple-web.sh
          Restart=always
          RestartSec=3

          [Install]
          WantedBy=multi-user.target
        dest: /etc/systemd/system/simple-web.service
      notify: Reload and restart simple-web

    - name: Enable simple-web service
      service:
        name: simple-web
        state: started
        enabled: yes

  handlers:
    - name: Reload and restart simple-web
      systemd:
        daemon_reload: yes
      notify: Restart simple-web

    - name: Restart simple-web
      service:
        name: simple-web
        state: restarted
```

### 练习 3：命令执行模块对比

**目标：** 对比 command、shell、raw 模块的行为差异

```yaml
# practice-command-modules.yml
---
- name: Command module comparison
  hosts: webservers
  become: yes

  tasks:
    # command 模块 - 不通过 shell
    - name: Run with command module
      command: echo "Hello World"
      register: cmd_result
      changed_when: false

    - name: Display command result
      debug:
        msg: "command stdout: {{ cmd_result.stdout }}"

    # shell 模块 - 通过 shell
    - name: Run with shell module
      shell: echo "Hello World" | tr '[:lower:]' '[:upper:]'
      register: shell_result
      changed_when: false

    - name: Display shell result
      debug:
        msg: "shell stdout: {{ shell_result.stdout }}"

    # command 模块 - 使用 creates 实现幂等性
    - name: Create file with idempotency
      command: touch /tmp/command_test.txt
      args:
        creates: /tmp/command_test.txt

    # shell 模块 - 管道和重定向
    - name: Generate system report
      shell: |
        echo "=== System Report ===" > /tmp/report.txt
        echo "Date: $(date)" >> /tmp/report.txt
        echo "Hostname: $(hostname)" >> /tmp/report.txt
        uptime >> /tmp/report.txt
      args:
        creates: /tmp/report.txt

    # raw 模块 - 无需 Python
    - name: Test raw module
      raw: echo "Raw module works without Python"
      register: raw_result
      changed_when: false

    - name: Display raw result
      debug:
        msg: "raw stdout: {{ raw_result.stdout | default('no output') }}"

    # 对比：处理特殊字符
    - name: Command with special characters (may fail)
      command: echo $HOME
      register: cmd_special
      changed_when: false
      failed_when: false

    - name: Shell with special characters (works)
      shell: echo $HOME
      register: shell_special
      changed_when: false

    - name: Compare special character handling
      debug:
        msg: |
          command: {{ cmd_special.stdout | default('failed') }}
          shell: {{ shell_special.stdout }}
```

---

## 🎯 面试题精选

### 1. command、shell 和 raw 模块有什么区别？

**参考答案：**
- **command**：直接执行命令，不通过 shell，不支持管道、重定向、通配符。最安全，推荐优先使用。
- **shell**：通过 /bin/sh 执行命令，支持管道、重定向、环境变量。存在 shell 注入风险。
- **raw**：直接通过 SSH 执行命令，不需要远程主机安装 Python。适用于初始化新服务器。

推荐优先级：command > shell > raw。使用 command 模块可以避免 shell 注入攻击。

### 2. 如何实现 shell/command 模块的幂等性？

**参考答案：**
有三种方式：
1. 使用 `creates` 参数：如果指定文件存在则跳过
2. 使用 `removes` 参数：如果指定文件不存在则跳过
3. 使用 `register` + `when` 条件：根据前一个任务的结果决定是否执行

```yaml
- name: Compile (idempotent)
  command: make
  args:
    creates: /opt/app/bin/app
```

### 3. yum 和 apt 模块有什么区别？各自的 state 参数有哪些值？

**参考答案：**
- **yum**（RHEL/CentOS）：state 可选 present/installed/absent/removed/latest
- **apt**（Debian/Ubuntu）：state 可选 present/latest/absent，额外支持 `update_cache` 和 `cache_valid_time`

apt 模块还支持 `deb` 参数直接安装 .deb 文件，yum 模块支持 `disable_gpg_check` 跳过签名验证。

### 4. template 模块和 copy 模块有什么区别？

**参考答案：**
- **copy**：复制静态文件到远程主机
- **template**：先使用 Jinja2 引擎渲染模板，再将渲染结果复制到远程主机

template 模块支持变量替换、条件判断、循环等动态内容生成。两者都支持 `backup`、`validate`、`owner`、`mode` 等参数。

### 5. service 模块和 systemd 模块有什么区别？

**参考答案：**
- **service**：通用服务管理模块，兼容 SysV init 和 systemd
- **systemd**：专门针对 systemd 的模块，支持 `daemon_reload`、`masked`、`enabled` 等 systemd 特有功能

推荐在 systemd 系统上使用 systemd 模块，因为它支持更多 systemd 特性（如 `daemon_reload`、`scope`）。

### 6. lineinfile 和 blockinfile 模块有什么区别？各自适用于什么场景？

**参考答案：**
- **lineinfile**：修改或添加单行内容，使用正则匹配定位
- **blockinfile**：在文件中插入、替换或删除多行文本块，使用标记（marker）定位

lineinfile 适用于修改单个配置项（如 SSH 端口），blockinfile 适用于添加配置段落（如自定义 hosts 条目）。对于大量配置修改，建议使用 template 模块。

### 7. 如何安全地在 Playbook 中传递密码和敏感信息？

**参考答案：**
1. 使用 Ansible Vault 加密敏感变量文件
2. 使用 `--vault-password-file` 参数传递 Vault 密码
3. 使用 `no_log: true` 防止敏感信息出现在日志中
4. 使用环境变量传递密钥（`environment` 参数）
5. 使用 `ansible_password` 和 `ansible_become_pass` 变量

```yaml
- name: Database setup
  mysql_user:
    name: admin
    password: "{{ db_password }}"  # 从 Vault 加密文件加载
    priv: "*.*:ALL"
  no_log: true                     # 防止密码出现在日志中
```

---

## 📚 深入阅读

- [Ansible Module Index](https://docs.ansible.com/ansible/latest/collections/index_module.html)
- [Ansible Module Development](https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html)
- [Ansible Module Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Ansible Lint](https://ansible-lint.readthedocs.io/)

---

## ✅ 自检清单

- [ ] 掌握 file 模块（创建目录、文件、符号链接、设置权限）
- [ ] 掌握 copy 模块（复制文件、写入内容、备份）
- [ ] 掌握 template 模块（Jinja2 渲染、验证、备份）
- [ ] 掌握 yum/apt 模块（安装、卸载、更新、特定版本）
- [ ] 掌握 service/systemd 模块（启动、停止、重启、自启、daemon_reload）
- [ ] 掌握 user/authorized_key 模块（创建用户、设置密码、管理 SSH 密钥）
- [ ] 掌握 cron 模块（创建、修改、删除定时任务）
- [ ] 理解 command、shell、raw 模块的区别和使用场景
- [ ] 掌握 lineinfile/blockinfile 模块的精确文件编辑
- [ ] 掌握 uri 模块的 HTTP 请求和 API 调用
- [ ] 能组合多个模块完成完整的服务器部署
