# Architecture

`etcd3aio` is organized as a thin facade over async gRPC services.

## Modules

- `client.py`: service lifecycle and wiring (`Etcd3Client`); `lock()` / `election()` / `token_refresher()` factory methods
- `connections.py`: channel creation, TLS/mTLS, round-robin load balancing, gRPC keepalive; `tls_server_name` sets `grpc.ssl_target_name_override` — required for multi-endpoint TLS because the `ipv4:` scheme cannot derive a server name from a comma-separated address list
- `base.py`: shared retry/backoff helper for unary RPCs; per-call `asyncio.timeout()`; maps `UNAUTHENTICATED` → `EtcdUnauthenticatedError`, `PERMISSION_DENIED` → `EtcdPermissionDeniedError`; `set_token()` injects auth token as gRPC metadata
- `kv.py`: KV operations (put/get/delete/compact/txn); `SortOrder` / `SortTarget` enums; `prefix_range_end()` utility; `txn_compare_create_revision()` for the "key does not exist" idiom
- `lease.py`: lease operations (grant/revoke/time_to_live/keep_alive/leases); `LeaseKeepalive` async context manager for background keepalive
- `auth.py`: full Auth API — `auth_status()` / `authenticate()` / `auth_enable()` / `auth_disable()`; user management (`user_add/get/list/delete/change_password/grant_role/revoke_role`); role management (`role_add/get/list/delete/grant_permission/revoke_permission`); `PermissionType` enum; `TokenRefresher` async context manager for automatic token renewal
- `maintenance.py`: cluster status and alarm management (`status`, `alarms`, `alarm_deactivate`); `defragment()`; `hash()` (full-store); `hash_kv()`; `move_leader()`; `snapshot()` async generator for binary backup streaming; `downgrade()` for version downgrade management; `AlarmType` and `DowngradeAction` enums
- `cluster.py`: cluster membership management — `member_list()`, `member_add()`, `member_remove()`, `member_update()`, `member_promote()`
- `concurrency.py`: distributed lock (`Lock`) and leader election (`Election`) built on KV + Lease; `Election` exposes `leader()`, `proclaim()` and `observe()` beyond the Campaign/Resign lifecycle
- `watch.py`: watch stream with automatic reconnection and revision tracking; `WatchFilter` enum for server-side event filtering
- `_protobuf.py`: protobuf/stub type aliases and import bootstrap
- `errors.py`: library exceptions (`EtcdError`, `EtcdConnectionError`, `EtcdTransientError`, `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`)

## Design Boundaries

- The facade stays small.
- gRPC details stay out of the user-facing API.
- Service modules must be cohesive and easy to test.
- Avoid deep inheritance and complex indirection.

## Request Flow

1. User calls a facade service method.
2. The service builds the protobuf request object.
3. The service executes the gRPC call.
4. The retry helper handles transient unary failures.
5. The response is returned as a protobuf object.

## Non-Goals (for now)

- Custom DSLs for etcd operations
- Heavy plugin/interceptor framework
- Multiplexed watch manager for large-scale fan-out
