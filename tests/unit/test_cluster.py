from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from etcd3aio._protobuf import (
    MemberAddResponse,
    MemberListResponse,
    MemberPromoteResponse,
    MemberRemoveResponse,
    MemberUpdateResponse,
)
from etcd3aio.cluster import ClusterService

_PEER_URLS = ['http://10.0.0.2:2380']


# ---------------------------------------------------------------------------
# member_list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_list_default_linearizable() -> None:
    response = MemberListResponse()

    stub = MagicMock()
    stub.MemberList = AsyncMock(return_value=response)

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        result = await service.member_list()

    assert result is response
    request = stub.MemberList.await_args.args[0]
    assert request.linearizable is True


@pytest.mark.asyncio
async def test_member_list_non_linearizable() -> None:
    stub = MagicMock()
    stub.MemberList = AsyncMock(return_value=MemberListResponse())

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        await service.member_list(linearizable=False)

    request = stub.MemberList.await_args.args[0]
    assert request.linearizable is False


# ---------------------------------------------------------------------------
# member_add
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_add_voting_member() -> None:
    response = MemberAddResponse()

    stub = MagicMock()
    stub.MemberAdd = AsyncMock(return_value=response)

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        result = await service.member_add(_PEER_URLS)

    assert result is response
    request = stub.MemberAdd.await_args.args[0]
    assert list(request.peerURLs) == _PEER_URLS
    assert request.isLearner is False


@pytest.mark.asyncio
async def test_member_add_learner() -> None:
    stub = MagicMock()
    stub.MemberAdd = AsyncMock(return_value=MemberAddResponse())

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        await service.member_add(_PEER_URLS, is_learner=True)

    request = stub.MemberAdd.await_args.args[0]
    assert request.isLearner is True


# ---------------------------------------------------------------------------
# member_remove
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_remove_sends_member_id() -> None:
    response = MemberRemoveResponse()

    stub = MagicMock()
    stub.MemberRemove = AsyncMock(return_value=response)

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        result = await service.member_remove(member_id=99)

    assert result is response
    request = stub.MemberRemove.await_args.args[0]
    assert request.ID == 99


# ---------------------------------------------------------------------------
# member_update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_update_sends_id_and_peer_urls() -> None:
    response = MemberUpdateResponse()
    new_urls = ['http://10.0.0.5:2380']

    stub = MagicMock()
    stub.MemberUpdate = AsyncMock(return_value=response)

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        result = await service.member_update(member_id=7, peer_urls=new_urls)

    assert result is response
    request = stub.MemberUpdate.await_args.args[0]
    assert request.ID == 7
    assert list(request.peerURLs) == new_urls


# ---------------------------------------------------------------------------
# member_promote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_promote_sends_member_id() -> None:
    response = MemberPromoteResponse()

    stub = MagicMock()
    stub.MemberPromote = AsyncMock(return_value=response)

    with patch('etcd3aio.cluster.ClusterStub', return_value=stub):
        service = ClusterService(channel=MagicMock())
        result = await service.member_promote(member_id=42)

    assert result is response
    request = stub.MemberPromote.await_args.args[0]
    assert request.ID == 42
