from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioetcd3._protobuf import (
    LeaseGrantResponse,
    LeaseLeasesResponse,
    LeaseRevokeResponse,
    LeaseTimeToLiveResponse,
)
from aioetcd3.lease import LeaseKeepalive, LeaseService


class _FakeStream:
    """Async iterable mock with a cancel() shim, mimicking a gRPC streaming call."""

    def __init__(self, *responses: object) -> None:
        self._iter = iter(responses)
        self.cancel = MagicMock()

    def __aiter__(self) -> _FakeStream:
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_grant_revoke_time_to_live() -> None:
    lease_id = 99
    grant_ttl = 30
    current_ttl = 20

    stub = MagicMock()
    stub.LeaseGrant = AsyncMock(return_value=LeaseGrantResponse(ID=lease_id, TTL=grant_ttl))
    stub.LeaseRevoke = AsyncMock(return_value=LeaseRevokeResponse())
    stub.LeaseTimeToLive = AsyncMock(
        return_value=LeaseTimeToLiveResponse(ID=lease_id, TTL=current_ttl)
    )
    stub.LeaseKeepAlive = MagicMock()

    with patch('aioetcd3.lease.LeaseStub', return_value=stub):
        service = LeaseService(channel=MagicMock())
        grant_response = await service.grant(ttl=grant_ttl, lease_id=lease_id)
        await service.revoke(lease_id=lease_id)
        ttl_response = await service.time_to_live(lease_id=lease_id, keys=True)

    assert grant_response.ID == lease_id
    assert grant_response.TTL == grant_ttl
    assert ttl_response.ID == lease_id
    assert ttl_response.TTL == current_ttl

    grant_request = stub.LeaseGrant.await_args.args[0]
    revoke_request = stub.LeaseRevoke.await_args.args[0]
    ttl_request = stub.LeaseTimeToLive.await_args.args[0]

    assert grant_request.ID == lease_id
    assert grant_request.TTL == grant_ttl
    assert revoke_request.ID == lease_id
    assert ttl_request.ID == lease_id
    assert ttl_request.keys is True


@pytest.mark.asyncio
async def test_keep_alive_starts_stream_with_lease_id() -> None:
    lease_id = 123

    stream = MagicMock()

    stub = MagicMock()
    stub.LeaseGrant = AsyncMock(return_value=LeaseGrantResponse())
    stub.LeaseRevoke = AsyncMock(return_value=LeaseRevokeResponse())
    stub.LeaseTimeToLive = AsyncMock(return_value=LeaseTimeToLiveResponse())
    stub.LeaseKeepAlive = MagicMock(return_value=stream)

    with patch('aioetcd3.lease.LeaseStub', return_value=stub):
        service = LeaseService(channel=MagicMock())
        returned_stream = service.keep_alive(lease_id=lease_id)

    assert returned_stream is stream

    request_generator = stub.LeaseKeepAlive.call_args.args[0]
    first_request = await anext(request_generator)
    assert first_request.ID == lease_id


@pytest.mark.asyncio
async def test_leases_returns_all_active_leases() -> None:
    leases_response = LeaseLeasesResponse()

    stub = MagicMock()
    stub.LeaseGrant = AsyncMock(return_value=LeaseGrantResponse())
    stub.LeaseLeases = AsyncMock(return_value=leases_response)

    with patch('aioetcd3.lease.LeaseStub', return_value=stub):
        service = LeaseService(channel=MagicMock())
        response = await service.leases()

    assert response is leases_response
    stub.LeaseLeases.assert_awaited_once()


# ---------------------------------------------------------------------------
# LeaseKeepalive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_keep_alive_context_lifecycle() -> None:
    """Context manager starts a background task and cancels it cleanly on exit."""
    stub = MagicMock()
    # LeaseKeepAlive won't be reached because the task sleeps first
    stub.LeaseKeepAlive = MagicMock()

    ka = LeaseKeepalive(stub, lease_id=42, ttl=30)

    async with ka:
        assert ka.alive is True
        assert ka._task is not None
        assert not ka._task.done()

    # After __aexit__: task cancelled and awaited, reference cleared
    assert ka._task is None
    assert ka.alive is True  # Not expired, just cancelled


@pytest.mark.asyncio
async def test_keep_alive_context_marks_alive_false_when_lease_expires() -> None:
    """When the server reports TTL=0, alive becomes False."""
    stream = _FakeStream(MagicMock(TTL=0))
    stub = MagicMock()
    stub.LeaseKeepAlive = MagicMock(return_value=stream)

    with patch('asyncio.sleep', new=AsyncMock()):
        ka = LeaseKeepalive(stub, lease_id=99, ttl=3)
        await ka._run()

    assert ka.alive is False
    stream.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_keep_alive_context_adjusts_interval_from_server_ttl() -> None:
    """Interval for each subsequent sleep is derived from the server-reported TTL."""
    # First stream: TTL=15 → next interval = max(1, 15//3) = 5
    # Second stream: TTL=0  → alive=False, stop
    stream1 = _FakeStream(MagicMock(TTL=15))
    stream2 = _FakeStream(MagicMock(TTL=0))
    stub = MagicMock()
    stub.LeaseKeepAlive = MagicMock(side_effect=[stream1, stream2])

    sleep_calls: list[float] = []

    async def _fake_sleep(secs: float) -> None:
        sleep_calls.append(secs)

    with patch('asyncio.sleep', new=_fake_sleep):
        ka = LeaseKeepalive(stub, lease_id=99, ttl=9)  # initial interval = max(1, 9//3) = 3
        await ka._run()

    assert sleep_calls == [3, 5]  # 9//3=3, then 15//3=5
    assert ka.alive is False
