# Day 14: 第二周综合实战 — 搭建 LAMP 环境

> 📅 日期：2026-04-30
> 📖 学习主题：第二周综合实战 — 搭建 LAMP 环境
> ⏰ 计划学习时间：4-5 小时
> 📋 前置知识：Day 08-13（进程管理、systemd、磁盘管理、日志管理）

---

## 🎯 学习目标

完成 Day 14 的学习后，你应该掌握：
- 理解 LAMP 架构的完整请求处理流程（Apache + MySQL + PHP）
- 掌握 Apache 的 MPM 模块对比（prefork vs worker vs event）和选择策略
- 能够配置 Apache 虚拟主机（基于域名、基于端口、基于 IP）
- 理解 mod_php 和 PHP-FPM 的区别和选择
- 掌握 MySQL 安全初始化、用户权限管理和远程访问配置
- 能够从零搭建完整的 LAMP 环境并部署应用
- 能够排查 LAMP 环境的常见故障（500 错误、连接失败、白屏）
- 能够进行 LAMP 性能优化和安全加固

---

## 📖 核心知识点

### 1. LAMP 架构原理

#### 1.1 什么是 LAMP

```
LAMP = Linux + Apache + MySQL + PHP

用户请求处理流程：

  浏览器
    │
    │ HTTP/HTTPS 请求
    ▼
  ┌─────────────────────────────────────────────────┐
  │              Apache HTTP Server                  │
  │                                                  │
  │  1. 接收请求，解析 URL                           │
  │  2. 匹配 VirtualHost                            │
  │  3. 检查 .htaccess 规则                         │
  │  4. 判断请求类型：                               │
  │     ├── 静态文件 (.html/.css/.js/.png)           │
  │     │   → 直接读取文件，返回给客户端              │
  │     │                                           │
  │     └── PHP 文件 (.php)                          │
  │         → 交给 PHP 解释器处理                    │
  │                                                  │
  └──────────────────────┬──────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────┐
  │              PHP 解释器                           │
  │                                                  │
  │  方式 A: mod_php（Apache 模块）                   │
  │    → PHP 解释器嵌入 Apache 进程                   │
  │    → 每个 Apache 进程都包含 PHP                   │
  │                                                  │
  │  方式 B: PHP-FPM（独立进程管理器）                 │
  │    → Apache 通过 FastCGI 协议与 PHP-FPM 通信     │
  │    → PHP-FPM 独立管理 PHP 进程池                  │
  │                                                  │
  │  PHP 处理流程：                                   │
  │    1. 解析 PHP 代码                              │
  │    2. 执行业务逻辑                               │
  │    3. 可能需要查询数据库                          │
  │    4. 生成 HTML 输出                              │
  │                                                  │
  └──────────────────────┬──────────────────────────┘
                         │
                         │ SQL 查询
                         ▼
  ┌─────────────────────────────────────────────────┐
  │              MySQL / MariaDB                     │
  │                                                  │
  │  1. 接收 SQL 查询                                │
  │  2. 查询优化器选择执行计划                        │
  │  3. 执行查询，返回结果集                          │
  │  4. PHP 将结果渲染为 HTML                        │
  │                                                  │
  └─────────────────────────────────────────────────┘
```

#### 1.2 各组件角色

| 组件 | 角色 | 可选替代品 |
|------|------|-----------|
| **L** — Linux | 操作系统 | FreeBSD, Windows Server |
| **A** — Apache | Web 服务器 | Nginx, Caddy, LiteSpeed |
| **M** — MySQL | 关系型数据库 | MariaDB, PostgreSQL, SQLite |
| **P** — PHP | 服务端脚本语言 | Python, Perl, Ruby, Node.js |

#### 1.3 LAMP vs LEMP 对比

```
LAMP（Apache + mod_php）：
  浏览器 → Apache → mod_php（嵌入） → MySQL
  特点：配置简单，兼容性好，但内存占用大

LEMP（Nginx + PHP-FPM）：
  浏览器 → Nginx → FastCGI → PHP-FPM（独立） → MySQL
  特点：高并发性能好，内存占用小，但配置稍复杂

对比表：
┌─────────────┬──────────────────┬──────────────────┐
│ 维度         │ LAMP (Apache)    │ LEMP (Nginx)     │
├─────────────┼──────────────────┼──────────────────┤
│ 并发模型     │ 进程/线程         │ 事件驱动          │
│ 内存占用     │ 较高              │ 较低              │
│ 静态文件     │ 一般              │ 优秀              │
│ .htaccess   │ 支持              │ 不支持            │
│ 配置复杂度   │ 简单              │ 中等              │
│ 模块生态     │ 丰富              │ 较少              │
│ 适用场景     │ 共享主机、CMS     │ 高并发、API       │
└─────────────┴──────────────────┴──────────────────┘
```

---

### 2. Apache 深入

#### 2.1 MPM 模块对比

Apache 的 MPM（Multi-Processing Module）决定了它如何处理并发请求：

```
prefork MPM（进程模型）：
  ┌──────────────────────────────────────┐
  │  Apache 主进程 (root)                 │
  │  ├── 子进程 1 (www-data) → 处理请求 1 │
  │  ├── 子进程 2 (www-data) → 处理请求 2 │
  │  ├── 子进程 3 (www-data) → 等待       │
  │  └── ...                              │
  └──────────────────────────────────────┘
  每个进程处理一个请求，进程间完全隔离
  内存占用大，但稳定性好

worker MPM（线程模型）：
  ┌──────────────────────────────────────┐
  │  Apache 主进程 (root)                 │
  │  ├── 子进程 1                         │
  │  │   ├── 线程 1 → 处理请求 1          │
  │  │   ├── 线程 2 → 处理请求 2          │
  │  │   └── 线程 3 → 等待                │
  │  ├── 子进程 2                         │
  │  │   ├── 线程 1 → 处理请求 3          │
  │  │   └── ...                          │
  │  └── ...                              │
  └──────────────────────────────────────┘
  每个进程包含多个线程，线程共享进程内存
  内存占用较小，但线程安全问题

event MPM（事件驱动模型）：
  ┌──────────────────────────────────────┐
  │  Apache 主进程 (root)                 │
  │  ├── 子进程 1                         │
  │  │   ├── 工作线程 → 处理活跃请求       │
  │  │   └── 监听线程 → 管理 Keep-Alive   │
  │  ├── 子进程 2                         │
  │  └── ...                              │
  └──────────────────────────────────────┘
  worker 的增强版，专门优化 Keep-Alive 连接
  空闲的 Keep-Alive 连接不占用工作线程
```

**MPM 对比表：**

| 特性 | prefork | worker | event |
|------|---------|--------|-------|
| 并发模型 | 一个进程一个请求 | 一个线程一个请求 | 事件驱动+线程 |
| 内存占用 | 高 | 中 | 低 |
| Keep-Alive | 占用进程 | 占用线程 | 不占用线程 |
| 线程安全 | 无需考虑 | 需要线程安全 | 需要线程安全 |
| mod_php | 支持 | 不支持 | 不支持 |
| PHP-FPM | 支持 | 支持 | 支持 |
| 稳定性 | 最好 | 好 | 好 |
| 适用场景 | mod_php、兼容性 | 通用 | 高并发（推荐） |

