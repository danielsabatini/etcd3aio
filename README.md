# etcd3aio

Async Python client for etcd v3 using `grpc.aio`.

[![CI](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml/badge.svg)](https://github.com/dsfreitas/etcd3aio/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dsfreitas/etcd3aio/branch/main/graph/badge.svg)](https://codecov.io/gh/dsfreitas/etcd3aio)
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

### ClusterService — `client.cluster`

Cluster membership management: list, add, remove, update, and promote members.

```python
# List all cluster members
resp = await client.cluster.member_list()
for m in resp.members:
    print(f'id={m.ID}  name={m.name}  learner={m.isLearner}  urls={list(m.peerURLs)}')

# Add a learner member (non-voting), then promote to voting
add_resp = await client.cluster.member_add(['http://10.0.0.4:2380'], is_learner=True)
new_id = add_resp.member.ID
await client.cluster.member_promote(new_id)

# Remove a member
await client.cluster.member_remove(new_id)
```

### MaintenanceService — `client.maintenance`

Cluster health, alarm management, storage defragmentation, consistency hashing, and snapshot streaming.

```python
from etcd3aio import DowngradeAction
from etcd3aio.maintenance import AlarmType

status = await client.maintenance.status()
print(f'leader={status.leader}, version={status.version}')

alarms = await client.maintenance.alarms()
await client.maintenance.alarm_deactivate(AlarmType.NOSPACE)

# Reclaim storage freed by compaction
await client.maintenance.defragment()

# Full-store hash for cross-member consistency verification
h = await client.maintenance.hash()
print(f'hash={h.hash:#010x}')

# MVCC consistency check between members
hkv = await client.maintenance.hash_kv()
print(f'hash={hkv.hash:#010x}, revision={hkv.hash_revision}')

# Validate downgrade eligibility (read-only, does not change cluster state)
await client.maintenance.downgrade(DowngradeAction.VALIDATE, '3.5.0')

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
docker compose -f docker/compose.yaml up -d
```

This starts a 3-node etcd cluster on ports 2379, 3379, and 4379.

## Examples

The [`examples/`](examples/) directory contains standalone scripts for every module. All examples require a running etcd cluster — see [Local cluster](#local-cluster-docker).

| Script | Covers |
|---|---|
| `get_started_example.py` | most common use cases |
| `client_example.py` | client lifecycle, manual connect/close, `ping()` |
| `connections_example.py` | `ConnectionManager`, endpoint health check, cluster smoke test |
| `kv_example.py` | put, get, delete, prefix scan, sort, compact |
| `lease_example.py` | grant, revoke, keep-alive, TTL, watch-on-expire |
| `watch_example.py` | basic watch, server-side filters, prefix range |
| `txn_example.py` | compare-and-swap, atomic ops |
| `concurrency_example.py` | distributed lock, leader election |
| `auth_example.py` | auth status, token management, user/role RBAC |
| `cluster_example.py` | member list, add learner, promote, remove |
| `maintenance_example.py` | cluster status, alarms, defragment, hash, hash_kv, downgrade, snapshot |
| `full_example.py` | integrated end-to-end smoke test |

### Step-by-step walkthrough

---

#### 1. `get_started_example.py`

**What it does:** entry point covering the most common use cases — ping, put/get/delete, prefix scan, distributed lock, and leader election.

```bash
uv run python examples/get_started_example.py
```

**Expected output:**
```
ping -> cluster is reachable
get -> hello-etcd
after delete -> exists=False
prefix scan -> 3 keys found
lock -> acquired exclusive section
lock -> released
election -> this node is the leader
election -> resigned
```

**What to observe:**
- `ping` verifies the cluster accepts both reads and writes before doing anything else
- `after delete -> exists=False` confirms the key was fully removed
- `prefix scan -> 3 keys found` exercises a range query using `prefix_range_end()`
- `lock` and `election` confirm that distributed concurrency primitives are functional end-to-end

---

#### 2. `client_example.py`

**What it does:** demonstrates manual client lifecycle management — `connect()` and `close()` called explicitly instead of using `async with`, plus `ping()` with and without write verification.

```bash
uv run python examples/client_example.py
```

**Expected output:**
```
Client connected and services initialized: kv, lease, watch, auth, maintenance
Client ping -> cluster is reachable and accepting writes
Client ping(write_check=False) -> cluster is readable
Client closed
```

**What to observe:**
- The client is created and connected without `async with` — useful when lifecycle is managed by a framework or DI container
- `ping()` performs a put + get + delete to verify full read/write availability
- `ping(write_check=False)` skips the write step — lighter check for read-only health probes
- `Client closed` confirms the `finally: await client.close()` block executed even if an exception occurred

---

#### 3. `connections_example.py`

**What it does:** checks each endpoint individually for reachability, then runs a KV smoke test using the full endpoint list. Demonstrates direct use of `ConnectionManager`.

**Variant A — three-node cluster (default):**
```bash
uv run python examples/connections_example.py
```

```
Checking endpoints:
  - localhost:2379: ok
  - localhost:3379: ok
  - localhost:4379: ok
Cluster KV smoke test passed.
```

**Variant B — single endpoint:**
```bash
uv run python examples/connections_example.py --endpoints localhost:2379
```

```
Checking endpoints:
  - localhost:2379: ok
Cluster KV smoke test passed.
```

**Variant C — unreachable endpoint (failure path):**
```bash
uv run python examples/connections_example.py --endpoints localhost:9999 --timeout 2
```

```
Checking endpoints:
  - localhost:9999: failed
Error: no endpoint became ready
```

**What to observe:**
- All endpoints are checked **concurrently** with `asyncio.gather` — no sequential waiting
- `--timeout` caps the wait per endpoint, avoiding long hangs on unreachable nodes
- The smoke test only runs when at least one endpoint is reachable
- Variant C exits cleanly with code 1 and a plain error message — no raw traceback

---

#### 4. `kv_example.py`

**What it does:** covers the full KV API — put, get, delete, prefix scan with descending sort, `keys_only`, `count_only`, and history compaction.

```bash
uv run python examples/kv_example.py
```

**Expected output:**
```
KV get -> hello-kv
KV delete -> exists=False
KV prefix scan (descend) -> ['example:kv:items/2', 'example:kv:items/1', 'example:kv:items/0']
KV keys_only -> 3 keys
KV count_only -> count=3
KV compact -> compacted up to revision <N>
```

**What to observe:**

| Line | What it proves |
|---|---|
| `prefix scan (descend)` | `SortOrder.DESCEND + SortTarget.KEY` returns keys in reverse lexicographic order |
| `keys_only -> 3 keys` | Returns KeyValue entries with no `value` bytes — saves bandwidth on large datasets |
| `count_only -> count=3` | Returns only the count field — transfers no key or value data at all |
| `compact -> revision <N>` | Eliminates historical revisions up to `<N>`; `<N>` varies with cluster state |

---

#### 5. `lease_example.py`

**What it does:** covers the full lease lifecycle — grant, attach key, time_to_live, leases listing, background keep-alive, and revoke — plus a **watch-on-expire** demo that shows the automatic `DELETE` event etcd fires when a lease TTL reaches zero.

**Variant A — default TTL (15 s):**
```bash
uv run python examples/lease_example.py
```

**Variant B — short TTL (recommended — expiry watch fires in ~4 s):**
```bash
uv run python examples/lease_example.py --ttl 5
```

**Expected output (Variant B):**
```
Lease grant -> lease_id=<ID>, requested_ttl=5
Lease ttl -> current_ttl=4, granted_ttl=5, keys=['example:lease:module']
Lease leases() -> active ids=[<ID>]
keep_alive_context -> running, alive=True
keep_alive_context -> stopped
Lease revoke -> ok

Lease grant (expiry demo) -> lease_id=<ID>, ttl=4s
Watching 'example:lease:expiry-watch' — waiting up to 9s for natural expiry...
Watch on expire -> type=1 (DELETE), key=example:lease:expiry-watch
```

**What to observe:**

| Line | What it proves |
|---|---|
| `current_ttl=4, granted_ttl=5` | The server starts counting down immediately after grant |
| `keys=['example:lease:module']` | `put(..., lease=lease_id)` attached the key to the lease |
| `keep_alive_context -> running` | Background loop is active and renewing the lease |
| `keep_alive_context -> stopped` | Loop is cancelled cleanly when the `async with` block exits |
| `Watch on expire -> type=1 (DELETE)` | No explicit revoke — etcd fires DELETE automatically when TTL reaches zero |

The watch-on-expire pattern (`type=1 = EventType.DELETE`) is the foundation of service discovery and distributed health-check systems.

---

#### 6. `watch_example.py`

**What it does:** demonstrates a basic watch on a single key and a watch with `WatchFilter.NODELETE` that suppresses DELETE events server-side before they reach the client.

```bash
uv run python examples/watch_example.py
```

**Expected output:**
```
Watch event -> key=example:watch:module, value=watch-event, type=0
Watch NODELETE filter -> events=1, type=0
```

**What to observe:**

| Line | What it proves |
|---|---|
| `type=0` | `EventType.PUT` — watcher received the write event |
| `NODELETE filter -> events=1, type=0` | Code issued PUT + DELETE, but only 1 event arrived — the DELETE was dropped **server-side** before transmission, saving bandwidth |

**Variant — smaller timeout:**
```bash
uv run python examples/watch_example.py --timeout 1
```
Still works — the PUT is issued 0.2 s after the watch is registered, well within 1 s.

---

#### 7. `txn_example.py`

**What it does:** exercises all transaction comparison strategies — compare by value, version, and create_revision — plus an atomic read inside a transaction's success branch.

```bash
uv run python examples/txn_example.py
```

**Expected output:**
```
txn_compare_value -> succeeded=True, value=v2
txn_compare_version -> succeeded=True
txn_compare_create_revision (key not exist) -> succeeded=True
txn_compare_create_revision (key exists) -> succeeded=False
txn_op_get -> value=created-once
```

**What to observe:**

| Line | What it proves |
|---|---|
| `compare_value succeeded=True, value=v2` | Value was `v1` → condition matched → wrote `v2` atomically |
| `compare_version succeeded=True` | Version count matched → DELETE executed |
| `create_revision (key not exist) succeeded=True` | `create_revision == 0` means key never existed → PUT executed |
| `create_revision (key exists) succeeded=False` | Key exists (`create_revision > 0`) → transaction rejected, no write |
| `txn_op_get value=created-once` | GET inside the `success` branch — read and write performed atomically |

`txn_compare_create_revision(key, 0)` is the canonical **put-if-not-exists** idiom in etcd and the foundation of all distributed locking algorithms.

---

#### 8. `concurrency_example.py`

**What it does:** demonstrates `Lock` (mutual exclusion) and `Election` (leader election) with `leader()`, `proclaim()`, and `observe()`.

```bash
uv run python examples/concurrency_example.py
```

**Expected output:**
```
Lock: acquired exclusive section
Lock: released
Election: won leadership
Election leader() -> node-1
Election proclaim() -> updated to node-1-v2
Election: resigned
Election observe() -> received 1 event(s)
```

**What to observe:**

| Line | What it proves |
|---|---|
| `Lock: acquired` → `released` | Exclusive section — no other holder can enter simultaneously |
| `Election: won leadership` | This node campaigned and won (sole candidate) |
| `leader() -> node-1` | Linearized read of the current leader's identity value |
| `proclaim() -> updated to node-1-v2` | Leader updates its identity without relinquishing leadership |
| `Election: resigned` | `async with` exited — leader key deleted, lease revoked |
| `observe() -> received 1 event(s)` | Observer received the Campaign PUT event — Watch + Election integration |

**Variant — two concurrent processes (contention):**

Open two terminals and run the command simultaneously. The second process will block at both `Lock` and `Election` until the first exits — demonstrating automatic queue behavior built on etcd's revision ordering.

---

#### 9. `auth_example.py`

**What it does:** covers auth status check, token management, and the full user/role RBAC lifecycle. Behavior changes depending on the arguments passed.

**Variant A — status only (auth disabled):**
```bash
uv run python examples/auth_example.py
```

```
Auth status -> enabled=False, authRevision=1
Auth is disabled; use --username/--password on an auth-enabled cluster.
```

**Variant B — full RBAC management (`--admin`):**
```bash
uv run python examples/auth_example.py --admin
```

```
Auth status -> enabled=False, authRevision=1
Auth is disabled; use --username/--password on an auth-enabled cluster.

--- Admin operations ---
role_add('example-viewer') -> ok
role_grant_permission('example-viewer', '/example/', READ) -> ok
role_get('example-viewer') -> 1 permission(s)
role_list() -> ['example-viewer']
user_add('example-user') -> ok
user_grant_role('example-user', 'example-viewer') -> ok
user_get('example-user') -> roles=['example-viewer']
user_list() -> ['example-user']
user_change_password('example-user') -> ok
user_revoke_role('example-user', 'example-viewer') -> ok
user_delete('example-user') -> ok
role_revoke_permission('example-viewer', '/example/') -> ok
role_delete('example-viewer') -> ok
```

**What to observe:**
- `authRevision` is an independent counter for the auth subsystem, separate from the KV revision
- `--admin` exercises the **complete RBAC lifecycle**: create role → grant permission → create user → assign role → query → change password → full cleanup
- With auth disabled, all admin operations succeed without credentials — in production they would require a root token
- When auth is enabled, add `--username root --password <pass>` to authenticate before running admin operations

---

#### 10. `maintenance_example.py`

**What it does:** covers cluster status, alarm management, defragmentation, consistency hashing, downgrade validation, and optional full-database snapshot streaming.

**Variant A — standard operations:**
```bash
uv run python examples/maintenance_example.py
```

**Variant B — with snapshot:**
```bash
uv run python examples/maintenance_example.py --snapshot
```

**Expected output:**
```
Status -> leader=<ID>, version=3.6.8, db_size=<N> bytes
Alarms -> none active
alarm_deactivate(NOSPACE) -> ok
defragment() -> ok
hash_kv() -> hash=0x<HASH>, compact_revision=<N>, hash_revision=<N>
hash() -> hash=0x<HASH>
downgrade(VALIDATE, "3.5.0") -> version=3.6
# Variant B adds:
snapshot() -> received <N> bytes
```

**What to observe:**

| Line | What it proves |
|---|---|
| `leader=<ID>` | Numeric ID of the current Raft leader |
| `db_size=<N> bytes` | Current size of the boltdb file on disk |
| `alarm_deactivate(NOSPACE)` | No-op when no alarm is active — safe to call unconditionally |
| `defragment()` | Compacts the boltdb file, reclaiming space freed by compaction |
| `hash_kv()` | MVCC hash at a specific revision — used to verify consistency between members |
| `hash()` | Full-store hash including internal metadata — used in testing |
| `downgrade(VALIDATE, "3.5.0")` | **Read-only** — only checks eligibility, does not change cluster state |
| `snapshot()` | Binary stream of the full database — base for backup and point-in-time restore |

---

#### 11. `cluster_example.py`

**What it does:** lists all cluster members with their IDs, names, peer URLs, and client URLs. Mutations (add/promote/update/remove) are shown as commented examples in the script.

**Variant A — default endpoint:**
```bash
uv run python examples/cluster_example.py
```

**Variant B — query from a different member:**
```bash
uv run python examples/cluster_example.py --endpoints localhost:3379
```

**Expected output:**
```
member_list() -> 3 member(s)
  id=<ID>  name='etcd2'  peerURLs=['http://etcd2:2380']  clientURLs=['http://etcd2:2379']
  id=<ID>  name='etcd3'  peerURLs=['http://etcd3:2380']  clientURLs=['http://etcd3:2379']
  id=<ID>  name='etcd1'  peerURLs=['http://etcd1:2380']  clientURLs=['http://etcd1:2379']
```

**What to observe:**
- Any cluster member answers with the **full member list** — the response is identical regardless of which node is queried
- `peerURLs` (port 2380) — used for internal Raft communication between members
- `clientURLs` (port 2379) — the address exposed to clients
- No `[learner]` tag — all three are full voting members
- Member order may vary across calls — it is not guaranteed to be stable

---

#### 12. `full_example.py`

**What it does:** end-to-end smoke test that exercises every service in sequence — ping, KV, Lease, Watch, Maintenance, Lock, and Election — using all 3 cluster nodes with automatic round-robin load balancing.

```bash
uv run python examples/full_example.py
```

**Expected output:**
```
Ping ok -> cluster is reachable and writes are accepted
KV put/get ok -> hello-etcd3aio
KV delete ok -> exists=False
Lease grant ok -> lease_id=<ID>, ttl=<N>
Watch event ok -> key=example:watch, type=0
Maintenance status ok -> leader=<ID>, version=3.6.8
Maintenance alarms ok -> active=0
Lock ok -> acquired exclusive section
Lock ok -> released
Election ok -> won leadership
Election leader() ok -> node-1
Election proclaim() ok -> updated
Election ok -> resigned
```

**What to observe:**
- Each block validates a different service — if any service fails, execution stops with a clear error pointing to the failing step
- Uses all 3 endpoints by default — requests are automatically distributed across nodes
- Run this after bringing up a new cluster or after upgrading the library to confirm every service is fully operational

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) — local workflow, design principles and quality checks
- [ARCHITECTURE.md](ARCHITECTURE.md) — module boundaries and responsibilities
- [CHANGELOG.md](CHANGELOG.md) — version history
- [ROADMAP.md](ROADMAP.md) — implemented and deferred features
