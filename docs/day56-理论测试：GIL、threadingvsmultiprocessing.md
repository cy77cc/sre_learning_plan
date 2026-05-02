# Day 56: 理论测试 — GIL、threading vs multiprocessing

> 📅 日期：2026-05-02
> 📖 学习主题：理论测试：GIL、threading vs multiprocessing
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 GIL 的本质和影响
- 能正确选择 threading 或 multiprocessing
- 掌握并发编程的常见陷阱

---

## 📖 GIL 详解

### 1. 什么是 GIL

GIL（Global Interpreter Lock）是 CPython 中的一个互斥锁，确保同一时刻只有一个线程执行 Python 字节码。

为什么需要 GIL？
- CPython 的内存管理不是线程安全的
- GIL 简化了 C 扩展的实现
- 代价：多线程不能真正并行执行 CPU 密集型任务

### 2. GIL 的影响

```python
# CPU 密集型 - threading 无效（受 GIL 限制）
import threading
import time

def cpu_work():
    x = 0
    for i in range(10**7):
        x += i

# 串行
start = time.time()
cpu_work()
cpu_work()
print(f"Serial: {time.time()-start:.2f}s")

# 多线程（不会更快！）
start = time.time()
t1 = threading.Thread(target=cpu_work)
t2 = threading.Thread(target=cpu_work)
t1.start(); t2.start()
t1.join(); t2.join()
print(f"Thread: {time.time()-start:.2f}s")  # 差不多甚至更慢

# 多进程（会更快）
import multiprocessing
start = time.time()
p1 = multiprocessing.Process(target=cpu_work)
p2 = multiprocessing.Process(target=cpu_work)
p1.start(); p2.start()
p1.join(); p2.join()
print(f"Process: {time.time()-start:.2f}s")  # 快约 2 倍
```

### 3. 选择指南

| 场景 | 推荐 | 原因 |
|------|------|------|
| HTTP 请求 | ThreadPoolExecutor | I/O 密集，GIL 在等待时释放 |
| 文件读写 | ThreadPoolExecutor | I/O 密集 |
| 数据库查询 | ThreadPoolExecutor | I/O 密集 |
| 数据处理 | ProcessPoolExecutor | CPU 密集，绕过 GIL |
| 加密计算 | ProcessPoolExecutor | CPU 密集 |
| 图像处理 | ProcessPoolExecutor | CPU 密集 |

### 4. 绕过 GIL 的方法

1. 使用 multiprocessing（每个进程有自己的 GIL）
2. 使用 C 扩展（numpy、scipy 等在 C 层释放 GIL）
3. 使用其他 Python 实现（PyPy STM、Jython）
4. Python 3.13+ 的 free-threading 实验功能

---

## 🧪 理论测试题

### 问题 1：以下哪个场景适合用 threading？

A. 计算 100 万个数字的平方和
B. 从 100 个 URL 下载网页
C. 压缩一个大文件
D. 训练一个机器学习模型

<details>
<summary>答案</summary>

B. 从 100 个 URL 下载网页
因为这是 I/O 密集型任务，线程在等待网络响应时会释放 GIL，其他线程可以继续执行。
</details>

### 问题 2：以下代码的输出是什么？

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(100000):
        counter += 1

t1 = threading.Thread(target=increment)
t2 = threading.Thread(target=increment)
t1.start()
t2.start()
t1.join()
t2.join()
print(counter)
```

<details>
<summary>答案</summary>

结果不确定！可能小于 200000。
因为 `counter += 1` 不是原子操作，存在竞态条件。
需要使用 threading.Lock 来保护共享变量：
```python
lock = threading.Lock()
def increment():
    global counter
    for _ in range(100000):
        with lock:
            counter += 1
```
</details>

### 问题 3：GIL 在 Python 3.13 中的变化是什么？

<details>
<summary>答案</summary>

Python 3.13 引入了实验性的 free-threading 模式（PEP 703），
可以通过 `python3.13t` 运行，不再有 GIL。
但这仍然是实验性的，生产环境不建议使用。
</details>

---

## 📚 扩展阅读

- [GIL 官方 Wiki](https://wiki.python.org/moin/GlobalInterpreterLock)
- [David Beazley - GIL 演讲](https://www.dabeaz.com/python/UnderstandingGIL.pdf)
