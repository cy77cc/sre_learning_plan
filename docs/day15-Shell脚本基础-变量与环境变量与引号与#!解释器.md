# Day 15: Shell 脚本基础 — 变量、环境变量、引号、#!解释器

> 📅 日期：2026-04-26
> 📖 学习主题：Shell 脚本基础 — 变量与环境变量、引号、#!解释器
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 14（LAMP 环境搭建）

## 🎯 学习目标

完成 Day 15 的学习后，你应该能够：
- 理解 Shell 架构体系（bash、sh、zsh、dash 的区别与适用场景）
- 深入掌握 Shebang（#!）机制及三种常见写法的差异
- 熟练使用变量展开的所有形式（默认值、截取、替换、大小写转换）
- 理解登录 Shell 与非登录 Shell 的配置文件加载顺序
- 掌握引号规则（单引号、双引号、反引号、$()）的精确行为差异
- 能诊断并修复因变量、环境变量、引号使用不当导致的生产故障

---

## 📖 核心知识点

### 1. Shell 架构体系

#### 1.1 什么是 Shell

Shell 是操作系统内核（Kernel）与用户之间的桥梁。它接收用户输入的命令，解析后交给内核执行，再将结果返回给用户。

```
┌─────────────────────────────────────────────────────────────┐
│                        用户空间                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │ 用户输入  │   │ Shell 脚本│   │  应用程序 │               │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│       │              │              │                       │
│       ▼              ▼              ▼                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Shell（命令解释器）                      │   │
│  │  ┌─────────┬─────────┬─────────┬─────────┐          │   │
│  │  │  bash   │   sh    │  zsh    │  dash   │  ...     │   │
│  │  └─────────┴─────────┴─────────┴─────────┘          │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│  ┌────────────────────────▼────────────────────────────┐   │
│  │               系统调用接口（System Call）              │   │
│  │    fork()  exec()  read()  write()  wait()  ...     │   │
│  └────────────────────────┬────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    内核空间（Kernel）                         │
│  ┌────────────────────────▼────────────────────────────┐   │
│  │               进程管理 / 文件系统 / 内存管理           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 主流 Shell 对比

| Shell | 全称 | 默认系统 | 特点 | 适用场景 |
|-------|------|---------|------|---------|
| **bash** | Bourne Again Shell | CentOS/RHEL/Fedora | 功能丰富、数组、关联数组、正则匹配 | 通用脚本、系统管理 |
| **sh** (dash) | POSIX Shell | Ubuntu/Debian (链接到 dash) | 启动快、POSIX 兼容、功能少 | 系统启动脚本、POSIX 兼容脚本 |
| **zsh** | Z Shell | macOS (Catalina+) | 自动补全强大、主题丰富、Oh-My-Zsh | 交互式终端 |
| **dash** | Debian Almquist Shell | Ubuntu/Debian (/bin/sh) | 极速启动、最小化、纯 POSIX | init 脚本、cron 任务 |
| **ksh** | Korn Shell | AIX/Solaris | 历史悠久、企业级 | 银行、电信系统 |
| **fish** | Friendly Interactive Shell | 独立安装 | 用户友好、语法高亮、自动建议 | 交互式终端 |

```bash
# 查看当前使用的 Shell
echo $SHELL          # 默认 Shell（登录时使用的）
echo $0              # 当前正在运行的 Shell

# 查看系统中可用的 Shell
cat /etc/shells

# 查看 bash 版本
bash --version

# 查看 sh 指向哪个 Shell
ls -la /bin/sh
# Ubuntu: /bin/sh -> dash
# CentOS: /bin/sh -> bash
```

#### 1.3 bash 与 sh 的关键差异

```bash
# 以下语法在 bash 中可用，但在 sh (dash) 中会报错：

# 1. 数组
arr=(1 2 3)                    # bash ✅  sh ❌
echo ${arr[0]}

# 2. [[ ]] 双括号条件测试
[[ -f /etc/passwd ]]           # bash ✅  sh ❌

# 3. (( )) 算术运算
((i++))                        # bash ✅  sh ❌

# 4. here string
cat <<< "hello"                # bash ✅  sh ❌

# 5. 进程替换
diff <(ls dir1) <(ls dir2)     # bash ✅  sh ❌

# 6. ${var,,} 大小写转换
name="HELLO"
echo ${name,,}                 # bash ✅  sh ❌ → hello

# 7. 函数定义中的 local 关键字（POSIX 未定义，但 dash 支持）
myfunc() {
    local x=1                  # bash ✅  sh: 非标准但大多数实现支持
}
```

#### 1.4 如何选择 Shell

```
场景判断流程：

需要写脚本？
├── 是 → 需要 bash 特有功能（数组、正则、进程替换）？
│        ├── 是 → #!/bin/bash 或 #!/usr/bin/env bash
│        └── 否 → 需要最大兼容性（跨 Unix 系统）？
│                  ├── 是 → #!/bin/sh（严格 POSIX）
│                  └── 否 → #!/bin/bash（大多数 Linux 默认）
└── 否 → 交互式使用？
         ├── 是 → zsh（推荐，配合 Oh-My-Zsh）
         └── 否 → 你可能不需要 Shell
```

---

### 2. Shebang（#!）深入

#### 2.1 Shebang 的工作原理

Shebang 是脚本文件第一行的前两个字节 `#!`，内核用它来决定用哪个解释器执行该文件。

```
执行流程：

$ ./myscript.sh
      │
      ▼
内核读取文件前两个字节
      │
      ├── 是 #! ？
      │    ├── 是 → 解析 shebang 行，获取解释器路径
      │    │        → exec("/bin/bash", ["/bin/bash", "./myscript.sh"], env)
      │    └── 否 → 尝试用默认 Shell 执行（行为不确定）
      │
      ▼
解释器读取脚本内容并执行
```

```bash
# 内核处理 shebang 的伪代码（Linux 内核 fs/binfmt_script.c）：
if (buf[0] == '#' && buf[1] == '!') {
    // 找到 shebang
    interpreter = parse_interpreter(buf);  // 提取解释器路径
    args = construct_args(interpreter, script_path);
    exec(interpreter, args);  // 用解释器重新执行
}
```

