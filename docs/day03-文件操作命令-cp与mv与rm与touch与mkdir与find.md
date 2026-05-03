# Day 03: 文件操作命令 — cp/mv/rm/touch/mkdir/find

> 📅 日期：2026-04-25
> 📖 学习主题：文件操作的系统调用、find 命令深入、文件删除安全实践、大文件处理
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 02（文件系统与目录结构）

## 🎯 学习目标

完成 Day 03 的学习后，你应该能够：
1. 从系统调用层面理解文件操作（open/read/write/close、unlink、rename）的工作原理
2. 精通 find 命令的高级用法（-exec、xargs、性能优化、-prune 排除）
3. 掌握文件删除的安全实践（trash-cli、safe-rm alias）
4. 使用 split、dd、truncate 处理大文件
5. 编写日志清理和临时文件管理脚本
6. 回答 rm -rf 误删恢复、find 与 locate 区别等面试题

---

## 📖 核心知识点

### 1. 文件操作的系统调用层面

#### 1.1 文件描述符与系统调用

```
文件操作的系统调用层次：

应用程序
    │
    │  fopen("file.txt", "r")    ← C 库函数
    ▼
C 标准库 (glibc)
    │
    │  open("file.txt", O_RDONLY) ← 系统调用
    ▼
VFS 层
    │
    │  file->f_op->open()        ← 文件系统实现
    ▼
具体文件系统 (ext4/xfs/...)
    │
    │  读取 inode、分配数据块
    ▼
块设备驱动
    │
    │  发送 I/O 请求
    ▼
硬件 (磁盘/SSD)
```

#### 1.2 open() 系统调用

```c
// 系统调用原型
int open(const char *pathname, int flags, mode_t mode);

// 常用 flags
O_RDONLY      // 只读
O_WRONLY      // 只写
O_RDWR        // 读写
O_CREAT       // 文件不存在则创建
O_TRUNC       // 截断文件（清空内容）
O_APPEND      // 追加模式
O_EXCL        // 与 O_CREAT 配合，文件必须不存在
O_NONBLOCK    // 非阻塞模式
O_CLOEXEC     // exec 时自动关闭

// 常用 mode（权限）
0644          // rw-r--r--
0755          // rwxr-xr-x
0600          // rw-------

// 返回值：文件描述符（非负整数），失败返回 -1
```

**SRE 相关知识**：
```bash
# 查看进程打开的文件描述符
ls -la /proc/<PID>/fd

# 查看系统文件描述符限制
cat /proc/sys/fs/file-max          # 系统级限制
ulimit -n                          # 当前用户的软限制
ulimit -Hn                         # 当前用户的硬限制

# 查看文件描述符使用情况
cat /proc/sys/fs/file-nr
# 已分配  未使用  最大值
# 12345   0       1000000

# 调整文件描述符限制
# 临时调整
ulimit -n 65535

# 永久调整
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
EOF
```

#### 1.3 read() 和 write() 系统调用

```c
// read 原型
ssize_t read(int fd, void *buf, size_t count);
// 返回值：实际读取的字节数，0 表示 EOF，-1 表示错误

// write 原型
ssize_t write(int fd, const void *buf, size_t count);
// 返回值：实际写入的字节数，-1 表示错误
```

**read/write 的内部流程**：
```
read() 流程：
1. 应用程序调用 read(fd, buf, 4096)
2. 内核检查 fd 是否有效
3. 内核检查 buf 地址是否可写
4. 内核调用 VFS 的 read 方法
5. VFS 调用具体文件系统的 read 方法
6. 检查页缓存 (Page Cache)：
   ├── 命中：直接从缓存复制到用户空间
   └── 未命中：
       ├── 从磁盘读取数据到页缓存
       ├── 从页缓存复制到用户空间
       └── 更新页缓存
7. 更新文件位置 (f_pos)
8. 返回读取的字节数

write() 流程：
1. 应用程序调用 write(fd, buf, 4096)
2. 内核检查 fd 是否有效
3. 内核将数据复制到页缓存（标记为脏页）
4. 更新文件元数据（大小、时间戳）
5. 返回写入的字节数
6. 脏页稍后由内核的 pdflush/flush 线程写回磁盘

关键点：write() 不会立即写入磁盘！
同步写入：fsync(fd) 或 fdatasync(fd)
```

#### 1.4 close() 系统调用

```c
// close 原型
int close(int fd);
// 返回值：成功返回 0，失败返回 -1
```

