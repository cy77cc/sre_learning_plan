# Day 14: 第二周综合实战 — 搭建 LAMP 环境

> 📅 日期：2026-04-26
> 📖 学习主题：复习与实战：第二周综合实战 — 搭建 LAMP 环境
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 14 的学习后，你应该掌握：
- 理解 LAMP 架构：Linux + Apache/Nginx + MySQL/MariaDB + PHP
- 能在一台全新的 Ubuntu 服务器上从零搭建完整的 LAMP 环境
- 理解每个组件的作用和它们之间的协作关系
- 能配置虚拟主机（Virtual Host），部署多个网站
- 能排查 LAMP 环境的常见故障
- 理解生产环境的安全加固措施

---

## 📖 LAMP 架构概览

### 1. 什么是 LAMP

```
用户请求流程：
  浏览器 ──HTTP──→ Apache/Nginx（Web 服务器）
                          │
                          ├── 静态文件 (.html/.css/.js/.png) → 直接返回
                          │
                          └── 动态请求 (.php) ──→ PHP 解释器
                                                        │
                                                        ├── 业务逻辑处理
                                                        │
                                                        └── SQL 查询 ──→ MySQL（数据库）
                                                                                │
                                                                                └── 返回结果
                                                        │
                                                        └── HTML 响应 ──→ 用户浏览器
```

| 组件 | 角色 | 可选替代品 |
|------|------|-----------|
| **L** — Linux | 操作系统 | FreeBSD, Windows Server |
| **A** — Apache | Web 服务器 | Nginx, Caddy, LiteSpeed |
| **M** — MySQL | 关系型数据库 | MariaDB, PostgreSQL, SQLite |
| **P** — PHP | 服务端脚本语言 | Python, Perl, Ruby |

### 2. 为什么选 LAMP

**优势：**
- 全部开源免费，社区活跃
- 文档丰富，遇到问题容易搜索到解决方案
- 适合中小网站、博客、CMS（WordPress, Drupal, Joomla）
- 运维成熟度高，有大量自动化脚本和工具

**劣势：**
- PHP 在高并发场景不如 Node.js/Go
- Apache 比 Nginx 占用更多内存（每个连接一个进程/线程）
- 单体架构，不易水平扩展

### 3. LEMP 变体（Nginx + PHP-FPM）

```
Nginx 本身不能执行 PHP，需要借助 PHP-FPM（FastCGI 进程管理器）：

浏览器 ──→ Nginx
               │
               ├── 静态文件 → 直接返回（Nginx 擅长这个）
               │
               └── .php 请求 ──FastCGI──→ PHP-FPM
                                                │
                                                └── SQL ──→ MySQL

这种组合叫 LEMP（E 来自 Nginx 的发音 "engine x"）。
Nginx 处理静态文件的性能远超 Apache，所以现代部署更多用 LEMP。
```

---

## 🏗️ 实战：从零搭建 LAMP

### 环境

- OS：Ubuntu 22.04 LTS
- Web 服务器：Apache 2.4
- 数据库：MariaDB 10.6（MySQL 的社区兼容版）
- 脚本语言：PHP 8.1

### 第一步：系统准备

```bash
# 更新包索引
sudo apt update

# 升级已有包
sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget vim git ufw

# 配置时区
sudo timedatectl set-timezone Asia/Shanghai

# 检查系统信息
echo "=== 系统信息 ==="
hostnamectl
echo ""
echo "=== 内存 ==="
free -h
echo ""
echo "=== 磁盘 ==="
df -h /
echo ""
echo "=== CPU ==="
nproc
```

### 第二步：安装 Apache

```bash
sudo apt install -y apache2

# 启动并设置开机自启
sudo systemctl enable apache2
sudo systemctl start apache2

# 验证
sudo systemctl status apache2
# 应该显示 active (running)

# 测试 HTTP
curl -sI http://localhost
# 输出应包含：HTTP/1.1 200 OK

# Apache 的关键文件位置
# 配置文件：/etc/apache2/apache2.conf
# 站点配置：/etc/apache2/sites-available/
# 已启用的站点：/etc/apache2/sites-enabled/（符号链接）
# 模块配置：/etc/apache2/mods-available/ 和 mods-enabled/
# 默认网站根目录：/var/www/html
# 错误日志：/var/log/apache2/error.log
# 访问日志：/var/log/apache2/access.log

# Apache 的 MPM 模式（多进程处理模块）
# prefork：每个请求一个进程（兼容 mod_php）
# worker：每个请求一个线程（更省内存）
# event：worker 的增强版，处理长连接更好
apachectl -V | grep -i mpm
# Ubuntu 22.04 默认是 event

# 防火墙放行
sudo ufw allow 'Apache Full'    # 80 + 443
sudo ufw status
```

