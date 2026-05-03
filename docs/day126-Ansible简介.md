# Day 126: Ansible 简介

> 📅 日期：2026-05-04
> 📖 学习主题：Ansible 无代理架构、SSH 连接、Inventory、Ad-hoc 命令、ansible.cfg、安装配置
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 120（Terraform 简介），Day 38（tcpdump 抓包分析）

## 🎯 学习目标

- 理解 Ansible 无代理架构的原理与优势，能与 Puppet/Chef 进行对比
- 掌握 Inventory 文件的编写（静态与动态）
- 掌握 ansible.cfg 配置文件的层级与常用参数
- 能使用 Ad-hoc 命令管理远程主机
- 完成 Ansible 安装并成功连接多台远程主机

---

## 📖 核心知识点

### 1. Ansible 概述与架构

#### 1.1 什么是 Ansible

Ansible 是 Red Hat 开发的开源自动化工具，用于配置管理、应用部署、任务编排和基础设施即代码（IaC）。它的核心设计理念是**简单**和**无代理（Agentless）**。

```
┌─────────────────────────────────────────────────────────────────┐
│                      Ansible 核心特性                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  无代理      │  │  幂等性     │  │  声明式     │             │
│  │  Agentless   │  │  Idempotent │  │  Declarative│             │
│  │             │  │             │  │             │             │
│  │ 不需要在目标 │  │ 多次执行    │  │ 描述期望    │             │
│  │ 主机安装任何 │  │ 结果相同    │  │ 状态而非    │             │
│  │ 代理软件     │  │             │  │ 执行步骤    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  YAML 语法  │  │  模块化     │  │  SSH 连接   │             │
│  │             │  │  Modular    │  │             │             │
│  │ Playbook    │  │             │  │ 通过 SSH    │             │
│  │ 使用 YAML   │  │ 3000+ 内置  │  │ 管理远程    │             │
│  │ 编写        │  │ 模块        │  │ 主机        │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 无代理架构详解

Ansible 的最大特点是无代理架构。与 Puppet 和 Chef 不同，Ansible 不需要在被管理节点上安装任何代理软件。

```
┌─────────────────────────────────────────────────────────────────┐
│                Ansible 无代理架构                                │
│                                                                 │
│  ┌──────────────────────┐                                       │
│  │   控制节点            │                                       │
│  │   (Control Node)     │                                       │
│  │                      │                                       │
│  │  ┌────────────────┐  │                                       │
│  │  │  Ansible Engine│  │                                       │
│  │  │                │  │                                       │
│  │  │  ┌──────────┐  │  │                                       │
│  │  │  │ Playbook │  │  │                                       │
│  │  │  │ Engine   │  │  │                                       │
│  │  │  └────┬─────┘  │  │                                       │
│  │  │       │        │  │                                       │
│  │  │  ┌────▼─────┐  │  │                                       │
│  │  │  │ Module   │  │  │                                       │
│  │  │  │ Library  │  │  │                                       │
│  │  │  └────┬─────┘  │  │                                       │
│  │  │       │        │  │                                       │
│  │  │  ┌────▼─────┐  │  │                                       │
│  │  │  │ Plugin   │  │  │                                       │
│  │  │  │ System   │  │  │                                       │
│  │  │  └────┬─────┘  │  │                                       │
│  │  └───────┼────────┘  │                                       │
│  └──────────┼───────────┘                                       │
│             │                                                   │
│             │  SSH (Paramiko/OpenSSH)                           │
│             │                                                   │
│  ┌──────────▼──────────────────────────────────────────────┐   │
│  │              被管理节点 (Managed Nodes)                   │   │
│  │                                                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│  │  │ Web     │  │ DB      │  │ Cache   │  │ LB      │   │   │
│  │  │ Server  │  │ Server  │  │ Server  │  │ Server  │   │   │
│  │  │         │  │         │  │         │  │         │   │   │
│  │  │ 无需    │  │ 无需    │  │ 无需    │  │ 无需    │   │   │
│  │  │ 安装    │  │ 安装    │  │ 安装    │  │ 安装    │   │   │
│  │  │ 代理    │  │ 代理    │  │ 代理    │  │ 代理    │   │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  工作流程：                                                      │
│  1. 控制节点读取 Playbook/Inventory                              │
│  2. 通过 SSH 连接到被管理节点                                     │
│  3. 将 Python 模块代码传输到临时目录                               │
│  4. 在被管理节点上执行模块                                        │
│  5. 返回 JSON 格式的执行结果                                      │
│  6. 清理临时文件                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3 Ansible vs Puppet vs Chef 详细对比