```bash
# 查看当前使用的 MPM
apachectl -V | grep -i mpm
# Server MPM: event

# 切换 MPM（Ubuntu/Debian）
sudo a2dismod mpm_event
sudo a2enmod mpm_prefork
sudo systemctl restart apache2

# 切换 MPM（CentOS/RHEL）
# 编辑 /etc/httpd/conf.modules.d/00-mpm.conf
# 注释 LoadModule mpm_event_module，启用 mpm_prefork_module
```

#### 2.2 MPM 配置调优

```bash
# 查看当前 MPM 配置
# /etc/apache2/mods-available/mpm_event.conf

# event MPM 配置详解
<IfModule mpm_event_module>
    StartServers             3          # 启动时的子进程数
    MinSpareThreads         75          # 最小空闲线程数
    MaxSpareThreads        250          # 最大空闲线程数
    ThreadLimit             64          # 每进程最大线程数
    ThreadsPerChild         25          # 每进程默认线程数
    MaxRequestWorkers      150          # 最大并发请求数（= 子进程数 × 线程数）
    MaxConnectionsPerChild   0          # 每进程最大请求数（0=无限）
    # 建议设为非零值，防止内存泄漏
    # 如 10000，每个进程处理 10000 个请求后自动回收
</IfModule>

# 计算公式：
# MaxRequestWorkers = StartServers × ThreadsPerChild
# 150 = 3 × 25 + 额外进程

# 根据内存调整：
# 每个 Apache 进程约占用 10-50MB 内存
# 如果服务器有 4GB 内存，预留给系统和其他服务 1GB
# 可用 3GB / 30MB ≈ 100 个进程
# 设置 MaxRequestWorkers = 100

# prefork MPM 配置
<IfModule mpm_prefork_module>
    StartServers             5
    MinSpareServers          5
    MaxSpareServers         10
    MaxRequestWorkers      150
    MaxConnectionsPerChild   0
</IfModule>
```

#### 2.3 虚拟主机配置

```bash
# ===== 基于域名的虚拟主机（最常用）=====
# 多个域名共享同一个 IP 地址

# 网站 1：example.com
sudo mkdir -p /var/www/example.com/public
sudo chown -R www-data:www-data /var/www/example.com

sudo tee /etc/apache2/sites-available/example.com.conf << 'EOF'
<VirtualHost *:80>
    ServerName example.com
    ServerAlias www.example.com
    ServerAdmin admin@example.com
    DocumentRoot /var/www/example.com/public

    <Directory /var/www/example.com/public>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/example.com-error.log
    CustomLog ${APACHE_LOG_DIR}/example.com-access.log combined
</VirtualHost>
EOF

# 网站 2：blog.example.com
sudo mkdir -p /var/www/blog.example.com/public
sudo tee /etc/apache2/sites-available/blog.example.com.conf << 'EOF'
<VirtualHost *:80>
    ServerName blog.example.com
    DocumentRoot /var/www/blog.example.com/public

    <Directory /var/www/blog.example.com/public>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/blog-error.log
    CustomLog ${APACHE_LOG_DIR}/blog-access.log combined
</VirtualHost>
EOF

# 启用站点
sudo a2ensite example.com.conf
sudo a2ensite blog.example.com.conf
sudo a2dissite 000-default.conf    # 禁用默认站点
sudo systemctl reload apache2

# ===== 基于端口的虚拟主机 =====
# 同一个 IP，不同端口

# 先在 ports.conf 中监听额外端口
echo "Listen 8080" | sudo tee -a /etc/apache2/ports.conf

sudo tee /etc/apache2/sites-available/api.conf << 'EOF'
<VirtualHost *:8080>
    ServerName api.example.com
    DocumentRoot /var/www/api/public

    <Directory /var/www/api/public>
        Require all granted
    </Directory>
</VirtualHost>
EOF

# ===== 基于 IP 的虚拟主机 =====
# 不同 IP 地址（多网卡场景）

<VirtualHost 192.168.1.10:80>
    ServerName site1.example.com
    DocumentRoot /var/www/site1
</VirtualHost>

<VirtualHost 192.168.1.20:80>
    ServerName site2.example.com
    DocumentRoot /var/www/site2
</VirtualHost>
```

#### 2.4 mod_php vs PHP-FPM

```
mod_php 方式：
  ┌──────────────────────────────────┐
  │  Apache 子进程                     │
  │  ├── Apache 核心                  │
  │  └── mod_php（PHP 解释器）         │
  │      └── 执行 PHP 代码            │
  └──────────────────────────────────┘
  PHP 解释器嵌入每个 Apache 进程
  每个进程都包含完整的 PHP 环境
  内存占用大，但配置简单

PHP-FPM 方式：
  ┌──────────────────────────────────┐
  │  Apache 子进程                     │
  │  ├── Apache 核心                  │
  │  └── mod_proxy_fcgi              │
  │      └── FastCGI 协议 ──────────→ ┐
  └──────────────────────────────────┘  │
                                        ▼
  ┌──────────────────────────────────┐
  │  PHP-FPM 进程池                    │
  │  ├── PHP 工作进程 1               │
  │  ├── PHP 工作进程 2               │
  │  └── PHP 工作进程 N               │
  └──────────────────────────────────┘
  Apache 和 PHP 独立运行
  PHP-FPM 管理自己的进程池
  内存占用小，可以独立调优

对比：
┌─────────────┬──────────────────┬──────────────────┐
│ 维度         │ mod_php          │ PHP-FPM          │
├─────────────┼──────────────────┼──────────────────┤
│ 配置复杂度   │ 简单              │ 中等              │
│ 内存占用     │ 高（每个进程含PHP）│ 低（独立进程池）  │
│ MPM 兼容     │ 仅 prefork       │ 全部 MPM         │
│ 性能         │ 一般              │ 好               │
│ 独立调优     │ 不支持            │ 支持              │
│ 多 PHP 版本  │ 不支持            │ 支持              │
│ Nginx 兼容   │ 不支持            │ 支持              │
│ 推荐程度     │ 开发环境          │ 生产环境（推荐）  │
└─────────────┴──────────────────┴──────────────────┘
```

```bash
# 启用 PHP-FPM（Ubuntu）
sudo apt install php8.1-fpm
sudo systemctl enable php8.1-fpm
sudo systemctl start php8.1-fpm

# Apache 配置使用 PHP-FPM
sudo a2enmod proxy_fcgi
sudo a2enconf php8.1-fpm

# 在虚拟主机或全局配置中
# /etc/apache2/conf-available/php8.1-fpm.conf
<FilesMatch \.php$>
    SetHandler "proxy:unix:/run/php/php8.1-fpm.sock|fcgi://localhost"
</FilesMatch>
```

