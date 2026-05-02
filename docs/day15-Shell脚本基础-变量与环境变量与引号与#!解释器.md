# Day 15: Shell 脚本基础 — 变量、环境变量、引号、#!解释器

> 📅 日期：2026-04-26
> 📖 学习主题：Shell 脚本基础 — 变量与环境变量、引号、#!解释器
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 15 的学习后，你应该掌握：
- 理解 Shell 脚本的本质：解释执行的命令序列
- 掌握变量的声明、引用、删除和作用域
- 理解单引号、双引号、反引号/$() 的区别
- 理解环境变量的作用范围和 export 的意义
- 能编写第一个可用的 Shell 脚本
- 理解 Shebang（#!）的作用和常见解释器选择

---

## 📖 详细知识点

### 1. Shell 脚本的本质

Shell 是一个**命令行解释器**。你在终端输入的每一条命令，Shell 都会解析并执行。

```
你输入: ls -la /tmp
Shell:
  1. 解析命令 → 命令名=ls, 参数=["-la", "/tmp"]
  2. 查找 ls 的路径 → /usr/bin/ls（通过 PATH 环境变量）
  3. fork 一个新进程
  4. exec 执行 /usr/bin/ls
  5. 等待进程结束
  6. 返回退出码（0=成功，非0=失败）
```

Shell 脚本就是把多条命令写到一个文件里，按顺序执行：

```bash
#!/bin/bash
# script.sh — 一个简单的 Shell 脚本
echo "开始备份..."
tar czf /backup/home.tar.gz /home
echo "备份完成"
```

### 2. Shebang（#!）

脚本第一行的 `#!` 告诉系统**用什么解释器**来执行这个文件：

```bash
#!/bin/bash          # 使用 Bash
#!/bin/sh            # 使用系统默认 sh（Ubuntu 上是 dash，不是 bash！）
#!/usr/bin/env bash  # 通过 env 查找 bash（推荐，跨平台兼容性好）
#!/usr/bin/python3   # 使用 Python 3
#!/usr/bin/env node  # 使用 Node.js
```

**为什么推荐 `#!/usr/bin/env bash`？**
```
/bin/bash  — bash 在固定路径，但不同系统路径可能不同（FreeBSD 在 /usr/local/bin/bash）
/usr/bin/env bash — env 会在 PATH 中查找 bash，找到第一个匹配的就用
                    这在虚拟环境（conda, nvm）中特别有用
```

**赋予执行权限：**
```bash
chmod +x script.sh    # 添加执行权限
./script.sh           # 直接执行（Shebang 会指定解释器）

# 或者不赋予权限也能执行：
bash script.sh        # 显式指定解释器
sh script.sh
```

### 3. 变量

#### 3.1 基本语法

```bash
# 声明变量（注意：等号两边不能有空格！）
name="SRE学习"
count=100
message='Hello World'

# 错误写法（会报错）：
# name = SRE     ← 空格！Shell 会认为 name 是命令，= 和 SRE 是参数
# name=hello world ← world 会被当作另一个命令

# 引用变量（用 $）
echo $name
echo "${name}"     # 推荐：大括号明确变量边界

# 变量名规则：字母、数字、下划线，不能以数字开头
my_var=1       # ✅
_var=2         # ✅
VAR123=3       # ✅
1var=4         # ❌ 错误
my-var=5       # ❌ 错误（- 会被当作减号）
```

#### 3.2 变量类型

```bash
# 字符串
greeting="Hello"
echo "${greeting} World"    # Hello World

# 数字（Shell 中的变量都是字符串，运算需要特殊语法）
a=10
b=3

# 算术运算
echo $((a + b))     # 13
echo $((a - b))     # 7
echo $((a * b))     # 30
echo $((a / b))     # 3（整数除法）
echo $((a % b))     # 1（取余）

# 浮点数运算（Shell 本身不支持，用 bc）
echo "scale=2; 10 / 3" | bc    # 3.33

# 数组
fruits=("apple" "banana" "cherry")
echo "${fruits[0]}"     # apple
echo "${fruits[@]}"     # 所有元素：apple banana cherry
echo "${#fruits[@]}"    # 元素个数：3
echo "${#fruits[1]}"    # 第二个元素的长度：6

# 关联数组（Bash 4.0+）
declare -A ages
ages["Alice"]=30
ages["Bob"]=25
echo "${ages[Alice]}"    # 30
```

#### 3.3 变量的高级用法

```bash
# 默认值（如果变量未设置，使用默认值）
echo "${name:-默认用户}"     # 如果 name 为空，输出"默认用户"

# 赋值默认值（变量未设置时赋值）
echo "${count:=50}"          # 如果 count 为空，设为 50

# 错误提示（变量未设置时报错）
echo "${name:?必须设置 name 变量}"

# 截取子串
str="Hello World"
echo "${str:0:5}"      # Hello（从0开始，取5个字符）
echo "${str:6}"        # World（从第6个字符到结尾）

# 字符串替换
filename="report.txt"
echo "${filename/.txt/.md}"    # report.md

# 字符串长度
echo "${#str}"         # 11

# 删除变量
unset name

# 只读变量（不可修改）
readonly PI=3.14159
# PI=3.14    ← 会报错
```

