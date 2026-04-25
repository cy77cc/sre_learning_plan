# Day 05: 文件权限管理 — chmod/chown/chgrp 与数字权限

> 📅 日期：2026-04-25  
> 📖 学习主题：文件权限管理 — chmod/chown/chgrp 与数字权限  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 05 的学习后，你应该掌握：
- 理解 文件权限管理 — chmod/chown/chgrp 与数字权限 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Linux 权限基础

Linux 是一个多用户系统，权限管理是系统安全的基石。

#### 1.1 权限的三个层级

| 层级 | 符号 | 含义 |
|------|------|------|
| 所有者 (Owner) | `u` | 文件的创建者 |
| 用户组 (Group) | `g` | 文件所属的用户组 |
| 其他用户 (Others) | `o` | 既不是所有者也不属于用户组的其他人 |
| 所有人 | `a` | 所有者 + 用户组 + 其他用户 |

#### 1.2 三种基本权限

| 权限 | 符号 | 数字 | 对文件的含义 | 对目录的含义 |
|------|------|------|-------------|-------------|
| 读取 (Read) | `r` | 4 | 可以查看文件内容 | 可以列出目录内容 (`ls`) |
| 写入 (Write) | `w` | 2 | 可以修改文件内容 | 可以在目录中创建/删除文件 |
| 执行 (Execute) | `x` | 1 | 可以执行文件 | 可以进入目录 (`cd`) |

#### 1.3 权限表示方法

**符号表示法**：`rwxrwxrwx`
- 第 1-3 位：所有者权限 (rwx)
- 第 4-6 位：用户组权限 (rwx)
- 第 7-9 位：其他用户权限 (rwx)

**数字表示法**：`755`, `644`, `600` 等
- 每个权限对应一个数字：r=4, w=2, x=1
- 三位数字之和：rwx = 4+2+1 = 7

**常用权限对照表**：

| 权限 | 数字 | 用途 |
|------|------|------|
| `rwx------` | 700 | 所有者完全控制，目录/脚本 |
| `rwxr-xr-x` | 755 | 所有者完全控制，其他人读和执行 |
| `rw-r--r--` | 644 | 所有者读写，其他人读（配置文件） |
| `rw-r-----` | 640 | 所有者读写，用户组读 |
| `rw-------` | 600 | 所有者读写（敏感文件，如私钥） |
| `rwxr-xr-x` | 755 | 可执行程序、脚本 |
| `r--------` | 400 | 极高敏感文件（私钥） |

---

### 2. chmod - 修改权限

#### 2.1 符号模式

```bash
chmod [who][+/-/=][permission] file...
```

**示例**：
```bash
# 给脚本添加执行权限
chmod +x deploy.sh

# 移除所有用户的写权限
chmod a-w file.txt

# 单独设置所有者权限
chmod u+x,g+r,o-rwx script.sh

# 设置精确权限（覆盖原有）
chmod u=rw,g=r,o= config.yaml

# 递归修改目录及所有子文件
chmod -R 755 /var/www/html/
```

#### 2.2 数字模式

```bash
chmod 755 file      # rwxr-xr-x
chmod 644 file      # rw-r--r--
chmod 700 file      # rwx------
chmod 600 file      # rw-------
```

#### 2.3 实战案例

**场景 1：部署 Web 应用**
```bash
# Web 目录权限（nginx 用户需要读权限）
chown -R www-data:www-data /var/www/html/
chmod -R 755 /var/www/html/
chmod 644 /var/www/html/index.html    # 配置文件不需执行
chmod +x /var/www/html/*.cgi          # CGI 脚本需要执行

# 上传目录（需要写权限）
chmod 775 /var/www/html/uploads/
chown www-data:www-data /var/www/html/uploads/
```

**场景 2：配置 SSH 密钥登录**
```bash
# SSH 私钥权限必须是 600
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub    # 公钥可以公开
chmod 700 ~/.ssh/              # SSH 目录必须安全

# 如果权限不对，SSH 会拒绝使用
# @ WARNING: UNPROTECTED PRIVATE KEY FILE! @
```

