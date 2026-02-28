Adicionamos TypeAlias para satisfazer o Pyright.
import sys
from pathlib import Path
from typing import TypeAlias

# 1. Injeção do diretório 'proto' no sys.path
_proto_dir = Path(__file__).parent / 'proto'
if str(_proto_dir) not in sys.path:
    sys.path.insert(0, str(_proto_dir))

# 2. Importação na ordem exigida pelo gRPC para evitar conflitos de descritores
from etcd.api.mvccpb import kv_pb2 # noqa: F401
from etcd.api.authpb import auth_pb2 # noqa: F401
from etcd.api.versionpb import version_pb2 # noqa: F401
from etcd.api.etcdserverpb import rpc_pb2, rpc_pb2_grpc

# ==============================================================================
# 3. Exportação de Stubs (Clientes de Serviço) como TypeAliases
# ==============================================================================
KVStub: TypeAlias = rpc_pb2_grpc.KVStub
LeaseStub: TypeAlias = rpc_pb2_grpc.LeaseStub
WatchStub: TypeAlias = rpc_pb2_grpc.WatchStub

# ==============================================================================
# 4. Exportação de Mensagens como TypeAliases
# ==============================================================================
# KV
PutRequest: TypeAlias = rpc_pb2.PutRequest
RangeRequest: TypeAlias = rpc_pb2.RangeRequest
DeleteRangeRequest: TypeAlias = rpc_pb2.DeleteRangeRequest

# Lease
LeaseGrantRequest: TypeAlias = rpc_pb2.LeaseGrantRequest
LeaseRevokeRequest: TypeAlias = rpc_pb2.LeaseRevokeRequest
LeaseKeepAliveRequest: TypeAlias = rpc_pb2.LeaseKeepAliveRequest
LeaseTimeToLiveRequest: TypeAlias = rpc_pb2.LeaseTimeToLiveRequest

# Watch
WatchRequest: TypeAlias = rpc_pb2.WatchRequest
WatchCreateRequest: TypeAlias = rpc_pb2.WatchCreateRequest
WatchCancelRequest: TypeAlias = rpc_pb2.WatchCancelRequest
WatchResponse: TypeAlias = rpc_pb2.WatchResponse