#### 2.2 三种 Shebang 写法对比

```bash
# 写法 1：绝对路径
#!/bin/bash

# 写法 2：系统默认 sh
#!/bin/sh

# 写法 3：通过 env 查找
#!/usr/bin/env bash
```

| 写法 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| `#!/bin/bash` | 明确、直接 | 路径可能不存在（FreeBSD: /usr/local/bin/bash） | 确定目标系统 |
| `#!/bin/sh` | POSIX 兼容、启动快 | 功能受限、不同系统指向不同 Shell | 系统脚本、启动脚本 |
| `#!/usr/bin/env bash` | 跨平台、尊重 PATH | 不能传递额外参数给解释器 | 通用脚本、开源项目 |

```bash
# env 方式不能传递参数的限制：
#!/usr/bin/env bash -x    # ❌ 会尝试执行 "bash -x" 这个程序名
#!/bin/bash -x            # ✅ 正确传递 -x 参数

# 解决方案：在脚本内部设置
#!/usr/bin/env bash
set -x    # 等效于 -x 参数
```

#### 2.3 Shebang 的实际影响

```bash
# 演示 shebang 的影响
cat > test_shebang.sh << 'EOF'
#!/bin/bash
echo "Shell: $0"
echo "BASH_VERSION: ${BASH_VERSION:-not bash}"
echo "数组测试: "
arr=(1 2 3)
echo "  arr[0]=${arr[0]}"
EOF
chmod +x test_shebang.sh

./test_shebang.sh
# 输出：
# Shell: ./test_shebang.sh
# BASH_VERSION: 5.1.16(1)-release
# 数组测试:
#   arr[0]=1

# 改用 sh 执行
sh test_shebang.sh
# 输出：
# Shell: test_shebang.sh
# BASH_VERSION: not bash
# 数组测试:
#   arr[0]=1 2 3   ← sh 不支持数组，(1 2 3) 被当作命令执行
```

---

### 3. 变量系统深入

#### 3.1 变量定义规则

```bash
# 变量命名规则
# ✅ 合法的变量名
name="Alice"
_private="secret"
VAR_123="value"
camelCase="ok"
UPPER_CASE="constant style"

# ❌ 非法的变量名
123var="no"         # 不能以数字开头
my-var="no"         # 不能包含连字符（- 会被解析为减法）
my var="no"         # 不能包含空格
my.var="no"         # 不能包含点号

# 为什么不能以数字开头？
# 因为 Shell 词法分析器需要区分：
#   123  → 数字字面量
#   var  → 变量名/命令名
# 如果允许 123var，解析器无法判断它是数字还是变量名

# 大小写敏感
name="Alice"
Name="Bob"
NAME="Charlie"
echo "$name $Name $NAME"    # Alice Bob Charlie

# Shell 惯例
# 环境变量和常量：大写（PATH, HOME, MY_CONFIG）
# 局部变量：小写（count, filename, user_input）
# 函数名：小写下划线（check_disk_usage, log_message）
```

#### 3.2 变量赋值的陷阱

```bash
# 等号两边不能有空格！
name="Alice"      # ✅ 赋值
name = "Alice"    # ❌ Shell 解析为：name 命令，参数 = 和 "Alice"

# 未加引号的字符串
greeting=Hello World      # ❌ World 被当作命令执行
greeting="Hello World"    # ✅

# 变量值包含特殊字符
path=/usr/local/bin       # ✅ 没有特殊字符
path="/usr/local/bin"     # ✅ 引号保护
path=/usr/local/my dir    # ❌ 空格导致问题
path="/usr/local/my dir"  # ✅

# 命令替换
today=$(date +%Y-%m-%d)   # ✅ 推荐
today=`date +%Y-%m-%d`    # ✅ 旧语法，不推荐
today=date                # ❌ 字面字符串 "date"
```

#### 3.3 变量展开（Parameter Expansion）

变量展开是 Shell 最强大的特性之一。基本形式是 `${variable}`，但它的扩展形式可以实现默认值、截取、替换等操作。

##### 基本展开

```bash
name="Hello World"

# 基本引用
echo $name           # Hello World
echo ${name}         # Hello World（推荐，边界更清晰）

# 大括号的必要性
prefix="file"
echo "${prefix}_backup.txt"    # file_backup.txt
echo "$prefix_backup.txt"      # 空！Shell 尝试展开 prefix_backup 变量
echo "${prefix}backup.txt"     # filebackup.txt
```

##### 默认值处理

```bash
# 语法总结：
# ${var:-default}   变量未设置或为空时，返回 default（不修改变量）
# ${var:=default}   变量未设置或为空时，返回 default 并赋值给 var
# ${var:+alt}       变量已设置且非空时，返回 alt
# ${var:?error}     变量未设置或为空时，报错并退出

# 详细示例：

# :- 使用默认值（不修改原变量）
unset name
echo "${name:-Anonymous}"    # 输出: Anonymous
echo "$name"                 # 仍然是空（:- 不修改变量）

name=""
echo "${name:-Anonymous}"    # 输出: Anonymous（空字符串也算"未设置"）

name="Alice"
echo "${name:-Anonymous}"    # 输出: Alice（已设置，不使用默认值）

# := 赋值默认值（修改原变量）
unset name
echo "${name:=Anonymous}"    # 输出: Anonymous
echo "$name"                 # 输出: Anonymous（变量被赋值了）

# :+ 替代值
name="Alice"
echo "${name:+Guest}"        # 输出: Guest（变量已设置，返回替代值）

unset name
echo "${name:+Guest}"        # 输出: 空（变量未设置，不返回替代值）

# :? 错误提示
unset name
echo "${name:?Name is required}"
# 输出: bash: name: Name is required
# 然后脚本退出（exit code 1）

# 实际应用：脚本参数验证
#!/bin/bash
DB_HOST="${1:?Usage: $0 <db_host>}"
DB_PORT="${2:-3306}"
DB_NAME="${3:?Usage: $0 <db_host> [db_port] <db_name>}"

echo "Connecting to ${DB_HOST}:${DB_PORT}/${DB_NAME}"
```