**SRE 关键知识 - 进程持有文件描述符的问题**：
```
当进程持有文件描述符时，rm 删除文件会发生什么？

1. rm 命令调用 unlink() 系统调用
2. unlink() 将文件从目录中移除（dentry 删除）
3. 文件的 inode 链接计数减 1
4. 如果链接计数为 0，且没有进程持有该文件：
   → 文件数据被标记为可回收
   → 磁盘空间被释放
5. 如果链接计数为 0，但有进程持有文件描述符：
   → 文件数据不会被释放！
   → 磁盘空间不会被回收！
   → 进程仍然可以读写该文件！
   → 只有进程关闭文件描述符后，空间才会释放

这就是为什么 rm 删除日志文件后，磁盘空间没有释放的原因！
```

**排查已删除但未释放的文件**：
```bash
# 方法1：lsof 查找
lsof +L1 | sort -k7 -rn | head -10
# 输出示例：
# COMMAND   PID   USER   FD   TYPE   DEVICE SIZE/OFF NLINK  NAME
# nginx     1234  root   5w   REG    8,1    1073741824  0    /var/log/nginx/access.log (deleted)

# 方法2：find 查找
find /proc/*/fd -lname '*(deleted)*' -ls 2>/dev/null

# 解决方法：
# 方法1：重启进程（最简单）
systemctl restart nginx

# 方法2：截断文件描述符（不重启进程）
echo > /proc/1234/fd/5

# 方法3：使用 truncate 截断
truncate -s 0 /proc/1234/fd/5

# 方法4：使用 gdb（最危险，不推荐）
gdb -p 1234 -ex "call close(5)" -ex quit
```

#### 1.5 unlink() 和 rename() 系统调用

```c
// unlink - 删除文件
int unlink(const char *pathname);
// 将文件从目录中移除
// 如果文件的链接计数变为 0，且没有进程持有，释放数据

// rename - 重命名/移动文件
int rename(const char *oldpath, const char *newpath);
// 原子操作
// 如果 newpath 存在，会被覆盖
```

**mv 命令的内部机制**：
```
mv old_file new_file 的内部流程：

情况1：同文件系统内移动
├── 调用 rename("old_file", "new_file")
├── 仅修改目录项（dentry），不移动数据
└── 操作瞬间完成（O(1)）

情况2：跨文件系统移动
├── 调用 open("old_file") + read() + write("new_file")
├── 复制所有数据
├── 设置新文件权限
├── 调用 unlink("old_file")
└── 操作时间与文件大小成正比（O(n)）

这就是为什么跨文件系统 mv 大文件很慢的原因！
```

#### 1.6 cp 命令的内部机制

```
cp src_file dst_file 的内部流程：

1. open("src_file", O_RDONLY)
2. open("dst_file", O_WRONLY | O_CREAT | O_TRUNC, 0644)
3. 循环：
   read(src_fd, buf, 4096)
   write(dst_fd, buf, bytes_read)
4. 复制文件元数据（权限、时间戳等）
5. close(src_fd)
6. close(dst_fd)

cp 常用选项的系统调用差异：
-a (archive)  → 保留所有属性（权限、所有者、时间戳）
-p (preserve) → 保留权限和时间戳
-r (recursive) → 递归复制目录
-u (update)   → 只复制更新的文件
-l (link)     → 创建硬链接而不是复制
-s (symbolic) → 创建软链接而不是复制
```

**SRE 实用知识**：
```bash
# 复制时保留所有属性
cp -a /etc/nginx /backup/nginx_backup

# 使用 rsync 代替 cp（更安全，支持断点续传）
rsync -av --progress /data/src/ /data/dst/

# 大文件复制时显示进度
rsync -av --progress --info=progress2 large_file /backup/

# 复制目录时排除某些文件
rsync -av --exclude='*.log' --exclude='.git' /src/ /dst/

# 使用 tar 保持权限复制
tar -cf - /source | tar -xf - -C /destination

# 使用 dd 复制（适合磁盘级别复制）
dd if=/dev/sda of=/dev/sdb bs=4M status=progress
```

---

### 2. find 命令深入

find 是 SRE 最强大的文件查找工具，但很多人只用到了它的皮毛。

#### 2.1 find 的执行原理

```
find 命令的工作流程：

find /path -name "*.log" -mtime -7

1. 从 /path 开始遍历目录树
2. 对每个文件/目录：
   ├── 检查是否匹配 -name "*.log"
   ├── 检查是否匹配 -mtime -7
   ├── 如果所有条件都匹配，输出文件路径
   └── 如果是目录，递归进入
3. 遍历方式：深度优先（DFS）

性能关键点：
- find 会遍历所有文件，包括挂载的网络文件系统
- 使用 -xdev 限制在同一文件系统内
- 使用 -prune 排除不需要的目录
- 使用 -maxdepth 限制搜索深度
```

