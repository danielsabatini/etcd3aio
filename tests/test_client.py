from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from etcd3aio.auth import TokenRefresher
from etcd3aio.client import Etcd3Client
from etcd3aio.errors import EtcdConnectionError


@pytest.mark.asyncio
async def test_connect_initializes_services() -> None:
    channel = AsyncMock()
    get_channel_mock = AsyncMock(return_value=channel)

    auth_service = MagicMock()
    kv_service = MagicMock()
    lease_service = MagicMock()
    watch_service = MagicMock()
    maintenance_service = MagicMock()

    with (
        patch('etcd3aio.client.ConnectionManager.get_channel', new=get_channel_mock),
        patch('etcd3aio.client.AuthService', return_value=auth_service),
        patch('etcd3aio.client.KVService', return_value=kv_service),
        patch('etcd3aio.client.LeaseService', return_value=lease_service),
        patch('etcd3aio.client.MaintenanceService', return_value=maintenance_service),
        patch('etcd3aio.client.WatchService', return_value=watch_service),
    ):
        client = Etcd3Client(['localhost:2379'])
        await client.connect()

        assert client.auth is auth_service
        assert client.kv is kv_service
        assert client.lease is lease_service
        assert client.maintenance is maintenance_service
        assert client.watch is watch_service

        await client.close()

    channel.close.assert_awaited_once()
    assert client.auth is None
    assert client.kv is None
    assert client.lease is None
    assert client.maintenance is None
    assert client.watch is None


@pytest.mark.asyncio
async def test_async_context_manager_lifecycle() -> None:
    channel = AsyncMock()
    get_channel_mock = AsyncMock(return_value=channel)

    kv_service = MagicMock()
    lease_service = MagicMock()
    watch_service = MagicMock()

    with (
        patch('etcd3aio.client.ConnectionManager.get_channel', new=get_channel_mock),
        patch('etcd3aio.client.AuthService', return_value=MagicMock()),
        patch('etcd3aio.client.KVService', return_value=kv_service),
        patch('etcd3aio.client.LeaseService', return_value=lease_service),
        patch('etcd3aio.client.MaintenanceService', return_value=MagicMock()),
        patch('etcd3aio.client.WatchService', return_value=watch_service),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            assert client.kv is kv_service
            assert client.lease is lease_service
            assert client.watch is watch_service

    channel.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_ping_performs_read_and_write_check() -> None:
    kv = MagicMock()
    kv.get = AsyncMock(return_value=MagicMock())
    kv.put = AsyncMock(return_value=MagicMock())
    lease = MagicMock()
    lease.grant = AsyncMock(return_value=MagicMock(ID=42))
    lease.revoke = AsyncMock(return_value=MagicMock())

    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=MagicMock()),
        patch('etcd3aio.client.KVService', return_value=kv),
        patch('etcd3aio.client.LeaseService', return_value=lease),
        patch('etcd3aio.client.MaintenanceService', return_value=MagicMock()),
        patch('etcd3aio.client.WatchService', return_value=MagicMock()),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            await client.ping()

    kv.get.assert_awaited_once()
    lease.grant.assert_awaited_once_with(ttl=5)
    kv.put.assert_awaited_once()
    lease.revoke.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_ping_read_only_skips_write() -> None:
    kv = MagicMock()
    kv.get = AsyncMock(return_value=MagicMock())
    lease = MagicMock()
    lease.grant = AsyncMock()

    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=MagicMock()),
        patch('etcd3aio.client.KVService', return_value=kv),
        patch('etcd3aio.client.LeaseService', return_value=lease),
        patch('etcd3aio.client.MaintenanceService', return_value=MagicMock()),
        patch('etcd3aio.client.WatchService', return_value=MagicMock()),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            await client.ping(write_check=False)

    kv.get.assert_awaited_once()
    lease.grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_ping_revoke_suppressed_on_write_failure() -> None:
    kv = MagicMock()
    kv.get = AsyncMock(return_value=MagicMock())
    kv.put = AsyncMock(side_effect=EtcdConnectionError('no leader'))
    lease = MagicMock()
    lease.grant = AsyncMock(return_value=MagicMock(ID=42))
    lease.revoke = AsyncMock(side_effect=EtcdConnectionError('no leader'))

    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=MagicMock()),
        patch('etcd3aio.client.KVService', return_value=kv),
        patch('etcd3aio.client.LeaseService', return_value=lease),
        patch('etcd3aio.client.MaintenanceService', return_value=MagicMock()),
        patch('etcd3aio.client.WatchService', return_value=MagicMock()),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            with pytest.raises(EtcdConnectionError):
                await client.ping()

    lease.revoke.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_ping_raises_when_not_connected() -> None:
    client = Etcd3Client(['localhost:2379'])
    with pytest.raises(RuntimeError, match='not connected'):
        await client.ping()


# ---------------------------------------------------------------------------
# Token injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_param_applies_to_all_services_on_connect() -> None:
    """token= passed to constructor is propagated to all services after connect."""
    auth_service = MagicMock()
    kv_service = MagicMock()
    lease_service = MagicMock()
    maintenance_service = MagicMock()
    watch_service = MagicMock()

    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=auth_service),
        patch('etcd3aio.client.KVService', return_value=kv_service),
        patch('etcd3aio.client.LeaseService', return_value=lease_service),
        patch('etcd3aio.client.MaintenanceService', return_value=maintenance_service),
        patch('etcd3aio.client.WatchService', return_value=watch_service),
    ):
        async with Etcd3Client(['localhost:2379'], token='my-token'):
            pass

    for svc in (auth_service, kv_service, lease_service, maintenance_service, watch_service):
        svc.set_token.assert_called_once_with('my-token')


@pytest.mark.asyncio
async def test_set_token_propagates_to_all_active_services() -> None:
    """set_token() after connect() calls set_token() on every service."""
    auth_service = MagicMock()
    kv_service = MagicMock()
    lease_service = MagicMock()
    maintenance_service = MagicMock()
    watch_service = MagicMock()

    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=auth_service),
        patch('etcd3aio.client.KVService', return_value=kv_service),
        patch('etcd3aio.client.LeaseService', return_value=lease_service),
        patch('etcd3aio.client.MaintenanceService', return_value=maintenance_service),
        patch('etcd3aio.client.WatchService', return_value=watch_service),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            client.set_token('runtime-token')

    for svc in (auth_service, kv_service, lease_service, maintenance_service, watch_service):
        svc.set_token.assert_called_with('runtime-token')


# ---------------------------------------------------------------------------
# token_refresher factory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_refresher_factory_returns_refresher() -> None:
    """client.token_refresher() returns a TokenRefresher bound to the auth service."""
    with (
        patch(
            'etcd3aio.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())
        ),
        patch('etcd3aio.client.AuthService', return_value=MagicMock()),
        patch('etcd3aio.client.KVService', return_value=MagicMock()),
        patch('etcd3aio.client.LeaseService', return_value=MagicMock()),
        patch('etcd3aio.client.MaintenanceService', return_value=MagicMock()),
        patch('etcd3aio.client.WatchService', return_value=MagicMock()),
    ):
        async with Etcd3Client(['localhost:2379']) as client:
            refresher = client.token_refresher('alice', 'secret', interval=120)

    assert isinstance(refresher, TokenRefresher)
    assert refresher._name == 'alice'
    assert refresher._password == 'secret'
    assert refresher._interval == 120


def test_token_refresher_factory_raises_when_not_connected() -> None:
    client = Etcd3Client(['localhost:2379'])
    with pytest.raises(RuntimeError, match='not connected'):
        client.token_refresher('alice', 'secret')
