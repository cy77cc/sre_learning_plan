# Day 150: Jenkins

> 📅 日期：2026-05-08
> 📖 学习主题：Pipeline 语法、Declarative vs Scripted、Jenkinsfile、共享库、插件生态、Blue Ocean、分布式构建、安全配置
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 147（CI/CD 概念与 GitOps）、Day 148（GitHub Actions）、Day 149（GitLab CI）

---

## 🎯 学习目标

- 理解 Jenkins Pipeline 的两种语法（Declarative vs Scripted）
- 掌握 Jenkinsfile 的编写和最佳实践
- 能配置共享库（Shared Library）实现 Pipeline 复用
- 了解 Jenkins 插件生态和常用插件
- 掌握分布式构建（Master-Agent 架构）
- 理解 Jenkins 安全配置和加固

---

## 📖 核心知识点

### 1. Jenkins 架构

```
Jenkins 架构：

┌──────────────────────────────────────────────────────────────┐
│                      Jenkins 架构                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Jenkins Controller（Master）           │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ Web UI   │  │ REST API │  │ CLI      │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ Job      │  │ Plugin   │  │ Queue    │           │   │
│  │  │ 配置     │  │ 管理     │  │ 调度     │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ 凭证     │  │ 节点     │  │ 安全     │           │   │
│  │  │ 管理     │  │ 管理     │  │ 管理     │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  └──────────────────────────────────────────────────────┘   │
│              │           │           │                       │
│              ▼           ▼           ▼                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Agent 1     │ │  Agent 2     │ │  Agent 3     │        │
│  │  (Linux)     │ │  (Docker)    │ │  (K8s Pod)   │        │
│  │              │ │              │ │              │        │
│  │  Workspace   │ │  Workspace   │ │  Workspace   │        │
│  │  Executor    │ │  Executor    │ │  Executor    │        │
│  │  Tools       │ │  Tools       │ │  Tools       │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  Controller 职责：                                           │
│  • 调度 Build、分配 Agent                                    │
│  • 提供 Web UI 和 API                                        │
│  • 管理插件和配置                                             │
│                                                              │
│  Agent 职责：                                                │
│  • 执行 Build 任务                                           │
│  • 提供构建环境                                               │
│  • 向 Controller 报告状态                                    │
└──────────────────────────────────────────────────────────────┘
```

### 2. Declarative Pipeline

#### 2.1 基础语法

```groovy
// Jenkinsfile - Declarative Pipeline
pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()                          // 显示时间戳
        disableConcurrentBuilds()             // 禁止并发构建
        buildDiscarder(logRotator(            // 构建历史保留
            numToKeepStr: '10',
            artifactNumToKeepStr: '5'
        ))
        retry(2)                              // 全局重试
    }

    environment {
        APP_NAME = 'my-application'
        VERSION = "${env.BUILD_NUMBER}"
        REGISTRY = 'registry.example.com'
        IMAGE = "${REGISTRY}/${APP_NAME}:${VERSION}"
    }

    parameters {
        string(name: 'DEPLOY_ENV', defaultValue: 'staging', description: 'Deploy environment')
        booleanParam(name: 'SKIP_TESTS', defaultValue: false, description: 'Skip tests')
        choice(name: 'LOG_LEVEL', choices: ['info', 'debug', 'warn'], description: 'Log level')
        password(name: 'SECRET', description: 'Secret value')
    }

    triggers {
        pollSCM('H/5 * * * *')                // 每 5 分钟轮询
        cron('H 2 * * 1-5')                   // 工作日 2:00
        githubPush()                           // GitHub Webhook
    }

    tools {
        go 'go-1.22'
        nodejs 'node-20'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_MSG = sh(
                        script: 'git log -1 --pretty=%B',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Build') {
            steps {
                sh 'go build -o app ./cmd/server'
                sh 'npm run build:frontend'
            }
        }

        stage('Test') {
            when {
                not { expression { return params.SKIP_TESTS } }
            }
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh 'go test ./... -coverprofile=coverage.out'
                    }
                    post {
                        always {
                            publishHTML(target: [
                                reportDir: 'coverage',
                                reportFiles: 'index.html',
                                reportName: 'Coverage Report'
                            ])
                        }
                    }
                }
                stage('Integration Tests') {
                    steps {
                        sh 'go test -tags=integration ./...'
                    }
                }
                stage('Lint') {
                    steps {
                        sh 'golangci-lint run'
                    }
                }
            }
        }

        stage('Security Scan') {
            steps {
                sh 'trivy fs --format json -o trivy-report.json .'
                sh 'govulncheck ./...'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.withRegistry("https://${REGISTRY}", 'registry-credentials') {
                        def img = docker.build("${APP_NAME}:${VERSION}")
                        img.push()
                        img.push('latest')
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            input {
                message 'Deploy to production?'
                ok 'Deploy'
                submitter 'admin,sre-team'
                parameters {
                    string(name: 'DEPLOY_REASON', defaultValue: '', description: 'Reason for deployment')
                }
            }
            steps {
                script {
                    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                        sh """
                            kubectl set image deployment/${APP_NAME} \
                                ${APP_NAME}=${IMAGE} \
                                --kubeconfig=${KUBECONFIG}
                            kubectl rollout status deployment/${APP_NAME} \
                                --kubeconfig=${KUBECONFIG}
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            cleanWs()                         // 清理工作空间
        }
        success {
            slackSend(
                channel: '#deployments',
                color: 'good',
                message: "✅ ${APP_NAME} v${VERSION} deployed successfully"
            )
        }
        failure {
            slackSend(
                channel: '#deployments',
                color: 'danger',
                message: "❌ ${APP_NAME} v${VERSION} build failed"
            )
        }
        unstable {
            slackSend(
                channel: '#deployments',
                color: 'warning',
                message: "⚠️ ${APP_NAME} v${VERSION} unstable"
            )
        }
    }
}
```

