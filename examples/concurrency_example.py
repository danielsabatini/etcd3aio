from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncGenerator
from typing import cast

from etcd3aio._protobuf import WatchResponse
from etcd3aio.client import Etcd3Client
from etcd3aio.concurrency import Lock


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Concurrency example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    return parser.parse_args()


async def run_lock_example(lock: Lock) -> None:
    async with lock:
        print('Lock: acquired exclusive section')
    print('Lock: released')


async def run_election_example(client: Etcd3Client) -> None:
    election_name = 'example-election'

    # Start observing before campaigning to capture the campaign PUT event.
    observe_gen = cast(
        AsyncGenerator[WatchResponse, None],
        client.election(election_name, ttl=10).observe(),
    )
    observer_task = asyncio.create_task(asyncio.wait_for(anext(observe_gen), timeout=10.0))
    await asyncio.sleep(0.1)  # give watch time to register

    async with client.election(election_name, value=b'node-1', ttl=10) as e:
        print('Election: won leadership')

        # Query current leader
        leader_resp = await e.leader()
        if leader_resp.kvs:
            print(f'Election leader() -> {leader_resp.kvs[0].value.decode()}')

        # Update the leader identity value
        await e.proclaim(b'node-1-v2')
        print('Election proclaim() -> updated to node-1-v2')

    print('Election: resigned')

    try:
        watch_resp = await observer_task
        print(f'Election observe() -> received {len(watch_resp.events)} event(s)')
    except asyncio.TimeoutError:
        print('Election observe() -> no event within timeout')
    finally:
        await observe_gen.aclose()


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        lock = client.lock('example-lock', ttl=30)
        await run_lock_example(lock)

        await run_election_example(client)


if __name__ == '__main__':
    asyncio.run(main())