### 4. 引号的区别

这是 Shell 初学者最容易混淆的地方：

| 引号类型 | 变量展开 | 命令替换 | 转义字符 | 示例 |
|---------|---------|---------|---------|------|
| **双引号 "..."** | ✅ | ✅ | ✅（部分） | `echo "$HOME"` |
| **单引号 '...'** | ❌ | ❌ | ❌ | `echo '$HOME'` |
| **反引号 \`...\`** | ✅ | ✅ | ✅ | `` echo `date` `` |
| **$()** | ✅ | ✅ | ✅ | `echo $(date)` |

```bash
name="World"

# 双引号：变量会被展开
echo "Hello $name"        # 输出: Hello World

# 单引号：原样输出，不展开
echo 'Hello $name'        # 输出: Hello $name

# 反引号和 $()：执行命令并获取输出
echo "当前时间: `date +%H:%M`"    # 输出: 当前时间: 14:30
echo "当前时间: $(date +%H:%M)"   # 输出: 当前时间: 14:30

# 推荐用 $() 替代反引号：
# 1. $() 可以嵌套：$(echo $(whoami))
# 2. 反引号嵌套需要转义，容易出错
# 3. $() 在视觉上更清晰

# 双引号中的转义
echo "路径: $HOME\n用户名: $USER"    # \n 不会被当作换行（echo 默认不解析）
echo -e "路径: $HOME\n用户名: $USER"  # -e 启用转义

# 单引号中的转义无效
echo '路径: $HOME\n用户名: $USER'    # 原样输出：路径: $HOME\n用户名: $USER

# 引号中的引号
echo "他说：'你好'"          # 他说：'你好'
echo '他说："你好"'          # 他说："你好"
echo "路径是 \"$HOME\""      # 路径是 "/root"（用反斜杠转义双引号）
```

### 5. 环境变量

#### 5.1 什么是环境变量

环境变量是影响 Shell 和程序行为的**全局变量**。它们不是脚本内部的变量，而是操作系统层面的配置。

```bash
# 查看当前所有环境变量
env
# 或
printenv

# 查看特定环境变量
echo $PATH
echo $HOME
echo $USER
printenv LANG
```

#### 5.2 常用环境变量

| 变量 | 含义 | 示例值 |
|------|------|--------|
| PATH | 可执行文件搜索路径 | `/usr/local/bin:/usr/bin:/bin` |
| HOME | 用户家目录 | `/home/sreuser` |
| USER | 当前用户名 | `sreuser` |
| SHELL | 默认 Shell | `/bin/bash` |
| LANG | 语言和编码 | `en_US.UTF-8` |
| TERM | 终端类型 | `xterm-256color` |
| PWD | 当前工作目录 | `/var/log` |
| HOSTNAME | 主机名 | `my-server` |

#### 5.3 局部变量 vs 环境变量

```bash
# 局部变量（只在当前 Shell 中可见）
my_var="local"
bash              # 启动子 Shell
echo $my_var      # 空！子 Shell 看不到父 Shell 的局部变量
exit

# 环境变量（对子进程也可见）
export my_var="global"
bash
echo $my_var      # global！子 Shell 能看到
exit
```

**export 的本质：**
```
export 将变量标记为"导出"，子进程继承这个变量。

进程环境变量传递图：

  父进程 (PID 100)
  │ export APP_ENV=production
  │
  └──→ 子进程 (PID 200)  ← 继承 APP_ENV=production
       │
       └──→ 孙进程 (PID 300)  ← 也继承 APP_ENV=production

注意：子进程无法修改父进程的环境变量！
      子进程对 export 的修改只影响它自己和它的子进程。
```

#### 5.4 设置环境变量的方式

```bash
# 方式 1：当前会话（退出后消失）
export APP_ENV=production

# 方式 2：用户级别（写入 ~/.bashrc 或 ~/.bash_profile）
echo 'export APP_ENV=production' >> ~/.bashrc
source ~/.bashrc    # 立即生效

# 方式 3：系统级别（所有用户，写入 /etc/environment 或 /etc/profile.d/）
echo 'APP_ENV=production' | sudo tee -a /etc/environment
# 或
echo 'export APP_ENV=production' | sudo tee /etc/profile.d/app_env.sh

# 方式 4：单条命令的环境变量（不影响当前 Shell）
APP_ENV=production ./myapp
# APP_ENV 只在 ./myapp 的执行期间有效
# 命令执行完后，当前 Shell 没有 APP_ENV 变量
```

#### 5.5 PATH 环境变量

```bash
# PATH 是命令搜索路径，用 : 分隔
echo $PATH
# 输出：/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# 当你输入 ls 时，Shell 按顺序在 PATH 的每个目录中查找 ls：
# /usr/local/bin/ls → 找到！执行

# 添加自定义路径到 PATH
export PATH="$HOME/bin:$PATH"    # 添加到最前面（优先查找）
export PATH="$PATH:/opt/custom/bin"  # 添加到末尾

