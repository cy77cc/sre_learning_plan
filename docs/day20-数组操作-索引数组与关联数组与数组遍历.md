# Day 20: 数组操作 — 索引数组/关联数组/数组遍历

> 📅 日期：2026-05-02
> 📖 学习主题：数组操作 — 索引数组/关联数组/数组遍历
> ⏰ 预计学习时间：2-3 小时
> 📋 前置知识：Day 11 (循环与条件)、Day 19 (Case 语句)

---

## 🎯 学习目标

完成 Day 20 的学习后，你应该掌握：

- 理解 Bash 索引数组和关联数组的底层实现机制
- 熟练声明、赋值、读取、删除数组元素
- 掌握多种数组遍历方式及其性能差异
- 能够使用 `mapfile`/`readarray` 命令高效填充数组
- 在 SRE 运维脚本中灵活运用数组处理配置、主机列表、监控指标等

---

## 📖 核心知识点

### 1. 索引数组（Indexed Array）

#### 1.1 声明与初始化

**底层原理**：Bash 的数组基于变量名后缀的语法糖。当你声明 `arr[0]="hello"` 时，Bash 内部创建了一个名为 `arr` 的复合变量，其元素通过索引键进行哈希映射。

```bash
# 方法一：直接赋值（自动声明为索引数组）
colors=("red" "green" "blue")

# 方法二：显式声明
declare -a services

# 方法三：逐个赋值
services[0]="nginx"
services[1]="mysql"
services[3]="redis"   # 注意：索引可以不连续，索引 2 为空

# 方法四：追加元素
colors+=("yellow" "purple")

# 方法五：从命令输出初始化
mapfile -t lines < /etc/hosts
# 或
readarray -t lines < /etc/hosts

# 方法六：使用括号初始化（支持换行和引号）
servers=(
    "web01"
    "web02"
    "db01"
    "cache01"
)
```

**重要细节**：Bash 数组索引可以不连续。如果你给 `arr[10]="value"` 赋值而 `arr[1]` 到 `arr[9]` 未定义，Bash 只存储这一个元素，不会分配中间空间。

#### 1.2 读取元素

```bash
servers=("web01" "web02" "db01" "db02" "cache01")

# 读取单个元素
echo ${servers[0]}        # web01
echo ${servers[3]}        # db02

# 使用变量作为索引
i=2
echo ${servers[$i]}       # db01

# 读取所有元素（两种方式）
echo ${servers[@]}        # web01 web02 db01 db02 cache01
echo ${servers[*]}        # web01 web02 db01 db02 cache01

# 关键区别：在双引号中的行为
for s in "${servers[@]}"; do echo "[$s]"; done
# 输出：
# [web01]
# [web02]
# [db01]
# [db02]
# [cache01]

for s in "${servers[*]}"; do echo "[$s]"; done
# 输出（合并为一个元素，IFS 分隔）：
# [web01 web02 db01 db02 cache01]
```

**`@` vs `*` 的本质区别**：

| 特性 | `"${arr[@]}"` | `"${arr[*]}"` |
|------|---------------|---------------|
| 展开方式 | 多个独立的词 | 单个词 |
| 分隔符 | 无（保持独立） | `$IFS`（默认空格） |
| 适用场景 | 循环遍历 | 字符串拼接 |
| 安全性 | 高（保留空格） | 低（丢失边界） |

**在 SRE 脚本中，永远优先使用 `"${arr[@]}"`**，这是避免空格导致 bug 的关键实践。

#### 1.3 数组长度与索引

```bash
servers=("web01" "web02" "db01" "db02" "cache01")

# 数组元素个数
echo ${#servers[@]}       # 5
echo ${#servers[*]}       # 5

# 所有索引（对于不连续数组特别有用）
declare -a sparse
sparse[0]="a"
sparse[5]="f"
sparse[10]="k"

echo ${!sparse[@]}        # 0 5 10
echo ${#sparse[@]}        # 3（不是 11！）

# 单个元素的长度
echo ${#servers[0]}       # 5（"web01" 的长度）
```

#### 1.4 元素操作

```bash
servers=("web01" "web02" "db01" "db02" "cache01")

# 替换元素
servers[2]="mysql-primary"
echo ${servers[@]}
# web01 web02 mysql-primary db02 cache01

# 删除元素
unset servers[4]
echo ${servers[@]}
# web01 web02 mysql-primary db02
echo ${#servers[@]}        # 4

# 删除整个数组
unset servers

# 切片操作（类似 Python 的切片）
nums=(0 1 2 3 4 5 6 7 8 9)
echo ${nums[@]:3:4}       # 3 4 5 6（从索引 3 开始，取 4 个）
echo ${nums[@]: -3}       # 7 8 9（取最后 3 个，注意负号前的空格）

# 查找模式匹配
files=(report.pdf data.csv notes.txt backup.tar.gz)
echo ${files[@]#*.}       # 删除前缀匹配：pdf csv txt tar.gz
echo ${files[@]%.*}       # 删除后缀匹配：report data notes backup
```

