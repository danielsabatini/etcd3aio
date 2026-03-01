from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from aioetcd3._protobuf import Compare, DeleteRangeResponse, PutResponse, RangeResponse, TxnResponse
from aioetcd3.errors import EtcdConnectionError, EtcdTransientError
from aioetcd3.kv import KVService


class FakeRpcError(grpc.aio.AioRpcError):
    def __init__(self, status_code: grpc.StatusCode, detail: str = '') -> None:
        self._status_code = status_code
        self._detail = detail

    def code(self) -> grpc.StatusCode:
        return self._status_code

    def details(self) -> str:
        return self._detail


@pytest.mark.asyncio
async def test_put_encodes_string_inputs() -> None:
    stub = _build_kv_stub()

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
    stub = _build_kv_stub()

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
    stub = _build_kv_stub()
    stub.Put = AsyncMock(
        side_effect=[
            FakeRpcError(grpc.StatusCode.UNAVAILABLE),
            PutResponse(),
        ]
    )

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
    stub = _build_kv_stub()
    stub.Put = AsyncMock(side_effect=FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED))

    with (
        patch('aioetcd3.kv.KVStub', return_value=stub),
        patch('aioetcd3.base.asyncio.sleep', new=AsyncMock()),
    ):
        service = KVService(channel=MagicMock(), max_attempts=2)
        with pytest.raises(EtcdTransientError, match='KV.Put failed after 2 attempts'):
            await service.put('k', 'v')


@pytest.mark.asyncio
async def test_unavailable_raises_connection_error_after_max_attempts() -> None:
    stub = _build_kv_stub()
    stub.Put = AsyncMock(side_effect=FakeRpcError(grpc.StatusCode.UNAVAILABLE))

    with (
        patch('aioetcd3.kv.KVStub', return_value=stub),
        patch('aioetcd3.base.asyncio.sleep', new=AsyncMock()),
    ):
        service = KVService(channel=MagicMock(), max_attempts=2)
        with pytest.raises(EtcdConnectionError, match='KV.Put failed after 2 attempts'):
            await service.put('k', 'v')


@pytest.mark.asyncio
async def test_error_message_includes_grpc_detail() -> None:
    stub = _build_kv_stub()
    stub.Put = AsyncMock(
        side_effect=FakeRpcError(grpc.StatusCode.UNAVAILABLE, 'etcdserver: no leader')
    )

    with (
        patch('aioetcd3.kv.KVStub', return_value=stub),
        patch('aioetcd3.base.asyncio.sleep', new=AsyncMock()),
    ):
        service = KVService(channel=MagicMock(), max_attempts=1)
        with pytest.raises(EtcdConnectionError, match='etcdserver: no leader'):
            await service.put('k', 'v')


@pytest.mark.asyncio
async def test_txn_calls_stub_with_compare_and_operations() -> None:
    stub = _build_kv_stub()
    stub.Txn = AsyncMock(return_value=TxnResponse(succeeded=True))

    with patch('aioetcd3.kv.KVStub', return_value=stub):
        service = KVService(channel=MagicMock())

        compare = [service.txn_compare_value('my-key', 'v1')]
        success = [service.txn_op_put('my-key', 'v2')]
        failure = [service.txn_op_put('my-key', 'fallback')]

        response = await service.txn(compare=compare, success=success, failure=failure)

    assert response.succeeded is True

    request = stub.Txn.await_args.args[0]
    assert len(request.compare) == 1
    assert len(request.success) == 1
    assert len(request.failure) == 1
    assert request.compare[0].target == Compare.VALUE
    assert request.compare[0].result == Compare.EQUAL
    assert request.compare[0].key == b'my-key'
    assert request.compare[0].value == b'v1'
    assert request.success[0].request_put.key == b'my-key'
    assert request.success[0].request_put.value == b'v2'


def test_txn_helper_builders() -> None:
    version_compare = KVService.txn_compare_version('version-key', 3)
    put_op = KVService.txn_op_put('a', 'b', lease=7, prev_kv=True)
    get_op = KVService.txn_op_get('a', range_end='z', serializable=True, revision=9)
    delete_op = KVService.txn_op_delete('a', range_end='z', prev_kv=True)

    assert version_compare.target == Compare.VERSION
    assert version_compare.result == Compare.EQUAL
    assert version_compare.key == b'version-key'
    assert version_compare.version == 3

    assert put_op.request_put.key == b'a'
    assert put_op.request_put.value == b'b'
    assert put_op.request_put.lease == 7
    assert put_op.request_put.prev_kv is True

    assert get_op.request_range.key == b'a'
    assert get_op.request_range.range_end == b'z'
    assert get_op.request_range.serializable is True
    assert get_op.request_range.revision == 9

    assert delete_op.request_delete_range.key == b'a'
    assert delete_op.request_delete_range.range_end == b'z'
    assert delete_op.request_delete_range.prev_kv is True


def _build_kv_stub() -> MagicMock:
    stub = MagicMock()
    stub.Put = AsyncMock(return_value=PutResponse())
    stub.Range = AsyncMock(return_value=RangeResponse())
    stub.DeleteRange = AsyncMock(return_value=DeleteRangeResponse())
    stub.Txn = AsyncMock(return_value=TxnResponse())
    return stub
