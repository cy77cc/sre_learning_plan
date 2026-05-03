# Day 21: 字符串处理与正则 — sed/awk 进阶

> 📅 日期：2026-05-02
> 📖 学习主题：字符串处理与正则 — sed/awk 进阶
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 04 (文本处理基础)、Day 20 (数组操作)

---

## 🎯 学习目标

完成 Day 21 的学习后，你应该掌握：

- 掌握 Bash 内置字符串操作（不依赖外部命令）
- 理解 sed 的多行处理、hold space 和分支跳转
- 掌握 awk 的用户自定义函数、getline 和多维数组
- 能够使用 sed/awk 进行复杂的日志分析和数据处理
- 在 SRE 工作中灵活应用字符串处理技术

---

## 📖 核心知识点

### 1. Bash 内置字符串操作

Bash 提供了丰富的内置字符串操作，不需要调用外部命令（如 sed、awk），性能更好。

#### 1.1 字符串长度

```bash
str="Hello, World!"

# 获取长度
echo ${#str}              # 13

# 获取数组元素长度
arr=("hello" "world")
echo ${#arr[0]}           # 5
echo ${#arr[@]}           # 2
```

#### 1.2 字符串切片

```bash
str="Hello, World!"

# 从位置开始到末尾
echo ${str:7}             # World!

# 从位置开始取指定长度
echo ${str:0:5}           # Hello

# 从末尾开始
echo ${str: -6}           # World!（注意负号前的空格）

# 从末尾开始取指定长度
echo ${str: -6:5}         # World
```

#### 1.3 模式删除

```bash
filepath="/home/user/documents/report.tar.gz"

# 删除前缀匹配（最短匹配）
echo ${filepath#*/}       # home/user/documents/report.tar.gz

# 删除前缀匹配（最长匹配）
echo ${filepath##*/}      # report.tar.gz

# 删除后缀匹配（最短匹配）
echo ${filepath%.*}       # /home/user/documents/report.tar

# 删除后缀匹配（最长匹配）
echo ${filepath%%.*}      # /home/user/documents/report
```

**模式删除速查表**：

| 操作 | 语法 | 示例 | 结果 |
|------|------|------|------|
| 删除前缀（最短） | `${var#pattern}` | `${filepath#*/}` | `home/user/...` |
| 删除前缀（最长） | `${var##pattern}` | `${filepath##*/}` | `report.tar.gz` |
| 删除后缀（最短） | `${var%pattern}` | `${filepath%.*}` | `.../report.tar` |
| 删除后缀（最长） | `${var%%pattern}` | `${filepath%%.*}` | `.../report` |

#### 1.4 模式替换

```bash
str="Hello, World! Hello, Bash!"

# 替换第一个匹配
echo ${str/Hello/Hi}     # Hi, World! Hello, Bash!

# 替换所有匹配
echo ${str//Hello/Hi}    # Hi, World! Hi, Bash!

# 替换开头匹配
echo ${str/#Hello/Hi}    # Hi, World! Hello, Bash!

# 替换结尾匹配
echo ${str/%Bash/Shell}  # Hello, World! Hello, Shell!
```

**模式替换速查表**：

| 操作 | 语法 | 示例 | 结果 |
|------|------|------|------|
| 替换第一个 | `${var/old/new}` | `${str/Hello/Hi}` | 第一个 Hello 变 Hi |
| 替换所有 | `${var//old/new}` | `${str//Hello/Hi}` | 所有 Hello 变 Hi |
| 替换开头 | `${var/#old/new}` | `${str/#Hello/Hi}` | 开头 Hello 变 Hi |
| 替换结尾 | `${var/%old/new}` | `${str/%Bash/Shell}` | 结尾 Bash 变 Shell |

#### 1.5 大小写转换（Bash 4.0+）

