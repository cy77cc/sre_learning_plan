# Day 48: 网络编程与 HTTP 客户端

> 📅 日期：2026-05-03
> 📖 学习主题：Python 网络编程与 HTTP 客户端（socket/requests/httpx/aiohttp, 连接池, 超时控制, 重试机制, API 封装）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 46（Python 基础语法）, Day 47（Python 标准库）

## 🎯 学习目标

- 理解 TCP/IP 网络模型与 socket 编程的底层原理，能用 Python 实现自定义网络协议
- 掌握 requests/httpx/aiohttp 三大 HTTP 客户端的核心用法与适用场景
- 能设计并实现带连接池、超时控制、指数退避重试的生产级 HTTP 客户端
- 理解 I/O 多路复用（select/poll/epoll）的原理及其对 Python 网络编程的影响
- 能独立编写 SRE 场景下的健康检查、批量 API 调用、服务探测等工具

---

## 📖 核心知识点

### 1. 网络编程基础：从 TCP/IP 到 Socket

#### 1.1 TCP/IP 协议栈与 SRE 的关系

作为 SRE 工程师，你每天都在与网络打交道——负载均衡器的健康检查、服务间的 RPC 调用、监控数据的采集上报，这些都建立在 TCP/IP 协议栈之上。理解底层原理能帮助你快速定位网络层面的故障。

```
┌─────────────────────────────────────────────────────┐
│                    应用层                             │
│  HTTP / HTTPS / gRPC / DNS / SSH / SMTP             │
│  Python: requests, httpx, aiohttp                   │
├─────────────────────────────────────────────────────┤
│                    传输层                             │
│  TCP (可靠, 面向连接) / UDP (不可靠, 无连接)          │
│  Python: socket (SOCK_STREAM / SOCK_DGRAM)          │
├─────────────────────────────────────────────────────┤
│                    网络层                             │
│  IP (寻址) / ICMP (ping) / ARP                      │
├─────────────────────────────────────────────────────┤
│                    链路层                             │
│  Ethernet / Wi-Fi                                   │
└─────────────────────────────────────────────────────┘
```

#### 1.2 Socket 编程：网络通信的基石

Socket（套接字）是操作系统提供的网络编程接口。Python 的 `socket` 模块是对 BSD Socket API 的封装。

**TCP 三次握手与四次挥手：**

```
    TCP 三次握手 (建立连接)          TCP 四次挥手 (关闭连接)
    ========================        ========================
    Client          Server          Client          Server
      │    SYN        │               │    FIN        │
      │──────────────→│               │──────────────→│
      │  SYN+ACK      │               │    ACK        │
      │←──────────────│               │←──────────────│
      │    ACK        │               │    FIN        │
      │──────────────→│               │←──────────────│
      │  连接已建立    │               │    ACK        │
                                   │──────────────→│
                                   │  连接已关闭    │
```

**为什么 SRE 需要理解 Socket？**

- 排查连接超时问题时，你需要知道 SYN 包是否到达了对端
- 理解 TIME_WAIT 状态对高并发服务端口耗尽问题至关重要
- 健康检查的 TCP 探测模式直接使用 Socket 连接

```python
#!/usr/bin/env python3
"""
Socket 基础：TCP 客户端与服务端
SRE 场景：实现自定义协议的健康检查探针
"""

import socket
import json
import time


def tcp_health_check(host: str, port: int, timeout: float = 5.0) -> dict:
    """
    TCP 层面的健康检查
    返回连接状态、延迟等信息，用于判断服务是否存活
    """
    result = {
        "host": host,
        "port": port,
        "status": "unknown",
        "latency_ms": None,
        "error": None,
    }
    start = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            latency = (time.monotonic() - start) * 1000
            result["status"] = "healthy"
            result["latency_ms"] = round(latency, 2)
    except socket.timeout:
        result["status"] = "timeout"
        result["error"] = f"Connection timed out after {timeout}s"
    except ConnectionRefusedError:
        result["status"] = "refused"
        result["error"] = "Connection refused - service may be down"
    except OSError as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def tcp_server_example(host: str = "0.0.0.0", port: int = 8888):
    """
    简单的 TCP 服务端，用于理解 Socket 服务端编程
    SRE 场景：自定义监控数据接收端
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        # SO_REUSEADDR 避免 "Address already in use" 错误
        # SRE 必知：服务重启时端口可能处于 TIME_WAIT 状态
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(5)  # backlog 队列大小
        print(f"[*] Listening on {host}:{port}")

        while True:
            client_sock, client_addr = server_sock.accept()
            print(f"[+] Connection from {client_addr}")
            with client_sock:
                data = client_sock.recv(4096)
                if data:
                    # 简单的 JSON 协议
                    request = json.loads(data.decode("utf-8"))
                    response = {
                        "status": "ok",
                        "received": request,
                        "timestamp": time.time(),
                    }
                    client_sock.sendall(json.dumps(response).encode("utf-8"))


def udp_example():
    """
    UDP 通信示例
    SRE 场景：StatsD 监控数据上报（UDP 无连接，低开销）
    """
    import socket

    # 发送端（模拟 StatsD 上报）
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        metric = "sre.api.response_time:150|ms|#env:prod"
        sock.sendto(metric.encode(), ("localhost", 8125))

    # 接收端
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", 8125))
        data, addr = sock.recvfrom(4096)
        print(f"Received metric from {addr}: {data.decode()}")


if __name__ == "__main__":
    # 测试 TCP 健康检查
    result = tcp_health_check("httpbin.org", 80)
    print(json.dumps(result, indent=2))
```

#### 1.3 I/O 多路复用：select、poll 与 epoll

I/O 多路复用是高性能网络编程的核心。SRE 在调优 Nginx、Redis 等服务时经常遇到相关概念。

```
┌─────────────────────────────────────────────────────────────┐
│                    I/O 多路复用模型对比                        │
├──────────┬──────────────┬──────────────┬────────────────────┤
│ 特性      │ select       │ poll         │ epoll              │
├──────────┼──────────────┼──────────────┼────────────────────┤
│ 最大连接数│ 1024 (FD_SET)│ 无限制       │ 无限制              │
│ 时间复杂度│ O(n)         │ O(n)         │ O(1)               │
│ 触发方式  │ 水平触发      │ 水平触发     │ 水平/边缘触发       │
│ 内核开销  │ 每次拷贝FD集合│ 每次拷贝FD   │ mmap 共享内存       │
│ 平台      │ 跨平台       │ 跨平台       │ Linux 专用          │
│ Python    │ select模块    │ select模块   │ selectors模块       │
└──────────┴──────────────┴──────────────┴────────────────────┘
```

