from __future__ import annotations

import argparse
import asyncio

from etcd3aio.client import Etcd3Client
from etcd3aio.kv import KVService


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

    # --- txn_compare_value ---
    # Write v1, then atomically update to v2 only if current value is v1.
    await kv.put(key, 'v1')

    txn_response = await kv.txn(
        compare=[kv.txn_compare_value(key, 'v1')],
        success=[kv.txn_op_put(key, 'v2')],
        failure=[kv.txn_op_put(key, 'conflict')],
    )
    resp = await kv.get(key)
    print(
        f'txn_compare_value -> succeeded={txn_response.succeeded}, '
        f'value={resp.kvs[0].value.decode() if resp.kvs else None}'
    )

    # --- txn_compare_version ---
    # Atomically delete only if the version (update count) equals the current version.
    version_resp = await kv.get(key)
    current_version = version_resp.kvs[0].version if version_resp.kvs else 0

    txn_response = await kv.txn(
        compare=[kv.txn_compare_version(key, current_version)],
        success=[kv.txn_op_delete(key)],
    )
    print(f'txn_compare_version -> succeeded={txn_response.succeeded}')

    # --- txn_compare_create_revision ---
    # Canonical idiom: put a key only if it does not already exist
    # (create_revision == 0 means the key was never created).
    txn_response = await kv.txn(
        compare=[kv.txn_compare_create_revision(key, 0)],
        success=[kv.txn_op_put(key, 'created-once')],
    )
    print(f'txn_compare_create_revision (key not exist) -> succeeded={txn_response.succeeded}')

    # Try again — should fail because the key now exists (create_revision > 0).
    txn_response = await kv.txn(
        compare=[kv.txn_compare_create_revision(key, 0)],
        success=[kv.txn_op_put(key, 'should-not-write')],
    )
    print(f'txn_compare_create_revision (key exists) -> succeeded={txn_response.succeeded}')

    # --- txn_op_get inside a transaction ---
    # Read the key atomically as part of the transaction success branch.
    txn_response = await kv.txn(
        compare=[kv.txn_compare_value(key, 'created-once')],
        success=[kv.txn_op_get(key)],
    )
    if txn_response.succeeded and txn_response.responses:
        value = txn_response.responses[0].response_range.kvs[0].value.decode()
        print(f'txn_op_get -> value={value}')

    # Cleanup
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
