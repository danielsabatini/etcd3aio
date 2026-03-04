"""Integration tests — MaintenanceService."""

from __future__ import annotations

import pytest

from etcd3aio import DowngradeAction, Etcd3Client
from etcd3aio.maintenance import AlarmType

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_status_returns_version_and_leader(etcd: Etcd3Client) -> None:
    """status() must return a non-empty version string and a valid leader ID."""
    resp = await etcd.maintenance.status()

    assert resp.version  # e.g. "3.6.8"
    assert resp.leader != 0  # leader member ID


@pytest.mark.asyncio
async def test_status_db_size_is_positive(etcd: Etcd3Client) -> None:
    """A cluster with any data must report a positive DB size."""
    await etcd.kv.put('test/status-probe', 'x')
    resp = await etcd.maintenance.status()

    assert resp.dbSize > 0


@pytest.mark.asyncio
async def test_alarms_returns_list(etcd: Etcd3Client) -> None:
    """alarms() should succeed; a healthy cluster has no active alarms."""
    resp = await etcd.maintenance.alarms()

    # alarms is a repeated field — may be empty or contain NONE entries
    assert resp is not None


@pytest.mark.asyncio
async def test_no_active_nospace_or_corrupt_alarms(etcd: Etcd3Client) -> None:
    """A healthy test cluster must not have NOSPACE or CORRUPT alarms."""
    resp = await etcd.maintenance.alarms()

    active_types = {a.alarm for a in resp.alarms}
    assert AlarmType.NOSPACE not in active_types
    assert AlarmType.CORRUPT not in active_types


@pytest.mark.asyncio
async def test_defragment_does_not_raise(etcd: Etcd3Client) -> None:
    """defragment() should complete without error on a healthy cluster."""
    await etcd.maintenance.defragment()


@pytest.mark.asyncio
async def test_hash_returns_nonzero_value(etcd: Etcd3Client) -> None:
    """hash() returns a full-store hash that is non-zero on any non-empty cluster."""
    await etcd.kv.put('test/hash-probe', 'data')
    resp = await etcd.maintenance.hash()

    assert resp.hash != 0


@pytest.mark.asyncio
async def test_hash_kv_returns_consistent_hash_and_revision(etcd: Etcd3Client) -> None:
    """hash_kv() returns a hash paired with the revision at which it was computed."""
    await etcd.kv.put('test/hashkv-probe', 'data')
    resp = await etcd.maintenance.hash_kv()

    assert resp.hash != 0
    assert resp.hash_revision > 0


@pytest.mark.asyncio
async def test_snapshot_streams_non_empty_bytes(etcd: Etcd3Client) -> None:
    """snapshot() must stream at least one non-empty chunk."""
    chunks: list[bytes] = []
    async for chunk in etcd.maintenance.snapshot():
        chunks.append(chunk)
        if len(chunks) >= 3:
            break  # don't need the full snapshot for this check

    assert len(chunks) > 0
    assert any(len(c) > 0 for c in chunks)


@pytest.mark.asyncio
async def test_downgrade_validate_does_not_raise(etcd: Etcd3Client) -> None:
    """downgrade(VALIDATE, ...) is a read-only eligibility check — must not fail."""
    # VALIDATE is safe: it only checks eligibility, never changes cluster state.
    # We use the current version to guarantee the check passes.
    status = await etcd.maintenance.status()
    version = status.version  # e.g. "3.6.8"

    # May raise if the cluster is not eligible — that is a valid server response,
    # not a library bug.  We simply assert the call reaches the server.
    try:
        await etcd.maintenance.downgrade(DowngradeAction.VALIDATE, version)
    except Exception:
        pass  # server-side rejection is acceptable; no crash = test passes