```bash
str="Hello, World!"

# 转小写
echo ${str,,}             # hello, world!
echo ${str,}              # hello, World!（只转换第一个字符）

# 转大写
echo ${str^^}             # HELLO, WORLD!
echo ${str^}              # Hello, World!（只转换第一个字符）

# 首字母大写
name="john doe"
echo ${name^}             # John doe
echo ${name^^}            # JOHN DOE
```

#### 1.6 变量长度和存在性检查

```bash
# 变量存在性检查
unset var

# 如果变量未定义，返回 "default"
echo ${var:-default}      # default

# 如果变量未定义或为空，返回 "default"
echo ${var:=default}      # default（同时赋值）

# 如果变量未定义，报错
echo ${var:?变量未定义}   # 报错退出

# 如果变量已定义，返回 "exists"
echo ${var:+exists}       # 空（因为 var 未定义）

# 检查变量是否定义
if [[ -z ${var+x} ]]; then
    echo "var 未定义"
fi
```

---

### 2. sed 进阶

#### 2.1 多行处理命令

sed 默认按行处理，但提供了多行处理命令：

| 命令 | 含义 |
|------|------|
| `N` | 将下一行追加到模式空间 |
| `P` | 打印模式空间的第一行 |
| `D` | 删除模式空间的第一行 |
| `n` | 读取下一行到模式空间（覆盖） |

**N 命令：合并行**

```bash
# 将两行合并为一行
echo -e "line1\nline2\nline3\nline4" | sed 'N;s/\n/ /'
# 输出：
# line1 line2
# line3 line4

# 将连续的三行合并
echo -e "a\nb\nc\nd\ne\nf" | sed 'N;N;s/\n/ /g'
# 输出：
# a b c
# d e f
```

**P 和 D 命令：处理多行模式空间**

```bash
# 打印模式空间的第一行（当模式空间包含多行时）
echo -e "line1\nline2\nline3" | sed -n 'N;P'
# 输出：
# line1

# 删除模式空间的第一行
echo -e "line1\nline2\nline3" | sed 'N;D'
# 输出：
# line3
```

#### 2.2 Hold Space 高级用法

sed 有两个缓冲区：
- **模式空间（Pattern Space）**：当前处理的行
- **保持空间（Hold Space）**：临时存储区域

| 命令 | 含义 |
|------|------|
| `h` | 将模式空间复制到保持空间（覆盖） |
| `H` | 将模式空间追加到保持空间 |
| `g` | 将保持空间复制到模式空间（覆盖） |
| `G` | 将保持空间追加到模式空间 |
| `x` | 交换模式空间和保持空间 |

**反转文件行序**：

```bash
echo -e "1\n2\n3\n4\n5" | sed -n '1!G;h;$p'
# 输出：
# 5
# 4
# 3
# 2
# 1
```

**解释**：
1. `1!G`：除第一行外，将保持空间追加到模式空间
2. `h`：将模式空间复制到保持空间
3. `$p`：在最后一行打印

**在匹配行前后插入空行**：

```bash
# 在包含 "ERROR" 的行前后插入空行
sed '/ERROR/{x;p;x;G;}' logfile.txt
```

#### 2.3 分支跳转命令

| 命令 | 含义 |
|------|------|
| `b label` | 无条件跳转到标签 |
| `b` | 跳转到脚本末尾（跳过后续命令） |
| `t label` | 如果上次替换成功，跳转到标签 |
| `T label` | 如果上次替换失败，跳转到标签（GNU sed） |

**使用标签实现条件处理**：

```bash
# 如果行包含 "ERROR"，替换并跳转到 end 标签
sed '/ERROR/{
    s/ERROR/CRITICAL/
    b end
}
s/.*/INFO: &/
:end' logfile.txt
```

**使用 t 命令实现循环替换**：

```bash
# 循环删除连续的空行直到只剩一个
sed '/^$/{
    N
    /^\n$/ba
    P
    D
    :a
    s/^\n$//
}' file.txt

# 更简洁的写法
sed '/^$/N;/^\n$/d' file.txt
```

