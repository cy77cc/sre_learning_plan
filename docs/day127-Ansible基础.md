# Day 127: Ansible 基础

> 📅 日期：2026-05-05
> 📖 学习主题：Playbook 语法、任务/处理程序/变量/条件/循环、Jinja2 模板、标签、错误处理
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 126（Ansible 简介）

## 🎯 学习目标

- 掌握 Playbook 的完整语法结构
- 理解并运用任务（Tasks）、处理程序（Handlers）、变量（Variables）
- 掌握条件（when）、循环（loop）和错误处理（block/rescue/always）
- 熟练使用 Jinja2 模板引擎
- 掌握标签（Tags）控制任务执行

---

## 📖 核心知识点

### 1. Playbook 基础结构

#### 1.1 Playbook 是什么

Playbook 是 Ansible 的配置、部署和编排语言。它使用 YAML 格式编写，描述了要在远程主机上执行的一系列任务。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Playbook 结构层次                              │
│                                                                 │
│  Playbook（.yml 文件）                                          │
│  │                                                              │
│  ├── Play 1                                                    │
│  │   ├── hosts: webservers      # 目标主机组                    │
│  │   ├── become: yes            # 全局提权                      │
│  │   ├── vars:                  # Play 级变量                   │
│  │   ├── tasks:                 # 任务列表                      │
│  │   │   ├── Task 1            # 单个任务                       │
│  │   │   ├── Task 2                                           │
│  │   │   └── Task 3                                           │
│  │   ├── handlers:              # 处理程序                      │
│  │   ├── pre_tasks:             # 在 tasks 之前执行             │
│  │   ├── post_tasks:            # 在 tasks 之后执行             │
│  │   └── roles:                 # 引用的 Role                   │
│  │                                                              │
│  └── Play 2                                                    │
│      ├── hosts: dbservers                                       │
│      └── tasks:                                                 │
│          └── ...                                                │
│                                                                 │
│  执行顺序：                                                      │
│  pre_tasks → roles → tasks → post_tasks（每个 Play 内）         │
│  Play 1 完成后 → Play 2 → Play 3 ...                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 完整的 Playbook 示例

```yaml
---
# site.yml — Web 应用部署 Playbook
# 版本：1.0
# 作者：SRE Team

- name: Configure and deploy web application
  hosts: webservers
  become: yes
  gather_facts: yes
  serial: "30%"    # 滚动更新，每次 30% 的主机

  vars:
    app_name: mywebapp
    app_version: "2.1.0"
    app_port: 8080
    nginx_port: 80
    deploy_user: deploy
    deploy_group: deploy
    app_dir: /opt/{{ app_name }}
    log_dir: /var/log/{{ app_name }}

  vars_files:
    - vars/common.yml
    - vars/{{ ansible_distribution }}.yml

  pre_tasks:
    - name: Verify target hosts are reachable
      ping:

    - name: Display deployment info
      debug:
        msg: "Deploying {{ app_name }} v{{ app_version }} to {{ inventory_hostname }}"

  tasks:
    - name: Install required packages
      package:
        name:
          - nginx
          - python3
          - python3-pip
          - curl
          - jq
        state: present
      tags: [install, packages]

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
        group: "{{ deploy_group }}"
        mode: "0755"
      loop:
        - "{{ app_dir }}"
        - "{{ app_dir }}/config"
        - "{{ app_dir }}/logs"
        - "{{ log_dir }}"
      tags: [config, directories]

    - name: Deploy application configuration
      template:
        src: templates/app.conf.j2
        dest: "{{ app_dir }}/config/app.conf"
        owner: "{{ deploy_user }}"
        group: "{{ deploy_group }}"
        mode: "0640"
        backup: yes
      notify: Restart application
      tags: [config, deploy]

    - name: Deploy Nginx configuration
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/conf.d/{{ app_name }}.conf
        owner: root
        group: root
        mode: "0644"
        validate: "nginx -t -c %s"
      notify: Reload Nginx
      tags: [config, nginx]

    - name: Deploy application code
      git:
        repo: "https://github.com/example/{{ app_name }}.git"
        dest: "{{ app_dir }}/code"
        version: "{{ app_version }}"
        force: yes
      become_user: "{{ deploy_user }}"
      notify: Restart application
      tags: [deploy, code]

    - name: Install Python dependencies
      pip:
        requirements: "{{ app_dir }}/code/requirements.txt"
        virtualenv: "{{ app_dir }}/venv"
        virtualenv_command: python3 -m venv
      become_user: "{{ deploy_user }}"
      tags: [deploy, dependencies]

    - name: Ensure services are running
      service:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - nginx
        - "{{ app_name }}"
      tags: [services]

    - name: Verify application health
      uri:
        url: "http://localhost:{{ app_port }}/health"
        method: GET
        status_code: 200
      register: health_check
      retries: 5
      delay: 10
      until: health_check.status == 200
      tags: [verify, health]

  post_tasks:
    - name: Send deployment notification
      debug:
        msg: "Deployment of {{ app_name }} v{{ app_version }} completed on {{ inventory_hostname }}"
      tags: [notify]

  handlers:
    - name: Restart application
      service:
        name: "{{ app_name }}"
        state: restarted
      listen: "restart app"

    - name: Reload Nginx
      service:
        name: nginx
        state: reloaded
      listen: "reload nginx"
```

