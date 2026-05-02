# Day 17: Shell 循环结构 — for/while/until

> 📅 日期：2026-04-26
> 📖 学习主题：Shell 循环结构 — for/while/until
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 17 的学习后，你应该掌握：
- 掌握 for 循环的多种写法（列表、C 风格、命令替换、glob）
- 掌握 while/until 循环的使用场景和区别
- 理解 break、continue 的用法和嵌套控制
- 掌握 read 命令逐行处理文件的安全写法
- 理解子 Shell 陷阱（管道中的 while 修改变量不可见）
- 了解循环性能优化的常见方法

---

## 📖 详细知识点

### 1. for 循环

#### 1.1 遍历列表

```bash
# 基本语法
for 变量 in 值1 值2 值3; do
    命令
done

# 示例
for color in red green blue; do
    echo "颜色: $color"
done
# 输出：
# 颜色: red
# 颜色: green
# 颜色: blue

# 使用数组
servers=("web01" "web02" "db01" "cache01")
for server in "${servers[@]}"; do
    echo "检查 $server..."
    # ssh "$server" "uptime"
done

# 数组索引遍历
for i in "${!servers[@]}"; do
    echo "索引 $i: ${servers[$i]}"
done
```

#### 1.2 遍历数字范围

```bash
# {start..end} 语法
for i in {1..5}; do
    echo "$i"
done
# 输出：1 2 3 4 5

# 带步长
for i in {0..10..2}; do
    echo "$i"    # 0 2 4 6 8 10
done

# 递减
for i in {5..1}; do
    echo "倒计时: $i"
done

# C 风格（最灵活）
for ((i=0; i<10; i+=2)); do
    echo "i = $i"    # 0 2 4 6 8
done

# 多变量
for ((i=0, j=10; i<j; i++, j--)); do
    echo "i=$i, j=$j"
done
```

#### 1.3 遍历文件和目录

```bash
# 遍历当前目录的 .txt 文件
for file in *.txt; do
    echo "处理: $file"
    wc -l "$file"
done

# ⚠️ 陷阱：如果没有匹配的文件
# *.txt 不会被展开，file 会变成字面量 "*.txt"
# 解决方案 1：nullglob
shopt -s nullglob    # 没有匹配时展开为空列表
for file in *.txt; do
    echo "处理: $file"
done
shopt -u nullglob

# 解决方案 2：检查文件是否存在
for file in *.txt; do
    [[ -e $file ]] || continue
    echo "处理: $file"
done

# 遍历目录
for dir in /var/log/*/; do
    echo "目录: $dir"
    count=$(find "$dir" -type f 2>/dev/null | wc -l)
    echo "  文件数: $count"
done

# 递归遍历（用 find + for，注意空格陷阱）
for file in $(find . -name "*.log" -type f); do
    echo "$file"    # 文件名有空格时会出问题
done
```

#### 1.4 命令替换

```bash
# 遍历命令输出
for user in $(cut -d: -f1 /etc/passwd); do
    echo "用户: $user"
done

# 遍历 find 结果
for logfile in $(find /var/log -name "*.log" -type f 2>/dev/null); do
    echo "日志: $logfile"
done

# ⚠️ 文件名含空格的问题
# for 按空格/换行分割，文件名 "my file.log" 会变成两个
# 解决方案：用 while read（见下文）
```

### 2. while 循环

```bash
# 基本语法
while 条件; do
    命令
done

# 计数器
count=0
while (( count < 5 )); do
    echo "count = $count"
    ((count++))
done

# 条件为真就一直执行
while true; do
    echo "$(date): 运行中..."
    sleep 10
done

# 逐行读取文件（标准写法）
while IFS= read -r line; do
    echo "行: $line"
done < /etc/passwd

# IFS= 的作用：
# 默认 read 会按空格/Tab 分割行，IFS= 保留原始内容
# -r 的作用：不转义反斜杠
# < file 的作用：重定向输入，而不是管道
```

### 3. until 循环

