# Day 104: K8s 阶段测试

> 📅 日期：2026-05-03
> 📖 学习主题：K8s 阶段测试：部署完整应用 + 理论测试
> ⏰ 计划学习时间：2-3 小时

---

## 🏗️ 实战：部署完整应用

```bash
# 1. 创建 namespace
kubectl create namespace production

# 2. 部署所有资源
kubectl apply -f k8s/

# 3. 验证
kubectl get pods -n production
kubectl get svc -n production
kubectl get ingress -n production
```

## 📝 理论测试

### 问题 1：Pod 的 restartPolicy 有哪些？

<details>
<summary>答案</summary>
Always（默认）、OnFailure、Never
</details>

### 问题 2：Service 有哪四种类型？

<details>
<summary>答案</summary>
ClusterIP、NodePort、LoadBalancer、ExternalName
</details>

### 问题 3：Deployment 如何回滚？

<details>
<summary>答案</summary>
kubectl rollout undo deployment/name --to-revision=N
</details>

---

## 📚 扩展阅读

- [K8s 官方教程](https://kubernetes.io/docs/tutorials/)