#### 1.5 数组切片详解

| 操作 | 语法 | 示例 | 结果 |
|------|------|------|------|
| 从位置开始 | `${arr[@]:pos}` | `${arr[@]:2}` | 从索引 2 到末尾 |
| 指定长度 | `${arr[@]:pos:len}` | `${arr[@]:1:3}` | 从索引 1 取 3 个 |
| 从末尾开始 | `${arr[@]: -n}` | `${arr[@]: -2}` | 最后 2 个元素 |
| 复制数组 | `${arr[@]}` | `new=("${arr[@]}")` | 完整复制 |

**注意**：负数索引前必须有空格，否则会被解释为变量替换的默认值语法。

---

### 2. 关联数组（Associative Array）

#### 2.1 声明与赋值

**版本要求**：关联数组需要 Bash 4.0+（2009 年发布）。macOS 默认的 Bash 3.2 不支持。

```bash
# 检查 Bash 版本
echo ${BASH_VERSINFO[0]}  # 需要 >= 4

# 必须先显式声明
declare -A host_info

# 逐个赋值
host_info["web01"]="192.168.1.10:nginx"
host_info["db01"]="192.168.1.20:mysql"
host_info["cache01"]="192.168.1.30:redis"

# 批量赋值
declare -A config=(
    ["max_connections"]="1000"
    ["timeout"]="30"
    ["log_level"]="info"
    ["retry_count"]="3"
)

# 追加
host_info["lb01"]="192.168.1.40:haproxy"
```

**关键区别**：

| 特性 | 索引数组 | 关联数组 |
|------|----------|----------|
| 声明 | `declare -a`（可选） | `declare -A`（必须） |
| 键类型 | 整数 | 字符串 |
| 默认值 | 未声明自动创建 | 必须先声明 |
| Bash 版本 | 所有版本 | 4.0+ |
| 底层结构 | 连续/哈希 | 哈希表 |

#### 2.2 读取与遍历

```bash
declare -A host_info=(
    ["web01"]="192.168.1.10"
    ["db01"]="192.168.1.20"
    ["cache01"]="192.168.1.30"
)

# 读取单个值
echo ${host_info["web01"]}     # 192.168.1.10

# 所有键
echo ${!host_info[@]}          # web01 db01 cache01（顺序不保证！）

# 所有值
echo ${host_info[@]}           # 192.168.1.10 192.168.1.20 192.168.1.30

# 遍历键值对
for host in "${!host_info[@]}"; do
    ip="${host_info[$host]}"
    echo "主机: $host, IP: $ip"
done

# 检查键是否存在
if [[ -v host_info["db01"] ]]; then
    echo "db01 存在于数组中"
fi

# 检查值是否为空
if [[ -z ${host_info["unknown"]+_} ]]; then
    echo "unknown 键不存在"
fi
```

**重要**：关联数组的遍历顺序**不保证与插入顺序一致**。这是哈希表的固有特性。如果需要有序遍历，可以先对键排序：

```bash
for host in $(echo "${!host_info[@]}" | tr ' ' '\n' | sort); do
    echo "$host -> ${host_info[$host]}"
done
```

#### 2.3 关联数组的高级操作

```bash
declare -A config=(
    ["host"]="localhost"
    ["port"]="5432"
    ["user"]="admin"
    ["dbname"]="mydb"
)

# 合并两个关联数组
declare -A override=(
    ["host"]="prod-db.internal"
    ["port"]="5433"
)

# 合并（覆盖同名键）
for key in "${!override[@]}"; do
    config["$key"]="${override[$key]}"
done

# 删除键值对
unset config["dbname"]

# 获取数组大小
echo "配置项数量: ${#config[@]}"

# 检查某个值是否存在（需要遍历）
value_to_find="admin"
for key in "${!config[@]}"; do
    if [[ "${config[$key]}" == "$value_to_find" ]]; then
        echo "找到键: $key"
    fi
done
```

#### 2.4 模拟多维数组

Bash 不支持真正的多维数组，但可以用关联数组模拟：

