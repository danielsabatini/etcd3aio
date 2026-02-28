_proto_dir = Path(__file__).parent / 'proto'
if str(_proto_dir) not in sys.path:
    sys.path.insert(0, str(_proto_dir))

# 2. Importação na ordem exigida pelo gRPC para evitar conflitos de descritores
from etcd.api.mvccpb import kv_pb2 # noqa: F401
from etcd.api.authpb import auth_pb2 # noqa: F401
from etcd.api.versionpb import version_pb2 # noqa: F401
from etcd.api.etcdserverpb import rpc_pb2, rpc_pb2_grpc

# ==============================================================================
# 3. Exportação de Stubs (Clientes de Serviço)
# ==============================================================================
KVStub = rpc_pb2_grpc.KVStub
LeaseStub = rpc_pb2_grpc.LeaseStub
WatchStub = rpc_pb2_grpc.WatchStub

# ==============================================================================
# 4. Exportação de Mensagens (Requisições e Respostas)
# ==============================================================================
# KV
PutRequest = rpc_pb2.PutRequest
RangeRequest = rpc_pb2.RangeRequest
DeleteRangeRequest = rpc_pb2.DeleteRangeRequest

# Lease
LeaseGrantRequest = rpc_pb2.LeaseGrantRequest
LeaseRevokeRequest = rpc_pb2.LeaseRevokeRequest
LeaseKeepAliveRequest = rpc_pb2.LeaseKeepAliveRequest
LeaseTimeToLiveRequest = rpc_pb2.LeaseTimeToLiveRequest

# Watch
WatchRequest = rpc_pb2.WatchRequest
WatchCreateRequest = rpc_pb2.WatchCreateRequest
WatchCancelRequest = rpc_pb2.WatchCancelRequest
WatchResponse = rpc_pb2.WatchResponse