from __future__ import annotations

import grpc.aio

from ._protobuf import (
    ClusterStub,
    MemberAddRequest,
    MemberAddResponse,
    MemberListRequest,
    MemberListResponse,
    MemberPromoteRequest,
    MemberPromoteResponse,
    MemberRemoveRequest,
    MemberRemoveResponse,
    MemberUpdateRequest,
    MemberUpdateResponse,
)
from .base import BaseService


class ClusterService(BaseService):
    """Cluster facade: member listing, addition, removal, update and promotion."""

    def __init__(self, channel: grpc.aio.Channel, *, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._stub = ClusterStub(channel)

    async def member_list(
        self,
        *,
        linearizable: bool = True,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> MemberListResponse:
        """List all members in the cluster.

        Args:
            linearizable: If ``True`` (default), the response is linearizable,
                ensuring it reflects the latest committed cluster state.
                Set to ``False`` for a serializable (potentially stale) read that
                avoids a quorum round-trip.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Key response field: ``members`` — list of ``Member`` objects, each with
        ``ID``, ``name``, ``peerURLs``, ``clientURLs`` and ``isLearner``.
        """
        return await self._rpc(
            self._stub.MemberList,
            MemberListRequest(linearizable=linearizable),
            operation='Cluster.MemberList',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def member_add(
        self,
        peer_urls: list[str],
        *,
        is_learner: bool = False,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> MemberAddResponse:
        """Add a new member to the cluster.

        Args:
            peer_urls: Peer URL strings for the new member (e.g.
                ``['http://10.0.0.4:2380']``).
            is_learner: If ``True``, add the member as a raft learner
                (non-voting).  A learner must be promoted via
                :meth:`member_promote` before it participates in consensus.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Key response fields: ``member`` (the added ``Member``), ``members``
        (full updated member list).
        """
        return await self._rpc(
            self._stub.MemberAdd,
            MemberAddRequest(peerURLs=peer_urls, isLearner=is_learner),
            operation='Cluster.MemberAdd',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def member_remove(
        self, member_id: int, *, timeout: float | None = None, max_attempts: int | None = None
    ) -> MemberRemoveResponse:
        """Remove a member from the cluster by its numeric ID.

        Args:
            member_id: The ``ID`` field of the ``Member`` to remove (obtained
                from :meth:`member_list`).
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Key response field: ``members`` — updated full member list after removal.
        """
        return await self._rpc(
            self._stub.MemberRemove,
            MemberRemoveRequest(ID=member_id),
            operation='Cluster.MemberRemove',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def member_update(
        self,
        member_id: int,
        peer_urls: list[str],
        *,
        timeout: float | None = None,
        max_attempts: int | None = None,
    ) -> MemberUpdateResponse:
        """Update the peer URLs of an existing cluster member.

        Args:
            member_id: The ``ID`` of the member to update.
            peer_urls: New list of peer URL strings.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        Key response field: ``members`` — updated full member list.
        """
        return await self._rpc(
            self._stub.MemberUpdate,
            MemberUpdateRequest(ID=member_id, peerURLs=peer_urls),
            operation='Cluster.MemberUpdate',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def member_promote(
        self, member_id: int, *, timeout: float | None = None, max_attempts: int | None = None
    ) -> MemberPromoteResponse:
        """Promote a raft learner member to a full voting member.

        Args:
            member_id: The ``ID`` of the learner member to promote.
            timeout: Per-call deadline in seconds (``None`` = no deadline).
            max_attempts: Override the retry limit for this call (``None`` = service default).

        The member must have been added with ``is_learner=True`` via
        :meth:`member_add` and must be up to date with the leader log before
        promotion is allowed.

        Key response field: ``members`` — updated full member list after promotion.
        """
        return await self._rpc(
            self._stub.MemberPromote,
            MemberPromoteRequest(ID=member_id),
            operation='Cluster.MemberPromote',
            timeout=timeout,
            max_attempts=max_attempts,
        )
