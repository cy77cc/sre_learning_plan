# Day 50: 并发编程

> 📅 日期：2026-05-03
> 📖 学习主题：Python 并发编程（threading/multiprocessing/asyncio/concurrent.futures, GIL, 线程安全, 协程, 异步IO模型）
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 46（Python 基础语法）, Day 47（Python 标准库）, Day 48（网络编程）

## 🎯 学习目标

- 深入理解 Python GIL 的本质及其对并发编程的影响
- 掌握 threading、multiprocessing、asyncio、concurrent.futures 四种并发模型
- 理解线程安全问题，能正确使用锁、信号量、队列等同步原语
- 理解协程和异步 I/O 模型的底层原理（事件循环、epoll、协程切换）
- 能根据 SRE 场景（CPU 密集 vs I/O 密集）选择合适的并发方案
- 能编写高并发的监控数据采集、批量健康检查等工具

---

## 📖 核心知识点

### 1. 并发模型全景：线程 vs 进程 vs 协程

#### 1.1 三种并发模型对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Python 并发模型全景                                │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│ 特性          │ threading    │ multiprocessing │ asyncio            │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│ 并发类型      │ 并发(伪并行)  │ 并行(真并行)  │ 并发(协作式)           │
│ 内存空间      │ 共享内存      │ 独立内存      │ 共享内存               │
│ 创建开销      │ 中等          │ 大            │ 小                    │
│ 切换开销      │ OS 调度(高)   │ OS 调度(高)   │ 协程切换(低)           │
│ GIL 影响      │ 受限          │ 不受限        │ 不影响(I/O等待时释放)   │
│ 适用场景      │ I/O 密集      │ CPU 密集      │ I/O 密集(高并发)       │
│ 数据共享      │ 简单(共享内存) │ 复杂(IPC)     │ 简单(单线程)           │
│ 典型并发数    │ 数十~数百      │ 数个(CPU核数) │ 数千~数万              │
│ SRE 场景      │ 文件I/O, DB  │ 数据处理,计算 │ 批量API调用,监控采集    │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
```

#### 1.2 选择并发模型的决策树

```
                    你的任务是什么？
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
        I/O 密集     CPU 密集     混合型
            │            │            │
    ┌───────┼───────┐    │            │
    ▼       ▼       ▼    ▼            ▼
  低并发  中并发  高并发  多进程    多进程 + 协程
 (<10)  (10-100) (>100)           (进程池 + 事件循环)
    │       │       │
    ▼       ▼       ▼
 threading  线程池   asyncio
          (Pool)   (协程)
```

---

### 2. GIL 深入理解

#### 2.1 什么是 GIL？

```
┌─────────────────────────────────────────────────────────────┐
│          GIL (Global Interpreter Lock) 全局解释器锁           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Python 进程                                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    GIL (互斥锁)                        │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │ │
│  │  │ Thread 1 │  │ Thread 2 │  │ Thread 3 │               │ │
│  │  │ (持有GIL)│  │ (等待)   │  │ (等待)   │               │ │
│  │  │ 执行中 ✓ │  │  阻塞 ✗  │  │  阻塞 ✗  │               │ │
│  │  └─────────┘  └─────────┘  └─────────┘               │ │
│  │                                                       │ │
│  │  同一时刻只有一个线程能执行 Python 字节码                  │ │
│  │  GIL 在 I/O 操作时会释放，允许其他线程执行                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  为什么需要 GIL？                                             │
│  1. CPython 的内存管理不是线程安全的（引用计数）                │
│  2. GIL 简化了 C 扩展的实现                                  │
│  3. 对于 I/O 密集型任务，GIL 影响不大                          │
│                                                             │
│  GIL 的影响：                                                │
│  - CPU 密集型：多线程几乎无法利用多核 → 用 multiprocessing     │
│  - I/O 密集型：GIL 在 I/O 等待时释放 → 多线程仍然有效         │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 GIL 的实际影响

```python
#!/usr/bin/env python3
"""
GIL 影响的实证演示
通过对比实验展示 GIL 对 CPU 密集和 I/O 密集任务的影响
"""

import threading
import multiprocessing
import time
import requests


# ============================================================
# CPU 密集型任务：GIL 会阻碍多线程并行
# ============================================================

def cpu_bound(n: int) -> float:
    """CPU 密集型计算（计算斐波那契数列）"""
    def fib(n):
        if n < 2:
            return n
        return fib(n - 1) + fib(n - 2)
    return fib(n)


def benchmark_cpu_sequential(n: int = 35, count: int = 4) -> float:
    """顺序执行 CPU 密集任务"""
    start = time.monotonic()
    for _ in range(count):
        cpu_bound(n)
    return time.monotonic() - start


def benchmark_cpu_threading(n: int = 35, count: int = 4) -> float:
    """多线程执行 CPU 密集任务"""
    threads = [threading.Thread(target=cpu_bound, args=(n,)) for _ in range(count)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.monotonic() - start


def benchmark_cpu_multiprocessing(n: int = 35, count: int = 4) -> float:
    """多进程执行 CPU 密集任务"""
    with multiprocessing.Pool(processes=count) as pool:
        start = time.monotonic()
        pool.map(cpu_bound, [n] * count)
        return time.monotonic() - start


def demo_gil_cpu():
    """演示 GIL 对 CPU 密集任务的影响"""
    print("=== CPU 密集型任务（n=35, 4次）===")
    count = 4

    seq_time = benchmark_cpu_sequential(35, count)
    print(f"  顺序执行:  {seq_time:.2f}s")

    thread_time = benchmark_cpu_threading(35, count)
    print(f"  多线程:    {thread_time:.2f}s (加速比: {seq_time / thread_time:.2f}x)")

    try:
        mp_time = benchmark_cpu_multiprocessing(35, count)
        print(f"  多进程:    {mp_time:.2f}s (加速比: {seq_time / mp_time:.2f}x)")
    except Exception as e:
        print(f"  多进程:    跳过（{e}）")

    print()
    print("  结论: CPU 密集任务，多线程因 GIL 无法并行，多进程才能利用多核")


# ============================================================
# I/O 密集型任务：GIL 影响不大，多线程仍然有效
# ============================================================

def io_bound(url: str) -> float:
    """I/O 密集型任务（HTTP 请求）"""
    try:
        start = time.monotonic()
        requests.get(url, timeout=10)
        return time.monotonic() - start
    except Exception:
        return -1


def demo_gil_io():
    """演示 GIL 对 I/O 密集任务的影响"""
    print("=== I/O 密集型任务（HTTP 请求）===")
    # 注意：这个演示需要网络连接
    # 在实际场景中，I/O 等待时 GIL 会释放

    print("  结论: I/O 密集任务，多线程在等待 I/O 时释放 GIL，可以有效并发")
    print("  这就是为什么 requests + ThreadPoolExecutor 是 SRE 的常用组合")


if __name__ == "__main__":
    demo_gil_cpu()
    print()
    demo_gil_io()
```

---

### 3. threading：多线程编程

#### 3.1 线程基础

