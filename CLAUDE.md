# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**aioetcd3** is an async Python client for etcd v3 using `grpc.aio`. It follows a strict **facade pattern** — a thin, well-typed wrapper over generated gRPC stubs with centralized retry logic.

Non-negotiable rules are documented in [CONTRACT.md](CONTRACT.md). Architectural boundaries are in [ARCHITECTURE.md](ARCHITECTURE.md).

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

# Type check
pyright

# Start local etcd cluster (3-node)
docker compose -f docker/docker-compose.yaml up -d
```

## Architecture

### Module Responsibilities

| Module | Role |
|---|---|
| `client.py` | `Etcd3Client` — facade, lifecycle, wires services together |
| `connections.py` | Channel creation, TLS, round-robin load balancing |
| `base.py` | `BaseService` — shared unary RPC retry/backoff logic |
| `kv.py` | `KVService` — put/get/delete/compact/txn operations |
| `lease.py` | `LeaseService` — grant/revoke/leases/keep_alive |
| `maintenance.py` | `MaintenanceService` — status/alarms/alarm_deactivate; `AlarmType` enum |
| `auth.py` | `AuthService` — auth_status/authenticate for developer-facing auth |
| `concurrency.py` | `Lock`, `Election` — distributed lock and leader election built on KV + Lease |
| `watch.py` | `WatchService` — async iterator with auto-reconnect |
| `errors.py` | `EtcdError`, `EtcdConnectionError`, `EtcdTransientError`, `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError` |
| `_protobuf.py` | Centralizes all protobuf imports and TypeAlias definitions |

### Request Flow

```
User call → Service method → Protobuf request object → BaseService._rpc() → gRPC stub → Response
```

Transient errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`) are retried with exponential backoff (up to 3 attempts by default, 0.05s → 1.0s max). On exhaustion: `UNAVAILABLE` raises `EtcdConnectionError`; `DEADLINE_EXCEEDED` raises `EtcdTransientError`. Non-retried gRPC errors are also mapped: `UNAUTHENTICATED` → `EtcdUnauthenticatedError`; `PERMISSION_DENIED` → `EtcdPermissionDeniedError`.

Watch streams track `next_revision` for safe reconnection after transient failures.

### Protobuf Layer

All generated proto stubs live in `src/aioetcd3/proto/`. **Never modify these files** — they are generated from the etcd v3 API. The `_protobuf.py` module adds the proto directory to `sys.path` and provides TypeAlias exports for use throughout the package.

## Key Invariants

- **Python 3.13+** only — use modern typing syntax
- **Async-first** — never block the event loop, always `await` gRPC calls
- **Facade pattern** — keep gRPC internals isolated inside service modules
- **Strong typing** — use `TypeAlias` and satisfy `pyright` in basic mode
- **Backward compatible** — only additive changes to public API
- String keys are UTF-8 encoded to bytes at the service layer
