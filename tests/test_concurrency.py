from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aioetcd3.client import Etcd3Client
from aioetcd3.concurrency import Election, Lock, _prefix_range_end
from aioetcd3.errors import EtcdError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kv(key: bytes, create_revision: int) -> MagicMock:
    kv = MagicMock()
    kv.key = key
    kv.create_revision = create_revision
    return kv


def _make_range_resp(kvs: list[MagicMock], revision: int) -> MagicMock:
    resp = MagicMock()
    resp.kvs = kvs
    resp.header = MagicMock()
    resp.header.revision = revision
    return resp


def _make_delete_event(key: bytes) -> MagicMock:
    event = MagicMock()
    event.type = 1  # DELETE
    event.kv = MagicMock()
    event.kv.key = key
    return event


def _make_watch_resp(events: list[MagicMock]) -> MagicMock:
    resp = MagicMock()
    resp.events = events
    return resp


async def _async_gen(*items: MagicMock):
    for item in items:
        yield item


def _make_services(
    *,
    lease_id: int,
    get_side_effect: list[MagicMock] | MagicMock,
    watch_responses: list[MagicMock] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    lease_resp = MagicMock()
    lease_resp.ID = lease_id

    kv = MagicMock()
    kv.put = AsyncMock()
    kv.delete = AsyncMock()
    kv.get = (
        AsyncMock(side_effect=get_side_effect)
        if isinstance(get_side_effect, list)
        else AsyncMock(return_value=get_side_effect)
    )

    lease = MagicMock()
    lease.grant = AsyncMock(return_value=lease_resp)
    lease.revoke = AsyncMock()

    watch = MagicMock()
    if watch_responses is not None:
        watch.watch = MagicMock(return_value=_async_gen(*watch_responses))

    return kv, lease, watch


# ---------------------------------------------------------------------------
# _prefix_range_end
# ---------------------------------------------------------------------------


def test_prefix_range_end_increments_last_byte() -> None:
    assert _prefix_range_end(b'abc/') == b'abc0'


def test_prefix_range_end_handles_0xff_suffix() -> None:
    assert _prefix_range_end(b'a\xff') == b'b'


# ---------------------------------------------------------------------------
# Lock — no contention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_acquired_immediately_when_no_contention() -> None:
    lease_id = 42
    prefix = b'__aioetcd3:lock/mylock/'
    my_key = prefix + b'000000000000002a'

    range_resp = _make_range_resp([_make_kv(my_key, 5)], revision=5)
    kv, lease, watch = _make_services(lease_id=lease_id, get_side_effect=range_resp)

    async with Lock(kv, lease, watch, 'mylock', ttl=10):
        pass

    kv.put.assert_awaited_once_with(my_key, b'', lease=lease_id)
    kv.delete.assert_awaited_once_with(my_key)
    lease.revoke.assert_awaited_once_with(lease_id)


# ---------------------------------------------------------------------------
# Lock — contention: one predecessor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_waits_for_predecessor_deletion() -> None:
    lease_id = 42
    prefix = b'__aioetcd3:lock/mylock/'
    predecessor_key = prefix + b'0000000000000010'
    my_key = prefix + b'000000000000002a'

    # First get: predecessor + us; second get: only us (after predecessor gone)
    range_resp_1 = _make_range_resp([_make_kv(predecessor_key, 3), _make_kv(my_key, 5)], revision=5)
    range_resp_2 = _make_range_resp([_make_kv(my_key, 5)], revision=7)

    watch_resp = _make_watch_resp([_make_delete_event(predecessor_key)])

    kv, lease, watch = _make_services(
        lease_id=lease_id,
        get_side_effect=[range_resp_1, range_resp_2],
        watch_responses=[watch_resp],
    )

    async with Lock(kv, lease, watch, 'mylock', ttl=10):
        pass

    assert kv.get.await_count == 2
    watch.watch.assert_called_once_with(predecessor_key, start_revision=6)


# ---------------------------------------------------------------------------
# Lock — release suppresses errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_release_suppresses_etcd_errors() -> None:
    lease_id = 1
    prefix = b'__aioetcd3:lock/x/'
    my_key = prefix + b'0000000000000001'

    range_resp = _make_range_resp([_make_kv(my_key, 1)], revision=1)
    kv, lease, watch = _make_services(lease_id=lease_id, get_side_effect=range_resp)
    kv.delete = AsyncMock(side_effect=EtcdError('gone'))
    lease.revoke = AsyncMock(side_effect=EtcdError('gone'))

    async with Lock(kv, lease, watch, 'x', ttl=5):
        pass  # no error raised despite delete/revoke failing


# ---------------------------------------------------------------------------
# Lock — key prefix isolation
# ---------------------------------------------------------------------------


def test_lock_keys_are_isolated_by_name() -> None:
    """Different names must not share the same prefix."""
    lock_a = Lock(MagicMock(), MagicMock(), MagicMock(), 'a')
    lock_b = Lock(MagicMock(), MagicMock(), MagicMock(), 'b')
    assert lock_a._prefix != lock_b._prefix


# ---------------------------------------------------------------------------
# Election — immediate leadership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_election_stores_value_as_leader_identity() -> None:
    lease_id = 7
    prefix = b'__aioetcd3:election/leader/'
    my_key = prefix + b'0000000000000007'

    range_resp = _make_range_resp([_make_kv(my_key, 1)], revision=1)
    kv, lease, watch = _make_services(lease_id=lease_id, get_side_effect=range_resp)

    async with Election(kv, lease, watch, 'leader', value=b'node-1', ttl=10):
        pass

    kv.put.assert_awaited_once_with(my_key, b'node-1', lease=lease_id)


# ---------------------------------------------------------------------------
# Election — waits for predecessor like Lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_election_waits_for_predecessor() -> None:
    lease_id = 7
    prefix = b'__aioetcd3:election/leader/'
    predecessor_key = prefix + b'0000000000000003'
    my_key = prefix + b'0000000000000007'

    range_resp_1 = _make_range_resp([_make_kv(predecessor_key, 1), _make_kv(my_key, 2)], revision=2)
    range_resp_2 = _make_range_resp([_make_kv(my_key, 2)], revision=4)

    watch_resp = _make_watch_resp([_make_delete_event(predecessor_key)])

    kv, lease, watch = _make_services(
        lease_id=lease_id,
        get_side_effect=[range_resp_1, range_resp_2],
        watch_responses=[watch_resp],
    )

    async with Election(kv, lease, watch, 'leader', value=b'node-1', ttl=10):
        pass

    assert kv.get.await_count == 2


# ---------------------------------------------------------------------------
# Lock — factory method on client raises when not connected
# ---------------------------------------------------------------------------


def test_client_lock_raises_when_not_connected() -> None:
    client = Etcd3Client(['localhost:2379'])
    with pytest.raises(RuntimeError, match='not connected'):
        client.lock('x')


def test_client_election_raises_when_not_connected() -> None:
    client = Etcd3Client(['localhost:2379'])
    with pytest.raises(RuntimeError, match='not connected'):
        client.election('x')