##### 字符串长度

```bash
str="Hello World"
echo "${#str}"       # 11（字符数）

# 数组元素个数
arr=("apple" "banana" "cherry")
echo "${#arr[@]}"    # 3
echo "${#arr[1]}"    # 6（"banana" 的长度）
```

##### 子串截取

```bash
str="Hello World"

# ${var:offset}        从 offset 开始到结尾
# ${var:offset:length} 从 offset 开始取 length 个字符
# ${var: -offset}      从右边数 offset 个字符（注意冒号后有空格）
# ${var:(-offset)}     同上，括号写法更清晰

echo "${str:0:5}"     # Hello（从位置 0 开始，取 5 个字符）
echo "${str:6}"       # World（从位置 6 到结尾）
echo "${str:6:3}"     # Wor（从位置 6 开始，取 3 个字符）

# 负数偏移（注意：冒号后面必须有空格或使用括号）
echo "${str: -5}"     # World（倒数 5 个字符）
echo "${str:(-5)}"    # World（同上，更清晰）
echo "${str: -5:3}"   # Wor（倒数 5 个字符开始，取 3 个）

# 实际应用
filepath="/var/log/syslog.1"
echo "${filepath:0:8}"       # /var/log（截取路径前缀）
echo "${filepath##*/}"       # syslog.1（提取文件名）
echo "${filepath%.*}"        # /var/log/syslog（去掉扩展名）
```

##### 模式匹配删除

```bash
# #  从左边开始，删除最短匹配
# ## 从左边开始，删除最长匹配
# %  从右边开始，删除最短匹配
# %% 从右边开始，删除最长匹配

filepath="/var/log/syslog.1"

# 提取文件名（删除最后一个 / 及之前的内容）
echo "${filepath##*/}"       # syslog.1（贪婪匹配）

# 提取目录路径（删除最后一个 / 及之后的内容）
echo "${filepath%/*}"        # /var/log

# 删除文件扩展名
echo "${filepath%.*}"        # /var/log/syslog

# 对比 # 和 ##
path="home/user/documents/file.txt"
echo "${path#*/}"            # user/documents/file.txt（最短匹配：删除到第一个 /）
echo "${path##*/}"           # file.txt（最长匹配：删除到最后一个 /）

# 对比 % 和 %%
name="archive.tar.gz"
echo "${name%.*}"            # archive.tar（最短匹配：删除最后一个 . 及之后）
echo "${name%%.*}"           # archive（最长匹配：删除第一个 . 及之后）

# 实际应用：批量重命名
for file in *.jpeg; do
    mv "$file" "${file%.jpeg}.jpg"
done

# 提取文件前缀
for file in *.log; do
    prefix="${file%.log}"
    echo "Processing: $prefix"
done
```

##### 模式替换

```bash
# ${var/pattern/replacement}   替换第一个匹配
# ${var//pattern/replacement}  替换所有匹配
# ${var/#pattern/replacement}  如果开头匹配，替换
# ${var/%pattern/replacement}  如果结尾匹配，替换

text="hello world hello bash hello"

# 替换第一个
echo "${text/hello/Hi}"         # Hi world hello bash hello

# 替换所有
echo "${text//hello/Hi}"        # Hi world Hi bash Hi

# 替换开头
echo "${text/#hello/Hi}"        # Hi world hello bash hello

# 替换结尾
echo "${text/%hello/Hi}"        # hello world hello bash Hi

# 实际应用：路径处理
path="/home/user/docs"
echo "${path/home/user}"         # /user/user/docs（替换了第一个 home）
echo "${path//home/user}"        # /user/user/docs

# URL 编码（简单场景）
url="hello world"
encoded="${url// /%20}"
echo "$encoded"                  # hello%20world

# 配置文件模板替换
config="DATABASE_HOST=localhost"
echo "${config/localhost/10.0.1.50}"   # DATABASE_HOST=10.0.1.50
```

##### 大小写转换（Bash 4.0+）

```bash
name="Hello World"

# ${var^^}  全部转大写
echo "${name^^}"           # HELLO WORLD

# ${var,,}  全部转小写
echo "${name,,}"           # hello world

# ${var^}   首字母转大写
echo "${name^}"            # Hello World（第一个字符已经是大写）

# ${var,}   首字母转小写
echo "${name,}"            # hello World

# 带模式匹配的大小写转换（Bash 4.4+）
name="hello world"
echo "${name^^[h-w]}"      # Hello World（只转换 h-w 范围的字符）
echo "${name,,[H-W]}"      # hello world

# 实际应用：用户输入规范化
read -p "确认操作 (yes/no): " answer
answer="${answer,,}"        # 转小写
if [[ "$answer" == "yes" || "$answer" == "y" ]]; then
    echo "执行操作..."
fi
```

---

### 4. 环境变量体系

#### 4.1 登录 Shell vs 非登录 Shell

```
Shell 类型判断：

登录 Shell（Login Shell）：
  - 通过终端登录（输入用户名密码）
  - ssh 远程登录
  - su - username（带减号）
  - bash --login

非登录 Shell（Non-Login Shell）：
  - 在已登录的终端中输入 bash
  - su username（不带减号）
  - 图形界面中打开终端
  - 脚本执行（#!/bin/bash）

交互式 Shell（Interactive Shell）：
  - 用户可以直接输入命令
  - 有提示符（PS1）

非交互式 Shell（Non-Interactive Shell）：
  - 执行脚本
  - 管道中的 Shell
```

#### 4.2 配置文件加载顺序

