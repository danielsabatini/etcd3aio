from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from enum import IntEnum
from typing import TypeAlias

import grpc
import grpc.aio

from ._protobuf import WatchCreateRequest, WatchRequest, WatchResponse, WatchStub
from .base import BaseService

BytesLike: TypeAlias = str | bytes


class WatchFilter(IntEnum):
    """Event filter for :meth:`WatchService.watch`.

    Pass one or both values to suppress specific event types server-side,
    reducing network traffic when only PUTs or only DELETEs are relevant.
    """

    NOPUT = 0  # suppress PUT events (watch only deletes)
    NODELETE = 1  # suppress DELETE events (watch only puts)


class WatchService(BaseService):
    """Async iterator interface over the etcd Watch API."""

    def __init__(
        self,
        channel: grpc.aio.Channel,
        *,
        max_attempts: int = 3,
        reconnect_backoff_seconds: float = 0.25,
        max_reconnect_backoff_seconds: float = 5.0,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        if reconnect_backoff_seconds <= 0:
            raise ValueError('reconnect_backoff_seconds must be > 0')
        if max_reconnect_backoff_seconds < reconnect_backoff_seconds:
            raise ValueError('max_reconnect_backoff_seconds must be >= reconnect_backoff_seconds')

        self._stub = WatchStub(channel)
        self._reconnect_backoff_seconds = reconnect_backoff_seconds
        self._max_reconnect_backoff_seconds = max_reconnect_backoff_seconds

    async def watch(  # noqa: PLR0913
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        start_revision: int = 0,
        prev_kv: bool = False,
        *,
        filters: Sequence[WatchFilter] = (),
        progress_notify: bool = False,
    ) -> AsyncIterator[WatchResponse]:
        """Stream watch events for *key* (or a key range).

        Args:
            key: Key to watch.
            range_end: Exclusive upper bound for a range watch (e.g. from
                :func:`~etcd3aio.kv.prefix_range_end`).
            start_revision: Watch from this cluster revision.  ``0`` means
                start from the current revision.
            prev_kv: Include the key-value pair as it existed before each event.
            filters: Server-side event filters.  Use :class:`WatchFilter` to
                suppress PUT or DELETE events before they reach the client.
            progress_notify: Ask the server to send empty progress events
                periodically so the client can verify its watch position, which
                is useful for reliable cache invalidation.
        """
        key_bytes = self._to_bytes(key)
        range_end_bytes = self._to_bytes(range_end) if range_end is not None else b''
        filter_ints = [int(f) for f in filters]
        next_revision = start_revision
        reconnect_backoff_seconds = self._reconnect_backoff_seconds

        while True:

            async def request_generator() -> AsyncIterator[WatchRequest]:
                create_request = WatchCreateRequest(
                    key=key_bytes,
                    range_end=range_end_bytes,
                    start_revision=next_revision,
                    prev_kv=prev_kv,
                    filters=filter_ints,
                    progress_notify=progress_notify,
                )
                yield WatchRequest(create_request=create_request)
                await asyncio.Future()

            stream = self._stub.Watch(request_generator(), metadata=self._metadata or None)  # type: ignore[call-arg]

            try:
                async for response in stream:
                    if response.compact_revision > 0:
                        next_revision = response.compact_revision + 1
                    elif response.header.revision > 0:
                        next_revision = response.header.revision + 1

                    reconnect_backoff_seconds = self._reconnect_backoff_seconds
                    yield response

                return
            except grpc.aio.AioRpcError as exc:
                if not self._is_transient_error(exc):
                    raise

                await asyncio.sleep(reconnect_backoff_seconds)
                reconnect_backoff_seconds = min(
                    reconnect_backoff_seconds * 2,
                    self._max_reconnect_backoff_seconds,
                )
            finally:
                stream.cancel()

    @staticmethod
    def _to_bytes(data: BytesLike) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
