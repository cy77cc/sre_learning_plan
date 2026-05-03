# Day 16: Shell 条件判断 — if/elif/else/test 运算符

> 📅 日期：2026-04-27
> 📖 学习主题：Shell 条件判断 — if/elif/else 与 test 运算符
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 15（Shell 脚本基础 — 变量与环境变量）

## 🎯 学习目标

完成 Day 16 的学习后，你应该能够：
- 熟练使用 if/elif/else/fi 构建条件分支
- 掌握 test 命令、[ ] 和 [[ ]] 的使用场景和区别
- 熟练使用文件测试、字符串比较、数值比较操作符
- 理解逻辑运算符（&&、||、!、-a、-o）和短路求值
- 能编写生产级的前置条件检查和健康检查脚本
- 掌握 case 语句的用法

---

## 📖 核心知识点

### 1. if/elif/else/fi 基础语法

#### 1.1 基本结构

```bash
# 完整语法
if condition1; then
    commands1
elif condition2; then
    commands2
elif condition3; then
    commands3
else
    commands4
fi

# 单行写法
if [[ -f /etc/passwd ]]; then echo "exists"; fi

# 简写（仅适合简单情况）
[[ -f /etc/passwd ]] && echo "exists" || echo "not found"
```

#### 1.2 条件判断的执行流程

```
if condition1; then
    commands1         ← condition1 为真（exit code 0）
elif condition2; then
    commands2         ← condition1 为假，condition2 为真
elif condition3; then
    commands3         ← 前两个都为假，condition3 为真
else
    commands4         ← 所有条件都为假
fi

关键点：
- Shell 中的"条件"是一个命令，判断的是它的退出码（exit code）
- 退出码 0 = 真（成功），非 0 = 假（失败）
- 这与大多数编程语言相反！（0 = true, 非0 = false）
```

#### 1.3 任何命令都可以作为条件

```bash
# 因为条件判断的是退出码，所以任何命令都能作为条件

# grep 找到匹配 → 退出码 0 → 条件为真
if grep -q "error" /var/log/syslog; then
    echo "发现错误日志"
fi

# ping 成功 → 退出码 0 → 条件为真
if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    echo "网络连通"
else
    echo "网络不通"
fi

# 命令执行成功 → 退出码 0 → 条件为真
if systemctl is-active nginx; then
    echo "nginx 正在运行"
fi

# 文件存在测试
if [ -f /etc/nginx/nginx.conf ]; then
    echo "nginx 已安装"
fi

# 自定义函数作为条件
is_root() {
    [[ $(id -u) -eq 0 ]]
}

if is_root; then
    echo "当前是 root 用户"
fi
```

#### 1.4 多行与单行写法

```bash
# 单行写法（适合简单条件）
if [[ -f /etc/passwd ]]; then echo "exists"; fi

# 多行写法（推荐用于复杂逻辑）
if [[ -f /etc/passwd ]]; then
    echo "exists"
fi

# elif 链
if [[ "$env" == "production" ]]; then
    echo "生产环境"
elif [[ "$env" == "staging" ]]; then
    echo "预发布环境"
elif [[ "$env" == "development" ]]; then
    echo "开发环境"
else
    echo "未知环境: $env"
    exit 1
fi

# 嵌套 if（不推荐，应该用 elif 替代）
# ❌ 不推荐
if [[ "$a" == 1 ]]; then
    if [[ "$b" == 2 ]]; then
        echo "a=1, b=2"
    fi
fi

# ✅ 推荐
if [[ "$a" == 1 && "$b" == 2 ]]; then
    echo "a=1, b=2"
fi
```

---

### 2. test 命令和 [ ]

#### 2.1 test 命令

```bash
# test 是一个内置命令，用于评估条件表达式
# test 和 [ ] 是等价的

# 以下两种写法完全相同：
test -f /etc/passwd && echo "exists"
[ -f /etc/passwd ] && echo "exists"

# [ 实际上是一个命令，不是语法符号
# 它要求最后一个参数必须是 ]
type [
# [ is a shell builtin

# 查看 test 的帮助
help test
```

#### 2.2 [ ] 和 [[ ]] 的区别

```
┌─────────────────────────────────────────────────────────────────────┐
│                    [ ] vs [[ ]] 对比                                │
├─────────────────┬────────────────────┬──────────────────────────────┤
│ 特性            │ [ ] (test)         │ [[ ]]                        │
├─────────────────┼────────────────────┼──────────────────────────────┤
│ 来源            │ POSIX 标准         │ Bash/Zsh 扩展                │
│ 兼容性          │ 所有 Shell         │ 仅 bash/zsh/ksh93            │
│ 类型            │ 外部命令/builtin   │ Shell 关键字                  │
│ 变量展开        │ 需要引号保护       │ 不需要引号保护                │
│ 正则匹配        │ 不支持             │ =~ 支持                      │
│ 模式匹配        │ 不支持             │ == 支持 glob 模式             │
│ 逻辑运算符      │ -a -o !            │ && || !                      │
│ 分词问题        │ 有（需引号）       │ 无（安全）                    │
│ 性能            │ 稍慢（外部命令）   │ 稍快（内建关键字）            │
└─────────────────┴────────────────────┴──────────────────────────────┘
```

