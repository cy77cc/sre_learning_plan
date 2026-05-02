# Day 48: Python 网络编程与 HTTP 客户端

> 📅 日期：2026-05-02
> 📖 学习主题：Python 网络编程与 HTTP 客户端
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 requests 库的高级用法
- 理解 socket 编程基础
- 能编写 HTTP 客户端与 REST API 交互

---

## 📖 详细知识点

### 1. requests 高级用法

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 会话（保持连接）
session = requests.Session()
session.headers.update({"User-Agent": "SRE-Tool/1.0"})

# 重试策略
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 发送请求
resp = session.get("https://api.example.com/data", params={"page": 1})
resp.raise_for_status()  # 抛出 HTTP 错误
data = resp.json()

# 上传文件
with open("backup.tar.gz", "rb") as f:
    session.put("https://storage.example.com/file", data=f)

# 超时设置
resp = requests.get(url, timeout=(3.05, 30))  # (connect, read)
```

### 2. Socket 编程基础

```python
import socket

# TCP 客户端
def tcp_client(host, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode())
        data = s.recv(1024)
        return data.decode()

# TCP 服务端
def tcp_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        conn, addr = s.accept()
        with conn:
            data = conn.recv(1024)
            conn.sendall(b"OK")

# UDP
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(b"hello", ("localhost", 9999))
    data, addr = s.recvfrom(1024)
```

### 3. 实战：API 健康检查

```python
#!/usr/bin/env python3
"""API health checker with retry and timeout."""

import requests
import sys
import time


def check_api(url, retries=3, timeout=5):
    session = requests.Session()
    for i in range(retries):
        try:
            start = time.time()
            resp = session.get(url, timeout=timeout)
            elapsed = time.time() - start
            print(f"OK {url} {resp.status_code} {elapsed:.3f}s")
            return True
        except requests.RequestException as e:
            print(f"FAIL {url} attempt {i+1}: {e}")
            if i < retries - 1:
                time.sleep(2 ** i)
    return False


urls = ["http://localhost:8080/health", "http://localhost:9090/metrics"]
all_ok = all(check_api(u) for u in urls)
sys.exit(0 if all_ok else 1)
```

---

## 4. HTTP 方法详解

```python
# GET - 获取资源
resp = requests.get("https://api.example.com/users/1")

# POST - 创建资源
resp = requests.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"},
)

# PUT - 替换资源
resp = requests.put(
    "https://api.example.com/users/1",
    json={"name": "Alice Updated"},
)

# PATCH - 部分更新
resp = requests.patch(
    "https://api.example.com/users/1",
    json={"email": "new@example.com"},
)

# DELETE - 删除资源
resp = requests.delete("https://api.example.com/users/1")
```

## 5. HTTP 状态码处理

```python
def handle_response(resp):
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 201:
        print("Resource created")
        return resp.json()
    elif resp.status_code == 204:
        print("No content")
        return None
    elif resp.status_code == 400:
        print(f"Bad request: {resp.text}")
        return None
    elif resp.status_code == 401:
        print("Unauthorized - check credentials")
        return None
    elif resp.status_code == 403:
        print("Forbidden - insufficient permissions")
        return None
    elif resp.status_code == 404:
        print("Not found")
        return None
    elif resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", 5)
        print(f"Rate limited, retry after {retry_after}s")
        return None
    elif resp.status_code >= 500:
        print(f"Server error: {resp.status_code}")
        return None
    else:
        print(f"Unexpected status: {resp.status_code}")
        return None
```

## 6. 分页处理

```python
def fetch_all_pages(base_url, session=None):
    """Fetch all pages from a paginated API."""
    session = session or requests.Session()
    all_data = []
    page = 1

    while True:
        resp = session.get(f"{base_url}?page={page}&per_page=100")
        resp.raise_for_status()
        data = resp.json()

        if not data:
            break

        all_data.extend(data)

        # Check for next page
        if "next" not in resp.links:
            break
        page += 1

    return all_data
```

## 7. 实战：端口扫描工具

```python
#!/usr/bin/env python3
"""TCP port scanner using sockets."""

import socket
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


def scan_port(host, port, timeout=1):
    """Scan a single port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return port, result == 0
    except socket.error:
        return port, False


def scan(host, ports, max_workers=50):
    """Scan multiple ports concurrently."""
    open_ports = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(scan_port, host, p): p for p in ports
        }
        for future in as_completed(futures):
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
    return sorted(open_ports)


def main():
    parser = argparse.ArgumentParser(description="TCP Port Scanner")
    parser.add_argument("host", help="Target host")
    parser.add_argument("-p", "--ports", default="1-1024", help="Port range")
    parser.add_argument("-t", "--threads", type=int, default=50)
    args = parser.parse_args()

    # Parse port range
    if "-" in args.ports:
        start, end = args.ports.split("-")
        ports = range(int(start), int(end) + 1)
    else:
        ports = [int(p) for p in args.ports.split(",")]

    print(f"Scanning {args.host}...")
    open_ports = scan(args.host, ports, args.threads)

    if open_ports:
        print(f"Open ports on {args.host}:")
        for port in open_ports:
            print(f"  {port}/tcp")
    else:
        print("No open ports found")


if __name__ == "__main__":
    main()
```

---

## 🧪 练习题

### 练习 1：并发 URL 检查

用 ThreadPoolExecutor 并发检查 100 个 URL 的健康状态。

<details>
<summary>答案</summary>

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def check(url):
    try:
        r = requests.get(url, timeout=5)
        return url, r.status_code, True
    except Exception as e:
        return url, None, False

urls = [f"http://example.com/page/{i}" for i in range(100)]
with ThreadPoolExecutor(max_workers=20) as ex:
    for f in as_completed(ex.submit(check, u) for u in urls):
        url, status, ok = f.result()
        print(f"{'OK' if ok else 'FAIL'} {url}")
```
</details>

### 练习 2：Socket 实现简单的 HTTP 服务器

<details>
<summary>答案</summary>

```python
import socket

def simple_server(host="0.0.0.0", port=8080):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print(f"Listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024)
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    "\r\n"
                    "<h1>Hello World</h1>"
                )
                conn.sendall(response.encode())
```
</details>

---

## 📖 补充知识：HTTPS 与 TLS

### 8. TLS 握手过程

```
客户端                              服务器
  │                                   │
  │  ClientHello                      │
  │  (支持的TLS版本、加密套件)         │
  │ ────────────────────────────────→│
  │                                   │
  │  ServerHello                      │
  │  (选择的TLS版本、加密套件)         │
  │  Certificate (服务器证书)          │
  │ ←─────────────────────────────── │
  │                                   │
  │  ClientKeyExchange                │
  │  ChangeCipherSpec                 │
  │ ────────────────────────────────→│
  │                                   │
  │  ←── 加密通信开始 ──→              │
```

### 9. 证书验证

```python
# requests 默认验证证书
requests.get("https://example.com")  # 验证证书

# 跳过验证（不推荐）
requests.get("https://example.com", verify=False)

# 使用自定义 CA
requests.get("https://example.com", verify="/path/to/ca.pem")

# 查看证书信息
import ssl
import socket

context = ssl.create_default_context()
with socket.create_connection(("example.com", 443)) as sock:
    with context.wrap_socket(sock, server_hostname="example.com") as ssock:
        cert = ssock.getpeercert()
        print(cert)
```

---

## 📚 扩展阅读

- [requests 文档](https://requests.readthedocs.io/)
- [Python socket 文档](https://docs.python.org/3/library/socket.html)
- [urllib3 高级用法](https://urllib3.readthedocs.io/)
