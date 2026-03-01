# Roadmap

Referência: [API etcd v3.6](https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/)

## Implementado

### Serviço KV
- `Range` → `kv.get()` — com `limit`, `sort_order` / `sort_target` (`SortOrder`, `SortTarget`), `keys_only`, `count_only`
- `Put` → `kv.put()`
- `DeleteRange` → `kv.delete()`
- `Compact` → `kv.compact()`
- `Txn` → `kv.txn()` + helpers de comparação/operação
- `prefix_range_end()` — helper para construir o limite superior exclusivo para varreduras de prefixo

### Serviço Lease
- `LeaseGrant` → `lease.grant()`
- `LeaseRevoke` → `lease.revoke()`
- `LeaseTimeToLive` → `lease.time_to_live()`
- `LeaseKeepAlive` → `lease.keep_alive()` (stream bruto) / `lease.keep_alive_context()` (tarefa em segundo plano)
- `LeaseLeases` → `lease.leases()`

### Serviço Watch
- `Watch` → `watch.watch()` — com `filters` (`WatchFilter`) e `progress_notify`

### Serviço Maintenance
- `Status` → `maintenance.status()`
- `Alarm` (GET) → `maintenance.alarms()`
- `Alarm` (DEACTIVATE) → `maintenance.alarm_deactivate()`

### Primitivos de Concorrência
- `Lock` → `client.lock()` — lock distribuído
- `Election` → `client.election()` — eleição de líder

### Serviço Auth (voltado ao desenvolvedor)
- `AuthStatus` → `auth.auth_status()` — verifica se a autenticação está habilitada no cluster
- `Authenticate` → `auth.authenticate()` — obtém um token para um par usuário/senha

### Cliente
- Gerenciador de conexão com balanceamento de carga round-robin
- Retry com backoff exponencial (`BaseService._rpc`)
- Timeout por chamada: `timeout: float | None = None` em todos os métodos de serviço (`asyncio.timeout()`)
- `client.ping()` — verificação de conectividade e quórum de escrita
- Mapeamento de erros de autenticação: `EtcdUnauthenticatedError`, `EtcdPermissionDeniedError`
- `client.set_token()` / parâmetro `token=` no construtor — propaga o token de autenticação para todos os serviços como metadata do gRPC
- `client.token_refresher(name, password)` / `TokenRefresher` — gerenciador de contexto em segundo plano que re-autentica antes do token expirar

---

## Admin (adiado)

> Operações para administradores de cluster, não para desenvolvedores de aplicações.


### Serviço Cluster
- `MemberList` — lista todos os membros com suas URLs de peer/client
- `MemberAdd` / `MemberRemove` / `MemberUpdate` — gerenciamento de membros
- `MemberPromote` — promove um learner a membro votante

### Serviço Auth (admin)
- `AuthEnable` / `AuthDisable` — habilitar/desabilitar autenticação
- Gerenciamento de usuários: `UserAdd`, `UserGet`, `UserList`, `UserDelete`, `UserChangePassword`
- Gerenciamento de roles: `RoleAdd`, `RoleGet`, `RoleList`, `RoleDelete`
- RBAC: `UserGrantRole`, `UserRevokeRole`, `RoleGrantPermission`, `RoleRevokePermission`

### Maintenance (pesado para admin)
- `Defragment` — recuperar espaço de armazenamento do backend
- `Snapshot` — transmitir um backup completo do banco de dados backend
- `MoveLeader` — transferir liderança para outro membro
- `Hash` / `HashKV` — checksum para verificação de integridade de dados
- `Downgrade` — gerenciar downgrade de versão do cluster
