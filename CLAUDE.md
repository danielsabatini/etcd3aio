# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**etcd3aio** is an async Python client for etcd v3 using `grpc.aio`. It strictly follows the **facade pattern** — a thin, well-typed wrapper over generated gRPC stubs with centralized retry logic.

Design principles and rules are in [CONTRIBUTING.md](CONTRIBUTING.md). Architectural boundaries are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Development Setup

```bash
uv venv
uv pip install -e .
```

## Commands

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_kv.py

# Run a single test
pytest tests/test_kv.py::test_put_success

# Format
ruff format .

# Lint (with auto-fix)
ruff check --fix .

# Type checking
pyright

# Start local etcd cluster (3 nodes)
docker compose -f docker/docker-compose.yaml up -d
```

## Architecture

### Module Responsibilities

| Module | Role |
|---|---|
| `client.py` | `Etcd3Client` — facade, lifecycle, wires services; `ping()`, `token_refresher()`, `lock()`, `election()` factory methods |
| `connections.py` | `ConnectionManager` — channel creation, TLS, round-robin load balancing; `localhost` is auto-resolved to `127.0.0.1` |
| `base.py` | `BaseService` — shared retry/backoff for unary RPC; `set_token()` for gRPC metadata |
| `kv.py` | `KVService` — put/get/delete/compact/txn; `SortOrder`, `SortTarget` enums; `prefix_range_end()`; `txn_compare_create_revision()` for "key doesn't exist" idiom |
| `lease.py` | `LeaseService` — grant/revoke/leases/keep_alive; `LeaseKeepalive` background context manager |
| `maintenance.py` | `MaintenanceService` — status/alarms/alarm_deactivate; `AlarmType` enum |
| `auth.py` | `AuthService` — auth_status/authenticate; `TokenRefresher` background context manager for token refresh |
| `concurrency.py` | `Lock`, `Election` — distributed lock and leader election built on KV + Lease; `Election` exposes `leader()`, `proclaim()`, `observe()` beyond Campaign/Resign |
| `watch.py` | `WatchService` — async iterator with automatic reconnection; `WatchFilter` enum |
| `errors.py` | `EtcdError`, `EtcdConnectionError`, `EtcdTransientError`, `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError` |
| `_protobuf.py` | Centralizes all protobuf imports and TypeAlias definitions |

### Request Flow

```
User call → Service method → Protobuf request object → BaseService._rpc() → gRPC stub → Response
```

Transient errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`) are retried with exponential backoff (up to 3 attempts by default, 0.05 s → 1.0 s max). After exhaustion: `UNAVAILABLE` raises `EtcdConnectionError`; `DEADLINE_EXCEEDED` raises `EtcdTransientError`. Non-retried gRPC errors are also mapped: `UNAUTHENTICATED` → `EtcdUnauthenticatedError`; `PERMISSION_DENIED` → `EtcdPermissionDeniedError`.

Watch streams track `next_revision` for safe reconnection after transient failures. Unlike unary RPCs, watch reconnects indefinitely (no `max_attempts` limit).

### Protobuf Layer

All generated proto stubs live in `src/etcd3aio/proto/`. **Never modify these files** — they are generated from the etcd v3 API. The `_protobuf.py` module adds the proto directory to `sys.path` and provides TypeAlias exports for use across the package.

## Key Invariants

- **Python 3.13+** only — use modern typing syntax
- **Async-first** — never block the event loop, always `await` gRPC calls
- **Facade pattern** — keep gRPC details isolated inside service modules
- **Strong typing** — use `TypeAlias` and satisfy `pyright` in basic mode
- **Backward compatibility** — additive changes only to the public API
- String keys are encoded as UTF-8 bytes at the service layer