#### 2.5 .htaccess 和 AllowOverride

```bash
# .htaccess 是目录级别的 Apache 配置文件
# 允许在不修改主配置的情况下覆盖设置

# 主配置中的 AllowOverride 控制 .htaccess 的权限
<Directory /var/www/html>
    AllowOverride None          # 不允许任何 .htaccess 覆盖
    AllowOverride All           # 允许所有 .htaccess 覆盖
    AllowOverride "AuthConfig FileInfo"  # 只允许特定指令
</Directory>

# AllowOverride 常用选项：
# All            - 允许所有指令
# None           - 禁止所有指令（性能最好）
# AuthConfig     - 认证相关（AuthUserFile, Require 等）
# FileInfo       - 文件类型相关（AddType, RewriteRule 等）
# Indexes        - 目录索引相关（DirectoryIndex, IndexOptions）
# Limit          - 访问控制（Allow, Deny）
# Options        - 目录选项（Options）

# 常见 .htaccess 用法：
# URL 重写（WordPress 必需）
RewriteEngine On
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]

# 密码保护目录
AuthType Basic
AuthName "Restricted Area"
AuthUserFile /var/www/.htpasswd
Require valid-user

# 自定义错误页面
ErrorDocument 404 /errors/404.html
ErrorDocument 500 /errors/500.html

# 性能考虑：
# AllowOverride All 允许 .htaccess，但每个请求都要读取目录链上的所有 .htaccess
# 生产环境建议 AllowOverride None，在主配置中直接写规则
```

---

### 3. MySQL 基础配置

#### 3.1 安全初始化

```bash
# 安装 MySQL/MariaDB
sudo apt install -y mariadb-server mariadb-client    # Ubuntu/Debian
# 或
sudo yum install -y mariadb-server mariadb-client    # CentOS/RHEL

# 启动服务
sudo systemctl enable mariadb
sudo systemctl start mariadb

# 安全初始化（非常重要！）
sudo mysql_secure_installation

# 交互过程：
# 1. Switch to unix_socket authentication? → Y
#    使用系统用户认证（Ubuntu 推荐）
# 2. Change the root password? → Y
#    设置 root 密码（强密码）
# 3. Remove anonymous users? → Y
#    删除匿名用户（安全）
# 4. Disallow root login remotely? → Y
#    禁止 root 远程登录（安全）
# 5. Remove test database? → Y
#    删除测试数据库（安全）
# 6. Reload privilege tables? → Y
#    刷新权限表
```

#### 3.2 用户权限管理

```bash
# 登录 MySQL
sudo mysql -u root -p

# ===== 创建用户 =====

# 创建本地用户
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';

# 创建远程用户（允许从特定 IP 连接）
CREATE USER 'app_user'@'192.168.1.%' IDENTIFIED BY 'StrongPassword123!';

# 创建远程用户（允许从任意 IP 连接，不推荐）
CREATE USER 'app_user'@'%' IDENTIFIED BY 'StrongPassword123!';

# ===== 授权 =====

# 授予特定数据库的所有权限
GRANT ALL PRIVILEGES ON myapp.* TO 'app_user'@'localhost';

# 授予只读权限
GRANT SELECT ON myapp.* TO 'readonly_user'@'localhost';

# 授予特定表的特定权限
GRANT SELECT, INSERT, UPDATE ON myapp.users TO 'app_user'@'localhost';

# 授予全局权限（谨慎！）
GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'monitor'@'localhost';

# ===== 刷新权限 =====
FLUSH PRIVILEGES;

# ===== 查看权限 =====
SHOW GRANTS FOR 'app_user'@'localhost';

# ===== 撤销权限 =====
REVOKE INSERT ON myapp.* FROM 'app_user'@'localhost';

# ===== 删除用户 =====
DROP USER 'app_user'@'localhost';

# ===== 最佳实践 =====
# 1. 每个应用使用独立的数据库用户
# 2. 最小权限原则（只授予需要的权限）
# 3. 禁止使用 root 连接应用
# 4. 使用强密码（包含大小写字母、数字、特殊字符）
# 5. 限制用户的来源 IP
```

#### 3.3 远程访问配置

```bash
# 默认情况下 MySQL 只监听 localhost
# 需要修改配置才能接受远程连接

# 1. 修改绑定地址
# 编辑 /etc/mysql/mariadb.conf.d/50-server.cnf（MariaDB）
# 或 /etc/mysql/mysql.conf.d/mysqld.cnf（MySQL）

# 将 bind-address 改为：
bind-address = 0.0.0.0    # 监听所有接口
# 或
bind-address = 192.168.1.10    # 只监听特定接口

# 2. 重启 MySQL
sudo systemctl restart mariadb

# 3. 创建远程用户
GRANT ALL PRIVILEGES ON myapp.* TO 'app_user'@'192.168.1.%' IDENTIFIED BY 'StrongPassword123!';
FLUSH PRIVILEGES;

# 4. 防火墙放行
sudo ufw allow from 192.168.1.0/24 to any port 3306

# 5. 测试远程连接
mysql -u app_user -p -h 192.168.1.10 -D myapp

# 安全考虑：
# - 不要 bind-address = 0.0.0.0 在公网服务器
# - 使用防火墙限制来源 IP
# - 使用 SSL 加密连接
# - 定期审计用户权限
```

#### 3.4 MySQL 关键配置

```bash
# /etc/mysql/mariadb.conf.d/50-server.cnf 关键参数

[mysqld]
# === 基础配置 ===
bind-address = 127.0.0.1         # 监听地址
port = 3306                       # 端口
datadir = /var/lib/mysql          # 数据目录
socket = /var/run/mysqld/mysqld.sock
pid-file = /var/run/mysqld/mysqld.pid

# === 字符集 ===
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# === InnoDB 配置 ===
innodb_buffer_pool_size = 1G      # 推荐为物理内存的 50-70%
innodb_log_file_size = 256M       # redo log 大小
innodb_flush_log_at_trx_commit = 1  # 1=每次提交刷盘（安全），2=每秒刷盘（快）
innodb_flush_method = O_DIRECT    # 跳过 OS 缓存

# === 连接配置 ===
max_connections = 200             # 最大连接数
wait_timeout = 600                # 空闲连接超时（秒）
interactive_timeout = 600

# === 查询缓存（MySQL 8.0 已移除）===
# query_cache_type = 0           # 禁用查询缓存
# query_cache_size = 0

# === 慢查询日志 ===
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2               # 超过 2 秒的查询记录

# === 错误日志 ===
log_error = /var/log/mysql/error.log
```

---

### 4. PHP 配置

#### 4.1 php.ini 关键参数

```bash
# PHP 配置文件位置
# /etc/php/8.1/apache2/php.ini    ← Apache + mod_php
# /etc/php/8.1/fpm/php.ini        ← PHP-FPM
# /etc/php/8.1/cli/php.ini        ← 命令行

# 查看当前配置
php -i | grep "Loaded Configuration File"
php -i | grep "memory_limit"

# 关键参数
```

