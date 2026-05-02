# Day 141: Logstash/Fluentd 日志采集

> 📅 日期：2026-05-05
> 📖 学习主题：Logstash/Fluentd 日志采集
> ⏰ 计划学习时间：2-3 小时

---

## 📖 Logstash 配置

```
input { file { path => "/var/log/*.log" } }
filter { grok { match => { "message" => "%{COMBINEDAPACHELOG}" } } }
output { elasticsearch { hosts => ["localhost:9200"] } }
```

---

## 📚 扩展阅读

- [Logstash 文档](https://www.elastic.co/guide/en/logstash/current/introduction.html)
