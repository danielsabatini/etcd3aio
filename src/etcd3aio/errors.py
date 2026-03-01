from __future__ import annotations


class EtcdError(Exception):
    """Base exception for etcd3aio."""


class EtcdTransientError(EtcdError):
    """Raised when a transient gRPC error persists after retries."""


class EtcdConnectionError(EtcdError):
    """Raised when the etcd cluster is unreachable after retries."""


class EtcdUnauthenticatedError(EtcdError):
    """Raised when the request is not authenticated or credentials are invalid.

    Common causes:
    - Invalid username or password passed to ``auth.authenticate()``.
    - Missing or expired auth token on a cluster with auth enabled.
    - Authentication is not enabled on the cluster.
    """


class EtcdPermissionDeniedError(EtcdError):
    """Raised when the authenticated user lacks permission for the requested operation."""