| 参数 | 默认值 | 推荐值 | 说明 |
|------|--------|--------|------|
| `memory_limit` | 128M | 256M-512M | 单个脚本最大内存 |
| `max_execution_time` | 30 | 30-60 | 最大执行时间（秒） |
| `upload_max_filesize` | 2M | 50M-100M | 最大上传文件大小 |
| `post_max_size` | 8M | 100M | POST 数据最大大小 |
| `max_input_vars` | 1000 | 3000 | 最大输入变量数 |
| `date.timezone` | (空) | Asia/Shanghai | 时区设置 |
| `display_errors` | On | **Off** | 生产环境必须关闭 |
| `error_reporting` | E_ALL | E_ALL & ~E_DEPRECATED & ~E_STRICT | 错误报告级别 |
| `log_errors` | On | On | 记录错误到日志 |
| `error_log` | (空) | /var/log/php/error.log | 错误日志路径 |
| `session.save_handler` | files | files/redis/memcached | Session 存储方式 |
| `expose_php` | On | **Off** | 隐藏 PHP 版本信息 |
| `allow_url_fopen` | On | Off | 禁止 URL fopen（安全） |
| `disable_functions` | (空) | exec,passthru,... | 禁用危险函数 |

```bash
# 生产环境推荐配置
sudo vim /etc/php/8.1/fpm/php.ini

memory_limit = 256M
max_execution_time = 30
upload_max_filesize = 50M
post_max_size = 100M
max_input_vars = 3000
date.timezone = Asia/Shanghai
display_errors = Off
log_errors = On
error_log = /var/log/php/error.log
expose_php = Off
allow_url_fopen = Off
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,parse_ini_file,show_source

# 创建日志目录
sudo mkdir -p /var/log/php
sudo chown www-data:www-data /var/log/php
```

#### 4.2 PHP-FPM 配置

```bash
# PHP-FPM 配置文件
# /etc/php/8.1/fpm/pool.d/www.conf

# 查看 PHP-FPM 进程状态
sudo systemctl status php8.1-fpm
ps aux | grep php-fpm

# 关键配置
```

```ini
; /etc/php/8.1/fpm/pool.d/www.conf

; === 进程管理方式 ===
; static    - 固定数量的进程（适合专用服务器）
; dynamic   - 动态调整进程数（推荐）
; ondemand  - 按需创建进程（适合低流量）

pm = dynamic

; === 进程数配置 ===
pm.max_children = 50          ; 最大子进程数
pm.start_servers = 5          ; 启动时的进程数
pm.min_spare_servers = 3      ; 最小空闲进程数
pm.max_spare_servers = 10     ; 最大空闲进程数
pm.max_requests = 1000        ; 每个进程最大请求数（防内存泄漏）
pm.process_idle_timeout = 10s ; 空闲进程超时

; === 进程状态页面（监控用）===
pm.status_path = /fpm-status

; === 慢日志 ===
slowlog = /var/log/php/fpm-slow.log
request_slowlog_timeout = 5s

; === 超时配置 ===
request_terminate_timeout = 60s

; === 监听方式 ===
; Unix Socket（推荐，性能好）
listen = /run/php/php8.1-fpm.sock
; TCP Socket（跨服务器时使用）
; listen = 127.0.0.1:9000

; === 权限 ===
listen.owner = www-data
listen.group = www-data
listen.mode = 0660
```

**pm.max_children 调优：**
```bash
# 计算方法：
# 查看单个 PHP-FPM 进程的内存占用
ps aux | grep php-fpm | awk '{print $6/1024 " MB"}' | sort -n

# 假设每个进程约 30MB，服务器有 4GB 内存
# 预留 1GB 给系统和其他服务
# 可用 3GB / 30MB ≈ 100 个进程
# 设置 pm.max_children = 100

# 监控 PHP-FPM 状态
curl http://localhost/fpm-status
# 输出：
# pool:                 www
# process manager:      dynamic
# start time:           01/May/2026:10:00:00 +0800
# start since:          86400
# accepted conn:        12345
# listen queue:         0
# max listen queue:     0
# listen queue len:     128
# idle processes:       5
# active processes:     3
# total processes:      8
# max active processes: 50
# max children reached: 0
# slow requests:        0
```

---

### 5. 从零搭建完整 LAMP 环境

#### 5.1 系统准备

```bash
#!/bin/bash
# lamp-setup.sh — 从零搭建 LAMP 环境
set -euo pipefail

echo "=========================================="
echo "  LAMP 环境搭建脚本"
echo "  Ubuntu 22.04 + Apache 2.4 + MariaDB 10.6 + PHP 8.1"
echo "=========================================="

# 1. 更新系统
echo "[1/8] 更新系统..."
sudo apt update
sudo apt upgrade -y

# 2. 安装基础工具
echo "[2/8] 安装基础工具..."
sudo apt install -y curl wget vim git ufw htop net-tools

# 3. 配置时区
sudo timedatectl set-timezone Asia/Shanghai

# 4. 配置防火墙
echo "[3/8] 配置防火墙..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Apache Full'    # 80 + 443
sudo ufw --force enable
sudo ufw status
```

#### 5.2 安装 Apache

```bash
# 5. 安装 Apache
echo "[4/8] 安装 Apache..."
sudo apt install -y apache2

# 启动并设置开机自启
sudo systemctl enable apache2
sudo systemctl start apache2

# 验证
sudo systemctl status apache2
curl -sI http://localhost | head -5

# 查看 MPM
apachectl -V | grep -i mpm

# 启用常用模块
sudo a2enmod rewrite headers ssl proxy_fcgi
sudo systemctl restart apache2

# Apache 关键文件位置
echo "=== Apache 关键文件 ==="
echo "主配置文件: /etc/apache2/apache2.conf"
echo "站点配置:   /etc/apache2/sites-available/"
echo "已启用站点: /etc/apache2/sites-enabled/"
echo "模块配置:   /etc/apache2/mods-available/"
echo "默认根目录: /var/www/html"
echo "错误日志:   /var/log/apache2/error.log"
echo "访问日志:   /var/log/apache2/access.log"
```

#### 5.3 安装 MariaDB

```bash
# 6. 安装 MariaDB
echo "[5/8] 安装 MariaDB..."
sudo apt install -y mariadb-server mariadb-client

sudo systemctl enable mariadb
sudo systemctl start mariadb

# 安全初始化
echo ">>> 执行 mysql_secure_installation..."
echo ">>> 请按提示操作："
echo ">>>   Switch to unix_socket? → Y"
echo ">>>   Change root password? → Y（设置密码）"
echo ">>>   Remove anonymous users? → Y"
echo ">>>   Disallow root remote? → Y"
echo ">>>   Remove test database? → Y"
echo ">>>   Reload privileges? → Y"
sudo mysql_secure_installation

# 创建应用数据库和用户
echo "[6/8] 创建数据库..."
sudo mysql -u root -p << 'SQL'
CREATE DATABASE lamp_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lamp_user'@'localhost' IDENTIFIED BY 'LampPass123!';
GRANT ALL PRIVILEGES ON lamp_app.* TO 'lamp_user'@'localhost';
FLUSH PRIVILEGES;

USE lamp_app;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users (username, email) VALUES
    ('admin', 'admin@example.com'),
    ('user1', 'user1@example.com'),
    ('user2', 'user2@example.com');
SQL

echo "数据库创建完成"
mysql -u lamp_user -p'LampPass123!' -D lamp_app -e "SELECT * FROM users;"
```

