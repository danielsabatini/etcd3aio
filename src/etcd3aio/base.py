from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import NoReturn, TypeAlias, TypeVar

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

# gRPC metadata type: sequence of (key, value) string pairs.
# Used to inject auth tokens into every outgoing call.
_Metadata: TypeAlias = tuple[tuple[str, str], ...]


class BaseService:
    """Shared retry logic and token management for all service classes.

    Provides :meth:`_rpc` — the single entry point for every unary gRPC call
    in the library.  All service modules inherit from this class instead of
    duplicating retry logic.

    Args:
        max_attempts: Maximum retry attempts for transient errors.
        initial_backoff_seconds: Starting delay between retries (doubles on
            each attempt up to *max_backoff_seconds*).
        max_backoff_seconds: Upper cap on the retry backoff delay.
    """

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
        self._metadata: _Metadata = ()

    def set_token(self, token: str | None) -> None:
        """Set the auth token sent as gRPC metadata on every subsequent call."""
        self._metadata = (('token', token),) if token else ()

    @staticmethod
    def _is_transient_error(exc: grpc.aio.AioRpcError) -> bool:
        """Return ``True`` if *exc* has a status code that warrants a retry."""
        return exc.code() in TRANSIENT_CODES

    @staticmethod
    def _raise_rpc_exception(
        exc: grpc.aio.AioRpcError,
        operation: str,
        *,
        attempts: int,
    ) -> NoReturn:
        """Map *exc* to a library exception and raise it.  Always raises.

        Args:
            exc: The original gRPC error.
            operation: Human-readable label used in error messages.
            attempts: Number of attempts made (used in transient error messages).
        """
        detail = exc.details() or ''
        if exc.code() == grpc.StatusCode.UNAUTHENTICATED:
            suffix = f': {detail}' if detail else ''
            raise EtcdUnauthenticatedError(f'{operation} failed{suffix}') from exc
        if exc.code() == grpc.StatusCode.PERMISSION_DENIED:
            suffix = f': {detail}' if detail else ''
            raise EtcdPermissionDeniedError(f'{operation} failed{suffix}') from exc
        if exc.code() in TRANSIENT_CODES:
            suffix = f' ({detail})' if detail else ''
            message = f'{operation} failed after {attempts} attempts: {exc.code().name}{suffix}'
            if exc.code() == grpc.StatusCode.UNAVAILABLE:
                raise EtcdConnectionError(message) from exc
            raise EtcdTransientError(message) from exc
        raise exc

    async def _rpc(
        self,
        call: UnaryRpcCall[RequestT, ResponseT],
        request: RequestT,
        *,
        operation: str,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> ResponseT:
        """Execute a unary gRPC call with retry and error mapping.

        Wraps *call* in an ``asyncio.timeout`` and retries on transient status
        codes (``UNAVAILABLE``, ``DEADLINE_EXCEEDED``) with exponential backoff.
        Non-transient status codes are mapped to library exceptions via
        :meth:`_raise_rpc_exception`.

        Args:
            call: The gRPC stub method to invoke.
            request: Protobuf request object.
            operation: Human-readable label used in error messages (e.g. ``'KV.Put'``).
            timeout: Per-attempt gRPC deadline in seconds (``None`` = no deadline).
                The ``asyncio.timeout`` wrapper also bounds the total retry loop.
            max_attempts: Override the service-level retry limit for this call
                only (``None`` uses the value set on the service instance).
        """
        effective_attempts = max_attempts if max_attempts is not None else self._max_attempts
        async with asyncio.timeout(timeout):
            backoff_seconds = self._initial_backoff_seconds

            for attempt in range(1, effective_attempts + 1):
                try:
                    return await call(request, metadata=self._metadata or None, timeout=timeout)  # type: ignore[call-arg]
                except grpc.aio.AioRpcError as exc:
                    is_last_attempt = attempt == effective_attempts
                    if not self._is_transient_error(exc) or is_last_attempt:
                        self._raise_rpc_exception(exc, operation, attempts=effective_attempts)
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds = min(backoff_seconds * 2, self._max_backoff_seconds)

        raise RuntimeError('unreachable')
