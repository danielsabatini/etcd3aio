# Roadmap

Reference: [etcd v3.6 API](https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/)

## Implemented

### KV Service
- `Range` → `kv.get()` — with `limit`, `sort_order` / `sort_target` (`SortOrder`, `SortTarget`), `keys_only`, `count_only`
- `Put` → `kv.put()`
- `DeleteRange` → `kv.delete()`
- `Compact` → `kv.compact()`
- `Txn` → `kv.txn()` + compare/operation helpers
- `prefix_range_end()` — helper to build the exclusive upper bound for prefix scans

### Lease Service
- `LeaseGrant` → `lease.grant()`
- `LeaseRevoke` → `lease.revoke()`
- `LeaseTimeToLive` → `lease.time_to_live()`
- `LeaseKeepAlive` → `lease.keep_alive()` (raw stream) / `lease.keep_alive_context()` (background task)
- `LeaseLeases` → `lease.leases()`

### Watch Service
- `Watch` → `watch.watch()` — with `filters` (`WatchFilter`) and `progress_notify`

### Maintenance Service
- `Status` → `maintenance.status()`
- `Alarm` (GET) → `maintenance.alarms()`
- `Alarm` (DEACTIVATE) → `maintenance.alarm_deactivate()`
- `Defragment` → `maintenance.defragment()` — reclaim storage freed by compaction
- `HashKV` → `maintenance.hash_kv()` — consistency check between cluster members
- `MoveLeader` → `maintenance.move_leader()` — transfer leadership to another member
- `Snapshot` → `maintenance.snapshot()` — async generator streaming a full binary backup

### Concurrency Primitives
- `Lock` → `client.lock()` — distributed lock
- `Election` → `client.election()` — leader election
  - Campaign / Resign — `async with client.election(...)`
  - Proclaim — `election.proclaim(value)` — leader updates its published value
  - Leader — `election.leader()` — query the current leader
  - Observe — `election.observe()` — stream of leadership changes (PUT events)
- `txn_compare_create_revision()` — canonical "key does not exist" idiom (`create_revision == 0`)

### Auth Service
- `AuthStatus` → `auth.auth_status()` — checks whether authentication is enabled on the cluster
- `Authenticate` → `auth.authenticate()` — obtains a token for a username/password pair
- `AuthEnable` → `auth.auth_enable()` — enables authentication on the cluster
- `AuthDisable` → `auth.auth_disable()` — disables authentication on the cluster
- User management: `UserAdd` → `auth.user_add()`, `UserGet` → `auth.user_get()`, `UserList` → `auth.user_list()`, `UserDelete` → `auth.user_delete()`, `UserChangePassword` → `auth.user_change_password()`
- RBAC: `UserGrantRole` → `auth.user_grant_role()`, `UserRevokeRole` → `auth.user_revoke_role()`
- Role management: `RoleAdd` → `auth.role_add()`, `RoleGet` → `auth.role_get()`, `RoleList` → `auth.role_list()`, `RoleDelete` → `auth.role_delete()`
- RBAC: `RoleGrantPermission` → `auth.role_grant_permission()` (with `PermissionType` enum), `RoleRevokePermission` → `auth.role_revoke_permission()`

### Client
- Connection manager with round-robin load balancing
- Retry with exponential backoff (`BaseService._rpc`)
- Per-call timeout: `timeout: float | None = None` on all service methods (`asyncio.timeout()`)
- `client.ping()` — connectivity and write-quorum check
- Auth error mapping: `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`
- `client.set_token()` / `token=` constructor parameter — propagates the auth token to all services as gRPC metadata
- `client.token_refresher(name, password)` / `TokenRefresher` — background context manager that re-authenticates before the token expires

---

## Deferred

### Cluster Service
- `MemberList` — list all members with their peer/client URLs
- `MemberAdd` / `MemberRemove` / `MemberUpdate` — member management
- `MemberPromote` — promote a learner to voting member

### Maintenance
- `Hash` — full-store hash (vs `HashKV` which covers MVCC keys only)
- `Downgrade` — manage cluster version downgrade