#### 5.4 安装 PHP

```bash
# 7. 安装 PHP
echo "[7/8] 安装 PHP..."
sudo apt install -y \
    php8.1 \
    php8.1-fpm \
    php8.1-mysql \
    php8.1-cli \
    php8.1-common \
    php8.1-curl \
    php8.1-gd \
    php8.1-mbstring \
    php8.1-xml \
    php8.1-zip \
    php8.1-intl \
    php8.1-bcmath \
    php8.1-opcache \
    php8.1-readline

# 启用 PHP-FPM
sudo systemctl enable php8.1-fpm
sudo systemctl start php8.1-fpm

# 配置 Apache 使用 PHP-FPM
sudo a2enmod proxy_fcgi
sudo a2enconf php8.1-fpm
sudo systemctl restart apache2

# 生产环境 PHP 配置
sudo sed -i 's/display_errors = On/display_errors = Off/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/expose_php = On/expose_php = Off/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/upload_max_filesize = 2M/upload_max_filesize = 50M/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/post_max_size = 8M/post_max_size = 100M/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/memory_limit = 128M/memory_limit = 256M/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/;date.timezone =/date.timezone = Asia\/Shanghai/' /etc/php/8.1/fpm/php.ini

# 禁用危险函数
sudo sed -i 's/disable_functions =.*/disable_functions = exec,passthru,shell_exec,system,proc_open,popen,show_source/' /etc/php/8.1/fpm/php.ini

# 配置错误日志
sudo mkdir -p /var/log/php
sudo chown www-data:www-data /var/log/php
sudo sed -i 's|;error_log = /var/log/php|error_log = /var/log/php/error.log|' /etc/php/8.1/fpm/php.ini

# 配置 OPcache
sudo tee /etc/php/8.1/fpm/conf.d/10-opcache-custom.ini << 'EOF'
opcache.enable=1
opcache.memory_consumption=128
opcache.interned_strings_buffer=8
opcache.max_accelerated_files=10000
opcache.revalidate_freq=60
opcache.fast_shutdown=1
opcache.enable_cli=0
EOF

sudo systemctl restart php8.1-fpm
```

#### 5.5 部署测试应用

```bash
# 8. 部署测试应用
echo "[8/8] 部署测试应用..."

# 创建网站目录
sudo mkdir -p /var/www/lamp-app/public
sudo chown -R www-data:www-data /var/www/lamp-app

# 创建 PHP 应用
sudo tee /var/www/lamp-app/public/index.php << 'PHP'
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAMP 环境测试</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .success { color: green; } .error { color: red; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>LAMP 环境测试</h1>

    <h2>PHP 信息</h2>
    <p>PHP 版本: <?php echo PHP_VERSION; ?></p>
    <p>服务器: <?php echo $_SERVER['SERVER_SOFTWARE'] ?? 'Unknown'; ?></p>
    <p>操作系统: <?php echo php_uname('s') . ' ' . php_uname('r'); ?></p>

    <h2>数据库连接测试</h2>
    <?php
    try {
        $pdo = new PDO(
            'mysql:host=localhost;dbname=lamp_app;charset=utf8mb4',
            'lamp_user',
            'LampPass123!',
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
        echo '<p class="success">数据库连接成功！</p>';
        echo '<p>MySQL 版本: ' . $pdo->query("SELECT VERSION()")->fetchColumn() . '</p>';

        $users = $pdo->query("SELECT * FROM users ORDER BY id")->fetchAll(PDO::FETCH_ASSOC);
        echo '<table><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>创建时间</th></tr>';
        foreach ($users as $u) {
            echo "<tr><td>{$u['id']}</td><td>{$u['username']}</td><td>{$u['email']}</td><td>{$u['created_at']}</td></tr>";
        }
        echo '</table>';
    } catch (PDOException $e) {
        echo '<p class="error">数据库连接失败: ' . htmlspecialchars($e->getMessage()) . '</p>';
    }
    ?>

    <h2>PHP 扩展检查</h2>
    <?php
    $required = ['pdo_mysql', 'mbstring', 'curl', 'gd', 'xml', 'opcache', 'zip'];
    echo '<table><tr><th>扩展</th><th>状态</th></tr>';
    foreach ($required as $ext) {
        $status = extension_loaded($ext) ? '<span class="success">已安装</span>' : '<span class="error">未安装</span>';
        echo "<tr><td>{$ext}</td><td>{$status}</td></tr>";
    }
    echo '</table>';
    ?>
</body>
</html>
PHP

# 创建虚拟主机配置
sudo tee /etc/apache2/sites-available/lamp-app.conf << 'EOF'
<VirtualHost *:80>
    ServerName lamp.local
    ServerAlias www.lamp.local
    DocumentRoot /var/www/lamp-app/public

    <Directory /var/www/lamp-app/public>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </directory>

    # PHP-FPM
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/run/php/php8.1-fpm.sock|fcgi://localhost"
    </FilesMatch>

    # 日志
    ErrorLog ${APACHE_LOG_DIR}/lamp-app-error.log
    CustomLog ${APACHE_LOG_DIR}/lamp-app-access.log combined

    # 安全头
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options SAMEORIGIN
    Header always set X-XSS-Protection "1; mode=block"
</VirtualHost>
EOF

# 启用站点
sudo a2ensite lamp-app.conf
sudo a2dissite 000-default.conf
sudo a2enmod headers
sudo systemctl reload apache2

# 配置本地 hosts
echo "127.0.0.1 lamp.local" | sudo tee -a /etc/hosts

# 测试
echo "=== 测试完成 ==="
echo "访问 http://lamp.local 查看测试页面"
curl -s http://lamp.local | head -20
```

---

### 6. 故障排查

#### 6.1 Apache 500 错误