```bash
# === [ ] 的陷阱 ===

# 陷阱 1：变量为空时的分词问题
name=""
[ $name = "hello" ]       # ❌ 展开为 [ = "hello" ] → 语法错误
[ "$name" = "hello" ]     # ✅ 正确：[ "" = "hello" ]

# 陷阱 2：变量包含空格
file="my file.txt"
[ -f $file ]              # ❌ 展开为 [ -f my file.txt ] → 语法错误
[ -f "$file" ]            # ✅ 正确：[ -f "my file.txt" ]

# 陷阱 3：逻辑运算符 -a 和 -o 的歧义
# 如果变量值看起来像操作符
name="-o"
[ "$name" = "test" ]      # ✅ 正确
[ $name = "test" ]        # ❌ 可能被解析为 [ -o = "test" ]

# === [[ ]] 的优势 ===

# 优势 1：变量不需要引号
name=""
[[ $name = "hello" ]]     # ✅ 安全，不会分词

# 优势 2：正则匹配
email="user@example.com"
if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo "有效邮箱"
fi

# 优势 3：模式匹配（glob）
filename="backup_2026.tar.gz"
if [[ "$filename" == backup_*.tar.gz ]]; then
    echo "是备份文件"
fi

# 优势 4：逻辑运算符更自然
name="Alice"
age=25
if [[ "$name" == "Alice" && "$age" -gt 20 ]]; then    # ✅ && 在 [[ ]] 中
    echo "Alice is over 20"
fi

# 对比 [ ] 的写法
if [ "$name" = "Alice" ] && [ "$age" -gt 20 ]; then   # 需要分开写
    echo "Alice is over 20"
fi

# 或使用 -a（不推荐，POSIX 已弃用）
if [ "$name" = "Alice" -a "$age" -gt 20 ]; then
    echo "Alice is over 20"
fi
```

---

### 3. 文件测试操作符

```bash
# 文件测试是最常用的操作，用于检查文件/目录的各种属性

# ===== 存在性测试 =====
[ -e path ]    # 文件存在（任何类型）
[ -a path ]    # 同 -e（旧写法）

# ===== 类型测试 =====
[ -f path ]    # 是普通文件（不是目录、设备等）
[ -d path ]    # 是目录
[ -L path ]    # 是符号链接（也可用 -h）
[ -p path ]    # 是命名管道（FIFO）
[ -S path ]    # 是套接字（socket）
[ -b path ]    # 是块设备
[ -c path ]    # 是字符设备

# ===== 权限测试 =====
[ -r path ]    # 可读
[ -w path ]    # 可写
[ -x path ]    # 可执行
[ -u path ]    # 设置了 SUID 位
[ -g path ]    # 设置了 SGID 位
[ -k path ]    # 设置了 sticky 位

# ===== 内容测试 =====
[ -s path ]    # 文件存在且大小 > 0（非空文件）

# ===== 时间比较 =====
[ file1 -nt file2 ]    # file1 比 file2 新（newer than）
[ file1 -ot file2 ]    # file1 比 file2 旧（older than）
[ file1 -ef file2 ]    # file1 和 file2 指向同一个 inode（硬链接）
```

```bash
# 文件测试的详细示例

# 检查文件是否存在
if [ -f /etc/nginx/nginx.conf ]; then
    echo "nginx 配置文件存在"
fi

# 检查目录是否存在
if [ -d /var/log/nginx ]; then
    echo "nginx 日志目录存在"
fi

# 检查文件是否为空
if [ -s /var/log/syslog ]; then
    echo "日志文件有内容"
else
    echo "日志文件为空"
fi

# 检查符号链接
if [ -L /usr/bin/python ]; then
    echo "python 是符号链接"
    readlink /usr/bin/python    # 显示链接目标
fi

# 检查文件权限
if [ -r /etc/shadow ]; then
    echo "当前用户可以读取 /etc/shadow"
fi

if [ -x /usr/bin/docker ]; then
    echo "docker 可执行"
fi

# 检查 SUID/SGID 位
if [ -u /usr/bin/passwd ]; then
    echo "passwd 设置了 SUID 位"
fi

# 文件比较
if [ /tmp/new_file -nt /tmp/old_file ]; then
    echo "new_file 比 old_file 新"
fi

# 组合检查
check_config() {
    local config_file="$1"

    if [ ! -e "$config_file" ]; then
        echo "ERROR: 配置文件不存在: $config_file" >&2
        return 1
    fi

    if [ ! -f "$config_file" ]; then
        echo "ERROR: 不是普通文件: $config_file" >&2
        return 1
    fi

    if [ ! -r "$config_file" ]; then
        echo "ERROR: 文件不可读: $config_file" >&2
        return 1
    fi

    if [ ! -s "$config_file" ]; then
        echo "WARNING: 配置文件为空: $config_file" >&2
        return 1
    fi

    echo "OK: 配置文件有效: $config_file"
    return 0
}
```

#### 3.1 文件测试的实际应用场景

