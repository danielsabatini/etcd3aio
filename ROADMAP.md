# Roadmap

Reference: [etcd v3.6 API](https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/)

## Implemented

### KV Service
- `Range` → `kv.get()`
- `Put` → `kv.put()`
- `DeleteRange` → `kv.delete()`
- `Compact` → `kv.compact()`
- `Txn` → `kv.txn()` + compare/op helpers

### Lease Service
- `LeaseGrant` → `lease.grant()`
- `LeaseRevoke` → `lease.revoke()`
- `LeaseTimeToLive` → `lease.time_to_live()`
- `LeaseKeepAlive` → `lease.keep_alive()`
- `LeaseLeases` → `lease.leases()`

### Watch Service
- `Watch` → `watch.watch()`

### Maintenance Service
- `Status` → `maintenance.status()`
- `Alarm` (GET) → `maintenance.alarms()`
- `Alarm` (DEACTIVATE) → `maintenance.alarm_deactivate()`

### Concurrency primitives
- `Lock` → `client.lock()` — distributed lock
- `Election` → `client.election()` — leader election

### Client
- Connection manager with round-robin load balancing
- Retry with exponential backoff (`BaseService._rpc`)
- `client.ping()` — connectivity and write quorum check
- Auth error mapping: `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`

---

## Next

### Auth Service (developer-facing)
- `AuthStatus` → `auth.auth_status()` — check if auth is enabled on the cluster
- `Authenticate` → `auth.authenticate()` — obtain a token for a user/password pair

---

## Admin (deferred)

> Operations for cluster operators, not application developers.

### Cluster Service
- `MemberList` — list all members with their peer/client URLs
- `MemberAdd` / `MemberRemove` / `MemberUpdate` — membership management
- `MemberPromote` — promote a learner to voting member

### Auth Service (admin)
- `AuthEnable` / `AuthDisable` — turn auth on/off
- User management: `UserAdd`, `UserGet`, `UserList`, `UserDelete`, `UserChangePassword`
- Role management: `RoleAdd`, `RoleGet`, `RoleList`, `RoleDelete`
- RBAC: `UserGrantRole`, `UserRevokeRole`, `RoleGrantPermission`, `RoleRevokePermission`

### Maintenance (admin-heavy)
- `Defragment` — reclaim storage space from the backend
- `Snapshot` — stream a full backup of the backend database
- `MoveLeader` — transfer leadership to another member
- `Hash` / `HashKV` — checksum for data integrity verification
- `Downgrade` — manage cluster version downgrade
