"""Shared fixtures for integration tests.

All tests in this package require a running etcd cluster.  If etcd is not
reachable at the configured endpoint the entire session is skipped
automatically — no manual flags required.

Run unit tests only:
    pytest tests/unit/

Run integration tests only (requires etcd):
    pytest tests/integration/

Run everything:
    pytest

Note: ``tests/integration/tls/conftest.py`` defines its own ``cleanup``
fixture with the same name that shadows this one for all TLS tests, so that
the plain-TCP ``etcd`` fixture is never pulled in when running TLS tests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from etcd3aio import Etcd3Client

from ._helpers import delete_test_keys

# Endpoint used by docker/compose.yaml (etcd1 maps host port 2379 → container 2379)
ETCD_ENDPOINT = 'localhost:2379'

# All test keys live under this prefix so cleanup is safe and targeted
TEST_PREFIX = 'test/'


# ---------------------------------------------------------------------------
# Session-scoped client — connects once, shared across all integration tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope='session')
async def etcd() -> Etcd3Client:  # type: ignore[return]
    """Yield a connected Etcd3Client; skip the entire session if etcd is down."""
    async with Etcd3Client([ETCD_ENDPOINT]) as client:
        try:
            await client.ping(timeout=3.0)
        except Exception as exc:
            pytest.skip(f'etcd not reachable at {ETCD_ENDPOINT}: {exc}')
        yield client


# ---------------------------------------------------------------------------
# Per-test cleanup — deletes all keys under TEST_PREFIX after every test
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def cleanup(etcd: Etcd3Client) -> None:  # type: ignore[return]
    """Delete all test/* keys after each test to guarantee isolation.

    Shadowed by ``tests/integration/tls/conftest.py::cleanup`` for TLS tests.
    """
    yield
    await delete_test_keys(etcd, TEST_PREFIX)