```python
#!/usr/bin/env python3
"""
使用 selectors 模块实现 I/O 多路复用的 TCP 服务器
SRE 场景：高性能日志收集器、监控数据聚合器
"""

import selectors
import socket
import json

sel = selectors.DefaultSelector()  # Linux 上自动使用 epoll


def accept_connection(sock, mask):
    """接受新连接"""
    conn, addr = sock.accept()
    print(f"[+] New connection from {addr}")
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, handle_client)


def handle_client(conn, mask):
    """处理客户端数据"""
    try:
        data = conn.recv(4096)
        if data:
            message = json.loads(data.decode())
            print(f"[<] Received: {message}")
            response = {"status": "ok", "echo": message}
            conn.sendall(json.dumps(response).encode())
        else:
            # 客户端关闭连接
            print(f"[-] Closing connection")
            sel.unregister(conn)
            conn.close()
    except (ConnectionResetError, json.JSONDecodeError) as e:
        print(f"[!] Error: {e}")
        sel.unregister(conn)
        conn.close()


def run_multiplexed_server(host="0.0.0.0", port=9999):
    """
    基于 I/O 多路复用的服务器
    单线程即可处理数千个并发连接
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(100)
    server_sock.setblocking(False)

    sel.register(server_sock, selectors.EVENT_READ, accept_connection)
    print(f"[*] Multiplexed server on {host}:{port}")

    try:
        while True:
            events = sel.select(timeout=1)  # 阻塞等待事件
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
    except KeyboardInterrupt:
        print("\n[*] Shutting down")
    finally:
        sel.close()
        server_sock.close()


if __name__ == "__main__":
    run_multiplexed_server()
```

---

### 2. HTTP 客户端：requests / httpx / aiohttp

#### 2.1 三大 HTTP 客户端对比

```
┌──────────────────────────────────────────────────────────────────┐
│                  Python HTTP 客户端对比                            │
├───────────┬──────────────┬───────────────┬───────────────────────┤
│ 特性       │ requests     │ httpx         │ aiohttp               │
├───────────┼──────────────┼───────────────┼───────────────────────┤
│ 同步/异步  │ 同步          │ 同步+异步      │ 纯异步                 │
│ HTTP/2     │ 不支持        │ 支持          │ 支持                   │
│ 连接池     │ urllib3       │ 内置 httpcore │ 内置                   │
│ 流式传输   │ 支持          │ 支持          │ 支持                   │
│ WebSocket  │ 不支持        │ 不支持        │ 支持                   │
│ 成熟度     │ ★★★★★       │ ★★★★        │ ★★★★                  │
│ 性能       │ 中等          │ 高            │ 高（异步场景）           │
│ SRE 推荐   │ 脚本/工具     │ 新项目首选     │ 高并发场景              │
└───────────┴──────────────┴───────────────┴───────────────────────┘
```

#### 2.2 requests 深入：生产级用法

```python
#!/usr/bin/env python3
"""
requests 库的生产级用法
SRE 场景：封装可靠的 API 客户端
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.timeout import Timeout
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_robust_session(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: list = None,
    pool_connections: int = 10,
    pool_maxsize: int = 20,
) -> requests.Session:
    """
    创建一个带重试、连接池、超时控制的 Session

    为什么用 Session 而不是直接 requests.get()？
    1. Session 维护连接池，复用 TCP 连接，减少三次握手开销
    2. Session 可以统一设置 headers、auth、cookies
    3. Session 的 mount 机制支持不同 URL 前缀使用不同配置

    SRE 场景：调用 Kubernetes API、Prometheus API、自定义监控 API
    """
    if status_forcelist is None:
        status_forcelist = [500, 502, 503, 504]

    session = requests.Session()

    # 重试策略
    # backoff_factor: 重试间隔 = backoff_factor * (2 ** (retry_number - 1))
    # 第1次重试: 0.5s, 第2次: 1s, 第3次: 2s
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        raise_on_status=False,  # 不要自动抛异常，让我们自己处理
    )

    # HTTPAdapter 控制连接池大小
    # pool_connections: 连接池数量（不同 host 的连接数）
    # pool_maxsize: 每个 host 的最大连接数
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
    )

    # mount 对 http 和 https 前缀的 URL 都生效
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 默认 headers
    session.headers.update({
        "User-Agent": "SRE-Toolkit/1.0",
        "Accept": "application/json",
    })

    return session


class APIClient:
    """
    生产级 API 客户端封装
    包含超时控制、重试、日志、指标采集

    SRE 场景：封装公司内部 API、Kubernetes API、云服务 API
    """

    def __init__(
        self,
        base_url: str,
        timeout: tuple = (3.05, 30),
        max_retries: int = 3,
        api_token: str = None,
    ):
        """
        Args:
            base_url: API 基础 URL
            timeout: (连接超时, 读取超时) - 分别控制
                连接超时 3.05s: TCP 三次握手的超时
                读取超时 30s: 等待服务器响应的超时
            max_retries: 最大重试次数
            api_token: API 认证令牌
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = create_robust_session(max_retries=max_retries)

        if api_token:
            self.session.headers["Authorization"] = f"Bearer {api_token}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        统一的请求方法，包含日志和指标采集

        为什么不在这里设置 timeout？
        因为 timeout 应该在调用时可以被覆盖
        """
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        start_time = time.monotonic()
        try:
            response = self.session.request(method, url, **kwargs)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                f"{method} {url} -> {response.status_code} "
                f"({elapsed_ms:.1f}ms)"
            )

            # 记录指标（可以对接 Prometheus client）
            # http_requests_total.labels(method=method, status=response.status_code).inc()
            # http_request_duration_ms.labels(method=method).observe(elapsed_ms)

            return response

        except requests.exceptions.ConnectionError as e:
            logger.error(f"{method} {url} -> ConnectionError: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"{method} {url} -> Timeout: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"{method} {url} -> RequestException: {e}")
            raise

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("DELETE", path, **kwargs)

    def health_check(self) -> dict:
        """健康检查，返回状态和延迟"""
        start = time.monotonic()
        try:
            resp = self.get("/healthz", timeout=(2, 5))
            return {
                "status": "healthy" if resp.ok else "unhealthy",
                "status_code": resp.status_code,
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }

    def close(self):
        """关闭连接池，释放资源"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# 使用示例
def demo_api_client():
    with APIClient("https://httpbin.org") as client:
        # 基本 GET 请求
        resp = client.get("/get", params={"env": "production"})
        print(resp.json())

        # POST 请求
        resp = client.post("/post", json={"service": "api", "replicas": 3})
        print(resp.json())

        # 健康检查
        health = client.health_check()
        print(f"Health: {health}")


if __name__ == "__main__":
    demo_api_client()
```

#### 2.3 httpx 深入：新一代 HTTP 客户端