**场景 3：设置 Samba 共享目录**
```bash
# 共享目录需要 777 权限（或 775 + SGID）
chmod 777 /shared_data/
# 或
chmod 2775 /shared_data/   # SGID 继承用户组
chgrp sambashare /shared_data/
```

---

### 3. chown - 修改所有者和用户组

#### 3.1 基本语法

```bash
chown [选项] owner[:group] file...
chgrp [选项] group file...
```

#### 3.2 常用选项

| 选项 | 含义 |
|------|------|
| `-R` | 递归修改 |
| `-v` | 显示详细信息 |
| `--reference=RFILE` | 参考另一个文件的权限 |

#### 3.3 实战案例

```bash
# 修改文件所有者
chown nginx /etc/nginx/nginx.conf

# 修改所有者和用户组
chown nginx:nginx /var/log/nginx/

# 只修改用户组
chgrp www-data /var/www/html/

# 递归修改（目录及所有内容）
chown -R www-data:www-data /var/www/

# 参考另一个文件的权限
chown --reference=file1.txt file2.txt

# 批量修改（find + xargs）
find /var/www -type d -exec chown www-data:www-data {} \;
```

---

### 4. 特殊权限

#### 4.1 SUID (4000) - 执行时以所有者身份运行

```bash
# /usr/bin/passwd 需要 root 权限修改 /etc/passwd
ls -l /usr/bin/passwd
# -rwsr-xr-x 1 root root ... /usr/bin/passwd
#                   ^ s = SUID

# 设置 SUID
chmod u+s /path/to/file
chmod 4755 /path/to/file   # 4 = SUID
```

**注意**：SUID 很危险，应尽量避免使用。

#### 4.2 SGID (2000) - 执行时以用户组身份运行

```bash
# 设置 SGID
chmod g+s /path/to/file
chmod 2755 /path/to/file   # 2 = SGID
```

#### 4.3 Sticky Bit (1000) - 目录中只能删除自己的文件

```bash
# /tmp 目录使用了 Sticky Bit
ls -ld /tmp
# drwxrwxrwt 12 root root ... /tmp
#                   ^ t = Sticky Bit

# 这确保用户 A 不能删除用户 B 的文件

# 设置 Sticky Bit
chmod +t /shared_dir/
chmod 1777 /shared_dir/
```

#### 4.4 特殊权限组合示例

```bash
# Web 共享目录：所有者/用户组完全控制，其他人读和执行
chmod 2775 /var/www/shared/
# 2 = SGID：新文件继承用户组
# 7 = rwx：所有者完全控制
# 7 = rwx：用户组完全控制
# 5 = r-x：其他人读和执行

# 临时上传目录
chmod 3777 /tmp/uploads/
# 3 = SGID + Sticky Bit
# 确保文件安全又可写
```

---

### 5. ACL - 访问控制列表（精细化权限）

ACL 提供了比传统 Unix 权限更细粒度的控制。

#### 5.1 查看 ACL

```bash
# 查看文件 ACL
getfacl /path/to/file

# 示例输出：
# # file: test.txt
# owner: nginx
# group: nginx
# user::rw-
# user:www-data:rw-
# group::r--
# mask::rw-
# other::r--
```

#### 5.2 设置 ACL

```bash
# 给特定用户设置权限
setfacl -m u:www-data:rw /var/www/html/index.html

# 给特定用户组设置权限
setfacl -m g:developers:rx /var/www/html/

# 设置默认 ACL（目录中新文件自动继承）
setfacl -m d:u:www-data:rw /var/www/html/uploads/

# 移除 ACL
setfacl -x u:www-data /path/to/file

# 清除所有 ACL
setfacl -b /path/to/file
```

#### 5.3 实战案例

```bash
# 场景：nginx 需要读取 /home/user/docs/ 下的文件
# 但不让其他用户访问

# 方法 1：把 nginx 加入用户的主用户组
usermod -aG user nginx
setfacl -m g:nginx:rx /home/user/
setfacl -m g:nginx:rx /home/user/docs/

# 方法 2：直接给 nginx 用户设置 ACL
setfacl -m u:nginx:rx /home/user/docs/

# 验证
getfacl /home/user/docs/
getfacl /home/user/docs/ | grep nginx
```

