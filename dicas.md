export ETCDCTL_ENDPOINTS=http://localhost:2379,http://localhost:3379,http://localhost:4379
etcdctl endpoint health    
etcdctl member list
etcdctl endpoint status -w table
etcdctl put /app/desired_state '{"replicas": 3, "version": "v1.2"}'
etcdctl get /app/desired_state 
docker stop etcd1
etcdctl --endpoints=http://localhost:3379,http://localhost:4379 endpoint status -w table
etcdctl --endpoints=http://localhost:3379 put /app/status '{"running": 2, "degraded": true}'
docker start etcd1
etcdctl --endpoints=http://localhost:2379 get /app/status
etcdctl del --prefix /app/


# Cria as pastas necessárias
mkdir -p temp_proto/etcd/api/{etcdserverpb,mvccpb,authpb,versionpb}
mkdir -p temp_proto/google/api
mkdir -p temp_proto/protoc-gen-openapiv2/options

# Baixa os arquivos do etcd (branch release-3.6)
curl -sSL https://raw.githubusercontent.com/etcd-io/etcd/release-3.6/api/etcdserverpb/rpc.proto -o temp_proto/etcd/api/etcdserverpb/rpc.proto
curl -sSL https://raw.githubusercontent.com/etcd-io/etcd/release-3.6/api/mvccpb/kv.proto -o temp_proto/etcd/api/mvccpb/kv.proto
curl -sSL https://raw.githubusercontent.com/etcd-io/etcd/release-3.6/api/authpb/auth.proto -o temp_proto/etcd/api/authpb/auth.proto
curl -sSL https://raw.githubusercontent.com/etcd-io/etcd/release-3.6/api/versionpb/version.proto -o temp_proto/etcd/api/versionpb/version.proto

# Baixa os arquivos do Google API
curl -sSL https://raw.githubusercontent.com/googleapis/googleapis/master/google/api/annotations.proto -o temp_proto/google/api/annotations.proto
curl -sSL https://raw.githubusercontent.com/googleapis/googleapis/master/google/api/http.proto -o temp_proto/google/api/http.proto

# Baixa os arquivos do grpc-gateway / openapiv2
curl -sSL https://raw.githubusercontent.com/grpc-ecosystem/grpc-gateway/main/protoc-gen-openapiv2/options/annotations.proto -o temp_proto/protoc-gen-openapiv2/options/annotations.proto
curl -sSL https://raw.githubusercontent.com/grpc-ecosystem/grpc-gateway/main/protoc-gen-openapiv2/options/openapiv2.proto -o temp_proto/protoc-gen-openapiv2/options/openapiv2.proto

echo "Todos os arquivos foram baixados com sucesso!"

mkdir -p ./src/aioetcd3/proto

python -m grpc_tools.protoc \
    -I ./temp_proto \
    --python_out=./src/aioetcd3/proto \
    --grpc_python_out=./src/aioetcd3/proto \
    ./temp_proto/etcd/api/etcdserverpb/rpc.proto \
    ./temp_proto/etcd/api/mvccpb/kv.proto \
    ./temp_proto/etcd/api/authpb/auth.proto


find docker src tests -type f \( -name "*.py" -o -name "*.yaml" -o -name "*.toml" \) \
  -not -path "*/__pycache__/*" \
  -not -path "*/.egg-info/*" \
  -not -path "*/.pytest_cache/*" \
  | sort \
  | while read f; do 
      echo "\n================ FILE: $f ================"
      cat "$f"
    done | pbcopy