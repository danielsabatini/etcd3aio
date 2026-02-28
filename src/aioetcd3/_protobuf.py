from __future__ import annotations

import sys
from pathlib import Path
from typing import TypeAlias

# ruff: noqa: I001
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false

# Ensure generated protobuf modules can resolve relative imports.
_PROTO_DIR = Path(__file__).parent / 'proto'
if str(_PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTO_DIR))

# Import order matters for descriptor registration.
from google.api import annotations_pb2  # noqa: E402,F401
from google.api import http_pb2  # noqa: E402,F401
from protoc_gen_openapiv2.options import annotations_pb2 as openapi_annotations_pb2  # noqa: E402,F401
from protoc_gen_openapiv2.options import openapiv2_pb2  # noqa: E402,F401

from etcd.api.mvccpb import kv_pb2  # noqa: E402,F401
from etcd.api.authpb import auth_pb2  # noqa: E402,F401
from etcd.api.versionpb import version_pb2  # noqa: E402,F401
from etcd.api.etcdserverpb import rpc_pb2, rpc_pb2_grpc  # noqa: E402

KVStub: TypeAlias = rpc_pb2_grpc.KVStub
LeaseStub: TypeAlias = rpc_pb2_grpc.LeaseStub
WatchStub: TypeAlias = rpc_pb2_grpc.WatchStub

PutRequest: TypeAlias = rpc_pb2.PutRequest
PutResponse: TypeAlias = rpc_pb2.PutResponse
RangeRequest: TypeAlias = rpc_pb2.RangeRequest
RangeResponse: TypeAlias = rpc_pb2.RangeResponse
DeleteRangeRequest: TypeAlias = rpc_pb2.DeleteRangeRequest
DeleteRangeResponse: TypeAlias = rpc_pb2.DeleteRangeResponse

Compare: TypeAlias = rpc_pb2.Compare
RequestOp: TypeAlias = rpc_pb2.RequestOp
ResponseOp: TypeAlias = rpc_pb2.ResponseOp
TxnRequest: TypeAlias = rpc_pb2.TxnRequest
TxnResponse: TypeAlias = rpc_pb2.TxnResponse

LeaseGrantRequest: TypeAlias = rpc_pb2.LeaseGrantRequest
LeaseGrantResponse: TypeAlias = rpc_pb2.LeaseGrantResponse
LeaseRevokeRequest: TypeAlias = rpc_pb2.LeaseRevokeRequest
LeaseRevokeResponse: TypeAlias = rpc_pb2.LeaseRevokeResponse
LeaseKeepAliveRequest: TypeAlias = rpc_pb2.LeaseKeepAliveRequest
LeaseKeepAliveResponse: TypeAlias = rpc_pb2.LeaseKeepAliveResponse
LeaseTimeToLiveRequest: TypeAlias = rpc_pb2.LeaseTimeToLiveRequest
LeaseTimeToLiveResponse: TypeAlias = rpc_pb2.LeaseTimeToLiveResponse

WatchRequest: TypeAlias = rpc_pb2.WatchRequest
WatchCreateRequest: TypeAlias = rpc_pb2.WatchCreateRequest
WatchCancelRequest: TypeAlias = rpc_pb2.WatchCancelRequest
WatchResponse: TypeAlias = rpc_pb2.WatchResponse

__all__ = [
    'Compare',
    'DeleteRangeRequest',
    'DeleteRangeResponse',
    'KVStub',
    'LeaseGrantRequest',
    'LeaseGrantResponse',
    'LeaseKeepAliveRequest',
    'LeaseKeepAliveResponse',
    'LeaseRevokeRequest',
    'LeaseRevokeResponse',
    'LeaseStub',
    'LeaseTimeToLiveRequest',
    'LeaseTimeToLiveResponse',
    'PutRequest',
    'PutResponse',
    'RangeRequest',
    'RangeResponse',
    'RequestOp',
    'ResponseOp',
    'TxnRequest',
    'TxnResponse',
    'WatchCancelRequest',
    'WatchCreateRequest',
    'WatchRequest',
    'WatchResponse',
    'WatchStub',
]
