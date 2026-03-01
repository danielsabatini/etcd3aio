from __future__ import annotations

from enum import IntEnum

import grpc.aio

from ._protobuf import (
    AlarmRequest,
    AlarmResponse,
    MaintenanceStub,
    StatusRequest,
    StatusResponse,
)
from .base import BaseService


class AlarmType(IntEnum):
    """Alarm types reported by etcd cluster members."""

    NONE = 0
    NOSPACE = 1
    CORRUPT = 2


class MaintenanceService(BaseService):
    """Maintenance facade: cluster status and alarm management."""

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = MaintenanceStub(channel)

    async def status(self, *, timeout: float | None = None) -> StatusResponse:
        """Return the status of the cluster member this client is connected to.

        Key fields:
        - ``leader``: member ID of the current leader (0 = no leader / no quorum).
        - ``errors``: list of error strings reported by the member.
        - ``db_size``: total backend database size in bytes.
        - ``db_size_in_use``: bytes actually in use (after compaction).
        - ``version``: etcd server version string.
        """
        return await self._rpc(
            self._stub.Status, StatusRequest(), operation='Maintenance.Status', timeout=timeout
        )

    async def alarms(self, *, timeout: float | None = None) -> AlarmResponse:
        """List all active alarms in the cluster.

        Returns an :class:`AlarmResponse` whose ``alarms`` field is a list of
        :class:`AlarmMember` objects, each with ``memberID`` and ``alarm``
        (one of :class:`AlarmType`).
        """
        request = AlarmRequest(
            action=AlarmRequest.GET,
            memberID=0,
            alarm=0,
        )
        return await self._rpc(
            self._stub.Alarm, request, operation='Maintenance.Alarm', timeout=timeout
        )

    async def alarm_deactivate(
        self,
        alarm_type: AlarmType = AlarmType.NONE,
        *,
        member_id: int = 0,
        timeout: float | None = None,
    ) -> AlarmResponse:
        """Deactivate an alarm on one or all cluster members.

        Args:
            alarm_type: The alarm to clear. Defaults to ``AlarmType.NONE``
                which clears all alarm types.
            member_id: Target member ID. ``0`` (default) broadcasts to all
                members.
        """
        request = AlarmRequest(
            action=AlarmRequest.DEACTIVATE,
            memberID=member_id,
            alarm=int(alarm_type),
        )
        return await self._rpc(
            self._stub.Alarm, request, operation='Maintenance.Alarm', timeout=timeout
        )