```python
#!/usr/bin/env python3
"""
httpx：支持 HTTP/2 的现代 HTTP 客户端
SRE 场景：调用支持 HTTP/2 的 gRPC-Web 服务、现代 API
"""

import httpx
import asyncio
import time


def httpx_sync_example():
    """
    httpx 同步用法，与 requests API 兼容

    为什么 SRE 应该关注 httpx？
    1. HTTP/2 支持：多路复用，减少连接数
    2. 原生异步支持：无需切换库
    3. 更严格的默认配置：默认不信任环境变量中的代理
    """
    # 同步客户端，带连接池和超时
    with httpx.Client(
        base_url="https://httpbin.org",
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(
            max_connections=100,        # 总连接数上限
            max_keepalive_connections=20,  # keep-alive 连接数
            keepalive_expiry=30,        # keep-alive 过期时间(秒)
        ),
        follow_redirects=True,  # 自动跟随重定向
        http2=True,             # 启用 HTTP/2
    ) as client:
        # GET 请求
        resp = client.get("/get", params={"key": "value"})
        print(f"HTTP version: {resp.http_version}")
        print(f"Status: {resp.status_code}")

        # 流式响应（大文件下载）
        with client.stream("GET", "/stream-bytes/1000000") as resp:
            total_bytes = 0
            for chunk in resp.iter_bytes(chunk_size=8192):
                total_bytes += len(chunk)
            print(f"Downloaded {total_bytes} bytes")


async def httpx_async_example():
    """
    httpx 异步用法
    SRE 场景：并发检查多个服务的健康状态
    """
    async with httpx.AsyncClient(
        base_url="https://httpbin.org",
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=50),
    ) as client:
        # 并发请求多个健康检查端点
        services = [
            "/status/200",
            "/status/200",
            "/status/500",
        ]

        async def check(path: str) -> dict:
            try:
                resp = await client.get(path)
                return {"path": path, "status": resp.status_code, "healthy": resp.status_code == 200}
            except Exception as e:
                return {"path": path, "status": None, "healthy": False, "error": str(e)}

        results = await asyncio.gather(*[check(s) for s in services])
        for r in results:
            print(f"  {r['path']}: {'healthy' if r['healthy'] else 'UNHEALTHY'}")


if __name__ == "__main__":
    print("=== httpx 同步示例 ===")
    httpx_sync_example()

    print("\n=== httpx 异步示例 ===")
    asyncio.run(httpx_async_example())
```

#### 2.4 aiohttp 深入：纯异步 HTTP

```python
#!/usr/bin/env python3
"""
aiohttp：纯异步 HTTP 客户端/服务端
SRE 场景：高并发监控数据采集、批量 API 调用
"""

import aiohttp
import asyncio
import time


async def aiohttp_basic():
    """
    aiohttp 基础用法

    与 httpx 的区别：
    - aiohttp 是纯异步库，没有同步 API
    - aiohttp 同时支持 HTTP 客户端和服务端
    - aiohttp 支持 WebSocket
    - httpx 的 API 设计更现代，与 requests 更兼容
    """
    async with aiohttp.ClientSession() as session:
        # GET 请求
        async with session.get("https://httpbin.org/get") as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Origin: {data['origin']}")

        # POST 请求
        async with session.post(
            "https://httpbin.org/post",
            json={"service": "sre-tool"},
        ) as resp:
            result = await resp.json()
            print(f"Posted: {result['json']}")


async def batch_health_check(urls: list[str], concurrency: int = 50) -> list[dict]:
    """
    批量健康检查
    SRE 场景：一次性检查整个服务网格中所有微服务的健康状态

    使用 Semaphore 控制并发数，避免瞬间打满目标服务
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def check_one(session: aiohttp.ClientSession, url: str) -> dict:
        async with semaphore:  # 限制并发数
            start = time.monotonic()
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    elapsed = (time.monotonic() - start) * 1000
                    return {
                        "url": url,
                        "status": resp.status,
                        "healthy": 200 <= resp.status < 400,
                        "latency_ms": round(elapsed, 2),
                    }
            except asyncio.TimeoutError:
                return {"url": url, "status": None, "healthy": False, "error": "timeout"}
            except aiohttp.ClientError as e:
                return {"url": url, "status": None, "healthy": False, "error": str(e)}

    connector = aiohttp.TCPConnector(
        limit=100,           # 总连接数限制
        limit_per_host=20,   # 每个 host 的连接数限制
        ttl_dns_cache=300,   # DNS 缓存 TTL
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_one(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    return results


async def aiohttp_stream_example():
    """
    流式下载大文件
    SRE 场景：下载大型日志文件、备份文件
    """
    url = "https://httpbin.org/stream-bytes/10000000"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            total = 0
            with open("/tmp/download.bin", "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)
                    total += len(chunk)
            print(f"Downloaded {total} bytes")


async def websocket_example():
    """
    WebSocket 客户端
    SRE 场景：实时接收告警推送、实时日志流
    """
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect("wss://echo.websocket.org") as ws:
            await ws.send_str("Hello SRE!")
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print(f"Received: {msg.data}")
                    await ws.close()
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"Error: {ws.exception()}")
                    break


async def main():
    print("=== aiohttp 基础示例 ===")
    await aiohttp_basic()

    print("\n=== 批量健康检查 ===")
    urls = [f"https://httpbin.org/status/{code}" for code in [200, 200, 500, 200, 404]]
    results = await batch_health_check(urls, concurrency=3)
    healthy = sum(1 for r in results if r["healthy"])
    print(f"  {healthy}/{len(results)} services healthy")
    for r in results:
        status = "OK" if r["healthy"] else "FAIL"
        print(f"  [{status}] {r['url']} ({r.get('latency_ms', 'N/A')}ms)")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 3. 连接池原理与配置

#### 3.1 为什么需要连接池？

```
没有连接池的请求流程（每次新建连接）：
┌────────┐    SYN      ┌────────┐
│ Client │────────────→│ Server │  每个请求都要经历
│        │←────────────│        │  TCP 三次握手
│        │    SYN+ACK  │        │  TLS 握手(HTTPS)
│        │────────────→│        │  = 高延迟
│        │    ACK      │        │
│        │             │        │
│        │  HTTP 请求   │        │
│        │────────────→│        │
│        │  HTTP 响应   │        │
│        │←────────────│        │
│        │             │        │
│        │  FIN 关闭    │        │  连接被销毁
│        │────────────→│        │
└────────┘             └────────┘

