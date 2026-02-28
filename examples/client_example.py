from __future__ import annotations

import argparse
import asyncio

from aioetcd3.client import Etcd3Client


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

        print('Client connected and services initialized: kv, lease, watch')
    finally:
        await client.close()
        print('Client closed')


if __name__ == '__main__':
    asyncio.run(main())
