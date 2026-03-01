from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from types import TracebackType

import grpc.aio

from ._protobuf import (
    AuthenticateRequest,
    AuthenticateResponse,
    AuthStatusRequest,
    AuthStatusResponse,
    AuthStub,
)
from .base import BaseService

_log = logging.getLogger(__name__)


class AuthService(BaseService):
    """Auth facade: authenticate users and query cluster auth status.

    Designed for application developers connecting to a cluster that already
    has authentication configured.  Admin operations (enable/disable auth,
    user/role management) are out of scope.
    """

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = AuthStub(channel)

    async def auth_status(self, *, timeout: float | None = None) -> AuthStatusResponse:
        """Return the current authentication status of the cluster.

        The response includes:
        - ``enabled``: whether auth is currently enabled.
        - ``authRevision``: the current auth revision.
        """
        request = AuthStatusRequest()
        return await self._rpc(
            self._stub.AuthStatus, request, operation='Auth.AuthStatus', timeout=timeout
        )

    async def authenticate(
        self, name: str, password: str, *, timeout: float | None = None
    ) -> AuthenticateResponse:
        """Obtain a token for the given credentials.

        The returned ``token`` should be attached to subsequent calls via gRPC
        metadata: ``[('token', response.token)]``.

        Raises:
            EtcdUnauthenticatedError: credentials are invalid or auth is not enabled.
        """
        request = AuthenticateRequest(name=name, password=password)
        return await self._rpc(
            self._stub.Authenticate, request, operation='Auth.Authenticate', timeout=timeout
        )


class TokenRefresher:
    """Background context manager that keeps an auth token fresh.

    Authenticates immediately on entry, stores the token via ``set_token``,
    and then re-authenticates every ``interval`` seconds so the token never
    expires.  On exit the background task is cancelled cleanly.

    etcd's default token TTL is 5 minutes (300 s); the default interval of
    240 s gives a 60-second safety margin.

    Usage::

        async with client.token_refresher('alice', 'secret') as tr:
            # client.set_token() was called with the fresh token
            await client.kv.put('key', 'value')
        # background task stopped; token cleared from all services

    If a refresh attempt fails (e.g. transient network error), the previous
    token remains active and the error is logged.  If credentials become
    invalid the task stops and raises ``EtcdUnauthenticatedError`` on the
    next background iteration — the outer code will detect service failures
    on subsequent RPC calls.
    """

    def __init__(
        self,
        auth: AuthService,
        set_token: Callable[[str | None], None],
        name: str,
        password: str,
        *,
        interval: float = 240.0,
    ) -> None:
        if interval <= 0:
            raise ValueError('interval must be > 0')
        self._auth = auth
        self._set_token = set_token
        self._name = name
        self._password = password
        self._interval = interval
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> TokenRefresher:
        resp = await self._auth.authenticate(self._name, self._password)
        self._set_token(resp.token)
        self._task = asyncio.create_task(self._run(), name='token-refresher')
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._set_token(None)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                resp = await self._auth.authenticate(self._name, self._password)
                self._set_token(resp.token)
            except Exception:
                _log.warning('token-refresher: re-authentication failed', exc_info=True)
