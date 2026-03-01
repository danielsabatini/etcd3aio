# Gemini Context: aioetcd3

This document provides a comprehensive overview of the `aioetcd3` project, intended to be used as a context for AI-powered development assistance.

## Project Overview

`aioetcd3` is an asynchronous Python client library for etcd v3. It uses `grpc.aio` for communication with the etcd cluster. The library provides a simple, high-level facade for interacting with etcd services like Key-Value, Lease, and Watch.

**Key Technologies:**

*   **Python 3.13+**
*   **gRPC (`grpc.aio`)**: For asynchronous communication with etcd.
*   **etcd v3**

**Architecture:**

The project is structured as a standard Python library with the source code located in the `src/aioetcd3` directory. It is divided into modules, each corresponding to a specific etcd service (e.g., `kv.py`, `lease.py`, `watch.py`). The main entry point is the `Etcd3Client` class in `src/aioetcd3/client.py`, which acts as a facade for all the services.

The project uses `setuptools` for packaging, `pytest` for testing, `ruff` for linting and formatting, and `pyright` for static type checking.

## Building and Running

### Local Development Setup

To set up the local development environment, you need `uv`.

1.  **Create and activate the virtual environment:**
    ```bash
    uv venv
    ```

2.  **Install the project in editable mode with all dependencies:**
    ```bash
    uv pip install -e .
    ```

### Running an etcd Cluster

The project includes a `docker-compose.yaml` file to easily run a local etcd cluster.

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### Running Quality Checks

The following commands are used to ensure code quality:

*   **Format code:**
    ```bash
    .venv/bin/ruff format .
    ```

*   **Lint code:**
    ```bash
    .venv/bin/ruff check --fix .
    ```

*   **Type check:**
    ```bash
    .venv/bin/pyright
    ```

*   **Run tests:**
    ```bash
    .venv/bin/pytest
    ```

## Development Conventions

*   **Follow `CONTRACT.md`**: Adhere to the non-negotiable project contract.
*   **Small, focused changes**: Keep pull requests small and focused on a single issue or feature.
*   **Do not edit generated protobuf files**: The protobuf files in `src/aioetcd3/proto` are generated and should not be edited manually.
*   **Backward compatibility**: The public API should remain backward compatible.
*   **Add tests**: All behavior changes must be accompanied by tests.
*   **Coding Style**: The project uses `ruff` to enforce a consistent coding style. The configuration can be found in `pyproject.toml`.