有连接池的请求流程（复用连接）：
┌────────┐             ┌────────┐
│ Client │  HTTP 请求 1 │ Server │  连接建立一次
│        │────────────→│        │  后续请求复用
│        │  HTTP 响应 1 │        │  省去握手开销
│        │←────────────│        │
│        │             │        │
│        │  HTTP 请求 2 │        │  同一个连接
│        │────────────→│        │
│        │  HTTP 响应 2 │        │
│        │←────────────│        │
│        │             │        │
│ Connection Pool      │        │
│ [conn1] [conn2] ...  │        │
└────────┘             └────────┘
```

#### 3.2 连接池配置最佳实践

```python
#!/usr/bin/env python3
"""
连接池配置与监控
SRE 场景：优化服务间 HTTP 调用性能
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import httpx
import time
import statistics


def benchmark_connection_pool():
    """
    对比有无连接池的性能差异
    SRE 场景：证明连接池优化的价值
    """
    url = "https://httpbin.org/get"
    num_requests = 20

    # 无连接池：每次创建新 session
    times_no_pool = []
    for _ in range(num_requests):
        start = time.monotonic()
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        times_no_pool.append((time.monotonic() - start) * 1000)

    # 有连接池：复用 session
    times_with_pool = []
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    for _ in range(num_requests):
        start = time.monotonic()
        try:
            session.get(url, timeout=10)
        except Exception:
            pass
        times_with_pool.append((time.monotonic() - start) * 1000)
    session.close()

    print("无连接池:")
    print(f"  平均: {statistics.mean(times_no_pool):.1f}ms")
    print(f"  P50:  {statistics.median(times_no_pool):.1f}ms")

    print("有连接池:")
    print(f"  平均: {statistics.mean(times_with_pool):.1f}ms")
    print(f"  P50:  {statistics.median(times_with_pool):.1f}ms")


def configure_pool_for_high_concurrency():
    """
    高并发场景的连接池配置
    SRE 场景：服务需要同时调用多个下游 API
    """
    session = requests.Session()

    # 对内部 API 使用更大的连接池
    internal_adapter = HTTPAdapter(
        pool_connections=20,   # 20 个不同的 host
        pool_maxsize=50,       # 每个 host 50 个连接
        max_retries=Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
        ),
    )
    session.mount("https://internal-api.", internal_adapter)

    # 对外部 API 使用较小的连接池
    external_adapter = HTTPAdapter(
        pool_connections=5,
        pool_maxsize=10,
        max_retries=Retry(total=2, backoff_factor=1),
    )
    session.mount("https://external-api.", external_adapter)

    return session


if __name__ == "__main__":
    benchmark_connection_pool()
```

---

### 4. 超时控制：最容易被忽视的故障源

#### 4.1 超时的层次

```
一次 HTTPS 请求涉及的超时层次：

┌─────────────────────────────────────────────────────────────┐
│  DNS 解析超时                                                │
│  ├── 系统默认: 30s (太长!)                                   │
│  └── 建议: 使用 DNS 缓存或设置 5s                             │
├─────────────────────────────────────────────────────────────┤
│  TCP 连接超时 (connect timeout)                              │
│  ├── 三次握手的超时                                          │
│  ├── 建议: 3-5s                                             │
│  └── 超时表示: 对端不可达或端口未监听                           │
├─────────────────────────────────────────────────────────────┤
│  TLS 握手超时                                                │
│  ├── 包含在 connect 超时中                                   │
│  └── 在高延迟网络中可能需要更长时间                             │
├─────────────────────────────────────────────────────────────┤
│  读取超时 (read timeout)                                     │
│  ├── 等待服务器发送响应的超时                                  │
│  ├── 建议: 根据 API 特性设置 (10-60s)                        │
│  └── 超时表示: 服务器处理慢或网络中断                           │
├─────────────────────────────────────────────────────────────┤
│  写入超时 (write timeout)                                    │
│  ├── 发送请求体的超时                                         │
│  └── 上传大文件时需要特别注意                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 超时配置策略

```python
#!/usr/bin/env python3
"""
超时控制的最佳实践
SRE 场景：避免因超时配置不当导致的级联故障
"""

import requests
import httpx
import aiohttp
import asyncio


# ============================================================
# 超时配置原则（SRE 必知）
# ============================================================
# 1. 永远不要不设超时！没有超时 = 潜在的无限阻塞
# 2. 连接超时应该短于读取超时
# 3. 超时值应该小于上游调用者的超时值（避免级联超时）
# 4. 根据 API 的 P99 延迟设置超时，而不是平均延迟
# ============================================================


def requests_timeout_strategies():
    """requests 超时配置策略"""

    # 策略1: 统一超时（简单但不够灵活）
    requests.get("https://api.example.com", timeout=10)

    # 策略2: 分别设置连接和读取超时（推荐）
    requests.get("https://api.example.com", timeout=(3.05, 30))
    # 3.05s 连接超时: 为什么是 3.05 而不是 3？
    # 因为 urllib3 内部会加上一些处理时间，3.05 确保实际等待约 3s

    # 策略3: 对不同类型的 API 使用不同超时
    # 健康检查: 快速
    requests.get("https://api.example.com/healthz", timeout=(2, 5))
    # 普通查询: 中等
    requests.get("https://api.example.com/data", timeout=(3, 30))
    # 报表生成: 较长
    requests.get("https://api.example.com/report", timeout=(5, 120))


def httpx_timeout_strategies():
    """httpx 超时配置策略（更精细的控制）"""
    # httpx 的 Timeout 类提供了更精细的控制
    timeout = httpx.Timeout(
        connect=5.0,    # 连接超时
        read=30.0,      # 读取超时
        write=10.0,     # 写入超时
        pool=5.0,       # 从连接池获取连接的超时
    )

    with httpx.Client(timeout=timeout) as client:
        resp = client.get("https://httpbin.org/get")


async def aiohttp_timeout_strategies():
    """aiohttp 超时配置策略"""
    timeout = aiohttp.ClientTimeout(
        total=60,       # 总超时（包含连接+读取+处理）
        connect=5,      # 连接超时
        sock_connect=5, # socket 连接超时
        sock_read=30,   # socket 读取超时
    )

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get("https://httpbin.org/get") as resp:
            data = await resp.json()


def timeout_cascade_example():
    """
    超时级联问题示例

    场景：A -> B -> C 三层服务调用
    如果每层超时都是 30s，最坏情况用户等待 90s

    正确的超时配置：
    A->B: 10s (含重试)
    B->C: 5s
    """
    # 服务 A 的客户端配置
    session_a = requests.Session()
    adapter_a = HTTPAdapter(
        max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[503]),
    )
    session_a.mount("https://", adapter_a)

    # 调用服务 B，超时设置要小于用户能接受的等待时间
    try:
        resp = session_a.get(
            "https://service-b/api",
            timeout=(3, 8),  # 连接3s，读取8s
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        # 服务 B 超时，返回降级结果
        return {"status": "degraded", "data": None}
    except requests.exceptions.ConnectionError:
        return {"status": "unavailable", "data": None}


if __name__ == "__main__":
    requests_timeout_strategies()
    httpx_timeout_strategies()
    asyncio.run(aiohttp_timeout_strategies())
```

---

### 5. 重试机制：指数退避与抖动

#### 5.1 重试策略设计

```python
#!/usr/bin/env python3
"""
重试机制实现
SRE 场景：处理临时性网络故障，提高 API 调用的可靠性
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Type, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    计算指数退避延迟时间

    为什么需要 jitter（抖动）？
    如果多个客户端同时重试，没有 jitter 会导致：
    1. 所有客户端在相同时间点重试
    2. 造成"惊群效应"（Thundering Herd）
    3. 服务器瞬间压力飙升

    抖动打散重试时间，平滑服务器负载

    延迟计算公式:
    delay = min(base_delay * 2^attempt, max_delay)
    如果 jitter: delay = random(0, delay)
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        delay = random.uniform(0, delay)
    return delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (Exception,),
    retryable_status_codes: set = None,
):
    """
    通用重试装饰器
    SRE 场景：包装任何可能失败的网络调用
    """
    if retryable_status_codes is None:
        retryable_status_codes = {500, 502, 503, 504}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查 HTTP 状态码
                    if hasattr(result, "status_code"):
                        if result.status_code in retryable_status_codes:
                            raise RetryableHTTPError(
                                result.status_code,
                                f"HTTP {result.status_code}",
                            )

                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = exponential_backoff_with_jitter(
                            attempt, base_delay, max_delay
                        )
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


