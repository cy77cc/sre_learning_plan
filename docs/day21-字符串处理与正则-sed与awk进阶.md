# Day 21: 字符串处理与正则 — sed/awk 进阶

> 📅 日期：2026-04-25  
> 📖 学习主题：字符串处理与正则 — sed/awk 进阶  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 21 的学习后，你应该掌握：
- 理解 字符串处理与正则 — sed/awk 进阶 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. grep - 文本搜索神器

grep 是 Linux 中最常用的文本搜索工具，SRE 必备技能。

#### 1.1 基础语法

```bash
grep [选项] "搜索模式" [文件...]
```

#### 1.2 常用选项

| 选项 | 含义 | 示例 |
|------|------|------|
| `-i` | 忽略大小写 | `grep -i "error" log.txt` |
| `-n` | 显示行号 | `grep -n "Failed" auth.log` |
| `-c` | 只显示匹配行数 | `grep -c "404" access.log` |
| `-v` | 反向匹配（不包含） | `grep -v "GET /health" access.log` |
| `-r` | 递归搜索目录 | `grep -r "config" /etc/` |
| `-A N` | 显示匹配行后 N 行 | `grep -A 5 "ERROR" log.txt` |
| `-B N` | 显示匹配行前 N 行 | `grep -B 3 "ERROR" log.txt` |
| `-l` | 只显示文件名 | `grep -rl "password" /etc/` |
| `-w` | 整词匹配 | `grep -w "root" /etc/passwd` |
| `-E` | 扩展正则 | `grep -E "error|fatal|critical" log.txt` |
| `-o` | 只输出匹配部分 | `grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" access.log` |

**实战案例 - 日志分析**：
```bash
# 查找所有 error 日志（不区分大小写）
grep -i "error" /var/log/syslog | tail -50

# 查找登录失败记录（安全监控）
grep "Failed password" /var/log/auth.log | grep "sshd"

# 统计 404 错误出现次数
grep -c " 404 " /var/log/nginx/access.log

# 查找错误前后 5 行（完整上下文）
grep -B 5 -A 5 "ERROR" /var/log/app.log

# 反向查找（排除健康检查）
grep -v "GET /health" /var/log/nginx/access.log | wc -l

# 提取 IP 地址
grep -oE "\b[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b" /var/log/nginx/access.log

# 多条件匹配（扩展正则）
grep -E "error|fatal|critical|warning" /var/log/nginx/error.log
```

---

### 2. sed - 流编辑器

sed 是强大的流编辑器，用于对文本进行替换、删除、插入等操作。

#### 2.1 基础语法

```bash
sed [选项] '命令' [文件...]
sed -i '命令' [文件...]    # -i: 直接修改文件
```

#### 2.2 常用命令

| 命令 | 含义 | 示例 |
|------|------|------|
| `s/old/new/` | 替换第一处 | `sed 's/nginx/apache/' file` |
| `s/old/new/g` | 全部替换 | `sed 's/nginx/apache/g' file` |
| `s/old/new/2` | 只替换第二处 | `sed 's/nginx/apache/2' file` |
| `Nd` | 删除第 N 行 | `sed '5d' file` |
| `N,Md` | 删除 N 到 M 行 | `sed '1,10d' file` |
| `/pattern/d` | 删除匹配行 | `sed '/^#/d' file` |
| `p` | 打印行 | `sed -n '5p' file` |
| `i\text` | 在行前插入 | `sed '1i\Header' file` |
| `a\text` | 在行后追加 | `sed '1a\Footer' file` |

**实战案例 - 配置文件处理**：
```bash
# 替换配置文件中的端口（nginx 端口 80 -> 8080）
sed -i 's/listen 80;/listen 8080;/' /etc/nginx/nginx.conf

# 替换所有注释为空行
sed -i '/^#/d' /etc/nginx/nginx.conf

# 删除空行
sed -i '/^$/d' /etc/nginx/nginx.conf

# 在每行行首添加行号
sed = file.txt | sed 'N;s/\n/\t/'

# 替换多个空格为单个空格
sed -i 's/  */ /g' file.txt

# 替换 tab 为空格
sed -i 's/\t/ /g' file.txt

# 替换包含特定字符的行
sed -i '/max_connections/c\max_connections = 1000' /etc/mysql/mysql.conf.d/mysqld.cnf

# 备份并修改（安全的做法）
sed -i.backup 's/old/new/g' file.txt
# 原文件保存为 file.txt.backup
```