#### 2.2 Declarative 指令详解

```
Declarative Pipeline 指令：

┌──────────────────────────────────────────────────────────────┐
│                    Declarative 指令                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  agent         指定执行节点                                   │
│  ├── any       任意可用 Agent                                 │
│  ├── none      不指定（在 stage 中指定）                      │
│  ├── label     指定标签的 Agent                               │
│  ├── docker    Docker 容器中执行                              │
│  └── kubernetes K8s Pod 中执行                                │
│                                                              │
│  stages       定义所有阶段                                    │
│  └── stage    单个阶段                                       │
│      ├── steps       执行步骤                                │
│      ├── when        条件执行                                │
│      ├── parallel    并行阶段                                │
│      └── input       人工审批                                │
│                                                              │
│  post         构建后操作                                      │
│  ├── always   始终执行                                       │
│  ├── success  成功时执行                                     │
│  ├── failure  失败时执行                                     │
│  ├── unstable 不稳定时执行                                   │
│  ├── aborted  中止时执行                                     │
│  └── changed  状态变化时执行                                 │
│                                                              │
│  environment  环境变量                                        │
│  parameters   构建参数                                        │
│  triggers     触发器                                          │
│  tools        工具配置                                        │
│  options       构建选项                                       │
└──────────────────────────────────────────────────────────────┘
```

```groovy
// agent 配置示例
pipeline {
    // Docker Agent
    agent {
        docker {
            image 'golang:1.22'
            args '-v /tmp:/tmp -p 8080:8080'
            label 'docker'
            registryUrl 'https://registry.example.com'
            registryCredentialsId 'registry-creds'
        }
    }

    // Kubernetes Agent
    // agent {
    //     kubernetes {
    //         yaml """
    //             apiVersion: v1
    //             kind: Pod
    //             spec:
    //               containers:
    //                 - name: golang
    //                   image: golang:1.22
    //                   command: ['cat']
    //                   tty: true
    //                 - name: docker
    //                   image: docker:24
    //                   command: ['cat']
    //                   tty: true
    //                   volumeMounts:
    //                     - name: docker-sock
    //                       mountPath: /var/run/docker.sock
    //               volumes:
    //                 - name: docker-sock
    //                   hostPath:
    //                     path: /var/run/docker.sock
    //         """
    //     }
    // }

    stages {
        stage('Build') {
            agent {
                docker {
                    image 'node:20'
                    reuseNode true        // 复用 Pipeline 级别的节点
                }
            }
            steps {
                sh 'npm ci && npm run build'
            }
        }
    }
}

// when 条件指令
stage('Deploy Production') {
    when {
        branch 'main'
        environment name: 'DEPLOY_ENV', value: 'production'
        expression { return params.DEPLOY }
        not { triggeredBy 'TimerTrigger' }
        changeRequest()                 // 是 PR/MR
        allOf {
            branch 'main'
            environment name: 'DEPLOY', value: 'true'
        }
        anyOf {
            branch 'main'
            branch 'release/*'
        }
        beforeAgent true                // 在分配 Agent 前判断
    }
    steps {
        sh './deploy.sh production'
    }
}
```