| 维度 | Ansible | Puppet | Chef |
|------|---------|--------|------|
| **架构** | 无代理（SSH） | Agent/Server | Agent/Server |
| **语言** | YAML（Playbook） | Ruby DSL（Puppet DSL） | Ruby DSL（Recipes） |
| **学习曲线** | 低 | 中等 | 高 |
| **连接方式** | SSH/WinRM | Agent 主动拉取 | Agent 主动拉取 |
| **控制节点** | 需要 | 需要（Master） | 需要（Server） |
| **被管理节点** | 仅需 Python + SSH | 需安装 Puppet Agent | 需安装 Chef Client |
| **推送/拉取** | 推送（Push）为主 | 拉取（Pull）为主 | 拉取（Pull）为主 |
| **幂等性** | 内置 | 内置 | 需要编写 |
| **Web UI** | AWX/Tower | Puppet Enterprise Console | Chef Manage |
| **社区生态** | Galaxy（丰富） | Forge（丰富） | Supermarket（中等） |
| **适用规模** | 中小到大型 | 大型 | 大型 |
| **Windows 支持** | WinRM | 原生 Agent | 原生 Agent |
| **性能** | 中等（SSH 开销） | 高（Agent 缓存） | 高（Agent 缓存） |
| **许可证** | GPL v3 | Apache 2.0 | Apache 2.0 |

```
┌─────────────────────────────────────────────────────────────────┐
│              架构对比：Push vs Pull                               │
│                                                                 │
│  Ansible (Push 模式)：                                          │
│  ┌──────────┐     SSH Push      ┌──────────┐                   │
│  │ 控制节点  │ ───────────────→  │ 目标主机  │                   │
│  │          │  执行并返回结果    │          │                   │
│  └──────────┘                   └──────────┘                   │
│                                                                 │
│  Puppet/Chef (Pull 模式)：                                      │
│  ┌──────────┐                   ┌──────────┐                   │
│  │ Master/  │  存储配置清单      │ Agent    │                   │
│  │ Server   │ ←─────────────── │ 主机     │                   │
│  └──────────┘  Agent 定期拉取   └──────────┘                   │
│                   │                                             │
│                   ▼                                             │
│              应用配置变更                                        │
│                                                                 │
│  对比分析：                                                     │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │     特性       │   Push（Ansible）│  Pull（Puppet）│          │
│  ├────────────────┼────────────────┼────────────────┤          │
│  │ 实时性         │ 高（立即执行）   │ 低（等待周期）  │          │
│  │ Agent 依赖     │ 无              │ 有              │          │
│  │ 防火墙友好     │ 需要 SSH 出口   │ 需要 Agent 入口 │          │
│  │ 扩展性         │ 中等            │ 高              │          │
│  │ 离线管理       │ 不支持          │ 支持            │          │
│  └────────────────┴────────────────┴────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Ansible 安装与配置

#### 2.1 安装方式

```bash
# 方法 1：使用 pip 安装（推荐，最灵活）
pip3 install ansible
pip3 install ansible-core    # 仅安装核心（更轻量）

# 方法 2：使用系统包管理器
# Ubuntu/Debian
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install -y ansible

# CentOS/RHEL/Rocky
sudo dnf install -y epel-release
sudo dnf install -y ansible

# 方法 3：使用 pipx（隔离环境，推荐用于开发）
pipx install ansible
pipx inject ansible pywinrm    # Windows 管理需要

# 验证安装
ansible --version
# ansible [core 2.17.x]
#   config file = /etc/ansible/ansible.cfg
#   configured module search path = ['/home/user/.ansible/plugins/modules']
#   ansible python module location = /usr/lib/python3/dist-packages/ansible
#   ansible collection location = /home/user/.ansible/collections
#   executable location = /usr/bin/ansible
#   python version = 3.12.x

# 查看已安装的模块数量
ansible-doc --list | wc -l

# 查看特定模块文档
ansible-doc yum
ansible-doc copy
```

#### 2.2 控制节点要求

```
┌─────────────────────────────────────────────────────────────────┐
│                   控制节点要求                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  操作系统：                                                      │
│  - Linux（推荐：RHEL, Ubuntu, Debian, Fedora）                   │
│  - macOS（支持）                                                 │
│  - Windows（不原生支持，使用 WSL）                                │
│                                                                 │
│  Python 版本：                                                   │
│  - Ansible 2.17+ 需要 Python 3.11+                              │
│  - Ansible 2.16 需要 Python 3.10+                               │
│                                                                 │
│  依赖软件：                                                      │
│  - OpenSSH（SSH 客户端）                                         │
│  - Python 3.11+                                                 │
│  - sshpass（可选，用于密码认证）                                  │
│                                                                 │
│  被管理节点要求：                                                 │
│  - SSH 服务运行                                                  │
│  - Python 2.7+ 或 Python 3.6+（用于执行模块）                    │
│  - 足够的临时磁盘空间（用于模块传输）                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Inventory 文件详解

