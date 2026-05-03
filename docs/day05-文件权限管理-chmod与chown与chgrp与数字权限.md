# Day 05: 文件权限管理 -- chmod/chown/chgrp 与数字权限

> 📅 日期：2026-04-26
> 📖 学习主题：文件权限管理 -- chmod/chown/chgrp 与数字权限
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 01-04（Linux 基础、文件系统、文件操作、文本处理）

## 🎯 学习目标

完成 Day 05 的学习后，你应该能够：
- 深入理解 Linux 权限模型（rwx 在文件和目录上的本质区别）
- 掌握特殊权限 SUID/SGID/Sticky Bit 的工作原理与安全影响
- 熟练使用 ACL（setfacl/getfacl）进行精细化权限控制
- 理解 umask 的计算方法并能正确设置默认权限
- 独立排查生产环境中的权限问题（Nginx 403、SSH 密钥、共享目录）

---

## 📖 核心知识点

### 1. Linux 权限模型深入

#### 1.1 权限的三要素

Linux 权限围绕三个主体和三种权限展开：

```
文件权限位:  - rwx r-x r--
             │  │   │   │
             │  │   │   └── 其他人 (Others)
             │  │   └────── 所属组 (Group)
             │  └────────── 所有者 (Owner)
             └───────────── 文件类型 (- 普通文件, d 目录, l 链接, c 字符设备, b 块设备)
```

每个文件在 inode 中存储以下权限相关信息：

| 字段 | 含义 | 示例 |
|------|------|------|
| st_uid | 所有者 UID | 1000 |
| st_gid | 所属组 GID | 1000 |
| st_mode | 权限位 | 0100755（八进制） |

#### 1.2 rwx 在文件与目录上的本质区别

这是 Linux 权限中最容易混淆的概念。同一个权限位在文件和目录上的含义完全不同：

```
┌─────────┬──────────────────────┬─────────────────────────────────┐
│  权限位  │       对文件          │         对目录                   │
├─────────┼──────────────────────┼─────────────────────────────────┤
│  r (4)  │ 读取文件内容          │ 列出目录内容（ls）               │
│         │ cat/head/tail/less   │ 只能看文件名，不能看属性          │
├─────────┼──────────────────────┼─────────────────────────────────┤
│  w (2)  │ 修改文件内容          │ 在目录中创建/删除/重命名文件      │
│         │ vim/echo >> / truncate│ 注意：删除文件取决于目录的 w 权限 │
│         │                      │ 而非文件本身的 w 权限             │
├─────────┼──────────────────────┼─────────────────────────────────┤
│  x (1)  │ 执行文件（程序/脚本） │ 进入目录（cd）                   │
│         │ 需要同时有 r 权限     │ 是目录遍历的基础权限              │
│         │ 才能运行脚本          │ 没有 x 权限，即使有 r 也无法访问  │
└─────────┴──────────────────────┴─────────────────────────────────┘
```

**关键理解 -- 目录的 x 权限是"门"**：

```bash
# 目录权限实验
mkdir /tmp/test_perm
touch /tmp/test_perm/secret.txt
chmod 700 /tmp/test_perm          # rwx------

# 有 x 权限时：可以进入目录并访问文件
ls -la /tmp/test_perm/            # 可以列出
cat /tmp/test_perm/secret.txt     # 可以读取

# 去掉 x 权限，只保留 r
chmod 400 /tmp/test_perm          # r--------
ls /tmp/test_perm/                # 可以列出文件名
cat /tmp/test_perm/secret.txt     # Permission denied! 无法访问

# 去掉 r 权限，只保留 x
chmod 100 /tmp/test_perm          # --x------
ls /tmp/test_perm/                # Permission denied! 无法列出
cat /tmp/test_perm/secret.txt     # 如果知道文件名，可以读取！

# 没有任何权限
chmod 000 /tmp/test_perm          # ---------
ls /tmp/test_perm/                # Permission denied
cat /tmp/test_perm/secret.txt     # Permission denied
```

**实战要点**：目录的 x 权限是路径遍历的基础。要访问 `/a/b/c.txt`，用户对 `/a`、`/b` 都必须有 x 权限。这就是为什么 `namei` 命令在排查权限问题时非常有用。

#### 1.3 权限检查的内核流程

当用户尝试访问文件时，内核按以下顺序检查：

```
用户发起访问请求
       │
       ▼
   是 root 用户？ ──是──▶ 通常直接放行（跳过权限检查）
       │                        │
       否                       │ 例外：某些系统调用（如 access()）
       ▼                        │ 仍会检查，用于 setuid 程序
  检查文件 st_uid               │
  与进程 euid 比较              │
       │
  匹配？──是──▶ 使用 Owner 权限（前三位）
       │
       否
       ▼
  检查进程所属组
  是否包含文件 st_gid
       │
  匹配？──是──▶ 使用 Group 权限（中间三位）
       │
       否
       ▼
  使用 Others 权限（后三位）
```

**重要**：内核只检查第一组匹配的权限，不会累加。如果用户是文件所有者，即使 Group 和 Others 权限更宽松，也只按 Owner 权限判断。

#### 1.4 八进制权限表示法详解

权限用 4 位八进制数表示（如 `0755`），但通常只写后 3 位：

```
第 4 位（特殊权限）  第 3 位（Owner）  第 2 位（Group）  第 1 位（Others）
    SUID/SGID/SBit     rwx               rwx              rwx
      0-7               0-7               0-7              0-7

常见组合速查：
  755 = rwxr-xr-x  → 程序/脚本/Web 目录
  644 = rw-r--r--  → 配置文件/普通文件
  700 = rwx------  → 私人目录
  600 = rw-------  → 敏感文件（SSH 私钥）
  400 = r--------  → 只读私钥
  1777 = rwxrwxrwt → /tmp 目录（Sticky Bit）
  4755 = rwsr-xr-x → SUID 程序
  2755 = rwxr-sr-x → SGID 目录
```

#### 1.5 符号模式详解

chmod 的符号模式比数字模式更灵活：

