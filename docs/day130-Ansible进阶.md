# Day 130: Ansible 进阶

> 📅 日期：2026-05-08
> 📖 学习主题：动态 inventory、Vault 加密、性能优化、回调插件、自定义模块、Molecule 测试
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 129（Ansible Roles）

## 🎯 学习目标

- 掌握动态 Inventory 的原理和实现
- 熟练使用 Ansible Vault 加密敏感数据
- 掌握 Ansible 性能优化技巧
- 理解回调插件的工作原理
- 能编写简单的自定义模块
- 掌握 Molecule Role 测试框架

---

## 📖 核心知识点

### 1. 动态 Inventory

#### 1.1 什么是动态 Inventory

动态 Inventory 通过脚本或插件从外部数据源（云平台、CMDB、LDAP 等）动态获取主机列表，而非维护静态文件。

```
┌─────────────────────────────────────────────────────────────────┐
│                    静态 vs 动态 Inventory                        │
│                                                                 │
│  静态 Inventory：                                                │
│  ┌──────────────┐                                               │
│  │ hosts.yml    │ ──→ Ansible ──→ 执行任务                      │
│  │ 手动维护     │                                               │
│  └──────────────┘                                               │
│  问题：                                                         │
│  - 主机频繁变化时维护困难                                        │
│  - 无法反映实时状态                                              │
│  - 云环境主机 IP 动态变化                                        │
│                                                                 │
│  动态 Inventory：                                                │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │ AWS API      │    │ 动态脚本/    │                           │
│  │ GCP API      │───→│ 插件         │───→ Ansible ──→ 执行任务  │
│  │ CMDB         │    │              │                           │
│  │ Consul       │    └──────────────┘                           │
│  └──────────────┘                                               │
│  优势：                                                         │
│  - 实时反映基础设施状态                                          │
│  - 自动发现新主机                                                │
│  - 支持云平台原生标签过滤                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 编写动态 Inventory 脚本

```python
#!/usr/bin/env python3
"""
dynamic_inventory.py — 自定义动态 Inventory 脚本
支持 --list 和 --host 参数
"""

import argparse
import json
import sys

def get_inventory():
    """返回完整的 Inventory 数据"""
    inventory = {
        # 主机组定义
        "webservers": {
            "hosts": ["web01", "web02", "web03"],
            "vars": {
                "http_port": 80,
                "app_env": "production"
            }
        },
        "dbservers": {
            "hosts": ["db01", "db02"],
            "vars": {
                "db_port": 5432
            }
        },
        "cacheservers": {
            "hosts": ["cache01"],
            "vars": {
                "redis_port": 6379
            }
        },
        # 父组
        "production": {
            "children": ["webservers", "dbservers", "cacheservers"],
            "vars": {
                "env": "production"
            }
        },
        # 全局变量
        "_meta": {
            "hostvars": {
                "web01": {
                    "ansible_host": "10.0.1.10",
                    "ansible_port": 22,
                    "ansible_user": "ansible"
                },
                "web02": {
                    "ansible_host": "10.0.1.11",
                    "ansible_port": 22,
                    "ansible_user": "ansible"
                },
                "web03": {
                    "ansible_host": "10.0.1.12",
                    "ansible_port": 22,
                    "ansible_user": "ansible"
                },
                "db01": {
                    "ansible_host": "10.0.2.10",
                    "ansible_port": 22,
                    "ansible_user": "postgres"
                },
                "db02": {
                    "ansible_host": "10.0.2.11",
                    "ansible_port": 22,
                    "ansible_user": "postgres"
                },
                "cache01": {
                    "ansible_host": "10.0.3.10",
                    "ansible_port": 22,
                    "ansible_user": "redis"
                }
            }
        }
    }
    return inventory

def get_host(hostname):
    """返回特定主机的变量"""
    inventory = get_inventory()
    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    return hostvars.get(hostname, {})