#### 2.4 正则捕获组和反向引用

```bash
# 使用捕获组和反向引用
echo "2024-01-15" | sed 's/\([0-9]\{4\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\)/\3\/\2\/\1/'
# 输出：15/01/2024

# 使用 -E 选项简化（扩展正则）
echo "2024-01-15" | sed -E 's/([0-9]{4})-([0-9]{2})-([0-9]{2})/\3\/\2\/\1/'
# 输出：15/01/2024

# 交换两个字段
echo "first:last" | sed -E 's/([^:]+):([^:]+)/\2:\1/'
# 输出：last:first
```

**GNU sed 的 \w、\s 等元字符**：

```bash
# 匹配单词字符
echo "hello world" | sed -E 's/\w+/WORD/g'
# 输出：WORD WORD

# 匹配空白字符
echo "hello   world" | sed -E 's/\s+/ /g'
# 输出：hello world
```

#### 2.5 sed 实用技巧

**提取配置文件中的值**：

```bash
# 提取 nginx 配置中的端口号
sed -n 's/.*listen[[:space:]]*\([0-9]*\).*/\1/p' /etc/nginx/nginx.conf

# 提取所有 server_name
sed -n 's/.*server_name[[:space:]]*\([^;]*\).*/\1/p' /etc/nginx/nginx.conf
```

**批量修改配置文件**：

```bash
# 修改 MySQL 配置
sed -i '/^\[mysqld\]/a\
max_connections = 1000\
innodb_buffer_pool_size = 2G' /etc/mysql/my.cnf

# 注释掉某行
sed -i 's/^#*\(max_connections\)/#\1/' /etc/mysql/my.cnf

# 取消注释
sed -i 's/^#\s*\(max_connections\)/\1/' /etc/mysql/my.cnf
```

---

### 3. awk 编程语言

#### 3.1 用户自定义函数

```bash
# 定义函数
awk '
function abs(x) {
    return (x < 0) ? -x : x
}

function max(a, b) {
    return (a > b) ? a : b
}

function min(a, b) {
    return (a < b) ? a : b
}

function percentage(part, total) {
    if (total == 0) return 0
    return sprintf("%.2f", part / total * 100)
}

{
    print "绝对值:", abs($1)
    print "最大值:", max($1, $2)
    print "百分比:", percentage($1, $2)
}
' <<< "10 50"
```

**带局部变量的函数**：

```bash
awk '
function factorial(n,    i, result) {
    # i 和 result 是局部变量（通过额外的参数列表声明）
    result = 1
    for (i = 1; i <= n; i++) {
        result *= i
    }
    return result
}

{
    print "阶乘:", factorial($1)
}
' <<< "5"
# 输出：阶乘: 120
```

#### 3.2 getline 命令

`getline` 用于从文件、管道或变量中读取输入：

```bash
# 从文件读取
awk '{
    getline line < "other.txt"
    print $0, ":", line
}' input.txt

# 从管道读取
awk '{
    cmd = "hostname"
    cmd | getline hostname
    close(cmd)
    print $0, "on", hostname
}' input.txt

# 读取下一行
awk '{
    getline next_line
    print "当前:", $0
    print "下一行:", next_line
}' input.txt

# 从变量读取
awk 'BEGIN {
    data = "line1\nline2\nline3"
    while ((getline line < data) > 0) {
        print line
    }
}'
```

#### 3.3 多维数组（模拟）

awk 不支持真正的多维数组，但可以用下标模拟：

