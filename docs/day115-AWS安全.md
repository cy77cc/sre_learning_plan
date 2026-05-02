# Day 115: AWS 安全

> 📅 日期：2026-05-04
> 📖 学习主题：AWS 安全
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 AWS 安全最佳实践
- 掌握 KMS 和 CloudTrail

---

## 📖 安全服务

### KMS

```bash
aws kms create-key
aws kms encrypt --key-id alias/my-key --plaintext "secret"
aws kms decrypt --ciphertext-blob fileb://encrypted
```

### CloudTrail

- 记录所有 API 调用
- 审计和合规

### GuardDuty

- 威胁检测
- 异常行为分析

---

## 📚 扩展阅读

- [AWS 安全文档](https://docs.aws.amazon.com/security/)
