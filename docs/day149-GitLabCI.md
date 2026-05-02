# Day 149: GitLab CI

> 📅 日期：2026-05-05
> 📖 学习主题：GitLab CI
> ⏰ 计划学习时间：2-3 小时

---

## 📖 GitLab CI

```yaml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - docker build -t myapp .
```

---

## 📚 扩展阅读

- [GitLab CI 文档](https://docs.gitlab.com/ee/ci/)