#### 2.2 find 条件详解

```bash
# ===== 按名称查找 =====
find / -name "*.conf"                    # 精确匹配（区分大小写）
find / -iname "*.conf"                   # 不区分大小写
find / -name "nginx*"                    # 通配符匹配
find / -regex ".*\.\(conf\|cfg\)"        # 正则匹配

# ===== 按类型查找 =====
find / -type f                           # 普通文件
find / -type d                           # 目录
find / -type l                           # 符号链接
find / -type b                           # 块设备
find / -type c                           # 字符设备
find / -type s                           # 套接字
find / -type p                           # 命名管道

# ===== 按时间查找 =====
find / -mtime -7                         # 7 天内修改过的文件
find / -mtime +30                        # 30 天前修改过的文件
find / -mmin -30                         # 30 分钟内修改过的文件
find / -atime -1                         # 1 天内访问过的文件
find / -ctime -7                         # 7 天内状态改变的文件（权限、所有权）

# 时间参数详解：
# -mtime -7  = 修改时间在 7 天前到现在之间
# -mtime 7   = 修改时间恰好在 7 天前（第 7 天到第 8 天之间）
# -mtime +7  = 修改时间在 8 天前或更早

# ===== 按大小查找 =====
find / -size +100M                       # 大于 100MB
find / -size -1M                         # 小于 1MB
find / -size 0                           # 空文件
find / -size +1G                         # 大于 1GB

# ===== 按权限查找 =====
find / -perm 777                         # 精确匹配 777
find / -perm -644                        # 至少有 644 权限
find / -perm /666                        # 任意匹配（owner/group/other 有写权限）

# 权限查找的区别：
# -perm 777  = 权限必须是 777
# -perm -644 = 权限必须包含 644（可以更多）
# -perm /666 = 权限中任意一位匹配（更宽松）

# ===== 按所有者查找 =====
find / -user nginx                       # 属于 nginx 用户
find / -group www-data                   # 属于 www-data 组
find / -nouser                           # 没有有效用户的文件
find / -nogroup                          # 没有有效用户组的文件

# ===== 逻辑运算 =====
find / -name "*.log" -a -size +100M      # AND（默认）
find / -name "*.log" -o -name "*.txt"    # OR
find / -not -name "*.log"                # NOT
find / ! -name "*.log"                   # NOT（另一种写法）
find / \( -name "*.log" -o -name "*.txt" \) -size +100M  # 组合条件
```

#### 2.3 find -exec 与 xargs

```bash
# ===== -exec 用法 =====
# 基本语法
find /path -name "*.log" -exec command {} \;
# {} = 匹配到的文件名
# \; = 命令结束（每个文件执行一次命令）

# 批量执行（更高效）
find /path -name "*.log" -exec command {} +
# + = 将多个文件名作为参数传给一次命令

# 实际案例
# 删除 7 天前的日志
find /var/log -name "*.log" -mtime +7 -exec rm {} +

# 修改权限
find /var/www -type f -exec chmod 644 {} +
find /var/www -type d -exec chmod 755 {} +

# 复制文件
find /src -name "*.conf" -exec cp {} /dst/ \;

# 搜索文件内容
find /etc -name "*.conf" -exec grep -l "nginx" {} +

# ===== xargs 用法 =====
# 基本用法
find /var/log -name "*.log" | xargs rm

# 处理带空格的文件名
find /var/log -name "*.log" -print0 | xargs -0 rm

# -print0 和 -0 配合使用，以 null 字符分隔
# 这样可以正确处理文件名中的空格、引号等特殊字符

# 并行执行
find /src -name "*.txt" | xargs -P 4 -I {} cp {} /dst/
# -P 4 = 最多 4 个并行进程
# -I {} = 用 {} 作为占位符

# 限制每次传递的参数数量
find /src -name "*.txt" | xargs -n 10 command
# 每次传递 10 个文件名
```

#### 2.4 -exec vs xargs 性能对比

```
性能对比：

find /path -name "*.log" -exec rm {} \;
├── 每找到一个文件，fork 一个新进程执行 rm
├── 如果找到 10000 个文件，fork 10000 次
└── 性能：非常慢

find /path -name "*.log" -exec rm {} +
├── 将多个文件名作为参数传给一次 rm 命令
├── 如果找到 10000 个文件，可能只需要几次 fork
└── 性能：快

find /path -name "*.log" | xargs rm
├── xargs 会将输入合并成尽可能长的命令行
├── 如果找到 10000 个文件，可能只需要几次 fork
└── 性能：快

find /path -name "*.log" | xargs -P 4 rm
├── 4 个并行进程同时执行
└── 性能：最快（在多核 CPU 上）
```

