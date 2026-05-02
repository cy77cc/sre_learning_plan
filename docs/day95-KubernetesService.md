# Day 95: Kubernetes Service

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Service
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Service 的四种类型
- 掌握服务发现和负载均衡

---

## 📖 Service 类型

### 1. ClusterIP（默认）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: ClusterIP
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```
- 集群内部可访问
- 自动分配 ClusterIP
- 内置 DNS：myapp.default.svc.cluster.local

### 2. NodePort

```yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
```
- 通过节点 IP + 端口访问
- 端口范围：30000-32767

### 3. LoadBalancer

```yaml
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
```
- 云提供商自动创建 LB
- 外部可访问

### 4. ExternalName

```yaml
spec:
  type: ExternalName
  externalName: api.example.com
```
- DNS CNAME 别名

---

## 📚 扩展阅读

- [Service 文档](https://kubernetes.io/docs/concepts/services-networking/service/)