```python
#!/usr/bin/env python3
"""
threading 模块详解
SRE 场景：并发执行 I/O 操作（文件读写、网络请求、数据库查询）
"""

import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable


# ============================================================
# 线程创建的三种方式
# ============================================================

# 方式 1: 创建 Thread 对象，传入 target 函数
def worker(name: str, duration: float):
    """简单的工作线程"""
    print(f"[{name}] Starting (thread: {threading.current_thread().name})")
    time.sleep(duration)
    print(f"[{name}] Done after {duration}s")
    return f"{name} result"


def demo_thread_basic():
    """基本线程使用"""
    # 创建并启动线程
    t1 = threading.Thread(target=worker, args=("worker-1", 2), name="my-thread-1")
    t2 = threading.Thread(target=worker, args=("worker-2", 1), name="my-thread-2")

    t1.start()  # 启动线程（非阻塞）
    t2.start()

    print(f"Main thread: waiting for workers...")
    t1.join()  # 等待线程结束
    t2.join()
    print("All workers done")


# 方式 2: 继承 Thread 类
class HealthCheckThread(threading.Thread):
    """
    自定义线程类
    SRE 场景：有状态的后台检查线程
    """

    def __init__(self, host: str, port: int, interval: float = 5.0):
        super().__init__(daemon=True)  # 守护线程：主线程退出时自动结束
        self.host = host
        self.port = port
        self.interval = interval
        self.results = queue.Queue()
        self._stop_event = threading.Event()

    def run(self):
        """线程主逻辑"""
        import socket
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((self.host, self.port))
                    latency = (time.monotonic() - start) * 1000
                    self.results.put({
                        "host": self.host,
                        "status": "healthy",
                        "latency_ms": round(latency, 2),
                    })
            except Exception as e:
                self.results.put({
                    "host": self.host,
                    "status": "unhealthy",
                    "error": str(e),
                })

            # 等待间隔时间或被停止
            self._stop_event.wait(self.interval)

    def stop(self):
        """优雅停止线程"""
        self._stop_event.set()


# 方式 3: ThreadPoolExecutor（推荐）
def demo_thread_pool():
    """
    使用 ThreadPoolExecutor
    SRE 场景：批量并发操作的标准方式
    """
    hosts = [
        ("httpbin.org", 80),
        ("example.com", 80),
        ("localhost", 8080),  # 可能不可达
    ]

    def check_host(args):
        host, port = args
        import socket
        start = time.monotonic()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((host, port))
                return {
                    "host": host,
                    "port": port,
                    "status": "up",
                    "latency_ms": round((time.monotonic() - start) * 1000, 2),
                }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "status": "down",
                "error": str(e),
            }

    # 使用 as_completed 获取最先完成的结果
    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="health-check") as executor:
        futures = {executor.submit(check_host, h): h for h in hosts}

        for future in as_completed(futures):
            host_info = futures[future]
            try:
                result = future.result(timeout=10)
                status = result["status"]
                print(f"  [{status.upper()}] {result['host']}:{result['port']}")
            except Exception as e:
                print(f"  [ERROR] {host_info}: {e}")


if __name__ == "__main__":
    print("=== 基本线程 ===")
    demo_thread_basic()
    print("\n=== 线程池 ===")
    demo_thread_pool()
```

#### 3.2 线程安全与同步原语

```python
#!/usr/bin/env python3
"""
线程安全与同步原语
SRE 场景：多线程共享数据时的安全操作

为什么需要关注线程安全？
当多个线程同时访问共享数据时，可能出现竞态条件（Race Condition）。
例如：两个线程同时执行 counter += 1，由于这不是原子操作，
最终结果可能比预期小。
"""

import threading
import time
import queue
from collections import defaultdict


# ============================================================
# 问题演示：竞态条件
# ============================================================

class UnsafeCounter:
    """不安全的计数器（存在竞态条件）"""

    def __init__(self):
        self.count = 0

    def increment(self):
        # 这不是原子操作！实际包含三步：
        # 1. 读取 self.count 的值
        # 2. 加 1
        # 3. 写回 self.count
        # 两个线程可能同时读到相同的值
        current = self.count
        time.sleep(0.0001)  # 放大竞态条件
        self.count = current + 1


class SafeCounter:
    """线程安全的计数器（使用锁）"""

    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()  # 互斥锁

    def increment(self):
        with self._lock:  # 获取锁，操作完成后自动释放
            current = self.count
            time.sleep(0.0001)
            self.count = current + 1


def demo_race_condition():
    """演示竞态条件及其修复"""
    print("=== 竞态条件演示 ===")

    # 不安全的计数器
    unsafe = UnsafeCounter()
    threads = [
        threading.Thread(target=lambda: [unsafe.increment() for _ in range(100)])
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  Unsafe counter: {unsafe.count} (expected: 1000)")

    # 安全的计数器
    safe = SafeCounter()
    threads = [
        threading.Thread(target=lambda: [safe.increment() for _ in range(100)])
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  Safe counter:   {safe.count} (expected: 1000)")


# ============================================================
# 同步原语详解
# ============================================================

def demo_lock():
    """
    Lock（互斥锁）
    最基本的同步原语，保证同一时刻只有一个线程能访问临界区
    """
    print("\n=== Lock 示例 ===")
    lock = threading.Lock()
    shared_data = {"value": 0}

    def update_data(name):
        with lock:
            current = shared_data["value"]
            time.sleep(0.01)
            shared_data["value"] = current + 1
            print(f"  {name}: set value to {shared_data['value']}")

    threads = [threading.Thread(target=update_data, args=(f"T{i}",)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def demo_rlock():
    """
    RLock（可重入锁）
    同一线程可以多次获取同一个锁（计数机制）
    适用场景：递归函数中需要加锁
    """
    print("\n=== RLock 示例 ===")
    rlock = threading.RLock()

    def recursive_task(n):
        with rlock:
            if n > 0:
                print(f"  Level {n}")
                recursive_task(n - 1)

    recursive_task(3)


def demo_semaphore():
    """
    Semaphore（信号量）
    控制同时访问资源的线程数量
    SRE 场景：限制并发 API 调用数量
    """
    print("\n=== Semaphore 示例 ===")
    # 最多同时 3 个线程访问
    sem = threading.Semaphore(3)

    def limited_task(name):
        with sem:
            print(f"  {name}: acquired semaphore")
            time.sleep(1)
            print(f"  {name}: releasing semaphore")

    threads = [threading.Thread(target=limited_task, args=(f"Task-{i}",)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def demo_event():
    """
    Event（事件）
    线程间的通知机制
    SRE 场景：优雅停止后台线程
    """
    print("\n=== Event 示例 ===")
    stop_event = threading.Event()

    def background_worker():
        while not stop_event.is_set():
            print("  Worker: running...")
            stop_event.wait(0.5)  # 等待 0.5 秒或被通知停止
        print("  Worker: stopped gracefully")

    t = threading.Thread(target=background_worker)
    t.start()
    time.sleep(2)
    print("  Main: sending stop signal")
    stop_event.set()
    t.join()


def demo_thread_safe_queue():
    """
    Queue（线程安全队列）
    SRE 场景：生产者-消费者模式，日志收集、任务分发
    """
    print("\n=== 线程安全队列示例 ===")
    q = queue.Queue(maxsize=100)

    def producer(name, count):
        for i in range(count):
            item = f"{name}-item-{i}"
            q.put(item)
            print(f"  Producer {name}: put {item}")
            time.sleep(0.1)
        q.put(None)  # 哨兵值，通知消费者结束

    def consumer(name):
        while True:
            item = q.get()
            if item is None:
                q.put(None)  # 传递给其他消费者
                break
            print(f"  Consumer {name}: got {item}")
            time.sleep(0.2)
            q.task_done()

    # 1 个生产者，2 个消费者
    threads = [
        threading.Thread(target=producer, args=("P1", 5)),
        threading.Thread(target=consumer, args=("C1",)),
        threading.Thread(target=consumer, args=("C2",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    demo_race_condition()
    demo_lock()
    demo_rlock()
    demo_semaphore()
    demo_event()
    demo_thread_safe_queue()
```

