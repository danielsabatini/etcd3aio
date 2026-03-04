from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from types import TracebackType

from ._protobuf import PutResponse, RangeResponse, WatchResponse
from .errors import EtcdError
from .kv import KVService, SortOrder, SortTarget, prefix_range_end
from .lease import LeaseService
from .watch import WatchService

_LOCK_PREFIX = '__etcd3aio:lock'
_ELECTION_PREFIX = '__etcd3aio:election'

# mvccpb.Event.EventType: PUT=0, DELETE=1
_EVENT_PUT = 0
_EVENT_DELETE = 1


class _Semaphore:
    """Shared acquire/release protocol used by Lock and Election.

    Protocol (etcd linearizable locking):
    1. Grant a lease (TTL defines max hold time on crash).
    2. Put ``{prefix}/{lease_id:016x}`` tied to the lease.
    3. Scan all keys under the prefix, sorted by ``create_revision``.
    4. If ours has the lowest revision → we hold it.
    5. Otherwise watch the preceding key until DELETE, then go to 3.
    """

    def __init__(  # noqa: PLR0913
        self,
        kv: KVService,
        lease: LeaseService,
        watch: WatchService,
        prefix: bytes,
        value: bytes,
        ttl: int,
    ) -> None:
        self._kv = kv
        self._lease = lease
        self._watch = watch
        self._prefix = prefix
        self._prefix_end = prefix_range_end(prefix)
        self._value = value
        self._ttl = ttl
        self._my_key: bytes | None = None
        self._lease_id: int | None = None

    async def _acquire(self) -> None:
        """Acquire the semaphore slot using the etcd linearizable locking protocol."""
        lease_resp = await self._lease.grant(ttl=self._ttl)
        lease_id: int = int(lease_resp.ID)
        self._lease_id = lease_id
        my_key = self._prefix + f'{lease_id:016x}'.encode()
        self._my_key = my_key

        await self._kv.put(my_key, self._value, lease=lease_id)

        while True:
            range_resp = await self._kv.get(self._prefix, range_end=self._prefix_end)
            kvs = sorted(range_resp.kvs, key=lambda kv: kv.create_revision)

            my_idx = next((i for i, kv in enumerate(kvs) if kv.key == my_key), None)
            if my_idx is None:
                raise RuntimeError('semaphore key disappeared; lease may have expired')
            if my_idx == 0:
                return  # acquired

            predecessor = kvs[my_idx - 1].key
            watch_from = range_resp.header.revision + 1

            async for response in self._watch.watch(predecessor, start_revision=watch_from):
                if any(
                    e.type == _EVENT_DELETE and e.kv.key == predecessor for e in response.events
                ):
                    break  # predecessor gone — re-check who's first

    async def _release(self) -> None:
        """Release the semaphore by deleting the etcd key and revoking the lease."""
        if self._my_key is not None:
            with contextlib.suppress(EtcdError):
                await self._kv.delete(self._my_key)
            self._my_key = None
        if self._lease_id is not None:
            with contextlib.suppress(EtcdError):
                await self._lease.revoke(self._lease_id)
            self._lease_id = None


class Lock(_Semaphore):
    """Distributed lock backed by etcd KV + Lease.

    Usage::

        async with client.lock('my-resource', ttl=30):
            # exclusive section

    The lock is released on context exit. If the holder crashes, etcd expires
    the underlying lease after *ttl* seconds and unblocks the next waiter.

    Not re-entrant: a single ``Lock`` instance must not be entered twice.
    """

    def __init__(
        self,
        kv: KVService,
        lease: LeaseService,
        watch: WatchService,
        name: str,
        *,
        ttl: int = 30,
    ) -> None:
        prefix = f'{_LOCK_PREFIX}/{name}/'.encode()
        super().__init__(kv, lease, watch, prefix, b'', ttl)

    async def acquire(self) -> None:
        """Acquire the lock without a context manager.

        Must be paired with :meth:`release` in a ``try/finally`` block.
        Prefer the ``async with`` form when possible.
        """
        await self._acquire()

    async def release(self) -> None:
        """Release the lock acquired via :meth:`acquire`."""
        await self._release()

    async def __aenter__(self) -> Lock:
        await self._acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._release()


class Election(_Semaphore):
    """Leader election backed by etcd KV + Lease.

    Usage::

        async with client.election('my-election', value=b'node-1', ttl=30):
            # this node is the leader

    *value* is stored as the leader's identity and can be read by observers.
    Leadership is relinquished on context exit or when the lease expires.

    Not re-entrant: a single ``Election`` instance must not be entered twice.
    """

    def __init__(  # noqa: PLR0913
        self,
        kv: KVService,
        lease: LeaseService,
        watch: WatchService,
        name: str,
        *,
        value: bytes = b'',
        ttl: int = 30,
    ) -> None:
        prefix = f'{_ELECTION_PREFIX}/{name}/'.encode()
        super().__init__(kv, lease, watch, prefix, value, ttl)

    async def leader(self, *, timeout: float | None = None) -> RangeResponse:
        """Return the current leader's KV entry.

        The response ``.kvs`` list contains the leader's key-value if a leader
        exists, or is empty if no candidate has won the election yet.
        ``response.kvs[0].value`` is the value the leader posted on campaign.
        """
        return await self._kv.get(
            self._prefix,
            range_end=self._prefix_end,
            sort_order=SortOrder.ASCEND,
            sort_target=SortTarget.CREATE,
            limit=1,
            timeout=timeout,
        )

    async def proclaim(self, value: bytes, *, timeout: float | None = None) -> PutResponse:
        """Update the value posted by this leader.

        Must be called while holding the election (inside the ``async with`` block).
        Raises ``RuntimeError`` if the election has not been acquired.

        Args:
            value: New bytes value to store under the leader key.
        """
        if self._my_key is None or self._lease_id is None:
            raise RuntimeError('not holding the election; call proclaim() inside the async context')
        self._value = value
        return await self._kv.put(self._my_key, value, lease=self._lease_id, timeout=timeout)

    async def observe(self) -> AsyncIterator[WatchResponse]:
        """Stream watch responses whenever a new leader is elected.

        Yields a :class:`WatchResponse` for each server response that contains
        at least one PUT event on the election prefix — i.e. every time a new
        leader is crowned.  DELETE events (leader resigned) are filtered out.

        The stream reconnects automatically on transient errors (same behaviour
        as :meth:`WatchService.watch`).
        """
        async for response in self._watch.watch(self._prefix, range_end=self._prefix_end):
            if any(e.type == _EVENT_PUT for e in response.events):
                yield response

    async def __aenter__(self) -> Election:
        await self._acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._release()