```
┌─────────────────────────────────────────────────────────────────┐
│                     登录 Shell 启动流程                          │
│                                                                 │
│  1. /etc/profile                                                │
│     │   系统级配置，所有用户共享                                   │
│     │   通常设置 PATH、umask、环境变量                             │
│     │   会 source /etc/profile.d/*.sh                            │
│     │                                                           │
│     ▼                                                           │
│  2. ~/.bash_profile  (或 ~/.bash_login 或 ~/.profile)           │
│     │   用户级配置，只加载第一个存在的文件                          │
│     │   查找顺序：.bash_profile > .bash_login > .profile         │
│     │   通常 source ~/.bashrc                                    │
│     │                                                           │
│     ▼                                                           │
│  3. ~/.bashrc                                                    │
│     │   每次打开新终端都会加载                                     │
│     │   设置别名、函数、提示符、bash 特有配置                       │
│     │                                                           │
│     ▼                                                           │
│  Shell 就绪，显示提示符                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   非登录 Shell 启动流程                           │
│                                                                 │
│  1. ~/.bashrc                                                    │
│     │   只加载这一个文件                                          │
│     │                                                           │
│     ▼                                                           │
│  Shell 就绪                                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   非交互式 Shell（脚本）启动流程                   │
│                                                                 │
│  1. 检查 BASH_ENV 变量                                           │
│     │   如果设置了，source 该文件指向的脚本                        │
│     │   例如：export BASH_ENV=~/my_env.sh                        │
│     │                                                           │
│     ▼                                                           │
│  2. 执行脚本                                                     │
│     │   注意：不加载 .bashrc、.bash_profile                      │
│     │   这就是为什么 cron 脚本经常找不到命令！                     │
│     │                                                           │
│     ▼                                                           │
│  脚本结束                                                        │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 验证配置文件加载顺序

# 在 ~/.bash_profile 中添加
echo 'echo "加载 .bash_profile"' >> ~/.bash_profile

# 在 ~/.bashrc 中添加
echo 'echo "加载 .bashrc"' >> ~/.bashrc

# 测试登录 Shell
ssh localhost
# 输出：
# 加载 .bash_profile
# 加载 .bashrc
# ...

# 测试非登录 Shell
bash
# 输出：
# 加载 .bashrc
# ...

# 清理（删除刚才添加的行）
sed -i '/echo "加载/d' ~/.bash_profile ~/.bashrc
```

#### 4.3 各配置文件的作用

```bash
# /etc/profile — 系统级环境变量和启动程序
# 内容示例：
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LANG="en_US.UTF-8"
umask 022

# 加载 /etc/profile.d/ 下的所有 .sh 文件
for i in /etc/profile.d/*.sh; do
    if [ -r "$i" ]; then
        . "$i"
    fi
done

# ~/.bash_profile — 用户级登录配置
# 内容示例：
# User specific environment and startup programs
export GOPATH="$HOME/go"
export PATH="$HOME/bin:$GOPATH/bin:$PATH"

# 加载 .bashrc
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

# ~/.bashrc — 用户级交互式 Shell 配置
# 内容示例：
# 别名
alias ll='ls -alF'
alias grep='grep --color=auto'

# 提示符
PS1='\u@\h:\w\$ '

# 自定义函数
mkcd() { mkdir -p "$1" && cd "$1"; }

# ~/.profile — 通用配置（bash 和其他 Shell 都会读取）
# 如果没有 .bash_profile，bash 会读取 .profile
# 适合设置不依赖 bash 特性的环境变量
```

#### 4.4 export 的本质

```bash
# export 的作用是将变量放入"环境"中，子进程会继承这个环境

# 进程环境传递机制
# ┌─────────────────────────────────────────────────┐
# │ 父进程 (PID 1000)                                │
# │ 环境变量表:                                       │
# │   HOME=/home/user                                │
# │   PATH=/usr/bin:/bin                             │
# │   APP_ENV=production  ← export 的变量            │
# │                                                  │
# │ 局部变量表:                                       │
# │   count=42              ← 未 export 的变量       │
# │                                                  │
# │ 当 fork() 创建子进程时：                           │
# │   子进程 = 父进程环境变量表的副本 + 全新的局部变量表│
# │                                                  │
# │ ┌─────────────────────────────────────────────┐  │
# │ │ 子进程 (PID 2000)                           │  │
# │ │ 环境变量表:  HOME, PATH, APP_ENV ✅          │  │
# │ │ 局部变量表:  （空）count ❌ 不继承            │  │
# │ └─────────────────────────────────────────────┘  │
# └─────────────────────────────────────────────────┘

# 验证实验
my_local="local_value"
export my_export="export_value"

bash -c 'echo "子进程看 local: [$my_local]"; echo "子进程看 export: [$my_export]"'
# 输出：
# 子进程看 local: []
# 子进程看 export: [export_value]

# export -n 取消导出
export -n my_export
echo "父进程: $my_export"    # export_value（还在，只是不再导出）

# export -p 列出所有导出的变量
export -p | head -20

# 环境变量是单向继承的！
bash -c 'export CHILD_VAR="from_child"'
echo "$CHILD_VAR"    # 空！子进程的 export 不影响父进程
```

#### 4.5 常用环境变量详解

```bash
# PATH — 命令搜索路径
echo $PATH
# /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# PATH 的查找顺序：从左到右
# 第一个找到的可执行文件会被执行
which ls        # /usr/bin/ls
type -a ls      # ls is aliased to 'ls --color=auto'
                # ls is /usr/bin/ls
                # ls is /bin/ls

# HOME — 用户家目录
echo $HOME      # /root 或 /home/username
cd ~            # 等价于 cd $HOME
cd              # 也是 cd $HOME

# USER / LOGNAME — 当前用户名
echo $USER      # root
echo $LOGNAME   # root

# SHELL — 默认 Shell
echo $SHELL     # /bin/bash

# PWD — 当前工作目录
echo $PWD       # /root/learn/sre_learning_plan
pwd             # 同上

# OLDPWD — 上一个工作目录
cd /tmp
echo $OLDPWD    # /root/learn/sre_learning_plan
cd -            # 等价于 cd $OLDPWD

# HOSTNAME — 主机名
echo $HOSTNAME  # my-server

# LANG — 语言和编码
echo $LANG      # en_US.UTF-8
locale          # 显示所有语言设置

# TERM — 终端类型
echo $TERM      # xterm-256color

# PPID — 父进程 PID
echo $PPID      # 父进程的 PID

# RANDOM — 随机数（0-32767）
echo $RANDOM
echo $((RANDOM % 100))    # 0-99 的随机数

# BASH_VERSION — Bash 版本
echo $BASH_VERSION    # 5.1.16(1)-release

# LINENO — 当前行号（脚本中使用）
echo "这是第 $LINENO 行"

# FUNCNAME — 当前函数名（数组）
my_function() {
    echo "当前函数: ${FUNCNAME[0]}"    # my_function
    echo "调用者: ${FUNCNAME[1]}"      # 调用此函数的函数名
}
```

