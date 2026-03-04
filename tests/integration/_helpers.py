"""Shared async helpers for integration test fixtures."""

from __future__ import annotations

from etcd3aio import Etcd3Client
from etcd3aio.kv import prefix_range_end


async def delete_test_keys(client: Etcd3Client, prefix: str) -> None:
    """Delete all keys under *prefix* in etcd.

    Used by both the plain-TCP and TLS conftest ``cleanup`` fixtures so that
    cleanup logic is not duplicated and remains consistent.
    """
    await client.kv.delete(prefix, range_end=prefix_range_end(prefix))
