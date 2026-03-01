from __future__ import annotations

import argparse
import asyncio

from etcd3aio.auth import AuthService
from etcd3aio.client import Etcd3Client
from etcd3aio.errors import EtcdUnauthenticatedError


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


if __name__ == '__main__':
    asyncio.run(main())
