# Day 04: 文本处理三剑客 — grep/sed/awk 与正则表达式

> 📅 日期：2026-04-25
> 📖 学习主题：grep 底层原理、sed 深入、awk 编程语言、正则表达式引擎对比、日志分析实战
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 03（文件操作命令）

## 🎯 学习目标

完成 Day 04 的学习后，你应该能够：
1. 解释 grep 的 DFA/NFA 正则引擎原理，以及 -E 和 -P 的区别
2. 掌握 sed 的高级用法（多行处理、hold space、分支跳转）
3. 精通 awk 编程语言（数组、函数、用户自定义函数、getline）
4. 对比 PCRE、POSIX ERE、POSIX BRE 正则表达式引擎
5. 使用 grep/sed/awk 完成 Nginx/Apache 日志分析
6. 进行 grep vs awk vs python 处理大文件的性能对比

---

## 📖 核心知识点

### 1. grep 底层原理

#### 1.1 grep 的正则引擎

grep 支持三种正则表达式模式，使用不同的引擎：

```
grep 模式与引擎：

grep            → Basic Regular Expression (BRE)  → NFA 引擎
grep -E (egrep) → Extended Regular Expression (ERE) → NFA 引擎
grep -P (pcregrep) → Perl Compatible RE (PCRE)    → NFA 引擎（带回溯）

grep 家族：
grep   - 基本正则搜索
egrep  - 扩展正则搜索（等同于 grep -E）
fgrep  - 固定字符串搜索（等同于 grep -F，最快）
pgrep  - 按进程名搜索（不是正则搜索！）
zgrep  - 搜索压缩文件
```

#### 1.2 NFA 与 DFA 引擎对比

```
正则表达式引擎分类：

1. NFA (Non-deterministic Finite Automaton，非确定性有限自动机)
   ├── 由正则表达式驱动
   ├── 逐字符匹配正则表达式
   ├── 支持回溯（backtracking）
   ├── 支持反向引用（\1, \2）
   ├── 支持惰性量词（*?, +?）
   └── 最坏情况：指数级时间复杂度

2. DFA (Deterministic Finite Automaton，确定性有限自动机)
   ├── 由文本驱动
   ├── 逐字符匹配文本
   ├── 不支持回溯
   ├── 不支持反向引用
   ├── 最坏情况：线性时间复杂度
   └── 预处理时间较长（编译正则表达式）

性能对比：
┌──────────────┬──────────────┬──────────────┐
│              │ NFA          │ DFA          │
├──────────────┼──────────────┼──────────────┤
│ 预处理时间    │ O(m)         │ O(2^m)       │
│ 匹配时间      │ O(m*n)       │ O(n)         │
│ 最坏情况      │ 指数级       │ 线性         │
│ 反向引用      │ 支持         │ 不支持       │
│ 惰性量词      │ 支持         │ 不支持       │
│ 实现复杂度    │ 简单         │ 复杂         │
└──────────────┴──────────────┴──────────────┘

m = 正则表达式长度
n = 文本长度
```

**NFA 回溯示例**：
```
正则：a.*b
文本：axxxbxxxb

NFA 匹配过程：
1. a 匹配 a ✓
2. .* 匹配 xxxbxxxb（贪婪匹配到末尾）
3. 需要匹配 b，但已经到末尾
4. 回溯：.* 退回一个字符 → xxxbxxxb
5. 仍然没有 b
6. 继续回溯：.* 退回 → xxxbxxxb
7. ... 持续回溯
8. 最终：.* 匹配 xxx，b 匹配 b ✓

贪婪 vs 惰性：
贪婪：.*  匹配尽可能多的字符（默认）
惰性：.*? 匹配尽可能少的字符

a.*b  匹配 axxxbxxxb（最长匹配）
a.*?b 匹配 axxxb（最短匹配）
```

#### 1.3 grep -E vs grep -P 区别

```bash
# grep -E (ERE - Extended Regular Expression)
# 不需要转义的元字符：+ ? | () {}
grep -E "error|fatal|critical" log.txt
grep -E "colou?r" log.txt           # 匹配 color 或 colour
grep -E "(ab)+" log.txt              # 匹配 ab, abab, ababab

# grep -P (PCRE - Perl Compatible Regular Expression)
# 支持更强大的特性
grep -P "\d{3}-\d{4}" phone.txt     # \d = [0-9]
grep -P "(?<=error):" log.txt        # 前瞻断言
grep -P "(?<=\[).*?(?=\])" log.txt   # 非捕获匹配
grep -P "\b\w+\b" text.txt           # \b = 单词边界

# ERE vs PCRE 对比
┌──────────────────┬──────────┬──────────┐
│ 特性              │ ERE      │ PCRE     │
├──────────────────┼──────────┼──────────┤
│ \d \w \s         │ 不支持   │ 支持     │
│ 反向引用 \1      │ 不支持   │ 支持     │
│ 前瞻/后顾断言    │ 不支持   │ 支持     │
│ 非贪婪量词 *?    │ 不支持   │ 支持     │
│ 命名捕获 (?P<n>) │ 不支持   │ 支持     │
│ Unicode 支持     │ 有限     │ 完整     │
│ 性能             │ 快       │ 较慢     │
└──────────────────┴──────────┴──────────┘
```

#### 1.4 grep 常用选项详解