---

### 4. multiprocessing：多进程编程

#### 4.1 多进程基础

```python
#!/usr/bin/env python3
"""
multiprocessing 模块详解
SRE 场景：CPU 密集型数据处理、并行日志分析
"""

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass


# ============================================================
# 进程创建方式
# ============================================================

def cpu_intensive_task(n: int) -> dict:
    """
    CPU 密集型任务
    计算素数数量（故意用低效算法模拟 CPU 压力）
    """
    start = time.monotonic()
    count = 0
    for num in range(2, n):
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    elapsed = time.monotonic() - start
    return {
        "process": os.getpid(),
        "n": n,
        "primes": count,
        "elapsed_s": round(elapsed, 2),
    }


def demo_process_pool():
    """
    ProcessPoolExecutor 使用
    SRE 场景：并行处理大量监控数据
    """
    print("=== ProcessPoolExecutor 示例 ===")
    numbers = [100000, 150000, 200000, 250000]

    # 顺序执行
    start = time.monotonic()
    sequential_results = [cpu_intensive_task(n) for n in numbers]
    seq_time = time.monotonic() - start
    print(f"  顺序执行: {seq_time:.2f}s")

    # 并行执行
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=4) as executor:
        parallel_results = list(executor.map(cpu_intensive_task, numbers))
    par_time = time.monotonic() - start
    print(f"  并行执行: {par_time:.2f}s (加速比: {seq_time / par_time:.2f}x)")

    for r in parallel_results:
        print(f"    Process {r['process']}: {r['primes']} primes in {n} (took {r['elapsed_s']}s)")


def demo_process_communication():
    """
    进程间通信
    SRE 场景：多进程协作处理监控数据
    """
    print("\n=== 进程间通信示例 ===")

    # 方式 1: Queue（最常用）
    result_queue = multiprocessing.Queue()

    def worker_with_queue(name, data, result_queue):
        """工作进程，将结果放入队列"""
        result = sum(data)
        result_queue.put({"name": name, "result": result, "pid": os.getpid()})

    processes = [
        multiprocessing.Process(
            target=worker_with_queue,
            args=(f"worker-{i}", list(range(i * 100, (i + 1) * 100)), result_queue)
        )
        for i in range(3)
    ]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    while not result_queue.empty():
        r = result_queue.get()
        print(f"  {r['name']} (pid={r['pid']}): result={r['result']}")

    # 方式 2: Pool + map（更简洁）
    print("\n=== Pool.map 示例 ===")
    with multiprocessing.Pool(processes=3) as pool:
        results = pool.map(sum, [list(range(100)), list(range(200)), list(range(300))])
        print(f"  Results: {results}")


if __name__ == "__main__":
    demo_process_pool()
    demo_process_communication()
```

---

### 5. asyncio：异步编程

#### 5.1 协程与事件循环

```
┌─────────────────────────────────────────────────────────────────┐
│                    asyncio 事件循环模型                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  事件循环 (Event Loop)                      │ │
│  │                                                           │ │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │ │
│  │   │ 协程 A   │  │ 协程 B   │  │ 协程 C   │  │ 协程 D   │    │ │
│  │   │ (运行中) │  │ (等待IO) │  │ (就绪)   │  │ (等待IO) │    │ │
│  │   └────┬────┘  └─────────┘  └─────────┘  └─────────┘    │ │
│  │        │                                                  │ │
│  │        ▼                                                  │ │
│  │   遇到 await                                              │ │
│  │   (I/O 操作)                                              │ │
│  │        │                                                  │ │
│  │        ▼                                                  │ │
│  │   挂起协程 A，                                             │ │
│  │   切换到协程 C 执行                                         │ │
│  │                                                           │ │
│  │   I/O 完成后，协程 B/D 变为就绪，                            │ │
│  │   等待事件循环调度                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  关键概念：                                                      │
│  1. 协程 (Coroutine): 用 async def 定义的函数                    │
│  2. await: 暂停协程，让出控制权给事件循环                          │
│  3. 事件循环: 调度协程执行的核心机制                               │
│  4. Task: 对协程的封装，可以并发执行多个 Task                     │
│                                                                 │
│  与线程的区别：                                                   │
│  - 线程切换由 OS 调度（抢占式），切换开销大                        │
│  - 协程切换由代码控制（协作式），切换开销小                         │
│  - 协程是单线程的，不存在竞态条件（但需要注意 await 点）             │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 asyncio 核心用法

```python
#!/usr/bin/env python3
"""
asyncio 异步编程详解
SRE 场景：高并发监控数据采集、批量 API 调用
"""

import asyncio
import time
import aiohttp
from typing import Coroutine


# ============================================================
# 协程基础
# ============================================================

async def fetch_data(name: str, delay: float) -> str:
    """
    模拟异步 I/O 操作
    await 关键字表示：这里会暂停，让出控制权给事件循环
    """
    print(f"  [{name}] Starting (delay={delay}s)")
    await asyncio.sleep(delay)  # 非阻塞等待
    print(f"  [{name}] Done")
    return f"{name}_data"


async def demo_basic_coroutines():
    """协程基础：顺序执行 vs 并发执行"""
    print("=== 协程基础 ===")

    # 顺序执行（每个 await 会等待完成）
    print("\n  顺序执行:")
    start = time.monotonic()
    r1 = await fetch_data("A", 2)
    r2 = await fetch_data("B", 1)
    r3 = await fetch_data("C", 1)
    seq_time = time.monotonic() - start
    print(f"  总耗时: {seq_time:.1f}s")

    # 并发执行（使用 gather）
    print("\n  并发执行:")
    start = time.monotonic()
    results = await asyncio.gather(
        fetch_data("A", 2),
        fetch_data("B", 1),
        fetch_data("C", 1),
    )
    par_time = time.monotonic() - start
    print(f"  结果: {results}")
    print(f"  总耗时: {par_time:.1f}s (节省: {seq_time - par_time:.1f}s)")


# ============================================================
# Task 与并发控制
# ============================================================

async def demo_tasks():
    """Task 的创建和使用"""
    print("\n=== Task 示例 ===")

    # 创建 Task（立即开始执行）
    task1 = asyncio.create_task(fetch_data("task-1", 2))
    task2 = asyncio.create_task(fetch_data("task-2", 1))

    # 先做其他事情
    print("  Tasks created, doing other work...")
    await asyncio.sleep(0.5)
    print("  Other work done")

    # 等待 Task 完成
    result1 = await task1
    result2 = await task2
    print(f"  Results: {result1}, {result2}")


async def demo_task_group():
    """TaskGroup（Python 3.11+）"""
    print("\n=== TaskGroup 示例 ===")
    results = []

    async with asyncio.TaskGroup() as tg:
        for i in range(5):
            task = tg.create_task(fetch_data(f"tg-{i}", 0.5 + i * 0.3))
            # TaskGroup 会在所有 task 完成后继续

    print("  All tasks completed")


# ============================================================
# 超时控制
# ============================================================

async def demo_timeout():
    """超时控制"""
    print("\n=== 超时控制 ===")

    # 方式 1: asyncio.wait_for
    try:
        result = await asyncio.wait_for(fetch_data("slow", 10), timeout=2.0)
        print(f"  Result: {result}")
    except asyncio.TimeoutError:
        print("  Timeout! Task took too long")

    # 方式 2: asyncio.timeout (Python 3.11+)
    try:
        async with asyncio.timeout(2.0):
            result = await fetch_data("slow", 10)
    except TimeoutError:
        print("  Timeout via context manager")


