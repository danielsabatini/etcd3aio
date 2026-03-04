# etcd3aio — Module Reference

Service API reference with usage examples for every module exposed by `Etcd3Client`.

All services are accessed via properties on the client instance (`client.kv`, `client.lease`, etc.).
Concurrency primitives (`lock`, `election`) are created via factory methods.

---

## KVService — `client.kv`

Key-value operations: put, get, delete, compact, and atomic transactions.

```python
from etcd3aio.kv import SortOrder, SortTarget, prefix_range_end

# Put and get
await client.kv.put('myapp/greeting', 'hello')
resp = await client.kv.get('myapp/greeting')
print(resp.kvs[0].value.decode())  # hello

# Delete
await client.kv.delete('myapp/greeting')

# Prefix scan with descending sort
resp = await client.kv.get(
    'myapp/',
    range_end=prefix_range_end('myapp/'),
    sort_order=SortOrder.DESCEND,
    sort_target=SortTarget.KEY,
)

# Keys only (no value bytes transferred)
resp = await client.kv.get('myapp/', range_end=prefix_range_end('myapp/'), keys_only=True)

# Count only (no key or value data transferred)
resp = await client.kv.get('myapp/', range_end=prefix_range_end('myapp/'), count_only=True)
print(resp.count)

# Compact historical revisions
header = await client.kv.compact(revision=resp.header.revision)

# Compare-and-swap (atomic transaction)
resp = await client.kv.txn(
    compare=[client.kv.txn_compare_value('myapp/flag', 'off')],
    success=[client.kv.txn_op_put('myapp/flag', 'on')],
    failure=[client.kv.txn_op_get('myapp/flag')],
)

# Put-if-not-exists (canonical etcd idiom)
resp = await client.kv.txn(
    compare=[client.kv.txn_compare_create_revision('myapp/lock', 0)],
    success=[client.kv.txn_op_put('myapp/lock', 'holder')],
    failure=[],
)
print(resp.succeeded)  # True if key did not exist
```

---

## LeaseService — `client.lease`

Lease lifecycle management with optional background keep-alive.

```python
# Grant a lease and attach a key to it
lease = await client.lease.grant(ttl=30)
await client.kv.put('myapp/lock', 'held', lease=lease.ID)

# Query remaining TTL and attached keys
info = await client.lease.time_to_live(lease.ID, keys=True)
print(info.TTL, info.keys)

# List all active leases
resp = await client.lease.leases()
print([l.ID for l in resp.leases])

# Automatic renewal in the background
async with client.lease.keep_alive_context(lease.ID, ttl=30):
    await do_long_work()  # lease is renewed automatically

# Revoke when done
await client.lease.revoke(lease.ID)
```

**Watch-on-expire pattern:** when a lease TTL reaches zero, etcd automatically fires a `DELETE`
event (`EventType=1`) on every key attached to that lease — the foundation of service discovery
and distributed health-check systems.

---

## WatchService — `client.watch`

Async iterator over etcd events with automatic reconnection and server-side filtering.
Watch streams reconnect indefinitely on transient errors, tracking `next_revision` to
avoid duplicate or missed events.

```python
from etcd3aio.watch import WatchFilter
from etcd3aio.kv import prefix_range_end

# Watch a single key
async for response in client.watch.watch('myapp/flag'):
    for event in response.events:
        print(event.type, event.kv.value.decode())

# Watch a prefix, suppress DELETE events server-side
async for response in client.watch.watch(
    'myapp/',
    range_end=prefix_range_end('myapp/'),
    filters=(WatchFilter.NODELETE,),
):
    for event in response.events:
        print(event.type, event.kv.key.decode())

# Start watching from a specific revision (no missed events)
async for response in client.watch.watch('myapp/flag', start_revision=42):
    ...
```

| `WatchFilter` | Effect |
|---|---|
| `NODELETE` | Server drops DELETE events before transmission |
| `NOPUT` | Server drops PUT events before transmission |

---

## Lock — `client.lock()`

Distributed mutex built on KV + Lease. Guarantees mutual exclusion across processes and nodes.
Multiple waiters queue automatically using etcd's revision ordering.

```python
# Context manager (recommended)
async with client.lock('myapp/resource', ttl=10):
    # Only one holder at a time across the entire cluster
    await do_exclusive_work()

# Manual acquire / release
lock = client.lock('myapp/resource', ttl=10)
await lock.acquire()
try:
    await do_exclusive_work()
finally:
    await lock.release()
```

---

## Election — `client.election()`

Leader election built on KV + Lease. Supports campaign, resign, observe, proclaim, and leader query.

```python
# Campaign for leadership (blocks until won)
async with client.election('myapp/leader', value=b'node-1', ttl=10) as e:
    # This node is the leader inside this block
    leader = await e.leader()
    print(leader.kvs[0].value.decode())   # node-1

    # Update the published identity without relinquishing leadership
    await e.proclaim(b'node-1-updated')

# Stream leadership changes (useful for followers / observers)
async for response in client.election('myapp/leader').observe():
    print('new leader event', response.events)
```

---

## AuthService — `client.auth`

