# Project Contract

This contract defines the mandatory rules for `etcd3aio`.

## 1. Product Contract

- Keep the code simple to use.
- Keep the code simple to maintain.
- Maintain the facade pattern: `Etcd3Client` exposes the services.
- Maintain backward compatibility on public APIs, except when explicitly planned.
- Prefer additive changes over breaking ones.

## 2. Execution Contract

- Python 3.13+ only.
- Never block the asyncio event loop.
- Prefer async APIs end-to-end.
- All gRPC calls must be awaited with `await` where applicable.

## 3. Code Contract

- Use simple but modern coding style.
- Keep gRPC details isolated inside the service/connection layers.
- Keep `Etcd3Client` lightweight (only wiring and lifecycle).
- Use strong, explicit typing.
- `pyproject.toml` defines the enforced Pyright mode.
- Use `TypeAlias` where it improves readability.
- Do not modify generated protobuf files under `src/etcd3aio/proto/`.

## 4. Reliability Contract

- Handle transient gRPC failures predictably.
- Keep retries simple and centralised.
- Ensure channels and streams are properly closed/cancelled.

## 5. Quality Contract

- `ruff format .` must pass (auto-formats code).
- `ruff check --fix .` must pass (linting).
- `pyright` must pass.
- `pytest` must pass.
- New behaviours must include focused tests.

## 6. Documentation Contract

- Keep documentation short and up to date.
- Avoid duplicating guidance across files.
- `CONTRIBUTING.md` is the single source of truth for actionable code and process rules.
- After any change, keep cross-references consistent: module tables in `ARCHITECTURE.md`, and `README.md` must match the implementation; `ROADMAP.md` status must reflect what is done; `CHANGELOG.md` must record each versioned change.
- Keep `README.md` complete and accessible to beginners, intermediate users, advanced users, and contributors.

## 7. Change Checklist

Before merging, confirm:

- The API remained simple.
- No unnecessary abstractions were introduced.
- Async behaviour was preserved.
- Typing and tests were updated.
- Quality checks are green.
- All `.md` files were reviewed for consistency: module tables, ROADMAP status and cross-references match the current implementation.

## 8. Library Examples Guidelines

- All examples must be stored in the `examples/` directory.
- For each library module, a dedicated example must exist following the naming pattern: `<module>_example.py`
  - It must demonstrate the module's main features directly and objectively.
- A complete integrated example must exist: `full_example.py`
  - It must demonstrate integrated library usage covering the full workflow across different modules.
- An introductory example must also exist: `get_started_example.py`
  - It must contain the most common use cases, serving as the entry point for new users.
- Examples must:
  - Cover all relevant public features of each module.
  - Demonstrate API usage in the simplest and most direct way possible.
  - Avoid unnecessary complexity, excessive mocks, or external dependencies unless essential.
  - Be independently executable.
- Each example must prioritise clarity and didactic value, allowing users to quickly understand how to use the module or feature.

## 9. Logging

Follows the [Python logging HOWTO for libraries](https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library):

- The library never configures handlers, formatters, or log levels — that is the application's responsibility.
- `__init__.py` attaches a `NullHandler` to the root package logger.
- Each module that logs uses `logging.getLogger(__name__)`.
- All log calls use `%`-style lazy formatting (never f-strings or `.format()`).
- Examples (application code) must call `logging.basicConfig()` so library output is visible.