### 第三步：安装 MariaDB

```bash
sudo apt install -y mariadb-server mariadb-client

# 启动
sudo systemctl enable mariadb
sudo systemctl start mariadb

# 验证
sudo systemctl status mariadb
mysql --version

# 安全初始化（非常重要！）
sudo mysql_secure_installation

# 交互过程：
# 1. Switch to unix_socket authentication? → Y
# 2. Change the root password? → Y（设置强密码）
# 3. Remove anonymous users? → Y
# 4. Disallow root login remotely? → Y
# 5. Remove test database? → Y
# 6. Reload privilege tables? → Y

# 测试登录
sudo mysql -u root -p
# 输入刚才设置的密码

# 在 MariaDB 中执行：
CREATE DATABASE lamp_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lamp_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON lamp_app.* TO 'lamp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 验证新用户
mysql -u lamp_user -p -D lamp_app
# 能登录说明配置成功
```

### 第四步：安装 PHP

```bash
sudo apt install -y php8.1 libapache2-mod-php8.1 php8.1-mysql php8.1-cli php8.1-common

# 常用扩展（按需安装）
sudo apt install -y \
  php8.1-curl \
  php8.1-gd \
  php8.1-mbstring \
  php8.1-xml \
  php8.1-zip \
  php8.1-intl \
  php8.1-bcmath \
  php8.1-soap

# 重启 Apache 加载 PHP 模块
sudo systemctl restart apache2

# 创建测试页面
sudo tee /var/www/html/info.php > /dev/null << 'EOF'
<?php
phpinfo();
?>
EOF

# 在浏览器访问 http://你的IP/info.php
# 能看到 PHP 信息页面说明 PHP + Apache 集成成功

# ⚠️ 生产环境必须删除此文件（泄露敏感信息）
sudo rm /var/www/html/info.php
```

### 第五步：测试 LAMP 集成

创建一个简单的数据库连接测试页面：

```bash
sudo tee /var/www/html/db-test.php > /dev/null << 'PHPEOF'
<?php
$host = 'localhost';
$db   = 'lamp_app';
$user = 'lamp_user';
$pass = 'StrongPassword123!';
$charset = 'utf8mb4';

$dsn = "mysql:host=$host;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
    echo "✅ 数据库连接成功！\n";
    echo "MariaDB 版本: " . $pdo->query("SELECT VERSION()")->fetchColumn() . "\n";

    // 创建测试表
    $pdo->exec("CREATE TABLE IF NOT EXISTS test_users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        email VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // 插入测试数据
    $stmt = $pdo->prepare("INSERT INTO test_users (name, email) VALUES (?, ?)");
    $stmt->execute(["测试用户", "test@example.com"]);

    // 查询并显示
    $users = $pdo->query("SELECT * FROM test_users ORDER BY id DESC LIMIT 5")->fetchAll();
    echo "\n最近的用户：\n";
    foreach ($users as $u) {
        printf("  ID: %d, 名称: %s, 邮箱: %s, 创建: %s\n",
            $u['id'], $u['name'], $u['email'], $u['created_at']);
    }

} catch (\PDOException $e) {
    echo "❌ 数据库连接失败: " . $e->getMessage() . "\n";
    exit(1);
}
?>
PHPEOF

# 在浏览器访问 http://你的IP/db-test.php
# 应该看到 "✅ 数据库连接成功！" 和测试数据
```

### 第六步：配置虚拟主机（Virtual Host）

