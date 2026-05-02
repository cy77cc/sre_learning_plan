# Day 148: GitHub Actions

> 📅 日期：2026-05-05
> 📖 学习主题：GitHub Actions
> ⏰ 计划学习时间：2-3 小时

---

## 📖 GitHub Actions

```yaml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: pytest
```

---

## 📚 扩展阅读

- [GitHub Actions 文档](https://docs.github.com/en/actions)
