from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.auth import AuthService, PermissionType
from etcd3aio.client import Etcd3Client
from etcd3aio.errors import EtcdUnauthenticatedError
from etcd3aio.kv import prefix_range_end

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Auth example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    parser.add_argument('--username', default=None, help='etcd username (optional).')
    parser.add_argument('--password', default=None, help='etcd password (optional).')
    parser.add_argument(
        '--admin',
        action='store_true',
        help='Run admin operations (user/role management). Requires root credentials.',
    )
    return parser.parse_args()


async def run_auth_status(auth: AuthService) -> bool:
    status = await auth.auth_status()
    print(f'Auth status -> enabled={status.enabled}, authRevision={status.authRevision}')
    return bool(status.enabled)


async def run_authenticate(client: Etcd3Client, username: str, password: str) -> None:
    if client.auth is None:
        raise RuntimeError('auth service is not initialized')

    resp = await client.auth.authenticate(username, password)
    print(f'Authenticate -> token obtained ({len(resp.token)} chars)')

    # Propagate the token to all services
    client.set_token(resp.token)
    print('set_token() -> token applied to all services')

    if client.kv is None:
        raise RuntimeError('kv service is not initialized')
    await client.kv.get('__etcd3aio:auth-check')
    print('KV get with token -> ok')

    client.set_token(None)
    print('set_token(None) -> token cleared')


async def run_token_refresher(client: Etcd3Client, username: str, password: str) -> None:
    async with client.token_refresher(username, password):
        print('token_refresher -> authenticated, background refresh running')

        if client.kv is None:
            raise RuntimeError('kv service is not initialized')
        await client.kv.get('__etcd3aio:refresh-check')
        print('KV get with auto-token -> ok')

    print('token_refresher -> context exited, token cleared')


async def run_admin_example(auth: AuthService) -> None:
    """Demonstrates full user and role management.

    Assumes the client is already authenticated as root (or auth is disabled).
    All created resources are cleaned up at the end.
    """
    role = 'example-viewer'
    user = 'example-user'
    password = 'example-pass'
    key_prefix = '/example/'

    # --- Role management ---
    await auth.role_add(role)
    print(f'role_add({role!r}) -> ok')

    # Grant read-only access to /example/ prefix
    await auth.role_grant_permission(
        role,
        key_prefix,
        prefix_range_end(key_prefix),
        perm_type=PermissionType.READ,
    )
    print(f'role_grant_permission({role!r}, {key_prefix!r}, READ) -> ok')

    role_info = await auth.role_get(role)
    print(f'role_get({role!r}) -> {len(role_info.perm)} permission(s)')

    roles_resp = await auth.role_list()
    print(f'role_list() -> {list(roles_resp.roles)}')

    # --- User management ---
    await auth.user_add(user, password)
    print(f'user_add({user!r}) -> ok')

    await auth.user_grant_role(user, role)
    print(f'user_grant_role({user!r}, {role!r}) -> ok')

    user_info = await auth.user_get(user)
    print(f'user_get({user!r}) -> roles={list(user_info.roles)}')

    users_resp = await auth.user_list()
    print(f'user_list() -> {list(users_resp.users)}')

    await auth.user_change_password(user, 'new-example-pass')
    print(f'user_change_password({user!r}) -> ok')

    # --- Cleanup ---
    await auth.user_revoke_role(user, role)
    print(f'user_revoke_role({user!r}, {role!r}) -> ok')

    await auth.user_delete(user)
    print(f'user_delete({user!r}) -> ok')

    await auth.role_revoke_permission(role, key_prefix, prefix_range_end(key_prefix))
    print(f'role_revoke_permission({role!r}, {key_prefix!r}) -> ok')

    await auth.role_delete(role)
    print(f'role_delete({role!r}) -> ok')


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        if client.auth is None:
            raise RuntimeError('auth service is not initialized')

        enabled = await run_auth_status(client.auth)

        if args.username and args.password:
            try:
                await run_authenticate(client, args.username, args.password)
                await run_token_refresher(client, args.username, args.password)
            except EtcdUnauthenticatedError:
                print('Authenticate -> failed (invalid credentials or auth not enabled)')

        elif enabled:
            print('Auth is enabled; pass --username and --password to test authentication.')
        else:
            print('Auth is disabled; use --username/--password on an auth-enabled cluster.')

        if args.admin:
            print('\n--- Admin operations ---')
            await run_admin_example(client.auth)


if __name__ == '__main__':
    asyncio.run(main())