```bash
# 模拟二维数组
awk '
BEGIN {
    # 使用 SUBSEP 作为分隔符（默认是 \034）
    rows = 3
    cols = 3

    # 填充数组
    for (i = 0; i < rows; i++) {
        for (j = 0; j < cols; j++) {
            arr[i, j] = i * cols + j
        }
    }

    # 打印数组
    for (i = 0; i < rows; i++) {
        for (j = 0; j < cols; j++) {
            printf "%4d", arr[i, j]
        }
        printf "\n"
    }
}'

# 使用自定义分隔符
awk 'BEGIN {
    SUBSEP = ","
    arr["web",0] = "web01"
    arr["web",1] = "web02"
    arr["db",0] = "db01"

    for (key in arr) {
        split(key, parts, SUBSEP)
        print "组:", parts[1], "索引:", parts[2], "值:", arr[key]
    }
}'
```

#### 3.4 格式化输出（printf）

```bash
# 基本格式化
awk 'BEGIN {
    printf "%-20s %10s %10s\n", "服务器", "CPU%", "内存%"
    printf "%-20s %10s %10s\n", "--------------------", "----------", "----------"
}'

# 从数据格式化
echo -e "web01 45 78\nweb02 67 89\ndb01 23 56" | awk '{
    printf "%-20s %9.1f%% %9.1f%%\n", $1, $2, $3
}'

# 数字格式化
awk 'BEGIN {
    # 整数
    printf "十进制: %d\n", 255
    printf "八进制: %o\n", 255
    printf "十六进制: %x\n", 255

    # 浮点数
    printf "默认: %f\n", 3.14159
    printf "科学计数: %e\n", 3.14159
    printf "两位小数: %.2f\n", 3.14159

    # 字符串
    printf "左对齐: %-20s\n", "hello"
    printf "右对齐: %20s\n", "hello"
}'
```

#### 3.5 与其他命令的管道协作

```bash
# 使用 system() 调用外部命令
awk '{
    cmd = "echo " $1 " | tr a-z A-Z"
    cmd | getline result
    close(cmd)
    print $1, "->", result
}' <<< "hello"

# 使用管道处理
awk '{
    print $1
}' /etc/passwd | sort | uniq -c | sort -rn | head -10

# 复杂管道链
awk -F: '$3 >= 1000 {print $1}' /etc/passwd | while read user; do
    echo "用户: $user"
    last "$user" | head -1
done
```

#### 3.6 awk 内置函数

**字符串函数**：

```bash
awk 'BEGIN {
    # length
    print length("hello")          # 5

    # substr
    print substr("hello world", 7) # world
    print substr("hello world", 1, 5) # hello

    # index
    print index("hello world", "world") # 7

    # split
    n = split("a:b:c:d", arr, ":")
    print "元素数:", n
    for (i = 1; i <= n; i++) print arr[i]

    # gsub
    str = "hello world"
    gsub(/world/, "awk", str)
    print str                      # hello awk

    # match
    if (match("hello 123 world", /[0-9]+/)) {
        print "匹配:", substr($0, RSTART, RLENGTH)
    }

    # sprintf
    printf "%s\n", sprintf("%05d", 42)  # 00042
}'
```

**数学函数**：

```bash
awk 'BEGIN {
    print int(3.7)       # 3
    print sqrt(16)       # 4
    print exp(1)         # 2.71828
    print log(2.71828)   # 1
    print sin(3.14159)   # ~0
    print cos(0)         # 1
    print atan2(1, 1)    # ~0.7854 (π/4)
    print rand()         # 0-1 之间的随机数
    srand()              # 设置随机种子
}'
```

---

### 4. sed/awk 进阶实战

#### 4.1 Nginx 日志复杂分析

