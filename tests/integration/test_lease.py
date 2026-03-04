"""Integration tests — LeaseService."""

from __future__ import annotations

import asyncio

import pytest

from etcd3aio import Etcd3Client

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_grant_and_time_to_live(etcd: Etcd3Client) -> None:
    """Grant a lease and verify TTL is reported correctly."""
    lease = await etcd.lease.grant(ttl=30)
    try:
        assert lease.ID != 0
        assert lease.TTL == 30

        info = await etcd.lease.time_to_live(lease.ID)
        assert info.TTL > 0
        assert info.TTL <= 30
    finally:
        await etcd.lease.revoke(lease.ID)


@pytest.mark.asyncio
async def test_key_attached_to_lease_is_deleted_when_revoked(etcd: Etcd3Client) -> None:
    """Key attached to a lease disappears when the lease is revoked."""
    lease = await etcd.lease.grant(ttl=30)
    try:
        await etcd.kv.put('test/leased-key', 'value', lease=lease.ID)

        # Key exists while lease is alive
        resp = await etcd.kv.get('test/leased-key')
        assert resp.count == 1

        await etcd.lease.revoke(lease.ID)

        # Key gone after revoke
        resp = await etcd.kv.get('test/leased-key')
        assert resp.count == 0
    except Exception:
        await etcd.lease.revoke(lease.ID)
        raise


@pytest.mark.asyncio
async def test_time_to_live_with_keys_shows_attached_keys(etcd: Etcd3Client) -> None:
    """time_to_live(keys=True) returns the list of keys attached to the lease."""
    lease = await etcd.lease.grant(ttl=30)
    try:
        await etcd.kv.put('test/attached', 'v', lease=lease.ID)

        info = await etcd.lease.time_to_live(lease.ID, keys=True)
        attached = list(info.keys)
        assert b'test/attached' in attached
    finally:
        await etcd.lease.revoke(lease.ID)


@pytest.mark.asyncio
async def test_leases_lists_active_lease(etcd: Etcd3Client) -> None:
    """leases() includes the newly granted lease ID."""
    lease = await etcd.lease.grant(ttl=30)
    try:
        resp = await etcd.lease.leases()
        ids = [m.ID for m in resp.leases]
        assert lease.ID in ids
    finally:
        await etcd.lease.revoke(lease.ID)


@pytest.mark.asyncio
async def test_lease_expires_and_key_disappears(etcd: Etcd3Client) -> None:
    """A short-lived lease (TTL=2) causes the attached key to vanish after expiry."""
    lease = await etcd.lease.grant(ttl=2)
    await etcd.kv.put('test/expiring', 'gone-soon', lease=lease.ID)

    resp = await etcd.kv.get('test/expiring')
    assert resp.count == 1

    # Wait for the lease to expire (TTL + 1 s margin)
    await asyncio.sleep(3)

    resp = await etcd.kv.get('test/expiring')
    assert resp.count == 0


@pytest.mark.asyncio
async def test_keep_alive_context_keeps_key_alive(etcd: Etcd3Client) -> None:
    """keep_alive_context() renews the lease — key must still exist after TTL passes."""
    lease = await etcd.lease.grant(ttl=2)
    try:
        await etcd.kv.put('test/kept-alive', 'still-here', lease=lease.ID)

        async with etcd.lease.keep_alive_context(lease.ID, ttl=2):
            # Sleep longer than TTL — keep-alive should prevent expiry
            await asyncio.sleep(3)

        # Key should still be present immediately after the context exits
        resp = await etcd.kv.get('test/kept-alive')
        assert resp.count == 1
    finally:
        await etcd.lease.revoke(lease.ID)
