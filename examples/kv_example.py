from __future__ import annotations

import argparse
import asyncio

from aioetcd3.client import Etcd3Client
from aioetcd3.kv import KVService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run KV example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def run_kv_example(kv: KVService) -> None:
    key = 'example:kv:module'

    await kv.put(key, 'hello-kv')
    get_response = await kv.get(key)

    if not get_response.kvs:
        raise RuntimeError('expected key to exist after put')

    print(f'KV get -> {get_response.kvs[0].value.decode("utf-8")}')

    await kv.delete(key)
    deleted_response = await kv.get(key)
    print(f'KV delete -> exists={bool(deleted_response.kvs)}')


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        if kv is None:
            raise RuntimeError('kv service is not initialized')

        await run_kv_example(kv)


if __name__ == '__main__':
    asyncio.run(main())
