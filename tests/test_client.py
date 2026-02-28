from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioetcd3.client import Etcd3Client


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