```bash
# 语法格式
chmod [ugoa][+-=][rwxXst] file...

# u = owner, g = group, o = others, a = all（默认）
# + = 添加权限, - = 移除权限, = = 精确设置
# X = 只对目录或已有执行权限的文件添加 x
# s = SUID/SGID, t = Sticky Bit

# 实用示例
chmod u+x script.sh          # 只给所有者添加执行权限
chmod go-w file.txt           # 移除组和其他人的写权限
chmod a+r file.txt            # 所有人添加读权限
chmod u=rw,go=r file.txt      # 精确设置
chmod -R g+rwX /project/      # 递归：目录加 rwx，文件加 rw
chmod ug+s shared_script      # 设置 SUID + SGID
```

---

### 2. chown 与 chgrp

#### 2.1 chown 命令

```bash
# 基本语法
chown [OPTION]... [OWNER][:[GROUP]] FILE...

# 常用选项
chown nginx file.txt              # 只改所有者
chown nginx:nginx file.txt        # 改所有者和组
chown :nginx file.txt             # 只改组
chown -R www-data:www-data /var/www/  # 递归修改

# 参照其他文件
chown --reference=source.txt target.txt

# 只在文件属于特定用户时才修改（配合 find）
find /var/www -user old_owner -exec chown new_owner {} +
```

#### 2.2 chgrp 命令

```bash
# chgrp 等价于 chown :group
chgrp developers /project/
chgrp -R developers /project/     # 递归

# 普通用户只能 chgrp 到自己所属的其他组
# root 可以 chgrp 到任意组
```

#### 2.3 内核系统调用

```bash
# 权限相关的系统调用
chmod(path, mode)       # 修改文件权限
fchmod(fd, mode)        # 通过文件描述符修改权限
lchmod(path, mode)      # 修改符号链接权限（不跟随链接）
chown(path, uid, gid)   # 修改所有者和组
fchown(fd, uid, gid)    # 通过文件描述符修改
lchown(path, uid, gid)  # 修改符号链接所有者
access(path, mode)      # 检查进程是否有访问权限

# access() 的陷阱
# setuid 程序中使用 access() 检查的是真实 UID，不是有效 UID
# 这是一个安全特性，防止 setuid 程序被利用
```

---

### 3. 特殊权限 -- SUID/SGID/Sticky Bit

Linux 除了基本的 rwx 权限外，还有三个特殊权限位，它们在安全和协作场景中扮演重要角色。

#### 3.1 SUID (Set User ID) -- 数值 4000

**原理**：当一个可执行文件设置了 SUID 位，任何用户执行该文件时，进程的有效 UID（euid）将变为文件所有者的 UID，而不是执行者的 UID。

```
普通执行：                          SUID 执行：
用户 alice (uid=1000)               用户 alice (uid=1000)
    │                                   │
    ▼                                   ▼
执行 /usr/bin/program               执行 /usr/bin/passwd
    │                                   │
    ▼                                   ▼
进程 euid = 1000 (alice)            进程 euid = 0 (root)
    │                                   │
    ▼                                   ▼
只能访问 alice 的文件               可以访问 /etc/shadow
```

**passwd 为什么需要 SUID**：

```bash
$ ls -l /usr/bin/passwd
-rwsr-xr-x 1 root root 68208 Mar 23  2023 /usr/bin/passwd

$ ls -l /etc/shadow
-rw-r----- 1 root shadow 1234 Jan  1 00:00 /etc/shadow

# 普通用户需要修改自己的密码
# 密码存储在 /etc/shadow（只有 root 和 shadow 组可读写）
# 所以 passwd 必须以 root 身份运行才能修改 shadow 文件
# 但 passwd 程序内部会做安全检查：用户只能修改自己的密码
```

**SUID 的安全风险**：

```bash
# 危险示例 1：对 vim 设置 SUID
# 任何用户都可以用 vim 编辑任意文件！
sudo chmod u+s /usr/bin/vim
# 攻击者可以直接 vim /etc/shadow 修改密码

# 危险示例 2：对 shell 设置 SUID
sudo chmod u+s /bin/bash
# 任何用户执行 bash 就能获得 root shell！
bash -p   # -p 保持特权

# 危险示例 3：对 cp 设置 SUID
sudo chmod u+s /bin/cp
# 攻击者可以覆盖任何文件
cp /dev/null /etc/shadow   # 清空密码文件！

# 安全审计：查找系统中所有 SUID 文件
find / -type f -perm /4000 -ls 2>/dev/null

# 典型的合法 SUID 文件：
# /usr/bin/passwd      - 修改密码
# /usr/bin/sudo        - 执行特权命令
# /usr/bin/su          - 切换用户
# /usr/bin/ping        - 发送 ICMP（需要 raw socket）
# /usr/bin/mount       - 挂载文件系统
# /usr/bin/chsh        - 更改 shell
# /usr/bin/newgrp      - 切换主组
```

**SUID 在脚本上无效**：

```bash
# 重要：SUID 对 shell 脚本不起作用！
# 内核在 exec 脚本时会忽略 SUID 位（安全原因）
# 如果需要脚本以 root 运行，使用 sudo 或 capabilities

chmod u+s my_script.sh    # 无效！脚本仍以当前用户身份运行

# 正确做法：使用 sudo
echo "user ALL=(ALL) NOPASSWD: /path/to/my_script.sh" | sudo tee /etc/sudoers.d/my_script
```

#### 3.2 SGID (Set Group ID) -- 数值 2000

SGID 在文件和目录上有不同的行为：

**对文件**：类似 SUID，但以文件所属组的身份运行。

```bash
# 查看 SGID 文件
ls -l /usr/bin/wall
# -rwxr-sr-x 1 root tty ... /usr/bin/wall
#              ^ s = SGID
# wall 以 tty 组身份运行，可以写入其他用户的终端
```

**对目录（更重要）**：新创建的文件自动继承目录的组，而不是创建者的主组。

```bash
# 场景：开发团队共享目录
sudo groupadd devteam
sudo mkdir /project
sudo chown :devteam /project
sudo chmod 2775 /project    # 2 = SGID, 775 = rwxrwxr-x

# 验证效果
ls -ld /project
# drwxrwsr-x 2 root devteam 4096 ... /project
#            ^ s = SGID

# 用户 alice 创建文件
su - alice -c "touch /project/newfile.txt"
ls -l /project/newfile.txt
# -rw-rw-r-- 1 alice devteam ... newfile.txt
#                  ^ devteam！不是 alice 的主组

# 没有 SGID 时
sudo chmod 0775 /project    # 去掉 SGID
su - alice -c "touch /project/another.txt"
ls -l /project/another.txt
# -rw-rw-r-- 1 alice alice ... another.txt
#                  ^ alice 的主组
```