```bash
# 创建网站目录
sudo mkdir -p /var/www/myapp/public
sudo chown -R www-data:www-data /var/www/myapp
sudo chmod -R 755 /var/www/myapp

# 创建示例网站
sudo tee /var/www/myapp/public/index.php > /dev/null << 'EOF'
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>我的 LAMP 应用</title>
</head>
<body>
    <h1>🎉 LAMP 环境搭建成功！</h1>
    <p>PHP 版本: <?php echo PHP_VERSION; ?></p>
    <p>服务器: <?php echo $_SERVER['SERVER_SOFTWARE']; ?></p>
    <p>操作系统: <?php echo php_uname('s') . ' ' . php_uname('r'); ?></p>
</body>
</html>
EOF

# 创建虚拟主机配置
sudo tee /etc/apache2/sites-available/myapp.conf > /dev/null << 'EOF'
<VirtualHost *:80>
    ServerName myapp.example.com
    ServerAlias www.myapp.example.com
    ServerAdmin admin@example.com
    DocumentRoot /var/www/myapp/public

    <Directory /var/www/myapp/public>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # 日志
    ErrorLog ${APACHE_LOG_DIR}/myapp-error.log
    CustomLog ${APACHE_LOG_DIR}/myapp-access.log combined

    # 安全头
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options SAMEORIGIN
    Header always set X-XSS-Protection "1; mode=block"
</VirtualHost>
EOF

# 启用站点
sudo a2ensite myapp.conf
sudo a2dissite 000-default.conf    # 禁用默认站点

# 启用必要的模块
sudo a2enmod rewrite              # URL 重写（WordPress 等需要）
sudo a2enmod headers              # HTTP 头设置
sudo a2enmod ssl                  # HTTPS 支持

# 测试配置并重载
sudo apache2ctl configtest
sudo systemctl reload apache2

# 本地测试（如果没有 DNS，改 hosts 文件）
echo "127.0.0.1 myapp.example.com" | sudo tee -a /etc/hosts
curl -sI http://myapp.example.com
```

### 第七步：安全加固

```bash
# ===== Apache 安全 =====

# 1. 隐藏 Apache 版本信息
sudo sed -i 's/^ServerTokens OS/ServerTokens Prod/' /etc/apache2/conf-available/security.conf
sudo sed -i 's/^ServerSignature On/ServerSignature Off/' /etc/apache2/conf-available/security.conf
sudo systemctl reload apache2

# 验证
curl -sI http://localhost | grep Server
# 应该只显示 "Server: Apache"，不显示版本号

# 2. 禁用目录列表（防止浏览目录内容）
# 已在虚拟主机配置中设置 Options -Indexes

# 3. 禁用不需要的模块
sudo a2dismod autoindex           # 目录列表
sudo a2dismod status              # 服务器状态
sudo a2dismod info                # PHP 信息
sudo systemctl reload apache2

# ===== MariaDB 安全 =====

# 4. 只监听本地连接（不需要远程访问时）
sudo sed -i 's/^#bind-address/bind-address = 127.0.0.1/' /etc/mysql/mariadb.conf.d/50-server.cnf
sudo systemctl restart mariadb

# 验证
sudo ss -tlnp | grep 3306
# 应该显示 127.0.0.1:3306，不是 0.0.0.0:3306

# 5. 定期备份
sudo tee /etc/cron.daily/mysql-backup > /dev/null << 'SCRIPT'
#!/bin/bash
BACKUP_DIR="/var/backups/mysql"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u root -p'你的root密码' --all-databases \
  | gzip > "$BACKUP_DIR/all_db_$DATE.sql.gz"
# 保留最近 7 天的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
SCRIPT
sudo chmod +x /etc/cron.daily/mysql-backup

# ===== 系统安全 =====

# 6. 配置 fail2ban（防暴力破解）
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 7. 定期安全更新
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 🔧 常见故障排查

### 问题 1：Apache 启动失败

```bash
# 查看错误
sudo systemctl status apache2
sudo journalctl -u apache2 -n 50 --no-pager

# 测试配置文件
sudo apache2ctl configtest

# 常见原因：
# 1. 端口被占用：ss -tlnp | grep ':80'
# 2. 配置文件语法错误：apache2ctl configtest
# 3. 权限问题：检查 /var/www 目录权限
```

### 问题 2：PHP 页面显示源码而非执行

```bash
# 原因：Apache 没有加载 PHP 模块
# 检查
apache2ctl -M | grep php

# 如果没有输出，说明模块没加载
sudo a2enmod php8.1
sudo systemctl restart apache2

# 或者确认安装了 libapache2-mod-php8.1
dpkg -l | grep libapache2-mod-php
```

### 问题 3：数据库连接失败

```bash
# PHP 报错 "Access denied for user"
# 检查：