def main():
    parser = argparse.ArgumentParser(description="Dynamic Inventory Script")
    parser.add_argument("--list", action="store_true", help="List all hosts and groups")
    parser.add_argument("--host", type=str, help="Get variables for a specific host")
    args = parser.parse_args()

    if args.list:
        inventory = get_inventory()
        # 移除 _meta（--list 时不需要）
        inventory.pop("_meta", None)
        print(json.dumps(inventory, indent=2))
    elif args.host:
        host_vars = get_host(args.host)
        print(json.dumps(host_vars, indent=2))
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

```bash
# 设置可执行权限
chmod +x dynamic_inventory.py

# 测试 --list
./dynamic_inventory.py --list

# 测试 --host
./dynamic_inventory.py --host web01

# 使用动态 Inventory
ansible -i dynamic_inventory.py all -m ping
ansible -i dynamic_inventory.py webservers -m ping
ansible-playbook -i dynamic_inventory.py site.yml
```

#### 1.3 AWS EC2 动态 Inventory 插件

```yaml
# inventory/aws_ec2.yml
---
plugin: amazon.aws.aws_ec2

regions:
  - us-east-1
  - us-west-2

# 使用 IAM Role 认证（推荐）
# 或设置 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 环境变量

# 主机过滤条件
filters:
  tag:Environment: production
  instance-state-name: running

# 按标签分组
keyed_groups:
  # 按环境分组
  - key: tags.Environment
    prefix: env
    separator: "_"
  # 按角色分组
  - key: tags.Role
    prefix: role
    separator: "_"
  # 按区域分组
  - key: placement.region
    prefix: region
    separator: "_"
  # 按实例类型分组
  - key: instance_type
    prefix: type
    separator: "_"

# 主机变量映射
compose:
  ansible_host: public_ip_address
  ansible_user: "'ec2-user'"
  ansible_ssh_private_key_file: "'~/.ssh/aws_key.pem'"
  private_ip: private_ip_address

# 排除特定主机
exclude_filters:
  - tag:Role: bastion

# 缓存配置
cache: true
cache_plugin: jsonfile
cache_timeout: 300
cache_connection: /tmp/aws_inventory_cache
```

```bash
# 安装 AWS 集合
ansible-galaxy collection install amazon.aws

# 使用
ansible-inventory -i inventory/aws_ec2.yml --list
ansible-inventory -i inventory/aws_ec2.yml --graph
ansible -i inventory/aws_ec2.yml all -m ping
```

### 2. Ansible Vault 加密

#### 2.1 Vault 基础操作

```bash
# ── 创建加密文件 ──
ansible-vault create secrets.yml
# 会提示输入密码，然后打开编辑器

# ── 加密已有文件 ──
ansible-vault encrypt vars/secrets.yml

# ── 查看加密文件内容 ──
ansible-vault view vars/secrets.yml

# ── 编辑加密文件 ──
ansible-vault edit vars/secrets.yml

# ── 解密文件 ──
ansible-vault decrypt vars/secrets.yml

# ── 修改密码 ──
ansible-vault rekey secrets.yml

# ── 加密单个字符串（内联加密） ──
ansible-vault encrypt_string 'SuperSecretPassword' --name 'db_password'
# 输出：
# db_password: !vault |
#   $ANSIBLE_VAULT;1.1;AES256
#   3832666538613533...
```

#### 2.2 Vault 密码管理

```bash
# 方法 1：交互式输入密码（默认）
ansible-playbook site.yml --ask-vault-pass

# 方法 2：密码文件（推荐用于自动化）
echo "MyVaultPassword" > ~/.vault_pass
chmod 600 ~/.vault_pass
ansible-playbook site.yml --vault-password-file ~/.vault_pass

# 方法 3：在 ansible.cfg 中配置
# [defaults]
# vault_password_file = ~/.vault_pass

# 方法 4：使用密码脚本（支持动态获取密码）
cat > vault_password.py << 'EOF'
#!/usr/bin/env python3
"""从密钥管理系统获取 Vault 密码"""
import subprocess
import sys

def get_password():
    # 示例：从 AWS Secrets Manager 获取
    # result = subprocess.run(
    #     ['aws', 'secretsmanager', 'get-secret-value',
    #      '--secret-id', 'ansible-vault-password',
    #      '--query', 'SecretString', '--output', 'text'],
    #     capture_output=True, text=True
    # )
    # return result.stdout.strip()

    # 示例：从文件读取
    with open('/etc/ansible/vault_pass', 'r') as f:
        return f.read().strip()

if __name__ == "__main__":
    print(get_password())
EOF
chmod +x vault_password.py
```

