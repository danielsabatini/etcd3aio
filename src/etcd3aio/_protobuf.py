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

AuthStub: TypeAlias = rpc_pb2_grpc.AuthStub
KVStub: TypeAlias = rpc_pb2_grpc.KVStub
LeaseStub: TypeAlias = rpc_pb2_grpc.LeaseStub
MaintenanceStub: TypeAlias = rpc_pb2_grpc.MaintenanceStub
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
CompactionRequest: TypeAlias = rpc_pb2.CompactionRequest
CompactionResponse: TypeAlias = rpc_pb2.CompactionResponse

LeaseGrantRequest: TypeAlias = rpc_pb2.LeaseGrantRequest
LeaseGrantResponse: TypeAlias = rpc_pb2.LeaseGrantResponse
LeaseRevokeRequest: TypeAlias = rpc_pb2.LeaseRevokeRequest
LeaseRevokeResponse: TypeAlias = rpc_pb2.LeaseRevokeResponse
LeaseKeepAliveRequest: TypeAlias = rpc_pb2.LeaseKeepAliveRequest
LeaseKeepAliveResponse: TypeAlias = rpc_pb2.LeaseKeepAliveResponse
LeaseTimeToLiveRequest: TypeAlias = rpc_pb2.LeaseTimeToLiveRequest
LeaseTimeToLiveResponse: TypeAlias = rpc_pb2.LeaseTimeToLiveResponse
LeaseLeasesRequest: TypeAlias = rpc_pb2.LeaseLeasesRequest
LeaseLeasesResponse: TypeAlias = rpc_pb2.LeaseLeasesResponse

StatusRequest: TypeAlias = rpc_pb2.StatusRequest
StatusResponse: TypeAlias = rpc_pb2.StatusResponse
AlarmRequest: TypeAlias = rpc_pb2.AlarmRequest
AlarmResponse: TypeAlias = rpc_pb2.AlarmResponse
AlarmMember: TypeAlias = rpc_pb2.AlarmMember
DefragmentRequest: TypeAlias = rpc_pb2.DefragmentRequest
DefragmentResponse: TypeAlias = rpc_pb2.DefragmentResponse
HashKVRequest: TypeAlias = rpc_pb2.HashKVRequest
HashKVResponse: TypeAlias = rpc_pb2.HashKVResponse
SnapshotRequest: TypeAlias = rpc_pb2.SnapshotRequest
SnapshotResponse: TypeAlias = rpc_pb2.SnapshotResponse
MoveLeaderRequest: TypeAlias = rpc_pb2.MoveLeaderRequest
MoveLeaderResponse: TypeAlias = rpc_pb2.MoveLeaderResponse

WatchRequest: TypeAlias = rpc_pb2.WatchRequest
WatchCreateRequest: TypeAlias = rpc_pb2.WatchCreateRequest
WatchCancelRequest: TypeAlias = rpc_pb2.WatchCancelRequest
WatchResponse: TypeAlias = rpc_pb2.WatchResponse