```bash
#!/bin/bash
#============================================================
# Nginx 日志深度分析脚本
# 用法: ./nginx_analysis.sh [日志文件]
#============================================================

set -euo pipefail

LOG_FILE="${1:-/var/log/nginx/access.log}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "错误: 日志文件不存在: $LOG_FILE"
    exit 1
fi

echo "=========================================="
echo "  Nginx 日志深度分析报告"
echo "  日志文件: $LOG_FILE"
echo "  分析时间: $(date)"
echo "=========================================="

# 1. 每小时请求量分析
echo ""
echo "--- 每小时请求量 ---"
awk '{
    # 提取小时（假设标准 Nginx 日志格式）
    split($4, dt, ":")
    hour = dt[2]
    count[hour]++
}
END {
    for (h = 0; h < 24; h++) {
        hour = sprintf("%02d", h)
        c = count[hour] + 0
        bar = ""
        for (i = 0; i < c/100; i++) bar = bar "#"
        printf "%s: %6d %s\n", hour, c, bar
    }
}' "$LOG_FILE"

# 2. 响应时间分析（如果日志包含响应时间）
echo ""
echo "--- 响应时间分析 ---"
awk '{
    # 假设响应时间在最后一个字段
    time = $NF
    if (time ~ /^[0-9.]+$/) {
        total += time
        count++
        if (time > max_time) max_time = time
        if (min_time == 0 || time < min_time) min_time = time

        # 分桶统计
        if (time < 0.1) bucket["< 0.1s"]++
        else if (time < 0.5) bucket["0.1-0.5s"]++
        else if (time < 1) bucket["0.5-1s"]++
        else if (time < 5) bucket["1-5s"]++
        else bucket["> 5s"]++
    }
}
END {
    if (count > 0) {
        printf "总请求数: %d\n", count
        printf "平均响应时间: %.3f 秒\n", total/count
        printf "最大响应时间: %.3f 秒\n", max_time
        printf "最小响应时间: %.3f 秒\n", min_time
        print ""
        print "响应时间分布:"
        for (b in bucket) {
            printf "  %-10s: %d\n", b, bucket[b]
        }
    }
}' "$LOG_FILE"

# 3. 异常请求检测
echo ""
echo "--- 异常请求检测 ---"
awk '{
    # 5xx 错误
    if ($9 >= 500) {
        errors[$7]++
        error_ips[$1]++
    }
}
END {
    print "5xx 错误 URL Top 10:"
    n = 0
    for (url in errors) {
        if (n++ >= 10) break
        printf "  %6d %s\n", errors[url], url
    }

    print ""
    print "5xx 错误 IP Top 10:"
    n = 0
    for (ip in error_ips) {
        if (n++ >= 10) break
        printf "  %6d %s\n", error_ips[ip], ip
    }
}' "$LOG_FILE"

# 4. 流量异常检测
echo ""
echo "--- 流量异常检测 ---"
awk '{
    # 每分钟请求量
    split($4, dt, ":")
    minute = dt[2] ":" dt[3]
    count[minute]++
}
END {
    # 计算平均值
    total = 0
    n = 0
    for (m in count) {
        total += count[m]
        n++
    }
    avg = total / n

    # 计算标准差
    sum_sq = 0
    for (m in count) {
        sum_sq += (count[m] - avg)^2
    }
    stddev = sqrt(sum_sq / n)

    # 检测异常（超过 2 倍标准差）
    threshold = avg + 2 * stddev
    print "每分钟平均请求:", int(avg)
    print "标准差:", int(stddev)
    print "异常阈值:", int(threshold)
    print ""
    print "异常时间点:"
    for (m in count) {
        if (count[m] > threshold) {
            printf "  %s: %d 请求\n", m, count[m]
        }
    }
}' "$LOG_FILE"
```

#### 4.2 配置文件批量修改和验证