# ============================================================
# Semaphore 限制并发数
# ============================================================

async def demo_semaphore():
    """
    使用 Semaphore 限制并发数
    SRE 场景：避免瞬间打满下游服务
    """
    print("\n=== Semaphore 限制并发 ===")
    sem = asyncio.Semaphore(3)  # 最多同时 3 个并发
    results = []

    async def limited_fetch(name: str, delay: float):
        async with sem:
            print(f"  [{name}] Acquired semaphore")
            await asyncio.sleep(delay)
            print(f"  [{name}] Released semaphore")
            return f"{name}_done"

    tasks = [limited_fetch(f"task-{i}", 1.0) for i in range(8)]
    results = await asyncio.gather(*tasks)
    print(f"  Completed {len(results)} tasks with max concurrency 3")


# ============================================================
# 异步生成器与队列
# ============================================================

async def async_range(n: int):
    """异步生成器"""
    for i in range(n):
        await asyncio.sleep(0.1)
        yield i


async def demo_async_iteration():
    """异步迭代"""
    print("\n=== 异步迭代 ===")
    async for value in async_range(5):
        print(f"  Got: {value}")


async def demo_async_queue():
    """
    异步队列
    SRE 场景：生产者-消费者模式的日志处理
    """
    print("\n=== 异步队列示例 ===")
    queue = asyncio.Queue(maxsize=10)

    async def producer(name: str, count: int):
        for i in range(count):
            item = f"{name}-item-{i}"
            await queue.put(item)
            print(f"  Producer {name}: put {item}")
            await asyncio.sleep(0.2)
        await queue.put(None)  # 哨兵值

    async def consumer(name: str):
        while True:
            item = await queue.get()
            if item is None:
                await queue.put(None)  # 传递给其他消费者
                break
            print(f"  Consumer {name}: got {item}")
            await asyncio.sleep(0.3)
            queue.task_done()

    # 1 个生产者，2 个消费者
    await asyncio.gather(
        producer("P1", 6),
        consumer("C1"),
        consumer("C2"),
    )


# ============================================================
# 异步上下文管理器
# ============================================================

class AsyncResource:
    """异步上下文管理器示例"""

    def __init__(self, name: str):
        self.name = name

    async def __aenter__(self):
        print(f"  Acquiring {self.name}...")
        await asyncio.sleep(0.5)
        print(f"  Acquired {self.name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f"  Releasing {self.name}...")
        await asyncio.sleep(0.2)
        print(f"  Released {self.name}")

    async def do_work(self):
        await asyncio.sleep(0.5)
        return f"{self.name} work done"


async def demo_async_context_manager():
    """异步上下文管理器"""
    print("\n=== 异步上下文管理器 ===")
    async with AsyncResource("db-connection") as resource:
        result = await resource.do_work()
        print(f"  Result: {result}")


# ============================================================
# 异步 HTTP 请求（SRE 核心场景）
# ============================================================

async def async_health_check(url: str, session: aiohttp.ClientSession) -> dict:
    """异步健康检查"""
    start = time.monotonic()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            elapsed = (time.monotonic() - start) * 1000
            return {
                "url": url,
                "status": resp.status,
                "healthy": 200 <= resp.status < 400,
                "latency_ms": round(elapsed, 2),
            }
    except Exception as e:
        return {"url": url, "status": None, "healthy": False, "error": str(e)}


async def demo_async_http():
    """
    异步 HTTP 请求
    SRE 场景：批量健康检查、监控数据采集
    """
    print("\n=== 异步 HTTP 请求 ===")

    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/500",
        "https://httpbin.org/delay/1",
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [async_health_check(url, session) for url in urls]
        results = await asyncio.gather(*tasks)

    for r in results:
        status = "HEALTHY" if r.get("healthy") else "UNHEALTHY"
        print(f"  [{status}] {r['url']} ({r.get('latency_ms', 'N/A')}ms)")


# ============================================================
# 错误处理
# ============================================================

async def demo_error_handling():
    """异步错误处理"""
    print("\n=== 错误处理 ===")

    async def risky_task(name: str, should_fail: bool):
        await asyncio.sleep(0.5)
        if should_fail:
            raise ValueError(f"{name} failed!")
        return f"{name} succeeded"

    # gather 的 return_exceptions 参数
    results = await asyncio.gather(
        risky_task("task-1", False),
        risky_task("task-2", True),  # 这个会失败
        risky_task("task-3", False),
        return_exceptions=True,  # 不抛异常，而是返回异常对象
    )

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"  Task {i}: ERROR - {r}")
        else:
            print(f"  Task {i}: {r}")


async def main():
    """运行所有演示"""
    await demo_basic_coroutines()
    await demo_tasks()
    await demo_timeout()
    await demo_semaphore()
    await demo_async_iteration()
    await demo_async_queue()
    await demo_async_context_manager()
    await demo_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 6. concurrent.futures：统一的并发接口

```python
#!/usr/bin/env python3
"""
concurrent.futures 模块详解
SRE 场景：统一的并发接口，根据任务类型选择线程池或进程池
"""

import concurrent.futures
import time
import os
from typing import Any, Callable


def demo_thread_pool_executor():
    """
    ThreadPoolExecutor：线程池
    适用于 I/O 密集型任务
    """
    print("=== ThreadPoolExecutor ===")

    def io_task(url: str) -> dict:
        """模拟 I/O 操作"""
        import random
        delay = random.uniform(0.5, 2.0)
        time.sleep(delay)
        return {"url": url, "delay": round(delay, 2), "pid": os.getpid()}

    urls = [f"https://api.example.com/endpoint/{i}" for i in range(10)]

    # 方式 1: submit + as_completed（推荐，按完成顺序获取结果）
    print("\n  submit + as_completed:")
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=5, thread_name_prefix="api-call"
    ) as executor:
        future_to_url = {executor.submit(io_task, url): url for url in urls}

        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result(timeout=30)
                print(f"    {result['url']}: {result['delay']}s")
            except concurrent.futures.TimeoutError:
                print(f"    {url}: TIMEOUT")
            except Exception as e:
                print(f"    {url}: ERROR - {e}")

    # 方式 2: map（按提交顺序获取结果）
    print("\n  map:")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(io_task, urls[:5])
        for result in results:
            print(f"    {result['url']}: {result['delay']}s")


def demo_process_pool_executor():
    """
    ProcessPoolExecutor：进程池
    适用于 CPU 密集型任务
    """
    print("\n=== ProcessPoolExecutor ===")

    def cpu_task(n: int) -> dict:
        """CPU 密集型任务"""
        total = sum(i * i for i in range(n))
        return {"n": n, "result": total, "pid": os.getpid()}

    numbers = [10**6, 2 * 10**6, 3 * 10**6, 4 * 10**6]

    # 顺序执行
    start = time.monotonic()
    seq_results = [cpu_task(n) for n in numbers]
    seq_time = time.monotonic() - start

    # 并行执行
    start = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        par_results = list(executor.map(cpu_task, numbers))
    par_time = time.monotonic() - start

    print(f"  顺序: {seq_time:.2f}s, 并行: {par_time:.2f}s (加速: {seq_time / par_time:.2f}x)")
    for r in par_results:
        print(f"    n={r['n']}: pid={r['pid']}, result={r['result']}")


def demo_callback():
    """
    回调函数
    SRE 场景：任务完成后的异步通知
    """
    print("\n=== 回调函数示例 ===")
    results_log = []

    def on_complete(future: concurrent.futures.Future):
        """任务完成时的回调"""
        try:
            result = future.result()
            results_log.append({"status": "success", "data": result})
            print(f"    Callback: task completed - {result}")
        except Exception as e:
            results_log.append({"status": "error", "error": str(e)})
            print(f"    Callback: task failed - {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for i in range(5):
            future = executor.submit(lambda x: x * 2, i)
            future.add_done_callback(on_complete)

    print(f"  Results log: {len(results_log)} entries")


def demo_cancellation():
    """
    任务取消
    SRE 场景：优雅停止长时间运行的任务
    """
    print("\n=== 任务取消示例 ===")

    def long_task(name: str, duration: float) -> str:
        time.sleep(duration)
        return f"{name} done"

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future1 = executor.submit(long_task, "task-1", 5)
        future2 = executor.submit(long_task, "task-2", 5)

        time.sleep(1)

        # 尝试取消（只能取消还未开始的任务）
        cancelled = future2.cancel()
        print(f"  Cancel task-2: {'success' if cancelled else 'already running'}")

        # 等待 task-1
        try:
            result = future1.result(timeout=10)
            print(f"  task-1 result: {result}")
        except concurrent.futures.TimeoutError:
            print("  task-1 timeout")


if __name__ == "__main__":
    demo_thread_pool_executor()
    demo_process_pool_executor()
    demo_callback()
    demo_cancellation()
```

