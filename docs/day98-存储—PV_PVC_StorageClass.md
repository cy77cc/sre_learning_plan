# Day 98: 存储 — PV/PVC/StorageClass

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes 存储（PV/PVC/StorageClass, 静态/动态供给, 回收策略, CSI 驱动, NFS/云存储, 本地存储 Local PV）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 91 Kubernetes Pod, Day 92 Deployment, Day 95 Kubernetes Service

## 🎯 学习目标

完成 Day 98 的学习后，你应该能够：

1. 深入理解 Kubernetes 的存储抽象模型（PV/PVC/StorageClass）
2. 掌握静态供给和动态供给的工作流程
3. 理解回收策略（Retain/Delete/Recycle）的区别和使用场景
4. 能够配置 NFS、云存储、本地存储（Local PV）
5. 了解 CSI 驱动架构和常用 CSI 驱动

---

## 📖 核心知识点

### 1. Kubernetes 存储模型

#### 1.1 为什么需要存储抽象

```
容器存储的问题：
  1. 容器文件系统是临时的（容器重启数据丢失）
  2. 不同云厂商/基础设施的存储 API 不同
  3. 开发者关心"需要多少存储"，不关心"底层是什么存储"
  4. 需要存储与 Pod 生命周期解耦

Kubernetes 存储抽象：
  PersistentVolume (PV)      →  集群管理员创建的存储资源
  PersistentVolumeClaim (PVC) →  用户的存储请求
  StorageClass               →  动态创建 PV 的模板
```

#### 1.2 存储架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes 存储架构                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│  │ StorageClass │     │ StorageClass │     │ StorageClass│  │
│  │   (fast)     │     │   (standard) │     │   (slow)    │  │
│  └──────┬───────┘     └──────┬───────┘     └──────┬──────┘  │
│         │                    │                    │         │
│         │ 动态供给           │ 动态供给           │ 动态供给 │
│         ▼                    ▼                    ▼         │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│  │  PV (SSD)    │     │  PV (HDD)    │     │  PV (HDD)  │  │
│  │  100Gi       │     │  50Gi        │     │  200Gi     │  │
│  └──────┬───────┘     └──────┬───────┘     └──────┬──────┘  │
│         │                    │                    │         │
│         │ 绑定               │ 绑定               │ 绑定    │
│         ▼                    ▼                    ▼         │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│  │  PVC         │     │  PVC         │     │  PVC       │  │
│  │  请求 80Gi   │     │  请求 30Gi   │     │  请求 100Gi│  │
│  └──────┬───────┘     └──────┬───────┘     └──────┬──────┘  │
│         │                    │                    │         │
│         │ 挂载               │ 挂载               │ 挂载    │
│         ▼                    ▼                    ▼         │
│     ┌───────┐           ┌───────┐           ┌───────┐      │
│     │ Pod 1 │           │ Pod 2 │           │ Pod 3 │      │
│     └───────┘           └───────┘           └───────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 访问模式

| 模式 | 缩写 | 说明 | 典型存储 |
|------|------|------|----------|
| ReadWriteOnce | RWO | 单节点读写 | 块存储（EBS、PD） |
| ReadOnlyMany | ROX | 多节点只读 | NFS、文件存储 |
| ReadWriteMany | RWX | 多节点读写 | NFS、EFS、CephFS |
| ReadWriteOncePod | RWOP | 单 Pod 读写（1.27+） | CSI 块存储 |

```
访问模式选择指南：

有状态应用（数据库）：
  → RWO（单节点读写，数据一致性）

共享存储（日志、媒体文件）：
  → RWX（多节点读写）

只读数据（配置、静态资源）：
  → ROX（多节点只读）

强一致性需求（etcd、ZooKeeper）：
  → RWOP（单 Pod 读写，K8s 1.27+）
```

---

### 2. PersistentVolume（PV）

#### 2.1 PV 定义

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-nfs-data
  labels:
    type: nfs
    environment: production
spec:
  capacity:
    storage: 100Gi           # 存储容量
  accessModes:
    - ReadWriteMany          # 访问模式
  persistentVolumeReclaimPolicy: Retain   # 回收策略
  storageClassName: nfs      # 存储类名称
  nfs:
    server: 192.168.1.100
    path: /data/k8s-volumes/pv-nfs-data
  # 可选：挂载选项
  mountOptions:
    - hard
    - nfsvers=4.1
  # 可选：节点亲和性（Local PV 必须）
  # nodeAffinity:
  #   required:
  #     nodeSelectorTerms:
  #       - matchExpressions:
  #           - key: kubernetes.io/hostname
  #             operator: In
  #             values:
  #               - node-1
