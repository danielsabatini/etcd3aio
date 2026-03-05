"""Fixtures for TLS / mTLS integration tests.

This conftest fully manages the TLS test environment:

  1. ``tls_certs``    — generates certificate files via ``docker/gen-certs.sh``
                        if any required file is missing.
  2. ``tls_cluster``  — starts the ``etcdtls1/2/3`` Docker Compose services
                        (idempotent: ``docker compose up -d`` is a no-op when
                        they are already running).
  3. ``etcd_tls``     — opens a session-scoped mTLS client, waiting up to 30 s
                        for the cluster to become healthy before giving up.
  4. ``cleanup``      — overrides the parent conftest ``cleanup`` so that the
                        plain-TCP ``etcd`` fixture is never pulled in for these
                        tests.

Run TLS tests only::

    pytest tests/integration/tls/ -v

Run everything (TLS cluster auto-started via Docker)::

    pytest
"""

from __future__ import annotations

import asyncio
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio

from etcd3aio import Etcd3Client

from .._helpers import delete_test_keys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
_DOCKER_DIR = _REPO_ROOT / 'docker'
_COMPOSE_FILE = _DOCKER_DIR / 'compose.yaml'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TLS_ENDPOINTS = ['localhost:5379', 'localhost:6379', 'localhost:7379']
TLS_SERVICES = ['etcdtls1', 'etcdtls2', 'etcdtls3']
TEST_PREFIX = 'test/'

_CERT_FILES = [
    'peer-ca.crt',
    'peer-cert.crt',
    'peer-key.key',
    'server-ca.crt',
    'server-cert.crt',
    'server-key.key',
    'client-cert.crt',
    'client-key.key',
]

_CLUSTER_WAIT_SECONDS = 30
_CLUSTER_POLL_INTERVAL = 5


# ---------------------------------------------------------------------------
# Fixture: certificate generation
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def tls_certs() -> None:
    """Generate TLS certificates if any required file is missing.

    Runs ``docker/gen-certs.sh`` (requires ``openssl`` on PATH).
    """
    missing = [f for f in _CERT_FILES if not (_DOCKER_DIR / f).exists()]
    if not missing:
        return

    try:
        subprocess.run(
            ['bash', str(_DOCKER_DIR / 'gen-certs.sh')],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        pytest.skip(f'Could not generate TLS certificates: {exc}')


# ---------------------------------------------------------------------------
# Fixture: Docker Compose cluster
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def tls_cluster(tls_certs: None) -> None:  # type: ignore[return]
    """Ensure the TLS etcd services are running via Docker Compose.

    Uses ``docker compose up -d`` which is idempotent — already-running
    services are left untouched.  The cluster is intentionally **not** stopped
    after the session so that re-runs stay fast; use
    ``docker compose -f docker/compose.yaml stop etcdtls1 etcdtls2 etcdtls3``
    to clean up manually.
    """
    try:
        subprocess.run(
            [
                'docker',
                'compose',
                '-f',
                str(_COMPOSE_FILE),
                'up',
                '-d',
                *TLS_SERVICES,
            ],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pytest.skip('docker not found — TLS cluster cannot be started')
    except subprocess.CalledProcessError as exc:
        pytest.skip(
            f'docker compose up failed — TLS cluster could not be started: {exc.stderr.decode()}'
        )


# ---------------------------------------------------------------------------
# Fixture: mTLS client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope='session')
async def etcd_tls(tls_cluster: None) -> AsyncGenerator[Etcd3Client, None]:
    """Yield a session-scoped mTLS Etcd3Client.

    Waits up to ``_CLUSTER_WAIT_SECONDS`` seconds for the TLS cluster to
    become healthy before skipping the session.
    """
    async with Etcd3Client(
        TLS_ENDPOINTS,
        ca_cert=(_DOCKER_DIR / 'server-ca.crt').read_bytes(),
        cert_chain=(_DOCKER_DIR / 'client-cert.crt').read_bytes(),
        cert_key=(_DOCKER_DIR / 'client-key.key').read_bytes(),
        tls_server_name='localhost',
    ) as client:
        deadline = _CLUSTER_WAIT_SECONDS
        last_exc: Exception | None = None
        while deadline > 0:
            try:
                await client.ping(timeout=5.0)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(_CLUSTER_POLL_INTERVAL)
                deadline -= _CLUSTER_POLL_INTERVAL

        if last_exc is not None:
            pytest.skip(
                f'TLS etcd cluster not reachable after {_CLUSTER_WAIT_SECONDS} s: {last_exc}'
            )

        yield client


# ---------------------------------------------------------------------------
# Fixture: per-test key cleanup (overrides parent conftest cleanup)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def cleanup(etcd_tls: Etcd3Client) -> AsyncGenerator[None, None]:
    """Delete all ``test/*`` keys after each TLS test.

    This fixture intentionally shadows the parent ``cleanup`` in
    ``tests/integration/conftest.py`` so that the plain-TCP ``etcd`` fixture
    is never pulled in for TLS tests.
    """
    yield
    await delete_test_keys(etcd_tls, TEST_PREFIX)