#### 2.5 -prune 排除目录

```bash
# 排除特定目录
find / -path /proc -prune -o -path /sys -prune -o -name "*.log" -print
# /proc 和 /sys 目录不会被搜索

# 排除多个目录
find / \( -path /proc -o -path /sys -o -path /dev \) -prune \
    -o -name "*.conf" -print

# 排除 .git 目录
find /src -path "*/.git" -prune -o -type f -name "*.py" -print

# 排除多个目录并执行操作
find / \( -path /proc -o -path /sys -o -path /tmp \) -prune \
    -o -type f -name "*.log" -mtime +30 -print

# -prune 的工作原理：
# 1. find 遍历到 /proc 目录
# 2. -path /proc 匹配成功
# 3. -prune 告诉 find 不要进入该目录
# 4. 继续遍历其他目录
```

#### 2.6 find 性能优化

```bash
# 1. 限制搜索深度
find / -maxdepth 3 -name "*.conf"    # 最多搜索 3 层
find / -mindepth 2 -name "*.conf"    # 至少搜索 2 层

# 2. 限制在同一文件系统
find / -xdev -name "*.log"
# 不会搜索挂载的网络文件系统

# 3. 先过滤再执行
# 差：find / -exec command {} \;
# 好：find / -name "*.log" -exec command {} +

# 4. 使用 -delete 代替 -exec rm
find /tmp -name "*.tmp" -mtime +7 -delete
# 比 -exec rm {} + 更快（避免 fork）

# 5. 使用 locate 代替 find（如果只需要文件名）
# locate 使用预建的数据库，速度非常快
# 但数据库可能不是最新的
locate nginx.conf
updatedb                        # 更新 locate 数据库

# 6. 避免搜索大目录
find / -path /proc -prune -o \
       -path /sys -prune -o \
       -path /dev -prune -o \
       -name "*.log" -print
```

#### 2.7 find 高级用法

```bash
# 查找并统计文件大小
find /var/log -name "*.log" -type f -printf '%s %p\n' | sort -rn | head -10

# -printf 格式化输出
# %s = 文件大小（字节）
# %p = 文件路径
# %u = 所有者
# %g = 所属组
# %m = 权限（八进制）
# %t = 修改时间
# %T+ = 修改时间（格式化）

# 查找重复文件（基于 MD5）
find /data -type f -exec md5sum {} + | sort | uniq -d -w 32

# 查找最近修改的配置文件
find /etc -name "*.conf" -mtime -1 -printf '%T+ %p\n' | sort -r

# 查找大目录（目录下文件总大小）
find / -type d -exec du -sh {} + 2>/dev/null | sort -rh | head -20

# 查找空文件和空目录
find /tmp -type f -empty
find /tmp -type d -empty

# 查找 SUID/SGID 文件（安全审计）
find / -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null

# 查找全局可写的文件（安全审计）
find / -type f -perm -0002 ! -path "/proc/*" ! -path "/sys/*" -ls 2>/dev/null

# 查找没有所有者的文件
find / -nouser -o -nogroup 2>/dev/null

# 查找符号链接目标
find / -type l -exec ls -la {} + 2>/dev/null | grep -v "proc\|sys"

# 查找断链
find / -type l ! -exec test -e {} \; -print 2>/dev/null
```

---

### 3. 文件删除的安全实践

#### 3.1 rm 命令的危险性

```
rm 命令的危险场景：

1. rm -rf /                    # 删除整个系统
2. rm -rf /tmp/*               # 如果 /tmp/* 为空，展开为 /tmp/*
3. rm -rf ./*~                 # 文件名以 ~ 开头可能被展开
4. rm -rf "$VAR"/*             # 如果 $VAR 为空，变成 rm -rf /*
5. rm -rf /var/log/*.log       # 通配符展开可能匹配到意料之外的文件

安全原则：
1. 永远不要直接使用 rm -rf /
2. 删除前先用 ls 预览
3. 使用 rm -i（交互模式）
4. 使用 trash-cli 代替 rm
5. 使用 safe-rm 保护重要目录
```

#### 3.2 trash-cli 使用

```bash
# 安装 trash-cli
apt install trash-cli        # Debian/Ubuntu
dnf install trash-cli        # RHEL/Rocky

# 常用命令
trash-put file.txt           # 移到回收站
trash-list                   # 列出回收站内容
trash-restore                # 恢复文件
trash-empty                  # 清空回收站
trash-rm file.txt            # 从回收站删除

# 替换 rm 命令
alias rm='trash-put'
# 添加到 ~/.bashrc 使其永久生效

# 查看回收站位置
ls ~/.local/share/Trash/
# files/    - 被删除的文件
# info/     - 删除信息（路径、时间）
```

