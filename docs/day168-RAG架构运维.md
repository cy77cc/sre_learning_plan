# Day 168: RAG 架构运维

> 阶段七：AI 基础设施与 LLMOps | Week 25 | Day 1

## 今日学习目标

1. 掌握向量数据库的运维（Milvus 集群部署、pgvector、Weaviate）
2. 学会 Embedding 服务的部署与扩展策略
3. 理解 RAG 检索流水线的监控（检索延迟、召回率）
4. 掌握向量索引管理（HNSW/IVF 参数调优、索引重建）
5. 学会 Chunk 切分优化（重叠、语义切分）
6. 理解 RAG 评估指标（检索精度/召回、回答相关性、忠实度）

---

## 核心知识点

### 1. RAG 流水线架构

#### 1.1 完整 RAG 流水线

```
┌──────────────────────────────────────────────────────────────────┐
│                    RAG 完整流水线架构                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  离线流水线（文档摄取）                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ 文档源   │───→│ 文档解析 │───→│ Chunk 切分│            │ │
│  │  │ PDF/HTML │    │ 文本提取 │    │ 语义分割  │            │ │
│  │  │ Word/MD  │    │ 元数据   │    │ 重叠窗口  │            │ │
│  │  └──────────┘    └──────────┘    └────┬─────┘            │ │
│  │                                       │                   │ │
│  │                                       ▼                   │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ 索引存储 │◄───│ 向量化   │◄───│ Chunk 清洗│            │ │
│  │  │ Milvus   │    │Embedding │    │ 去重/过滤│            │ │
│  │  │ pgvector │    │ Model    │    │          │            │ │
│  │  └──────────┘    └──────────┘    └──────────┘            │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  在线流水线（查询响应）                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ 用户查询 │───→│ 查询编码 │───→│ 向量检索 │            │ │
│  │  │ "..."    │    │Embedding │    │ Top-K    │            │ │
│  │  └──────────┘    └──────────┘    └────┬─────┘            │ │
│  │                                       │                   │ │
│  │                                       ▼                   │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ LLM 生成 │◄───│ Prompt   │◄───│ 上下文拼接│            │ │
│  │  │ 回答     │    │ 模板     │    │ 相关片段  │            │ │
│  │  └──────────┘    └──────────┘    └──────────┘            │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  延迟分解:                                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  查询编码 (Embedding):  10~50ms                            │ │
│  │  向量检索 (Milvus):     5~50ms                             │ │
│  │  Prompt 拼接:           <1ms                               │ │
│  │  LLM 生成 (TTFT):      200~2000ms                         │ │
│  │  LLM 生成 (Token):     30~100 tokens/s                    │ │
│  │  ─────────────────────────────                             │ │
│  │  总延迟 (首 Token):     250~2100ms                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2. 向量数据库运维

#### 2.1 向量数据库对比

| 特性 | Milvus | pgvector | Weaviate | Qdrant |
|------|--------|----------|----------|--------|
| 部署复杂度 | 高（分布式） | 低（PG 扩展） | 中 | 中 |
| 可扩展性 | 百亿级 | 千万级 | 十亿级 | 十亿级 |
| 索引类型 | HNSW/IVF/DiskANN | HNSW/IVF | HNSW | HNSW |
| 混合搜索 | 支持 | 支持 | 支持 | 支持 |
| 多租户 | 支持 | Schema 级 | Class 级 | Collection 级 |
| 运维成本 | 高 | 低 | 中 | 中 |
| 适用场景 | 大规模生产 | 小规模/已有 PG | 中大规模 | 中大规模 |

#### 2.2 Milvus 集群部署

```yaml
# milvus-cluster-values.yaml (Helm)
# helm repo add milvus https://milvus-io.github.io/milvus-helm
# helm install milvus milvus/milvus -f milvus-cluster-values.yaml

cluster:
  enabled: true

# etcd 集群（元数据存储）
etcd:
  replicaCount: 3
  persistence:
    enabled: true
    size: 20Gi
  resources:
    requests:
      cpu: 500m
      memory: 1Gi

# MinIO 对象存储（数据存储）
minio:
  mode: distributed
  replicas: 4
  persistence:
    enabled: true
    size: 100Gi
  resources:
    requests:
      cpu: 500m
      memory: 1Gi

# Pulsar 消息队列（日志流）
pulsar:
  enabled: true
  broker:
    replicaCount: 2
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
  bookkeeper:
    replicaCount: 3
    resources:
      requests:
        cpu: 500m
        memory: 1Gi

# Milvus Proxy（接入层）
proxy:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: "2"
      memory: 4Gi

# Milvus IndexNode（索引构建）
indexNode:
  replicas: 2
  resources:
    requests:
      cpu: "2"
      memory: 4Gi
    limits:
      cpu: "4"
      memory: 8Gi

# Milvus QueryNode（查询服务）
queryNode:
  replicas: 3
  resources:
    requests:
      cpu: "2"
      memory: 4Gi
    limits:
      cpu: "4"
      memory: 8Gi

# Milvus DataNode（数据写入）
dataNode:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 2Gi

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

#### 2.3 pgvector 部署