```bash
# ===== 基本选项 =====
grep "pattern" file              # 基本搜索
grep -i "pattern" file           # 忽略大小写
grep -n "pattern" file           # 显示行号
grep -c "pattern" file           # 只显示匹配行数
grep -l "pattern" files...       # 只显示匹配的文件名
grep -L "pattern" files...       # 只显示不匹配的文件名
grep -w "pattern" file           # 整词匹配
grep -x "pattern" file           # 整行匹配
grep -v "pattern" file           # 反向匹配（不包含）

# ===== 上下文选项 =====
grep -A 5 "ERROR" log.txt        # 显示匹配行后 5 行
grep -B 3 "ERROR" log.txt        # 显示匹配行前 3 行
grep -C 2 "ERROR" log.txt        # 显示匹配行前后各 2 行

# ===== 输出控制 =====
grep -o "pattern" file           # 只输出匹配的部分
grep -m 5 "pattern" file         # 最多匹配 5 次
grep --color=auto "pattern" file # 高亮显示匹配

# ===== 递归搜索 =====
grep -r "pattern" /path/         # 递归搜索目录
grep -R "pattern" /path/         # 递归搜索（跟随符号链接）
grep --include="*.log" -r "pattern" /path/  # 只搜索 .log 文件
grep --exclude="*.bak" -r "pattern" /path/  # 排除 .bak 文件
grep --exclude-dir=".git" -r "pattern" /path/  # 排除目录

# ===== 性能选项 =====
grep -F "pattern" file           # 固定字符串搜索（最快）
grep -f patterns.txt file        # 从文件读取模式
grep --mmap "pattern" file       # 使用 mmap 读取文件

# ===== 二进制文件 =====
grep -a "pattern" binary_file    # 将二进制文件当作文本处理
grep -I "pattern" files...       # 跳过二进制文件
```

#### 1.5 grep 高级用法

```bash
# 多模式匹配
grep -E "error|fatal|critical" log.txt
grep -e "error" -e "fatal" -e "critical" log.txt

# 从文件读取模式
cat > patterns.txt << 'EOF'
error
fatal
critical
EOF
grep -f patterns.txt log.txt

# 使用管道组合
cat /var/log/syslog | grep -i "error" | grep -v "health_check" | wc -l

# 提取 IP 地址
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log

# 提取邮箱
grep -oE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" file.txt

# 匹配 URL
grep -oE "https?://[^\"' ]+" file.txt

# 统计每个 IP 的出现次数
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log | sort | uniq -c | sort -rn | head -20

# 查找包含中文的行
grep -P "[\x{4e00}-\x{9fff}]" file.txt

# 使用零宽断言
grep -P "(?<=error): " log.txt    # 匹配 "error: " 中的 ": "
grep -P "(?=error)" log.txt       # 匹配 "error" 的位置
```

---

### 2. sed 深入

#### 2.1 sed 工作原理

```
sed (Stream Editor) 工作流程：

输入流
  │
  ▼
┌─────────────────────────────────────────┐
│  1. 读取一行到模式空间 (Pattern Space)   │
│  2. 执行所有命令（按顺序）               │
│  3. 输出模式空间内容                     │
│  4. 清空模式空间                         │
│  5. 读取下一行                           │
│  6. 重复直到文件结束                     │
└─────────────────────────────────────────┘
  │
  ▼
输出流

sed 内存结构：
┌─────────────────────────────────────────┐
│  模式空间 (Pattern Space)                │
│  ├── 当前正在处理的行                    │
│  ├── 默认每行都会输出                    │
│  └── 可以被命令修改                      │
│                                          │
│  保持空间 (Hold Space)                   │
│  ├── 临时存储区域                        │
│  ├── 初始为空                            │
│  └── 可以与模式空间交换数据              │
└─────────────────────────────────────────┘
```

#### 2.2 sed 命令详解

```bash
# ===== 替换命令 s =====
sed 's/old/new/' file            # 替换每行第一处
sed 's/old/new/g' file           # 替换所有
sed 's/old/new/2' file           # 只替换第二处
sed 's/old/new/gi' file          # 替换所有（忽略大小写）
sed 's/old/new/gp' file          # 替换并打印修改的行

# 使用不同的分隔符（处理路径时很有用）
sed 's#/old/path/#/new/path/#g' file
sed 's|old|new|g' file

# 使用 & 引用匹配的内容
sed 's/[0-9]/[&]/g' file         # 将数字用方括号包裹
sed 's/.*/echo "&"/' file        # 包裹整行

# 使用分组和反向引用
sed 's/\(.*\):\(.*\)/\2:\1/' file       # 交换冒号两边的内容
sed -E 's/(.+):(.+)/\2:\1/' file        # ERE 语法（更清晰）

# ===== 删除命令 d =====
sed '5d' file                    # 删除第 5 行
sed '1,10d' file                 # 删除 1-10 行
sed '/^#/d' file                 # 删除注释行
sed '/^$/d' file                 # 删除空行
sed '/pattern/d' file            # 删除匹配行

# ===== 打印命令 p =====
sed -n '5p' file                 # 只打印第 5 行
sed -n '1,10p' file              # 只打印 1-10 行
sed -n '/pattern/p' file         # 只打印匹配行

# ===== 插入和追加 =====
sed '1i\Header line' file        # 在第 1 行前插入
sed '1a\Footer line' file        # 在第 1 行后追加
sed '/pattern/i\Insert before' file    # 在匹配行前插入
sed '/pattern/a\Append after' file     # 在匹配行后追加

# ===== 行号和地址 =====
sed '3,5s/old/new/g' file        # 只在 3-5 行替换
sed '0~2d' file                  # 删除偶数行
sed '1~2d' file                  # 删除奇数行
sed '$d' file                    # 删除最后一行
sed '1~3s/old/new/g' file        # 每 3 行替换一次

# ===== 写入文件 =====
sed -n '/pattern/w output.txt' file    # 将匹配行写入文件
sed -i 's/old/new/g' file              # 直接修改文件（原地编辑）
sed -i.bak 's/old/new/g' file          # 修改并备份原文件
```

#### 2.3 sed 高级用法：多行处理