```bash
# 场景 1：确保目录存在
ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        echo "创建目录: $dir"
    fi
}

# 场景 2：安全地读取配置文件
load_config() {
    local config_file="$1"

    # 文件不存在
    if [[ ! -e "$config_file" ]]; then
        echo "ERROR: 配置文件不存在: $config_file" >&2
        return 1
    fi

    # 不是普通文件
    if [[ ! -f "$config_file" ]]; then
        echo "ERROR: 不是普通文件: $config_file" >&2
        return 1
    fi

    # 文件为空
    if [[ ! -s "$config_file" ]]; then
        echo "WARNING: 配置文件为空: $config_file" >&2
        return 1
    fi

    # 不可读
    if [[ ! -r "$config_file" ]]; then
        echo "ERROR: 文件不可读: $config_file" >&2
        return 1
    fi

    source "$config_file"
    echo "OK: 配置文件已加载: $config_file"
}

# 场景 3：备份前检查原文件
backup_file() {
    local src="$1"
    local dst="$2"

    # 检查源文件
    if [[ ! -f "$src" ]]; then
        echo "ERROR: 源文件不存在: $src" >&2
        return 1
    fi

    # 检查目标文件是否已存在
    if [[ -f "$dst" ]]; then
        echo "WARNING: 目标文件已存在: $dst" >&2
        read -p "是否覆盖? (y/N) " answer
        if [[ "${answer,,}" != "y" ]]; then
            echo "取消备份"
            return 0
        fi
    fi

    # 执行备份
    cp -a "$src" "$dst"
    echo "备份完成: $src → $dst"
}
```

---

### 4. 字符串比较

```bash
# ===== 相等性比较 =====
[ "$str1" = "$str2" ]     # 相等（POSIX 标准）
[ "$str1" == "$str2" ]    # 相等（Bash 扩展，推荐在 [[ ]] 中使用）
[ "$str1" != "$str2" ]    # 不相等

# ===== 空值检查 =====
[ -z "$str" ]             # 字符串为空（长度为 0）
[ -n "$str" ]             # 字符串非空（长度 > 0）

# ===== 模式匹配（[[ ]] 专用） =====
[[ "$str" == pattern ]]   # glob 模式匹配
[[ "$str" =~ regex ]]     # 正则表达式匹配

# ===== 字典序比较 =====
[[ "$str1" < "$str2" ]]   # str1 字典序小于 str2
[[ "$str1" > "$str2" ]]   # str1 字典序大于 str2
```

```bash
# 字符串比较的详细示例

# === 空值检查 ===
name=""

# ❌ 错误：变量未加引号，空值会导致语法错误
[ -z $name ]              # 展开为 [ -z ] → 永远为假！

# ✅ 正确
[ -z "$name" ]            # 真：字符串为空
[ -n "$name" ]            # 假：字符串非空

# 在 [[ ]] 中更安全
[[ -z $name ]]            # ✅ 即使不加引号也安全
[[ -n $name ]]            # ✅

# === 字符串长度 ===
str="Hello"
if [[ ${#str} -gt 3 ]]; then
    echo "字符串长度大于 3"
fi

# === 精确匹配 ===
answer="yes"
if [[ "$answer" == "yes" ]]; then
    echo "用户确认"
fi

# === 正则匹配（Bash 3.0+） ===
ip="192.168.1.100"
if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "有效 IP 地址"
fi

# 提取正则匹配组（Bash 3.0+）
version="nginx/1.18.0"
if [[ "$version" =~ ^nginx/([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[3]}"
    echo "nginx 版本: $major.$minor.$patch"
fi

# === glob 模式匹配（[[ ]] 专用） ===
filename="backup_20260426.tar.gz"

# * 匹配任意字符
if [[ "$filename" == backup_*.tar.gz ]]; then
    echo "是备份文件"
fi

# ? 匹配单个字符
if [[ "$filename" == backup_????????.tar.gz ]]; then
    echo "日期格式正确（8 位）"
fi

# [...] 匹配字符范围
if [[ "$filename" == backup_[0-9]*.tar.gz ]]; then
    echo "日期以数字开头"
fi

# === 字符串包含检查 ===
text="Error: connection timeout"

# 方法 1：glob 模式
if [[ "$text" == *Error* ]]; then
    echo "包含错误信息"
fi

# 方法 2：正则
if [[ "$text" =~ Error ]]; then
    echo "包含错误信息"
fi

# 方法 3：grep（适合变量中存储模式）
if echo "$text" | grep -q "Error"; then
    echo "包含错误信息"
fi
```

#### 4.1 字符串比较的最佳实践

```bash
# 1. 始终用双引号引用变量（在 [ ] 中）
name="Alice"
[[ "$name" == "Alice" ]]    # ✅ 推荐

# 2. 检查变量是否为空
if [[ -z "${var:-}" ]]; then
    echo "变量为空或未设置"
fi

# 3. 检查变量是否非空
if [[ -n "${var:-}" ]]; then
    echo "变量已设置且非空"
fi

# 4. 用户输入验证
read -p "请输入用户名: " username
if [[ ! "$username" =~ ^[a-z][a-z0-9_-]{2,15}$ ]]; then
    echo "用户名格式不正确" >&2
    exit 1
fi

# 5. 命令输出检查
if [[ "$(systemctl is-active nginx)" == "active" ]]; then
    echo "nginx 正在运行"
fi
```

---

### 5. 数值比较