### 2. 变量系统详解

#### 2.1 变量定义位置（优先级从高到低）

```
┌─────────────────────────────────────────────────────────────────┐
│              Ansible 变量优先级（从高到低）                        │
│                                                                 │
│  1. extra vars（-e）                最高优先级                   │
│  2. task vars（任务级别）                                        │
│  3. block vars（块级别）                                         │
│  4. role vars（roles/x/vars/main.yml）                          │
│  5. include vars                                                 │
│  6. set_facts / registered vars                                 │
│  7. play vars（play 级别）                                       │
│  8. play vars_files                                             │
│  9. play vars_prompt                                            │
│ 10. role defaults（roles/x/defaults/main.yml）最低优先级         │
│ 11. inventory vars                                              │
│ 12. inventory host_vars                                         │
│ 13. inventory group_vars                                        │
│ 14. inventory file vars                                         │
│                                                                 │
│  简化记忆：                                                      │
│  extra vars > task vars > role vars > play vars > inventory     │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 变量定义方式

```yaml
# 方式 1：Play 级别 vars
- name: Example play
  hosts: webservers
  vars:
    http_port: 80
    app_name: myapp
    db_host: 10.0.2.10

# 方式 2：Play 级别 vars_files
- name: Example play
  hosts: webservers
  vars_files:
    - vars/common.yml
    - vars/{{ ansible_distribution }}.yml

# 方式 3：通过命令行传递 extra vars
# ansible-playbook site.yml -e "app_version=2.1.0 env=production"

# 方式 4：通过 -e 传递文件
# ansible-playbook site.yml -e "@vars/production.yml"

# 方式 5：Inventory 变量
# inventory/group_vars/webservers.yml
# inventory/host_vars/web01.yml
```

```yaml
# vars/common.yml
---
app_name: mywebapp
app_port: 8080
deploy_user: deploy
max_connections: 1000
log_level: info

# vars/RedHat.yml
---
package_manager: yum
nginx_user: nginx
nginx_config_dir: /etc/nginx

# vars/Debian.yml
---
package_manager: apt
nginx_user: www-data
nginx_config_dir: /etc/nginx
```

#### 2.3 注册变量（register）

```yaml
tasks:
  - name: Check if application is running
    shell: systemctl is-active {{ app_name }}
    register: app_status
    ignore_errors: yes

  - name: Display application status
    debug:
      var: app_status

  - name: Start application if not running
    service:
      name: "{{ app_name }}"
      state: started
    when: app_status.rc != 0

  - name: Get disk usage
    shell: df -h / | tail -1 | awk '{print $5}' | sed 's/%//'
    register: disk_usage

  - name: Alert if disk usage is high
    debug:
      msg: "WARNING: Disk usage is {{ disk_usage.stdout }}%"
    when: disk_usage.stdout | int > 80

  # register 变量的常用属性
  # .stdout       标准输出
  # .stdout_lines 标准输出按行分割
  # .stderr       标准错误
  # .rc           返回码
  # .changed      是否有变更
  # .failed       是否失败
  # .msg          消息
