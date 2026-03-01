# Agent Instructions

This repository implements `etcd3aio`.

## Source of Truth

Read `CONTRIBUTING.md` first.

## Mandatory Rules

- Python 3.13+
- Async-first (never block the event loop)
- Use `await` on gRPC calls where applicable
- Maintain the facade pattern
- Keep the client lightweight
- Isolate gRPC logic inside service/connection modules
- Use strong typing and `TypeAlias` where useful
- Follow the Pyright mode configured in `pyproject.toml`
- `ruff format`, `ruff check --fix`, `pyright` and `pytest` must all pass
- Do not modify generated protobuf files
- Maintain backward compatibility

## References
- asyncio: https://docs.python.org/3/howto/asyncio.html
- A Conceptual Overview of asyncio: https://docs.python.org/3/library/asyncio-task.html#conceptual-overview
- Discovery protocol: https://etcd.io/docs/v3.6/dev-guide/discovery_protocol/
- Setting up a local cluster: https://etcd.io/docs/v3.6/dev-guide/local_cluster/
- Interacting with etcd: https://etcd.io/docs/v3.6/dev-guide/interacting_v3/
- Why gRPC gateway: https://etcd.io/docs/v3.6/dev-guide/api_grpc_gateway/
- gRPC naming and discovery: https://etcd.io/docs/v3.6/dev-guide/grpc_naming/
- System limits: https://etcd.io/docs/v3.6/dev-guide/limit/
- etcd features: https://etcd.io/docs/v3.6/dev-guide/features/
- API reference: https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/
- API reference — concurrency: https://etcd.io/docs/v3.6/dev-guide/api_concurrency_reference_v3/