#### 2.3 Vault 最佳实践

```yaml
# 项目结构
ansible-project/
├── ansible.cfg
├── inventory/
│   ├── production/
│   │   ├── hosts.yml
│   │   ├── group_vars/
│   │   │   ├── all.yml              # 非敏感变量
│   │   │   ├── all_vault.yml        # 敏感变量（加密）
│   │   │   ├── webservers.yml
│   │   │   └── dbservers.yml
│   │   └── host_vars/
├── playbooks/
└── .vault_pass                       # 密码文件（不提交到 Git）
```

```yaml
# inventory/production/group_vars/all.yml
# 非敏感变量（明文）
app_name: mywebapp
app_port: 8080
nginx_port: 80
deploy_user: deploy
```

```yaml
# inventory/production/group_vars/all_vault.yml
# 敏感变量（加密）
$ANSIBLE_VAULT;1.1;AES256
3832666538613533...

# 解密后的内容：
# db_password: "SuperSecretDBPassword123"
# api_key: "sk-1234567890abcdef"
# slack_webhook: "https://hooks.slack.com/services/xxx"
# ssl_private_key: |
#   -----BEGIN RSA PRIVATE KEY-----
#   ...
#   -----END RSA PRIVATE KEY-----
```

```yaml
# 在 Playbook 中使用加密变量
# 变量名以 vault_ 前缀命名，便于识别
- name: Configure database
  mysql_user:
    name: "{{ db_user }}"
    password: "{{ vault_db_password }}"    # 来自加密文件
    priv: "*.*:ALL"
  no_log: true                              # 防止密码泄露到日志
```

### 3. 性能优化

#### 3.1 SSH 连接优化

```ini
# ansible.cfg
[ssh_connection]
# SSH 连接复用（最重要的优化）
ssh_args = -o ControlMaster=auto -o ControlPersist=600s -o StrictHostKeyChecking=no
control_path_dir = ~/.ansible/cp
control_path = %(directory)s/%%h-%%r

# 启用流水线模式（减少 SSH 连接次数）
pipelining = True

# SSH 保持连接
ssh_args = -o ServerAliveInterval=30 -o ServerAliveCountMax=5

# 使用 faster 异步 SSH
# ssh_args = -o ControlMaster=auto -o ControlPersist=300s
```

#### 3.2 并发与 Fact 优化

```ini
# ansible.cfg
[defaults]
# 增加并发数
forks = 50

# Fact 缓存策略
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts_cache
fact_caching_timeout = 86400

# 禁用不需要的 fact
# gather_facts: no  （在 Playbook 中）

# 或仅收集需要的 fact
# gather_facts: yes
# gather_subset:
#   - network
#   - hardware
```

```yaml
# 优化 gather_facts
- name: Optimized playbook
  hosts: webservers
  gather_facts: yes
  gather_subset:
    - "!all"          # 排除所有
    - network          # 仅收集网络
    - hardware         # 仅收集硬件
  tasks:
    - ...
```

#### 3.3 异步任务

```yaml
tasks:
  # 异步执行长时间任务
  - name: Run long database migration
    command: /opt/app/manage.py migrate
    async: 3600          # 最大执行时间（秒）
    poll: 0              # 不等待（0 = fire and forget）
    register: migration

  - name: Do other tasks while migration runs
    # ... 其他任务 ...

  - name: Wait for migration to complete
    async_status:
      jid: "{{ migration.ansible_job_id }}"
    register: job_result
    until: job_result.finished
    retries: 60
    delay: 10

  # 批量异步任务
  - name: Update all servers in parallel
    yum:
      name: "*"
      state: latest
    async: 600
    poll: 0
    register: update_jobs
    loop: "{{ groups['webservers'] }}"

  - name: Wait for all updates
    async_status:
      jid: "{{ item.ansible_job_id }}"
    loop: "{{ update_jobs.results }}"
    register: update_results
    until: item.finished
    retries: 60
    delay: 10
```