Inventory 是 Ansible 管理的主机清单，定义了被管理节点的分组和连接参数。

#### 3.1 静态 Inventory（INI 格式）

```ini
# /etc/ansible/hosts 或自定义路径
# 最简单的 Inventory —— 直接列出主机
web01.example.com
web02.example.com
db01.example.com

# 使用 IP 地址
192.168.1.10
192.168.1.11

# 定义主机组
[webservers]
web01 ansible_host=10.0.1.10 ansible_port=22
web02 ansible_host=10.0.1.11 ansible_port=22
web03 ansible_host=10.0.1.12 ansible_ssh_user=deploy

[dbservers]
db01 ansible_host=10.0.2.10 ansible_port=22
db02 ansible_host=10.0.2.11 ansible_port=22

[cacheservers]
cache01 ansible_host=10.0.3.10

# 定义父组（组的组）
[production:children]
webservers
dbservers
cacheservers

# 组变量
[webservers:vars]
ansible_user=ansible
ansible_ssh_private_key_file=~/.ssh/ansible_key
http_port=80
app_env=production

[dbservers:vars]
ansible_user=postgres
db_port=5432

# 全局变量
[all:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

#### 3.2 静态 Inventory（YAML 格式）

```yaml
# inventory.yml
all:
  vars:
    ansible_python_interpreter: /usr/bin/python3
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no'

  children:
    production:
      children:
        webservers:
          hosts:
            web01:
              ansible_host: 10.0.1.10
              ansible_port: 22
            web02:
              ansible_host: 10.0.1.11
              ansible_port: 22
            web03:
              ansible_host: 10.0.1.12
              ansible_ssh_user: deploy
          vars:
            ansible_user: ansible
            ansible_ssh_private_key_file: ~/.ssh/ansible_key
            http_port: 80
            app_env: production

        dbservers:
          hosts:
            db01:
              ansible_host: 10.0.2.10
            db02:
              ansible_host: 10.0.2.11
          vars:
            ansible_user: postgres
            db_port: 5432

        cacheservers:
          hosts:
            cache01:
              ansible_host: 10.0.3.10

    staging:
      children:
        webservers_staging:
          hosts:
            staging-web01:
              ansible_host: 10.1.1.10
            staging-web02:
              ansible_host: 10.1.1.11
          vars:
            ansible_user: ansible
            app_env: staging
```

#### 3.3 Inventory 常用主机变量

```yaml
# 连接变量
ansible_host: 10.0.1.10              # 主机 IP 或域名
ansible_port: 22                      # SSH 端口
ansible_user: deploy                  # SSH 用户
ansible_ssh_pass: secret              # SSH 密码（不推荐）
ansible_ssh_private_key_file: ~/.ssh/id_rsa  # SSH 私钥
ansible_ssh_common_args: '-o ProxyCommand="ssh -W %h:%p jump.example.com"'  # 跳板机
ansible_connection: ssh               # 连接类型（ssh/winrm/paramiko/local）
ansible_become: true                  # 是否提权
ansible_become_method: sudo           # 提权方式
ansible_become_user: root             # 提权用户
ansible_become_pass: secret           # 提权密码（不推荐）
ansible_python_interpreter: /usr/bin/python3  # Python 路径
ansible_shell_type: sh                # Shell 类型

# Windows 特有变量
ansible_connection: winrm
ansible_winrm_transport: ntlm
ansible_winrm_server_cert_validation: ignore
ansible_port: 5986
```

### 4. ansible.cfg 配置详解

Ansible 使用层级配置系统，配置项可以定义在多个位置，按优先级从高到低：

```
┌─────────────────────────────────────────────────────────────────┐
│              ansible.cfg 配置优先级（从高到低）                    │
│                                                                 │
│  1. ANSIBLE_CONFIG 环境变量                                      │
│     export ANSIBLE_CONFIG=/path/to/custom/ansible.cfg            │
│                                                                 │
│  2. ./ansible.cfg（当前目录）                                    │
│     项目级配置，最常用                                            │
│                                                                 │
│  3. ~/.ansible.cfg（用户家目录）                                 │
│     用户级配置                                                   │
│                                                                 │
│  4. /etc/ansible/ansible.cfg（系统级）                           │
│     全局默认配置                                                 │
│                                                                 │
│  ⚠️ 找到第一个配置文件后就停止搜索                                │
│  ⚠️ 不会合并多个配置文件                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.1 完整的 ansible.cfg 配置示例