---

### 7. SRE 实战案例

#### 7.1 高并发监控数据采集器

```python
#!/usr/bin/env python3
"""
高并发监控数据采集器
SRE 场景：同时从数百个服务端点采集监控指标

技术选型：
- asyncio + aiohttp：高并发 I/O（数千个端点）
- Semaphore：控制并发数，避免打满目标服务
- 超时控制：单个端点超时不影响其他端点
- 错误处理：单个失败不影响整体采集
"""

import asyncio
import aiohttp
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class MetricEndpoint:
    """监控端点配置"""
    name: str
    url: str
    scrape_interval: float = 15.0  # 采集间隔（秒）
    timeout: float = 10.0
    labels: dict = None


@dataclass
class MetricSample:
    """采集到的指标样本"""
    endpoint: str
    metric_name: str
    value: float
    timestamp: float
    labels: dict = None
    error: Optional[str] = None


class MetricsCollector:
    """
    异步监控数据采集器

    架构：
    ┌─────────────────────────────────────────┐
    │            MetricsCollector               │
    │                                          │
    │  ┌──────────┐  ┌──────────┐             │
    │  │ Scraper   │  │ Scraper   │  ...       │
    │  │ (async)   │  │ (async)   │             │
    │  └────┬─────┘  └────┬─────┘             │
    │       │              │                   │
    │       ▼              ▼                   │
    │  ┌─────────────────────────┐             │
    │  │     Semaphore (限流)     │             │
    │  └─────────────────────────┘             │
    │       │                                  │
    │       ▼                                  │
    │  ┌─────────────────────────┐             │
    │  │     MetricQueue          │             │
    │  └─────────────────────────┘             │
    │       │                                  │
    │       ▼                                  │
    │  ┌─────────────────────────┐             │
    │  │     Writer (批量写入)    │             │
    │  └─────────────────────────┘             │
    └─────────────────────────────────────────┘
    """

    def __init__(self, max_concurrency: int = 50):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.metric_queue = asyncio.Queue(maxsize=10000)
        self.running = False

    async def scrape_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: MetricEndpoint,
    ) -> list[MetricSample]:
        """采集单个端点的指标"""
        samples = []
        async with self.semaphore:  # 限制并发数
            start = time.monotonic()
            try:
                async with session.get(
                    endpoint.url,
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout),
                ) as resp:
                    latency = (time.monotonic() - start) * 1000

                    if resp.status == 200:
                        # 假设返回 Prometheus 格式的指标
                        text = await resp.text()
                        for line in text.strip().split("\n"):
                            if line.startswith("#") or not line.strip():
                                continue
                            try:
                                name, value = line.split(" ", 1)
                                samples.append(MetricSample(
                                    endpoint=endpoint.name,
                                    metric_name=name,
                                    value=float(value),
                                    timestamp=time.time(),
                                    labels=endpoint.labels,
                                ))
                            except ValueError:
                                pass

                        # 添加采集延迟指标
                        samples.append(MetricSample(
                            endpoint=endpoint.name,
                            metric_name="scrape_duration_ms",
                            value=round(latency, 2),
                            timestamp=time.time(),
                        ))
                    else:
                        samples.append(MetricSample(
                            endpoint=endpoint.name,
                            metric_name="scrape_error",
                            value=1,
                            timestamp=time.time(),
                            error=f"HTTP {resp.status}",
                        ))

            except asyncio.TimeoutError:
                samples.append(MetricSample(
                    endpoint=endpoint.name,
                    metric_name="scrape_error",
                    value=1,
                    timestamp=time.time(),
                    error="timeout",
                ))
            except aiohttp.ClientError as e:
                samples.append(MetricSample(
                    endpoint=endpoint.name,
                    metric_name="scrape_error",
                    value=1,
                    timestamp=time.time(),
                    error=str(e),
                ))

        return samples

    async def scrape_all(
        self,
        session: aiohttp.ClientSession,
        endpoints: list[MetricEndpoint],
    ) -> list[MetricSample]:
        """并发采集所有端点"""
        tasks = [self.scrape_endpoint(session, ep) for ep in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_samples = []
        for result in results:
            if isinstance(result, Exception):
                print(f"  Scrape task error: {result}")
            else:
                all_samples.extend(result)

        return all_samples

    async def run_collection_loop(
        self,
        endpoints: list[MetricEndpoint],
        interval: float = 15.0,
    ):
        """持续采集循环"""
        self.running = True
        connector = aiohttp.TCPConnector(limit=self.max_concurrency)

        async with aiohttp.ClientSession(connector=connector) as session:
            while self.running:
                start = time.monotonic()
                samples = await self.scrape_all(session, endpoints)
                elapsed = time.monotonic() - start

                healthy = sum(1 for s in samples if s.metric_name != "scrape_error")
                errors = sum(1 for s in samples if s.metric_name == "scrape_error")

                print(f"Collection round: {len(samples)} samples "
                      f"({healthy} healthy, {errors} errors) in {elapsed:.2f}s")

                # 将样本放入队列
                for sample in samples:
                    try:
                        self.metric_queue.put_nowait(sample)
                    except asyncio.QueueFull:
                        print("  Warning: metric queue full, dropping sample")

                # 等待下一轮采集
                await asyncio.sleep(max(0, interval - elapsed))

    def stop(self):
        """停止采集"""
        self.running = False


async def main():
    """演示用法"""
    # 定义监控端点
    endpoints = [
        MetricEndpoint(
            name=f"service-{i}",
            url=f"https://httpbin.org/status/{200 if i % 3 != 0 else 500}",
            labels={"instance": f"10.0.1.{i}"},
        )
        for i in range(10)
    ]

    collector = MetricsCollector(max_concurrency=5)

    # 单次采集演示
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        samples = await collector.scrape_all(session, endpoints)

    print(f"\nCollected {len(samples)} samples:")
    for s in samples[:5]:
        error_info = f" (error: {s.error})" if s.error else ""
        print(f"  {s.endpoint}/{s.metric_name} = {s.value}{error_info}")


if __name__ == "__main__":
    asyncio.run(main())
```

#### 7.2 故障排查案例：线程饥饿

