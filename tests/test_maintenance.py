from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioetcd3._protobuf import AlarmMember, AlarmResponse, StatusResponse
from aioetcd3.maintenance import AlarmType, MaintenanceService


@pytest.mark.asyncio
async def test_status_returns_response() -> None:
    response = StatusResponse(version='3.6.0', leader=1)

    stub = MagicMock()
    stub.Status = AsyncMock(return_value=response)

    with patch('aioetcd3.maintenance.MaintenanceStub', return_value=stub):
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

    with patch('aioetcd3.maintenance.MaintenanceStub', return_value=stub):
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

    with patch('aioetcd3.maintenance.MaintenanceStub', return_value=stub):
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

    with patch('aioetcd3.maintenance.MaintenanceStub', return_value=stub):
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

    with patch('aioetcd3.maintenance.MaintenanceStub', return_value=stub):
        service = MaintenanceService(channel=MagicMock())
        result = await service.alarms()

    assert len(result.alarms) == 1
    assert result.alarms[0].memberID == 7
    assert result.alarms[0].alarm == AlarmType.NOSPACE