```ini
# ansible.cfg — 项目级配置文件
# 以下是 SRE 生产环境推荐配置

[defaults]
# ── 基础设置 ──
inventory = ./inventory          # Inventory 文件路径
remote_user = ansible            # 默认远程用户
host_key_checking = False        # 禁用 SSH 主机密钥检查（首次连接时）
timeout = 30                     # SSH 连接超时时间（秒）
log_path = ./ansible.log         # 日志文件路径

# ── 并发与性能 ──
forks = 20                       # 并行执行的主机数（默认 5）
poll_interval = 5                # 异步任务轮询间隔（秒）
internal_poll_interval = 0.001   # 内部轮询间隔

# ── 重试与容错 ──
retry_files_enabled = True       # 启用重试文件
retry_files_save_path = ./retry  # 重试文件保存路径

# ── 事实缓存 ──
gathering = smart                # 事实收集策略（smart/implicit/explicit）
fact_caching = jsonfile          # 事实缓存类型
fact_caching_connection = /tmp/ansible_facts_cache
fact_caching_timeout = 86400     # 缓存过期时间（秒）

# ── 输出控制 ──
nocows = 1                       # 禁用 cowsay（服务器环境）
stdout_callback = yaml           # 输出格式（default/yaml/json/minimal）
display_skipped_hosts = False    # 不显示跳过的主机
display_ok_hosts = True          # 显示成功的主机
show_custom_stats = True         # 显示自定义统计

# ── 角色路径 ──
roles_path = ./roles:/etc/ansible/roles

# ── Vault 密码文件 ──
vault_password_file = ~/.vault_pass

# ── 标签 ──
# 可以通过标签控制执行哪些任务
# tags = always,deploy

[privilege_escalation]
# ── 提权配置 ──
become = True                    # 默认启用提权
become_method = sudo             # 提权方式
become_user = root               # 提权目标用户
become_ask_pass = False          # 不询问提权密码

[ssh_connection]
# ── SSH 连接优化 ──
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=no
control_path_dir = ~/.ansible/cp  # SSH 控制路径目录
control_path = %(directory)s/%%h-%%r  # SSH 控制路径
pipelining = True                # 启用流水线模式（显著提升性能）
retries = 3                      # SSH 连接重试次数

[winrm_connection]
# ── WinRM 连接配置（Windows 管理） ──
winrm_operation_timeout_sec = 60
winrm_read_timeout_sec = 70

[persistent_connection]
# ── 持久连接配置 ──
connect_timeout = 30             # 连接超时
command_timeout = 30             # 命令超时
```

#### 4.2 验证配置

```bash
# 查看当前生效的配置
ansible-config dump
ansible-config dump --only-changed    # 仅显示修改过的配置

# 查看配置文件路径
ansible-config view                    # 查看当前配置文件内容

# 验证 Inventory
ansible-inventory --list -y            # YAML 格式列出所有主机
ansible-inventory --graph              # 图形化显示主机分组
ansible-inventory --host web01         # 查看特定主机的变量

# 测试连接
ansible all -m ping                    # ping 所有主机
ansible webservers -m ping             # ping webservers 组
```

### 5. Ad-hoc 命令

Ad-hoc 命令是 Ansible 的单行命令，用于执行一次性任务，无需编写 Playbook。

#### 5.1 基本语法

```bash
ansible <主机模式> -m <模块名> -a '<模块参数>' [选项]

# 常用选项：
# -i <inventory>    指定 Inventory 文件
# -u <user>         指定远程用户
# -b                提权（become）
# -K                询问提权密码
# -f <forks>        并行数
# -k                询问 SSH 密码
# -C                检查模式（dry-run）
# -v/-vv/-vvv       详细输出级别
# --diff            显示文件差异
# --limit <host>    限制执行范围
# --tags <tags>     仅执行指定标签
```

#### 5.2 常用 Ad-hoc 命令示例

