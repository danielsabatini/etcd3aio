from __future__ import annotations

from typing import TypeAlias

import grpc.aio

from ._protobuf import (
    DeleteRangeRequest,
    DeleteRangeResponse,
    KVStub,
    PutRequest,
    PutResponse,
    RangeRequest,
    RangeResponse,
)
from .base import BaseService

BytesLike: TypeAlias = str | bytes


class KVService(BaseService):
    """KV facade with default linearizable semantics."""

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = KVStub(channel)

    async def put(
        self,
        key: BytesLike,
        value: BytesLike,
        lease: int = 0,
        prev_kv: bool = False,
    ) -> PutResponse:
        request = PutRequest(
            key=self._to_bytes(key),
            value=self._to_bytes(value),
            lease=lease,
            prev_kv=prev_kv,
        )
        return await self._rpc(self._stub.Put, request, operation='KV.Put')

    async def get(
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        serializable: bool = False,
        revision: int = 0,
    ) -> RangeResponse:
        request = RangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end is not None else b'',
            serializable=serializable,
            revision=revision,
        )
        return await self._rpc(self._stub.Range, request, operation='KV.Range')

    async def delete(
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        prev_kv: bool = False,
    ) -> DeleteRangeResponse:
        request = DeleteRangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end is not None else b'',
            prev_kv=prev_kv,
        )
        return await self._rpc(self._stub.DeleteRange, request, operation='KV.DeleteRange')

    @staticmethod
    def _to_bytes(data: BytesLike) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