```bash
# 500 Internal Server Error 排查步骤

# 1. 查看 Apache 错误日志
sudo tail -20 /var/log/apache2/error.log
sudo tail -20 /var/log/apache2/lamp-app-error.log

# 2. 常见原因和解决

# 原因 A：PHP 语法错误
# 日志显示：PHP Parse error: syntax error, unexpected...
# 解决：修复 PHP 代码语法

# 原因 B：PHP 致命错误
# 日志显示：PHP Fatal error: Uncaught Error: Class 'PDO' not found
# 解决：安装缺少的 PHP 扩展
sudo apt install php8.1-mysql
sudo systemctl restart php8.1-fpm

# 原因 C：文件权限问题
# 日志显示：Permission denied: ... /var/www/...
# 解决：
sudo chown -R www-data:www-data /var/www/lamp-app
sudo chmod -R 755 /var/www/lamp-app
sudo chmod -R 644 /var/www/lamp-app/public/*.php

# 原因 D：.htaccess 错误
# 日志显示：Invalid command 'RewriteEngine'
# 解决：
sudo a2enmod rewrite
sudo systemctl restart apache2

# 原因 E：PHP-FPM 连接失败
# 日志显示：FastCGI: incomplete headers
# 解决：
sudo systemctl status php8.1-fpm
sudo systemctl restart php8.1-fpm

# 3. 临时开启 PHP 错误显示（仅调试！）
sudo sed -i 's/display_errors = Off/display_errors = On/' /etc/php/8.1/fpm/php.ini
sudo systemctl restart php8.1-fpm
# 测试完成后务必改回 Off
```

#### 6.2 MySQL 连接失败

```bash
# MySQL 连接失败排查步骤

# 1. 检查 MySQL 是否运行
sudo systemctl status mariadb
sudo ss -tlnp | grep 3306

# 2. 检查用户是否存在
sudo mysql -u root -p -e "SELECT user, host FROM mysql.user;"

# 3. 检查用户权限
sudo mysql -u root -p -e "SHOW GRANTS FOR 'lamp_user'@'localhost';"

# 4. 检查数据库是否存在
sudo mysql -u root -p -e "SHOW DATABASES;"

# 5. 检查 PHP 是否安装了 MySQL 扩展
php -m | grep -i mysql
# 应该有 mysqli 和 pdo_mysql

# 6. 检查 socket 文件
ls -la /var/run/mysqld/mysqld.sock
# 如果不存在：
sudo systemctl restart mariadb

# 7. 检查 PHP 配置中的 socket 路径
php -i | grep mysql.default_socket

# 常见错误信息：
# "Access denied for user" → 密码错误或用户不存在
# "Can't connect to MySQL server" → MySQL 未运行或 socket 不存在
# "Unknown database" → 数据库不存在
# "SQLSTATE[HY000] [2002] No such file or directory" → socket 文件路径错误
```

#### 6.3 PHP 白屏（White Screen of Death）

```bash
# PHP 白屏排查步骤

# 1. 开启错误显示
sudo sed -i 's/display_errors = Off/display_errors = On/' /etc/php/8.1/fpm/php.ini
sudo sed -i 's/error_reporting =.*/error_reporting = E_ALL/' /etc/php/8.1/fpm/php.ini
sudo systemctl restart php8.1-fpm

# 2. 查看 PHP 错误日志
sudo tail -20 /var/log/php/error.log
sudo tail -20 /var/log/php/fpm-slow.log

# 3. 常见原因

# 原因 A：PHP 致命错误（内存耗尽）
# 日志显示：PHP Fatal error: Allowed memory size of 134217728 bytes exhausted
# 解决：增加 memory_limit
sudo sed -i 's/memory_limit = 128M/memory_limit = 256M/' /etc/php/8.1/fpm/php.ini
sudo systemctl restart php8.1-fpm

# 原因 B：PHP 超时
# 解决：增加 max_execution_time
sudo sed -i 's/max_execution_time = 30/max_execution_time = 60/' /etc/php/8.1/fpm/php.ini
sudo systemctl restart php8.1-fpm

# 原因 C：缺少 PHP 扩展
# 在代码中添加错误报告
# ini_set('display_errors', 1);
# error_reporting(E_ALL);

# 原因 D：文件编码问题（BOM 头）
# 检查文件是否有 BOM 头
hexdump -C /var/www/lamp-app/public/index.php | head -1
# 如果前三个字节是 EF BB BF，说明有 BOM 头
# 解决：用 vim 去除 BOM
# vim file.php → :set nobomb → :wq

# 原因 E：OPcache 缓存了旧代码
# 解决：重启 PHP-FPM 清除缓存
sudo systemctl restart php8.1-fpm

# 4. 修复后务必关闭错误显示
sudo sed -i 's/display_errors = On/display_errors = Off/' /etc/php/8.1/fpm/php.ini
sudo systemctl restart php8.1-fpm
```

---

### 7. 性能优化

#### 7.1 Apache 优化

```bash
# 1. 启用 Keep-Alive
# /etc/apache2/apache2.conf
KeepAlive On
MaxKeepAliveRequests 100       # 每个连接最大请求数
KeepAliveTimeout 5             # Keep-Alive 超时时间（秒）

# 2. 启用压缩（mod_deflate）
sudo a2enmod deflate
# /etc/apache2/mods-available/deflate.conf
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml
    AddOutputFilterByType DEFLATE text/css text/javascript
    AddOutputFilterByType DEFLATE application/javascript application/json
    AddOutputFilterByType DEFLATE application/xml application/xhtml+xml
</IfModule>

# 3. 启用缓存（mod_expires）
sudo a2enmod expires
# /etc/apache2/mods-available/expires.conf
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
</IfModule>

# 4. 禁用不需要的模块
sudo a2dismod autoindex status info
sudo systemctl restart apache2

# 5. 隐藏版本信息
# /etc/apache2/conf-available/security.conf
ServerTokens Prod
ServerSignature Off
```

#### 7.2 MySQL 优化

```bash
# 1. InnoDB 缓冲池（最重要的参数）
# /etc/mysql/mariadb.conf.d/50-server.cnf
innodb_buffer_pool_size = 1G    # 物理内存的 50-70%

# 2. 查询缓存（MySQL 8.0 已移除）
# query_cache_type = 0          # 建议禁用

# 3. 慢查询日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# 4. 连接池
max_connections = 200
wait_timeout = 600

# 5. 分析慢查询
sudo mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# 6. 查看 MySQL 状态
mysql -u root -p -e "SHOW GLOBAL STATUS LIKE 'Threads_connected';"
mysql -u root -p -e "SHOW GLOBAL STATUS LIKE 'Slow_queries';"
mysql -u root -p -e "SHOW ENGINE INNODB STATUS\G" | head -50
```

#### 7.3 PHP OPcache 优化

```bash
# OPcache 将编译后的 PHP 代码缓存到共享内存中
# 避免每次请求都重新编译，显著提升性能

# /etc/php/8.1/fpm/conf.d/10-opcache.ini
opcache.enable=1
opcache.memory_consumption=128      # 共享内存大小（MB）
opcache.interned_strings_buffer=8   # 内部字符串缓冲区（MB）
opcache.max_accelerated_files=10000 # 最大缓存文件数
opcache.revalidate_freq=60          # 文件检查频率（秒）
opcache.fast_shutdown=1             # 快速关闭
opcache.enable_cli=0                # CLI 模式不启用

# 开发环境配置（每次修改立即生效）
opcache.revalidate_freq=0
opcache.validate_timestamps=1

# 查看 OPcache 状态
php -r "print_r(opcache_get_status());"

# OPcache 性能提升：
# - 首次请求：编译 PHP 代码 → 执行
# - 后续请求：直接执行缓存的字节码
# - 性能提升：30-50%
```