**SGID 的实际应用场景**：

```bash
# 场景 1：Web 服务器共享目录
# 所有开发者都能部署文件，nginx 需要读取
sudo groupadd webdev
sudo mkdir -p /var/www/shared
sudo chown :webdev /var/www/shared
sudo chmod 2775 /var/www/shared
sudo setfacl -m d:g:webdev:rwx /var/www/shared   # 默认 ACL

# 场景 2：FTP/SFTP 上传目录
sudo groupadd ftpusers
sudo mkdir -p /srv/ftp/upload
sudo chown :ftpusers /srv/ftp/upload
sudo chmod 2770 /srv/ftp/upload
```

#### 3.3 Sticky Bit -- 数值 1000

**原理**：对目录设置 Sticky Bit 后，该目录中的文件只有文件所有者、目录所有者或 root 才能删除，即使其他人有写权限。

```bash
# /tmp 是最典型的 Sticky Bit 目录
ls -ld /tmp
# drwxrwxrwt 15 root root 4096 ... /tmp
#            ^ t = Sticky Bit

# 实验：没有 Sticky Bit 的危险
mkdir /tmp/nosticky
chmod 777 /tmp/nosticky

# 用户 alice 创建文件
su - alice -c "echo secret > /tmp/nosticky/alice_file.txt"

# 用户 bob 可以删除 alice 的文件！（因为 bob 对目录有 w 权限）
su - bob -c "rm /tmp/nosticky/alice_file.txt"   # 成功删除！

# 有 Sticky Bit 时
chmod 1777 /tmp/withsticky

# 用户 alice 创建文件
su - alice -c "echo secret > /tmp/withsticky/alice_file.txt"

# 用户 bob 无法删除 alice 的文件
su - bob -c "rm /tmp/withsticky/alice_file.txt"
# rm: cannot remove 'alice_file.txt': Operation not permitted
```

#### 3.4 特殊权限的数字表示总结

```
┌──────────────────────────────────────────────────┐
│  四位八进制权限表示                                │
│                                                  │
│  第一位：特殊权限     后三位：基本权限             │
│                                                  │
│  4 = SUID           7 = rwx                      │
│  2 = SGID           6 = rw-                      │
│  1 = Sticky Bit     5 = r-x                      │
│  0 = 无特殊权限      4 = r--                      │
│                      3 = -wx                      │
│  组合：               2 = -w-                      │
│  4+2 = 6 (SUID+SGID) 1 = --x                     │
│  4+1 = 5 (SUID+Sticky) 0 = ---                   │
│  2+1 = 3 (SGID+Sticky)                           │
│  4+2+1 = 7 (全部)                                 │
│                                                  │
│  常见组合：                                       │
│  4755 = rwsr-xr-x   SUID 程序                    │
│  2755 = rwxr-sr-x   SGID 目录/文件               │
│  1777 = rwxrwxrwt   共享可写目录（如 /tmp）       │
│  3777 = rwxrwxrwt   SGID + Sticky（共享上传目录） │
│  7755 = rwsr-sr-t   极少见，全部特殊权限          │
└──────────────────────────────────────────────────┘
```

#### 3.5 特殊权限的符号设置

```bash
# SUID
chmod u+s file       # 添加
chmod u-s file       # 移除
chmod 4755 file      # 数字方式

# SGID
chmod g+s dir/       # 添加
chmod g-s dir/       # 移除
chmod 2755 dir/      # 数字方式

# Sticky Bit
chmod +t dir/        # 添加
chmod -t dir/        # 移除
chmod 1777 dir/      # 数字方式

# 查看特殊权限
ls -la               # SUID: s/S, SGID: s/S, Sticky: t/T
# 大写 S/T 表示对应的 x 位未设置（可能有问题）
# 小写 s/t 表示对应的 x 位已设置（正常）
```

**大小写 s/t 的区别**：

```bash
# 小写 s：SUID + x 位都设置了（正常）
chmod 4755 file
ls -l file
# -rwsr-xr-x  # s = SUID + x

# 大写 S：只有 SUID，没有 x 位（异常/危险）
chmod 4644 file
ls -l file
# -rwSr--r--  # S = SUID 但没有 x，可能无法执行

# 同理，大写 T 表示 Sticky Bit 但没有 x 位
chmod 1666 dir/
ls -ld dir/
# drw-rw-rwT   # T = Sticky 但没有 x
```

---

### 4. ACL -- 访问控制列表

#### 4.1 为什么需要 ACL

传统 Unix 权限只能为三类用户（owner/group/others）设置权限，无法满足复杂需求：

```
场景：项目目录需要
  - owner (alice): rwx
  - group (devteam): rwx
  - bob (特定用户，不在 devteam): r-x    ← 传统权限做不到！
  - 其他人: ---

传统权限无法为"特定用户"单独设置权限
ACL 可以为任意用户/组单独授权
```

#### 4.2 ACL 条目类型

```
┌──────────────────────────────────────────────────────┐
│  ACL 条目类型                                         │
├────────────┬─────────────────────────────────────────┤
│  类型       │  说明                                   │
├────────────┼─────────────────────────────────────────┤
│ user::rwx  │  文件所有者权限（等同传统 owner 权限）    │
│ user:bob:r-x│  特定用户 bob 的权限                    │
│ group::r-x │  文件所属组权限（等同传统 group 权限）    │
│ group:dev:rwx│ 特定组 dev 的权限                      │
│ mask::rwx  │  ACL 权限掩码（限制所有 ACL 用户和组）    │
│ other::r-- │  其他人权限（等同传统 others 权限）       │
└────────────┴─────────────────────────────────────────┘
```

#### 4.3 getfacl -- 查看 ACL

```bash
getfacl /path/to/file

# 输出示例：
# file: project/data.csv
# owner: alice
# group: devteam
user::rw-
user:bob:r-x
group::rwx
group:qa:r--
mask::rwx
other::---

# 注意：mask 显示的是有效权限上限
# 如果 mask::r--，即使 user:bob:r-x，bob 实际也只有 r-- 权限
```

#### 4.4 setfacl -- 设置 ACL

