from __future__ import annotations

import logging
from importlib.metadata import version

from .auth import PermissionType, TokenRefresher
from .client import Etcd3Client
from .concurrency import Election, Lock
from .errors import (
    EtcdConnectionError,
    EtcdError,
    EtcdPermissionDeniedError,
    EtcdTransientError,
    EtcdUnauthenticatedError,
)
from .kv import SortOrder, SortTarget, prefix_range_end
from .lease import LeaseKeepalive
from .maintenance import AlarmType, DowngradeAction
from .watch import WatchFilter

__version__ = version(__name__)

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    '__version__',
    'AlarmType',
    'DowngradeAction',
    'Election',
    'Etcd3Client',
    'EtcdConnectionError',
    'EtcdError',
    'EtcdPermissionDeniedError',
    'EtcdTransientError',
    'EtcdUnauthenticatedError',
    'LeaseKeepalive',
    'Lock',
    'PermissionType',
    'SortOrder',
    'SortTarget',
    'TokenRefresher',
    'WatchFilter',
    'prefix_range_end',
]