---

### 8. 安全加固

#### 8.1 目录权限

```bash
# 网站目录权限设置
# 所有文件属主设为 www-data
sudo chown -R www-data:www-data /var/www/lamp-app

# 目录权限 755（所有者 rwx，组 rx，其他 rx）
sudo find /var/www/lamp-app -type d -exec chmod 755 {} \;

# 文件权限 644（所有者 rw，组 r，其他 r）
sudo find /var/www/lamp-app -type f -exec chmod 644 {} \;

# 敏感配置文件（如 .env）权限 600
sudo chmod 600 /var/www/lamp-app/.env

# 禁止访问隐藏文件（.htaccess, .env, .git）
# Apache 配置
<DirectoryMatch "/\.">
    Require all denied
</DirectoryMatch>

# 或在 .htaccess 中
<FilesMatch "^\.">
    Require all denied
</FilesMatch>
```

#### 8.2 禁用危险 PHP 函数

```bash
# /etc/php/8.1/fpm/php.ini
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,
    curl_exec,curl_multi_exec,parse_ini_file,show_source,
    pcntl_exec,dl,pfsockopen,fsockopen

# 这些函数可以执行系统命令或加载外部代码
# 被黑客利用后可以完全控制服务器
```

#### 8.3 SQL 注入防护

```php
// 错误做法（字符串拼接，容易被注入）
$sql = "SELECT * FROM users WHERE username = '" . $_GET['username'] . "'";
// 攻击者输入: ' OR '1'='1
// 实际 SQL: SELECT * FROM users WHERE username = '' OR '1'='1'

// 正确做法（使用预处理语句）
$stmt = $pdo->prepare("SELECT * FROM users WHERE username = :username");
$stmt->execute(['username' => $_GET['username']]);
$users = $stmt->fetchAll(PDO::FETCH_ASSOC);

// PDO 配置防注入
$pdo = new PDO($dsn, $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_EMULATE_PREPARES => false,  // 禁用模拟预处理
]);
```

#### 8.4 完整安全检查清单

```bash
#!/bin/bash
# lamp-security-check.sh — LAMP 安全检查
set -euo pipefail

echo "=== LAMP 安全检查 $(date) ==="

# 1. Apache 版本隐藏
echo -e "\n[1] Apache 版本信息:"
curl -sI http://localhost | grep -i server
if curl -sI http://localhost | grep -q "Apache/"; then
    echo "  [WARN] 版本信息暴露，建议设置 ServerTokens Prod"
else
    echo "  [OK] 版本信息已隐藏"
fi

# 2. PHP 版本隐藏
echo -e "\n[2] PHP 版本信息:"
if curl -sI http://localhost | grep -qi "X-Powered-By"; then
    echo "  [WARN] PHP 版本暴露，建议设置 expose_php = Off"
else
    echo "  [OK] PHP 版本已隐藏"
fi

# 3. 目录列表
echo -e "\n[3] 目录列表:"
if curl -s http://localhost/ | grep -q "Index of"; then
    echo "  [WARN] 目录列表已启用，建议设置 Options -Indexes"
else
    echo "  [OK] 目录列表已禁用"
fi

# 4. MySQL 远程访问
echo -e "\n[4] MySQL 远程访问:"
if ss -tlnp | grep 3306 | grep -q "0.0.0.0"; then
    echo "  [WARN] MySQL 监听所有接口，建议绑定 127.0.0.1"
else
    echo "  [OK] MySQL 只监听本地"
fi

# 5. 文件权限
echo -e "\n[5] 网站目录权限:"
find /var/www -name ".env" -exec ls -la {} \; 2>/dev/null | while read line; do
    if echo "$line" | grep -q -v "^-rw-------"; then
        echo "  [WARN] .env 权限过宽: $line"
    fi
done

# 6. PHP 危险函数
echo -e "\n[6] PHP 危险函数:"
disabled=$(php -i 2>/dev/null | grep "disable_functions" | head -1)
if echo "$disabled" | grep -q "exec"; then
    echo "  [OK] 危险函数已禁用"
else
    echo "  [WARN] 建议禁用 exec, system, passthru 等函数"
fi

# 7. SSL/TLS
echo -e "\n[7] SSL/TLS:"
if apache2ctl -M 2>/dev/null | grep -q "ssl_module"; then
    echo "  [OK] SSL 模块已启用"
else
    echo "  [INFO] SSL 模块未启用（建议配置 HTTPS）"
fi

echo -e "\n=== 检查完成 ==="
```

---

## 💻 实战练习

### 练习 1：完整的 LAMP 自动化安装脚本

编写一个脚本，自动完成 LAMP 环境安装，包括：
- 安装 Apache、MariaDB、PHP
- 创建数据库和用户
- 创建虚拟主机
- 安全加固

```bash
#!/bin/bash
# lamp-auto-install.sh — LAMP 自动化安装
set -euo pipefail

# 配置变量
DB_ROOT_PASS="RootPass123!"
APP_DB="myapp"
APP_USER="myapp_user"
APP_PASS="AppPass456!"
APP_DOMAIN="myapp.local"

echo "=== LAMP 自动化安装开始 ==="

# 安装软件包
apt update
apt install -y apache2 mariadb-server \
    php8.1 php8.1-fpm php8.1-mysql php8.1-cli \
    php8.1-curl php8.1-gd php8.1-mbstring php8.1-xml \
    php8.1-zip php8.1-opcache

# 启动服务
systemctl enable apache2 mariadb php8.1-fpm
systemctl start apache2 mariadb php8.1-fpm

# 配置数据库
mysql -u root << SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PASS}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
CREATE DATABASE ${APP_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '${APP_USER}'@'localhost' IDENTIFIED BY '${APP_PASS}';
GRANT ALL ON ${APP_DB}.* TO '${APP_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

# 创建网站
mkdir -p /var/www/${APP_DOMAIN}/public
cat > /var/www/${APP_DOMAIN}/public/index.php << 'PHP'
<?php
echo "<h1>LAMP 环境搭建成功！</h1>";
echo "<p>PHP 版本: " . PHP_VERSION . "</p>";
echo "<p>MySQL 版本: ";
$pdo = new PDO('mysql:host=localhost', 'myapp_user', 'AppPass456!');
echo $pdo->query("SELECT VERSION()")->fetchColumn() . "</p>";
PHP
chown -R www-data:www-data /var/www/${APP_DOMAIN}

# 虚拟主机
cat > /etc/apache2/sites-available/${APP_DOMAIN}.conf << CONF
<VirtualHost *:80>
    ServerName ${APP_DOMAIN}
    DocumentRoot /var/www/${APP_DOMAIN}/public
    <Directory /var/www/${APP_DOMAIN}/public>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
CONF

a2ensite ${APP_DOMAIN}.conf
a2dissite 000-default.conf
a2enmod rewrite proxy_fcgi headers
a2enconf php8.1-fpm
systemctl reload apache2

echo "${APP_DOMAIN} 127.0.0.1" >> /etc/hosts

echo "=== 安装完成 ==="
echo "访问 http://${APP_DOMAIN}"
```

