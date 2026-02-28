from __future__ import annotations

from ._protobuf import (
    LeaseGrantRequest,
    LeaseKeepAliveRequest,
    LeaseRevokeRequest,
    LeaseStub,
    LeaseTimeToLiveRequest,
)


class LeaseService:
    """Gerencia concessões e vivacidade do cliente [7]."""

    def __init__(self, channel):
        self._stub = LeaseStub(channel)

    async def grant(self, ttl: int, id: int = 0):
        return await self._stub.LeaseGrant(LeaseGrantRequest(TTL=ttl, ID=id))

    async def revoke(self, id: int):
        return await self._stub.LeaseRevoke(LeaseRevokeRequest(ID=id))

    async def time_to_live(self, id: int, keys: bool = False):
        return await self._stub.LeaseTimeToLive(LeaseTimeToLiveRequest(ID=id, keys=keys))

    async def keep_alive(self, id: int):
        """Usa stream bidirecional gRPC para renovar o TTL [8]."""

        async def req_gen():
            yield LeaseKeepAliveRequest(ID=id)

        return self._stub.LeaseKeepAlive(req_gen())