#### 3.4 Mitogen 加速插件

```bash
# 安装 Mitogen
pip3 install mitogen

# 在 ansible.cfg 中启用
# [defaults]
# strategy_plugins = /path/to/mitogen/ansible_mitogen/plugins/strategy
# strategy = mitogen_linear
```

### 4. 回调插件

#### 4.1 回调插件概述

回调插件在 Ansible 执行的不同阶段被调用，用于自定义输出、记录日志、发送通知等。

```
┌─────────────────────────────────────────────────────────────────┐
│                    回调插件生命周期                                │
│                                                                 │
│  Playbook 开始                                                  │
│      │                                                          │
│      ▼                                                          │
│  v2_playbook_on_start ──────────────────────────────            │
│      │                                                          │
│      ▼                                                          │
│  v2_playbook_on_play_start (每个 Play)                          │
│      │                                                          │
│      ▼                                                          │
│  v2_playbook_on_task_start (每个 Task)                          │
│      │                                                          │
│      ├── v2_runner_on_ok (任务成功)                             │
│      ├── v2_runner_on_failed (任务失败)                         │
│      ├── v2_runner_on_unreachable (主机不可达)                  │
│      ├── v2_runner_on_skipped (任务跳过)                        │
│      └── v2_runner_on_retry (任务重试)                          │
│      │                                                          │
│      ▼                                                          │
│  v2_playbook_on_stats (统计信息)                                │
│      │                                                          │
│      ▼                                                          │
│  v2_playbook_on_end ────────────────────────────────            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 常用回调插件

```ini
# ansible.cfg
[defaults]
# 输出格式
stdout_callback = yaml          # YAML 格式输出（更易读）
# stdout_callback = json        # JSON 格式输出
# stdout_callback = minimal     # 最小化输出
# stdout_callback = default     # 默认输出

# 启用回调插件
callback_whitelist = timer, profile_tasks, profile_roles
```

```yaml
# 使用 timer 插件查看执行时间
# 使用 profile_tasks 插件查看每个任务的执行时间
# 输出示例：
# Thursday 08 May 2026  10:30:00 +0800 (0:00:02.345)  0:00:15.678 ***
# ================================================================
# Install packages ----------------------------------------- 5.23s
# Deploy application code ---------------------------------- 3.45s
# Configure Nginx ------------------------------------------ 1.23s
# Start services ------------------------------------------- 0.89s
```

#### 4.3 自定义回调插件

```python
# callback_plugins/slack_notify.py
"""
Slack 通知回调插件
在 Playbook 执行完成或失败时发送 Slack 通知
"""

from ansible.plugins.callback import CallbackBase
import json
import os

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'slack_notify'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.webhook_url = os.environ.get('SLACK_WEBHOOK_URL', '')
        self.playbook_name = ''
        self.play_name = ''
        self.task_results = []

    def v2_playbook_on_start(self, playbook):
        self.playbook_name = playbook._file_name

    def v2_playbook_on_play_start(self, play):
        self.play_name = play.get_name()

    def v2_runner_on_ok(self, result):
        self.task_results.append({
            'task': result._task.get_name(),
            'host': result._host.get_name(),
            'status': 'ok',
            'changed': result._result.get('changed', False)
        })

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not ignore_errors:
            self.task_results.append({
                'task': result._task.get_name(),
                'host': result._host.get_name(),
                'status': 'failed',
                'msg': result._result.get('msg', 'Unknown error')
            })

    def v2_playbook_on_stats(self, stats):
        if not self.webhook_url or not HAS_URLLIB:
            return

        hosts = sorted(stats.processed.keys())
        summary = {}
        for host in hosts:
            s = stats.summarize(host)
            summary[host] = s

        # 检查是否有失败
        has_failures = any(s.get('failures', 0) > 0 for s in summary.values())
        status = "FAILED" if has_failures else "SUCCESS"
        color = "#ff0000" if has_failures else "#36a64f"

        message = {
            "attachments": [{
                "color": color,
                "title": f"Ansible Playbook: {self.playbook_name}",
                "text": f"Status: {status}",
                "fields": [
                    {
                        "title": host,
                        "value": f"OK: {s['ok']} | Changed: {s['changed']} | Failed: {s['failures']}",
                        "short": True
                    }
                    for host, s in summary.items()
                ]
            }]
        }

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(message).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
        except Exception as e:
            self._display.warning(f"Failed to send Slack notification: {e}")