```bash
# 模拟二维数组：服务器角色矩阵
declare -A server_roles

# web 组
server_roles["web,0"]="web01"
server_roles["web,1"]="web02"
server_roles["web,2"]="web03"

# db 组
server_roles["db,0"]="db01"
server_roles["db,1"]="db02"

# cache 组
server_roles["cache,0"]="cache01"
server_roles["cache,1"]="cache02"

# 遍历
for key in "${!server_roles[@]}"; do
    IFS=',' read -r group idx <<< "$key"
    echo "组: $group, 索引: $idx, 服务器: ${server_roles[$key]}"
done

# 获取某组的所有服务器
get_group_servers() {
    local group="$1"
    local servers=()

    for key in "${!server_roles[@]}"; do
        if [[ "$key" == "$group,"* ]]; then
            servers+=("${server_roles[$key]}")
        fi
    done

    echo "${servers[@]}"
}

web_servers=$(get_group_servers "web")
echo "Web 服务器: $web_servers"
```

---

### 3. 数组操作详解

#### 3.1 追加元素

```bash
# 索引数组追加
arr=("a" "b" "c")
arr+=("d" "e")              # 追加多个元素
echo ${arr[@]}               # a b c d e

# 指定索引追加
arr[10]="z"                  # 稀疏数组
echo ${arr[@]}               # a b c d e z
echo ${!arr[@]}              # 0 1 2 3 4 10

# 关联数组追加
declare -A map
map["key1"]="value1"
map+=("key2" "value2")      # 错误！关联数组不能这样追加
map["key2"]="value2"         # 正确
```

#### 3.2 删除元素

```bash
arr=("a" "b" "c" "d" "e")

# 删除单个元素
unset arr[2]
echo ${arr[@]}               # a b d e
echo ${#arr[@]}              # 4
echo ${!arr[@]}              # 0 1 3 4（索引不连续）

# 删除整个数组
unset arr
echo ${#arr[@]}              # 0

# 关联数组删除
declare -A map=(["a"]=1 ["b"]=2 ["c"]=3)
unset map["b"]
echo ${!map[@]}              # a c
```

#### 3.3 替换元素

```bash
arr=("nginx" "mysql" "redis" "nginx")

# 替换所有匹配（使用模式匹配）
echo ${arr[@]/nginx/apache}  # apache mysql redis apache

# 替换第一个匹配
echo ${arr[@]/#nginx/apache} # apache mysql redis nginx

# 替换最后一个匹配
echo ${arr[@]/%nginx/apache} # nginx mysql redis apache

# 不修改原数组，需要赋值
new_arr=("${arr[@]/nginx/apache}")
```

#### 3.4 排序

```bash
# 索引数组排序
arr=("banana" "apple" "cherry" "date")

# 使用 sort 命令
IFS=$'\n' sorted=($(sort <<<"${arr[*]}")); unset IFS
echo "${sorted[@]}"          # apple banana cherry date

# 使用管道（更安全）
mapfile -t sorted < <(printf '%s\n' "${arr[@]}" | sort)
echo "${sorted[@]}"

# 关联数组按键排序
declare -A map=(["c"]=3 ["a"]=1 ["b"]=2)
for key in $(printf '%s\n' "${!map[@]}" | sort); do
    echo "$key = ${map[$key]}"
done

# 关联数组按值排序
for key in $(for k in "${!map[@]}"; do echo "$k ${map[$k]}"; done | sort -k2 | awk '{print $1}'); do
    echo "$key = ${map[$key]}"
done
```

#### 3.5 去重

```bash
# 使用关联数组去重
deduplicate() {
    local input=("$@")
    declare -A seen
    local unique=()

    for item in "${input[@]}"; do
        if [[ -z "${seen[$item]}" ]]; then
            seen["$item"]=1
            unique+=("$item")
        fi
    done

    echo "${unique[@]}"
}

arr=("nginx" "mysql" "nginx" "redis" "mysql" "nginx")
result=$(deduplicate "${arr[@]}")
echo "$result"               # nginx mysql redis
```

#### 3.6 合并与交集

```bash
# 合并两个数组
a=("nginx" "mysql" "redis")
b=("postgres" "redis" "mongodb")

# 合并（去重）
merge_arrays() {
    declare -A seen
    local merged=()

    for item in "$@"; do
        if [[ -z "${seen[$item]}" ]]; then
            seen["$item"]=1
            merged+=("$item")
        fi
    done

    echo "${merged[@]}"
}

merged=$(merge_arrays "${a[@]}" "${b[@]}")
echo "合并: $merged"         # nginx mysql redis postgres mongodb

# 交集
intersect_arrays() {
    local a=("$1")
    local b=("$2")
    declare -A count

    for item in "${a[@]}"; do
        ((count[$item]++))
    done

    for item in "${b[@]}"; do
        ((count[$item]++))
    done

    local intersection=()
    for item in "${!count[@]}"; do
        if [[ ${count[$item]} -ge 2 ]]; then
            intersection+=("$item")
        fi
    done

    echo "${intersection[@]}"
}
```