```bash
# 多行处理命令
# N - 将下一行追加到模式空间
# P - 打印模式空间中第一行
# D - 删除模式空间中第一行

# 示例：合并连续行
# 输入：
# line1
# line2
# line3
# line4

# 合并每两行为一行
sed 'N;s/\n/ /' file
# 输出：
# line1 line2
# line3 line4

# 删除空行（包括连续空行）
sed '/^$/d' file                 # 只删除单个空行
sed '/^$/{N;/^\n$/d}' file       # 删除连续空行
sed '/./,/^$/!d' file            # 删除多个连续空行

# 在匹配行前插入空行
sed '/pattern/{x;p;x;}' file

# 在匹配行后插入空行
sed '/pattern/G' file
```

#### 2.4 sed 高级用法：Hold Space

```bash
# Hold Space 命令
# h - 将模式空间复制到保持空间
# H - 将模式空间追加到保持空间
# g - 将保持空间复制到模式空间
# G - 将保持空间追加到模式空间
# x - 交换模式空间和保持空间

# 示例1：反转文件行序（类似 tac）
sed -n '1!G;h;$p' file

# 解释：
# 1!G - 除了第一行，将保持空间追加到模式空间
# h   - 将模式空间复制到保持空间
# $p  - 最后一行时打印

# 示例2：在每行后添加空行
sed 'G' file

# 示例3：将文件内容反转（字符级别）
# 这个比较复杂，通常用 rev 命令更简单
rev file
```

#### 2.5 sed 分支跳转

```bash
# 分支命令
# :label - 定义标签
# b label - 无条件跳转到标签
# b      - 无条件跳转到脚本末尾（跳过后续命令）
# t label - 如果上次替换成功，跳转到标签
# T label - 如果上次替换失败，跳转到标签

# 示例1：跳过前 5 行
sed '1,5b; s/old/new/g' file

# 示例2：只在匹配行执行替换
sed '/pattern/!b; s/old/new/g' file

# 示例3：循环替换（处理嵌套）
:loop
s/()//g
t loop
# 移除所有括号（包括嵌套的）

# 示例4：条件替换
sed '{
  /error/!b
  s/error/ERROR/
  s/fatal/FATAL/
}' file
```

#### 2.6 sed 实战案例

```bash
# 1. 批量修改配置文件
# 修改 Nginx 配置中的端口
sed -i 's/listen 80;/listen 8080;/' /etc/nginx/nginx.conf

# 2. 删除配置文件中的注释和空行
sed -i '/^#/d; /^$/d' /etc/nginx/nginx.conf

# 3. 在文件开头添加内容
sed -i '1i\# This file is managed by Ansible' /etc/nginx/nginx.conf

# 4. 批量替换多个文件
find /etc/nginx -name "*.conf" -exec sed -i 's/old_domain/new_domain/g' {} +

# 5. 提取配置文件中的有效行
sed -n '/^[^#]/p' /etc/ssh/sshd_config

# 6. 修改 /etc/passwd 中的 shell
sed -i 's|/bin/bash|/bin/zsh|' /etc/passwd

# 7. 提取日志中的时间戳
sed -n 's/.*\[\(.*\)\].*/\1/p' access.log

# 8. 转换 CSV 为 TSV
sed 's/,/\t/g' data.csv

# 9. 删除文件最后 5 行
sed -i 'N;$!P;D' file          # 删除最后一行
sed -i -n -e :a -e '1,5!{P;N;D;};N;ba' file  # 删除最后 5 行

# 10. 在匹配行后添加多行
sed -i '/\[mysqld\]/a\max_connections = 1000\ninnodb_buffer_pool_size = 2G' /etc/mysql/my.cnf
```

---

### 3. awk 编程语言

#### 3.1 awk 工作原理

```
awk 工作流程：

输入文件
  │
  ▼
┌─────────────────────────────────────────┐
│  BEGIN { 初始化代码 }                    │
│  ──── 在读取任何输入之前执行一次 ────    │
│                                          │
│  模式1 { 动作1 }                         │
│  模式2 { 动作2 }                         │
│  ──── 对每一行执行 ────                  │
│  ──── 如果模式匹配，执行动作 ────        │
│                                          │
│  END { 清理代码 }                        │
│  ──── 在处理完所有输入后执行一次 ────    │
└─────────────────────────────────────────┘
  │
  ▼
输出
```

#### 3.2 awk 内置变量

```bash
# 字段分隔和记录分隔
FS   - 输入字段分隔符（默认空格/Tab）
OFS  - 输出字段分隔符（默认空格）
RS   - 输入记录分隔符（默认换行）
ORS  - 输出记录分隔符（默认换行）

# 字段引用
$0   - 整行
$1   - 第一个字段
$2   - 第二个字段
$NF  - 最后一个字段
$(NF-1) - 倒数第二个字段

# 行号和文件名
NR   - 当前已读取的总行数（跨文件累加）
FNR  - 当前文件中的行号
FILENAME - 当前文件名

# 示例
awk -F: '{print NR, FNR, $1, $NF}' /etc/passwd /etc/group

# 其他内置变量
ARGC  - 命令行参数个数
ARGV  - 命令行参数数组
ENVIRON - 环境变量数组
OFMT  - 数字输出格式（默认 %.6g）
RSTART - match() 匹配的起始位置
RLENGTH - match() 匹配的长度
SUBSEP - 下标分隔符（默认 \034）
```

#### 3.3 awk 模式匹配

```bash
# 正则模式
awk '/error/' file               # 匹配包含 error 的行
awk '!/error/' file              # 不匹配包含 error 的行
awk '/error|fatal/' file         # 匹配 error 或 fatal
awk '$1 ~ /^[0-9]+$/' file       # 第一个字段是纯数字
awk '$9 ~ /^[45]/' access.log    # 状态码以 4 或 5 开头

# 比较模式
awk '$3 > 100' file              # 第三个字段大于 100
awk '$1 == "admin"' file         # 第一个字段等于 admin
awk '$NF != ""' file             # 最后一个字段不为空
awk 'NR > 10' file               # 行号大于 10
awk 'FNR == 5' file              # 当前文件的第 5 行

# 范围模式
awk '/start/,/end/' file         # 从 start 到 end 的所有行
awk 'NR==10,NR==20' file         # 第 10 到 20 行

# 组合模式
awk '/error/ && $9 >= 500' access.log
awk '/error/ || /fatal/' file
awk '!/health_check/ && /200/' access.log
```