```

### 5. 自定义模块

#### 5.1 模块开发基础

```python
# library/check_port.py
"""
检查远程端口是否开放的自定义模块
"""

from ansible.module_utils.basic import AnsibleModule
import socket

def check_port(host, port, timeout=5):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except socket.error:
        return False

def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            port=dict(type='int', required=True),
            timeout=dict(type='int', default=5),
            state=dict(type='str', default='started', choices=['started', 'stopped']),
        ),
        supports_check_mode=True
    )

    host = module.params['host']
    port = module.params['port']
    timeout = module.params['timeout']
    state = module.params['state']

    is_open = check_port(host, port, timeout)

    if state == 'started' and not is_open:
        module.fail_json(
            msg=f"Port {port} on {host} is not open",
            host=host,
            port=port
        )
    elif state == 'stopped' and is_open:
        module.fail_json(
            msg=f"Port {port} on {host} is open (expected closed)",
            host=host,
            port=port
        )
    else:
        module.exit_json(
            changed=False,
            msg=f"Port {port} on {host} is {'open' if is_open else 'closed'}",
            host=host,
            port=port,
            is_open=is_open
        )

if __name__ == '__main__':
    main()
```

```yaml
# 使用自定义模块
tasks:
  - name: Check if application port is open
    check_port:
      host: localhost
      port: 8080
      state: started
      timeout: 10
    register: port_check

  - name: Display result
    debug:
      msg: "Port 8080 is {{ 'open' if port_check.is_open else 'closed' }}"
```

#### 5.2 自定义 Lookup 插件

```python
# lookup_plugins/consul_kv.py
"""
从 Consul KV 读取配置的 Lookup 插件
"""

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
import json
import urllib.request

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        consul_url = kwargs.get('url', 'http://localhost:8500')
        results = []

        for term in terms:
            url = f"{consul_url}/v1/kv/{term}?raw"
            try:
                req = urllib.request.Request(url)
                response = urllib.request.urlopen(req)
                value = response.read().decode('utf-8')
                results.append(value)
            except Exception as e:
                raise AnsibleError(f"Failed to read Consul key '{term}': {e}")

        return results
```

```yaml
# 使用自定义 Lookup 插件
vars:
  db_password: "{{ lookup('consul_kv', 'config/db/password', url='http://consul:8500') }}"
  api_key: "{{ lookup('consul_kv', 'config/api/key', url='http://consul:8500') }}"
```

### 6. Molecule 测试框架

#### 6.1 Molecule 概述

Molecule 是 Ansible Role 的测试框架，支持在 Docker 容器中测试 Role。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Molecule 测试流程                              │
│                                                                 │
│  1. molecule create    ──→ 创建测试环境（Docker 容器）           │
│  2. molecule converge  ──→ 执行 Ansible Playbook                │
│  3. molecule idempotence ──→ 验证幂等性                         │
│  4. molecule verify    ──→ 运行验证测试                         │
│  5. molecule destroy   ──→ 销毁测试环境                         │
│                                                                 │
│  或者：molecule test ──→ 执行完整流程                           │
│                                                                 │
│  ┌─────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐      │
│  │ create  │→ │ converge  │→ │ idempot.  │→ │ verify  │      │
│  │         │  │           │  │           │  │         │      │
│  │ 启动    │  │ 执行      │  │ 再次执行  │  │ 验证    │      │
│  │ Docker  │  │ Playbook  │  │ 检查变更  │  │ 测试    │      │
│  └─────────┘  └───────────┘  └───────────┘  └─────────┘      │
│       │                                                       │
│       ▼                                                       │
│  ┌─────────┐                                                  │
│  │ destroy │                                                  │
│  │ 清理    │                                                  │
│  └─────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.2 安装和初始化

```bash
# 安装 Molecule
pip3 install molecule molecule-docker ansible-lint yamllint

