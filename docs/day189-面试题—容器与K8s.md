# Day 189: 面试题 — 容器与 Kubernetes（30 道高频题 + 详细解析）

> 📅 日期：2026-05-02
> 📖 学习主题：容器与 Kubernetes 高频面试题
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 70-90（Docker）、Day 90-104（Kubernetes）

---

## 🎯 学习目标

完成 Day 189 的学习后，你应该能够：

- 流利回答 30 道容器与 Kubernetes 高频面试题
- 深入理解容器底层原理（不只是会用）
- 能够设计 Kubernetes 集群架构方案
- 应对 K8s 故障排查和场景题

---

## 📖 核心知识点

### 第一部分：Docker 与容器基础（10 题）

---

#### 题目 1：Docker 和虚拟机有什么区别？

**难度**：⭐⭐⭐

**详细解析**：

```
Docker 容器 vs 虚拟机：

+------------------+-------------------+-------------------+
| 特性              | Docker 容器        | 虚拟机             |
+------------------+-------------------+-------------------+
| 虚拟化层级        | 操作系统级         | 硬件级             |
| 启动时间          | 秒级              | 分钟级             |
| 资源占用          | MB 级             | GB 级             |
| 性能损耗          | 接近原生           | 5-15%             |
| 隔离性            | 进程级隔离         | 完全隔离           |
| 镜像大小          | 通常 < 1GB        | 通常 > 1GB        |
| 运行密度          | 单机可运行数百个   | 单机通常数十个     |
| 操作系统          | 共享宿主机内核     | 独立操作系统       |
+------------------+-------------------+-------------------+

架构对比：

虚拟机：
+----------+  +----------+  +----------+
|  App A   |  |  App B   |  |  App C   |
+----------+  +----------+  +----------+
|  Bins/Libs|  | Bins/Libs|  | Bins/Libs|
+----------+  +----------+  +----------+
| Guest OS  |  | Guest OS |  | Guest OS |
+----------+  +----------+  +----------+
|       Hypervisor (VMware/KVM)         |
+---------------------------------------+
|         Host OS / Hardware            |
+---------------------------------------+

Docker 容器：
+----------+  +----------+  +----------+
|  App A   |  |  App B   |  |  App C   |
+----------+  +----------+  +----------+
|  Bins/Libs|  | Bins/Libs|  | Bins/Libs|
+----------+  +----------+  +----------+
|       Docker Engine                   |
+---------------------------------------+
|         Host OS (Shared Kernel)       |
+---------------------------------------+

关键区别：
1. 容器共享宿主机内核，虚拟机有独立内核
2. 容器使用 Namespace 隔离，虚拟机使用硬件虚拟化
3. 容器使用 cgroup 限制资源，虚拟机在 Hypervisor 层限制
4. 容器更轻量，但隔离性不如虚拟机
```

---

#### 题目 2：Docker 的底层技术是什么？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Docker 底层核心技术：

1. Linux Namespace（资源隔离）
   - PID Namespace：进程隔离
   - Network Namespace：网络隔离
   - Mount Namespace：文件系统隔离
   - UTS Namespace：主机名隔离
   - IPC Namespace：进程间通信隔离
   - User Namespace：用户隔离

2. Linux Cgroup（资源限制）
   - cpu.cfs_quota_us：CPU 时间配额
   - memory.limit_in_bytes：内存限制
   - blkio.throttle.read_bps_device：磁盘读限速
   - pids.max：最大进程数

3. Union FS（联合文件系统）
   - 分层镜像，共享基础层
   - 写时复制（Copy-on-Write）
   - 常见实现：overlay2、aufs

4. 容器运行时（Container Runtime）
   - Docker Engine -> containerd -> runc
   - OCI 标准：开放容器倡议
   - 其他运行时：CRI-O、gVisor、Kata Containers

查看容器的底层信息：
$ docker inspect <container>         # 容器详细信息
$ ls -la /proc/<pid>/ns/             # 查看 Namespace
$ cat /proc/<pid>/cgroup             # 查看 Cgroup
$ docker info                        # Docker 引擎信息
```

---

#### 题目 3：解释 Docker 镜像的分层原理

**难度**：⭐⭐⭐

**详细解析**：

```
Docker 镜像采用分层存储，每一层都是只读的。

分层原理：
+-------------------------------------------+
|  Container Layer (可写层)                  |
+-------------------------------------------+
|  Layer 4: COPY app.py /app/               |
+-------------------------------------------+
|  Layer 3: RUN pip install -r requirements  |
+-------------------------------------------+
|  Layer 2: RUN apt-get update               |
+-------------------------------------------+
|  Layer 1: Ubuntu 22.04 base               |
+-------------------------------------------+

写时复制（Copy-on-Write）：
- 容器启动时，Docker 在镜像层之上添加一个可写层
- 修改文件时，先从只读层复制到可写层，再修改
- 删除文件时，在可写层创建 whiteout 标记

查看镜像层：
$ docker history <image>             # 查看镜像层历史
$ docker inspect <image> | jq '.[0].RootFS.Layers'
$ dive <image>                       # 使用 dive 工具分析镜像层

优化镜像大小的技巧：
1. 合并 RUN 指令（减少层数）
   RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

2. 使用多阶段构建
   FROM golang:1.21 AS builder
   RUN go build -o app .
   FROM alpine:latest
   COPY --from=builder /app /app

3. 使用 .dockerignore 排除不需要的文件
4. 选择合适的基础镜像（alpine vs debian vs distroless）
5. 清理缓存和临时文件

镜像存储驱动：
- overlay2（推荐，性能最好）
- devicemapper（已弃用）
- btrfs / zfs（特殊场景）
```

---

#### 题目 4：Dockerfile 中 CMD 和 ENTRYPOINT 有什么区别？

**难度**：⭐⭐⭐

**详细解析**：

```
CMD 和 ENTRYPOINT 的区别：

CMD：
- 设置容器启动时的默认命令
- 可以被 docker run 的参数覆盖
- 一个 Dockerfile 中只有最后一个 CMD 生效
- 两种格式：shell 格式和 exec 格式

ENTRYPOINT：
- 设置容器的入口点
- 不会被 docker run 的参数覆盖（除非用 --entrypoint）
- 适合设置固定的启动命令
- docker run 的参数会追加到 ENTRYPOINT 后面

组合使用：
ENTRYPOINT ["python"]
CMD ["app.py"]