#### 3.3 safe-rm 保护重要目录

```bash
# 安装 safe-rm
apt install safe-rm

# safe-rm 会检查 /etc/safe-rm.conf 中定义的保护路径
# 如果试图删除受保护的路径，会拒绝执行

# 配置保护路径
cat > /etc/safe-rm.conf << 'EOF'
/
/bin
/boot
/etc
/home
/lib
/lib64
/opt
/proc
/root
/run
/sbin
/srv
/sys
/tmp
/usr
/var
/bin/bash
/bin/sh
/etc/passwd
/etc/shadow
/etc/ssh
/etc/nginx
/var/log
EOF

# 测试
rm -rf /etc/nginx
# safe-rm: skipping /etc/nginx
```

#### 3.4 rm 别名最佳实践

```bash
# 在 ~/.bashrc 中添加以下别名

# 交互式删除（每次删除都确认）
alias rm='rm -i'

# 或者使用 trash-cli
alias rm='trash-put'

# 或者使用 safe-rm（推荐）
# 安装 safe-rm 后，rm 会自动被 safe-rm 替代

# 显示删除的文件
alias rm='rm -v'

# 强制删除时不提示（用于脚本中）
# 使用 /bin/rm 绕过别名
/bin/rm -f file.txt
```

---

### 4. 大文件处理

#### 4.1 split - 分割大文件

```bash
# 基本用法
split -b 100M large_file.tar.gz part_
# 将 large_file.tar.gz 分割成 100MB 的小文件
# 生成 part_aa, part_ab, part_ac, ...

# 按行数分割
split -l 10000 large_file.txt part_
# 每 10000 行一个文件

# 指定后缀长度
split -b 100M -d -a 3 large_file.tar.gz part_
# -d = 使用数字后缀
# -a 3 = 后缀长度 3 位
# 生成 part_000, part_001, part_002, ...

# 合并分割的文件
cat part_* > large_file.tar.gz

# 使用数字后缀
split -b 100M -d large_file.tar.gz part_

# 配合管道使用
tar czf - /data | split -b 1G -d - /backup/data_part_
# 直接将 tar 输出分割

# 合并并解压
cat /backup/data_part_* | tar xzf - -C /restore/
```

#### 4.2 dd - 底层数据复制

```bash
# 基本用法
dd if=input_file of=output_file bs=4M count=100
# if = 输入文件
# of = 输出文件
# bs = 块大小
# count = 复制的块数

# 常用场景

# 1. 创建指定大小的文件
dd if=/dev/zero of=test.img bs=1M count=1024
# 创建 1GB 的零填充文件

# 2. 创建随机数据文件
dd if=/dev/urandom of=random.bin bs=1M count=100

# 3. 磁盘镜像备份
dd if=/dev/sda of=/backup/sda.img bs=4M status=progress

# 4. 磁盘镜像恢复
dd if=/backup/sda.img of=/dev/sdb bs=4M status=progress

# 5. 测试磁盘写入速度
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
# oflag=direct 绕过页缓存，直接写入磁盘

# 6. 测试磁盘读取速度
dd if=/dev/sda of=/dev/null bs=1M count=1024 iflag=direct

# 7. 安全擦除磁盘
dd if=/dev/urandom of=/dev/sdb bs=4M status=progress
# 或者使用 shred
shred -vfz -n 3 /dev/sdb

# 8. 转换文件格式
dd if=input.txt of=output.txt conv=ucase    # 转大写
dd if=input.txt of=output.txt conv=lcase    # 转小写
dd if=input.txt of=output.txt conv=swab     # 交换字节序
```

#### 4.3 truncate - 创建稀疏文件

```bash
# 创建指定大小的稀疏文件
truncate -s 10G sparse_file.img
# 创建 10GB 的文件，但实际占用磁盘空间接近 0

# 查看稀疏文件
ls -lh sparse_file.img
# -rw-r--r-- 1 root root 10G ... sparse_file.img

du -h sparse_file.img
# 0       sparse_file.img    # 实际占用 0

# 截断文件（缩小）
truncate -s 100M large_file.txt
# 将文件截断为 100MB

# 扩展文件（用零填充）
truncate -s +100M file.txt
# 文件大小增加 100MB

# 缩小文件
truncate -s -100M file.txt
# 文件大小减少 100MB

# 配合 dd 使用
# 创建 10GB 的测试文件
truncate -s 10G test.img
dd if=/dev/zero of=test.img bs=1M count=1024 conv=notrunc
# conv=notrunc 不截断文件，只覆盖前 1GB
```

#### 4.4 大文件查找和清理