```bash
# 基本语法
setfacl [选项] u:[用户]:[权限] 文件    # 用户 ACL
setfacl [选项] g:[组]:[权限] 文件      # 组 ACL

# 常用选项
-m    # 修改 ACL
-x    # 删除特定 ACL 条目
-b    # 删除所有 ACL
-R    # 递归
-d    # 设置默认 ACL（只对目录有意义）
-k    # 删除默认 ACL

# 示例 1：给特定用户设置权限
setfacl -m u:bob:r-x /project/
getfacl /project/
# user::rwx
# user:bob:r-x     ← 新增
# group::r-x
# mask::r-x        ← mask 自动更新
# other::---

# 示例 2：给特定组设置权限
setfacl -m g:qa:rx /project/

# 示例 3：删除特定 ACL 条目
setfacl -x u:bob /project/

# 示例 4：清除所有 ACL
setfacl -b /project/

# 示例 5：递归设置
setfacl -R -m u:bob:rx /project/
```

#### 4.5 默认 ACL（Default ACL）

默认 ACL 只能设置在目录上，新创建的文件/子目录会自动继承默认 ACL：

```bash
# 设置默认 ACL
setfacl -d -m u:bob:rx /project/
setfacl -d -m g:qa:rw /project/

# 查看默认 ACL
getfacl /project/
# file: project/
# owner: root
# group: devteam
user::rwx
group::r-x
other::---
default:user::rwx
default:user:bob:r-x      ← 默认 ACL
default:group::r-x
default:group:qa:rw       ← 默认 ACL
default:mask::rwx
default:other::---

# 新文件自动继承默认 ACL
touch /project/newfile.txt
getfacl /project/newfile.txt
# user::rw-
# user:bob:r-x          ← 继承自目录的默认 ACL
# group::r-x
# group:qa:rw           ← 继承自目录的默认 ACL
# mask::rw-
# other::---
```

#### 4.6 ACL Mask

mask 是 ACL 的权限上限，它限制了所有命名用户（named user）、命名组（named group）和所属组的有效权限：

```bash
# 设置 mask
setfacl -m m::rx /project/

# 查看效果
getfacl /project/
# user:bob:rwx         # 声明的权限
# mask::r-x            # mask 限制
# effective:r-x        # bob 的实际有效权限

# mask 的计算规则
# effective = declared AND mask
# 即：声明的权限 和 mask 取交集
#
# user:bob:rwx (111)
# mask::r-x   (101)
# AND 结果    (101) = r-x
#
# 所以 bob 实际只有 r-x 权限

# 注意：chmod 会同时修改 ACL mask！
chmod g=rx /project/   # 这会把 mask 也设为 r-x
```

#### 4.7 ACL 与传统权限的关系

```
┌───────────────────────────────────────────────────────┐
│  ls -l 显示中的 ACL 标记                               │
│                                                       │
│  -rw-rwxr--+ 1 bob devteam ... file.txt               │
│              ^                                        │
│              + 表示文件有 ACL                          │
│              . 表示文件有 SELinux 安全上下文            │
│                                                       │
│  注意：mask 位替代了传统的 group 位在 ls 中的显示       │
│  ls 显示的 group 权限实际上是 mask（如果有 ACL）       │
└───────────────────────────────────────────────────────┘
```

#### 4.8 ACL 实战场景

**场景 1：Web 服务器需要读取用户目录的文件**

```bash
# 问题：nginx 需要读取 /home/alice/web/ 下的文件
# 但不能把 alice 的目录设为 755（太宽松）

# 方案：使用 ACL 精确授权
setfacl -m u:www-data:rx /home/alice/
setfacl -m u:www-data:rx /home/alice/web/
setfacl -R -m u:www-data:rx /home/alice/web/

# 设置默认 ACL（新文件自动授权）
setfacl -d -m u:www-data:rx /home/alice/web/

# 验证
namei -l /home/alice/web/index.html   # 检查路径上每级权限
getfacl /home/alice/web/index.html    # 确认 ACL
sudo -u www-data cat /home/alice/web/index.html  # 实际测试
```

**场景 2：多团队共享项目目录**

```bash
# 需求：
# - devteam 组：完全控制（rwx）
# - qateam 组：只读（rx）
# - ops 组：完全控制（rwx）
# - auditor 用户：只读（r）

sudo mkdir /opt/project-alpha
sudo chown :devteam /opt/project-alpha
sudo chmod 2770 /opt/project-alpha    # SGID + owner/group rwx

# 设置 ACL
sudo setfacl -m g:qateam:rx /opt/project-alpha
sudo setfacl -m g:ops:rwx /opt/project-alpha
sudo setfacl -m u:auditor:r /opt/project-alpha

# 设置默认 ACL（新建文件自动继承）
sudo setfacl -d -m g:devteam:rwx /opt/project-alpha
sudo setfacl -d -m g:qateam:rx /opt/project-alpha
sudo setfacl -d -m g:ops:rwx /opt/project-alpha
sudo setfacl -d -m u:auditor:r /opt/project-alpha

# 验证
getfacl /opt/project-alpha
```

**场景 3：备份和恢复 ACL**

```bash
# 备份 ACL
getfacl -R /project/ > /backup/project.acl

# 恢复 ACL
setfacl --restore=/backup/project.acl

# 备份单个文件的 ACL
getfacl file.txt > file.txt.acl

# 注意：tar 命令默认不保存 ACL，需要使用 --acls 选项
tar --acls -czf backup.tar.gz /project/
tar --acls -xzf backup.tar.gz
```

---

### 5. umask -- 默认权限控制

#### 5.1 umask 的工作原理

umask 定义了新创建文件/目录时要"遮罩"（去掉）的权限位：

```
umask 计算公式：
  文件默认权限 = 0666 - umask
  目录默认权限 = 0777 - umask

注意：这不是简单的减法，而是位运算（AND NOT）
  文件权限 = 0666 & ~umask
  目录权限 = 0777 & ~umask
```

```
┌─────────────────────────────────────────────────────────────┐
│  umask 权限计算表                                           │
├─────────┬──────────────┬──────────────┬─────────────────────┤
│  umask  │  文件权限     │  目录权限     │  典型场景            │
├─────────┼──────────────┼──────────────┼─────────────────────┤
│  0000   │  rw-rw-rw-   │  rwxrwxrwx   │  极度不安全          │
│  0002   │  rw-rw-r--   │  rwxrwxr-x   │  Ubuntu/RHEL 默认   │
│  0022   │  rw-r--r--   │  rwxr-xr-x   │  root 默认           │
│  0027   │  rw-r-----   │  rwxr-x---   │  严格安全环境         │
│  0077   │  rw-------   │  rwx------   │  最高安全级别         │
│  0007   │  rw-rw----   │  rwxrwx---   │  组内共享             │
└─────────┴──────────────┴──────────────┴─────────────────────┘
```

