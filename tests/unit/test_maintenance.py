from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from etcd3aio._protobuf import (
    AlarmMember,
    AlarmResponse,
    DefragmentResponse,
    DowngradeResponse,
    HashKVResponse,
    HashResponse,
    MoveLeaderResponse,
    SnapshotResponse,
    StatusResponse,
)
from etcd3aio.errors import EtcdConnectionError
from etcd3aio.maintenance import AlarmType, DowngradeAction, MaintenanceService


class FakeRpcError(grpc.aio.AioRpcError):
    def __init__(self, status_code: grpc.StatusCode = grpc.StatusCode.UNAVAILABLE, detail: str = '') -> None:
        self._status_code = status_code
        self._detail = detail

    def code(self) -> grpc.StatusCode:
        return self._status_code

    def details(self) -> str:
        return self._detail


@pytest.mark.asyncio
async def test_status_returns_response() -> None:
    response = StatusResponse(version='3.6.0', leader=1)

    stub = MagicMock()
    stub.Status = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.status()

    assert result is response
    stub.Status.assert_awaited_once()
    request = stub.Status.await_args.args[0]
    # StatusRequest has no fields; just verify it was called
    assert request is not None


@pytest.mark.asyncio
async def test_alarms_sends_get_action() -> None:
    response = AlarmResponse()

    stub = MagicMock()
    stub.Alarm = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.alarms()

    assert result is response
    request = stub.Alarm.await_args.args[0]
    assert request.action == 0  # AlarmRequest.GET


@pytest.mark.asyncio
async def test_alarm_deactivate_sends_deactivate_action() -> None:
    response = AlarmResponse()

    stub = MagicMock()
    stub.Alarm = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.alarm_deactivate(AlarmType.NOSPACE, member_id=42)

    assert result is response
    request = stub.Alarm.await_args.args[0]
    assert request.action == 2  # AlarmRequest.DEACTIVATE
    assert request.memberID == 42
    assert request.alarm == AlarmType.NOSPACE


@pytest.mark.asyncio
async def test_alarm_deactivate_defaults_broadcast_all() -> None:
    stub = MagicMock()
    stub.Alarm = AsyncMock(return_value=AlarmResponse())

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        await service.alarm_deactivate()

    request = stub.Alarm.await_args.args[0]
    assert request.memberID == 0


@pytest.mark.asyncio
async def test_alarms_response_contains_alarm_members() -> None:
    member = AlarmMember(memberID=7, alarm=1)  # 1 = NOSPACE
    response = AlarmResponse(alarms=[member])

    stub = MagicMock()
    stub.Alarm = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.alarms()

    assert len(result.alarms) == 1
    assert result.alarms[0].memberID == 7
    assert result.alarms[0].alarm == AlarmType.NOSPACE


# ---------------------------------------------------------------------------
# defragment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_defragment_returns_response() -> None:
    response = DefragmentResponse()

    stub = MagicMock()
    stub.Defragment = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.defragment()

    assert result is response
    stub.Defragment.assert_awaited_once()
    request = stub.Defragment.await_args.args[0]
    assert request is not None  # DefragmentRequest has no fields


# ---------------------------------------------------------------------------
# hash_kv
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hash_kv_sends_revision() -> None:
    response = HashKVResponse(hash=0xDEADBEEF, compact_revision=5, hash_revision=10)

    stub = MagicMock()
    stub.HashKV = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.hash_kv(revision=10)

    assert result is response
    assert result.hash == 0xDEADBEEF
    request = stub.HashKV.await_args.args[0]
    assert request.revision == 10


@pytest.mark.asyncio
async def test_hash_kv_defaults_to_latest() -> None:
    stub = MagicMock()
    stub.HashKV = AsyncMock(return_value=HashKVResponse())

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        await service.hash_kv()

    request = stub.HashKV.await_args.args[0]
    assert request.revision == 0


# ---------------------------------------------------------------------------
# move_leader
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_move_leader_sends_target_id() -> None:
    response = MoveLeaderResponse()

    stub = MagicMock()
    stub.MoveLeader = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.move_leader(target_id=42)

    assert result is response
    request = stub.MoveLeader.await_args.args[0]
    assert request.targetID == 42


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_yields_blob_chunks() -> None:
    chunks = [b'chunk-one', b'chunk-two', b'chunk-three']

    async def _fake_call(*args: object, **kwargs: object) -> AsyncGenerator[SnapshotResponse, None]:
        for data in chunks:
            yield SnapshotResponse(blob=data)

    stub = MagicMock()
    stub.Snapshot = _fake_call

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        received: list[bytes] = []
        async for chunk in service.snapshot():
            received.append(chunk)

    assert received == chunks