Full authentication and RBAC management: auth enable/disable, user and role lifecycle,
token refresh.

```python
from etcd3aio import PermissionType
from etcd3aio.kv import prefix_range_end

# Check auth status
status = await client.auth.auth_status()
print(status.enabled, status.authRevision)

# Authenticate and set token manually
resp = await client.auth.authenticate('user', 'password')
client.set_token(resp.token)

# Or use the background refresher (re-authenticates automatically before expiry)
async with client.token_refresher('user', 'password'):
    await client.kv.put('secure/key', 'value')

# Enable / disable auth (requires root credentials)
await client.auth.auth_enable()
await client.auth.auth_disable()

# User management
await client.auth.user_add('alice', 'secret')
await client.auth.user_change_password('alice', 'new-secret')
await client.auth.user_get('alice')
await client.auth.user_list()
await client.auth.user_grant_role('alice', 'viewer')
await client.auth.user_revoke_role('alice', 'viewer')
await client.auth.user_delete('alice')

# Role management (RBAC)
await client.auth.role_add('viewer')
await client.auth.role_grant_permission(
    'viewer', '/app/', prefix_range_end('/app/'), perm_type=PermissionType.READ
)
await client.auth.role_get('viewer')
await client.auth.role_list()
await client.auth.role_revoke_permission('viewer', '/app/', prefix_range_end('/app/'))
await client.auth.role_delete('viewer')
```

| `PermissionType` | Access granted |
|---|---|
| `READ` | Get and range queries |
| `WRITE` | Put and delete |
| `READWRITE` | Both read and write |

---

## ClusterService — `client.cluster`

Cluster membership management: list, add, remove, update, and promote members.

```python
# List all cluster members
resp = await client.cluster.member_list()
for m in resp.members:
    print(f'id={m.ID}  name={m.name}  learner={m.isLearner}  urls={list(m.peerURLs)}')

# Add a learner member (non-voting), then promote to full voting member
add_resp = await client.cluster.member_add(['http://10.0.0.4:2380'], is_learner=True)
new_id = add_resp.member.ID
await client.cluster.member_promote(new_id)

# Update peer URLs of an existing member
await client.cluster.member_update(new_id, ['http://10.0.0.4:2381'])

# Remove a member
await client.cluster.member_remove(new_id)
```

---

## MaintenanceService — `client.maintenance`

Cluster health, alarm management, storage defragmentation, consistency hashing,
leader transfer, and snapshot streaming.

```python
from etcd3aio import DowngradeAction
from etcd3aio.maintenance import AlarmType

# Cluster status
status = await client.maintenance.status()
print(f'leader={status.leader}, version={status.version}, db_size={status.dbSize}')

# Alarm management
alarms = await client.maintenance.alarms()
await client.maintenance.alarm_deactivate(AlarmType.NOSPACE)

# Reclaim storage freed by compaction
await client.maintenance.defragment()

# Full-store hash (includes internal metadata — used in testing)
h = await client.maintenance.hash()
print(f'hash={h.hash:#010x}')

# MVCC hash at a specific revision — verifies consistency between members
hkv = await client.maintenance.hash_kv()
print(f'hash={hkv.hash:#010x}, revision={hkv.hash_revision}')

# Transfer Raft leadership to another member
await client.maintenance.move_leader(target_id)

# Validate downgrade eligibility (read-only, does not change cluster state)
await client.maintenance.downgrade(DowngradeAction.VALIDATE, '3.5.0')

# Stream a full binary backup
chunks: list[bytes] = []
async for chunk in client.maintenance.snapshot():
    chunks.append(chunk)
data = b''.join(chunks)
```

| `AlarmType` | Meaning |
|---|---|
| `NONE` | No alarm (used to deactivate all) |
| `NOSPACE` | Disk quota exceeded |
| `CORRUPT` | Data corruption detected |

| `DowngradeAction` | Effect |
|---|---|
| `VALIDATE` | Read-only eligibility check |
| `ENABLE` | Begin downgrade process |
| `CANCEL` | Abort in-progress downgrade |

---

## Multi-endpoint & TLS

Pass multiple endpoints for automatic round-robin load balancing across cluster nodes.
For TLS, supply certificate bytes directly to the client constructor.

```python
from pathlib import Path
from etcd3aio import Etcd3Client

# Multi-endpoint (round-robin load balancing)
async with Etcd3Client(
    ['etcd-node1:2379', 'etcd-node2:2379', 'etcd-node3:2379'],
) as client:
    await client.ping()

# One-way TLS (server certificate verification)
async with Etcd3Client(
    ['etcd-node1:2379'],
    ca_cert=Path('ca.crt').read_bytes(),
) as client:
    await client.ping()

# Mutual TLS (mTLS — client presents its own certificate)
async with Etcd3Client(
    ['etcd-node1:2379', 'etcd-node2:2379', 'etcd-node3:2379'],
    ca_cert=Path('ca.crt').read_bytes(),
    cert_key=Path('client.key').read_bytes(),
    cert_chain=Path('client.crt').read_bytes(),
) as client:
    await client.ping()
```
