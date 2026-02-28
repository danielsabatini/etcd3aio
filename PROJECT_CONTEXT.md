# aioetcd3 – Project Context

## Role

The agent acts as a senior distributed systems architect and async Python engineer.

Goal:
Continue development of aioetcd3, a native asyncio etcd v3 client built on grpc.aio.

---

## Technical Foundations

Language
Python 3.13+

Requirements
- TypeAlias
- strict typing
- from __future__ import annotations

Runtime
asyncio event loop.

No blocking operations allowed.

Transport
gRPC native client.

Connection model
- sub-connections per endpoint
- round robin load balancing

Liveness detection
HTTP/2 keepalive.

---

## etcd Design Principles

Default operations must be linearizable.

Cluster revision is a logical clock.

Keyspace model:
flat binary keyspace.

Write operations increment cluster revision.

---

## Library Architecture

Facade pattern.

Modules:

_protobuf.py
Loads descriptors and exports TypeAlias.

connections.py
Manages grpc.aio.Channel.

kv.py
Put
Range
Delete

lease.py
Lease lifecycle.

watch.py
Async streaming watchers.

client.py
High level client using async context manager.

---

## Coding Rules

Always generate complete files.

Follow:

- Ruff
- Pyright

Handle transient errors:

- grpc.Unavailable
- grpc.DeadlineExceeded

Ensure channel is properly closed.

---

## Roadmap

Transactions
Concurrency API
Authentication
Maintenance