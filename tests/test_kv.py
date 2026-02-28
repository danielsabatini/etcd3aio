from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from aioetcd3._protobuf import DeleteRangeResponse, PutResponse, RangeResponse
from aioetcd3.errors import EtcdTransientError
from aioetcd3.kv import KVService


class FakeRpcError(grpc.aio.AioRpcError):
    def __init__(self, status_code: grpc.StatusCode) -> None:
        self._status_code = status_code

    def code(self) -> grpc.StatusCode:
        return self._status_code


@pytest.mark.asyncio
async def test_put_encodes_string_inputs() -> None:
    stub = MagicMock()
    stub.Put = AsyncMock(return_value=PutResponse())
    stub.Range = AsyncMock(return_value=RangeResponse())
    stub.DeleteRange = AsyncMock(return_value=DeleteRangeResponse())

    with patch('aioetcd3.kv.KVStub', return_value=stub):
        service = KVService(channel=MagicMock())
        await service.put('key', 'value', lease=10, prev_kv=True)

    request = stub.Put.await_args.args[0]
    assert request.key == b'key'
    assert request.value == b'value'
    assert request.lease == 10
    assert request.prev_kv is True


@pytest.mark.asyncio
async def test_get_and_delete_accept_bytes_range_end() -> None:
    stub = MagicMock()
    stub.Put = AsyncMock(return_value=PutResponse())
    stub.Range = AsyncMock(return_value=RangeResponse())
    stub.DeleteRange = AsyncMock(return_value=DeleteRangeResponse())

    with patch('aioetcd3.kv.KVStub', return_value=stub):
        service = KVService(channel=MagicMock())
        await service.get(b'a', range_end=b'z', serializable=True, revision=4)
        await service.delete(b'a', range_end=b'z', prev_kv=True)

    get_request = stub.Range.await_args.args[0]
    delete_request = stub.DeleteRange.await_args.args[0]

    assert get_request.key == b'a'
    assert get_request.range_end == b'z'
    assert get_request.serializable is True
    assert get_request.revision == 4

    assert delete_request.key == b'a'
    assert delete_request.range_end == b'z'
    assert delete_request.prev_kv is True


@pytest.mark.asyncio
async def test_transient_error_retries_then_succeeds() -> None:
    stub = MagicMock()
    stub.Put = AsyncMock(
        side_effect=[
            FakeRpcError(grpc.StatusCode.UNAVAILABLE),
            PutResponse(),
        ]
    )
    stub.Range = AsyncMock(return_value=RangeResponse())
    stub.DeleteRange = AsyncMock(return_value=DeleteRangeResponse())

    with (
        patch('aioetcd3.kv.KVStub', return_value=stub),
        patch('aioetcd3.base.asyncio.sleep', new=AsyncMock()) as sleep_mock,
    ):
        service = KVService(channel=MagicMock(), max_attempts=2)
        await service.put('k', 'v')

    assert stub.Put.await_count == 2
    sleep_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_transient_error_raises_after_max_attempts() -> None:
    stub = MagicMock()
    stub.Put = AsyncMock(side_effect=FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED))
    stub.Range = AsyncMock(return_value=RangeResponse())
    stub.DeleteRange = AsyncMock(return_value=DeleteRangeResponse())

    with (
        patch('aioetcd3.kv.KVStub', return_value=stub),
        patch('aioetcd3.base.asyncio.sleep', new=AsyncMock()),
    ):
        service = KVService(channel=MagicMock(), max_attempts=2)
        with pytest.raises(EtcdTransientError, match='KV.Put failed after 2 attempts'):
            await service.put('k', 'v')
