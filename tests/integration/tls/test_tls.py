"""Integration tests for TLS + mTLS connectivity.

Requires the ``etcdtls1/etcdtls2/etcdtls3`` cluster from ``docker/compose.yaml``.
The cluster is started automatically by the ``tls_cluster`` fixture in
``conftest.py`` (uses ``docker compose up -d``).  Certificates are generated
automatically by the ``tls_certs`` fixture if any file is missing.

All tests are skipped automatically when Docker is unavailable or the cluster
fails to become healthy within 30 s.
"""

from __future__ import annotations

import pytest

from etcd3aio import Etcd3Client

from .conftest import TLS_ENDPOINTS

_TEST_KEY = 'test/tls-ping'


@pytest.mark.asyncio
async def test_tls_ping(etcd_tls: Etcd3Client) -> None:
    """ping() succeeds over mTLS — cluster is healthy and writable."""
    await etcd_tls.ping()


@pytest.mark.asyncio
async def test_tls_put_and_get(etcd_tls: Etcd3Client) -> None:
    """Basic put/get round-trip over mTLS."""
    await etcd_tls.kv.put(_TEST_KEY, b'tls-ok')
    resp = await etcd_tls.kv.get(_TEST_KEY)
    assert len(resp.kvs) == 1
    assert resp.kvs[0].value == b'tls-ok'


@pytest.mark.asyncio
async def test_tls_member_list(etcd_tls: Etcd3Client) -> None:
    """Cluster API works over mTLS — all 3 members are visible."""
    resp = await etcd_tls.cluster.member_list()
    assert len(resp.members) == 3


@pytest.mark.asyncio
async def test_tls_no_plaintext_access(tls_cluster: None) -> None:
    """Connecting without TLS credentials to the TLS port must fail."""
    async with Etcd3Client([TLS_ENDPOINTS[0]]) as plain_client:
        with pytest.raises(Exception):
            await plain_client.ping(timeout=3.0)
