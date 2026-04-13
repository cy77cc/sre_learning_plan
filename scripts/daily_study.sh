#!/bin/bash
#===========================================
# SRE 每日学习资料自动生成脚本
# 每天 9:00 自动执行
#===========================================

set -e

BASE_DIR="/root/sre_learning"
DOCS_DIR="$BASE_DIR/docs"
START_DATE="2026-04-13"
GIT_EMAIL="hermes@sre-learning.local"
GIT_NAME="Hermes Agent"

# 配置 Git
git config --global user.email "$GIT_EMAIL"
git config --global user.name "$GIT_NAME"
git config --global --add safe.directory "$BASE_DIR"

# 计算当前是第几天
calc_day() {
    local start_ts=$(date -d "$START_DATE" +%s)
    local now_ts=$(date +%s)
    local days=$(( (now_ts - start_ts) / 86400 + 1 ))
    echo $days
}

# 获取当天学习主题
get_topic() {
    local day=$1
    case $day in
        1)  echo "Linux简介与虚拟机安装 - Ubuntu 22.04安装与基础配置" ;;
        2)  echo "Linux文件系统与目录结构 - FHS标准详解" ;;
        3)  echo "Linux文件操作命令 - cp/mv/rm/cat/head/tail" ;;
        4)  echo "文本处理三剑客 - grep/sed/awk与正则表达式" ;;
        5)  echo "文件权限管理 - chmod/chown与数字权限" ;;
        6)  echo "用户与用户组管理 - useradd/usermod/sudo" ;;
        7)  echo "第一周综合复习与实战练习" ;;
        8)  echo "进程管理基础 - ps/top/htop/pstree" ;;
        9)  echo "进程控制 - kill/killall/信号机制" ;;
        10) echo "systemd服务管理 - systemctl/单元文件" ;;
        11) echo "系统监控命令 - uptime/free/df/vmstat/sar" ;;
        12) echo "磁盘管理 - fdisk/mkfs/mount/du/df" ;;
        13) echo "日志管理 - journalctl/rsyslog/日志分析" ;;
        14) echo "第二周综合实战 - LAMP环境搭建" ;;
        15) echo "Shell脚本基础 - 变量/环境变量/引号" ;;
        16) echo "Shell条件判断 - if/elif/else/test运算符" ;;
        17) echo "Shell循环结构 - for/while/until" ;;
        18) echo "Shell函数 - 函数定义/参数传递/返回值" ;;
        19) echo "Case语句与菜单 - select菜单制作" ;;
        20) echo "数组操作 - 数组遍历/关联数组" ;;
        21) echo "字符串处理与正则 - sed/awk进阶" ;;
        22) echo "脚本调试与信号 - trap/set -x/set -e" ;;
        23) echo "expect自动化交互 - SSH自动登录" ;;
        24) echo "实战项目 - 服务器初始化脚本" ;;
        25) echo "实战项目 - 日志监控告警脚本" ;;
        26) echo "实战项目 - 备份脚本编写" ;;
        27) echo "Bash脚本编程进阶 - 高级技巧" ;;
        28) echo "第一阶段总结与测试 - 综合能力评估" ;;
        *)  echo "复习与扩展学习" ;;
    esac
}

# 搜索最新学习资料 (模拟，实际会调用网络搜索)
search_resources() {
    local topic="$1"
    local day=$2
    
    # 返回搜索URL列表（示例）
    cat << 'RESOURCES'
## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/)
- [Linux Journey](https://linuxjourney.com/)
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/)

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜配套视频](https://search.bilibili.com)
- [YouTube: NetworkChuck Linux Basics](https://youtube.com)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/)
- [KodeKloud](https://kodekloud.com)
- [Play with Docker](https://play.docker.com)
RESOURCES
}

# 生成当天学习文档
generate_day_doc() {
    local day=$(calc_day)
    local day_padded=$(printf "%02d" $day)
    local topic=$(get_topic $day)
    local day_dir="$DOCS_DIR/day$day_padded"
    
    mkdir -p "$day_dir"
    
    # 生成文档
    cat > "$day_dir/README.md" << EOF
# Day $day_padded: $topic

> 📅 日期：$(date '+%Y-%m-%d')  
> 📖 学习主题：$topic  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day $day_padded 的学习后，你应该掌握：
- 理解 $topic 的核心概念
- 能够独立完成相关练习
- 为后续学习打下坚实基础

---

## 📖 详细知识点

### 1. 核心概念

（详细知识点内容 - 由脚本自动生成）

### 2. 命令详解

\`\`\`bash
# 示例命令
echo "Hello SRE"
\`\`\`

### 3. 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| 问题1 | 方案1 |
| 问题2 | 方案2 |

---

## 💻 实战练习

### 练习 1：
\`\`\`bash
# 在此完成练习
\`\`\`

### 练习 2：
\`\`\`bash
# 在此完成练习
\`\`\`

---

## 🔗 学习资源

$(search_resources "$topic" $day)

---

## 📝 笔记

（在此记录你的学习笔记）

---

## ✅ 完成检查

- [ ] 理解核心概念
- [ ] 完成所有练习
- [ ] 记录笔记和疑问
- [ ] 延伸阅读至少一篇

---

*由 SRE 学习计划自动生成 | $(date '+%Y-%m-%d %H:%M:%S')*
EOF

    echo "✅ Day $day_padded 文档已生成: $day_dir/README.md"
}

# 推送到 GitHub
push_to_github() {
    cd "$BASE_DIR"
    git add -A
    git commit -m "Day $(printf "%02d" $(calc_day)): $(date '+%Y-%m-%d') update

- Auto-generated study materials
- $(date '+%H:%M:%S')"
    git push origin main
    echo "✅ 已推送到 GitHub"
}

# 发送微信通知
send_notification() {
    local day=$(calc_day)
    local topic=$(get_topic $day)
    local msg="📚 SRE 学习计划

✅ Day $day 学习资料已准备好！

📖 今日主题：$topic

📁 文档位置：$DOCS_DIR/day$(printf "%02d" $day)/README.md

💪 加油！坚持就是胜利！"
    
    # 通过 WeChat 发送（使用 Hermes 的 weixin 工具）
    echo "$msg"
}

# 主流程
main() {
    local day=$(calc_day)
    echo "=========================================="
    echo "📅 SRE 每日学习资料生成"
    echo "=========================================="
    echo "今天是 Day $day"
    echo "主题：$(get_topic $day)"
    echo "=========================================="
    
    generate_day_doc
    push_to_github
    send_notification
    
    echo "=========================================="
    echo "✅ 任务完成！"
    echo "=========================================="
}

main
