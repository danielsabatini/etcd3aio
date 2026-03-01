from __future__ import annotations


class EtcdError(Exception):
    """Base exception for aioetcd3."""


class EtcdTransientError(EtcdError):
    """Raised when a transient gRPC error persists after retries."""


class EtcdConnectionError(EtcdError):
    """Raised when the etcd cluster is unreachable after retries."""