```

#### 2.4 Facts 变量

```yaml
tasks:
  - name: Display OS information
    debug:
      msg: |
        操作系统: {{ ansible_distribution }} {{ ansible_distribution_version }}
        内核版本: {{ ansible_kernel }}
        主机名: {{ ansible_hostname }}
        IP 地址: {{ ansible_default_ipv4.address }}
        CPU 核数: {{ ansible_processor_vcpus }}
        内存大小: {{ ansible_memtotal_mb }} MB
        架构: {{ ansible_architecture }}

  # 常用 Facts 变量
  # ansible_distribution          发行版名称（CentOS/Ubuntu）
  # ansible_distribution_version  发行版版本号
  # ansible_os_family             OS 家族（RedHat/Debian）
  # ansible_kernel                内核版本
  # ansible_hostname              主机名
  # ansible_fqdn                  完全限定域名
  # ansible_default_ipv4.address  默认 IPv4 地址
  # ansible_processor_vcpus       CPU 核数
  # ansible_memtotal_mb           总内存（MB）
  # ansible_architecture          系统架构
  # ansible_mounts                挂载点列表
  # ansible_interfaces            网络接口列表
```

### 3. 处理程序（Handlers）

#### 3.1 Handlers 基础

Handlers 是被通知时才执行的任务。它们只在所有 tasks 执行完毕后运行，并且即使被多次通知也只执行一次。

```yaml
tasks:
  - name: Deploy Nginx configuration
    template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
    notify: Reload Nginx          # 通知 handler

  - name: Deploy application config
    template:
      src: app.conf.j2
      dest: /opt/app/config/app.conf
    notify:
      - Restart Application        # 可以通知多个 handler
      - Send Notification

  - name: Force handler execution
    meta: flush_handlers           # 立即执行已通知的 handlers

handlers:
  - name: Reload Nginx
    service:
      name: nginx
      state: reloaded

  - name: Restart Application
    service:
      name: myapp
      state: restarted

  - name: Send Notification
    debug:
      msg: "Application configuration updated on {{ inventory_hostname }}"
```

#### 3.2 Handlers 执行时机

```
┌─────────────────────────────────────────────────────────────────┐
│                    Handlers 执行时机                              │
│                                                                 │
│  正常流程：                                                      │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌──────────────┐         │
│  │pre_ │→ │roles│→ │tasks│→ │post_│→ │  handlers    │         │
│  │tasks│  │     │  │     │  │tasks│  │  (一次性)    │         │
│  └─────┘  └─────┘  └─────┘  └─────┘  └──────────────┘         │
│                                                                 │
│  使用 meta: flush_handlers 可以在 tasks 中间强制执行 handlers：  │
│  ┌─────┐  ┌─────┐  ┌────────┐  ┌─────┐  ┌─────┐               │
│  │Task1│→ │Task2│→ │handlers│→ │Task3│→ │Task4│               │
│  │     │  │notify│  │flush   │  │     │  │notify│              │
│  └─────┘  └─────┘  └────────┘  └─────┘  └─────┘               │
│                                      │                          │
│                                      ▼                          │
│                              ┌──────────────┐                   │
│                              │  handlers    │                   │
│                              └──────────────┘                   │
│                                                                 │
│  注意事项：                                                      │
│  1. Handler 名称全局唯一（跨 Role 也要唯一）                      │
│  2. 即使被多次通知，也只执行一次                                  │
│  3. 如果任务失败，handler 不会执行                                │
│  4. 使用 listen 可以让多个 handler 响应同一个通知                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4. 条件判断（when）

#### 4.1 基本条件

```yaml
tasks:
  - name: Install packages on Debian/Ubuntu
    apt:
      name: "{{ item }}"
      state: present
      update_cache: yes
    loop:
      - nginx
      - curl
      - jq
    when: ansible_os_family == "Debian"

  - name: Install packages on RedHat/CentOS
    yum:
      name: "{{ item }}"
      state: present
    loop:
      - nginx
      - curl
      - jq
    when: ansible_os_family == "RedHat"

  - name: Run only on CentOS 7
    debug:
      msg: "This is CentOS 7"
    when:
      - ansible_distribution == "CentOS"
      - ansible_distribution_major_version == "7"
```

#### 4.2 复杂条件表达式