```bash
# ── 连接测试 ──
ansible all -m ping                                    # 测试所有主机连通性
ansible webservers -m ping -u deploy                   # 使用指定用户测试

# ── 系统信息收集 ──
ansible all -m setup                                    # 收集所有事实
ansible all -m setup -a 'filter=ansible_distribution'  # 仅收集发行版信息
ansible all -m setup -a 'filter=ansible_memory_mb'     # 收集内存信息
ansible all -m setup -a 'filter=ansible_processor_vcpus'  # 收集 CPU 信息

# ── 包管理 ──
ansible webservers -m yum -a 'name=nginx state=present' -b       # 安装 nginx（CentOS）
ansible webservers -m apt -a 'name=nginx state=present' -b       # 安装 nginx（Ubuntu）
ansible webservers -m yum -a 'name=nginx state=latest' -b        # 更新 nginx
ansible webservers -m yum -a 'name=nginx state=absent' -b        # 卸载 nginx

# ── 服务管理 ──
ansible webservers -m service -a 'name=nginx state=started' -b   # 启动服务
ansible webservers -m service -a 'name=nginx state=stopped' -b   # 停止服务
ansible webservers -m service -a 'name=nginx state=restarted' -b # 重启服务
ansible webservers -m service -a 'name=nginx enabled=yes' -b     # 设置开机自启

# ── 文件操作 ──
ansible all -m file -a 'path=/tmp/test state=directory mode=0755' -b  # 创建目录
ansible all -m copy -a 'src=./local.txt dest=/tmp/remote.txt' -b      # 复制文件
ansible all -m file -a 'path=/tmp/test state=absent' -b               # 删除文件/目录

# ── 执行命令 ──
ansible all -m command -a 'uptime'                    # 执行命令（不通过 shell）
ansible all -m shell -a 'df -h | grep /dev/sda'      # 执行 shell 命令
ansible all -m raw -a 'cat /etc/os-release'           # 原始 SSH 执行（无需 Python）

# ── 用户管理 ──
ansible all -m user -a 'name=sre state=present shell=/bin/bash' -b  # 创建用户
ansible all -m user -a 'name=sre state=absent' -b                    # 删除用户

# ── 高级用法 ──
# 并行执行 50 台主机
ansible all -m ping -f 50

# 限制特定主机
ansible webservers -m ping --limit web01

# 检查模式（dry-run）
ansible webservers -m yum -a 'name=nginx state=present' -b -C

# 详细输出
ansible all -m ping -vvv

# JSON 格式输出
ANSIBLE_STDOUT_CALLBACK=json ansible all -m setup -a 'filter=ansible_distribution'
```

#### 5.3 主机模式（Host Patterns）

```bash
# 所有主机
ansible all -m ping
ansible '*' -m ping

# 特定组
ansible webservers -m ping

# 多个组（并集）
ansible 'webservers:dbservers' -m ping

# 多个组（交集）
ansible 'webservers:&production' -m ping

# 排除
ansible 'webservers:!web03' -m ping

# 通配符
ansible 'web*.example.com' -m ping
ansible '192.168.1.*' -m ping

# 正则表达式
ansible '~web\d+' -m ping

# 组合使用
ansible 'webservers:dbservers:!db02' -m ping
```

### 6. SSH 连接管理

#### 6.1 SSH 密钥管理

```bash
# 生成 SSH 密钥对
ssh-keygen -t ed25519 -C "ansible@control-node" -f ~/.ssh/ansible_key

# 分发公钥到目标主机
ssh-copy-id -i ~/.ssh/ansible_key.pub ansible@web01
ssh-copy-id -i ~/.ssh/ansible_key.pub ansible@web02

# 批量分发公钥（使用 sshpass）
for host in web01 web02 db01 db02; do
    sshpass -p 'initial_password' ssh-copy-id -i ~/.ssh/ansible_key.pub ansible@${host}
done

# 验证无密码连接
ssh -i ~/.ssh/ansible_key ansible@web01 'hostname'
```

#### 6.2 SSH 优化配置