**批量替换实战**：
```bash
# 批量替换多个文件中的字符串
find /etc/nginx/sites-enabled/ -name "*.conf"     | xargs sed -i 's/80/8080/g'

# 将所有 .txt 文件中的 "localhost" 替换为 "127.0.0.1"
find . -name "*.txt" | xargs sed -i 's/localhost/127.0.0.1/g'

# 在文件特定位置插入内容（第 10 行后）
sed -i '10a\# Added by SRE automation' /etc/config.conf
```

---

### 3. awk - 强大的文本分析工具

awk 不仅仅是文本编辑工具，更是数据分析和报表生成的利器。

#### 3.1 基础语法

```bash
awk '模式 {动作}' [文件...]
awk -F: '{print $1}' /etc/passwd    # -F 指定分隔符
```

#### 3.2 内置变量

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `$0` | 整行 | "root:x:0:0:root:/root:/bin/bash" |
| `$1, $2...` | 第 1, 2... 个字段 | $1="root", $2="x" |
| `NF` | 字段数量 | 7 |
| `NR` | 当前行号 | 1, 2, 3... |
| `FNR` | 当前文件的行号 | 1, 2, 3... |
| `FS` | 字段分隔符 | ":" |
| `OFS` | 输出字段分隔符 | " " |
| `RS` | 记录分隔符 | "\n" |
| `ORS` | 输出记录分隔符 | "\n" |

**实战案例 - 日志分析**：
```bash
# 统计 Nginx 日志每小时的请求数
awk '{print $4}' /var/log/nginx/access.log     | cut -d: -f1     | sort     | uniq -c     | sort -k1 -nr

# 提取 Nginx 日志中的状态码统计
awk '{print $9}' /var/log/nginx/access.log     | sort     | uniq -c     | sort -rn

# 统计每个 IP 的访问次数（降序）
awk '{print $1}' /var/log/nginx/access.log     | sort     | uniq -c     | sort -rn     | head -20

# 查找 5xx 错误并显示详细信息
awk '$9 ~ /^[45][0-9][0-9]$/ {print $1, $4, $7, $9}' /var/log/nginx/access.log

# 统计 POST 请求的字节数
awk '$6 == "POST" {sum += $10} END {print sum}' /var/log/nginx/access.log

# 统计每个 URL 的访问次数
awk '{print $7}' /var/log/nginx/access.log     | sort     | uniq -c     | sort -rn     | head -20
```

**复杂分析案例 - SRE 健康检查报告**：
```bash
# 分析 Nginx 状态码分布
awk '{
    if ($9 >= 200 && $9 < 300) success++
    else if ($9 >= 300 && $9 < 400) redirect++
    else if ($9 >= 400 && $9 < 500) client_error++
    else if ($9 >= 500) server_error++
    total++
}
END {
    print "=== Nginx 健康检查报告 ==="
    print "总请求数:", total
    print "成功 (2xx):", success, sprintf("(%.1f%%)", success/total*100)
    print "重定向 (3xx):", redirect, sprintf("(%.1f%%)", redirect/total*100)
    print "客户端错误 (4xx):", client_error, sprintf("(%.1f%%)", client_error/total*100)
    print "服务端错误 (5xx):", server_error, sprintf("(%.1f%%)", server_error/total*100)
}' /var/log/nginx/access.log
```

#### 3.3 条件判断

```bash
# 基本条件
awk '{if ($9 >= 500) print $0}' /var/log/nginx/access.log

# 多条件
awk '{
    if ($9 >= 500) print "ERROR:", $0
    else if ($9 >= 400) print "CLIENT_ERR:", $0
}' /var/log/nginx/access.log

# 正则匹配
awk '/error|fatal|critical/ {print NR": "$0}' /var/log/syslog

# BEGIN 和 END 块
awk 'BEGIN {print "=== 分析开始 ==="} {sum+=$10} END {print "总流量: "sum" bytes"}' /var/log/nginx/access.log
```

---

### 4. 正则表达式

grep/sed/awk 都支持正则表达式，这是 SRE 必须掌握的技能。

#### 4.1 基础正则

| 符号 | 含义 | 示例 |
|------|------|------|
| `.` | 任意单个字符 | `a.c` 匹配 "abc", "aXc" |
| `^` | 行首 | `^error` 匹配行首的 error |
| `$` | 行尾 | `error$` 匹配行尾的 error |
| `*` | 0 个或多个 | `ab*c` 匹配 "ac", "abc", "abbc" |
| `+` | 1 个或多个 | `ab+c` 匹配 "abc", "abbc" (需 -E) |
| `?` | 0 个或 1 个 | `ab?c` 匹配 "ac", "abc" |
| `[abc]` | 字符集 | `[0-9]` 任意数字 |
| `[^abc]` | 反向字符集 | `[^0-9]` 非数字 |
| `\` | 转义 | `\.` 匹配字面 "." |
| `{n}` | 重复 n 次 | `a{3}` 匹配 "aaa" |
| `{n,m}` | 重复 n 到 m 次 | `a{2,4}` 匹配 "aa" 到 "aaaa" |

**实战案例**：
```bash
# 匹配 IP 地址
grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" /var/log/nginx/access.log

