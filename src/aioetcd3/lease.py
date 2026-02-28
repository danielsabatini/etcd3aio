from ._protobuf import (
    LeaseGrantRequest,
    LeaseKeepAliveRequest,
    LeaseRevokeRequest,
    LeaseStub,
    LeaseTimeToLiveRequest,
)


class LeaseService:
    """Contratos renováveis para detecção de liveness [2, 16]."""

    def __init__(self, channel):
        self._stub = LeaseStub(channel)

    async def grant(self, ttl: int, id: int = 0):
        return await self._stub.LeaseGrant(LeaseGrantRequest(TTL=ttl, ID=id))

    async def revoke(self, id: int):
        return await self._stub.LeaseRevoke(LeaseRevokeRequest(ID=id))

    async def time_to_live(self, id: int, keys: bool = False):
        return await self._stub.LeaseTimeToLive(LeaseTimeToLiveRequest(ID=id, keys=keys))

    async def keep_alive(self, id: int):
        """Usa stream bidirecional para renovar a concessão [15]."""

        async def req_gen():
            yield LeaseKeepAliveRequest(ID=id)

        return self._stub.LeaseKeepAlive(req_gen())