```bash
# 查找大文件（按大小排序）
find / -type f -size +100M -exec ls -lhS {} + 2>/dev/null | sort -k5 -rh | head -20

# 查找并删除大文件
find /tmp -type f -size +1G -delete

# 查找大目录
du -sh /* 2>/dev/null | sort -rh | head -10
du -sh /var/* 2>/dev/null | sort -rh | head -10

# 查找日志文件并按大小排序
find /var/log -type f -name "*.log" -exec ls -lhS {} + | sort -k5 -rh | head -20

# 清理日志文件（不删除，清空内容）
find /var/log -name "*.log" -size +100M -exec truncate -s 0 {} +

# 查找并压缩大日志
find /var/log -name "*.log" -size +50M -exec gzip {} +
```

---

### 5. touch 和 mkdir 命令详解

#### 5.1 touch 命令

```bash
# 基本用法
touch file.txt               # 创建空文件（如果不存在）
touch file.txt               # 更新时间戳（如果存在）

# 只更新访问时间
touch -a file.txt

# 只更新修改时间
touch -m file.txt

# 指定时间
touch -t 202401151200 file.txt    # 2024-01-15 12:00
touch -d "2024-01-15 12:00" file.txt

# 使用参考文件的时间
touch -r reference_file new_file

# 批量创建文件
touch file_{1..100}.txt      # 创建 file_1.txt 到 file_100.txt
touch {a,b,c}.log            # 创建 a.log, b.log, c.log

# 不创建文件，只更新时间戳
touch -c file.txt            # 如果文件不存在，不创建

# SRE 实用场景
# 1. 创建日志文件
touch /var/log/myapp_$(date +%Y%m%d).log

# 2. 更新配置文件时间戳（触发 inotify）
touch /etc/nginx/nginx.conf

# 3. 创建空文件作为标记
touch /tmp/.setup_done
```

#### 5.2 mkdir 命令

```bash
# 基本用法
mkdir dirname                # 创建目录

# 递归创建目录（包括父目录）
mkdir -p /path/to/deep/dir

# 设置权限
mkdir -m 755 dirname         # 创建时设置权限

# 批量创建目录
mkdir -p /data/{web,api,worker}/{logs,config,cache}

# 创建目录结构
mkdir -p /opt/myapp/{bin,conf,log,data,tmp}

# SRE 实用场景
# 1. 创建项目目录结构
mkdir -p /var/www/myapp/{public,logs,config,cache}

# 2. 创建备份目录
mkdir -p /backup/$(date +%Y%m%d)

# 3. 创建多级日志目录
mkdir -p /var/log/myapp/{access,error,debug}
```

---

### 6. SRE 实战：日志清理策略

#### 6.1 日志清理脚本

```bash
#!/bin/bash
# log_cleanup.sh - 日志清理脚本
set -euo pipefail

LOG_DIR="/var/log"
RETENTION_DAYS=30
COMPRESS_DAYS=7

echo "===== 日志清理开始 $(date) ====="

# 1. 压缩 7 天前的日志
echo "压缩旧日志..."
find "$LOG_DIR" -name "*.log" -mtime +$COMPRESS_DAYS -exec gzip {} +

# 2. 删除 30 天前的压缩日志
echo "删除旧压缩日志..."
find "$LOG_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete

# 3. 清理大日志文件（超过 100MB）
echo "清理大日志文件..."
find "$LOG_DIR" -name "*.log" -size +100M -exec truncate -s 0 {} +

# 4. 清理 journal 日志
echo "清理 journal 日志..."
journalctl --vacuum-size=500M
journalctl --vacuum-time=7d

# 5. 清理 apt 缓存
echo "清理包管理器缓存..."
apt clean 2>/dev/null || dnf clean all 2>/dev/null || true

# 6. 清理临时文件
echo "清理临时文件..."
find /tmp -type f -mtime +7 -delete
find /var/tmp -type f -mtime +30 -delete

echo "===== 日志清理完成 ====="
```

#### 6.2 定时任务配置

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 3 点执行日志清理
0 3 * * * /opt/scripts/log_cleanup.sh >> /var/log/cleanup.log 2>&1

# 每周日凌晨 4 点清理 Docker
0 4 * * 0 docker system prune -a -f >> /var/log/docker_cleanup.log 2>&1
```

---

### 7. SRE 实战：临时文件管理

```bash
# 1. 配置 tmpfs 挂载 /tmp
# 在 /etc/fstab 中添加
tmpfs /tmp tmpfs defaults,size=2G,noexec,nosuid 0 0

# 2. 配置 systemd-tmpfiles
cat > /etc/tmpfiles.d/myapp.conf << 'EOF'
# 类型  路径         模式  用户  组  生命周期
d      /tmp/myapp    0755  root  root  7d
e      /tmp/myapp    -     -     -     7d
EOF