#### 3.4 awk 数组

```bash
# awk 关联数组（类似字典/哈希表）
awk '{count[$1]++} END {for (ip in count) print count[ip], ip}' access.log

# 数组遍历
awk '{
    for (i = 1; i <= NF; i++) {
        word_count[$i]++
    }
}
END {
    for (word in word_count) {
        print word_count[word], word
    }
}' file.txt | sort -rn | head -20

# 删除数组元素
awk '{count[$1]++} END {
    delete count["127.0.0.1"]
    for (ip in count) print count[ip], ip
}' access.log

# 多维数组（使用 SUBSEP）
awk '{
    count[$1, $9]++
}
END {
    for (key in count) {
        split(key, parts, SUBSEP)
        print parts[1], parts[2], count[key]
    }
}' access.log

# 数组长度
awk '{a[$1]++} END {print length(a)}' access.log

# 检查元素是否存在
awk '{if ($1 in visited) print "duplicate:", $0; visited[$1]=1}' file
```

#### 3.5 awk 内置函数

```bash
# ===== 字符串函数 =====
length(s)                    # 字符串长度
substr(s, start, len)        # 子字符串
index(s, target)             # 查找子字符串位置
split(s, arr, sep)           # 分割字符串到数组
sub(regexp, replacement, s)  # 替换第一处
gsub(regexp, replacement, s) # 替换所有
match(s, regexp)             # 正则匹配
sprintf(fmt, ...)            # 格式化字符串
tolower(s)                   # 转小写
toupper(s)                   # 转大写

# ===== 数学函数 =====
int(x)                       # 取整
sqrt(x)                      # 平方根
exp(x)                       # e 的 x 次方
log(x)                       # 自然对数
sin(x) / cos(x)             # 三角函数
rand()                       # 0-1 之间的随机数
srand()                      # 设置随机数种子

# ===== I/O 函数 =====
getline                      # 读取下一行
getline < "file"             # 从文件读取
getline var                  # 读取到变量
getline var < "file"         # 从文件读取到变量
close("command")             # 关闭管道/文件

# ===== 示例 =====
# 提取日期
awk '{match($4, /\[([^\]]+)\]/, arr); print arr[1]}' access.log

# 格式化输出
awk '{printf "%-20s %10d\n", $1, $10}' access.log

# 字符串分割
awk '{n=split($0, arr, ":"); print n, arr[1]}' /etc/passwd
```

#### 3.6 awk 用户自定义函数

```bash
# 定义函数
awk '
function max(a, b) {
    return (a > b) ? a : b
}
function min(a, b) {
    return (a < b) ? a : b
}
function abs(x) {
    return (x < 0) ? -x : x
}
{
    print max($1, $2), min($1, $2)
}' numbers.txt

# 带局部变量的函数
awk '
function format_size(bytes,    units, i) {
    split("B KB MB GB TB", units, " ")
    i = 1
    while (bytes >= 1024 && i < 5) {
        bytes /= 1024
        i++
    }
    return sprintf("%.2f %s", bytes, units[i])
}
{
    print format_size($1)
}' sizes.txt

# 递归函数
awk '
function factorial(n) {
    if (n <= 1) return 1
    return n * factorial(n - 1)
}
{
    print $1, "!= " factorial($1)
}' numbers.txt
```

#### 3.7 awk getline 用法

```bash
# 从标准输入读取下一行
awk '{getline next_line; print $0, "=>", next_line}' file

# 从文件读取
awk '{
    getline line < "config.txt"
    print $0, line
}' data.txt

# 从命令读取
awk '{
    "date +%H:%M:%S" | getline timestamp
    print timestamp, $0
}' access.log

# 循环读取文件
awk 'BEGIN {
    while ((getline line < "config.txt") > 0) {
        config[line] = 1
    }
    close("config.txt")
}
{
    if ($0 in config) print "Found:", $0
}' data.txt

# 读取命令输出
awk 'BEGIN {
    cmd = "hostname"
    cmd | getline hostname
    close(cmd)
    print "Host:", hostname
}'
```

#### 3.8 awk 流程控制

```bash
# if-else
awk '{
    if ($9 >= 500) {
        print "SERVER_ERROR:", $0
    } else if ($9 >= 400) {
        print "CLIENT_ERROR:", $0
    } else if ($9 >= 300) {
        print "REDIRECT:", $0
    } else {
        print "SUCCESS:", $0
    }
}' access.log

# for 循环
awk '{
    for (i = 1; i <= NF; i++) {
        if ($i ~ /^[0-9]+$/) {
            sum += $i
        }
    }
    print "Sum:", sum
}' numbers.txt

# while 循环
awk '{
    i = 1
    while (i <= NF) {
        print $i
        i++
    }
}' file

# do-while 循环
awk 'BEGIN {
    i = 1
    do {
        print i
        i++
    } while (i <= 5)
}'

# break 和 continue
awk '{
    for (i = 1; i <= NF; i++) {
        if ($i == "skip") continue
        if ($i == "stop") break
        print $i
    }
}' file

# next - 跳过当前行
awk '/^#/ {next} {print}' config.txt  # 跳过注释行

# nextfile - 跳过当前文件
awk 'FNR == 1 {nextfile} {print}' *.txt
```

---

### 4. 正则表达式引擎对比

#### 4.1 BRE vs ERE vs PCRE

