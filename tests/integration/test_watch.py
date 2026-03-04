"""Integration tests — WatchService."""

from __future__ import annotations

import asyncio

import pytest

from etcd3aio import Etcd3Client
from etcd3aio.watch import WatchFilter

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_watch_receives_put_event(etcd: Etcd3Client) -> None:
    """Watch on a key receives the PUT event when the key is written."""
    events: list = []
    ready = asyncio.Event()

    async def _watcher() -> None:
        ready.set()
        async for response in etcd.watch.watch('test/watched-put'):
            events.extend(response.events)
            if events:
                return  # exit after first non-empty batch

    task = asyncio.create_task(_watcher())
    await ready.wait()
    await asyncio.sleep(0.05)  # allow gRPC to register the watch server-side

    await etcd.kv.put('test/watched-put', 'hello')
    await asyncio.wait_for(task, timeout=5.0)

    assert len(events) == 1
    assert events[0].type == 0  # EventType.PUT
    assert events[0].kv.value == b'hello'


@pytest.mark.asyncio
async def test_watch_receives_delete_event(etcd: Etcd3Client) -> None:
    """Watch on a key receives the DELETE event when the key is removed."""
    await etcd.kv.put('test/watched-del', 'to-be-deleted')

    events: list = []
    ready = asyncio.Event()

    async def _watcher() -> None:
        ready.set()
        async for response in etcd.watch.watch('test/watched-del'):
            events.extend(response.events)
            if events:
                return

    task = asyncio.create_task(_watcher())
    await ready.wait()
    await asyncio.sleep(0.05)

    await etcd.kv.delete('test/watched-del')
    await asyncio.wait_for(task, timeout=5.0)

    assert len(events) == 1
    assert events[0].type == 1  # EventType.DELETE


@pytest.mark.asyncio
async def test_watch_nodelete_filter_suppresses_delete(etcd: Etcd3Client) -> None:
    """NODELETE filter: DELETE is dropped server-side, only PUT arrives."""
    await etcd.kv.put('test/filtered', 'initial')

    events: list = []
    ready = asyncio.Event()

    async def _watcher() -> None:
        ready.set()
        async for response in etcd.watch.watch(
            'test/filtered',
            filters=(WatchFilter.NODELETE,),
        ):
            events.extend(response.events)
            if events:
                return  # stop after we see the PUT

    task = asyncio.create_task(_watcher())
    await ready.wait()
    await asyncio.sleep(0.05)

    # Issue both PUT and DELETE — watcher should only see the PUT
    await etcd.kv.put('test/filtered', 'updated')
    await etcd.kv.delete('test/filtered')

    await asyncio.wait_for(task, timeout=5.0)

    assert len(events) == 1
    assert events[0].type == 0  # only the PUT


@pytest.mark.asyncio
async def test_watch_from_start_revision_replays_past_events(etcd: Etcd3Client) -> None:
    """watch(start_revision=r) replays events from revision r without waiting."""
    # Write the key first and record the revision
    await etcd.kv.put('test/past', 'value')
    resp = await etcd.kv.get('test/past')
    write_revision = resp.header.revision

    # Start watching from before the write — the event must be replayed immediately
    events: list = []
    async for response in etcd.watch.watch('test/past', start_revision=write_revision):
        events.extend(response.events)
        if events:
            break  # take the first non-empty batch

    assert len(events) >= 1
    # The first event must be the PUT we already issued
    assert events[0].type == 0
    assert events[0].kv.value == b'value'