```bash
# until 条件为假时继续，为真时停止（与 while 相反）

# 等待服务就绪
until systemctl is-active --quiet nginx; do
    echo "等待 Nginx 启动..."
    sleep 2
done
echo "Nginx 已启动"

# 等价于 while !
while ! systemctl is-active --quiet nginx; do
    sleep 2
done

# 等待文件出现
until [[ -f /tmp/ready ]]; do
    echo "等待就绪文件..."
    sleep 1
done

# 带超时控制
timeout=60
until curl -sf http://localhost:8080/health > /dev/null; do
    if (( timeout <= 0 )); then
        echo "超时！"
        exit 1
    fi
    echo "等待中... (${timeout}s)"
    sleep 2
    ((timeout -= 2))
done
```

### 4. break 和 continue

```bash
# break — 退出整个循环
for i in {1..10}; do
    if [[ $i -eq 5 ]]; then
        echo "找到 5，退出"
        break
    fi
    echo "$i"
done

# continue — 跳过当前迭代，继续下一个
for i in {1..10}; do
    if (( i % 2 == 0 )); then
        continue    # 跳过偶数
    fi
    echo "奇数: $i"
done

# break N — 退出 N 层嵌套循环
for i in {1..3}; do
    for j in {1..3}; do
        echo "($i, $j)"
        if [[ $i -eq 2 && $j -eq 2 ]]; then
            echo "找到 (2,2)，退出所有"
            break 2    # 退出两层
        fi
    done
done
```

### 5. 子 Shell 陷阱

```bash
# ⚠️ 管道中的 while 在子 Shell 中执行
# 子 Shell 中的变量修改对外部不可见

count=0
cat /etc/passwd | while read -r line; do
    ((count++))
done
echo "$count"    # 0！修改在子 Shell 中

# ✅ 修复 1：进程替换
count=0
while read -r line; do
    ((count++))
done < <(cat /etc/passwd)
echo "$count"    # 正确

# ✅ 修复 2：重定向
count=0
while read -r line; do
    ((count++))
done < /etc/passwd
echo "$count"    # 正确

# ✅ 修复 3：用最后一个管道在子 Shell 的特性
# 如果只需要在循环内处理，管道也没问题
cat /etc/passwd | while read -r line; do
    echo "处理: $line"    # 在子 Shell 中可以正常操作
done
```

### 6. read 的高级用法

```bash
# 读取带分隔符的数据
while IFS=: read -r user _ uid _ info home shell; do
    if (( uid >= 1000 )); then
        echo "普通用户: $user, 家目录: $home"
    fi
done < /etc/passwd

# 读取多行直到空行
while read -r line; do
    [[ -z "$line" ]] && break
    echo "处理: $line"
done

# 从用户输入读取
echo "输入你的名字（Ctrl+D 结束）："
while read -r name; do
    echo "你好, $name"
done

# 读取命令输出并处理
docker ps --format "{{.Names}} {{.Status}}" | while read -r name status; do
    echo "容器: $name, 状态: $status"
done
```

### 7. 性能优化

```bash
# ❌ 每次循环启动子进程（1000 次 = 很慢）
for i in {1..1000}; do
    result=$(echo "$i * 2" | bc)
done

# ✅ 用 Bash 内置算术（快 100 倍）
for i in {1..1000}; do
    result=$((i * 2))
done

# ❌ 逐行处理大文件
for file in *.log; do
    lines=$(wc -l < "$file")
    echo "$file: $lines 行"
done

# ✅ 用 awk 一次处理
awk '{files[FILENAME]++} END {for(f in files) print f, files[f]}' *.log
```

### 8. 并行循环

```bash
# 串行处理
for server in web01 web02 web03 web04; do
    ssh "$server" "uptime"
done

# 并行处理（& + wait）
for server in web01 web02 web03 web04; do
    ssh "$server" "uptime" &    # 后台执行
done
wait    # 等待所有后台任务完成
echo "全部完成"

# 控制并发数
MAX_PARALLEL=4
for server in $(cat servers.txt); do
    ssh "$server" "uptime" &
    while (( $(jobs -r | wc -l) >= MAX_PARALLEL )); do
        sleep 0.1
    done
done
wait
```

