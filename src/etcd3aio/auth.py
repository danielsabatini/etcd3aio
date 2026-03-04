from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from enum import IntEnum
from types import TracebackType

import grpc.aio

from ._protobuf import (
    AuthDisableRequest,
    AuthDisableResponse,
    AuthEnableRequest,
    AuthEnableResponse,
    AuthenticateRequest,
    AuthenticateResponse,
    AuthRoleAddRequest,
    AuthRoleAddResponse,
    AuthRoleDeleteRequest,
    AuthRoleDeleteResponse,
    AuthRoleGetRequest,
    AuthRoleGetResponse,
    AuthRoleGrantPermissionRequest,
    AuthRoleGrantPermissionResponse,
    AuthRoleListRequest,
    AuthRoleListResponse,
    AuthRoleRevokePermissionRequest,
    AuthRoleRevokePermissionResponse,
    AuthStatusRequest,
    AuthStatusResponse,
    AuthStub,
    AuthUserAddRequest,
    AuthUserAddResponse,
    AuthUserChangePasswordRequest,
    AuthUserChangePasswordResponse,
    AuthUserDeleteRequest,
    AuthUserDeleteResponse,
    AuthUserGetRequest,
    AuthUserGetResponse,
    AuthUserGrantRoleRequest,
    AuthUserGrantRoleResponse,
    AuthUserListRequest,
    AuthUserListResponse,
    AuthUserRevokeRoleRequest,
    AuthUserRevokeRoleResponse,
    Permission,
    UserAddOptions,
)
from .base import BaseService

_log = logging.getLogger(__name__)

BytesLike = str | bytes


def _to_bytes(data: BytesLike) -> bytes:
    return data.encode('utf-8') if isinstance(data, str) else data


class PermissionType(IntEnum):
    """Key permission type used in :meth:`AuthService.role_grant_permission`."""

    READ = 0
    WRITE = 1
    READWRITE = 2