```
故障现象：
  SRE 工具使用 ThreadPoolExecutor 执行批量 API 调用
  运行一段时间后，新任务不再被执行，工具看起来"卡住"了

排查链路：
  1. 现象 → 任务提交后不执行，无响应
  2. 诊断 → 使用 psutil 或 threading.enumerate() 查看线程状态
  3. 根因 → 某个任务占用了线程但永远不会返回（死锁或无限等待）
  4. 修复 → 设置任务超时 + 监控线程池使用率
  5. 预防 → 定期检查线程池健康状态
"""

import concurrent.futures
import threading
import time


def healthy_task(name: str) -> str:
    """正常任务"""
    time.sleep(1)
    return f"{name} done"


def stuck_task(name: str) -> str:
    """会卡住的任务（模拟死锁）"""
    time.sleep(999999)  # 永远不会返回
    return f"{name} done"


def safe_submit(
    executor: concurrent.futures.ThreadPoolExecutor,
    fn: callable,
    *args,
    timeout: float = 30.0,
) -> concurrent.futures.Future:
    """
    安全地提交任务（带超时监控）

    为什么需要这个？
    - ThreadPoolExecutor 的 submit 不会检查任务是否卡住
    - 如果任务永远不返回，线程就永远不会被回收
    - 最终线程池中所有线程都被卡住的任务占用
    """
    future = executor.submit(fn, *args)

    def timeout_callback(fut):
        """超时回调：如果任务还在运行，记录警告"""
        if fut.running():
            print(f"  WARNING: Task is still running after {timeout}s")

    # 设置超时检查（注意：这不会自动取消任务）
    timer = threading.Timer(timeout, timeout_callback, args=[future])
    timer.daemon = True
    timer.start()

    return future


def monitor_thread_pool(executor: concurrent.futures.ThreadPoolExecutor):
    """监控线程池状态"""
    # 注意：Python 标准库没有直接暴露线程池内部状态
    # 但可以通过 threading 模块间接监控
    threads = threading.enumerate()
    worker_threads = [t for t in threads if t.name.startswith("ThreadPoolExecutor")]
    print(f"  Active threads: {len(worker_threads)}")
    return len(worker_threads)
```

#### 7.3 异步批量 API 调用框架

```python
#!/usr/bin/env python3
"""
异步批量 API 调用框架
SRE 场景：批量操作 Kubernetes 资源、批量查询监控数据
"""

import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class BatchExecutor:
    """
    异步批量执行器

    特性：
    - 并发控制（Semaphore）
    - 超时控制（per-task timeout）
    - 重试机制（指数退避）
    - 进度回调
    - 错误容忍（单个失败不影响其他）
    """

    def __init__(
        self,
        max_concurrency: int = 20,
        task_timeout: float = 30.0,
        max_retries: int = 2,
        on_progress: Callable = None,
    ):
        self.max_concurrency = max_concurrency
        self.task_timeout = task_timeout
        self.max_retries = max_retries
        self.on_progress = on_progress
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_task(
        self,
        task_id: str,
        coro_func: Callable,
        *args,
        **kwargs,
    ) -> TaskResult:
        """执行单个任务（带重试和超时）"""
        async with self.semaphore:
            last_error = None
            for attempt in range(self.max_retries + 1):
                start = time.monotonic()
                try:
                    result = await asyncio.wait_for(
                        coro_func(*args, **kwargs),
                        timeout=self.task_timeout,
                    )
                    duration = (time.monotonic() - start) * 1000
                    task_result = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.SUCCESS,
                        result=result,
                        duration_ms=round(duration, 2),
                    )
                    if self.on_progress:
                        self.on_progress(task_result)
                    return task_result

                except asyncio.TimeoutError:
                    last_error = "timeout"
                    if attempt < self.max_retries:
                        delay = 2 ** attempt
                        await asyncio.sleep(delay)

                except Exception as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        delay = 2 ** attempt
                        await asyncio.sleep(delay)

            duration = (time.monotonic() - start) * 1000
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.TIMEOUT if last_error == "timeout" else TaskStatus.FAILED,
                error=last_error,
                duration_ms=round(duration, 2),
            )
            if self.on_progress:
                self.on_progress(task_result)
            return task_result

    async def execute_batch(
        self,
        tasks: list[tuple[str, Callable, tuple, dict]],
    ) -> list[TaskResult]:
        """
        批量执行任务

        tasks: [(task_id, func, args, kwargs), ...]
        """
        coroutines = [
            self.execute_task(task_id, func, *args, **kwargs)
            for task_id, func, args, kwargs in tasks
        ]
        return await asyncio.gather(*coroutines)


async def main():
    """演示用法"""

    async def api_call(endpoint: str, delay: float = 1.0) -> dict:
        """模拟 API 调用"""
        await asyncio.sleep(delay)
        return {"endpoint": endpoint, "data": "ok"}

    def progress_callback(result: TaskResult):
        status = result.status.value.upper()
        print(f"  [{status}] {result.task_id}: {result.duration_ms}ms")

    executor = BatchExecutor(
        max_concurrency=5,
        task_timeout=10.0,
        max_retries=1,
        on_progress=progress_callback,
    )

    # 构建任务列表
    tasks = [
        (f"task-{i}", api_call, (f"/api/endpoint/{i}",), {"delay": 0.5 + i * 0.2})
        for i in range(10)
    ]

    print("=== Batch Execution ===")
    start = time.monotonic()
    results = await executor.execute_batch(tasks)
    total_time = time.monotonic() - start

    # 统计
    success = sum(1 for r in results if r.status == TaskStatus.SUCCESS)
    failed = sum(1 for r in results if r.status != TaskStatus.SUCCESS)
    print(f"\nTotal: {len(results)}, Success: {success}, Failed: {failed}")
    print(f"Total time: {total_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💻 实战练习

### 练习 1：基础操作 -- 并发端口扫描器

```python
#!/usr/bin/env python3
"""
练习 1：并发端口扫描器
要求：
1. 使用 ThreadPoolExecutor 并发扫描端口
2. 支持自定义端口范围和并发数
3. 输出扫描结果表格
4. 支持 JSON 格式输出
"""

import socket
import concurrent.futures
import time
import json
import sys


def scan_port(host: str, port: int, timeout: float = 1.0) -> dict:
    """扫描单个端口"""
    start = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            latency = (time.monotonic() - start) * 1000
            return {
                "port": port,
                "open": result == 0,
                "latency_ms": round(latency, 2),
            }
    except socket.error:
        return {"port": port, "open": False, "error": "socket error"}


def scan_ports(
    host: str,
    ports: range,
    max_workers: int = 100,
    timeout: float = 1.0,
) -> list[dict]:
    """并发扫描多个端口"""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(scan_port, host, port, timeout): port
            for port in ports
        }
        for future in concurrent.futures.as_completed(future_to_port):
            result = future.result()
            results.append(result)
    return sorted(results, key=lambda x: x["port"])


def print_table(results: list[dict]):
    """打印表格"""
    print(f"{'Port':<8} {'Status':<10} {'Latency':<12}")
    print("-" * 30)
    for r in results:
        if r["open"]:
            print(f"{r['port']:<8} {'OPEN':<10} {r.get('latency_ms', 'N/A')}ms")


