# Day 03: 文件操作命令

> 📅 日期：2026-04-15  
> 📖 学习主题：文件操作命令  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 03 的学习后，你应该掌握：
- 理解 文件操作命令 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. 文件操作基础命令

Linux 下一切皆文件，文件操作是每个 SRE 必须掌握的基础技能。

#### 1.1 创建和删除文件/目录

| 命令 | 用途 | 示例 |
|------|------|------|
| `touch` | 创建空文件或更新时间戳 | `touch file.txt` |
| `mkdir` | 创建目录 | `mkdir -p /path/to/deep/dir` |
| `rm` | 删除文件 | `rm -rf /tmp/old_files` |
| `rmdir` | 删除空目录 | `rmdir empty_dir/` |

**真实案例 - 批量创建文件**：
```bash
# 创建 30 天的日志文件（模拟日志场景）
for i in $(seq 1 30); do
    touch "/var/log/app_2024-01-$(printf '%02d' $i).log"
done
ls /var/log/app_*.log | wc -l   # 验证：30
```

**危险操作警示**：
```bash
# ⛔ 永远不要这样做！
rm -rf /      # 删除整个根目录
rm -rf /tmp/* ~   # 错误：空格会导致删掉 home 目录
rm -rf ./*~    # 错误：文件名以 ~ 开头可能被展开

# ✅ 安全做法：先预览再删除
ls /tmp/old_*          # 先看有哪些文件
rm -i /tmp/old_*       # 逐个确认删除
```

#### 1.2 复制和移动

| 命令 | 用途 | 示例 |
|------|------|------|
| `cp` | 复制文件/目录 | `cp -r src_dir/ dest_dir/` |
| `mv` | 移动或重命名 | `mv old_name new_name` |

**实战案例 - 备份配置文件**：
```bash
# 备份 Nginx 配置（每次修改前必做！）
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d%H%M%S)
cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup

# 批量复制并重命名（加水印日期）
for f in /data/logs/*.log; do
    cp "$f" "${f%.log}.backup.$(date +%Y%m%d)"
done
```

**移动并保持属性**：
```bash
# 移动整个目录（保留权限和属性）
mv -p /opt/old_service /opt/new_service

# 移动时创建目标目录
mkdir -p /backup/services
mv /opt/service_a /opt/service_b /backup/services/
```

#### 1.3 查看文件内容

| 命令 | 用途 | 特点 |
|------|------|------|
| `cat` | 查看小文件（一次性显示全部） | 内容多时屏幕飞速滚动 |
| `less` | **分页查看大文件**（推荐） | 支持搜索、上下滚动 |
| `more` | 分页查看（功能比 less 少） | 只能向下翻页 |
| `head` | 查看文件头部 | 默认 10 行 |
| `tail` | 查看文件尾部 | **最常用！日志分析必备** |
| `wc` | 统计行数/字数/字节 | `wc -l` 统计行数 |

**日志分析必备命令**：
```bash
# 实时监控日志文件（按 Ctrl+C 退出）
tail -f /var/log/syslog
tail -f /var/log/nginx/access.log

# 实时监控多个日志
tail -f /var/log/nginx/access.log /var/log/nginx/error.log

# 查看最后 100 行
tail -n 100 /var/log/nginx/access.log

# 从第 50 行开始显示（查看大文件尾部）
tail -n +50 /var/log/large_file.log

# 监控日志并高亮关键字
tail -f /var/log/nginx/access.log | grep --line-buffered "ERROR\|timeout"
```

**真实案例 - 分析 Nginx 日志**：
```bash
# 统计 PV（页面访问量）
wc -l /var/log/nginx/access.log

# 查看最新 20 条访问记录
tail -20 /var/log/nginx/access.log

# 查看有多少个独立 IP 访问
awk '{print $1}' /var/log/nginx/access.log | sort | uniq | wc -l

# 查找 404 错误
awk '$9 == 404 {print $7, $9}' /var/log/nginx/access.log | tail -20

# 统计每秒请求数
awk '{print $4}' /var/log/nginx/access.log | cut -d: -f2 | sort | uniq -c | sort -k1 -nr | head -10
```