```

#### 2.2 PV 状态

| 状态 | 说明 |
|------|------|
| Available | 可用，未绑定到 PVC |
| Bound | 已绑定到 PVC |
| Released | PVC 已删除，但 PV 尚未回收 |
| Failed | 自动回收失败 |

```
PV 生命周期：

  Available ──→ Bound ──→ Released ──→ (Recycle/Delete/Retain)
     ↑                                      │
     └──────────────────────────────────────┘
                   (Retain 后手动恢复)
```

#### 2.3 PV 回收策略

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| Retain | 保留数据，需手动处理 | 生产数据、NFS |
| Delete | 删除 PV 和底层存储 | 云存储、临时数据 |
| Recycle | 清空数据（rm -rf），变为 Available | 已废弃，不推荐 |

```
回收策略详解：

Retain（推荐用于重要数据）：
  1. PVC 删除后，PV 状态变为 Released
  2. PV 保留数据，不会被自动删除
  3. 管理员需要手动处理：
     - 确认数据可以删除 → 删除 PV
     - 需要保留数据 → 修改 PV 删除 claimRef，变为 Available

Delete（云存储默认）：
  1. PVC 删除后，PV 和底层存储资产一起删除
  2. 适合临时数据或可重建的数据
  3. AWS EBS、GCE PD 等云存储默认行为

