# Day 20: Bash 数组操作 — 索引数组、关联数组与数组遍历

> 📅 日期：2026-04-25
> 📖 学习主题：Bash 数组操作 — 索引数组、关联数组与数组遍历
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 20 的学习后，你应该掌握：
- 理解 Bash 索引数组和关联数组的底层实现机制
- 熟练声明、赋值、读取、删除数组元素
- 掌握多种数组遍历方式及其性能差异
- 能够在 SRE 运维脚本中灵活运用数组处理配置、主机列表、监控指标等
- 理解数组在 Bash 4.0+ 版本中引入关联数组的历史背景

---

## 📖 底层原理详解

### 1. Bash 数组的内部实现

Bash 的数组并非真正的数据结构，而是**基于变量名后缀的语法糖**。

当你声明 `arr[0]="hello"` 时，Bash 内部创建了一个名为 `arr` 的复合变量，其元素通过索引键（整数或字符串）进行哈希映射。

**索引数组（Indexed Array）**：使用非负整数作为索引，底层是连续的哈希表结构。索引不必连续，Bash 不会为缺失的索引分配空间。

**关联数组（Associative Array）**：Bash 4.0（2009 年发布）引入的新特性，使用字符串作为键，底层是一个哈希表（hash table），键值对的查找时间复杂度为 O(1)。

**版本检查**：
```bash
$ bash --version
GNU bash, version 5.1.16(1)-release

# 检查是否支持关联数组（Bash 4.0+）
$ echo ${BASH_VERSINFO[0]}
5  # 5 >= 4，支持关联数组
```

### 2. 索引数组基础操作

#### 2.1 声明与赋值

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
```

**重要细节**：Bash 数组索引可以不连续。如果你给 `arr[10]="value"` 赋值而 `arr[1]` 到 `arr[9]` 未定义，Bash 只存储这一个元素，不会分配中间空间。

#### 2.2 读取元素

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
- `"${arr[@]}"` 展开为多个独立的词（word），每个元素保持独立
- `"${arr[*]}"` 展开为单个词，所有元素用 `$IFS`（默认空格）连接

在 SRE 脚本中，**永远优先使用 `"${arr[@]}"`**，这是避免空格导致 bug 的关键实践。

#### 2.3 数组长度与索引

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
```

#### 2.4 元素操作

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

### 3. 关联数组（Bash 4.0+）

#### 3.1 声明与赋值

```bash
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

#### 3.2 读取与遍历

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
if [[ -z ${host_info["unknown"]} ]]; then
    echo "unknown 键不存在或值为空"
fi
```

**重要**：关联数组的遍历顺序**不保证与插入顺序一致**。这是哈希表的固有特性。如果需要有序遍历，可以先对键排序：

```bash
for host in $(echo "${!host_info[@]}" | tr ' ' '\n' | sort); do
    echo "$host -> ${host_info[$host]}"
done
```

### 4. 数组遍历方式对比

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

---

## 💻 SRE 实战场景

### 场景 1：批量主机管理

```bash
#!/bin/bash
# batch_host_manager.sh — 使用数组管理服务器列表

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

deploy_to_group "web" "systemctl reload nginx"

# 检查所有服务器状态
check_all() {
    local failed_hosts=()

    for host in "${all_servers[@]}"; do
        if ! ping -c 1 -W 2 "$host" &>/dev/null; then
            failed_hosts+=("$host")
        fi
    done

    if [[ ${#failed_hosts[@]} -gt 0 ]]; then
        echo "⚠️  以下主机不可达: ${failed_hosts[*]}"
        return 1
    else
        echo "✅ 所有 ${#all_servers[@]} 台主机在线"
    fi
}

check_all
```

### 场景 2：配置文件解析为数组

```bash
#!/bin/bash
# config_parser.sh — 将 .env 配置文件解析为关联数组

declare -A app_config

# 解析配置文件
while IFS='=' read -r key value; do
    # 跳过注释和空行
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    # 去除引号
    value="${value%\"}"
    value="${value#\"}"
    app_config["$key"]="$value"
done < /etc/myapp/app.conf

# 使用配置
DB_HOST="${app_config[DB_HOST]:-localhost}"
DB_PORT="${app_config[DB_PORT]:-5432}"

echo "连接数据库: $DB_HOST:$DB_PORT"

# 打印所有配置项（按字母排序）
for key in $(echo "${!app_config[@]}" | tr ' ' '\n' | sort); do
    echo "  $key = ${app_config[$key]}"
done
```