### 练习 2：排查 403 Forbidden

```bash
# 部署网站后访问返回 403 Forbidden，列出排查步骤

# 1. 检查目录权限
ls -la /var/www/myapp/public/
# Apache 用户（www-data）需要有读和执行权限

# 2. 检查父目录权限（需要 x 权限）
namei -l /var/www/myapp/public/index.html

# 3. 检查 Apache 配置中的 Require 指令
grep -r "Require" /etc/apache2/sites-available/

# 4. 检查是否有 index 文件
ls -la /var/www/myapp/public/
# 如果目录没有 index 文件且 Options -Indexes，会返回 403

# 5. 检查 SELinux/AppArmor
sudo aa-status | grep apache
# 如果 AppArmor 限制了 Apache，需要调整配置

# 6. 查看错误日志
sudo tail -5 /var/log/apache2/error.log

# 修复：
sudo chown -R www-data:www-data /var/www/myapp
sudo chmod -R 755 /var/www/myapp
```

### 练习 3：性能基准测试

```bash
# 使用 ab (Apache Benchmark) 进行性能测试

# 安装 ab
sudo apt install -y apache2-utils

# 基本测试：1000 个请求，100 个并发
ab -n 1000 -c 100 http://lamp.local/

# 输出关键指标：
# Requests per second:    500.00 [#/sec] (mean)
# Time per request:       200.000 [ms] (mean)
# Transfer rate:          1500.00 [Kbytes/sec] received

# PHP 动态页面测试
ab -n 500 -c 50 http://lamp.local/index.php

# 带 POST 数据的测试
ab -n 100 -c 10 -p data.txt -T 'application/x-www-form-urlencoded' http://lamp.local/api.php

# 优化前后对比：
# 优化前：50 req/s
# 启用 OPcache 后：150 req/s（3 倍提升）
# 启用 Keep-Alive 后：200 req/s
# 启用压缩后：180 req/s（传输量减少 60%）
```

---

## 🎯 面试题精选

### 1. Apache 的 prefork、worker、event MPM 如何选择？

**答：**
- **prefork**：每个请求一个进程，兼容 mod_php，稳定性最好。适用于需要 mod_php 的遗留系统。
- **worker**：每个请求一个线程，内存占用比 prefork 小。适用于通用场景。
- **event**：worker 的增强版，专门优化 Keep-Alive 连接。空闲的 Keep-Alive 不占用工作线程。**生产环境推荐**。
- **选择**：如果使用 PHP-FPM，选 event；如果必须用 mod_php，选 prefork。

### 2. PHP-FPM 的进程模型是什么？如何调优？

**答：** PHP-FPM 使用 master-worker 模型：
- **master 进程**：管理 worker 进程的生命周期
- **worker 进程**：处理实际的 PHP 请求
- **进程管理方式**：
  - `static`：固定数量的进程（适合专用服务器）
  - `dynamic`：动态调整进程数（推荐）
  - `ondemand`：按需创建进程（适合低流量）
- **调优**：`pm.max_children` = (可用内存 - 系统预留) / 单个进程内存。查看单个进程内存：`ps aux | grep php-fpm | awk '{print $6/1024 " MB"}'`

### 3. LAMP 和 LEMP 的主要区别是什么？

**答：**
- **LAMP**：Apache + mod_php 或 PHP-FPM。配置简单，支持 .htaccess，适合共享主机和 CMS。
- **LEMP**：Nginx + PHP-FPM。事件驱动模型，高并发性能好，内存占用小，适合 API 和高流量网站。
- **选择**：传统 CMS（WordPress）用 LAMP，高并发 API 用 LEMP。

### 4. Apache 的 AllowOverride 有什么作用？为什么生产环境建议关闭？

**答：** AllowOverride 控制 .htaccess 文件的权限。设为 All 时允许目录级别的配置覆盖。生产环境建议 AllowOverride None，因为在主配置中直接写规则性能更好（避免每个请求都读取目录链上的所有 .htaccess 文件）。

### 5. 如何排查 PHP 白屏问题？

**答：**
1. 临时开启 `display_errors = On` 和 `error_reporting = E_ALL`
2. 查看 PHP 错误日志 `/var/log/php/error.log`
3. 常见原因：内存耗尽（增加 `memory_limit`）、超时（增加 `max_execution_time`）、缺少扩展、BOM 头、OPcache 缓存

### 6. 如何防止 SQL 注入？

**答：**
1. 使用预处理语句（PDO prepared statements）
2. 设置 `PDO::ATTR_EMULATE_PREPARES => false`
3. 不要拼接 SQL 字符串
4. 使用 ORM 框架（Laravel、Doctrine）
5. 输入验证和过滤

### 7. OPcache 的工作原理是什么？

**答：** OPcache 将 PHP 脚本编译后的字节码（opcode）缓存到共享内存中。当请求到达时，直接执行缓存的字节码，跳过词法分析、语法分析和编译步骤。性能提升 30-50%。开发环境需要设置 `opcache.validate_timestamps=1` 和 `opcache.revalidate_freq=0`，以便代码修改立即生效。

### 8. 如何规划 MySQL 的 innodb_buffer_pool_size？

**答：** 推荐设为物理内存的 50-70%。例如 8GB 内存的服务器，设置 4-5GB。这个参数是 MySQL 最重要的性能参数，它决定了 InnoDB 能缓存多少数据和索引。可以通过 `SHOW ENGINE INNODB STATUS` 查看缓冲池命中率，命中率应保持在 99% 以上。

---

## 📚 深入阅读

- [Apache 官方文档](https://httpd.apache.org/docs/2.4/)
- [Apache MPM 模块](https://httpd.apache.org/docs/2.4/mod/mpm_common.html)
- [MariaDB 官方文档](https://mariadb.com/kb/en/documentation/)
- [PHP 官方手册](https://www.php.net/manual/zh/)
- [PHP-FPM 配置](https://www.php.net/manual/en/install.fpm.configuration.php)
- [Let's Encrypt — 免费 HTTPS 证书](https://letsencrypt.org/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

---

## ✅ 自检清单

- [ ] 理解 LAMP 架构的完整请求处理流程
- [ ] 能区分 Apache 的 prefork/worker/event MPM 并正确选择
- [ ] 能配置 Apache 虚拟主机（基于域名、端口、IP）
- [ ] 理解 mod_php 和 PHP-FPM 的区别和选择
- [ ] 能完成 MySQL 安全初始化和用户权限管理
- [ ] 能从零搭建完整的 LAMP 环境并部署应用
- [ ] 能排查 Apache 500 错误、MySQL 连接失败、PHP 白屏
- [ ] 能进行 Apache KeepAlive、MySQL 缓存、PHP OPcache 优化
- [ ] 能进行目录权限、危险函数禁用、SQL 注入防护等安全加固
- [ ] 能使用 ab 进行性能基准测试并分析结果