### 3. Scripted Pipeline

#### 3.1 Scripted 语法

```groovy
// Jenkinsfile - Scripted Pipeline
node('linux') {
    def app

    try {
        stage('Checkout') {
            checkout scm
        }

        stage('Build') {
            // 使用工具
            withGoEnv(version: '1.22') {
                sh 'go build -o app ./cmd/server'
            }
        }

        stage('Test') {
            parallel(
                'Unit Tests': {
                    sh 'go test ./... -coverprofile=coverage.out'
                },
                'Integration Tests': {
                    sh 'go test -tags=integration ./...'
                },
                'Lint': {
                    sh 'golangci-lint run'
                }
            )
        }

        stage('Docker Build') {
            docker.withRegistry('https://registry.example.com', 'registry-creds') {
                app = docker.build("myapp:${env.BUILD_NUMBER}")
                app.push()
                app.push('latest')
            }
        }

        stage('Deploy') {
            if (env.BRANCH_NAME == 'main') {
                input message: 'Deploy to production?'

                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh "kubectl set image deployment/myapp myapp=registry.example.com/myapp:${env.BUILD_NUMBER}"
                }
            }
        }

    } catch (e) {
        currentBuild.result = 'FAILURE'
        throw e
    } finally {
        // 清理
        cleanWs()

        // 通知
        if (currentBuild.result == 'FAILURE') {
            slackSend(color: 'danger', message: "Build failed: ${env.BUILD_URL}")
        } else {
            slackSend(color: 'good', message: "Build succeeded: ${env.BUILD_URL}")
        }
    }
}
```

#### 3.2 Declarative vs Scripted 对比

| 维度 | Declarative | Scripted |
|------|-------------|----------|
| 语法 | 结构化 YAML-like | Groovy 脚本 |
| 学习曲线 | 较低 | 较高 |
| 灵活性 | 中等 | 完全灵活 |
| 错误处理 | post 块 | try-catch-finally |
| 条件执行 | when 指令 | if-else |
| 并行 | parallel 块 | parallel 函数 |
| 推荐度 | 推荐（新项目） | 复杂场景 |
| IDE 支持 | 较好（Blue Ocean） | 一般 |
| 模板化 | 支持 | 支持 |
| 调试 | 较难 | 较容易 |

### 4. 共享库（Shared Library）

#### 4.1 共享库结构

```
共享库目录结构：

shared-library/
├── vars/                          # 全局变量和函数
│   ├── standardPipeline.groovy    # 标准 Pipeline 函数
│   ├── deployToK8s.groovy         # 部署函数
│   ├── sendNotification.groovy    # 通知函数
│   └── dockerBuild.groovy         # Docker 构建函数
├── src/                           # Groovy 类
│   └── com/
│       └── example/
│           └── jenkins/
│               ├── Docker.groovy
│               ├── Kubernetes.groovy
│               └── Notification.groovy
├── resources/                     # 资源文件
│   ├── templates/
│   │   ├── k8s-deployment.yaml
│   │   └── docker-compose.yaml
│   └── scripts/
│       └── deploy.sh
└── test/                          # 测试
    └── vars/
        └── standardPipelineTest.groovy
```

#### 4.2 共享库实现