```bash
#!/bin/bash
#============================================================
# 配置文件批量修改脚本
# 用法: ./config_modifier.sh <配置文件>
#============================================================

set -euo pipefail

CONFIG_FILE="${1:-/etc/nginx/nginx.conf}"
BACKUP_DIR="/etc/nginx/backups"

# 创建备份
backup_config() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"
    cp "$CONFIG_FILE" "${BACKUP_DIR}/nginx_${timestamp}.conf"
    echo "已备份到 ${BACKUP_DIR}/nginx_${timestamp}.conf"
}

# 验证配置
validate_config() {
    if [[ "$CONFIG_FILE" == *"nginx"* ]]; then
        if nginx -t 2>&1; then
            echo "配置验证通过"
            return 0
        else
            echo "配置验证失败"
            return 1
        fi
    fi
}

# 修改 worker_processes
set_worker_processes() {
    local value="$1"
    sed -i "s/worker_processes.*/worker_processes $value;/" "$CONFIG_FILE"
    echo "已设置 worker_processes = $value"
}

# 添加配置项
add_config() {
    local section="$1"
    local config="$2"

    sed -i "/$section/a\\    $config" "$CONFIG_FILE"
    echo "已在 $section 中添加: $config"
}

# 删除配置项
remove_config() {
    local pattern="$1"
    sed -i "/$pattern/d" "$CONFIG_FILE"
    echo "已删除匹配 $pattern 的行"
}

# 批量修改
batch_modify() {
    # 备份
    backup_config

    # 修改
    set_worker_processes "auto"

    # 添加 SSL 配置
    sed -i '/ssl_protocols/a\    ssl_ciphers HIGH:!aNULL:!MD5;' "$CONFIG_FILE"

    # 修改 keepalive_timeout
    sed -i 's/keepalive_timeout.*/keepalive_timeout 65;/' "$CONFIG_FILE"

    # 验证
    if validate_config; then
        echo "批量修改完成"
    else
        echo "修改失败，恢复备份"
        cp "${BACKUP_DIR}/nginx_$(ls -t ${BACKUP_DIR} | head -1)" "$CONFIG_FILE"
    fi
}

# 主程序
main() {
    echo "配置文件: $CONFIG_FILE"
    echo ""

    while true; do
        echo "1. 查看配置"
        echo "2. 修改 worker_processes"
        echo "3. 添加配置项"
        echo "4. 删除配置项"
        echo "5. 批量修改"
        echo "6. 验证配置"
        echo "0. 退出"

        read -rp "选择操作: " choice

        case "$choice" in
            1) cat "$CONFIG_FILE" ;;
            2)
                read -rp "worker_processes 值: " value
                set_worker_processes "$value"
                ;;
            3)
                read -rp "配置节: " section
                read -rp "配置内容: " config
                add_config "$section" "$config"
                ;;
            4)
                read -rp "删除模式: " pattern
                remove_config "$pattern"
                ;;
            5) batch_modify ;;
            6) validate_config ;;
            0) exit 0 ;;
            *) echo "无效选择" ;;
        esac
    done
}

main
```

#### 4.3 CSV/TSV 数据处理

```bash
#!/bin/bash
#============================================================
# CSV 数据处理脚本
# 用法: ./csv_processor.sh <csv文件>
#============================================================

set -euo pipefail

CSV_FILE="${1:-data.csv}"

if [[ ! -f "$CSV_FILE" ]]; then
    echo "错误: 文件不存在: $CSV_FILE"
    exit 1
fi

# 读取 CSV 文件
process_csv() {
    local file="$1"

    # 获取列数
    local cols
    cols=$(head -1 "$file" | awk -F, '{print NF}')

    echo "文件: $file"
    echo "列数: $cols"
    echo "行数: $(wc -l < "$file")"
    echo ""

    # 打印表头
    echo "表头:"
    head -1 "$file" | awk -F, '{
        for (i = 1; i <= NF; i++) {
            printf "  列 %d: %s\n", i, $i
        }
    }'
}

# 统计数值列
stats_column() {
    local file="$1"
    local col="$2"
    local header="$3"

    awk -F, -v col="$col" -v header="$header" '
    NR > 1 && $col ~ /^[0-9.]+$/ {
        sum += $col
        count++
        if ($col > max) max = $col
        if (min == 0 || $col < min) min = $col
    }
    END {
        if (count > 0) {
            printf "%-20s: 数量=%d, 总和=%.2f, 平均=%.2f, 最小=%.2f, 最大=%.2f\n",
                   header, count, sum, sum/count, min, max
        }
    }' "$file"
}

# 筛选行
filter_rows() {
    local file="$1"
    local col="$2"
    local op="$3"
    local value="$4"

    awk -F, -v col="$col" -v op="$op" -v value="$value" '
    NR == 1 || (op == "==" && $col == value) ||
    (op == ">" && $col > value) ||
    (op == "<" && $col < value) ||
    (op == "!=" && $col != value)
    {
        print
    }' "$file"
}

# 主程序
main() {
    process_csv "$CSV_FILE"

    echo ""
    echo "数值列统计:"
    head -1 "$CSV_FILE" | awk -F, '{
        for (i = 1; i <= NF; i++) {
            print i, $i
        }
    }' | while read col_num col_name; do
        stats_column "$CSV_FILE" "$col_num" "$col_name"
    done
}

main
```