# 在 ~/.bashrc 中永久生效
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc

# 查找命令的完整路径
which ls          # /usr/bin/ls
which python3     # /usr/bin/python3
which nginx       # /usr/sbin/nginx

# 查看命令的详细信息
type ls           # ls is aliased to `ls --color=auto`
type -a ls        # 显示所有匹配的 ls（别名、函数、可执行文件）
```

### 6. 特殊变量

Shell 提供了一些内置的特殊变量：

| 变量 | 含义 | 示例 |
|------|------|------|
| `$0` | 脚本名 | `./deploy.sh` |
| `$1`, `$2`, ... | 位置参数（命令行参数） | `./script.sh arg1 arg2` → $1=arg1, $2=arg2 |
| `$#` | 参数个数 | `./script.sh a b` → $#=2 |
| `$*` | 所有参数（一个字符串） | `"a b c"` |
| `$@` | 所有参数（独立字符串） | `"a" "b" "c"` |
| `$?` | 上一个命令的退出码 | 0=成功，非0=失败 |
| `$$` | 当前进程 PID | |
| `$!` | 最后一个后台进程的 PID | |
| `$_` | 上一个命令的最后一个参数 | |

```bash
#!/bin/bash
# args_demo.sh

echo "脚本名: $0"
echo "参数个数: $#"
echo "第一个参数: $1"
echo "第二个参数: $2"
echo "所有参数(*): $*"
echo "所有参数(@): $@"
echo "我的 PID: $$"

# 运行上一个命令
ls /nonexistent 2>/dev/null
echo "上一个命令的退出码: $?"    # 输出: 2（ls 失败）

ls /
echo "上一个命令的退出码: $?"    # 输出: 0（ls 成功）
```

### 7. 退出码（Exit Code）

每个命令执行完毕后都会返回一个退出码（0-255）：

```bash
# 0 = 成功
ls /
echo $?    # 0

# 非 0 = 失败
ls /nonexistent
echo $?    # 2

# 常用退出码
# 0  — 成功
# 1  — 通用错误
# 2  — 用法错误（参数不对）
# 126 — 文件不可执行
# 127 — 命令未找到
# 130 — 被 Ctrl+C 中断（128+2）
# 137 — 被 SIGKILL 杀死（128+9）
# 139 — 段错误（128+11）
# 128+N — 被信号 N 终止

# 自定义退出码
#!/bin/bash
if [ ! -f "/etc/config.yaml" ]; then
    echo "错误：配置文件不存在"
    exit 1
fi
echo "配置加载成功"
exit 0
```

---

## 🏗️ 实战

### 实战 1：系统信息收集脚本

```bash
#!/usr/bin/env bash
# sysinfo.sh — 收集系统信息

set -euo pipefail

# 变量
REPORT_DIR="/tmp/sysinfo"
DATE=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/sysinfo_${DATE}.txt"

# 创建目录
mkdir -p "$REPORT_DIR"

# 收集信息
{
    echo "=== 系统信息报告 ==="
    echo "生成时间: $(date)"
    echo "主机名: $(hostname)"
    echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "内核: $(uname -r)"
    echo ""

    echo "=== CPU ==="
    echo "核心数: $(nproc)"
    echo "型号: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"
    echo "负载: $(cat /proc/loadavg)"
    echo ""

    echo "=== 内存 ==="
    free -h
    echo ""

    echo "=== 磁盘 ==="
    df -h --local
    echo ""

    echo "=== 网络 ==="
    ip -4 addr show | grep inet | grep -v 127.0.0.1
    echo ""

    echo "=== 运行时间 ==="
    uptime
} > "$REPORT_FILE"

echo "报告已保存到: $REPORT_FILE"
```

---

## 🧪 练习题

### 练习 1：引号测试

以下命令的输出分别是什么？
```bash
name="World"
echo 'Hello $name'
echo "Hello $name"
echo "Hello \$name"
echo Hello $name
```

<details>
<summary>答案</summary>

```
Hello $name       ← 单引号，不展开
Hello World       ← 双引号，展开变量
Hello $name       ← 双引号，\$ 转义了 $，输出字面量 $
Hello World       ← 没有引号，$name 被展开
```
</details>

### 练习 2：环境变量传递

解释以下输出为什么不同：
```bash
# 终端 A
MY_VAR=hello
bash
echo $MY_VAR      # 输出：（空）
exit

# 终端 B
export MY_VAR=hello
bash
echo $MY_VAR      # 输出：hello
exit
```

<details>
<summary>答案</summary>

- 终端 A：`MY_VAR=hello` 只是局部变量，子 Shell（`bash`）继承不了
- 终端 B：`export MY_VAR=hello` 将变量导出为环境变量，子 Shell 可以继承
</details>

---

## 📚 扩展阅读

- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)
- [ShellCheck](https://www.shellcheck.net/) — 在线检查 Shell 脚本语法
- [Bash Pitfalls](http://mywiki.wooledge.org/BashPitfalls) — 常见陷阱
