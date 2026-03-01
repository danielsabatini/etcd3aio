from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.client import Etcd3Client
from etcd3aio.kv import KVService, SortOrder, SortTarget, prefix_range_end

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


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

    # Put and get
    await kv.put(key, 'hello-kv')
    get_response = await kv.get(key)

    if not get_response.kvs:
        raise RuntimeError('expected key to exist after put')

    print(f'KV get -> {get_response.kvs[0].value.decode()}')

    # Delete and verify
    await kv.delete(key)
    deleted_response = await kv.get(key)
    print(f'KV delete -> exists={bool(deleted_response.kvs)}')

    # Prefix scan with sort
    prefix = 'example:kv:items/'
    for i in range(3):
        await kv.put(f'{prefix}{i}', f'item-{i}')

    range_end = prefix_range_end(prefix)
    sorted_response = await kv.get(
        prefix,
        range_end=range_end,
        sort_order=SortOrder.DESCEND,
        sort_target=SortTarget.KEY,
    )
    keys = [kv_entry.key.decode() for kv_entry in sorted_response.kvs]
    print(f'KV prefix scan (descend) -> {keys}')

    # keys_only: retrieve only key names, no values
    keys_response = await kv.get(prefix, range_end=range_end, keys_only=True)
    print(f'KV keys_only -> {len(keys_response.kvs)} keys')

    # count_only: retrieve only the count
    count_response = await kv.get(prefix, range_end=range_end, count_only=True)
    print(f'KV count_only -> count={count_response.count}')

    # Compact history up to the current revision
    current_revision = sorted_response.header.revision
    await kv.compact(current_revision)
    print(f'KV compact -> compacted up to revision {current_revision}')

    # Cleanup
    await kv.delete(prefix, range_end=range_end)


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        if kv is None:
            raise RuntimeError('kv service is not initialized')

        await run_kv_example(kv)


if __name__ == '__main__':
    asyncio.run(main())