---

## 💻 实战练习

### 练习 1：日志分析报告

**目标**：生成 Nginx 每日运营报告。

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

### 练习 2：配置文件批量修改

```bash
# 批量替换配置文件中的端口
find /etc/nginx -name "*.conf" -exec sed -i 's/listen 80/listen 8080/' {} +

# 删除所有空行和注释
sed -i '/^#/d; /^$/d' /etc/nginx/nginx.conf
```

### 练习 3：CSV 数据处理

```bash
# 处理 CSV 文件，计算每列的统计信息
awk -F, '
NR == 1 {for (i=1; i<=NF; i++) header[i]=$i; next}
{
    for (i=1; i<=NF; i++) {
        if ($i ~ /^[0-9.]+$/) {
            sum[i] += $i
            count[i]++
            if ($i > max[i]) max[i] = $i
            if (min[i]=="" || $i < min[i]) min[i] = $i
        }
    }
}
END {
    for (i in header) {
        if (count[i] > 0) {
            printf "%s: avg=%.2f, min=%.2f, max=%.2f\n", header[i], sum[i]/count[i], min[i], max[i]
        }
    }
}' data.csv
```

---

## 🎯 面试题精选

### 1. sed 如何处理多行？

**参考答案**：

sed 默认按行处理，但提供了多行处理命令：

```bash
# N - 将下一行追加到模式空间
echo -e "line1\nline2\nline3" | sed 'N;s/\n/ /'
# 输出：line1 line2（line3 单独一行）

# P - 打印模式空间的第一行
echo -e "line1\nline2" | sed -n 'N;P'
# 输出：line1

# D - 删除模式空间的第一行
echo -e "line1\nline2\nline3" | sed 'N;D'
# 输出：line3
```

### 2. awk 数组是关联数组吗？

**参考答案**：

是的，**awk 的数组都是关联数组**（也称为哈希表或字典）。awk 没有传统意义上的索引数组。

```bash
# awk 数组使用字符串作为键
awk 'BEGIN {
    arr["name"] = "Alice"
    arr["age"] = 30
    arr[1] = "one"    # 数字也被当作字符串

    for (key in arr) {
        print key, "=", arr[key]
    }
}'
```

这与 Bash 不同，Bash 有真正的索引数组（连续整数键）和关联数组之分。

### 3. 如何用 awk 去重？

**参考答案**：

```bash
# 方法 1：使用关联数组
awk '!seen[$0]++' file.txt

# 解释：
# - seen[$0]：以整行为键访问数组
# - !seen[$0]++：第一次见到时值为 0，取反为 1（真），然后自增
# - 后续见到时值为 1+，取反为 0（假）

# 方法 2：更明确的写法
awk '{
    if (!seen[$0]) {
        print
        seen[$0] = 1
    }
}' file.txt

# 方法 3：按字段去重
awk '!seen[$1]++' file.txt  # 按第一列去重
```