```bash
# ===== 数值比较操作符 =====
[ "$a" -eq "$b" ]    # equal（等于）
[ "$a" -ne "$b" ]    # not equal（不等于）
[ "$a" -gt "$b" ]    # greater than（大于）
[ "$a" -ge "$b" ]    # greater or equal（大于等于）
[ "$a" -lt "$b" ]    # less than（小于）
[ "$a" -le "$b" ]    # less or equal（小于等于）

# ===== 算术比较（(( )) 专用） =====
(( a == b ))    # 等于
(( a != b ))    # 不等于
(( a > b ))     # 大于
(( a >= b ))    # 大于等于
(( a < b ))     # 小于
(( a <= b ))    # 小于等于

# ===== 注意事项 =====
# ❌ 不能用 < > 比较数值（会被当作重定向）
[ 3 > 2 ]      # 实际上创建了文件名为 "2" 的文件！
[ 3 -gt 2 ]    # ✅ 正确

# ❌ 不能用 == 比较数值（在 [ ] 中是字符串比较）
[ 01 == 1 ]    # 假！字符串 "01" != "1"
[ 01 -eq 1 ]   # 真！数值 1 == 1
```

```bash
# 数值比较的详细示例

# === 磁盘使用率检查 ===
disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [[ "$disk_usage" -gt 80 ]]; then
    echo "WARNING: 磁盘使用率 ${disk_usage}% 超过 80%"
fi

# === 内存检查 ===
free_mb=$(free -m | awk '/Mem:/{print $7}')
if [[ "$free_mb" -lt 100 ]]; then
    echo "WARNING: 可用内存不足 100MB"
fi

# === 负载检查 ===
load=$(cat /proc/loadavg | awk '{print $1}')
cpu_count=$(nproc)
# 使用 bc 进行浮点比较
if (( $(echo "$load > $cpu_count * 2" | bc -l) )); then
    echo "WARNING: 负载过高 ($load > $cpu_count * 2)"
fi

# === (( )) 的算术运算 ===
count=5

# 自增
(( count++ ))
echo "$count"    # 6

# 比较
if (( count > 3 )); then
    echo "count 大于 3"
fi

# 三元运算
(( count > 10 )) && echo "大" || echo "小"

# 复杂表达式
if (( (count > 3) && (count < 10) )); then
    echo "count 在 3 到 10 之间"
fi

# === 使用 awk 进行浮点比较 ===
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
if awk "BEGIN {exit !($cpu_usage > 80.0)}"; then
    echo "CPU 使用率超过 80%"
fi
```

#### 5.1 浮点数比较技巧

```bash
# Shell 的 [ ] 和 [[ ]] 只支持整数比较
# 浮点数比较需要借助外部工具

# 方法 1：使用 bc
a=3.14
b=2.71
if (( $(echo "$a > $b" | bc -l) )); then
    echo "$a 大于 $b"
fi

# 方法 2：使用 awk
if awk "BEGIN {exit !($a > $b)}"; then
    echo "$a 大于 $b"
fi

# 方法 3：乘以 100 转为整数（适合两位小数）
a_int=$(echo "$a * 100" | bc | cut -d. -f1)
b_int=$(echo "$b * 100" | bc | cut -d. -f1)
if [[ "$a_int" -gt "$b_int" ]]; then
    echo "$a 大于 $b"
fi

# 方法 4：使用 python（如果安装了）
if python3 -c "exit(0 if $a > $b else 1)"; then
    echo "$a 大于 $b"
fi
```

---

### 6. 逻辑运算符

```bash
# ===== [ ] 中的逻辑运算符 =====
# -a  逻辑与（AND）
# -o  逻辑或（OR）
# !   逻辑非（NOT）

[ condition1 -a condition2 ]    # AND
[ condition1 -o condition2 ]    # OR
[ ! condition ]                 # NOT

# ===== [[ ]] 中的逻辑运算符 =====
# &&  逻辑与
# ||  逻辑或
# !   逻辑非

[[ condition1 && condition2 ]]    # AND
[[ condition1 || condition2 ]]    # OR
[[ ! condition ]]                 # NOT

# ===== 分离条件（推荐） =====
# 使用独立的 [ ] 配合 && 和 ||
[ condition1 ] && [ condition2 ]    # AND
[ condition1 ] || [ condition2 ]    # OR
```

```bash
# 逻辑运算符的详细示例

# === AND 操作 ===
age=25
name="Alice"

# [[ ]] 中使用 &&
if [[ "$name" == "Alice" && "$age" -gt 20 ]]; then
    echo "Alice is over 20"
fi

# 分离写法（推荐，更清晰）
if [[ "$name" == "Alice" ]] && [[ "$age" -gt 20 ]]; then
    echo "Alice is over 20"
fi

# === OR 操作 ===
env="production"
if [[ "$env" == "production" || "$env" == "staging" ]]; then
    echo "生产或预发布环境"
fi

# 分离写法
if [[ "$env" == "production" ]] || [[ "$env" == "staging" ]]; then
    echo "生产或预发布环境"
fi

# === NOT 操作 ===
debug=false
if [[ ! "$debug" == true ]]; then
    echo "非调试模式"
fi

# === 复杂逻辑组合 ===
# 检查是否是工作日的上午 9 点
hour=$(date +%H)
day=$(date +%u)    # 1=Monday, 7=Sunday

if [[ "$day" -ge 1 && "$day" -le 5 && "$hour" -ge 9 && "$hour" -lt 18 ]]; then
    echo "工作时间"
else
    echo "非工作时间"
fi
```

---

### 7. 短路求值（Short-Circuit Evaluation）

