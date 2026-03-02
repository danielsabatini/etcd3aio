# etcd3aio

Async Python client for etcd v3 using `grpc.aio`.

[![CI](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml/badge.svg)](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml)
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
- etcd v3.5+ (see [Local cluster](#local-cluster-docker) to run one locally)

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

## Modules

### KVService — `client.kv`

Key-value operations: put, get, delete, compact, and atomic transactions.

```python
# Prefix scan with sorting
from etcd3aio.kv import SortOrder, SortTarget, prefix_range_end

resp = await client.kv.get(
    'myapp/',
    range_end=prefix_range_end('myapp/'),
    sort_order=SortOrder.DESCEND,
    sort_target=SortTarget.KEY,
)

# Compare-and-swap (atomic transaction)
resp = await client.kv.txn(
    compare=[client.kv.txn_compare_value('myapp/flag', 'off')],
    success=[client.kv.txn_op_put('myapp/flag', 'on')],
    failure=[client.kv.txn_op_get('myapp/flag')],
)
```

### LeaseService — `client.lease`

Lease lifecycle management with optional background keep-alive.

```python
# Grant a lease and attach a key to it
lease = await client.lease.grant(ttl=30)
await client.kv.put('myapp/lock', 'held', lease=lease.ID)

# Automatic renewal in the background
async with client.lease.keep_alive_context(lease.ID, ttl=30):
    await do_long_work()  # lease is renewed automatically

# Revoke when done
await client.lease.revoke(lease.ID)
```

### WatchService — `client.watch`

Async iterator over etcd events with automatic reconnection and server-side filtering.

```python
from etcd3aio.watch import WatchFilter
from etcd3aio.kv import prefix_range_end

# Watch a single key
async for response in client.watch.watch('myapp/flag'):
    for event in response.events:
        print(event.type, event.kv.value.decode())

# Watch a prefix, suppress DELETE events
async for response in client.watch.watch(
    'myapp/',
    range_end=prefix_range_end('myapp/'),
    filters=(WatchFilter.NODELETE,),
):
    ...
```

### Lock — `client.lock()`

Distributed mutex built on KV + Lease. Guarantees mutual exclusion across processes.

```python
async with client.lock('myapp/resource', ttl=10):
    # Only one holder at a time across the entire cluster
    await do_exclusive_work()
```

### Election — `client.election()`

Leader election built on KV + Lease. Supports campaign, resign, observe, proclaim, and leader query.

```python
async with client.election('myapp/leader', value=b'node-1', ttl=10) as e:
    # This node is the leader
    leader = await e.leader()
    print(leader.kvs[0].value.decode())   # b'node-1'
    await e.proclaim(b'node-1-updated')   # update published value

# Stream leadership changes (useful for followers)
async for response in client.election('myapp/leader').observe():
    print('new leader event', response.events)
```

### AuthService — `client.auth`

Full authentication and RBAC management: auth enable/disable, user and role lifecycle, token refresh.

```python
# Check if auth is enabled
status = await client.auth.auth_status()

# Authenticate and set token manually
resp = await client.auth.authenticate('user', 'password')
client.set_token(resp.token)

# Or use the background refresher (re-authenticates before expiry)
async with client.token_refresher('user', 'password'):
    await client.kv.put('secure/key', 'value')

# Enable / disable auth (requires root credentials)
await client.auth.auth_enable()
await client.auth.auth_disable()

# User and role management (RBAC)
from etcd3aio import PermissionType
from etcd3aio.kv import prefix_range_end

await client.auth.role_add('viewer')
await client.auth.role_grant_permission(
    'viewer', '/app/', prefix_range_end('/app/'), perm_type=PermissionType.READ
)
await client.auth.user_add('alice', 'secret')
await client.auth.user_grant_role('alice', 'viewer')
```

### MaintenanceService — `client.maintenance`

Cluster health, alarm management, storage defragmentation, consistency hashing, and snapshot streaming.

```python
from etcd3aio.maintenance import AlarmType

status = await client.maintenance.status()
print(f'leader={status.leader}, version={status.version}')

alarms = await client.maintenance.alarms()
await client.maintenance.alarm_deactivate(AlarmType.NOSPACE)

# Reclaim storage freed by compaction
await client.maintenance.defragment()

# Consistency check between members
hkv = await client.maintenance.hash_kv()
print(f'hash={hkv.hash:#010x}, revision={hkv.hash_revision}')

# Stream a full binary backup
chunks: list[bytes] = []
async for chunk in client.maintenance.snapshot():
    chunks.append(chunk)
data = b''.join(chunks)
```

### Multi-endpoint & TLS

Pass multiple endpoints for automatic round-robin load balancing. For TLS, supply the certificate bytes directly to the client constructor:

```python
from pathlib import Path

async with Etcd3Client(
    ['etcd-node1:2379', 'etcd-node2:2379', 'etcd-node3:2379'],
    ca_cert=Path('ca.crt').read_bytes(),
    cert_key=Path('client.key').read_bytes(),    # mutual TLS (optional)
    cert_chain=Path('client.crt').read_bytes(),  # mutual TLS (optional)
) as client:
    await client.ping()
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
| `client_example.py` | client lifecycle, manual connect/close, `ping()` |
| `connections_example.py` | `ConnectionManager`, endpoint health check, cluster smoke test |
| `kv_example.py` | put, get, delete, prefix scan, sort, compact |
| `lease_example.py` | grant, revoke, keep-alive, TTL |
| `watch_example.py` | basic watch, filters, prefix range |
| `txn_example.py` | compare-and-swap, atomic ops |
| `concurrency_example.py` | distributed lock, leader election |
| `auth_example.py` | auth status, token management, user/role management |
| `maintenance_example.py` | cluster status, alarms, defragment, hash_kv, snapshot |
| `full_example.py` | integrated end-to-end demo |

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) — local workflow, design principles and quality checks
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and responsibilities
- [CHANGELOG.md](CHANGELOG.md) — version history
- [ROADMAP.md](ROADMAP.md) — implemented and deferred features