---

## 🏗️ 实战

### 实战 1：批量备份数据库

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS=7

mkdir -p "$BACKUP_DIR"

# 获取所有非系统数据库
databases=$(mysql -u root -N -e "SHOW DATABASES" \
  | grep -Ev "^(information_schema|mysql|performance_schema|sys)$")

success=0
fail=0

for db in $databases; do
    echo -n "备份 $db... "
    if mysqldump -u root "$db" | gzip > "$BACKUP_DIR/${db}_${DATE}.sql.gz"; then
        echo "✅"
        ((success++))
    else
        echo "❌"
        ((fail++))
    fi
done

# 清理旧备份
old_count=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETAIN_DAYS | wc -l)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETAIN_DAYS -delete
echo ""
echo "完成: 成功 $success, 失败 $fail, 清理 $old_count 个旧备份"
```

### 实战 2：批量修复 Web 权限

```bash
#!/usr/bin/env bash
WEB_ROOT="${1:?用法: $0 <网站根目录>}"

if [[ ! -d "$WEB_ROOT" ]]; then
    echo "错误: $WEB_ROOT 不是目录"
    exit 1
fi

echo "修复 $WEB_ROOT 权限..."

# 统计
dir_count=$(find "$WEB_ROOT" -type d | wc -l)
file_count=$(find "$WEB_ROOT" -type f | wc -l)

echo "  目录: $dir_count 个"
echo "  文件: $file_count 个"

# 批量设置
find "$WEB_ROOT" -type d -exec chmod 755 {} +
find "$WEB_ROOT" -type f -exec chmod 644 {} +

# 特定目录需要执行权限
for dir in bin scripts; do
    if [[ -d "$WEB_ROOT/$dir" ]]; then
        find "$WEB_ROOT/$dir" -type f -exec chmod 755 {} +
        echo "  $dir 目录设为可执行"
    fi
done

sudo chown -R www-data:www-data "$WEB_ROOT"
echo "✅ 权限修复完成"
```

### 实战 3：持续监控

```bash
#!/usr/bin/env bash
URL="${1:?用法: $0 <URL> [最大等待秒数]}"
MAX_WAIT="${2:-60}"
INTERVAL=2

echo "等待 $URL 就绪（最多 ${MAX_WAIT}s）..."
elapsed=0

until curl -sf "$URL" > /dev/null 2>&1; do
    if (( elapsed >= MAX_WAIT )); then
        echo "❌ 超时！$URL 在 ${MAX_WAIT}s 内未就绪"
        exit 1
    fi
    sleep $INTERVAL
    ((elapsed += INTERVAL))
done

echo "✅ $URL 已就绪（耗时 ${elapsed}s）"
```

---

## 🧪 练习题

### 练习 1：找出最大的文件

遍历指定目录，找出最大的 5 个文件。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
dir="${1:-.}"

find "$dir" -type f -printf '%s %p\n' 2>/dev/null \
  | sort -rn \
  | head -5 \
  | while read -r size path; do
      printf "%10s  %s\n" "$(numfmt --to=iec $size)" "$path"
    done
```
</details>

### 练习 2：批量重命名

将当前目录所有 .jpg 文件重命名为 photo_001.jpg, photo_002.jpg...

<details>
<summary>答案</summary>

```bash
#!/bin/bash
i=1
for file in *.jpg; do
    [[ -e $file ]] || continue
    new_name=$(printf "photo_%03d.jpg" $i)
    mv "$file" "$new_name"
    echo "$file → $new_name"
    ((i++))
done
```
</details>

---

## 📚 扩展阅读

- `man bash` — 搜索 "LOOPING COMMANDS"
- [Bash for 循环完全指南](https://linuxize.com/post/bash-for-loop/)
- [Bash Pitfalls — 循环常见错误](http://mywiki.wooledge.org/BashPitfalls#for_f_in_.24.28ls_.2A.mp3.29)