```yaml
# pgvector-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pgvector
  namespace: vector-db
spec:
  serviceName: pgvector
  replicas: 3
  selector:
    matchLabels:
      app: pgvector
  template:
    metadata:
      labels:
        app: pgvector
    spec:
      containers:
      - name: postgres
        image: pgvector/pgvector:pg16
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: pgvector-secret
              key: password
        - name: POSTGRES_DB
          value: vectordb
        resources:
          requests:
            cpu: "2"
            memory: 8Gi
          limits:
            cpu: "4"
            memory: 16Gi
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        readinessProbe:
          exec:
            command: ["pg_isready", "-U", "postgres"]
          periodSeconds: 10
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: pgvector-data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
# pgvector 初始化 SQL
apiVersion: v1
kind: ConfigMap
metadata:
  name: pgvector-init
  namespace: vector-db
data:
  init.sql: |
    -- 启用 pgvector 扩展
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 创建文档向量表
    CREATE TABLE IF NOT EXISTS documents (
        id BIGSERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        metadata JSONB DEFAULT '{}',
        embedding vector(1536),  -- OpenAI embedding 维度
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- 创建 HNSW 索引
    CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

    -- 创建元数据索引
    CREATE INDEX IF NOT EXISTS idx_documents_metadata
    ON documents USING gin (metadata);

    -- 创建全文搜索索引
    CREATE INDEX IF NOT EXISTS idx_documents_content_fts
    ON documents USING gin (to_tsvector('english', content));
```

#### 2.4 Milvus 运维管理脚本

```python
"""
milvus_admin.py
Milvus 向量数据库运维管理工具
"""

from pymilvus import (
    connections, Collection, CollectionSchema,
    FieldSchema, DataType, utility
)
import time

class MilvusAdmin:
    """Milvus 管理工具"""

    def __init__(self, host: str = "localhost", port: int = 19530):
        connections.connect(host=host, port=port)

    def create_collection(self, name: str, dim: int = 1536):
        """创建 Collection"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, description=f"RAG document collection: {name}")
        collection = Collection(name, schema)

        # 创建 HNSW 索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200}
        }
        collection.create_index("embedding", index_params)
        print(f"Collection '{name}' created with HNSW index")
        return collection

    def get_collection_stats(self, name: str) -> dict:
        """获取 Collection 统计信息"""
        collection = Collection(name)
        collection.load()
        stats = {
            "name": name,
            "num_entities": collection.num_entities,
            "schema": str(collection.schema),
            "indexes": [idx.params for idx in collection.indexes],
            "loaded": utility.load_state(name),
        }
        return stats

    def rebuild_index(self, name: str, index_type: str = "HNSW", params: dict = None):
        """重建索引（用于参数调优）"""
        collection = Collection(name)

        # 删除旧索引
        collection.drop_index()
        print(f"Dropped old index on '{name}'")

        # 创建新索引
        if params is None:
            params = {"M": 16, "efConstruction": 200}

        index_params = {
            "metric_type": "COSINE",
            "index_type": index_type,
            "params": params
        }
        start = time.time()
        collection.create_index("embedding", index_params)
        elapsed = time.time() - start
        print(f"Rebuilt {index_type} index on '{name}' in {elapsed:.1f}s")
        print(f"Params: {params}")

    def benchmark_search(self, name: str, dim: int = 1536, top_k: int = 10,
                         n_queries: int = 100) -> dict:
        """搜索性能基准测试"""
        import random
        collection = Collection(name)
        collection.load()

        # 生成随机查询向量
        query_vectors = [[random.random() for _ in range(dim)] for _ in range(n_queries)]

        search_params = {"metric_type": "COSINE", "params": {"ef": 128}}

        start = time.time()
        results = collection.search(
            data=query_vectors,
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content"]
        )
        elapsed = time.time() - start

        latencies = [r[0].distance for r in results]  # 占位
        return {
            "n_queries": n_queries,
            "total_time_s": round(elapsed, 3),
            "avg_latency_ms": round(elapsed / n_queries * 1000, 2),
            "qps": round(n_queries / elapsed, 1),
            "top_k": top_k,
        }

    def compact_collection(self, name: str):
        """压缩 Collection（清理已删除数据）"""
        collection = Collection(name)
        collection.compact()
        print(f"Compaction triggered for '{name}'")

    def list_collections(self) -> list[str]:
        """列出所有 Collection"""
        return utility.list_collections()
```

### 3. Embedding 服务部署与扩展

#### 3.1 Embedding 服务架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Embedding 服务架构                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  方案 1: 专用 Embedding 模型部署                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────┐    ┌──────────────────┐                     │ │
│  │  │ RAG App  │───→│ Embedding Service │                     │ │
│  │  │          │    │ (TEI / Triton)    │                     │ │
│  │  │          │    │ ┌────┐ ┌────┐    │                     │ │
│  │  │          │    │ │GPU │ │GPU │    │                     │ │
│  │  │          │    │ │ 0  │ │ 1  │    │                     │ │
│  │  │          │    │ └────┘ └────┘    │                     │ │
│  │  └──────────┘    └──────────────────┘                     │ │
│  │                                                            │ │
│  │  优点: 独立扩展、资源隔离、高吞吐                          │ │
│  │  缺点: 额外服务管理                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  方案 2: 批量 Embedding（离线摄取）                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ 文档队列 │───→│ Batch    │───→│ 向量存储 │            │ │
│  │  │ (Kafka)  │    │ Embedding│    │ Milvus   │            │ │
│  │  └──────────┘    └──────────┘    └──────────┘            │ │
│  │                                                            │ │
│  │  Batch Size: 32~256（根据 GPU 显存调整）                   │ │
│  │  吞吐: 1000~5000 docs/s (A100)                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  方案 3: 实时 Embedding（在线查询）                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐            │ │
│  │  │ 查询请求 │───→│ Embedding│───→│ 向量检索 │            │ │
│  │  │          │    │ 服务     │    │ Milvus   │            │ │
│  │  └──────────┘    └──────────┘    └──────────┘            │ │
│  │                                                            │ │
│  │  延迟: 10~50ms                                            │ │
│  │  并发: 100~500 QPS                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2 TEI (Text Embeddings Inference) 部署

