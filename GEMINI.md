# Gemini Context: etcd3aio

This document provides a comprehensive overview of the `etcd3aio` project for AI-assisted development.

## Project Overview

`etcd3aio` is an async Python client library for etcd v3. It uses `grpc.aio` for communication with the etcd cluster and provides a simple, high-level facade for interacting with etcd services such as Key-Value, Lease, and Watch.

**Core Technologies:**

- **Python 3.13+**
- **gRPC (`grpc.aio`)**: for async communication with etcd
- **etcd v3**

**Architecture:**

The project is structured as a standard Python library with source code under `src/etcd3aio`. It is divided into modules, each corresponding to a specific etcd service (e.g. `kv.py`, `lease.py`, `watch.py`). The main entry point is the `Etcd3Client` class in `src/etcd3aio/client.py`, which acts as a facade for all services.

The project uses `setuptools` for packaging, `pytest` for testing, `ruff` for linting and formatting, and `pyright` for static type checking.

## Build and Execution

### Local Development Setup

Requirements: `uv`

1. **Create and activate the virtual environment:**
    ```bash
    uv venv
    ```

2. **Install the project in editable mode with all dependencies:**
    ```bash
    uv sync --group dev
    ```

### Running an etcd Cluster

The project includes a `docker-compose.yaml` to easily run a local etcd cluster:

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### Running Quality Checks

```bash
uv run ruff format .        # format code
uv run ruff check --fix .   # lint with auto-fix
uv run pyright              # type check
uv run pytest               # run tests
```

## Development Conventions

- **Follow `CONTRIBUTING.md`**: adhere to the project's design principles and rules.
- **Small, focused changes**: keep pull requests small and focused on a single issue or feature.
- **Do not edit generated protobuf files**: files under `src/etcd3aio/proto` are generated and must not be edited manually.
- **Backward compatibility**: the public API must remain backward compatible.
- **Add tests**: all behaviour changes must be accompanied by tests.
- **Code style**: the project uses `ruff` for consistent code style; configuration is in `pyproject.toml`.
