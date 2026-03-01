# Arquitetura

O `etcd3aio` é organizado como uma fachada fina sobre serviços gRPC assíncronos.

## Módulos

- `client.py`: ciclo de vida e fiação dos serviços (`Etcd3Client`); fábricas `lock()` / `election()` / `token_refresher()`
- `connections.py`: criação de canal, TLS, balanceamento de carga round-robin, keepalive do gRPC
- `base.py`: helper de retry/backoff para RPC unário compartilhado; `asyncio.timeout()` por chamada; mapeia `UNAUTHENTICATED` → `EtcdUnauthenticatedError`, `PERMISSION_DENIED` → `EtcdPermissionDeniedError`; `set_token()` injeta o token de autenticação como metadata do gRPC
- `kv.py`: operações KV (put/get/delete/compact/txn); enums `SortOrder` / `SortTarget`; utilitário `prefix_range_end()`
- `lease.py`: operações de lease (grant/revoke/time_to_live/keep_alive/leases); gerenciador de contexto assíncrono `LeaseKeepalive` para keepalive em segundo plano
- `auth.py`: autenticação voltada ao desenvolvedor — `auth_status()` / `authenticate()`; gerenciador de contexto assíncrono `TokenRefresher` para renovação automática de token
- `maintenance.py`: status do cluster e gerenciamento de alarmes; enum `AlarmType`
- `concurrency.py`: lock distribuído (`Lock`) e eleição de líder (`Election`) construídos sobre KV + Lease; `Election` expõe `leader()`, `proclaim()` e `observe()` além do ciclo Campaign/Resign
- `watch.py`: stream de watch com reconexão automática e rastreamento de revisão; enum `WatchFilter` para filtragem de eventos no servidor
- `_protobuf.py`: aliases de protobuf/stub e bootstrap de importação
- `errors.py`: exceções da biblioteca (`EtcdError`, `EtcdConnectionError`, `EtcdTransientError`, `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`)

## Limites de Design

- A fachada permanece pequena.
- Os detalhes do gRPC ficam fora da API voltada ao usuário.
- Os módulos de serviço devem ser coesos e fáceis de testar.
- Evitar herança profunda e indireção complexa.

## Fluxo de Requisição

1. Usuário chama o método de serviço da fachada.
2. O serviço constrói o objeto de requisição protobuf.
3. O serviço executa a chamada gRPC.
4. O helper de retry trata falhas transitórias unárias.
5. A resposta é retornada como objeto protobuf.

## Não-Objetivos (por ora)

- DSLs personalizadas para operações etcd
- Framework pesado de plugins/interceptores
- Gerenciador de watch multiplexado para fan-out em larga escala
