"""Integration tests — KVService."""

from __future__ import annotations

import pytest

from etcd3aio import Etcd3Client
from etcd3aio.kv import SortOrder, SortTarget, prefix_range_end

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# put / get / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_and_get_roundtrip(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/greeting', 'hello')
    resp = await etcd.kv.get('test/greeting')

    assert resp.count == 1
    assert resp.kvs[0].key == b'test/greeting'
    assert resp.kvs[0].value == b'hello'


@pytest.mark.asyncio
async def test_put_overwrites_existing_value(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/x', 'first')
    await etcd.kv.put('test/x', 'second')
    resp = await etcd.kv.get('test/x')

    assert resp.kvs[0].value == b'second'


@pytest.mark.asyncio
async def test_get_missing_key_returns_empty(etcd: Etcd3Client) -> None:
    resp = await etcd.kv.get('test/does-not-exist')

    assert resp.count == 0
    assert list(resp.kvs) == []


@pytest.mark.asyncio
async def test_delete_removes_key(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/to-delete', 'bye')
    await etcd.kv.delete('test/to-delete')
    resp = await etcd.kv.get('test/to-delete')

    assert resp.count == 0


@pytest.mark.asyncio
async def test_delete_with_prev_kv_returns_old_value(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/prev', 'original')
    resp = await etcd.kv.delete('test/prev', prev_kv=True)

    assert len(resp.prev_kvs) == 1
    assert resp.prev_kvs[0].value == b'original'


# ---------------------------------------------------------------------------
# Range queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prefix_scan_returns_all_keys(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/items/a', '1')
    await etcd.kv.put('test/items/b', '2')
    await etcd.kv.put('test/items/c', '3')

    resp = await etcd.kv.get('test/items/', range_end=prefix_range_end('test/items/'))

    assert resp.count == 3
    keys = [kv.key for kv in resp.kvs]
    assert b'test/items/a' in keys
    assert b'test/items/b' in keys
    assert b'test/items/c' in keys


@pytest.mark.asyncio
async def test_get_with_limit(etcd: Etcd3Client) -> None:
    for i in range(5):
        await etcd.kv.put(f'test/limited/{i}', str(i))

    resp = await etcd.kv.get(
        'test/limited/',
        range_end=prefix_range_end('test/limited/'),
        limit=3,
    )

    assert len(resp.kvs) == 3


@pytest.mark.asyncio
async def test_get_keys_only_returns_no_values(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/konly/a', 'value-a')
    await etcd.kv.put('test/konly/b', 'value-b')

    resp = await etcd.kv.get(
        'test/konly/',
        range_end=prefix_range_end('test/konly/'),
        keys_only=True,
    )

    assert resp.count == 2
    for kv in resp.kvs:
        assert kv.value == b''


@pytest.mark.asyncio
async def test_get_count_only_returns_count_without_data(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/cnt/a', 'v')
    await etcd.kv.put('test/cnt/b', 'v')

    resp = await etcd.kv.get(
        'test/cnt/',
        range_end=prefix_range_end('test/cnt/'),
        count_only=True,
    )

    assert resp.count == 2
    assert list(resp.kvs) == []


@pytest.mark.asyncio
async def test_get_sort_descend_by_key(etcd: Etcd3Client) -> None:
    await etcd.kv.put('test/sort/a', '1')
    await etcd.kv.put('test/sort/b', '2')
    await etcd.kv.put('test/sort/c', '3')

    resp = await etcd.kv.get(
        'test/sort/',
        range_end=prefix_range_end('test/sort/'),
        sort_order=SortOrder.DESCEND,
        sort_target=SortTarget.KEY,
    )

    keys = [kv.key for kv in resp.kvs]
    assert keys == [b'test/sort/c', b'test/sort/b', b'test/sort/a']


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_txn_put_if_key_does_not_exist(etcd: Etcd3Client) -> None:
    """put-if-not-exists: succeeds on first call, fails on second."""
    compare = [etcd.kv.txn_compare_create_revision('test/new-key', 0)]
    success = [etcd.kv.txn_op_put('test/new-key', 'created')]

    first = await etcd.kv.txn(compare=compare, success=success, failure=[])
    assert first.succeeded is True

    # Key now exists — create_revision != 0 → compare fails
    second = await etcd.kv.txn(compare=compare, success=success, failure=[])
    assert second.succeeded is False


@pytest.mark.asyncio
async def test_txn_compare_and_swap(etcd: Etcd3Client) -> None:
    """compare-and-swap by value: swap 'off' → 'on'."""
    await etcd.kv.put('test/flag', 'off')

    compare = [etcd.kv.txn_compare_value('test/flag', 'off')]
    success = [etcd.kv.txn_op_put('test/flag', 'on')]
    failure = [etcd.kv.txn_op_get('test/flag')]

    resp = await etcd.kv.txn(compare=compare, success=success, failure=failure)
    assert resp.succeeded is True

    after = await etcd.kv.get('test/flag')
    assert after.kvs[0].value == b'on'


# ---------------------------------------------------------------------------
# Compact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compact_does_not_raise(etcd: Etcd3Client) -> None:
    """compact() should succeed without error (physical=False is non-blocking)."""
    await etcd.kv.put('test/compact-me', 'v')
    resp = await etcd.kv.get('test/compact-me')
    revision = resp.header.revision

    # compact up to current revision — should not raise
    await etcd.kv.compact(revision=revision)