```groovy
// vars/standardPipeline.groovy
def call(Map config = [:]) {
    def defaults = [
        language: 'go',
        goVersion: '1.22',
        nodeVersion: '20',
        dockerImage: '',
        deployEnv: 'staging',
        slackChannel: '#builds',
        skipTests: false
    ]
    def cfg = defaults + config

    pipeline {
        agent {
            kubernetes {
                yaml libraryResource('templates/k8s-pod.yaml')
            }
        }

        options {
            timeout(time: 30, unit: 'MINUTES')
            timestamps()
            buildDiscarder(logRotator(numToKeepStr: '10'))
        }

        environment {
            APP_NAME = env.JOB_NAME.split('/').first()
            VERSION = "${env.BUILD_NUMBER}-${env.GIT_COMMIT?.take(7) ?: 'unknown'}"
        }

        stages {
            stage('Checkout') {
                steps {
                    checkout scm
                }
            }

            stage('Build') {
                steps {
                    script {
                        if (cfg.language == 'go') {
                            container('golang') {
                                sh "go build -o app ./cmd/server"
                            }
                        } else if (cfg.language == 'node') {
                            container('node') {
                                sh 'npm ci && npm run build'
                            }
                        }
                    }
                }
            }

            stage('Test') {
                when { not { expression { return cfg.skipTests } } }
                steps {
                    script {
                        if (cfg.language == 'go') {
                            container('golang') {
                                sh 'go test ./... -coverprofile=coverage.out'
                            }
                        } else if (cfg.language == 'node') {
                            container('node') {
                                sh 'npm test'
                            }
                        }
                    }
                }
            }

            stage('Docker Build') {
                when { branch 'main' }
                steps {
                    script {
                        docker.withRegistry("https://${cfg.registry}", 'registry-creds') {
                            def img = docker.build("${APP_NAME}:${VERSION}")
                            img.push()
                            img.push('latest')
                        }
                    }
                }
            }

            stage('Deploy') {
                when { branch 'main' }
                steps {
                    script {
                        deployToK8s(
                            app: APP_NAME,
                            image: "${APP_NAME}:${VERSION}",
                            env: cfg.deployEnv
                        )
                    }
                }
            }
        }

        post {
            always {
                cleanWs()
            }
            success {
                sendNotification(
                    status: 'success',
                    channel: cfg.slackChannel,
                    message: "${APP_NAME} v${VERSION} deployed"
                )
            }
            failure {
                sendNotification(
                    status: 'failure',
                    channel: cfg.slackChannel,
                    message: "${APP_NAME} v${VERSION} build failed"
                )
            }
        }
    }
}

// vars/deployToK8s.groovy
def call(Map config) {
    def namespace = config.env == 'production' ? 'production' : 'staging'

    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh """
            kubectl set image deployment/${config.app} \
                ${config.app}=${config.image} \
                -n ${namespace} \
                --kubeconfig=${KUBECONFIG}
            kubectl rollout status deployment/${config.app} \
                -n ${namespace} \
                --kubeconfig=${KUBECONFIG} \
                --timeout=300s
        """
    }
}

// vars/sendNotification.groovy
def call(Map config) {
    def color = config.status == 'success' ? 'good' : 'danger'
    def emoji = config.status == 'success' ? '✅' : '❌'

    slackSend(
        channel: config.channel,
        color: color,
        message: "${emoji} ${config.message}\nBuild: ${env.BUILD_URL}"
    )
}

// vars/dockerBuild.groovy
def call(Map config) {
    def registry = config.registry ?: 'registry.example.com'
    def image = "${registry}/${config.name}:${config.tag}"

    docker.withRegistry("https://${registry}", config.credentialsId ?: 'registry-creds') {
        def img = docker.build(image, config.context ?: '.')
        img.push()
        if (config.pushLatest) {
            img.push('latest')
        }
        return image
    }
}
```

#### 4.3 共享库配置

```groovy
// Jenkinsfile 中使用共享库
@Library('my-shared-library') _

// 使用默认配置
standardPipeline()

// 使用自定义配置
standardPipeline(
    language: 'go',
    goVersion: '1.22',
    deployEnv: 'production',
    slackChannel: '#production-deploys'
)

// 使用共享库中的函数
@Library('my-shared-library') _

pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                script {
                    def image = dockerBuild(
                        name: 'myapp',
                        tag: env.BUILD_NUMBER,
                        context: '.',
                        pushLatest: true
                    )
                    echo "Built image: ${image}"
                }
            }
        }

        stage('Deploy') {
            steps {
                deployToK8s(
                    app: 'myapp',
                    image: "registry.example.com/myapp:${env.BUILD_NUMBER}",
                    env: 'staging'
                )
            }
        }
    }
    post {
        failure {
            sendNotification(
                status: 'failure',
                channel: '#builds',
                message: 'Build failed'
            )
        }
    }
}
```

### 5. 插件生态

#### 5.1 核心插件

