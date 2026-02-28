from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

import grpc.aio

from ._protobuf import (
    Compare,
    DeleteRangeRequest,
    DeleteRangeResponse,
    KVStub,
    PutRequest,
    PutResponse,
    RangeRequest,
    RangeResponse,
    RequestOp,
    TxnRequest,
    TxnResponse,
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

    async def txn(
        self,
        compare: Sequence[Compare],
        success: Sequence[RequestOp],
        failure: Sequence[RequestOp] = (),
    ) -> TxnResponse:
        request = TxnRequest(
            compare=list(compare),
            success=list(success),
            failure=list(failure),
        )
        return await self._rpc(self._stub.Txn, request, operation='KV.Txn')

    @classmethod
    def txn_compare_value(
        cls,
        key: BytesLike,
        value: BytesLike,
        *,
        result: int = Compare.EQUAL,
        range_end: BytesLike | None = None,
    ) -> Compare:
        compare = Compare(
            result=result,
            target=Compare.VALUE,
            key=cls._to_bytes(key),
            value=cls._to_bytes(value),
        )
        if range_end is not None:
            compare.range_end = cls._to_bytes(range_end)
        return compare

    @classmethod
    def txn_compare_version(
        cls,
        key: BytesLike,
        version: int,
        *,
        result: int = Compare.EQUAL,
        range_end: BytesLike | None = None,
    ) -> Compare:
        compare = Compare(
            result=result,
            target=Compare.VERSION,
            key=cls._to_bytes(key),
            version=version,
        )
        if range_end is not None:
            compare.range_end = cls._to_bytes(range_end)
        return compare

    @classmethod
    def txn_op_put(
        cls,
        key: BytesLike,
        value: BytesLike,
        *,
        lease: int = 0,
        prev_kv: bool = False,
    ) -> RequestOp:
        put_request = PutRequest(
            key=cls._to_bytes(key),
            value=cls._to_bytes(value),
            lease=lease,
            prev_kv=prev_kv,
        )
        return RequestOp(request_put=put_request)

    @classmethod
    def txn_op_get(
        cls,
        key: BytesLike,
        *,
        range_end: BytesLike | None = None,
        serializable: bool = False,
        revision: int = 0,
    ) -> RequestOp:
        range_request = RangeRequest(
            key=cls._to_bytes(key),
            range_end=cls._to_bytes(range_end) if range_end is not None else b'',
            serializable=serializable,
            revision=revision,
        )
        return RequestOp(request_range=range_request)

    @classmethod
    def txn_op_delete(
        cls,
        key: BytesLike,
        *,
        range_end: BytesLike | None = None,
        prev_kv: bool = False,
    ) -> RequestOp:
        delete_request = DeleteRangeRequest(
            key=cls._to_bytes(key),
            range_end=cls._to_bytes(range_end) if range_end is not None else b'',
            prev_kv=prev_kv,
        )
        return RequestOp(request_delete_range=delete_request)

    @staticmethod
    def _to_bytes(data: BytesLike) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
