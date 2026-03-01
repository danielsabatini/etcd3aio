from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from aioetcd3._protobuf import AuthenticateResponse, AuthStatusResponse
from aioetcd3.auth import AuthService
from aioetcd3.errors import EtcdPermissionDeniedError, EtcdUnauthenticatedError
from aioetcd3.kv import KVService


class _FakeRpcError(grpc.aio.AioRpcError):
    def __init__(self, status_code: grpc.StatusCode, details: str = '') -> None:
        self._status_code = status_code
        self._details = details

    def code(self) -> grpc.StatusCode:
        return self._status_code

    def details(self) -> str:
        return self._details


# ---------------------------------------------------------------------------
# auth_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_status_returns_response() -> None:
    response = AuthStatusResponse(enabled=True, authRevision=5)

    stub = MagicMock()
    stub.AuthStatus = AsyncMock(return_value=response)

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.auth_status()

    assert result is response
    stub.AuthStatus.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_status_disabled() -> None:
    response = AuthStatusResponse(enabled=False, authRevision=0)

    stub = MagicMock()
    stub.AuthStatus = AsyncMock(return_value=response)

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.auth_status()

    assert result.enabled is False


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_returns_token() -> None:
    response = AuthenticateResponse(token='my-token-abc')

    stub = MagicMock()
    stub.Authenticate = AsyncMock(return_value=response)

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.authenticate('alice', 'secret')

    assert result.token == 'my-token-abc'
    request = stub.Authenticate.await_args.args[0]
    assert request.name == 'alice'
    assert request.password == 'secret'


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials_raises_unauthenticated() -> None:
    stub = MagicMock()
    stub.Authenticate = AsyncMock(
        side_effect=_FakeRpcError(grpc.StatusCode.UNAUTHENTICATED, 'invalid username or password')
    )

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        with pytest.raises(EtcdUnauthenticatedError, match='invalid username or password'):
            await service.authenticate('alice', 'wrong')


@pytest.mark.asyncio
async def test_authenticate_auth_not_enabled_raises_unauthenticated() -> None:
    stub = MagicMock()
    stub.Authenticate = AsyncMock(
        side_effect=_FakeRpcError(grpc.StatusCode.UNAUTHENTICATED, 'authentication is not enabled')
    )

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        with pytest.raises(EtcdUnauthenticatedError, match='authentication is not enabled'):
            await service.authenticate('alice', 'secret')


# ---------------------------------------------------------------------------
# Permission denied — mapped from any service via base._rpc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permission_denied_raises_etcd_error() -> None:
    stub = MagicMock()
    stub.AuthStatus = AsyncMock(
        side_effect=_FakeRpcError(
            grpc.StatusCode.PERMISSION_DENIED, 'etcdserver: permission denied'
        )
    )

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        with pytest.raises(EtcdPermissionDeniedError, match='permission denied'):
            await service.auth_status()


# ---------------------------------------------------------------------------
# Missing/expired token on a KV call — mapped via base._rpc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_token_on_kv_raises_unauthenticated() -> None:
    """UNAUTHENTICATED from any service maps to EtcdUnauthenticatedError."""
    stub = MagicMock()
    stub.Range = AsyncMock(
        side_effect=_FakeRpcError(grpc.StatusCode.UNAUTHENTICATED, 'invalid auth token')
    )

    with patch('aioetcd3.kv.KVStub', return_value=stub):
        service = KVService(channel=MagicMock())
        with pytest.raises(EtcdUnauthenticatedError, match='invalid auth token'):
            await service.get('key')


# ---------------------------------------------------------------------------
# Token injection via set_token()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_token_injects_metadata_into_rpc_call() -> None:
    """After set_token(), every gRPC call carries the token in metadata."""
    response = AuthStatusResponse(enabled=True)
    stub = MagicMock()
    stub.AuthStatus = AsyncMock(return_value=response)

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        service.set_token('my-token')
        await service.auth_status()

    metadata = stub.AuthStatus.await_args.kwargs.get('metadata')
    assert metadata == (('token', 'my-token'),)


@pytest.mark.asyncio
async def test_set_token_none_clears_metadata() -> None:
    response = AuthStatusResponse(enabled=True)
    stub = MagicMock()
    stub.AuthStatus = AsyncMock(return_value=response)

    with patch('aioetcd3.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        service.set_token('my-token')
        service.set_token(None)
        await service.auth_status()

    # metadata=None when empty tuple is falsy
    metadata = stub.AuthStatus.await_args.kwargs.get('metadata')
    assert metadata is None