```
正则表达式语法对比：

┌──────────────┬──────────┬──────────┬──────────┐
│ 语法          │ BRE      │ ERE      │ PCRE     │
├──────────────┼──────────┼──────────┼──────────┤
│ 任意字符      │ .        │ .        │ .        │
│ 0 或多个      │ *        │ *        │ *        │
│ 1 或多个      │ \+       │ +        │ +        │
│ 0 或 1 个     │ \?       │ ?        │ ?        │
│ 或            │ \|       │ |        │ |        │
│ 分组          │ \(\)     │ ()       │ ()       │
│ 反向引用      │ \1       │ 不支持   │ \1       │
│ 花括号        │ \{n,m\}  │ {n,m}    │ {n,m}    │
│ 字符类        │ [[:alpha:]] │ [[:alpha:]] │ [[:alpha:]] │
│ \d (数字)     │ 不支持   │ 不支持   │ \d       │
│ \w (单词)     │ 不支持   │ 不支持   │ \w       │
│ \s (空白)     │ 不支持   │ 不支持   │ \s       │
│ \b (边界)     │ \b       │ \b       │ \b       │
│ 前瞻断言      │ 不支持   │ 不支持   │ (?=...)  │
│ 后顾断言      │ 不支持   │ 不支持   │ (?<=...) │
│ 非贪婪        │ 不支持   │ 不支持   │ *? +?    │
│ 命名分组      │ 不支持   │ 不支持   │ (?P<n>)  │
└──────────────┴──────────┴──────────┴──────────┘

BRE 转义规则：+ ? | () {} 需要转义 \+ \? \| \(\) \{\}
ERE 转义规则：这些字符不需要转义
PCRE 转义规则：同 ERE，加上 \d \w \s 等
```

#### 4.2 正则表达式最佳实践

```bash
# 1. 能用固定字符串就不用正则
grep -F "error" file           # 最快
grep "error" file              # 较慢

# 2. 能用 ERE 就不用 PCRE
grep -E "error|fatal" file     # 快
grep -P "error|fatal" file     # 较慢

# 3. 避免回溯陷阱
# 差：.* 会导致大量回溯
grep "a.*b.*c" file

# 好：使用更精确的字符类
grep "a[^b]*b[^c]*c" file

# 4. 使用锚点减少匹配范围
grep "^error" file             # 只匹配行首的 error
grep "error$" file             # 只匹配行尾的 error

# 5. 使用 -w 整词匹配
grep -w "error" file           # 不匹配 "errors" 或 "error_msg"
```

---

### 5. Nginx/Apache 日志分析完整实战

#### 5.1 Nginx 日志格式

```
Nginx 默认日志格式（combined）：
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"

示例：
192.168.1.100 - - [15/Jan/2024:10:30:45 +0800] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0"

字段对应：
$1  = 192.168.1.100          (客户端 IP)
$2  = -                      (认证用户)
$3  = -                      (认证用户)
$4  = [15/Jan/2024:10:30:45  (时间戳开始)
$5  = +0800]                 (时区)
$6  = "GET                   (请求方法)
$7  = /api/users             (请求 URL)
$8  = HTTP/1.1"              (协议版本)
$9  = 200                    (状态码)
$10 = 1234                   (响应字节数)
$11 = "https://example.com"  (来源页)
$12 = "Mozilla/5.0..."       (User-Agent)
```

#### 5.2 日志分析脚本

```bash
#!/bin/bash
# nginx_report.sh - Nginx 日志分析报告
LOG="/var/log/nginx/access.log"

echo "=============================="
echo "Nginx 日志分析报告"
echo "日期: $(date '+%Y-%m-%d %H:%M:%S')"
echo "日志: $LOG"
echo "=============================="

# 1. 基本统计
echo ""
echo "--- 基本统计 ---"
echo "总请求数: $(wc -l < $LOG)"
echo "独立 IP 数: $(awk '{print $1}' $LOG | sort -u | wc -l)"
echo "总流量: $(awk '{sum+=$10} END {printf "%.2f GB\n", sum/1024/1024/1024}' $LOG)"

# 2. HTTP 状态码分布
echo ""
echo "--- HTTP 状态码分布 ---"
awk '{print $9}' $LOG | sort | uniq -c | sort -rn | \
    awk '{
        pct = $1/total*100
        printf "%6d  %s  (%5.1f%%)\n", $1, $2, pct
    }' total=$(wc -l < $LOG)

# 3. Top 20 访问 IP
echo ""
echo "--- Top 20 访问 IP ---"
awk '{print $1}' $LOG | sort | uniq -c | sort -rn | head -20 | \
    awk '{printf "%6d  %s\n", $1, $2}'

# 4. Top 20 请求 URL
echo ""
echo "--- Top 20 请求 URL ---"
awk '{print $7}' $LOG | sort | uniq -c | sort -rn | head -20 | \
    awk '{printf "%6d  %s\n", $1, $2}'

# 5. 4xx/5xx 错误详情
echo ""
echo "--- 4xx 错误 (Top 10) ---"
awk '$9 ~ /^4/ {print $9, $7}' $LOG | sort | uniq -c | sort -rn | head -10

echo ""
echo "--- 5xx 错误 (Top 10) ---"
awk '$9 ~ /^5/ {print $9, $7}' $LOG | sort | uniq -c | sort -rn | head -10

# 6. 每小时请求量
echo ""
echo "--- 每小时请求量 ---"
awk '{print $4}' $LOG | cut -d: -f2 | sort | uniq -c | sort -k2n

# 7. 响应时间分析（如果有 $request_time 字段）
echo ""
echo "--- 响应时间分析 ---"
# 如果日志格式包含响应时间
# awk '{print $NF}' $LOG | sort -n | awk '
#     {a[NR]=$1; sum+=$1}
#     END {
#         print "最小:", a[1]
#         print "最大:", a[NR]
#         print "平均:", sum/NR
#         print "P50:", a[int(NR*0.5)]
#         print "P95:", a[int(NR*0.95)]
#         print "P99:", a[int(NR*0.99)]
#     }'

# 8. 每分钟请求数（QPS）
echo ""
echo "--- 每分钟请求数 (最近 10 分钟) ---"
awk '{print $4}' $LOG | cut -d: -f1-3 | sort | uniq -c | tail -10

# 9. 带宽使用
echo ""
echo "--- 带宽使用 (按 IP) ---"
awk '{bytes[$1]+=$10} END {for (ip in bytes) printf "%10d  %s\n", bytes[ip], ip}' $LOG | sort -rn | head -10

# 10. User-Agent 统计
echo ""
echo "--- Top 10 User-Agent ---"
awk -F'"' '{print $6}' $LOG | sort | uniq -c | sort -rn | head -10
```