```yaml
tasks:
  # 比较运算符
  - name: Task for high-memory servers
    debug:
      msg: "Server has more than 8GB RAM"
    when: ansible_memtotal_mb > 8192

  # 逻辑运算符
  - name: Complex condition
    debug:
      msg: "CentOS or RedHat with more than 4 CPUs"
    when: >
      (ansible_os_family == "RedHat") and
      (ansible_processor_vcpus > 4)

  # 字符串匹配
  - name: Check hostname pattern
    debug:
      msg: "Web server detected"
    when: inventory_hostname is match("web*")

  # 正则表达式
  - name: Check hostname with regex
    debug:
      msg: "Database server detected"
    when: inventory_hostname is search("db\d+")

  # 列表包含
  - name: Check if in allowed list
    debug:
      msg: "Server is in allowed list"
    when: inventory_hostname in ["web01", "web02", "web03"]

  # 变量是否存在
  - name: Check if variable is defined
    debug:
      msg: "app_version is {{ app_version }}"
    when: app_version is defined

  - name: Check if variable is not defined
    debug:
      msg: "app_version is not set"
    when: app_version is not defined

  # 布尔判断
  - name: Run when variable is truthy
    debug:
      msg: "Feature is enabled"
    when: enable_feature | default(false) | bool

  # 使用 register 结果作为条件
  - name: Check if file exists
    stat:
      path: /etc/nginx/nginx.conf
    register: nginx_conf

  - name: Backup existing config
    copy:
      src: /etc/nginx/nginx.conf
      dest: /etc/nginx/nginx.conf.bak
      remote_src: yes
    when: nginx_conf.stat.exists
```

### 5. 循环（Loop）

#### 5.1 基本循环

```yaml
tasks:
  # 简单列表循环
  - name: Create users
    user:
      name: "{{ item }}"
      state: present
      shell: /bin/bash
    loop:
      - alice
      - bob
      - charlie

  # 使用 loop 和索引
  - name: Create numbered config files
    template:
      src: worker.conf.j2
      dest: "/etc/workers/worker-{{ idx }}.conf"
    loop: "{{ workers }}"
    loop_control:
      index_var: idx

  # 使用 loop 和 label（简化输出）
  - name: Install packages
    apt:
      name: "{{ item.name }}"
      state: "{{ item.state | default('present') }}"
    loop:
      - { name: nginx, state: present }
      - { name: curl, state: present }
      - { name: vim, state: latest }
    loop_control:
      label: "{{ item.name }}"    # 仅显示包名，不显示整个字典
```

#### 5.2 高级循环

```yaml
tasks:
  # 嵌套循环
  - name: Grant database access
    mysql_user:
      name: "{{ item[0] }}"
      host: "{{ item[1] }}"
      priv: "{{ item[0] }}.*:ALL"
      state: present
    loop: "{{ ['alice', 'bob'] | product(['10.0.1.%', '10.0.2.%']) | list }}"

  # 使用 until 重试
  - name: Wait for application to be ready
    uri:
      url: "http://localhost:{{ app_port }}/health"
      method: GET
      status_code: 200
    register: health_check
    until: health_check.status == 200
    retries: 10
    delay: 5

  # 使用 with_* 传统语法（仍然支持）
  - name: With items (legacy)
    yum:
      name: "{{ item }}"
      state: present
    with_items:
      - nginx
      - curl

  - name: With dict (legacy)
    debug:
      msg: "Key={{ item.key }} Value={{ item.value }}"
    with_dict:
      name: myapp
      version: "2.0"
      port: 8080

  - name: With fileglob (legacy)
    copy:
      src: "{{ item }}"
      dest: /etc/config/
    with_fileglob:
      - "configs/*.conf"
```

#### 5.3 loop_control 详解

```yaml
tasks:
  - name: Process items with loop_control
    debug:
      msg: "Item {{ idx }}: {{ item }} (pause: {{ ansible_loop.nextitem | default('last') }})"
    loop:
      - alpha
      - beta
      - gamma
    loop_control:
      index_var: idx           # 当前索引（从 0 开始）
      label: "{{ item }}"      # 简化输出标签
      pause: 2                 # 每次循环暂停 2 秒

  # ansible_loop 内置变量
  # ansible_loop.index        当前迭代索引（从 1 开始）
  # ansible_loop.index0       当前迭代索引（从 0 开始）
  # ansible_loop.first        是否是第一次迭代
  # ansible_loop.last         是否是最后一次迭代
  # ansible_loop.length       循环总长度
  # ansible_loop.nextitem     下一个元素（最后一个为 undefined）
```