---

### 4. 数组在循环中的使用

#### 4.1 遍历方式对比

```bash
servers=("nginx:80" "mysql:3306" "redis:6379" "elasticsearch:9200")

# 方式 1：直接遍历值（最常用）
for svc in "${servers[@]}"; do
    echo "服务: $svc"
done

# 方式 2：通过索引遍历（需要同时用到索引和值时）
for i in "${!servers[@]}"; do
    echo "索引 $i: ${servers[$i]}"
done

# 方式 3：C 风格循环（适合需要计数器的场景）
for ((i=0; i<${#servers[@]}; i++)); do
    echo "$i: ${servers[$i]}"
done

# 方式 4：while read 管道（适合从命令输出填充）
while IFS= read -r line; do
    servers+=("$line")
done < <(ls /etc/nginx/conf.d/)
```

**性能对比**：

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| `for in "${arr[@]}"` | 简洁、安全 | 无法获取索引 | 只需值 |
| `for i in "${!arr[@]}"` | 获取索引 | 语法稍长 | 需要索引 |
| `for ((i=0;...))` | C 风格、灵活 | 只适合连续索引 | 需要计数器 |
| `while read` | 从命令填充 | 需要额外处理 | 命令输出 |

#### 4.2 mapfile/readarray 命令

`mapfile`（别名 `readarray`）是 Bash 4.0+ 引入的高效数组填充命令。

```bash
# 基本用法：从文件读取到数组
mapfile -t lines < /etc/passwd
echo "行数: ${#lines[@]}"
echo "第一行: ${lines[0]}"

# 跳过前 N 行
mapfile -t -s 2 lines < /etc/passwd  # 跳过前 2 行

# 限制读取行数
mapfile -t -n 10 lines < /etc/passwd  # 只读取 10 行

# 从命令输出读取
mapfile -t processes < <(ps aux | awk '{print $11}' | sort -u)

# 使用自定义分隔符
mapfile -d ':' -t fields <<< "root:x:0:0:root:/root:/bin/bash"

# 带回调函数（每读一行调用一次）
process_line() {
    echo "处理: $REPLY"
}
mapfile -t -C process_line -c 1 lines < /etc/passwd
```

**mapfile vs while read**：

```bash
# while read 方式
declare -a arr1
while IFS= read -r line; do
    arr1+=("$line")
done < /etc/passwd

# mapfile 方式（更高效）
mapfile -t arr2 < /etc/passwd

# 两者结果相同，但 mapfile 更快（减少循环开销）
```

---

### 5. 数组与函数

#### 5.1 传递数组给函数

```bash
# Bash 不能直接传递数组给函数，需要特殊处理

# 方法 1：传递所有参数
print_array() {
    local arr=("$@")
    echo "数组长度: ${#arr[@]}"
    echo "元素: ${arr[@]}"
}

servers=("web01" "web02" "db01")
print_array "${servers[@]}"

# 方法 2：通过 nameref（Bash 4.3+）
process_array() {
    local -n ref=$1  # 声明 nameref
    echo "数组长度: ${#ref[@]}"
    for item in "${ref[@]}"; do
        echo "  - $item"
    done
}

servers=("web01" "web02" "db01")
process_array servers  # 传递数组名，不是值

# 方法 3：通过全局变量
declare -a global_arr=()

add_to_array() {
    global_arr+=("$1")
}

add_to_array "web01"
add_to_array "web02"
echo "${global_arr[@]}"   # web01 web02
```

#### 5.2 从函数返回数组

```bash
# 方法 1：通过 nameref（推荐，Bash 4.3+）
get_servers() {
    local -n result=$1
    result=("web01" "web02" "db01" "db02")
}

declare -a my_servers
get_servers my_servers
echo "服务器: ${my_servers[@]}"

# 方法 2：通过 stdout（需要 mapfile）
get_servers_v2() {
    echo "web01"
    echo "web02"
    echo "db01"
}

mapfile -t servers < <(get_servers_v2)
echo "服务器: ${servers[@]}"

# 方法 3：通过全局变量
declare -a RESULT=()

calculate() {
    RESULT=()
    for i in {1..5}; do
        RESULT+=($((i * 2)))
    done
}

calculate
echo "结果: ${RESULT[@]}"   # 2 4 6 8 10
```

