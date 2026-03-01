from __future__ import annotations

from collections.abc import AsyncIterator

import grpc.aio

from ._protobuf import (
    LeaseGrantRequest,
    LeaseGrantResponse,
    LeaseKeepAliveRequest,
    LeaseLeasesRequest,
    LeaseLeasesResponse,
    LeaseRevokeRequest,
    LeaseRevokeResponse,
    LeaseStub,
    LeaseTimeToLiveRequest,
    LeaseTimeToLiveResponse,
)
from .base import BaseService


class LeaseService(BaseService):
    """Lease lifecycle API."""

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = LeaseStub(channel)

    async def grant(self, ttl: int, lease_id: int = 0) -> LeaseGrantResponse:
        request = LeaseGrantRequest(TTL=ttl, ID=lease_id)
        return await self._rpc(self._stub.LeaseGrant, request, operation='Lease.LeaseGrant')

    async def revoke(self, lease_id: int) -> LeaseRevokeResponse:
        request = LeaseRevokeRequest(ID=lease_id)
        return await self._rpc(self._stub.LeaseRevoke, request, operation='Lease.LeaseRevoke')

    async def time_to_live(self, lease_id: int, keys: bool = False) -> LeaseTimeToLiveResponse:
        request = LeaseTimeToLiveRequest(ID=lease_id, keys=keys)
        return await self._rpc(
            self._stub.LeaseTimeToLive,
            request,
            operation='Lease.LeaseTimeToLive',
        )

    async def leases(self) -> LeaseLeasesResponse:
        """List all active leases in the cluster."""
        return await self._rpc(
            self._stub.LeaseLeases, LeaseLeasesRequest(), operation='Lease.LeaseLeases'
        )

    def keep_alive(self, lease_id: int) -> grpc.aio.StreamStreamCall:
        """Starts the keep alive stream for a lease."""

        async def req_gen() -> AsyncIterator[LeaseKeepAliveRequest]:
            yield LeaseKeepAliveRequest(ID=lease_id)

        return self._stub.LeaseKeepAlive(req_gen())
