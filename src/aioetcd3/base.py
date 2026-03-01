from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeAlias, TypeVar

import grpc

from .errors import (
    EtcdConnectionError,
    EtcdPermissionDeniedError,
    EtcdTransientError,
    EtcdUnauthenticatedError,
)

RequestT = TypeVar('RequestT')
ResponseT = TypeVar('ResponseT')
UnaryRpcCall: TypeAlias = Callable[[RequestT], Awaitable[ResponseT]]
TransientCodes: TypeAlias = tuple[grpc.StatusCode, ...]
TRANSIENT_CODES: TransientCodes = (
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
)


class BaseService:
    """Shared RPC helpers for unary etcd calls."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 0.05,
        max_backoff_seconds: float = 1.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError('max_attempts must be >= 1')
        if initial_backoff_seconds <= 0:
            raise ValueError('initial_backoff_seconds must be > 0')
        if max_backoff_seconds < initial_backoff_seconds:
            raise ValueError('max_backoff_seconds must be >= initial_backoff_seconds')

        self._max_attempts = max_attempts
        self._initial_backoff_seconds = initial_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds

    @staticmethod
    def _is_transient_error(exc: grpc.aio.AioRpcError) -> bool:
        return exc.code() in TRANSIENT_CODES

    async def _rpc(
        self,
        call: UnaryRpcCall[RequestT, ResponseT],
        request: RequestT,
        *,
        operation: str,
    ) -> ResponseT:
        backoff_seconds = self._initial_backoff_seconds

        for attempt in range(1, self._max_attempts + 1):
            try:
                return await call(request)
            except grpc.aio.AioRpcError as exc:
                is_last_attempt = attempt == self._max_attempts
                if not self._is_transient_error(exc) or is_last_attempt:
                    if self._is_transient_error(exc):
                        detail = exc.details() or ''
                        suffix = f' ({detail})' if detail else ''
                        message = (
                            f'{operation} failed after {self._max_attempts} attempts: '
                            f'{exc.code().name}{suffix}'
                        )
                        if exc.code() == grpc.StatusCode.UNAVAILABLE:
                            raise EtcdConnectionError(message) from exc
                        raise EtcdTransientError(message) from exc
                    detail = exc.details() or ''
                    suffix = f': {detail}' if detail else ''
                    if exc.code() == grpc.StatusCode.UNAUTHENTICATED:
                        raise EtcdUnauthenticatedError(f'{operation} failed{suffix}') from exc
                    if exc.code() == grpc.StatusCode.PERMISSION_DENIED:
                        raise EtcdPermissionDeniedError(f'{operation} failed{suffix}') from exc
                    raise

                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, self._max_backoff_seconds)

        raise RuntimeError('unreachable')