```
Jenkins 核心插件分类：

┌──────────────────────────────────────────────────────────────┐
│                    Jenkins 核心插件                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  源码管理                                                     │
│  ├── Git Plugin                  Git 集成                     │
│  ├── GitHub Plugin               GitHub 集成                  │
│  ├── GitLab Plugin               GitLab 集成                  │
│  └── Bitbucket Plugin            Bitbucket 集成               │
│                                                              │
│  构建工具                                                     │
│  ├── Gradle Plugin               Gradle 构建                  │
│  ├── Maven Integration           Maven 构建                   │
│  ├── NodeJS Plugin               Node.js 环境                 │
│  ├── Go Plugin                   Go 环境                      │
│  └── Docker Pipeline             Docker 构建                  │
│                                                              │
│  测试与报告                                                   │
│  ├── JUnit Plugin                JUnit 测试报告               │
│  ├── JaCoCo Plugin               代码覆盖率                   │
│  ├── Cobertura Plugin            覆盖率报告                   │
│  └── HTML Publisher               HTML 报告                   │
│                                                              │
│  部署与发布                                                   │
│  ├── Kubernetes CD               K8s 部署                     │
│  ├── AWS Steps                   AWS 操作                     │
│  ├── Azure CLI                   Azure 操作                   │
│  └── Deploy to Container         WAR 部署                    │
│                                                              │
│  通知                                                         │
│  ├── Slack Notification          Slack 通知                   │
│  ├── Email Extension             邮件通知                     │
│  ├── DingTalk                    钉钉通知                     │
│  └── Telegram                    Telegram 通知                │
│                                                              │
│  代码质量                                                     │
│  ├── SonarQube Scanner           代码扫描                     │
│  ├── Checkstyle                  代码风格                     │
│  ├── PMD                         静态分析                     │
│  └── Warnings Next Gen           警告收集                     │
│                                                              │
│  安全                                                         │
│  ├── Credentials Binding         凭证绑定                     │
│  ├── OWASP Dependency Check      依赖漏洞扫描                 │
│  └── Snyk Security               安全扫描                     │
│                                                              │
│  UI                                                           │
│  ├── Blue Ocean                  现代 UI                      │
│  ├── Dashboard View              仪表盘                       │
│  └── Job Generator               Job 生成器                   │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 常用插件配置

```groovy
// Docker Pipeline 插件
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                script {
                    // 构建镜像
                    def app = docker.build("myapp:${env.BUILD_NUMBER}")

                    // 运行测试（在容器中）
                    app.inside {
                        sh 'npm test'
                    }

                    // 推送镜像
                    docker.withRegistry('https://registry.example.com', 'registry-creds') {
                        app.push()
                        app.push('latest')
                    }
                }
            }
        }

        stage('Test with services') {
            steps {
                script {
                    // 使用 Docker Compose
                    docker.image('postgres:15').withRun(
                        '-e POSTGRES_PASSWORD=test -p 5432:5432'
                    ) { postgres ->
                        docker.image('redis:7').withRun(
                            '-p 6379:6379'
                        ) { redis ->
                            sh """
                                export DATABASE_URL=postgresql://postgres:test@localhost:5432/test
                                export REDIS_URL=redis://localhost:6379
                                npm test
                            """
                        }
                    }
                }
            }
        }
    }
}

// Credentials Binding 插件
pipeline {
    agent any
    stages {
        stage('Deploy') {
            steps {
                // 用户名密码
                withCredentials([usernamePassword(
                    credentialsId: 'aws-creds',
                    usernameVariable: 'AWS_ACCESS_KEY_ID',
                    passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                )]) {
                    sh 'aws s3 sync dist/ s3://my-bucket/'
                }

                // SSH 密钥
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key',
                    keyFileVariable: 'SSH_KEY',
                    usernameVariable: 'SSH_USER'
                )]) {
                    sh 'scp -i $SSH_KEY dist/* $SSH_USER@server:/app/'
                }

                // Secret 文件
                withCredentials([file(
                    credentialsId: 'kubeconfig',
                    variable: 'KUBECONFIG'
                )]) {
                    sh 'kubectl get pods --kubeconfig=$KUBECONFIG'
                }

                // Secret 文本
                withCredentials([string(
                    credentialsId: 'api-token',
                    variable: 'API_TOKEN'
                )]) {
                    sh 'curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com'
                }
            }
        }
    }
}

// SonarQube 插件
pipeline {
    agent any
    stages {
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        sonar-scanner \
                            -Dsonar.projectKey=my-project \
                            -Dsonar.sources=src \
                            -Dsonar.tests=test \
                            -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
    }
}
```

### 6. Blue Ocean

```
Blue Ocean 特性：

