from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import cast

from etcd3aio import Etcd3Client, EtcdConnectionError
from etcd3aio._protobuf import WatchResponse
from etcd3aio.kv import KVService
from etcd3aio.lease import LeaseService
from etcd3aio.maintenance import MaintenanceService
from etcd3aio.watch import WatchService

logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(name)s: %(message)s')


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
        maintenance = client.maintenance

        if kv is None or lease is None or watch is None or maintenance is None:
            raise RuntimeError('client services are not initialized')

        await client.ping()
        print('Ping ok -> cluster is reachable and writes are accepted')

        await _run_kv_demo(kv)
        await _run_lease_demo(kv, lease)
        await _run_watch_demo(kv, watch)
        await _run_maintenance_demo(maintenance)
        await _run_concurrency_demo(client)


async def _run_kv_demo(kv: KVService) -> None:
    key = 'example:kv'

    await kv.put(key, 'hello-etcd3aio')
    response = await kv.get(key)

    if not response.kvs:
        raise RuntimeError('expected key to exist after put')

    print(f'KV put/get ok -> {response.kvs[0].value.decode()}')

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
    print(f'Watch event ok -> key={event.kv.key.decode()}, type={event.type}')

    await kv.delete(watch_key)


async def _run_maintenance_demo(maintenance: MaintenanceService) -> None:
    status = await maintenance.status()
    print(f'Maintenance status ok -> leader={status.leader}, version={status.version}')

    alarms_resp = await maintenance.alarms()
    print(f'Maintenance alarms ok -> active={len(alarms_resp.alarms)}')


async def _run_concurrency_demo(client: Etcd3Client) -> None:
    async with client.lock('example:lock'):
        print('Lock ok -> acquired exclusive section')
    print('Lock ok -> released')

    async with client.election('example:election', value=b'node-1') as e:
        print('Election ok -> won leadership')
        leader_resp = await e.leader()
        if leader_resp.kvs:
            print(f'Election leader() ok -> {leader_resp.kvs[0].value.decode()}')
        await e.proclaim(b'node-1-v2')
        print('Election proclaim() ok -> updated')
    print('Election ok -> resigned')


async def main() -> None:
    endpoints = ['localhost:2379', 'localhost:3379', 'localhost:4379']
    try:
        await run_demo(endpoints)
    except EtcdConnectionError as exc:
        print(f'Error: could not reach etcd at {endpoints}')
        print(f'Cause: {exc}')
        raise SystemExit(1) from None


if __name__ == '__main__':
    asyncio.run(main())
