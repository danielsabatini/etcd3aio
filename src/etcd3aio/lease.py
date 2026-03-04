from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from types import TracebackType

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
from .base import BaseService, _Metadata

_log = logging.getLogger(__name__)


class LeaseKeepalive:
    """Background keepalive context manager for an etcd lease.

    Sends periodic ``LeaseKeepAlive`` requests so the lease is not expired
    by the server.  The keepalive interval is derived from the server-reported
    TTL after each response (``max(1, TTL // 3)`` seconds).

    Usage::

        lease = await client.lease.grant(ttl=30)
        async with client.lease.keep_alive_context(lease.ID, ttl=30) as ka:
            # lease is renewed automatically in the background
            if not ka.alive:
                raise RuntimeError('lease expired')
            await do_work()
        # keepalive stopped; lease will expire naturally
    """

    def __init__(
        self,
        stub: LeaseStub,
        lease_id: int,
        ttl: int,
        *,
        metadata: _Metadata = (),
    ) -> None:
        self._stub = stub
        self._lease_id = lease_id
        self._ttl = ttl
        self._metadata = metadata
        self._alive = True
        self._task: asyncio.Task[None] | None = None

    @property
    def alive(self) -> bool:
        """``True`` while the lease is valid and the keepalive loop is running."""
        return self._alive

    async def __aenter__(self) -> LeaseKeepalive:
        self._task = asyncio.create_task(self._run(), name=f'lease-keepalive-{self._lease_id}')
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

    async def _run(self) -> None:
        interval = max(1, self._ttl // 3)
        while True:
            await asyncio.sleep(interval)

            async def _req() -> AsyncIterator[LeaseKeepAliveRequest]:
                yield LeaseKeepAliveRequest(ID=self._lease_id)

            stream = self._stub.LeaseKeepAlive(_req(), metadata=self._metadata or None)  # type: ignore[call-arg]
            try:
                async for response in stream:
                    if response.TTL <= 0:
                        self._alive = False
                        return
                    interval = max(1, response.TTL // 3)
            except grpc.aio.AioRpcError as exc:
                _log.warning(
                    'lease-keepalive: request failed for lease %d (%s)',
                    self._lease_id,
                    exc.code().name,
                    exc_info=True,
                )
            finally:
                stream.cancel()


class LeaseService(BaseService):
    """Lease lifecycle API."""

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = LeaseStub(channel)

    async def grant(
        self, ttl: int, lease_id: int = 0, *, timeout: float | None = None, max_attempts: int | None = None
    ) -> LeaseGrantResponse:
        """Grant a new lease with the given TTL.

        Args:
            ttl: Time-to-live in seconds.  etcd may round this up to a
                server-side minimum.
            lease_id: Requested lease ID (0 = server assigns one automatically).
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the service-level retry limit for this call only (``None`` uses the service default).

        Returns:
            ``LeaseGrantResponse`` — key fields: ``ID`` (pass to
            :meth:`~KVService.put`), ``TTL`` (actual TTL granted by the server).
        """
        request = LeaseGrantRequest(TTL=ttl, ID=lease_id)
        return await self._rpc(
            self._stub.LeaseGrant, request, operation='Lease.Grant', timeout=timeout, max_attempts=max_attempts
        )

    async def revoke(self, lease_id: int, *, timeout: float | None = None, max_attempts: int | None = None) -> LeaseRevokeResponse:
        """Revoke *lease_id* and delete all keys attached to it.

        Args:
            lease_id: ID returned by :meth:`grant`.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the service-level retry limit for this call only (``None`` uses the service default).
        """
        request = LeaseRevokeRequest(ID=lease_id)
        return await self._rpc(
            self._stub.LeaseRevoke, request, operation='Lease.Revoke', timeout=timeout, max_attempts=max_attempts
        )

    async def time_to_live(
        self, lease_id: int, keys: bool = False, *, timeout: float | None = None, max_attempts: int | None = None
    ) -> LeaseTimeToLiveResponse:
        """Return the remaining TTL and optionally the attached keys for *lease_id*.

        Args:
            lease_id: ID returned by :meth:`grant`.
            keys: If ``True``, include the list of keys attached to the lease.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the service-level retry limit for this call only (``None`` uses the service default).

        Returns:
            ``LeaseTimeToLiveResponse`` — key fields: ``TTL`` (remaining seconds,
            ``-1`` if expired), ``grantedTTL``, ``keys`` (populated only when
            *keys* is ``True``).
        """
        request = LeaseTimeToLiveRequest(ID=lease_id, keys=keys)
        return await self._rpc(
            self._stub.LeaseTimeToLive,
            request,
            operation='Lease.TimeToLive',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def leases(self, *, timeout: float | None = None, max_attempts: int | None = None) -> LeaseLeasesResponse:
        """List all active leases in the cluster.

        Args:
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the service-level retry limit for this call only (``None`` uses the service default).
        """
        return await self._rpc(
            self._stub.LeaseLeases,
            LeaseLeasesRequest(),
            operation='Lease.Leases',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    def keep_alive(self, lease_id: int) -> grpc.aio.StreamStreamCall:
        """Return the raw bidirectional keep-alive stream for *lease_id*.

        Prefer :meth:`keep_alive_context` for new code — it handles the
        periodic re-sending automatically.
        """

        async def req_gen() -> AsyncIterator[LeaseKeepAliveRequest]:
            yield LeaseKeepAliveRequest(ID=lease_id)

        return self._stub.LeaseKeepAlive(req_gen(), metadata=self._metadata or None)  # type: ignore[call-arg]

    def keep_alive_context(self, lease_id: int, ttl: int) -> LeaseKeepalive:
        """Return an async context manager that keeps *lease_id* alive in the background.

        The context manager spawns an ``asyncio.Task`` that sends a
        ``LeaseKeepAlive`` request every ``max(1, ttl // 3)`` seconds and
        adjusts the interval based on the TTL reported by the server.

        Args:
            lease_id: ID of the lease to keep alive (from :meth:`grant`).
            ttl: The lease TTL in seconds (used to compute the initial interval).

        Raises:
            RuntimeError: if the lease already expired before the context exits.
        """
        return LeaseKeepalive(self._stub, lease_id, ttl, metadata=self._metadata)
