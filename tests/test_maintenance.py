from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from etcd3aio._protobuf import (
    AlarmMember,
    AlarmResponse,
    DefragmentResponse,
    HashKVResponse,
    MoveLeaderResponse,
    SnapshotResponse,
    StatusResponse,
)
from etcd3aio.maintenance import AlarmType, MaintenanceService


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
