from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TypeAlias

import grpc
import grpc.aio

from ._protobuf import WatchCreateRequest, WatchRequest, WatchResponse, WatchStub
from .base import BaseService

BytesLike: TypeAlias = str | bytes


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

    async def watch(
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        start_revision: int = 0,
        prev_kv: bool = False,
    ) -> AsyncIterator[WatchResponse]:
        key_bytes = self._to_bytes(key)
        range_end_bytes = self._to_bytes(range_end) if range_end is not None else b''
        next_revision = start_revision
        reconnect_backoff_seconds = self._reconnect_backoff_seconds

        while True:

            async def request_generator() -> AsyncIterator[WatchRequest]:
                create_request = WatchCreateRequest(
                    key=key_bytes,
                    range_end=range_end_bytes,
                    start_revision=next_revision,
                    prev_kv=prev_kv,
                )
                yield WatchRequest(create_request=create_request)
                await asyncio.Future()

            stream = self._stub.Watch(request_generator())

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
