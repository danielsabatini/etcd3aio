# Contributing

## Local Setup

```bash
uv venv
uv sync --group dev
```

## Quality Checks

All checks must pass before merging:

```bash
uv run ruff format .        # auto-format
uv run ruff check --fix .   # lint with auto-fix
uv run pyright              # type check
uv run pytest               # tests
```

## Design Principles

- **Facade pattern** — `Etcd3Client` wires services; keep gRPC details isolated inside service modules.
- **Async-first** — never block the event loop; all gRPC calls must be `await`ed.
- **Python 3.13+** — use modern syntax; no compatibility shims for older versions.
- **Strong typing** — all public API must be fully annotated and satisfy `pyright` in basic mode.
- **Backward compatibility** — prefer additive changes; breaking changes require explicit planning.
- **Lightweight client** — no hidden magic, no heavy frameworks, no unnecessary abstractions.

## Code Rules

- Keep the `Etcd3Client` thin: only lifecycle wiring and factory methods.
- Do not modify generated protobuf files under `src/etcd3aio/proto/`.
- Use `TypeAlias` from `_protobuf.py` instead of importing proto types directly.
- Handle transient gRPC errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`) through `BaseService._rpc()` — do not add per-method retry logic.
- Ensure channels and streams are properly closed/cancelled on exit.

## PR Checklist

Before opening a pull request, confirm:

- [ ] Public API remains simple and consistent with existing patterns
- [ ] No unnecessary abstractions introduced
- [ ] Async behaviour preserved (no blocking calls)
- [ ] Typing and tests updated to cover new behaviour
- [ ] All quality checks are green (`ruff`, `pyright`, `pytest`)
- [ ] Relevant `.md` files updated (module tables, ROADMAP status, CHANGELOG)

## Examples

Each module has a dedicated `examples/<module>_example.py`. When adding or changing public API:

- Update the corresponding example to cover the new feature.
- Keep examples independently executable against a real etcd cluster (no mocks).
- Use `examples/get_started_example.py` for the most common use cases.
- Use `examples/full_example.py` for integrated end-to-end flows.