#### 5.3 实时日志监控

```bash
# 实时监控错误日志
tail -f /var/log/nginx/error.log | grep --line-buffered -i "error\|warn\|crit"

# 实时统计 QPS
tail -f /var/log/nginx/access.log | awk '{print $4}' | cut -d: -f2 | uniq -c

# 实时监控 5xx 错误
tail -f /var/log/nginx/access.log | awk '$9 ~ /^5/ {print $0}'

# 实时监控特定 IP
tail -f /var/log/nginx/access.log | grep "192.168.1.100"

# 实时监控慢请求（假设最后一个字段是响应时间）
tail -f /var/log/nginx/access.log | awk '$NF > 1.0 {print $0}'
```

---

### 6. 性能对比：grep vs awk vs python

#### 6.1 测试环境

```bash
# 创建测试文件
# 1GB 文件，每行约 100 字符
shuf -i 1-10000000 -n 10000000 | awk '{printf "%010d %s %s %s\n", $1, "error", "some text here", rand()}' > test.log

# 文件大小
ls -lh test.log
# 1.1G test.log
```

#### 6.2 性能测试

```bash
# 测试 1：简单字符串搜索
time grep "error" test.log | wc -l
# 约 2-3 秒

time awk '/error/' test.log | wc -l
# 约 4-5 秒

time python3 -c "
count = 0
with open('test.log') as f:
    for line in f:
        if 'error' in line:
            count += 1
print(count)
"
# 约 5-6 秒

# 测试 2：正则匹配
time grep -E "error[0-9]+" test.log | wc -l
# 约 3-4 秒

time awk '/error[0-9]+/' test.log | wc -l
# 约 5-6 秒

time python3 -c "
import re
count = 0
pattern = re.compile(r'error[0-9]+')
with open('test.log') as f:
    for line in f:
        if pattern.search(line):
            count += 1
print(count)
"
# 约 4-5 秒

# 测试 3：字段提取和统计
time awk '{print $1}' test.log | sort | uniq -c | sort -rn | head -10
# 约 10-15 秒

time python3 -c "
from collections import Counter
with open('test.log') as f:
    ips = [line.split()[0] for line in f]
for ip, count in Counter(ips).most_common(10):
    print(count, ip)
"
# 约 8-10 秒
```

#### 6.3 性能总结

```
性能对比总结：

┌──────────────┬──────────┬──────────┬──────────┐
│ 场景          │ grep     │ awk      │ python   │
├──────────────┼──────────┼──────────┼──────────┤
│ 简单字符串    │ 最快     │ 中等     │ 最慢     │
│ 正则匹配      │ 最快     │ 中等     │ 中等     │
│ 字段提取      │ 不支持   │ 最快     │ 中等     │
│ 复杂统计      │ 需组合   │ 最快     │ 中等     │
│ 多文件处理    │ 最快     │ 中等     │ 中等     │
│ 流式处理      │ 最快     │ 最快     │ 需要代码 │
└──────────────┴──────────┴──────────┴──────────┘

选择建议：
1. 简单搜索 → grep（最快）
2. 字段处理 → awk（最灵活）
3. 复杂逻辑 → python（最强大）
4. 大文件流式处理 → grep + awk 管道组合
5. 实时日志分析 → grep/awk（低延迟）
```

#### 6.4 性能优化技巧

```bash
# 1. 使用 grep -F 进行固定字符串搜索
grep -F "error" file           # 最快（不使用正则引擎）

# 2. 先 grep 过滤，再 awk 处理
grep "error" large_file | awk '{print $1, $7}'

# 3. 使用 LC_ALL=C 加速
LC_ALL=C grep "error" file    # 避免 locale 处理开销

# 4. 使用 --mmap 映射文件
grep --mmap "error" file

# 5. 并行处理
split -n l/4 -d large_file part_
for f in part_*; do
    grep "error" "$f" > "result_$f" &
done
wait
cat result_part_* > results.txt

# 6. 使用 ripgrep (rg) 替代 grep
rg "error" file                # 通常比 grep 快 2-10 倍

# 7. 使用 mawk 替代 gawk
mawk '{print $1}' file         # mawk 比 gawk 快
```

---

### 7. 三剑客组合技

#### 7.1 日志分析组合

```bash
# 统计每小时的错误率
awk '{
    hour = substr($4, 14, 2)
    total[hour]++
    if ($9 >= 500) error[hour]++
}
END {
    for (h in total) {
        e = error[h] + 0
        printf "%s:00  total=%d  errors=%d  rate=%.2f%%\n", h, total[h], e, e/total[h]*100
    }
}' access.log | sort

# 查找异常流量（每分钟请求数超过阈值）
awk '{
    minute = substr($4, 2, 17)
    count[minute]++
}
END {
    for (m in count) {
        if (count[m] > 1000) {
            print "HIGH TRAFFIC:", m, count[m], "req/min"
        }
    }
}' access.log

# 生成 CSV 格式的报告
awk 'BEGIN {
    print "IP,Requests,Bytes,Errors"
}
{
    ip[$1]++
    bytes[$1] += $10
    if ($9 >= 400) errors[$1]++
}
END {
    for (i in ip) {
        printf "%s,%d,%d,%d\n", i, ip[i], bytes[i], errors[i]+0
    }
}' access.log | sort -t, -k2 -rn | head -100
```

#### 7.2 配置文件处理组合