#### 5.2 umask 的位运算详解

```bash
# 以 umask 0022 为例
# 文件默认权限计算：
#   起始权限:  0666 = 110 110 110（二进制）
#   umask:     0022 = 000 010 010（二进制）
#   取反:           = 111 101 101
#   AND 结果:        = 110 100 100 = 644 = rw-r--r--

# 目录默认权限计算：
#   起始权限:  0777 = 111 111 111
#   umask:     0022 = 000 010 010
#   取反:           = 111 101 101
#   AND 结果:        = 111 101 101 = 755 = rwxr-xr-x

# 注意：umask 不会影响已有文件的权限
# umask 只影响 open()、creat()、mkdir() 等创建操作
```

#### 5.3 查看和设置 umask

```bash
# 查看当前 umask（符号模式，更易读）
umask -S
# u=rwx,g=rx,o=rx

# 查看八进制
umask
# 0022

# 临时设置 umask（仅当前 shell 会话有效）
umask 0027

# 永久设置 umask
# 方法 1：用户级别（~/.bashrc 或 ~/.profile）
echo "umask 0027" >> ~/.bashrc

# 方法 2：系统级别（/etc/profile 或 /etc/login.defs）
# /etc/login.defs 中的 UMASK 设置
UMASK 027

# 方法 3：PAM 模块（/etc/pam.d/common-session）
# session optional pam_umask.so umask=0027
```

#### 5.4 umask 的常见误区

```bash
# 误区 1：umask 0666 会让文件权限为 0000
# 实际上：0666 & ~0666 = 0000，但文件至少保留执行位
# 真实情况：文件默认 0666，umask 只能去掉已有的位

# 误区 2：umask 是减法
# umask 0033 时：
#   文件：0666 & ~0033 = 0666 & 0744 = 0644 (rw-r--r--)
#   而不是 0666 - 0033 = 0633

# 误区 3：umask 影响 chmod
# umask 只影响新创建文件的默认权限
# chmod 显式设置的权限不受 umask 影响
umask 0077
touch newfile.txt    # 权限为 0600 (rw-------)
chmod 755 newfile.txt # 权限变为 0755，umask 不影响
```

#### 5.5 安全场景下的 umask 配置

```bash
# 场景 1：开发服务器（宽松，方便协作）
umask 0002    # 文件 664，目录 775
# 同组用户可以互相读写

# 场景 2：生产服务器（标准安全）
umask 0022    # 文件 644，目录 755
# 只有 owner 可以写

# 场景 3：安全敏感服务器（严格）
umask 0077    # 文件 600，目录 700
# 只有 owner 可以访问

# 场景 4：多用户共享服务器
umask 0027    # 文件 640，目录 750
# 同组可以读，其他人无权限

# SRE 最佳实践：生产服务器 umask 0027
# 在 /etc/profile.d/ 下创建自定义文件
cat > /etc/profile.d/umask.sh << 'EOF'
# 生产环境 umask 设置
if [ "$(id -u)" -gt 0 ]; then
    umask 0027    # 普通用户
else
    umask 0022    # root
fi
EOF
```

---

### 6. 权限相关的系统调用

#### 6.1 文件访问权限检查流程

```c
// 内核中的权限检查伪代码（fs/namei.c）
int inode_permission(struct inode *inode, int mask) {
    // 1. 如果是 root，检查是否有 CAP_DAC_OVERRIDE
    //    如果有，直接放行

    // 2. 如果进程的 euid == inode->i_uid（所有者）
    //    使用 owner 权限位检查

    // 3. 如果进程的 egid == inode->i_gid 或者
    //    进程属于文件的附加组
    //    使用 group 权限位检查

    // 4. 使用 others 权限位检查

    // 5. 如果有 ACL，检查 ACL 条目

    // 6. 检查结果返回 0（允许）或 -EACCES（拒绝）
}
```

#### 6.2 access() 系统调用

```bash
# access() 检查真实 UID/GID 的权限，而不是有效 UID/GID
# 这对 setuid 程序非常重要

# C 语言示例
# if (access("/etc/shadow", R_OK) == 0) {
#     // 真实用户有读权限
#     // 注意：这不是检查 euid，而是 ruid
# }

# 在 setuid 程序中：
# - ruid = 调用者的真实 UID
# - euid = 文件所有者的 UID（如 root）
# access() 用 ruid 检查，防止 setuid 程序被利用

# Shell 中的 test 命令使用 access()
[ -r /etc/shadow ] && echo "readable"   # 检查真实用户权限
```

#### 6.3 实用的权限检查命令

```bash
# namei：检查路径上每一级的权限
namei -l /var/www/html/index.html
# f: /var/www/html/index.html
# drwxr-xr-x root    root    /
# drwxr-xr-x root    root    var
# drwxr-xr-x root    root    www
# drwxr-xr-x www-data www-data html
# -rw-r--r-- www-data www-data index.html

# 查看文件的 ACL
getfacl /path/to/file

# 检查 SELinux 上下文
ls -Z /path/to/file
getenforce

# stat 命令查看详细信息
stat /etc/passwd
# Access: (0644/-rw-r--r--)  Uid: (    0/    root)   Gid: (    0/    root)
```

---

### 7. SRE 实战案例

#### 7.1 案例一：Nginx 403 Forbidden 排查

这是 SRE 最常遇到的权限问题之一。完整的排查链路：