### 6. 错误处理

#### 6.1 block/rescue/always

```yaml
tasks:
  - name: Handle deployment with error recovery
    block:
      - name: Deploy application code
        git:
          repo: "https://github.com/example/app.git"
          dest: /opt/app
          version: "{{ app_version }}"
        register: deploy_result

      - name: Install dependencies
        pip:
          requirements: /opt/app/requirements.txt
          virtualenv: /opt/app/venv

      - name: Restart application
        service:
          name: myapp
          state: restarted

      - name: Verify health
        uri:
          url: "http://localhost:{{ app_port }}/health"
          status_code: 200
        retries: 5
        delay: 10
        register: health

    rescue:
      - name: Log deployment failure
        debug:
          msg: "DEPLOYMENT FAILED on {{ inventory_hostname }}: {{ ansible_failed_task.name }}"

      - name: Rollback to previous version
        git:
          repo: "https://github.com/example/app.git"
          dest: /opt/app
          version: "{{ app_version_previous | default('main') }}"
        when: deploy_result is defined

      - name: Restart with previous version
        service:
          name: myapp
          state: restarted

      - name: Send failure alert
        debug:
          msg: "ALERT: Deployment failed on {{ inventory_hostname }}, rolled back to previous version"

    always:
      - name: Clean up temporary files
        file:
          path: "{{ item }}"
          state: absent
        loop:
          - /tmp/deploy_temp
          - /tmp/build_artifacts

      - name: Update deployment log
        lineinfile:
          path: /var/log/deployments.log
          line: "{{ ansible_date_time.iso8601 }} - {{ inventory_hostname }} - {{ app_version }} - {{ 'FAILED' if deploy_result is failed else 'SUCCESS' }}"
          create: yes
```

#### 6.2 ignore_errors 和 failed_when

```yaml
tasks:
  # 忽略错误继续执行
  - name: Check optional service
    shell: systemctl is-active optional-service
    register: optional_status
    ignore_errors: yes

  - name: Log optional service status
    debug:
      msg: "Optional service status: {{ optional_status.rc }}"
    when: optional_status is failed

  # 自定义失败条件
  - name: Check disk space
    shell: df -h / | tail -1 | awk '{print $5}' | sed 's/%//'
    register: disk_usage
    failed_when: disk_usage.stdout | int > 95

  # 自定义变更条件
  - name: Check configuration
    shell: nginx -t
    register: nginx_test
    changed_when: false    # 此命令永远不会产生变更

  # 自定义成功条件
  - name: Run deployment script
    shell: /opt/scripts/deploy.sh
    register: deploy_output
    changed_when: "'changed' in deploy_output.stdout"
    failed_when:
      - deploy_output.rc != 0
      - "'FATAL' in deploy_output.stderr"
```

#### 6.3 assert 断言

```yaml
tasks:
  - name: Validate system requirements
    assert:
      that:
        - ansible_memtotal_mb >= 2048
        - ansible_processor_vcpus >= 2
        - ansible_distribution in ["CentOS", "Ubuntu", "Debian"]
        - ansible_distribution_major_version | int >= 7
      fail_msg: "System does not meet minimum requirements"
      success_msg: "System requirements validated"
      quiet: false

  - name: Validate configuration
    assert:
      that:
        - app_port is defined and app_port | int > 0 and app_port | int < 65536
        - app_name is match('[a-z][a-z0-9-]+')
        - deploy_user is defined
      fail_msg: "Invalid configuration detected"
```

### 7. Jinja2 模板引擎

#### 7.1 Jinja2 基础语法