```bash
# 短路求值：Shell 在逻辑表达式中提前终止评估

# ===== && 短路（AND） =====
# 如果第一个条件为假，不评估第二个条件
false && echo "这不会执行"
true && echo "这会执行"

# ===== || 短路（OR） =====
# 如果第一个条件为真，不评估第二个条件
true || echo "这不会执行"
false || echo "这会执行"

# ===== 实际应用 =====

# 1. 安全的条件执行
# 如果命令成功，执行后续操作
[[ -f /etc/nginx/nginx.conf ]] && nginx -t && systemctl reload nginx

# 2. 条件默认值
# 如果变量未设置，赋默认值
[[ -z "$PORT" ]] && PORT=8080

# 3. 提前返回模式
# 如果条件不满足，输出错误并退出
[[ -f "$CONFIG_FILE" ]] || { echo "Config not found"; exit 1; }

# 4. 复杂的短路逻辑
# 只有当前两个条件都满足时才执行第三个
is_root && [[ -f /etc/shadow ]] && cat /etc/shadow
```

#### 7.1 短路求值模式

```bash
# 模式 1：条件执行（&&）
# 如果 A 成功，执行 B
command_a && command_b

# 等价于：
if command_a; then
    command_b
fi

# 模式 2：默认执行（||）
# 如果 A 失败，执行 B
command_a || command_b

# 等价于：
if ! command_a; then
    command_b
fi

# 模式 3：条件默认值
# 如果变量为空，设置默认值
[[ -z "$VAR" ]] && VAR="default"

# 等价于：
VAR="${VAR:-default}"

# 模式 4：守卫子句（Guard Clause）
# 如果条件不满足，提前退出
[[ -f "$file" ]] || { echo "File not found: $file"; exit 1; }

# 等价于：
if [[ ! -f "$file" ]]; then
    echo "File not found: $file"
    exit 1
fi

# 模式 5：链式条件
# A 成功后执行 B，B 成功后执行 C
command_a && command_b && command_c

# 等价于：
if command_a; then
    if command_b; then
        command_c
    fi
fi
```

---

### 8. case 语句

```bash
# case 语句用于多分支匹配，比多个 elif 更清晰

# 基本语法
case "$variable" in
    pattern1)
        commands1
        ;;
    pattern2)
        commands2
        ;;
    pattern3|pattern4)    # 多个模式用 | 分隔
        commands3
        ;;
    *)                    # 默认分支
        default_commands
        ;;
esac
```

```bash
# === 命令行参数解析 ===
#!/usr/bin/env bash
case "$1" in
    start)
        echo "启动服务..."
        systemctl start myapp
        ;;
    stop)
        echo "停止服务..."
        systemctl stop myapp
        ;;
    restart)
        echo "重启服务..."
        systemctl restart myapp
        ;;
    status)
        systemctl status myapp
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

# === 文件扩展名处理 ===
for file in *; do
    case "$file" in
        *.tar.gz|*.tgz)
            echo "解压 tar.gz: $file"
            tar xzf "$file"
            ;;
        *.tar.bz2)
            echo "解压 tar.bz2: $file"
            tar xjf "$file"
            ;;
        *.zip)
            echo "解压 zip: $file"
            unzip "$file"
            ;;
        *.gz)
            echo "解压 gz: $file"
            gunzip "$file"
            ;;
        *)
            echo "跳过: $file"
            ;;
    esac
done

# === 模式匹配（Bash 4.0+） ===
read -p "输入 IP 地址: " ip
case "$ip" in
    10.*|172.16.*|192.168.*)
        echo "私有 IP 地址"
        ;;
    127.*)
        echo "回环地址"
        ;;
    0.0.0.0)
        echo "全零地址"
        ;;
    [0-9]*.[0-9]*.[0-9]*.[0-9]*)
        echo "公网 IP 地址"
        ;;
    *)
        echo "无效的 IP 地址"
        ;;
esac

# === 服务管理脚本 ===
#!/usr/bin/env bash
# manage_service.sh

SERVICE="$1"
ACTION="$2"

case "$ACTION" in
    start)
        case "$SERVICE" in
            nginx)  systemctl start nginx ;;
            mysql)  systemctl start mysql ;;
            redis)  systemctl start redis ;;
            *)      echo "未知服务: $SERVICE"; exit 1 ;;
        esac
        ;;
    stop)
        case "$SERVICE" in
            nginx)  systemctl stop nginx ;;
            mysql)  systemctl stop mysql ;;
            redis)  systemctl stop redis ;;
            *)      echo "未知服务: $SERVICE"; exit 1 ;;
        esac
        ;;
    *)
        echo "Usage: $0 <service> {start|stop|restart|status}"
        exit 1
        ;;
esac
```

---

### 9. SRE 实战案例

#### 9.1 部署脚本中的前置条件检查

