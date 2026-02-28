# Agent Instructions

This repository implements `aioetcd3`.

## Source of Truth

Read `CONTRACT.md` first.

## Hard Rules

- Python 3.13+
- Async-first (do not block event loop)
- Await gRPC calls when applicable
- Keep facade pattern
- Keep client lightweight
- Isolate gRPC logic in services/connections
- Use strong typing and `TypeAlias` when helpful
- Follow Pyright mode configured in `pyproject.toml`
- `ruff`, `pyright`, and `pytest` must pass
- Do not modify generated protobuf files
- Keep backwards compatibility

## References

- etcd API: https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/
- asyncio: https://docs.python.org/3/howto/asyncio.html
