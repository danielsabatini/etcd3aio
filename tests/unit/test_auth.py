from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from etcd3aio._protobuf import (
    AuthDisableResponse,
    AuthEnableResponse,
    AuthenticateResponse,
    AuthRoleAddResponse,
    AuthRoleDeleteResponse,
    AuthRoleGetResponse,
    AuthRoleGrantPermissionResponse,
    AuthRoleListResponse,
    AuthRoleRevokePermissionResponse,
    AuthStatusResponse,
    AuthUserAddResponse,
    AuthUserChangePasswordResponse,
    AuthUserDeleteResponse,
    AuthUserGetResponse,
    AuthUserGrantRoleResponse,
    AuthUserListResponse,
    AuthUserRevokeRoleResponse,
)
from etcd3aio.auth import AuthService, PermissionType, TokenRefresher
from etcd3aio.errors import EtcdPermissionDeniedError, EtcdUnauthenticatedError
from etcd3aio.kv import KVService


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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.auth_status()

    assert result is response
    stub.AuthStatus.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_status_disabled() -> None:
    response = AuthStatusResponse(enabled=False, authRevision=0)

    stub = MagicMock()
    stub.AuthStatus = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        with pytest.raises(EtcdUnauthenticatedError, match='invalid username or password'):
            await service.authenticate('alice', 'wrong')


@pytest.mark.asyncio
async def test_authenticate_auth_not_enabled_raises_unauthenticated() -> None:
    stub = MagicMock()
    stub.Authenticate = AsyncMock(
        side_effect=_FakeRpcError(grpc.StatusCode.UNAUTHENTICATED, 'authentication is not enabled')
    )

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
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

    with patch('etcd3aio.kv.KVStub', return_value=stub):
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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
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

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        service.set_token('my-token')
        service.set_token(None)
        await service.auth_status()

    # metadata=None when empty tuple is falsy
    metadata = stub.AuthStatus.await_args.kwargs.get('metadata')
    assert metadata is None


# ---------------------------------------------------------------------------
# TokenRefresher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_refresher_authenticates_on_entry_and_clears_on_exit() -> None:
    """__aenter__ authenticates immediately; __aexit__ cancels task and clears token."""
    auth_service = MagicMock()
    auth_service.authenticate = AsyncMock(return_value=MagicMock(token='my-token'))

    tokens_applied: list[str | None] = []

    refresher = TokenRefresher(
        auth_service, tokens_applied.append, 'alice', 'secret', interval=3600
    )

    async with refresher:
        assert tokens_applied == ['my-token']
        assert refresher._task is not None
        assert not refresher._task.done()

    assert refresher._task is None
    assert tokens_applied[-1] is None  # set_token(None) called on exit
    auth_service.authenticate.assert_awaited_once_with('alice', 'secret')


@pytest.mark.asyncio
async def test_token_refresher_run_re_authenticates_at_interval() -> None:
    """_run() sleeps then re-authenticates and updates the token on each iteration."""
    auth_service = MagicMock()
    call_count = 0

    async def _authenticate(name: str, password: str, *, timeout: float | None = None) -> object:
        nonlocal call_count
        call_count += 1
        return MagicMock(token=f'token-{call_count}')

    auth_service.authenticate = _authenticate

    tokens_set: list[str | None] = []

    sleep_count = 0

    async def _fake_sleep(secs: float) -> None:
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 3:  # stop after two full iterations
            raise asyncio.CancelledError

    refresher = TokenRefresher(auth_service, tokens_set.append, 'alice', 'secret', interval=60)

    with patch('etcd3aio.auth.asyncio.sleep', new=_fake_sleep):
        with pytest.raises(asyncio.CancelledError):
            await refresher._run()

    assert tokens_set == ['token-1', 'token-2']


@pytest.mark.asyncio
async def test_token_refresher_handles_reauth_failure_gracefully() -> None:
    """A failed re-authentication logs a warning and the loop continues."""
    auth_service = MagicMock()
    call_count = 0

    async def _authenticate(name: str, password: str, *, timeout: float | None = None) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise EtcdUnauthenticatedError('transient failure')
        raise asyncio.CancelledError

    auth_service.authenticate = _authenticate
    tokens_set: list[str | None] = []

    async def _fake_sleep(secs: float) -> None:
        pass

    refresher = TokenRefresher(auth_service, tokens_set.append, 'alice', 'secret', interval=60)

    with patch('etcd3aio.auth.asyncio.sleep', new=_fake_sleep):
        with pytest.raises(asyncio.CancelledError):
            await refresher._run()

    assert tokens_set == []  # set_token never called because both attempts failed


# ---------------------------------------------------------------------------
# auth_enable / auth_disable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_enable_returns_response() -> None:
    response = AuthEnableResponse()
    stub = MagicMock()
    stub.AuthEnable = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.auth_enable()

    assert result is response
    stub.AuthEnable.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_disable_returns_response() -> None:
    response = AuthDisableResponse()
    stub = MagicMock()
    stub.AuthDisable = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.auth_disable()

    assert result is response
    stub.AuthDisable.assert_awaited_once()


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_add_sends_name_and_password() -> None:
    response = AuthUserAddResponse()
    stub = MagicMock()
    stub.UserAdd = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_add('alice', 'secret')

    assert result is response
    request = stub.UserAdd.await_args.args[0]
    assert request.name == 'alice'
    assert request.password == 'secret'
    assert not request.options.no_password


