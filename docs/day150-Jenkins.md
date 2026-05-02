# Day 150: Jenkins

> 📅 日期：2026-05-05
> 📖 学习主题：Jenkins
> ⏰ 计划学习时间：2-3 小时

---

## 📖 Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'make'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

---

## 📚 扩展阅读

- [Jenkins 文档](https://www.jenkins.io/doc/)