# 匹配日期格式 (2024-01-15)
grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" /var/log/nginx/access.log

# 匹配时间格式 (14:30:25)
grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}" /var/log/nginx/access.log

# 匹配 HTTP 状态码
grep -oE " [45][0-9]{2} " /var/log/nginx/access.log

# 匹配邮箱地址
grep -oE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" /var/log/nginx/access.log

# 匹配 URL
grep -oE "https?://[^ ]+" /var/log/nginx/access.log

# 匹配日志格式中的特定字段
grep -oE "\[[0-9]{2}/[A-Za-z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2}" /var/log/nginx/access.log
```

---

### 5. 三剑客组合技

**真实 SRE 场景：分析 Nginx 访问日志，生成日报告**：
```bash
#!/bin/bash
LOG_FILE="/var/log/nginx/access.log"
REPORT="/tmp/nginx_report_$(date +%Y%m%d).txt"

{
    echo "=== Nginx 日报 $(date +%Y-%m-%d) ==="
    echo ""
    
    # 总请求数
    echo "1. 总请求数:"
    wc -l < $LOG_FILE
    
    # 各状态码统计
    echo ""
    echo "2. HTTP 状态码分布:"
    awk '{print $9}' $LOG_FILE         | sort         | uniq -c         | sort -rn         | awk '{print "   "$2": "$1" 次"}'
    
    # Top 20 访问 IP
    echo ""
    echo "3. Top 20 访问 IP:"
    awk '{print $1}' $LOG_FILE         | sort         | uniq -c         | sort -rn         | head -20         | awk '{print "   "$2": "$1" 次"}'
    
    # Top 20 请求 URL
    echo ""
    echo "4. Top 20 请求 URL:"
    awk '{print $7}' $LOG_FILE         | sort         | uniq -c         | sort -rn         | head -20         | awk '{print "   "$2": "$1" 次"}'
    
    # 5xx 错误详细
    echo ""
    echo "5. 5xx 错误记录:"
    awk '$9 >= 500 {print $1, $4, $7, $9}' $LOG_FILE         | tail -10
    
} > $REPORT

echo "报告已生成: $REPORT"
```

---

### 6. 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| grep 搜索中文字符乱码 | `grep -a "错误" log.txt` 或设置 LANG |
| sed 替换斜杠多的路径 | 用 `#` 做分隔符：`sed 's#/old/path/#/new/path/#g'` |
| awk 分割 URL 中的多个空格 | `awk -F' +' '{print $1}'` 指定多个空格为分隔符 |
| 特殊字符导致正则失效 | 转义：`grep '\.\.\/' file` |
| 大文件处理很慢 | 用 `grep` 先过滤，再用 `awk` 处理子集 |


---

## 💻 实战练习

### 练习 1：生产日志分析报告

**场景**：生成 Nginx 每日运营报告，用于早会汇报。

```bash
#!/bin/bash
LOG="/var/log/nginx/access.log"
echo "===== Nginx 日报 $(date +%Y-%m-%d) ====="
echo "总请求数: $(wc -l < $LOG)"
echo "独立 IP:  $(awk '{print $1}' $LOG | sort -u | wc -l)"
echo ""
echo "状态码分布:"
awk '{print $9}' $LOG | sort | uniq -c | sort -rn
echo ""
echo "Top 10 IP:"
awk '{print $1}' $LOG | sort | uniq -c | sort -rn | head -10
echo ""
echo "5xx 错误:"
awk '$9 >= 500 {printf "  %s %s %s\n", $1, $4, $7}' $LOG | head -20
```

### 练习 2：安全审计脚本

```bash
#!/bin/bash
AUTH_LOG="/var/log/auth.log"
echo "暴力破解尝试:"
grep "Failed password" $AUTH_LOG | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | \
    awk '$1 > 10 {printf "  %s: %d 次\n", $2, $1}'

echo "最近登录:"
last -a | head -20
```

### 练习 3：配置文件批量修改

```bash
# 批量替换配置文件中的端口
find /etc/nginx -name "*.conf" -exec sed -i 's/listen 80/listen 8080/' {} +

# 删除所有空行和注释
sed -i '/^#/d; /^$/d' /etc/nginx/nginx.conf
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

*由 SRE 学习计划自动生成 | 2026-04-25 10:58:14*  
*Generated by Hermes Agent with review*
