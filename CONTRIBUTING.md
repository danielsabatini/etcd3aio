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
- **Python 3.11+** — use modern syntax; no compatibility shims for older versions.
- **Strong typing** — all public API must be fully annotated and satisfy `pyright` in basic mode.
- **Backward compatibility** — prefer additive changes; breaking changes require explicit planning.
- **Lightweight client** — no hidden magic, no heavy frameworks, no unnecessary abstractions.

## Code Rules

- Keep the `Etcd3Client` thin: only lifecycle wiring and factory methods.
- Do not modify generated protobuf files under `src/etcd3aio/proto/`.
- Use `TypeAlias` from `_protobuf.py` instead of importing proto types directly.
- Handle transient gRPC errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`) through `BaseService._rpc()` — do not add per-method retry logic.
- Ensure channels and streams are properly closed/cancelled on exit.

## Docstrings

All public API must follow Google-style docstrings:

- **Classes**: class-level docstring describing purpose, with a usage example for non-trivial classes.  `__init__` does not need its own docstring.
- **Public methods**: one-line summary + `Args:` for non-obvious parameters + `Returns:` with key response fields + `Raises:` for documented exceptions.
- **Private methods** (`_`-prefixed): a one-liner is enough.
- **Protocol methods** (`__aenter__`, `__aexit__`): no docstring required.

Style reference:

```python
async def put(self, key: str, value: str, *, timeout: float | None = None) -> PutResponse:
    """Store *key* with the given *value*.

    Args:
        key: Key name (UTF-8 string or bytes).
        value: Value to store (UTF-8 string or bytes).
        timeout: Per-call deadline in seconds (``None`` = no deadline).

    Returns:
        ``PutResponse`` — ``prev_kv`` is populated only when ``prev_kv=True``.
    """
```

## PR Checklist

Before opening a pull request, confirm:

- [ ] Public API remains simple and consistent with existing patterns
- [ ] No unnecessary abstractions introduced
- [ ] Async behaviour preserved (no blocking calls)
- [ ] Typing and tests updated to cover new behaviour
- [ ] All quality checks are green (`ruff`, `pyright`, `pytest`)
- [ ] Relevant `.md` files updated (module tables, ROADMAP status, CHANGELOG)

## Logging

This library follows the [Python logging HOWTO for libraries](https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library):

- Each module that emits log records must declare `_log = logging.getLogger(__name__)`.
- `src/etcd3aio/__init__.py` attaches a `NullHandler` to the root package logger — no other handler, formatter, or level is ever set by the library.
- All log calls must use `%`-style lazy formatting: `_log.warning('msg %s', value)`, never f-strings or `.format()`.
- Level guidelines: `WARNING` for recoverable background failures (keepalive, reconnect, token refresh); `ERROR` for unrecoverable background failures.
- Examples are application code and must configure logging so library output is visible to users:
  ```python
  logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')
  ```

## Examples

Each module has a dedicated `examples/<module>_example.py`. When adding or changing public API:

- Update the corresponding example to cover the new feature.
- Keep examples independently executable against a real etcd cluster (no mocks).
- Use `examples/get_started_example.py` for the most common use cases.
- Use `examples/full_example.py` for integrated end-to-end flows.