```bash
# 提取 Nginx 配置中的 server 块
awk '/^server\s*\{/{p=1} p{print} /^\}/{if(p) p=0}' nginx.conf

# 批量修改配置文件
find /etc/nginx -name "*.conf" -exec \
    grep -l "old_domain" {} \; | \
    xargs sed -i 's/old_domain/new_domain/g'

# 验证配置文件语法
find /etc/nginx -name "*.conf" -exec \
    nginx -t -c {} \; 2>&1 | grep -v "successful"
```

#### 7.3 系统监控组合

```bash
# 监控系统资源
watch -n 1 'echo "=== CPU ==="; top -bn1 | head -5; echo ""; echo "=== Memory ==="; free -h; echo ""; echo "=== Disk ==="; df -h /'

# 分析 /proc/meminfo
cat /proc/meminfo | awk -F: '{
    gsub(/^[ \t]+/, "", $2)
    printf "%-25s %s\n", $1, $2
}'

# 监控网络连接
ss -tn | awk 'NR>1 {print $4}' | sort | uniq -c | sort -rn | head -20

# 分析进程内存使用
ps aux | awk 'NR>1 {
    printf "%-10s %5s %5s %s\n", $1, $3, $4, $11
}' | sort -k3 -rn | head -20
```

---

## 💻 实战练习

### 练习 1：grep 实战

**目标**：使用 grep 完成各种文本搜索任务。

```bash
# 1. 查找所有包含 "error" 的日志行
grep -i "error" /var/log/syslog | wc -l

# 2. 查找 IP 地址
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" /var/log/nginx/access.log | head -10

# 3. 查找 404 错误的 URL
grep " 404 " /var/log/nginx/access.log | awk '{print $7}' | sort | uniq -c | sort -rn

# 4. 排除健康检查请求
grep -v "GET /health" /var/log/nginx/access.log | wc -l

# 5. 使用正则提取日期
grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" /var/log/syslog | sort -u

# 6. 递归搜索配置文件
grep -r "max_connections" /etc/mysql/
```

### 练习 2：sed 实战

**目标**：使用 sed 完成文本处理任务。

```bash
# 1. 批量替换配置文件
echo "server_name old.example.com;" > /tmp/test.conf
sed -i 's/old\.example\.com/new.example.com/g' /tmp/test.conf
cat /tmp/test.conf

# 2. 删除配置文件中的注释和空行
cat /etc/ssh/sshd_config | sed '/^#/d; /^$/d' | head -20

# 3. 在文件开头添加时间戳
sed -i "1i\# Last modified: $(date)" /tmp/test.conf

# 4. 提取配置文件中的值
echo "max_connections = 1000" | sed -E 's/.*=\s*(.*)/\1/'

# 5. 批量修改文件扩展名
for f in *.txt; do
    mv "$f" "$(echo $f | sed 's/\.txt$/.md/')"
done
```

### 练习 3：awk 实战

**目标**：使用 awk 完成数据分析任务。

```bash
# 1. 统计 Nginx 日志状态码分布
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 2. 统计每个 IP 的请求量和流量
awk '{
    ip[$1]++
    bytes[$1] += $10
}
END {
    for (i in ip) printf "%10d %10d %s\n", ip[i], bytes[i], i
}' /var/log/nginx/access.log | sort -rn | head -20

# 3. 计算平均响应大小
awk '{sum+=$10; count++} END {printf "Average: %.2f bytes\n", sum/count}' /var/log/nginx/access.log

# 4. 查找访问量最大的 URL
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# 5. 生成每小时统计
awk '{
    hour = substr($4, 14, 2)
    count[hour]++
}
END {
    for (h in count) printf "%s:00 - %d requests\n", h, count[h]
}' /var/log/nginx/access.log | sort

# 6. 查找慢请求（假设最后字段是响应时间）
# awk '$NF > 1.0 {print $4, $7, $NF"s"}' /var/log/nginx/access.log
```

### 练习 4：组合技实战

**目标**：使用三剑客组合完成复杂任务。

```bash
# 1. 生成完整的 Nginx 分析报告
cat > /tmp/nginx_report.sh << 'SCRIPT'
#!/bin/bash
LOG="/var/log/nginx/access.log"
echo "=== Nginx Report $(date) ==="
echo ""
echo "Total Requests: $(wc -l < $LOG)"
echo "Unique IPs: $(awk '{print $1}' $LOG | sort -u | wc -l)"
echo ""
echo "Status Code Distribution:"
awk '{print $9}' $LOG | sort | uniq -c | sort -rn
echo ""
echo "Top 10 IPs:"
awk '{print $1}' $LOG | sort | uniq -c | sort -rn | head -10
echo ""
echo "Top 10 URLs:"
awk '{print $7}' $LOG | sort | uniq -c | sort -rn | head -10
SCRIPT
chmod +x /tmp/nginx_report.sh

# 2. 查找并清理大日志文件
find /var/log -name "*.log" -size +100M -exec ls -lh {} + | \
    awk '{print $5, $9}' | sort -rh

# 3. 监控实时错误率
tail -f /var/log/nginx/access.log | awk '{
    total++
    if ($9 >= 400) errors++
    if (total % 100 == 0) printf "Total: %d  Errors: %d  Rate: %.2f%%\n", total, errors, errors/total*100
}'
```

---

## 🎯 面试题精选

### 面试题 1：grep -E 和 grep -P 有什么区别？

**参考答案**：

| 特性 | grep -E (ERE) | grep -P (PCRE) |
|------|---------------|-----------------|
| 引擎 | POSIX ERE | PCRE |
| \d \w \s | 不支持 | 支持 |
| 反向引用 \1 | 不支持 | 支持 |
| 前瞻/后顾断言 | 不支持 | 支持 |
| 非贪婪量词 *? | 不支持 | 支持 |
| 性能 | 快 | 较慢 |
| 可移植性 | 高 | 低（需要 PCRE 库） |

