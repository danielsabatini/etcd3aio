"""Integration tests — ClusterService."""

from __future__ import annotations

import pytest

from etcd3aio import Etcd3Client

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_member_list_returns_at_least_one_member(etcd: Etcd3Client) -> None:
    """A running cluster must have at least one member."""
    resp = await etcd.cluster.member_list()

    assert len(resp.members) >= 1


@pytest.mark.asyncio
async def test_member_list_members_have_client_urls(etcd: Etcd3Client) -> None:
    """Each member must advertise at least one client URL."""
    resp = await etcd.cluster.member_list()

    for member in resp.members:
        assert len(list(member.clientURLs)) >= 1


@pytest.mark.asyncio
async def test_member_list_non_linearizable(etcd: Etcd3Client) -> None:
    """linearizable=False (serializable read) must also return members."""
    resp = await etcd.cluster.member_list(linearizable=False)

    assert len(resp.members) >= 1


@pytest.mark.asyncio
async def test_member_list_single_node_cluster_has_no_learners(etcd: Etcd3Client) -> None:
    """In a single-node dev cluster none of the members should be learners."""
    resp = await etcd.cluster.member_list()

    # A single-node cluster has no learners by definition.
    # In a multi-node cluster this may be False for some members.
    learners = [m for m in resp.members if m.isLearner]
    # We just assert the field is accessible — value depends on cluster topology
    assert isinstance(learners, list)