# docker run myimage           -> python app.py
# docker run myimage test.py   -> python test.py
# docker run myimage --help    -> python --help

常见用法：

# 场景 1：纯 CMD
CMD ["nginx", "-g", "daemon off;"]
# docker run myimage                     -> nginx -g daemon off;
# docker run myimage bash                -> bash (覆盖了 CMD)

# 场景 2：纯 ENTRYPOINT
ENTRYPOINT ["python", "app.py"]
# docker run myimage                     -> python app.py
# docker run myimage --port 8080         -> python app.py --port 8080

# 场景 3：CMD + ENTRYPOINT 组合
ENTRYPOINT ["python"]
CMD ["app.py"]
# docker run myimage                     -> python app.py
# docker run myimage test.py             -> python test.py

# 场景 4：Shell 格式 vs Exec 格式
CMD python app.py            # Shell 格式（不推荐，会被 /bin/sh -c 包装）
CMD ["python", "app.py"]     # Exec 格式（推荐，直接执行）

注意：
- 使用 Exec 格式（JSON 数组），避免 Shell 格式
- Shell 格式不传递信号，导致容器无法优雅关闭
```

---

#### 题目 5：如何优化 Docker 镜像大小？

**难度**：⭐⭐⭐

**详细解析**：

```
优化策略：

1. 选择合适的基础镜像
   - alpine（5MB）vs debian（120MB）vs ubuntu（72MB）
   - distroless（最小化，无 shell）
   - scratch（空镜像，用于静态编译的二进制）

2. 使用多阶段构建
   # 构建阶段
   FROM golang:1.21-alpine AS builder
   WORKDIR /app
   COPY go.mod go.sum ./
   RUN go mod download
   COPY . .
   RUN CGO_ENABLED=0 go build -o app .

   # 运行阶段
   FROM alpine:3.18
   RUN apk --no-cache add ca-certificates
   COPY --from=builder /app/app /app
   CMD ["/app"]

   效果：从 1GB 降到 20MB