┌──────────────────────────────────────────────────────────────┐
│                    Blue Ocean UI                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  特性：                                                      │
│  • 可视化 Pipeline 编辑器（拖拽式）                           │
│  • 清晰的 Pipeline 执行状态展示                               │
│  • 实时日志查看                                               │
│  • Git 集成（创建 Pipeline 从 Git 开始）                      │
│  • 个性化 Dashboard                                          │
│                                                              │
│  Pipeline 可视化：                                           │
│                                                              │
│  ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐                 │
│  │Build │──►│ Test │──►│Scan  │──►│Deploy│                 │
│  │  ✅  │   │  ✅  │   │  ✅  │   │  ⏳  │                 │
│  └──────┘   └──────┘   └──────┘   └──────┘                 │
│                │                                             │
│          ┌─────┴─────┐                                      │
│          ▼           ▼                                      │
│     ┌──────┐   ┌──────┐                                     │
│     │ Unit │   │ Int  │                                     │
│     │  ✅  │   │  ✅  │                                     │
│     └──────┘   └──────┘                                     │
│                                                              │
│  安装：                                                      │
│  Jenkins > Manage Jenkins > Plugins > Blue Ocean             │
│                                                              │
│  访问：                                                      │
│  http://jenkins.example.com/blue                             │
└──────────────────────────────────────────────────────────────┘
```

### 7. 分布式构建

#### 7.1 Agent 配置

```groovy
// 配置 Jenkins Agent

// 方式 1: SSH Agent
// Jenkins > Manage Jenkins > Nodes > New Node
// - Remote root directory: /var/jenkins
// - Launch method: Launch agents via SSH
// - Host: agent1.example.com
// - Credentials: SSH 密钥

// 方式 2: Docker Agent
// Jenkins > Manage Jenkins > Clouds > Docker
// - Docker Host URI: unix:///var/run/docker.sock
// - Docker Agent Templates:
//   - Labels: docker
//   - Docker Image: jenkins/inbound-agent:latest

// 方式 3: Kubernetes Agent
// Jenkins > Manage Jenkins > Clouds > Kubernetes
// - Kubernetes URL: https://kubernetes.default.svc
// - Jenkins URL: http://jenkins:8080
// - Pod Templates:
//   - Labels: k8s
//   - Containers:
//     - Name: jnlp
//       Image: jenkins/inbound-agent:latest