---

## 💻 SRE 实战案例

### 场景 1：批量主机管理

```bash
#!/bin/bash
#============================================================
# 批量主机管理脚本
# 用法: ./batch_host_manager.sh
#============================================================

set -euo pipefail

# 定义服务器分组（关联数组）
declare -A server_groups=(
    ["web"]="web01 web02 web03"
    ["db"]="db01 db02"
    ["cache"]="cache01 cache02"
    ["monitor"]="prometheus grafana"
)

# 定义所有服务器（索引数组）
all_servers=("web01" "web02" "web03" "db01" "db02" "cache01" "cache02" "prometheus" "grafana")

# 按组批量执行命令
deploy_to_group() {
    local group=$1
    local cmd=$2

    local hosts_str="${server_groups[$group]}"
    # 将字符串转为数组
    read -ra hosts <<< "$hosts_str"

    echo "=== 部署到 $group 组 (${#hosts[@]} 台主机) ==="

    for host in "${hosts[@]}"; do
        echo -n "[$host] "
        ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$host" "$cmd" 2>&1 || \
            echo "FAILED"
    done
}

# 检查所有服务器状态
check_all() {
    local failed_hosts=()

    for host in "${all_servers[@]}"; do
        if ! ping -c 1 -W 2 "$host" &>/dev/null; then
            failed_hosts+=("$host")
        fi
    done

    if [[ ${#failed_hosts[@]} -gt 0 ]]; then
        echo "以下主机不可达: ${failed_hosts[*]}"
        return 1
    else
        echo "所有 ${#all_servers[@]} 台主机在线"
    fi
}

# 获取服务器信息
get_server_info() {
    local -n info_ref=$1
    local host=$2

    info_ref=(
        ["hostname"]=$(ssh "$host" "hostname")
        ["ip"]=$(ssh "$host" "hostname -I | awk '{print \$1}'")
        ["os"]=$(ssh "$host" "cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2")
        ["kernel"]=$(ssh "$host" "uname -r")
        ["cpu"]=$(ssh "$host" "nproc")
        ["memory"]=$(ssh "$host" "free -h | awk '/Mem:/ {print \$2}'")
    )
}

# 主菜单
main() {
    echo "批量主机管理"
    echo "服务器总数: ${#all_servers[@]}"

    while true; do
        echo ""
        echo "1. 检查所有服务器"
        echo "2. 按组执行命令"
        echo "3. 获取服务器信息"
        echo "4. 同步配置文件"
        echo "0. 退出"

        read -rp "选择操作: " choice

        case "$choice" in
            1) check_all ;;
            2)
                echo "可用分组: ${!server_groups[*]}"
                read -rp "选择分组: " group
                read -rp "执行命令: " cmd
                deploy_to_group "$group" "$cmd"
                ;;
            3)
                read -rp "服务器名称: " host
                declare -A info
                get_server_info info "$host"
                for key in "${!info[@]}"; do
                    echo "$key: ${info[$key]}"
                done
                ;;
            0) exit 0 ;;
            *) echo "无效选择" ;;
        esac
    done
}

main
```

### 场景 2：日志状态码统计

```bash
#!/bin/bash
#============================================================
# Nginx 日志状态码统计脚本
# 用法: ./log_stats.sh [日志文件]
#============================================================

set -euo pipefail

LOG_FILE="${1:-/var/log/nginx/access.log}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "错误: 日志文件不存在: $LOG_FILE"
    exit 1
fi

# 使用关联数组统计状态码
declare -A status_count
declare -A status_desc=(
    ["200"]="OK"
    ["301"]="Moved Permanently"
    ["302"]="Found"
    ["304"]="Not Modified"
    ["400"]="Bad Request"
    ["401"]="Unauthorized"
    ["403"]="Forbidden"
    ["404"]="Not Found"
    ["500"]="Internal Server Error"
    ["502"]="Bad Gateway"
    ["503"]="Service Unavailable"
)

# 统计每个状态码
while IFS= read -r line; do
    # 提取状态码（假设标准 Nginx 日志格式）
    status=$(echo "$line" | awk '{print $9}')
    if [[ -n "$status" ]]; then
        ((status_count[$status]++))
    fi
done < "$LOG_FILE"

# 输出统计结果
echo "=========================================="
echo "  Nginx 状态码统计"
echo "  日志文件: $LOG_FILE"
echo "  统计时间: $(date)"
echo "=========================================="
echo ""

# 按状态码排序输出
for status in $(printf '%s\n' "${!status_count[@]}" | sort); do
    count=${status_count[$status]}
    desc="${status_desc[$status]:-Unknown}"

    # 计算百分比
    total=$(awk 'END {print NR}' "$LOG_FILE")
    percent=$(awk "BEGIN {printf \"%.2f\", $count/$total*100}")

    # 根据状态码设置颜色
    case "$status" in
        2*) color="\033[0;32m" ;;  # 绿色
        3*) color="\033[0;34m" ;;  # 蓝色
        4*) color="\033[1;33m" ;;  # 黄色
        5*) color="\033[0;31m" ;;  # 红色
        *)  color="\033[0m" ;;
    esac

    printf "${color}%-6s %-30s %8d (%6.2f%%)\033[0m\n" \
        "$status" "$desc" "$count" "$percent"
done

echo ""
echo "=========================================="
echo "  总请求数: $(wc -l < "$LOG_FILE")"
echo "=========================================="
```