---

### 2. find 命令 - 强大的文件查找工具

`find` 是 SRE 工作中最常用的命令之一，用于在目录树中查找文件。

#### 2.1 基础语法

```bash
find [路径] [条件] [动作]
```

#### 2.2 常用查找条件

| 条件 | 含义 | 示例 |
|------|------|------|
| `-name` | 按文件名查找 | `find /etc -name "*.conf"` |
| `-type f` | 只找文件 | `find / -type f -name "nginx.conf"` |
| `-type d` | 只找目录 | `find / -type d -name "nginx"` |
| `-mtime -N` | N 天内修改过的 | `find /var/log -mtime -7` |
| `-size +N` | 大于 N 大小的文件 | `find / -size +100M` |
| `-perm NNN` | 按权限查找 | `find / -perm 777` |
| `-user` | 按所有者查找 | `find /home -user www-data` |
| `-group` | 按用户组查找 | `find / -group sudo` |

**实战案例**：
```bash
# 查找所有 Nginx 配置文件
find /etc /usr -name "nginx*.conf" 2>/dev/null

# 查找 7 天内修改过的日志文件
find /var/log -name "*.log" -mtime -7 -ls

# 查找大于 100MB 的文件
find / -type f -size +100M -ls

# 查找所有 777 权限的文件（安全检查！）
find / -type f -perm 777 -ls 2>/dev/null

# 查找指定用户的所有文件
find / -user nginx -ls 2>/dev/null | head -20

# 查找空文件
find /tmp -type f -empty

# 查找并删除（删除 30 天前的旧日志）
find /var/log -name "*.log" -mtime +30 -delete
```

**危险操作 - 慎用 delete**：
```bash
# ⛔ 永远不要这样做！
find / -name "*.log" -delete   # 可能误删系统重要日志

# ✅ 安全做法：先找到，再加确认
find / -name "*.log" -mtime +30   # 先预览
find / -name "*.log" -mtime +30 -ok rm {} \;   # 逐个确认删除
```

#### 2.3 查找后执行动作

```bash
# 查找并显示详细信息
find /etc -name "*.conf" -ls

# 查找并复制到指定目录
find /var/log -name "*.log" -mtime -1 -exec cp {} /backup/logs/ \;

# 查找并打包（将 7 天前的日志打包）
find /var/log -name "*.log" -mtime +7 | xargs tar -czf logs_backup.tar.gz

# 查找所有 .conf 文件并统计行数
find /etc -name "*.conf" -exec wc -l {} + | sort -n
```

---

### 3. 链接文件 - ln 命令

Linux 有两种链接：硬链接和软链接（符号链接）。

#### 3.1 硬链接 vs 软链接

| 特性 | 硬链接 | 软链接 |
|------|--------|--------|
| 原理 | 同一文件的多个别名 | 指向另一个文件的路径 |
| 跨分区 | ❌ 不能跨文件系统 | ✅ 可以跨文件系统 |
| 目录 | ❌ 不能链接目录 | ✅ 可以链接目录 |
| 删除源文件 | 链接仍然有效（文件未删除） | 链接失效（断链） |

**实战案例**：
```bash
# 创建硬链接（备份配置文件）
ln /etc/nginx/nginx.conf /backup/nginx.conf.backup

# 创建软链接（Nginx 配置目录）
ln -s /etc/nginx/sites-enabled /etc/nginx/sites-enabled

# 查看链接（第二个字段是链接数）
ls -la /etc/nginx/
# lrwxrwxrwx 1 root root  4096 xxx sites-enabled -> ../sites-available/default

# 查找所有软链接
find /etc -type l -ls

# 查找断链（目标不存在的软链接）
find /etc -type l ! -exists
```