// Jenkinsfile 中使用 Agent
pipeline {
    agent {
        label 'linux && docker'      // 标签匹配
    }

    stages {
        stage('Build') {
            agent {
                docker {
                    image 'golang:1.22'
                    label 'docker'     // 在 docker 标签的节点上运行
                }
            }
            steps {
                sh 'go build .'
            }
        }

        stage('Deploy') {
            agent {
                label 'production'     // 在 production 标签的节点上运行
            }
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

#### 7.2 Kubernetes 动态 Agent

```groovy
// Kubernetes Pod Template
pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-agent
spec:
  containers:
    - name: golang
      image: golang:1.22
      command: ['cat']
      tty: true
      resources:
        requests:
          cpu: '500m'
          memory: '1Gi'
        limits:
          cpu: '2'
          memory: '4Gi'
      volumeMounts:
        - name: go-cache
          mountPath: /go/pkg/mod
    - name: docker
      image: docker:24
      command: ['cat']
      tty: true
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
    - name: kubectl
      image: bitnami/kubectl:1.28
      command: ['cat']
      tty: true
  volumes:
    - name: docker-sock
      hostPath:
        path: /var/run/docker.sock
    - name: go-cache
      persistentVolumeClaim:
        claimName: go-cache-pvc
"""
        }
    }

    stages {
        stage('Build') {
            steps {
                container('golang') {
                    sh 'go build -o app ./cmd/server'
                }
            }
        }

        stage('Docker Build') {
            steps {
                container('docker') {
                    sh 'docker build -t myapp:latest .'
                }
            }
        }

        stage('Deploy') {
            steps {
                container('kubectl') {
                    sh 'kubectl apply -f k8s/'
                }
            }
        }
    }
}
```

### 8. 安全配置

#### 8.1 Jenkins 安全加固

```
Jenkins 安全配置清单：

┌──────────────────────────────────────────────────────────────┐
│                    Jenkins 安全加固                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 认证                                                     │
│  ├── 启用 Jenkins 内置用户数据库                              │
│  ├── 集成 LDAP/Active Directory                              │
│  ├── 配置 SSO（SAML/OAuth/OIDC）                             │
│  └── 禁用匿名访问                                            │
│                                                              │
│  2. 授权                                                     │
│  ├── 基于矩阵的授权                                          │
│  ├── 基于项目的授权                                           │
│  ├── Role-Based Authorization Strategy                       │
│  └── 最小权限原则                                            │
│                                                              │
│  3. 网络                                                     │
│  ├── 启用 HTTPS                                              │
│  ├── 配置 CSRF 防护（默认开启）                               │
│  ├── 限制 Agent 连接端口                                     │
│  └── 配置反向代理                                            │
│                                                              │
│  4. 凭证                                                     │
│  ├── 使用 Credentials Plugin 管理凭证                        │
│  ├── 使用 Credentials Binding 绑定到环境变量                  │
│  ├── 定期轮换凭证                                            │
│  └── 不在 Jenkinsfile 中硬编码凭证                            │
│                                                              │
│  5. 脚本安全                                                  │
│  ├── Script Security Plugin（Groovy 脚本沙箱）               │
│  ├── 审批 Groovy 脚本                                        │
│  └── 限制 Pipeline 执行用户                                   │
│                                                              │
│  6. 审计                                                     │
│  ├── Audit Trail Plugin                                      │
│  ├── Job Config History Plugin                               │
│  └── 启用安全审计日志                                         │
└──────────────────────────────────────────────────────────────┘
```

#### 8.2 RBAC 配置

```groovy
// 使用 Role-Based Authorization Strategy

// 角色定义：
// admin: 完全控制
// developer: 构建和查看
// viewer: 只读

// 全局角色
// admin: Overall/Administer
// developer: Overall/Read, Job/Build, Job/Read, Job/Workspace
// viewer: Overall/Read, Job/Read

// 项目角色（基于 Pattern）
// Pattern: team-a-.*
// Permissions: Job/Build, Job/Read, Job/Configure

// Pattern: production-.*
// Permissions: Job/Read (只读，生产 Job 不允许普通用户构建)
```

```groovy
// Jenkinsfile 中的安全实践
pipeline {
    agent any

    options {
        // 禁用 Groovy 脚本沙箱中的危险操作
        scriptSecurity {
            // 自动审批安全的脚本
        }
    }

    stages {
        stage('Build') {
            steps {
                // 使用 credentials 绑定，不在脚本中硬编码
                withCredentials([usernamePassword(
                    credentialsId: 'docker-registry',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh '''
                        echo "$REGISTRY_PASS" | docker login -u "$REGISTRY_USER" --password-stdin registry.example.com
                        docker build -t myapp .
                        docker push registry.example.com/myapp
                    '''
                }
            }
        }
    }

    post {
        always {
            // 清理敏感文件
            sh 'rm -f .env credentials.json'
            cleanWs()
        }
    }
}
```

---

## 💻 实战练习

### 练习 1：编写 Declarative Pipeline

**目标**：为一个 Java Spring Boot 应用编写完整的 Jenkinsfile

**步骤**：

1. 创建 `Jenkinsfile`：
   - 使用 Maven 构建
   - 运行单元测试和集成测试
   - SonarQube 代码扫描
   - Docker 镜像构建
   - 部署到 staging（自动）和 production（手动审批）

2. 配置 Jenkins Job：
   - Multibranch Pipeline
   - GitHub/Webhook 触发
   - 构建参数（环境选择）

3. 配置 Credentials：
   - Docker Registry 凭证
   - SonarQube Token
   - Kubeconfig

**验证**：Push 代码后 Pipeline 自动运行，所有 Stage 成功

### 练习 2：创建共享库

**目标**：创建一个标准化的共享库

**步骤**：

1. 创建 Git 仓库 `jenkins-shared-library`
2. 实现以下函数：
   - `standardPipeline()` - 标准 Pipeline 模板
   - `dockerBuild()` - Docker 构建
   - `deployToK8s()` - K8s 部署
   - `sendNotification()` - 通知

3. 在 Jenkins 中配置共享库
4. 在项目中使用共享库

**验证**：多个项目使用同一共享库，Pipeline 标准化

### 练习 3：故障排查 - Jenkins 构建失败

**场景**：Pipeline 在 Docker Build 阶段失败

**排查步骤**：

1. 查看构建控制台输出
2. 检查 Jenkins 系统日志（Manage Jenkins > System Log）
3. 检查 Agent 状态（Manage Jenkins > Nodes）
4. 检查凭证配置
5. 检查插件版本兼容性

**验证**：修复问题后 Pipeline 成功运行

---

## 🎯 面试题精选

### 1. Declarative Pipeline 和 Scripted Pipeline 有什么区别？

**参考答案**：
- **Declarative**：结构化语法，以 `pipeline {}` 开头，更易读和维护，支持 Blue Ocean 可视化编辑，推荐新项目使用
- **Scripted**：Groovy 脚本语法，以 `node {}` 开头，更灵活，适合复杂逻辑，需要 Groovy 知识

Declarative 是 Jenkins 2.x 引入的，旨在降低 Pipeline 编写门槛。两者可以混合使用（在 Declarative 中嵌入 `script {}` 块）。

### 2. 如何实现 Jenkins Pipeline 的代码复用？

**参考答案**：
- **Shared Library**：最常用方式，将通用逻辑抽取为共享库，存储在独立 Git 仓库
- **Template Pipeline**：创建模板 Jenkinsfile，其他项目继承
- **Stages 复用**：在 `script {}` 块中调用外部 Groovy 脚本
- **Docker 镜像**：将构建环境封装为 Docker 镜像

Shared Library 是推荐方式，支持 `vars/`（全局函数）、`src/`（类）、`resources/`（资源文件）。

### 3. Jenkins Master-Agent 架构有什么优势？

**参考答案**：
- **可扩展性**：可以动态添加 Agent，支持水平扩展
- **隔离性**：构建在 Agent 上执行，不影响 Master
- **异构环境**：不同 Agent 可以运行不同 OS、不同工具
- **资源优化**：Agent 可以按需创建（K8s Pod）、用完销毁
- **安全**：Agent 不需要访问 Master 的文件系统

### 4. 如何确保 Jenkins 的安全性？

**参考答案**：
- 启用认证（LDAP/SSO）和授权（RBAC）
- 使用 Credentials Plugin 管理凭证，不在 Jenkinsfile 中硬编码
- 启用 CSRF 防护和 HTTPS
- 使用 Script Security Plugin 的 Groovy 沙箱
- 定期更新 Jenkins 和插件
- 限制 Agent 连接和网络访问
- 启用审计日志（Audit Trail Plugin）

### 5. 什么是 Jenkins 共享库？如何组织？

**参考答案**：
共享库是存储在独立 Git 仓库中的可复用 Pipeline 代码。目录结构：
- `vars/`：全局变量和函数（Pipeline 中直接调用）
- `src/`：Groovy 类（需要 import）
- `resources/`：非 Groovy 资源文件

使用方式：在 Jenkins 中配置共享库（Manage Jenkins > Configure System > Global Pipeline Libraries），然后在 Jenkinsfile 中 `@Library('lib-name') _` 引用。

### 6. 如何优化 Jenkins 构建速度？

**参考答案**：
- 并行执行无依赖 Stage（`parallel {}`）
- 使用 Docker 缓存层
- 配置 Workspace 缓存
- 使用 K8s 动态 Agent（按需创建）
- 优化测试（只运行受影响的测试）
- 使用增量构建
- 配置合理的构建超时

---

## 📚 深入阅读

- [Jenkins 官方文档](https://www.jenkins.io/doc/)
- [Pipeline 语法参考](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Shared Library 文档](https://www.jenkins.io/doc/book/pipeline/shared-libraries/)
- [Blue Ocean 文档](https://www.jenkins.io/doc/book/blueocean/)
- [Jenkins Security](https://www.jenkins.io/doc/book/system-administration/security/)

---

## ✅ 自检清单

- [ ] 理解 Jenkins 架构（Controller-Agent）
- [ ] 能编写 Declarative Pipeline Jenkinsfile
- [ ] 理解 Scripted Pipeline 语法
- [ ] 能创建和使用共享库
- [ ] 了解常用插件及其配置
- [ ] 理解 Blue Ocean 的功能
- [ ] 能配置分布式构建（SSH/Docker/K8s Agent）
- [ ] 掌握 Jenkins 安全加固方法
- [ ] 能使用 Credentials 管理敏感信息
- [ ] 能排查常见的 Jenkins 构建问题