class AuthService(BaseService):
    """Auth facade: authentication, user management and role management.

    Covers the full etcd Auth API:

    - **Authentication**: :meth:`auth_status`, :meth:`authenticate`,
      :meth:`auth_enable`, :meth:`auth_disable`.
    - **Users**: :meth:`user_add`, :meth:`user_get`, :meth:`user_list`,
      :meth:`user_delete`, :meth:`user_change_password`,
      :meth:`user_grant_role`, :meth:`user_revoke_role`.
    - **Roles**: :meth:`role_add`, :meth:`role_get`, :meth:`role_list`,
      :meth:`role_delete`, :meth:`role_grant_permission`,
      :meth:`role_revoke_permission`.
    """

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = AuthStub(channel)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def auth_status(self, *, timeout: float | None = None) -> AuthStatusResponse:
        """Return the current authentication status of the cluster.

        The response includes:
        - ``enabled``: whether auth is currently enabled.
        - ``authRevision``: the current auth revision.
        """
        return await self._rpc(
            self._stub.AuthStatus,
            AuthStatusRequest(),
            operation='Auth.Status',
            timeout=timeout,
        )

    async def authenticate(
        self, name: str, password: str, *, timeout: float | None = None
    ) -> AuthenticateResponse:
        """Obtain a token for the given credentials.

        The returned ``token`` should be attached to subsequent calls via
        :meth:`~etcd3aio.Etcd3Client.set_token`.

        Raises:
            EtcdUnauthenticatedError: credentials are invalid or auth is not enabled.
        """
        return await self._rpc(
            self._stub.Authenticate,
            AuthenticateRequest(name=name, password=password),
            operation='Auth.Authenticate',
            timeout=timeout,
        )

    async def auth_enable(self, *, timeout: float | None = None) -> AuthEnableResponse:
        """Enable authentication on the cluster.

        Once enabled, all RPCs require a valid token obtained via
        :meth:`authenticate`.  The root user must exist before calling this.
        """
        return await self._rpc(
            self._stub.AuthEnable,
            AuthEnableRequest(),
            operation='Auth.Enable',
            timeout=timeout,
        )

    async def auth_disable(self, *, timeout: float | None = None) -> AuthDisableResponse:
        """Disable authentication on the cluster."""
        return await self._rpc(
            self._stub.AuthDisable,
            AuthDisableRequest(),
            operation='Auth.Disable',
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    async def user_add(
        self,
        name: str,
        password: str = '',
        *,
        no_password: bool = False,
        timeout: float | None = None,
    ) -> AuthUserAddResponse:
        """Create a new user.

        Args:
            name: Username.
            password: Plaintext password.  Ignored when *no_password* is
                ``True``.
            no_password: Create a user that authenticates without a password
                (e.g. for certificate-based auth).
        """
        options = UserAddOptions(no_password=no_password)
        return await self._rpc(
            self._stub.UserAdd,
            AuthUserAddRequest(name=name, password=password, options=options),
            operation='Auth.UserAdd',
            timeout=timeout,
        )

    async def user_get(self, name: str, *, timeout: float | None = None) -> AuthUserGetResponse:
        """Return the roles assigned to *name*.

        Response field ``roles`` is a list of role name strings.
        """
        return await self._rpc(
            self._stub.UserGet,
            AuthUserGetRequest(name=name),
            operation='Auth.UserGet',
            timeout=timeout,
        )

    async def user_list(self, *, timeout: float | None = None) -> AuthUserListResponse:
        """Return all users in the cluster.

        Response field ``users`` is a list of username strings.
        """
        return await self._rpc(
            self._stub.UserList,
            AuthUserListRequest(),
            operation='Auth.UserList',
            timeout=timeout,
        )

    async def user_delete(
        self, name: str, *, timeout: float | None = None
    ) -> AuthUserDeleteResponse:
        """Delete the user identified by *name*."""
        return await self._rpc(
            self._stub.UserDelete,
            AuthUserDeleteRequest(name=name),
            operation='Auth.UserDelete',
            timeout=timeout,
        )

    async def user_change_password(
        self, name: str, password: str, *, timeout: float | None = None
    ) -> AuthUserChangePasswordResponse:
        """Change the password for *name*."""
        return await self._rpc(
            self._stub.UserChangePassword,
            AuthUserChangePasswordRequest(name=name, password=password),
            operation='Auth.UserChangePassword',
            timeout=timeout,
        )

    async def user_grant_role(
        self, user: str, role: str, *, timeout: float | None = None
    ) -> AuthUserGrantRoleResponse:
        """Grant *role* to *user*."""
        return await self._rpc(
            self._stub.UserGrantRole,
            AuthUserGrantRoleRequest(user=user, role=role),
            operation='Auth.UserGrantRole',
            timeout=timeout,
        )

    async def user_revoke_role(
        self, name: str, role: str, *, timeout: float | None = None
    ) -> AuthUserRevokeRoleResponse:
        """Revoke *role* from the user identified by *name*."""
        return await self._rpc(
            self._stub.UserRevokeRole,
            AuthUserRevokeRoleRequest(name=name, role=role),
            operation='Auth.UserRevokeRole',
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Role management
    # ------------------------------------------------------------------

    async def role_add(self, name: str, *, timeout: float | None = None) -> AuthRoleAddResponse:
        """Create a new role identified by *name*."""
        return await self._rpc(
            self._stub.RoleAdd,
            AuthRoleAddRequest(name=name),
            operation='Auth.RoleAdd',
            timeout=timeout,
        )

    async def role_get(self, role: str, *, timeout: float | None = None) -> AuthRoleGetResponse:
        """Return the permissions associated with *role*.

        Response field ``perm`` is a list of ``Permission`` objects, each with
        ``permType``, ``key`` and ``range_end``.
        """
        return await self._rpc(
            self._stub.RoleGet,
            AuthRoleGetRequest(role=role),
            operation='Auth.RoleGet',
            timeout=timeout,
        )

    async def role_list(self, *, timeout: float | None = None) -> AuthRoleListResponse:
        """Return all roles in the cluster.

        Response field ``roles`` is a list of role name strings.
        """
        return await self._rpc(
            self._stub.RoleList,
            AuthRoleListRequest(),
            operation='Auth.RoleList',
            timeout=timeout,
        )

    async def role_delete(
        self, role: str, *, timeout: float | None = None
    ) -> AuthRoleDeleteResponse:
        """Delete the role identified by *role*."""
        return await self._rpc(
            self._stub.RoleDelete,
            AuthRoleDeleteRequest(role=role),
            operation='Auth.RoleDelete',
            timeout=timeout,
        )

    async def role_grant_permission(
        self,
        role: str,
        key: BytesLike,
        range_end: BytesLike | None = None,
        *,
        perm_type: PermissionType = PermissionType.READ,
        timeout: float | None = None,
    ) -> AuthRoleGrantPermissionResponse:
        """Grant a key permission to *role*.

        Args:
            role: Name of the role to update.
            key: Key (or range start) the permission applies to.
            range_end: Exclusive upper bound for a range permission.  Use
                :func:`~etcd3aio.prefix_range_end` for prefix-scoped
                permissions.  ``None`` means a single-key permission.
            perm_type: :class:`PermissionType` — ``READ``, ``WRITE`` or
                ``READWRITE``.
        """
        perm = Permission(
            permType=int(perm_type),
            key=_to_bytes(key),
            range_end=_to_bytes(range_end) if range_end is not None else b'',
        )
        return await self._rpc(
            self._stub.RoleGrantPermission,
            AuthRoleGrantPermissionRequest(name=role, perm=perm),
            operation='Auth.RoleGrantPermission',
            timeout=timeout,
        )

    async def role_revoke_permission(
        self,
        role: str,
        key: BytesLike,
        range_end: BytesLike | None = None,
        *,
        timeout: float | None = None,
    ) -> AuthRoleRevokePermissionResponse:
        """Revoke a key permission from *role*.

        Args:
            role: Name of the role to update.
            key: Key (or range start) the permission applies to.
            range_end: Exclusive upper bound for the range.  ``None`` means
                single-key.
        """
        return await self._rpc(
            self._stub.RoleRevokePermission,
            AuthRoleRevokePermissionRequest(
                role=role,
                key=_to_bytes(key),
                range_end=_to_bytes(range_end) if range_end is not None else b'',
            ),
            operation='Auth.RoleRevokePermission',
            timeout=timeout,
        )


class TokenRefresher:
    """Background context manager that keeps an auth token fresh.

    Authenticates immediately on entry, stores the token via ``set_token``,
    and then re-authenticates every ``interval`` seconds so the token never
    expires.  On exit the background task is cancelled cleanly.

    etcd's default token TTL is 5 minutes (300 s); the default interval of
    240 s gives a 60-second safety margin.

    Usage::

        async with client.token_refresher('alice', 'secret') as tr:
            # client.set_token() was called with the fresh token
            await client.kv.put('key', 'value')
        # background task stopped; token cleared from all services

    If a refresh attempt fails (e.g. transient network error), the previous
    token remains active and the error is logged.  If credentials become
    invalid the task stops and raises ``EtcdUnauthenticatedError`` on the
    next background iteration — the outer code will detect service failures
    on subsequent RPC calls.
    """

    def __init__(
        self,
        auth: AuthService,
        set_token: Callable[[str | None], None],
        name: str,
        password: str,
        *,
        interval: float = 240.0,
    ) -> None:
        if interval <= 0:
            raise ValueError('interval must be > 0')
        self._auth = auth
        self._set_token = set_token
        self._name = name
        self._password = password
        self._interval = interval
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> TokenRefresher:
        resp = await self._auth.authenticate(self._name, self._password)
        self._set_token(resp.token)
        self._task = asyncio.create_task(self._run(), name='token-refresher')
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._set_token(None)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                resp = await self._auth.authenticate(self._name, self._password)
                self._set_token(resp.token)
            except Exception:
                _log.warning('token-refresher: re-authentication failed', exc_info=True)