**软链接的实际应用**：
```bash
# 为常用目录创建快捷方式
ln -s /var/log/nginx /home/sre/nginx_logs

# 版本切换（软件多版本管理）
ln -sfn /opt/python3.10 /usr/local/python  # 切换默认 Python

# 创建临时链接访问其他位置的文件
ln -s /mnt/backup/data /var/www/html/backup
```

---

### 4. 管道和重定向

这是 Linux 最强大的特性之一，SRE 必须精通。

#### 4.1 输出重定向

| 符号 | 含义 | 示例 |
|------|------|------|
| `>` | 重定向输出（覆盖） | `echo "test" > file.txt` |
| `>>` | 追加重定向 | `echo "test" >> file.txt` |
| `2>` | 重定向错误输出 | `command 2> error.log` |
| `&>` | 重定向所有输出 | `command &> all.log` |
| `2>&1` | 错误输出重定向到标准输出 | `command > log.txt 2>&1` |

**实战案例**：
```bash
# 保存命令输出到文件
ls -la > file_list.txt

# 追加而不是覆盖
echo "=== $(date) ===" >> system_info.log
df -h >> system_info.log

# 将错误信息保存到文件
grep "error" /var/log/syslog 2> errors.txt

# 同时保存正确和错误输出
command > output.log 2>&1

# 静默丢弃输出（定时任务中常用）
command > /dev/null 2>&1
```

#### 4.2 管道 |

管道将前一个命令的输出作为后一个命令的输入：

```bash
# 统计当前运行的 Python 进程数
ps aux | grep python | wc -l

# 查找最大的 10 个文件
du -sh /var/* | sort -rh | head -10

# 实时查看最新的 20 条错误日志
tail -f /var/log/syslog | grep -i error | tail -20

# 提取 IP 并统计访问次数
cat /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -nr
```

**复杂管道实战**：
```bash
# 分析日志：统计每小时的请求数
cat /var/log/nginx/access.log     | awk '{print $4}'     | cut -d: -f1     | sort     | uniq -c     | sort -k1 -nr

# 查找系统中最大的 5 个文件
find / -type f -exec du -h {} + 2>/dev/null | sort -rh | head -5

# 清理所有 .tmp 文件但保留最新的 3 个
ls -t /tmp/*.tmp | tail -n +4 | xargs rm -f
```

---

### 5. 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| 文件被误删但进程还在使用 | `lsof +L1` 找到后恢复，或重启进程 |
| 删除大量文件很慢 | `rsync -a --delete /empty_dir/ /target_dir/` 比 `rm` 快 10 倍 |
| 文件名有特殊字符 | 用单引号：`rm -i 'file with spaces.txt'` |
| 磁盘空间不足但找不到大文件 | `du -sh /*` 从根目录逐层排查 |
| 复制目录时权限丢失 | 用 `cp -a` 保留所有属性 |
| 文件名乱码 | `convmv -f gbk -t utf8 --notest filename` |


---

## 💻 实战练习

### 练习 1：基础命令练习

```bash
# 1. 查看系统信息（根据今日主题调整）
# 例如如果是进程管理，执行：
ps aux | head -10

# 2. 查看相关配置
# 例如：
ls -la /etc/ | grep -E "nginx|ssh"

# 3. 尝试实际操作（测试环境）
```

### 练习 2：实际工作场景

```bash
# 根据今日主题设计一个实际场景
# 例如：日志分析、配置修改、故障排查等

# 场景：排查一个常见问题
# 步骤 1：...
# 步骤 2：...
```

### 练习 3：进阶挑战（选做）

```bash
# 尝试完成一个稍微复杂的任务
# 例如：自动化脚本、批量处理等
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

*由 SRE 学习计划自动生成 | 2026-04-15 09:01:29*  
*Generated by Hermes Agent with review*
