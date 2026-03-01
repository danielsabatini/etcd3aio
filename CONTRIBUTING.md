# Contributing

## Local Setup

```bash
uv venv
uv pip install -e .
```

## Run Quality Checks

```bash
.venv/bin/ruff format .
.venv/bin/ruff check --fix .
.venv/bin/pyright
.venv/bin/pytest
```

## Rules

- Follow `CONTRACT.md`.
- Keep changes small and focused.
- Do not edit generated protobuf files.
- Keep public API backward compatible.
- Add tests for behavior changes.