### 4. sed 的 hold space 和 pattern space 有什么区别？

**参考答案**：

- **Pattern Space（模式空间）**：sed 当前处理的行，每读入一行都会放入模式空间
- **Hold Space（保持空间）**：临时存储区域，可以在处理过程中保存数据

```bash
# h - 将模式空间复制到保持空间（覆盖）
# H - 将模式空间追加到保持空间
# g - 将保持空间复制到模式空间（覆盖）
# G - 将保持空间追加到模式空间
# x - 交换两个空间

# 示例：反转文件行序
sed -n '1!G;h;$p' file.txt
```

### 5. awk 的 getline 命令有什么用途？

**参考答案**：

`getline` 用于从不同来源读取输入：

```bash
# 从文件读取
awk '{getline line < "other.txt"; print $0, line}' input.txt

# 从命令读取
awk '{cmd = "date"; cmd | getline date; close(cmd); print $0, date}' input.txt

# 读取下一行
awk '{getline next; print "当前:", $0; print "下一行:", next}' input.txt
```

### 6. 如何用 sed 实现非贪婪匹配？

**参考答案**：

sed 默认是贪婪匹配，要实现非贪婪匹配，需要使用否定字符类：

```bash
# 贪婪匹配（匹配到最后一个引号）
echo 'start "hello" world "end"' | sed 's/".*"/REMOVED/'
# 输出：start REMOVED

# 非贪婪匹配（匹配到第一个引号）
echo 'start "hello" world "end"' | sed 's/"[^"]*"/REMOVED/'
# 输出：start REMOVED world "end"
```

### 7. awk 中如何处理多维数组？

**参考答案**：

awk 没有真正的多维数组，但可以用逗号分隔的下标模拟：

```bash
awk 'BEGIN {
    # 创建 3x3 矩阵
    for (i = 1; i <= 3; i++) {
        for (j = 1; j <= 3; j++) {
            arr[i, j] = i * 10 + j
        }
    }

    # 遍历
    for (i = 1; i <= 3; i++) {
        for (j = 1; j <= 3; j++) {
            printf "%4d", arr[i, j]
        }
        printf "\n"
    }
}'
```

---

## 📚 深入阅读

### 官方文档
- [GNU sed Manual](https://www.gnu.org/software/sed/manual/sed.html)
- [GNU awk Manual](https://www.gnu.org/software/gawk/manual/gawk.html)
- [Bash Manual - Shell Parameter Expansion](https://www.gnu.org/software/bash/manual/bash.html#Shell-Parameter-Expansion)

### 推荐书籍
- 《sed & awk》- Dale Dougherty, Arnold Robbins
- 《Effective awk Programming》- Arnold Robbins
- 《Mastering Regular Expressions》- Jeffrey E.F. Friedl

### 在线资源
- [sed one-liners](https://catonmat.net/sed-one-liners-explained)
- [awk one-liners](https://catonmat.net/awk-one-liners-explained)
- [Regular Expressions 101](https://regex101.com/) - 正则表达式在线测试

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 Bash 内置字符串操作（切片、删除、替换）
- [ ] 理解 sed 的模式空间和保持空间
- [ ] 理解 awk 的关联数组特性
- [ ] 知道 sed 的多行处理命令（N、P、D）
- [ ] 理解 awk 的 getline 命令

### 实操检查点
- [ ] 能够使用 Bash 内置操作处理字符串
- [ ] 能够使用 sed 进行多行处理
- [ ] 能够使用 awk 编写自定义函数
- [ ] 能够使用 awk 处理多维数组
- [ ] 能够使用 sed/awk 进行日志分析
- [ ] 能够使用 sed/awk 批量修改配置文件

---

> 📝 **学习笔记**
>
> 记录你在学习过程中的心得和疑问：
>
> 1. ________________________________________________
> 2. ________________________________________________
> 3. ________________________________________________
