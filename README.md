# aioetcd3

Async etcd v3 client for Python using `grpc.aio`.

## Principles

- Simple facade API
- Async-first
- Strong typing
- Easy to maintain

## Requirements

- Python 3.13+
- etcd v3

## Quick Start

Start a local etcd cluster:

```bash
docker compose -f docker/docker-compose.yaml up -d
```

Basic usage:

```python
import asyncio

from aioetcd3 import Etcd3Client


async def main() -> None:
    async with Etcd3Client(['localhost:2379']) as client:
        await client.kv.put('foo', 'bar')
        response = await client.kv.get('foo')
        print(response.kvs[0].value)


if __name__ == '__main__':
    asyncio.run(main())
```

## Project Docs

- `CONTRACT.md`: non-negotiable project contract
- `ARCHITECTURE.md`: module boundaries and responsibilities
- `CONTRIBUTING.md`: local workflow and quality checks
- `ROADMAP.md`: next features