### 场景 3：多服务器并发健康检查

```bash
#!/bin/bash
#============================================================
# 多服务器并发健康检查脚本
# 用法: ./parallel_health_check.sh
#============================================================

set -euo pipefail

# 服务器列表
declare -a servers=(
    "web01:192.168.1.10:80"
    "web02:192.168.1.11:80"
    "db01:192.168.1.20:3306"
    "db02:192.168.1.21:3306"
    "cache01:192.168.1.30:6379"
)

# 检查结果
declare -A check_results
declare -A check_latency

# 并发检查单个服务器
check_server() {
    local server_info="$1"
    IFS=':' read -r name ip port <<< "$server_info"

    local start_time
    start_time=$(date +%s%N)

    # TCP 端口检查
    if nc -z -w 3 "$ip" "$port" 2>/dev/null; then
        local end_time
        end_time=$(date +%s%N)
        local latency=$(( (end_time - start_time) / 1000000 ))

        check_results["$name"]="OK"
        check_latency["$name"]="${latency}ms"
    else
        check_results["$name"]="FAIL"
        check_latency["$name"]="timeout"
    fi
}

# 并发执行所有检查
run_parallel_checks() {
    local pids=()

    echo "开始并发健康检查..."
    echo ""

    # 启动所有检查
    for server_info in "${servers[@]}"; do
        check_server "$server_info" &
        pids+=($!)
    done

    # 等待所有检查完成
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
}

# 输出结果
print_results() {
    echo "=========================================="
    echo "  健康检查结果"
    echo "  检查时间: $(date)"
    echo "=========================================="
    echo ""

    local ok_count=0
    local fail_count=0

    printf "%-12s %-15s %-8s %-10s\n" "服务器" "IP" "状态" "延迟"
    echo "------------------------------------------"

    for server_info in "${servers[@]}"; do
        IFS=':' read -r name ip port <<< "$server_info"

        status="${check_results[$name]:-UNKNOWN}"
        latency="${check_latency[$name]:-N/A}"

        if [[ "$status" == "OK" ]]; then
            printf "\033[0;32m%-12s %-15s %-8s %-10s\033[0m\n" \
                "$name" "$ip" "$status" "$latency"
            ((ok_count++))
        else
            printf "\033[0;31m%-12s %-15s %-8s %-10s\033[0m\n" \
                "$name" "$ip" "$status" "$latency"
            ((fail_count++))
        fi
    done

    echo ""
    echo "=========================================="
    echo "  总计: ${#servers[@]} | 正常: $ok_count | 异常: $fail_count"
    echo "=========================================="
}

# 主程序
main() {
    run_parallel_checks
    print_results

    # 如果有失败的服务器，返回非零退出码
    for result in "${check_results[@]}"; do
        if [[ "$result" != "OK" ]]; then
            exit 1
        fi
    done
}

main
```

### 场景 4：配置文件解析为关联数组

