# etcd3aio

Async Python client for etcd v3 using `grpc.aio`.

[![CI](https://github.com/danielsabatini/etcd3aio/actions/workflows/ci.yml/badge.svg)](https://github.com/danielsabatini/etcd3aio/actions/workflows/ci.yml)
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

This starts two independent clusters:

| Cluster | Ports | Transport |
|---|---|---|
| `etcd1 / etcd2 / etcd3` | 2379, 3379, 4379 | Plain TCP (no TLS) |
| `etcdtls1 / etcdtls2 / etcdtls3` | 5379, 6379, 7379 | Mutual TLS (mTLS) |

### Generating TLS certificates

The mTLS cluster requires certificate files in `docker/`. To regenerate them:

```bash
bash docker/gen-certs.sh
```

This creates `server-ca.crt`, `client-cert.crt`, `client-key.key`, and peer certificate pairs — all with the correct Subject Alternative Names for the TLS cluster nodes.

### Connecting to the TLS cluster

Three certificate files are required — obtain them from your etcd administrator or generate them with `gen-certs.sh` for local development:

| File | Purpose | `Etcd3Client` parameter |
|---|---|---|
| `server-ca.crt` | CA that signed the server certificate | `ca_cert` |
| `client-cert.crt` | Client certificate presented during the mTLS handshake | `cert_chain` |
| `client-key.key` | Private key for the client certificate | `cert_key` |

Pass the file contents as `bytes` directly to the client constructor:

```python
from pathlib import Path
from etcd3aio import Etcd3Client

certs = Path('docker')  # adjust to your certificate directory

async with Etcd3Client(
    ['localhost:5379', 'localhost:6379', 'localhost:7379'],
    ca_cert=    (certs / 'server-ca.crt').read_bytes(),
    cert_chain= (certs / 'client-cert.crt').read_bytes(),
    cert_key=   (certs / 'client-key.key').read_bytes(),
    tls_server_name='localhost',  # required for multi-endpoint TLS — see MODULES.md
) as client:
    await client.ping()
```

> **`tls_server_name`** is required when connecting to multiple endpoints. The gRPC `ipv4:` round-robin scheme encodes all addresses as a comma-separated string and cannot derive a hostname for TLS verification. Set it to a DNS name present in the server certificate's Subject Alternative Names (SANs).

## Documentation

- [MODULES.md](MODULES.md) — service API reference with code examples
- [EXAMPLES.md](EXAMPLES.md) — step-by-step walkthrough of all example scripts
- [CONTRIBUTING.md](CONTRIBUTING.md) — local workflow, design principles and quality checks
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and responsibilities
- [CHANGELOG.md](CHANGELOG.md) — version history
- [ROADMAP.md](ROADMAP.md) — implemented and deferred features
