# etcd3aio — Examples

Step-by-step walkthrough of every script in the [`examples/`](examples/) directory.

All examples require a running etcd cluster. Start a local 3-node cluster with:

```bash
docker compose -f docker/compose.yaml up -d
```

This starts etcd on ports **2379**, **3379**, and **4379**.

---

## Example scripts

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

---

## Step-by-step walkthrough

---

### 1. `get_started_example.py`

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

| Line | What it proves |
|---|---|
| `ping -> cluster is reachable` | Cluster accepts both reads and writes before doing anything else |
| `after delete -> exists=False` | Key was fully removed — `get` returns no `kvs` |
| `prefix scan -> 3 keys found` | Range query using `prefix_range_end()` returns all keys under a prefix |
| `lock -> acquired` / `released` | Distributed mutex acquired and cleanly released |
| `election -> this node is the leader` | Campaign succeeded — node holds leadership |
| `election -> resigned` | Leadership relinquished cleanly on `async with` exit |

---

### 2. `client_example.py`

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

| Line | What it proves |
|---|---|
| `services initialized: kv, lease, watch, auth, maintenance` | Client without `async with` is valid — useful for DI containers and frameworks |
| `ping -> cluster is reachable and accepting writes` | `ping()` performs put + get + delete to verify full read/write availability |
| `ping(write_check=False) -> cluster is readable` | Lighter health probe that skips the write step |
| `Client closed` | `finally: await client.close()` executed — no resource leak even on exception |

---

### 3. `connections_example.py`

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

| Behaviour | What it proves |
|---|---|
| All endpoints checked simultaneously | `asyncio.gather` — no sequential waiting per node |
| `--timeout` argument | Caps the wait per endpoint — avoids long hangs on unreachable nodes |
| Smoke test only runs when reachable | Guard logic prevents attempting KV ops against a dead cluster |
| Variant C exits with code 1, no traceback | Clean CLI failure path — `RuntimeError` caught and converted to a plain message |

---

### 4. `kv_example.py`

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
| `keys_only -> 3 keys` | Returns `KeyValue` entries with no `value` bytes — saves bandwidth on large datasets |
| `count_only -> count=3` | Returns only the count field — transfers no key or value data at all |
| `compact -> revision <N>` | Eliminates historical revisions up to `<N>`; value varies with cluster state |

---

### 5. `lease_example.py`

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
| `current_ttl=4, granted_ttl=5` | Server starts the countdown immediately after grant |
| `keys=['example:lease:module']` | `put(..., lease=lease_id)` attached the key to the lease |
| `keep_alive_context -> running` | Background loop is active and renewing the lease |
| `keep_alive_context -> stopped` | Loop is cancelled cleanly when the `async with` block exits |
| `Watch on expire -> type=1 (DELETE)` | No explicit revoke — etcd fires DELETE automatically when TTL reaches zero |

The watch-on-expire pattern (`EventType.DELETE = 1`) is the foundation of service discovery
and distributed health-check systems: a node's keys disappear automatically when it stops
renewing its lease.

---

### 6. `watch_example.py`

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

| Behaviour | What it proves |
|---|---|
| Output identical to default | PUT is issued 0.2 s after the watch is registered — well within 1 s |
| No timeout error | Watch stream receives the event before the deadline expires |

---

### 7. `txn_example.py`

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
| `compare_value -> succeeded=True, value=v2` | Value was `v1` → condition matched → wrote `v2` atomically |
| `compare_version -> succeeded=True` | Version count matched → DELETE executed atomically |
| `create_revision (key not exist) -> succeeded=True` | `create_revision == 0` means key never existed → PUT executed |
| `create_revision (key exists) -> succeeded=False` | Key exists (`create_revision > 0`) → transaction rejected, no write |
| `txn_op_get -> value=created-once` | GET inside the `success` branch — read and write performed in one atomic operation |

`txn_compare_create_revision(key, 0)` is the canonical **put-if-not-exists** idiom in etcd
and the foundation of all distributed locking algorithms.

---

### 8. `concurrency_example.py`

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
| `leader() -> node-1` | Linearized read of the current leader's published identity |
| `proclaim() -> updated to node-1-v2` | Leader updates its identity without relinquishing leadership |
| `Election: resigned` | `async with` exited — leader key deleted, lease revoked |
| `observe() -> received 1 event(s)` | Observer received the Campaign PUT event — Watch + Election integration |

**Variant — two concurrent processes (contention):**

Open two terminals and run the command simultaneously. The second process blocks at both
`Lock` and `Election` until the first exits — demonstrating automatic queue behavior built
on etcd's revision ordering.

---

### 9. `auth_example.py`

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

| Behaviour | What it proves |
|---|---|
| `authRevision` is separate from KV revision | The auth subsystem maintains its own independent revision counter |
| `--admin` runs the full RBAC lifecycle | Create role → grant permission → create user → assign role → query → change password → full cleanup |
| Admin ops succeed without credentials | Auth is disabled — in production they require a root token |
| `--username / --password` flags | When auth is enabled, use these to authenticate before running admin operations |

---

### 10. `maintenance_example.py`

**What it does:** covers cluster status, alarm management, defragmentation, consistency hashing, downgrade validation, and optional full-database snapshot streaming.

**Variant A — standard operations:**
```bash
uv run python examples/maintenance_example.py
```

**Expected output (Variant A):**
```
Status -> leader=<ID>, version=3.6.8, db_size=<N> bytes
Alarms -> none active
alarm_deactivate(NOSPACE) -> ok
defragment() -> ok
hash_kv() -> hash=0x<HASH>, compact_revision=<N>, hash_revision=<N>
hash() -> hash=0x<HASH>
downgrade(VALIDATE, "3.5.0") -> version=3.6
```

**Variant B — with snapshot:**
```bash
uv run python examples/maintenance_example.py --snapshot
```

**Expected output (Variant B adds):**
```
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

### 11. `cluster_example.py`

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

| Behaviour | What it proves |
|---|---|
| Output identical from any node | Any member answers `member_list()` with the full cluster view |
| `peerURLs` use port 2380 | Internal Raft communication between members |
| `clientURLs` use port 2379 | Address exposed to client applications |
| No `[learner]` tag | All three are full voting members |
| Member order may vary | The list is not guaranteed to be stable across calls |

---

### 12. `full_example.py`

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

| Line | What it proves |
|---|---|
| `Ping ok -> writes are accepted` | Cluster is healthy before any other operation runs |
| `KV put/get ok` / `KV delete ok` | Full read/write/delete cycle confirmed |
| `Lease grant ok` | Lease service is functional — ID varies with cluster state |
| `Watch event ok -> type=0` | Watch stream receives `EventType.PUT` in real time |
| `Maintenance status ok` | Status RPC returns leader ID and version — cluster is stable |
| `Maintenance alarms ok -> active=0` | No active alarms — cluster storage and state are healthy |
| `Lock ok -> acquired` / `released` | Distributed mutex works end-to-end |
| `Election ok -> won` / `resigned` | Full campaign + resign cycle confirmed |
| All 13 lines printed without error | Every service operational — safe to proceed with upgrading or deploying |

Run this script after bringing up a new cluster or after upgrading the library to confirm
every service is fully operational end-to-end.
