from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioetcd3.client import Etcd3Client
from aioetcd3.errors import EtcdConnectionError


@pytest.mark.asyncio
async def test_connect_initializes_services() -> None:
    channel = AsyncMock()
    get_channel_mock = AsyncMock(return_value=channel)

    kv_service = MagicMock()
    lease_service = MagicMock()
    watch_service = MagicMock()

    with (
        patch('aioetcd3.client.ConnectionManager.get_channel', new=get_channel_mock),
        patch('aioetcd3.client.KVService', return_value=kv_service),
        patch('aioetcd3.client.LeaseService', return_value=lease_service),
        patch('aioetcd3.client.WatchService', return_value=watch_service),
    ):
        client = Etcd3Client(['localhost:2379'])
        await client.connect()

        assert client.kv is kv_service
        assert client.lease is lease_service
        assert client.watch is watch_service

        await client.close()

    channel.close.assert_awaited_once()
    assert client.kv is None
    assert client.lease is None
    assert client.watch is None


@pytest.mark.asyncio
async def test_async_context_manager_lifecycle() -> None:
    channel = AsyncMock()
    get_channel_mock = AsyncMock(return_value=channel)

    kv_service = MagicMock()
    lease_service = MagicMock()
    watch_service = MagicMock()

    with (
        patch('aioetcd3.client.ConnectionManager.get_channel', new=get_channel_mock),
        patch('aioetcd3.client.KVService', return_value=kv_service),
        patch('aioetcd3.client.LeaseService', return_value=lease_service),
        patch('aioetcd3.client.WatchService', return_value=watch_service),
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
        patch('aioetcd3.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())),
        patch('aioetcd3.client.KVService', return_value=kv),
        patch('aioetcd3.client.LeaseService', return_value=lease),
        patch('aioetcd3.client.WatchService', return_value=MagicMock()),
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
        patch('aioetcd3.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())),
        patch('aioetcd3.client.KVService', return_value=kv),
        patch('aioetcd3.client.LeaseService', return_value=lease),
        patch('aioetcd3.client.WatchService', return_value=MagicMock()),
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
        patch('aioetcd3.client.ConnectionManager.get_channel', new=AsyncMock(return_value=AsyncMock())),
        patch('aioetcd3.client.KVService', return_value=kv),
        patch('aioetcd3.client.LeaseService', return_value=lease),
        patch('aioetcd3.client.WatchService', return_value=MagicMock()),
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