@pytest.mark.asyncio
async def test_snapshot_empty_stream_yields_nothing() -> None:
    async def _fake_call(*args: object, **kwargs: object) -> AsyncGenerator[SnapshotResponse, None]:
        for _ in ():
            yield SnapshotResponse()

    stub = MagicMock()
    stub.Snapshot = _fake_call

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        received: list[bytes] = []
        async for chunk in service.snapshot():
            received.append(chunk)

    assert received == []


@pytest.mark.asyncio
async def test_snapshot_retries_on_transient_error_before_yield() -> None:
    """UNAVAILABLE before any bytes are yielded → retry transparently."""
    chunks = [b'chunk-one', b'chunk-two']
    calls: list[int] = []

    async def _good_gen() -> AsyncGenerator[SnapshotResponse, None]:
        for data in chunks:
            yield SnapshotResponse(blob=data)

    def _fake_snapshot(*args: object, **kwargs: object) -> object:
        calls.append(1)
        if len(calls) == 1:
            raise FakeRpcError(grpc.StatusCode.UNAVAILABLE)
        return _good_gen()

    stub = MagicMock()
    stub.Snapshot = _fake_snapshot

    with (
        patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub),
        patch('etcd3aio.maintenance.asyncio.sleep', new=AsyncMock()),
    ):
        service = MaintenanceService(channel=MagicMock(), max_attempts=2)
        received: list[bytes] = []
        async for chunk in service.snapshot():
            received.append(chunk)

    assert received == chunks
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_snapshot_surfaces_error_immediately_after_yielding_bytes() -> None:
    """UNAVAILABLE after bytes have been yielded → error surfaced immediately, no retry."""

    async def _partial_then_fail(*args: object, **kwargs: object) -> AsyncGenerator[SnapshotResponse, None]:
        yield SnapshotResponse(blob=b'partial')
        raise FakeRpcError(grpc.StatusCode.UNAVAILABLE)

    stub = MagicMock()
    stub.Snapshot = _partial_then_fail

    with (
        patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub),
        patch('etcd3aio.maintenance.asyncio.sleep', new=AsyncMock()) as sleep_mock,
    ):
        service = MaintenanceService(channel=MagicMock(), max_attempts=3)
        received: list[bytes] = []
        with pytest.raises(EtcdConnectionError):
            async for chunk in service.snapshot():
                received.append(chunk)

    assert received == [b'partial']
    sleep_mock.assert_not_awaited()  # no retry was attempted


@pytest.mark.asyncio
async def test_snapshot_raises_connection_error_after_max_attempts() -> None:
    """UNAVAILABLE on every attempt (no bytes) → EtcdConnectionError after exhaustion."""

    def _always_fail(*args: object, **kwargs: object) -> object:
        raise FakeRpcError(grpc.StatusCode.UNAVAILABLE)

    stub = MagicMock()
    stub.Snapshot = _always_fail

    with (
        patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub),
        patch('etcd3aio.maintenance.asyncio.sleep', new=AsyncMock()),
    ):
        service = MaintenanceService(channel=MagicMock(), max_attempts=2)
        with pytest.raises(EtcdConnectionError, match='Maintenance.Snapshot failed after 2 attempts'):
            async for _ in service.snapshot():
                pass


# ---------------------------------------------------------------------------
# hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hash_returns_response() -> None:
    response = HashResponse(hash=0xCAFEBABE)

    stub = MagicMock()
    stub.Hash = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.hash()

    assert result is response
    assert result.hash == 0xCAFEBABE
    stub.Hash.assert_awaited_once()
    request = stub.Hash.await_args.args[0]
    assert request is not None  # HashRequest has no fields


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_downgrade_validate_sends_correct_request() -> None:
    response = DowngradeResponse(version='3.5.0')

    stub = MagicMock()
    stub.Downgrade = AsyncMock(return_value=response)

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.downgrade(DowngradeAction.VALIDATE, '3.5.0')

    assert result is response
    request = stub.Downgrade.await_args.args[0]
    assert request.action == 0  # VALIDATE
    assert request.version == '3.5.0'


@pytest.mark.asyncio
async def test_downgrade_enable_sends_correct_request() -> None:
    stub = MagicMock()
    stub.Downgrade = AsyncMock(return_value=DowngradeResponse(version='3.5.0'))

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        await service.downgrade(DowngradeAction.ENABLE, '3.5.0')

    request = stub.Downgrade.await_args.args[0]
    assert request.action == 1  # ENABLE
    assert request.version == '3.5.0'


@pytest.mark.asyncio
async def test_downgrade_cancel_sends_correct_request() -> None:
    stub = MagicMock()
    stub.Downgrade = AsyncMock(return_value=DowngradeResponse(version='3.5.0'))

    with patch('etcd3aio.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        await service.downgrade(DowngradeAction.CANCEL, '3.5.0')

    request = stub.Downgrade.await_args.args[0]
    assert request.action == 2  # CANCEL
    assert request.version == '3.5.0'