```bash
#!/usr/bin/env bash
# deploy_checks.sh — 部署前的全面检查

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'    # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

errors=0

# 检查 1：是否以 root 运行
if [[ $(id -u) -ne 0 ]]; then
    log_error "必须以 root 用户运行此脚本"
    (( errors++ ))
else
    log_info "用户检查通过 (root)"
fi

# 检查 2：操作系统版本
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "$ID" == "ubuntu" && "$VERSION_ID" == "22.04" ]]; then
        log_info "操作系统检查通过 ($PRETTY_NAME)"
    else
        log_warn "操作系统版本不匹配: $PRETTY_NAME (期望 Ubuntu 22.04)"
    fi
else
    log_error "无法确定操作系统版本"
    (( errors++ ))
fi

# 检查 3：必要命令是否存在
required_commands=("docker" "docker-compose" "git" "curl" "jq")
for cmd in "${required_commands[@]}"; do
    if command -v "$cmd" &>/dev/null; then
        log_info "命令 '$cmd' 存在: $(command -v "$cmd")"
    else
        log_error "命令 '$cmd' 未找到"
        (( errors++ ))
    fi
done

# 检查 4：磁盘空间
disk_free_mb=$(df / | awk 'NR==2{print int($4/1024)}')
if [[ "$disk_free_mb" -lt 1024 ]]; then
    log_error "磁盘空间不足: ${disk_free_mb}MB (需要至少 1GB)"
    (( errors++ ))
else
    log_info "磁盘空间充足: ${disk_free_mb}MB"
fi

# 检查 5：内存
mem_free_mb=$(free -m | awk '/Mem:/{print $7}')
if [[ "$mem_free_mb" -lt 512 ]]; then
    log_warn "可用内存较低: ${mem_free_mb}MB"
else
    log_info "内存充足: ${mem_free_mb}MB"
fi

# 检查 6：网络连通性
if curl -sf --max-time 5 https://registry.hub.docker.com/v2/ &>/dev/null; then
    log_info "Docker Hub 网络连通"
else
    log_warn "无法连接 Docker Hub，可能影响镜像拉取"
fi

# 检查 7：Docker 服务状态
if systemctl is-active docker &>/dev/null; then
    log_info "Docker 服务运行中"
else
    log_error "Docker 服务未运行"
    (( errors++ ))
fi

# 检查 8：配置文件
CONFIG_FILE="/opt/myapp/config.yaml"
if [[ -f "$CONFIG_FILE" && -r "$CONFIG_FILE" ]]; then
    log_info "配置文件存在且可读: $CONFIG_FILE"
else
    log_error "配置文件不存在或不可读: $CONFIG_FILE"
    (( errors++ ))
fi

# 检查 9：端口是否被占用
APP_PORT=8080
if ss -tlnp | grep -q ":${APP_PORT} "; then
    log_warn "端口 $APP_PORT 已被占用"
    ss -tlnp | grep ":${APP_PORT} "
else
    log_info "端口 $APP_PORT 可用"
fi

# 检查 10：SSL 证书有效期
CERT_FILE="/etc/ssl/certs/myapp.crt"
if [[ -f "$CERT_FILE" ]]; then
    expiry_date=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null)
    current_epoch=$(date +%s)
    days_left=$(( (expiry_epoch - current_epoch) / 86400 ))

    if [[ "$days_left" -lt 30 ]]; then
        log_error "SSL 证书将在 ${days_left} 天后过期"
        (( errors++ ))
    elif [[ "$days_left" -lt 90 ]]; then
        log_warn "SSL 证书将在 ${days_left} 天后过期"
    else
        log_info "SSL 证书有效期充足: ${days_left} 天"
    fi
fi

# 总结
echo ""
if [[ "$errors" -gt 0 ]]; then
    log_error "发现 $errors 个错误，无法继续部署"
    exit 1
else
    log_info "所有检查通过，可以开始部署"
    exit 0
fi
```

#### 9.2 服务健康检查脚本

```bash
#!/usr/bin/env bash
# health_check.sh — 服务健康检查

set -euo pipefail

# 配置
SERVICES=("nginx" "mysql" "redis" "myapp")
HEALTH_URL="http://localhost:8080/health"
TIMEOUT=5

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# 检查系统服务状态
check_service() {
    local service="$1"

    if ! systemctl is-active "$service" &>/dev/null; then
        log "ERROR: $service 未运行"
        return 1
    fi

    log "OK: $service 运行正常"
    return 0
}

# 检查 HTTP 端点
check_http() {
    local url="$1"
    local timeout="$2"

    local http_code
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo "000")

    if [[ "$http_code" -eq 200 ]]; then
        log "OK: HTTP 端点 $url 响应正常 ($http_code)"
        return 0
    else
        log "ERROR: HTTP 端点 $url 响应异常 ($http_code)"
        return 1
    fi
}

# 检查端口
check_port() {
    local host="$1"
    local port="$2"

    if timeout "$TIMEOUT" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        log "OK: $host:$port 端口可访问"
        return 0
    else
        log "ERROR: $host:$port 端口不可访问"
        return 1
    fi
}

# 检查磁盘使用率
check_disk() {
    local path="$1"
    local threshold="$2"

    local usage
    usage=$(df "$path" | awk 'NR==2{print $5}' | tr -d '%')

    if [[ "$usage" -gt "$threshold" ]]; then
        log "ERROR: $path 磁盘使用率 ${usage}% 超过阈值 ${threshold}%"
        return 1
    else
        log "OK: $path 磁盘使用率 ${usage}%"
        return 0
    fi
}

# 检查内存
check_memory() {
    local threshold="$1"

    local usage
    usage=$(free | awk '/Mem:/{printf "%.0f", $3/$2*100}')

    if [[ "$usage" -gt "$threshold" ]]; then
        log "ERROR: 内存使用率 ${usage}% 超过阈值 ${threshold}%"
        return 1
    else
        log "OK: 内存使用率 ${usage}%"
        return 0
    fi
}

# 主检查流程
main() {
    local overall_status=0

    log "========== 健康检查开始 =========="

    # 系统服务检查
    log "--- 系统服务检查 ---"
    for service in "${SERVICES[@]}"; do
        check_service "$service" || overall_status=1
    done

    # HTTP 端点检查
    log "--- HTTP 端点检查 ---"
    check_http "$HEALTH_URL" "$TIMEOUT" || overall_status=1

    # 端口检查
    log "--- 端口检查 ---"
    check_port "localhost" 3306 || overall_status=1    # MySQL
    check_port "localhost" 6379 || overall_status=1    # Redis
    check_port "localhost" 8080 || overall_status=1    # App

    # 资源检查
    log "--- 资源检查 ---"
    check_disk "/" 80 || overall_status=1
    check_disk "/var/log" 90 || overall_status=1
    check_memory 85 || overall_status=1

    # 结果
    log "================================="
    if [[ "$overall_status" -eq 0 ]]; then
        log "所有检查通过"
    else
        log "存在异常，请检查日志"
    fi

    return "$overall_status"
}

main "$@"
```

