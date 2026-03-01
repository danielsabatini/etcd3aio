from __future__ import annotations

import contextlib
from collections.abc import Sequence
from types import TracebackType

import grpc.aio

from .connections import ConnectionManager
from .errors import EtcdError
from .kv import KVService
from .lease import LeaseService
from .watch import WatchService

_PING_KEY = '__aioetcd3:ping__'


class Etcd3Client:
    """High level facade for etcd v3 services."""

    def __init__(
        self,
        endpoints: Sequence[str] | None = None,
        *,
        rpc_max_attempts: int = 3,
        watch_reconnect_backoff_seconds: float = 0.25,
        watch_max_reconnect_backoff_seconds: float = 5.0,
        **conn_args: bytes | None,
    ) -> None:
        self._manager = ConnectionManager(endpoints or ['localhost:2379'])
        self._conn_args = conn_args
        self._rpc_max_attempts = rpc_max_attempts
        self._watch_reconnect_backoff_seconds = watch_reconnect_backoff_seconds
        self._watch_max_reconnect_backoff_seconds = watch_max_reconnect_backoff_seconds

        self._channel: grpc.aio.Channel | None = None
        self.kv: KVService | None = None
        self.lease: LeaseService | None = None
        self.watch: WatchService | None = None

    async def connect(self) -> None:
        """Initializes channel and service facades."""
        self._channel = await self._manager.get_channel(**self._conn_args)
        self.kv = KVService(self._channel, max_attempts=self._rpc_max_attempts)
        self.lease = LeaseService(self._channel, max_attempts=self._rpc_max_attempts)
        self.watch = WatchService(
            self._channel,
            max_attempts=self._rpc_max_attempts,
            reconnect_backoff_seconds=self._watch_reconnect_backoff_seconds,
            max_reconnect_backoff_seconds=self._watch_max_reconnect_backoff_seconds,
        )

    async def close(self) -> None:
        """Closes the gRPC channel and clears facades."""
        if self._channel is not None:
            await self._channel.close()

        self._channel = None
        self.kv = None
        self.lease = None
        self.watch = None

    async def ping(self, *, write_check: bool = True) -> None:
        """Verify cluster health.

        Raises EtcdConnectionError if the cluster is unreachable.
        With write_check=True (default), also validates write capability,
        detecting quorum loss in multi-node clusters.
        """
        if self.kv is None or self.lease is None:
            raise RuntimeError('client is not connected')

        await self.kv.get(_PING_KEY)

        if not write_check:
            return

        lease = await self.lease.grant(ttl=5)
        try:
            await self.kv.put(_PING_KEY, b'', lease=lease.ID)
        finally:
            with contextlib.suppress(EtcdError):
                await self.lease.revoke(lease.ID)

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