# 3. 手动清理临时文件
systemd-tmpfiles --clean

# 4. 查看临时文件配置
systemd-tmpfiles --cat-config
```

---

## 💻 实战练习

### 练习 1：系统调用跟踪

**目标**：使用 strace 跟踪文件操作的系统调用。

```bash
# 1. 跟踪 cp 命令的系统调用
strace -e trace=open,openat,read,write,close cp /etc/hostname /tmp/hostname.bak

# 2. 跟踪 rm 命令
strace rm /tmp/hostname.bak 2>&1 | grep -E "unlink|openat|close"

# 3. 跟踪 find 命令
strace -e trace=openat,getdents,stat find /tmp -name "*.txt" 2>&1 | head -30

# 4. 跟踪 cat 命令
strace cat /etc/hostname 2>&1 | grep -E "open|read|write|close"

# 5. 跟踪 touch 命令
strace touch /tmp/test_touch.txt 2>&1 | grep -E "open|utimensat|close"
```

### 练习 2：find 命令实战

**目标**：使用 find 命令完成各种文件查找任务。

```bash
# 1. 查找系统中所有 .conf 文件
find /etc -name "*.conf" -type f 2>/dev/null | wc -l

# 2. 查找 7 天内修改过的日志文件
find /var/log -name "*.log" -mtime -7 -ls

# 3. 查找大于 100MB 的文件
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null | sort -k5 -rh

# 4. 查找所有 777 权限的文件
find / -type f -perm 777 ! -path "/proc/*" ! -path "/sys/*" -ls 2>/dev/null

# 5. 查找 SUID 文件（安全审计）
find / -type f -perm -4000 -ls 2>/dev/null

# 6. 查找并删除 30 天前的临时文件
find /tmp -type f -mtime +30 -delete

# 7. 查找并打包 7 天前的日志
find /var/log -name "*.log" -mtime +7 -exec tar czf /backup/old_logs.tar.gz {} +

# 8. 查找重复文件
find /data -type f -exec md5sum {} + 2>/dev/null | sort | uniq -d -w 32
```

### 练习 3：大文件处理

**目标**：练习处理大文件的各种技巧。

```bash
# 1. 创建大文件
dd if=/dev/urandom of=/tmp/large_file.bin bs=1M count=500

# 2. 分割大文件
split -b 100M -d /tmp/large_file.bin /tmp/part_

# 3. 验证分割
ls -lh /tmp/part_*

# 4. 合并分割的文件
cat /tmp/part_* > /tmp/restored_file.bin

# 5. 验证文件完整性
md5sum /tmp/large_file.bin /tmp/restored_file.bin

# 6. 清理
rm /tmp/large_file.bin /tmp/part_* /tmp/restored_file.bin
```

---

## 🎯 面试题精选

### 面试题 1：rm -rf 误删文件后如何恢复？

**参考答案**：

**Linux 下 rm 删除的文件很难恢复**，因为：

1. rm 调用 unlink() 系统调用，直接从文件系统移除目录项
2. 不像 Windows 有回收站机制
3. 文件系统不会保留已删除文件的信息

**可能的恢复方法**：

1. **如果有备份**：从备份恢复（最可靠）
2. **如果进程还在运行**：
   ```bash
   # 找到进程持有的文件描述符
   lsof +L1 | grep deleted
   # 从 /proc/<PID>/fd/<FD> 复制
   cp /proc/1234/fd/5 /recovered/file
   ```
3. **使用数据恢复工具**：
   ```bash
   # extundelete（ext4）
   extundelete /dev/sda1 --restore-file /path/to/file
   
   # testdisk（多种文件系统）
   testdisk /dev/sda1
   ```
4. **预防措施**：
   - 使用 trash-cli 替代 rm
   - 使用 safe-rm 保护重要目录
   - 定期备份

### 面试题 2：find 和 locate 有什么区别？

**参考答案**：

| 特性 | find | locate |
|------|------|--------|
| 搜索方式 | 实时遍历文件系统 | 查询预建数据库 |
| 速度 | 慢（遍历磁盘） | 极快（查数据库） |
| 实时性 | 实时结果 | 依赖数据库更新 |
| 条件 | 支持丰富的条件 | 只支持文件名匹配 |
| 资源消耗 | CPU/IO 密集 | 几乎无消耗 |
| 数据库 | 无 | /var/lib/mlocate/mlocate.db |

**使用建议**：
- 查找文件名：`locate`（快速）
- 复杂条件查找：`find`（功能强大）
- 定期更新 locate 数据库：`updatedb`

### 面试题 3：文件被删除但空间没有释放，怎么排查？

**参考答案**：

这是因为进程仍然持有已删除文件的文件描述符。

```bash
# 排查方法
lsof +L1 | sort -k7 -rn | head -10

