from __future__ import annotations

import contextlib
from collections.abc import Sequence
from types import TracebackType

import grpc.aio

from .auth import AuthService, TokenRefresher
from .cluster import ClusterService
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
    """High-level async facade for etcd v3 services.

    Wires all service modules onto a single gRPC channel and exposes factory
    methods for distributed concurrency primitives.

    Args:
        endpoints: List of ``host:port`` strings.  Defaults to
            ``['localhost:2379']``.  Multiple endpoints enable round-robin
            load balancing.
        token: Optional auth token applied immediately to all services.
        rpc_max_attempts: Maximum retry attempts for transient unary RPCs
            (``UNAVAILABLE`` / ``DEADLINE_EXCEEDED``).  Defaults to 3.
        watch_reconnect_backoff_seconds: Initial reconnect delay for watch
            streams.  Doubles on each failure up to
            *watch_max_reconnect_backoff_seconds*.
        watch_max_reconnect_backoff_seconds: Cap on watch stream reconnect delay.
        **conn_args: TLS keyword arguments forwarded to
            :meth:`~ConnectionManager.get_channel` — ``ca_cert``,
            ``cert_key``, ``cert_chain``.

    Usage::

        async with Etcd3Client(['localhost:2379']) as client:
            await client.kv.put('hello', 'world')
    """

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
        self.cluster: ClusterService | None = None
        self.kv: KVService | None = None
        self.lease: LeaseService | None = None
        self.maintenance: MaintenanceService | None = None
        self.watch: WatchService | None = None

    async def connect(self) -> None:  # NOSONAR
        """Open the gRPC channel and initialise all service facades.

        Called automatically when using the ``async with`` context manager.
        Call explicitly if you prefer manual lifecycle management.
        """
        self._channel = self._manager.get_channel(**self._conn_args)
        self.auth = AuthService(self._channel, max_attempts=self._rpc_max_attempts)
        self.cluster = ClusterService(self._channel, max_attempts=self._rpc_max_attempts)
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
        for svc in (self.auth, self.cluster, self.kv, self.lease, self.maintenance, self.watch):
            if svc is not None:
                svc.set_token(token)

    async def close(self) -> None:
        """Closes the gRPC channel and clears facades."""
        if self._channel is not None:
            await self._channel.close()

        self._channel = None
        self.auth = None
        self.cluster = None
        self.kv = None
        self.lease = None
        self.maintenance = None
        self.watch = None

    async def ping(self, *, write_check: bool = True, timeout: float = 5.0) -> None:  # NOSONAR
        """Verify cluster health.

        Raises EtcdConnectionError if the cluster is unreachable.
        With write_check=True (default), also validates write capability,
        detecting quorum loss in multi-node clusters.

        Args:
            write_check: When True, also validates write capability via a
                short-lived lease put.  Set to False for a cheaper read-only check.
            timeout: Maximum seconds to wait for the cluster to respond before
                raising TimeoutError.  Defaults to 5.0 s.
        """
        if self.kv is None or self.lease is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)

        await self.kv.get(_PING_KEY, timeout=timeout)

        if not write_check:
            return

        lease = await self.lease.grant(ttl=5, timeout=timeout)
        try:
            await self.kv.put(_PING_KEY, b'', lease=lease.ID, timeout=timeout)
        finally:
            with contextlib.suppress(EtcdError):
                await self.lease.revoke(lease.ID, timeout=timeout)

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
        """Return a distributed lock for *name*.

        Must be used as an ``async with`` context manager.  Blocks until the
        lock is acquired (previous holder exits or their lease expires).

        Args:
            name: Logical lock name.  Competing holders must use the same *name*.
            ttl: Lease TTL in seconds.  If the holder crashes, the lock is
                released automatically after this many seconds.
        """
        if self.kv is None or self.lease is None or self.watch is None:
            raise RuntimeError(_ERR_NOT_CONNECTED)
        return Lock(self.kv, self.lease, self.watch, name, ttl=ttl)

    def election(self, name: str, *, value: bytes = b'', ttl: int = 30) -> Election:
        """Return a leader election for *name*.

        Must be used as an ``async with`` context manager.  Blocks until this
        node wins the election.  *value* is stored as the leader's identity and
        can be read by non-leader nodes via :meth:`Election.leader` or
        :meth:`Election.observe`.

        Args:
            name: Election name.  All participants must use the same *name*.
            value: Bytes value stored as the leader's identity.
            ttl: Lease TTL in seconds.  Leadership is revoked if the holder
                crashes and the lease expires.
        """
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
