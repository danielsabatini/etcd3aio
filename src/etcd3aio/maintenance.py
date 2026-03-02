from __future__ import annotations

from collections.abc import AsyncGenerator
from enum import IntEnum

import grpc.aio

from ._protobuf import (
    AlarmRequest,
    AlarmResponse,
    DefragmentRequest,
    DefragmentResponse,
    HashKVRequest,
    HashKVResponse,
    MaintenanceStub,
    MoveLeaderRequest,
    MoveLeaderResponse,
    SnapshotRequest,
    SnapshotResponse,
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
    """Maintenance facade: cluster status, alarm management, defragmentation,
    consistency hashing, snapshot streaming and leader transfer."""

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

    async def defragment(self, *, timeout: float | None = None) -> DefragmentResponse:
        """Defragment the backend database of the member this client is connected to.

        Reclaims disk space that was freed by previous compactions.  The call
        blocks until defragmentation completes on the target member.  Only one
        defragmentation should run in the cluster at a time to avoid impacting
        availability.
        """
        return await self._rpc(
            self._stub.Defragment,
            DefragmentRequest(),
            operation='Maintenance.Defragment',
            timeout=timeout,
        )

    async def hash_kv(self, revision: int = 0, *, timeout: float | None = None) -> HashKVResponse:
        """Compute a hash of MVCC keys up to the given *revision*.

        Useful for consistency checks between cluster members.

        Args:
            revision: Compute the hash up to this revision (0 = latest).

        Key response fields:
        - ``hash``: 32-bit hash of the key-value store up to *revision*.
        - ``compact_revision``: compacted revision at the time of the call.
        - ``hash_revision``: the revision the hash was computed at.
        """
        return await self._rpc(
            self._stub.HashKV,
            HashKVRequest(revision=revision),
            operation='Maintenance.HashKV',
            timeout=timeout,
        )

    async def move_leader(
        self, target_id: int, *, timeout: float | None = None
    ) -> MoveLeaderResponse:
        """Transfer cluster leadership to the member identified by *target_id*.

        The caller must be the current leader; otherwise etcd returns an error.
        Use :meth:`status` to discover member IDs before calling this method.

        Args:
            target_id: Member ID of the peer to promote as the new leader.
        """
        return await self._rpc(
            self._stub.MoveLeader,
            MoveLeaderRequest(targetID=target_id),
            operation='Maintenance.MoveLeader',
            timeout=timeout,
        )

    async def snapshot(self, *, timeout: float | None = None) -> AsyncGenerator[bytes, None]:
        """Stream a binary snapshot of the backend database.

        Yields raw ``bytes`` chunks as they arrive from the server.  Reassemble
        them in order to obtain a complete etcd snapshot that can be used for
        disaster recovery with ``etcdctl snapshot restore``.

        Example::

            chunks: list[bytes] = []
            async for chunk in client.maintenance.snapshot():
                chunks.append(chunk)
            data = b''.join(chunks)

        Args:
            timeout: Per-call deadline in seconds (``None`` = no deadline).
        """
        call: grpc.aio.UnaryStreamCall[SnapshotRequest, SnapshotResponse] = self._stub.Snapshot(
            SnapshotRequest(), timeout=timeout
        )
        async for response in call:
            yield response.blob