### 场景 3：监控指标采集与告警

```bash
#!/bin/bash
# array_monitor.sh — 使用数组进行多指标采集告警

# 阈值配置（关联数组）
declare -A thresholds=(
    ["cpu_warn"]="80"
    ["cpu_crit"]="95"
    ["mem_warn"]="70"
    ["mem_crit"]="90"
    ["disk_warn"]="80"
    ["disk_crit"]="95"
)

# 告警级别（索引数组）
alerts=()

# 采集 CPU
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print int($2)}')
if (( cpu_usage >= thresholds["cpu_crit"] )); then
    alerts+=("CRITICAL: CPU ${cpu_usage}% >= ${thresholds[cpu_crit]}%")
elif (( cpu_usage >= thresholds["cpu_warn"] )); then
    alerts+=("WARNING: CPU ${cpu_usage}% >= ${thresholds[cpu_warn]}%")
fi

# 采集内存
mem_usage=$(free | awk '/Mem:/ {printf "%d", $3/$2*100}')
if (( mem_usage >= thresholds["mem_crit"] )); then
    alerts+=("CRITICAL: Memory ${mem_usage}% >= ${thresholds[mem_crit]}%")
elif (( mem_usage >= thresholds["mem_warn"] ]]; then
    alerts+=("WARNING: Memory ${mem_usage}% >= ${thresholds[mem_warn]}%")
fi

# 采集磁盘
while read -r line; do
    usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
    mount=$(echo "$line" | awk '{print $6}')
    if (( usage >= thresholds["disk_crit"] )); then
        alerts+=("CRITICAL: Disk $mount at ${usage}%")
    elif (( usage >= thresholds["disk_warn"] )); then
        alerts+=("WARNING: Disk $mount at ${usage}%")
    fi
done < <(df -h --total 2>/dev/null | grep '^/dev/')

# 输出告警
if [[ ${#alerts[@]} -gt 0 ]]; then
    echo "🚨 $(date '+%Y-%m-%d %H:%M:%S') — ${#alerts[@]} 条告警"
    for alert in "${alerts[@]}"; do
        echo "  - $alert"
    done
    # 这里可以接入 webhook / 邮件 / PagerDuty
else
    echo "✅ 所有指标正常"
fi
```

---

## 🧪 练习题

### 练习 1：数组去重
```bash
# 给定包含重复元素的数组，输出一个去重后的新数组
duplicates=("nginx" "mysql" "nginx" "redis" "mysql" "nginx")
# 期望输出: nginx mysql redis
```

<details>
<summary>答案</summary>

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
</details>

### 练习 2：数组合并与交集
```bash
# 给定两个数组，求并集和交集
a=("nginx" "mysql" "redis")
b=("mysql" "redis" "postgres")
```

<details>
<summary>答案</summary>

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
</details>

### 练习 3：服务器角色分配
```bash
# 使用关联数组实现：给定服务器列表和角色列表，
# 按轮询方式将角色分配给服务器
```

<details>
<summary>答案</summary>

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
</details>

---

## 📚 扩展阅读

- [Bash Reference Manual — Arrays](https://www.gnu.org/software/bash/manual/bash.html#Arrays) — GNU 官方数组文档
- [Bash 4.0 Release Notes](https://tiswww.case.edu/php/chet/bash/NEWS) — 关联数组引入的原始说明
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) — Google 的 Bash 编码规范
- [Advanced Bash-Scripting Guide — Arrays](https://tldp.org/LDP/abs/htm/arrays.html) — 经典教程
- 对比学习：Python 的 `list`/`dict` 与 Bash 数组的异同

### 关键要点回顾

| 概念 | 语法 | 说明 |
|------|------|------|
| 索引数组声明 | `declare -a arr` | 可省略，赋值时自动创建 |
| 关联数组声明 | `declare -A arr` | 必须先声明再使用 |
| 元素个数 | `${#arr[@]}` | 不连续的索引不会计算在内 |
| 所有索引 | `${!arr[@]}` | 索引数组返回数字，关联数组返回字符串键 |
| 追加元素 | `arr+=("new")` | 两种方式都支持 |
| 删除元素 | `unset arr[idx]` | 不会重排索引 |
| 切片 | `${arr[@]:start:len}` | 类似 Python 切片 |
| 安全遍历 | `"${arr[@]}"` | 永远加双引号，防止空格分词 |

---

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