def main():
    host = "scanme.nmap.org"  # Nmap 提供的合法扫描目标
    ports = range(20, 100)
    max_workers = 50

    if len(sys.argv) > 1:
        host = sys.argv[1]

    print(f"Scanning {host} (ports {ports.start}-{ports.stop - 1})...")
    start = time.monotonic()
    results = scan_ports(host, ports, max_workers)
    elapsed = time.monotonic() - start

    open_ports = [r for r in results if r["open"]]
    print(f"\nScan completed in {elapsed:.2f}s")
    print(f"Open ports: {len(open_ports)}/{len(results)}")
    print_table(open_ports)

    # JSON 输出
    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
```

### 练习 2：进阶场景 -- 异步日志聚合器

```python
#!/usr/bin/env python3
"""
练习 2：异步日志聚合器
要求：
1. 从多个日志源并发读取日志
2. 使用 asyncio.Queue 进行生产者-消费者模式
3. 实时统计错误日志数量
4. 支持优雅停止
"""

import asyncio
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    timestamp: float
    level: str
    service: str
    message: str


class LogAggregator:
    """异步日志聚合器"""

    def __init__(self, max_queue_size: int = 10000):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.stats = Counter()
        self.service_stats = defaultdict(Counter)
        self.running = False
        self.total_processed = 0

    async def log_source(self, name: str, rate: float = 1.0):
        """模拟日志源（生产者）"""
        levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
        while self.running:
            entry = LogEntry(
                timestamp=time.time(),
                level=random.choice(levels),
                service=name,
                message=f"Log message from {name}",
            )
            try:
                self.queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass  # 丢弃（背压）

            await asyncio.sleep(random.uniform(0.1, 1.0) / rate)

    async def processor(self):
        """日志处理器（消费者）"""
        while self.running or not self.queue.empty():
            try:
                entry = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.stats[entry.level] += 1
                self.service_stats[entry.service][entry.level] += 1
                self.total_processed += 1
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def reporter(self, interval: float = 5.0):
        """定期报告统计"""
        while self.running:
            await asyncio.sleep(interval)
            print(f"\n=== Report ({self.total_processed} total) ===")
            print(f"  By level: {dict(self.stats)}")
            for svc, counts in self.service_stats.items():
                print(f"  {svc}: {dict(counts)}")

    async def run(self, duration: float = 15.0):
        """运行聚合器"""
        self.running = True
        sources = [
            self.log_source("api-gateway", rate=2.0),
            self.log_source("auth-service", rate=1.0),
            self.log_source("notification", rate=0.5),
        ]

        await asyncio.gather(
            *sources,
            self.processor(),
            self.reporter(interval=5.0),
            asyncio.sleep(duration),
        )

        self.running = False
        await asyncio.sleep(1)  # 等待队列清空

        print(f"\n=== Final Report ===")
        print(f"Total processed: {self.total_processed}")
        print(f"Level distribution: {dict(self.stats)}")


async def main():
    aggregator = LogAggregator()
    await asyncio.gather(aggregator.run(duration=10.0))


if __name__ == "__main__":
    asyncio.run(main())
```

### 练习 3：故障排查挑战 -- 诊断并发 Bug

```python
#!/usr/bin/env python3
"""
练习 3：诊断并发 Bug
挑战：找出以下代码中的并发问题并修复

症状：
1. 偶尔出现数据不一致
2. 有时程序会死锁
3. 内存使用持续增长
"""

import threading
import time
from collections import defaultdict


# === 问题代码 ===

class BuggyMetricsAggregator:
    """有 Bug 的指标聚合器"""

    def __init__(self):
        self.metrics = defaultdict(list)  # Bug 1: 非线程安全的数据结构

    def record(self, name: str, value: float):
        # Bug 2: 非原子操作
        current = self.metrics[name]  # 读取
        time.sleep(0.0001)            # 放大竞态条件
        current.append(value)         # 修改

    def get_stats(self, name: str) -> dict:
        # Bug 3: 遍历时可能被修改
        values = self.metrics[name]
        return {
            "count": len(values),
            "avg": sum(values) / len(values) if values else 0,
        }


class BuggyWorkerPool:
    """有 Bug 的工作池"""

    def __init__(self):
        self.lock1 = threading.Lock()
        self.lock2 = threading.Lock()

    def task_a(self):
        # Bug 4: 不一致的加锁顺序 → 死锁
        with self.lock1:
            time.sleep(0.1)
            with self.lock2:
                pass

    def task_b(self):
        with self.lock2:  # 反序！
            time.sleep(0.1)
            with self.lock1:
                pass


# === 修复后的代码 ===

