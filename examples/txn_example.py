from __future__ import annotations

import argparse
import asyncio

from aioetcd3.client import Etcd3Client
from aioetcd3.kv import KVService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Txn example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def run_txn_example(kv: KVService) -> None:
    key = 'example:txn:module'

    await kv.put(key, 'v1')

    compare = [kv.txn_compare_value(key, 'v1')]
    success = [kv.txn_op_put(key, 'v2')]
    failure = [kv.txn_op_put(key, 'conflict')]

    txn_response = await kv.txn(compare=compare, success=success, failure=failure)
    get_response = await kv.get(key)

    if not get_response.kvs:
        raise RuntimeError('expected key to exist after txn')

    current_value = get_response.kvs[0].value.decode('utf-8')
    print(f'Txn succeeded={txn_response.succeeded}, value={current_value}')

    await kv.delete(key)


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        if kv is None:
            raise RuntimeError('kv service is not initialized')

        await run_txn_example(kv)


if __name__ == '__main__':
    asyncio.run(main())