```
用户访问网站 → 403 Forbidden
       │
       ▼
  1. 检查 Nginx 错误日志
       │  tail -20 /var/log/nginx/error.log
       │
       ├── "Permission denied" → 文件/目录权限问题
       │        │
       │        ▼
       │   2. 检查文件权限
       │      ls -la /var/www/html/index.html
       │      应该是 644，owner 是 www-data
       │        │
       │        ▼
       │   3. 检查目录权限（逐级检查）
       │      namei -l /var/www/html/index.html
       │      每级目录都需要 x 权限
       │        │
       │        ▼
       │   4. 检查 nginx.conf 的 user 指令
       │      grep user /etc/nginx/nginx.conf
       │      确保运行用户与文件 owner 匹配
       │
       ├── "open() failed (13: Permission denied)" → 可能是 SELinux
       │        │
       │        ▼
       │   5. 检查 SELinux 状态
       │      getenforce
       │      ls -Z /var/www/html/
       │        │
       │        ▼
       │   6. 修复 SELinux 上下文
       │      semanage fcontext -a -t httpd_sys_content_t "/var/www/html(/.*)?"
       │      restorecon -Rv /var/www/html
       │
       └── "directory index of ... is forbidden" → 缺少 index 文件
                │
                ▼
           7. 检查 autoindex 或 index 配置
              grep -r "autoindex\|index" /etc/nginx/
```

**完整排查脚本**：

```bash
#!/bin/bash
# nginx_403_troubleshoot.sh
# 排查 Nginx 403 Forbidden 的完整脚本

WEBROOT="/var/www/html"
NGINX_USER=$(grep -E "^user" /etc/nginx/nginx.conf | awk '{print $2}' | tr -d ';')
echo "Nginx 运行用户: $NGINX_USER"
echo ""

# 1. 检查文件权限
echo "=== 文件权限检查 ==="
ls -la "$WEBROOT/"
echo ""

# 2. 逐级检查路径权限
echo "=== 路径权限检查 ==="
namei -l "$WEBROOT/index.html"
echo ""

# 3. 检查 SELinux
echo "=== SELinux 检查 ==="
if command -v getenforce &>/dev/null; then
    echo "SELinux 状态: $(getenforce)"
    ls -Z "$WEBROOT/"
else
    echo "SELinux 未安装"
fi
echo ""

# 4. 检查 AppArmor
echo "=== AppArmor 检查 ==="
if command -v aa-status &>/dev/null; then
    sudo aa-status 2>/dev/null | grep -i nginx
else
    echo "AppArmor 未安装"
fi
echo ""

# 5. 检查 Nginx 错误日志
echo "=== 最近的错误日志 ==="
tail -20 /var/log/nginx/error.log
echo ""

# 6. 修复建议
echo "=== 修复建议 ==="
echo "1. chown -R $NGINX_USER:$NGINX_USER $WEBROOT/"
echo "2. find $WEBROOT -type f -exec chmod 644 {} +"
echo "3. find $WEBROOT -type d -exec chmod 755 {} +"
echo "4. 如果是 SELinux: restorecon -Rv $WEBROOT/"
```

#### 7.2 案例二：SSH 密钥权限要求

SSH 对密钥文件的权限要求非常严格，不满足就会拒绝使用：

```
SSH 密钥权限要求：
┌─────────────────────────────────────────────────────┐
│  文件/目录              │  必须权限  │  原因          │
├─────────────────────────┼──────────┼────────────────┤
│  ~/.ssh/               │  700      │  只有 owner     │
│  ~/.ssh/authorized_keys│  600      │  防止篡改       │
│  ~/.ssh/id_rsa         │  600      │  私钥保密       │
│  ~/.ssh/id_rsa.pub     │  644      │  公钥可公开     │
│  ~/.ssh/config         │  600      │  防止泄露配置   │
│  ~/.ssh/known_hosts    │  644      │  可共享         │
├─────────────────────────┼──────────┼────────────────┤
│  /home/用户/           │  755      │  不能组可写     │
└─────────────────────────┴──────────┴────────────────┘
```

**常见 SSH 密钥权限问题**：

```bash
# 错误信息 1：UNPROTECTED PRIVATE KEY FILE!
# 原因：私钥权限太宽松
chmod 600 ~/.ssh/id_rsa

# 错误信息 2：Authentication refused
# 原因：authorized_keys 权限不对，或父目录权限太宽松
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# 错误信息 3：Bad owner or modes
# 原因：~/.ssh/ 目录权限不对
chmod 700 ~/.ssh

# 排查 SSH 权限问题
ssh -vvv user@host    # 详细调试输出

# 批量检查所有用户的 SSH 权限
for home_dir in /home/*/; do
    username=$(basename "$home_dir")
    ssh_dir="$home_dir.ssh"
    if [ -d "$ssh_dir" ]; then
        perm=$(stat -c %a "$ssh_dir")
        [ "$perm" != "700" ] && echo "WARN: $ssh_dir 权限为 $perm (应为 700)"

        auth_file="$ssh_dir/authorized_keys"
        if [ -f "$auth_file" ]; then
            perm=$(stat -c %a "$auth_file")
            [ "$perm" != "600" ] && echo "WARN: $auth_file 权限为 $perm (应为 600)"
        fi
    fi
done
```

#### 7.3 案例三：共享目录权限设计

**场景**：开发团队需要一个共享目录，要求：
- 所有开发者可以读写
- 部署用户可以读写
- nginx 用户只读
- 其他人无权限
- 新文件自动继承组权限

```bash
# 1. 创建用户和组
sudo groupadd devteam
sudo useradd -m -G devteam alice
sudo useradd -m -G devteam bob
sudo useradd -m -G devteam deploy
sudo useradd -r -s /sbin/nologin nginx

# 2. 创建共享目录
sudo mkdir -p /opt/shared
sudo chown :devteam /opt/shared
sudo chmod 2770 /opt/shared    # SGID + owner/group rwx

# 3. 给 nginx 只读 ACL
sudo setfacl -m u:nginx:rx /opt/shared

# 4. 设置默认 ACL（新文件自动继承）
sudo setfacl -d -m g:devteam:rw /opt/shared
sudo setfacl -d -m u:nginx:r /opt/shared

# 5. 验证
getfacl /opt/shared

# 6. 测试
su - alice -c "echo 'hello' > /opt/shared/test.txt"
ls -l /opt/shared/test.txt
# -rw-rw-r-- 1 alice devteam ... test.txt
# SGID 生效：组是 devteam，不是 alice

su - nginx -c "cat /opt/shared/test.txt"   # 可以读
su - nginx -c "echo 'hack' >> /opt/shared/test.txt"  # Permission denied
```

---

### 8. 权限安全最佳实践

#### 8.1 最小权限原则