```jinja2
{# 这是注释，不会出现在输出中 #}

{# 变量输出 #}
App Name: {{ app_name }}
App Port: {{ app_port }}
Hostname: {{ ansible_hostname }}

{# 表达式 #}
Max Connections: {{ ansible_processor_vcpus * 256 }}
Total Memory: {{ ansible_memtotal_mb }} MB
Available Memory: {{ ansible_memtotal_mb - ansible_memfree_mb }} MB

{# 过滤器 #}
Upper Case: {{ app_name | upper }}
Lower Case: {{ app_name | lower }}
Default Value: {{ undefined_var | default('not set') }}
Join List: {{ ['web01', 'web02', 'web03'] | join(', ') }}
Length: {{ ['a', 'b', 'c'] | length }}
JSON: {{ some_dict | to_json }}
YAML: {{ some_dict | to_yaml }}
```

#### 7.2 Jinja2 控制结构

```jinja2
{# 条件语句 #}
{% if ansible_os_family == "Debian" %}
  # Debian/Ubuntu 配置
  user www-data;
  worker_processes auto;
{% elif ansible_os_family == "RedHat" %}
  # RedHat/CentOS 配置
  user nginx;
  worker_processes {{ ansible_processor_vcpus }};
{% else %}
  # 默认配置
  user nginx;
  worker_processes 1;
{% endif %}

{# 循环 #}
{% for server in groups['webservers'] %}
server {
    listen 80;
    server_name {{ hostvars[server]['ansible_hostname'] }};
    backend {{ hostvars[server]['ansible_default_ipv4']['address'] }}:{{ app_port }};
}
{% endfor %}

{# 带条件的循环 #}
{% for user in users %}
{% if user.enabled | default(true) %}
{{ user.name }} ALL=(ALL) {{ user.privileges | default('NOPASSWD:ALL') }}
{% endif %}
{% endfor %}

{# 循环变量 #}
{% for item in list %}
  loop.index:  当前迭代次数（从 1 开始）
  loop.index0: 当前迭代次数（从 0 开始）
  loop.first:  是否是第一次迭代
  loop.last:   是否是最后一次迭代
  loop.length: 序列长度
{% endfor %}
```

#### 7.3 模板文件示例

```jinja2
{# templates/nginx.conf.j2 #}
# Managed by Ansible - DO NOT EDIT MANUALLY
# Generated at: {{ ansible_date_time.iso8601 }}

user {{ nginx_user | default('nginx') }};
worker_processes {{ ansible_processor_vcpus }};
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections {{ nginx_worker_connections | default(1024) }};
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout {{ nginx_keepalive_timeout | default(65) }};
    types_hash_max_size 2048;

    {% if nginx_gzip_enabled | default(true) %}
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    {% endif %}

    # Upstream backend
    upstream {{ app_name }}_backend {
        {% for host in groups['webservers'] %}
        server {{ hostvars[host]['ansible_default_ipv4']['address'] }}:{{ app_port }} weight=1;
        {% endfor %}
    }

    server {
        listen {{ nginx_port | default(80) }};
        server_name {{ nginx_server_name | default('_') }};

        location / {
            proxy_pass http://{{ app_name }}_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30;
            proxy_send_timeout 60;
            proxy_read_timeout 60;
        }

        location /health {
            access_log off;
            return 200 "OK\n";
        }

        location /nginx_status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
        }
    }
}
```

```jinja2
{# templates/app.service.j2 #}
[Unit]
Description={{ app_name }} Application
After=network.target
Wants=network-online.target

[Service]
Type=simple
User={{ deploy_user }}
Group={{ deploy_group }}
WorkingDirectory={{ app_dir }}
Environment=APP_ENV={{ app_env | default('production') }}
Environment=APP_PORT={{ app_port }}
Environment=LOG_LEVEL={{ log_level | default('info') }}
Environment=DATABASE_URL={{ database_url | default('') }}
ExecStart={{ app_dir }}/venv/bin/python {{ app_dir }}/code/app.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier={{ app_name }}

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={{ app_dir }} {{ log_dir }}

[Install]
WantedBy=multi-user.target
```

### 8. 标签（Tags）

