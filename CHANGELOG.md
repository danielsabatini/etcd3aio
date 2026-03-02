# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

**Auth service** — full Auth API coverage
- `auth.auth_enable()` / `auth.auth_disable()` — enable and disable authentication on the cluster
- User management: `auth.user_add()`, `auth.user_get()`, `auth.user_list()`, `auth.user_delete()`, `auth.user_change_password()`
- RBAC: `auth.user_grant_role()`, `auth.user_revoke_role()`
- Role management: `auth.role_add()`, `auth.role_get()`, `auth.role_list()`, `auth.role_delete()`
- RBAC: `auth.role_grant_permission()`, `auth.role_revoke_permission()`
- `PermissionType` enum (`READ`, `WRITE`, `READWRITE`) — exported from the top-level package

**Maintenance service** — extended operations
- `maintenance.defragment()` — reclaim storage freed by previous compactions
- `maintenance.hash_kv()` — compute an MVCC hash for consistency checks
- `maintenance.move_leader()` — transfer cluster leadership to another member
- `maintenance.snapshot()` — async generator streaming a full binary backup

---

## [0.1.0] - 2026-03-01

Initial release of **etcd3aio** — async Python client for etcd v3 using `grpc.aio`.

### Added

**KV service** (`kv.put`, `kv.get`, `kv.delete`, `kv.compact`, `kv.txn`)
- Range queries with `limit`, `sort_order` / `sort_target` (`SortOrder`, `SortTarget`), `keys_only`, `count_only`
- Transaction helpers: `txn_compare_value`, `txn_compare_version`, `txn_compare_create_revision`
- Transaction operations: `txn_op_put`, `txn_op_get`, `txn_op_delete`
- `prefix_range_end()` helper for prefix scans

**Lease service** (`lease.grant`, `lease.revoke`, `lease.time_to_live`, `lease.keep_alive`, `lease.leases`)
- `keep_alive_context()` — background context manager for automatic lease renewal

**Watch service** (`watch.watch`)
- Async iterator with automatic reconnection on transient failures
- Server-side event filtering via `WatchFilter` (`NOPUT`, `NODELETE`)
- `progress_notify` support

**Maintenance service** (`maintenance.status`, `maintenance.alarms`, `maintenance.alarm_deactivate`)
- `AlarmType` enum (`NONE`, `NOSPACE`, `CORRUPT`)

**Auth service** (`auth.auth_status`, `auth.authenticate`)
- `client.set_token()` — propagates auth token to all services as gRPC metadata
- `client.token_refresher()` / `TokenRefresher` — background context manager for token refresh

**Concurrency primitives**
- `Lock` — distributed lock via `client.lock()`
- `Election` — leader election via `client.election()`:
  - `Campaign` / `Resign` — `async with client.election(...)`
  - `leader()` — query current leader
  - `proclaim()` — leader updates its published value
  - `observe()` — stream of leadership changes (PUT events)

**Client** (`Etcd3Client`)
- Round-robin load balancing across multiple endpoints
- Exponential backoff retry for transient errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`)
- Per-call timeout via `timeout: float | None = None` on all service methods
- `client.ping()` — connectivity and write-quorum check
- Error hierarchy: `EtcdError`, `EtcdConnectionError`, `EtcdTransientError`, `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`
- Full PEP 561 typing support (`py.typed` marker)

[0.1.0]: https://github.com/dsfreitas/etcd3aio/releases/tag/v0.1.0