#### 9.3 操作系统版本判断和兼容性处理

```bash
#!/usr/bin/env bash
# os_compat.sh — 操作系统版本判断和兼容性处理

set -euo pipefail

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS_ID="$ID"
        OS_VERSION="$VERSION_ID"
        OS_NAME="$PRETTY_NAME"
    elif [[ -f /etc/redhat-release ]]; then
        OS_ID="rhel"
        OS_VERSION=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release)
        OS_NAME=$(cat /etc/redhat-release)
    elif [[ "$(uname)" == "Darwin" ]]; then
        OS_ID="macos"
        OS_VERSION=$(sw_vers -productVersion)
        OS_NAME="macOS $OS_VERSION"
    else
        OS_ID="unknown"
        OS_VERSION="unknown"
        OS_NAME="Unknown OS"
    fi

    echo "$OS_ID"
}

# 检测包管理器
detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v apk &>/dev/null; then
        echo "apk"
    elif command -v brew &>/dev/null; then
        echo "brew"
    else
        echo "unknown"
    fi
}

# 安装软件包
install_package() {
    local package="$1"
    local pkg_manager
    pkg_manager=$(detect_package_manager)

    case "$pkg_manager" in
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y "$package"
            ;;
        yum)
            sudo yum install -y "$package"
            ;;
        dnf)
            sudo dnf install -y "$package"
            ;;
        apk)
            sudo apk add "$package"
            ;;
        brew)
            brew install "$package"
            ;;
        *)
            echo "ERROR: 未知的包管理器，无法安装 $package"
            return 1
            ;;
    esac
}

# 主逻辑
main() {
    local os_id
    os_id=$(detect_os)

    echo "检测到操作系统: $OS_NAME"
    echo "包管理器: $(detect_package_manager)"

    case "$os_id" in
        ubuntu|debian)
            echo "Debian/Ubuntu 系统"
            # 特定于 Ubuntu 的配置
            if [[ "$OS_VERSION" == "22.04" || "$OS_VERSION" == "24.04" ]]; then
                echo "支持的 Ubuntu 版本"
            else
                echo "警告: 未测试的 Ubuntu 版本: $OS_VERSION"
            fi
            ;;
        centos|rhel|rocky|almalinux)
            echo "RHEL 系统"
            # 特定于 RHEL 的配置
            if [[ "${OS_VERSION%%.*}" -ge 8 ]]; then
                echo "RHEL 8+，使用 dnf"
            else
                echo "RHEL 7，使用 yum"
            fi
            ;;
        alpine)
            echo "Alpine Linux"
            echo "注意: Alpine 使用 musl libc，某些二进制不兼容"
            ;;
        *)
            echo "未测试的操作系统: $os_id"
            echo "继续执行可能会有问题"
            ;;
    esac
}

main "$@"
```

---

## 💻 实战练习

### 练习 1：文件检查器

```bash
# 编写一个脚本，接受一个文件路径作为参数
# 检查并输出：
# 1. 文件是否存在
# 2. 文件类型（普通文件、目录、符号链接等）
# 3. 文件权限（读、写、执行）
# 4. 文件大小（是否为空）
# 5. 文件的所有者

cat > file_checker.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

file="$1"
# 你的实现...
SCRIPT
```

### 练习 2：端口检查器

```bash
# 编写一个脚本，检查多个端口是否可访问
# 输入：主机名和端口列表
# 输出：每个端口的状态（开放/关闭）

cat > port_checker.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

HOST="${1:?Usage: $0 <host> <port1> [port2] ...}"
shift

# 你的实现...
SCRIPT
```

### 练习 3：条件执行挑战

```bash
# 不使用 if 语句，只用短路求值（&& 和 ||）完成以下任务：

# 1. 如果变量 DIR 不存在则创建
# 2. 如果 docker 命令存在则输出版本
# 3. 如果文件 /tmp/lock 存在则退出
# 4. 如果磁盘使用率超过 90% 则发送告警
```

<details>
<summary>答案</summary>

```bash
# 1. 创建目录
[[ -d "$DIR" ]] || mkdir -p "$DIR"

# 2. 检查 docker
command -v docker &>/dev/null && docker --version

# 3. 检查锁文件
[[ -f /tmp/lock ]] && { echo "已锁定"; exit 1; }

# 4. 磁盘检查
(( $(df / | awk 'NR==2{print $5}' | tr -d '%') > 90 )) && echo "磁盘告警"
```
</details>

---

## 🎯 面试题精选