```yaml
# tei-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tei-bge-large
  namespace: embedding
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tei
      model: bge-large-zh
  template:
    metadata:
      labels:
        app: tei
        model: bge-large-zh
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      containers:
      - name: tei
        image: ghcr.io/huggingface/text-embeddings-inference:1.5
        args:
        - "--model-id"
        - "BAAI/bge-large-zh-v1.5"
        - "--max-batch-tokens"
        - "16384"
        - "--max-client-batch-size"
        - "32"
        ports:
        - containerPort: 8080
          name: http
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "8Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "4Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          periodSeconds: 10
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          periodSeconds: 30
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: tei-bge-large
  namespace: embedding
spec:
  selector:
    app: tei
    model: bge-large-zh
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

#### 3.3 Embedding 服务 Python 客户端

```python
"""
embedding_client.py
Embedding 服务客户端（支持批量和实时）
"""

import httpx
import asyncio
import numpy as np
from typing import Optional

class EmbeddingClient:
    """Embedding 服务客户端"""

    def __init__(self, endpoint: str, max_batch_size: int = 32):
        self.endpoint = endpoint.rstrip("/")
        self.max_batch_size = max_batch_size
        self.client = httpx.AsyncClient(timeout=60.0)

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """批量获取文本向量"""
        all_embeddings = []

        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            resp = await self.client.post(
                f"{self.endpoint}/embed",
                json={"inputs": batch}
            )
            resp.raise_for_status()
            all_embeddings.extend(resp.json())

        return np.array(all_embeddings)

    async def embed_query(self, query: str) -> np.ndarray:
        """单条查询向量化"""
        resp = await self.client.post(
            f"{self.endpoint}/embed",
            json={"inputs": [query]}
        )
        resp.raise_for_status()
        return np.array(resp.json()[0])

    async def embed_with_retry(self, texts: list[str], max_retries: int = 3) -> np.ndarray:
        """带重试的向量化"""
        for attempt in range(max_retries):
            try:
                return await self.embed_texts(texts)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

