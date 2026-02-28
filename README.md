# aioetcd3

Native asyncio Python client for etcd v3 built on grpc.aio.

## Goals

- Native async client
- Strict typing
- Linearizable operations by default
- gRPC based (no HTTP gateway)

## Features

Current:

- KV API
- Lease API
- Watch API
- Round robin connection manager

Planned:

- Transactions
- Distributed locks
- Leader election
- Authentication
- Maintenance API

## Quickstart

Start local cluster

docker compose up -d

Example

```python
import asyncio
from aioetcd3.client import Etcd3Client

async def main():
    async with Etcd3Client(["localhost:2379"]) as cli:
        await cli.kv.put("foo", "bar")
        res = await cli.kv.get("foo")
        print(res)

asyncio.run(main())