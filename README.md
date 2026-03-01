# etcd3aio

Async Python client for etcd v3 using `grpc.aio`.

[![CI](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml/badge.svg)](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/etcd3aio)](https://pypi.org/project/etcd3aio/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

- Thin facade over the etcd v3 gRPC API — no hidden magic
- Async-first: all I/O via `grpc.aio`, never blocks the event loop
- Strong typing: fully annotated, `py.typed` marker, satisfies `pyright`
- Automatic retry with exponential backoff for transient errors
- Watch streams with automatic reconnection
- Distributed lock and leader election primitives
- Background lease keep-alive and token refresh context managers

## Requirements

- Python 3.13+
- etcd v3.5+

## Installation

```bash
pip install etcd3aio
```

## Quick Start

```python
import asyncio
from etcd3aio import Etcd3Client

async def main() -> None:
    async with Etcd3Client(['localhost:2379']) as client:
        await client.ping()

        # Key-value
        await client.kv.put('myapp/greeting', 'hello')
        resp = await client.kv.get('myapp/greeting')
        print(resp.kvs[0].value.decode())  # hello

        # Distributed lock
        async with client.lock('myapp/resource'):
            print('acquired exclusive section')

        # Leader election
        async with client.election('myapp/leader', value=b'node-1') as e:
            leader = await e.leader()
            print(f'leader: {leader.kvs[0].value.decode()}')

asyncio.run(main())
```

## Local cluster (Docker)

```bash
docker compose -f docker/docker-compose.yaml up -d
```

This starts a 3-node etcd cluster on ports 2379, 3379, and 4379.

## Examples

The [`examples/`](examples/) directory contains standalone scripts for every module:

| Script | Covers |
|---|---|
| `get_started_example.py` | most common use cases |
| `kv_example.py` | put, get, delete, prefix scan, sort, compact |
| `lease_example.py` | grant, revoke, keep-alive, TTL |
| `watch_example.py` | basic watch, filters, prefix range |
| `txn_example.py` | compare-and-swap, atomic ops |
| `concurrency_example.py` | distributed lock, leader election |
| `auth_example.py` | auth status, token management |
| `maintenance_example.py` | cluster status, alarms |
| `full_example.py` | integrated end-to-end demo |

## Documentation

- [CONTRACT.md](CONTRACT.md) — non-negotiable project contract
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and responsibilities
- [CONTRIBUTING.md](CONTRIBUTING.md) — local workflow and quality checks
- [CHANGELOG.md](CHANGELOG.md) — version history
- [ROADMAP.md](ROADMAP.md) — implemented and deferred features