# 在 Role 目录中初始化
cd roles/nginx
molecule init scenario default --driver-name docker

# 查看生成的目录结构
tree molecule/
# molecule/
# └── default/
#     ├── converge.yml        # 测试 Playbook
#     ├── molecule.yml        # Molecule 配置
#     └── verify.yml          # 验证测试
```

#### 6.3 Molecule 配置

```yaml
# roles/nginx/molecule/default/molecule.yml
---
dependency:
  name: galaxy
  options:
    role-file: requirements.yml
    roles-path: /tmp/molecule/roles

driver:
  name: docker

platforms:
  - name: nginx-ubuntu
    image: geerlingguy/docker-ubuntu2404-ansible
    pre_build_image: true
    privileged: true
    command: ""
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    cgroupns_mode: host
    published_ports:
      - "8080:80"

  - name: nginx-centos
    image: geerlingguy/docker-rockylinux9-ansible
    pre_build_image: true
    privileged: true
    command: ""
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    cgroupns_mode: host
    published_ports:
      - "8081:80"

provisioner:
  name: ansible
  inventory:
    group_vars:
      all:
        nginx_port: 80
        nginx_server_name: "localhost"
  playbooks:
    converge: converge.yml
  options:
    vvv: true

verifier:
  name: ansible

scenario:
  name: default
  test_sequence:
    - dependency
    - cleanup
    - destroy
    - syntax
    - create
    - converge
    - idempotence
    - verify
    - cleanup
    - destroy
```

```yaml
# roles/nginx/molecule/default/converge.yml
---
- name: Converge
  hosts: all
  become: yes
  tasks:
    - name: Include nginx role
      include_role:
        name: nginx
```

```yaml
# roles/nginx/molecule/default/verify.yml
---
- name: Verify
  hosts: all
  become: yes
  tasks:
    - name: Verify Nginx is installed
      package:
        name: nginx
        state: present
      check_mode: yes
      register: nginx_installed

    - name: Assert Nginx is installed
      assert:
        that:
          - not nginx_installed.changed
        fail_msg: "Nginx is not installed"

    - name: Verify Nginx is running
      service:
        name: nginx
        state: started
        enabled: yes
      check_mode: yes
      register: nginx_service

    - name: Assert Nginx is running
      assert:
        that:
          - not nginx_service.changed
        fail_msg: "Nginx is not running"

    - name: Verify Nginx is listening
      uri:
        url: "http://localhost:{{ nginx_port }}/"
        method: GET
        status_code: 200
      register: nginx_response

    - name: Assert Nginx responds
      assert:
        that:
          - nginx_response.status == 200
        fail_msg: "Nginx is not responding on port {{ nginx_port }}"

    - name: Verify Nginx configuration
      command: nginx -t
      register: nginx_config_test
      changed_when: false

    - name: Assert Nginx config is valid
      assert:
        that:
          - nginx_config_test.rc == 0
        fail_msg: "Nginx configuration is invalid"
```

#### 6.4 运行 Molecule 测试

```bash
cd roles/nginx

# 运行完整测试流程
molecule test

# 仅创建环境
molecule create

# 仅执行 Playbook
molecule converge

# 验证幂等性
molecule idempotence

# 运行验证测试
molecule verify

# 登录测试容器
molecule login --host nginx-ubuntu

# 销毁环境
molecule destroy

# 查看日志
molecule --debug test
```

---

## 💻 实战练习

### 练习 1：编写动态 Inventory 脚本

**目标：** 编写一个从 JSON 文件读取主机信息的动态 Inventory 脚本

```python
#!/usr/bin/env python3
"""从 JSON 文件读取 Inventory"""
import json
import sys
import argparse

INVENTORY_FILE = "/etc/ansible/hosts.json"

def load_inventory():
    with open(INVENTORY_FILE) as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--host", type=str)
    args = parser.parse_args()

    inventory = load_inventory()

    if args.list:
        print(json.dumps(inventory, indent=2))
    elif args.host:
        hostvars = inventory.get("_meta", {}).get("hostvars", {})
        print(json.dumps(hostvars.get(args.host, {}), indent=2))

if __name__ == "__main__":
    main()
