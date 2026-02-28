# Project Contract

This contract defines mandatory rules for `aioetcd3`.

## 1. Product Contract

- Keep the client simple to use.
- Keep the facade pattern: `Etcd3Client` exposes services.
- Keep backward compatibility for public APIs unless explicitly planned.
- Prefer additive changes over breaking changes.

## 2. Runtime Contract

- Python 3.13+ only.
- Never block the asyncio event loop.
- Prefer async APIs end-to-end.
- Every gRPC call must be awaited when applicable.

## 3. Code Contract

- Keep gRPC details isolated in service/connection layers.
- Keep `Etcd3Client` lightweight (wiring/lifecycle only).
- Use strong, explicit typing.
- `pyproject.toml` defines the enforced Pyright mode.
- Use `TypeAlias` when it improves readability.
- Do not modify generated protobuf files under `src/aioetcd3/proto/`.

## 4. Reliability Contract

- Handle transient gRPC failures predictably.
- Keep retries simple and centralized.
- Ensure channels and streams are closed/cancelled correctly.

## 5. Quality Contract

- `ruff check .` must pass.
- `pyright` must pass.
- `pytest` must pass.
- New behavior should include focused tests.

## 6. Documentation Contract

- Keep docs short and current.
- Avoid duplicated guidance across files.
- Prefer one source of truth for rules (this file).

## 7. Change Checklist

Before merge, confirm:

- API remained simple.
- No unnecessary abstraction was introduced.
- Async behavior is preserved.
- Typing and tests are updated.
- Quality checks are green.