AuthenticateRequest: TypeAlias = rpc_pb2.AuthenticateRequest
AuthenticateResponse: TypeAlias = rpc_pb2.AuthenticateResponse
AuthStatusRequest: TypeAlias = rpc_pb2.AuthStatusRequest
AuthStatusResponse: TypeAlias = rpc_pb2.AuthStatusResponse
AuthEnableRequest: TypeAlias = rpc_pb2.AuthEnableRequest
AuthEnableResponse: TypeAlias = rpc_pb2.AuthEnableResponse
AuthDisableRequest: TypeAlias = rpc_pb2.AuthDisableRequest
AuthDisableResponse: TypeAlias = rpc_pb2.AuthDisableResponse
AuthUserAddRequest: TypeAlias = rpc_pb2.AuthUserAddRequest
AuthUserAddResponse: TypeAlias = rpc_pb2.AuthUserAddResponse
AuthUserGetRequest: TypeAlias = rpc_pb2.AuthUserGetRequest
AuthUserGetResponse: TypeAlias = rpc_pb2.AuthUserGetResponse
AuthUserListRequest: TypeAlias = rpc_pb2.AuthUserListRequest
AuthUserListResponse: TypeAlias = rpc_pb2.AuthUserListResponse
AuthUserDeleteRequest: TypeAlias = rpc_pb2.AuthUserDeleteRequest
AuthUserDeleteResponse: TypeAlias = rpc_pb2.AuthUserDeleteResponse
AuthUserChangePasswordRequest: TypeAlias = rpc_pb2.AuthUserChangePasswordRequest
AuthUserChangePasswordResponse: TypeAlias = rpc_pb2.AuthUserChangePasswordResponse
AuthUserGrantRoleRequest: TypeAlias = rpc_pb2.AuthUserGrantRoleRequest
AuthUserGrantRoleResponse: TypeAlias = rpc_pb2.AuthUserGrantRoleResponse
AuthUserRevokeRoleRequest: TypeAlias = rpc_pb2.AuthUserRevokeRoleRequest
AuthUserRevokeRoleResponse: TypeAlias = rpc_pb2.AuthUserRevokeRoleResponse
AuthRoleAddRequest: TypeAlias = rpc_pb2.AuthRoleAddRequest
AuthRoleAddResponse: TypeAlias = rpc_pb2.AuthRoleAddResponse
AuthRoleGetRequest: TypeAlias = rpc_pb2.AuthRoleGetRequest
AuthRoleGetResponse: TypeAlias = rpc_pb2.AuthRoleGetResponse
AuthRoleListRequest: TypeAlias = rpc_pb2.AuthRoleListRequest
AuthRoleListResponse: TypeAlias = rpc_pb2.AuthRoleListResponse
AuthRoleDeleteRequest: TypeAlias = rpc_pb2.AuthRoleDeleteRequest
AuthRoleDeleteResponse: TypeAlias = rpc_pb2.AuthRoleDeleteResponse
AuthRoleGrantPermissionRequest: TypeAlias = rpc_pb2.AuthRoleGrantPermissionRequest
AuthRoleGrantPermissionResponse: TypeAlias = rpc_pb2.AuthRoleGrantPermissionResponse
AuthRoleRevokePermissionRequest: TypeAlias = rpc_pb2.AuthRoleRevokePermissionRequest
AuthRoleRevokePermissionResponse: TypeAlias = rpc_pb2.AuthRoleRevokePermissionResponse
Permission: TypeAlias = auth_pb2.Permission
UserAddOptions: TypeAlias = auth_pb2.UserAddOptions

__all__ = [
    'AlarmMember',
    'AlarmRequest',
    'AlarmResponse',
    'AuthDisableRequest',
    'AuthDisableResponse',
    'AuthEnableRequest',
    'AuthEnableResponse',
    'AuthRoleAddRequest',
    'AuthRoleAddResponse',
    'AuthRoleDeleteRequest',
    'AuthRoleDeleteResponse',
    'AuthRoleGetRequest',
    'AuthRoleGetResponse',
    'AuthRoleGrantPermissionRequest',
    'AuthRoleGrantPermissionResponse',
    'AuthRoleListRequest',
    'AuthRoleListResponse',
    'AuthRoleRevokePermissionRequest',
    'AuthRoleRevokePermissionResponse',
    'AuthStub',
    'AuthStatusRequest',
    'AuthStatusResponse',
    'AuthUserAddRequest',
    'AuthUserAddResponse',
    'AuthUserChangePasswordRequest',
    'AuthUserChangePasswordResponse',
    'AuthUserDeleteRequest',
    'AuthUserDeleteResponse',
    'AuthUserGetRequest',
    'AuthUserGetResponse',
    'AuthUserGrantRoleRequest',
    'AuthUserGrantRoleResponse',
    'AuthUserListRequest',
    'AuthUserListResponse',
    'AuthUserRevokeRoleRequest',
    'AuthUserRevokeRoleResponse',
    'AuthenticateRequest',
    'AuthenticateResponse',
    'Compare',
    'CompactionRequest',
    'CompactionResponse',
    'DefragmentRequest',
    'DefragmentResponse',
    'DeleteRangeRequest',
    'DeleteRangeResponse',
    'HashKVRequest',
    'HashKVResponse',
    'KVStub',
    'LeaseGrantRequest',
    'LeaseGrantResponse',
    'LeaseKeepAliveRequest',
    'LeaseKeepAliveResponse',
    'LeaseLeasesRequest',
    'LeaseLeasesResponse',
    'LeaseRevokeRequest',
    'LeaseRevokeResponse',
    'LeaseStub',
    'LeaseTimeToLiveRequest',
    'LeaseTimeToLiveResponse',
    'MaintenanceStub',
    'MoveLeaderRequest',
    'MoveLeaderResponse',
    'Permission',
    'UserAddOptions',
    'PutRequest',
    'PutResponse',
    'RangeRequest',
    'RangeResponse',
    'RequestOp',
    'ResponseOp',
    'SnapshotRequest',
    'SnapshotResponse',
    'StatusRequest',
    'StatusResponse',
    'TxnRequest',
    'TxnResponse',
    'WatchCancelRequest',
    'WatchCreateRequest',
    'WatchRequest',
    'WatchResponse',
    'WatchStub',
]