```

### 练习 2：Vault 加密实践

**目标：** 使用 Vault 加密敏感变量并在 Playbook 中使用

```bash
# 1. 创建加密变量文件
ansible-vault create inventory/group_vars/all_vault.yml

# 2. 添加敏感变量
# db_password: "SecurePassword123!"
# api_key: "sk-1234567890abcdef"

# 3. 在 Playbook 中使用
ansible-playbook site.yml --ask-vault-pass

# 4. 使用密码文件
echo "MyVaultPass" > ~/.vault_pass
chmod 600 ~/.vault_pass
ansible-playbook site.yml --vault-password-file ~/.vault_pass
```

### 练习 3：Molecule 测试 Role

**目标：** 为自定义 Role 编写 Molecule 测试

```bash
# 1. 进入 Role 目录
cd roles/common

# 2. 初始化 Molecule
molecule init scenario default --driver-name docker

# 3. 配置 molecule.yml
# 4. 编写 converge.yml
# 5. 编写 verify.yml
# 6. 运行测试
molecule test
```

---

## 🎯 面试题精选

### 1. 什么是动态 Inventory？它解决了什么问题？

**参考答案：**
动态 Inventory 通过脚本或插件从外部数据源（云平台、CMDB、LDAP）实时获取主机列表。它解决了：
- 云环境中主机 IP 动态变化的问题
- 大规模环境中手动维护 Inventory 的困难
- 自动发现新创建的主机
- 根据标签/属性自动分组

### 2. Ansible Vault 的加密机制是什么？如何管理密码？

**参考答案：**
Vault 使用 AES256 加密算法。密码管理方式：
1. 交互式输入（`--ask-vault-pass`）
2. 密码文件（`--vault-password-file`）
3. 在 ansible.cfg 中配置 `vault_password_file`
4. 密码脚本（支持从密钥管理系统动态获取）

### 3. 如何优化 Ansible 的执行性能？

**参考答案：**
1. 增加 forks 数量（`forks = 50`）
2. 启用 SSH 连接复用（`ControlMaster=auto`）
3. 启用流水线模式（`pipelining = True`）
4. 使用 fact 缓存（`gathering = smart` + `fact_caching`）
5. 使用异步任务（`async` + `poll`）
6. 限制 fact 收集范围（`gather_subset`）
7. 使用 Mitogen 加速插件
8. 使用 `serial` 实现滚动更新

### 4. 回调插件的作用是什么？有哪些常用插件？

**参考答案：**
回调插件在 Ansible 执行的不同阶段被调用，用于自定义输出、记录日志、发送通知。常用插件：
- `timer`：显示每个 Play 的执行时间
- `profile_tasks`：显示每个任务的执行时间
- `profile_roles`：显示每个 Role 的执行时间
- `json`：JSON 格式输出
- `yaml`：YAML 格式输出
- `slack`/`email`：发送通知

### 5. 如何编写和使用自定义 Ansible 模块？

**参考答案：**
1. 在 `library/` 目录下创建 Python 文件
2. 使用 `AnsibleModule` 类定义参数和返回值
3. 实现模块逻辑
4. 使用 `module.exit_json()` 或 `module.fail_json()` 返回结果
5. 在 Playbook 中像内置模块一样调用

---

## 📚 深入阅读

- [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/)
- [Dynamic Inventory](https://docs.ansible.com/ansible/latest/inventory_guide/)
- [Ansible Performance](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Molecule Documentation](https://molecule.readthedocs.io/)
- [Ansible Module Development](https://docs.ansible.com/ansible/latest/dev_guide/)

---

## ✅ 自检清单

- [ ] 理解动态 Inventory 的原理和实现方式
- [ ] 能编写自定义动态 Inventory 脚本
- [ ] 掌握 Ansible Vault 的加密、解密、编辑操作
- [ ] 理解 Vault 密码管理的最佳实践
- [ ] 掌握 SSH 连接优化、fact 缓存、异步任务等性能优化技巧
- [ ] 理解回调插件的工作原理和常用插件
- [ ] 能编写简单的自定义模块
- [ ] 掌握 Molecule 测试框架的基本用法
