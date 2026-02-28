from __future__ import annotations

import argparse
import asyncio

from aioetcd3.client import Etcd3Client
from aioetcd3.kv import KVService
from aioetcd3.lease import LeaseService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Lease example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    parser.add_argument('--ttl', type=int, default=15, help='Lease TTL in seconds.')
    return parser.parse_args()


async def run_lease_example(kv: KVService, lease: LeaseService, ttl: int) -> None:
    key = 'example:lease:module'

    lease_response = await lease.grant(ttl=ttl)
    lease_id = lease_response.ID
    print(f'Lease grant -> lease_id={lease_id}, requested_ttl={ttl}')

    await kv.put(key, 'leased-value', lease=lease_id)
    ttl_response = await lease.time_to_live(lease_id)
    print(f'Lease ttl -> current_ttl={ttl_response.TTL}, granted_ttl={ttl_response.grantedTTL}')

    await lease.revoke(lease_id)
    await kv.delete(key)
    print('Lease revoke -> ok')


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        lease = client.lease

        if kv is None or lease is None:
            raise RuntimeError('kv or lease service is not initialized')

        await run_lease_example(kv, lease, ttl=args.ttl)


if __name__ == '__main__':
    asyncio.run(main())
