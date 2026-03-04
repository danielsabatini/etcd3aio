"""Integration tests — Lock and Election (concurrency primitives)."""

from __future__ import annotations

import asyncio

import pytest

from etcd3aio import Etcd3Client

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_acquired_and_released(etcd: Etcd3Client) -> None:
    """Lock context manager acquires and releases without error."""
    async with etcd.lock('test/mylock', ttl=10):
        # Inside the block we hold the lock exclusively
        resp = await etcd.kv.get('test/mylock-probe')
        assert resp is not None  # just proves we can do work while holding the lock


@pytest.mark.asyncio
async def test_lock_mutual_exclusion_between_two_holders(etcd: Etcd3Client) -> None:
    """Two concurrent lock attempts must not overlap inside the critical section."""
    inside_count = 0
    max_concurrent = 0

    async def _hold_lock(client: Etcd3Client) -> None:
        nonlocal inside_count, max_concurrent
        async with client.lock('test/mutex', ttl=10):
            inside_count += 1
            max_concurrent = max(max_concurrent, inside_count)
            await asyncio.sleep(0.05)  # hold briefly so the other task arrives
            inside_count -= 1

    # Run two holders concurrently against the same key
    await asyncio.gather(_hold_lock(etcd), _hold_lock(etcd))

    # At no point should both be inside the critical section simultaneously
    assert max_concurrent == 1


@pytest.mark.asyncio
async def test_lock_manual_acquire_and_release(etcd: Etcd3Client) -> None:
    """Manual acquire/release API works without context manager."""
    lock = etcd.lock('test/manual-lock', ttl=10)
    await lock.acquire()
    try:
        resp = await etcd.kv.get('test/manual-probe')
        assert resp is not None
    finally:
        await lock.release()


# ---------------------------------------------------------------------------
# Election
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_election_campaign_and_resign(etcd: Etcd3Client) -> None:
    """Campaign wins leadership and resign relinquishes it cleanly."""
    async with etcd.election('test/leader', value=b'node-1', ttl=10) as e:
        leader_resp = await e.leader()
        # We are the only candidate — we must be the leader
        assert leader_resp.count >= 1
        assert leader_resp.kvs[0].value == b'node-1'

        # Proclaim a new identity without resigning
        await e.proclaim(b'node-1-updated')

        updated = await e.leader()
        assert updated.kvs[0].value == b'node-1-updated'

    # After the context exits (resign), no candidate holds the election
    # (the key is deleted along with the lease)
    final = await etcd.election('test/leader').leader()
    assert final.count == 0


@pytest.mark.asyncio
async def test_election_observe_yields_put_events(etcd: Etcd3Client) -> None:
    """observe() yields responses containing PUT events when leadership changes."""
    observed: list = []

    async def _observe() -> None:
        async for resp in etcd.election('test/obs-leader').observe():
            observed.append(resp)
            return  # take only the first event

    task = asyncio.create_task(_observe())
    await asyncio.sleep(0.1)  # let observer register

    # Campaign — this will emit a PUT event on the election prefix
    async with etcd.election('test/obs-leader', value=b'candidate', ttl=10):
        await asyncio.wait_for(task, timeout=5.0)

    assert len(observed) == 1
    # The response must carry at least one PUT event
    put_events = [ev for ev in observed[0].events if ev.type == 0]
    assert len(put_events) >= 1