```yaml
tasks:
  - name: Install packages
    apt:
      name: "{{ item }}"
      state: present
    loop:
      - nginx
      - python3
      - curl
    tags: [install, packages]

  - name: Deploy configuration
    template:
      src: app.conf.j2
      dest: /etc/app.conf
    notify: Restart app
    tags: [config, deploy]

  - name: Deploy application code
    git:
      repo: "https://github.com/example/app.git"
      dest: /opt/app
    tags: [deploy, code]

  - name: Start services
    service:
      name: "{{ item }}"
      state: started
      enabled: yes
    loop:
      - nginx
      - myapp
    tags: [services, always]    # 'always' 标签总是执行

  - name: Health check
    uri:
      url: "http://localhost:{{ app_port }}/health"
      status_code: 200
    tags: [verify, never]       # 'never' 标签默认不执行
```

```bash
# 标签使用命令
ansible-playbook site.yml --tags "install"         # 仅执行 install 标签
ansible-playbook site.yml --tags "install,config"  # 执行 install 或 config 标签
ansible-playbook site.yml --skip-tags "deploy"     # 跳过 deploy 标签
ansible-playbook site.yml --tags "always"          # 仅执行 always 标签
ansible-playbook site.yml --list-tags              # 列出所有标签
ansible-playbook site.yml --list-tasks             # 列出所有任务
```

---

## 💻 实战练习

### 练习 1：编写完整的服务器配置 Playbook

**目标：** 编写一个 Playbook，配置 Web 服务器（Nginx + 应用）

```yaml
# playbook: configure-webserver.yml
---
- name: Configure web server
  hosts: webservers
  become: yes
  gather_facts: yes

  vars:
    nginx_port: 80
    app_name: mywebapp
    app_port: 8080

  tasks:
    - name: Install Nginx
      package:
        name: nginx
        state: present
      tags: [install]

    - name: Deploy Nginx config
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/conf.d/{{ app_name }}.conf
        validate: "nginx -t -c /etc/nginx/nginx.conf"
      notify: Reload Nginx
      tags: [config]

    - name: Ensure Nginx is running
      service:
        name: nginx
        state: started
        enabled: yes
      tags: [services]

  handlers:
    - name: Reload Nginx
      service:
        name: nginx
        state: reloaded
```

### 练习 2：编写带错误处理的部署 Playbook

**目标：** 使用 block/rescue/always 实现部署失败自动回滚

```yaml
# playbook: deploy-with-rollback.yml
---
- name: Deploy with rollback
  hosts: webservers
  become: yes

  vars:
    app_name: mywebapp
    app_version: "2.1.0"
    app_dir: /opt/{{ app_name }}

  tasks:
    - name: Deployment block
      block:
        - name: Backup current version
          shell: |
            if [ -d {{ app_dir }}/code ]; then
              cp -r {{ app_dir }}/code {{ app_dir }}/code.bak.$(date +%Y%m%d%H%M%S)
            fi

        - name: Deploy new version
          git:
            repo: "https://github.com/example/{{ app_name }}.git"
            dest: "{{ app_dir }}/code"
            version: "{{ app_version }}"

        - name: Install dependencies
          pip:
            requirements: "{{ app_dir }}/code/requirements.txt"
            virtualenv: "{{ app_dir }}/venv"

        - name: Restart application
          service:
            name: "{{ app_name }}"
            state: restarted

        - name: Health check
          uri:
            url: "http://localhost:8080/health"
            status_code: 200
          retries: 5
          delay: 10

      rescue:
        - name: Rollback to backup
          shell: |
            LATEST_BACKUP=$(ls -t {{ app_dir }}/code.bak.* 2>/dev/null | head -1)
            if [ -n "$LATEST_BACKUP" ]; then
              rm -rf {{ app_dir }}/code
              mv "$LATEST_BACKUP" {{ app_dir }}/code
            fi

        - name: Restart with old version
          service:
            name: "{{ app_name }}"
            state: restarted

        - name: Fail with message
          fail:
            msg: "Deployment failed, rolled back to previous version"

      always:
        - name: Log deployment result
          lineinfile:
            path: /var/log/deployments.log
            line: "{{ ansible_date_time.iso8601 }} {{ inventory_hostname }} {{ app_version }}"
            create: yes
```

### 练习 3：Jinja2 模板挑战

**目标：** 编写一个动态生成 HAProxy 配置的 Jinja2 模板

