# Day 97: ConfigMap 与 Secret

> 📅 日期：2026-05-03
> 📖 学习主题：ConfigMap 与 Secret
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解配置与代码分离的原则
- 掌握 ConfigMap 和 Secret 的使用

---

## 📖 配置管理

### 1. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
  database.conf: |
    host=db
    port=3306
```

使用方式：
```yaml
# 环境变量
env:
  - name: APP_ENV
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: APP_ENV

# 挂载为文件
volumeMounts:
  - name: config
    mountPath: /etc/config
volumes:
  - name: config
    configMap:
      name: app-config
```

### 2. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=    # base64
  password: c2VjcmV0MTIz
```

```bash
# 创建
kubectl create secret generic db-credentials \
    --from-literal=username=admin \
    --from-literal=password=secret123
```

---

## 📚 扩展阅读

- [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret](https://kubernetes.io/docs/concepts/configuration/secret/)
