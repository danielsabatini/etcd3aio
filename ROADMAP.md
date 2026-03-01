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

### Concurrency Primitives
- `Lock` → `client.lock()` — distributed lock
- `Election` → `client.election()` — leader election
  - Campaign / Resign — `async with client.election(...)`
  - Proclaim — `election.proclaim(value)` — leader updates its published value
  - Leader — `election.leader()` — query the current leader
  - Observe — `election.observe()` — stream of leadership changes (PUT events)
- `txn_compare_create_revision()` — canonical "key does not exist" idiom (`create_revision == 0`)

### Auth Service (developer-facing)
- `AuthStatus` → `auth.auth_status()` — checks whether authentication is enabled on the cluster
- `Authenticate` → `auth.authenticate()` — obtains a token for a username/password pair

### Client
- Connection manager with round-robin load balancing
- Retry with exponential backoff (`BaseService._rpc`)
- Per-call timeout: `timeout: float | None = None` on all service methods (`asyncio.timeout()`)
- `client.ping()` — connectivity and write-quorum check
- Auth error mapping: `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`
- `client.set_token()` / `token=` constructor parameter — propagates the auth token to all services as gRPC metadata
- `client.token_refresher(name, password)` / `TokenRefresher` — background context manager that re-authenticates before the token expires

---

## Admin (deferred)

> Operations for cluster administrators, not application developers.

### Cluster Service
- `MemberList` — list all members with their peer/client URLs
- `MemberAdd` / `MemberRemove` / `MemberUpdate` — member management
- `MemberPromote` — promote a learner to voting member

### Auth Service (admin)
- `AuthEnable` / `AuthDisable` — enable/disable authentication
- User management: `UserAdd`, `UserGet`, `UserList`, `UserDelete`, `UserChangePassword`
- Role management: `RoleAdd`, `RoleGet`, `RoleList`, `RoleDelete`
- RBAC: `UserGrantRole`, `UserRevokeRole`, `RoleGrantPermission`, `RoleRevokePermission`

### Maintenance (heavy admin)
- `Defragment` — reclaim storage space from the backend
- `Snapshot` — stream a full backup of the backend database
- `MoveLeader` — transfer leadership to another member
- `Hash` / `HashKV` — checksum for data integrity verification
- `Downgrade` — manage cluster version downgrade
