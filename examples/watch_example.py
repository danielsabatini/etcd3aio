from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncGenerator
from typing import cast

from etcd3aio._protobuf import WatchResponse
from etcd3aio.client import Etcd3Client
from etcd3aio.kv import KVService, prefix_range_end
from etcd3aio.watch import WatchFilter, WatchService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Watch example against etcd.')
    parser.add_argument(
        '--endpoints',
        nargs='*',
        default=['localhost:2379'],
        help='List of etcd endpoints in host:port format.',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=8.0,
        help='Watch timeout in seconds.',
    )
    return parser.parse_args()


async def wait_for_watch_event(
    watch_service: WatchService,
    key: str,
    timeout: float,
    *,
    filters: tuple[WatchFilter, ...] = (),
    range_end: str | None = None,
) -> WatchResponse:
    watch_stream = cast(
        AsyncGenerator[WatchResponse, None],
        watch_service.watch(key, range_end=range_end, filters=filters),
    )

    try:
        while True:
            response = await asyncio.wait_for(anext(watch_stream), timeout=timeout)
            if response.events:
                return response
    finally:
        await watch_stream.aclose()


async def run_watch_example(kv: KVService, watch: WatchService, timeout: float) -> None:
    key = 'example:watch:module'

    # Basic watch: receive any event on a single key
    watcher_task = asyncio.create_task(wait_for_watch_event(watch, key, timeout))
    await asyncio.sleep(0.2)
    await kv.put(key, 'watch-event')

    response = await watcher_task
    event = response.events[0]
    print(
        f'Watch event -> '
        f'key={event.kv.key.decode()}, '
        f'value={event.kv.value.decode()}, '
        f'type={event.type}'
    )

    await kv.delete(key)

    # WatchFilter.NODELETE: suppress DELETE events, receive only PUTs
    prefix = 'example:watch:items/'
    range_end = prefix_range_end(prefix)

    watcher_task = asyncio.create_task(
        wait_for_watch_event(
            watch,
            prefix,
            timeout,
            filters=(WatchFilter.NODELETE,),
            range_end=range_end,
        )
    )
    await asyncio.sleep(0.2)

    # This DELETE would be filtered out server-side
    await kv.put(f'{prefix}item-a', 'hello')
    await kv.delete(f'{prefix}item-a')

    # The watch receives only the PUT event
    response = await watcher_task
    print(
        f'Watch NODELETE filter -> '
        f'events={len(response.events)}, '
        f'type={response.events[0].type}'  # 0 = PUT
    )

    await kv.delete(prefix, range_end=range_end)


async def main() -> None:
    args = parse_args()

    async with Etcd3Client(args.endpoints) as client:
        kv = client.kv
        watch = client.watch

        if kv is None or watch is None:
            raise RuntimeError('kv or watch service is not initialized')

        await run_watch_example(kv, watch, timeout=args.timeout)


if __name__ == '__main__':
    asyncio.run(main())