Recycle（已废弃）：
  1. 执行 rm -rf /thevolume/*
  2. PV 变为 Available
  3. 已废弃，不推荐使用
  4. 仅支持 NFS 和 HostPath
```

---

### 3. PersistentVolumeClaim（PVC）

#### 3.1 PVC 定义

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-data-pvc
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi          # 请求存储容量
  storageClassName: fast      # 指定存储类
  # 可选：选择特定 PV（通过标签）
  selector:
    matchLabels:
      type: ssd
      environment: production
  # 可选：数据源（用于从快照恢复）
  # dataSource:
  #   name: mysql-snapshot
  #   kind: VolumeSnapshot
  #   apiGroup: snapshot.storage.k8s.io
```

#### 3.2 PVC 绑定过程

```
┌─ PVC 绑定过程 ──────────────────────────────────────────┐
│                                                         │
│  1. 用户创建 PVC                                        │
│     - 指定容量、访问模式、存储类                         │
│                                                         │
│  2. PVC Controller 查找匹配的 PV                        │
│     匹配条件：                                          │
│     - storageClassName 相同                             │
│     - capacity >= PVC 请求的容量                        │
│     - accessModes 包含 PVC 请求的模式                   │
│     - selector 匹配（如果指定）                         │
│     - volumeMode 相同                                   │
│                                                         │
│  3a. 找到匹配 PV → 绑定                                │
│      PV 状态：Available → Bound                        │
│      PVC 状态：Pending → Bound                         │
│                                                         │
│  3b. 未找到匹配 PV                                      │
│      如果 StorageClass 存在 → 动态创建 PV              │
│      如果 StorageClass 不存在 → PVC 保持 Pending       │
└─────────────────────────────────────────────────────────┘
```

#### 3.3 在 Pod 中使用 PVC

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql-pod
spec:
  containers:
    - name: mysql
      image: mysql:8.0
      env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: root-password
      volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
      # 可选：设置子路径（支持多个 Pod 共享 PV 不同目录）
      # - name: mysql-data
      #   mountPath: /var/lib/mysql
      #   subPath: mysql-instance-1
  volumes:
    - name: mysql-data
      persistentVolumeClaim:
        claimName: mysql-data-pvc
        readOnly: false          # 是否只读挂载
```

---

### 4. StorageClass（存储类）

#### 4.1 StorageClass 定义

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: kubernetes.io/aws-ebs     # 供给者（已弃用，推荐 CSI）
# provisioner: ebs.csi.aws.com         # CSI 驱动
parameters:
  type: gp3                             # 存储类型
  iopsPerGB: "3000"                     # 每 GB IOPS
  encrypted: "true"                     # 加密
  fsType: ext4                          # 文件系统类型
reclaimPolicy: Delete                   # 回收策略（默认 Delete）
allowVolumeExpansion: true              # 允许扩容
volumeBindingMode: WaitForFirstConsumer # 绑定模式
mountOptions:
  - debug                               # 挂载选项
```

#### 4.2 各云厂商 StorageClass 示例

```yaml
# AWS EBS (CSI)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
# GCE Persistent Disk
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gce-ssd
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
  replication-type: regional-pd       # 区域持久盘
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
# Azure Disk
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: azure-ssd
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS                # SSD
  cachingmode: ReadOnly
  kind: Managed
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
# 阿里云 ESSD
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: alicloud-essd
provisioner: diskplugin.csi.alibabacloud.com
parameters:
  type: cloud_essd
  performanceLevel: PL1               # PL0/PL1/PL2/PL3
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

#### 4.3 volumeBindingMode 详解

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| Immediate | PVC 创建后立即绑定 PV | 集群级存储（NFS） |
| WaitForFirstConsumer | 等待 Pod 调度后再绑定 | 区域/可用区存储（EBS） |

```
WaitForFirstConsumer 的重要性：

问题：
  如果使用 Immediate 模式，PV 会在 PVC 创建时立即创建。
  如果 PV 创建在可用区 A，但 Pod 被调度到可用区 B，
  Pod 将无法挂载 PV（跨可用区挂载不支持）。

解决：
  WaitForFirstConsumer 模式下，PV 会在 Pod 调度时创建。
  Kubernetes 会根据 Pod 调度的节点，选择正确的可用区创建 PV。

推荐：
  - 云存储（EBS、GCE PD、Azure Disk）：WaitForFirstConsumer
  - 集群级存储（NFS、Ceph）：Immediate
```

---

### 5. 静态供给 vs 动态供给

#### 5.1 静态供给（Static Provisioning）

```
流程：
  1. 管理员手动创建底层存储（NFS 导出、云盘）
  2. 管理员手动创建 PV 对象
  3. 用户创建 PVC
  4. Kubernetes 自动绑定 PVC 和 PV

适用场景：
  - 特殊存储需求
  - 已有存储资产
  - 不支持动态供给的存储类型
```

```yaml
# 静态供给示例
# 1. 管理员创建 PV
apiVersion: v1
kind: PersistentVolume
metadata:
  name: static-nfs-pv
spec:
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  nfs:
    server: 192.168.1.100
    path: /exports/data
---
# 2. 用户创建 PVC（不指定 storageClassName 或指定与 PV 匹配的名称）
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 30Gi    # <= PV 的 50Gi，可以绑定
  # storageClassName: ""  # 空字符串表示只绑定没有 storageClassName 的 PV
```

#### 5.2 动态供给（Dynamic Provisioning）

```
流程：
  1. 管理员创建 StorageClass
  2. 用户创建 PVC（指定 storageClassName）
  3. PVC Controller 检测到没有匹配的 PV
  4. 调用 StorageClass 的 provisioner 创建 PV
  5. 自动绑定 PVC 和新创建的 PV

优势：
  - 无需管理员手动创建 PV
  - 自动化程度高
  - 支持按需创建
```

```yaml
# 动态供给示例
# 1. StorageClass（已提前创建）
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
reclaimPolicy: Delete
allowVolumeExpansion: true
---
# 2. 用户创建 PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast    # 指定 StorageClass，触发动态供给
---
# 3. PV 自动创建
# kubectl get pv
# NAME                                       CAPACITY   RECLAIMPOLICY   STATUS   CLAIM
# pvc-a1b2c3d4-e5f6-7890-abcd-ef1234567890  100Gi      Delete          Bound    default/dynamic-pvc
```

---

### 6. CSI（Container Storage Interface）

#### 6.1 CSI 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CSI 架构                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐                                       │
│  │   kubelet        │                                       │
│  └────────┬────────┘                                       │
│           │ gRPC                                            │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │  CSI Node       │  ← 每个节点运行                       │
│  │  Driver         │     处理卷的挂载/卸载                  │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  CSI Controller │     │  External        │               │
│  │  Plugin         │ ←── │  Provisioner     │               │
│  │  (可选)         │     │  (Sidecar)       │               │
│  └────────┬────────┘     └─────────────────┘               │
│           │ gRPC                                            │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │  存储后端       │  ← 云厂商 API / 存储系统               │
│  │  (EBS/GPD/NFS) │                                       │
│  └─────────────────┘                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 6.2 常用 CSI 驱动

| 存储类型 | CSI 驱动 | 说明 |
|----------|----------|------|
| AWS EBS | ebs.csi.aws.com | AWS 块存储 |
| AWS EFS | efs.csi.aws.com | AWS 文件存储 |
| GCE PD | pd.csi.storage.gke.io | GCP 持久盘 |
| Azure Disk | disk.csi.azure.com | Azure 磁盘 |
| Azure File | file.csi.azure.com | Azure 文件 |
| Ceph RBD | rbd.csi.ceph.com | Ceph 块存储 |
| CephFS | cephfs.csi.ceph.com | Ceph 文件存储 |
| NFS | nfs.csi.k8s.io | NFS 存储 |
| Longhorn | driver.longhorn.io | 轻量级分布式存储 |
| OpenEBS | openebs.io/local | 本地存储 |
| Local Path | rancher.io/local-path | 本地路径存储 |

#### 6.3 安装 CSI 驱动（以 NFS 为例）

```bash
# 安装 NFS CSI Driver
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
  --namespace kube-system \
  --set kubeletDir=/var/lib/kubelet

# 创建 NFS StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-csi
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.100
  share: /exports/k8s-data
reclaimPolicy: Delete
volumeBindingMode: Immediate
mountOptions:
  - nfsvers=4.1
  - hard
EOF
```

---

### 7. NFS 存储配置

#### 7.1 NFS Server 端配置

```bash
# 在 NFS 服务器上安装 NFS
sudo apt update && sudo apt install -y nfs-kernel-server

# 创建共享目录
sudo mkdir -p /exports/k8s-data
sudo chown nobody:nogroup /exports/k8s-data

# 配置导出
echo "/exports/k8s-data *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

# 导出并重启
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

#### 7.2 NFS PV 静态配置

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nfs-pv-data
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs
  nfs:
    server: 192.168.1.100
    path: /exports/k8s-data
  mountOptions:
    - hard
    - nfsvers=4.1
    - rsize=1048576
    - wsize=1048576
```

#### 7.3 NFS Subdir External Provisioner（动态供给）

```bash
# 安装 NFS Subdir External Provisioner
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner

helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace nfs-provisioner \
  --create-namespace \
  --set nfs.server=192.168.1.100 \
  --set nfs.path=/exports/k8s-data \
  --set storageClass.name=nfs-client \
  --set storageClass.defaultClass=false
```

---

### 8. 本地存储（Local PV）

#### 8.1 Local PV vs HostPath

| 特性 | HostPath | Local PV |
|------|----------|----------|
| 生命周期 | Pod | 节点 |
| 数据持久性 | Pod 删除后可能丢失 | 节点重启后保留 |
| 调度感知 | 不感知 | 感知（通过 nodeAffinity） |
| 适合场景 | 开发测试 | 生产本地存储 |
| 动态供给 | 不支持 | 不支持（需要外部 provisioner） |

#### 8.2 Local PV 配置

```yaml
# 1. 在节点上准备存储目录
# ssh node-1 "mkdir -p /mnt/disks/ssd1"

# 2. 创建 Local PV
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv-ssd1
spec:
  capacity:
    storage: 200Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/disks/ssd1
  # 必须指定节点亲和性
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - node-1
---
# 3. PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: local-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 150Gi
  storageClassName: local-storage
```

#### 8.3 Local Path Provisioner（Rancher）

```bash
# 安装 Local Path Provisioner
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml

# 创建 StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
EOF

# 配置存储路径
kubectl edit configmap local-path-config -n local-path-storage
# data:
#   config.json: |
#     {
#       "nodePathMap": [
#         {
#           "node": "DEFAULT_PATH_FOR_NON_LISTED_NODES",
#           "paths": ["/opt/local-path-provisioner"]
#         }
#       ]
#     }
```

---

### 9. 存储扩容

#### 9.1 在线扩容

```yaml
# StorageClass 必须设置 allowVolumeExpansion: true
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: expandable
provisioner: ebs.csi.aws.com
allowVolumeExpansion: true    # 关键字段
```

```bash
# 扩容 PVC
kubectl get pvc my-pvc -o yaml

# 编辑 PVC（只能增大，不能缩小）
kubectl patch pvc my-pvc -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'

# 查看扩容状态
kubectl get pvc my-pvc
kubectl describe pvc my-pvc
```

```
扩容流程：

  1. 用户修改 PVC 的 storage 大小（只能增大）
  2. PVC Controller 检测到变化
  3. 调用 CSI 驱动的 ControllerExpandVolume
  4. 底层存储扩容
  5. 如果文件系统需要扩展：
     - RWO：自动扩展（kubelet 负责）
     - RWX：可能需要手动扩展
  6. PVC 状态更新
```

---

### 10. VolumeSnapshot（快照）

#### 10.1 创建快照

```yaml
# 1. 安装 Snapshot Controller
# kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/
# kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/

# 2. 创建 VolumeSnapshotClass
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapclass
driver: ebs.csi.aws.com
deletionPolicy: Delete
---
# 3. 创建快照
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: mysql-data-snapshot
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: mysql-data-pvc
```

#### 10.2 从快照恢复

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-data-restored
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast
  dataSource:
    name: mysql-data-snapshot     # 快照名称
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

---

### 11. SRE 实战：存储故障排查

#### 11.1 常见问题清单

```
问题 1：PVC 一直处于 Pending 状态
  原因：
  - 没有匹配的 PV（静态供给）
  - StorageClass 的 provisioner 失败
  - 存储配额不足
  - volumeBindingMode=WaitForFirstConsumer 但没有 Pod 使用

  排查：
  kubectl describe pvc <name>
  kubectl get events --field-selector involvedObject.name=<pvc-name>
  kubectl logs -n kube-system -l app=<csi-driver>

问题 2：Pod 无法挂载 Volume
  原因：
  - PV/PVC 不在同一命名空间
  - 访问模式不匹配
  - 节点无法访问存储后端
  - 文件系统损坏

  排查：
  kubectl describe pod <name> | grep -A10 "Events"
  kubectl get pv <name> -o yaml
  dmesg | tail    # 查看内核错误

问题 3：存储性能差
  原因：
  - 存储类型选择不当
  - IOPS/吞吐量限制
  - 网络瓶颈
  - 文件系统配置

  排查：
  kubectl exec <pod> -- fio --name=test --rw=randread --bs=4k --numjobs=4 --size=1G --runtime=60
  kubectl exec <pod> -- iostat -x 1 10

问题 4：数据丢失
  原因：
  - 回收策略为 Delete
  - 使用 HostPath 而非 PV
  - PV 被误删除

  预防：
  - 重要数据使用 Retain 策略
  - 定期备份（VolumeSnapshot）
  - 使用 RBAC 限制 PV 删除权限
```

#### 11.2 排查命令

```bash
# 1. 查看 PV 状态
kubectl get pv
kubectl describe pv <name>
kubectl get pv <name> -o yaml

# 2. 查看 PVC 状态
kubectl get pvc
kubectl describe pvc <name>
kubectl get pvc <name> -o yaml

# 3. 查看 StorageClass
kubectl get storageclass
kubectl describe storageclass <name>

# 4. 查看 CSI 驱动
kubectl get csidrivers
kubectl get csinodes

# 5. 查看事件
kubectl get events --field-selector reason=FailedBinding
kubectl get events --field-selector reason=ProvisioningFailed

# 6. 查看 CSI 驱动日志
kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin
kubectl logs -n kube-system -l app=ebs-csi-node -c ebs-plugin

# 7. 验证存储挂载
kubectl exec <pod> -- df -h
kubectl exec <pod> -- mount | grep <mount-path>
kubectl exec <pod> -- ls -la <mount-path>
```

---

## 💻 实战练习

### 练习 1：NFS 静态供给

**目标**：手动创建 NFS PV 和 PVC 并验证

```bash
# 1. 在 NFS 服务器上创建目录（如果没有 NFS，使用 hostPath 模拟）
# 假设 NFS 服务器为 192.168.1.100

# 2. 创建 PV
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nfs-pv-test
  labels:
    type: nfs
    env: test
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs
  nfs:
    server: 192.168.1.100
    path: /exports/test-data
EOF

# 3. 查看 PV 状态
kubectl get pv nfs-pv-test
kubectl describe pv nfs-pv-test

# 4. 创建 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nfs-pvc-test
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 3Gi
  storageClassName: nfs
EOF

# 5. 验证绑定
kubectl get pvc nfs-pvc-test
kubectl get pv nfs-pv-test

# 6. 创建使用 PVC 的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: nfs-test-pod
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "echo 'Hello from NFS' > /data/test.txt && cat /data/test.txt && sleep 3600"]
      volumeMounts:
        - name: nfs-volume
          mountPath: /data
  volumes:
    - name: nfs-volume
      persistentVolumeClaim:
        claimName: nfs-pvc-test
EOF

# 7. 验证数据写入
kubectl exec nfs-test-pod -- cat /data/test.txt

# 8. 清理
kubectl delete pod nfs-test-pod
kubectl delete pvc nfs-pvc-test
kubectl delete pv nfs-pv-test
```

### 练习 2：动态供给实践

**目标**：使用 StorageClass 实现动态 PV 创建

```bash
# 1. 创建 StorageClass（使用 hostPath 模拟，实际应使用 CSI 驱动）
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-test
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
EOF

# 2. 创建 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc-test
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: local-test
EOF

# 3. 查看 PVC 状态（应该是 Pending，因为 WaitForFirstConsumer）
kubectl get pvc dynamic-pvc-test

# 4. 创建 Pod 触发绑定
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: dynamic-test-pod
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "echo 'Dynamic PV test' > /data/dynamic.txt && sleep 3600"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: dynamic-pvc-test
EOF

# 5. 验证 PV 自动创建
kubectl get pv
kubectl get pvc dynamic-pvc-test

# 6. 验证数据
kubectl exec dynamic-test-pod -- cat /data/dynamic.txt

# 7. 清理
kubectl delete pod dynamic-test-pod
kubectl delete pvc dynamic-pvc-test
# PV 会自动删除（reclaimPolicy: Delete）
```

### 练习 3：存储扩容实践

**目标**：练习 PVC 在线扩容

```bash
# 1. 创建支持扩容的 StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: expandable-test
provisioner: rancher.io/local-path
allowVolumeExpansion: true
reclaimPolicy: Delete
EOF

# 2. 创建 PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: expand-pvc-test
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: expandable-test
EOF

# 3. 创建 Pod 并写入数据
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: expand-test-pod
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "echo 'Before expansion' > /data/test.txt && df -h /data && sleep 3600"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: expand-pvc-test
EOF

# 4. 记录扩容前的大小
kubectl exec expand-test-pod -- df -h /data

# 5. 扩容 PVC
kubectl patch pvc expand-pvc-test -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'

# 6. 查看扩容状态
kubectl get pvc expand-pvc-test
kubectl describe pvc expand-pvc-test

# 7. 验证扩容后的大小
kubectl exec expand-test-pod -- df -h /data

# 8. 验证原有数据未丢失
kubectl exec expand-test-pod -- cat /data/test.txt

# 9. 清理
kubectl delete pod expand-test-pod
kubectl delete pvc expand-pvc-test
kubectl delete storageclass expandable-test
```

---

## 🎯 面试题精选

### 题目 1：PV、PVC、StorageClass 的关系是什么？

**参考答案**：

- **PV（PersistentVolume）**：集群级别的存储资源，由管理员创建。定义了存储的容量、访问模式、回收策略等。
- **PVC（PersistentVolumeClaim）**：用户的存储请求。声明需要的容量和访问模式。
- **StorageClass**：动态创建 PV 的模板。定义了 provisioner、参数、回收策略等。

关系：
- PVC 通过 storageClassName 引用 StorageClass
- StorageClass 的 provisioner 动态创建 PV
- PV 和 PVC 通过容量和访问模式匹配绑定

### 题目 2：什么是动态供给？什么是静态供给？

**参考答案**：

- **静态供给**：管理员手动创建 PV，用户创建 PVC 后自动绑定。适合特殊存储需求。
- **动态供给**：用户创建 PVC 时，自动触发 StorageClass 的 provisioner 创建 PV。自动化程度高，适合云环境。

动态供给流程：
1. 用户创建 PVC（指定 storageClassName）
2. PVC Controller 检测到无匹配 PV
3. 调用 StorageClass 的 provisioner
4. provisioner 创建底层存储和 PV
5. 自动绑定 PVC 和 PV

### 题目 3：PV 的回收策略有哪几种？各有什么特点？

**参考答案**：

1. **Retain**：保留数据，PV 状态变为 Released。需要管理员手动处理（删除或重新激活）。适合重要数据。
2. **Delete**：PV 和底层存储资产一起删除。适合临时数据或云存储。云存储的默认策略。
3. **Recycle**：执行 `rm -rf` 清空数据，PV 变为 Available。已废弃，不推荐使用。

### 题目 4：什么是 volumeBindingMode？Immediate 和 WaitForFirstConsumer 有什么区别？

**参考答案**：

- **Immediate**：PVC 创建后立即绑定/创建 PV。适合集群级存储（如 NFS）。
- **WaitForFirstConsumer**：等待 Pod 调度后再绑定/创建 PV。适合区域/可用区存储（如 EBS）。

WaitForFirstConsumer 的重要性：
防止 PV 创建在错误的可用区，导致 Pod 无法挂载。例如，EBS 只能挂载到同一可用区的 EC2 实例。

### 题目 5：Local PV 和 HostPath 有什么区别？

**参考答案**：

| 特性 | HostPath | Local PV |
|------|----------|----------|
| 生命周期 | 与 Pod 相同 | 与节点相同 |
| 调度感知 | 不感知 | 通过 nodeAffinity 感知 |
| 数据持久性 | Pod 删除后可能丢失 | 节点重启后保留 |
| 适合场景 | 开发测试 | 生产本地存储 |

Local PV 的优势：
- 数据在 Pod 重建后仍然保留
- 调度器知道 PV 在哪个节点，避免错误调度
- 可以与 StatefulSet 配合使用

### 题目 6：如何实现 PVC 扩容？

**参考答案**：

1. StorageClass 必须设置 `allowVolumeExpansion: true`
2. 修改 PVC 的 storage 字段（只能增大，不能缩小）
3. 底层存储自动扩容
4. 文件系统自动扩展（RWO）或手动扩展（RWX）

```bash
kubectl patch pvc my-pvc -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
```

### 题目 7：什么是 CSI？为什么需要它？

**参考答案**：

CSI（Container Storage Interface）是容器存储的标准接口，允许存储厂商开发统一的驱动。

CSI 的优势：
- **标准化**：统一的 gRPC 接口，不依赖 Kubernetes 版本
- **解耦**：存储驱动独立于 Kubernetes 开发和发布
- **灵活性**：支持动态供给、快照、扩容等功能
- **社区**：所有主流云厂商都提供 CSI 驱动

### 题目 8：如何排查 PVC 一直 Pending 的问题？

**参考答案**：

1. 查看 PVC 事件：`kubectl describe pvc <name>`
2. 检查 StorageClass：`kubectl get sc`
3. 检查是否有匹配的 PV（静态供给）
4. 检查 CSI 驱动日志：`kubectl logs -n kube-system -l app=<csi-driver>`
5. 检查存储配额是否充足
6. 如果是 WaitForFirstConsumer，检查是否有 Pod 使用该 PVC

### 题目 9：如何备份 Kubernetes 中的数据？

**参考答案**：

1. **VolumeSnapshot**：使用 CSI 快照功能创建存储快照
2. **Velero**：Kubernetes 备份工具，支持 PV 备份和恢复
3. **数据库原生备份**：如 MySQL mysqldump、PostgreSQL pg_dump
4. **文件级备份**：使用 rsync 或 restic 备份到对象存储

### 题目 10：StorageClass 的 reclaimPolicy 什么时候用 Retain？

**参考答案**：

使用 Retain 的场景：
- 生产数据库数据
- 关键业务数据
- 需要长期保留的数据
- 不能自动删除的合规数据

Retain 的工作流程：
1. PVC 删除后，PV 状态变为 Released
2. PV 保留数据，不自动删除
3. 管理员需要手动处理：
   - 删除 PV → 数据丢失
   - 删除 claimRef → PV 变为 Available，可重新绑定

---

## 📚 深入阅读

- [Kubernetes 存储文档](https://kubernetes.io/docs/concepts/storage/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [CSI 规范](https://container-storage-interface.github.io/spec/)
- [NFS CSI Driver](https://github.com/kubernetes-csi/csi-driver-nfs)
- [Local Path Provisioner](https://github.com/rancher/local-path-provisioner)
- [Velero 备份](https://velero.io/)

---

## ✅ 自检清单

- [ ] 能够解释 PV、PVC、StorageClass 的关系
- [ ] 理解静态供给和动态供给的工作流程
- [ ] 掌握 PV 的三种回收策略
- [ ] 理解 volumeBindingMode 的区别
- [ ] 能够配置 NFS、云存储、本地存储
- [ ] 了解 CSI 驱动架构
- [ ] 能够实现 PVC 在线扩容
- [ ] 能够创建和恢复 VolumeSnapshot
- [ ] 能够排查存储相关的常见问题