---

### 5. 引号规则详解

#### 5.1 引号类型总览

```
Shell 解析命令时的处理顺序：
  1. Tokenization（分词）
  2. Alias 展开
  3. Brace Expansion（大括号展开）
  4. Tilde Expansion（波浪号展开）
  5. Parameter Expansion（变量展开）     ← 引号影响这一步
  6. Command Substitution（命令替换）     ← 引号影响这一步
  7. Arithmetic Expansion（算术展开）
  8. Word Splitting（分词）              ← 引号影响这一步
  9. Pathname Expansion（通配符展开）    ← 引号影响这一步
  10. Quote Removal（引号移除）
```

#### 5.2 单引号（Strong Quote）

```bash
# 单引号：所见即所得，不做任何展开
# 内部的所有字符都保持字面意思

echo 'Hello $USER'           # Hello $USER
echo 'Today is $(date)'      # Today is $(date)
echo 'Price is $100'         # Price is $100
echo 'Path: /usr/local/bin'  # Path: /usr/local/bin

# 单引号中不能包含单引号本身
echo 'It's a test'           # ❌ 语法错误
echo "It's a test"           # ✅ 用双引号
echo 'It'\''s a test'        # ✅ 拼接：It's a test
echo 'It'"'"'s a test'       # ✅ 同上

# 单引号的使用场景：
# 1. 正则表达式
grep 'log.*error' /var/log/syslog

# 2. 命令中的特殊字符
awk '{print $1}' file.txt

# 3. 防止变量展开
echo 'The variable $HOME is not expanded'

# 4. here document 中防止展开
cat << 'EOF'
This $HOME will NOT be expanded
$(date) will NOT be executed
EOF
```

#### 5.3 双引号（Weak Quote）

```bash
# 双引号：大部分保持字面意思，但展开以下内容：
# - 变量展开：$var, ${var}
# - 命令替换：$(cmd), `cmd`
# - 反斜杠转义：\", \\, \$, \`, \newline
# - 历史展开：!（如果启用了 history）

name="World"
echo "Hello $name"              # Hello World
echo "Home: $HOME"              # Home: /root
echo "Date: $(date +%Y-%m-%d)"  # Date: 2026-04-26
echo "Price: \$100"             # Price: $100
echo "Quote: \"Hello\""         # Quote: "Hello"
echo "Backslash: \\"            # Backslash: \

# 双引号中的特殊转义
echo "Tab:\there"               # Tab:	here
echo "Newline:\nhere"           # 需要 echo -e
echo -e "Newline:\nhere"        # Newline:
                                # here

# 双引号防止分词（Word Splitting）和通配符展开
files="file1.txt file2.txt file3.txt"
# 不加引号：Shell 会对 $files 进行分词
echo $files                     # file1.txt file2.txt file3.txt（看起来一样）

# 但如果有特殊字符
path="/my dir/file.txt"
cat $path                       # ❌ 错误：/my 和 dir/file.txt 被当作两个参数
cat "$path"                     # ✅ 正确："/my dir/file.txt" 作为一个参数

# 通配符保护
echo "*"                        # *（字面量）
echo *                          # 当前目录所有文件（通配符展开）

# 永远用双引号引用变量！（最佳实践）
# ✅
echo "$variable"
echo "${array[@]}"
rm "$file"

# ❌
echo $variable
rm $file
```

#### 5.4 反引号 vs $()

```bash
# 两者都是命令替换，但 $() 更推荐

# 反引号（旧语法）
today=`date +%Y-%m-%d`
echo "Today: $today"

# $()（新语法，推荐）
today=$(date +%Y-%m-%d)
echo "Today: $today"

# 嵌套命令替换的区别：

# 反引号嵌套需要转义，可读性差
result=`echo \`whoami\`@`hostname``

# $() 可以自然嵌套
result=$(echo $(whoami)@$(hostname))

# 更复杂的嵌套
disk_usage=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
echo "磁盘使用率: ${disk_usage}%"