@pytest.mark.asyncio
async def test_user_add_no_password_sets_option() -> None:
    stub = MagicMock()
    stub.UserAdd = AsyncMock(return_value=AuthUserAddResponse())

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        await service.user_add('svc-account', '', no_password=True)

    request = stub.UserAdd.await_args.args[0]
    assert request.options.no_password is True


@pytest.mark.asyncio
async def test_user_get_sends_name() -> None:
    response = AuthUserGetResponse(roles=['admin', 'viewer'])
    stub = MagicMock()
    stub.UserGet = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_get('alice')

    assert result is response
    request = stub.UserGet.await_args.args[0]
    assert request.name == 'alice'


@pytest.mark.asyncio
async def test_user_list_returns_response() -> None:
    response = AuthUserListResponse(users=['alice', 'bob'])
    stub = MagicMock()
    stub.UserList = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_list()

    assert result is response
    assert list(result.users) == ['alice', 'bob']


@pytest.mark.asyncio
async def test_user_delete_sends_name() -> None:
    response = AuthUserDeleteResponse()
    stub = MagicMock()
    stub.UserDelete = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_delete('alice')

    assert result is response
    request = stub.UserDelete.await_args.args[0]
    assert request.name == 'alice'


@pytest.mark.asyncio
async def test_user_change_password_sends_name_and_password() -> None:
    response = AuthUserChangePasswordResponse()
    stub = MagicMock()
    stub.UserChangePassword = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_change_password('alice', 'new-secret')

    assert result is response
    request = stub.UserChangePassword.await_args.args[0]
    assert request.name == 'alice'
    assert request.password == 'new-secret'


@pytest.mark.asyncio
async def test_user_grant_role_sends_user_and_role() -> None:
    response = AuthUserGrantRoleResponse()
    stub = MagicMock()
    stub.UserGrantRole = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_grant_role('alice', 'admin')

    assert result is response
    request = stub.UserGrantRole.await_args.args[0]
    assert request.user == 'alice'
    assert request.role == 'admin'


@pytest.mark.asyncio
async def test_user_revoke_role_sends_name_and_role() -> None:
    response = AuthUserRevokeRoleResponse()
    stub = MagicMock()
    stub.UserRevokeRole = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.user_revoke_role('alice', 'admin')

    assert result is response
    request = stub.UserRevokeRole.await_args.args[0]
    assert request.name == 'alice'
    assert request.role == 'admin'


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_role_add_sends_name() -> None:
    response = AuthRoleAddResponse()
    stub = MagicMock()
    stub.RoleAdd = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_add('admin')

    assert result is response
    request = stub.RoleAdd.await_args.args[0]
    assert request.name == 'admin'


@pytest.mark.asyncio
async def test_role_get_returns_permissions() -> None:
    response = AuthRoleGetResponse()
    stub = MagicMock()
    stub.RoleGet = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_get('admin')

    assert result is response
    request = stub.RoleGet.await_args.args[0]
    assert request.role == 'admin'


@pytest.mark.asyncio
async def test_role_list_returns_response() -> None:
    response = AuthRoleListResponse(roles=['admin', 'viewer'])
    stub = MagicMock()
    stub.RoleList = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_list()

    assert result is response
    assert list(result.roles) == ['admin', 'viewer']


@pytest.mark.asyncio
async def test_role_delete_sends_role() -> None:
    response = AuthRoleDeleteResponse()
    stub = MagicMock()
    stub.RoleDelete = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_delete('admin')

    assert result is response
    request = stub.RoleDelete.await_args.args[0]
    assert request.role == 'admin'


@pytest.mark.asyncio
async def test_role_grant_permission_single_key() -> None:
    response = AuthRoleGrantPermissionResponse()
    stub = MagicMock()
    stub.RoleGrantPermission = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_grant_permission(
            'admin', '/config/db', perm_type=PermissionType.READWRITE
        )

    assert result is response
    request = stub.RoleGrantPermission.await_args.args[0]
    assert request.name == 'admin'
    assert request.perm.key == b'/config/db'
    assert request.perm.range_end == b''
    assert request.perm.permType == PermissionType.READWRITE


@pytest.mark.asyncio
async def test_role_grant_permission_range() -> None:
    stub = MagicMock()
    stub.RoleGrantPermission = AsyncMock(return_value=AuthRoleGrantPermissionResponse())

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        await service.role_grant_permission(
            'viewer', b'/logs/', b'/logs0', perm_type=PermissionType.READ
        )

    request = stub.RoleGrantPermission.await_args.args[0]
    assert request.perm.key == b'/logs/'
    assert request.perm.range_end == b'/logs0'
    assert request.perm.permType == PermissionType.READ


@pytest.mark.asyncio
async def test_role_revoke_permission_sends_role_and_key() -> None:
    response = AuthRoleRevokePermissionResponse()
    stub = MagicMock()
    stub.RoleRevokePermission = AsyncMock(return_value=response)

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        result = await service.role_revoke_permission('admin', '/config/db')

    assert result is response
    request = stub.RoleRevokePermission.await_args.args[0]
    assert request.role == 'admin'
    assert request.key == b'/config/db'
    assert request.range_end == b''


@pytest.mark.asyncio
async def test_role_revoke_permission_with_range() -> None:
    stub = MagicMock()
    stub.RoleRevokePermission = AsyncMock(return_value=AuthRoleRevokePermissionResponse())

    with patch('etcd3aio.auth.AuthStub', return_value=stub):
        service = AuthService(channel=MagicMock())
        await service.role_revoke_permission('viewer', b'/logs/', b'/logs0')

    request = stub.RoleRevokePermission.await_args.args[0]
    assert request.key == b'/logs/'
    assert request.range_end == b'/logs0'