```
┌──────────────────────────────────────────────────────────────┐
│  SRE 权限安全检查清单                                        │
├──────────────────────────────────────────────────────────────┤
│  [ ] 生产服务器 umask 设置为 0027                            │
│  [ ] SSH 密钥权限 600，SSH 目录权限 700                       │
│  [ ] 敏感配置文件（密码、密钥）权限 600                       │
│  [ ] Web 目录权限 755（目录）/ 644（文件）                    │
│  [ ] 定期审计 SUID/SGID 文件                                │
│  [ ] 不使用 777 权限，使用 ACL 或 SGID 代替                  │
│  [ ] /tmp 使用 Sticky Bit (1777)                             │
│  [ ] 关键目录使用 ACL 而非放宽传统权限                        │
│  [ ] 定期检查 world-writable 文件                            │
│  [ ] SELinux/AppArmor 保持 enforcing 模式                    │
└──────────────────────────────────────────────────────────────┘
```

#### 8.2 常用权限审计命令

```bash
# 查找全局可写的文件（安全隐患）
find / -type f -perm -o+w -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# 查找全局可写的目录（没有 Sticky Bit）
find / -type d -perm -o+w -not -perm -1000 \
  -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# 查找 SUID 文件
find / -type f -perm /4000 -ls 2>/dev/null

# 查找 SGID 文件
find / -type f -perm /2000 -ls 2>/dev/null

# 查找没有属主的文件（可能表示用户已被删除）
find / -nouser -o -nogroup 2>/dev/null

# 查找 ACL 文件
find / -maxdepth 3 -exec getfacl -s {} + 2>/dev/null | grep -v "^#"

# 统计不同权限的文件数
find /var/www -type f -exec stat -c '%a' {} + 2>/dev/null | sort | uniq -c | sort -rn
```

---

## 💻 实战练习

### 练习 1：权限计算

计算以下 umask 和 chmod 组合的最终权限：

```
问题 1：umask 为 0027 时，新创建的文件默认权限是什么？
问题 2：umask 为 0027 时，新创建的目录默认权限是什么？
问题 3：chmod 4755 设置的完整权限是什么？
问题 4：chmod 2750 设置的完整权限是什么？
问题 5：chmod 1777 设置的完整权限是什么？
```

<details>
<summary>答案</summary>

```
问题 1：0666 & ~0027 = 0666 & 0750 = 0640 (rw-r-----)
问题 2：0777 & ~0027 = 0777 & 0750 = 0750 (rwxr-x---)
问题 3：4755 = rwsr-xr-x（SUID + 755）
问题 4：2750 = rwxr-s---（SGID + 750）
问题 5：1777 = rwxrwxrwt（Sticky Bit + 777）
```
</details>

### 练习 2：权限排查

用户报告无法通过 SSH 密钥登录服务器。编写一个排查脚本，检查所有可能导致问题的权限因素。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# ssh_permission_check.sh

USERNAME=${1:?用法: $0 <用户名>}
HOME_DIR=$(eval echo ~$USERNAME)

echo "=== SSH 权限排查: $USERNAME ==="

# 1. 检查用户是否存在
id "$USERNAME" &>/dev/null || { echo "ERROR: 用户不存在"; exit 1; }

# 2. 检查 home 目录权限
home_perm=$(stat -c %a "$HOME_DIR")
echo "Home 目录 $HOME_DIR: $home_perm"
[[ "$home_perm" -gt 755 ]] && echo "  WARN: home 目录权限过宽"

# 3. 检查 .ssh 目录
ssh_dir="$HOME_DIR/.ssh"
if [ -d "$ssh_dir" ]; then
    perm=$(stat -c %a "$ssh_dir")
    echo ".ssh 目录: $perm"
    [[ "$perm" != "700" ]] && echo "  ERROR: 应为 700"

    # 4. 检查 authorized_keys
    auth="$ssh_dir/authorized_keys"
    if [ -f "$auth" ]; then
        perm=$(stat -c %a "$auth")
        echo "authorized_keys: $perm"
        [[ "$perm" != "600" ]] && echo "  ERROR: 应为 600"
        key_count=$(wc -l < "$auth")
        echo "  已配置 $key_count 个公钥"
    else
        echo "  ERROR: authorized_keys 不存在"
    fi

    # 5. 检查私钥权限
    for key in "$ssh_dir"/id_*; do
        [ -f "$key" ] || continue
        [[ "$key" == *.pub ]] && continue
        perm=$(stat -c %a "$key")
        echo "私钥 $key: $perm"
        [[ "$perm" != "600" ]] && echo "  ERROR: 私钥应为 600"
    done
else
    echo "ERROR: .ssh 目录不存在"
fi

# 6. 检查 sshd 配置
echo ""
echo "=== sshd 配置 ==="
grep -E "^(PubkeyAuthentication|PasswordAuthentication|PermitRootLogin)" /etc/ssh/sshd_config

# 7. 检查账户是否锁定
echo ""
echo "=== 账户状态 ==="
passwd -S "$USERNAME"

# 8. 检查 fail2ban
if command -v fail2ban-client &>/dev/null; then
    echo ""
    echo "=== fail2ban 状态 ==="
    sudo fail2ban-client status sshd 2>/dev/null
fi
```
</details>

### 练习 3：共享目录设计

设计一个满足以下需求的共享目录权限方案：
- 项目目录 `/opt/projectx`
- `devteam` 组完全控制
- `qateam` 组只读
- `nginx` 用户只读
- 新文件自动继承权限
- 任何人都不能删除其他人的文件

<details>
<summary>参考答案</summary>

```bash
# 1. 创建组和目录
sudo groupadd devteam
sudo groupadd qateam
sudo mkdir -p /opt/projectx

# 2. 基本权限（SGID + Sticky Bit + 组权限）
sudo chown :devteam /opt/projectx
sudo chmod 3770 /opt/projectx
# 3 = SGID(2) + Sticky(1)
# 7 = owner rwx
# 7 = group rwx (devteam)
# 0 = others ---

# 3. ACL 设置
sudo setfacl -m g:qateam:rx /opt/projectx
sudo setfacl -m u:nginx:rx /opt/projectx

# 4. 默认 ACL（新文件自动继承）
sudo setfacl -d -m g:devteam:rw /opt/projectx
sudo setfacl -d -m g:qateam:r /opt/projectx
sudo setfacl -d -m u:nginx:r /opt/projectx