```bash
#!/bin/bash
#============================================================
# 配置文件解析脚本
# 用法: ./config_parser.sh <配置文件>
#============================================================

set -euo pipefail

CONFIG_FILE="${1:-/etc/myapp/config.ini}"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "错误: 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

declare -A config

# 解析 INI 格式配置文件
parse_config() {
    local section="default"

    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue

        # 解析 section
        if [[ "$line" =~ ^\[(.+)\]$ ]]; then
            section="${BASH_REMATCH[1]}"
            continue
        fi

        # 解析 key=value
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"

            # 去除首尾空格
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)

            # 去除引号
            value="${value#\"}"
            value="${value%\"}"
            value="${value#\'}"
            value="${value%\'}"

            # 存储为 section.key 格式
            config["${section}.${key}"]="$value"
        fi
    done < "$CONFIG_FILE"
}

# 获取配置值
get_config() {
    local key="$1"
    local default="${2:-}"

    echo "${config[$key]:-$default}"
}

# 打印所有配置
print_config() {
    echo "配置文件: $CONFIG_FILE"
    echo "配置项数量: ${#config[@]}"
    echo ""

    for key in $(printf '%s\n' "${!config[@]}" | sort); do
        printf "%-30s = %s\n" "$key" "${config[$key]}"
    done
}

# 主程序
parse_config
print_config

# 使用示例
echo ""
echo "数据库配置:"
echo "  主机: $(get_config "database.host" "localhost")"
echo "  端口: $(get_config "database.port" "3306")"
echo "  用户: $(get_config "database.user" "root")"
```

---

## 💻 实战练习

### 练习 1：数组去重

```bash
# 给定包含重复元素的数组，输出一个去重后的新数组
duplicates=("nginx" "mysql" "nginx" "redis" "mysql" "nginx")
# 期望输出: nginx mysql redis
```

**参考答案**：

```bash
duplicates=("nginx" "mysql" "nginx" "redis" "mysql" "nginx")
declare -A seen
unique=()

for item in "${duplicates[@]}"; do
    if [[ -z ${seen[$item]} ]]; then
        seen[$item]=1
        unique+=("$item")
    fi
done

echo "${unique[@]}"  # nginx mysql redis
```

### 练习 2：数组合并与交集

```bash
# 给定两个数组，求并集和交集
a=("nginx" "mysql" "redis")
b=("mysql" "redis" "postgres")
```

**参考答案**：

```bash
a=("nginx" "mysql" "redis")
b=("mysql" "redis" "postgres")

# 交集
declare -A count
for item in "${a[@]}" "${b[@]}"; do
    ((count[$item]++))
done

intersection=()
for item in "${!count[@]}"; do
    [[ ${count[$item]} -ge 2 ]] && intersection+=("$item")
done
echo "交集: ${intersection[*]}"

# 并集（利用关联数组天然去重）
declare -A union_map
for item in "${a[@]}" "${b[@]}"; do
    union_map[$item]=1
done
union=("${!union_map[@]}")
echo "并集: ${union[*]}"
```

### 练习 3：服务器角色分配

```bash
# 使用关联数组实现：给定服务器列表和角色列表，
# 按轮询方式将角色分配给服务器
```

**参考答案**：

```bash
servers=("web01" "web02" "web03" "web04" "web05")
roles=("primary" "secondary" "tertiary")

declare -A server_role

for i in "${!servers[@]}"; do
    role_idx=$((i % ${#roles[@]}))
    server_role[${servers[$i]}]=${roles[$role_idx]}
done

for s in "${servers[@]}"; do
    echo "$s -> ${server_role[$s]}"
done
```

---

## 🎯 面试题精选

### 1. Bash 数组有哪些限制？

**参考答案**：

Bash 数组的主要限制：

1. **不支持真正的多维数组**：需要通过关联数组模拟
2. **没有内置的数组操作函数**：如 push、pop、shift 等，需要手动实现
3. **关联数组需要 Bash 4.0+**：macOS 默认的 Bash 3.2 不支持
4. **数组传递需要特殊处理**：不能直接作为函数参数传递
5. **性能有限**：大量数据处理应该使用 awk/python
6. **没有类型系统**：所有元素都是字符串
7. **索引不连续时的行为**：`unset` 元素不会重排索引

### 2. 关联数组的版本要求是什么？

**参考答案**：

关联数组需要 **Bash 4.0+**（2009 年发布）。检查版本：

```bash
echo ${BASH_VERSINFO[0]}  # 需要 >= 4

# 或者
if ((BASH_VERSINFO[0] >= 4)); then
    echo "支持关联数组"
else
    echo "不支持关联数组"
fi
```

macOS 默认的 Bash 是 3.2 版本，不支持关联数组。需要通过 Homebrew 安装 Bash 5+。

### 3. 如何传递数组给函数？

**参考答案**：

Bash 不能直接传递数组给函数，有以下几种方法：

