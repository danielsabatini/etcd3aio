# Instruções para Agentes

Este repositório implementa o `etcd3aio`.

## Fonte da Verdade

Leia o `CONTRACT.md` primeiro.

## Regras Obrigatórias

- Python 3.13+
- Async em primeiro lugar (não bloquear o loop de eventos)
- Usar `await` nas chamadas gRPC quando aplicável
- Manter o padrão de fachada
- Manter o cliente leve
- Isolar a lógica gRPC nos serviços/conexões
- Usar tipagem forte e `TypeAlias` quando útil
- Seguir o modo Pyright configurado no `pyproject.toml`
- `ruff format`, `ruff check --fix`, `pyright` e `pytest` devem todos passar
- Não modificar os arquivos protobuf gerados
- Manter compatibilidade retroativa

## Referências
- asyncio: https://docs.python.org/3/howto/asyncio.html
- Protocolo de descoberta: https://etcd.io/docs/v3.6/dev-guide/discovery_protocol/
- Configurar um cluster local: https://etcd.io/docs/v3.6/dev-guide/local_cluster/
- Interagindo com o etcd: https://etcd.io/docs/v3.6/dev-guide/interacting_v3/
- Por que o gRPC gateway: https://etcd.io/docs/v3.6/dev-guide/api_grpc_gateway/
- Nomenclatura e descoberta gRPC: https://etcd.io/docs/v3.6/dev-guide/grpc_naming/
- Limites do sistema: https://etcd.io/docs/v3.6/dev-guide/limit/
- Funcionalidades do etcd: https://etcd.io/docs/v3.6/dev-guide/features/
- Referência da API: https://etcd.io/docs/v3.6/dev-guide/api_reference_v3/
- Referência da API: concorrência: https://etcd.io/docs/v3.6/dev-guide/api_concurrency_reference_v3/