```bash
# ~/.ssh/config
# 跳板机配置
Host jump
    HostName jump.example.com
    User admin
    Port 22
    IdentityFile ~/.ssh/jump_key

# 通过跳板机连接内网主机
Host 10.0.*
    ProxyJump jump
    User ansible
    IdentityFile ~/.ssh/ansible_key
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# 连接复用（提升性能）
Host *
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

```bash
# 创建 SSH socket 目录
mkdir -p ~/.ssh/sockets
```

### 7. Ansible 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                Ansible 执行流程详解                              │
│                                                                 │
│  1. 解析命令/Playbook                                           │
│     │                                                           │
│     ▼                                                           │
│  2. 加载配置（ansible.cfg）                                     │
│     │                                                           │
│     ▼                                                           │
│  3. 解析 Inventory                                              │
│     │  - 构建主机列表                                           │
│     │  - 合并组变量                                             │
│     │  - 合并主机变量                                           │
│     │                                                           │
│     ▼                                                           │
│  4. 收集 Facts（setup 模块）                                    │
│     │  - 操作系统信息                                           │
│     │  - 网络配置                                               │
│     │  - 硬件信息                                               │
│     │                                                           │
│     ▼                                                           │
│  5. 执行任务                                                    │
│     │  - 对每个主机：                                           │
│     │    a. 建立 SSH 连接                                       │
│     │    b. 传输模块代码到临时目录                               │
│     │    c. 执行模块                                             │
│     │    d. 收集 JSON 结果                                      │
│     │    e. 清理临时文件                                        │
│     │                                                           │
│     ▼                                                           │
│  6. 汇总结果                                                    │
│     │  - 成功（ok）                                             │
│     │  - 变更（changed）                                        │
│     │  - 失败（failed）                                         │
│     │  - 跳过（skipped）                                        │
│     │                                                           │
│     ▼                                                           │
│  7. 生成重试文件（如有失败）                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8. SRE 实战：服务器批量初始化

```yaml
# inventory/hosts.yml
all:
  children:
    new_servers:
      hosts:
        server01:
          ansible_host: 10.0.1.10
        server02:
          ansible_host: 10.0.1.11
        server03:
          ansible_host: 10.0.1.12
      vars:
        ansible_user: root
        ansible_ssh_private_key_file: ~/.ssh/provision_key
```

```bash
# 使用 Ad-hoc 命令完成快速初始化

# 1. 测试连接
ansible new_servers -m ping

# 2. 设置主机名
ansible new_servers -m hostname -a 'name={{ inventory_hostname }}' -b

# 3. 创建运维用户
ansible new_servers -m user -a 'name=ansible state=present shell=/bin/bash create_home=yes' -b
ansible new_servers -m authorized_key -a 'user=ansible key="{{ lookup("file", "~/.ssh/ansible_key.pub") }}"' -b

# 4. 配置 sudo 免密
ansible new_servers -m copy -a 'content="ansible ALL=(ALL) NOPASSWD:ALL\n" dest=/etc/sudoers.d/ansible mode=0440' -b

# 5. 安装基础软件包
ansible new_servers -m yum -a 'name=vim,htop,net-tools,iotop,sysstat,tcpdump,jq state=present' -b

# 6. 配置 NTP 时间同步
ansible new_servers -m yum -a 'name=chrony state=present' -b
ansible new_servers -m service -a 'name=chronyd state=started enabled=yes' -b

# 7. 配置 sysctl 内核参数
ansible new_servers -m sysctl -a 'name=net.core.somaxconn value=65535 state=present reload=yes' -b
ansible new_servers -m sysctl -a 'name=vm.swappiness value=10 state=present reload=yes' -b

# 8. 配置文件描述符限制
ansible new_servers -m copy -a 'content="* soft nofile 655350\n* hard nofile 655350\n" dest=/etc/security/limits.d/99-ansible.conf mode=0644' -b

# 9. 配置 SSH 安全加固
ansible new_servers -m lineinfile -a 'path=/etc/ssh/sshd_config regexp="^#?PermitRootLogin" line="PermitRootLogin no"' -b
ansible new_servers -m lineinfile -a 'path=/etc/ssh/sshd_config regexp="^#?PasswordAuthentication" line="PasswordAuthentication no"' -b
ansible new_servers -m service -a 'name=sshd state=restarted' -b

# 10. 配置防火墙
ansible new_servers -m firewalld -a 'service=ssh state=enabled permanent=yes immediate=yes' -b

# 11. 重启所有服务器
ansible new_servers -m reboot -a 'reboot_timeout=300' -b
```

---

## 💻 实战练习

### 练习 1：搭建 Ansible 实验环境

**目标：** 使用 Vagrant 或 Docker 搭建多节点 Ansible 实验环境

```bash
# 创建项目目录
mkdir -p ~/ansible-lab/day126 && cd ~/ansible-lab/day126

# 方法 1：使用 Docker 创建实验环境
# docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  control:
    image: geerlingguy/docker-ubuntu2404-ansible
    container_name: ansible-control
    volumes:
      - .:/ansible
    working_dir: /ansible
    command: sleep infinity
    networks:
      ansible-net:
        ipv4_address: 172.20.0.10

  web01:
    image: geerlingguy/docker-ubuntu2404-ansible
    container_name: web01
    command: sleep infinity
    networks:
      ansible-net:
        ipv4_address: 172.20.0.11

  web02:
    image: geerlingguy/docker-centos9-ansible
    container_name: web02
    command: sleep infinity
    networks:
      ansible-net:
        ipv4_address: 172.20.0.12

networks:
  ansible-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