# 1. 用户是否存在
mysql -u root -p -e "SELECT user, host FROM mysql.user;"

# 2. 用户权限
mysql -u root -p -e "SHOW GRANTS FOR 'lamp_user'@'localhost';"

# 3. 数据库是否存在
mysql -u root -p -e "SHOW DATABASES;"

# 4. PHP 是否正确安装了 mysql 扩展
php -m | grep -i mysql
# 应该有 mysqli 和 pdo_mysql
```

### 问题 4：500 Internal Server Error

```bash
# 查看 Apache 错误日志
sudo tail -20 /var/log/apache2/error.log

# 查看 PHP 错误日志
sudo tail -20 /var/log/apache2/myapp-error.log

# 临时开启 PHP 错误显示（仅调试！）
sudo sed -i 's/display_errors = Off/display_errors = On/' /etc/php/8.1/apache2/php.ini
sudo sed -i 's/error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT/error_reporting = E_ALL/' /etc/php/8.1/apache2/php.ini
sudo systemctl restart apache2

# ⚠️ 修复后务必改回来！
```

---

## 🧪 练习题

### 练习 1：完整的 LAMP 安装脚本

编写一个脚本，自动完成 LAMP 环境安装，包括：
- 安装 Apache、MariaDB、PHP
- 创建数据库和用户
- 创建虚拟主机
- 安全加固

<details>
<summary>答案</summary>

```bash
#!/bin/bash
set -euo pipefail

DB_ROOT_PASS="ChangeMe123!"
APP_DB="myapp"
APP_USER="myapp_user"
APP_PASS="AppPass456!"
APP_DOMAIN="myapp.local"

echo "=== 安装 LAMP 环境 ==="

# 安装
sudo apt update
sudo apt install -y apache2 mariadb-server \
  php8.1 libapache2-mod-php8.1 php8.1-mysql php8.1-cli

# 启动服务
sudo systemctl enable apache2 mariadb
sudo systemctl start apache2 mariadb

# 配置数据库
sudo mysql << EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PASS}';
CREATE DATABASE ${APP_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '${APP_USER}'@'localhost' IDENTIFIED BY '${APP_PASS}';
GRANT ALL ON ${APP_DB}.* TO '${APP_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

# 创建网站
sudo mkdir -p /var/www/myapp/public
sudo tee /var/www/myapp/public/index.php > /dev/null << 'INDEX'
<?php echo "LAMP is working! PHP " . PHP_VERSION; ?>
INDEX
sudo chown -R www-data:www-data /var/www/myapp

# 虚拟主机
sudo tee /etc/apache2/sites-available/myapp.conf > /dev/null << VHOST
<VirtualHost *:80>
    ServerName ${APP_DOMAIN}
    DocumentRoot /var/www/myapp/public
    <Directory /var/www/myapp/public>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
VHOST
sudo a2ensite myapp.conf
sudo a2dissite 000-default.conf
sudo systemctl reload apache2

echo "✅ LAMP 安装完成！访问 http://${APP_DOMAIN}"
```
</details>

### 练习 2：排查 403 Forbidden

部署网站后访问返回 403 Forbidden，列出排查步骤。

<details>
<summary>答案</summary>

```bash
# 1. 检查目录权限
ls -la /var/www/myapp/public/
# Apache 用户（www-data）需要有读和执行权限

# 2. 检查父目录权限
namei -l /var/www/myapp/public/index.html

# 3. 检查 Apache 配置中的 Require 指令
grep -r "Require" /etc/apache2/sites-available/

# 4. 检查 SELinux/AppArmor
sudo aa-status | grep apache

# 5. 查看错误日志
sudo tail -5 /var/log/apache2/error.log

# 修复：
sudo chown -R www-data:www-data /var/www/myapp
sudo chmod -R 755 /var/www/myapp
```
</details>

---

## 📚 扩展阅读

- [Apache 官方文档](https://httpd.apache.org/docs/2.4/)
- [MariaDB 官方文档](https://mariadb.com/kb/en/documentation/)
- [PHP 官方手册](https://www.php.net/manual/zh/)
- [Let's Encrypt — 免费 HTTPS 证书](https://letsencrypt.org/) — 下一步：给你的 LAMP 加 HTTPS