# 命令替换中的换行会被删除（但保留内部换行）
files=$(ls /etc/*.conf)
echo "$files"    # 每行一个文件（保留换行）
echo $files      # 所有文件在一行（分词 + 换行被压缩）

# 最佳实践：总是使用 $()
# 1. 可读性更好
# 2. 支持嵌套
# 3. 不需要转义
```

#### 5.5 引号组合使用

```bash
# 场景 1：在单引号字符串中包含变量
# 方法：拼接
name="Alice"
echo 'Hello '"$name"'!'        # Hello Alice!
echo 'Hello '"$name"'! Welcome to '$HOME
# 解析：'Hello ' + "$name" + '!' + ' Welcome to ' + $HOME

# 场景 2：在双引号字符串中包含单引号
echo "It's a \"good\" day"     # It's a "good" day
echo "他说：'你好'"             # 他说：'你好'

# 场景 3：构建复杂命令
user="admin"
host="server01"
ssh "$user@$host" 'cat /etc/hostname'
# 解析：ssh admin@server01 cat /etc/hostname

# 场景 4：在变量中存储带引号的值
cmd='grep "error" /var/log/syslog'
eval $cmd    # ⚠️ eval 会再次解析引号（慎用）

# 场景 5：数组与引号
files=("file 1.txt" "file 2.txt" "file 3.txt")
for f in "${files[@]}"; do    # ⚠️ 必须用 "${files[@]}"
    echo "Processing: $f"
done

# 错误写法
for f in ${files[@]}; do      # ❌ 会按空格分词
    echo "Processing: $f"
done
```

---

### 6. 特殊变量详解

```bash
#!/usr/bin/env bash
# special_vars.sh — 演示所有特殊变量

echo "=== 位置参数 ==="
echo "\$0  = $0"          # 脚本名
echo "\$1  = $1"          # 第 1 个参数
echo "\$2  = $2"          # 第 2 个参数
echo "\$3  = $3"          # 第 3 个参数
echo "\$4  = $4"          # 第 4 个参数
echo "\$5  = $5"          # 第 5 个参数
echo "\$6  = $6"          # 第 6 个参数
echo "\$7  = $7"          # 第 7 个参数
echo "\$8  = $8"          # 第 8 个参数
echo "\$9  = $9"          # 第 9 个参数
echo "\$10 = ${10}"       # 第 10 个参数（必须用大括号！）
echo "\$11 = ${11}"       # 第 11 个参数

echo ""
echo "=== 参数统计 ==="
echo "\$#  = $#"          # 参数个数
echo "\$*  = [$*]"        # 所有参数（一个字符串）
echo "\$@  = [$@]"        # 所有参数（独立字符串）

echo ""
echo "=== 进程信息 ==="
echo "\$\$  = $$"         # 当前进程 PID
echo "\$!  = $!"          # 最后一个后台进程的 PID
echo "\$-  = $-"          # 当前 Shell 的选项标志
echo "\$_  = $_"          # 上一个命令的最后一个参数

echo ""
echo "=== 退出状态 ==="
true
echo "\$? after true  = $?"    # 0
false
echo "\$? after false = $?"    # 1
ls /nonexistent 2>/dev/null
echo "\$? after failed ls = $?" # 2
```

#### 6.1 $@ 和 $* 的关键区别

```bash
#!/usr/bin/env bash
# 这是 $@ 和 $* 最重要的区别

set -- "hello world" "foo bar" "baz"

echo "=== 不加引号 ==="
echo '$*:'
for arg in $*; do echo "  [$arg]"; done
#   [hello]
#   [world]
#   [foo]
#   [bar]
#   [baz]

echo '$@:'
for arg in $@; do echo "  [$arg]"; done
#   [hello]
#   [world]
#   [foo]
#   [bar]
#   [baz]
# 不加引号时，$* 和 $@ 行为相同，都会分词

echo ""
echo '=== 加双引号 ==='
echo '"$*":'
for arg in "$*"; do echo "  [$arg]"; done
#   [hello world foo bar baz]   ← 所有参数合并为一个字符串

echo '"$@":'
for arg in "$@"; do echo "  [$arg]"; done
#   [hello world]     ← 保持原始分组
#   [foo bar]
#   [baz]

# 结论：
# "$*" — 所有参数合并为一个字符串（IFS 的第一个字符作为分隔符）
# "$@" — 每个参数保持独立（推荐用于遍历参数）
# 不加引号 — 两者行为相同，都会分词和通配符展开

# 实际应用：
# 处理文件名含空格的情况
process_files() {
    for file in "$@"; do    # ✅ 必须用 "$@"
        echo "Processing: $file"
    done
}

# 如果用 $* 或不加引号：
process_files_wrong() {
    for file in $*; do      # ❌ 文件名中的空格会导致分词
        echo "Processing: $file"
    done
}

# 调用
process_files "my file.txt" "another file.txt"
# 正确输出：
# Processing: my file.txt
# Processing: another file.txt

process_files_wrong "my file.txt" "another file.txt"
# 错误输出：
# Processing: my
# Processing: file.txt
# Processing: another
# Processing: file.txt
```

#### 6.2 shift 命令

```bash
#!/usr/bin/env bash
# shift 演示

echo "初始参数: $@"
echo "参数个数: $#"

# shift N — 向左移动 N 个参数（默认 N=1）
shift
echo "shift 1 后: $@"

shift 2
echo "shift 2 后: $@"

# 实际应用：解析命令行选项
#!/usr/bin/env bash
# parse_args.sh

verbose=false
output="default.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose)
            verbose=true
            shift
            ;;
        -o|--output)
            output="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-v] [-o output] [files...]"
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# 剩余的参数
echo "verbose=$verbose"
echo "output=$output"
echo "files=$@"
```

---

### 7. SRE 实战案例

#### 7.1 变量为空导致 rm -rf 灾难

```bash
#!/usr/bin/env bash
# 危险脚本 — 变量为空导致灾难

# 场景：清理某个目录下的临时文件
TARGET_DIR="/tmp/myapp_cache"
# 某天 TARGET_DIR 因为某种原因变成空字符串

rm -rf $TARGET_DIR/*     # 展开为 rm -rf /*
# 💥 删除整个文件系统！

# 安全写法：
TARGET_DIR="/tmp/myapp_cache"

# 1. 使用 set -u（未定义变量报错）
set -u
rm -rf $TARGET_DIR/*     # 如果 TARGET_DIR 未定义，脚本会报错退出

# 2. 检查变量是否为空
if [[ -z "$TARGET_DIR" ]]; then
    echo "ERROR: TARGET_DIR is empty!" >&2
    exit 1
fi
rm -rf "$TARGET_DIR"/*    # 引号保护

# 3. 使用变量展开的错误提示
rm -rf "${TARGET_DIR:?TARGET_DIR is not set}"/*

# 4. 验证路径合理性
if [[ "$TARGET_DIR" == "/" || "$TARGET_DIR" == "/home" || -z "$TARGET_DIR" ]]; then
    echo "ERROR: Refusing to operate on dangerous path: '$TARGET_DIR'" >&2
    exit 1
fi
rm -rf "$TARGET_DIR"/*

# 5. 使用 -- 终止选项解析
rm -rf -- "$TARGET_DIR"/*
# 防止 TARGET_DIR 以 - 开头被当作选项
```

#### 7.2 环境变量未加载导致 cron 脚本失败

```bash
#!/usr/bin/env bash
# cron_backup.sh — 定时备份脚本

# 问题：手动执行正常，cron 执行失败
# 原因：cron 使用非交互式非登录 Shell，不加载 .bashrc 和 .bash_profile

# 错误日志：
# /etc/cron.d/backup: line 5: mysqldump: command not found
# /etc/cron.d/backup: line 8: aws: command not found

# 解决方案 1：在脚本中设置完整 PATH
#!/usr/bin/env bash
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/mysql/bin:/usr/local/aws-cli/bin"

# 解决方案 2：使用绝对路径
#!/usr/bin/env bash
/usr/bin/mysqldump -u root mydb > /backup/db.sql
/usr/local/bin/aws s3 cp /backup/db.sql s3://mybucket/

# 解决方案 3：在 cron 中 source 环境文件
# /etc/cron.d/backup
# SHELL=/bin/bash
# 0 2 * * * root source /etc/profile && /opt/scripts/backup.sh

# 解决方案 4：脚本开头加载配置文件
#!/usr/bin/env bash
# 加载系统环境
[[ -f /etc/profile ]] && source /etc/profile
# 加载用户环境
[[ -f ~/.bash_profile ]] && source ~/.bash_profile
[[ -f ~/.bashrc ]] && source ~/.bashrc

# 最佳实践：SRE 推荐的 cron 脚本模板
#!/usr/bin/env bash
set -euo pipefail

# 显式设置 PATH
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 显式设置所有需要的变量
export HOME="/root"
export LANG="en_US.UTF-8"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# 主逻辑
log "Starting backup..."
# ... 备份逻辑 ...
log "Backup completed successfully"
```

#### 7.3 配置文件路径问题排查

```bash
#!/usr/bin/env bash
# config_debug.sh — 配置加载问题排查脚本

# 场景：脚本在开发环境正常，生产环境找不到配置文件

# 常见原因：
# 1. 相对路径 vs 绝对路径
# 2. 用户家目录不同
# 3. 环境变量未设置
# 4. 文件权限问题

# 排查脚本
echo "=== 环境信息 ==="
echo "当前用户: $(whoami)"
echo "家目录: $HOME"
echo "工作目录: $PWD"
echo "脚本位置: $(dirname "$0")"
echo "脚本绝对路径: $(readlink -f "$0")"

echo ""
echo "=== 配置文件检查 ==="
CONFIG_FILE="${1:-/etc/myapp/config.yaml}"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: 配置文件不存在: $CONFIG_FILE"
    echo ""
    echo "尝试查找配置文件..."
    find / -name "config.yaml" -path "*/myapp/*" 2>/dev/null
    exit 1
fi

if [[ ! -r "$CONFIG_FILE" ]]; then
    echo "ERROR: 配置文件不可读: $CONFIG_FILE"
    ls -la "$CONFIG_FILE"
    exit 1
fi

echo "配置文件存在且可读: $CONFIG_FILE"
echo "文件大小: $(stat -c %s "$CONFIG_FILE") bytes"
echo "最后修改: $(stat -c %y "$CONFIG_FILE")"

# 获取脚本所在目录的可靠方法
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${SCRIPT_DIR}/../config/config.yaml"

# 推荐的配置文件查找顺序
find_config() {
    local config_name="$1"

    # 1. 命令行参数
    if [[ -n "${CONFIG_FILE:-}" ]]; then
        echo "$CONFIG_FILE"
        return
    fi

    # 2. 环境变量
    if [[ -n "${MYAPP_CONFIG:-}" ]]; then
        echo "$MYAPP_CONFIG"
        return
    fi

    # 3. 脚本相对路径
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local candidates=(
        "${script_dir}/../config/${config_name}"
        "${script_dir}/${config_name}"
        "/etc/myapp/${config_name}"
        "${HOME}/.config/myapp/${config_name}"
    )

    for candidate in "${candidates[@]}"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return
        fi
    done

    echo ""
    return 1
}
```

---

## 💻 实战练习

### 练习 1：变量展开练习

```bash
# 预测以下命令的输出，然后运行验证

str="Hello World Bash Script"

echo "${str:6:5}"           # ?
echo "${str: -6}"           # ?
echo "${str%% *}"           # ?
echo "${str#* }"            # ?
echo "${str##* }"           # ?
echo "${str/ /_}"           # ?
echo "${str// /_}"          # ?
echo "${#str}"              # ?
echo "${str^^}"             # ?
echo "${str,,}"             # ?
```

<details>
<summary>答案</summary>

```
${str:6:5}     → World（从位置 6 开始取 5 个字符）
${str: -6}     → Script（倒数 6 个字符）
${str%% *}     → Hello（删除第一个空格及之后的所有内容）
${str#* }      → World Bash Script（删除到第一个空格）
${str##* }     → Script（删除到最后一个空格）
${str/ /_}     → Hello_World Bash Script（替换第一个空格）
${str// /_}    → Hello_World_Bash_Script（替换所有空格）
${#str}        → 23（字符串长度）
${str^^}       → HELLO WORLD BASH SCRIPT
${str,,}       → hello world bash script
```
</details>

### 练习 2：环境变量排查

```bash
# 场景：一个 cron 任务执行失败，错误信息是 "command not found"
# 请编写一个诊断脚本，输出以下信息：
# 1. 当前 Shell 类型（登录/非登录、交互/非交互）
# 2. PATH 的值
# 3. 关键命令的路径（bash, python3, curl, aws）
# 4. 环境变量 HOME, USER, SHELL 的值
# 5. 加载了哪些配置文件

cat > diagnose_shell.sh << 'SCRIPT'
#!/usr/bin/env bash
echo "=== Shell 类型判断 ==="
# 检查是否登录 Shell
shopt -q login_shell && echo "登录 Shell" || echo "非登录 Shell"
# 检查是否交互式
[[ $- == *i* ]] && echo "交互式 Shell" || echo "非交互式 Shell"

echo ""
echo "=== PATH ==="
echo "$PATH" | tr ':' '\n'

echo ""
echo "=== 关键命令路径 ==="
for cmd in bash python3 curl aws git docker; do
    path=$(which "$cmd" 2>/dev/null)
    echo "$cmd: ${path:-NOT FOUND}"
done

echo ""
echo "=== 环境变量 ==="
echo "HOME=$HOME"
echo "USER=$USER"
echo "SHELL=$SHELL"
echo "LANG=$LANG"
echo "PWD=$PWD"
SCRIPT
chmod +x diagnose_shell.sh

# 对比手动执行和 cron 环境
./diagnose_shell.sh
# 然后在 cron 中执行，对比输出差异
```

### 练习 3：编写安全的变量使用脚本

```bash
# 编写一个脚本，接收一个目录路径作为参数
# 要求：
# 1. 验证参数不为空
# 2. 验证路径不是危险路径（/、/home、/etc 等）
# 3. 验证目录存在
# 4. 使用变量展开提取目录名和父目录
# 5. 输出目录的详细信息

cat > safe_dir_info.sh << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

# 你的实现...
SCRIPT
```

---

## 🎯 面试题精选

### 1. $@ 和 $* 的区别是什么？

**答：**
- **不加引号时**：两者行为相同，所有参数按空格分词
- **加双引号时**：
  - `"$@"` — 每个参数保持独立，`"$1" "$2" "$3"`
  - `"$*"` — 所有参数合并为一个字符串，`"$1 $2 $3"`（以 IFS 第一个字符连接）
- **最佳实践**：遍历参数时始终使用 `"$@"`

### 2. 如何安全地使用变量防止命令注入？

**答：**
```bash
# 1. 始终用双引号引用变量
rm "$file"         # ✅
rm $file           # ❌

# 2. 使用 set -u 检测未定义变量
set -u
echo "$undefined"  # 报错退出

# 3. 使用 ${var:?} 做参数验证
DB_HOST="${1:?Usage: $0 <db_host>}"

# 4. 避免使用 eval
eval "$user_input"  # ❌ 极度危险

# 5. 验证路径防止目录遍历
[[ "$path" == ..* ]] && { echo "Invalid path"; exit 1; }

# 6. 使用 -- 终止选项解析
rm -- "$file"
```

### 3. Shell 配置文件的加载顺序是什么？

**答：**
- **登录 Shell**：`/etc/profile` → `~/.bash_profile`（或 `~/.bash_login` 或 `~/.profile`）→ `~/.bashrc`
- **非登录交互式 Shell**：`~/.bashrc`
- **非交互式 Shell（脚本）**：检查 `BASH_ENV` 变量，不加载 `.bashrc`
- **关键点**：`~/.bash_profile` 通常会 `source ~/.bashrc`

### 4. 以下代码有什么问题？
```bash
rm -rf $DIR/*
```

**答：**
- 如果 `DIR` 未定义或为空，会执行 `rm -rf /*`，删除整个文件系统
- **修复方案**：
  ```bash
  rm -rf "${DIR:?DIR is not set}"/*
  # 或
  [[ -z "$DIR" ]] && { echo "DIR is empty"; exit 1; }
  rm -rf "$DIR"/*
  ```

### 5. export 的本质是什么？子进程能修改父进程的环境变量吗？

**答：**
- `export` 将变量标记为"导出"，使其进入进程的环境变量表
- fork() 创建子进程时，子进程继承父进程的环境变量表的副本
- **子进程不能修改父进程的环境变量** — 修改只影响子进程自己和它的子进程
- 这是单向继承机制：父 → 子 → 孙

### 6. 如何判断当前是登录 Shell 还是非登录 Shell？

**答：**
```bash
# 方法 1：检查 login_shell 选项
shopt -q login_shell && echo "Login Shell" || echo "Non-Login Shell"

# 方法 2：检查 $0
# 登录 Shell 通常 $0 以 - 开头（如 -bash）
echo $0

# 方法 3：检查 $-
# 登录 Shell 通常没有 i 标志
echo $-
```

### 7. `${var:-default}` 和 `${var:=default}` 的区别？

**答：**
- `${var:-default}` — 变量未设置或为空时返回 default，**不修改变量**
- `${var:=default}` — 变量未设置或为空时返回 default，**同时将 default 赋值给变量**

```bash
unset x
echo "${x:-hello}"    # hello
echo "$x"             # 空（未修改）

echo "${x:=hello}"    # hello
echo "$x"             # hello（已修改）
```

### 8. 为什么推荐用 `$()` 而不是反引号？

**答：**
1. **可嵌套**：`$(cmd1 $(cmd2))` 自然嵌套，反引号需要转义 `` `cmd1 \`cmd2\`` ``
2. **可读性**：`$()` 的开始和结束更清晰
3. **与引号组合更自然**：`echo "$(cmd)"` vs `` echo "`cmd`" ``
4. **现代 Shell 都支持**，包括 bash、zsh、ksh

---

## 📚 深入阅读

### 官方文档
- [Bash Manual](https://www.gnu.org/software/bash/manual/bash.html) — GNU 官方 Bash 手册
- [Bash Hackers Wiki](https://wiki.bash-hackers.org/) — Bash 技巧和陷阱
- [POSIX Shell Spec](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html) — POSIX Shell 规范

### 推荐书籍
- 《Bash Cookbook》— O'Reilly 出版，实战案例丰富
- 《Learning the bash Shell》— O'Reilly 出版，入门经典
- 《Pro Bash Programming》— Apress 出版，进阶技巧

### 在线资源
- [ShellCheck](https://www.shellcheck.net/) — 在线 Shell 脚本静态分析工具
- [Bash Pitfalls](http://mywiki.wooledge.org/BashPitfalls) — 常见 Bash 陷阱集合
- [Explain Shell](https://explainshell.com/) — 在线解析 Shell 命令含义
- [Bash Scripting Tutorial](https://ryanstutorials.net/bash-scripting-tutorial/) — 入门教程

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 bash、sh、zsh、dash 的区别和适用场景
- [ ] 理解 Shebang 的工作原理和三种写法的差异
- [ ] 掌握变量展开的所有形式（:- := :+ :? # ## % %% / //）
- [ ] 理解登录 Shell vs 非登录 Shell 的配置文件加载顺序
- [ ] 能解释 export 的本质（子进程继承机制）
- [ ] 掌握单引号、双引号、反引号、$() 的精确行为差异
- [ ] 理解 $@ 和 $* 在加引号和不加引号时的区别

### 实操检查点
- [ ] 能编写使用变量展开的安全脚本
- [ ] 能诊断 cron 脚本因环境变量导致的失败
- [ ] 能正确处理文件名含空格的情况
- [ ] 能编写带参数验证的脚本（使用 ${var:?} 模式）
- [ ] 理解并能演示 rm -rf $EMPTY_VAR/* 的危险性
