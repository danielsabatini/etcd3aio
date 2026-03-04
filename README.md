# etcd3aio

Async Python client for etcd v3 using `grpc.aio`.

[![CI](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml/badge.svg)](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/danielsabatini/etcd3aio/graph/badge.svg)](https://codecov.io/gh/danielsabatini/etcd3aio)
[![PyPI](https://img.shields.io/pypi/v/etcd3aio)](https://pypi.org/project/etcd3aio/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
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

- Python 3.11+
- etcd v3.5+ tested against v3.6 (see [Local cluster](#local-cluster-docker) to run one locally)

## Installation

```bash
pip install etcd3aio
```

## Quick Start

```python
import asyncio
from etcd3aio import Etcd3Client, EtcdConnectionError

async def main() -> None:
    try:
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
    except EtcdConnectionError:
        print('could not connect to etcd')
        raise SystemExit(1)

asyncio.run(main())
```

## Error Handling

All etcd errors inherit from `EtcdError`. The table below maps each exception to the
underlying gRPC status code and the typical recovery action.

```python
from etcd3aio import (
    EtcdError,
    EtcdConnectionError,
    EtcdTransientError,
    EtcdUnauthenticatedError,
    EtcdPermissionDeniedError,
)

try:
    await client.kv.put('key', 'value')
except EtcdConnectionError:
    # UNAVAILABLE — endpoint unreachable after all retry attempts
    # Action: check cluster health, verify endpoints
    ...
except EtcdTransientError:
    # DEADLINE_EXCEEDED — operation timed out after all retry attempts
    # Action: retry with backoff or increase the deadline
    ...
except EtcdUnauthenticatedError:
    # UNAUTHENTICATED — token missing, expired, or invalid
    # Action: re-authenticate and set a new token
    ...
except EtcdPermissionDeniedError:
    # PERMISSION_DENIED — authenticated user lacks the required role/permission
    # Action: review RBAC grants for this user
    ...
except EtcdError:
    # Catch-all for any other etcd-related error
    ...
```

Transient errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`) are retried automatically with
exponential backoff (up to 3 attempts, 0.05 s → 1.0 s). Exceptions are only raised
after all retry attempts are exhausted.

## Local cluster (Docker)

```bash
docker compose -f docker/compose.yaml up -d
```

This starts a 3-node etcd cluster on ports 2379, 3379, and 4379.

## Documentation

- [MODULES.md](MODULES.md) — service API reference with code examples
- [EXAMPLES.md](EXAMPLES.md) — step-by-step walkthrough of all example scripts
- [CONTRIBUTING.md](CONTRIBUTING.md) — local workflow, design principles and quality checks
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and responsibilities
- [CHANGELOG.md](CHANGELOG.md) — version history
- [ROADMAP.md](ROADMAP.md) — implemented and deferred features