class RetryableHTTPError(Exception):
    """可重试的 HTTP 错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


# 装饰器用法示例
@retry_with_backoff(
    max_retries=3,
    base_delay=0.5,
    retryable_exceptions=(ConnectionError, TimeoutError, RetryableHTTPError),
)
def call_external_api(url: str) -> dict:
    """
    调用外部 API，自动重试

    哪些错误应该重试？
    - 连接错误（网络抖动）
    - 超时错误（服务暂时过载）
    - 5xx 服务器错误（服务端临时问题）

    哪些错误不应该重试？
    - 400 Bad Request（请求本身有误）
    - 401 Unauthorized（认证失败）
    - 403 Forbidden（权限不足）
    - 404 Not Found（资源不存在）
    - 422 Unprocessable Entity（参数校验失败）
    """
    import requests
    resp = requests.get(url, timeout=(3, 10))
    resp.raise_for_status()
    return resp.json()


# requests 内置的重试配置
def requests_retry_config():
    """
    使用 urllib3 的 Retry 配置
    这是 requests 生产级重试的标准做法
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(
        total=3,                    # 总重试次数
        connect=3,                  # 连接失败重试次数
        read=3,                     # 读取失败重试次数
        status=3,                   # 状态码重试次数
        backoff_factor=0.5,         # 退避因子
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
        raise_on_status=False,      # 不自动抛异常
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


if __name__ == "__main__":
    # 测试重试机制
    try:
        result = call_external_api("https://httpbin.org/status/503")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")
```

---

### 6. SRE 实战案例

#### 6.1 生产级批量健康检查工具

```python
#!/usr/bin/env python3
"""
批量服务健康检查工具
SRE 场景：监控整个微服务集群的健康状态

功能：
- 并发检查多个服务
- 支持 TCP 和 HTTP 两种检查模式
- 输出 JSON 格式报告
- 支持告警阈值
"""

import asyncio
import aiohttp
import socket
import json
import time
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class CheckType(Enum):
    TCP = "tcp"
    HTTP = "http"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    host: str
    port: int
    check_type: CheckType = CheckType.HTTP
    health_path: str = "/healthz"
    timeout: float = 10.0
    expected_status: int = 200
    critical: bool = False  # 是否是关键服务


@dataclass
class HealthResult:
    """健康检查结果"""
    service: str
    status: HealthStatus
    latency_ms: float
    check_type: str
    details: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


async def check_tcp(host: str, port: int, timeout: float) -> HealthResult:
    """TCP 层面的健康检查"""
    start = time.monotonic()
    try:
        # 使用 asyncio 的非阻塞 socket
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return HealthResult(
            service=f"{host}:{port}",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            check_type="tcp",
        )
    except asyncio.TimeoutError:
        return HealthResult(
            service=f"{host}:{port}",
            status=HealthStatus.UNHEALTHY,
            latency_ms=timeout * 1000,
            check_type="tcp",
            details="Connection timeout",
        )
    except (ConnectionRefusedError, OSError) as e:
        return HealthResult(
            service=f"{host}:{port}",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.monotonic() - start) * 1000,
            check_type="tcp",
            details=str(e),
        )


async def check_http(
    session: aiohttp.ClientSession,
    config: ServiceConfig,
) -> HealthResult:
    """HTTP 层面的健康检查"""
    url = f"http://{config.host}:{config.port}{config.health_path}"
    start = time.monotonic()
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=config.timeout),
        ) as resp:
            latency = (time.monotonic() - start) * 1000
            if resp.status == config.expected_status:
                status = HealthStatus.HEALTHY
                details = f"HTTP {resp.status}"
            elif 400 <= resp.status < 500:
                status = HealthStatus.DEGRADED
                details = f"HTTP {resp.status} - client error"
            else:
                status = HealthStatus.UNHEALTHY
                details = f"HTTP {resp.status}"
            return HealthResult(
                service=config.name,
                status=status,
                latency_ms=round(latency, 2),
                check_type="http",
                details=details,
            )
    except asyncio.TimeoutError:
        return HealthResult(
            service=config.name,
            status=HealthStatus.UNHEALTHY,
            latency_ms=config.timeout * 1000,
            check_type="http",
            details="Request timeout",
        )
    except aiohttp.ClientError as e:
        return HealthResult(
            service=config.name,
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.monotonic() - start) * 1000,
            check_type="http",
            details=str(e),
        )


async def run_health_checks(services: list[ServiceConfig]) -> list[HealthResult]:
    """并发执行所有健康检查"""
    results = []

    connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for svc in services:
            if svc.check_type == CheckType.TCP:
                tasks.append(check_tcp(svc.host, svc.port, svc.timeout))
            else:
                tasks.append(check_http(session, svc))

        results = await asyncio.gather(*tasks)

    return list(results)


def generate_report(results: list[HealthResult]) -> dict:
    """生成健康检查报告"""
    healthy = [r for r in results if r.status == HealthStatus.HEALTHY]
    unhealthy = [r for r in results if r.status == HealthStatus.UNHEALTHY]
    degraded = [r for r in results if r.status == HealthStatus.DEGRADED]

    report = {
        "timestamp": time.time(),
        "summary": {
            "total": len(results),
            "healthy": len(healthy),
            "degraded": len(degraded),
            "unhealthy": len(unhealthy),
            "health_percentage": round(len(healthy) / len(results) * 100, 1)
            if results
            else 0,
        },
        "services": [asdict(r) for r in results],
        "avg_latency_ms": round(
            sum(r.latency_ms for r in results) / len(results), 2
        ) if results else 0,
    }

    return report


