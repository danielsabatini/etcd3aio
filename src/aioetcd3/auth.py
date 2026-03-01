from __future__ import annotations

import grpc.aio

from ._protobuf import (
    AuthenticateRequest,
    AuthenticateResponse,
    AuthStatusRequest,
    AuthStatusResponse,
    AuthStub,
)
from .base import BaseService


class AuthService(BaseService):
    """Auth facade: authenticate users and query cluster auth status.

    Designed for application developers connecting to a cluster that already
    has authentication configured.  Admin operations (enable/disable auth,
    user/role management) are out of scope.
    """

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = AuthStub(channel)

    async def auth_status(self) -> AuthStatusResponse:
        """Return the current authentication status of the cluster.

        The response includes:
        - ``enabled``: whether auth is currently enabled.
        - ``authRevision``: the current auth revision.
        """
        request = AuthStatusRequest()
        return await self._rpc(self._stub.AuthStatus, request, operation='Auth.AuthStatus')

    async def authenticate(self, name: str, password: str) -> AuthenticateResponse:
        """Obtain a token for the given credentials.

        The returned ``token`` should be attached to subsequent calls via gRPC
        metadata: ``[('token', response.token)]``.

        Raises:
            EtcdUnauthenticatedError: credentials are invalid or auth is not enabled.
        """
        request = AuthenticateRequest(name=name, password=password)
        return await self._rpc(self._stub.Authenticate, request, operation='Auth.Authenticate')
