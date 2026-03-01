from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from etcd3aio.client import Etcd3Client
from etcd3aio.connections import ConnectionManager
from etcd3aio.kv import KVService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Check etcd endpoints and run cluster smoke test.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379', 'localhost:3379', 'localhost:4379'],
        help='List of etcd endpoints in host:port format.',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=3.0,
        help='Timeout in seconds for endpoint readiness.',
    )
    return parser.parse_args()


async def check_endpoint(endpoint: str, timeout: float) -> bool:
    manager = ConnectionManager([endpoint])
    channel = await manager.get_channel()

    try:
        await asyncio.wait_for(channel.channel_ready(), timeout=timeout)
        return True
    except (TimeoutError, asyncio.TimeoutError):
        return False
    finally:
        await channel.close()


async def run_cluster_smoke(endpoints: Sequence[str]) -> None:
    async with Etcd3Client(endpoints) as client:
        kv = client.kv
        if kv is None:
            raise RuntimeError('kv service is not initialized')

        await _kv_smoke(kv)


async def _kv_smoke(kv: KVService) -> None:
    key = 'health:smoke'
    value = 'ok'

    await kv.put(key, value)
    response = await kv.get(key)

    if not response.kvs:
        raise RuntimeError('cluster smoke test failed: key not found after put')

    await kv.delete(key)
    print('Cluster KV smoke test passed.')


async def main() -> None:
    args = parse_args()
    endpoints = list(args.endpoints)

    print('Checking endpoints:')
    results = await asyncio.gather(
        *(check_endpoint(endpoint, args.timeout) for endpoint in endpoints)
    )

    for endpoint, ok in zip(endpoints, results, strict=True):
        status = 'ok' if ok else 'failed'
        print(f'  - {endpoint}: {status}')

    if not any(results):
        raise RuntimeError('no endpoint became ready')

    await run_cluster_smoke(endpoints)


if __name__ == '__main__':
    asyncio.run(main())