```bash
# 方法 1：传递所有参数（最常用）
process_array() {
    local arr=("$@")
    echo "长度: ${#arr[@]}"
}

my_arr=("a" "b" "c")
process_array "${my_arr[@]}"

# 方法 2：通过 nameref（Bash 4.3+，推荐）
process_array_v2() {
    local -n ref=$1
    echo "长度: ${#ref[@]}"
}

my_arr=("a" "b" "c")
process_array_v2 my_arr

# 方法 3：通过全局变量
declare -a GLOBAL_ARR=()
fill_array() {
    GLOBAL_ARR=("x" "y" "z")
}
fill_array
echo "${GLOBAL_ARR[@]}"
```

### 4. `${arr[@]}` 和 `${arr[*]}` 有什么区别？

**参考答案**：

在双引号中：
- `"${arr[@]}"`：展开为多个独立的词，每个元素保持独立
- `"${arr[*]}"`：展开为单个词，所有元素用 `$IFS` 连接

```bash
arr=("hello world" "foo bar")

# 正确：保持元素独立
for item in "${arr[@]}"; do
    echo "[$item]"
done
# [hello world]
# [foo bar]

# 错误：丢失元素边界
for item in "${arr[*]}"; do
    echo "[$item]"
done
# [hello world foo bar]
```

### 5. 如何检查关联数组中是否存在某个键？

**参考答案**：

```bash
declare -A map=(["key1"]="value1" ["key2"]="value2")

# 方法 1：使用 -v 测试（Bash 4.2+）
if [[ -v map["key1"] ]]; then
    echo "key1 存在"
fi

# 方法 2：检查值是否非空
if [[ -n "${map[key1]+x}" ]]; then
    echo "key1 存在"
fi

# 方法 3：遍历键
key_to_find="key1"
for key in "${!map[@]}"; do
    if [[ "$key" == "$key_to_find" ]]; then
        echo "找到 $key"
        break
    fi
done
```

### 6. mapfile 和 while read 有什么区别？

**参考答案**：

| 特性 | mapfile | while read |
|------|---------|------------|
| Bash 版本 | 4.0+ | 所有版本 |
| 性能 | 更快（减少循环） | 较慢（逐行处理） |
| 内存 | 一次性加载 | 逐行处理 |
| 语法 | 简洁 | 灵活 |

```bash
# mapfile 方式
mapfile -t lines < /etc/passwd

# while read 方式
declare -a lines
while IFS= read -r line; do
    lines+=("$line")
done < /etc/passwd
```

### 7. 如何在 Bash 中模拟多维数组？

**参考答案**：

```bash
# 使用关联数组模拟二维数组
declare -A matrix

# 设置值
matrix["0,0"]="a"
matrix["0,1"]="b"
matrix["1,0"]="c"
matrix["1,1"]="d"

# 遍历
for i in 0 1; do
    for j in 0 1; do
        echo -n "${matrix[$i,$j]} "
    done
    echo
done

# 使用分隔符（更灵活）
declare -A arr
arr["web,0"]="web01"
arr["web,1"]="web02"
arr["db,0"]="db01"

# 获取某个组的所有元素
get_group() {
    local group="$1"
    local result=()
    for key in "${!arr[@]}"; do
        if [[ "$key" == "$group,"* ]]; then
            result+=("${arr[$key]}")
        fi
    done
    echo "${result[@]}"
}
```

---

## 📚 深入阅读

### 官方文档
- [Bash Manual - Arrays](https://www.gnu.org/software/bash/manual/bash.html#Arrays)
- [Bash 4.0 Release Notes](https://tiswww.case.edu/php/chet/bash/NEWS)

### 推荐书籍
- 《Bash Cookbook》- Carl Albing, JP Vossen
- 《Shell Scripting: Expert Recipes for Linux, Bash, and More》- Steve Parker

### 在线资源
- [Advanced Bash-Scripting Guide - Arrays](https://tldp.org/LDP/abs/htm/arrays.html)
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能够解释索引数组和关联数组的区别
- [ ] 理解 `${arr[@]}` 和 `${arr[*]}` 的区别
- [ ] 知道关联数组的版本要求（Bash 4.0+）
- [ ] 理解数组切片语法
- [ ] 知道 mapfile 命令的用法

### 实操检查点
- [ ] 能够声明和初始化索引数组
- [ ] 能够声明和使用关联数组
- [ ] 能够遍历数组（多种方式）
- [ ] 能够实现数组去重、合并、交集
- [ ] 能够传递数组给函数
- [ ] 能够使用 mapfile 填充数组
- [ ] 能够在 SRE 脚本中使用数组

---

> 📝 **学习笔记**
>
> 记录你在学习过程中的心得和疑问：
>
> 1. ________________________________________________
> 2. ________________________________________________
> 3. ________________________________________________