# 5. 验证
echo "=== 目录权限 ==="
ls -ld /opt/projectx
echo ""
echo "=== ACL ==="
getfacl /opt/projectx

# 测试 Sticky Bit
su - alice -c "touch /opt/projectx/alice.txt"
su - bob -c "rm /opt/projectx/alice.txt"    # Operation not permitted
```
</details>

---

## 🎯 面试题精选

### 面试题 1：chmod 7500 的含义是什么？

**参考答案**：
7500 = 7000 + 500
- 第一位 7 = SUID(4) + SGID(2) + Sticky(1)
- 第二位 5 = r-x（owner 可读可执行，不可写）
- 第三位 0 = ---（group 无权限）
- 第四位 0 = ---（others 无权限）

所以权限是：`r-sr-S--T`（或显示为 `rwsr-s--T`），但实际上这种组合很少使用。owner 有 SUID 和执行，group 有 SGID 但无执行（显示大写 S），others 有 Sticky Bit 但无执行（显示大写 T）。

### 面试题 2：为什么删除一个文件不需要文件的写权限？

**参考答案**：
删除文件操作实际上修改的是**目录**的内容（目录中的条目），而不是文件本身。目录本质上是一个包含文件名到 inode 映射的特殊文件。删除文件 = 从目录中移除一个条目，所以需要目录的**写权限（w）**，而不是文件的写权限。

这也是为什么 Sticky Bit 对目录有意义：设置 Sticky Bit 后，即使用户对目录有 w 权限，也只能删除自己拥有的文件。

### 面试题 3：SUID 的安全风险有哪些？如何缓解？

**参考答案**：

**安全风险**：
1. SUID 程序以文件所有者（通常是 root）身份运行，如果程序有漏洞，攻击者可以提升权限
2. 对 shell/编辑器等通用工具设置 SUID 会导致任意命令执行
3. 攻击者可能利用 SUID 程序写入任意文件

**缓解措施**：
1. 最小化 SUID 程序数量，定期审计 `find / -perm /4000`
2. 使用 Linux Capabilities 替代 SUID（如 `cap_net_raw` 替代 ping 的 SUID）
3. 使用 sudo 替代 SUID，提供更细粒度的控制和日志审计
4. 对 SUID 程序进行安全审计和定期更新
5. 使用 nosuid 挂载选项限制不可信分区上的 SUID

### 面试题 4：ACL 的 mask 有什么作用？

**参考答案**：
ACL mask 定义了所有命名用户（named user）、命名组（named group）和文件所属组的有效权限上限。即使某个 ACL 条目声明了更宽松的权限，实际有效权限 = 声明权限 AND mask。

mask 的重要特性：
- `chmod` 修改 group 权限时会同时修改 mask
- mask 保护了权限不会因为个别 ACL 条目设置过大而失控
- `ls -l` 显示的 group 权限实际上是 mask（当有 ACL 时）

### 面试题 5：umask 0022 和 umask 0027 有什么区别？

**参考答案**：
| umask | 文件权限 | 目录权限 | 安全级别 |
|-------|---------|---------|---------|
| 0022 | 644 (rw-r--r--) | 755 (rwxr-xr-x) | 标准（同组和其他人可读） |
| 0027 | 640 (rw-r-----) | 750 (rwxr-x---) | 严格（其他人无任何权限） |

0027 比 0022 更安全，因为去掉了 other 的所有权限（27 中的 7 = rwx）。在生产环境中推荐使用 0027。

### 面试题 6：如何排查 Nginx 403 Forbidden？

**参考答案**：
排查步骤（按优先级）：
1. 查看 Nginx 错误日志：`tail /var/log/nginx/error.log`
2. 检查文件权限：`ls -la` 确保 nginx 用户有 r 权限
3. 检查目录权限：`namei -l` 确保路径上每级目录都有 x 权限
4. 检查 SELinux：`getenforce`，如果是 enforcing，检查上下文 `ls -Z`
5. 检查 nginx.conf 的 user 指令
6. 检查是否有 index 文件或 autoindex 配置

### 面试题 7：SGID 对目录的作用是什么？

**参考答案**：
对目录设置 SGID 后，该目录中新创建的文件和子目录会自动继承目录的**组**，而不是创建者的主组。

这对于团队共享目录非常重要：无论哪个用户创建文件，文件的组都会是目录的组，从而确保团队成员都能访问。

示例：`/shared` 目录属于 `devteam` 组，设置了 SGID。即使用户 alice（主组是 alice）在其中创建文件，文件的组也会是 `devteam`。

---

## 📚 深入阅读

### 官方文档
- [Linux man page: chmod(2)](https://man7.org/linux/man-pages/man2/chmod.2.html)
- [Linux man page: acl(5)](https://man7.org/linux/man-pages/man5/acl.5.html)
- [Linux man page: umask(2)](https://man7.org/linux/man-pages/man2/umask.2.html)
- [Red Hat: Managing File Permissions](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_file_systems/assembly_using-file-systems_managing-file-systems)

### 推荐书籍
- 《鸟哥的 Linux 私房菜》第 6 章 -- Linux 文件权限
- 《Linux 系统管理与网络管理》-- 权限管理章节
- 《How Linux Works》第 3 章 -- 文件与权限

### 在线资源
- [Explain Shell](https://explainshell.com/) -- 输入命令逐段解释
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) -- 通过游戏学习 Linux 权限
- [Linux Permissions Calculator](https://chmod-calculator.com/) -- 在线权限计算器

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 rwx 在文件和目录上的区别
- [ ] 理解 SUID/SGID/Sticky Bit 的工作原理和安全影响
- [ ] 知道 ACL 各条目类型的含义（user/group/mask/default）
- [ ] 理解 umask 的位运算原理
- [ ] 知道为什么删除文件不需要文件的写权限
- [ ] 理解权限检查的内核流程

### 实操检查点
- [ ] 能用 chmod 的符号和数字两种模式设置权限
- [ ] 能用 setfacl/getfacl 管理 ACL
- [ ] 能正确设置 umask 并理解其影响
- [ ] 能独立排查 Nginx 403 Forbidden 权限问题
- [ ] 能设计多团队共享目录的权限方案
- [ ] 能编写权限审计脚本
- [ ] 能正确配置 SSH 密钥权限

---

*由 SRE 学习计划生成 | 2026-04-26*