async def main():
    """主函数"""
    # 定义要检查的服务
    services = [
        ServiceConfig(
            name="api-gateway",
            host="localhost",
            port=8080,
            check_type=CheckType.HTTP,
            critical=True,
        ),
        ServiceConfig(
            name="auth-service",
            host="localhost",
            port=8081,
            check_type=CheckType.HTTP,
            critical=True,
        ),
        ServiceConfig(
            name="redis",
            host="localhost",
            port=6379,
            check_type=CheckType.TCP,
        ),
        ServiceConfig(
            name="postgres",
            host="localhost",
            port=5432,
            check_type=CheckType.TCP,
        ),
    ]

    # 运行健康检查
    results = await run_health_checks(services)

    # 生成报告
    report = generate_report(results)
    print(json.dumps(report, indent=2, default=str))

    # 检查关键服务
    critical_unhealthy = [
        r for r, s in zip(results, services)
        if s.critical and r.status == HealthStatus.UNHEALTHY
    ]
    if critical_unhealthy:
        print(f"\n[ALERT] {len(critical_unhealthy)} critical service(s) unhealthy!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

#### 6.2 SRE 故障排查案例：连接泄漏

```
故障现象：
  服务 A 调用服务 B 的 API，运行一段时间后开始报 ConnectionError
  错误信息: "Connection pool is full, discarding connection"

故障排查链路：
  1. 现象 → ConnectionError, pool full
  2. 诊断 → 检查 netstat 发现大量 CLOSE_WAIT 连接
  3. 根因 → 代码中每次请求创建新 Session 且未关闭，导致连接泄漏
  4. 修复 → 使用全局 Session + 连接池限制
  5. 预防 → 监控连接池使用率

修复前（有 Bug 的代码）：
"""

# BAD: 每次调用创建新 session，连接不会被复用
def call_api_broken(url):
    session = requests.Session()  # 每次都创建新 session！
    resp = session.get(url, timeout=10)
    # session 没有关闭！连接泄漏
    return resp.json()


# GOOD: 使用全局 session 或 context manager
_global_session = None


def get_session() -> requests.Session:
    global _global_session
    if _global_session is None:
        _global_session = requests.Session()
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
        _global_session.mount("https://", adapter)
    return _global_session


def call_api_fixed(url: str) -> dict:
    session = get_session()
    resp = session.get(url, timeout=(3, 10))
    resp.raise_for_status()
    return resp.json()


# BETTER: 使用 context manager
def call_api_best(url: str) -> dict:
    with requests.Session() as session:
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
        session.mount("https://", adapter)
        resp = session.get(url, timeout=(3, 10))
        resp.raise_for_status()
        return resp.json()
```

---

## 💻 实战练习

### 练习 1：基础操作 -- 实现 HTTP 健康检查器

编写一个命令行工具，接受 URL 列表文件，并发检查所有 URL 的健康状态，输出表格形式的报告。

```python
#!/usr/bin/env python3
"""
练习 1：批量 URL 健康检查器
要求：
1. 从文件读取 URL 列表（每行一个 URL）
2. 并发检查（使用 asyncio + aiohttp）
3. 输出表格形式的报告
4. 统计健康率
"""

import asyncio
import aiohttp
import time
import sys


async def check_url(session: aiohttp.ClientSession, url: str) -> dict:
    """检查单个 URL 的健康状态"""
    start = time.monotonic()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            elapsed = (time.monotonic() - start) * 1000
            return {
                "url": url,
                "status": resp.status,
                "latency_ms": round(elapsed, 2),
                "healthy": 200 <= resp.status < 400,
            }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "url": url,
            "status": None,
            "latency_ms": round(elapsed, 2),
            "healthy": False,
            "error": str(e),
        }


async def check_all(urls: list[str], concurrency: int = 20) -> list[dict]:
    """并发检查所有 URL"""
    semaphore = asyncio.Semaphore(concurrency)

    async def limited_check(session, url):
        async with semaphore:
            return await check_url(session, url)

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [limited_check(session, url) for url in urls]
        return await asyncio.gather(*tasks)


def print_report(results: list[dict]):
    """打印表格报告"""
    # 表头
    print(f"{'URL':<50} {'Status':<8} {'Latency':<12} {'Health':<8}")
    print("-" * 80)

    # 数据行
    for r in results:
        status = str(r["status"]) if r["status"] else "ERR"
        latency = f"{r['latency_ms']:.1f}ms"
        health = "HEALTHY" if r["healthy"] else "UNHEALTHY"
        url_display = r["url"][:48] + ".." if len(r["url"]) > 50 else r["url"]
        print(f"{url_display:<50} {status:<8} {latency:<12} {health:<8}")

    # 统计
    total = len(results)
    healthy = sum(1 for r in results if r["healthy"])
    print("-" * 80)
    print(f"Total: {total}  Healthy: {healthy}  Unhealthy: {total - healthy}")
    print(f"Health Rate: {healthy / total * 100:.1f}%")


async def main():
    # 示例 URL 列表
    urls = [
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/500",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/404",
        "https://httpbin.org/get",
    ]

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            urls = [line.strip() for line in f if line.strip()]

    results = await check_all(urls, concurrency=10)
    print_report(results)


if __name__ == "__main__":
    asyncio.run(main())
```

### 练习 2：进阶场景 -- 封装 Kubernetes API 客户端

```python
#!/usr/bin/env python3
"""
练习 2：Kubernetes API 客户端封装
要求：
1. 使用 requests 封装 K8s API 的常用操作
2. 支持 ServiceAccount Token 认证
3. 包含连接池、超时、重试
4. 支持获取 Pod 列表、Deployment 状态等
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os
from typing import Optional


class K8sClient:
    """
    简易 Kubernetes API 客户端

    SRE 场景：
    - 从 Pod 内部查询其他服务的状态
    - 自动化部署脚本
    - 故障排查工具
    """

    def __init__(
        self,
        api_server: str = None,
        token: str = None,
        verify_ssl: bool = True,
        ca_cert: str = None,
    ):
        # 默认从 ServiceAccount 读取
        self.api_server = api_server or os.environ.get(
            "KUBERNETES_SERVICE_HOST",
            "https://kubernetes.default.svc"
        )
        if not api_server and "KUBERNETES_SERVICE_HOST" in os.environ:
            port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
            self.api_server = f"https://{os.environ['KUBERNETES_SERVICE_HOST']}:{port}"

        # Token: 优先使用传入的，否则从 ServiceAccount 读取
        self.token = token or self._load_service_account_token()

        # 创建 Session
        self.session = requests.Session()
        self.session.verify = ca_cert or verify_ssl
        self.session.headers["Authorization"] = f"Bearer {self.token}"

        # 配置重试和连接池
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=10)
        self.session.mount("https://", adapter)

    def _load_service_account_token(self) -> Optional[str]:
        """从 ServiceAccount 加载 Token"""
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        try:
            with open(token_path) as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def get_pods(self, namespace: str = "default", label_selector: str = None) -> list:
        """获取 Pod 列表"""
        params = {}
        if label_selector:
            params["labelSelector"] = label_selector

        resp = self.session.get(
            f"{self.api_server}/api/v1/namespaces/{namespace}/pods",
            params=params,
            timeout=(3, 10),
        )
        resp.raise_for_status()
        return resp.json()["items"]

    def get_deployment_status(self, name: str, namespace: str = "default") -> dict:
        """获取 Deployment 状态"""
        resp = self.session.get(
            f"{self.api_server}/apis/apps/v1/namespaces/{namespace}/deployments/{name}",
            timeout=(3, 10),
        )
        resp.raise_for_status()
        deploy = resp.json()
        status = deploy.get("status", {})
        spec = deploy.get("spec", {})
        return {
            "name": name,
            "namespace": namespace,
            "replicas": spec.get("replicas", 0),
            "ready_replicas": status.get("readyReplicas", 0),
            "available_replicas": status.get("availableReplicas", 0),
            "updated_replicas": status.get("updatedReplicas", 0),
            "conditions": status.get("conditions", []),
        }

    def get_nodes(self) -> list:
        """获取集群节点列表"""
        resp = self.session.get(
            f"{self.api_server}/api/v1/nodes",
            timeout=(3, 10),
        )
        resp.raise_for_status()
        return resp.json()["items"]

    def close(self):
        """关闭连接"""
        self.session.close()


def demo():
    """使用示例"""
    client = K8sClient()
    try:
        # 获取 default namespace 的所有 Pod
        pods = client.get_pods()
        for pod in pods:
            name = pod["metadata"]["name"]
            phase = pod["status"]["phase"]
            print(f"  Pod: {name}, Phase: {phase}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    demo()
```

### 练习 3：故障排查挑战 -- 诊断连接超时

```python
#!/usr/bin/env python3
"""
练习 3：网络故障诊断工具
挑战：以下代码存在多个问题，请找出并修复

症状：
1. 有时请求会挂起很久才返回
2. 高并发时偶尔出现 ConnectionResetError
3. 部分请求报 "Connection pool is full"
"""

# === 问题代码（请找出所有 Bug） ===

import requests
import time

# Bug 1: 没有设置超时
def check_service_buggy(url):
    resp = requests.get(url)  # 没有 timeout!
    return resp.status_code

# Bug 2: 每次创建新 session（连接泄漏）
def check_all_services_buggy(urls):
    results = []
    for url in urls:
        session = requests.Session()  # 每次都创建新 session
        try:
            resp = session.get(url, timeout=5)
            results.append(resp.status_code)
        except Exception:
            results.append(None)
        # Bug 3: 没有关闭 session
    return results

# Bug 4: 重试时没有退避
def call_with_retry_buggy(url, retries=3):
    for i in range(retries):
        try:
            return requests.get(url, timeout=5)
        except Exception:
            continue  # 立即重试，没有等待
    return None


# === 修复后的代码 ===

def check_service_fixed(url: str, timeout: tuple = (3, 10)) -> dict:
    """
    修复 1: 添加超时控制
    分别设置连接超时和读取超时
    """
    start = time.monotonic()
    try:
        with requests.Session() as session:
            resp = session.get(url, timeout=timeout)
            return {
                "url": url,
                "status": resp.status_code,
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
                "ok": resp.ok,
            }
    except requests.exceptions.Timeout:
        return {"url": url, "status": None, "error": "timeout"}
    except requests.exceptions.ConnectionError as e:
        return {"url": url, "status": None, "error": str(e)}


def check_all_services_fixed(urls: list[str], max_workers: int = 20) -> list[dict]:
    """
    修复 2 & 3: 使用共享 Session + 连接池
    使用 ThreadPoolExecutor 并发检查
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=max_workers,
        pool_maxsize=max_workers,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    def _check(url: str) -> dict:
        start = time.monotonic()
        try:
            resp = session.get(url, timeout=(3, 10))
            return {
                "url": url,
                "status": resp.status_code,
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
        except Exception as e:
            return {"url": url, "error": str(e)}

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check, url): url for url in urls}
        for future in as_completed(futures):
            results.append(future.result())

    session.close()
    return results


def call_with_retry_fixed(url: str, max_retries: int = 3) -> dict:
    """
    修复 4: 添加指数退避重试
    """
    import random

    for attempt in range(max_retries + 1):
        try:
            with requests.Session() as session:
                resp = session.get(url, timeout=(3, 10))
                resp.raise_for_status()
                return {"status": resp.status_code, "data": resp.json()}
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                # 指数退避 + 随机抖动
                delay = min(2 ** attempt, 30) * random.uniform(0.5, 1.5)
                time.sleep(delay)
            else:
                return {"error": str(e), "attempts": max_retries + 1}


if __name__ == "__main__":
    # 测试修复后的代码
    result = check_service_fixed("https://httpbin.org/get")
    print(f"Check result: {result}")
```

---

## 🎯 面试题精选

### 题目 1：requests.get() 和 session.get() 有什么区别？

**参考答案：**

`requests.get()` 每次调用都会创建一个新的 Session 对象，请求结束后 Session 被销毁，TCP 连接也随之关闭。这意味着每次请求都要经历完整的 TCP 三次握手和 TLS 握手（HTTPS 场景），性能较差。

`session.get()` 使用一个持久化的 Session 对象，底层维护了连接池（基于 urllib3 的 PoolManager），TCP 连接可以被复用，省去了重复握手的开销。此外，Session 还可以统一管理 headers、cookies、auth 等配置。

SRE 建议：在需要多次请求同一服务时，始终使用 Session。特别是对于服务间调用，应该使用全局共享的 Session 实例。

### 题目 2：什么是 HTTP 连接池？为什么要使用它？

**参考答案：**

HTTP 连接池是一种管理 TCP 连接的机制，它维护一组可复用的 TCP 连接，避免每次 HTTP 请求都创建和销毁连接。

使用连接池的好处：
1. **减少延迟**：复用已有连接，省去 TCP 三次握手和 TLS 握手的时间
2. **降低资源消耗**：减少 socket 文件描述符的创建和销毁
3. **控制并发**：通过 pool_maxsize 限制对同一 host 的最大并发连接数，避免打满下游服务
4. **提高吞吐**：减少 TIME_WAIT 状态的连接数

在 Python 中，requests 底层使用 urllib3 的连接池，通过 HTTPAdapter 配置 pool_connections（不同 host 的连接池数量）和 pool_maxsize（每个 host 的最大连接数）。

### 题目 3：解释指数退避（Exponential Backoff）及其在重试机制中的作用

**参考答案：**

指数退避是一种重试策略，每次重试的等待时间按指数增长：delay = base * 2^attempt。

作用：
1. **给服务恢复时间**：如果服务暂时过载，快速重试只会加重负担
2. **避免惊群效应**：多个客户端同时重试可能造成更大的冲击
3. **提高成功率**：等待更长时间后重试，成功率通常更高

为什么需要随机抖动（Jitter）？
如果所有客户端都使用相同的退避策略，它们会在相同的时间点重试，形成"重试风暴"。抖动通过随机化等待时间来分散重试请求，平滑服务器负载。

公式：delay = random(0, min(base * 2^attempt, max_delay))

### 题目 4：TCP 的 TIME_WAIT 状态是什么？对 SRE 有什么影响？

**参考答案：**

TIME_WAIT 是 TCP 连接关闭过程中的一个状态。当主动关闭连接的一方发送最后一个 ACK 后，会进入 TIME_WAIT 状态，等待 2MSL（Maximum Segment Lifetime，通常 60 秒）后才真正关闭。

对 SRE 的影响：
1. **端口耗尽**：高并发短连接场景下，大量 TIME_WAIT 连接可能耗尽可用端口
2. **服务重启失败**：如果服务重启时旧连接仍在 TIME_WAIT，bind 同一端口会失败（需要 SO_REUSEADDR）
3. **连接池优化的驱动力**：使用连接池复用连接，从根本上减少 TIME_WAIT 的产生

解决方案：
- 使用 HTTP 连接池复用连接
- 设置 SO_REUSEADDR socket 选项
- 调整内核参数 tcp_tw_reuse（谨慎使用）

### 题目 5：requests、httpx、aiohttp 三个 HTTP 客户端库如何选择？

**参考答案：**

| 场景 | 推荐库 | 理由 |
|------|--------|------|
| 简单脚本、一次性任务 | requests | 最简单，生态最好 |
| 新项目、需要 HTTP/2 | httpx | API 现代，同时支持同步和异步 |
| 高并发异步场景 | aiohttp | 纯异步，性能最好 |
| 需要 WebSocket | aiohttp | 原生支持 WebSocket |
| 兼容 requests 生态 | httpx | API 设计与 requests 高度兼容 |

SRE 实际建议：
- 对于日常运维脚本，requests 足够
- 对于新的微服务客户端 SDK，推荐 httpx
- 对于高并发的监控数据采集器，推荐 aiohttp
- 迁移时注意 httpx 的默认行为更严格（如不信任环境代理）

### 题目 6：如何排查 "Connection pool is full" 错误？

**参考答案：**

这个错误表示连接池中所有连接都被占用，新的请求无法获取连接。

排查步骤：
1. **检查连接泄漏**：是否在代码中创建了 Session 但没有关闭？是否使用了全局 Session 但没有配置连接池大小？
2. **检查连接池配置**：pool_maxsize 是否太小？对于高并发场景，默认值可能不够
3. **检查下游服务响应时间**：如果下游服务响应慢，连接会长时间被占用
4. **检查 netstat**：查看 CLOSE_WAIT 和 ESTABLISHED 状态的连接数

修复方案：
- 使用全局 Session 实例，配置合理的 pool_maxsize
- 使用 Semaphore 或队列限制并发请求数
- 设置合理的超时时间，避免连接长时间被占用
- 对于 aiohttp，使用 TCPConnector 的 limit 参数

### 题目 7：HTTP 超时应该设置为多少？为什么？

**参考答案：**

没有一个万能的超时值，应该根据具体场景设置：

1. **连接超时**（connect timeout）：3-5 秒
   - 如果 3 秒内无法建立 TCP 连接，说明网络或目标服务有严重问题
   - 不需要等待太久

2. **读取超时**（read timeout）：取决于 API 特性
   - 健康检查：3-5 秒
   - 普通 API 查询：10-30 秒
   - 报表/批处理：60-120 秒
   - 流式传输：按 chunk 设置

3. **关键原则**：
   - 永远不要不设超时（默认超时可能是无限）
   - 上游超时 < 下游超时之和（避免级联超时）
   - 基于 P99 延迟设置，而不是平均延迟
   - 留出重试的时间余量

### 题目 8：解释 I/O 多路复用中 select、poll、epoll 的区别

**参考答案：**

I/O 多路复用允许单个线程同时监控多个文件描述符（socket），在任何一个就绪时得到通知。

| 特性 | select | poll | epoll |
|------|--------|------|-------|
| 数据结构 | fd_set (位图) | pollfd 数组 | 红黑树 + 就绪链表 |
| 最大 FD 数 | 1024 (FD_SETSIZE) | 无硬限制 | 无硬限制 |
| 每次调用开销 | 拷贝全部 FD 集合 | 拷贝全部 FD 数组 | 只关注变化的 FD |
| 时间复杂度 | O(n) | O(n) | O(1) |
| 触发模式 | 水平触发 | 水平触发 | 水平/边缘触发 |
| Python | select.select() | - | selectors.DefaultSelector() |

在 Python 中，推荐使用 `selectors` 模块，它会自动选择当前平台最优的实现（Linux 上用 epoll，macOS 上用 kqueue）。

### 题目 9：如何设计一个高可用的 HTTP 客户端？

**参考答案：**

高可用 HTTP 客户端应该包含以下要素：

1. **连接管理**：连接池复用、连接健康检查、连接超时回收
2. **超时控制**：分层超时（连接/读取/写入）、级联超时设计
3. **重试机制**：指数退避 + 抖动、可重试错误码白名单、幂等性保证
4. **熔断降级**：连续失败达到阈值时快速失败、定期探测恢复
5. **可观测性**：请求日志、延迟指标、错误率统计
6. **负载均衡**：多 endpoint 轮询、基于延迟的选择
7. **优雅降级**：缓存最后一次成功响应、返回默认值

### 题目 10：解释 TCP 与 UDP 的区别，以及各自的 SRE 应用场景

**参考答案：**

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接方式 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 可靠（确认重传） | 不可靠 |
| 顺序性 | 保证顺序 | 不保证 |
| 速度 | 较慢（握手+确认） | 较快 |
| 适用场景 | API 调用、数据库连接、SSH | DNS 查询、监控上报、日志采集 |

SRE 应用场景：
- **TCP**：Kubernetes API 调用、数据库连接、服务间 RPC、SSH 远程管理
- **UDP**：StatsD 监控指标上报（容忍少量丢失）、Syslog 日志收集、DNS 解析、NTP 时间同步

选择原则：需要可靠性用 TCP，需要低延迟且容忍丢失用 UDP。监控数据通常用 UDP，因为少量数据丢失不影响趋势分析，但高延迟会影响实时告警。

---

## 📚 深入阅读

### 官方文档

- [Python socket 官方文档](https://docs.python.org/3/library/socket.html)
- [Python selectors 官方文档](https://docs.python.org/3/library/selectors.html)
- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
- [requests 官方文档](https://requests.readthedocs.io/en/latest/)
- [httpx 官方文档](https://www.python-httpx.org/)
- [aiohttp 官方文档](https://docs.aiohttp.org/en/stable/)
- [urllib3 官方文档](https://urllib3.readthedocs.io/en/stable/)

### 推荐书籍

- 《Python 网络编程攻略》 -- Dr. M. O. Faruque Sarker
- 《HTTP 权威指南》 -- David Gourley, Brian Totty
- 《TCP/IP 详解 卷1：协议》 -- W. Richard Stevens
- 《高性能 Python》 -- Micha Gorelick, Ian Ozsvald -- 第7章 网络

### 技术博客

- [The Hitchhiker's Guide to Python: Requests](https://docs.python-guide.org/scenarios/web/)
- [urllib3 Best Practices](https://urllib3.readthedocs.io/en/latest/advanced-usage.html)
- [httpx vs requests comparison](https://www.python-httpx.org/advanced/)

---

## ✅ 自检清单

- [ ] 能解释 TCP 三次握手和四次挥手的过程
- [ ] 能用 socket 模块实现基本的 TCP 客户端和服务端
- [ ] 理解 I/O 多路复用（select/epoll）的原理和 Python 实现
- [ ] 能使用 requests 创建带连接池、重试、超时控制的 Session
- [ ] 理解 httpx 与 requests 的异同，知道何时选择哪个
- [ ] 能用 aiohttp 实现异步的批量 HTTP 请求
- [ ] 能设计指数退避 + 抖动的重试策略
- [ ] 理解超时级联问题，能正确配置分层超时
- [ ] 能编写生产级的健康检查工具
- [ ] 能诊断和修复连接泄漏问题
