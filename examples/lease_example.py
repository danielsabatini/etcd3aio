from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import cast

from etcd3aio._protobuf import WatchResponse
from etcd3aio.client import Etcd3Client
from etcd3aio.kv import KVService
from etcd3aio.lease import LeaseService
from etcd3aio.watch import WatchService

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


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

    # Grant a lease and attach a key to it
    lease_response = await lease.grant(ttl=ttl)
    lease_id = lease_response.ID
    print(f'Lease grant -> lease_id={lease_id}, requested_ttl={ttl}')

    await kv.put(key, 'leased-value', lease=lease_id)

    # Time to live — pass keys=True to include attached key names
    ttl_response = await lease.time_to_live(lease_id, keys=True)
    attached = [k.decode() for k in ttl_response.keys]
    print(
        f'Lease ttl -> current_ttl={ttl_response.TTL}, '
        f'granted_ttl={ttl_response.grantedTTL}, keys={attached}'
    )

    # List all active leases in the cluster
    leases_response = await lease.leases()
    lease_ids = [lr.ID for lr in leases_response.leases]
    print(f'Lease leases() -> active ids={lease_ids}')

    # Background keep-alive context manager
    async with lease.keep_alive_context(lease_id, ttl) as ka:
        print(f'keep_alive_context -> running, alive={ka.alive}')
        await asyncio.sleep(0.1)  # keepalive loop is active during this block

    print('keep_alive_context -> stopped')

    # Revoke the lease (also removes the attached key)
    await lease.revoke(lease_id)
    print('Lease revoke -> ok')


async def run_watch_on_expire(kv: KVService, lease: LeaseService, watch: WatchService) -> None:
    """Grant a short-lived lease, attach a key and watch for the auto-DELETE on expiry."""
    ttl = 4
    key = 'example:lease:expiry-watch'

    expire_resp = await lease.grant(ttl=ttl)
    expire_id = expire_resp.ID
    print(f'\nLease grant (expiry demo) -> lease_id={expire_id}, ttl={ttl}s')

    await kv.put(key, 'will-expire', lease=expire_id)
    print(f'Watching {key!r} — waiting up to {ttl + 5}s for natural expiry...')

    watch_gen = cast(AsyncGenerator[WatchResponse, None], watch.watch(key))
    try:
        while True:
            response = await asyncio.wait_for(anext(watch_gen), timeout=ttl + 5)
            if response.events:
                event = response.events[0]
                # EventType: 0=PUT, 1=DELETE
                print(f'Watch on expire -> type={event.type} (DELETE), key={event.kv.key.decode()}')
                break
    finally:
        await watch_gen.aclose()


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        lease = client.lease
        watch = client.watch

        if kv is None or lease is None or watch is None:
            raise RuntimeError('kv, lease or watch service is not initialized')

        await run_lease_example(kv, lease, ttl=args.ttl)
        await run_watch_on_expire(kv, lease, watch)


if __name__ == '__main__':
    asyncio.run(main())
