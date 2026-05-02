# Day 16: Shell 条件判断 — if/elif/else 与 test/[ 运算符

> 📅 日期：2026-04-26
> 📖 学习主题：Shell 条件判断 — if/elif/else 与 test/[ 运算符
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 16 的学习后，你应该掌握：
- 理解 if/elif/else 的语法和执行流程
- 理解 `[ ]`、`[[ ]]`、`test` 三者的区别
- 掌握文件测试、字符串测试、数值比较的各种运算符
- 掌握逻辑与（&&）、逻辑或（||）、逻辑非（!）的组合
- 能编写带条件判断的实用脚本

---

## 📖 详细知识点

### 1. if/elif/else 基本语法

```bash
# 基本结构
if 条件; then
    # 条件为真时执行
elif 条件2; then
    # 条件2为真时执行
else
    # 以上都不满足时执行
fi
```

**关键理解：if 检查的是命令的退出码**
```bash
# if 的本质：
# if 后面的"条件"实际上是一条命令
# 命令退出码为 0 → 条件为真
# 命令退出码非 0 → 条件为假

# 以下写法完全等价：
if [ -f /etc/passwd ]; then
    echo "存在"
fi

if test -f /etc/passwd; then
    echo "存在"
fi
```

### 2. 三种条件测试方式

| 方式 | 类型 | 说明 |
|------|------|------|
| `[ expression ]` | 内置命令 | POSIX 标准，兼容性好 |
| `[[ expression ]]` | Shell 关键字 | Bash 扩展，功能更强 |
| `test expression` | 内置命令 | 等价于 `[ ]`，但不用括号 |

**关键区别：**

```bash
# [ ] 是命令，[[ ]] 是语法
# [ 是一个真实存在的可执行文件：
which [
# /usr/bin/[
# 所以 [ ] 需要严格的空格：
# [  -f file  ]  ← 错误！多出的空格导致参数解析错误
# [ -f file ]   ← 正确

# [[ ]] 的优势：
name=""

# 1. [[ ]] 中空字符串不需要引号
if [[ -z $name ]]; then    # ✅ 不会报错
    echo "空"
fi
if [ -z $name ]; then      # ⚠️ 在某些情况下可能出问题
    echo "空"
fi

# 2. [[ ]] 支持正则和逻辑运算符
if [[ $name =~ ^[a-z]+$ ]]; then    # ✅ 正则匹配
    echo "全是小写字母"
fi
if [[ $a == foo && $b == bar ]]; then    # ✅ 用 && 组合
    echo "都匹配"
fi
# [ ] 中要用 -a/-o，或者多个 [ ]：
# [ "$a" = foo ] && [ "$b" = bar ]

# 3. [[ ]] 中 < > 是字符串比较，不是重定向
if [[ "abc" < "def" ]]; then    # ✅ 字符串比较
    echo "abc 小于 def"
fi
# 在 [ ] 中 < > 会被当作重定向：
# [ "abc" \< "def" ]    ← 需要转义

# 推荐：写 Bash 脚本时优先使用 [[ ]]
```

### 3. 文件测试运算符

| 运算符 | 含义 | 示例 |
|--------|------|------|
| `-e` | 文件或目录存在 | `[ -e /etc/passwd ]` |
| `-f` | 是普通文件 | `[ -f /etc/passwd ]` |
| `-d` | 是目录 | `[ -d /tmp ]` |
| `-L` | 是符号链接 | `[ -L /bin ]` |
| `-s` | 文件存在且不为空 | `[ -s /var/log/syslog ]` |
| `-r` | 可读 | `[ -r /etc/passwd ]` |
| `-w` | 可写 | `[ -w /tmp ]` |
| `-x` | 可执行 | `[ -x /usr/bin/python3 ]` |
| `-O` | 当前用户是所有者 | `[ -O /etc/passwd ]` |
| `-G` | 当前用户组是所有者 | `[ -G /etc/group ]` |

```bash
# 实用示例
if [[ -f /etc/nginx/nginx.conf ]]; then
    echo "Nginx 配置文件存在"
else
    echo "Nginx 未安装或未配置"
fi

if [[ -d /var/www ]]; then
    echo "/var/www 是一个目录"
fi

# 检查文件是否可写
if [[ ! -w /etc/hosts ]]; then
    echo "需要 root 权限"
    exit 1
fi

# 检查目录是否存在，不存在则创建
if [[ ! -d /var/log/myapp ]]; then
    mkdir -p /var/log/myapp
    echo "已创建日志目录"
fi
```

### 4. 字符串测试

| 运算符 | 含义 | 示例 |
|--------|------|------|
| `-z STRING` | 字符串为空 | `[ -z "$name" ]` |
| `-n STRING` | 字符串非空 | `[ -n "$name" ]` |
| `=` 或 `==` | 相等 | `[ "$a" = "$b" ]` |
| `!=` | 不相等 | `[ "$a" != "$b" ]` |
| `<` | 字典序小于 | `[[ "$a" < "$b" ]]` |
| `>` | 字典序大于 | `[[ "$a" > "$b" ]]` |

```bash
name=""

if [[ -z $name ]]; then
    echo "name 为空"
fi

if [[ -n $name ]]; then
    echo "name 不为空"
fi

# 字符串比较
password="secret123"
if [[ "$password" != "changeme" ]]; then
    echo "密码已修改"
fi

# ⚠️ 重要：字符串变量一定要加引号！
str="hello world"
[ $str = "hello world" ]    # ❌ 错误！$str 展开后变成 [ hello world = "hello world" ]
[ "$str" = "hello world" ]  # ✅ 正确
```

### 5. 数值比较

| 运算符 | 含义 | 示例 |
|--------|------|------|
| `-eq` | 等于 | `[ $a -eq 10 ]` |
| `-ne` | 不等于 | `[ $a -ne 10 ]` |
| `-gt` | 大于 | `[ $a -gt 10 ]` |
| `-ge` | 大于等于 | `[ $a -ge 10 ]` |
| `-lt` | 小于 | `[ $a -lt 10 ]` |
| `-le` | 小于等于 | `[ $a -le 10 ]` |

```bash
disk_usage=85

if [[ $disk_usage -gt 90 ]]; then
    echo "🔴 磁盘使用率超过 90%！"
elif [[ $disk_usage -gt 75 ]]; then
    echo "🟡 磁盘使用率超过 75%，需要注意"
else
    echo "🟢 磁盘使用率正常"
fi

# 数学比较（用 (( ))，这是算术表达式，不是条件测试）
age=25
if (( age >= 18 )); then
    echo "已成年"
fi

# (( )) 中的运算符：
# >  >=  <  <=  ==  !=  &&  ||
# 这些是 C 风格的运算符，不是文件/字符串测试

cpu_count=4
load_avg=3.5
if (( $(echo "$load_avg > $cpu_count" | bc -l) )); then
    echo "负载过高"
fi
```

### 6. 逻辑组合

```bash
# 逻辑与（&&）— 两个条件都为真
if [[ -f /etc/nginx/nginx.conf ]] && [[ -x /usr/sbin/nginx ]]; then
    echo "Nginx 已安装且可执行"
fi

# 简写（[[ ]] 内部）
if [[ -f /etc/nginx/nginx.conf && -x /usr/sbin/nginx ]]; then
    echo "同上"
fi

# 逻辑或（||）— 任一条件为真
if [[ ! -f /etc/nginx/nginx.conf ]] || [[ ! -f /etc/apache2/apache2.conf ]]; then
    echo "没有安装 Nginx 也没有安装 Apache"
fi

# 逻辑非（!）— 取反
if [[ ! -d /var/log/nginx ]]; then
    echo "Nginx 日志目录不存在"
fi

# 组合使用
if [[ -f "$config" ]] && [[ -r "$config" ]] && [[ -s "$config" ]]; then
    echo "配置文件存在、可读、且不为空"
fi
```

### 7. case 语句简介（详细见 Day 19）

```bash
# case 是多路分支的更优雅写法
os=$(uname)
case $os in
    Linux)
        echo "Linux 系统"
        ;;
    Darwin)
        echo "macOS 系统"
        ;;
    *)
        echo "未知系统: $os"
        ;;
esac
```

---

## 🏗️ 实战

### 实战 1：服务健康检查脚本

```bash
#!/usr/bin/env bash
# health_check.sh — 检查服务是否正常

set -euo pipefail

check_service() {
    local service=$1

    # 检查服务是否存在
    if ! systemctl is-active --quiet "$service"; then
        echo "❌ $service 未运行"
        return 1
    fi

    # 检查是否开机自启
    if ! systemctl is-enabled --quiet "$service"; then
        echo "⚠️  $service 未设置开机自启"
    fi

    echo "✅ $service 运行正常"
    return 0
}

# 检查列表
services=("sshd" "nginx" "mysql")

failed=0
for svc in "${services[@]}"; do
    if ! check_service "$svc"; then
        ((failed++))
    fi
done

if (( failed > 0 )); then
    echo ""
    echo "有 $failed 个服务异常"
    exit 1
else
    echo ""
    echo "所有服务正常"
    exit 0
fi
```

### 实战 2：部署前置检查

```bash
#!/usr/bin/env bash
# pre_deploy_check.sh — 部署前环境检查

errors=0

# 1. 检查是否在正确的分支
current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" ]] && [[ "$current_branch" != "production" ]]; then
    echo "❌ 当前分支 $current_branch 不是 main 或 production"
    ((errors++))
fi

# 2. 检查磁盘空间
disk_pct=$(df / --output=pcent | tail -1 | tr -d ' %')
if [[ $disk_pct -gt 85 ]]; then
    echo "❌ 磁盘使用率 ${disk_pct}%，超过 85% 阈值"
    ((errors++))
fi

# 3. 检查配置文件
if [[ ! -f config/app.yaml ]]; then
    echo "❌ 配置文件 config/app.yaml 不存在"
    ((errors++))
fi

# 4. 检查环境变量
if [[ -z "${DB_PASSWORD:-}" ]]; then
    echo "❌ 环境变量 DB_PASSWORD 未设置"
    ((errors++))
fi

# 5. 检查端口是否被占用
if ss -tlnp | grep -q ':8080 '; then
    echo "⚠️  8080 端口已被占用"
fi

# 总结
if (( errors > 0 )); then
    echo ""
    echo "发现 $errors 个错误，部署中止"
    exit 1
else
    echo ""
    echo "✅ 所有检查通过，可以部署"
    exit 0
fi
```

---

## 🧪 练习题

### 练习 1：判断文件类型

编写脚本，接受一个路径参数，判断它是文件、目录、链接还是不存在。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
path="${1:?用法: $0 <路径>}"

if [[ ! -e $path ]]; then
    echo "$path 不存在"
elif [[ -L $path ]]; then
    echo "$path 是符号链接"
    echo "指向: $(readlink -f $path)"
elif [[ -f $path ]]; then
    echo "$path 是普通文件"
    echo "大小: $(du -h $path | cut -f1)"
elif [[ -d $path ]]; then
    echo "$path 是目录"
    echo "内容数: $(ls -A $path | wc -l)"
else
    echo "$path 是其他类型"
fi
```
</details>

---

## 📚 扩展阅读

- `man test` — 所有测试运算符的手册
- [Bash 条件判断完整指南](https://tldp.org/LDP/abs/html/testconstructs.html)