class EmbeddingPipeline:
    """完整的 Embedding 流水线"""

    def __init__(self, embedding_client: EmbeddingClient, vector_store):
        self.embedding = embedding_client
        self.store = vector_store

    async def ingest_documents(self, documents: list[dict], batch_size: int = 64):
        """摄取文档到向量库"""
        total = len(documents)
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc["content"] for doc in batch]
            metadatas = [doc.get("metadata", {}) for doc in batch]

            # 批量向量化
            embeddings = await self.embedding.embed_with_retry(texts)

            # 存入向量库
            await self.store.insert(
                embeddings=embeddings.tolist(),
                texts=texts,
                metadatas=metadatas
            )

            print(f"Ingested {min(i + batch_size, total)}/{total} documents")

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义检索"""
        # 查询向量化
        query_embedding = await self.embedding.embed_query(query)

        # 向量检索
        results = await self.store.search(
            embedding=query_embedding.tolist(),
            top_k=top_k
        )

        return results
```

### 4. 向量索引管理

#### 4.1 索引类型对比

```
┌──────────────────────────────────────────────────────────────────┐
│                    向量索引类型对比                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HNSW (Hierarchical Navigable Small World)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  原理: 多层图结构，从顶层快速定位到目标区域                 │ │
│  │                                                            │ │
│  │  Layer 2:  ●─────────●                                    │ │
│  │            │         │                                    │ │
│  │  Layer 1:  ●────●────●────●                               │ │
│  │            │    │    │    │                               │ │
│  │  Layer 0:  ●─●──●─●──●─●──●─●                            │ │
│  │                                                            │ │
│  │  参数:                                                     │ │
│  │  ├── M: 每层连接数 (默认 16，越大越精确越慢)              │ │
│  │  ├── efConstruction: 建索引时的搜索范围 (默认 200)         │ │
│  │  └── ef: 查询时的搜索范围 (默认 128，越大越精确越慢)      │ │
│  │                                                            │ │
│  │  特点:                                                     │ │
│  │  ├── 查询速度快 (毫秒级)                                  │ │
│  │  ├── 内存占用大 (全量在内存)                               │ │
│  │  ├── 适合百万~千万级数据                                   │ │
│  │  └── 不适合频繁更新                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  IVF (Inverted File Index)                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  原理: 先聚类，查询时只搜索最近的几个聚类                  │ │
│  │                                                            │ │
│  │  Cluster 1    Cluster 2    Cluster 3                       │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐                      │ │
│  │  │ ●  ●  │  │ ●  ●  │  │ ●  ●  │                      │ │
│  │  │ ●  ●  │  │ ●  ●  │  │ ●  ●  │                      │ │
│  │  └────────┘  └────────┘  └────────┘                      │ │
│  │                                                            │ │
│  │  参数:                                                     │ │
│  │  ├── nlist: 聚类中心数 (通常 sqrt(N))                     │ │
│  │  └── nprobe: 查询时搜索的聚类数 (越大越精确越慢)          │ │
│  │                                                            │ │
│  │  特点:                                                     │ │
│  │  ├── 内存占用较小 (可配合 PQ 量化)                        │ │
│  │  ├── 适合亿级数据                                         │ │
│  │  ├── 查询速度比 HNSW 稍慢                                 │ │
│  │  └── 支持增量更新                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  DiskANN                                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  原理: 基于磁盘的近似最近邻搜索                           │ │
│  │  特点:                                                     │ │
│  │  ├── 支持超大规模 (十亿级)                                │ │
│  │  ├── 内存占用极低                                         │ │
│  │  ├── 查询延迟较高 (10~50ms)                               │ │
│  │  └── 适合内存受限场景                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2 索引参数调优

```python
"""
index_tuning.py
HNSW 索引参数调优工具
"""

import time
import random
from pymilvus import Collection, connections

def benchmark_hnsw_params(collection_name: str, dim: int = 1536):
    """HNSW 参数调优基准测试"""
    collection = Collection(collection_name)

    # 参数组合
    param_combinations = [
        {"M": 8,  "efConstruction": 100},
        {"M": 16, "efConstruction": 200},
        {"M": 32, "efConstruction": 200},
        {"M": 16, "efConstruction": 400},
    ]

    ef_values = [32, 64, 128, 256]

    results = []
    for build_params in param_combinations:
        # 重建索引
        collection.drop_index()
        start = time.time()
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": build_params
        }
        collection.create_index("embedding", index_params)
        build_time = time.time() - start

        collection.load()

        # 测试不同 ef 值
        for ef in ef_values:
            query_vectors = [[random.random() for _ in range(dim)] for _ in range(50)]
            search_params = {"metric_type": "COSINE", "params": {"ef": ef}}

            start = time.time()
            collection.search(
                data=query_vectors,
                anns_field="embedding",
                param=search_params,
                limit=10
            )
            elapsed = time.time() - start

            results.append({
                "M": build_params["M"],
                "efConstruction": build_params["efConstruction"],
                "ef": ef,
                "build_time_s": round(build_time, 1),
                "query_latency_ms": round(elapsed / 50 * 1000, 2),
                "qps": round(50 / elapsed, 1),
            })

    return results

# 推荐配置
RECOMMENDED_CONFIGS = {
    "low_latency": {
        "M": 16, "efConstruction": 200, "ef": 64,
        "适用": "延迟敏感场景 (<10ms)",
        "数据量": "百万级"
    },
    "balanced": {
        "M": 16, "efConstruction": 200, "ef": 128,
        "适用": "通用场景",
        "数据量": "百万~千万级"
    },
    "high_recall": {
        "M": 32, "efConstruction": 400, "ef": 256,
        "适用": "召回率优先",
        "数据量": "百万级"
    },
    "large_scale": {
        "M": 16, "efConstruction": 200, "ef": 128,
        "适用": "大规模数据",
        "数据量": "千万~亿级（配合 IVF）"
    },
}
```

### 5. Chunk 切分优化

#### 5.1 切分策略对比

```
┌──────────────────────────────────────────────────────────────────┐
│                    Chunk 切分策略对比                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  策略 1: 固定长度切分                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [This is a sample text that...] [text that will be split] │ │
│  │  |<------- 512 tokens ------>| |<------ 512 tokens ------>|| │
│  │  |<--- overlap 64 tokens --->|                            │ │
│  │                                                            │ │
│  │  参数: chunk_size=512, chunk_overlap=64                    │ │
│  │  优点: 实现简单，大小可控                                  │ │
│  │  缺点: 可能切断句子/段落语义                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  策略 2: 语义切分                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [段落 1: 关于向量数据库的介绍...]                         │ │
│  │  [段落 2: HNSW 索引的原理是...]                            │ │
│  │  [段落 3: 在实际部署中需要注意...]                         │ │
│  │                                                            │ │
│  │  依据: 段落/标题/换行符/语义相似度                         │ │
│  │  优点: 保持语义完整性                                      │ │
│  │  缺点: Chunk 大小不均匀                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  策略 3: 递归切分                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  先按大分隔符切分，再按小分隔符细分                        │ │
│  │  分隔符优先级: \n\n > \n > 。 > ， > 空格                  │ │
│  │                                                            │ │
│  │  [整个文档]                                                │ │
│  │  ├── [章节 1]                                              │ │
│  │  │   ├── [段落 1.1] (如果 < chunk_size)                   │ │
│  │  │   └── [段落 1.2] → 如果太大 → [句子 1.2a] [句子 1.2b] │ │
│  │  └── [章节 2]                                              │ │
│  │                                                            │ │
│  │  优点: 兼顾语义和大小                                      │ │
│  │  缺点: 实现复杂                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 Chunk 切分实现

```python
"""
chunk_optimizer.py
文档 Chunk 切分优化工具
"""

import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class Chunk:
    """文档片段"""
    content: str
    metadata: dict
    index: int
    token_count: int

class TextChunker:
    """文本切分器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64,
                 separators: Optional[list[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " "]

    def count_tokens(self, text: str) -> int:
        """估算 token 数（简化：中文 1 字 ≈ 2 token，英文 1 词 ≈ 1.3 token）"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 2 + english_words * 1.3)

    def split_text(self, text: str, metadata: dict = None) -> list[Chunk]:
        """递归切分文本"""
        if metadata is None:
            metadata = {}

        chunks = self._recursive_split(text, 0)
        result = []
        for i, chunk_text in enumerate(chunks):
            result.append(Chunk(
                content=chunk_text.strip(),
                metadata={**metadata, "chunk_index": i},
                index=i,
                token_count=self.count_tokens(chunk_text)
            ))
        return result

    def _recursive_split(self, text: str, depth: int) -> list[str]:
        """递归切分"""
        if self.count_tokens(text) <= self.chunk_size:
            return [text]

        for separator in self.separators:
            if separator in text:
                parts = text.split(separator)
                result = []
                current = ""

                for part in parts:
                    candidate = current + separator + part if current else part
                    if self.count_tokens(candidate) <= self.chunk_size:
                        current = candidate
                    else:
                        if current:
                            result.append(current)
                        current = part

                if current:
                    result.append(current)

                # 处理仍然过大的片段
                final = []
                for r in result:
                    if self.count_tokens(r) > self.chunk_size and depth < 3:
                        final.extend(self._recursive_split(r, depth + 1))
                    else:
                        final.append(r)

                # 添加重叠
                if self.chunk_overlap > 0 and len(final) > 1:
                    final = self._add_overlap(final)

                return final

        # 没有分隔符可用，按 token 数硬切
        return self._hard_split(text)

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """添加重叠"""
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = chunks[i - 1].split()
            overlap_tokens = prev_tokens[-self.chunk_overlap:]
            overlap_text = " ".join(overlap_tokens)
            result.append(overlap_text + " " + chunks[i])
        return result

    def _hard_split(self, text: str) -> list[str]:
        """硬切分"""
        words = text.split()
        result = []
        current = []
        current_count = 0

        for word in words:
            word_count = self.count_tokens(word)
            if current_count + word_count > self.chunk_size and current:
                result.append(" ".join(current))
                current = []
                current_count = 0
            current.append(word)
            current_count += word_count

        if current:
            result.append(" ".join(current))

        return result

class SemanticChunker:
    """语义切分器（基于段落和标题）"""

    def __init__(self, max_chunk_size: int = 1024):
        self.max_chunk_size = max_chunk_size

    def split_by_sections(self, text: str) -> list[dict]:
        """按章节切分"""
        sections = []
        current_section = {"title": "", "content": "", "level": 0}

        for line in text.split("\n"):
            # 检测标题
            if line.startswith("#"):
                if current_section["content"].strip():
                    sections.append(current_section)
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()
                current_section = {"title": title, "content": "", "level": level}
            else:
                current_section["content"] += line + "\n"

        if current_section["content"].strip():
            sections.append(current_section)

        return sections
```

### 6. RAG 检索流水线监控

#### 6.1 监控指标体系

```
┌──────────────────────────────────────────────────────────────────┐
│                    RAG 监控指标体系                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  检索质量指标                                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  检索精度 (Precision@K): 检索结果中相关文档的比例           │ │
│  │  检索召回 (Recall@K):    所有相关文档中被检索到的比例       │ │
│  │  MRR (Mean Reciprocal Rank): 第一个相关结果的排名倒数      │ │
│  │  NDCG (Normalized Discounted Cumulative Gain): 排序质量    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  性能指标                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Embedding 延迟 P50/P95/P99                               │ │
│  │  向量检索延迟 P50/P95/P99                                  │ │
│  │  端到端延迟 (含 LLM 生成)                                  │ │
│  │  向量检索 QPS                                               │ │
│  │  Embedding 服务 QPS                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  资源指标                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  向量数据库内存使用                                        │ │
│  │  向量数据库磁盘使用                                        │ │
│  │  Embedding 服务 GPU 使用                                    │ │
│  │  索引构建进度                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  业务指标                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  回答相关性 (Relevance Score)                               │ │
│  │  忠实度 (Faithfulness)                                      │ │
│  │  用户满意度                                                  │ │
│  │  无结果查询比例                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 6.2 RAG Pipeline 监控代码

```python
"""
rag_monitor.py
RAG 流水线监控
"""

import time
import logging
from dataclasses import dataclass, field
from prometheus_client import Histogram, Counter, Gauge

# Prometheus 指标定义
EMBEDDING_LATENCY = Histogram(
    'rag_embedding_latency_seconds',
    'Embedding 服务延迟',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

RETRIEVAL_LATENCY = Histogram(
    'rag_retrieval_latency_seconds',
    '向量检索延迟',
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

END_TO_END_LATENCY = Histogram(
    'rag_end_to_end_latency_seconds',
    '端到端延迟',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

RETRIEVAL_RESULTS = Histogram(
    'rag_retrieval_results_count',
    '检索结果数量',
    buckets=[0, 1, 3, 5, 10, 20]
)

QUERY_COUNTER = Counter(
    'rag_queries_total',
    '查询总数',
    ['status', 'has_results']
)

RETRIEVAL_CACHE_HITS = Counter(
    'rag_cache_hits_total',
    '缓存命中数'
)

@dataclass
class RAGMetrics:
    """单次 RAG 查询指标"""
    query: str
    embedding_latency_ms: float = 0
    retrieval_latency_ms: float = 0
    llm_latency_ms: float = 0
    total_latency_ms: float = 0
    num_results: int = 0
    relevance_scores: list[float] = field(default_factory=list)
    status: str = "success"

class RAGMonitor:
    """RAG 流水线监控"""

    def __init__(self):
        self.logger = logging.getLogger("rag_monitor")
        self.metrics_history: list[RAGMetrics] = []

    def track_query(self, query: str):
        """开始追踪一次查询"""
        return QueryTracker(self, query)

    def record_metrics(self, metrics: RAGMetrics):
        """记录指标"""
        self.metrics_history.append(metrics)

        # 更新 Prometheus 指标
        EMBEDDING_LATENCY.observe(metrics.embedding_latency_ms / 1000)
        RETRIEVAL_LATENCY.observe(metrics.retrieval_latency_ms / 1000)
        END_TO_END_LATENCY.observe(metrics.total_latency_ms / 1000)
        RETRIEVAL_RESULTS.observe(metrics.num_results)
        QUERY_COUNTER.labels(
            status=metrics.status,
            has_results="true" if metrics.num_results > 0 else "false"
        ).inc()

    def get_stats(self, window_minutes: int = 60) -> dict:
        """获取统计信息"""
        cutoff = time.time() - window_minutes * 60
        recent = [m for m in self.metrics_history if m.total_latency_ms > 0]

        if not recent:
            return {}

        latencies = [m.total_latency_ms for m in recent]
        retrieval_latencies = [m.retrieval_latency_ms for m in recent]

        return {
            "window_minutes": window_minutes,
            "total_queries": len(recent),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "p50_latency_ms": sorted(latencies)[len(latencies) // 2],
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "avg_retrieval_ms": sum(retrieval_latencies) / len(retrieval_latencies),
            "avg_results": sum(m.num_results for m in recent) / len(recent),
            "success_rate": sum(1 for m in recent if m.status == "success") / len(recent),
        }

class QueryTracker:
    """查询追踪上下文管理器"""

    def __init__(self, monitor: RAGMonitor, query: str):
        self.monitor = monitor
        self.metrics = RAGMetrics(query=query)
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics.total_latency_ms = (time.time() - self.start_time) * 1000
        if exc_type:
            self.metrics.status = "error"
        self.monitor.record_metrics(self.metrics)

    def record_embedding(self, latency_ms: float):
        self.metrics.embedding_latency_ms = latency_ms

    def record_retrieval(self, latency_ms: float, num_results: int):
        self.metrics.retrieval_latency_ms = latency_ms
        self.metrics.num_results = num_results

    def record_llm(self, latency_ms: float):
        self.metrics.llm_latency_ms = latency_ms
```

### 7. RAG 评估指标

#### 7.1 评估体系

```python
"""
rag_evaluator.py
RAG 系统评估工具
"""

import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class EvalResult:
    """评估结果"""
    query: str
    retrieved_docs: list[str]
    generated_answer: str
    ground_truth: Optional[str]

    # 检索质量
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0

    # 生成质量
    answer_relevance: float = 0.0
    faithfulness: float = 0.0

class RAGEvaluator:
    """RAG 系统评估器"""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def evaluate_retrieval(self, query: str, retrieved_docs: list[str],
                           ground_truth_docs: list[str], k: int = 5) -> dict:
        """评估检索质量"""
        retrieved_set = set(retrieved_docs[:k])
        truth_set = set(ground_truth_docs)

        # Precision@K
        relevant_retrieved = retrieved_set & truth_set
        precision = len(relevant_retrieved) / len(retrieved_set) if retrieved_set else 0

        # Recall@K
        recall = len(relevant_retrieved) / len(truth_set) if truth_set else 0

        # MRR
        mrr = 0
        for i, doc in enumerate(retrieved_docs[:k]):
            if doc in truth_set:
                mrr = 1 / (i + 1)
                break

        return {
            f"precision@{k}": round(precision, 4),
            f"recall@{k}": round(recall, 4),
            "mrr": round(mrr, 4),
        }

    def evaluate_faithfulness(self, answer: str, context_docs: list[str]) -> float:
        """评估忠实度：回答是否基于检索到的上下文"""
        if not self.llm:
            return 0.0

        prompt = f"""请评估以下回答是否忠实于提供的上下文。
只基于上下文中的信息来判断，不要使用外部知识。

上下文:
{chr(10).join(context_docs)}

回答:
{answer}

评分标准:
- 1.0: 完全基于上下文，没有添加额外信息
- 0.5: 部分基于上下文，有一些推断
- 0.0: 完全不基于上下文或与上下文矛盾

请只返回一个 0 到 1 之间的数字。"""

        try:
            response = self.llm.generate(prompt)
            score = float(response.strip())
            return max(0, min(1, score))
        except:
            return 0.0

    def evaluate_relevance(self, query: str, answer: str) -> float:
        """评估回答与查询的相关性"""
        if not self.llm:
            return 0.0

        prompt = f"""请评估以下回答与问题的相关性。

问题: {query}

回答: {answer}

评分标准:
- 1.0: 完全回答了问题
- 0.5: 部分回答了问题
- 0.0: 与问题无关

请只返回一个 0 到 1 之间的数字。"""

        try:
            response = self.llm.generate(prompt)
            score = float(response.strip())
            return max(0, min(1, score))
        except:
            return 0.0

    def batch_evaluate(self, eval_data: list[dict]) -> dict:
        """批量评估"""
        results = []
        for item in eval_data:
            result = self.evaluate_retrieval(
                query=item["query"],
                retrieved_docs=item["retrieved"],
                ground_truth_docs=item["ground_truth"]
            )
            results.append(result)

        # 汇总
        avg_metrics = {}
        for key in results[0]:
            values = [r[key] for r in results]
            avg_metrics[f"avg_{key}"] = round(sum(values) / len(values), 4)

        return {
            "num_samples": len(results),
            "metrics": avg_metrics,
            "details": results,
        }
```

### 8. SRE 场景：向量检索延迟优化

```
┌──────────────────────────────────────────────────────────────────┐
│     SRE 场景：向量检索延迟 2s → 50ms 优化过程                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  问题现象:                                                        │
│  ├── 用户反馈 RAG 回答延迟过高（端到端 5~8 秒）                  │
│  ├── 监控显示向量检索延迟 P95 = 2000ms                           │
│  └── Embedding 服务延迟正常（P95 = 30ms）                        │
│                                                                  │
│  排查过程:                                                        │
│                                                                  │
│  Step 1: 检查索引配置                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  当前配置: HNSW M=32, efConstruction=400, ef=256           │ │
│  │  问题: 参数过大，查询精度换来的延迟过高                     │ │
│  │  数据量: 500 万条向量                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Step 2: 检查资源使用                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Milvus QueryNode 内存使用: 90%                            │ │
│  │  查询并发: 200 QPS                                         │ │
│  │  问题: 内存接近上限，频繁 swap                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  优化措施:                                                        │
│                                                                  │
│  1. 调整 HNSW 参数                                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  M: 32 → 16 (减少连接数)                                  │ │
│  │  efConstruction: 400 → 200 (降低索引构建精度)              │ │
│  │  ef: 256 → 128 (降低查询精度)                              │ │
│  │  预期: 延迟降低 50%，召回率下降 ~2%                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  2. 扩容 QueryNode                                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  replicas: 3 → 6                                           │ │
│  │  内存: 8Gi → 16Gi                                          │ │
│  │  预期: 并发能力翻倍，消除内存压力                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  3. 添加缓存层                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Redis 缓存热门查询结果                                    │ │
│  │  缓存策略: 查询向量相似度 > 0.98 视为命中                  │ │
│  │  TTL: 5 分钟                                               │ │
│  │  预期: 缓存命中率 30%，平均延迟再降 30%                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  优化结果:                                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  检索延迟 P95:  2000ms → 50ms (降低 97.5%)                │ │
│  │  端到端延迟:    5000ms → 800ms (降低 84%)                  │ │
│  │  检索召回率:    95% → 93% (下降 2%，可接受)                │ │
│  │  查询 QPS:      200 → 800 (提升 4 倍)                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 实战练习

### 练习 1: 部署 Milvus 并创建向量 Collection

**目标**: 在 K8s 集群部署 Milvus，创建 Collection 并进行基本的增删改查操作。

```bash
# 1. 添加 Helm 仓库
helm repo add milvus https://milvus-io.github.io/milvus-helm
helm repo update

# 2. 部署 Milvus 单机版（学习环境）
helm install milvus milvus/milvus \
  --namespace vector-db --create-namespace \
  --set cluster.enabled=false \
  --set etcd.replicaCount=1 \
  --set minio.mode=standalone \
  --set pulsar.enabled=false

# 3. 等待就绪
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=milvus \
  -n vector-db --timeout=300s

# 4. 安装 Python SDK
pip install pymilvus

# 5. 创建 Collection 并插入数据
python3 -c "
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

connections.connect(host='localhost', port=19530)

fields = [
    FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=128),
]
schema = CollectionSchema(fields)
collection = Collection('test_collection', schema)

# 创建 HNSW 索引
index_params = {'metric_type': 'COSINE', 'index_type': 'HNSW', 'params': {'M': 16, 'efConstruction': 200}}
collection.create_index('embedding', index_params)

# 插入测试数据
import random
data = [
    ['test document ' + str(i) for i in range(100)],
    [[random.random() for _ in range(128)] for _ in range(100)],
]
collection.insert(data)
print(f'Inserted {collection.num_entities} entities')

# 搜索
collection.load()
results = collection.search(
    data=[[random.random() for _ in range(128)]],
    anns_field='embedding',
    param={'metric_type': 'COSINE', 'params': {'ef': 128}},
    limit=5
)
print(f'Found {len(results[0])} results')
"
```

### 练习 2: 搭建完整 RAG Pipeline

**目标**: 实现文档摄取 → Chunk 切分 → Embedding → 向量存储 → 检索的完整流水线。

```python
# rag_pipeline_demo.py
import asyncio
from chunk_optimizer import TextChunker
from embedding_client import EmbeddingClient, EmbeddingPipeline

async def main():
    # 1. 初始化组件
    chunker = TextChunker(chunk_size=512, chunk_overlap=64)
    embedding = EmbeddingClient(endpoint="http://tei-bge-large:8080")

    # 2. 准备测试文档
    documents = [
        {
            "content": """向量数据库是专门用于存储和检索高维向量的数据库系统。
            与传统关系型数据库不同，向量数据库使用近似最近邻（ANN）算法来高效地
            在海量向量中找到与查询向量最相似的结果。常见的向量数据库包括 Milvus、
            Pinecone、Weaviate、Qdrant 等。向量数据库在 RAG（检索增强生成）系统中
            扮演着核心角色，负责存储文档的向量表示并在查询时快速检索相关文档。""",
            "metadata": {"source": "vector_db_intro.md", "page": 1}
        },
        {
            "content": """HNSW（Hierarchical Navigable Small World）是一种基于图的
            近似最近邻搜索算法。它构建一个多层图结构，顶层包含少量节点，底层包含
            所有节点。搜索时从顶层开始，逐层向下导航，最终在底层找到最近邻。
            HNSW 的关键参数包括 M（每层最大连接数）、efConstruction（构建时的
            搜索范围）和 ef（查询时的搜索范围）。M 越大、ef 越高，精度越高但
            速度越慢。""",
            "metadata": {"source": "hnsw_explained.md", "page": 1}
        }
    ]

    # 3. Chunk 切分
    all_chunks = []
    for doc in documents:
        chunks = chunker.split_text(doc["content"], doc["metadata"])
        all_chunks.extend(chunks)
        print(f"Document '{doc['metadata']['source']}': {len(chunks)} chunks")

    # 4. 模拟向量化和存储（实际需要 Embedding 服务）
    print(f"\nTotal chunks: {len(all_chunks)}")
    for chunk in all_chunks:
        print(f"  Chunk {chunk.index}: {chunk.token_count} tokens - {chunk.content[:50]}...")

    # 5. 模拟检索
    query = "什么是 HNSW 索引？"
    print(f"\nQuery: {query}")
    # 在实际系统中，这里会调用 embedding 和 vector search

if __name__ == "__main__":
    asyncio.run(main())
```

### 练习 3: RAG 检索延迟优化

**目标**: 通过索引参数调优和缓存策略，将检索延迟从 >100ms 降低到 <50ms。

```python
# retrieval_optimization.py
import time
import random
from pymilvus import Collection, connections

def benchmark_retrieval(collection_name: str, dim: int = 1536):
    """检索性能基准测试"""
    connections.connect(host="localhost", port=19530)
    collection = Collection(collection_name)
    collection.load()

    # 不同 ef 值的测试
    ef_values = [32, 64, 128, 256, 512]
    results = []

    for ef in ef_values:
        query_vectors = [[random.random() for _ in range(dim)] for _ in range(100)]
        search_params = {"metric_type": "COSINE", "params": {"ef": ef}}

        start = time.time()
        for qv in query_vectors:
            collection.search(
                data=[qv],
                anns_field="embedding",
                param=search_params,
                limit=10
            )
        elapsed = time.time() - start

        results.append({
            "ef": ef,
            "avg_latency_ms": round(elapsed / 100 * 1000, 2),
            "qps": round(100 / elapsed, 1),
        })
        print(f"ef={ef}: avg={results[-1]['avg_latency_ms']}ms, QPS={results[-1]['qps']}")

    return results

# 执行测试
if __name__ == "__main__":
    benchmark_retrieval("my_documents")
```

---

## 面试题精选

### 1. 什么是 RAG？为什么需要 RAG？

**参考答案**：

RAG（Retrieval-Augmented Generation，检索增强生成）是一种将外部知识检索与 LLM 生成相结合的架构。

需要 RAG 的原因：
1. **知识时效性**：LLM 训练数据有截止日期，RAG 可以引入最新信息
2. **领域专业性**：LLM 通用知识有限，RAG 可以注入领域文档
3. **减少幻觉**：基于检索到的真实文档生成回答，降低虚构概率
4. **可追溯性**：回答有源文档可查，便于验证

### 2. HNSW 和 IVF 索引有什么区别？如何选择？

**参考答案**：

| 对比项 | HNSW | IVF |
|--------|------|-----|
| 原理 | 多层图结构 | 聚类 + 倒排索引 |
| 查询速度 | 快（<10ms） | 中等（10~50ms） |
| 内存占用 | 高（全量在内存） | 中（可配合 PQ 量化） |
| 构建速度 | 慢 | 快 |
| 适合数据量 | 百万~千万 | 千万~亿 |
| 更新支持 | 差（需重建） | 好（增量） |

选择建议：
- 百万级数据、延迟敏感 → HNSW
- 亿级数据、内存受限 → IVF+PQ
- 超大规模 → DiskANN

### 3. Chunk 切分的 overlap 有什么作用？应该设多大？

**参考答案**：

overlap 的作用：
- 防止切分边界处的语义丢失
- 确保跨 Chunk 的上下文被检索到
- 提高检索召回率

推荐设置：
- 通常为 chunk_size 的 10%~20%
- chunk_size=512 时，overlap=64~128
- 中文文档可适当增大（中文 token 密度高）

### 4. 如何监控 RAG 系统的检索质量？

**参考答案**：

1. **离线评估**：构建标注数据集，计算 Precision@K、Recall@K、MRR
2. **在线评估**：
   - 监控无结果查询比例
   - 用户反馈（点赞/点踩）
   - LLM 自动评估（Faithfulness、Relevance）
3. **性能监控**：Embedding 延迟、检索延迟、端到端延迟
4. **A/B 测试**：对比不同索引参数/Chunk 策略的效果

### 5. 向量检索延迟过高如何排查和优化？

**参考答案**：

排查步骤：
1. 确认是 Embedding 延迟还是检索延迟
2. 检查向量数据库资源（内存/CPU/磁盘 IO）
3. 检查索引参数配置
4. 检查并发量和数据规模

优化方案：
1. 降低 HNSW ef 参数（牺牲少量精度）
2. 扩容 QueryNode 增加并发能力
3. 添加查询缓存（Redis）
4. 使用 IVF 量化减少内存占用
5. 分片（Sharding）分散查询压力

### 6. pgvector 和 Milvus 如何选择？

**参考答案**：

| 场景 | 推荐 | 原因 |
|------|------|------|
| 已有 PostgreSQL | pgvector | 无需额外组件 |
| 数据量 < 1000 万 | pgvector | 够用且运维简单 |
| 数据量 > 1 亿 | Milvus | 分布式架构，可扩展 |
| 需要混合搜索 | 两者皆可 | 都支持 |
| 团队运维能力有限 | pgvector | 运维成本低 |

### 7. 如何评估 RAG 系统的 Faithfulness（忠实度）？

**参考答案**：

Faithfulness 评估回答是否忠实于检索到的上下文：

1. **基于 LLM 的评估**：将上下文和回答发给 LLM，判断回答中每个声明是否可以从上下文中推导
2. **声明级评估**：
   - 将回答拆分为独立声明
   - 对每个声明检查是否有上下文支持
   - Faithfulness = 有支持的声明数 / 总声明数
3. **工具**：RAGAS、TruLens 等 RAG 评估框架

### 8. 如何实现 RAG 系统的多租户隔离？

**参考答案**：

1. **Collection 级隔离**：每个租户一个 Collection，完全隔离
2. **Partition 级隔离**：同一 Collection 不同 Partition，按租户 ID 分区
3. **字段级隔离**：在 metadata 中添加 tenant_id，查询时附加过滤条件
4. **行级安全**（pgvector）：使用 PostgreSQL RLS 策略

推荐：Partition 级隔离（平衡隔离性和资源利用率）

---

## 延伸阅读

- [Milvus Documentation](https://milvus.io/docs) - Milvus 官方文档
- [pgvector GitHub](https://github.com/pgvector/pgvector) - pgvector 扩展
- [Weaviate Documentation](https://weaviate.io/developers/weaviate) - Weaviate 文档
- [HNSW Paper](https://arxiv.org/abs/1603.09320) - HNSW 算法论文
- [RAGAS Framework](https://docs.ragas.io/) - RAG 评估框架
- [Text Embeddings Inference](https://huggingface.co/docs/text-embeddings-inference) - HuggingFace Embedding 服务
- [LangChain RAG](https://python.langchain.com/docs/tutorials/rag/) - LangChain RAG 教程

---

## 今日自检清单

- [ ] 理解 RAG 流水线的完整架构（文档摄取 → Chunk → Embedding → 索引 → 检索 → 生成）
- [ ] 能部署 Milvus/pgvector 并创建向量 Collection
- [ ] 理解 HNSW 和 IVF 索引的原理和区别
- [ ] 能进行 HNSW 索引参数调优（M、efConstruction、ef）
- [ ] 掌握 Chunk 切分策略（固定长度、语义切分、递归切分）
- [ ] 能部署 Embedding 服务（TEI）并实现批量/实时向量化
- [ ] 理解 RAG 评估指标（Precision、Recall、Faithfulness、Relevance）
- [ ] 能监控 RAG 检索流水线的延迟和质量
- [ ] 能排查和优化向量检索延迟问题
- [ ] 完成了所有 3 个实战练习

---

*由 SRE 学习计划生成 | 2026-05-03*