# 解决方法
# 1. 重启进程
systemctl restart <service>

# 2. 截断文件描述符
echo > /proc/<PID>/fd/<FD>

# 3. 使用 truncate
truncate -s 0 /proc/<PID>/fd/<FD>
```

### 面试题 4：如何查找系统中的大文件？

**参考答案**：

```bash
# 查找大于 100MB 的文件
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null | sort -k5 -rh

# 查找大目录
du -sh /* 2>/dev/null | sort -rh | head -10

# 查找日志文件
find /var/log -name "*.log" -exec ls -lhS {} + | sort -k5 -rh | head -20

# 查找已删除但未释放的文件
lsof +L1 | sort -k7 -rn | head -10
```

### 面试题 5：-exec 和 xargs 有什么区别？什么时候用哪个？

**参考答案**：

| 特性 | -exec | xargs |
|------|-------|-------|
| 参数传递 | 每个文件一次（\;）或批量（+） | 批量传递 |
| 特殊字符 | 安全处理 | 需要 -print0/-0 |
| 并行执行 | 不支持 | 支持 (-P) |
| 性能 | 较慢（\;）或较快（+） | 快 |
| 灵活性 | 可以在命令中使用 {} | 需要 -I {} |

**使用建议**：
- 简单操作：`find ... -exec command {} +`
- 需要并行：`find ... -print0 | xargs -0 -P 4 command`
- 文件名有特殊字符：`find ... -print0 | xargs -0 command`

### 面试题 6：如何安全地删除大量文件？

**参考答案**：

```bash
# 方法1：rsync 清空（最快）
mkdir /tmp/empty
rsync -a --delete /tmp/empty/ /target/dir/

# 方法2：find + delete
find /target/dir -type f -delete

# 方法3：find + xargs
find /target/dir -type f -print0 | xargs -0 rm -f

# 方法4：Perl
perl -e 'use File::Path; rmtree("/target/dir")'
```

### 面试题 7：mv 和 cp 的系统调用有什么区别？

**参考答案**：

**mv（同文件系统）**：
- 调用 rename() 系统调用
- 只修改目录项，不移动数据
- O(1) 操作，瞬间完成

**mv（跨文件系统）**：
- 调用 open() + read() + write() + unlink()
- 复制所有数据到新位置
- 删除原文件
- O(n) 操作，与文件大小成正比

**cp**：
- 调用 open() + read() + write()
- 复制所有数据
- O(n) 操作，与文件大小成正比

---

## 📚 深入阅读

### 官方文档
- [GNU Coreutils - cp/mv/rm](https://www.gnu.org/software/coreutils/manual/)
- [GNU Findutils - find](https://www.gnu.org/software/findutils/manual/)
- [Linux Man Pages](https://man7.org/linux/man-pages/)
- [trash-cli GitHub](https://github.com/andreafrancia/trash-cli)

### 推荐书籍
- 《UNIX 环境高级编程》(APUE) - 文件 I/O 章节
- 《Linux 命令行与 Shell 脚本编程大全》- 文件操作章节
- 《鸟哥的 Linux 私房菜》- 文件与目录管理

### 技术博客
- [Brendan Gregg - Linux Performance](http://www.brendangregg.com/linuxperf.html)
- [The Art of Command Line](https://jvns.ca/blog/2022/04/12/a-list-of-new-ish--command-line-tools/)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 open/read/write/close 系统调用的工作原理
- [ ] 能说明 unlink() 删除文件的机制
- [ ] 能解释 mv 在同文件系统和跨文件系统时的区别
- [ ] 能解释 cp 命令的内部流程
- [ ] 能说明 find 命令的执行原理和性能优化
- [ ] 能区分 -exec {} \; 和 -exec {} + 的区别
- [ ] 能解释为什么删除文件后空间未释放
- [ ] 能说明硬链接和软链接在 inode 层面的区别

### 实操检查点
- [ ] 能使用 strace 跟踪文件操作的系统调用
- [ ] 能使用 find 完成各种复杂的文件查找任务
- [ ] 能使用 -prune 排除不需要的目录
- [ ] 能使用 split/dd/truncate 处理大文件
- [ ] 能配置 trash-cli 和 safe-rm 保护重要文件
- [ ] 能编写日志清理脚本
- [ ] 能排查已删除但未释放的文件
- [ ] 能使用 xargs 并行处理文件

---

*Day 03 完成 | 2026-04-25*