EOF

# 启动环境
docker-compose up -d

# 进入控制节点
docker exec -it ansible-control bash

# 在控制节点中配置 SSH
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
# 将公钥复制到 web01 和 web02
```

```ini
# inventory/hosts.ini
[webservers]
web01 ansible_host=172.20.0.11
web02 ansible_host=172.20.0.12

[all:vars]
ansible_user=root
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

```bash
# 测试连接
ansible all -m ping -i inventory/hosts.ini

# 收集系统信息
ansible all -m setup -a 'filter=ansible_distribution' -i inventory/hosts.ini
```

### 练习 2：Ad-hoc 命令批量管理

**目标：** 使用 Ad-hoc 命令完成 10 项常见的运维任务

```bash
# 1. 查看所有主机的系统信息
ansible all -m setup -a 'filter=ansible_distribution,ansible_kernel' -i inventory/hosts.ini

# 2. 检查磁盘使用率
ansible all -m shell -a 'df -h | head -5' -i inventory/hosts.ini

# 3. 检查内存使用
ansible all -m shell -a 'free -h' -i inventory/hosts.ini

# 4. 检查系统负载
ansible all -m shell -a 'uptime' -i inventory/hosts.ini

# 5. 创建目录
ansible all -m file -a 'path=/opt/app state=directory mode=0755 owner=root' -i inventory/hosts.ini

# 6. 复制文件
echo "Hello from Ansible" > /tmp/test.txt
ansible all -m copy -a 'src=/tmp/test.txt dest=/opt/app/test.txt mode=0644' -i inventory/hosts.ini

# 7. 安装软件包（在 Ubuntu 容器上）
ansible web01 -m apt -a 'name=curl state=present update_cache=yes' -i inventory/hosts.ini

# 8. 检查服务状态
ansible all -m shell -a 'systemctl is-active sshd || service ssh status' -i inventory/hosts.ini

# 9. 查看网络配置
ansible all -m shell -a 'ip addr show | grep "inet "' -i inventory/hosts.ini

# 10. 清理临时文件
ansible all -m file -a 'path=/opt/app state=absent' -i inventory/hosts.ini
```

### 练习 3：故障排查挑战

**目标：** 排查以下 Ansible 连接和执行故障

```bash
# 故障 1：SSH 连接超时
# 症状：ansible all -m ping 返回 "UNREACHABLE"
# 排查步骤：
ansible all -m ping -vvv 2>&1 | grep -E "connect|timeout|refused"
# 检查：
# - SSH 服务是否运行
# - 防火墙是否允许 22 端口
# - ansible_host 地址是否正确
# - 网络是否可达

# 故障 2：权限拒绝
# 症状：任务返回 "Permission denied"
# 排查步骤：
ansible all -m shell -a 'whoami' -b -K
# 检查：
# - ansible_user 是否正确
# - sudo 配置是否正确
# - SSH 密钥权限（600）

# 故障 3：Python 解释器未找到
# 症状："/usr/bin/python: No such file or directory"
# 解决：
ansible all -m setup -a 'filter=ansible_python' -e 'ansible_python_interpreter=/usr/bin/python3'

# 故障 4：主机密钥验证失败
# 症状：Host key verification failed
# 解决：
# 在 ansible.cfg 中设置：
# host_key_checking = False
# 或在 SSH 配置中：
# StrictHostKeyChecking no
```

---

## 🎯 面试题精选

### 1. Ansible 的无代理架构是如何工作的？

**参考答案：**
Ansible 通过 SSH（Linux）或 WinRM（Windows）连接到被管理节点。执行流程为：
1. 控制节点将 Python 模块代码打包为临时文件
2. 通过 SFTP 或 SCP 传输到被管理节点的临时目录（~/.ansible/tmp/）
3. 在被管理节点上执行模块（需要 Python 解释器）
4. 模块返回 JSON 格式的执行结果
5. 控制节点接收结果并清理临时文件

优势是被管理节点无需安装任何代理软件，降低了管理复杂度和安全风险。劣势是每次执行都需要建立 SSH 连接，相比 Agent 模式有额外开销。

### 2. Ansible 的 Inventory 有什么作用？支持哪些格式？

**参考答案：**
Inventory 是 Ansible 的主机清单，用于定义和组织被管理节点。它有以下作用：
- 定义被管理主机列表
- 将主机分组（如 webservers、dbservers）
- 定义组变量和主机变量
- 指定连接参数（IP、端口、用户、密钥等）

支持两种格式：
- **INI 格式**：传统格式，语法简单，适合小型环境
- **YAML 格式**：结构化更好，支持嵌套，适合复杂环境

