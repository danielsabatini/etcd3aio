from __future__ import annotations

import contextlib
from collections.abc import Sequence
from types import TracebackType

import grpc.aio

from .auth import AuthService, TokenRefresher
from .concurrency import Election, Lock
from .connections import ConnectionManager
from .errors import EtcdError
from .kv import KVService
from .lease import LeaseService
from .maintenance import MaintenanceService
from .watch import WatchService

_PING_KEY = '__etcd3aio:ping__'
_ERR_NOT_CONNECTED = 'client is not connected'


class Etcd3Client:
    """High level facade for etcd v3 services."""

    def __init__(
        self,
        endpoints: Sequence[str] | None = None,
        *,
        token: str | None = None,
        rpc_max_attempts: int = 3,
        watch_reconnect_backoff_seconds: float = 0.25,
        watch_max_reconnect_backoff_seconds: float = 5.0,
        **conn_args: bytes | None,
    ) -> None:
        self._manager = ConnectionManager(endpoints or ['localhost:2379'])
        self._conn_args = conn_args
        self._token = token
        self._rpc_max_attempts = rpc_max_attempts
        self._watch_reconnect_backoff_seconds = watch_reconnect_backoff_seconds
        self._watch_max_reconnect_backoff_seconds = watch_max_reconnect_backoff_seconds

        self._channel: grpc.aio.Channel | None = None
        self.auth: AuthService | None = None
        self.kv: KVService | None = None
        self.lease: LeaseService | None = None
        self.maintenance: MaintenanceService | None = None
        self.watch: WatchService | None = None

    async def connect(self) -> None:
        """Initializes channel and service facades."""
        self._channel = self._manager.get_channel(**self._conn_args)
        await self._channel.channel_ready()
        self.auth = AuthService(self._channel, max_attempts=self._rpc_max_attempts)
        self.kv = KVService(self._channel, max_attempts=self._rpc_max_attempts)
        self.lease = LeaseService(self._channel, max_attempts=self._rpc_max_attempts)
        self.maintenance = MaintenanceService(self._channel, max_attempts=self._rpc_max_attempts)
        self.watch = WatchService(
            self._channel,
            max_attempts=self._rpc_max_attempts,
            reconnect_backoff_seconds=self._watch_reconnect_backoff_seconds,
            max_reconnect_backoff_seconds=self._watch_max_reconnect_backoff_seconds,
        )
        if self._token:
            self.set_token(self._token)

    def set_token(self, token: str | None) -> None:
        """Apply *token* as gRPC metadata on all subsequent calls across every service.

        Call this after ``auth.authenticate()`` to enable authenticated requests::

            resp = await client.auth.authenticate('alice', 'secret')
            client.set_token(resp.token)
        """
        self._token = token
        for svc in (self.auth, self.kv, self.lease, self.maintenance, self.watch):
            if svc is not None:
                svc.set_token(token)

    async def close(self) -> None:
        """Closes the gRPC channel and clears facades."""
        if self._channel is not None:
            await self._channel.close()

        self._channel = None
        self.auth = None
        self.kv = None
        self.lease = None
        self.maintenance = None
        self.watch = None

    async def ping(self, *, write_check: bool = True) -> None:
        """Verify cluster health.

        Raises EtcdConnectionError if the cluster is unreachable.
        With write_check=True (default), also validates write capability,
        detecting quorum loss in multi-node clusters.
        """
        if self.kv is None or self.lease is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)

        await self.kv.get(_PING_KEY)

        if not write_check:
            return

        lease = await self.lease.grant(ttl=5)
        try:
            await self.kv.put(_PING_KEY, b'', lease=lease.ID)
        finally:
            with contextlib.suppress(EtcdError):
                await self.lease.revoke(lease.ID)

    def token_refresher(
        self,
        name: str,
        password: str,
        *,
        interval: float = 240.0,
    ) -> TokenRefresher:
        """Return a context manager that authenticates and keeps the token refreshed.

        On entry the user is authenticated immediately and the token is applied
        to all services via :meth:`set_token`.  A background task re-authenticates
        every *interval* seconds.  On exit the task is cancelled and the token is
        cleared.

        Args:
            name: etcd username.
            password: etcd password.
            interval: Seconds between token refreshes (default 240 s = 4 min,
                safe for etcd's default 5-minute token TTL).

        Must be connected before calling this method.
        """
        if self.auth is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)
        return TokenRefresher(self.auth, self.set_token, name, password, interval=interval)

    def lock(self, name: str, *, ttl: int = 30) -> Lock:
        """Return a distributed lock for *name*. Must be used as an async context manager."""
        if self.kv is None or self.lease is None or self.watch is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)
        return Lock(self.kv, self.lease, self.watch, name, ttl=ttl)

    def election(self, name: str, *, value: bytes = b'', ttl: int = 30) -> Election:
        """Return a leader election for *name*. Must be used as an async context manager."""
        if self.kv is None or self.lease is None or self.watch is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)
        return Election(self.kv, self.lease, self.watch, name, value=value, ttl=ttl)

    async def __aenter__(self) -> Etcd3Client:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
