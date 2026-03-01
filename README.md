# etcd3aio

Cliente assíncrono para etcd v3 em Python usando `grpc.aio`.

## Princípios

- API de fachada simples
- Async em primeiro lugar
- Tipagem forte
- Fácil de manter

## Requisitos

- Python 3.13+
- etcd v3

## Início Rápido

Inicie um cluster etcd local:

```bash
docker compose -f docker/docker-compose.yaml up -d
```

Uso básico:

```python
import asyncio

from etcd3aio import Etcd3Client


async def main() -> None:
    async with Etcd3Client(['localhost:2379']) as client:
        await client.kv.put('foo', 'bar')
        response = await client.kv.get('foo')
        print(response.kvs[0].value)


if __name__ == '__main__':
    asyncio.run(main())
```

## Documentação do Projeto

- `CONTRACT.md`: contrato não negociável do projeto
- `ARCHITECTURE.md`: limites e responsabilidades dos módulos
- `CONTRIBUTING.md`: fluxo de trabalho local e verificações de qualidade
- `ROADMAP.md`: próximas funcionalidades