此外还支持**动态 Inventory**，通过脚本或插件从云平台（AWS、GCP、Azure）或 CMDB 动态获取主机列表。

### 3. ansible.cfg 的配置优先级是什么？

**参考答案：**
Ansible 按以下优先级从高到低查找配置文件：
1. `ANSIBLE_CONFIG` 环境变量指定的文件
2. 当前目录下的 `ansible.cfg`
3. 用户家目录下的 `~/.ansible.cfg`
4. 系统级 `/etc/ansible/ansible.cfg`

**重要：** 找到第一个配置文件后就停止搜索，不会合并多个配置文件。推荐在每个 Ansible 项目中使用项目级 `ansible.cfg`，确保配置的一致性和可移植性。

### 4. Ad-hoc 命令和 Playbook 有什么区别？各自适用于什么场景？

**参考答案：**

| 维度 | Ad-hoc 命令 | Playbook |
|------|------------|----------|
| 语法 | 单行命令 | YAML 文件 |
| 可重复性 | 低（需要记住命令） | 高（文件版本控制） |
| 复杂任务 | 不支持 | 支持（条件、循环、模板） |
| 幂等性 | 取决于模块 | 内置支持 |
| 适用场景 | 一次性任务、快速验证 | 生产部署、配置管理 |

Ad-hoc 适用于：快速检查连通性、临时执行命令、收集信息。Playbook 适用于：服务器初始化、应用部署、配置管理。

### 5. Ansible 的 `connection: local` 和 `connection: ssh` 有什么区别？

**参考答案：**
- `connection: ssh`（默认）：通过 SSH 连接到远程主机执行任务，适用于管理远程服务器
- `connection: local`：在控制节点本地执行任务，适用于：
  - 管理本地资源（如本地文件操作）
  - 调用云 API（如 AWS、GCP 操作）
  - 在控制节点上运行 Terraform
  - 测试 Playbook 逻辑

### 6. 如何优化 Ansible 的执行性能？

**参考答案：**
1. **增加 forks 数量**：`ansible.cfg` 中设置 `forks = 20`（默认 5）
2. **启用 SSH 连接复用**：`ssh_args = -o ControlMaster=auto -o ControlPersist=60s`
3. **启用流水线模式**：`pipelining = True`（减少 SSH 连接次数）
4. **使用 fact 缓存**：`gathering = smart` + `fact_caching = jsonfile`
5. **使用异步任务**：`async` + `poll` 处理长时间运行的任务
6. **限制 fact 收集**：`gather_facts: no` 或仅收集需要的 fact
7. **使用 Mitogen**：Ansible 执行加速插件

### 7. 什么是 Ansible 的幂等性？举例说明。

**参考答案：**
幂等性是指无论执行多少次，结果都是相同的。例如：
- `apt: name=nginx state=present`：如果 nginx 已安装则跳过，不会重复安装
- `service: name=nginx state=started`：如果 nginx 已启动则跳过
- `file: path=/tmp/test state=directory`：如果目录已存在则跳过

`command` 和 `shell` 模块默认不是幂等的，需要使用 `creates`/`removes` 参数或配合 `when` 条件实现幂等性。

---

## 📚 深入阅读

- [Ansible 官方文档](https://docs.ansible.com/ansible/latest/)
- [Ansible Galaxy](https://galaxy.ansible.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Ansible for DevOps (Jeff Geerling)](https://www.ansiblefordevops.com/)
- [Ansible: Up and Running (Lorin Hochstein)](https://www.oreilly.com/library/view/ansible-up-and/9781098109141/)
- [Red Hat Ansible Automation Platform](https://www.redhat.com/en/technologies/management/ansible)

---

## ✅ 自检清单

- [ ] 理解 Ansible 无代理架构的原理（SSH + Python 模块）
- [ ] 能对比 Ansible、Puppet、Chef 的优劣势
- [ ] 完成 Ansible 安装并验证 `ansible --version`
- [ ] 能编写 INI 和 YAML 格式的 Inventory 文件
- [ ] 理解 Inventory 的组变量、主机变量和父子组
- [ ] 掌握 ansible.cfg 的配置优先级和常用参数
- [ ] 能使用 Ad-hoc 命令执行常见运维任务（ping、shell、copy、yum/apt、service）
- [ ] 理解主机模式（all、组名、通配符、交集、差集）
- [ ] 掌握 SSH 密钥管理和批量分发
- [ ] 理解 Ansible 的执行流程（解析 → 连接 → 传输 → 执行 → 返回）
- [ ] 能排查常见的连接和执行故障
