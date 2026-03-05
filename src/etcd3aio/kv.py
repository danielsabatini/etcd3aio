from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum
from typing import TypeAlias

import grpc.aio

from ._protobuf import (
    CompactionRequest,
    CompactionResponse,
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

_BYTE_MAX = 0xFF


def prefix_range_end(prefix: BytesLike) -> bytes:
    """Return the exclusive upper-bound key for a lexicographic prefix scan.

    Use with :meth:`KVService.get` or :meth:`KVService.delete` to operate on
    all keys that start with *prefix*::

        end = prefix_range_end('/services/')
        resp = await kv.get('/services/', range_end=end, keys_only=True)

    Returns ``b'\\x00'`` for the edge case where every byte in the prefix is
    ``0xFF``, which selects all keys in etcd.
    """
    b = bytearray(prefix.encode('utf-8') if isinstance(prefix, str) else prefix)
    for i in range(len(b) - 1, -1, -1):
        if b[i] < _BYTE_MAX:
            b[i] += 1
            return bytes(b[: i + 1])
    return b'\x00'


class SortOrder(IntEnum):
    """Sort order for :meth:`KVService.get` range queries."""

    NONE = 0
    ASCEND = 1
    DESCEND = 2


class SortTarget(IntEnum):
    """Field to sort on for :meth:`KVService.get` range queries."""

    KEY = 0
    VERSION = 1
    CREATE = 2
    MOD = 3
    VALUE = 4


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
        *,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> PutResponse:
        """Store *key* with the given *value*.

        Args:
            key: Key name (UTF-8 string or bytes).
            value: Value to store (UTF-8 string or bytes).
            lease: Lease ID to attach to the key (0 = no lease).
            prev_kv: If ``True``, return the previous key-value in the response.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Returns:
            ``PutResponse`` — ``prev_kv`` is populated only when *prev_kv* is ``True``.
        """
        request = PutRequest(
            key=self._to_bytes(key),
            value=self._to_bytes(value),
            lease=lease,
            prev_kv=prev_kv,
        )
        return await self._rpc(
            self._stub.Put, request, operation='KV.Put', timeout=timeout, max_attempts=max_attempts
        )

    async def get(  # noqa: PLR0913
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        serializable: bool = False,
        revision: int = 0,
        *,
        limit: int = 0,
        sort_order: SortOrder = SortOrder.NONE,
        sort_target: SortTarget = SortTarget.KEY,
        keys_only: bool = False,
        count_only: bool = False,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> RangeResponse:
        """Fetch a single key or a key range.

        Args:
            key: Key to fetch. Use with *range_end* for range/prefix scans.
            range_end: Exclusive upper bound for a range scan.  Pass the result
                of :func:`prefix_range_end` to scan all keys under a prefix.
            serializable: Allow stale reads from any member (lower latency).
            revision: Read at a specific cluster revision (0 = latest).
            limit: Maximum number of keys to return (0 = unlimited).  Use for
                pagination over large key spaces.
            sort_order: :class:`SortOrder` applied after filtering.
            sort_target: :class:`SortTarget` field to sort on.
            keys_only: Return only keys; omit values (efficient for discovery).
            count_only: Return only the key count; omit keys and values.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).
        """
        request = RangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end is not None else b'',
            serializable=serializable,
            revision=revision,
            limit=limit,
            sort_order=int(sort_order),
            sort_target=int(sort_target),
            keys_only=keys_only,
            count_only=count_only,
        )
        return await self._rpc(
            self._stub.Range,
            request,
            operation='KV.Range',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def delete(
        self,
        key: BytesLike,
        range_end: BytesLike | None = None,
        prev_kv: bool = False,
        *,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> DeleteRangeResponse:
        """Delete a single key or a key range.

        Args:
            key: Key to delete.  Use with *range_end* for range/prefix deletions.
            range_end: Exclusive upper bound for a range deletion.  Pass the result
                of :func:`prefix_range_end` to delete all keys under a prefix.
            prev_kv: If ``True``, include the deleted key-value pairs in the response.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Returns:
            ``DeleteRangeResponse`` — ``deleted`` is the number of keys removed;
            ``prev_kvs`` is populated only when *prev_kv* is ``True``.
        """
        request = DeleteRangeRequest(
            key=self._to_bytes(key),
            range_end=self._to_bytes(range_end) if range_end is not None else b'',
            prev_kv=prev_kv,
        )
        return await self._rpc(
            self._stub.DeleteRange,
            request,
            operation='KV.DeleteRange',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def compact(
        self,
        revision: int,
        *,
        physical: bool = False,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> CompactionResponse:
        """Compact the event history up to the given revision.

        After compaction, any watch starting from a revision older than the
        compacted one will receive a compacted-revision error.

        With physical=True, the call blocks until the compaction is physically
        applied to the backend (slower but guarantees storage reclaim).

        Args:
            revision: Compact up to this cluster revision (inclusive).
            physical: If ``True``, block until the compaction is physically
                applied to the backend.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).
        """
        request = CompactionRequest(revision=revision, physical=physical)
        return await self._rpc(
            self._stub.Compact,
            request,
            operation='KV.Compact',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def txn(
        self,
        compare: Sequence[Compare],
        success: Sequence[RequestOp],
        failure: Sequence[RequestOp] = (),
        *,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> TxnResponse:
        """Execute an atomic compare-and-swap transaction.

        Evaluates *compare* conditions atomically: if all pass, *success* operations
        run; otherwise *failure* operations run.  All operations are applied in a
        single cluster revision.

        Args:
            compare: Sequence of :class:`Compare` predicates built with the
                ``txn_compare_*`` class methods.
            success: Operations executed when every predicate evaluates to ``True``.
            failure: Operations executed when any predicate evaluates to ``False``.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Returns:
            ``TxnResponse`` — ``succeeded`` is ``True`` if the success branch ran;
            ``responses`` contains the results of the executed branch operations.
        """
        request = TxnRequest(
            compare=list(compare),
            success=list(success),
            failure=list(failure),
        )
        return await self._rpc(
            self._stub.Txn, request, operation='KV.Txn', timeout=timeout, max_attempts=max_attempts
        )

    @classmethod
    def txn_compare_value(
        cls,
        key: BytesLike,
        value: BytesLike,
        *,
        result: int = Compare.EQUAL,
        range_end: BytesLike | None = None,
    ) -> Compare:
        """Build a Compare predicate on a key's value.

        Args:
            key: Key to compare.
            value: Expected value (UTF-8 string or bytes).
            result: Comparison operator (``Compare.EQUAL``, ``LESS``, ``GREATER``,
                ``NOT_EQUAL``).  Defaults to ``Compare.EQUAL``.
            range_end: If set, the predicate applies to all keys in ``[key, range_end)``.

        Returns:
            ``Compare`` suitable for the *compare* argument of :meth:`txn`.
        """
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
        """Build a Compare predicate on a key's version counter.

        A key's version starts at 1 on creation and increments on each write.
        A version of 0 means the key does not exist.

        Args:
            key: Key to compare.
            version: Expected version number.
            result: Comparison operator (default ``Compare.EQUAL``).
            range_end: Optional range upper bound.

        Returns:
            ``Compare`` suitable for the *compare* argument of :meth:`txn`.
        """
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
    def txn_compare_create_revision(
        cls,
        key: BytesLike,
        create_revision: int,
        *,
        result: int = Compare.EQUAL,
        range_end: BytesLike | None = None,
    ) -> Compare:
        """Compare the create_revision of a key.

        The canonical etcd idiom for "key does not exist yet" is::

            KVService.txn_compare_create_revision('my-key', 0)

        which evaluates to True only if ``my-key`` has never been created
        (``create_revision == 0``).
        """
        compare = Compare(
            result=result,
            target=Compare.CREATE,
            key=cls._to_bytes(key),
            create_revision=create_revision,
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
        """Build a Put operation for use in a :meth:`txn` success/failure branch.

        Args:
            key: Key to write.
            value: Value to write.
            lease: Lease ID to attach (0 = no lease).
            prev_kv: If ``True``, include the previous value in the response.

        Returns:
            ``RequestOp`` wrapping a ``PutRequest``.
        """
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
        """Build a Range (get) operation for use in a :meth:`txn` success/failure branch.

        Args:
            key: Key to read.  Use with *range_end* for range reads.
            range_end: Exclusive upper bound for a range read.
            serializable: Allow stale reads (default ``False``).
            revision: Read at a specific cluster revision (0 = latest).

        Returns:
            ``RequestOp`` wrapping a ``RangeRequest``.
        """
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
        """Build a DeleteRange operation for use in a :meth:`txn` success/failure branch.

        Args:
            key: Key to delete.  Use with *range_end* for range deletions.
            range_end: Exclusive upper bound for a range deletion.
            prev_kv: If ``True``, include the previous key-value pairs in the response.

        Returns:
            ``RequestOp`` wrapping a ``DeleteRangeRequest``.
        """
        delete_request = DeleteRangeRequest(
            key=cls._to_bytes(key),
            range_end=cls._to_bytes(range_end) if range_end is not None else b'',
            prev_kv=prev_kv,
        )
        return RequestOp(request_delete_range=delete_request)

    @staticmethod
    def _to_bytes(data: BytesLike) -> bytes:
        return data.encode('utf-8') if isinstance(data, str) else data
