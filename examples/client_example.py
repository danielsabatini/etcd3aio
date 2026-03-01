from __future__ import annotations

import argparse
import asyncio
import logging

from etcd3aio.client import Etcd3Client

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Etcd3Client lifecycle example.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    client = Etcd3Client(args.endpoints)
    await client.connect()

    try:
        if client.kv is None or client.lease is None or client.watch is None:
            raise RuntimeError('client services are not initialized')

        print('Client connected and services initialized: kv, lease, watch, auth, maintenance')

        # Ping verifies cluster health: readable and writable
        await client.ping()
        print('Client ping -> cluster is reachable and accepting writes')

        # Read-only ping (skips the write check)
        await client.ping(write_check=False)
        print('Client ping(write_check=False) -> cluster is readable')
    finally:
        await client.close()
        print('Client closed')


if __name__ == '__main__':
    asyncio.run(main())
