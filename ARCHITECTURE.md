# Architecture

`aioetcd3` is organized as a thin facade over async gRPC services.

## Modules

- `client.py`: lifecycle and service wiring (`Etcd3Client`); `lock()` / `election()` factories
- `connections.py`: channel creation and connection options
- `base.py`: shared unary RPC retry helper
- `kv.py`: KV operations (put/get/delete/compact/txn)
- `lease.py`: lease operations (grant/revoke/time_to_live/keep_alive/leases)
- `maintenance.py`: cluster status and alarm management
- `concurrency.py`: distributed lock (`Lock`) and leader election (`Election`) built on KV + Lease
- `watch.py`: watch stream with basic reconnect behavior
- `_protobuf.py`: protobuf/stub aliases and import bootstrap
- `errors.py`: library-level exceptions

## Design Boundaries

- Facade stays small.
- gRPC internals stay out of user-facing API.
- Service modules should be cohesive and easy to test.
- Avoid deep inheritance and complex indirection.

## Request Flow

1. User calls facade service method.
2. Service builds protobuf request.
3. Service executes gRPC call.
4. Retry helper handles transient unary failures.
5. Response is returned as protobuf object.

## Non-Goals (for now)

- Custom DSLs around etcd operations
- Heavy plugin/interceptor framework
- Multiplexed watch manager for large-scale fan-out