### 1. [ ] 和 [[ ]] 有什么区别？

**答：**
- `[ ]` 是 POSIX 标准的 test 命令，`[[ ]]` 是 Bash/Zsh 的扩展
- `[[ ]]` 不需要对变量加引号（不会分词）
- `[[ ]]` 支持 `=~` 正则匹配和 `==` glob 模式匹配
- `[[ ]]` 支持 `&&`、`||` 逻辑运算符
- `[ ]` 中需要用 `-a`、`-o` 做逻辑运算（已弃用）
- **推荐**：在 Bash 脚本中使用 `[[ ]]`

### 2. 如何判断文件是否存在且可写？

**答：**
```bash
if [[ -f "$file" && -w "$file" ]]; then
    echo "文件存在且可写"
fi

# 或分离写法
if [[ -f "$file" ]] && [[ -w "$file" ]]; then
    echo "文件存在且可写"
fi
```

### 3. 什么是短路求值？请举例说明。

**答：**
短路求值是指在逻辑表达式中，如果前一个条件已经能确定最终结果，就不再评估后续条件。

```bash
# AND 短路：第一个为假，不评估第二个
false && echo "不会执行"

# OR 短路：第一个为真，不评估第二个
true || echo "不会执行"

# 实际应用：安全的条件执行
[[ -f /etc/passwd ]] && cat /etc/passwd
```

### 4. 以下代码有什么问题？
```bash
if [ $name == "Alice" ]; then
    echo "Hello Alice"
fi
```

**答：**
1. `$name` 未加引号，如果 name 为空，会变成 `[ == "Alice" ]`，导致语法错误
2. 在 `[ ]` 中应该用 `=` 而不是 `==`（虽然 Bash 兼容，但不是 POSIX 标准）

**修复：**
```bash
if [[ "$name" == "Alice" ]]; then
    echo "Hello Alice"
fi
```

### 5. 如何在 Shell 中进行浮点数比较？

**答：**
Shell 的 `[ ]` 和 `[[ ]]` 只支持整数比较。浮点数比较有以下方法：

```bash
# 方法 1：使用 bc
if (( $(echo "$a > $b" | bc -l) )); then
    echo "$a 大于 $b"
fi

# 方法 2：使用 awk
if awk "BEGIN {exit !($a > $b)}"; then
    echo "$a 大于 $b"
fi

# 方法 3：乘以 100 转为整数（适合两位小数）
a_int=$(echo "$a * 100" | bc | cut -d. -f1)
b_int=$(echo "$b * 100" | bc | cut -d. -f1)
if [[ "$a_int" -gt "$b_int" ]]; then
    echo "$a 大于 $b"
fi
```

### 6. case 语句中的模式匹配支持哪些语法？

**答：**
```bash
case "$var" in
    literal)        # 精确匹配
    pattern*)       # 以 pattern 开头
    *pattern)       # 以 pattern 结尾
    *pattern*)      # 包含 pattern
    pattern?)       # pattern 后跟一个字符
    [abc])          # 字符集
    [0-9])          # 字符范围
    p1|p2|p3)       # 多个模式（OR）
    *)              # 默认匹配
esac
```

### 7. 如何判断一个变量是否是数字？

**答：**
```bash
# 方法 1：正则匹配（推荐）
if [[ "$var" =~ ^-?[0-9]+$ ]]; then
    echo "是整数"
fi

# 方法 2：使用 case
case "$var" in
    -|[0-9]|[1-9][0-9]*) echo "是整数" ;;
    *) echo "不是整数" ;;
esac

# 方法 3：使用 expr（POSIX 兼容）
if expr "$var" + 0 &>/dev/null; then
    echo "是整数"
fi
```

### 8. 以下脚本的输出是什么？为什么？

```bash
x=0
if [[ $x -eq 0 ]]; then
    echo "zero"
elif [[ $x -gt 0 ]]; then
    echo "positive"
else
    echo "negative"
fi
```

**答：**
输出 `zero`。因为 `$x` 的值是 0，`-eq 0` 条件为真，执行第一个分支后退出 if 语句。

---

## 📚 深入阅读

- [Bash Conditional Expressions](https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs) — GNU 官方文档
- [ShellCheck](https://www.shellcheck.net/) — 静态分析工具，检查常见错误
- [Bash Guide: Tests and Conditionals](https://mywiki.wooledge.org/BashGuide/TestsAndConditionals) — 详细的条件判断指南
- [Advanced Bash-Scripting Guide: Tests](https://tldp.org/LDP/abs/html/tests.html) — 高级测试技巧

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 if/elif/else/fi 的语法和执行流程
- [ ] 掌握 test 命令、[ ] 和 [[ ]] 的区别
- [ ] 熟练使用文件测试操作符（-f、-d、-e、-s、-r、-w、-x）
- [ ] 掌握字符串比较（=、!=、-z、-n、=~）
- [ ] 掌握数值比较（-eq、-ne、-gt、-ge、-lt、-le）
- [ ] 理解短路求值的原理和应用
- [ ] 掌握 case 语句的模式匹配

### 实操检查点
- [ ] 能编写部署前置条件检查脚本
- [ ] 能编写服务健康检查脚本
- [ ] 能正确处理变量为空的情况（避免语法错误）
- [ ] 能使用正则匹配验证输入（IP、邮箱等）
- [ ] 能使用短路求值简化条件逻辑
