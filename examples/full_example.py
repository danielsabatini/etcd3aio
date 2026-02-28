from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Sequence
from typing import cast

from aioetcd3._protobuf import WatchResponse
from aioetcd3.client import Etcd3Client
from aioetcd3.kv import KVService
from aioetcd3.lease import LeaseService
from aioetcd3.watch import WatchService


async def _wait_for_watch_event(
    watch_service: WatchService,
    key: str,
    *,
    timeout_seconds: float = 8.0,
) -> WatchResponse:
    watch_stream = cast(AsyncGenerator[WatchResponse, None], watch_service.watch(key))

    try:
        while True:
            response = await asyncio.wait_for(anext(watch_stream), timeout=timeout_seconds)
            if response.events:
                return response
    finally:
        await watch_stream.aclose()


async def run_demo(endpoints: Sequence[str]) -> None:
    async with Etcd3Client(endpoints) as client:
        kv = client.kv
        lease = client.lease
        watch = client.watch

        if kv is None or lease is None or watch is None:
            raise RuntimeError('client services are not initialized')

        await _run_kv_demo(kv)
        await _run_lease_demo(kv, lease)
        await _run_watch_demo(kv, watch)


async def _run_kv_demo(kv: KVService) -> None:
    key = 'example:kv'

    await kv.put(key, 'hello-aioetcd3')
    response = await kv.get(key)

    if not response.kvs:
        raise RuntimeError('expected key to exist after put')

    print(f'KV put/get ok -> {response.kvs[0].value.decode("utf-8")}')

    await kv.delete(key)
    deleted = await kv.get(key)
    print(f'KV delete ok -> exists={bool(deleted.kvs)}')


async def _run_lease_demo(kv: KVService, lease: LeaseService) -> None:
    lease_key = 'example:lease'

    lease_response = await lease.grant(ttl=15)
    lease_id = lease_response.ID

    await kv.put(lease_key, 'leased-value', lease=lease_id)
    ttl_response = await lease.time_to_live(lease_id)

    print(f'Lease grant ok -> lease_id={lease_id}, ttl={ttl_response.TTL}')

    await lease.revoke(lease_id)
    await kv.delete(lease_key)


async def _run_watch_demo(kv: KVService, watch: WatchService) -> None:
    watch_key = 'example:watch'
    watcher_task = asyncio.create_task(_wait_for_watch_event(watch, watch_key))

    await asyncio.sleep(0.2)
    await kv.put(watch_key, 'watch-event')

    response = await watcher_task
    event = response.events[0]
    print(f'Watch event ok -> key={event.kv.key.decode("utf-8")}, type={event.type}')

    await kv.delete(watch_key)


async def main() -> None:
    endpoints = ['localhost:2379']
    await run_demo(endpoints)


if __name__ == '__main__':
    asyncio.run(main())