class SafeMetricsAggregator:
    """线程安全的指标聚合器"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self._lock = threading.Lock()

    def record(self, name: str, value: float):
        with self._lock:
            self.metrics[name].append(value)

    def get_stats(self, name: str) -> dict:
        with self._lock:
            values = list(self.metrics[name])  # 拷贝一份，避免遍历时被修改
        return {
            "count": len(values),
            "avg": sum(values) / len(values) if values else 0,
        }


class SafeWorkerPool:
    """修复死锁的工作池"""

    def __init__(self):
        self.lock1 = threading.Lock()
        self.lock2 = threading.Lock()

    def _do_work(self):
        """使用统一的加锁顺序"""
        pass

    def task_a(self):
        # 修复：统一加锁顺序（lock1 -> lock2）
        with self.lock1:
            time.sleep(0.1)
            with self.lock2:
                self._do_work()

    def task_b(self):
        # 修复：与 task_a 使用相同的加锁顺序
        with self.lock1:
            time.sleep(0.1)
            with self.lock2:
                self._do_work()


def demo():
    """对比 Bug 版和修复版"""
    print("=== Bug 演示 ===")

    # Bug 1: 竞态条件
    buggy = BuggyMetricsAggregator()
    threads = [
        threading.Thread(target=lambda: [buggy.record("cpu", i) for i in range(100)])
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stats = buggy.get_stats("cpu")
    print(f"  Buggy count: {stats['count']} (expected: 500)")

    # 修复版
    safe = SafeMetricsAggregator()
    threads = [
        threading.Thread(target=lambda: [safe.record("cpu", i) for i in range(100)])
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stats = safe.get_stats("cpu")
    print(f"  Safe count:  {stats['count']} (expected: 500)")


if __name__ == "__main__":
    demo()
```

---

## 🎯 面试题精选

### 题目 1：什么是 Python 的 GIL？它对并发编程有什么影响？

**参考答案：**

GIL（Global Interpreter Lock）是 CPython 解释器中的一个互斥锁，它确保同一时刻只有一个线程能执行 Python 字节码。

影响：
- **CPU 密集型**：多线程无法利用多核，因为 GIL 限制了并行执行。应使用 multiprocessing。
- **I/O 密集型**：GIL 在 I/O 操作时会释放，其他线程可以继续执行。多线程仍然有效。

Python 3.12+ 引入了"每解释器 GIL"（PEP 684），允许每个子解释器有自己的 GIL。Python 3.13 引入了"自由线程"模式实验（PEP 703），未来可能完全移除 GIL。

### 题目 2：线程和协程有什么区别？何时选择哪个？

**参考答案：**

| 维度 | 线程 | 协程 |
|------|------|------|
| 调度方式 | OS 抢占式调度 | 程序协作式调度 |
| 切换开销 | 高（内核态切换） | 低（用户态切换） |
| 内存占用 | 较大（每个线程约 8MB 栈） | 很小（每个协程几 KB） |
| 并发数量 | 数十~数百 | 数千~数万 |
| 数据共享 | 需要锁机制 | 单线程，无需锁 |
| 适用场景 | I/O 密集（中等并发） | I/O 密集（高并发） |

选择建议：
- 并发数 < 100：用线程（简单直接）
- 并发数 > 100：用协程（高效轻量）
- CPU 密集：用进程

### 题目 3：解释 asyncio 的事件循环工作原理

**参考答案：**

事件循环是 asyncio 的核心，它的工作流程：

1. 维护一个待执行的协程队列
2. 从队列中取出一个协程执行
3. 当协程遇到 `await` 时，将其挂起，记录挂起点
4. 继续执行下一个就绪的协程
5. 当 I/O 操作完成时，将对应的协程重新加入就绪队列
6. 重复以上过程，直到所有协程完成

底层实现：
- Linux 上使用 epoll
- macOS 上使用 kqueue
- Windows 上使用 IOCP

这与 Nginx、Redis 的事件驱动模型相同，单线程即可处理大量并发连接。

### 题目 4：什么是死锁？如何避免？

**参考答案：**

死锁是指两个或多个线程互相等待对方持有的资源，导致所有线程都无法继续执行。

死锁的四个必要条件：
1. 互斥：资源不能被共享
2. 持有并等待：线程持有资源的同时等待其他资源
3. 不可抢占：已获取的资源不能被强制释放
4. 循环等待：存在线程的循环等待链

避免方法：
1. **统一加锁顺序**：所有线程按相同顺序获取锁
2. **使用超时**：`lock.acquire(timeout=5)` 避免无限等待
3. **减少锁的使用**：使用线程安全的数据结构
4. **使用 tryLock**：获取失败时释放已持有的锁

### 题目 5：ThreadPoolExecutor 和 ProcessPoolExecutor 如何选择？

**参考答案：**

选择依据是任务类型：

| 任务类型 | 推荐 | 原因 |
|----------|------|------|
| I/O 密集（网络请求、文件读写） | ThreadPoolExecutor | GIL 在 I/O 等待时释放 |
| CPU 密集（计算、数据处理） | ProcessPoolExecutor | 多进程绕过 GIL，利用多核 |
| 混合型 | ProcessPoolExecutor + asyncio | 进程做计算，协程做 I/O |

关键参数：
- max_workers：线程池建议 10-100，进程池建议 CPU 核数
- 使用 as_completed() 而不是 map()，可以按完成顺序处理结果

### 题目 6：解释信号量（Semaphore）的原理和应用

**参考答案：**

信号量是一个计数器，用于控制同时访问共享资源的线程/协程数量。

工作原理：
- 初始化时设置最大并发数 N
- acquire()：计数器减 1，如果为 0 则阻塞
- release()：计数器加 1，唤醒等待的线程

SRE 应用场景：
1. **限制并发 API 调用**：避免打满下游服务
2. **数据库连接池**：控制同时打开的连接数
3. **文件句柄限制**：控制同时打开的文件数
4. **批量任务限流**：控制同时运行的任务数

```python
sem = asyncio.Semaphore(10)  # 最多 10 个并发
async with sem:
    await do_work()
```

### 题目 7：什么是竞态条件？如何在 Python 中避免？

**参考答案：**

竞态条件是指多个线程/进程同时访问和修改共享数据，最终结果取决于它们的执行顺序，导致不可预期的行为。

经典例子：
```python
# 两个线程同时执行 count += 1
# 读取 count (假设为 0)
# 加 1 (得到 1)
# 写回 count (count = 1)
# 最终结果可能是 1 而不是 2
```

避免方法：
1. **Lock（互斥锁）**：保证同一时刻只有一个线程访问临界区
2. **线程安全数据结构**：queue.Queue、collections.deque
3. **原子操作**：使用 `+=` 而不是 `= ... + 1`（但 Python 中 `+=` 也不是原子的）
4. **避免共享状态**：使用消息传递而非共享内存

### 题目 8：asyncio 中 gather 和 TaskGroup 有什么区别？

**参考答案：**

| 特性 | gather | TaskGroup |
|------|--------|-----------|
| Python 版本 | 3.4+ | 3.11+ |
| 错误处理 | 一个失败，其他继续执行 | 一个失败，取消所有其他任务 |
| 返回值 | 列表（按传入顺序） | 无（通过 task 对象获取） |
| 资源管理 | 手动管理 | 自动管理（上下文管理器） |

```python
# gather: 即使一个失败，其他也会完成
results = await asyncio.gather(task1, task2, task3, return_exceptions=True)

# TaskGroup: 一个失败，立即取消其他
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(task1)
    t2 = tg.create_task(task2)
# 如果 task1 失败，task2 会被自动取消
```

SRE 建议：需要错误容忍时用 gather，需要快速失败时用 TaskGroup。

### 题目 9：如何实现优雅停止（Graceful Shutdown）？

**参考答案：**

优雅停止是指收到停止信号后，允许正在执行的任务完成后再退出，而不是强制终止。

Python 实现方式：

```python
import signal
import asyncio

async def main():
    stop_event = asyncio.Event()

    def signal_handler():
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    while not stop_event.is_set():
        await do_work()
        await asyncio.sleep(1)

    # 等待正在执行的任务完成
    await cleanup()

asyncio.run(main())
```

关键点：
1. 捕获 SIGINT/SIGTERM 信号
2. 设置停止标志，让主循环退出
3. 等待正在执行的任务完成
4. 清理资源（关闭连接池、文件句柄等）

### 题目 10：如何在 Python 中实现生产者-消费者模式？

**参考答案：**

Python 提供了多种实现方式：

1. **queue.Queue（线程安全）**：
```python
import queue
q = queue.Queue(maxsize=100)
# 生产者: q.put(item)
# 消费者: item = q.get()
```

2. **asyncio.Queue（异步）**：
```python
q = asyncio.Queue(maxsize=100)
# 生产者: await q.put(item)
# 消费者: item = await q.get()
```

3. **multiprocessing.Queue（跨进程）**：
```python
q = multiprocessing.Queue(maxsize=100)
```

SRE 场景：
- 日志收集：生产者产生日志，消费者处理和存储
- 监控数据：采集器产生数据，分析器消费
- 任务队列：API 接收任务，工作线程处理

---

## 📚 深入阅读

### 官方文档

- [Python threading 官方文档](https://docs.python.org/3/library/threading.html)
- [Python multiprocessing 官方文档](https://docs.python.org/3/library/multiprocessing.html)
- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
- [Python concurrent.futures 官方文档](https://docs.python.org/3/library/concurrent.futures.html)
- [PEP 703 -- Making the GIL Optional](https://peps.python.org/pep-0703/)

### 推荐书籍

- 《Python 并发编程实战》 -- Anthony Simpson
- 《流畅的 Python》 -- Luciano Ramalho -- 第17-19章
- 《Python Cookbook》 -- David Beazley -- 第12章

### 技术博客

- [Real Python: Python Threading](https://realpython.com/intro-to-python-threading/)
- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)
- [David Beazley: Understanding the GIL](https://www.youtube.com/watch?v=Obt-vM1MfPs)

---

## ✅ 自检清单

- [ ] 理解 GIL 的本质及其对 CPU 密集和 I/O 密集任务的影响
- [ ] 能使用 threading 创建和管理线程
- [ ] 理解线程安全问题，能正确使用 Lock、Semaphore、Queue
- [ ] 能使用 multiprocessing 处理 CPU 密集型任务
- [ ] 理解协程和事件循环的工作原理
- [ ] 能使用 asyncio 编写异步程序（协程、Task、gather）
- [ ] 能使用 concurrent.futures 统一管理线程池和进程池
- [ ] 能根据任务类型选择合适的并发模型
- [ ] 能实现优雅停止机制
- [ ] 能诊断和修复死锁、竞态条件等并发 Bug