3. 合并 RUN 指令
   # 差
   RUN apt-get update
   RUN apt-get install -y curl
   RUN apt-get install -y wget
   RUN rm -rf /var/lib/apt/lists/*

   # 好
   RUN apt-get update && \
       apt-get install -y --no-install-recommends curl wget && \
       rm -rf /var/lib/apt/lists/*

4. 使用 .dockerignore
   .git
   node_modules
   *.md
   .env

5. 清理缓存
   RUN pip install --no-cache-dir -r requirements.txt
   RUN npm ci --production && npm cache clean --force

6. 使用 dive 分析镜像
   $ dive <image>                   # 可视化分析每一层

镜像大小对比：
- Python 官方镜像：~900MB
- Python slim：~150MB
- Python alpine：~50MB
- 多阶段构建 + alpine：~30MB
```

---

#### 题目 6：Docker 网络是怎么实现的？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Docker 网络基于 Linux Network Namespace 和虚拟网络设备。

bridge 网络（默认）实现原理：

  宿主机
  +-------------------------------------------+
  |                                           |
  |  eth0 (宿主机物理网卡)                     |
  |    |                                      |
  |  iptables NAT (端口映射 -p)                |
  |    |                                      |
  |  docker0 (虚拟网桥)                        |
  |    |           |                          |
  |  veth-xxx   veth-yyy                      |
  |    |           |                          |
  |  +------+  +------+                       |
  |  |容器A |  |容器B |                        |
  |  |172.17|  |172.17|                       |
  |  |.0.2  |  |.0.3  |                       |
  |  +------+  +------+                       |
  +-------------------------------------------+

网络通信流程：
1. 容器 A 访问外网：
   容器 A -> veth-xxx -> docker0 -> iptables NAT -> eth0 -> 外网

2. 容器 A 访问容器 B：
   容器 A -> veth-xxx -> docker0 -> veth-yyy -> 容器 B

3. 外部访问容器（端口映射）：
   外部请求 -> eth0 -> iptables DNAT -> docker0 -> veth-xxx -> 容器 A

常用网络操作：
$ docker network ls                  # 列出网络
$ docker network inspect bridge      # 查看网络详情
$ docker network create mynet        # 创建自定义网络
$ docker run --network mynet ...     # 使用自定义网络
$ docker exec <container> ip addr    # 查看容器 IP

自定义 bridge vs 默认 bridge：
- 自定义 bridge 支持自动 DNS 解析（容器名 -> IP）
- 自定义 bridge 可以指定子网和网关
- 生产环境建议使用自定义 bridge
```

---

#### 题目 7：Docker 的存储驱动是什么？overlay2 是如何工作的？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
存储驱动（Storage Driver）负责管理容器的文件系统层。

overlay2 工作原理：

overlay2 使用联合文件系统，将多个目录合并为一个统一的视图。

  lowerdir (只读层，镜像层)
  +------------------+
  | Layer 2: app.py  |
  +------------------+
  | Layer 1: ubuntu  |
  +------------------+
         |
         v
  upperdir (可写层，容器层)
  +------------------+
  | 修改的文件       |
  | 新增的文件       |
  | whiteout 标记    |
  +------------------+
         |
         v
  merged (合并视图，容器看到的文件系统)
  +------------------+
  | 所有层的合并结果  |
  +------------------+

读写操作：
- 读文件：先查 upperdir，没有则查 lowerdir
- 写文件：从 lowerdir 复制到 upperdir（Copy-on-Write），再修改
- 删除文件：在 upperdir 创建 whiteout 字符设备

查看存储驱动：
$ docker info | grep "Storage Driver"
$ docker inspect <container> | jq '.[0].GraphDriver'

overlay2 配置（/etc/docker/daemon.json）：
{
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.size=10G"          # 限制容器可写层大小
    ]
}

其他存储驱动：
- devicemapper：已弃用
- btrfs：适合 Btrfs 文件系统
- zfs：适合 ZFS 文件系统
- vfs：性能差，用于测试

生产建议：
- 使用 overlay2（性能最好，最稳定）
- 使用 SSD 存储
- 定期 docker system prune 清理无用数据
```

---

#### 题目 8：如何实现 Docker 容器的安全隔离？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Docker 容器安全隔离层次：

1. Namespace 隔离
   - PID：容器内看不到宿主机进程
   - Network：独立的网络栈
   - Mount：独立的文件系统
   - User：用户 ID 映射

2. Cgroup 限制
   # 限制 CPU
   $ docker run --cpus="1.5" myimage

   # 限制内存
   $ docker run --memory="512m" --memory-swap="1g" myimage

   # 限制 IO
   $ docker run --device-read-bps /dev/sda:10mb myimage

3. 安全选项
   # 只读文件系统
   $ docker run --read-only myimage

   # 禁用特权模式（不要用 --privileged）
   $ docker run --security-opt=no-new-privileges myimage

   # 使用非 root 用户运行
   USER 1000:1000                   # Dockerfile 中

   # 丢弃所有 capabilities
   $ docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage

   # 使用 seccomp 配置文件
   $ docker run --security-opt seccomp=profile.json myimage

4. 镜像安全扫描
   $ trivy image myimage:latest
   $ docker scan myimage:latest

5. 运行时安全
   # 使用 AppArmor
   $ docker run --security-opt apparmor=my-profile myimage

   # 使用 SELinux
   $ docker run --security-opt label=level:s0:c100,c200 myimage

最佳实践：
- 不要使用 --privileged
- 不要以 root 运行应用
- 使用最小基础镜像
- 定期扫描镜像漏洞
- 使用 Docker Content Trust 签名验证
- 限制容器资源
```

---

#### 题目 9：解释 Docker Compose 的作用和原理

**难度**：⭐⭐

**详细解析**：

```
Docker Compose 是定义和运行多容器应用的工具。

核心概念：
- Service：一个容器的定义
- Network：容器间的网络
- Volume：持久化存储
- Project：一组 service 的集合

docker-compose.yml 示例：
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8080:80"
    depends_on:
      - api
    environment:
      - API_URL=http://api:3000
    networks:
      - frontend

  api:
    image: node:18-alpine
    volumes:
      - ./api:/app
    environment:
      - DB_HOST=postgres
    depends_on:
      - postgres
    networks:
      - frontend
      - backend

  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret
    networks:
      - backend

volumes:
  pgdata:

networks:
  frontend:
  backend:

常用命令：
$ docker-compose up -d               # 启动所有服务
$ docker-compose down                # 停止并删除
$ docker-compose logs -f             # 查看日志
$ docker-compose ps                  # 查看状态
$ docker-compose exec web bash       # 进入容器
$ docker-compose build               # 构建镜像
$ docker-compose up -d --scale api=3 # 扩容服务

Compose 实现原理：
1. 解析 docker-compose.yml
2. 创建默认网络（projectname_default）
3. 创建 volume
4. 按依赖顺序创建并启动容器
5. 设置容器间 DNS 解析

Kubernetes 中的等价物：
- Service -> Kubernetes Service
- depends_on -> Init Container 或 readinessProbe
- volumes -> PersistentVolumeClaim
- networks -> Kubernetes Service + DNS
```

---

#### 题目 10：Docker 容器如何优雅关闭？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
容器关闭流程：

1. docker stop <container>
   - 发送 SIGTERM 信号
   - 等待 10 秒（默认）
   - 如果进程未退出，发送 SIGKILL

2. docker kill <container>
   - 直接发送 SIGKILL
   - 强制杀死进程

优雅关闭的实现：

# Dockerfile 中使用 exec 格式
CMD ["python", "app.py"]

# 如果使用 shell 格式，信号无法传递到应用进程
CMD python app.py                  # 不推荐！

PID 1 问题：
- 容器中 PID 1 进程负责处理信号
- 如果 PID 1 是 shell（/bin/sh），它不会转发信号给子进程
- 解决方案：
  1. 使用 exec 格式的 CMD/ENTRYPOINT
  2. 使用 tini 或 dumb-init 作为 PID 1
  3. 使用 --init 参数

# 使用 tini
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "app.py"]

# 使用 docker --init
$ docker run --init myimage

Kubernetes 中的优雅关闭：
spec:
  terminationGracePeriodSeconds: 60    # 优雅关闭等待时间
  containers:
    - name: app
      lifecycle:
        preStop:
          exec:
            command: ["/bin/sh", "-c", "sleep 10"]  # preStop 钩子

最佳实践：
1. 应用正确处理 SIGTERM 信号
2. 停止接受新请求
3. 等待现有请求完成
4. 关闭数据库连接
5. 清理临时文件
6. 设置合理的超时时间
```

---

### 第二部分：Kubernetes 核心概念（10 题）

---

#### 题目 11：请描述 Kubernetes 的架构

**难度**：⭐⭐⭐

**详细解析**：

```
Kubernetes 架构分为 Control Plane（控制平面）和 Worker Node（工作节点）。

Control Plane（主节点）组件：

1. kube-apiserver
   - Kubernetes API 的入口
   - 所有组件通过 API 通信
   - 认证、授权、准入控制
   - RESTful API 接口

2. etcd
   - 分布式键值存储
   - 存储所有集群状态数据
   - 强一致性（Raft 协议）
   - 高可用部署（3 或 5 节点）

3. kube-scheduler
   - 负责 Pod 调度到合适的 Node
   - 考虑因素：资源需求、亲和性、污点容忍等
   - 调度策略：过滤 -> 打分 -> 绑定

4. kube-controller-manager
   - 运行各种控制器
   - Node Controller：监控节点状态
   - Replication Controller：维护副本数
   - Deployment Controller：管理 Deployment
   - Service Controller：管理 LoadBalancer

5. cloud-controller-manager（可选）
   - 与云平台 API 交互
   - 管理云资源（LB、存储、节点）

Worker Node（工作节点）组件：

1. kubelet
   - 管理 Pod 生命周期
   - 执行容器健康检查
   - 向 API Server 汇报节点状态
   - 挂载 Volume

2. kube-proxy
   - 实现 Service 的网络代理
   - 维护网络规则（iptables/IPVS）
   - 负载均衡

3. Container Runtime
   - 运行容器的软件
   - containerd、CRI-O、Docker（已弃用）

Pod 创建流程：
1. kubectl apply -f pod.yaml
2. API Server 验证并存储到 etcd
3. Scheduler 选择合适的 Node
4. kubelet 检测到新 Pod
5. kubelet 调用 Container Runtime 创建容器
6. kubelet 汇报 Pod 状态

+------------------Control Plane------------------+
|  kube-apiserver  |  etcd  |  scheduler  |  cm  |
+--------------------------+----------------------+
                           |
+----------Node 1----------+----------Node 2------+
| kubelet | kube-proxy     | kubelet | kube-proxy |
| [Pod A] [Pod B]          | [Pod C] [Pod D]      |
+--------------------------+----------------------+
```

---

#### 题目 12：Pod、Deployment、StatefulSet 有什么区别？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Pod：
- 最小的部署单元
- 一个或多个容器共享网络和存储
- 生命周期短暂，不保证重启到同一节点
- 共享 IP 和端口空间

Deployment：
- 管理无状态应用
- 声明式更新（滚动更新、回滚）
- 管理 ReplicaSet
- Pod 名称随机，无序

StatefulSet：
- 管理有状态应用
- 稳定的网络标识（pod-0, pod-1, pod-2）
- 稳定的持久化存储
- 有序部署和扩缩容
- 有序删除（从 pod-N 到 pod-0）

对比表：
+----------------+----------+-------------+---------------+
| 特性            | Pod      | Deployment  | StatefulSet   |
+----------------+----------+-------------+---------------+
| 副本管理        | 无       | 有          | 有            |
| 网络标识        | 随机     | 随机        | 稳定（有序）   |
| 存储            | 临时     | 共享/无     | 每个 Pod 独立  |
| 更新策略        | 手动     | 滚动更新    | 滚动更新      |
| 部署顺序        | 无       | 并行        | 有序          |
| 删除顺序        | 无       | 并行        | 逆序          |
| 适用场景        | 一次性任务| Web 服务   | 数据库、MQ    |
+----------------+----------+-------------+---------------+

StatefulSet 使用场景：
- 数据库：MySQL、PostgreSQL、MongoDB
- 消息队列：Kafka、RabbitMQ、ZooKeeper
- 分布式存储：Elasticsearch、Cassandra

StatefulSet 稳定标识示例：
$ kubectl get pods -l app=mysql
mysql-0    1/1    Running    0    5m
mysql-1    1/1    Running    0    4m
mysql-2    1/1    Running    0    3m

# DNS 解析
mysql-0.mysql.default.svc.cluster.local
mysql-1.mysql.default.svc.cluster.local
```

---

#### 题目 13：Kubernetes 的 Service 有几种类型？

**难度**：⭐⭐⭐

**详细解析**：

```
Kubernetes Service 类型：

1. ClusterIP（默认）
   - 只能在集群内部访问
   - 分配一个集群内部虚拟 IP
   - 适用于内部服务间通信

   apiVersion: v1
   kind: Service
   metadata:
     name: my-service
   spec:
     type: ClusterIP
     selector:
       app: my-app
     ports:
       - port: 80
         targetPort: 8080

2. NodePort
   - 在每个 Node 上开放一个端口（30000-32767）
   - 外部通过 <NodeIP>:<NodePort> 访问
   - 适用于开发测试环境

   spec:
     type: NodePort
     ports:
       - port: 80
         targetPort: 8080
         nodePort: 30080

3. LoadBalancer
   - 使用云提供商的负载均衡器
   - 自动创建外部 IP
   - 适用于生产环境
   - 需要云平台支持（AWS ELB、GCP LB、阿里云 SLB）

   spec:
     type: LoadBalancer
     ports:
       - port: 80
         targetPort: 8080

4. ExternalName
   - 将 Service 映射到外部域名
   - 不创建 ClusterIP
   - 通过 CNAME 记录实现

   spec:
     type: ExternalName
     externalName: api.example.com

5. Headless Service（clusterIP: None）
   - 不分配 ClusterIP
   - DNS 直接解析到 Pod IP
   - 适用于 StatefulSet

   spec:
     clusterIP: None
     selector:
       app: my-app
     ports:
       - port: 80

Service 负载均衡实现：
- iptables 模式（默认）：随机选择 Pod
- IPVS 模式：支持更多负载均衡算法
  - rr（轮询）
  - lc（最少连接）
  - sh（源地址哈希）
  - dh（目标地址哈希）
```

---

#### 题目 14：解释 Kubernetes 的 Ingress 和 Ingress Controller

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Ingress 是 Kubernetes 的 L7 路由规则定义，Ingress Controller 是实现这些规则的组件。

Ingress 的作用：
- URL 路径路由（/api -> api-service, /web -> web-service）
- 域名路由（a.example.com -> service-a, b.example.com -> service-b）
- SSL/TLS 终止
- 负载均衡

Ingress 资源定义：
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - example.com
      secretName: tls-secret
  rules:
    - host: example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80

常见 Ingress Controller：
1. Nginx Ingress Controller（最常用）
   - 社区版：kubernetes/ingress-nginx
   - Nginx 官方版：nginxinc/kubernetes-ingress

2. Traefik
   - 自动服务发现
   - 支持 Let's Encrypt

3. HAProxy
   - 高性能
   - 支持 TCP/UDP

4. Istio Gateway
   - Service Mesh 集成
   - 高级流量管理

Ingress Controller 部署：
$ kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

Ingress vs Gateway API：
- Ingress：功能有限，注解驱动
- Gateway API：更强大，角色分离，标准化
- Gateway API 是 Ingress 的进化版
```

---

#### 题目 15：Kubernetes 中的 ConfigMap 和 Secret 有什么区别？

**难度**：⭐⭐

**详细解析**：

```
ConfigMap 和 Secret 都用于存储配置数据，但用途不同。

ConfigMap：
- 存储非敏感配置数据
- 数据以明文存储在 etcd 中
- 支持键值对、文件、目录

Secret：
- 存储敏感数据（密码、令牌、证书）
- 数据以 Base64 编码存储（注意：不是加密！）
- 可以通过加密配置增强安全性

创建 ConfigMap：
# 从键值对创建
$ kubectl create configmap my-config --from-literal=key1=value1 --from-literal=key2=value2

# 从文件创建
$ kubectl create configmap my-config --from-file=config.yaml

# YAML 定义
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  DATABASE_URL: "postgres://localhost:5432/mydb"
  config.yaml: |
    log_level: info
    max_connections: 100

创建 Secret：
# 从键值对创建
$ kubectl create secret generic my-secret --from-literal=password=abc123

# 从文件创建
$ kubectl create secret generic tls-secret --from-file=tls.crt --from-file=tls.key

# YAML 定义（需要 Base64 编码）
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  username: YWRtaW4=          # echo -n "admin" | base64
  password: MWYyZDFlMmU2N2Rm  # echo -n "1f2d1e2e67df" | base64

在 Pod 中使用：
spec:
  containers:
    - name: app
      env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: my-secret
              key: password
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: my-config
              key: log_level
      volumeMounts:
        - name: config-volume
          mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: my-config

Secret 安全增强：
- 启用 etcd 加密
- 使用 External Secrets Operator
- 使用 HashiCorp Vault
- 设置 RBAC 权限控制
```

---

#### 题目 16：解释 Kubernetes 的调度机制

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Kubernetes 调度器（kube-scheduler）负责将 Pod 分配到合适的 Node。

调度过程：
1. 过滤（Filtering）：排除不满足条件的 Node
2. 打分（Scoring）：对剩余 Node 评分
3. 绑定（Binding）：选择得分最高的 Node

过滤条件：
- 资源是否充足（CPU、内存）
- NodeSelector 是否匹配
- Node Affinity 是否满足
- Pod Affinity/Anti-Affinity
- Taints 和 Tolerations
- Node 是否 Ready
- 端口是否冲突

调度方式：

1. NodeSelector（简单节点选择）
   spec:
     nodeSelector:
       disktype: ssd
       gpu: "true"

2. Node Affinity（高级节点亲和性）
   spec:
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
             - matchExpressions:
                 - key: kubernetes.io/os
                   operator: In
                   values:
                     - linux
         preferredDuringSchedulingIgnoredDuringExecution:
           - weight: 1
             preference:
               matchExpressions:
                 - key: disktype
                   operator: In
                   values:
                     - ssd

3. Pod Affinity/Anti-Affinity（Pod 亲和性）
   # 将 Pod 调度到有特定标签 Pod 的 Node 上
   affinity:
     podAffinity:
       requiredDuringSchedulingIgnoredDuringExecution:
         - labelSelector:
             matchExpressions:
               - key: app
                 operator: In
                 values:
                   - web
           topologyKey: kubernetes.io/hostname

4. Taints 和 Tolerations
   # 给 Node 打污点
   $ kubectl taint nodes node1 gpu=true:NoSchedule

   # Pod 设置容忍
   spec:
     tolerations:
       - key: "gpu"
         operator: "Equal"
         value: "true"
         effect: "NoSchedule"

5. Priority Class（优先级调度）
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: "高优先级 Pod"
```

---

#### 题目 17：Kubernetes 中如何实现滚动更新和回滚？

**难度**：⭐⭐⭐

**详细解析**：

```
Deployment 滚动更新策略：

apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1           # 最多多出 1 个 Pod
      maxUnavailable: 0     # 最多 0 个 Pod 不可用
  template:
    spec:
      containers:
        - name: app
          image: myapp:v2   # 更新镜像版本

更新过程（maxSurge=1, maxUnavailable=0）：
1. 创建 1 个新 Pod（v2）
2. 新 Pod Ready 后，删除 1 个旧 Pod（v1）
3. 重复直到所有 Pod 更新完成

查看更新状态：
$ kubectl rollout status deployment/my-app
$ kubectl rollout history deployment/my-app

回滚操作：
# 回滚到上一版本
$ kubectl rollout undo deployment/my-app

# 回滚到指定版本
$ kubectl rollout undo deployment/my-app --to-revision=2

# 查看修订历史
$ kubectl rollout history deployment/my-app

其他更新策略：
1. Recreate（重建策略）
   spec:
     strategy:
       type: Recreate
   # 先删除所有旧 Pod，再创建新 Pod
   # 有停机时间，但保证不会新旧版本共存

2. 金丝雀发布（手动控制）
   # 通过控制 replicas 比例实现
   # 旧版本：replicas=9，新版本：replicas=1
   # 观察新版本无问题后逐步增加

3. 蓝绿部署
   # 使用两个 Deployment（blue 和 green）
   # 通过切换 Service selector 实现

最佳实践：
- 设置合理的 maxSurge 和 maxUnavailable
- 配置 readinessProbe 确保新 Pod 就绪
- 配置 resource requests 和 limits
- 使用镜像标签（不要用 latest）
- 保留修订历史以便回滚
```

---

#### 题目 18：Kubernetes 中的 HPA 是如何工作的？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
HPA（Horizontal Pod Autoscaler）根据指标自动调整 Pod 副本数。

工作原理：
1. HPA Controller 定期（默认 15 秒）获取指标
2. 计算期望的副本数
3. 调整 Deployment/ReplicaSet 的 replicas

计算公式：
期望副本数 = ceil(当前副本数 * (当前指标值 / 期望指标值))

例如：
- 当前副本数：3
- 当前 CPU 使用率：60%
- 期望 CPU 使用率：30%
- 期望副本数 = ceil(3 * (60/30)) = 6

HPA 配置：
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300    # 缩容稳定窗口
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15

前提条件：
- 安装 Metrics Server
- Pod 配置 resource requests

查看 HPA 状态：
$ kubectl get hpa
$ kubectl describe hpa my-app-hpa

自定义指标：
- 使用 Prometheus Adapter
- 使用 KEDA（Kubernetes Event-Driven Autoscaling）
```

---

#### 题目 19：Kubernetes 中的 PV、PVC 和 StorageClass 有什么关系？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
PV（PersistentVolume）：集群级的存储资源
PVC（PersistentVolumeClaim）：用户对存储的请求
StorageClass：动态创建 PV 的模板

关系图：
User                    Cluster Admin
  |                         |
  |  创建 PVC              |  创建 StorageClass
  |                         |
  v                         v
+-------+  匹配/动态创建  +----------------+
|  PVC  | ------------> |  PV / StorageClass |
+-------+               +----------------+
  |
  |  绑定
  v
+-------+
|  Pod  |
+-------+

PV 定义：
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  hostPath:
    path: /data

PVC 定义：
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard

StorageClass 定义：
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer

Access Modes：
- ReadWriteOnce (RWO)：单节点读写
- ReadOnlyMany (ROX)：多节点只读
- ReadWriteMany (RWX)：多节点读写
- ReadWriteOncePod (RWOP)：单 Pod 读写

Reclaim Policy：
- Retain：PV 保留，需手动清理
- Delete：PV 自动删除
- Recycle：已弃用

在 Pod 中使用：
spec:
  containers:
    - name: app
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: my-pvc
```

---

#### 题目 20：解释 Kubernetes 的 RBAC 权限管理

**难度**：⭐⭐⭐⭐

**详细解析**：

```
RBAC（Role-Based Access Control）基于角色的访问控制。

RBAC 四个核心资源：
1. Role：命名空间级的角色（定义权限）
2. ClusterRole：集群级的角色
3. RoleBinding：将 Role 绑定到用户/组
4. ClusterRoleBinding：将 ClusterRole 绑定到用户/组

关系：
Role/ClusterRole -> 定义"能做什么"
RoleBinding/ClusterRoleBinding -> 定义"谁能做"

Role 示例（命名空间级）：
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]

RoleBinding 示例：
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
  - kind: User
    name: jane
    apiGroup: rbac.authorization.k8s.io
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

ClusterRole 示例（集群级）：
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-reader
rules:
  - apiGroups: [""]
    resources: ["nodes", "namespaces"]
    verbs: ["get", "list", "watch"]

常见 verbs：
- get：获取单个资源
- list：列出资源
- watch：监听资源变化
- create：创建资源
- update：更新资源
- patch：部分更新
- delete：删除资源

ServiceAccount RBAC：
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-sa-binding
subjects:
  - kind: ServiceAccount
    name: my-sa
    namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

查看权限：
$ kubectl auth can-i create pods --as=jane -n default
$ kubectl auth can-i --list --as=system:serviceaccount:default:my-sa
```

---

### 第三部分：K8s 故障排查与场景题（10 题）

---

#### 题目 21：Pod 处于 CrashLoopBackOff 状态，如何排查？

**难度**：⭐⭐⭐⭐⭐

**详细解析**：

```
CrashLoopBackOff 表示容器反复崩溃重启。

排查步骤：

Step 1：查看 Pod 状态和事件
$ kubectl describe pod <pod-name>
# 关注 Events 和 Last State

Step 2：查看容器日志
$ kubectl logs <pod-name>                    # 当前日志
$ kubectl logs <pod-name> --previous         # 上一次崩溃的日志
$ kubectl logs <pod-name> -c <container>     # 指定容器

Step 3：进入容器排查
$ kubectl exec -it <pod-name> -- /bin/sh     # 进入容器
$ kubectl exec -it <pod-name> -- ls /app     # 检查文件

Step 4：检查配置
$ kubectl get configmap <name> -o yaml       # 检查 ConfigMap
$ kubectl get secret <name> -o yaml          # 检查 Secret

Step 5：检查资源限制
$ kubectl top pod <pod-name>                 # 查看资源使用

常见原因和解决：

1. 应用启动失败
   - 查看日志中的错误信息
   - 检查依赖服务是否可用
   - 检查配置文件是否正确

2. OOMKilled（内存不足）
   $ kubectl describe pod <pod-name> | grep -A 5 "Last State"
   # 解决：增加 memory limits 或优化应用内存

3. 存活探针（Liveness Probe）失败
   # 探针配置过于严格
   # 应用启动慢，探针超时
   # 解决：调整探针参数
   livenessProbe:
     httpGet:
       path: /healthz
       port: 8080
     initialDelaySeconds: 30    # 增加初始延迟
     periodSeconds: 10
     timeoutSeconds: 5
     failureThreshold: 3

4. 配置错误
   - ConfigMap/Secret 不存在
   - 环境变量引用错误
   - Volume 挂载失败

5. 权限问题
   - ServiceAccount 权限不足
   - SecurityContext 过于严格

6. 镜像问题
   - 镜像不存在或拉取失败
   - 镜像架构不匹配
```

---

#### 题目 22：Node 处于 NotReady 状态，如何排查？

**难度**：⭐⭐⭐⭐⭐

```
Node NotReady 表示节点不健康，无法调度新 Pod。

排查步骤：

Step 1：查看 Node 状态
$ kubectl describe node <node-name>
# 关注 Conditions 和 Events

Step 2：检查 Node 上的系统组件
$ systemctl status kubelet
$ journalctl -u kubelet -f

Step 3：检查系统资源
$ free -h                          # 内存
$ df -h                            # 磁盘
$ top                              # CPU

Step 4：检查容器运行时
$ systemctl status containerd      # 或 docker
$ crictl ps                        # 查看容器状态

Step 5：检查网络
$ ping <master-ip>
$ curl -k https://<master-ip>:6443

常见原因和解决：

1. kubelet 服务异常
   $ systemctl restart kubelet
   $ journalctl -u kubelet --no-pager | tail -50

2. 磁盘压力（DiskPressure）
   $ kubectl describe node <node> | grep -i disk
   # Conditions 中 DiskPressure=True
   # 解决：清理磁盘空间

3. 内存压力（MemoryPressure）
   # 解决：增加内存或驱逐 Pod

4. PID 压力（PIDPressure）
   # 进程数过多
   # 解决：清理僵尸进程

5. 网络不通
   # 节点无法与 API Server 通信
   # 检查防火墙、安全组

6. 证书过期
   $ kubeadm certs check-expiration
   $ kubeadm certs renew all

7. 容器运行时异常
   $ systemctl restart containerd
   $ crictl ps -a
```

---

#### 题目 23：如何设计一个生产级的 Kubernetes 集群？

**难度**：⭐⭐⭐⭐⭐

```
设计要点：

1. 集群架构
   - Master 节点：3 或 5 个（奇数，保证 etcd 高可用）
   - Worker 节点：根据业务规模扩展
   - etcd 独立部署（推荐）

2. 网络方案
   - CNI 插件：Calico（推荐）、Cilium、Flannel
   - Service 实现：IPVS（推荐）vs iptables
   - Ingress Controller：Nginx、Traefik

3. 存储方案
   - StorageClass：对接云存储或 Ceph
   - CSI 驱动：标准容器存储接口
   - 备份方案：Velero

4. 监控告警
   - Prometheus + Grafana
   - kube-state-metrics
   - node-exporter
   - 日志：EFK/Loki

5. 安全加固
   - RBAC 权限控制
   - Network Policy 网络策略
   - Pod Security Standards
   - Secret 加密存储
   - 镜像安全扫描

6. 高可用设计
   - API Server：负载均衡 + 多副本
   - etcd：3/5 节点集群
   - Scheduler/Controller Manager：Leader Election

7. 运维工具
   - kubectl / k9s / lens
   - Helm / Kustomize
   - ArgoCD / Flux（GitOps）

集群配置建议：
+------------------+---------+---------+
| 节点类型          | CPU     | 内存    |
+------------------+---------+---------+
| Master           | 4 核    | 8GB    |
| etcd（独立）      | 4 核    | 16GB   |
| Worker（通用）    | 8 核    | 16GB   |
| Worker（计算密集）| 16 核   | 32GB   |
+------------------+---------+---------+
```

---

#### 题目 24：Kubernetes 中如何实现零停机部署？

**难度**：⭐⭐⭐⭐

```
零停机部署的关键技术：

1. 滚动更新 + Readiness Probe
   spec:
     replicas: 3
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxSurge: 1
         maxUnavailable: 0
     template:
       spec:
         containers:
           - name: app
             readinessProbe:
               httpGet:
                 path: /ready
                 port: 8080
               initialDelaySeconds: 5
               periodSeconds: 5

2. PreStop Hook
   # 在容器停止前执行清理操作
   lifecycle:
     preStop:
       exec:
         command: ["/bin/sh", "-c", "sleep 10"]

3. 优雅关闭
   # 应用正确处理 SIGTERM
   # 停止接受新请求
   # 等待现有请求完成
   terminationGracePeriodSeconds: 60

4. PodDisruptionBudget
   # 保证在维护期间有足够的 Pod 运行
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: my-app-pdb
   spec:
     minAvailable: 2    # 至少 2 个 Pod 可用
     selector:
       matchLabels:
         app: my-app

5. Session 保持
   # 使用 Service 的 sessionAffinity
   spec:
     sessionAffinity: ClientIP
     sessionAffinityConfig:
       clientIP:
         timeoutSeconds: 1800

完整流程：
1. 创建新版本 Pod
2. 新 Pod 通过 Readiness Probe
3. 从 Service 的 Endpoints 中移除旧 Pod
4. 执行 PreStop Hook（sleep 10s）
5. 发送 SIGTERM 给旧 Pod
6. 等待 terminationGracePeriodSeconds
7. 删除旧 Pod
```

---

#### 题目 25：如何排查 Kubernetes 中的网络问题？

**难度**：⭐⭐⭐⭐

```
Kubernetes 网络排查清单：

1. Pod 网络不通
   # 检查 Pod 状态
   $ kubectl get pods -o wide

   # 从 Pod 内部测试
   $ kubectl exec -it <pod> -- ping <target-ip>
   $ kubectl exec -it <pod> -- curl http://<service>:<port>

   # 检查 DNS
   $ kubectl exec -it <pod> -- nslookup kubernetes.default

2. Service 无法访问
   # 检查 Endpoints
   $ kubectl get endpoints <service>

   # 如果 Endpoints 为空，检查 selector 是否匹配
   $ kubectl get pods --show-labels
   $ kubectl describe service <service>

   # 检查端口配置
   $ kubectl get svc <service> -o yaml

3. Ingress 问题
   # 检查 Ingress 状态
   $ kubectl get ingress
   $ kubectl describe ingress <name>

   # 检查 Ingress Controller 日志
   $ kubectl logs -n ingress-nginx <controller-pod>

4. 跨节点通信问题
   # 检查 CNI 插件状态
   $ kubectl get pods -n kube-system | grep calico

   # 检查网络策略
   $ kubectl get networkpolicies

   # 测试跨节点通信
   $ kubectl exec -it <pod-on-node1> -- ping <pod-ip-on-node2>

5. 外部访问问题
   # 检查 Service 类型
   $ kubectl get svc <service>

   # 检查安全组/防火墙
   # 检查云负载均衡器

6. DNS 问题
   # 检查 CoreDNS
   $ kubectl get pods -n kube-system -l k8s-app=kube-dns
   $ kubectl logs -n kube-system -l k8s-app=kube-dns

   # 测试 DNS 解析
   $ kubectl exec -it <pod> -- nslookup <service>.<namespace>.svc.cluster.local

常用调试工具：
$ kubectl run debug --image=nicolaka/netshoot -it --rm -- bash
$ kubectl run debug --image=busybox -it --rm -- sh
```

---

#### 题目 26：解释 Kubernetes 的 QoS（服务质量）等级

**难度**：⭐⭐⭐⭐

```
Kubernetes 根据资源请求和限制将 Pod 分为三个 QoS 等级：

1. Guaranteed（保证型）
   - 所有容器都设置了 requests 和 limits
   - requests == limits
   - 最不容易被驱逐

   containers:
     - name: app
       resources:
         requests:
           cpu: "500m"
           memory: "256Mi"
         limits:
           cpu: "500m"
           memory: "256Mi"

2. Burstable（突发型）
   - 至少一个容器设置了 requests 或 limits
   - requests < limits
   - 在需要时可以使用更多资源

   containers:
     - name: app
       resources:
         requests:
           cpu: "250m"
           memory: "128Mi"
         limits:
           cpu: "500m"
           memory: "256Mi"

3. BestEffort（尽力而为型）
   - 没有设置任何 requests 或 limits
   - 最容易被驱逐

   containers:
     - name: app
       resources: {}

驱逐优先级：
BestEffort > Burstable > Guaranteed

查看 Pod 的 QoS 等级：
$ kubectl get pod <pod-name> -o jsonpath='{.status.qosClass}'

最佳实践：
- 生产环境关键服务使用 Guaranteed
- 普通服务使用 Burstable
- 避免使用 BestEffort
- 始终设置 resource requests
```

---

#### 题目 27：Kubernetes 中的 Init Container 是什么？

**难度**：⭐⭐⭐

```
Init Container 是在主容器启动之前运行的容器。

特点：
1. 总是运行到完成
2. 按顺序执行（一个完成后才执行下一个）
3. 如果 Init Container 失败，Pod 会重启

使用场景：
1. 等待依赖服务就绪
2. 执行初始化配置
3. 数据库迁移
4. 注册服务

示例：
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  initContainers:
    - name: wait-for-db
      image: busybox:1.36
      command: ['sh', '-c', 'until nc -z mysql 3306; do echo waiting for db; sleep 2; done']

    - name: init-schema
      image: myapp:migrate
      command: ['python', 'manage.py', 'migrate']
      env:
        - name: DB_HOST
          value: mysql

  containers:
    - name: app
      image: myapp:latest
      ports:
        - containerPort: 8080

Init Container vs Sidecar：
- Init Container：运行一次后退出
- Sidecar：与主容器同时运行，生命周期相同

Kubernetes 1.28+ 原生 Sidecar：
spec:
  initContainers:
    - name: sidecar
      image: envoy:latest
      restartPolicy: Always    # 标记为 Sidecar
```

---

#### 题目 28：如何实现 Kubernetes 的多集群管理？

**难度**：⭐⭐⭐⭐⭐

```
多集群管理方案：

1. kubectl Context 切换
   # 添加集群
   $ kubectl config set-cluster cluster1 --server=https://cluster1:6443
   $ kubectl config set-context ctx1 --cluster=cluster1

   # 切换集群
   $ kubectl config use-context ctx1

   # 使用 --context 参数
   $ kubectl --context=ctx1 get pods

2. KubeFed（Kubernetes Federation）
   - 联邦多个集群
   - 统一管理资源分发
   - 跨集群服务发现

3. Submariner（跨集群网络）
   - 打通多集群网络
   - 支持跨集群 Service 访问
   - 支持 GlobalNet

4. ArgoCD / Flux（GitOps）
   - 多集群应用部署
   - 声明式配置管理
   - 自动同步

5. Rancher / Lens（管理平台）
   - 图形化管理多集群
   - 统一的权限管理
   - 应用商店

6. Cluster API（集群生命周期管理）
   - 声明式集群管理
   - 自动化集群创建和升级
   - 支持多云平台

多集群架构模式：
- 主备模式：主集群处理请求，备集群热备
- 多活模式：多集群同时处理请求
- 分区模式：按业务/地区分配集群
- 服务网格：Istio 多集群
```

---

#### 题目 29：Kubernetes 中如何进行资源配额管理？

**难度**：⭐⭐⭐⭐

```
资源配额（ResourceQuota）限制命名空间的资源使用。

ResourceQuota：
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "10"
    persistentvolumeclaims: "20"
    requests.storage: 100Gi

LimitRange（限制单个 Pod/Container 的资源范围）：
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: dev
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "256Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "2"
        memory: "4Gi"
      min:
        cpu: "50m"
        memory: "64Mi"
    - type: Pod
      max:
        cpu: "4"
        memory: "8Gi"

查看配额使用情况：
$ kubectl get resourcequota -n dev
$ kubectl describe resourcequota compute-quota -n dev

最佳实践：
- 为每个命名空间设置 ResourceQuota
- 使用 LimitRange 设置默认值
- 使用 LimitRanger 准入控制器强制设置 requests
- 定期审查配额使用情况
```

---

#### 题目 30：设计一个 Kubernetes 微服务部署方案

**难度**：⭐⭐⭐⭐⭐（开放性设计题）

```
场景：电商系统微服务化部署

微服务拆分：
1. 前端服务（web）
2. API 网关（gateway）
3. 用户服务（user）
4. 商品服务（product）
5. 订单服务（order）
6. 支付服务（payment）
7. 消息队列（rabbitmq）
8. 数据库（mysql）
9. 缓存（redis）

部署架构：
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: web
          image: web:v1.2.3
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10

关键设计点：

1. 服务发现：Kubernetes Service + DNS
2. 配置管理：ConfigMap + Secret
3. 流量管理：Ingress + Service Mesh
4. 弹性伸缩：HPA + VPA
5. 故障隔离：PodDisruptionBudget + NetworkPolicy
6. 监控告警：Prometheus + Grafana + AlertManager
7. 日志收集：EFK/Loki
8. 链路追踪：Jaeger/Zipkin
9. 持续部署：ArgoCD
10. 备份恢复：Velero
```

---

## 💻 实战练习

### 练习 1：Docker 镜像优化

```bash
# 1. 编写一个未优化的 Dockerfile
cat > Dockerfile.unoptimized << 'EOF'
FROM python:3.11
WORKDIR /app
COPY . .
RUN apt-get update
RUN apt-get install -y curl
RUN pip install flask
RUN pip install requests
CMD python app.py
EOF

# 2. 编写优化后的 Dockerfile
cat > Dockerfile.optimized << 'EOF'
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
RUN useradd -m appuser
USER appuser
CMD ["python", "app.py"]
EOF

# 3. 比较镜像大小
$ docker build -f Dockerfile.unoptimized -t app:unoptimized .
$ docker build -f Dockerfile.optimized -t app:optimized .
$ docker images | grep app
```

### 练习 2：Kubernetes 故障排查

```bash
# 1. 创建一个有问题的 Pod
$ kubectl run bad-pod --image=nginx:nonexistent
$ kubectl describe pod bad-pod
$ kubectl get events --field-selector involvedObject.name=bad-pod

# 2. 创建一个会崩溃的 Pod
$ kubectl run crash-pod --image=busybox -- sh -c "exit 1"
$ kubectl logs crash-pod --previous

# 3. 创建资源超限的 Pod
$ kubectl run oom-pod --image=busybox -- sh -c "dd if=/dev/zero of=/dev/shm/fill bs=1M count=512" --limits="memory=128Mi"
$ kubectl describe pod oom-pod | grep -A 5 "Last State"
```

### 练习 3：Kubernetes 应用部署

```bash
# 1. 创建完整的应用部署
$ kubectl create namespace myapp

# 2. 创建 ConfigMap 和 Secret
$ kubectl create configmap app-config --from-literal=log_level=info -n myapp
$ kubectl create secret generic app-secret --from-literal=db_password=abc123 -n myapp

# 3. 部署应用
$ kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
  namespace: myapp
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
EOF

# 4. 验证部署
$ kubectl get all -n myapp
$ kubectl rollout status deployment/web -n myapp
```

---

## 📚 深入阅读

### 书籍
- 《Kubernetes in Action》- Marko Lukša
- 《Kubernetes Patterns》- Bilgin Ibryam
- 《Production Kubernetes》- Josh Rosso

### 认证
- CKA（Certified Kubernetes Administrator）
- CKS（Certified Kubernetes Security Specialist）
- CKAD（Certified Kubernetes Application Developer）

### 在线资源
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Kubernetes GitHub](https://github.com/kubernetes/kubernetes)
- [CNCF Landscape](https://landscape.cncf.io/)

---

## ✅ 自检清单

- [ ] 能解释 Docker 和虚拟机的区别
- [ ] 能描述 Docker 底层技术（Namespace、Cgroup、Union FS）
- [ ] 能解释镜像分层原理和优化技巧
- [ ] 能区分 CMD 和 ENTRYPOINT
- [ ] 能描述 Kubernetes 架构和组件
- [ ] 能区分 Pod、Deployment、StatefulSet
- [ ] 能解释 Service 的四种类型
- [ ] 能配置 HPA 自动伸缩
- [ ] 能排查 CrashLoopBackOff 和 NotReady 问题
- [ ] 能设计生产级 K8s 集群方案
- [ ] 能实现零停机部署
- [ ] 能配置 RBAC 权限管理

---

*Day 189 完成。容器和 Kubernetes 是现代 SRE 的核心技能。*
*明天我们将进入运维与系统设计面试题。*