---

### 6. 权限问题排查

#### 6.1 常见权限错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `Permission denied` | 无读取/执行权限 | `chmod +r file` 或 `chmod +x dir` |
| `Operation not permitted` | 无写入权限 | `chmod +w file` |
| `cannot create file` | 目录无写权限 | `chmod +w /parent/dir` |
| `Is a directory` | 对目录执行了文件操作 | 检查目标是否正确 |
| `ssh: permission denied (publickey)` | SSH 密钥权限不对 | `chmod 600 ~/.ssh/id_rsa` |

#### 6.2 排查流程

```bash
# 1. 查看当前权限
ls -la /path/to/problematic/file

# 2. 查看当前用户和所属组
id

# 3. 查看目录权限（往上追查所有父目录）
namei -l /path/to/problematic/file

# 4. 检查 ACL
getfacl /path/to/problematic/file

# 5. 如果是 SELinux 问题
ls -Z /path/to/file
getenforce
sestatus
```

#### 6.3 实战：排查 Nginx 403 Forbidden

```bash
# 1. 检查文件权限
ls -la /var/www/html/index.html
# 如果是 644，nginx 用户（通常是 www-data）有读权限

# 2. 检查目录权限
ls -la /var/www/
ls -la /var/www/html/
# 目录需要至少 755 (rwxr-xr-x)，且 nginx 用户有执行权限

# 3. 检查上级目录
namei -l /var/www/html/index.html

# 4. 检查 SELinux
getenforce   # 可能是 SELinux 阻止了 nginx 访问
# 如果是：semanage fcontext -a -t httpd_sys_content_t "/var/www/html(/.*)?"
#         restorecon -Rv /var/www/html

# 5. 检查 nginx 配置
grep "user" /etc/nginx/nginx.conf
# 确保 user nginx www-data; 与实际文件所有者匹配
```

---

### 7. 安全最佳实践

| 场景 | 推荐权限 |
|------|----------|
| 系统配置文件 | 644 (rw-r--r--) |
| 敏感配置（密码等） | 600 (rw-------) |
| SSH 私钥 | 600 |
| SSH 公钥 | 644 |
| Web 目录 | 755 (所有者 www-data) |
| Web 可写目录 | 775 (用户组 www-data) |
| CGI 脚本 | 755 |
| 日志文件 | 644 或 640 |
| /tmp 目录 | 1777 (Sticky Bit) |
| SUID 程序 | 4755 (尽量避免) |


---

## 💻 实战练习

### 练习 1：Web 服务权限配置

**场景**：部署新 Web 应用，配置严格的权限模型。

```bash
# 创建应用专用用户和组
groupadd webapp
useradd -r -g webapp -s /sbin/nologin -d /var/www/webapp webapp

# 设置目录权限（最小权限原则）
mkdir -p /var/www/webapp/{public,private,logs,tmp}
chown -R webapp:webapp /var/www/webapp
chmod 750 /var/www/webapp
chmod 640 /var/www/webapp/.env
chmod 600 /var/www/webapp/.env  # 敏感配置

# 上传目录（SGID 继承用户组）
chmod 2775 /var/www/webapp/public/uploads
```

### 练习 2：权限安全审计

```bash
#!/bin/bash
echo "777 权限文件（安全隐患）:"
find /var/www -type f -perm 777 -ls 2>/dev/null

echo "SUID 文件:"
find / -type f -perm /4000 -ls 2>/dev/null

echo "SSH 密钥权限:"
for f in /home/*/.ssh/id_rsa; do
    [ -f "$f" ] && {
        perm=$(stat -c %a "$f")
        [ "$perm" != "600" ] && echo "  $f: $perm (应为 600)"
    }
done
```


---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-04-25 10:58:13*  
*Generated by Hermes Agent with review*