**使用建议**：
- 简单模式匹配：使用 grep（BRE）
- 多模式匹配：使用 grep -E
- 复杂正则（需要断言、反向引用）：使用 grep -P

### 面试题 2：awk 如何处理 CSV 文件？

**参考答案**：

```bash
# 简单 CSV（字段中没有逗号）
awk -F, '{print $1, $3}' data.csv

# 处理带引号的 CSV（字段中可能有逗号）
# 使用 FPAT（gawk 4.0+）
awk -v FPAT='([^,]*)|("[^"]*")' '{print $1, $3}' data.csv

# 或者使用 python 处理复杂 CSV
python3 -c "
import csv
with open('data.csv') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row[0], row[2])
"
```

### 面试题 3：如何使用 sed 在文件的特定行后插入内容？

**参考答案**：

```bash
# 在第 5 行后插入
sed -i '5a\new line content' file.txt

# 在匹配行后插入
sed -i '/pattern/a\new line content' file.txt

# 在匹配行后插入多行
sed -i '/pattern/a\line1\nline2\nline3' file.txt

# 在文件末尾追加
sed -i '$a\new line content' file.txt
```

### 面试题 4：如何统计 Nginx 日志中每个 IP 的请求量？

**参考答案**：

```bash
# 使用 awk
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# 使用 awk 数组（更高效，不需要 sort）
awk '{count[$1]++} END {for (ip in count) print count[ip], ip}' access.log | sort -rn | head -20

# 使用 awk 的 PROCINFO 数组排序（gawk 4.0+）
awk '{count[$1]++} END {
    PROCINFO["sorted_in"] = "@val_num_desc"
    for (ip in count) {
        print count[ip], ip
        if (++n >= 20) break
    }
}' access.log
```

### 面试题 5：grep、sed、awk 各自适合什么场景？

**参考答案**：

| 工具 | 适合场景 | 不适合场景 |
|------|----------|------------|
| grep | 文本搜索、过滤、计数 | 字段处理、复杂逻辑 |
| sed | 文本替换、删除、插入 | 统计分析、字段计算 |
| awk | 字段处理、统计分析、报表生成 | 简单搜索（grep 更快） |

**组合使用**：
```bash
# grep 过滤 + awk 处理
grep "error" access.log | awk '{print $1, $7}'

# awk 统计 + sort 排序
awk '{print $1}' access.log | sort | uniq -c | sort -rn
```

### 面试题 6：如何处理大文件（10GB+）的文本处理？

**参考答案**：

1. **使用流式处理**（不要把整个文件加载到内存）
   ```bash
   # 好：逐行处理
   awk '{...}' large_file
   
   # 差：加载整个文件
   python3 -c "lines = open('file').readlines()"
   ```

2. **使用 grep 先过滤**
   ```bash
   grep "pattern" large_file | awk '{print $1}'
   ```

3. **使用并行处理**
   ```bash
   split -n l/4 -d large_file part_
   for f in part_*; do awk '{...}' "$f" > "out_$f" & done
   wait
   ```

4. **使用 ripgrep**（比 grep 快 2-10 倍）
   ```bash
   rg "pattern" large_file
   ```

5. **使用 mawk**（比 gawk 快）
   ```bash
   mawk '{print $1}' large_file
   ```

### 面试题 7：如何使用正则表达式匹配 IP 地址？

**参考答案**：

```bash
# 简单匹配（可能匹配到无效 IP）
grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" file

# 精确匹配（0-255）
grep -oE "\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b" file

# 使用 PCRE
grep -oP "\b(?:\d{1,3}\.){3}\d{1,3}\b" file

# 使用 awk
awk '{
    for (i=1; i<=NF; i++) {
        if ($i ~ /^([0-9]{1,3}\.){3}[0-9]{1,3}$/) print $i
    }
}' file
```

---

## 📚 深入阅读

### 官方文档
- [GNU Grep Manual](https://www.gnu.org/software/grep/manual/)
- [GNU Sed Manual](https://www.gnu.org/software/sed/manual/)
- [Gawk Manual](https://www.gnu.org/software/gawk/manual/)
- [PCRE Documentation](https://www.pcre.org/)

### 推荐书籍
- 《sed & awk》(Dale Dougherty) - sed 和 awk 的经典教材
- 《Mastering Regular Expressions》(Jeffrey Friedl) - 正则表达式权威指南
- 《The AWK Programming Language》(Aho, Kernighan, Weinberger) - awk 之父的著作
- 《Shell 脚本学习指南》- 实用的 Shell 编程指南

### 在线工具
- [Regex101](https://regex101.com/) - 在线正则表达式测试
- [RegExr](https://regexr.com/) - 正则表达式学习和测试
- [Explain Shell](https://explainshell.com/) - Shell 命令解释

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 NFA 和 DFA 引擎的区别
- [ ] 能说明 grep -E 和 grep -P 的区别
- [ ] 能解释 sed 的模式空间和保持空间
- [ ] 能说明 awk 的工作流程（BEGIN/主体/END）
- [ ] 能区分 BRE、ERE、PCRE 三种正则表达式语法
- [ ] 能解释 awk 数组的工作原理
- [ ] 能说明 grep、sed、awk 各自的适用场景
- [ ] 能解释正则表达式中贪婪和惰性量词的区别

### 实操检查点
- [ ] 能使用 grep 进行各种文本搜索
- [ ] 能使用 sed 进行文本替换、删除、插入
- [ ] 能使用 awk 进行字段处理和统计分析
- [ ] 能编写 Nginx/Apache 日志分析脚本
- [ ] 能使用正则表达式匹配 IP、邮箱、URL 等
- [ ] 能使用三剑客组合完成复杂任务
- [ ] 能进行性能优化（grep -F、LC_ALL=C、并行处理）
- [ ] 能处理大文件（10GB+）的文本处理

---

*Day 04 完成 | 2026-04-25*