```jinja2
{# templates/haproxy.cfg.j2 #}
# Managed by Ansible
global
    maxconn {{ haproxy_maxconn | default(50000) }}
    log /dev/log local0
    stats socket /var/run/haproxy.sock mode 600

defaults
    mode http
    timeout connect 5s
    timeout client 30s
    timeout server 30s
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor

frontend http_front
    bind *:{{ haproxy_port | default(80) }}
{% for frontend_option in haproxy_frontend_options | default([]) %}
    {{ frontend_option }}
{% endfor %}
    default_backend {{ app_name }}_servers

backend {{ app_name }}_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

{% for host in groups['webservers'] %}
    server {{ hostvars[host]['ansible_hostname'] }} {{ hostvars[host]['ansible_default_ipv4']['address'] }}:{{ app_port }} check inter 5s fall 3 rise 2
{% endfor %}

{% if haproxy_stats_enabled | default(false) %}
listen stats
    bind *:{{ haproxy_stats_port | default(8404) }}
    stats enable
    stats uri /stats
    stats refresh 10s
    stats auth {{ haproxy_stats_user | default('admin') }}:{{ haproxy_stats_password | default('admin') }}
{% endif %}
```

---

## 🎯 面试题精选

### 1. Ansible Playbook 中 tasks 的执行顺序是什么？

**参考答案：**
在单个 Play 内，执行顺序为：
1. `pre_tasks` — 在 Role 和 tasks 之前执行
2. `roles` — Role 中的任务
3. `tasks` — 主要任务
4. `post_tasks` — 在 tasks 之后执行
5. `handlers` — 被通知的处理程序（在所有任务完成后一次性执行）

使用 `meta: flush_handlers` 可以在 tasks 中间强制执行已通知的 handlers。

### 2. Handlers 和 Tasks 有什么区别？

**参考答案：**
- **Tasks**：每次都执行（根据幂等性可能跳过）
- **Handlers**：仅在被 `notify` 通知时执行，且只执行一次
- **执行时机**：Handlers 在所有 tasks 完成后执行（除非使用 `meta: flush_handlers`）
- **用途**：Handlers 通常用于"重启服务"、"重载配置"等操作，避免不必要的服务重启

### 3. Ansible 变量的优先级是什么？

**参考答案：**
从高到低：extra vars (-e) > task vars > block vars > role vars > include vars > set_facts > play vars > play vars_files > role defaults > inventory vars

**最佳实践：** 使用 `role defaults` 定义可覆盖的默认值，使用 `inventory group_vars` 定义环境特定值，使用 `extra vars` 传递部署时参数。

### 4. 如何在 Playbook 中实现错误处理和回滚？

**参考答案：**
使用 `block/rescue/always` 结构：
- `block`：正常执行的任务
- `rescue`：block 中任务失败时执行（类似 try/catch）
- `always`：无论成功失败都执行（类似 finally）

配合 `register` 记录任务状态，使用 `when` 条件判断执行回滚操作。

### 5. Jinja2 模板中的 `default` 过滤器有什么作用？

**参考答案：**
`default` 过滤器用于为未定义的变量提供默认值：
- `{{ var | default('fallback') }}` — 如果 var 未定义则使用 'fallback'
- `{{ var | default(omit) }}` — 如果 var 未定义则完全省略该参数
- `{{ var | default(true) | bool }}` — 配合类型转换

这在编写通用 Role 时特别有用，允许调用者选择性地覆盖默认配置。

---

## 📚 深入阅读

- [Ansible Playbook Guide](https://docs.ansible.com/ansible/latest/playbook_guide/)
- [Ansible Variables](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html)
- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/)
- [Ansible Loops](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_loops.html)
- [Ansible Error Handling](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html)

---

## ✅ 自检清单

- [ ] 理解 Playbook 的完整结构（Play → Tasks → Handlers）
- [ ] 掌握变量定义的 5 种方式和优先级
- [ ] 能使用 register 注册变量并根据结果做条件判断
- [ ] 掌握 Handlers 的使用和执行时机
- [ ] 能使用 when 编写条件判断
- [ ] 掌握 loop 和 loop_control 的用法
- [ ] 能使用 block/rescue/always 实现错误处理
- [ ] 熟练使用 Jinja2 模板语法（变量、条件、循环、过滤器）
- [ ] 掌握 Tags 的使用和命令行控制
- [ ] 能编写完整的生产级 Playbook
